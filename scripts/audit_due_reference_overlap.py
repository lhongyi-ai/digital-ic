#!/usr/bin/env python3
"""Audit DUE normal references against development recordings without fitting."""
import json
from pathlib import Path
from collections import defaultdict
import numpy as np
from scipy.signal import resample_poly
from threadpoolctl import threadpool_limits
from vibfpga.recording_audit import lag_screen, refined_correlation
from experiment_acoustic_v2 import sha, dump
from vibfpga.mimii import sha as byte_sha

ROOT=Path(__file__).resolve().parents[1]


def main():
    source=ROOT/'artifacts/acoustic-due-normal-reference-v1/results.json'
    old=json.loads(source.read_text()); base=ROOT/'data/mimii-due-source-review'
    out=ROOT/'artifacts/acoustic-due-reference-overlap-v1'; out.mkdir(exist_ok=False)
    dump(out/'protocol.json',dict(source_sha256=sha(source),script_sha256=sha(Path(__file__)),
        helper_sha256=sha(ROOT/'src/vibfpga/recording_audit.py'),
        scope='each section: 203 normal reference/calibration files against 400 development files',
        screen='500 Hz antialias resampling, all lags with >=2 s overlap; abs correlation .8',
        confirmation='16 kHz raw correlation, +/-32 samples refinement, .98 threshold; top20 or up to100 candidates per section',
        exact_chunks='1 second at 0.5 second steps, all sections and nonconstant chunks',
        final_test_opened=False,no_training=True))
    sections=[]; chunk_hashes=defaultdict(list); full_hashes=defaultdict(list)
    for s in old['sections']:
        names=s['reference']+s['calibration']+[r['name'] for r in s['records']]
        groups=['reference']*203+['development']*400; assert len(names)==603
        pcm=[]
        for name,group in zip(names,groups):
            path=base/'pcm'/(Path(name).stem+'.npy')
            assert sha(path)==old['pcm_sha256'][str(path.relative_to(ROOT))]
            x=np.load(path,allow_pickle=False); pcm.append(x)
            full_hashes[byte_sha(x.tobytes())].append((name,group))
            for start in range(0,len(x)-16000+1,8000):
                segment=x[start:start+16000]
                if segment.min()!=segment.max():chunk_hashes[byte_sha(segment.tobytes())].append((name,group,start))
        low=np.stack([resample_poly(x.astype(float),1,32) for x in pcm])
        pairs=lag_screen(low,groups,1000); assert len(pairs)==203*400
        pairs.sort(key=lambda p:-abs(p[2])); candidates=[p for p in pairs if abs(p[2])>=.8]
        chosen=pairs[:max(20,min(100,len(candidates)))]; verified=[]
        for i,j,c,lag,length in chosen:
            value,raw_lag,n=refined_correlation(pcm[i],pcm[j],lag*32,32)
            verified.append(dict(reference=names[i],development=names[j],screen_correlation=c,
                raw_correlation=value,lag_samples=raw_lag,overlap_samples=n,flagged=abs(value)>=.98))
        result=dict(section=s['section'],screened_pairs=len(pairs),screen_candidates=len(candidates),
            raw_checked=verified,unconfirmed_candidates=max(0,len(candidates)-len(chosen)),
            flagged_pairs=sum(v['flagged'] for v in verified))
        sections.append(result); dump(out/f"section-{s['section']}.json",result)
        print(s['section'], 'pairs',len(pairs),'candidates',len(candidates),'flagged',result['flagged_pairs'],flush=True)
    dump(out/'results.json',dict(sections=sections,
        exact_full_groups=[v for v in full_hashes.values() if len(v)>1],
        exact_cross_role_chunks=[v for v in chunk_hashes.values() if len({x[1] for x in v})>1],
        limitations='Near-similarity screening is within section only, low-bandwidth and >=2s; capped confirmations. High correlation is a review flag, not proof of duplication. No result establishes independent acquisition batches.'))


if __name__=='__main__':
    with threadpool_limits(limits=2): main()
