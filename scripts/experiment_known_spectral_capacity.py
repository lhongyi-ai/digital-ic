#!/usr/bin/env python3
"""Fixed information-preserving candidates, with finite-sample normal calibration."""
import json
from pathlib import Path
import joblib
import numpy as np
import torch
from torch import nn
from sklearn.linear_model import LogisticRegression
from threadpoolctl import threadpool_limits
from experiment_acoustic_v2 import sha,dump
from experiment_known_machine_local import measure

ROOT=Path(__file__).resolve().parents[1]
IDS=('00','02','04','06')

def main():
    old=ROOT/'artifacts/acoustic-known-machines-v1';base=ROOT/'data/mimii-known-machines-v1'
    previous=json.loads((old/'results.json').read_text());rows=previous['records']
    binding=json.loads((ROOT/'artifacts/acoustic-known-detail-v1/protocol.json').read_text())
    assert binding['power_sha256']==sha(old/'development-power.npy') and binding['baseline_sha256']==sha(old/'results.json')
    assert binding['plan_sha256']==sha(base/'plan.json')
    assert all(r['role'] in ('cv','calibration') for r in rows)
    full=np.log2(np.maximum(np.load(old/'development-power.npy',allow_pickle=False),1e-12))
    y=np.array([r['label'] for r in rows]);ms=np.array([r['machine'] for r in rows])
    out=ROOT/'artifacts/acoustic-known-capacity-v1';out.mkdir(exist_ok=False)
    dump(out/'protocol.json',dict(source_sha256=sha(Path(__file__)),baseline_sha256=sha(old/'results.json'),
        power_sha256=sha(old/'development-power.npy'),plan_sha256=sha(base/'plan.json'),
        candidates=['full512 MLP512-16-ReLU-1, Adam .001 batch64 epochs100 seed71',
                    'sparse64 Logistic C1 max_iter3000; top64 absolute standardized training-only full512 Logistic coefficients, refit64'],
        threshold='k=ceil((32+1)*(1-.05))=32; maximum separate normal calibration score, strict >',
        threshold_source='https://arxiv.org/abs/2107.07511',
        statistical_limit='Exchangeability and fixed model required for marginal guarantee; adaptive development and batch uncertainty prevent claiming a population FPR certificate',
        scope='Per-ID development, fixed original folds, 24fits excluding12 feature selectors; no final audio',final_test_opened=False))
    results=[]
    for original in (f for f in previous['folds'] if f['model']=='mlp'):
        for m in IDS:
            indices={k:np.array([i for i in original[k] if ms[i]==m]) for k in ('fit_indices','validation_indices','calibration_indices')}
            fit,val,cal=(indices[k] for k in ('fit_indices','validation_indices','calibration_indices'))
            mean=full[fit].mean(0);std=np.maximum(full[fit].std(0),1e-6);z=((full-mean)/std).astype(np.float32)
            selector=LogisticRegression(C=1,max_iter=3000,random_state=71).fit(z[fit],y[fit])
            for name in ('full512mlp','sparse64linear'):
                bins=np.arange(512) if name=='full512mlp' else np.sort(np.lexsort((np.arange(512),-np.abs(selector.coef_[0])))[:64])
                values=np.ascontiguousarray(z[:,bins]);losses=[]
                if name=='full512mlp':
                    torch.manual_seed(71);model=nn.Sequential(nn.Linear(512,16),nn.ReLU(),nn.Linear(16,1))
                    optimizer=torch.optim.Adam(model.parameters(),lr=.001);x=torch.from_numpy(values[fit]);target=torch.tensor(y[fit],dtype=torch.float32)
                    for epoch in range(100):
                        total=0.
                        for ids in torch.randperm(len(fit)).split(64):
                            optimizer.zero_grad();loss=nn.functional.binary_cross_entropy_with_logits(model(x[ids]).flatten(),target[ids]);assert torch.isfinite(loss)
                            loss.backward();optimizer.step();total+=float(loss.detach())*len(ids)
                        losses.append(total/len(fit))
                    model.eval()
                    with torch.no_grad():s=model(torch.from_numpy(values)).flatten().numpy().astype(float)
                    path=out/f"{name}-id{m}-fold{original['fold']}.pt";torch.save(model.state_dict(),path)
                    restored=nn.Sequential(nn.Linear(512,16),nn.ReLU(),nn.Linear(16,1));restored.load_state_dict(torch.load(path,weights_only=True));restored.eval()
                    with torch.no_grad():np.testing.assert_array_equal(s,restored(torch.from_numpy(values)).flatten().numpy().astype(float))
                else:
                    model=LogisticRegression(C=1,max_iter=3000,random_state=71).fit(values[fit],y[fit]);s=model.decision_function(values)
                    path=out/f"{name}-id{m}-fold{original['fold']}.joblib";joblib.dump(model,path)
                    np.testing.assert_array_equal(s,joblib.load(path).decision_function(values))
                normals=s[cal[y[cal]==0]];rank=int(np.ceil((len(normals)+1)*.95));assert rank==32
                limit=float(np.sort(normals)[rank-1]);r=measure(y[val],s[val],limit)
                r.update(model=name,machine=m,fold=original['fold'],threshold=limit,bins=(bins+1).tolist(),
                    mean=mean[bins].tolist(),std=std[bins].tolist(),training_loss=losses,fit_metrics=measure(y[fit],s[fit],limit),
                    validation_scores=s[val].tolist(),calibration_scores=s[cal].tolist(),model_sha256=sha(path),
                    **{k:v.tolist() for k,v in indices.items()})
                results.append(r);print(name,m,original['fold'],r['tp'],r['fp'],round(r['auc'],5),flush=True)
    summary={}
    for name in ('full512mlp','sparse64linear'):
        groups={}
        for m in IDS:
            fs=[f for f in results if f['model']==name and f['machine']==m]
            tp=sum(f['tp'] for f in fs);fp=sum(f['fp'] for f in fs)
            g=dict(tp=tp,fp=fp,normal=96,abnormal=96,recall=tp/96,fpr=fp/96,auc=float(np.mean([f['auc'] for f in fs])))
            g['passed']=g['recall']>.9 and g['fpr']<.05 and g['auc']>=.9;groups[m]=g
        summary[name]=dict(groups=groups,passed=all(g['passed'] for g in groups.values()))
    dump(out/'results.json',dict(folds=results,records=rows,summary=summary,final_test_opened=False))
    print('SUMMARY',json.dumps(summary),flush=True)

if __name__=='__main__':
    torch.set_num_threads(2)
    with threadpool_limits(limits=2):main()
