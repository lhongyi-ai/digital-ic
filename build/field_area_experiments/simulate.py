import json, os, sys, hashlib
from pathlib import Path
import xml.etree.ElementTree as ET
from cocotb_tools.runner import get_runner

root=Path(__file__).resolve().parents[2]
directory=Path(__file__).resolve().parent/sys.argv[1]
out=directory/'classifier_test'
out.mkdir(exist_ok=True)
model=root/'build/field_fixture/trained/model/model.json'
manifest=json.loads((root/'build/sensor_classifier_l4/manifest.json').read_text())
manifest['experiment']=directory.name
manifest['model']=str(model)
manifest['model_sha256']=hashlib.sha256(model.read_bytes()).hexdigest()
sources=[directory/p for p in ('rtl/core/vib_coeff_rom.sv','rtl/core/vibration_core.sv','rtl/core/sync_fifo.sv','rtl/io/sensor_classifier.sv')]
manifest['experiment_sources']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
for p in out.glob('case_*.json'):p.unlink()
for name in ('results.xml','summary.json'):(out/name).unlink(missing_ok=True)
sys.path[:0]=[str(root/'src'),str(root/'sim')]
runner=get_runner('verilator')
runner.build(sources=sources,hdl_toplevel='sensor_classifier',build_dir=out/'compiled',
 parameters={'LANES':4,'MODEL_DIR':f'"{model.parent}"','HIDDEN_SHIFT':json.loads(model.read_text())['hidden_shift']},
 build_args=['--assert','-DVIB_ASSERT','-Wno-fatal','-Wno-WIDTHEXPAND','-Wno-WIDTHTRUNC','-CFLAGS','-std=c++17'],
 always=True,log_file=out/'compile.log')
runner.test(hdl_toplevel='sensor_classifier',test_module='test_sensor_classifier',test_dir=out,
 results_xml=str(out/'results.xml'),log_file=out/'simulation.log',
 extra_env={'SENSOR_CLASSIFIER_MANIFEST':str(out/'manifest.json'),'SENSOR_CLASSIFIER_BUILD':str(out),
 'PYTHONPATH':os.pathsep.join([str(root/'sim'),str(root/'src')]),'COCOTB_TRUST_INERTIAL_WRITES':'1'})
tree=ET.parse(out/'results.xml')
assert len(list(tree.iter('testcase')))==4 and not any(list(tree.iter(t)) for t in ('failure','error','skipped'))
assert len(list(out.glob('case_*.json')))==4
(out/'summary.json').write_text(json.dumps({'status':'passed','tests':4,'sources':manifest['experiment_sources']},indent=2)+'\n')
print(out/'summary.json')
