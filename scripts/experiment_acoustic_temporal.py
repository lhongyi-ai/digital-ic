#!/usr/bin/env python3
"""Fixed high gate before evaluating temporal features. Never accesses test PCM."""
from pathlib import Path
import json
import numpy as np
from sklearn.covariance import LedoitWolf
from experiment_acoustic_v2 import load,sha,dump
from diagnose_acoustic_v3 import metrics
from vibfpga.acoustic_experiment import normal_threshold
from vibfpga.acoustic_temporal import temporal_features
ROOT=Path(__file__).resolve().parents[1]
def main():
    out=ROOT/'artifacts/acoustic-v4-temporal';out.mkdir(exist_ok=False)
    sources=[Path(__file__).resolve(),ROOT/'src/vibfpga/acoustic_temporal.py',ROOT/'scripts/experiment_acoustic_v2.py',ROOT/'scripts/diagnose_acoustic_v3.py',ROOT/'src/vibfpga/acoustic_experiment.py',ROOT/'src/vibfpga/fixed.py']
    pp=ROOT/'data/mimii/plan.json';plan=json.loads(pp.read_text())
    protocol={'gate':{'min_validation_detected_of_30':27,'max_validation_false_alarms_of_40':2,'min_auc':.90},
      'test_requirement':'freeze all processing/thresholds before single test evaluation; test recall >=90%, FPR <=5%, AUC >=0.90; no guarantee from validation',
      'blocks':[64,128,256],'durations_seconds':[.512,1.024,2.048],'envelope_rate_hz':125,'stride_seconds':.512,
      'feature_sets':['static','modulation','impact','flux','combined'],'models':['diagonal','covariance'],'pooling':'mean segment scores, strict threshold',
      'candidate_count':30,'normalization':'normal training only','test_opened':False,'plan_sha256':sha(pp),
      'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sources}}
    dump(out/'protocol.json',protocol)
    ti,tr,th=load('train',plan,sha(pp));vi,va,vh=load('validation',plan,sha(pp));tr=tr.reshape(len(tr),-1);va=va.reshape(len(va),-1)
    y=np.array([r['label'] for r in vi]);normal=y==0;rows=[]
    for block in protocol['blocks']:
        train=temporal_features(tr,block);valid=temporal_features(va,block)
        for family in protocol['feature_sets']:
            tf=train[family].reshape(-1,train[family].shape[-1]);vf=valid[family];d=tf.shape[-1]
            mu=tf.mean(0);std=np.maximum(tf.std(0),1e-6);tz=(tf-mu)/std;vz=(vf-mu)/std
            for model in protocol['models']:
                params={'family':family,'block':block,'mean':mu.tolist(),'std':std.tolist(),'model':model}
                if model=='diagonal':ss=(vz*vz).mean(2)
                else:
                    m=LedoitWolf().fit(tz);v=vz-m.location_;ss=np.einsum('rti,ij,rtj->rt',v,m.precision_,v)/d
                    params.update(location=m.location_.tolist(),precision=m.precision_.tolist(),shrinkage=float(m.shrinkage_))
                scores=ss.mean(1);t=normal_threshold(scores[normal]);r=metrics(y,scores,t)
                name=f'{family}-{block}-{model}';r.update(name=name,dimension=d,segment_seconds=block*.008,segments_per_clip=ss.shape[1],scores=scores.tolist(),
                   scoring_multiplications_per_segment=d if model=='diagonal' else d*d,
                   feature_history_float32_bytes=block*16*4)
                rows.append(r);dump(out/(name+'-model.json'),params);np.save(out/(name+'-scores.npy'),ss)
                print(name,round(r['auc'],4),round(r['recall'],4),flush=True)
    best=max(rows,key=lambda r:(round(r['recall'],12),round(r['auc'],12),-r['dimension']))
    gate=best['confusion_matrix'][1][1]>=27 and best['confusion_matrix'][0][1]<=2 and best['auc']>=.9
    dump(out/'validation.json',{'selected':best,'candidates':rows,'high_standard_passed':gate,'test_opened':False,
      'records':[{'name':r['name'],'label':r['label']} for r in vi],
      'limitations':'normal-only training; same heavily reused validation set; clip pooling is not a streaming alarm; envelope Nyquist 62.5Hz; no claims for faster impact repetition'})
    dump(out/'receipt.json',{'sha256':{str(p.relative_to(ROOT)):sha(p) for p in out.iterdir() if p.is_file()},'pcm_sha256':th|vh,'test_opened':False})
    print('BEST',best['name'],best['recall'],best['auc'],'HIGH_GATE',gate)
if __name__=='__main__':main()
