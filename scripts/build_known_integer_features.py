#!/usr/bin/env python3
"""Generate exact integer DSP features for development/calibration only."""
import json
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from vibfpga.known_fixed import integer_power,power_log_q12
from experiment_acoustic_v2 import sha,dump
ROOT=Path(__file__).resolve().parents[1]

def main():
    base=ROOT/'data/mimii-known-machines-v1';cal=ROOT/'data/mimii-known-calibration00-v1'
    original=json.loads((base/'development.json').read_text());extra=json.loads((cal/'development.json').read_text())
    audit=json.loads((cal/'audit.json').read_text());assert audit['passed']
    assert all(sha(ROOT/p)==h for p,h in audit['manifest_sha256'].items())
    rows=original['records']+extra['records'];assert len(rows)==1152 and all(r['role']!='final_test' for r in rows)
    out=ROOT/'artifacts/acoustic-known-integer-dsp-v2';out.mkdir(exist_ok=False)
    dump(out/'protocol.json',dict(source_sha256=sha(ROOT/'src/vibfpga/known_fixed.py'),script_sha256=sha(Path(__file__)),
        manifests={str(p.relative_to(ROOT)):sha(p) for p in (base/'development.json',cal/'development.json')},
        stage='integer DSP development features; no final evaluation, no RTL claim',input_shift=1,n=1024,windows=156,
        coefficients='signed Q15 amplitude32767, quarter-wave table; Hann RNE((32767-cos)/2)',
        arithmetic='48bit DFT accumulation, RNE >>8 complex32, square uint64 RNE >>8, sum156; log2 LUT10 bits output Q12 in PCM-count-squared units',final_test_opened=False))
    powers=[];logs=[];stats=[]
    for start in range(0,len(rows),8):
        pcm=[]
        for r in rows[start:start+8]:
            path=ROOT/r['local'];assert sha(path)==r['npy_sha256'];x=np.load(path,allow_pickle=False)
            assert x.shape==(160000,) and x.dtype==np.int16;pcm.append(x[:159744])
        p,s=integer_power(np.stack(pcm));q=power_log_q12(p);powers.append(p);logs.append(q);stats.append(s)
        if (start+8)%64==0:print('integer DSP',start+8,'/1152',flush=True)
    np.save(out/'power-sum.npy',np.concatenate(powers));np.save(out/'log-q12.npy',np.concatenate(logs))
    dump(out/'receipt.json',dict(passed=True,rows=rows,stats=stats,source_sha256=sha(ROOT/'src/vibfpga/known_fixed.py'),
        protocol_sha256=sha(out/'protocol.json'),power_sha256=sha(out/'power-sum.npy'),log_sha256=sha(out/'log-q12.npy'),final_audio_read=False))
    print('COMPLETE exact integer DSP1152; center saturations',sum(s['center_saturated'] for s in stats),flush=True)
if __name__=='__main__':
    with threadpool_limits(limits=2):main()
