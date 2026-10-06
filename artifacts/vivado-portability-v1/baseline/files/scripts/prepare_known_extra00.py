#!/usr/bin/env python3
"""Freeze/download additional ID00 fit-only records; never move held-out records."""
import hashlib
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from experiment_acoustic_v2 import sha,dump
from vibfpga.mimii import extract_record

ROOT=Path(__file__).resolve().parents[1]

def main():
    base=ROOT/'data/mimii-known-machines-v1';plan=json.loads((base/'plan.json').read_text())
    assert sha(base/'plan.json')==json.loads((base/'freeze.json').read_text())['plan_sha256']
    index_path=ROOT/'data/mimii/archive-index.json';assert sha(index_path)==plan['index_sha256']
    index=json.loads(index_path.read_text())
    excluded={r['name'] for r in plan['records']}|set(plan['old_test_excluded'])
    out=ROOT/'data/mimii-known-extra00-v1';out.mkdir(exist_ok=True)
    frozen=out/'plan.json'
    if not frozen.exists():
        rows=[]
        for label,state in ((0,'normal'),(1,'abnormal')):
            candidates=[r for r in index if r['name'].startswith(f'fan/id_00/{state}/') and r['name'].endswith('.wav') and r['name'] not in excluded]
            candidates.sort(key=lambda r:hashlib.sha256(('known-extra00-v1:'+r['name']).encode()).hexdigest())
            assert len(candidates)>=128,(label,len(candidates))
            rows += [dict(r,machine='00',label=label,role='fit_extra',fold=None) for r in candidates[:128]]
        dump(frozen,dict(records=rows,original_plan_sha256=sha(base/'plan.json'),index_sha256=sha(index_path),
            script_sha256=sha(Path(__file__)),selection='128 per class ID00, fixed SHA256 order, excluding entire frozen plan and all old tests',
            scope='fit only in all three folds; existing validation/calibration/final unchanged',final_test_opened=False))
        dump(out/'freeze.json',dict(plan_sha256=sha(frozen)))
    assert json.loads((out/'freeze.json').read_text())['plan_sha256']==sha(frozen)
    p=json.loads(frozen.read_text());assert p['original_plan_sha256']==sha(base/'plan.json')
    assert len(p['records'])==256 and not {r['name'] for r in p['records']}&excluded
    # Reuse only official 0 dB caches with original WAV provenance and PCM digest.
    available={}
    for folder in ('mimii','mimii-supervised','mimii-multimachine','mimii-external-id02'):
        d=ROOT/'data'/folder;pp=d/'plan.json'
        if not pp.exists():continue
        doc=json.loads(pp.read_text())
        for r in doc.get('records',[]):
            if not r.get('name','').startswith('fan/id_00/') or not r.get('local'):continue
            options=[ROOT/r['local'],d/r['local']]
            local=next((q for q in options if q.exists()),None)
            if local is None:continue
            receipt=local.with_suffix('.json')
            if not receipt.exists():receipt=d/'receipts'/('00_'+str(r['label'])+'_'+Path(r['name']).stem+'.json')
            if not receipt.exists():continue
            meta=json.loads(receipt.read_text())
            if meta.get('npy_sha256')==sha(local) and meta.get('original_wav_sha256'):
                available[r['name']]=(local,meta)
    for sub in ('pcm','receipts'):(out/sub).mkdir(exist_ok=True)
    archive=json.loads((ROOT/'data/mimii-multimachine/plan.json').read_text())['archive']['links']['self']
    def one(r):
        stem='00_'+str(r['label'])+'_'+Path(r['name']).stem;rp=out/'receipts'/(stem+'.json')
        if rp.exists():
            meta=json.loads(rp.read_text());assert meta['plan_sha256']==sha(frozen) and meta['name']==r['name']
            path=ROOT/meta['local'];assert sha(path)==meta['npy_sha256']
        else:
            if r['name'] in available:
                path,meta=available[r['name']];reused=True
            else:
                pcm,meta=extract_record(r,archive);assert pcm.shape==(160000,) and pcm.dtype==np.int16
                path=out/'pcm'/(stem+'.npy');tmp=path.with_suffix('.part.npy');np.save(tmp,pcm);tmp.replace(path);reused=False
            meta=dict(meta,name=r['name'],local=str(path.relative_to(ROOT)),plan_sha256=sha(frozen),npy_sha256=sha(path),reused=reused)
            dump(rp,meta)
        return dict(r,local=meta['local'],npy_sha256=meta['npy_sha256'])
    records=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        for count,r in enumerate(pool.map(one,p['records']),1):
            records.append(r)
            if count%16==0:print('verified',count,'/256',flush=True)
    dump(out/'development.json',dict(passed=True,records=records,plan_sha256=sha(frozen),final_audio_read=False))
    print('COMPLETE 256 ID00 fit-only records',flush=True)

if __name__=='__main__':main()
