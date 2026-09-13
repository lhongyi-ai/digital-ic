#!/usr/bin/env python3
"""Complete raw-rate checks of every remaining screened candidate, no fitting."""
from pathlib import Path
import json
import numpy as np
from vibfpga.recording_audit import refined_correlation
from experiment_acoustic_v2 import sha,dump
ROOT=Path(__file__).resolve().parents[1]
def main():
    base=ROOT/'artifacts/acoustic-recording-audit';out=ROOT/'artifacts/acoustic-recording-audit-completion';out.mkdir(exist_ok=False)
    receipt=json.loads((base/'receipt.json').read_text())
    for rel,h in receipt['sha256'].items():assert sha(ROOT/rel)==h
    result=json.loads((base/'results.json').read_text());done={(r['i'],r['j']) for r in result['raw_verified_pairs']}
    pairs=np.load(base/'all-screen-pairs.npz')['pairs'];todo=[r for r in pairs if abs(r[2])>=.8 and (int(r[0]),int(r[1])) not in done]
    cache={};verified=[]
    for row in todo:
        i,j=int(row[0]),int(row[1]);lag=int(row[3])*32
        for k in [i,j]:
            if k not in cache:
                p=ROOT/result['records'][k]['path'];assert sha(p)==result['pcm_sha256'][str(p.relative_to(ROOT))];cache[k]=np.load(p,allow_pickle=False)
        c,l,n=refined_correlation(cache[i],cache[j],lag,32)
        verified.append({'i':i,'j':j,'raw_correlation':c,'raw_lag_samples':l,'overlap_seconds':n/16000})
    combined=result['raw_verified_pairs']+verified;confirmed=[r for r in combined if abs(r['raw_correlation'])>=.98]
    final={'additional_pairs':len(verified),'total_raw_verified':len(combined),'all_screen_candidates_checked':True,'confirmed_near_pairs':confirmed,
      'additional_results':verified,'remaining_screen_candidates':0,'original_receipt_sha256':sha(base/'receipt.json')}
    dump(out/'results.json',final);dump(out/'receipt.json',{'sha256':{str(p.relative_to(ROOT)):sha(p) for p in [out/'results.json',base/'receipt.json',Path(__file__).resolve(),ROOT/'src/vibfpga/recording_audit.py']}})
    print('raw pairs',len(combined),'near matches',len(confirmed))
if __name__=='__main__':main()
