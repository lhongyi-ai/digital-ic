#!/usr/bin/env python3
"""Normal recording distribution at full spectral resolution; no test access."""
from pathlib import Path
import json
import numpy as np
from experiment_acoustic_v2 import load,sha,dump
from diagnose_acoustic_v3 import metrics
from vibfpga.acoustic_experiment import normal_threshold
ROOT=Path(__file__).resolve().parents[1]
def spectrum(x,n):
    chunks=x[:,:x.shape[1]//n*n].reshape(len(x),-1,n).astype(float)
    chunks-=chunks.mean(2,keepdims=True)
    h=.5-.5*np.cos(2*np.pi*np.arange(n)/n)
    return (np.abs(np.fft.rfft(chunks*h,axis=2))**2).mean(1)[:,1:]/(n*n)
def main():
    out=ROOT/'artifacts/acoustic-v5-finespectrum';out.mkdir(exist_ok=False)
    pp=ROOT/'data/mimii/plan.json';plan=json.loads(pp.read_text())
    sources=[Path(__file__).resolve(),ROOT/'scripts/experiment_acoustic_v2.py',ROOT/'scripts/diagnose_acoustic_v3.py',ROOT/'src/vibfpga/acoustic_experiment.py']
    dump(out/'protocol.json',{'n':[1024,4096,16384],'representation':['logpower','logshape'],'models':['diagonal','nearest5','pca_residual16','ridge_covariance'],
      'candidate_count':24,'training':'normal records only, statistics on recording-average full spectra','threshold':'normal validation empirical 5%',
      'gate':{'tp':27,'max_fp':2,'auc':.9},'test_opened':False,'plan_sha256':sha(pp),
      'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sources}})
    ti,tr,th=load('train',plan,sha(pp));vi,va,vh=load('validation',plan,sha(pp));tr=tr.reshape(len(tr),-1);va=va.reshape(len(va),-1)
    y=np.array([r['label'] for r in vi]);normal=y==0;rows=[]
    for n in [1024,4096,16384]:
        train=spectrum(tr,n);valid=spectrum(va,n)
        floor=np.maximum(np.median(train,axis=0)*1e-3,1e-12)
        lt=np.log(train+floor);lv=np.log(valid+floor)
        for rep in ['logpower','logshape']:
            t=lt if rep=='logpower' else lt-lt.mean(1,keepdims=True)
            v=lv if rep=='logpower' else lv-lv.mean(1,keepdims=True)
            mean=t.mean(0);std=np.maximum(t.std(0),1e-3);t=(t-mean)/std;v=(v-mean)/std;d=t.shape[1]
            _,sing,vt=np.linalg.svd(t,full_matrices=False);proj=v@vt.T
            residual=np.maximum((v*v).sum(1)-(proj*proj).sum(1),0)
            eigen=sing*sing/(len(t)-1);ridge=.2*eigen.sum()/d
            distances=np.maximum((v*v).sum(1)[:,None]+(t*t).sum(1)[None,:]-2*v@t.T,0)
            scores={'diagonal':(v*v).mean(1),'nearest5':np.sort(distances,axis=1)[:,:5].mean(1)/d,
              'pca_residual16':np.maximum((v*v).sum(1)-(proj[:,:16]**2).sum(1),0)/d,
              'ridge_covariance':((proj*proj/(eigen+ridge)).sum(1)+residual/ridge)/d}
            np.savez_compressed(out/f'n{n}-{rep}-normal-model.npz',mean=mean,std=std,floor=floor,training=t,components=vt,eigen=eigen,ridge=ridge)
            for kind,s in scores.items():
                threshold=normal_threshold(s[normal]);r=metrics(y,s,threshold);r.update(name=f'n{n}-{rep}-{kind}',scores=s.tolist(),frequency_resolution_hz=16000/n)
                rows.append(r);print(r['name'],round(r['auc'],4),round(r['recall'],4),flush=True)
    best=max(rows,key=lambda r:(round(r['recall'],12),round(r['auc'],12)))
    dump(out/'validation.json',{'selected':best,'candidates':rows,'test_opened':False,'high_standard_passed':best['confusion_matrix'][1][1]>=27 and best['confusion_matrix'][0][1]<=2 and best['auc']>=.9,
      'records':[{'name':r['name'],'label':r['label']} for r in vi],'scope':'whole-recording statistical detector, not currently an FPGA implementation'})
    dump(out/'receipt.json',{'sha256':{str(p.relative_to(ROOT)):sha(p) for p in out.iterdir() if p.is_file()},'pcm_sha256':th|vh,'test_opened':False})
    print('BEST',best['name'],best['recall'],best['auc'])
if __name__=='__main__':main()
