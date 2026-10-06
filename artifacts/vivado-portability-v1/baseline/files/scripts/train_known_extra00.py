#!/usr/bin/env python3
"""Three full512 linear fits after fixed ID00 fit-only data expansion."""
import json
from pathlib import Path
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from threadpoolctl import threadpool_limits
from experiment_acoustic_v2 import sha,dump
from experiment_acoustic_finespectrum import spectrum
from experiment_known_machine_local import measure

ROOT=Path(__file__).resolve().parents[1]

def main():
    base=ROOT/'data/mimii-known-machines-v1';extra=ROOT/'data/mimii-known-extra00-v1'
    old=ROOT/'artifacts/acoustic-known-machines-v1';original=json.loads((old/'results.json').read_text())
    addition=json.loads((extra/'development.json').read_text());audit=json.loads((extra/'audit.json').read_text())
    assert audit['passed'] and audit['development_sha256']==sha(extra/'development.json') and audit['original_development_sha256']==sha(base/'development.json')
    assert json.loads((extra/'plan.json').read_text())['original_plan_sha256']==sha(base/'plan.json')
    assert sha(old/'development-power.npy')==json.loads((ROOT/'artifacts/acoustic-known-detail-v1/protocol.json').read_text())['power_sha256']
    out=ROOT/'artifacts/acoustic-known-extra00-v1';out.mkdir(exist_ok=False)
    dump(out/'protocol.json',dict(source_sha256=sha(Path(__file__)),original_results_sha256=sha(old/'results.json'),
        power_sha256=sha(old/'development-power.npy'),extra_sha256=sha(extra/'development.json'),audit_sha256=sha(extra/'audit.json'),
        plan_sha256=sha(base/'plan.json'),model='Per-ID00 full512 Logistic C1 max_iter3000 random_state71',
        training='Original fold128 fit plus256 extra fit-only, 384 recordings total per fold; existing64 val and64 calibration unchanged',
        threshold='maximum of32 separate normal calibration scores; finite rank ceil33*.95=32; strict >',
        scope='three fits on same validation folds; no final refit or final evaluation',final_test_opened=False))
    more=[]
    for r in addition['records']:
        path=ROOT/r['local'];assert sha(path)==r['npy_sha256'];x=np.load(path,allow_pickle=False)
        more.append(spectrum(x[None,:159744],1024)[0])
    added=np.stack(more);np.save(out/'extra-power.npy',added)
    power=np.concatenate([np.load(old/'development-power.npy',allow_pickle=False),added]);raw=np.log2(np.maximum(power,1e-12))
    rows=original['records']+addition['records'];y=np.array([r['label'] for r in rows]);extra_indices=np.arange(1024,1280);results=[]
    for f in (f for f in original['folds'] if f['model']=='mlp'):
        fit=np.r_[np.array([i for i in f['fit_indices'] if rows[i]['machine']=='00']),extra_indices]
        val=np.array([i for i in f['validation_indices'] if rows[i]['machine']=='00']);cal=np.array([i for i in f['calibration_indices'] if rows[i]['machine']=='00'])
        assert (len(fit),len(val),len(cal))==(384,64,64)
        mean=raw[fit].mean(0);std=np.maximum(raw[fit].std(0),1e-6);z=((raw-mean)/std).astype(np.float32)
        model=LogisticRegression(C=1,max_iter=3000,random_state=71).fit(z[fit],y[fit]);s=model.decision_function(z)
        path=out/f"linear-id00-fold{f['fold']}.joblib";joblib.dump(model,path)
        np.testing.assert_array_equal(s,joblib.load(path).decision_function(z))
        limit=float(max(s[cal[y[cal]==0]]));r=measure(y[val],s[val],limit)
        r.update(fold=f['fold'],machine='00',threshold=limit,mean=mean.tolist(),std=std.tolist(),model_sha256=sha(path),
                 validation_scores=s[val].tolist(),calibration_scores=s[cal].tolist(),fit_indices=fit.tolist(),validation_indices=val.tolist(),calibration_indices=cal.tolist(),
                 fit_metrics=measure(y[fit],s[fit],limit))
        results.append(r);print('fold',f['fold'],r['tp'],r['fp'],r['auc'],flush=True)
    tp=sum(f['tp'] for f in results);fp=sum(f['fp'] for f in results)
    g=dict(tp=tp,fp=fp,normal=96,abnormal=96,recall=tp/96,fpr=fp/96,auc=float(np.mean([f['auc'] for f in results])))
    g['passed']=g['recall']>.9 and g['fpr']<.05 and g['auc']>=.9
    dump(out/'results.json',dict(folds=results,summary=g,records=rows,extra_power_sha256=sha(out/'extra-power.npy'),final_test_opened=False))
    print('SUMMARY',json.dumps(g),flush=True)

if __name__=='__main__':
    with threadpool_limits(limits=2):main()
