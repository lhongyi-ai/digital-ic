#!/usr/bin/env python3
"""Native full-size production-window regression, with saved raw-record provenance."""
import argparse,json,struct,subprocess
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from vibfpga.known_fixed import prepare_windows,tables,rne_shift,power_log_q12,quantized_features
from experiment_acoustic_v2 import sha,dump
from build_support import cached_native_build
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--machine',default='00');p.add_argument('--clips',type=int,default=7)
    p.add_argument('--lanes',type=int,choices=(1,4),default=4);p.add_argument('--period',type=int,default=0);p.add_argument('--run-id',required=True);a=p.parse_args()
    model=ROOT/f'artifacts/acoustic-known-release-v1/id{a.machine}';m=json.loads((model/'model.json').read_text())
    freeze=json.loads((model.parent/'model-freeze.json').read_text());assert all(sha(ROOT/p)==h for p,h in freeze['sha256'].items())
    out=ROOT/'build/known-native'/a.run_id;out.mkdir(parents=True,exist_ok=False);vector=out/'vectors.bin'
    manifest=json.loads((ROOT/'data/mimii-known-machines-v1/development.json').read_text())
    pools={y:[r for r in manifest['records'] if r['machine']==a.machine and r['role']=='cv' and r['label']==y] for y in (0,1)}
    rows=[pools[k%2][k//2] for k in range(a.clips)];bindings={}
    with vector.open('wb') as f:
        f.write(struct.pack('<IIIIi',0x3150534b,1024,156,a.clips,m['threshold']))
        for r in rows:
            path=ROOT/r['local'];assert sha(path)==r['npy_sha256'];bindings[r['local']]=sha(path)
            raw=np.load(path,allow_pickle=False)[:159744];windowed,_=prepare_windows(raw[None,:])
            acc=(windowed.astype(np.float64)@tables()[3]).astype(np.int64);c=rne_shift(acc,8);re,im=np.split(c,2,axis=1)
            powers=rne_shift((re*re).astype(np.uint64)+(im*im).astype(np.uint64),8);sums=np.cumsum(powers,axis=0,dtype=np.uint64)
            qlog=power_log_q12(sums[-1:])[0];qx,_,_=quantized_features(qlog[None,:],m['mean'],m['input_scale'],m['std'])
            score=int(qx.astype(np.int64)[0]@np.array(m['weights'])+m['bias'])
            for v,dtype in [(raw,'<i2'),(windowed,'<i2'),(re,'<i4'),(im,'<i4'),(powers,'<u8'),(sums,'<u8'),(qlog,'<i4'),(qx,'i1')]:f.write(np.asarray(v,dtype=dtype).tobytes())
            f.write(struct.pack('<i',score))
    sources=[ROOT/s for s in ['rtl/core/vib_coeff_rom.sv','rtl/platform/spram16k.sv','rtl/core/known_capture.sv','rtl/core/known_spectral_core.sv','sim/known_native_main.cpp']]
    params=dict(N=1024,WINDOWS=156,LANES=a.lanes,MODEL_DIR=f'"{model}"',BIAS=m['bias'],THRESHOLD=m['threshold'],LOG_CONSTANT=m['log_constant_q12'],LOG_FLOOR=m['log_floor_q12'])
    flags=['--cc','--exe','-O3','--assert','-DVIB_ASSERT','-Wno-fatal','-Wno-WIDTHEXPAND','-Wno-WIDTHTRUNC','--top-module','known_spectral_core','-CFLAGS','-std=c++17 -O3']
    for path in [*sources,Path(__file__),ROOT/'src/vibfpga/known_fixed.py',*model.glob('*.hex'),model/'model.json',vector]:bindings[str(path.relative_to(ROOT))]=sha(path)
    dump(out/'attempt.json',dict(stage='started',bindings=bindings,records=rows,physical_hardware=False))
    exe,_=cached_native_build(ROOT/'build',out/'native',sources,params,flags,
        lambda directory:['verilator',*flags,'--Mdir',str(directory),*[f'-G{k}={v}' for k,v in params.items()],*map(str,sources)],'known_spectral_core')
    report=out/'report.json'
    with (out/'test.log').open('w') as f:result=subprocess.run([str(exe),str(vector),str(report),str(a.lanes),str(a.period)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    if result.returncode:raise RuntimeError(f'native failure {result.returncode}: {out/"test.log"}')
    assert all(sha(ROOT/p)==h for p,h in bindings.items())
    data=json.loads(report.read_text());assert data['passed'] and data['windows']==156*a.clips
    data.update(bindings=bindings,records=rows);dump(report,data)
    print(json.dumps({k:v for k,v in data.items() if k not in ('bindings','records')}))
if __name__=='__main__':
    with threadpool_limits(limits=2):main()
