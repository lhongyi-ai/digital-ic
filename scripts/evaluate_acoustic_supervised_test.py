#!/usr/bin/env python3
"""Freeze primary and hardware-friendly companion before one-shot test access."""
import json
from pathlib import Path
import numpy as np
import joblib
from train_acoustic_supervised import feature
from experiment_acoustic_v2 import sha,dump
from diagnose_acoustic_v3 import metrics
ROOT=Path(__file__).resolve().parents[1]
def main():
    out=ROOT/'artifacts/acoustic-v7-supervised-r2'
    audit=json.loads((out/'goal-audit.json').read_text());assert audit['high_standard_passed']
    r=json.loads((out/'validation.json').read_text());receipt=json.loads((out/'receipt.json').read_text());protocol=json.loads((out/'protocol.json').read_text())
    for rel,h in receipt['sha256'].items():assert sha(ROOT/rel)==h
    for rel,h in protocol['source_sha256'].items():assert sha(ROOT/rel)==h
    models=[r['selected']['name'],'spectrum1024-linear'];assert len(set(models))==2
    thresholds={n:next(v['threshold'] for v in r['candidates'] if v['name']==n) for n in models}
    files={**receipt['sha256'],**protocol['source_sha256']}
    for p in [out/'receipt.json',out/'goal-audit.json',ROOT/'data/mimii/plan.json',ROOT/'data/mimii-supervised/plan.json',Path(__file__).resolve()]:files[str(p.relative_to(ROOT))]=sha(p)
    with (out/'frozen.json').open('x') as f:json.dump({'models':models,'primary':models[0],'companion':'spectrum1024-linear','thresholds':thresholds,'sha256':files,'test_requirement':{'recall':.9,'max_fpr':.05,'auc':.9}},f,indent=2);f.write('\n')
    # Write attempt before opening any held-out PCM. A failed attempt is retained.
    with (out/'test-attempt.json').open('x') as f:json.dump({'freeze_sha256':sha(out/'frozen.json'),'started':True},f)
    pp=ROOT/'data/mimii/plan.json';plan=json.loads(pp.read_text());rows=[r for r in plan['records'] if r['split']=='test'];x=[];bindings={}
    for r in rows:
        p=ROOT/'data/mimii'/r['local'];m=json.loads(p.with_suffix('.json').read_text());h=sha(p)
        assert h==m['npy_sha256'] and m['plan_sha256']==sha(pp)
        a=np.load(p,allow_pickle=False);x.append(a[:len(a)//1024*1024]);bindings[str(p.relative_to(ROOT))]=h
    x=np.stack(x);y=np.array([r['label'] for r in rows]);assert (y==1).sum()==50 and (y==0).sum()==40
    feats=feature(x,'spectrum1024');results=[]
    for name in models:
        net=joblib.load(out/(name+'.joblib'));s=net.predict_proba(feats)[:,1] if name.endswith('-trees') else net.decision_function(feats)
        result=metrics(y,s,thresholds[name]);pred=s>thresholds[name]
        manual_auc=float(((s[y==1,None]>s[y==0]).sum()+.5*(s[y==1,None]==s[y==0]).sum())/(50*40))
        assert abs(manual_auc-result['auc'])<1e-12
        result.update(name=name,high_standard_passed=result['recall']>=.9 and result['fpr']<=.05 and result['auc']>=.9,
          predictions=[{'name':row['name'],'label':int(label),'score':float(score),'predicted_abnormal':bool(p)} for row,label,score,p in zip(rows,y,s,pred)])
        results.append(result)
    dump(out/'test.json',{'freeze_sha256':sha(out/'frozen.json'),'pcm_sha256':bindings,'results':results,'test_records':len(rows),'thresholds_unchanged':True,'task':'supervised known-fault recognition'})
    print(json.dumps([{k:v for k,v in r.items() if k!='predictions'} for r in results],indent=2))
if __name__=='__main__':main()
