#!/usr/bin/env python3
"""Recalculate saved fold metrics by explicit positive/negative score comparisons."""
import json
from pathlib import Path
import numpy as np
from experiment_acoustic_v2 import sha,dump
ROOT=Path(__file__).resolve().parents[1]

def auc(y,s):
    diff=s[y==1][:,None]-s[y==0][None,:]
    return float((np.sum(diff>0)+.5*np.sum(diff==0))/diff.size)

def main():
    base=ROOT/'artifacts/acoustic-known-machines-v1'; p=base/'results.json';r=json.loads(p.read_text())
    plan=ROOT/'data/mimii-known-machines-v1/plan.json'
    protocol=json.loads((base/'protocol.json').read_text())
    assert protocol['plan_sha256']==sha(plan)
    assert protocol['source_sha256']==sha(ROOT/'scripts/train_known_machine_models.py')
    rows=r['records']; y=np.array([v['label'] for v in rows]);machines=np.array([v['machine'] for v in rows]);checks=0
    for name in ('logistic','mlp'):
        votes=np.zeros(len(rows),dtype=int); decisions=np.zeros(len(rows),dtype=bool); fold_auc={m:[] for m in ('00','02','04','06','pooled')}
        for f in [f for f in r['folds'] if f['model']==name]:
            fit=set(f['fit_indices']);cal=np.array(f['calibration_indices']);val=np.array(f['validation_indices'])
            assert not fit&set(cal) and not fit&set(val) and not set(cal)&set(val)
            assert all(rows[i]['role']=='calibration' for i in cal)
            assert all(rows[i]['role']=='cv' and rows[i]['fold']==f['fold'] for i in val)
            cs=np.array(f['calibration_scores']);s=np.array(f['validation_scores']);limit=max(np.sort(cs[(machines[cal]==m)&(y[cal]==0)])[-2] for m in ('00','02','04','06'))
            assert limit==f['threshold'];votes[val]+=1;decisions[val]=s>limit
            for m in fold_auc:
                mask=np.ones(len(val),dtype=bool) if m=='pooled' else machines[val]==m
                value=auc(y[val][mask],s[mask]);fold_auc[m].append(value)
                expected=f['auc'] if m=='pooled' else f['per_machine'][m]['auc']
                assert abs(value-expected)<1e-12;checks+=1
        assert all(votes[i]==(1 if row['role']=='cv' else 0) for i,row in enumerate(rows))
        for m,values in fold_auc.items():
            mask=(votes==1)&(True if m=='pooled' else machines==m)
            pred=decisions[mask];truth=y[mask];tp=int(pred[truth==1].sum());fp=int(pred[truth==0].sum())
            g=r['summary'][name]['groups'][m]
            assert abs(g['auc']-np.mean(values))<1e-12
            assert g['recall']==tp/int((truth==1).sum()) and g['fpr']==fp/int((truth==0).sum())
            assert g['passed']==(g['recall']>.9 and g['fpr']<.05 and g['auc']>=.9);checks+=1
        assert r['summary'][name]['passed']==all(g['passed'] for g in r['summary'][name]['groups'].values())
    expected=next((n for n in ('logistic','mlp') if r['summary'][n]['passed']),None)
    assert r['selected']==expected
    dump(base/'audit.json',dict(passed=True,metric_checks=checks,results_sha256=sha(p),
        protocol_sha256=sha(base/'protocol.json'),script_sha256=sha(Path(__file__)),selected=expected,final_test_audio_read=False))
    print('PASS',checks,'metric checks; selected',expected)

if __name__=='__main__':main()
