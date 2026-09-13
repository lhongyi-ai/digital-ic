#!/usr/bin/env python3
"""Frozen official AudioSet embeddings; source-only downstream classifiers."""
from pathlib import Path
import sys,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'external/EfficientAT'))
import numpy as np
import torch,torchaudio,joblib
import models.mn.model as official
from models.preprocess import AugmentMelSTFT
from train_multimachine import make_model,scores
from vibfpga.multimachine import folds,source_threshold,violation
from experiment_acoustic_v2 import sha,dump
from diagnose_acoustic_v3 import metrics
from audit_multimachine import manual_metrics

def main():
    torch.set_num_threads(2);torch.manual_seed(57);torch.use_deterministic_algorithms(True)
    out=ROOT/'artifacts/acoustic-pretrained-v1';out.mkdir(exist_ok=False)
    pp=ROOT/'data/mimii-multimachine/plan.json';plan=json.loads(pp.read_text());base=ROOT/'artifacts/acoustic-multimachine-v1';binding=json.loads((base/'frozen.json').read_text());assert sha(pp)==binding['plan_sha256'];assert all(sha(ROOT/p)==h for p,h in binding['sha256'].items())
    rows=[r for r in plan['records'] if r['machine'] in ('00','02','04')];assert len(rows)==960
    vendor = ROOT/'external/EfficientAT'
    if (vendor/'.git').exists():
        commit = subprocess.check_output(['git','rev-parse','HEAD'], cwd=vendor, text=True).strip()
    else:
        commit = json.loads((ROOT/'external/EfficientAT.snapshot.json').read_text())['upstream_commit']
    dump(out/'protocol.json',{'plan_sha256':sha(pp),'upstream_commit':commit,'upstream':'https://github.com/fschmid56/EfficientAT','pretraining':'AudioSet according to upstream; not fine-tuned on MIMII','checkpoint':'mn10_as','downstream':['linear_01','linear_1','rbf_10'],'threshold':'source normal calibration max; held machine excluded','test_opened':False,'sample_rate':'16 kHz resampled to official 32 kHz; does not recover lost high frequencies','source_sha256':sha(Path(__file__)),'torch':torch.__version__,'torchaudio':torchaudio.__version__})
    official.model_dir=str(ROOT/'external/EfficientAT/resources')
    model=official.get_model(width_mult=1.0,pretrained_name='mn10_as').eval();mel=AugmentMelSTFT(n_mels=128,sr=32000,win_length=800,hopsize=320).eval();features=[]
    with torch.inference_mode():
        for start in range(0,len(rows),4):
            batch=[]
            for r in rows[start:start+4]:
                p=ROOT/r['local'];assert sha(p)==binding['pcm_sha256'][r['local']];wave=np.load(p);assert wave.shape==(160000,) and wave.dtype==np.int16;batch.append(wave.astype(np.float32)/32768)
            wave=torchaudio.functional.resample(torch.from_numpy(np.stack(batch)),16000,32000)
            _,embedding=model(mel(wave).unsqueeze(1));features.append(embedding.numpy().copy())
            if (start+4)%120==0:print('embedded',start+4,flush=True)
    x=np.concatenate(features);assert x.shape[0]==960 and np.isfinite(x).all();np.save(out/'embeddings.npy',x)
    y=np.array([r['label'] for r in rows]);m=np.array([r['machine'] for r in rows]);results=[]
    for kind in ('linear_01','linear_1','rbf_10'):
        rr=[]
        for held,fit,cal,val in folds(rows):
            net=make_model(kind);net.fit(x[fit],y[fit]);cs=scores(net,x[cal]);t=source_threshold(cs,y[cal],m[cal]);vs=scores(net,x[val]);r=metrics(y[val],vs,t);k=manual_metrics(y[val],vs,t);assert abs(k['auc']-r['auc'])<1e-12 and k['tp']==r['confusion_matrix'][1][1] and k['fp']==r['confusion_matrix'][0][1]
            path=out/(kind+'-'+held+'.joblib');joblib.dump(net,path);np.testing.assert_array_equal(vs,scores(joblib.load(path),x[val]));r.update(machine=held,fit_indices=fit.tolist(),calibration_indices=cal.tolist(),validation_indices=val.tolist(),calibration_scores=cs.tolist(),validation_scores=vs.tolist(),gate_passed=r['recall']>.9 and r['fpr']<.05 and r['auc']>=.9);rr.append(r);print(kind,held,'AUC',round(r['auc'],4),'TP/FP',k['tp'],k['fp'],flush=True)
        c={'name':kind,'folds':rr,'all_passed':all(r['gate_passed'] for r in rr),'max_violation':max(violation(r) for r in rr)};results.append(c);dump(out/(kind+'.json'),c)
    dump(out/'results.json',{'candidates':results,'all_passed':any(c['all_passed'] for c in results),'test_opened':False,'embedding_shape':x.shape})
    sources=list((ROOT/'external/EfficientAT/models').rglob('*.py'))+list((ROOT/'external/EfficientAT/helpers').rglob('*.py'))+list((ROOT/'external/EfficientAT/resources').glob('mn10_as*.pt'))+[Path(__file__).resolve()]
    dump(out/'bindings.json',{'sha256':{str(p.relative_to(ROOT)):sha(p) for p in list(out.iterdir())+sources if p.is_file()}})
if __name__=='__main__':main()
