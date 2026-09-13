#!/usr/bin/env python3
"""Check frozen development grouping and overlap, without reading final PCM."""
import json
from pathlib import Path
from collections import defaultdict
import numpy as np
from scipy.signal import resample_poly
from threadpoolctl import threadpool_limits
from vibfpga.recording_audit import lag_screen,refined_correlation
from experiment_acoustic_v2 import sha,dump
from vibfpga.mimii import sha as byte_sha
ROOT=Path(__file__).resolve().parents[1]

def main():
    base=ROOT/'data/mimii-known-machines-v1'; path=base/'development.json'
    d=json.loads(path.read_text()); assert d['passed'] and all(r['role']!='final_test' for r in d['records'])
    output=base/'development-audit.json'
    if output.exists():raise FileExistsError('Audit exists; inspect before rerun')
    exact=defaultdict(list); chunks=defaultdict(list); reports=[]
    for machine in ('00','02','04','06'):
        rows=[r for r in d['records'] if r['machine']==machine]; assert len(rows)==256
        pcm=[];groups=[str(r['fold']) if r['role']=='cv' else 'calibration' for r in rows]
        for r,g in zip(rows,groups):
            p=ROOT/r['local'];assert sha(p)==r['npy_sha256']
            x=np.load(p,allow_pickle=False);assert x.shape==(160000,) and x.dtype==np.int16
            pcm.append(x);exact[byte_sha(x.tobytes())].append(r['name'])
            for start in range(0,144001,8000):
                part=x[start:start+16000]
                if part.min()!=part.max():chunks[byte_sha(part.tobytes())].append((r['name'],g,start))
        low=np.stack([resample_poly(x.astype(float),1,32) for x in pcm])
        pairs=lag_screen(low,groups,1000);pairs.sort(key=lambda p:-abs(p[2]))
        candidates=[p for p in pairs if abs(p[2])>=.8];review=[]
        for i,j,c,lag,n in pairs[:max(20,min(100,len(candidates)))]:
            value,l,length=refined_correlation(pcm[i],pcm[j],lag*32,32)
            review.append(dict(a=rows[i]['name'],b=rows[j]['name'],correlation=value,lag=l,overlap=length,flag=abs(value)>=.98))
        reports.append(dict(machine=machine,screened=len(pairs),candidates=len(candidates),raw_review=review,unreviewed=max(0,len(candidates)-100)))
        print(machine,'screened',len(pairs),'flagged',sum(r['flag'] for r in review),flush=True)
    duplicates=[v for v in exact.values() if len(v)>1]
    overlaps=[v for v in chunks.values() if len({r[1] for r in v})>1]
    passed=not duplicates and not overlaps and all(not r['unreviewed'] and not any(p['flag'] for p in r['raw_review']) for r in reports)
    dump(output,dict(passed=passed,development_sha256=sha(path),script_sha256=sha(Path(__file__)),
        helper_sha256=sha(ROOT/'src/vibfpga/recording_audit.py'),reports=reports,exact_duplicates=duplicates,exact_cross_group_chunks=overlaps,
        final_audio_read=False,limitations='500 Hz screen within machine, >=2s overlap; high-frequency-only and shorter similarities may be missed. No batch-independence claim.'))
    print('PASSED',passed,flush=True)

if __name__=='__main__':
    with threadpool_limits(limits=2):main()
