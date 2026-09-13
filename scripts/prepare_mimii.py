#!/usr/bin/env python3
"""Freeze the MIMII subset before downloading its individual records."""
import argparse, concurrent.futures, json, os
from pathlib import Path
import numpy as np
from vibfpga.mimii import make_plan,validate_plan,extract_record,sha
p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,default=Path('data/mimii'));p.add_argument('--download',action='store_true');p.add_argument('--workers',type=int,default=3);a=p.parse_args()
d=a.directory; path=d/'plan.json'
if not path.exists():
    plan=make_plan(json.loads((d/'archive-index.json').read_text()),json.loads((d/'archive-file.json').read_text()))
    validate_plan(plan)
    with path.open('x') as f:json.dump(plan,f,indent=2)
plan=json.loads(path.read_text());validate_plan(plan)
print('Frozen plan:',len(plan['records']),'records;',sum(x['compressed'] for x in plan['records']),'compressed bytes',flush=True)
if a.download:
    (d/'pcm').mkdir(exist_ok=True)
    def get(info):
        out=d/info['local'];meta=out.with_suffix('.json')
        if out.exists() and meta.exists():
            m=json.loads(meta.read_text())
            if m['plan_sha256']==sha(path.read_bytes()) and m['npy_sha256']==sha(out.read_bytes()):return
            raise ValueError('existing member hash mismatch')
        pcm,m=extract_record(info,plan['archive']['links']['self'])
        tmp=out.with_suffix('.part.npy');np.save(tmp,pcm);os.replace(tmp,out)
        m.update(name=info['name'],plan_sha256=sha(path.read_bytes()),npy_sha256=sha(out.read_bytes()))
        meta.write_text(json.dumps(m,indent=2)+'\n')
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
        for i,_ in enumerate(pool.map(get,plan['records']),1):
            if i%10==0:print('Verified',i,'/',len(plan['records']),flush=True)
    (d/'download.json').write_text(json.dumps({'passed':True,'records':len(plan['records']),'plan_sha256':sha(path.read_bytes()),'verification':'official ZIP member CRC32, raw WAV SHA256, channel-0 NPY SHA256; full archive MD5 not verified'},indent=2)+'\n')
