#!/usr/bin/env python3
"""Audit existing splits only, never train or change thresholds."""
from pathlib import Path
from collections import defaultdict
import json
import numpy as np
from scipy.signal import resample_poly
from vibfpga.recording_audit import lag_screen,refined_correlation
from vibfpga.mimii import sha
ROOT=Path(__file__).resolve().parents[1]
def digest(p):return sha(p.read_bytes())
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
    out=ROOT/'artifacts/acoustic-recording-audit';out.mkdir(exist_ok=False)
    sources=[Path(__file__).resolve(),ROOT/'src/vibfpga/recording_audit.py']
    protocol={'scope':'400 existing training/validation/test recordings, read for duplicate audit only','no_training':True,
      'screen_rate_hz':500,'minimum_overlap_seconds':2,'all_integer_lags':True,'candidate_abs_correlation':.8,
      'raw_confirmation_abs_correlation':.98,'raw_refinement_samples':32,'max_raw_pairs':100,
      'exact_chunks':'1 second every 0.5 second at original 16kHz','source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in sources}}
    dump(out/'protocol.json',protocol)
    records=[];pcm=[];bindings={}
    for dirname in ['mimii','mimii-supervised']:
        d=ROOT/'data'/dirname;p=d/'plan.json';plan=json.loads(p.read_text())
        for r in plan['records']:
            path=d/r['local'];meta=json.loads(path.with_suffix('.json').read_text());h=digest(path)
            assert h==meta['npy_sha256'] and meta['plan_sha256']==digest(p)
            a=np.load(path,allow_pickle=False);pcm.append(a);records.append({'name':r['name'],'split':r['split'],'label':r['label'],'path':str(path.relative_to(ROOT))});bindings[str(path.relative_to(ROOT))]=h
    assert len(pcm)==400 and len({r['name'] for r in records})==400
    exact=defaultdict(list);chunks=defaultdict(list)
    for i,x in enumerate(pcm):
        exact[sha(x.tobytes())].append(i)
        for start in range(0,len(x)-16000+1,8000):
            segment=x[start:start+16000]
            if np.std(segment)>0:chunks[sha(segment.tobytes())].append((i,start))
    exact_groups=[v for v in exact.values() if len(v)>1]
    chunk_groups=[v for v in chunks.values() if len({records[i]['split'] for i,_ in v})>1]
    low=np.stack([resample_poly(x.astype(float),1,32) for x in pcm]);groups=[r['split'] for r in records]
    pairs=lag_screen(low,groups,1000);pairs.sort(key=lambda r:-abs(r[2]));candidates=[r for r in pairs if abs(r[2])>=.8]
    confirmed=[];verified=[]
    # Include top 20 even below screen threshold to document the strongest matches.
    chosen=pairs[:max(20,min(100,len(candidates)))]
    for i,j,c,lag,length in chosen:
        r,l,n=refined_correlation(pcm[i],pcm[j],lag*32,32)
        row={'i':i,'j':j,'screen_correlation':c,'screen_lag_seconds':lag/500,'raw_correlation':r,'raw_lag_samples':l,'overlap_seconds':n/16000}
        verified.append(row)
        if abs(r)>=.98:confirmed.append(row)
    result={'records':records,'record_counts':{g:groups.count(g) for g in sorted(set(groups))},'pcm_sha256':bindings,
      'exact_record_groups':exact_groups,'exact_cross_split_chunk_groups':chunk_groups,'cross_split_pairs_screened':len(pairs),
      'screen_candidates':len(candidates),'raw_verified_pairs':verified,'confirmed_near_pairs':confirmed,
      'unconfirmed_screen_candidates':max(0,len(candidates)-len(chosen)),
      'top_screen_pairs':[dict(zip(['i','j','correlation','lag_500Hz','overlap_500Hz'],p)) for p in pairs[:100]],
      'limitations':'Only channel0; 500Hz screen may miss high-frequency-only reuse; >=2s overlaps and top100 candidate cap; absence is not proof of independent sessions.'}
    dump(out/'results.json',result);np.savez_compressed(out/'all-screen-pairs.npz',pairs=np.array(pairs))
    dump(out/'receipt.json',{'sha256':{str(p.relative_to(ROOT)):digest(p) for p in out.iterdir() if p.is_file()}})
    print(json.dumps({k:result[k] for k in ['record_counts','exact_record_groups','exact_cross_split_chunk_groups','cross_split_pairs_screened','screen_candidates','confirmed_near_pairs','unconfirmed_screen_candidates']},indent=2))
if __name__=='__main__':main()
