"""Pin-level ADXL345 -> shared RTL classifier -> committed Flash regression."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from cocotb_tools.runner import get_runner

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_support import CachedRunner, add_run_arguments, run_path, yosys_quote
sys.path.insert(0,str(ROOT/"scripts"))
from build_field import SOURCES


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lanes",type=int,choices=(1,4),default=1)
    p.add_argument("--model",type=Path,default=ROOT/"build/field_fixture/trained/model/model.json")
    p.add_argument("--case",choices=("nominal","gap","wrong_id","watchdog","interrupted","dirty_log","all"),default="all")
    add_run_arguments(p)
    a=p.parse_args()
    path=a.model.resolve();model=json.loads(path.read_text())
    cases=["nominal","gap","wrong_id","watchdog","interrupted","dirty_log"] if a.case=="all" else [a.case]
    reports=[]
    if a.case=="all":
        (run_path(a, f"field_system_l{a.lanes}")/"summary.json").unlink(missing_ok=True)
    for case in cases:
        build=run_path(a, f"field_system_l{a.lanes}")/case;build.mkdir(parents=True,exist_ok=True)
        model_hash=hashlib.sha256(path.read_bytes()).hexdigest()
        total=773 if case=="nominal" else 529 if case=="gap" else 256
        report=build/"report.json";report.unlink(missing_ok=True)
        xml=build/"results.xml";xml.unlink(missing_ok=True)
        runner=CachedRunner(a.build_root)
        runner.build(sources=[ROOT/s for s in SOURCES],hdl_toplevel="field_system",build_dir=build,
            parameters={"LANES":a.lanes,"MODEL_DIR":f'"{path.parent}"',"HIDDEN_SHIFT":model["hidden_shift"],
                        "MODEL_HASH":f"256'h{int.from_bytes(bytes.fromhex(model_hash),'little'):064x}",
                        "AXIS":2,"TOTAL_SAMPLES":total,"LOG_SCAN_CHUNK_SHIFT":15 if case=="dirty_log" else 6,"SENSOR_POWERUP_CYCLES":8,
                        "WATCHDOG_CYCLES":60000},
            build_args=["--assert","-DVIB_ASSERT","-Wno-fatal","-Wno-WIDTHEXPAND","-Wno-WIDTHTRUNC","-CFLAGS","-std=c++17"],
            always=True,log_file=build/"build.log")
        runner.test(hdl_toplevel="field_system",test_module="test_field_system",test_dir=build,
            results_xml=xml,log_file=build/"test.log",
            extra_env={"FIELD_CASE":case,"FIELD_TOTAL":str(total),"FIELD_MODEL":str(path),"FIELD_REPORT":str(report),
                       "PYTHONPATH":os.pathsep.join([str(ROOT/"src"),str(ROOT/"sim")])})
        tree=ET.parse(xml)
        if not list(tree.iter("testcase")) or list(tree.iter("failure")) or list(tree.iter("error")):
            raise RuntimeError(f"failed cocotb report {xml}")
        result=json.loads(report.read_text())
        if not result.get("passed"):raise RuntimeError("field system check failed")
        reports.append(result)
        print(report,flush=True)
    if a.case=="all":
        inputs=[ROOT/s for s in SOURCES]+[path,ROOT/"sim/test_field_system.py",ROOT/"sim/run_field_system.py"]
        (run_path(a, f"field_system_l{a.lanes}")/"summary.json").write_text(json.dumps({"passed":True,
            "physical_hardware_tested":False,"lanes":a.lanes,"reports":reports,
            "source_sha256":{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}},indent=2)+"\n")


if __name__=="__main__":main()
