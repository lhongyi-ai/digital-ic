#!/usr/bin/env python3
"""Predeclared unseen-device evaluation: fan/id_02, same SNR, no fitting."""
import io,json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import numpy as np
from vibfpga.mimii import extract_record,sha
ROOT=Path(__file__).resolve().parents[1]
def main():
    d=ROOT/'data/mimii-external-id02';d.mkdir(exist_ok=True);(d/'pcm').mkdir(exist_ok=True)
    old=json.loads((ROOT/'data/mimii/plan.json').read_text());index=json.loads((ROOT/'data/mimii/archive-index.json').read_text());records=[]
    for label,count in [('normal',40),('abnormal',30)]:
        candidates=[x for x in index if x['name'].startswith('fan/id_02/'+label+'/')]
        candidates.sort(key=lambda x:sha(('external-id02-2026-09-11:'+x['name']).encode()))
        records += [{**r,'label':int(label=='abnormal'),'split':'external_test','local':'pcm/'+label+'_'+Path(r['name']).stem+'.npy'} for r in candidates[:count]]
    freeze=ROOT/'artifacts/acoustic-v7-supervised-r2/frozen.json'
    plan={'machine':'fan/id_02','snr_db':0,'channel':0,'records':records,'archive':old['archive'],
      'seed':'external-id02-2026-09-11','frozen_model_sha256':sha(freeze.read_bytes()),
      'scope':'new machine ID, distinct target-machine recording per official paper; per-file batch/noise-source independence unknown',
      'evaluation':'primary spectrum1024-trees, frozen threshold, no retraining or recalibration','goal':{'tp':27,'max_fp':2,'auc':.9}}
    p=d/'plan.json'
    if p.exists():assert json.loads(p.read_text())==plan
    else:p.write_text(json.dumps(plan,indent=2)+'\n')
    ph=sha(p.read_bytes())
    print('Predeclared',len(records),'records',sum(r['compressed'] for r in records),'compressed bytes',flush=True)
    def get(r):
        path=d/r['local'];meta=path.with_suffix('.json')
        if path.exists() and meta.exists():
            m=json.loads(meta.read_text());assert m['plan_sha256']==ph and m['npy_sha256']==sha(path.read_bytes());return
        pcm,m=extract_record(r,old['archive']['links']['self']);b=io.BytesIO();np.save(b,pcm,allow_pickle=False);path.write_bytes(b.getvalue())
        m.update(plan_sha256=ph,npy_sha256=sha(path.read_bytes()),record=r['name']);meta.write_text(json.dumps(m,indent=2)+'\n')
    with ThreadPoolExecutor(max_workers=3) as pool:
        for n,f in enumerate(as_completed([pool.submit(get,r) for r in records]),1):
            f.result()
            if n%10==0:print('Verified',n,flush=True)
    (d/'download.json').write_text(json.dumps({'passed':True,'records':70,'plan_sha256':ph},indent=2)+'\n')
if __name__=='__main__':main()
