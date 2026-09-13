#!/usr/bin/env python3
"""Resume 192 fixed +6 dB fit-only counterparts; preserve machine groups."""
import json
import zipfile
from pathlib import Path
import numpy as np
from probe_mimii_snr_pairs import RemoteIndex
from vibfpga.mimii import extract_record, sha

ROOT=Path(__file__).resolve().parents[1]


def main():
    source=ROOT/'data/mimii-multimachine/plan.json'; original=json.loads(source.read_text())
    probe=json.loads((ROOT/'data/mimii-snr-probe/protocol.json').read_text())
    assert probe['plan_sha256']==sha(source.read_bytes())
    archive=probe['archive']; url=archive['links']['self']
    out=ROOT/'data/mimii-snr-fit'; out.mkdir(exist_ok=True)
    selected=[]
    for machine in ('00','02','04'):
        for label in (0,1):
            eligible=[r for r in original['records'] if r['machine']==machine and r['label']==label and r['role']=='fit']
            selected+=sorted(eligible,key=lambda r:sha(('snr-fit-v1:'+r['name']).encode()))[:32]
    assert len(selected)==192 and not any(r['name'] in original['excluded_old_test'] for r in selected)
    plan_path=out/'plan.json'
    if not plan_path.exists():
        with zipfile.ZipFile(RemoteIndex(url,archive['size'])) as z:
            members={i.filename:i for i in z.infolist()}
        rows=[]
        for r in selected:
            i=members[r['name']]
            rows.append(dict(name=i.filename,size=i.file_size,compressed=i.compress_size,crc=i.CRC,
                method=i.compress_type,offset=i.header_offset,machine=r['machine'],label=r['label'],role='fit'))
        plan=dict(archive=archive,source_plan_sha256=sha(source.read_bytes()),records=rows,
            selection='32 per machine/label, SHA256 snr-fit-v1:name; original fit only',
            usage='Each fold uses only source machines; held machine variants excluded; 0 dB calibration and validation unchanged',
            final_test_access=False)
        plan_path.write_text(json.dumps(plan,indent=2)+'\n')
    plan=json.loads(plan_path.read_text()); ph=sha(plan_path.read_bytes())
    assert plan['source_plan_sha256']==sha(source.read_bytes())
    assert [r['name'] for r in plan['records']]==[r['name'] for r in selected]
    for n,r in enumerate(plan['records'],1):
        stem=r['machine']+'_'+str(r['label'])+'_'+Path(r['name']).stem
        path=out/(stem+'.npy'); receipt=out/(stem+'.json')
        if path.exists() and receipt.exists():
            meta=json.loads(receipt.read_text())
            assert meta['plan_sha256']==ph and meta['npy_sha256']==sha(path.read_bytes()) and meta['name']==r['name']
        else:
            pcm,meta=extract_record(r,url); assert pcm.shape==(160000,)
            temp=path.with_suffix('.part.npy'); np.save(temp,pcm); temp.replace(path)
            meta.update(name=r['name'],plan_sha256=ph,npy_sha256=sha(path.read_bytes()))
            receipt.write_text(json.dumps(meta,indent=2)+'\n')
        if n%24==0: print('verified',n,'/192',flush=True)
    (out/'complete.json').write_text(json.dumps(dict(passed=True,records=192,plan_sha256=ph),indent=2)+'\n')


if __name__=='__main__':main()
