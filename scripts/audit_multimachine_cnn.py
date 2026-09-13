#!/usr/bin/env python3
"""Reload CNNs and audit partitions, calibration and prediction metrics."""
from pathlib import Path
import json,importlib
import numpy as np
import torch
from vibfpga.multimachine import folds
from experiment_acoustic_v2 import sha,dump
from audit_multimachine import manual_metrics,manual_threshold
ROOT=Path(__file__).resolve().parents[1]
def main():
    torch.set_num_threads(2);torch.use_deterministic_algorithms(True);reports=[]
    plan=json.loads((ROOT/'data/mimii-multimachine/plan.json').read_text());rows=[r for r in plan['records'] if r['machine'] in ('00','02','04')];y=np.array([r['label'] for r in rows]);m=np.array([r['machine'] for r in rows])
    for version,module in [('v1','train_multimachine_cnn'),('v2','train_multimachine_cnn_v2')]:
        mod=importlib.import_module(module);out=ROOT/('artifacts/acoustic-cnn-'+version);b=json.loads((out/'bindings.json').read_text());assert all(sha(ROOT/p)==h for p,h in b['sha256'].items());assert sha(ROOT/('scripts/'+module+'.py'))==b['source_sha256']
        result=json.loads((out/'results.json').read_text());raw=np.load(out/'patches.npy');checks=[]
        for c in result['candidates']:
            x=raw-raw.mean(axis=(2,3),keepdims=True)
            if c['name']=='timecenter':x=x-x.mean(axis=3,keepdims=True)
            x=np.ascontiguousarray(x/4,dtype=np.float32)
            for saved,(held,fit,cal,val) in zip(c['folds'],folds(rows)):
                assert saved['machine']==held
                for key,idx in [('fit_indices',fit),('calibration_indices',cal),('validation_indices',val)]:assert saved[key]==idx.tolist()
                model=mod.Net();model.load_state_dict(torch.load(out/(c['name']+'-'+held+'.pt'),weights_only=True));cs=mod.predict(model,x[cal]);vs=mod.predict(model,x[val]);np.testing.assert_allclose(vs,saved['validation_scores'],atol=1e-5,rtol=1e-5);np.testing.assert_allclose(cs,saved['calibration_scores'],atol=1e-5,rtol=1e-5);assert manual_threshold(np.array(saved['calibration_scores']),y[cal],m[cal])==saved['threshold'];np.testing.assert_array_equal(vs>saved['threshold'],np.array(saved['validation_scores'])>saved['threshold'])
                reload_metrics=manual_metrics(y[val],vs,saved['threshold']);k=manual_metrics(y[val],np.array(saved['validation_scores']),saved['threshold']);assert abs(k['auc']-saved['auc'])<1e-12 and k['tp']==saved['confusion_matrix'][1][1] and k['fp']==saved['confusion_matrix'][0][1]
                fs=mod.predict(model,x[fit]);fm=manual_metrics(y[fit],fs,saved['threshold'])
                checks.append({'representation':c['name'],'held':held,'fit_auc_diagnostic_only':fm['auc'],'validation':k,'reload_auc':reload_metrics['auc'],'max_score_reload_error':float(np.max(np.abs(vs-np.array(saved['validation_scores']))))})
        dump(out/'audit.json',{'passed':True,'test_opened':False,'bindings_sha256':sha(out/'bindings.json'),'checks':checks});reports.append({'version':version,'checks':checks})
    print(json.dumps(reports,indent=2))
if __name__=='__main__':main()
