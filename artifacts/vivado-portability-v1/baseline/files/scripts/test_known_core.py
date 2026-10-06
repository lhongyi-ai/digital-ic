#!/usr/bin/env python3
"""Build a bounded functional fixture or the full deployment-dimension core."""
import argparse,json,os,sys,math
from pathlib import Path
import numpy as np
import xml.etree.ElementTree as ET
from build_support import CachedRunner
from train_known_release import hexfile
from vibfpga.known_fixed import tables
from experiment_acoustic_v2 import sha,dump
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--n',type=int,default=16);p.add_argument('--windows',type=int,default=2)
    p.add_argument('--lanes',type=int,choices=(1,4),default=4);p.add_argument('--machine',default='00');p.add_argument('--run-id',required=True);a=p.parse_args()
    assert a.n in (16,1024) and 1<=a.windows<=156
    base=ROOT/f'artifacts/acoustic-known-release-v1/id{a.machine}'
    m=json.loads((base/'model.json').read_text());out=ROOT/'build/known-core'/a.run_id;out.mkdir(parents=True,exist_ok=False)
    model=out/'model';model.mkdir();f=a.n//2
    for name,bits in [('mean_q12',32),('gain_q24',32),('weights',8)]:hexfile(model/(name+'.hex'),m[name][:f],bits)
    hexfile(model/'cos_quarter.hex',tables(a.n)[0],16)
    hexfile(model/'log_lut.hex',np.rint(np.log2(1+np.arange(1024)/1024)*4096).astype(int),12)
    m.update(n=a.n,windows=a.windows,features=f,lanes=a.lanes,fixture=a.n!=1024 or a.windows!=156)
    dump(model/'model.json',m)
    sources=[ROOT/'rtl/core/vib_coeff_rom.sv',ROOT/'rtl/platform/spram16k.sv',ROOT/'rtl/core/known_capture.sv',ROOT/'rtl/core/known_spectral_core.sv']
    paths=sources+[Path(__file__),ROOT/'sim/test_known_core.py',ROOT/'src/vibfpga/known_fixed.py',*model.glob('*')]
    bindings={str(p.relative_to(ROOT)):sha(p) for p in paths}
    runner=CachedRunner(ROOT/'build/known-core-cache')
    runner.build(sources=sources,hdl_toplevel='known_spectral_core',build_dir=out,
        parameters=dict(N=a.n,WINDOWS=a.windows,LANES=a.lanes,MODEL_DIR=f'"{model}"',BIAS=m['bias'],THRESHOLD=m['threshold'],
            LOG_CONSTANT=round((4+2*math.log2(a.n)+math.log2(a.windows))*4096),LOG_FLOOR=m['log_floor_q12']),
        build_args=['-CFLAGS','-std=c++17','--timing','--assert','-DVIB_ASSERT','-Wno-fatal','-Wno-WIDTHEXPAND','-Wno-WIDTHTRUNC'],always=True,log_file=out/'build.log')
    sys.path.insert(0,str(ROOT/'sim'))
    runner.test(hdl_toplevel='known_spectral_core',test_module='test_known_core',test_dir=out,results_xml=out/'results.xml',log_file=out/'test.log',
        extra_env={'KNOWN_MODEL':str(model/'model.json'),'KNOWN_REPORT':str(out/'report.json'),'PYTHONPATH':os.pathsep.join([str(ROOT/'src'),str(ROOT/'sim')])})
    tree=ET.parse(out/'results.xml').getroot()
    assert list(tree.iter('testcase')) and not list(tree.iter('failure')) and not list(tree.iter('error')),'See test.log'
    assert all(sha(ROOT/p)==h for p,h in bindings.items())
    report=json.loads((out/'report.json').read_text());report.update(passed=True,bindings=bindings,lanes=a.lanes,fixture=m['fixture'])
    dump(out/'report.json',report);print(json.dumps(report|{'bindings':'saved in report.json'}))
if __name__=='__main__':main()
