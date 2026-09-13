#!/usr/bin/env python3
"""One final held-machine test after freeze; no fitting or recalibration."""
from pathlib import Path
import json
import numpy as np
import joblib
from train_multimachine import spectra,transform,scores
from audit_multimachine import manual_metrics
from experiment_acoustic_v2 import sha,dump
from diagnose_acoustic_v3 import metrics
from vibfpga.multimachine import validate_plan
ROOT=Path(__file__).resolve().parents[1]
def main():
    out=ROOT/'artifacts/acoustic-multimachine-v1';f=json.loads((out/'frozen.json').read_text())
    for rel,h in f['sha256'].items():assert sha(ROOT/rel)==h
    a=json.loads((out/'development-audit.json').read_text());assert a['passed'] and a['freeze_sha256']==sha(out/'frozen.json')
    pp=ROOT/'data/mimii-multimachine/plan.json';p=json.loads(pp.read_text());validate_plan(p);assert sha(pp)==f['plan_sha256']
    with (out/'test-attempt.json').open('x') as handle:json.dump({'started':True,'freeze_sha256':sha(out/'frozen.json'),'machine':'06'},handle)
    rows=[r for r in p['records'] if r['role']=='final_test'];assert len(rows)==160 and {r['machine'] for r in rows}=={'06'}
    base,bindings=spectra(rows,f['plan_sha256'],allow_test=True)
    assert not(set(bindings)&set(f['pcm_sha256'])) and not(set(bindings.values())&set(f['pcm_sha256'].values()))
    x=transform(base,f['feature']);model=joblib.load(out/'final-model.joblib');s=scores(model,x);y=np.array([r['label'] for r in rows]);t=f['threshold']
    result=metrics(y,s,t);check=manual_metrics(y,s,t);assert abs(check['auc']-result['auc'])<1e-12
    assert check['tp']==result['confusion_matrix'][1][1] and check['fp']==result['confusion_matrix'][0][1]
    result.update(machine='06',candidate=f['candidate'],threshold_unchanged=True,normal_records=80,abnormal_records=80,high_standard_passed=result['recall']>=.9 and result['fpr']<=.05 and result['auc']>=.9,
      predictions=[{'name':r['name'],'label':int(label),'score':float(score),'predicted_abnormal':bool(score>t)} for r,label,score in zip(rows,y,s)],
      pcm_sha256=bindings,freeze_sha256=sha(out/'frozen.json'))
    dump(out/'test.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ('predictions','pcm_sha256')},indent=2))
if __name__=='__main__':main()
