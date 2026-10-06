#!/usr/bin/env python3
"""INT8 classifier feasibility on frozen floating spectral features (not DSP RTL)."""
import json,math
from pathlib import Path
import joblib
import numpy as np
from threadpoolctl import threadpool_limits
from experiment_acoustic_v2 import sha,dump
from audit_known_machine_results import auc
ROOT=Path(__file__).resolve().parents[1]

def main():
    chosen=ROOT/'artifacts/acoustic-known-calibration00-v2'
    audit=json.loads((chosen/'outcome-audit.json').read_text());assert audit['passed'] and audit['selected']=='original_fit'
    assert audit['results_sha256']==sha(chosen/'results.json')
    reference=json.loads((chosen/'results.json').read_text());detail=ROOT/'artifacts/acoustic-known-detail-v1'
    previous=json.loads((detail/'results.json').read_text());rows=previous['records']
    y=np.array([r['label'] for r in rows]);machines=np.array([r['machine'] for r in rows])
    full=np.log2(np.maximum(np.load(ROOT/'artifacts/acoustic-known-machines-v1/development-power.npy'),1e-12))
    extra=np.log2(np.maximum(np.load(chosen/'calibration-power.npy'),1e-12))
    out=ROOT/'artifacts/acoustic-known-int8-v1';out.mkdir(exist_ok=False)
    dump(out/'protocol.json',dict(source_sha256=sha(Path(__file__)),selected_audit_sha256=sha(chosen/'outcome-audit.json'),
        selected_results_sha256=sha(chosen/'results.json'),baseline_sha256=sha(detail/'results.json'),
        quantization='sx=max(abs(training standardized features))/127; sw=max(abs(weights))/127; ties-even round, clip[-127,127]; bias INT32; INT32 dot',
        threshold='alpha=.04 same calibration records; ascending ceil((n+1)*.96); integer score > integer threshold',
        scope='Classifier PTQ only, frontend log2 and standardization still floating; no RTL/FPGA equivalence claim',final_test_opened=False))
    results=[];decisions=np.zeros(len(rows),bool);margins=np.full(len(rows),np.nan);votes=np.zeros(len(rows),int)
    for f in [f for f in previous['folds'] if f['model']=='full512']:
        m,fold=f['machine'],f['fold'];fit=np.array(f['fit_indices']);val=np.array(f['validation_indices']);cal=np.array(f['calibration_indices'])
        model=joblib.load(detail/f'full512-id{m}-fold{fold}.joblib')
        z=(full-f['mean'])/f['std'];sx=max(float(np.abs(z[fit]).max())/127,1e-12)
        sw=max(float(np.abs(model.coef_[0]).max())/127,1e-12)
        qx=np.clip(np.rint(z/sx),-127,127).astype(np.int64);qw=np.clip(np.rint(model.coef_[0]/sw),-127,127).astype(np.int64)
        qb=int(np.rint(float(model.intercept_[0])/(sx*sw)));score=qx@qw+qb
        assert np.abs(score).max()<2**31 and abs(qb)<2**31
        normals=score[cal[y[cal]==0]];extra_scores=[]
        if m=='00':
            qcal=np.clip(np.rint(((extra-f['mean'])/f['std'])/sx),-127,127).astype(np.int64)
            extra_scores=(qcal@qw+qb).tolist();normals=np.r_[normals,extra_scores]
        rank=math.ceil((len(normals)+1)*.96);limit=int(np.sort(normals)[rank-1]);pred=score[val]>limit
        tp=int(pred[y[val]==1].sum());fp=int(pred[y[val]==0].sum());area=auc(y[val],score[val])
        r=dict(machine=m,fold=fold,weights=qw.tolist(),bias=qb,input_scale=sx,weight_scale=sw,mean=f['mean'],std=f['std'],
               threshold=limit,normal_calibration_scores=normals.tolist(),validation_indices=val.tolist(),validation_scores=score[val].tolist(),
               tp=tp,fp=fp,auc=area,validation_clipped_features=int((np.abs(z[val]/sx)>127).sum()))
        results.append(r);decisions[val]=pred;margins[val]=(score[val]-limit)*(sx*sw);votes[val]+=1
    assert all(votes[i]==int(row['role']=='cv') for i,row in enumerate(rows))
    groups={}
    for m in ('00','02','04','06','pooled'):
        mask=(votes==1)&(True if m=='pooled' else machines==m);tp=int(decisions[mask&(y==1)].sum());fp=int(decisions[mask&(y==0)].sum())
        normal=int((mask&(y==0)).sum());abnormal=int((mask&(y==1)).sum())
        areas=[]
        for fold in range(3):
            idx=np.array([i for i,row in enumerate(rows) if mask[i] and row['fold']==fold]);areas.append(auc(y[idx],margins[idx]))
        g=dict(tp=tp,fp=fp,normal=normal,abnormal=abnormal,recall=tp/abnormal,fpr=fp/normal,auc=float(np.mean(areas)))
        g['passed']=g['recall']>.9 and g['fpr']<.05 and g['auc']>=.9;groups[m]=g
    dump(out/'results.json',dict(folds=results,groups=groups,passed=all(g['passed'] for g in groups.values()),records=rows,final_test_opened=False))
    print('SUMMARY',json.dumps(groups),flush=True)
if __name__=='__main__':
    with threadpool_limits(limits=2):main()
