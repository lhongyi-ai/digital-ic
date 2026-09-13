#!/usr/bin/env python3
"""One-shot unseen-machine evaluation with frozen model and original threshold."""
from pathlib import Path
import json
import numpy as np
import joblib
from scipy.signal import resample_poly
from train_acoustic_supervised import feature
from diagnose_acoustic_v3 import metrics
from experiment_acoustic_v2 import sha,dump
from vibfpga.recording_audit import lag_screen,refined_correlation
ROOT=Path(__file__).resolve().parents[1]
def main():
    d=ROOT/'data/mimii-external-id02';p=d/'plan.json';plan=json.loads(p.read_text())
    old=ROOT/'artifacts/acoustic-v7-supervised-r2';freeze=json.loads((old/'frozen.json').read_text())
    assert sha(old/'frozen.json')==plan['frozen_model_sha256']
    for rel,h in freeze['sha256'].items():assert sha(ROOT/rel)==h
    out=ROOT/'artifacts/acoustic-external-id02';out.mkdir(exist_ok=False)
    dump(out/'attempt.json',{'freeze_sha256':sha(old/'frozen.json'),'plan_sha256':sha(p),'started':True,'threshold':freeze['thresholds'][freeze['primary']]})
    original_names=set();original=[];original_records=[];original_hashes={}
    for dirname in ['mimii','mimii-supervised']:
        dd=ROOT/'data'/dirname;pp=dd/'plan.json';base=json.loads(pp.read_text())
        for r in base['records']:
            original_names.add(r['name']);path=dd/r['local'];meta=json.loads(path.with_suffix('.json').read_text());h=sha(path)
            assert h==meta['npy_sha256'] and meta['plan_sha256']==sha(pp)
            original.append(np.load(path,allow_pickle=False));original_records.append({'name':r['name'],'split':r['split']});original_hashes[str(path.relative_to(ROOT))]=h
    pcm=[];bindings={}
    for r in plan['records']:
        assert r['name'] not in original_names and r['name'].startswith('fan/id_02/')
        path=d/r['local'];meta=json.loads(path.with_suffix('.json').read_text());h=sha(path)
        assert h==meta['npy_sha256'] and meta['plan_sha256']==sha(p)
        pcm.append(np.load(path,allow_pickle=False));bindings[str(path.relative_to(ROOT))]=h
    # File/PCM equality and shifted correlation against all old splits, auditing only.
    import hashlib
    raw_hash=lambda x:hashlib.sha256(x.tobytes()).hexdigest()
    old_hash={raw_hash(x):i for i,x in enumerate(original)}
    exact=[{'new':j,'existing':old_hash[raw_hash(x)]} for j,x in enumerate(pcm) if raw_hash(x) in old_hash]
    low=np.stack([resample_poly(x.astype(float),1,32) for x in original+pcm])
    pairs=lag_screen(low,['existing']*len(original)+['new']*len(pcm),1000);pairs.sort(key=lambda r:-abs(r[2]));candidates=[r for r in pairs if abs(r[2])>=.8]
    selected=pairs[:max(20,min(100,len(candidates)))];near=[];verified=[]
    for i,j,c,lag,length in selected:
        val,l,n=refined_correlation(original[i],pcm[j-len(original)],lag*32,32)
        r={'existing':i,'new':j-len(original),'screen_correlation':c,'raw_correlation':val,'lag_samples':l,'overlap_seconds':n/16000};verified.append(r)
        if abs(val)>=.98:near.append(r)
    dump(out/'independence-audit.json',{'existing_records':original_records,'new_records':[{'name':r['name'],'label':r['label']} for r in plan['records']],
      'pairs_screened':len(pairs),'screen_candidates':len(candidates),'exact_matches':exact,'raw_verified':verified,'confirmed_near_matches':near,
      'unconfirmed_screen_candidates':max(0,len(candidates)-len(selected)),'limitations':'same bounded screen as original audit, no per-record noise source or session metadata'})
    x=np.stack([a[:len(a)//1024*1024] for a in pcm]);y=np.array([r['label'] for r in plan['records']]);assert (y==0).sum()==40 and (y==1).sum()==30
    net=joblib.load(old/(freeze['primary']+'.joblib'));s=net.predict_proba(feature(x,'spectrum1024'))[:,1];threshold=freeze['thresholds'][freeze['primary']]
    result=metrics(y,s,threshold);manual=float(((s[y==1,None]>s[y==0]).sum()+.5*(s[y==1,None]==s[y==0]).sum())/(30*40));assert abs(manual-result['auc'])<1e-12
    result.update(model=freeze['primary'],machine='fan/id_02',snr_db=0,threshold_unchanged=True,retrained=False,
      high_standard_passed=result['recall']>=.9 and result['fpr']<=.05 and result['auc']>=.9,
      predictions=[{'name':r['name'],'label':int(label),'score':float(score),'predicted_abnormal':bool(score>threshold)} for r,label,score in zip(plan['records'],y,s)])
    dump(out/'results.json',result)
    sources=[Path(__file__).resolve(),ROOT/'src/vibfpga/recording_audit.py',ROOT/'scripts/train_acoustic_supervised.py',ROOT/'scripts/diagnose_acoustic_v3.py',ROOT/'scripts/experiment_acoustic_v2.py',ROOT/'scripts/experiment_acoustic_finespectrum.py']
    dump(out/'receipt.json',{'sha256':{str(q.relative_to(ROOT)):sha(q) for q in [*out.iterdir(),p,*sources] if q.is_file()},'new_pcm_sha256':bindings,'old_pcm_sha256':original_hashes,'freeze_sha256':sha(old/'frozen.json')})
    print(json.dumps({k:v for k,v in result.items() if k!='predictions'},indent=2))
if __name__=='__main__':main()
