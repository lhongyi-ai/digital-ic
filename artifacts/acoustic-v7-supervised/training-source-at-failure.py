#!/usr/bin/env python3
"""Authorized known-fault classifier, separate fault training, fixed validation/test."""
import json
from pathlib import Path
import joblib
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.model_selection import GridSearchCV,StratifiedKFold
from experiment_acoustic_v2 import load,sha,dump
from experiment_acoustic_finespectrum import spectrum
from diagnose_acoustic_v3 import metrics
from vibfpga.acoustic_experiment import normal_threshold
ROOT=Path(__file__).resolve().parents[1]
def validate_extension(orig,ext):
    originals={r['name'] for r in orig['records']};new=[r['name'] for r in ext['records']]
    if len(new)!=len(set(new)) or originals.intersection(new):raise ValueError('extension leakage or duplicates')
    if any(r['split']!='train' or r['label']!=1 for r in ext['records']):raise ValueError('invalid extension')

def feature(x,kind):
    if kind=='band_mean_std':
        x=x[:,:x.shape[1]//1024*1024].reshape(len(x),-1,1024).astype(float)
        x-=x.mean(2,keepdims=True);hann=.5-.5*np.cos(2*np.pi*np.arange(1024)/1024)
        p=np.abs(np.fft.rfft(x/32768*hann,axis=2))**2
        f=np.log1p(p[:,:,1:].reshape(len(x),-1,16,32).sum(3))
        return np.concatenate([f.mean(1),f.std(1)],axis=1)
    n=int(kind.removeprefix('spectrum'));return np.log(np.maximum(spectrum(x,n),1e-12))

def main():
    out=ROOT/'artifacts/acoustic-v7-supervised';out.mkdir(exist_ok=False)
    pp=ROOT/'data/mimii/plan.json';plan=json.loads(pp.read_text());ep=ROOT/'data/mimii-supervised/plan.json';ext=json.loads(ep.read_text());validate_extension(plan,ext)
    if ext['original_plan_sha256']!=sha(pp):raise ValueError('original split changed')
    sources=[Path(__file__).resolve(),ROOT/'scripts/experiment_acoustic_v2.py',ROOT/'scripts/experiment_acoustic_finespectrum.py',ROOT/'scripts/diagnose_acoustic_v3.py',ROOT/'src/vibfpga/acoustic_experiment.py']
    dump(out/'protocol.json',{'task':'supervised known-fault recognition; user authorized separate fault training','normal_train':120,'abnormal_train':120,
      'validation':'original 40 normal and 30 abnormal; no training on validation','features':['band_mean_std','spectrum1024','spectrum4096'],
      'models':['linear','rbf','trees'],'hyperparameters':'5-fold stratified CV on training only, select by AUC',
      'validation_selection':'recall at 5% empirical normal FPR then AUC','gate':{'tp':27,'max_fp':2,'auc':.9},'test_opened':False,
      'plan_sha256':sha(pp),'extension_sha256':sha(ep),'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sources}})
    ti,tr,th=load('train',plan,sha(pp));vi,va,vh=load('validation',plan,sha(pp));tr=tr.reshape(len(tr),-1);va=va.reshape(len(va),-1)
    fault=[];extra_hashes={}
    for r in ext['records']:
        p=ep.parent/r['local'];m=json.loads(p.with_suffix('.json').read_text())
        if sha(p)!=m['npy_sha256'] or m['plan_sha256']!=sha(ep):raise ValueError('fault PCM binding mismatch')
        fault.append(np.load(p,allow_pickle=False)[:tr.shape[1]]);extra_hashes[str(p.relative_to(ROOT))]=sha(p)
    x=np.concatenate([tr,np.stack(fault)]);yt=np.r_[np.zeros(len(tr),int),np.ones(len(fault),int)];yv=np.array([r['label'] for r in vi]);normal=yv==0
    cv=StratifiedKFold(n_splits=5,shuffle=True,random_state=17);rows=[]
    for kind in ['band_mean_std','spectrum1024','spectrum4096']:
        t=feature(x,kind);v=feature(va,kind);np.savez_compressed(out/(kind+'-features.npz'),train=t,validation=v,train_labels=yt)
        definitions=[('linear',LogisticRegression(max_iter=3000,random_state=17),{'logisticregression__C':[.01,.1,1,10]}),
          ('rbf',SVC(kernel='rbf'),{'svc__C':[.1,1,10,100]}),
          ('trees',ExtraTreesClassifier(n_estimators=300,min_samples_leaf=2,max_features=.5,random_state=17,n_jobs=2),{'extratreesclassifier__max_depth':[5,None]})]
        for model,est,grid in definitions:
            search=GridSearchCV(make_pipeline(StandardScaler(),est),grid,scoring='roc_auc',cv=cv,n_jobs=1,refit=True)
            search.fit(t,yt);net=search.best_estimator_
            s=net.predict_proba(v)[:,1] if model=='trees' else net.decision_function(v)
            name=kind+'-'+model;mp=out/(name+'.joblib');joblib.dump(net,mp);loaded=joblib.load(mp)
            restored=loaded.predict_proba(v)[:,1] if model=='trees' else loaded.decision_function(v);np.testing.assert_array_equal(s,restored)
            row=metrics(yv,s,normal_threshold(s[normal]));row.update(name=name,training_cv_auc=float(search.best_score_),best_params=search.best_params_,scores=s.tolist(),features=t.shape[1])
            rows.append(row);dump(out/(name+'-cv.json'),{'params':search.cv_results_['params'],'mean_auc':search.cv_results_['mean_test_score'].tolist(),'std_auc':search.cv_results_['std_test_score'].tolist()})
            if model=='linear':
                scaler,clf=net.steps[0][1],net.steps[1][1];w=clf.coef_[0]/scaler.scale_;b=float(clf.intercept_[0]-w@scaler.mean_)
                np.testing.assert_allclose(v@w+b,s,rtol=1e-8,atol=1e-8)
                dump(out/(name+'-linear.json'),{'weights':w.tolist(),'bias':b,'threshold':row['threshold'],'feature':kind})
            print(name,'cv',round(search.best_score_,4),'val',round(row['auc'],4),round(row['recall'],4),flush=True)
    best=max(rows,key=lambda r:(round(r['recall'],12),round(r['auc'],12),-r['features']))
    gate=best['confusion_matrix'][1][1]>=27 and best['confusion_matrix'][0][1]<=2 and best['auc']>=.9
    dump(out/'validation.json',{'selected':best,'candidates':rows,'high_standard_passed':gate,'test_opened':False,'task':'supervised known-fault recognition',
      'records':[{'name':r['name'],'label':r['label']} for r in vi]})
    dump(out/'receipt.json',{'sha256':{str(p.relative_to(ROOT)):sha(p) for p in out.iterdir() if p.is_file()},'pcm_sha256':th|vh|extra_hashes,'test_opened':False})
    print('BEST',best['name'],best['recall'],best['auc'],'GATE',gate)
if __name__=='__main__':main()
