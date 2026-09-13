#!/usr/bin/env python3
"""Two fixed feature diagnostics: unsmoothed selected32 MLP and full512 linear."""
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
    bind=json.loads((ROOT/'artifacts/acoustic-known-local-v1/protocol.json').read_text())
    assert bind['baseline_sha256']==sha(old/'results.json') and bind['power_sha256']==sha(old/'development-power.npy')
    assert bind['plan_sha256']==sha(base/'plan.json')
    assert all(r['role'] in ('cv','calibration') for r in rows)
    y=np.array([r['label'] for r in rows]);machines=np.array([r['machine'] for r in rows])
    power=np.load(old/'development-power.npy',allow_pickle=False);full=np.log2(np.maximum(power,1e-12))
    out=ROOT/'artifacts/acoustic-known-detail-v1';out.mkdir(exist_ok=False)
    dump(out/'protocol.json',dict(source_sha256=sha(Path(__file__)),baseline_sha256=sha(old/'results.json'),
        power_sha256=sha(old/'development-power.npy'),plan_sha256=sha(base/'plan.json'),
        scope='Per-ID, original frozen development folds and calibration; no test audio',
        candidates=['single32 MLP32-16-ReLU-1 Adam .001 batch64 epochs100 seed71, per-bin train Fisher top32',
                    'full512 LogisticRegression C1 max_iter3000 random_state71; information diagnostic'],
        threshold='second highest of32 separate normal calibration scores per ID; strict >',final_test_opened=False))
    results=[]
    for original in (f for f in previous['folds'] if f['model']=='mlp'):
        for m in IDS:
            idx={key:np.array([i for i in original[key] if machines[i]==m]) for key in ('fit_indices','validation_indices','calibration_indices')}
            fit,val,cal=(idx[k] for k in ('fit_indices','validation_indices','calibration_indices'))
            a,b=full[fit[y[fit]==0]],full[fit[y[fit]==1]]
            fisher=(a.mean(0)-b.mean(0))**2/(a.var(0)+b.var(0)+1e-6)
            for name in ('single32','full512'):
                bins=np.sort(np.lexsort((np.arange(512),-fisher))[:32]) if name=='single32' else np.arange(512)
                raw=full[:,bins];mean=raw[fit].mean(0);std=np.maximum(raw[fit].std(0),1e-6);z=((raw-mean)/std).astype(np.float32)
                losses=[]
                if name=='single32':
                    torch.manual_seed(71);model=nn.Sequential(nn.Linear(32,16),nn.ReLU(),nn.Linear(16,1))
                    opt=torch.optim.Adam(model.parameters(),lr=.001);x=torch.from_numpy(z[fit]);target=torch.tensor(y[fit],dtype=torch.float32)
                    for epoch in range(100):
                        total=0.
                        for ids in torch.randperm(len(fit)).split(64):
                            opt.zero_grad();loss=nn.functional.binary_cross_entropy_with_logits(model(x[ids]).flatten(),target[ids]);assert torch.isfinite(loss)
                            loss.backward();opt.step();total+=float(loss.detach())*len(ids)
                        losses.append(total/len(fit))
                    model.eval()
                    with torch.no_grad():s=model(torch.from_numpy(z)).flatten().numpy().astype(float)
                    path=out/f"{name}-id{m}-fold{original['fold']}.pt";torch.save(model.state_dict(),path)
                    restored=nn.Sequential(nn.Linear(32,16),nn.ReLU(),nn.Linear(16,1));restored.load_state_dict(torch.load(path,weights_only=True));restored.eval()
                    with torch.no_grad():np.testing.assert_array_equal(s,restored(torch.from_numpy(z)).flatten().numpy().astype(float))
                else:
                    model=LogisticRegression(C=1,max_iter=3000,random_state=71).fit(z[fit],y[fit]);s=model.decision_function(z)
                    path=out/f"{name}-id{m}-fold{original['fold']}.joblib";joblib.dump(model,path)
                    np.testing.assert_array_equal(s,joblib.load(path).decision_function(z))
                limit=float(np.sort(s[cal[y[cal]==0]])[-2]);r=measure(y[val],s[val],limit)
                r.update(model=name,machine=m,fold=original['fold'],threshold=limit,bins=(bins+1).tolist(),mean=mean.tolist(),std=std.tolist(),
                    training_loss=losses,fit_metrics=measure(y[fit],s[fit],limit),validation_scores=s[val].tolist(),calibration_scores=s[cal].tolist(),
                    model_sha256=sha(path),**{k:v.tolist() for k,v in idx.items()})
                results.append(r);print(name,m,original['fold'],r['tp'],r['fp'],round(r['auc'],5),flush=True)
    summary={}
    for name in ('single32','full512'):
        groups={}
        for m in IDS:
            fs=[r for r in results if r['model']==name and r['machine']==m]
            tp=sum(r['tp'] for r in fs);fp=sum(r['fp'] for r in fs)
            g=dict(tp=tp,fp=fp,normal=96,abnormal=96,recall=tp/96,fpr=fp/96,auc=float(np.mean([r['auc'] for r in fs])))
            g['passed']=g['recall']>.9 and g['fpr']<.05 and g['auc']>=.9;groups[m]=g
        summary[name]=dict(groups=groups,passed=all(g['passed'] for g in groups.values()))
    dump(out/'results.json',dict(folds=results,summary=summary,records=rows,final_test_opened=False))
    print('SUMMARY',json.dumps(summary),flush=True)

if __name__=='__main__':
    torch.set_num_threads(2)
    with threadpool_limits(limits=2):main()
