#!/usr/bin/env python3
"""Independent split, source-calibration and metric audit; no test-set access."""
from pathlib import Path
import json
import numpy as np
import joblib
from experiment_acoustic_v2 import sha,dump
from audit_multimachine import manual_metrics
from train_multimachine import scores
from vibfpga.multimachine import folds
ROOT=Path(__file__).resolve().parents[1]
def main():
    out=ROOT/'artifacts/acoustic-multimachine-temporal-v1'
    b=json.loads((out/'bindings.json').read_text())
    assert all(sha(ROOT/p)==h for p,h in {**b['sha256'],**b['source_sha256']}.items())
    result=json.loads((out/'results.json').read_text());protocol=json.loads((out/'protocol.json').read_text())
    pp=ROOT/'data/mimii-multimachine/plan.json';assert sha(pp)==protocol['plan_sha256']
    rows=[r for r in json.loads(pp.read_text())['records'] if r['machine'] in ('00','02','04')]
    assert [r['name'] for r in rows]==protocol['records']
    assert all(sha(ROOT/p)==h for p,h in result['pcm_sha256'].items())
    y=np.array([r['label'] for r in rows]);machines=np.array([r['machine'] for r in rows]);checked=0
    for candidate in result['candidates']:
        name=candidate['name'];kind=name.split('-')[0];x=np.load(out/(kind+'.npy'))
        for saved,(held,fit,cal,val) in zip(candidate['folds'],folds(rows)):
            assert held==saved['machine']
            for key,index in [('fit_indices',fit),('calibration_indices',cal),('validation_indices',val)]:assert saved[key]==index.tolist()
            model=joblib.load(out/(name+'-'+held+'.joblib'))
            np.testing.assert_allclose(model.named_steps['standardscaler'].mean_,x[fit].mean(0),rtol=1e-12,atol=1e-12)
            vs=scores(model,x[val]);cs=scores(model,x[cal])
            np.testing.assert_array_equal(vs,saved['validation_scores']);np.testing.assert_array_equal(cs,saved['calibration_scores'])
            thresholds=[]
            for m in set(machines[cal]):
                normal=np.sort(cs[(y[cal]==0)&(machines[cal]==m)])
                assert len(normal)==32
                thresholds.append(float(normal[-2]))
            assert saved['threshold']==max(thresholds)
            independent=manual_metrics(y[val],vs,saved['threshold'])
            assert independent['tp']==saved['confusion_matrix'][1][1] and independent['fp']==saved['confusion_matrix'][0][1]
            assert abs(independent['auc']-saved['auc'])<1e-12
            assert saved['gate_passed']==(independent['tp']/160>.9 and independent['fp']/160<.05 and independent['auc']>=.9)
            checked+=1
    dump(out/'audit.json',{'passed':True,'fold_models_checked':checked,'test_opened':False,'bindings_sha256':sha(out/'bindings.json'),'source_sha256':sha(Path(__file__))})
    print('AUDIT PASSED',checked,'fold models; no test access')
if __name__=='__main__':main()
