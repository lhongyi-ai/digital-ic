#!/usr/bin/env python3
"""Independent sklearn metric and saved-model reconstruction audit; no training/audio."""
import json
from pathlib import Path
import numpy as np
import torch
from torch import nn
from sklearn.metrics import roc_auc_score, confusion_matrix
from experiment_acoustic_v2 import sha, dump

ROOT=Path(__file__).resolve().parents[1]

def main():
    out=ROOT/'artifacts/acoustic-known-balanced-v1'; old=ROOT/'artifacts/acoustic-known-machines-v1'
    r=json.loads((out/'results.json').read_text()); p=json.loads((out/'protocol.json').read_text())
    baseline=json.loads((old/'results.json').read_text())
    assert p['source_sha256']==sha(ROOT/'scripts/experiment_known_machine_balanced.py')
    assert p['cached_power_sha256']==sha(old/'development-power.npy')
    assert p['baseline_results_sha256']==sha(old/'results.json')
    assert p['baseline_protocol_sha256']==sha(old/'protocol.json')
    assert p['plan_sha256']==sha(ROOT/'data/mimii-known-machines-v1/plan.json')
    assert r['records']==baseline['records'] and not r['final_test_opened']
    rows=r['records']; y=np.array([v['label'] for v in rows]); ms=np.array([v['machine'] for v in rows]); ids=('00','02','04','06')
    power=np.load(old/'development-power.npy'); checks=0; hashes={}
    for f in r['folds']:
        original=next(v for v in baseline['folds'] if v['model']=='mlp' and v['fold']==f['fold'])
        for key in ('fit_indices','validation_indices','calibration_indices'): assert f[key]==original[key]
        fit=np.array(f['fit_indices']); val=np.array(f['validation_indices']); cal=np.array(f['calibration_indices'])
        log=np.log2(np.maximum(np.stack([power[:,k-2:k+1].sum(1) for k in range(2,512)],1),1e-12))
        scores=[]
        for m in ids:
            a=log[fit][(ms[fit]==m)&(y[fit]==0)]; b=log[fit][(ms[fit]==m)&(y[fit]==1)]
            score=(a.mean(0)-b.mean(0))**2/(a.var(0)+b.var(0)+1e-6)
            scores.append(score/max(score.sum(),1e-12))
        total=np.sum(scores,0); bins=[]
        for k in sorted(range(2,512),key=lambda k:(-total[k-2],k)):
            if all(abs(k-v)>=3 for v in bins): bins.append(k)
            if len(bins)==32: break
        assert sorted(bins)==f['bins']
        raw=log[:,np.array(f['bins'])-2]
        np.testing.assert_array_equal(raw[fit].mean(0),f['mean'])
        np.testing.assert_array_equal(np.maximum(raw[fit].std(0),1e-6),f['std'])
        z=((raw-np.array(f['mean']))/np.array(f['std'])).astype(np.float32)
        path=out/f"mlp-fold{f['fold']}.pt"; hashes[path.name]=sha(path)
        model=nn.Sequential(nn.Linear(32,16),nn.ReLU(),nn.Linear(16,1))
        model.load_state_dict(torch.load(path,weights_only=True));model.eval()
        with torch.no_grad(): s=model(torch.from_numpy(z)).flatten().numpy()
        np.testing.assert_array_equal(s[val],f['validation_scores']);np.testing.assert_array_equal(s[cal],f['calibration_scores'])
        assert len(f['training_loss'])==100;checks+=1
    for name,folds in [('baseline',[f for f in baseline['folds'] if f['model']=='mlp']),('balanced',r['folds'])]:
        for policy in ('common','per_machine'):
            votes=np.zeros(len(rows),int); pred=np.zeros(len(rows),bool); areas={m:[] for m in (*ids,'pooled')}
            for f in folds:
                val=np.array(f['validation_indices']);cal=np.array(f['calibration_indices']); s=np.array(f['validation_scores']);cs=np.array(f['calibration_scores'])
                thresholds={m:sorted(cs[(ms[cal]==m)&(y[cal]==0)])[-2] for m in ids}
                pred[val]=s>np.array([max(thresholds.values()) if policy=='common' else thresholds[m] for m in ms[val]])
                votes[val]+=1
                for m in areas:
                    mask=np.ones(len(val),bool) if m=='pooled' else ms[val]==m
                    areas[m].append(roc_auc_score(y[val][mask],s[mask]))
            assert all(votes[i]==int(row['role']=='cv') for i,row in enumerate(rows))
            for m in areas:
                mask=(votes==1)&(True if m=='pooled' else ms==m)
                tn,fp,fn,tp=confusion_matrix(y[mask],pred[mask],labels=[0,1]).ravel()
                g=r['comparison'][name][policy]['groups'][m]
                assert (g['tp'],g['fp'],g['normal'],g['abnormal'])==(tp,fp,tn+fp,tp+fn)
                assert g['recall']==tp/(tp+fn) and g['fpr']==fp/(tn+fp)
                assert abs(g['auc']-np.mean(areas[m]))<1e-12
                assert g['passed']==bool(g['recall']>.9 and g['fpr']<.05 and g['auc']>=.9); checks+=1
            assert r['comparison'][name][policy]['passed']==all(g['passed'] for g in r['comparison'][name][policy]['groups'].values())
    dump(out/'audit.json',dict(passed=True,checks=checks,results_sha256=sha(out/'results.json'),protocol_sha256=sha(out/'protocol.json'),
         source_sha256=sha(Path(__file__)),model_sha256=hashes,final_test_audio_read=False))
    print('PASS',checks,'model/frequency/metric group checks; no final audio read')

if __name__=='__main__':
    torch.set_num_threads(2)
    main()
