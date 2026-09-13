#!/usr/bin/env python3
"""Paired higher-SNR fit augmentation; original 0 dB whole-machine validation."""
import json
from pathlib import Path
import joblib
import numpy as np
from train_multimachine import ROOT, make_model, scores, transform
from vibfpga.multimachine import folds, source_threshold
from experiment_acoustic_finespectrum import spectrum
from experiment_acoustic_v2 import dump, sha
from diagnose_acoustic_v3 import metrics


def main():
    old=ROOT/'artifacts/acoustic-multimachine-v1'
    frozen=json.loads((old/'frozen.json').read_text())
    # Only verify saved development evidence; never load final-test PCM.
    for path in (old/'development-spectra.npy',old/'development.json',ROOT/'scripts/train_multimachine.py',ROOT/'scripts/experiment_acoustic_finespectrum.py'):
        assert sha(path)==frozen['sha256'][str(path.relative_to(ROOT))]
    data=ROOT/'data/mimii-snr-fit'; plan_path=data/'plan.json'
    plan=json.loads(plan_path.read_text()); receipt=json.loads((data/'complete.json').read_text())
    assert receipt['passed'] and receipt['plan_sha256']==sha(plan_path)
    original_path=ROOT/'data/mimii-multimachine/plan.json'
    assert sha(original_path)==plan['source_plan_sha256']==frozen['plan_sha256']
    original=json.loads(original_path.read_text())
    rows=[r for r in original['records'] if r['role']!='final_test']
    out=ROOT/'artifacts/acoustic-mimii-snr-augmented-v1'; out.mkdir(exist_ok=False)
    dump(out/'protocol.json',dict(plan_sha256=sha(plan_path),script_sha256=sha(Path(__file__)),
        feature='existing 512-bin log spectrum, subtract per-record mean',
        models=['linear_1','trees'],additional_fit='64 paired +6 dB records per source machine only',
        threshold='unchanged source-machine normal 0 dB calibration rule',
        evaluation='unchanged 0 dB whole-machine held-out development recordings',
        final_test_opened=False,gate='recall > .90, FPR < .05, AUC >= .90 on all three folds'))
    extra=[]; hashes={}; seen=set()
    for r in plan['records']:
        path=data/(r['machine']+'_'+str(r['label'])+'_'+Path(r['name']).stem+'.npy')
        meta=json.loads(path.with_suffix('.json').read_text()); h=sha(path)
        assert meta['plan_sha256']==sha(plan_path) and meta['npy_sha256']==h and meta['name']==r['name']
        assert h not in seen; seen.add(h); hashes[str(path.relative_to(ROOT))]=h
        pcm=np.load(path,allow_pickle=False)
        assert pcm.shape==(160000,) and pcm.dtype==np.int16
        extra.append(np.log(np.maximum(spectrum(pcm[None,:159744],1024),1e-12))[0])
    x=transform(np.load(old/'development-spectra.npy',allow_pickle=False),'shape')
    xe=transform(np.stack(extra),'shape'); y=np.array([r['label'] for r in rows])
    ye=np.array([r['label'] for r in plan['records']]); machines=np.array([r['machine'] for r in rows])
    results=[]
    for kind in ('linear_1','trees'):
        for held,fit,cal,val in folds(rows):
            fit_names={rows[i]['name'] for i in fit}
            add=np.array([i for i,r in enumerate(plan['records']) if r['name'] in fit_names])
            assert len(add)==128 and all(plan['records'][i]['machine']!=held for i in add)
            model=make_model(kind); model.fit(np.r_[x[fit],xe[add]],np.r_[y[fit],ye[add]])
            cs=scores(model,x[cal]); vs=scores(model,x[val])
            limit=source_threshold(cs,y[cal],machines[cal]); result=metrics(y[val],vs,limit)
            path=out/f'{kind}-hold{held}.joblib'; joblib.dump(model,path)
            np.testing.assert_array_equal(vs,scores(joblib.load(path),x[val]))
            result.update(model=kind,machine=held,validation_indices=val.tolist(),validation_scores=vs.tolist(),
                extra_fit_indices=add.tolist(),calibration_scores=cs.tolist(),
                gate_passed=result['recall']>.9 and result['fpr']<.05 and result['auc']>=.9)
            results.append(result); dump(out/'partial-results.json',results)
            print(kind,held,result['recall'],result['fpr'],result['auc'],flush=True)
    dump(out/'results.json',dict(folds=results,pcm_sha256=hashes,
        all_passed=any(all(r['gate_passed'] for r in results if r['model']==k) for k in ('linear_1','trees'))))


if __name__=='__main__':main()
