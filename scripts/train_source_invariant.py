#!/usr/bin/env python3
"""Remove source-normal nuisance subspaces; never fit on held-machine data."""
from pathlib import Path
import json
import numpy as np
import joblib
from sklearn.decomposition import PCA
from train_multimachine import make_model,scores,transform
from vibfpga.multimachine import folds,source_threshold,violation
from experiment_acoustic_v2 import sha,dump
from diagnose_acoustic_v3 import metrics
from audit_multimachine import manual_metrics
ROOT=Path(__file__).resolve().parents[1]
def nuisance(x,y,m,kind):
    normal=x[y==0];mean=normal.mean(0)
    if kind=='centroid':
        direction=normal[m[y==0]==sorted(set(m))[0]].mean(0)-normal[m[y==0]==sorted(set(m))[1]].mean(0)
        basis=(direction/max(np.linalg.norm(direction),1e-20))[None,:]
    else:basis=PCA(n_components=int(kind[2:]),svd_solver='full').fit(normal).components_
    return mean,basis

def project(x,mean,basis):
    z=x-mean
    return z-(z@basis.T)@basis

def main():
    out=ROOT/'artifacts/acoustic-source-invariant-v1';out.mkdir(exist_ok=False)
    folder=ROOT/'artifacts/acoustic-multimachine-v1';f=json.loads((folder/'frozen.json').read_text())
    assert all(sha(ROOT/p)==h for p,h in f['sha256'].items())
    plan=json.loads((ROOT/'data/mimii-multimachine/plan.json').read_text());rows=[r for r in plan['records'] if r['machine'] in ('00','02','04')]
    x=transform(np.load(folder/'development-spectra.npy'),'shape');y=np.array([r['label'] for r in rows]);m=np.array([r['machine'] for r in rows])
    protocol={'source_sha256':sha(Path(__file__)),'base_binding':sha(folder/'frozen.json'),'kinds':['centroid','pc4','pc16'],'models':['linear_01','linear_1','rbf_10'],
      'nuisance_fit':'source fit-role normal recordings ONLY; held machine never used','threshold':'source normal calibration only, max across sources',
      'gate':'each held machine recall > .9, fpr < .05, auc >= .9','test_opened':False}
    dump(out/'protocol.json',protocol);results=[]
    for kind in protocol['kinds']:
        for modelkind in protocol['models']:
            name=kind+'-'+modelkind;rr=[]
            for held,fit,cal,val in folds(rows):
                mean,basis=nuisance(x[fit],y[fit],m[fit],kind)
                np.testing.assert_allclose(basis@basis.T,np.eye(len(basis)),atol=1e-10)
                xx=project(x,mean,basis);net=make_model(modelkind);net.fit(xx[fit],y[fit]);cs=scores(net,xx[cal]);t=source_threshold(cs,y[cal],m[cal]);vs=scores(net,xx[val]);r=metrics(y[val],vs,t)
                check=manual_metrics(y[val],vs,t);assert abs(check['auc']-r['auc'])<1e-12 and check['tp']==r['confusion_matrix'][1][1] and check['fp']==r['confusion_matrix'][0][1]
                artifact=out/(name+'-'+held+'.joblib');joblib.dump({'mean':mean,'basis':basis,'model':net},artifact)
                saved=joblib.load(artifact);np.testing.assert_array_equal(vs,scores(saved['model'],project(x[val],saved['mean'],saved['basis'])))
                r.update(machine=held,fit_indices=fit.tolist(),calibration_indices=cal.tolist(),validation_indices=val.tolist(),calibration_scores=cs.tolist(),validation_scores=vs.tolist(),gate_passed=r['recall']>.9 and r['fpr']<.05 and r['auc']>=.9);rr.append(r)
                print(name,held,'AUC',round(r['auc'],4),'TP/FP',check['tp'],check['fp'],flush=True)
            summary={'name':name,'folds':rr,'all_passed':all(r['gate_passed'] for r in rr),'max_violation':max(violation(r) for r in rr),'min_auc':min(r['auc'] for r in rr)};results.append(summary);dump(out/(name+'.json'),summary)
    selected=min(results,key=lambda r:(r['max_violation'],-r['min_auc'],r['name']))
    dump(out/'results.json',{'candidates':results,'selected':selected,'test_opened':False})
    dump(out/'bindings.json',{'sha256':{str(p.relative_to(ROOT)):sha(p) for p in out.iterdir() if p.is_file()},'source_sha256':sha(Path(__file__))})
    print('SELECTED',selected['name'],'ALL PASSED',selected['all_passed'],flush=True)
if __name__=='__main__':main()
