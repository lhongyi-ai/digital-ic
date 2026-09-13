"""Behavioral SPI NOR plus real RTL/core/ROM end-to-end regression; no board I/O."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from cocotb_tools.runner import get_runner

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_support import CachedRunner, add_run_arguments, run_path, yosys_quote


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model",type=Path,default=ROOT/"artifacts/model/model.json")
    parser.add_argument("--lanes",type=int,choices=(1,4),default=4)
    parser.add_argument("--full-log-scan",action="store_true",help="Run one full 128 KiB production scan with a dirty last byte; normal E2E uses four 256-byte chunks")
    add_run_arguments(parser)
    args=parser.parse_args()
    model_path = args.model.resolve()
    model = json.loads(model_path.read_text())
    digest_le = int.from_bytes(hashlib.sha256(model_path.read_bytes()).digest(), "little")
    bands=3 if model.get("feature_mode")=="neighbor3_energy" else 1
    scan_shift=15 if args.full_log_scan else 8
    build = run_path(args, f"flash_system{'_neighbor' if bands==3 else ''}{'_l1' if args.lanes==1 else ''}{'_full_scan' if args.full_log_scan else ''}")
    build.mkdir(parents=True, exist_ok=True)
    (build/"regression.json").unlink(missing_ok=True)
    (build/"results.xml").unlink(missing_ok=True)
    sys.path[:0] = [str(ROOT/"src"),str(ROOT/"sim")]
    runner = CachedRunner(args.build_root)
    runner.build(sources=[ROOT/p for p in [
        "rtl/core/vib_coeff_rom.sv", "rtl/core/vibration_core.sv", "rtl/core/sync_fifo.sv",
        "rtl/platform/spram16k.sv", "rtl/io/spi_master.sv", "rtl/io/flash_stream.sv",
        "rtl/io/replay_source.sv", "rtl/upduino_replay.sv", "sim/flash_system_tb.sv"]],
        hdl_toplevel="flash_system_tb", build_dir=build,
        parameters={"MODEL_DIR": f'"{model_path.parent}"',"HIDDEN_SHIFT":model["hidden_shift"],
                    "LANES":args.lanes,"BANDS":bands,
                    "LOG_SCAN_CHUNK_SHIFT":scan_shift,
                    "MODEL_HASH":f"256'h{digest_le:064x}"},
        build_args=["--timing","--assert","-DVIB_ASSERT","-Wno-fatal","-Wno-WIDTHEXPAND","-Wno-WIDTHTRUNC","-CFLAGS","-std=c++20"],
        always=True, log_file=build/"build.log")
    runner.test(hdl_toplevel="flash_system_tb",test_module="test_flash_system",test_dir=build,
        results_xml=build/"results.xml",log_file=build/"test.log",
        extra_env={"FLASH_MODEL":str(model_path),"FLASH_ROOT":str(ROOT),"FLASH_REPORT":str(build/"regression.json"),
                   "FLASH_SCAN_SHIFT":str(scan_shift),"FLASH_FULL_SCAN":str(int(args.full_log_scan)),
                   "FLASH_VECTORS":str(ROOT/("artifacts/vectors_neighbor" if bands==3 else "artifacts/vectors")),
                   "PYTHONPATH":os.pathsep.join([str(ROOT/"src"),str(ROOT/"sim")]),
                   "COCOTB_TRUST_INERTIAL_WRITES":"1"})
    # Standalone cocotb runners can return normally after a failed HDL test.
    # A missing/failed report must therefore make this command fail explicitly.
    xml=ET.parse(build/"results.xml").getroot()
    if not list(xml.iter("testcase")) or list(xml.iter("failure")) or list(xml.iter("error")):
        raise RuntimeError("Flash regression XML reports failed or missing tests")
    report=json.loads((build/"regression.json").read_text())
    if report.get("passed") is not True:
        raise RuntimeError("Flash regression did not produce passing evidence")
    print(f"Flash simulation evidence: {build/'regression.json'}")


if __name__ == "__main__":
    main()
