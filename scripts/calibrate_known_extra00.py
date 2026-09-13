#!/usr/bin/env python3
"""Recalibrate two saved linear models; no new fitting or final-test access."""
import json,math
from pathlib import Path
import joblib
import numpy as np
from sklearn.metrics import roc_auc_score
from threadpoolctl import threadpool_limits
from experiment_acoustic_v2 import sha,dump
from experiment_acoustic_finespectrum import spectrum
from experiment_known_machine_local import measure
ROOT=Path(__file__).resolve().parents[1]

def main():
    base=ROOT/'data/mimii-known-machines-v1';calbase=ROOT/'data/mimii-known-calibration00-v1'
    audit=json.loads((calbase/'audit.json').read_text());assert audit['passed']
    assert all(sha(ROOT/p)==h for p,h in audit['manifest_sha256'].items())
    new=json.loads((calbase/'development.json').read_text());assert len(new['records'])==128
    old=ROOT/'artifacts/acoustic-known-detail-v1';more=ROOT/'artifacts/acoustic-known-extra00-v1'
    previous=json.loads((old/'results.json').read_text());expanded=json.loads((more/'results.json').read_text())
    assert sha(more/'extra-power.npy')==expanded['extra_power_sha256']
    for folder,script in [(old,'experiment_known_spectral_detail.py'),(more,'train_known_extra00.py')]:
        p=json.loads((folder/'protocol.json').read_text())
        assert p['source_sha256']==sha(ROOT/'scripts'/script) and p['plan_sha256']==sha(base/'plan.json')
    rows=previous['records'];y=np.array([r['label'] for r in rows]);ms=np.array([r['machine'] for r in rows])
    out=ROOT/'artifacts/acoustic-known-calibration00-v2';out.mkdir(exist_ok=False)
    dump(out/'protocol.json',dict(source_sha256=sha(Path(__file__)),baseline_sha256=sha(old/'results.json'),expanded_sha256=sha(more/'results.json'),
        calibration_manifest_sha256=sha(calbase/'development.json'),calibration_audit_sha256=sha(calbase/'audit.json'),
        selection='compare original saved full512 linear and added-fit saved full512 linear; no refitting',
        threshold='ID00:original32+new128 normal calibration, alpha=.04 fixed, ceil161*.96=155; other IDs:32, rank32; strict >',
        overall_auc='mean fold AUC of calibrated score minus per-ID threshold; also raw logit AUC reported',
        scope='development only, all four installed IDs evaluated; no quantization or final audio',final_test_opened=False))
    powers=[]
    for r in new['records']:
        path=ROOT/r['local'];assert sha(path)==r['npy_sha256'];x=np.load(path,allow_pickle=False)
        powers.append(spectrum(x[None,:159744],1024)[0])
    pcal=np.stack(powers);np.save(out/'calibration-power.npy',pcal);features=np.log2(np.maximum(pcal,1e-12))
    original_power=np.load(ROOT/'artifacts/acoustic-known-machines-v1/development-power.npy',allow_pickle=False)
    added_power=np.load(more/'extra-power.npy',allow_pickle=False)
    outcomes={};checks=0
    for variant in ('original_fit','expanded_fit'):
        result=[];pred=np.zeros(len(rows),bool);sall=np.full(len(rows),np.nan);margins=sall.copy();votes=np.zeros(len(rows),int)
        for f in [f for f in previous['folds'] if f['model']=='full512']:
            m=f['machine'];fold=f['fold']
            if m=='00' and variant=='expanded_fit':
                f=next(v for v in expanded['folds'] if v['fold']==fold);path=more/f'linear-id00-fold{fold}.joblib'
                power=np.concatenate([original_power,added_power])
            else:
                path=old/f'full512-id{m}-fold{fold}.joblib';power=original_power
            assert sha(path)==f['model_sha256'];model=joblib.load(path)
            fit=np.array(f['fit_indices']);raw=np.log2(np.maximum(power,1e-12))
            np.testing.assert_allclose(raw[fit].mean(0),f['mean'],rtol=0,atol=1e-12)
            np.testing.assert_allclose(np.maximum(raw[fit].std(0),1e-6),f['std'],rtol=0,atol=1e-12)
            values=((raw-f['mean'])/f['std']).astype(np.float32)
            if not (m=='00' and variant=='expanded_fit'):values=np.asfortranarray(values)
            reproduced=model.decision_function(values)
            val=np.array(f['validation_indices']);cal=np.array(f['calibration_indices']);vs=np.array(f['validation_scores']);cs=np.array(f['calibration_scores'])
            np.testing.assert_allclose(reproduced[val],vs,rtol=0,atol=1e-10)
            np.testing.assert_allclose(reproduced[cal],cs,rtol=0,atol=1e-10)
            normals=cs[y[cal]==0]
            new_values=((features-f['mean'])/f['std']).astype(np.float32)
            if not (m=='00' and variant=='expanded_fit'):new_values=np.asfortranarray(new_values)
            new_scores=model.decision_function(new_values) if m=='00' else np.array([])
            normals=np.r_[normals,new_scores];rank=math.ceil((len(normals)+1)*.96);assert rank<=len(normals)
            limit=float(np.sort(normals)[rank-1]);r=measure(y[val],vs,limit)
            r.update(machine=m,fold=fold,threshold=limit,calibration_count=len(normals),rank=rank,original_normal_scores=cs[y[cal]==0].tolist(),
                extra_normal_scores=new_scores.tolist(),model_path=str(path.relative_to(ROOT)),model_sha256=sha(path),
                validation_indices=val.tolist(),validation_scores=vs.tolist())
            pred[val]=vs>limit;sall[val]=vs;margins[val]=vs-limit;votes[val]+=1;result.append(r);checks+=1
        assert all(votes[i]==int(row['role']=='cv') for i,row in enumerate(rows))
        groups={}
        for m in ('00','02','04','06','pooled'):
            mask=(votes==1)&(True if m=='pooled' else ms==m);tp=int(pred[mask&(y==1)].sum());fp=int(pred[mask&(y==0)].sum())
            normal=int((mask&(y==0)).sum());abnormal=int((mask&(y==1)).sum())
            if m=='pooled':
                sets=[np.array([i for i,row in enumerate(rows) if row['role']=='cv' and row['fold']==fold]) for fold in range(3)]
                auc=float(np.mean([roc_auc_score(y[v],margins[v]) for v in sets]));raw_auc=float(np.mean([roc_auc_score(y[v],sall[v]) for v in sets]))
            else:auc=float(np.mean([r['auc'] for r in result if r['machine']==m]));raw_auc=auc
            g=dict(tp=tp,fp=fp,normal=normal,abnormal=abnormal,recall=tp/abnormal,fpr=fp/normal,auc=auc,raw_logit_auc=raw_auc)
            g['passed']=g['recall']>.9 and g['fpr']<.05 and g['auc']>=.9;groups[m]=g
        outcomes[variant]=dict(folds=result,groups=groups,passed=all(g['passed'] for g in groups.values()))
    dump(out/'results.json',dict(outcomes=outcomes,records=rows,final_test_opened=False,calibration_power_sha256=sha(out/'calibration-power.npy')))
    dump(out/'audit.json',dict(passed=True,model_reconstruction_checks=checks,results_sha256=sha(out/'results.json'),protocol_sha256=sha(out/'protocol.json'),
         extra_calibration_sha256=sha(out/'calibration-power.npy'),source_sha256=sha(Path(__file__)),note='model reload/fit normalization checked; separate outcome audit still required',final_audio_read=False))
    print('SUMMARY',json.dumps({k:dict(groups=v['groups'],passed=v['passed']) for k,v in outcomes.items()}),flush=True)
if __name__=='__main__':
    with threadpool_limits(limits=2):main()
