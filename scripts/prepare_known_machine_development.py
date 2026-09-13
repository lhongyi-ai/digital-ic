#!/usr/bin/env python3
"""Download/reuse frozen development only; this entry cannot read final audio."""
import json
from pathlib import Path
import numpy as np
from vibfpga.mimii import extract_record,sha

ROOT=Path(__file__).resolve().parents[1]

def main():
    base=ROOT/'data/mimii-known-machines-v1'; pp=base/'plan.json'
    plan=json.loads(pp.read_text()); ph=sha(pp.read_bytes())
    assert ph==json.loads((base/'freeze.json').read_text())['plan_sha256']
    rows=[r for r in plan['records'] if r['role'] in ('cv','calibration')]; assert len(rows)==1024
    old_path=ROOT/'data/mimii-multimachine/plan.json'; old=json.loads(old_path.read_text())
    assert sha(old_path.read_bytes())==plan['prior_metadata_sha256'][str(old_path.relative_to(ROOT))]
    available={r['name']:r for r in old['records']}
    for sub in ('pcm','receipts'): (base/sub).mkdir(exist_ok=True)
    records=[]; reused=0
    for count,r in enumerate(rows,1):
        stem=r['machine']+'_'+str(r['label'])+'_'+Path(r['name']).stem
        receipt=base/'receipts'/(stem+'.json')
        if receipt.exists():
            meta=json.loads(receipt.read_text()); path=ROOT/meta['local']
            assert meta['plan_sha256']==ph and meta['name']==r['name'] and meta['npy_sha256']==sha(path.read_bytes())
        else:
            candidate=available.get(r['name'])
            if candidate is not None and (ROOT/candidate['local']).exists():
                path=ROOT/candidate['local']
                old_receipt=ROOT/'data/mimii-multimachine/receipts'/(stem+'.json')
                meta=json.loads(old_receipt.read_text())
                assert meta['plan_sha256']==sha(old_path.read_bytes()) and meta['name']==r['name'] and meta['npy_sha256']==sha(path.read_bytes())
                reused+=1
            else:
                pcm,meta=extract_record(r,old['archive']['links']['self'])
                assert pcm.shape==(160000,) and pcm.dtype==np.int16
                path=base/'pcm'/(stem+'.npy'); temp=path.with_suffix('.part.npy')
                np.save(temp,pcm); temp.replace(path)
            meta=dict(meta,name=r['name'],local=str(path.relative_to(ROOT)),plan_sha256=ph,npy_sha256=sha(path.read_bytes()))
            receipt.write_text(json.dumps(meta,indent=2)+'\n')
        records.append(dict(r,local=meta['local'],npy_sha256=meta['npy_sha256']))
        if count%64==0:print('verified',count,'/1024',flush=True)
    (base/'development.json').write_text(json.dumps(dict(passed=True,plan_sha256=ph,records=records,final_audio_read=False),indent=2)+'\n')
    print('complete; reused this run',reused,flush=True)

if __name__=='__main__':main()
