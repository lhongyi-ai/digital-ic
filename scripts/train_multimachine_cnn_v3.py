#!/usr/bin/env python3
"""Small spectrotemporal CNN, source-only training and calibration."""
from pathlib import Path
import json
import numpy as np
import torch
from torch import nn
from vibfpga.cnn_normalization import normalize
from vibfpga.multimachine import folds,source_threshold,violation
from experiment_acoustic_v2 import sha,dump
from diagnose_acoustic_v3 import metrics
from audit_multimachine import manual_metrics
ROOT=Path(__file__).resolve().parents[1]
class Net(nn.Module):
    def __init__(self):
        super().__init__();self.net=nn.Sequential(nn.Conv2d(1,8,3,padding=1),nn.ReLU(),nn.AvgPool2d(2),nn.Conv2d(8,16,3,padding=1),nn.ReLU(),nn.AvgPool2d(2),nn.Conv2d(16,16,3,padding=1),nn.ReLU(),nn.AdaptiveAvgPool2d((16,1)),nn.Flatten(),nn.Linear(256,32),nn.ReLU(),nn.Linear(32,1))
    def forward(self,x):return self.net(x).squeeze(1)

def patches(pcm):
    x=pcm.astype(np.float64);x-=x.mean();frames=np.lib.stride_tricks.sliding_window_view(x,1024)[::256]
    power=np.abs(np.fft.rfft(frames*np.hanning(1024),axis=1))[:,1:]**2
    energy=power.reshape(len(power),128,4).sum(2)
    # Four hops per column: 64 ms. Feature patches separate; raw support overlaps 48 ms.
    energy=energy[:512].reshape(128,4,128).mean(1)
    log=np.log(np.maximum(energy,1e-20)).astype(np.float32).T
    return np.stack([log[:,i:i+32] for i in range(0,128,32)])

def predict(model,x):
    model.eval();values=[]
    with torch.no_grad():
        for start in range(0,len(x),32):
            a=x[start:start+32];v=model(torch.from_numpy(a.reshape(-1,1,128,32))).reshape(-1,4).mean(1);values.extend(v.numpy().tolist())
    return np.array(values)

def main():
    torch.set_num_threads(2);torch.use_deterministic_algorithms(True)
    out=ROOT/'artifacts/acoustic-cnn-v3';out.mkdir(exist_ok=False)
    folder=ROOT/'artifacts/acoustic-multimachine-v1';f=json.loads((folder/'frozen.json').read_text());assert all(sha(ROOT/p)==h for p,h in f['sha256'].items())
    pp=ROOT/'data/mimii-multimachine/plan.json';assert sha(pp)==f['plan_sha256'];plan=json.loads(pp.read_text());rows=[r for r in plan['records'] if r['machine'] in ('00','02','04')];y=np.array([r['label'] for r in rows]);machines=np.array([r['machine'] for r in rows])
    protocol={'source_sha256':sha(Path(__file__)),'plan_sha256':sha(pp),'torch':torch.__version__,'seed':43,'epochs':60,'batch':64,'learning_rate':.002,
      'representations':['source_augmented'],'selection':'last epoch fixed; held machine never used for stopping','score':'mean four patch logits per recording','input':'four separate 32-column patches at 64 ms stride; each spans 2.096 s of raw waveform, adjacent supports overlap 48 ms; total support 8.24 s; 128 uniform bands; frequency position retained','threshold':'max source-machine normal calibration threshold','test_opened':False}
    protocol['augmentation']='uniform [-1,1] times difference of source fit-normal mean frequency profiles; independent of class';protocol['normalizer_sha256']=sha(ROOT/'src/vibfpga/cnn_normalization.py')
    dump(out/'protocol.json',protocol);xx=[]
    cache=ROOT/'artifacts/acoustic-cnn-v2';cb=json.loads((cache/'bindings.json').read_text());assert all(sha(ROOT/p)==h for p,h in cb['sha256'].items())
    raw=np.load(cache/'patches.npy');np.save(out/'patches.npy',raw);results=[]
    for representation in protocol['representations']:
        x=normalize(raw);rr=[]
        for held,fit,cal,val in folds(rows):
            source_ids=sorted(set(machines[fit]));profiles=[x[fit[(y[fit]==0)&(machines[fit]==machine)]].mean(axis=(0,1,3)) for machine in source_ids];direction=profiles[0]-profiles[1]
            torch.manual_seed(43);rng=np.random.default_rng(43);model=Net();opt=torch.optim.Adam(model.parameters(),lr=.002,weight_decay=1e-4);lossfn=nn.BCEWithLogitsLoss();history=[]
            for epoch in range(60):
                model.train();order=rng.permutation(fit);losses=[]
                for start in range(0,len(order),64):
                    idx=order[start:start+64];patch=rng.integers(0,4,len(idx));a=x[idx,patch,None,:,:].copy();a+=rng.uniform(-1,1,(len(idx),1,1,1)).astype(np.float32)*direction[None,None,:,None];target=torch.from_numpy(y[idx].astype(np.float32));opt.zero_grad();loss=lossfn(model(torch.from_numpy(a)),target);loss.backward();opt.step();losses.append(float(loss.detach()))
                history.append(float(np.mean(losses)))
            cs=predict(model,x[cal]);threshold=source_threshold(cs,y[cal],machines[cal]);vs=predict(model,x[val]);r=metrics(y[val],vs,threshold);check=manual_metrics(y[val],vs,threshold)
            assert abs(check['auc']-r['auc'])<1e-12 and check['tp']==r['confusion_matrix'][1][1] and check['fp']==r['confusion_matrix'][0][1]
            path=out/(representation+'-'+held+'.pt');torch.save(model.state_dict(),path);reload=Net();reload.load_state_dict(torch.load(path,weights_only=True));np.testing.assert_array_equal(vs,predict(reload,x[val]))
            r.update(machine=held,fit_indices=fit.tolist(),calibration_indices=cal.tolist(),validation_indices=val.tolist(),validation_scores=vs.tolist(),calibration_scores=cs.tolist(),training_loss=history,source_augmentation_direction=direction.tolist(),gate_passed=r['recall']>.9 and r['fpr']<.05 and r['auc']>=.9);rr.append(r)
            print(representation,held,'AUC',round(r['auc'],4),'TP/FP',check['tp'],check['fp'],flush=True)
        result={'name':representation,'folds':rr,'all_passed':all(r['gate_passed'] for r in rr),'max_violation':max(violation(r) for r in rr)};results.append(result);dump(out/(representation+'.json'),result)
    dump(out/'results.json',{'candidates':results,'all_passed':any(r['all_passed'] for r in results),'test_opened':False})
    dump(out/'bindings.json',{'source_sha256':sha(Path(__file__)),'sha256':{str(p.relative_to(ROOT)):sha(p) for p in out.iterdir() if p.is_file()}})
if __name__=='__main__':main()
