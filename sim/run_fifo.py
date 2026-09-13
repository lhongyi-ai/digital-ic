"""Run actual Verilator/cocotb tests. Run from any directory with the project venv."""
import argparse
import json
import sys
import os
from pathlib import Path

from cocotb_tools.runner import get_runner

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "sim")]
from build_support import CachedRunner, add_run_arguments, run_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--depths", nargs="+", type=int, default=[1, 3, 4])
    add_run_arguments(parser)
    args = parser.parse_args()
    reports = []
    run_path(args, "fifo_scenario_coverage.json").unlink(missing_ok=True)
    for depth in args.depths:
        if depth < 1:
            parser.error("DEPTH must be positive")
        build = run_path(args, f"fifo_d{depth}")
        coverage = build / "scenario_coverage.json"
        # Remove stale evidence so an interrupted run cannot look current.
        coverage.unlink(missing_ok=True)
        runner = CachedRunner(args.build_root)
        runner.build(sources=[ROOT / "rtl/core/sync_fifo.sv"],
                     hdl_toplevel="sync_fifo", parameters={"WIDTH": 16, "DEPTH": depth},
                     build_args=["--assert", "-CFLAGS", "-std=c++17"], build_dir=build,
                     always=True, log_file=build / "build.log")
        runner.test(hdl_toplevel="sync_fifo", test_module="test_fifo",
                    test_dir=build, build_dir=build,
                    results_xml=build / "results.xml", log_file=build / "test.log",
                    extra_env={"FIFO_DEPTH": str(depth),
                               "FIFO_COVERAGE_FILE": str(coverage)})
        reports.append(json.loads(coverage.read_text()))
    target = run_path(args, "fifo_scenario_coverage.json")
    target.write_text(json.dumps({"scope": "FIFO scenario counters only; not line/toggle coverage",
                                  "runs": reports}, indent=2) + "\n")
    print(f"FIFO simulation evidence: {target}")


if __name__ == "__main__":
    main()
