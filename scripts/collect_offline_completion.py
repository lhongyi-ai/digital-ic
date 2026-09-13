#!/usr/bin/env python3
"""Validate and index this offline completion batch; no training or hardware IO."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from vibfpga.field import source_hashes
from vibfpga.field_log import parse_field_log


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope",choices=("full","current-release"),default="full",
                        help="full retains historical field L4/area audit; current-release checks active release acceptance")
    args=parser.parse_args()
    current=args.scope=="current-release"
    destination=ROOT/("build/release/summary.json" if current else "build/offline-completion/summary.json")
    if current:destination.unlink(missing_ok=True)
    evidence=[]
    def read(path,check_sources=True):
        p=ROOT/path;d=json.loads(p.read_text())
        hashes=d.get("source_sha256",{})
        if check_sources and isinstance(hashes,dict):
            for name,expected in hashes.items():
                if sha(ROOT/name)!=expected:raise RuntimeError(f"stale evidence {path}: {name}")
        evidence.append({"path":path,"sha256":sha(p)})
        return d
    xml=ROOT/"build/offline-completion/python-results.xml"
    tree=ET.parse(xml);cases=list(tree.iter("testcase"))
    if not cases or any(list(tree.iter(t)) for t in ("failure","error","skipped")):
        raise RuntimeError("Python regression is incomplete or failed")
    evidence.append({"path":str(xml.relative_to(ROOT)),"sha256":sha(xml)})
    nn=read("build/nn_edges/summary.json")
    assert nn["status"]=="passed" and nn["deployed_model_files_unchanged"]
    for name,expected in nn["deployed_model_sha256"].items():assert sha(ROOT/name)==expected
    q=read("build/quantization_formal/report.json")
    assert q["source_sha256"]==sha(ROOT/"rtl/core/vibration_core.sv")
    assert q["harness_sha256"]==sha(ROOT/"formal/quant_harness.sv")
    assert q["complete_positive_suite"] and q["all_requested_checks_accepted"]
    assert len(q["negative_controls"])==2 and all(r["actual_status"]=="FAIL" and r["accepted_result"] for r in q["negative_controls"])
    coverage=read("build/rtl_coverage/coverage_report.json");assert coverage["status"]=="passed"
    protocol=read("build/protocol_edges/report.json")
    assert protocol["complete_four_configuration_suite"] and all(r["status"]=="passed" for r in protocol["results"])
    for result in protocol["results"]:read(result["report"])
    sensor=[];integrated=[];saved_logs=[]
    for lanes in (1,4):
        r=read(f"build/sensor_classifier_l{lanes}/regression.json");assert r["status"]=="passed"
        sensor.append({"lanes":lanes,"tests":r["tests"],"checked_outputs":r["checked_outputs"]})
        r=read(f"build/field_system_l{lanes}/summary.json");assert r["passed"] and len(r["reports"])==6
        integrated.append({"lanes":lanes,"tests":len(r["reports"]),"passed":all(v["passed"] for v in r["reports"])})
        for case in ("nominal","gap"):
            path=ROOT/f"build/field_system_l{lanes}/{case}/report.bin"
            parsed=parse_field_log(path.read_bytes(),expected_model_sha256=sha(ROOT/"build/field_fixture/trained/model/model.json"))
            saved_logs.append({"path":str(path.relative_to(ROOT)),"sha256":sha(path),"records":parsed["record_count"],"current_parser_recheck":"passed"})
    frozen=read("build/field_fixture/trained/frozen.json",check_sources=False)
    # Its source keys are package-relative, not repository-relative.
    assert frozen["source_sha256"]==source_hashes()
    for name,expected in frozen["files"].items():assert sha(ROOT/"build/field_fixture/trained"/name)==expected
    training=read("build/field_fixture/trained/training.json")
    fixture=read("build/field_fixture/trained/test.json")
    assert training["test_captures_opened"] is False and fixture["claim"]=="synthetic pipeline diagnostics only"
    field_builds=[]
    for lanes in ((1,) if current else (1,4)):
        base=ROOT/f"build/field_board_l{lanes}"
        if (base/"report.json").is_file():
            r=read(str((base/"report.json").relative_to(ROOT)))
            assert r["place_route_completed"] and all(v["achieved"]>=12 for v in r["fmax"].values())
            assert r["bitstream_sha256"]==sha(base/"board.bin")
            field_builds.append({"lanes":lanes,"status":"static_build_passed_with_synthetic_model",
                "utilization":r["utilization"],"fmax":r["fmax"],"model_sha256":r["model_sha256"]})
        else:
            log=base/"place_route.log";message=log.read_text()
            if not re.search(r"ERROR:.*ICESTORM_LCs",message):raise RuntimeError("missing field build result")
            evidence.append({"path":str(log.relative_to(ROOT)),"sha256":sha(log)})
            field_builds.append({"lanes":lanes,"status":"does_not_fit_current_UP5K",
                                 "reason":re.search(r"ERROR:.*",message).group(0)})
    if current:
        from release_validation import validate_current_release
        current_checks=validate_current_release(ROOT)
        area={"status":"historical_not_repeated", "reason":"field four-MAC capacity tuning is paused; excluded from current release acceptance"}
    else:
        current_checks=None
        area=read("build/field_area_experiments/report.json")
        assert area["status"]=="completed_no_fit" and area["production_source_files_unchanged"]
        for name,expected in area["production_source_sha256"].items():assert sha(ROOT/name)==expected
    report={"generated_utc":datetime.now(timezone.utc).isoformat(),
        "scope":"current active offline release checks; historical field L4 area tuning excluded" if current else "new offline work against pasted plan; physical work and actual field training data unavailable",
        "current_release_checks":current_checks,
        "python_tests_passed":len(cases),"nn_checked_outputs":nn["total_checked_outputs"],
        "quantization_formal":{"positive_suite":"passed","negative_controls":2,"serial_depth":64},
        "coverage_status":"passed; see original denominators and uncovered points, not a 100% claim",
        "protocol_edges":"passed","sensor_classifier":sensor,"field_pin_level_system":integrated,
        "field_fixture_pipeline":"passed; synthetic diagnostics only","field_static_builds":field_builds,
        "field_area_experiments":area if current else {"attempts":3,"best_l4_logic_cells":area["best_logic_cells"],
                                  "capacity":5280,"production_choice":"retain validated LANES1"},
        "saved_logs":saved_logs,"evidence":evidence,"physical_board_programmed":False,
        "pending_hardware_or_real_data":["board revision/clock/Flash identification and programming",
            "physical replay result readback","ADXL345 acquisition/calibration/noise/SPI measurements/repeatability",
            "real field-state records, training/evaluation and rebuild with their model",
            "physical continuous operation, resource/power measurements"],
        "outside_current_acceptance":["full-core unbounded formal equivalence","ASIC standard-cell PNR/STA extension","JTAG","envelope-spectrum upgrade without data evidence"]}
    dest=destination
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,indent=2)+"\n")
    artifact=ROOT/("artifacts/evidence/current-release.json" if current else "artifacts/evidence/offline-completion-2026-09-07.json")
    artifact.parent.mkdir(parents=True,exist_ok=True)
    artifact.write_text(dest.read_text())
    print(dest)


if __name__=="__main__":main()
