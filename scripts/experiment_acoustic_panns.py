#!/usr/bin/env python3
"""Frozen external AudioSet CNN6 teacher, normal-only anomaly detector."""
import sys,json
from pathlib import Path
import numpy as np
import torch
from scipy.signal import resample_poly
from sklearn.covariance import LedoitWolf
from experiment_acoustic_v2 import load,sha,dump
from diagnose_acoustic_v3 import metrics
from vibfpga.acoustic_experiment import normal_threshold
ROOT=Path(__file__).resolve().parents[1]
def main():
    vendor=ROOT/'third_party/panns';provenance=json.loads((vendor/'source.json').read_text())
    for name,h in provenance['sha256'].items():
        if sha(vendor/name)!=h:raise ValueError('pretrained source mismatch')
    sys.path.insert(0,str(vendor));from models import Cnn6
    out=ROOT/'artifacts/acoustic-v6-panns';out.mkdir(exist_ok=False)
    pp=ROOT/'data/mimii/plan.json';plan=json.loads(pp.read_text())
    checkpoint=vendor/provenance['checkpoint']['key']
    sources=[Path(__file__).resolve(),ROOT/'scripts/experiment_acoustic_v2.py',ROOT/'scripts/diagnose_acoustic_v3.py',ROOT/'src/vibfpga/acoustic_experiment.py',vendor/'source.json']
    dump(out/'protocol.json',{'teacher':'official CNN6 AudioSet pretrained, frozen evaluation; no MIMII fine-tuning','models':['diagonal','nearest5','covariance'],
      'representation':['embedding','unit_embedding'],'candidate_count':6,'gate':{'tp':27,'max_fp':2,'auc':.9},'test_opened':False,
      'resampling':'scipy resample_poly 16k to 32k','input':'signed int16 /32768, original amplitude',
      'checkpoint_sha256':sha(checkpoint),'plan_sha256':sha(pp),
      'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sources},'torch_version':torch.__version__})
    torch.set_num_threads(2)
    net=Cnn6(sample_rate=32000,window_size=1024,hop_size=320,mel_bins=64,fmin=50,fmax=14000,classes_num=527)
    net.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True)['model'],strict=True);net.eval()
    ti,tr,th=load('train',plan,sha(pp));vi,va,vh=load('validation',plan,sha(pp));y=np.array([r['label'] for r in vi]);normal=y==0;features=[]
    for tag,raw in [('train',tr),('validation',va)]:
        raw=raw.reshape(len(raw),-1);emb=[]
        with torch.inference_mode():
            for i in range(0,len(raw),2):
                x=resample_poly(raw[i:i+2].astype(np.float32)/32768,2,1,axis=1).astype(np.float32)
                e=net(torch.from_numpy(x))['embedding'].numpy();emb.append(e)
                if i%20==0:print(tag,i,'/',len(raw),flush=True)
        f=np.concatenate(emb);features.append(f);np.save(out/(tag+'-embeddings.npy'),f)
    rows=[]
    for rep in ['embedding','unit_embedding']:
        t,v=features
        if rep=='unit_embedding':t=t/np.maximum(np.linalg.norm(t,axis=1,keepdims=True),1e-12);v=v/np.maximum(np.linalg.norm(v,axis=1,keepdims=True),1e-12)
        mean=t.mean(0);std=np.maximum(t.std(0),1e-4);t=(t-mean)/std;v=(v-mean)/std;d=t.shape[1]
        cov=LedoitWolf().fit(t);center=v-cov.location_
        distance=np.maximum((v*v).sum(1)[:,None]+(t*t).sum(1)[None,:]-2*v@t.T,0)
        scores={'diagonal':(v*v).mean(1),'nearest5':np.sort(distance,axis=1)[:,:5].mean(1)/d,
          'covariance':np.einsum('ij,jk,ik->i',center,cov.precision_,center)/d}
        np.savez_compressed(out/(rep+'-normal-model.npz'),mean=mean,std=std,training=t,precision=cov.precision_,location=cov.location_)
        for name,s in scores.items():
            r=metrics(y,s,normal_threshold(s[normal]));r.update(name=rep+'-'+name,scores=s.tolist());rows.append(r)
            print(r['name'],r['auc'],r['recall'],flush=True)
    best=max(rows,key=lambda r:(round(r['recall'],12),round(r['auc'],12)))
    dump(out/'validation.json',{'selected':best,'candidates':rows,'test_opened':False,'high_standard_passed':best['confusion_matrix'][1][1]>=27 and best['confusion_matrix'][0][1]<=2 and best['auc']>=.9,
      'records':[{'name':r['name'],'label':r['label']} for r in vi],'scope':'offline pretrained teacher, not deployed or guaranteed to fit UPduino'})
    dump(out/'receipt.json',{'sha256':{str(p.relative_to(ROOT)):sha(p) for p in out.iterdir() if p.is_file()},'pcm_sha256':th|vh,'test_opened':False})
    print('BEST',best['name'],best['recall'],best['auc'])
if __name__=='__main__':main()
