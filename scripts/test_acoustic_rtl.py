#!/usr/bin/env python3
import argparse,json,os,sys,hashlib
from pathlib import Path
import xml.etree.ElementTree as ET
from build_support import CachedRunner
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--model',type=Path,default=ROOT/'artifacts/acoustic/model/model.json');p.add_argument('--lanes',type=int,choices=[1,4],default=1);p.add_argument('--frames',type=int,default=0);p.add_argument('--run-id',default='initial');a=p.parse_args();mp=a.model.resolve();m=json.loads(mp.read_text())
b=ROOT/'build/acoustic'/a.run_id/f'core_l{a.lanes}';b.mkdir(parents=True,exist_ok=True)
for name in ['results.xml','report.json']:(b/name).unlink(missing_ok=True)
sources=[ROOT/'rtl/core/vib_coeff_rom.sv',ROOT/'rtl/core/acoustic_core.sv']
inputs=sources+[mp,*mp.parent.glob('*.hex'),Path(__file__).resolve(),ROOT/'sim/test_acoustic.py',ROOT/'src/vibfpga/acoustic.py',ROOT/'src/vibfpga/fixed.py']
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
r=CachedRunner(ROOT/'build/acoustic')
r.build(sources=sources,hdl_toplevel='acoustic_core',build_dir=b,parameters={'N':m['n'],'LANES':a.lanes,'BANDS':3,'MODEL_DIR':f'"{mp.parent}"','HIDDEN_SHIFT':m['hidden_shift'],'OUTPUT_SHIFT':m['output_shift'],'INPUT_SHIFT':m['input_shift'],'LOG_FEATURES':int(m['acoustic_encoding']=='log4'),'THRESHOLD':m['threshold'],'ALARM_WINDOWS':m['alarm_windows']},build_args=['-CFLAGS','-std=c++17','--timing','--assert','-DVIB_ASSERT','-Wno-fatal','-Wno-WIDTHEXPAND','-Wno-WIDTHTRUNC'],always=True,log_file=b/'build.log')
sys.path.insert(0,str(ROOT/'sim'))
r.test(hdl_toplevel='acoustic_core',test_module='test_acoustic',test_dir=b,results_xml=b/'results.xml',log_file=b/'test.log',extra_env={'ACOUSTIC_MODEL':str(mp),'ACOUSTIC_FRAMES':str(a.frames),'ACOUSTIC_VECTORS':str(mp.parent.parent/'vectors'),'ACOUSTIC_REPORT':str(b/'report.json'),'PYTHONPATH':os.pathsep.join([str(ROOT/'src'),str(ROOT/'sim')])})
x=ET.parse(b/'results.xml').getroot()
if not list(x.iter('testcase')) or list(x.iter('failure')) or list(x.iter('error')):raise RuntimeError('acoustic HDL failed; see '+str(b/'test.log'))
report=json.loads((b/'report.json').read_text())
if not report['passed']:raise RuntimeError('missing PASS')
if any(hashlib.sha256(Path(p).read_bytes()).hexdigest()!=v for p,v in hashes.items()):raise RuntimeError('inputs changed')
report.update(input_sha256=hashes,lanes=a.lanes);(b/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':True,'frames':report['frames'],'report':str(b/'report.json')}))
