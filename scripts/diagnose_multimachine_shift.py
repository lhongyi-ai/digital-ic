#!/usr/bin/env python3
"""Development-only same-machine controls and machine-identity diagnostic."""
from pathlib import Path
import json
import numpy as np
import joblib
from train_multimachine import make_model,scores,transform
from experiment_acoustic_v2 import sha,dump
from audit_multimachine import manual_metrics
from vibfpga.multimachine import stable_order,source_threshold
from diagnose_acoustic_v3 import metrics
ROOT=Path(__file__).resolve().parents[1]
def main():
    out=ROOT/'artifacts/acoustic-machine-shift-v1';out.mkdir(exist_ok=False)
    a=ROOT/'artifacts/acoustic-multimachine-v1';b=ROOT/'artifacts/acoustic-multimachine-temporal-v1'
    frozen=json.loads((a/'frozen.json').read_text());binding=json.loads((b/'bindings.json').read_text())
    assert all(sha(ROOT/p)==h for p,h in frozen['sha256'].items())
    assert all(sha(ROOT/p)==h for p,h in {**binding['sha256'],**binding['source_sha256']}.items())
    plan=json.loads((ROOT/'data/mimii-multimachine/plan.json').read_text());rows=[r for r in plan['records'] if r['machine'] in ('00','02','04')]
    y=np.array([r['label'] for r in rows]);m=np.array([r['machine'] for r in rows])
    partitions={}
    for machine in ('00','02','04'):
        fit=[];cal=[]
        for label in (0,1):
            idx=sorted([i for i,r in enumerate(rows) if r['machine']==machine and r['role']=='fit' and r['label']==label],key=lambda i:stable_order(rows[i]['name']))
            fit+=idx[:96]
            if label==0:cal+=idx[96:]
        val=[i for i,r in enumerate(rows) if r['machine']==machine and r['role']=='calibration']
        assert len(fit)==192 and len(cal)==32 and len(val)==64
        assert not(set(fit)&set(cal) or set(fit)&set(val) or set(cal)&set(val))
        partitions[machine]={'fit':fit,'cal':cal,'val':val}
    protocol={'scope':'development diagnostics only, not cross-machine success','partitions':partitions,'test_opened':False,'source_sha256':sha(Path(__file__)),
      'feature_bindings':{str(p.relative_to(ROOT)):sha(p) for p in [a/'development-spectra.npy',b/'temporal.npy',b/'combined.npy']}}
    dump(out/'protocol.json',protocol)
    features={'spectrum':transform(np.load(a/'development-spectra.npy'),'shape'),'temporal':np.load(b/'temporal.npy'),'combined':np.load(b/'combined.npy')};results=[];identity=[]
    for feature,x in features.items():
        for kind in ('linear_1','trees'):
            for machine,part in partitions.items():
                fit,cal,val=(np.array(part[k]) for k in ('fit','cal','val'))
                net=make_model(kind);net.fit(x[fit],y[fit]);cs=scores(net,x[cal]);t=source_threshold(cs,y[cal],m[cal]);s=scores(net,x[val]);r=metrics(y[val],s,t);check=manual_metrics(y[val],s,t)
                assert abs(check['auc']-r['auc'])<1e-12 and check['tp']==r['confusion_matrix'][1][1] and check['fp']==r['confusion_matrix'][0][1]
                name=feature+'-'+kind+'-'+machine;joblib.dump(net,out/(name+'.joblib'));np.testing.assert_array_equal(s,scores(joblib.load(out/(name+'.joblib')),x[val]))
                r.update(name=name,machine=machine,feature=feature,model=kind,validation_scores=s.tolist(),calibration_scores=cs.tolist());results.append(r)
                print(name,'AUC',round(r['auc'],4),'TP/FP',check['tp'],check['fp'],flush=True)
        fit=np.array([i for p in partitions.values() for i in p['fit']]);val=np.array([i for p in partitions.values() for i in p['val']])
        net=make_model('linear_1');net.fit(x[fit],m[fit]);pred=net.predict(x[val]);acc=float(np.mean(pred==m[val]))
        joblib.dump(net,out/(feature+'-machine-identity.joblib'));identity.append({'feature':feature,'accuracy':acc,'count':len(val),'correct':int(np.sum(pred==m[val])),'fit_indices':fit.tolist(),'validation_indices':val.tolist(),'predictions':pred.tolist()})
        print('identity',feature,acc,flush=True)
    dump(out/'results.json',{'same_machine':results,'machine_identity':identity,'test_opened':False,'warning':'same-machine diagnostic uses development records only; not an independent final result'})
    dump(out/'bindings.json',{'sha256':{str(p.relative_to(ROOT)):sha(p) for p in out.iterdir() if p.is_file()},'source_sha256':sha(Path(__file__))})
if __name__=='__main__':main()
