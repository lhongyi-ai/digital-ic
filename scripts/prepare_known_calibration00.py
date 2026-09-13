#!/usr/bin/env python3
"""Add 128 independently assigned ID00 normal calibration records, no fitting."""
import hashlib,json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
from experiment_acoustic_v2 import sha,dump
from vibfpga.mimii import extract_record
ROOT=Path(__file__).resolve().parents[1]

def main():
    base=ROOT/'data/mimii-known-machines-v1';extra=ROOT/'data/mimii-known-extra00-v1'
    p=json.loads((base/'plan.json').read_text());ep=json.loads((extra/'plan.json').read_text())
    assert sha(base/'plan.json')==json.loads((base/'freeze.json').read_text())['plan_sha256']
    forbidden={r['name'] for r in p['records']+ep['records']}|set(p['old_test_excluded'])
    out=ROOT/'data/mimii-known-calibration00-v1';out.mkdir(exist_ok=True);pp=out/'plan.json'
    if not pp.exists():
        index=json.loads((ROOT/'data/mimii/archive-index.json').read_text())
        candidates=[r for r in index if r['name'].startswith('fan/id_00/normal/') and r['name'].endswith('.wav') and r['name'] not in forbidden]
        candidates.sort(key=lambda r:hashlib.sha256(('known-calibration00-v1:'+r['name']).encode()).hexdigest())
        assert len(candidates)>=128
        dump(pp,dict(records=[dict(r,machine='00',label=0,role='calibration_extra',fold=None) for r in candidates[:128]],
            original_plan_sha256=sha(base/'plan.json'),extra_fit_plan_sha256=sha(extra/'plan.json'),
            source_sha256=sha(Path(__file__)),policy='keep original32 normals, append128 normals; training and validation unchanged',
            threshold='Fixed alpha=.04; k=ceil((160+1)*.96)=155 ascending, sixth-highest, strict >; report old32 max as diagnostic',
            final_test_opened=False))
        dump(out/'freeze.json',dict(plan_sha256=sha(pp)))
    assert sha(pp)==json.loads((out/'freeze.json').read_text())['plan_sha256']
    plan=json.loads(pp.read_text());assert not {r['name'] for r in plan['records']}&forbidden
    for sub in ('pcm','receipts'):(out/sub).mkdir(exist_ok=True)
    url=json.loads((ROOT/'data/mimii-multimachine/plan.json').read_text())['archive']['links']['self']
    def one(r):
        stem='00_0_'+Path(r['name']).stem;rp=out/'receipts'/(stem+'.json')
        if rp.exists():
            meta=json.loads(rp.read_text());assert meta['plan_sha256']==sha(pp) and meta['name']==r['name']
            assert meta['npy_sha256']==sha(ROOT/meta['local'])
        else:
            x,meta=extract_record(r,url);assert x.shape==(160000,) and x.dtype==np.int16
            path=out/'pcm'/(stem+'.npy');tmp=path.with_suffix('.part.npy');np.save(tmp,x);tmp.replace(path)
            meta=dict(meta,name=r['name'],local=str(path.relative_to(ROOT)),plan_sha256=sha(pp),npy_sha256=sha(path));dump(rp,meta)
        return dict(r,local=meta['local'],npy_sha256=meta['npy_sha256'])
    rows=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        for n,r in enumerate(pool.map(one,plan['records']),1):
            rows.append(r)
            if n%16==0:print('verified',n,'/128',flush=True)
    dump(out/'development.json',dict(passed=True,records=rows,plan_sha256=sha(pp),final_audio_read=False))
    print('COMPLETE calibration128',flush=True)
if __name__=='__main__':main()
