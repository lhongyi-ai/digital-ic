#!/usr/bin/env python3
"""Screen added fit recordings against all original ID00 development recordings."""
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
    base=ROOT/'data/mimii-known-machines-v1';extra=ROOT/'data/mimii-known-extra00-v1'
    original=json.loads((base/'development.json').read_text());addition=json.loads((extra/'development.json').read_text())
    plan=json.loads((base/'plan.json').read_text());ep=json.loads((extra/'plan.json').read_text())
    assert addition['passed'] and addition['plan_sha256']==sha(extra/'plan.json')
    assert ep['original_plan_sha256']==sha(base/'plan.json')
    forbidden={r['name'] for r in plan['records']}|set(plan['old_test_excluded'])
    assert not {r['name'] for r in addition['records']}&forbidden
    old=[r for r in original['records'] if r['machine']=='00'];new=addition['records'];rows=old+new
    assert len(old)==len(new)==256 and all(r['role']=='fit_extra' for r in new)
    output=extra/'audit.json'
    if output.exists():raise FileExistsError('Inspect existing audit before any rerun')
    exact=defaultdict(list);chunks=defaultdict(list);pcm=[]
    for r in rows:
        path=ROOT/r['local'];assert sha(path)==r['npy_sha256'];x=np.load(path,allow_pickle=False)
        assert x.dtype==np.int16 and x.shape==(160000,);pcm.append(x)
        group='extra' if r['role']=='fit_extra' else 'original'
        exact[byte_sha(x.tobytes())].append((r['name'],group))
        for k in range(0,144001,8000):
            part=x[k:k+16000]
            if part.min()!=part.max():chunks[byte_sha(part.tobytes())].append((r['name'],group,k))
    low=np.stack([resample_poly(x.astype(float),1,32) for x in pcm])
    print('screening 65536 extra/original pairs, 500Hz, >=2s overlap',flush=True)
    pairs=lag_screen(low,['original']*256+['extra']*256,1000);assert len(pairs)==65536
    pairs.sort(key=lambda p:-abs(p[2]));count=max(20,sum(abs(p[2])>=.8 for p in pairs));review=[]
    for number,(i,j,c,lag,n) in enumerate(pairs[:count],1):
        value,l,length=refined_correlation(pcm[i],pcm[j],lag*32,32)
        review.append(dict(a=rows[i]['name'],b=rows[j]['name'],screen_correlation=c,correlation=value,lag=l,overlap=length,flag=abs(value)>=.98))
        if number%20==0:print('raw reviewed',number,'/',count,flush=True)
    duplicates=[v for v in exact.values() if len({x[1] for x in v})>1]
    overlaps=[v for v in chunks.values() if len({x[1] for x in v})>1]
    ok=not duplicates and not overlaps and not any(r['flag'] for r in review)
    dump(output,dict(passed=ok,original_development_sha256=sha(base/'development.json'),development_sha256=sha(extra/'development.json'),
        script_sha256=sha(Path(__file__)),helper_sha256=sha(ROOT/'src/vibfpga/recording_audit.py'),screened=len(pairs),
        candidates=sum(abs(p[2])>=.8 for p in pairs),raw_review=review,exact_duplicates=duplicates,exact_chunks=overlaps,
        final_audio_read=False,limits='Cross extra/original ID00 only, exact1s stride0.5s, 500Hz lag screen >=2s, raw review of all >=.8 and top20; no independent-batch claim'))
    print('PASSED',ok,flush=True)
    if not ok:raise RuntimeError('Overlap found; no automatic training')

if __name__=='__main__':
    with threadpool_limits(limits=2):main()
