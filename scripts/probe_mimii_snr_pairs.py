#!/usr/bin/env python3
"""Read ZIP index and six fit-only +6 dB counterparts; no held/test PCM."""
import io
import json
import urllib.request
import zipfile
from pathlib import Path
import numpy as np
from vibfpga.mimii import fetch_range, extract_record, sha

ROOT=Path(__file__).resolve().parents[1]


class RemoteIndex(io.RawIOBase):
    def __init__(self,url,size): self.url=url; self.size=size; self.pos=0
    def seekable(self): return True
    def tell(self): return self.pos
    def seek(self,offset,whence=0):
        self.pos = offset if whence==0 else (self.pos if whence==1 else self.size)+offset
        return self.pos
    def read(self,n=-1):
        n=self.size-self.pos if n<0 else min(n,self.size-self.pos)
        if n<0 or n>4_000_000: raise ValueError('non-index-sized request rejected')
        if not n: return b''
        value=fetch_range(self.url,self.pos,n); self.pos+=n; return value


def main():
    plan_path=ROOT/'data/mimii-multimachine/plan.json'
    plan=json.loads(plan_path.read_text())
    out=ROOT/'data/mimii-snr-probe'; out.mkdir(exist_ok=False)
    with urllib.request.urlopen('https://zenodo.org/api/records/3384388',timeout=60) as r:
        metadata=json.load(r)
    archive=next(f for f in metadata['files'] if f['key']=='6_dB_fan.zip')
    url=archive['links']['self']
    with zipfile.ZipFile(RemoteIndex(url,archive['size'])) as z:
        index={i.filename:dict(name=i.filename,size=i.file_size,compressed=i.compress_size,
            crc=i.CRC,method=i.compress_type,offset=i.header_offset) for i in z.infolist()}
    chosen=[]
    for machine in ('00','02','04'):
        for label in (0,1):
            chosen.append(sorted((r for r in plan['records'] if r['machine']==machine and r['label']==label and r['role']=='fit'),key=lambda r:r['name'])[0])
    protocol=dict(archive=archive,plan_sha256=sha(plan_path.read_bytes()),records=chosen,
        selection='alphabetically first fit record per machine and label; no score selection',
        final_test_opened=False,source_sha256=sha(Path(__file__).read_bytes()))
    (out/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    findings=[]
    for r in chosen:
        pcm,receipt=extract_record(index[r['name']],url)
        old=np.load(ROOT/r['local'],allow_pickle=False)
        assert old.shape==pcm.shape==(160000,)
        path=out/(r['machine']+'_'+str(r['label'])+'.npy'); np.save(path,pcm)
        receipt.update(npy_sha256=sha(path.read_bytes()),name=r['name'])
        path.with_suffix('.json').write_text(json.dumps(receipt,indent=2)+'\n')
        a=old.astype(float); b=pcm.astype(float)
        result=dict(name=r['name'],zero_six_correlation=float(np.corrcoef(a,b)[0,1]),
            zero_rms=float(np.sqrt(np.mean(a*a))),six_rms=float(np.sqrt(np.mean(b*b))))
        findings.append(result); print(result,flush=True)
    (out/'results.json').write_text(json.dumps(dict(records=findings,
        caution='Correlation does not by itself prove clean/noise decomposition or physical independence; these variants must stay in the same split.'),indent=2)+'\n')


if __name__=='__main__':main()
