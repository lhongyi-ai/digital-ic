#!/usr/bin/env python3
"""Independently recompute threshold order statistics, votes and pairwise AUC."""
import json,math
from pathlib import Path
import numpy as np
from experiment_acoustic_v2 import sha,dump
from audit_known_machine_results import auc
ROOT=Path(__file__).resolve().parents[1]

def main():
    out=ROOT/'artifacts/acoustic-known-calibration00-v2';r=json.loads((out/'results.json').read_text());p=json.loads((out/'protocol.json').read_text())
    assert p['source_sha256']==sha(ROOT/'scripts/calibrate_known_extra00.py')
    assert p['baseline_sha256']==sha(ROOT/'artifacts/acoustic-known-detail-v1/results.json')
    assert p['expanded_sha256']==sha(ROOT/'artifacts/acoustic-known-extra00-v1/results.json')
    assert p['calibration_manifest_sha256']==sha(ROOT/'data/mimii-known-calibration00-v1/development.json')
    assert p['calibration_audit_sha256']==sha(ROOT/'data/mimii-known-calibration00-v1/audit.json')
    assert r['calibration_power_sha256']==sha(out/'calibration-power.npy') and not r['final_test_opened']
    rows=r['records'];y=np.array([v['label'] for v in rows]);ms=np.array([v['machine'] for v in rows]);checks=0
    for name,o in r['outcomes'].items():
        pred=np.zeros(len(rows),bool);scores=np.full(len(rows),np.nan);raw=scores.copy();votes=np.zeros(len(rows),int)
        for f in o['folds']:
            val=np.array(f['validation_indices']);normal=np.array(f['original_normal_scores']+f['extra_normal_scores'])
            expected=sorted(normal)[math.ceil((len(normal)+1)*.96)-1]
            assert expected==f['threshold'] and len(normal)==f['calibration_count']
            assert len(normal)==(160 if f['machine']=='00' else 32)
            assert sha(ROOT/f['model_path'])==f['model_sha256']
            assert all(rows[i]['role']=='cv' and rows[i]['fold']==f['fold'] and rows[i]['machine']==f['machine'] for i in val)
            s=np.array(f['validation_scores']);pred[val]=s>expected;scores[val]=s-expected;raw[val]=s;votes[val]+=1
            assert f['tp']==int(pred[val][y[val]==1].sum()) and f['fp']==int(pred[val][y[val]==0].sum())
            assert abs(auc(y[val],s)-f['auc'])<1e-12;checks+=1
        assert all(votes[i]==int(row['role']=='cv') for i,row in enumerate(rows))
        for m,g in o['groups'].items():
            mask=(votes==1)&(True if m=='pooled' else ms==m)
            tp=int(pred[mask&(y==1)].sum());fp=int(pred[mask&(y==0)].sum())
            assert g['tp']==tp and g['fp']==fp and g['recall']==tp/g['abnormal'] and g['fpr']==fp/g['normal']
            values=[];raw_values=[]
            for fold in range(3):
                v=np.array([i for i,row in enumerate(rows) if mask[i] and row['fold']==fold])
                values.append(auc(y[v],scores[v]));raw_values.append(auc(y[v],raw[v]))
            assert abs(np.mean(values)-g['auc'])<1e-12 and abs(np.mean(raw_values)-g['raw_logit_auc'])<1e-12
            assert g['passed']==(g['recall']>.9 and g['fpr']<.05 and g['auc']>=.9);checks+=1
        assert o['passed']==all(g['passed'] for g in o['groups'].values())
    assert r['outcomes']['original_fit']['passed'] and not r['outcomes']['expanded_fit']['passed']
    dump(out/'outcome-audit.json',dict(passed=True,checks=checks,selected='original_fit',results_sha256=sha(out/'results.json'),
        protocol_sha256=sha(out/'protocol.json'),script_sha256=sha(Path(__file__)),final_audio_read=False))
    print('PASS',checks,'selected original_fit; development only')
if __name__=='__main__':main()
