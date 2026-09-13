#!/usr/bin/env python3
"""Reconstruct saved follow-up models and independently count development decisions."""
import json
from pathlib import Path
import joblib
import numpy as np
import torch
from torch import nn
from experiment_acoustic_v2 import sha,dump
from audit_known_machine_results import auc

ROOT=Path(__file__).resolve().parents[1]

def main():
    baseline=ROOT/'artifacts/acoustic-known-machines-v1'
    power=np.load(baseline/'development-power.npy',allow_pickle=False)
    for tag,script in [('local','experiment_known_machine_local.py'),('detail','experiment_known_spectral_detail.py'),('capacity','experiment_known_spectral_capacity.py')]:
        out=ROOT/f'artifacts/acoustic-known-{tag}-v1';r=json.loads((out/'results.json').read_text());protocol=json.loads((out/'protocol.json').read_text())
        assert protocol['source_sha256']==sha(ROOT/'scripts'/script)
        assert protocol['power_sha256']==sha(baseline/'development-power.npy')
        assert protocol['baseline_sha256']==sha(baseline/'results.json')
        assert protocol['plan_sha256']==sha(ROOT/'data/mimii-known-machines-v1/plan.json')
        assert not r['final_test_opened']
        rows=r['records'];y=np.array([v['label'] for v in rows]);checks=0;models={};scores={}
        for f in r['folds']:
            name=f.get('model','mlp');ids=np.array(f['validation_indices']);cal=np.array(f['calibration_indices']);fit=np.array(f['fit_indices'])
            assert not set(fit)&set(ids) and not set(fit)&set(cal) and not set(ids)&set(cal)
            assert all(rows[i]['role']=='cv' and rows[i]['machine']==f['machine'] and rows[i]['fold']==f['fold'] for i in ids)
            assert all(rows[i]['role']=='calibration' and rows[i]['machine']==f['machine'] for i in cal)
            assert all(rows[i]['role']=='cv' and rows[i]['machine']==f['machine'] and rows[i]['fold']!=f['fold'] for i in fit)
            bins=np.array(f['bins'])
            raw=np.log2(np.maximum(np.stack([power[:,k-2:k+1].sum(1) for k in bins],1),1e-12)) if tag=='local' else np.log2(np.maximum(power[:,bins-1],1e-12))
            np.testing.assert_allclose(raw[fit].mean(0),f['mean'],rtol=0,atol=1e-12)
            np.testing.assert_allclose(np.maximum(raw[fit].std(0),1e-6),f['std'],rtol=0,atol=1e-12)
            z=((raw-f['mean'])/f['std']).astype(np.float32)
            # Match the saved experiment's matrix layout: BLAS reduction order depends on it.
            if tag=='capacity':z=np.ascontiguousarray(z)
            suffix='.joblib' if name in ('full512','sparse64linear') else '.pt'
            path=out/f"{name}-id{f['machine']}-fold{f['fold']}{suffix}";assert sha(path)==f['model_sha256'];models[path.name]=sha(path)
            if suffix=='.pt':
                model=nn.Sequential(nn.Linear(len(bins),16),nn.ReLU(),nn.Linear(16,1));model.load_state_dict(torch.load(path,weights_only=True));model.eval()
                with torch.no_grad():s=model(torch.from_numpy(z)).flatten().numpy().astype(float)
            else:s=joblib.load(path).decision_function(z)
            np.testing.assert_allclose(s[ids],f['validation_scores'],rtol=0,atol=1e-6)
            np.testing.assert_allclose(s[cal],f['calibration_scores'],rtol=0,atol=1e-6)
            # Use serialized scores for exact decision checks, including values equal to a threshold.
            v=np.array(f['validation_scores']);c=np.array(f['calibration_scores'])
            threshold=sorted(c[y[cal]==0])[-1 if tag=='capacity' else -2]
            assert threshold==f['threshold'];p=v>threshold
            assert int(p[y[ids]==1].sum())==f['tp'] and int(p[y[ids]==0].sum())==f['fp']
            assert abs(auc(y[ids],v)-f['auc'])<1e-12
            assert f['passed']==(f['recall']>.9 and f['fpr']<.05 and f['auc']>=.9)
            scores.setdefault(name,[]).append((f,ids,p));checks+=1
        for name,fs in scores.items():
            votes=np.zeros(len(rows),int)
            for f,ids,p in fs:votes[ids]+=1
            assert all(votes[i]==int(row['role']=='cv') for i,row in enumerate(rows))
            for m in ('00','02','04','06'):
                group=[f for f,_,_ in fs if f['machine']==m]
                g=r['summary'][m] if tag=='local' else r['summary'][name]['groups'][m]
                assert sum(f['tp'] for f in group)==g['tp'] and sum(f['fp'] for f in group)==g['fp']
                assert abs(np.mean([f['auc'] for f in group])-g['auc'])<1e-12
                assert g['recall']==g['tp']/96 and g['fpr']==g['fp']/96
                assert g['passed']==(g['recall']>.9 and g['fpr']<.05 and g['auc']>=.9);checks+=1
        dump(out/'audit.json',dict(passed=True,model_and_group_checks=checks,results_sha256=sha(out/'results.json'),
            protocol_sha256=sha(out/'protocol.json'),script_sha256=sha(Path(__file__)),model_sha256=models,
            reload_absolute_tolerance=1e-6,metric_tolerance=1e-12,final_audio_read=False))
        print(tag,'PASS',checks,flush=True)

if __name__=='__main__':
    torch.set_num_threads(2);main()
