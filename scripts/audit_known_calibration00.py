#!/usr/bin/env python3
"""Audit new normal calibration against both original development and added fit."""
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.signal import resample_poly
from threadpoolctl import threadpool_limits
from vibfpga.recording_audit import lag_screen,refined_correlation
from vibfpga.mimii import sha as byte_sha
from experiment_acoustic_v2 import sha,dump
ROOT=Path(__file__).resolve().parents[1]

def main():
    paths=[ROOT/'data'/d/'development.json' for d in ('mimii-known-machines-v1','mimii-known-extra00-v1','mimii-known-calibration00-v1')]
    docs=[json.loads(p.read_text()) for p in paths];assert all(d['passed'] for d in docs)
    old=[r for d in docs[:2] for r in d['records'] if r['machine']=='00'];new=docs[2]['records'];rows=old+new
    assert len(old)==512 and len(new)==128 and all(r['role']=='calibration_extra' for r in new)
    assert len({r['name'] for r in rows})==640
    frozen=json.loads((ROOT/'data/mimii-known-machines-v1/plan.json').read_text())
    forbidden=set(frozen['old_test_excluded'])|{r['name'] for r in frozen['records'] if r['role']=='final_test'}
    assert not forbidden&{r['name'] for r in rows}
    output=paths[2].parent/'audit.json'
    if output.exists():raise FileExistsError('Audit exists; inspect before rerun')
    exact=defaultdict(list);chunks=defaultdict(list);pcm=[]
    for i,r in enumerate(rows):
        path=ROOT/r['local'];assert sha(path)==r['npy_sha256'];x=np.load(path,allow_pickle=False)
        assert x.shape==(160000,) and x.dtype==np.int16;pcm.append(x);g='original' if i<512 else 'new_calibration'
        exact[byte_sha(x.tobytes())].append((r['name'],g))
        for start in range(0,144001,8000):
            part=x[start:start+16000]
            if part.min()!=part.max():chunks[byte_sha(part.tobytes())].append((r['name'],g,start))
    print('screening65536pairs',flush=True)
    low=np.stack([resample_poly(x.astype(float),1,32) for x in pcm]);pairs=lag_screen(low,['old']*512+['new']*128,1000)
    assert len(pairs)==65536;pairs.sort(key=lambda p:-abs(p[2]));count=max(20,sum(abs(p[2])>=.8 for p in pairs));review=[]
    for n,(i,j,c,lag,length) in enumerate(pairs[:count],1):
        value,l,length=refined_correlation(pcm[i],pcm[j],lag*32,32)
        review.append(dict(a=rows[i]['name'],b=rows[j]['name'],correlation=value,lag=l,overlap=length,flag=abs(value)>=.98))
        if n%20==0:print('raw reviewed',n,'/',count,flush=True)
    duplicate=[v for v in exact.values() if len({r[1] for r in v})>1];overlap=[v for v in chunks.values() if len({r[1] for r in v})>1]
    ok=not duplicate and not overlap and not any(r['flag'] for r in review)
    dump(output,dict(passed=ok,manifest_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},source_sha256=sha(Path(__file__)),
        helper_sha256=sha(ROOT/'src/vibfpga/recording_audit.py'),screened=len(pairs),raw_review=review,exact_duplicates=duplicate,exact_chunks=overlap,
        final_audio_read=False,limits='>=2s500Hzscreen, all>.8plus top20 rawreview; exact1schunks; not proof of independent acquisition batches'))
    print('PASSED',ok,flush=True)
    if not ok:raise RuntimeError('Overlap; stop before calibration')
if __name__=='__main__':
    with threadpool_limits(limits=2):main()
