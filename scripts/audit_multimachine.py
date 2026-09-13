#!/usr/bin/env python3
"""Verify selected LOSO folds, fitting/calibration partition, and final threshold."""
from pathlib import Path
import json
import numpy as np
import joblib
from train_multimachine import transform,scores
from vibfpga.multimachine import validate_plan,folds
from experiment_acoustic_v2 import sha,dump
ROOT=Path(__file__).resolve().parents[1]
def manual_metrics(y,s,t):
    pred=s>t;normal=y==0;fault=y==1
    auc=float(((s[fault,None]>s[normal]).sum()+.5*(s[fault,None]==s[normal]).sum())/(fault.sum()*normal.sum()))
    return {'tp':int(np.sum(pred&fault)),'fp':int(np.sum(pred&normal)),'auc':auc}
def manual_threshold(s,y,m):
    return max(float(np.sort(s[(y==0)&(m==machine)])[len(s[(y==0)&(m==machine)])-int(np.floor(.05*np.sum((y==0)&(m==machine))))-1]) for machine in sorted(set(m)))
def main():
    out=ROOT/'artifacts/acoustic-multimachine-v1';f=json.loads((out/'frozen.json').read_text())
    for rel,h in f['sha256'].items():assert sha(ROOT/rel)==h
    pp=ROOT/'data/mimii-multimachine/plan.json';plan=json.loads(pp.read_text());validate_plan(plan);assert sha(pp)==f['plan_sha256']
    original_path=ROOT/'data/mimii/plan.json';original=json.loads(original_path.read_text())
    assert sha(original_path)==plan['old_plan_sha256'] and plan['excluded_old_test']==sorted(r['name'] for r in original['records'] if r['split']=='test')
    rows=[r for r in plan['records'] if r['role']!='final_test'];report=json.loads((out/'development.json').read_text());selected=report['selected'];base=np.load(out/'development-spectra.npy');x=transform(base,selected['feature'])
    assert set(f['pcm_sha256'])=={r['local'] for r in rows}
    for rel,h in f['pcm_sha256'].items():assert sha(ROOT/rel)==h
    y=np.array([r['label'] for r in rows]);m=np.array([r['machine'] for r in rows]);checks=[]
    for held,fit,cal,val in folds(rows):
        row=next(r for r in selected['folds'] if r['machine']==held)
        assert row['fit_indices']==fit.tolist() and row['calibration_indices']==cal.tolist() and row['validation_indices']==val.tolist()
        net=joblib.load(out/(selected['name']+'-hold'+held+'.joblib'))
        np.testing.assert_allclose(net.named_steps['standardscaler'].mean_,x[fit].mean(0),rtol=1e-12,atol=1e-12)
        cs=scores(net,x[cal]);vs=scores(net,x[val]);np.testing.assert_array_equal(vs,row['validation_scores'])
        threshold=manual_threshold(cs,y[cal],m[cal]);assert threshold==row['threshold']
        count=manual_metrics(y[val],vs,threshold);assert abs(count['auc']-row['auc'])<1e-12
        assert count['tp']==row['confusion_matrix'][1][1] and count['fp']==row['confusion_matrix'][0][1]
        checks.append({'held':held,**count,'threshold':threshold,'held_machine_used_for_calibration':False})
    config=json.loads((out/'final-config.json').read_text());fit=np.array(config['fit_indices']);cal=np.array(config['calibration_indices'])
    assert set(fit)=={i for i,r in enumerate(rows) if r['role']=='fit'} and set(cal)=={i for i,r in enumerate(rows) if r['role']=='calibration'}
    final=joblib.load(out/'final-model.joblib');np.testing.assert_allclose(final.named_steps['standardscaler'].mean_,x[fit].mean(0),rtol=1e-12,atol=1e-12)
    assert manual_threshold(scores(final,x[cal]),y[cal],m[cal])==config['threshold']==f['threshold']
    dump(out/'development-audit.json',{'passed':True,'selected_folds':checks,'final_fit_records':len(fit),'final_calibration_records':len(cal),'no_test_pcm_read':True,'freeze_sha256':sha(out/'frozen.json')})
    print(json.dumps(checks,indent=2))
if __name__=='__main__':main()
