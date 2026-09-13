#!/usr/bin/env python3
"""Run the independent protocol suite with frozen models and LANES 1/4."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from cocotb_tools.runner import get_runner
import cocotb

from build_support import get_space_safe_runner, configure_verilator_environment, CachedRunner, add_run_arguments, run_path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/protocol_edges"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    configure_verilator_environment()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=["baseline","neighbor","all"],default="all")
    parser.add_argument("--lanes",type=int,choices=[1,4],nargs="+",default=[1,4])
    add_run_arguments(parser)
    args = parser.parse_args()
    OUT = run_path(args, "protocol_edges")
    (OUT/"report.json").unlink(missing_ok=True)
    models = {"baseline":ROOT/"artifacts/model/model.json",
              "neighbor":ROOT/"artifacts/model_neighbor/model.json"}
    selected = models if args.model=="all" else {args.model:models[args.model]}
    OUT.mkdir(parents=True,exist_ok=True)
    results = []
    os.environ["COCOTB_TRUST_INERTIAL_WRITES"] = "1"
    sys.path[:0] = [str(ROOT/"src"),str(ROOT/"sim")]
    for label, model_path in selected.items():
        model = json.loads(model_path.read_text())
        if model["n"] != 1024:
            raise ValueError("This protocol supplement requires frozen N=1024 CWRU models")
        bands = 3 if model.get("feature_mode")=="neighbor3_energy" else 1
        vector_dir = ROOT/"artifacts"/("vectors_neighbor" if bands==3 else "vectors")
        sources = [ROOT/"rtl/core/vib_coeff_rom.sv",ROOT/"rtl/core/vibration_core.sv"]
        files = [*sources,model_path,Path(__file__).resolve(),ROOT/"sim/test_protocol_edges.py",
                 ROOT/"src/vibfpga/fixed.py",*sorted(model_path.parent.glob("*.hex")),
                 *sorted(vector_dir.glob("replay_*.json")),*sorted(vector_dir.glob("replay_*.hex"))]
        for lanes in dict.fromkeys(args.lanes):
            build = OUT/f"{label}_l{lanes}"
            build.mkdir(parents=True,exist_ok=True)
            report_path = build/"report.json"
            xml_path = build/"results.xml"
            report_path.unlink(missing_ok=True)
            xml_path.unlink(missing_ok=True)
            inputs = {(str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)):sha(p) for p in files}
            started = time.monotonic()
            runner = CachedRunner(args.build_root)
            runner.build(sources=sources,hdl_toplevel="vibration_core",build_dir=build,
                parameters={"N":1024,"LANES":lanes,"BANDS":bands,"HIDDEN_SHIFT":model["hidden_shift"],
                            "MODEL_DIR":f'"{model_path.parent}"'},
                build_args=["--assert","-DVIB_ASSERT","-Wno-fatal","-Wno-WIDTHEXPAND",
                            "-Wno-WIDTHTRUNC","-CFLAGS","-std=c++17"],
                always=True,log_file=build/"build.log")
            runner.test(hdl_toplevel="vibration_core",test_module="test_protocol_edges",
                build_dir=build,test_dir=build,results_xml=str(xml_path),log_file=build/"simulation.log",
                extra_env={"EDGE_MODEL":str(model_path),"EDGE_LANES":str(lanes),"EDGE_REPORT":str(report_path),
                           "PYTHONPATH":os.pathsep.join([str(ROOT/"src"),str(ROOT/"sim")]),
                           "COCOTB_TRUST_INERTIAL_WRITES":"1"})
            tree = ET.parse(xml_path)
            tests = list(tree.iter("testcase"))
            if len(tests)!=1 or list(tree.iter("failure")) or list(tree.iter("error")) or list(tree.iter("skipped")):
                raise RuntimeError(f"Protocol regression did not pass: {xml_path}")
            report = json.loads(report_path.read_text())
            if report.get("status")!="passed":
                raise RuntimeError(f"Successful simulation report missing: {report_path}")
            if any(sha(ROOT/p)!=digest for p,digest in inputs.items()):
                raise RuntimeError("A model, vector or implementation changed during the protocol run")
            report.update({"model":label,"model_sha256":sha(model_path),"input_sha256":inputs,
                           "seconds_including_build":time.monotonic()-started,
                           "source_inputs_unchanged":True})
            report_path.write_text(json.dumps(report,indent=2)+"\n")
            results.append({"model":label,"lanes":lanes,"status":"passed",
                            "report":(str(report_path.relative_to(ROOT)) if report_path.is_relative_to(ROOT) else str(report_path)),"model_sha256":sha(model_path),
                            "input_accepted_beats":report["input_accepted_beats"],
                            "valid_output_frames":report["output_handshakes"],
                            "protocol_errors":report["protocol_errors"],
                            "seconds_including_build":report["seconds_including_build"]})
            print(f"{label} LANES={lanes}: PASS, 9 exact outputs, 2 expected protocol errors",flush=True)
    aggregate = {"schema_version":1,"suite":"independent_protocol_edges",
                 "generated_utc":datetime.now(timezone.utc).isoformat(),"results":results,
                 "complete_four_configuration_suite":{(r["model"],r["lanes"]) for r in results}==
                     {(m,l) for m in models for l in (1,4)},
                 "tools":{"verilator":subprocess.check_output(["verilator","--version"],text=True).strip(),
                          "cocotb":cocotb.__version__,"python":platform.python_version()},
                 "original_coverage_database_modified":False,"coverage_percentage_recomputed":False,
                 "physical_hardware_tested":False}
    (OUT/"report.json").write_text(json.dumps(aggregate,indent=2)+"\n")
    print(OUT/"report.json")


if __name__=="__main__":
    main()
