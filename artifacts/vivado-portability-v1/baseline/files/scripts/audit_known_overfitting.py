#!/usr/bin/env python3
"""Frozen within-machine CV train/validation gap and 40 label-permutation controls."""
import json
from pathlib import Path
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from threadpoolctl import threadpool_limits
from experiment_acoustic_v2 import sha,dump
ROOT=Path(__file__).resolve().parents[1]

def main():
    old=ROOT/'artifacts/acoustic-known-detail-v1';r=json.loads((old/'results.json').read_text());rows=r['records']
    audit=json.loads((old/'audit.json').read_text());assert audit['passed'] and audit['results_sha256']==sha(old/'results.json')
    power_path=ROOT/'artifacts/acoustic-known-machines-v1/development-power.npy';power=np.load(power_path)
    assert json.loads((old/'protocol.json').read_text())['power_sha256']==sha(power_path)
    raw=np.log2(np.maximum(power,1e-12));y=np.array([v['label'] for v in rows])
    out=ROOT/'artifacts/acoustic-known-overfit-audit-v1';out.mkdir(exist_ok=False)
    dump(out/'protocol.json',dict(source_sha256=sha(Path(__file__)),results_sha256=sha(old/'results.json'),power_sha256=sha(power_path),
        task='Audit only, no model selection or changes',permutations=40,seeds=list(range(7100,7140)),
        permutation='Shuffle labels within each machine and each fixed CV fold, preserving32/32 balance; use permuted labels for both fitting and held-fold scoring',
        metric='mean of3 validation AUC per machine; training-only normalization; classifier configuration unchanged',
        caveat='Controls labels within existing recording splits, not acquisition-batch independence; repeated adaptive development means this is diagnostic, not a generalization guarantee',final_test_opened=False))
    results={}
    for m in ('00','02','04','06'):
        folds=[f for f in r['folds'] if f['model']=='full512' and f['machine']==m];data=[];gaps=[]
        for f in folds:
            fit=np.array(f['fit_indices']);val=np.array(f['validation_indices']);assert not set(fit)&set(val)
            # Preserve original advanced-index column layout for exact frozen-model inference.
            z=((raw[:,np.arange(512)]-f['mean'])/f['std']).astype(np.float32)
            path=old/f"full512-id{m}-fold{f['fold']}.joblib";assert sha(path)==f['model_sha256'];model=joblib.load(path)
            score=model.decision_function(z);np.testing.assert_allclose(score[val],f['validation_scores'],rtol=0,atol=1e-10)
            gaps.append(dict(fold=f['fold'],train_auc=roc_auc_score(y[fit],score[fit]),validation_auc=roc_auc_score(y[val],score[val])))
            data.append((fit,val,z))
        controls=[]
        for seed in range(7100,7140):
            rng=np.random.default_rng(seed);permuted=y.copy()
            for _,val,_ in data:permuted[val]=rng.permutation(y[val])
            values=[]
            for fit,val,z in data:
                model=LogisticRegression(C=1,max_iter=3000,random_state=71).fit(z[fit],permuted[fit])
                values.append(roc_auc_score(permuted[val],model.decision_function(z[val])))
            controls.append(dict(seed=seed,fold_auc=values,mean_auc=float(np.mean(values))))
        observed=float(np.mean([g['validation_auc'] for g in gaps]));null=np.array([c['mean_auc'] for c in controls])
        results[m]=dict(train_validation=gaps,observed_mean_auc=observed,permutations=controls,
            null_mean=float(null.mean()),null_min=float(null.min()),null_max=float(null.max()),
            monte_carlo_tail_fraction=float((1+np.sum(null>=observed))/(1+len(null))))
        print(m,'train',round(np.mean([g['train_auc'] for g in gaps]),5),'validation',round(observed,5),'shuffled',round(null.mean(),5),flush=True)
    dump(out/'results.json',dict(machines=results,final_test_opened=False,models_modified=False))
    dump(out/'receipt.json',dict(results_sha256=sha(out/'results.json'),protocol_sha256=sha(out/'protocol.json'),source_sha256=sha(Path(__file__))))
    lines=['# AUC=1 and overfitting review','','AUC=1 only means that fault scores exceed normal scores in this finite validation sample. A fixed threshold may still produce false alarms. AUC=1 alone proves neither overfitting nor field generalization. The checks below leave the final test sealed and do not change the model.','',
        '|Machine|Mean training AUC across three folds|Mean validation AUC across three folds|Mean AUC across 40 label shuffles|Range of shuffled mean AUC|','|---|---:|---:|---:|---|']
    for m,v in results.items():lines.append(f"|{m}|{np.mean([g['train_auc'] for g in v['train_validation']]):.5f}|{v['observed_mean_auc']:.5f}|{v['null_mean']:.5f}|{v['null_min']:.5f}–{v['null_max']:.5f}|")
    lines += ['', 'The 40 controls shuffle labels within each machine and CV fold, using shuffled labels for both training and validation. Spectral inputs contain no filenames or labels, and normalization uses training folds only. Near-chance controls support a relationship between labels and sound, but do not establish that it is the physical field-fault mechanism.', '',
        'Remaining limits: repeated model selection on development data can produce adaptive optimism; recordings of one machine on one test rig may share acquisition conditions; near-duplicate screening does not prove batch independence; four fans and one noise condition do not represent unfamiliar models or field environments.', '',
        'The 40 Monte Carlo tail counts are development diagnostics only. Their resolution is limited and they do not include earlier adaptive model selection; they do not independently establish significance or absence of overfitting.', '',
        'Final confirmation: after freezing the model, integer algorithm, RTL, and thresholds, evaluate the 720 holdout recordings once and report per-machine metrics and confidence intervals. Do not tune on this test set after failure or change splits, thresholds, or success criteria after viewing results.']
    (ROOT/'docs/known-overfitting-audit.md').write_text('\n'.join(lines)+'\n')
if __name__=='__main__':
    with threadpool_limits(limits=2):main()
