#!/usr/bin/env python3
import json
import argparse
import os
from pathlib import Path
import sys
from cocotb_tools.runner import get_runner

from build_support import CachedRunner, add_run_arguments, run_path
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
add_run_arguments(parser)
args=parser.parse_args()
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"sim")]
cases=[(0,4096000),(26*256,4194304),(-127,8192),(-2147483648,2147483647)]
results=[]
run_path(args, "calibration_results.json").unlink(missing_ok=True)
for index,(offset,gain) in enumerate(cases):
    out=run_path(args, f"calibration_{index}")
    report=out/"report.json"
    report.unlink(missing_ok=True)
    (out/"results.xml").unlink(missing_ok=True)
    runner=CachedRunner(args.build_root)
    runner.build(sources=[ROOT/"rtl/io/static_calibration.sv"],hdl_toplevel="static_calibration",build_dir=out,
        parameters={"OFFSET_Q8":offset,"GAIN_Q20":gain},build_args=["-CFLAGS","-std=c++17"],always=True)
    runner.test(hdl_toplevel="static_calibration",test_module="test_calibration",test_dir=out,
        extra_env={"CAL_OFFSET":str(offset),"CAL_GAIN":str(gain),"CAL_REPORT":str(report),
                   "PYTHONPATH":os.pathsep.join([str(ROOT/"src"),str(ROOT/"sim")])})
    result=json.loads(report.read_text())
    assert result["passed"]
    results.append(result)
(run_path(args, "calibration_results.json")).write_text(json.dumps(results,indent=2)+"\n")
