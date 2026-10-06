#!/usr/bin/env python3
"""Refit selected per-ID linear models and export deterministic deployment constants."""
import json,math
from pathlib import Path
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from threadpoolctl import threadpool_limits
from vibfpga.known_fixed import quantized_features,tables
from experiment_acoustic_v2 import sha,dump
ROOT=Path(__file__).resolve().parents[1]

def hexfile(path,values,bits):
    path.write_text(''.join(f'{int(v)&((1<<bits)-1):0{(bits+3)//4}x}\n' for v in values))

def main():
    evidence=ROOT/'artifacts/acoustic-known-integer-pipeline-v2';audit=json.loads((evidence/'audit.json').read_text())
    assert audit['passed'] and audit['results_sha256']==sha(evidence/'results.json')
    dsp=ROOT/'artifacts/acoustic-known-integer-dsp-v2';receipt=json.loads((dsp/'receipt.json').read_text())
    assert receipt['source_sha256']==sha(ROOT/'src/vibfpga/known_fixed.py') and receipt['log_sha256']==sha(dsp/'log-q12.npy')
    rows=receipt['rows'];assert len(rows)==1152 and all(r['role']!='final_test' for r in rows)
    base=ROOT/'data/mimii-known-machines-v1';assert sha(base/'plan.json')==json.loads((base/'freeze.json').read_text())['plan_sha256']
    raw=np.log2(np.maximum(np.load(ROOT/'artifacts/acoustic-known-machines-v1/development-power.npy'),1e-12))
    qlog=np.load(dsp/'log-q12.npy');out=ROOT/'artifacts/acoustic-known-release-v1';out.mkdir(exist_ok=False)
    dump(out/'protocol.json',dict(source_sha256=sha(Path(__file__)),fixed_source_sha256=sha(ROOT/'src/vibfpga/known_fixed.py'),
        development_audit_sha256=sha(evidence/'audit.json'),dsp_receipt_sha256=sha(dsp/'receipt.json'),plan_sha256=sha(base/'plan.json'),
        selection='original_fit full512 per-ID L2 logistic C1; all192 CV records per ID; extra fit256 excluded',
        threshold='normal calibration only alpha=.04; ID00 n160 rank155, others n32 rank32; integer scores',
        stage='final model constants, NOT final-test authorization until RTL/implementation freeze',final_test_opened=False))
    models={}
    for m in ('00','02','04','06'):
        fit=np.array([i for i,r in enumerate(rows[:1024]) if r['machine']==m and r['role']=='cv'])
        cal=np.array([i for i,r in enumerate(rows) if r['machine']==m and r['role'] in ('calibration','calibration_extra') and r['label']==0])
        assert len(fit)==192 and len(cal)==(160 if m=='00' else 32) and not set(fit)&set(cal)
        mean=raw[fit].mean(0);std=np.maximum(raw[fit].std(0),1e-6);z=((raw-mean)/std).astype(np.float32)
        model=LogisticRegression(C=1,max_iter=3000,random_state=71).fit(z[fit],np.array([rows[i]['label'] for i in fit]))
        sx=max(float(np.abs(z[fit]).max())/127,1e-12);sw=max(float(np.abs(model.coef_[0]).max())/127,1e-12)
        qw=np.clip(np.rint(model.coef_[0]/sw),-127,127).astype(np.int64);qb=int(np.rint(float(model.intercept_[0])/(sx*sw)))
        qx,mq,gq=quantized_features(qlog,mean,sx,std);scores=qx.astype(np.int64)@qw+qb
        assert np.abs(scores).max()<2**31 and abs(qb)+512*127*127<2**31
        threshold=int(np.sort(scores[cal])[math.ceil((len(cal)+1)*.96)-1])
        directory=out/f'id{m}';directory.mkdir();joblib.dump(model,directory/'float.joblib')
        np.testing.assert_array_equal(model.decision_function(z),joblib.load(directory/'float.joblib').decision_function(z))
        constants=dict(machine=m,n=1024,windows=156,features=512,input_scale=sx,weight_scale=sw,
            weights=qw.tolist(),bias=qb,threshold=threshold,mean_q12=mq.tolist(),gain_q24=gq.tolist(),mean=mean.tolist(),std=std.tolist(),
            train_indices=fit.tolist(),calibration_indices=cal.tolist(),calibration_scores=scores[cal].tolist(),
            log_constant_q12=round((24+np.log2(156))*4096),log_floor_q12=round(np.log2(1e-12)*4096),
            kind='quantized per-installed-machine supervised linear classifier',final_test_opened=False)
        dump(directory/'model.json',constants)
        for name,values,bits in [('weights',qw,8),('mean_q12',mq,32),('gain_q24',gq,32),
            ('cos_quarter',tables()[0],16),('log_lut',np.rint(np.log2(1+np.arange(1024)/1024)*4096).astype(int),12)]:
            hexfile(directory/(name+'.hex'),values,bits)
        np.save(directory/'development-scores.npy',scores)
        models[m]=dict(model_sha256=sha(directory/'model.json'),train_count=len(fit),calibration_count=len(cal),
                       bias=qb,threshold=threshold,max_gain=int(gq.max()),max_mean=int(np.abs(mq).max()))
        print(m,'fit192','cal',len(cal),'threshold',threshold,flush=True)
    dump(out/'model-freeze.json',dict(models=models,sha256={str(p.relative_to(ROOT)):sha(p) for p in out.rglob('*') if p.is_file()},
        meaning='weights/parameters frozen only; final test remains locked pending RTL validation',final_test_opened=False))
    print('FROZEN MODEL CONSTANTS; no final-test scores computed',flush=True)
if __name__=='__main__':
    with threadpool_limits(limits=2):main()
