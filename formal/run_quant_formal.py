#!/usr/bin/env python3
"""Run source-linked quantization formal checks and expected-failure controls."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

from quant_extract import ROOT, SOURCE, DESTINATION, extract

OUT = ROOT / "build/quantization_formal"
TASKS = ["functions_h8", "functions_h0", "functions_cover", "serial_bmc", "serial_cover"]


def version(command):
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    return (result.stdout + result.stderr).strip()


def run(task, configuration, destination, expected, timeout):
    command = ["sby", "-f", "-d", str(destination), str(configuration), task]
    started = time.monotonic()
    with (OUT / f"{destination.name}.console.log").open("w") as log:
        try:
            result = subprocess.run(command, cwd=ROOT / "formal", stdout=log,
                                    stderr=subprocess.STDOUT, timeout=timeout, check=False)
            returncode = result.returncode
        except subprocess.TimeoutExpired:
            returncode = "TIMEOUT"
    status_path = destination / "status"
    status = status_path.read_text().strip().split()[0] if status_path.exists() else "MISSING"
    log_path = destination / "logfile.txt"
    log = log_path.read_text() if log_path.exists() else ""
    result = {"task": task, "expected_status": expected, "actual_status": status,
              "mode": "cover" if task.endswith("cover") else "prove" if task.startswith("functions") else "bmc",
              "depth": 2 if task.startswith("functions") else 64,
              "engine": "abc bmc3" if task == "serial_bmc" else "smtbmc bitwuzla",
              "accepted_result": status == expected and (returncode == 0 if expected == "PASS" else isinstance(returncode, int) and returncode != 0),
              "returncode": returncode, "seconds": time.monotonic()-started,
              "command": command, "directory": str(destination.relative_to(ROOT)),
              "cover_events": re.findall(r"Reached cover statement .*", log),
              "counterexample_or_cover_traces": [str(p.relative_to(ROOT)) for p in destination.rglob("*.vcd")]}
    if task.endswith("cover"):
        result["cover_goals_expected"] = 13 if task.startswith("functions") else 45
        result["cover_goals_reached"] = len(result["cover_events"])
        result["accepted_result"] &= result["cover_goals_reached"] == result["cover_goals_expected"]
    if expected == "FAIL":
        result["accepted_result"] &= bool(result["counterexample_or_cover_traces"])
    print(f"{destination.name}: {status} (expected {expected}, {result['seconds']:.1f}s)", flush=True)
    if not result["accepted_result"]:
        print(log[-5000:], flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tasks", nargs="*", choices=TASKS)
    parser.add_argument("--timeout", type=int, default=240, help="Timeout per solver task, seconds")
    parser.add_argument("--negative-controls", action="store_true", help="Also run deliberately incorrect generated kernels")
    args = parser.parse_args()
    manifest = extract()
    results = []
    selected = args.tasks or TASKS
    for task in selected:
        results.append(run(task, ROOT / "formal/quant.sby", OUT / task, "PASS", args.timeout))
    negative = []
    if args.negative_controls:
        original = (DESTINATION / "quant_extract.sv").read_text()
        substitutions = {
            "serial_tie_away": ("(quant_guard && (quant_sticky || quant_work[0]))", "quant_guard", "serial_bmc"),
            "function_tie_away": ("((remainder == halfway) && quotient[0])", "(remainder == halfway)", "functions_h8"),
        }
        for name, (old, new, task) in substitutions.items():
            if original.count(old) != 1:
                raise RuntimeError(f"Expected exactly one mutation target: {name}")
            mutant = DESTINATION / f"{name}.sv"
            mutant.write_text(original.replace(old, new))
            config = (ROOT / "formal/quant.sby").read_text().replace(
                "quant_extract.sv", f"{name}.sv").replace(
                "../build/quantization_formal/generated/", str(DESTINATION) + "/").replace(
                "\nquant_harness.sv\n", "\n" + str(ROOT / "formal/quant_harness.sv") + "\n")
            # This OSS-CAD Suite's ABC->SMT witness conversion loses a reset
            # alias in this cut. Use direct SMT for an independently replayable
            # negative-control VCD; never treat a conversion ERROR as FAIL.
            config = config.replace("serial_bmc: abc bmc3", "serial_bmc: smtbmc bitwuzla")
            config_path = DESTINATION / f"{name}.sby"
            config_path.write_text(config)
            record = run(task, config_path, OUT / name, "FAIL", args.timeout)
            record.update({"mutation": name, "original_expression": old, "replacement_expression": new,
                           "engine": "smtbmc bitwuzla",
                           "mutant_sha256": hashlib.sha256(mutant.read_bytes()).hexdigest()})
            negative.append(record)
    source_unchanged = hashlib.sha256(SOURCE.read_bytes()).hexdigest() == manifest["source_sha256"]
    report = {"schema_version": 1, "generated_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "Source-linked combinational proofs and bounded serial feature requantization; not a full-core proof",
              "source_sha256": manifest["source_sha256"], "source_unchanged_during_run": source_unchanged,
              "generated_kernel_sha256": manifest["generated_sha256"],
              "harness_sha256": hashlib.sha256((ROOT / "formal/quant_harness.sv").read_bytes()).hexdigest(),
              "tools": {"yosys": version(["yosys", "-V"]), "sby": version(["sby", "--version"]),
                        "abc": version(["yosys-abc", "-c", "version"]),
                        "bitwuzla": version(["bitwuzla", "--version"])},
              "parameters": {"function_input_signed_bits": 40, "rne_shifts": [0,39],
                             "hidden_shifts": [0,8], "power_unsigned_bits": 33, "power_shifts": [0,255],
                             "feature_indices": [0,15], "functions_depth": 2, "serial_depth": 64},
              "assumptions": ["Signed RNE shift restricted to 0..39; larger shifts are outside its production input-width contract.",
                              "First serial clock edge asserts synchronous reset; subsequent reset/start are unconstrained.",
                              "One arbitrary constant power/shift/index tuple per serial trace; wrapper latches it at acceptance.",
                              "Quantizer input producer and successor states are abstracted; the three quantizer arms execute verbatim."],
              "results": results, "negative_controls": negative,
              "complete_positive_suite": set(selected) == set(TASKS),
              "all_requested_checks_accepted": source_unchanged and all(r["accepted_result"] for r in results+negative),
              "physical_hardware_tested": False}
    (OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(OUT / "report.json")
    if not report["all_requested_checks_accepted"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
