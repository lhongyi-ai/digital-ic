#!/usr/bin/env python3
"""Evaluate integer DSP+normalizer+INT8 dot product against unchanged development gates."""
import json,math
from pathlib import Path
import numpy as np
from vibfpga.known_fixed import quantized_features
from experiment_acoustic_v2 import sha,dump
from audit_known_machine_results import auc
ROOT=Path(__file__).resolve().parents[1]

def main():
    dsp=ROOT/'artifacts/acoustic-known-integer-dsp-v2';reference=ROOT/'artifacts/acoustic-known-int8-v1'
    receipt=json.loads((dsp/'receipt.json').read_text());assert receipt['passed'] and receipt['log_sha256']==sha(dsp/'log-q12.npy')
    assert receipt['source_sha256']==sha(ROOT/'src/vibfpga/known_fixed.py')
    previous=json.loads((reference/'results.json').read_text());rows=previous['records'];assert receipt['rows'][:1024]==rows
    assert all(r['role']=='calibration_extra' and r['machine']=='00' for r in receipt['rows'][1024:])
    log=np.load(dsp/'log-q12.npy',allow_pickle=False);assert log.shape==(1152,512)
    y=np.array([r['label'] for r in rows]);ms=np.array([r['machine'] for r in rows])
    out=ROOT/'artifacts/acoustic-known-integer-pipeline-v2';out.mkdir(exist_ok=False)
    dump(out/'protocol.json',dict(script_sha256=sha(Path(__file__)),fixed_source_sha256=sha(ROOT/'src/vibfpga/known_fixed.py'),
        dsp_receipt_sha256=sha(dsp/'receipt.json'),int8_reference_sha256=sha(reference/'results.json'),
        model='unchanged saved PTQ weights and bias; normalizer meanQ12/gainQ24; int8 saturated features; int32 score',
        threshold='same calibrated rank alpha=.04 using integer pipeline scores; no validation threshold fitting',
        scope='complete integer software front end and classifier, not yet RTL or board',final_test_opened=False))
    details=json.loads((ROOT/'artifacts/acoustic-known-detail-v1/results.json').read_text())
    results=[];pred=np.zeros(1024,bool);score_margin=np.full(1024,np.nan);votes=np.zeros(1024,int)
    for f in previous['folds']:
        m,fold=f['machine'],f['fold'];old=next(v for v in details['folds'] if v['model']=='full512' and v['machine']==m and v['fold']==fold)
        features,mean,gain=quantized_features(log,f['mean'],f['input_scale'],f['std'])
        weights=np.array(f['weights'],dtype=np.int64);score=features.astype(np.int64)@weights+f['bias']
        assert np.abs(score).max()<2**31
        val=np.array(f['validation_indices']);cal=np.array(old['calibration_indices']);normals=score[cal[y[cal]==0]]
        if m=='00':normals=np.r_[normals,score[1024:]]
        threshold=int(np.sort(normals)[math.ceil((len(normals)+1)*.96)-1]);p=score[val]>threshold
        # Independent scalar dot checks retain the exact integer requirement.
        for i in val[:2]:assert int(score[i])==sum(int(a)*int(b) for a,b in zip(features[i],weights))+f['bias']
        r=dict(machine=m,fold=fold,mean_q12=mean.tolist(),gain_q24=gain.tolist(),weights=weights.tolist(),bias=f['bias'],
               input_scale=f['input_scale'],weight_scale=f['weight_scale'],threshold=threshold,normal_calibration_scores=normals.tolist(),
               validation_indices=val.tolist(),validation_scores=score[val].tolist(),tp=int(p[y[val]==1].sum()),fp=int(p[y[val]==0].sum()),auc=auc(y[val],score[val]))
        results.append(r);pred[val]=p;score_margin[val]=(score[val]-threshold)*(f['input_scale']*f['weight_scale']);votes[val]+=1
    assert all(votes[i]==int(r['role']=='cv') for i,r in enumerate(rows))
    groups={}
    for m in ('00','02','04','06','pooled'):
        mask=(votes==1)&(True if m=='pooled' else ms==m);tp=int(pred[mask&(y==1)].sum());fp=int(pred[mask&(y==0)].sum())
        normal=int((mask&(y==0)).sum());abnormal=int((mask&(y==1)).sum());areas=[]
        for fold in range(3):
            v=np.array([i for i,r in enumerate(rows) if mask[i] and r['fold']==fold]);areas.append(auc(y[v],score_margin[v]))
        g=dict(tp=tp,fp=fp,normal=normal,abnormal=abnormal,recall=tp/abnormal,fpr=fp/normal,auc=float(np.mean(areas)))
        g['passed']=g['recall']>.9 and g['fpr']<.05 and g['auc']>=.9;groups[m]=g
    dump(out/'results.json',dict(folds=results,groups=groups,passed=all(g['passed'] for g in groups.values()),records=rows,final_test_opened=False))
    print('SUMMARY',json.dumps(groups),flush=True)
if __name__=='__main__':main()
