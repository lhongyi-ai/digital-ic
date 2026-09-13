#!/usr/bin/env python3
"""Separate authorized fault-training extension; original split is immutable."""
import io,json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import numpy as np
from vibfpga.mimii import extract_record,sha
ROOT=Path(__file__).resolve().parents[1]
def main():
    d=ROOT/'data/mimii-supervised';d.mkdir(exist_ok=True);(d/'pcm').mkdir(exist_ok=True)
    orig=ROOT/'data/mimii/plan.json';plan=json.loads(orig.read_text());index=json.loads((ROOT/'data/mimii/archive-index.json').read_text())
    excluded={x['name'] for x in plan['records']};eligible=[x for x in index if x['name'].startswith('fan/id_00/abnormal/') and x['name'] not in excluded]
    chosen=sorted(eligible,key=lambda x:sha(('mimii-supervised-v1:'+x['name']).encode()))[:120]
    assert len(chosen)==120 and not({x['name'] for x in chosen}&excluded)
    proposed={'original_plan_sha256':sha(orig.read_bytes()),'authorization':'user allowed independent fault training; original validation/test fixed',
      'scope':'supervised known-fault classification, not normal-only unknown anomaly detection','archive':plan['archive'],
      'seed':'mimii-supervised-v1','records':[{**x,'label':1,'split':'train','local':'pcm/abnormal_'+Path(x['name']).stem+'.npy'} for x in chosen]}
    path=d/'plan.json'
    if path.exists():assert json.loads(path.read_text())==proposed
    else:path.write_text(json.dumps(proposed,indent=2)+'\n')
    ph=sha(path.read_bytes())
    print('Independent abnormal training records',len(chosen),'compressed bytes',sum(x['compressed'] for x in chosen),flush=True)
    def get(info):
        out=d/info['local'];meta=out.with_suffix('.json')
        if out.exists() and meta.exists():
            m=json.loads(meta.read_text())
            if m['plan_sha256']==ph and sha(out.read_bytes())==m['npy_sha256']:return
            raise ValueError('existing record changed')
        pcm,m=extract_record(info,proposed['archive']['links']['self']);b=io.BytesIO();np.save(b,pcm,allow_pickle=False)
        out.write_bytes(b.getvalue());m.update(plan_sha256=ph,npy_sha256=sha(out.read_bytes()),record=info['name']);meta.write_text(json.dumps(m,indent=2)+'\n')
    with ThreadPoolExecutor(max_workers=3) as pool:
        for count,_ in enumerate(as_completed([pool.submit(get,x) for x in proposed['records']]),1):
            _.result()
            if count%10==0:print('Verified',count,'/',120,flush=True)
    (d/'download.json').write_text(json.dumps({'passed':True,'records':120,'plan_sha256':ph,'original_plan_sha256':sha(orig.read_bytes()),'test_opened':False},indent=2)+'\n')
if __name__=='__main__':main()
