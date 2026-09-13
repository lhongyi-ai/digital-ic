#!/usr/bin/env python3
"""Independent, board-free NN boundary regression; deployed models are read-only.

Build each lane configuration once. $readmemh runs at simulator startup, so each
subsequent simulation can load a different explicitly untrained fixture into
the same build-local active_model directory without rebuilding the RTL.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

from build_support import get_space_safe_runner, configure_verilator_environment, CachedRunner, add_run_arguments, run_path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np

from vibfpga.export import export_model
from vibfpga.fixed import frontend, infer

LOW, HIGH = -(1 << 31), (1 << 31) - 1


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes(paths):
    return {(str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)): digest(p) for p in sorted(paths)}


def deployment_hashes():
    return hashes(p for name in ("model", "model_neighbor")
                  for p in (ROOT / "artifacts" / name).rglob("*") if p.is_file())


def boundary_oracle(features, model):
    """Python-integer specification for deliberately invalid INT32 NN frames.

    infer() correctly refuses overflowing models/inputs. Here the expected
    error response is explicit: check final 40-bit dot results, retain full
    values for hidden clipping, truncate output storage to signed INT32, and
    mark the frame invalid. This is not a replacement deployment predictor.
    """
    def dot(row, x, bias):
        return int(bias) + sum(int(a) * int(b) for a, b in zip(row, x))

    assert model["hidden_shift"] == 0
    hacc = [dot(w, features, b) for w, b in zip(model["w1"], model["b1"])]
    hidden = [min(127, max(0, value)) for value in hacc]
    lacc = [dot(w, hidden, b) for w, b in zip(model["w2"], model["b2"])]
    assert all(-(1 << 39) <= value < (1 << 39) for value in hacc + lacc)
    wrapped = [((value + (1 << 31)) % (1 << 32)) - (1 << 31) for value in lacc]
    overflow = [{"layer": layer, "index": i, "accumulator": value,
                 "polarity": "positive" if value > HIGH else "negative"}
                for layer, values in enumerate((hacc, lacc)) for i, value in enumerate(values)
                if value < LOW or value > HIGH]
    expected = {"features": list(map(int, features)), "hidden_acc": hacc, "hidden": hidden,
                "output_acc": lacc, "logits": wrapped,
                "class_id": max(range(3), key=lambda i: wrapped[i]),
                "error": int(bool(overflow)), "overflow": overflow}
    try:
        accepted = infer(features, model)
    except OverflowError:
        assert overflow, "the standard reference rejected a supposedly valid fixture"
        expected["standard_reference"] = "rejected_INT32_overflow_as_expected"
    else:
        assert not overflow
        for name in ("hidden_acc", "hidden", "logits"):
            assert list(map(int, accepted[name])) == expected[name]
        assert int(accepted["class_id"]) == expected["class_id"]
        expected["standard_reference"] = "matched"
    return expected


def fixtures(directory):
    base = {"schema_version": 1, "n": 1024, "bins": list(range(1, 17)),
            "input_shift": 5, "dft_shift": 20, "feature_shifts": [10] * 16,
            "hidden_shift": 0,
            "training_status": "verification_fixture_not_trained",
            "verification_only": True, "physical_board_tested": False,
            "w1": [[0] * 16 for _ in range(16)], "b1": [0] * 16,
            "w2": [[0] * 16 for _ in range(3)], "b2": [7, -5, 3]}
    models = []
    for name, biases, winner in (("tie_all_zero", [0, 0, 0], 0),
                                  ("tie_01_negative", [-7, -7, -9], 0),
                                  ("tie_02_positive", [11, 0, 11], 0),
                                  ("tie_12_negative", [-8, -3, -3], 1)):
        model = json.loads(json.dumps(base))
        model.update({"fixture_name": name, "b2": biases, "expected_tie_winner": winner})
        models.append(model)
    for layer in ("hidden", "output"):
        for polarity, sign, bias in (("positive", 1, HIGH - 1),
                                     ("negative", -1, LOW + 1)):
            model = json.loads(json.dumps(base))
            model.update({"fixture_name": f"{layer}_{polarity}",
                          "edge_layer": 0 if layer == "hidden" else 1,
                          "edge_polarity": polarity})
            if layer == "hidden":
                model["w1"][0][0], model["b1"][0] = sign, bias
            else:
                model["w1"][0][0] = 1
                model["w2"][0][0], model["b2"][0] = sign, bias
            models.append(model)
    result = []
    for model in models:
        destination = directory / model["fixture_name"]
        export_model(model, destination)
        entries = []
        for name, amplitude, feature in (("below", 0, 0), ("boundary", 256, 1), ("overflow", 320, 2)):
            raw = np.rint(amplitude * np.cos(2 * np.pi * np.arange(1024) / 1024)).astype(np.int64)
            front = frontend(raw, model)
            assert int(front["features"][0]) == feature
            entries.append({"name": name, "amplitude": amplitude, "raw": raw.tolist(),
                            "raw_sha256": hashlib.sha256(raw.astype("<i2").tobytes()).hexdigest(),
                            "expected": boundary_oracle(front["features"], model)})
        if "edge_layer" in model:
            assert [e["expected"]["error"] for e in entries] == [0, 0, 1]
            overflow = entries[2]["expected"]["overflow"]
            assert len(overflow) == 1 and overflow[0]["layer"] == model["edge_layer"]
            assert overflow[0]["polarity"] == model["edge_polarity"]
            assert overflow[0]["accumulator"] == (HIGH + 1 if model["edge_polarity"] == "positive" else LOW - 1)
        (destination / "vectors.json").write_text(json.dumps(entries, indent=2) + "\n")
        result.append(destination)
    return result


def require_passed(xml_path, report_path):
    tree = ET.parse(xml_path)
    cases = list(tree.iter("testcase"))
    if len(cases) != 1 or any(list(tree.iter(tag)) for tag in ("failure", "error", "skipped")):
        raise RuntimeError(f"cocotb did not execute one passing test: {xml_path}")
    report = json.loads(report_path.read_text())
    if report.get("status") != "passed" or not report.get("checked_outputs"):
        raise RuntimeError(f"missing complete test evidence: {report_path}")
    return report


def main():
    configure_verilator_environment()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lanes", nargs="+", type=int, choices=(1, 4), default=[1, 4])
    add_run_arguments(parser)
    args = parser.parse_args()
    build = run_path(args, "nn_edges")
    build.mkdir(parents=True, exist_ok=True)
    summary_path = build / "summary.json"
    summary_path.unlink(missing_ok=True)
    frozen_before = deployment_hashes()
    sources = [ROOT / "rtl/core/vib_coeff_rom.sv", ROOT / "rtl/core/vibration_core.sv",
               ROOT / "sim/nn_edges_tb.sv"]
    inputs = sources + [Path(__file__).resolve(), ROOT / "sim/test_nn_edges.py",
                        ROOT / "src/vibfpga/fixed.py", ROOT / "src/vibfpga/export.py"]
    source_hashes = hashes(inputs)
    fixture_dirs = fixtures(build / "fixtures")
    # Each lane has its own runtime ROM path: independent invocations cannot
    # accidentally share model files with a different lane configuration.
    from cocotb_tools.runner import get_runner
    sys.path[:0] = [str(ROOT / "sim")]
    reports = []
    for lanes in dict.fromkeys(args.lanes):
        lane_build = build / f"l{lanes}"
        active = lane_build / "active_model"
        active.mkdir(parents=True, exist_ok=True)
        for path in fixture_dirs[0].iterdir():
            shutil.copyfile(path, active / path.name)
        runner = get_space_safe_runner()
        runner.build(sources=sources, hdl_toplevel="nn_edges_tb", build_dir=lane_build / "compiled",
                     parameters={"LANES": lanes, "MODEL_DIR": f'"{active}"'},
                     build_args=["--assert", "-DVIB_ASSERT", "-Wno-fatal", "-Wno-WIDTHEXPAND",
                                 "-Wno-WIDTHTRUNC", "-CFLAGS", "-std=c++17"],
                     always=True, log_file=lane_build / "compile.log")
        for fixture in fixture_dirs:
            for path in fixture.iterdir():
                shutil.copyfile(path, active / path.name)
            target = lane_build / fixture.name
            target.mkdir(exist_ok=True)
            xml_path, report_path = target / "results.xml", target / "result.json"
            xml_path.unlink(missing_ok=True)
            report_path.unlink(missing_ok=True)
            manifest = {"n": 1024, "bands": 1, "lanes": lanes, "hidden_shift": 0,
                        "fixture_name": fixture.name, "fixture_dir": str(fixture),
                        "model_sha256": digest(fixture / "model.json"),
                        "fixture_sha256": hashes(p for p in fixture.iterdir() if p.is_file()),
                        "source_sha256": source_hashes, "assertions_enabled": True,
                        "physical_board_tested": False,
                        "simulator": subprocess.check_output(["verilator", "--version"], text=True).strip()}
            manifest_path = target / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
            runner.test(hdl_toplevel="nn_edges_tb", test_module="test_nn_edges", test_dir=target,
                        results_xml=str(xml_path), log_file=target / "simulation.log",
                        extra_env={"NN_EDGE_MANIFEST": str(manifest_path),
                                   "NN_EDGE_REPORT": str(report_path),
                                   "PYTHONPATH": os.pathsep.join([str(ROOT / "src"), str(ROOT / "sim")]),
                                   "COCOTB_TRUST_INERTIAL_WRITES": "1"})
            report = require_passed(xml_path, report_path)
            assert hashes(inputs) == source_hashes, "source changed while tests ran"
            assert deployment_hashes() == frozen_before, "deployed model files changed"
            reports.append({"lanes": lanes, "fixture": fixture.name,
                            "result": (str(report_path.relative_to(ROOT)) if report_path.is_relative_to(ROOT) else str(report_path)),
                            "result_sha256": digest(report_path),
                            "xml_sha256": digest(xml_path),
                            "checked_outputs": len(report["checked_outputs"]),
                            "accepted_outputs": report["accepted_outputs"],
                            "reset_cancellations": len(report["reset_cancellations"])})
            print(f"PASS LANES={lanes} {fixture.name}: {len(report['checked_outputs'])} checked outputs", flush=True)
    summary = {"suite": "NN_directed_INT32_edges_and_ties", "status": "passed",
               "configurations": list(dict.fromkeys(args.lanes)), "runs": reports,
               "physical_board_tested": False, "source_sha256": source_hashes,
               "deployed_model_files_unchanged": True, "deployed_model_sha256": frozen_before,
               "total_checked_outputs": sum(r["checked_outputs"] for r in reports),
               "total_accepted_outputs": sum(r["accepted_outputs"] for r in reports),
               "total_reset_cancellations": sum(r["reset_cancellations"] for r in reports)}
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(summary_path)


if __name__ == "__main__":
    main()
