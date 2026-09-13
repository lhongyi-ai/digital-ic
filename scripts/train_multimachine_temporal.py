#!/usr/bin/env python3
"""Development-only temporal study. No 06 input or final-test operation."""
from pathlib import Path
import json
import numpy as np
import joblib
from vibfpga.temporal_acoustic import extract
from vibfpga.multimachine import validate_plan,folds,source_threshold,violation
from train_multimachine import make_model,scores
from experiment_acoustic_v2 import sha,dump
from diagnose_acoustic_v3 import metrics
ROOT=Path(__file__).resolve().parents[1]
def main():
    out=ROOT/'artifacts/acoustic-multimachine-temporal-v1';out.mkdir(exist_ok=False)
    pp=ROOT/'data/mimii-multimachine/plan.json';plan=json.loads(pp.read_text());validate_plan(plan)
    old=ROOT/'artifacts/acoustic-multimachine-v1/frozen.json';f=json.loads(old.read_text())
    assert sha(pp)==f['plan_sha256']
    assert all(sha(ROOT/p)==h for p,h in f['sha256'].items())
    rows=[r for r in plan['records'] if r['machine'] in ('00','02','04')]
    assert len(rows)==960 and not any(r['role']=='final_test' for r in rows)
    protocol={'task':'development-only whole-machine temporal classification','records':[r['name'] for r in rows],
      'plan_sha256':sha(pp),'features':['temporal','combined'],'models':['linear_01','linear_1','rbf_10','trees'],
      'threshold':'max source normal calibration empirical 5% thresholds; held machine never calibrated',
      'strict_gate':'recall > .90 and fpr < .05 and auc >= .90 for EVERY machine',
      'selection':'min worst normalized gate violation, then max minimum AUC',
      'final_test':'none; 06 excluded and previous result remains final for prior model',
      'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__).resolve(),ROOT/'src/vibfpga/temporal_acoustic.py']}}
    dump(out/'protocol.json',protocol)
    features={'temporal':[],'combined':[]};bindings={}
    for i,r in enumerate(rows):
        p=ROOT/r['local'];h=sha(p);assert f['pcm_sha256'][r['local']]==h
        bindings[r['local']]=h;v=extract(np.load(p,allow_pickle=False))
        for k in features:features[k].append(v[k])
        if (i+1)%160==0:print('features',i+1,flush=True)
    y=np.array([r['label'] for r in rows]);machines=np.array([r['machine'] for r in rows]);results=[]
    for kind,values in features.items():
        x=np.asarray(values);np.save(out/(kind+'.npy'),x)
        for modelkind in protocol['models']:
            name=kind+'-'+modelkind;rr=[]
            for held,fit,cal,val in folds(rows):
                model=make_model(modelkind);model.fit(x[fit],y[fit]);cs=scores(model,x[cal]);threshold=source_threshold(cs,y[cal],machines[cal]);vs=scores(model,x[val])
                path=out/(name+'-'+held+'.joblib');joblib.dump(model,path)
                np.testing.assert_array_equal(vs,scores(joblib.load(path),x[val]))
                r=metrics(y[val],vs,threshold);r.update(machine=held,gate_passed=r['recall']>.9 and r['fpr']<.05 and r['auc']>=.9,
                    fit_indices=fit.tolist(),calibration_indices=cal.tolist(),validation_indices=val.tolist(),calibration_scores=cs.tolist(),validation_scores=vs.tolist())
                rr.append(r);print(name,held,'AUC',round(r['auc'],4),'recall',round(r['recall'],4),'FPR',round(r['fpr'],4),flush=True)
            result={'name':name,'folds':rr,'all_passed':all(r['gate_passed'] for r in rr),'max_violation':max(violation(r) for r in rr),'min_auc':min(r['auc'] for r in rr)}
            results.append(result);dump(out/(name+'.json'),result)
    selected=min(results,key=lambda r:(r['max_violation'],-r['min_auc'],r['name']))
    dump(out/'results.json',{'selected':selected,'candidates':results,'pcm_sha256':bindings,'test_opened':False,'independent_confirmation':'still required; no new unused machine in current package'})
    dump(out/'bindings.json',{'sha256':{str(p.relative_to(ROOT)):sha(p) for p in out.iterdir() if p.is_file()},'source_sha256':protocol['source_sha256']})
    print('SELECTED',selected['name'],'ALL PASSED',selected['all_passed'],flush=True)
if __name__=='__main__':main()
