#!/usr/bin/env python3
"""Collect real Verilator HDL coverage without changing core RTL or models."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "sim"), str(ROOT / "scripts")]
from build_core import require_passed


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def run(command, log, env):
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w") as stream:
        stream.write("COMMAND " + json.dumps(list(map(str, command))) + "\n")
        stream.flush()
        subprocess.run(list(map(str, command)), cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)


def dsp_only(build, model, lanes):
    """Reuse one instrumented executable, with independent XML/report/data."""
    from cocotb_tools.runner import get_runner
    output = build.parent / "dsp"
    output.mkdir(parents=True, exist_ok=True)
    for name in ("coverage.dat", "regression.json", "results.xml"):
        (output / name).unlink(missing_ok=True)
    manifest = build / "build_manifest.json"
    if manifest.is_file():
        from build_support import require_unchanged
        receipt = json.loads(manifest.read_text())
        require_unchanged(receipt["manifest"]["input_sha256"])
        compiled = Path(receipt["compiler_directory"])
        complete = json.loads((compiled / "complete.json").read_text())
        if sha(compiled / "vibration_core") != complete["executable_sha256"]:
            raise RuntimeError("Instrumented executable changed")
    else:
        compiled = build
    get_runner("verilator").test(
        hdl_toplevel="vibration_core", hdl_toplevel_lang="verilog", test_module="test_core", build_dir=compiled, test_dir=output,
        test_args=["--coverage-per-instance"],
        extra_env={"CORE_MODEL": str(model), "CORE_LANES": str(lanes), "CORE_DSP_CASES": "1",
                   "CORE_FRAMES": "10", "CORE_REPORT": str(output / "regression.json"),
                   "PYTHONPATH": os.pathsep.join([str(ROOT / "src"), str(ROOT / "sim")]),
                   "COCOTB_TRUST_INERTIAL_WRITES": "1"})
    require_passed(output, output / "regression.json")
    if not (output / "coverage.dat").is_file():
        raise RuntimeError("DSP regression did not write HDL coverage")


def points(path):
    """Read Coverage-3 points without modifying/filtering the source data."""
    result = []
    for line in path.read_text().splitlines():
        if line.startswith("C '"):
            key, count = line[3:].rsplit("' ", 1)
            row = dict(field.split("\x02", 1) for field in key.split("\x01") if "\x02" in field)
            row["count"] = int(count)
            result.append(row)
    if not result:
        raise ValueError(f"No HDL coverage points in {path}")
    return result


def summarize(rows):
    result = {}
    for kind in sorted({row.get("t", "unknown") for row in rows}):
        selected = [row for row in rows if row.get("t", "unknown") == kind]
        hit = sum(row["count"] >= max(1, int(row.get("s", "1"))) for row in selected)
        result[kind] = {"hit_points": hit, "total_points": len(selected), "percent": 100 * hit / len(selected)}
    for kind in ("fsm_state", "fsm_arc", "user"):
        result.setdefault(kind, {"hit_points": 0, "total_points": 0, "percent": None,
                                 "status": "not instrumented; no coverage claim"})
    return result


def junit(path):
    tree = ET.parse(path)
    cases = list(tree.iter("testcase"))
    if not cases or list(tree.iter("failure")) or list(tree.iter("error")) or list(tree.iter("skipped")):
        raise ValueError(f"Coverage is not acceptable evidence from a failing/incomplete suite: {path}")
    return {"tests": len(cases), "passed": len(cases), "cases": [case.attrib["name"] for case in cases]}


def collect(output, inputs, tool, env, report_paths):
    output.mkdir(parents=True, exist_ok=True)
    commands = [
        [tool, "--write", output / "merged.dat", *inputs],
        [tool, "--write-info", output / "coverage.info", output / "merged.dat"],
        [tool, "--annotate", output / "annotated", "--annotate-all", "--annotate-min", "1", "--annotate-points", output / "merged.dat"],
        [tool, "--report", "summary", "--include-reset-arcs", output / "merged.dat"],
    ]
    for index, command in enumerate(commands):
        run(command, output / f"coverage_tool_{index}.log", env)
    rows = points(output / "merged.dat")
    uncovered = [row for row in rows if row["count"] < max(1, int(row.get("s", "1")))]
    write(output / "uncovered_points.json", uncovered)
    by_file = {name: summarize([row for row in rows if row.get("f") == name]) for name in sorted({row["f"] for row in rows})}
    reports = []
    for path in report_paths:
        reports.append({"report": (str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)), "report_sha256": sha(path),
                        "xml_sha256": sha(path.parent / "results.xml"),
                        "tests": junit(path.parent / "results.xml"), "result": json.loads(path.read_text())})
    summary = {"status": "passed", "coverage_types": summarize(rows), "per_file": by_file,
               "sources": [{"path": (str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)), "sha256": sha(path)} for path in inputs],
               "reports": reports, "threshold": "one hit per tool-generated point (or point-specific threshold if present)",
               "excluded_points": 0, "coverage_source_filters": [], "per_instance_requested_at_compile_and_runtime": True,
               "startup_and_reset_activity_included": True,
               "merged_data_sha256": sha(output / "merged.dat"), "lcov_sha256": sha(output / "coverage.info"),
               "uncovered_points_sha256": sha(output / "uncovered_points.json")}
    write(output / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-root", type=Path, default=ROOT / "build/rtl_coverage")
    parser.add_argument("--run-id", help="Isolate coverage outputs under BUILD_ROOT/runs/ID")
    parser.add_argument("--collect-only", action="store_true", help="Summarize already-passed local coverage runs without rerunning simulation")
    parser.add_argument("--dsp-only", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--build-dir", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--model", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--lanes", type=int, choices=(1, 4), help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.dsp_only:
        dsp_only(args.build_dir.resolve(), args.model.resolve(), args.lanes)
        return
    started = time.monotonic()
    from build_support import run_path
    base = run_path(args, "")
    base.mkdir(parents=True, exist_ok=True)
    (base/"coverage_report.json").unlink(missing_ok=True)
    env = dict(os.environ)
    suite = ROOT / ".tools/oss-cad-suite"
    env["PATH"] = str(suite / "bin") + os.pathsep + env.get("PATH", "")
    from build_support import configure_verilator_environment
    configure_verilator_environment()
    env["VERILATOR_ROOT"] = os.environ["VERILATOR_ROOT"]
    env["VERILATOR_BIN"] = os.environ["VERILATOR_BIN"]
    tool = suite / "bin/verilator_coverage"
    sources = [ROOT / name for name in ("rtl/core/vibration_core.sv", "rtl/core/vib_coeff_rom.sv", "sim/test_core.py",
               "sim/test_arithmetic.py", "sim/arithmetic_tb.sv", "src/vibfpga/fixed.py", "scripts/build_core.py",
               "scripts/run_core_coverage.py", "scripts/build_support.py")]
    sources += [path for name in ("artifacts/model", "artifacts/model_neighbor", "artifacts/vectors", "artifacts/vectors_neighbor")
                for path in (ROOT / name).glob("*") if path.is_file()]
    source_hashes = {(str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)): sha(path) for path in sources}
    version = subprocess.check_output([suite / "bin/verilator", "--version"], env=env, text=True).strip()
    configurations = [(lanes, bands, ROOT / ("artifacts/model_neighbor/model.json" if bands == 3 else "artifacts/model/model.json"))
                      for bands in (1, 3) for lanes in (1, 4)]
    run_manifest = {"started_utc": datetime.now(timezone.utc).isoformat(), "verilator_version": version,
                    "cocotb_version": importlib.metadata.version("cocotb"), "source_sha256": source_hashes,
                    "compile_flags": ["--coverage", "--coverage-per-instance", "--assert", "-DVIB_ASSERT"],
                    "runtime_flags": ["--coverage-per-instance"], "hardware_access": False,
                    "normal_frames_per_configuration": 14, "DSP_frames_per_configuration": 10}
    if not args.collect_only:
        write(base / "run_manifest.json", run_manifest)

        def one(config):
            lanes, bands, model = config
            folder = base / f"l{lanes}_b{bands}"
            run([sys.executable, ROOT / "scripts/build_core.py", "--coverage", "--build-dir", folder / "normal",
                 "--lanes", lanes, "--model", model, "--frames", "14"], folder / "normal.log", env)
            print(f"l{lanes}/b{bands}: normal + protocol/stall/reset PASS", flush=True)
            run([sys.executable, Path(__file__), "--dsp-only", "--build-dir", folder / "normal", "--model", model,
                 "--lanes", lanes], folder / "dsp.log", env)
            print(f"l{lanes}/b{bands}: DSP + protocol/stall/reset PASS", flush=True)

        with ThreadPoolExecutor(max_workers=2) as pool:
            for future in as_completed([pool.submit(one, configuration) for configuration in configurations]):
                future.result()
        run([sys.executable, ROOT / "scripts/build_core.py", "--coverage", "--build-dir", base / "arithmetic",
             "--arithmetic", "--model", ROOT / "artifacts/model/model.json"], base / "arithmetic.log", env)
        run([sys.executable, ROOT / "scripts/build_core.py", "--coverage", "--build-dir", base / "quant_boundary",
             "--quant-boundary", "--lanes", "4", "--frames", "5", "--model", ROOT / "artifacts/model_neighbor/model.json"],
             base / "quant_boundary.log", env)
        print("Separate direct arithmetic and serial quantizer boundary suites PASS", flush=True)
    else:
        stored = json.loads((base / "run_manifest.json").read_text())
        if stored["source_sha256"] != source_hashes or stored["verilator_version"] != version:
            raise ValueError("Source/model/tool drift: existing coverage cannot describe the current inputs")
    if any(sha(ROOT / name) != checksum for name, checksum in source_hashes.items()):
        raise ValueError("An instrumented source or frozen model changed during coverage collection")
    summaries = {}
    for lanes, bands, model in configurations:
        name = f"l{lanes}_b{bands}"
        folder = base / name
        summary = collect(folder / "coverage", [folder / kind / "coverage.dat" for kind in ("normal", "dsp")], tool, env,
                          [folder / kind / "regression.json" for kind in ("normal", "dsp")])
        summary.update(lanes=lanes, bands=bands, model_sha256=sha(model))
        summaries[name] = summary
    boundary = base / "quant_boundary"
    summaries["serial_quantizer_boundary_profile"] = collect(boundary / "coverage", [boundary / "coverage.dat"], tool, env,
                                                             [boundary / "regression.json"])
    arithmetic = base / "arithmetic/arithmetic"
    summaries["direct_arithmetic_functions"] = collect(arithmetic / "coverage", [arithmetic / "coverage.dat"], tool, env,
                                                       [arithmetic / "arithmetic.json"])
    report = {"status": "passed", "generated_utc": datetime.now(timezone.utc).isoformat(), "verilator_version": version,
              "seconds": time.monotonic() - started, "configurations": summaries,
              "source_sha256": source_hashes, "run_manifest_sha256": sha(base / "run_manifest.json"),
              "merge_rule": "Only normal and DSP runs with identical LANES/BANDS/model are merged. Parameter variants, deliberate boundary profile and direct function harness remain separate.",
              "physical_hardware_tested": False,
              "limits": ["Tool-generated HDL points, not Python coverage and not formal reachability proof.",
                         "No point waivers or source filters were applied; unreachable/configuration-specific points remain in the raw denominators.",
                         "Default Verilator toggle width/local-variable omissions remain in effect; startup/reset transitions are included.",
                         "Zero FSM/user points mean not instrumented, never 100% complete."]}
    write(base / "coverage_report.json", report)
    print(json.dumps({name: row["coverage_types"] for name, row in summaries.items()}, indent=2), flush=True)


if __name__ == "__main__":
    main()
