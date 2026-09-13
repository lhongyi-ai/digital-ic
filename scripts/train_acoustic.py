#!/usr/bin/env python3
"""Normal-only MIMII feasibility, quantization, frozen export; test requires --evaluate-test."""
import argparse,copy,hashlib,json,math,sys
from pathlib import Path
import numpy as np
import torch
from torch import nn
from sklearn.metrics import roc_auc_score,confusion_matrix
from vibfpga.fixed import frontend_batch_powers,quantize_features,round_shift_even
from vibfpga.acoustic import features_from_powers,infer,classify
from vibfpga.export import export_model,write_hex
from vibfpga.mimii import validate_plan,sha
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--evaluate-test',action='store_true');a=p.parse_args()
d=ROOT/'data/mimii';out=ROOT/'artifacts/acoustic';out.mkdir(exist_ok=True)
plan=json.loads((d/'plan.json').read_text());validate_plan(plan)
torch.set_num_threads(2)

def dump(path,obj):path.write_text(json.dumps(obj,indent=2)+'\n')
def metrics(labels,scores,threshold):
    y=np.array(labels);s=np.array(scores);pred=s>threshold
    tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
    return {'auc':float(roc_auc_score(y,s)),'pauc_fpr_0_1_standardized':float(roc_auc_score(y,s,max_fpr=.1)),
        'threshold':float(threshold),'fpr':float(fp/(tn+fp)),'recall':float(tp/(tp+fn)),
        'confusion_matrix':[[int(tn),int(fp)],[int(fn),int(tp)]],'record_count':len(y)}

def load(split):
    items=[x for x in plan['records'] if x['split']==split];frames=[]
    for info in items:
        path=d/info['local'];meta=json.loads(path.with_suffix('.json').read_text())
        if sha(path.read_bytes())!=meta['npy_sha256'] or meta['plan_sha256']!=sha((d/'plan.json').read_bytes()):raise ValueError('data binding changed')
        x=np.load(path);frames.append(x[:len(x)//1024*1024].reshape(-1,1024))
    return items,np.stack(frames)

def powers(frames,bins,tag):
    cache=ROOT/'build'/f'acoustic-powers-{tag}.npz'
    key=sha(frames.tobytes()+np.array(bins).tobytes()+b'input_shift=0;N=1024')
    if cache.exists():
        q=np.load(cache)
        if str(q['key'])==key:return q['powers']
    expanded=(np.array(bins)[:,None]+[-1,0,1]).reshape(-1)
    shape=frames.shape;flat=frames.reshape(-1,1024);parts=[]
    for start in range(0,len(flat),128):parts.append(frontend_batch_powers(flat[start:start+128],expanded,input_shift=0).reshape(-1,16,3).sum(2))
    v=np.concatenate(parts).reshape(shape[0],shape[1],16);np.savez(cache,powers=v,key=key);return v

def scores(x,m):
    flat=x.reshape(-1,16);h=np.clip(round_shift_even(np.maximum(flat@np.array(m['w1']).T+m['b1'],0),m['hidden_shift']),0,127)
    y=np.clip(round_shift_even(h@np.array(m['w2']).T+m['b2'],m['output_shift']),0,127)
    return ((flat-y)**2).sum(1).reshape(x.shape[:-1])

def quant(net,train_x,config):
    w1,b1=net[0].weight.detach().numpy(),net[0].bias.detach().numpy()
    w2,b2=net[2].weight.detach().numpy(),net[2].bias.detach().numpy()
    exp=lambda v:int(math.ceil(math.log2(max(float(np.max(np.abs(v))),1e-9)/127)))
    e1,e2=exp(w1),exp(w2);h=np.maximum(train_x@w1.T+b1,0);eh=max(exp(h),-7+e1)
    hs=eh-(-7+e1);os=-7-(eh+e2)
    if os<0:raise ValueError('negative output shift unsupported')
    q1=np.clip(np.rint(w1/2.**e1),-127,127).astype(int);qb1=np.rint(b1/2.**(-7+e1)).astype(np.int64)
    q2=np.clip(np.rint(w2/2.**e2),-127,127).astype(int);qb2=np.rint(b2/2.**(eh+e2)).astype(np.int64)
    # Pad hidden to 16 for existing ROM banking; only first 8 have learned weights.
    qw1=np.zeros((16,16),int);qw1[:8]=q1;qw2=np.zeros((16,16),int);qw2[:,:8]=q2;qbb1=np.zeros(16,np.int64);qbb1[:8]=qb1
    for w,b in [(qw1,qbb1),(qw2,qb2)]:
        if np.any(np.abs(w).sum(1)*127+np.abs(b)>=1<<31):raise OverflowError('conservative INT32 bound')
    return {**config,'w1':qw1.tolist(),'w2':qw2.tolist(),'b1':qbb1.tolist(),'b2':qb2.tolist(),'hidden_shift':hs,'output_shift':os,
            'hidden_active':8,'hidden_storage':16,'output_features':16,'scales':{'input':2.**-7,'w1':2.**e1,'hidden':2.**eh,'w2':2.**e2},
            'rounding':'nearest ties even','score':'sum sixteen squared INT8 reconstruction errors','score_max':258064,'alarm_windows':3}

if a.evaluate_test:
    freeze=json.loads((out/'frozen.json').read_text())
    for rel,h in freeze['sha256'].items():
        if sha((ROOT/rel).read_bytes())!=h:raise ValueError('frozen artifact changed')
    attempt=out/'test-attempt.json'
    with attempt.open('x') as f:json.dump({'started':True,'freeze_sha256':sha((out/'frozen.json').read_bytes())},f)
    m=json.loads((out/'model/model.json').read_text());items,frames=load('test')
    pp=powers(frames,m['bins'],'test');x=features_from_powers(pp,m);ss=scores(x,m).mean(1)
    result=metrics([i['label'] for i in items],ss,m['clip_threshold'])
    result.update(freeze_sha256=sha((out/'frozen.json').read_bytes()),scope=plan['scope'],predictions=[{'record':i['name'],'label':i['label'],'score':float(s)} for i,s in zip(items,ss)])
    dump(out/'test.json',result);print(json.dumps(result|{'predictions':'saved'},indent=2));sys.exit()
if (out/'frozen.json').exists():raise ValueError('model already frozen; no retraining')
train_info,tr=load('train');val_info,va=load('validation');vy=np.array([i['label'] for i in val_info])
candidates=[];models={}
for kind,bins in [('uniform',np.rint(np.linspace(3,480,16)).astype(int)),('log',np.rint(np.geomspace(3,480,16)).astype(int))]:
    if len(set(bins))!=16:raise ValueError('duplicate bins')
    tp=powers(tr,bins,kind+'-train');vp=powers(va,bins,kind+'-validation')
    for encoding in ['linear','log4']:
        peaks=np.percentile(tp.reshape(-1,16),99.5,axis=0);shifts=np.maximum(0,np.ceil(np.log2(np.maximum(peaks,1)/120))).astype(int)
        cfg={'n':1024,'sample_rate_hz':16000,'input_shift':0,'dft_shift':20,'bins':bins.tolist(),'dft_bins':(bins[:,None]+[-1,0,1]).reshape(-1).tolist(),
            'feature_mode':'neighbor3_energy','acoustic_encoding':encoding,'feature_shifts':shifts.tolist(),'profile':'mimii_fan_autoencoder','training_status':'normal_only_mimii_feasibility','plan_sha256':sha((d/'plan.json').read_bytes())}
        tx=features_from_powers(tp,cfg);vx=features_from_powers(vp,cfg);tf=tx.reshape(-1,16).astype('float32')/128;vf=vx.reshape(-1,16).astype('float32')/128
        mu=tf.mean(0);var=np.maximum(tf.var(0),1/128**2)
        for metric in ['centroid','diagonal_mahalanobis']:
            s=((vf-mu)**2/(var if metric!='centroid' else 1)).sum(1).reshape(len(va),-1).mean(1)
            threshold=np.quantile(s[vy==0],.95);candidates.append({'name':kind+'-'+encoding+'-'+metric,'kind':metric,**metrics(vy,s,threshold)})
        torch.manual_seed(7);net=nn.Sequential(nn.Linear(16,8),nn.ReLU(),nn.Linear(8,16));opt=torch.optim.Adam(net.parameters(),lr=.01)
        t=torch.from_numpy(tf);vnormal=torch.from_numpy(vf.reshape(len(va),-1,16)[vy==0].reshape(-1,16));bestloss=float('inf');best=None;bestepoch=0
        for epoch in range(300):
            opt.zero_grad();loss=((net(t)-t)**2).mean();loss.backward();opt.step()
            if epoch%5==0:
                with torch.no_grad():vl=float(((net(vnormal)-vnormal)**2).mean())
                if vl<bestloss:bestloss=vl;best=copy.deepcopy(net.state_dict());bestepoch=epoch+1
        net.load_state_dict(best)
        with torch.no_grad():reconstruction=np.clip(net(torch.from_numpy(vf)).numpy(),0,127/128)
        sf=((reconstruction-vf)**2).sum(1).reshape(len(va),-1).mean(1)
        m=quant(net,tf,cfg);si=scores(vx,m);ct=float(np.quantile(si[vy==0].mean(1),.95));wt=int(np.ceil(np.quantile(si[vy==0],.99)))
        m.update(clip_threshold=ct,threshold=wt,selected_epoch=bestepoch)
        name=kind+'-'+encoding+'-ae';row={'name':name,'kind':'autoencoder',**metrics(vy,si.mean(1),ct),'float_auc':float(roc_auc_score(vy,sf)),
            'float_to_int_auc_change':float(roc_auc_score(vy,si.mean(1))-roc_auc_score(vy,sf)),'window_threshold':wt}
        candidates.append(row);models[name]=m;print(json.dumps(row),flush=True)
        export_model(m,out/name)
best=max((c for c in candidates if c['kind']=='autoencoder'),key=lambda c:(c['auc'],c['recall'],-c['fpr'],c['name']))
m=models[best['name']];export_model(m,out/'model')
# Validation-only vectors; no test waveform is opened here.
vec=out/'vectors';vec.mkdir(exist_ok=True)
for j,record in enumerate([0,1,2,40,41,42]):
    x=va[record,0];write_hex(vec/f'replay_{j:03}.hex',x,16)
    result=classify(x,m);dump(vec/f'replay_{j:03}.json',{k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in result.items()})
    dump(vec/f'replay_{j:03}.source.json',{'record':val_info[record]['name'],'split':'validation','window':0})
report={'selected':best,'candidates':candidates,'selection':'fixed candidates, normal-only training; labeled validation selects AE by AUC; test never used',
        'scope':plan['scope'],'train_records':len(tr),'validation_records':len(va),'feasibility_passed':best['auc']>=.8 and best['recall']>=.5,
        'baseline_comparison':'All distance baselines retained; AE selection does not claim superiority over a better baseline.'}
dump(out/'validation.json',report)
files=[d/'plan.json',out/'validation.json',*sorted((out/'model').glob('*')),*sorted(vec.glob('*')),ROOT/'src/vibfpga/acoustic.py',ROOT/'src/vibfpga/fixed.py',Path(__file__).resolve()]
dump(out/'frozen.json',{'sha256':{str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in files},'test_evaluated':False,'scope':plan['scope']})
print('FROZEN',best['name'],'feasibility:',report['feasibility_passed'])
