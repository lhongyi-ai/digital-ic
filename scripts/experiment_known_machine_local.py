#!/usr/bin/env python3
"""Twelve fixed fits: per-installed-machine parameters on a shared MLP architecture."""
import json
from pathlib import Path
import numpy as np
import torch
from torch import nn
from threadpoolctl import threadpool_limits
from sklearn.metrics import roc_auc_score, roc_curve
from experiment_acoustic_v2 import dump, sha
from train_known_machine_models import frontend, passed

ROOT=Path(__file__).resolve().parents[1]
IDS=('00','02','04','06')

def select_local(power,y):
    features=frontend(power,np.arange(2,512))
    a,b=features[y==0],features[y==1]
    score=(a.mean(0)-b.mean(0))**2/(a.var(0)+b.var(0)+1e-6)
    chosen=[]
    for i in np.lexsort((np.arange(510),-score)):
        if all(abs(int(i)-j)>=3 for j in chosen):chosen.append(int(i))
        if len(chosen)==32:break
    return np.array(sorted(chosen))+2

def measure(y,s,limit):
    pred=s>limit;tp=int(pred[y==1].sum());fp=int(pred[y==0].sum())
    r=dict(tp=tp,fp=fp,normal=int((y==0).sum()),abnormal=int((y==1).sum()),
           recall=tp/int((y==1).sum()),fpr=fp/int((y==0).sum()),auc=float(roc_auc_score(y,s)))
    r['passed']=passed(r)
    return r

def main():
    old=ROOT/'artifacts/acoustic-known-machines-v1';base=ROOT/'data/mimii-known-machines-v1'
    previous=json.loads((old/'results.json').read_text()); audit=json.loads((old/'audit.json').read_text())
    balanced_protocol=json.loads((ROOT/'artifacts/acoustic-known-balanced-v1/protocol.json').read_text())
    assert audit['passed'] and audit['results_sha256']==sha(old/'results.json')
    assert balanced_protocol['cached_power_sha256']==sha(old/'development-power.npy')
    assert balanced_protocol['plan_sha256']==sha(base/'plan.json')==json.loads((base/'freeze.json').read_text())['plan_sha256']
    rows=previous['records'];assert rows==json.loads((base/'development.json').read_text())['records']
    assert len(rows)==1024 and all(r['role'] in ('cv','calibration') for r in rows)
    power=np.load(old/'development-power.npy',allow_pickle=False)
    y=np.array([r['label'] for r in rows]);machines=np.array([r['machine'] for r in rows])
    out=ROOT/'artifacts/acoustic-known-local-v1';out.mkdir(exist_ok=False)
    dump(out/'protocol.json',dict(source_sha256=sha(Path(__file__)),baseline_sha256=sha(old/'results.json'),
        plan_sha256=sha(base/'plan.json'),power_sha256=sha(old/'development-power.npy'),
        feature='Per-ID training Fisher selected32 spacing3 centers2..511; same mean power/log2 frontend',
        model='32-16-ReLU-1 Adam .001 batch64 epochs100 seed71; 12fits',
        calibration='Same independent32 normals per ID, second highest; strict >',
        scope='Known installed machine ID selects weights/frequencies; same hardware; development only',final_test_opened=False))
    results=[]; predictions=np.full(len(rows),np.nan);decisions=np.zeros(len(rows),bool);votes=np.zeros(len(rows),int)
    for original in (f for f in previous['folds'] if f['model']=='mlp'):
        for m in IDS:
            indices={key:np.array([i for i in original[key] if machines[i]==m]) for key in ('fit_indices','validation_indices','calibration_indices')}
            fit,val,cal=(indices[key] for key in ('fit_indices','validation_indices','calibration_indices'))
            assert (len(fit),len(val),len(cal))==(128,64,64)
            assert not set(fit)&set(val) and not set(fit)&set(cal) and not set(val)&set(cal)
            bins=select_local(power[fit],y[fit]);raw=frontend(power,bins)
            mean=raw[fit].mean(0);std=np.maximum(raw[fit].std(0),1e-6);z=((raw-mean)/std).astype(np.float32)
            torch.manual_seed(71);model=nn.Sequential(nn.Linear(32,16),nn.ReLU(),nn.Linear(16,1))
            optimizer=torch.optim.Adam(model.parameters(),lr=.001)
            x=torch.from_numpy(z[fit]);target=torch.tensor(y[fit],dtype=torch.float32);losses=[]
            for epoch in range(100):
                total=0.
                for ids in torch.randperm(len(fit)).split(64):
                    optimizer.zero_grad();loss=nn.functional.binary_cross_entropy_with_logits(model(x[ids]).flatten(),target[ids])
                    assert torch.isfinite(loss);loss.backward();optimizer.step();total+=float(loss.detach())*len(ids)
                losses.append(total/len(fit))
            model.eval()
            with torch.no_grad():s=model(torch.from_numpy(z)).flatten().numpy().astype(float)
            path=out/f"mlp-id{m}-fold{original['fold']}.pt";torch.save(model.state_dict(),path)
            restored=nn.Sequential(nn.Linear(32,16),nn.ReLU(),nn.Linear(16,1));restored.load_state_dict(torch.load(path,weights_only=True));restored.eval()
            with torch.no_grad():np.testing.assert_array_equal(s,restored(torch.from_numpy(z)).flatten().numpy().astype(float))
            limit=float(np.sort(s[cal[y[cal]==0]])[-2]);r=measure(y[val],s[val],limit)
            fp,tp,_=roc_curve(y[val],s[val]);oracle=float(tp[fp<.05].max())
            r.update(machine=m,fold=original['fold'],threshold=limit,model_sha256=sha(path),
                bins=bins.tolist(),mean=mean.tolist(),std=std.tolist(),training_loss=losses,
                train_auc=float(roc_auc_score(y[fit],s[fit])),optimistic_validation_roc_recall_below_5pct_fpr=oracle,
                validation_scores=s[val].tolist(),calibration_scores=s[cal].tolist(),
                **{k:v.tolist() for k,v in indices.items()})
            results.append(r);predictions[val]=s[val];decisions[val]=s[val]>limit;votes[val]+=1
            print(m,original['fold'],f"recall={r['recall']:.4f} FPR={r['fpr']:.4f} AUC={r['auc']:.4f} trainAUC={r['train_auc']:.4f}",flush=True)
    assert all(votes[i]==int(row['role']=='cv') for i,row in enumerate(rows))
    summary={}
    for m in (*IDS,'pooled'):
        mask=(votes==1)&(True if m=='pooled' else machines==m)
        tp=int(decisions[mask&(y==1)].sum());fp=int(decisions[mask&(y==0)].sum());n=int((mask&(y==0)).sum());a=int((mask&(y==1)).sum())
        if m=='pooled':
            areas=[roc_auc_score(y[sel],predictions[sel]) for f in range(3)
                   for sel in [np.array([i for i,row in enumerate(rows) if row['role']=='cv' and row['fold']==f])]]
        else:areas=[r['auc'] for r in results if r['machine']==m]
        g=dict(tp=tp,fp=fp,normal=n,abnormal=a,recall=tp/a,fpr=fp/n,auc=float(np.mean(areas)));g['passed']=passed(g);summary[m]=g
    dump(out/'results.json',dict(records=rows,folds=results,summary=summary,passed=all(g['passed'] for g in summary.values()),
        final_test_opened=False,pooled_auc_note='Mean pooled fold raw logits; per-ID AUC also mandatory; logits from different per-ID fitted models'))
    print('SUMMARY',json.dumps(summary),flush=True)

if __name__=='__main__':
    torch.set_num_threads(2)
    with threadpool_limits(limits=2):main()
