#!/usr/bin/env python3
"""Three leave-one-machine-out folds, source calibration, final freeze."""
from pathlib import Path
import json,platform
import numpy as np
import joblib
import sklearn
import scipy
from scipy.ndimage import uniform_filter1d
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import ExtraTreesClassifier
from vibfpga.multimachine import validate_plan,folds,source_threshold,violation
from experiment_acoustic_v2 import sha,dump
from experiment_acoustic_finespectrum import spectrum
from diagnose_acoustic_v3 import metrics
ROOT=Path(__file__).resolve().parents[1]

def spectra(rows,ph,allow_test=False):
    if not allow_test and any(r['role']=='final_test' for r in rows):raise ValueError('06 access prohibited before freeze')
    features=[];hashes={};seen={}
    for start in range(0,len(rows),16):
        batch=[]
        for r in rows[start:start+16]:
            p=ROOT/r['local'];rp=ROOT/'data/mimii-multimachine/receipts'/f"{r['machine']}_{r['label']}_{Path(r['name']).stem}.json";meta=json.loads(rp.read_text());h=sha(p)
            if h!=meta['npy_sha256'] or meta['plan_sha256']!=ph or meta['name']!=r['name']:raise ValueError('PCM receipt mismatch')
            if h in seen:raise ValueError('exact duplicate PCM: '+r['name']+' / '+seen[h])
            seen[h]=r['name'];hashes[r['local']]=h;x=np.load(p,allow_pickle=False)
            if x.shape!=(160000,) or x.dtype!=np.int16:raise ValueError('unexpected PCM shape/type')
            batch.append(x[:159744])
        features.append(np.log(np.maximum(spectrum(np.stack(batch),1024),1e-12)))
    return np.concatenate(features),hashes

def transform(x,kind):
    if kind=='absolute':return x
    if kind=='shape':return x-x.mean(1,keepdims=True)
    if kind=='localcontrast':return x-uniform_filter1d(x,size=17,axis=1,mode='reflect')
    raise ValueError(kind)

def make_model(kind):
    if kind=='linear_01':est=LogisticRegression(C=.1,max_iter=3000,random_state=29)
    elif kind=='linear_1':est=LogisticRegression(C=1,max_iter=3000,random_state=29)
    elif kind=='rbf_10':est=SVC(C=10,kernel='rbf',gamma='scale')
    elif kind=='trees':est=ExtraTreesClassifier(n_estimators=300,min_samples_leaf=2,max_features=.5,random_state=29,n_jobs=2)
    else:raise ValueError(kind)
    return make_pipeline(StandardScaler(),est)

def scores(model,x):
    if 'extratreesclassifier' in model.named_steps:
        model.set_params(extratreesclassifier__n_jobs=1)
        return model.predict_proba(x)[:,1]
    return model.decision_function(x)

def main():
    out=ROOT/'artifacts/acoustic-multimachine-v1';out.mkdir(exist_ok=False)
    pp=ROOT/'data/mimii-multimachine/plan.json';plan=json.loads(pp.read_text());validate_plan(plan);ph=sha(pp)
    original_path=ROOT/'data/mimii/plan.json';original=json.loads(original_path.read_text())
    assert sha(original_path)==plan['old_plan_sha256']
    assert plan['excluded_old_test']==sorted(r['name'] for r in original['records'] if r['split']=='test')
    receipt=json.loads((pp.parent/'development-download.json').read_text());assert receipt['complete'] and receipt['plan_sha256']==ph
    kinds=['absolute','shape','localcontrast'];models=['linear_01','linear_1','rbf_10','trees']
    source_paths=[Path(__file__).resolve(),ROOT/'src/vibfpga/multimachine.py',ROOT/'scripts/experiment_acoustic_v2.py',ROOT/'scripts/experiment_acoustic_finespectrum.py',ROOT/'scripts/diagnose_acoustic_v3.py',ROOT/'src/vibfpga/acoustic_experiment.py',ROOT/'scripts/prepare_multimachine.py',ROOT/'scripts/audit_multimachine.py',ROOT/'scripts/test_multimachine.py']
    protocol={'plan_sha256':ph,'task':'supervised multi-machine known-fault recognition','features':kinds,'models':models,'candidates':12,
      'folds':'hold out each of 00,02,04 in full; fit/calibration only from other two machines','source_fit_per_machine':256,'source_calibration_per_machine':64,
      'threshold':'max of source-machine normal calibration thresholds, strict score>threshold','held_machine_calibration':False,
      'selection':'minimize maximum per-machine normalized gate violation; then maximize worst-machine recall, mean AUC; deterministic name tie',
      'gate':{'min_recall':.9,'max_fpr':.05,'min_auc':.9},'final_fit':'fit-role records from all three machines; calibration-role records reserved for final threshold',
      'test':'06 once after freeze, even if development gate fails; no tuning or selective withholding of result','test_opened':False,
      'versions':{'python':platform.python_version(),'numpy':np.__version__,'sklearn':sklearn.__version__,'scipy':scipy.__version__,'joblib':joblib.__version__},
      'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in source_paths}}
    dump(out/'protocol.json',protocol)
    rows=[r for r in plan['records'] if r['role']!='final_test'];assert len(rows)==960
    base,bindings=spectra(rows,ph);np.save(out/'development-spectra.npy',base)
    y=np.array([r['label'] for r in rows]);machines=np.array([r['machine'] for r in rows]);results=[]
    for feature_kind in kinds:
        x=transform(base,feature_kind)
        for model_kind in models:
            name=feature_kind+'-'+model_kind;fold_results=[]
            for held,fit,cal,val in folds(rows):
                net=make_model(model_kind);net.fit(x[fit],y[fit]);cs=scores(net,x[cal]);threshold=source_threshold(cs,y[cal],machines[cal]);vs=scores(net,x[val])
                fold_path=out/(name+'-hold'+held+'.joblib');joblib.dump(net,fold_path)
                np.testing.assert_array_equal(vs,scores(joblib.load(fold_path),x[val]))
                r=metrics(y[val],vs,threshold);r.update(machine=held,fit_indices=fit.tolist(),calibration_indices=cal.tolist(),validation_indices=val.tolist(),
                  validation_scores=vs.tolist(),calibration_scores=cs.tolist(),gate_passed=r['recall']>=.9 and r['fpr']<=.05 and r['auc']>=.9)
                fold_results.append(r)
                print(name,'held',held,'AUC',round(r['auc'],4),'recall',round(r['recall'],4),'FPR',round(r['fpr'],4),flush=True)
            summary={'name':name,'feature':feature_kind,'model':model_kind,'folds':fold_results,
              'max_violation':max(violation(r) for r in fold_results),'min_recall':min(r['recall'] for r in fold_results),
              'mean_auc':float(np.mean([r['auc'] for r in fold_results])),'all_folds_passed':all(r['gate_passed'] for r in fold_results)}
            results.append(summary);dump(out/(name+'-folds.json'),summary)
    selected=min(results,key=lambda r:(round(r['max_violation'],12),-round(r['min_recall'],12),-round(r['mean_auc'],12),r['name']))
    dump(out/'development.json',{'selected':selected,'candidates':results,'records':[{'name':r['name'],'machine':r['machine'],'role':r['role'],'label':r['label']} for r in rows],
      'pcm_sha256':bindings,'test_opened':False,'selection_bias':'development folds used to select candidate; final 06 is the independent confirmation'})
    fit=np.array([i for i,r in enumerate(rows) if r['role']=='fit']);cal=np.array([i for i,r in enumerate(rows) if r['role']=='calibration'])
    x=transform(base,selected['feature']);final=make_model(selected['model']);final.fit(x[fit],y[fit]);cs=scores(final,x[cal]);threshold=source_threshold(cs,y[cal],machines[cal])
    joblib.dump(final,out/'final-model.joblib');np.testing.assert_array_equal(cs,scores(joblib.load(out/'final-model.joblib'),x[cal]))
    dump(out/'final-config.json',{'candidate':selected['name'],'feature':selected['feature'],'model':selected['model'],'threshold':threshold,
      'fit_records':len(fit),'calibration_records':len(cal),'fit_indices':fit.tolist(),'calibration_indices':cal.tolist(),'calibration_scores':cs.tolist(),
      'development_all_folds_passed':selected['all_folds_passed'],'test_machine':'06'})
    files={str(p.relative_to(ROOT)):sha(p) for p in out.iterdir() if p.is_file()};files.update(protocol['source_sha256']);files[str(pp.relative_to(ROOT))]=ph
    dump(out/'frozen.json',{'plan_sha256':ph,'candidate':selected['name'],'threshold':threshold,'feature':selected['feature'],'sha256':files,'pcm_sha256':bindings,'test_opened':False})
    print('FROZEN',selected['name'],'all development folds passed',selected['all_folds_passed'],'threshold',threshold,flush=True)
if __name__=='__main__':main()
