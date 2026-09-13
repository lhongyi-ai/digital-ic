#!/usr/bin/env python3
"""Standard log-power follow-up to the preserved log1p study. No test evaluation entry point."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import numpy as np
import torch
from torch import nn
from sklearn.metrics import roc_auc_score, confusion_matrix
from vibfpga.acoustic_experiment import filterbank, context, consecutive_alarm, normal_threshold
from vibfpga.fixed import round_shift_even
from vibfpga.mimii import validate_plan

ROOT = Path(__file__).resolve().parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p, x): p.write_text(json.dumps(x, indent=2)+'\n')

def load(split, plan, plan_hash):
    if split not in ('train', 'validation'):
        raise ValueError('test access prohibited in feasibility experiment')
    items = [r for r in plan['records'] if r['split'] == split]
    frames, receipts = [], {}
    for r in items:
        p = ROOT/'data/mimii'/r['local']
        meta = json.loads(p.with_suffix('.json').read_text())
        h = sha(p)
        if h != meta['npy_sha256'] or meta['plan_sha256'] != plan_hash:
            raise ValueError('PCM provenance mismatch')
        x = np.load(p, allow_pickle=False)
        frames.append(x[:len(x)//1024*1024].reshape(-1,1024))
        receipts[str(p.relative_to(ROOT))] = h
    return items, np.stack(frames).astype(np.int64), receipts

def metrics(labels, scores, threshold):
    tn, fp, fn, tp = confusion_matrix(labels, scores > threshold, labels=[0,1]).ravel()
    return dict(auc=float(roc_auc_score(labels,scores)), fpr=float(fp/(tn+fp)), recall=float(tp/(tp+fn)),
                confusion_matrix=[[int(tn),int(fp)],[int(fn),int(tp)]],threshold=float(threshold))

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default='artifacts/acoustic-v2-logpower');a=p.parse_args()
    out=ROOT/a.output;out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(2)
    plan_path=ROOT/'data/mimii/plan.json';plan=json.loads(plan_path.read_text());validate_plan(plan);ph=sha(plan_path)
    protocol={'plan_sha256':ph,'splits':['train','validation'],'test_opened':False,'seed':7,
      'features':['sparse16-log','uniform16-log','uniform32-log','mel16-log','mel32-log'],
      'context':[1,4,8],'models':['centroid','diagonal_mahalanobis','ae'],
      'ae_epochs':150,'ae_hidden':'min(16, max(8, dimension//4))','selection':'recall at empirical validation normal clip FPR <= 5%, then AUC, then smaller dimension',
      'gate':'validation recall >= 0.5 and AUC >= 0.8; no deployment/test on failure',
      'pooling':'mean context score per recording','alarm':'3 consecutive scores above normal validation 99th percentile; separately evaluated, not tuned',
      'normalization':'natural log(max(band energy, 1e-12)); means/std train normal only; centroid unstandardized, diagonal standardized, AE standardized',
      'context_stride_windows':1,'window':1024,'hop':1024,'rate':16000,
      'source_sha256':{str(q.relative_to(ROOT)):sha(q) for q in [Path(__file__).resolve(),ROOT/'src/vibfpga/acoustic_experiment.py',ROOT/'src/vibfpga/fixed.py']}}
    dump(out/'protocol.json',protocol)
    ti,tr,th=load('train',plan,ph);vi,va,vh=load('validation',plan,ph);y=np.array([r['label'] for r in vi]);normal=y==0
    # Audit at precisely v1's DC subtraction and 12-bit input limit.
    centered=[];audit=[]
    for label,raw in [('train-normal',tr),('validation-normal',va[normal]),('validation-abnormal',va[~normal])]:
        c=raw-round_shift_even(raw.sum(-1),10)[...,None]
        clip=(c < -2048)|(c > 2047)
        audit.append(dict(group=label,records=len(raw),samples=raw.size,clipped_samples=int(clip.sum()),clipped_fraction=float(clip.mean()),
          clips_with_clipping=int(clip.any(axis=(1,2)).sum()),peak=int(np.abs(c).max()),rms_median=float(np.median(np.sqrt((c.astype(float)**2).mean((1,2))))),
          clipping_per_record=clip.mean((1,2)).tolist(),rms_per_record=np.sqrt((c.astype(float)**2).mean((1,2))).tolist()))
    # Minimal power-of-two input scaling selected ONLY from training peak; no clipping on training.
    peak=int(np.abs(tr-round_shift_even(tr.sum(-1),10)[...,None]).max());shift=max(0,int(np.ceil(np.log2(max(peak,1)/2047))))
    h=.5-.5*np.cos(2*np.pi*np.arange(1024)/1024)
    spectra=[]
    for raw in [tr,va]:
        c=raw-round_shift_even(raw.sum(-1),10)[...,None]
        # Study full-resolution normalized waveform, no 12-bit clipping; scaling audit is separate.
        z=np.fft.rfft(c/32768*h,axis=-1);spectra.append(z.real*z.real+z.imag*z.imag)
    pt,pv=spectra
    sparse=filterbank(16,'sparse').sum(0)>0
    for row,ps in zip(audit,[pt,pv[normal],pv[~normal]]):
        row['sparse_energy_fraction']=float(ps[...,sparse].sum()/ps[...,1:].sum())
        row['mean_spectrum']=ps.mean((0,1)).tolist()
    dump(out/'input-audit.json',dict(groups=audit,training_selected_input_shift=shift,
      sparse_bins=np.flatnonzero(sparse).tolist(),covered_non_dc_bins=int(sparse.sum()),available_non_dc_bins=512,
      frequency_resolution_hz=15.625,study_frontend='float64, full-resolution PCM DC removal and periodic Hann; NOT current integer RTL'))
    results=[];models={};feature_data={}
    for kind,b in [('sparse',16),('uniform',16),('uniform',32),('mel',16),('mel',32)]:
        bank=filterbank(b,kind);tf=np.log(np.maximum(pt@bank.T,1e-12)).astype(np.float32);vf=np.log(np.maximum(pv@bank.T,1e-12)).astype(np.float32)
        for k in [1,4,8]:
            tx=context(tf,k);vx=context(vf,k);d=tx.shape[-1];flat=tx.reshape(-1,d);vflat=vx.reshape(-1,d)
            mu=flat.mean(0);std=np.maximum(flat.std(0),1e-4);tz=(flat-mu)/std;vz=(vflat-mu)/std
            for model in ['centroid','diagonal_mahalanobis','ae']:
                name=f'{kind}{b}-log-c{k}-{model}';params={'mean':mu.tolist(),'std':std.tolist(),'filterbank':bank.tolist(),'context':k,'model':model}
                if model=='centroid':ss=((vflat-mu)**2).mean(1)
                elif model=='diagonal_mahalanobis':ss=(vz**2).mean(1)
                else:
                    torch.manual_seed(7);hidden=min(16,max(8,d//4));net=nn.Sequential(nn.Linear(d,hidden),nn.ReLU(),nn.Linear(hidden,d))
                    t=torch.from_numpy(tz);v=torch.from_numpy(vz);nv=torch.from_numpy(vz.reshape(len(va),-1,d)[normal].reshape(-1,d))
                    opt=torch.optim.Adam(net.parameters(),lr=.005);best_loss=float('inf');best=None
                    for epoch in range(150):
                        opt.zero_grad();loss=((net(t)-t)**2).mean();loss.backward();opt.step()
                        if epoch%5==0:
                            with torch.no_grad():vl=float(((net(nv)-nv)**2).mean())
                            if vl<best_loss:best_loss=vl;best=copy.deepcopy(net.state_dict());best_epoch=epoch+1
                    net.load_state_dict(best)
                    with torch.no_grad():ss=((net(v)-v)**2).mean(1).numpy()
                    params.update(hidden=hidden,epoch=best_epoch,state={n:x.tolist() for n,x in best.items()})
                ss=ss.reshape(len(va),-1);clip=ss.mean(1);threshold=normal_threshold(clip[normal]);row=metrics(y,clip,threshold)
                wt=float(np.quantile(ss[normal],.99));alarms=consecutive_alarm(ss,wt);alarm=alarms.any(1)
                row.update(name=name,features=b,context=k,dimension=d,model=model,context_ms=64*k,
                  earliest_3window_alarm_ms=64*(k+2),score_steps_per_record=ss.shape[1],
                  alarm_threshold=wt,alarm_fpr=float(alarm[normal].mean()),alarm_recall=float(alarm[~normal].mean()),
                  alarm_confusion_matrix=confusion_matrix(y,alarm,labels=[0,1]).tolist(),
                  weights_or_parameters=(2*d*params['hidden']+params['hidden']+d if model=='ae' else d*(2 if model=='diagonal_mahalanobis' else 1)),
                  validation_scores=clip.tolist())
                results.append(row);models[name]=params;feature_data[name]=(tx,vx,ss)
                dump(out/(name+'.json'),{'metrics':row,'parameters':params})
                print(json.dumps({q:row[q] for q in ['name','auc','fpr','recall','alarm_fpr','alarm_recall']}),flush=True)
    best=max(results,key=lambda r:(r['recall'] if r['fpr']<=.05 else -1,r['auc'],-r['dimension'],r['name']))
    passed=best['recall']>=.5 and best['auc']>=.8 and best['fpr']<=.05
    report=dict(selected=best,candidates=results,feasibility_passed=passed,test_opened=False,
      validation_records=[{'name':r['name'],'label':r['label']} for r in vi],
      scope=plan['scope'],selection_optimism='45 candidates on the same small validation set; selection results are not unbiased test performance',
      next_stage='quantization and hardware cost study' if passed else 'no RTL change justified; quality gate failed')
    dump(out/'validation.json',report)
    tx,vx,ss=feature_data[best['name']];np.savez_compressed(out/'selected-features.npz',train=tx,validation=vx,validation_scores=ss)
    dump(out/'selected-model.json',models[best['name']])
    dump(out/'receipt.json',{'sha256':{str(q.relative_to(ROOT)):sha(q) for q in out.iterdir() if q.is_file()},'pcm_sha256':th|vh,'test_opened':False})
    print('SELECTED',best['name'],'GATE',passed,flush=True)

if __name__=='__main__':main()
