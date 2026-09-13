#!/usr/bin/env python3
"""Six fixed higher-resolution candidates, same normal training and validation."""
import json
from pathlib import Path
import numpy as np
from sklearn.covariance import LedoitWolf
from experiment_acoustic_v2 import load,sha,dump
from diagnose_acoustic_v3 import metrics
from vibfpga.acoustic_experiment import normal_threshold
from vibfpga.fixed import round_shift_even
ROOT=Path(__file__).resolve().parents[1]
def main():
    out=ROOT/'artifacts/acoustic-v3-resolution';out.mkdir(exist_ok=False)
    pp=ROOT/'data/mimii/plan.json';plan=json.loads(pp.read_text())
    sources=[Path(__file__).resolve(),ROOT/'scripts/experiment_acoustic_v2.py',ROOT/'scripts/diagnose_acoustic_v3.py',ROOT/'src/vibfpga/fixed.py',ROOT/'src/vibfpga/acoustic_experiment.py']
    dump(out/'protocol.json',{'bands':[32,64,128],'models':['centroid','covariance'],'pooling':'mean','compression':'log1p','test_opened':False,
      'selection':'empirical validation normal FPR 5%, then recall, AUC','plan_sha256':sha(pp),'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sources}})
    ti,tr,th=load('train',plan,sha(pp));vi,va,vh=load('validation',plan,sha(pp));y=np.array([r['label'] for r in vi]);normal=y==0
    hann=.5-.5*np.cos(2*np.pi*np.arange(1024)/1024);power=[]
    for x in [tr,va]:
        x=x-round_shift_even(x.sum(-1),10)[...,None];z=np.fft.rfft(x/32768*hann,axis=-1)
        power.append(z.real*z.real+z.imag*z.imag)
    rows=[]
    for bands in [32,64,128]:
        features=[np.log1p(p[...,1:].reshape(*p.shape[:2],bands,512//bands).sum(-1)) for p in power]
        train=features[0].reshape(-1,bands);valid=features[1];mu=train.mean(0);std=np.maximum(train.std(0),1e-4)
        for kind in ['centroid','covariance']:
            params={'bands':bands,'kind':kind,'mean':mu.tolist(),'std':std.tolist()}
            if kind=='centroid':ss=((valid-mu)**2).mean(2)
            else:
                m=LedoitWolf().fit((train-mu)/std);v=(valid-mu)/std-m.location_
                ss=np.einsum('rti,ij,rtj->rt',v,m.precision_,v)/bands
                params.update(precision=m.precision_.tolist(),location=m.location_.tolist(),shrinkage=float(m.shrinkage_))
            scores=ss.mean(1);threshold=normal_threshold(scores[normal]);row=metrics(y,scores,threshold);row.update(name=f'bands{bands}-{kind}',scores=scores.tolist())
            rows.append(row);dump(out/(row['name']+'-parameters.json'),params);np.save(out/(row['name']+'-scores.npy'),ss)
            print(row['name'],row['auc'],row['recall'],flush=True)
    best=max(rows,key=lambda r:(round(r['recall'],12),round(r['auc'],12)))
    dump(out/'validation.json',{'candidates':rows,'selected':best,'test_opened':False,'quality_gate_passed':best['auc']>=.8 and best['recall']>=.5,
      'records':[{'name':i['name'],'label':i['label']} for i in vi]})
    dump(out/'receipt.json',{'sha256':{str(p.relative_to(ROOT)):sha(p) for p in out.iterdir() if p.is_file()},'pcm_sha256':th|vh,'test_opened':False})
if __name__=='__main__':main()
