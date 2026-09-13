#!/usr/bin/env python3
"""Build and test the separate N256 sensor classifier, without a board."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_support import CachedRunner, add_run_arguments, run_path, yosys_quote


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lanes", type=int, nargs="+", choices=(1, 4), default=[1, 4])
    parser.add_argument("--model", type=Path, default=ROOT / "build/field_fixture/trained/model/model.json")
    add_run_arguments(parser)
    args = parser.parse_args()
    model_path = args.model.resolve()
    model = json.loads(model_path.read_text())
    if (model["n"] != 256 or model.get("feature_mode", "single_bin") != "single_bin"
            or len(model["bins"]) != 16 or len(model["b1"]) != 16 or len(model["b2"]) != 3):
        parser.error("sensor_classifier requires N256 / 16 features / 16 hidden / 3 classes / BANDS1")
    from cocotb_tools.runner import get_runner
    sys.path[:0] = [str(ROOT / "sim"), str(ROOT / "src")]
    sources = [ROOT / "rtl/core/vib_coeff_rom.sv", ROOT / "rtl/core/vibration_core.sv",
               ROOT / "rtl/core/sync_fifo.sv", ROOT / "rtl/io/sensor_classifier.sv"]
    inputs = sources + [Path(__file__).resolve(), ROOT / "sim/test_sensor_classifier.py",
                       ROOT / "src/vibfpga/field.py", ROOT / "src/vibfpga/fixed.py"]
    input_hashes = {str(p.relative_to(ROOT)): digest(p) for p in inputs}
    model_hashes = {str(p.relative_to(model_path.parent)): digest(p)
                    for p in sorted(model_path.parent.iterdir()) if p.is_file()}
    for lanes in dict.fromkeys(args.lanes):
        build = run_path(args, f"sensor_classifier_l{lanes}")
        build.mkdir(parents=True, exist_ok=True)
        summary_path, xml_path = build / "regression.json", build / "results.xml"
        summary_path.unlink(missing_ok=True)
        xml_path.unlink(missing_ok=True)
        for path in build.glob("case_*.json"):
            path.unlink()
        manifest = {"n": 256, "lanes": lanes, "bands": 1, "hidden_shift": model["hidden_shift"],
                    "model": str(model_path), "model_sha256": digest(model_path),
                    "model_file_sha256": model_hashes, "source_sha256": input_hashes,
                    "model_training_status": model.get("training_status", "unknown"),
                    "model_source_kind": model.get("source_kind", "unknown"),
                    "assertions_enabled": True, "physical_board_tested": False,
                    "simulator": subprocess.check_output(["verilator", "--version"], text=True).strip()}
        manifest_path = build / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        runner = CachedRunner(args.build_root)
        runner.build(sources=sources, hdl_toplevel="sensor_classifier", build_dir=build / "compiled",
                     parameters={"LANES": lanes, "MODEL_DIR": f'"{model_path.parent}"',
                                 "HIDDEN_SHIFT": model["hidden_shift"]},
                     build_args=["--assert", "-DVIB_ASSERT", "-Wno-fatal", "-Wno-WIDTHEXPAND",
                                 "-Wno-WIDTHTRUNC", "-CFLAGS", "-std=c++17"],
                     always=True, log_file=build / "compile.log")
        runner.test(hdl_toplevel="sensor_classifier", test_module="test_sensor_classifier",
                    test_dir=build, results_xml=str(xml_path), log_file=build / "simulation.log",
                    extra_env={"SENSOR_CLASSIFIER_MANIFEST": str(manifest_path),
                               "SENSOR_CLASSIFIER_BUILD": str(build),
                               "PYTHONPATH": os.pathsep.join([str(ROOT / "sim"), str(ROOT / "src")]),
                               "COCOTB_TRUST_INERTIAL_WRITES": "1"})
        tree = ET.parse(xml_path)
        tests = list(tree.iter("testcase"))
        if len(tests) != 4 or any(list(tree.iter(tag)) for tag in ("failure", "error", "skipped")):
            raise RuntimeError(f"four passing executed tests required: {xml_path}")
        paths = sorted(build.glob("case_*.json"))
        reports = [json.loads(p.read_text()) for p in paths]
        if len(reports) != 4 or any(r.get("status") != "passed" for r in reports):
            raise RuntimeError("all four fresh test reports are required")
        assert {str(p.relative_to(ROOT)): digest(p) for p in inputs} == input_hashes, "sources changed during test"
        assert {str(p.relative_to(model_path.parent)): digest(p)
                for p in sorted(model_path.parent.iterdir()) if p.is_file()} == model_hashes, "model files changed"
        summary = {**manifest, "status": "passed", "tests": len(tests),
                   "checked_outputs": sum(len(r["outputs"]) for r in reports),
                   "case_reports": {p.name: digest(p) for p in paths},
                   "xml_sha256": digest(xml_path),
                   "evidence_boundary": "synthetic raw-count vectors; no sensor/SPI/physical board execution"}
        summary_path.write_text(json.dumps(summary, indent=2) + "\n")
        print(f"PASS LANES={lanes}: four tests, {summary['checked_outputs']} checked outputs; {summary_path}", flush=True)


if __name__ == "__main__":
    main()
