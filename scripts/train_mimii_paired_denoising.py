#!/usr/bin/env python3
"""Fixed paired spectral regression diagnostic, source machines only."""
import json
from pathlib import Path
import joblib
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from train_multimachine import ROOT, make_model, scores, transform
from vibfpga.multimachine import folds, source_threshold
from experiment_acoustic_finespectrum import spectrum
from experiment_acoustic_v2 import dump, sha
from diagnose_acoustic_v3 import metrics


def main():
    old=ROOT/'artifacts/acoustic-multimachine-v1'
    frozen=json.loads((old/'frozen.json').read_text())
    p=old/'development-spectra.npy'; assert sha(p)==frozen['sha256'][str(p.relative_to(ROOT))]
    original=ROOT/'data/mimii-multimachine/plan.json'
    assert sha(original)==frozen['plan_sha256']
    rows=[r for r in json.loads(original.read_text())['records'] if r['role']!='final_test']
    data=ROOT/'data/mimii-snr-fit'; pp=data/'plan.json'; plan=json.loads(pp.read_text())
    assert plan['source_plan_sha256']==sha(original)
    previous=json.loads((ROOT/'artifacts/acoustic-mimii-snr-augmented-v1/results.json').read_text())
    out=ROOT/'artifacts/acoustic-mimii-paired-denoising-v1'; out.mkdir(exist_ok=False)
    dump(out/'protocol.json',dict(plan_sha256=sha(pp),script_sha256=sha(Path(__file__)),
        hypothesis='source-paired ridge mapping may remove nuisance noise better than sample augmentation',
        denoiser='StandardScaler then Ridge(alpha=10) on 128 source-only 0/+6 dB pairs per fold',
        classifier='shape spectrum, fixed linear_1 and trees; fit original source records after denoising',
        calibration='original 0 dB source normal records, unchanged rule',
        validation='original 0 dB held machine, no paired held data in fitting',final_test_opened=False))
    x=transform(np.load(p,allow_pickle=False),'shape')
    extras=[]
    for r in plan['records']:
        path=data/(r['machine']+'_'+str(r['label'])+'_'+Path(r['name']).stem+'.npy')
        assert sha(path)==previous['pcm_sha256'][str(path.relative_to(ROOT))]
        pcm=np.load(path,allow_pickle=False)
        extras.append(np.log(np.maximum(spectrum(pcm[None,:159744],1024),1e-12))[0])
    xe=transform(np.stack(extras),'shape'); lookup={r['name']:i for i,r in enumerate(rows)}
    y=np.array([r['label'] for r in rows]); machines=np.array([r['machine'] for r in rows])
    results=[]
    for held,fit,cal,val in folds(rows):
        allowed={rows[i]['name'] for i in fit}
        add=np.array([i for i,r in enumerate(plan['records']) if r['name'] in allowed])
        pair=np.array([lookup[plan['records'][i]['name']] for i in add])
        assert len(add)==128 and set(pair)<=set(fit)
        denoiser=make_pipeline(StandardScaler(),Ridge(alpha=10))
        denoiser.fit(x[pair],xe[add]); z=denoiser.predict(x)
        for kind in ('linear_1','trees'):
            model=make_model(kind); model.fit(z[fit],y[fit])
            cs=scores(model,z[cal]); vs=scores(model,z[val])
            limit=source_threshold(cs,y[cal],machines[cal]); result=metrics(y[val],vs,limit)
            path=out/f'{kind}-hold{held}.joblib'; joblib.dump((denoiser,model),path)
            d,m=joblib.load(path)
            np.testing.assert_allclose(vs,scores(m,d.predict(x[val])),rtol=0,atol=1e-10)
            np.testing.assert_array_equal(vs>limit,scores(m,d.predict(x[val]))>limit)
            result.update(model=kind,machine=held,validation_indices=val.tolist(),validation_scores=vs.tolist(),
                calibration_scores=cs.tolist(),paired_fit_indices=pair.tolist(),
                gate_passed=result['recall']>.9 and result['fpr']<.05 and result['auc']>=.9)
            results.append(result); dump(out/'partial-results.json',results)
            print(kind,held,result['recall'],result['fpr'],result['auc'],flush=True)
    dump(out/'results.json',dict(folds=results,all_passed=any(all(r['gate_passed'] for r in results if r['model']==k) for k in ('linear_1','trees'))))


if __name__=='__main__':main()
