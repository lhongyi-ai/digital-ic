#!/usr/bin/env python3
"""Bounded diagnosis: pooling, loudness, and correlations. Saved train/val only."""
import hashlib,json
from pathlib import Path
import numpy as np
from sklearn.covariance import LedoitWolf
from sklearn.cluster import KMeans
from sklearn.metrics import roc_auc_score,confusion_matrix
from vibfpga.acoustic_experiment import normal_threshold
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def pool(s,kind):
    if kind=='mean':return s.mean(1)
    if kind=='top10':return np.sort(s,axis=1)[:,-int(np.ceil(s.shape[1]*.1)):].mean(1)
    if kind=='max4':return np.stack([s[:,i:s.shape[1]-3+i] for i in range(4)]).mean(0).max(1)
    raise ValueError(kind)
def uncontext(x):
    # Saved c8 tensor has 149 contexts. Recover original 156 windows exactly once.
    if x.ndim!=3 or x.shape[-1]!=128:raise ValueError('requires frozen uniform16 c8 features')
    return np.concatenate([x[:,:,:16],x[:,-1,16:].reshape(len(x),7,16)],axis=1)
def metrics(y,s,t):
    tn,fp,fn,tp=confusion_matrix(y,s>t,labels=[0,1]).ravel()
    return dict(auc=float(roc_auc_score(y,s)),fpr=float(fp/(tn+fp)),recall=float(tp/(tp+fn)),threshold=float(t),confusion_matrix=[[int(tn),int(fp)],[int(fn),int(tp)]])
def main():
    out=ROOT/'artifacts/acoustic-v3-diagnosis';out.mkdir(exist_ok=False)
    prev=ROOT/'artifacts/acoustic-v2-study';receipt=json.loads((prev/'receipt.json').read_text())
    for rel,h in receipt['sha256'].items():
        if sha(ROOT/rel)!=h:raise ValueError('input evidence changed')
    protocol=dict(representations=['log1p','logshape','logshape_level'],models=['centroid','covariance','kmeans4'],pooling=['mean','top10','max4'],
      goal='test transient dilution, common loudness and correlated bands; 27 fixed candidates',
      normalization='train-normal only; centroid on log1p unstandardized for exact v2 baseline; other inputs standardized using normal training',
      threshold='normal validation empirical 5%, strict greater',seed=7,test_opened=False,
      inputs={str(prev/'receipt.json'):sha(prev/'receipt.json')},source_sha256={str(Path(__file__).resolve().relative_to(ROOT)):sha(Path(__file__).resolve()),'src/vibfpga/acoustic_experiment.py':sha(ROOT/'src/vibfpga/acoustic_experiment.py')})
    dump(out/'protocol.json',protocol)
    z=np.load(prev/'selected-features.npz');tr=uncontext(z['train']).astype(float);va=uncontext(z['validation']).astype(float)
    records=json.loads((prev/'validation.json').read_text())['validation_records'];y=np.array([r['label'] for r in records]);normal=y==0
    old=json.loads((prev/'uniform16-log-c1-centroid.json').read_text());mu=np.array(old['parameters']['mean']);baseline=((va-mu)**2).mean(2)
    np.testing.assert_allclose(baseline.mean(1),old['metrics']['validation_scores'],rtol=2e-6)
    base_t=normal_threshold(baseline[normal].mean(1));basepred=baseline.mean(1)>base_t
    audit=json.loads((prev/'input-audit.json').read_text());rms=np.r_[audit['groups'][1]['rms_per_record'],audit['groups'][2]['rms_per_record']]
    contrib=((va-mu)**2).mean(1)
    diag={'baseline_score_rms_correlation':float(np.corrcoef(baseline.mean(1),rms)[0,1]),
      'normal_score_rms_correlation':float(np.corrcoef(baseline[normal].mean(1),rms[normal])[0,1]),
      'per_band_normal_mean_squared_deviation':contrib[normal].mean(0).tolist(),
      'per_band_missed_abnormal_mean_squared_deviation':contrib[(y==1)&~basepred].mean(0).tolist(),
      'baseline_metrics':metrics(y,baseline.mean(1),base_t)}
    rows=[];score_arrays={}
    for rep in protocol['representations']:
        xx=[]
        for x in [tr,va]:
            if rep=='log1p':v=x
            else:
                log=np.log(np.maximum(np.expm1(x),1e-12));level=log.mean(2,keepdims=True);shape=log-level
                v=shape if rep=='logshape' else np.concatenate([shape,level],axis=2)
            xx.append(v)
        tx,vx=xx;d=tx.shape[-1];tf=tx.reshape(-1,d);vf=vx.reshape(-1,d)
        mean=tf.mean(0);std=np.maximum(tf.std(0),1e-4);tz=(tf-mean)/std;vz=(vf-mean)/std
        for kind in protocol['models']:
            params={'representation':rep,'mean':mean.tolist(),'std':std.tolist(),'model':kind}
            if kind=='centroid':
                if rep=='log1p':ss=baseline.copy()
                else:ss=(vz*vz).mean(1).reshape(vx.shape[:2])
            elif kind=='covariance':
                model=LedoitWolf().fit(tz);center=vz-model.location_;ss=np.einsum('ij,jk,ik->i',center,model.precision_,center).reshape(vx.shape[:2])/d
                params.update(precision=model.precision_.tolist(),location=model.location_.tolist(),shrinkage=float(model.shrinkage_))
            else:
                model=KMeans(n_clusters=4,random_state=7,n_init=10).fit(tz);ss=(model.transform(vz)**2).min(1).reshape(vx.shape[:2])/d
                params['centers']=model.cluster_centers_.tolist()
            for pooling in protocol['pooling']:
                s=pool(ss,pooling);t=normal_threshold(s[normal]);row=metrics(y,s,t);name=rep+'-'+kind+'-'+pooling
                row.update(name=name,scores=s.tolist(),detected_records=[r['name'] for r,pred in zip(records,s>t) if pred],
                  rescued_abnormal_records=[r['name'] for i,r in enumerate(records) if y[i] and not basepred[i] and s[i]>t],
                  lost_abnormal_records=[r['name'] for i,r in enumerate(records) if y[i] and basepred[i] and not s[i]>t])
                rows.append(row);score_arrays[name]=ss;print(name,round(row['auc'],4),round(row['recall'],4),flush=True)
            dump(out/(rep+'-'+kind+'-parameters.json'),params)
    best=max(rows,key=lambda r:(round(r['recall'],12),round(r['auc'],12)))
    diag['pooling_baseline']=[r for r in rows if r['name'].startswith('log1p-centroid-')]
    for group,mask in [('normal',normal),('detected_abnormal',(y==1)&basepred),('missed_abnormal',(y==1)&~basepred)]:
        diag[group]={'count':int(mask.sum()),'median_score':float(np.median(baseline[mask].mean(1))),
          'median_peak_to_mean':float(np.median(baseline[mask].max(1)/np.maximum(baseline[mask].mean(1),1e-12)))}
    # Threshold sensitivity: only normal calibration records resampled; candidate selection NOT re-run.
    rng=np.random.default_rng(71);scores=np.array(best['scores']);fprs=[];recalls=[];ths=[]
    for _ in range(1000):
        threshold=normal_threshold(rng.choice(scores[normal],size=40,replace=True));ths.append(threshold)
        fprs.append(float(np.mean(scores[normal]>threshold)));recalls.append(float(np.mean(scores[~normal]>threshold)))
    result=dict(selected=best,candidates=rows,diagnostics=diag,records=records,test_opened=False,
      quality_gate_passed=best['auc']>=.8 and best['recall']>=.5 and best['fpr']<=.05,
      threshold_resampling={'meaning':'sensitivity only, not independent confidence interval; same validation reused',
      'threshold_5_50_95':np.percentile(ths,[5,50,95]).tolist(),'fpr_5_50_95':np.percentile(fprs,[5,50,95]).tolist(),'recall_5_50_95':np.percentile(recalls,[5,50,95]).tolist()})
    dump(out/'validation.json',result);np.savez_compressed(out/'scores.npz',baseline=baseline,selected=score_arrays[best['name']])
    dump(out/'receipt.json',{'sha256':{str(p.relative_to(ROOT)):sha(p) for p in out.iterdir() if p.is_file()},'test_opened':False})
    print('BEST',best['name'],best['auc'],best['recall'],'gate',result['quality_gate_passed'])
if __name__=='__main__':main()
