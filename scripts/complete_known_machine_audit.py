#!/usr/bin/env python3
"""Finish remaining raw confirmations; preserve the original incomplete audit."""
import json
from pathlib import Path
import numpy as np
from scipy.signal import resample_poly
from threadpoolctl import threadpool_limits
from vibfpga.recording_audit import lag_screen,refined_correlation
from experiment_acoustic_v2 import dump,sha
ROOT=Path(__file__).resolve().parents[1]

def main():
    base=ROOT/'data/mimii-known-machines-v1'; ap=base/'development-audit.json'; dp=base/'development.json'
    original=json.loads(ap.read_text()); data=json.loads(dp.read_text())
    assert original['development_sha256']==sha(dp)
    assert not original['exact_duplicates'] and not original['exact_cross_group_chunks']
    assert not any(p['flag'] for r in original['reports'] for p in r['raw_review'])
    out=base/'development-audit-completion.json'
    if out.exists():raise FileExistsError('Completion exists')
    additional=[]
    for report in original['reports']:
        if not report['unreviewed']:continue
        rows=[r for r in data['records'] if r['machine']==report['machine']]
        groups=[str(r['fold']) if r['role']=='cv' else 'calibration' for r in rows]; pcm=[]
        for r in rows:
            p=ROOT/r['local'];assert sha(p)==r['npy_sha256'];pcm.append(np.load(p,allow_pickle=False))
        low=np.stack([resample_poly(x.astype(float),1,32) for x in pcm])
        candidates=[p for p in lag_screen(low,groups,1000) if abs(p[2])>=.8]
        candidates.sort(key=lambda p:-abs(p[2]));assert len(candidates)==report['candidates']
        remaining=candidates[100:];assert len(remaining)==report['unreviewed']
        for i,j,c,lag,n in remaining:
            value,l,length=refined_correlation(pcm[i],pcm[j],lag*32,32)
            additional.append(dict(a=rows[i]['name'],b=rows[j]['name'],correlation=value,lag=l,overlap=length,flag=abs(value)>=.98))
    dump(out,dict(passed=not any(r['flag'] for r in additional),original_audit_sha256=sha(ap),
        development_sha256=sha(dp),additional_review=additional,remaining=0,
        source_sha256=sha(Path(__file__)),limitations=original['limitations']))
    print('Additional checked',len(additional),'flags',sum(r['flag'] for r in additional),flush=True)

if __name__=='__main__':
    with threadpool_limits(limits=2):main()
