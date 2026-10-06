#!/usr/bin/env python3
"""Exactly two candidates and three frozen within-machine recording folds."""
import json
from pathlib import Path
import joblib
import numpy as np
import torch
from torch import nn
from sklearn.linear_model import LogisticRegression
from threadpoolctl import threadpool_limits
from experiment_acoustic_v2 import dump,sha
from experiment_acoustic_finespectrum import spectrum
from diagnose_acoustic_v3 import metrics

ROOT=Path(__file__).resolve().parents[1]

def passed(m):return m['recall']>.9 and m['fpr']<.05 and m['auc']>=.9

def select_bands(power,y,machine):
    # Candidate centers 2..511, feature column k corresponds to FFT bin k+1.
    bands=power[:,:-2]+power[:,1:-1]+power[:,2:]
    log=np.log2(np.maximum(bands,1e-12)); discriminant=np.zeros(510)
    for m in ('00','02','04','06'):
        a=log[(machine==m)&(y==0)]; b=log[(machine==m)&(y==1)]
        discriminant+=(a.mean(0)-b.mean(0))**2/(a.var(0)+b.var(0)+1e-6)
    chosen=[]
    for i in np.lexsort((np.arange(510),-discriminant)):
        if all(abs(int(i)-j)>=3 for j in chosen):chosen.append(int(i))
        if len(chosen)==32:break
    return np.array(sorted(chosen))+2

def frontend(power,bins):
    return np.log2(np.maximum(np.stack([power[:,k-2:k+1].sum(1) for k in bins],axis=1),1e-12))

def main():
    base=ROOT/'data/mimii-known-machines-v1'; pp=base/'plan.json'
    assert sha(pp)==json.loads((base/'freeze.json').read_text())['plan_sha256']
    data=json.loads((base/'development.json').read_text())
    assert data['passed'] and data['plan_sha256']==sha(pp)
    audit_path=base/'development-audit.json'
    audit=json.loads(audit_path.read_text())
    assert audit['development_sha256']==sha(base/'development.json')
    if not audit['passed']:
        completion=json.loads((base/'development-audit-completion.json').read_text())
        assert completion['passed'] and completion['remaining']==0
        assert completion['original_audit_sha256']==sha(audit_path) and completion['development_sha256']==sha(base/'development.json')
        assert not audit['exact_duplicates'] and not audit['exact_cross_group_chunks']
        assert not any(p['flag'] for r in audit['reports'] for p in r['raw_review'])
        assert len(completion['additional_review'])==sum(r['unreviewed'] for r in audit['reports'])
        assert not any(r['flag'] for r in completion['additional_review'])
    rows=data['records']; assert len(rows)==1024 and all(r['role']!='final_test' for r in rows)
    out=ROOT/'artifacts/acoustic-known-machines-v1'; out.mkdir(exist_ok=False)
    dump(out/'protocol.json',dict(plan_sha256=sha(pp),source_sha256=sha(Path(__file__)),
        spectrum_source_sha256=sha(ROOT/'scripts/experiment_acoustic_finespectrum.py'),
        stage='float feasibility; NOT integer RTL equivalence or final release',
        feature='mean power over156 periodic-Hann N1024 windows; sum3 neighboring bins; log2 floor1e-12',
        frequency_selection='mean within-machine Fisher discriminant of training log-band power; 32 centers2..511, spacing>=3, low-bin tie break',
        scaling='training-only per-feature mean/std, std floor1e-6',
        models=['logistic C1 max_iter3000','MLP32-16-ReLU-1 Adam .001 batch64 epochs100 seed71'],
        selection='fixed last epoch; no extra search',final_test_opened=False))
    powers=[]
    for r in rows:
        path=ROOT/r['local']; assert sha(path)==r['npy_sha256']
        x=np.load(path,allow_pickle=False);assert x.shape==(160000,) and x.dtype==np.int16
        powers.append(spectrum(x[None,:159744],1024)[0])
    power=np.stack(powers); np.save(out/'development-power.npy',power)
    y=np.array([r['label'] for r in rows]); machine=np.array([r['machine'] for r in rows])
    role=np.array([r['role'] for r in rows]); folds=np.array([-1 if r['fold'] is None else r['fold'] for r in rows])
    cal=np.flatnonzero(role=='calibration'); results=[]
    predictions={name:np.full(len(rows),np.nan) for name in ('logistic','mlp')}
    decisions={name:np.zeros(len(rows),dtype=bool) for name in predictions}
    for fold in range(3):
        fit=np.flatnonzero((role=='cv')&(folds!=fold)); val=np.flatnonzero((role=='cv')&(folds==fold))
        assert (len(fit),len(val),len(cal))==(512,256,256)
        bins=select_bands(power[fit],y[fit],machine[fit]); raw=frontend(power,bins)
        mean=raw[fit].mean(0); std=np.maximum(raw[fit].std(0),1e-6)
        z=((raw-mean)/std).astype(np.float32)
        for name in ('logistic','mlp'):
            losses=[]
            if name=='logistic':
                model=LogisticRegression(C=1,max_iter=3000,random_state=71).fit(z[fit],y[fit])
                score=model.decision_function(z)
                joblib.dump(model,out/f'logistic-fold{fold}.joblib')
                np.testing.assert_array_equal(score,joblib.load(out/f'logistic-fold{fold}.joblib').decision_function(z))
            else:
                torch.manual_seed(71); model=nn.Sequential(nn.Linear(32,16),nn.ReLU(),nn.Linear(16,1))
                optimizer=torch.optim.Adam(model.parameters(),lr=.001)
                x=torch.from_numpy(z[fit]); target=torch.tensor(y[fit],dtype=torch.float32)
                for epoch in range(100):
                    total=0.
                    for ids in torch.randperm(len(fit)).split(64):
                        optimizer.zero_grad(); loss=nn.functional.binary_cross_entropy_with_logits(model(x[ids]).flatten(),target[ids])
                        assert torch.isfinite(loss);loss.backward();optimizer.step();total+=float(loss.detach())*len(ids)
                    losses.append(total/len(fit))
                model.eval()
                with torch.no_grad():score=model(torch.from_numpy(z)).flatten().numpy().astype(float)
                torch.save(model.state_dict(),out/f'mlp-fold{fold}.pt')
                restored=nn.Sequential(nn.Linear(32,16),nn.ReLU(),nn.Linear(16,1))
                restored.load_state_dict(torch.load(out/f'mlp-fold{fold}.pt',weights_only=True));restored.eval()
                with torch.no_grad():
                    np.testing.assert_array_equal(score,restored(torch.from_numpy(z)).flatten().numpy().astype(float))
            limits=[float(np.sort(score[cal[(machine[cal]==m)&(y[cal]==0)]])[-2]) for m in ('00','02','04','06')]
            limit=max(limits); predictions[name][val]=score[val];decisions[name][val]=score[val]>limit
            r=metrics(y[val],score[val],limit)
            r.update(model=name,fold=fold,bins=bins.tolist(),mean=mean.tolist(),std=std.tolist(),
                training_loss=losses,fit_indices=fit.tolist(),validation_indices=val.tolist(),calibration_indices=cal.tolist(),
                calibration_scores=score[cal].tolist(),validation_scores=score[val].tolist(),source_thresholds=limits)
            r['per_machine']={m:metrics(y[val[machine[val]==m]],score[val[machine[val]==m]],limit) for m in ('00','02','04','06')}
            results.append(r); print(name,fold,r['recall'],r['fpr'],r['auc'],flush=True)
    summary={}
    for name in predictions:
        groups={}
        for m in ('00','02','04','06','pooled'):
            mask=(role=='cv') if m=='pooled' else ((role=='cv')&(machine==m))
            pred=decisions[name][mask];truth=y[mask]
            # OOF scores use separately fitted models: report pooled AUC with this limitation.
            r=metrics(truth,predictions[name][mask],0)
            tp=int(pred[truth==1].sum());fp=int(pred[truth==0].sum())
            r.update(recall=tp/int((truth==1).sum()),fpr=fp/int((truth==0).sum()),
                confusion_matrix=[[int((truth==0).sum())-fp,fp],[int((truth==1).sum())-tp,tp]])
            r.pop('threshold');r['passed']=passed(r);groups[m]=r
            r['raw_oof_auc']=r['auc']
            r['auc']=float(np.mean([f['auc'] if m=='pooled' else f['per_machine'][m]['auc'] for f in results if f['model']==name]))
            r['passed']=passed(r)
        summary[name]=dict(groups=groups,passed=all(r['passed'] for r in groups.values()))
    selected=next((n for n in ('logistic','mlp') if summary[n]['passed']),None)
    dump(out/'results.json',dict(folds=results,summary=summary,selected=selected,
        records=rows,scope='development OOF decisions; AUC is mean of three equal-size folds, raw pooled OOF AUC separately reported; final single model independently tested',
        final_test_opened=False))
    print('SELECTED',selected,flush=True)

if __name__=='__main__':
    torch.set_num_threads(2)
    with threadpool_limits(limits=2):main()
