#!/usr/bin/env python3
"""Actual SPI transport + actual spectral core + NOR protocol-model regression."""
import argparse,json,math,os,sys,subprocess
from pathlib import Path
import numpy as np
import xml.etree.ElementTree as ET
from build_support import CachedRunner,cached_native_build
from build_known_board import SOURCES
from train_known_release import hexfile
from vibfpga.known_fixed import tables,integer_power,power_log_q12,rne_shift
from vibfpga.known_board import build_image,parse_log
from threadpoolctl import threadpool_limits
from experiment_acoustic_v2 import sha,dump
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True)
    p.add_argument('--production',action='store_true');p.add_argument('--machine',choices=('00','02','04','06'),default='00')
    p.add_argument('--label',type=int,choices=(0,1),default=0);p.add_argument('--lanes',type=int,choices=(1,4),default=4)
    p.add_argument('--period',type=int,default=750);a=p.parse_args()
    out=ROOT/'build/known-flash'/a.run_id;out.mkdir(parents=True,exist_ok=False)
    if a.production:return production(a,out)
    model=out/'model';model.mkdir();n=16;windows=4
    m=json.loads((ROOT/'artifacts/acoustic-known-release-v1/id00/model.json').read_text())
    for name,bits in [('mean_q12',32),('gain_q24',32),('weights',8)]:hexfile(model/(name+'.hex'),m[name][:n//2],bits)
    hexfile(model/'cos_quarter.hex',tables(n)[0],16)
    hexfile(model/'log_lut.hex',np.rint(np.log2(1+np.arange(1024)/1024)*4096).astype(int),12)
    m.update(n=n,windows=windows,features=n//2,lanes=4,fixture=True,log_constant_q12=round((4+2*math.log2(n)+math.log2(windows))*4096))
    dump(model/'model.json',m)
    bindings={str(p.relative_to(ROOT)):sha(p) for p in [*[ROOT/s for s in SOURCES],Path(__file__),ROOT/'sim/test_known_flash.py',
        ROOT/'sim/test_flash_system.py',ROOT/'src/vibfpga/known_board.py',ROOT/'src/vibfpga/known_fixed.py',*model.glob('*')]}
    dump(out/'attempt.json',dict(stage='started',bindings=bindings,fixture=True))
    runner=CachedRunner(ROOT/'build/known-flash-cache')
    runner.build(sources=[ROOT/s for s in SOURCES],hdl_toplevel='known_replay_system',build_dir=out,
        parameters=dict(N=n,WINDOWS=windows,LANES=4,MODEL_DIR=f'"{model}"',BIAS=m['bias'],THRESHOLD=m['threshold'],
            LOG_CONSTANT=m['log_constant_q12'],LOG_FLOOR=m['log_floor_q12'],MODEL_HASH=f"256'h{bytes.fromhex(sha(model/'model.json'))[::-1].hex()}"),
        build_args=['--timing','--assert','-DVIB_ASSERT','-Wno-fatal','-Wno-WIDTHEXPAND','-Wno-WIDTHTRUNC','-CFLAGS','-std=c++17'],
        always=True,log_file=out/'build.log')
    sys.path.insert(0,str(ROOT/'sim'))
    runner.test(hdl_toplevel='known_replay_system',test_module='test_known_flash',test_dir=out,results_xml=out/'results.xml',log_file=out/'test.log',
        extra_env={'KNOWN_MODEL':str(model/'model.json'),'KNOWN_REPORT':str(out/'report.json'),
            'PYTHONPATH':os.pathsep.join([str(ROOT/'src'),str(ROOT/'sim')])})
    tree=ET.parse(out/'results.xml').getroot();assert list(tree.iter('testcase')) and not list(tree.iter('failure')) and not list(tree.iter('error')),'See test.log'
    assert all(sha(ROOT/p)==h for p,h in bindings.items())
    report=json.loads((out/'report.json').read_text());report.update(passed=True,bindings=bindings)
    dump(out/'report.json',report);print(json.dumps(report|{'bindings':'saved'}))
def production(a,out):
    model=ROOT/f'artifacts/acoustic-known-release-v1/id{a.machine}';model_bytes=(model/'model.json').read_bytes();m=json.loads(model_bytes)
    freeze=json.loads((model.parent/'model-freeze.json').read_text());assert all(sha(ROOT/p)==h for p,h in freeze['sha256'].items())
    records=json.loads((ROOT/'data/mimii-known-machines-v1/development.json').read_text())['records']
    row=next(r for r in records if r['machine']==a.machine and r['label']==a.label and r['role']=='cv')
    pcm=ROOT/row['local'];assert sha(pcm)==row['npy_sha256'];raw=np.load(pcm,allow_pickle=False)[:159744]
    power,_=integer_power(raw[None,:]);log=power_log_q12(power)[0]
    feature=np.clip(rne_shift((log-np.array(m['mean_q12']))*np.array(m['gain_q24']),24),-127,127)
    expected=int(feature@np.array(m['weights'])+m['bias'])
    image=out/'input.bin';image.write_bytes(build_image(raw,model_bytes,a.period))
    paths=[*[ROOT/s for s in SOURCES],ROOT/'sim/known_flash_main.cpp',Path(__file__),ROOT/'src/vibfpga/known_board.py',
           ROOT/'src/vibfpga/known_fixed.py',*model.glob('*.hex'),model/'model.json',image,pcm]
    bindings={str(p.relative_to(ROOT)):sha(p) for p in paths};dump(out/'attempt.json',dict(stage='started',bindings=bindings,record=row))
    params=dict(LANES=a.lanes,MODEL_DIR=f'"{model}"',BIAS=m['bias'],THRESHOLD=m['threshold'],LOG_CONSTANT=m['log_constant_q12'],
                LOG_FLOOR=m['log_floor_q12'],MODEL_HASH=f"256'h{bytes.fromhex(sha(model/'model.json'))[::-1].hex()}")
    sources=[*[ROOT/s for s in SOURCES],ROOT/'sim/known_flash_main.cpp']
    flags=['--cc','--exe','-O3','--assert','-DVIB_ASSERT','-Wno-fatal','-Wno-WIDTHEXPAND','-Wno-WIDTHTRUNC','--top-module','known_replay_system','-CFLAGS','-std=c++17 -O3']
    exe,_=cached_native_build(ROOT/'build',out/'native',sources,params,flags,
        lambda directory:['verilator',*flags,'--Mdir',str(directory),*[f'-G{k}={v}' for k,v in params.items()],*map(str,sources)],'known_replay_system')
    logfile=out/'output.bin'
    with (out/'test.log').open('w') as f:
        process=subprocess.run([str(exe),str(image),str(logfile),str(159744*a.period+5000000)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    assert process.returncode==0,f'native SPI failure: {out/"test.log"}'
    result=parse_log(logfile.read_bytes(),model_bytes,lanes=a.lanes,period=a.period)
    assert result['score']==expected and result['threshold']==m['threshold'],(result,expected)
    assert all(sha(ROOT/p)==h for p,h in bindings.items())
    dump(out/'report.json',dict(passed=True,fixture=False,physical_hardware=False,actual_spi_transport=True,actual_rtl_core=True,
        windows=156,samples=159744,machine=a.machine,lanes=a.lanes,period=a.period,bindings=bindings,record=row,
        result=result,output_sha256=sha(logfile)))
    print(json.dumps(result))
if __name__=='__main__':
    with threadpool_limits(limits=2):main()
