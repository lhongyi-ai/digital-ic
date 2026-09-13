#!/usr/bin/env python3
"""Collect existing results, source hashes and installed tool versions.

No tests, training, downloads or hardware commands are performed. Missing,
failed and potentially stale evidence remains visible rather than being filled
with expected results. A collection-time hash is not a retrospective build hash.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def xml_summary(path):
    path=Path(path)
    if not path.exists(): return {"status":"missing"}
    try:
        root=ET.parse(path).getroot()
        cases=list(root.iter("testcase"))
        failed=sum(c.find("failure") is not None or c.find("error") is not None for c in cases)
        skipped=sum(c.find("skipped") is not None for c in cases)
        # Some runners report suite-level failures without a testcase element.
        suite_errors=sum(int(s.get("failures",0))+int(s.get("errors",0)) for s in root.iter("testsuite"))
        return {"status":"passed" if cases and not failed and not suite_errors and skipped<len(cases) else "failed",
                "tests":len(cases),"failed":max(failed,suite_errors),"skipped":skipped,
                "sha256":digest(path)}
    except (ET.ParseError,ValueError,OSError) as error:
        return {"status":"invalid","error":str(error)}


def read_report(path):
    path=Path(path)
    if not path.exists(): return None
    return json.loads(path.read_text())


def file_evidence(path,root):
    return {"path":str(path.relative_to(root)),"sha256":digest(path),"bytes":path.stat().st_size}


def newer_sources(report, sources, root):
    if not report.exists(): return []
    return [str(p.relative_to(root)) for p in sources if p.exists() and p.stat().st_mtime_ns>report.stat().st_mtime_ns]


def verify_input_hashes(report, root, required=()):
    """Verify original build inputs when the build recorded their hashes.

    Missing bindings remain unavailable. A collection-time source snapshot is
    not a substitute, and an unchanged mtime cannot conceal a changed input.
    """
    bindings=report.get("input_sha256")
    if not isinstance(bindings,dict) or not bindings:
        return {"status":"unavailable","verified_files":0,"mismatches":[],"missing_required":list(required)}
    root=Path(root).resolve()
    mismatches=[]
    for relative,expected in bindings.items():
        path=(root/relative).resolve()
        if not path.is_relative_to(root) or not path.is_file() or digest(path)!=expected:
            mismatches.append(relative)
    missing=sorted(set(required)-set(bindings))
    return {"status":"passed" if not mismatches and not missing else "failed",
            "verified_files":len(bindings)-len(mismatches),"mismatches":sorted(mismatches),
            "missing_required":missing}


def environment(root):
    versions={}
    tool_env=dict(os.environ)
    for name,relative in (("XDG_CONFIG_HOME","build/xdg-config"),("XDG_DATA_HOME","build/xdg-data")):
        target=root/relative
        target.mkdir(parents=True,exist_ok=True)
        tool_env[name]=str(target)
    commands={"verilator":["--version"],"yosys":["-V"],"nextpnr-ice40":["--version"],
              "sby":["--version"],"z3":["--version"]}
    for name,args in commands.items():
        local=root/".tools/oss-cad-suite/bin"/name
        executable=str(local) if local.exists() else shutil.which(name)
        if not executable:
            versions[name]={"available":False};continue
        try:
            result=subprocess.run([executable,*args],capture_output=True,text=True,timeout=15,env=tool_env,cwd=root)
            actual=root/".tools/oss-cad-suite/libexec"/name
            versions[name]={"available":True,"executable":executable,"returncode":result.returncode,
                "version_output":(result.stdout+result.stderr).strip()[:1500],
                "executable_sha256":digest(actual if actual.is_file() else Path(executable))}
        except (OSError,subprocess.TimeoutExpired) as error:
            versions[name]={"available":False,"error":str(error)}
    installed={d.metadata["Name"].lower().replace("_","-"):d.version for d in importlib.metadata.distributions() if d.metadata["Name"]}
    lock=root/"requirements.lock.txt"
    mismatches=[]
    if lock.exists():
        for line in lock.read_text().splitlines():
            if "==" not in line or line.startswith("#"): continue
            name,expected=line.split("==",1)
            actual=installed.get(name.lower().replace("_","-"))
            if actual!=expected: mismatches.append({"package":name,"expected":expected,"actual":actual})
    return {"python":sys.version,"platform":platform.platform(),"machine":platform.machine(),
        "tools":versions,"python_packages":dict(sorted(installed.items())),
        "requirements_lock_sha256":digest(lock) if lock.exists() else None,
        "requirements_lock_mismatches":mismatches,
        "limitations":"Installed versions and binaries recorded at collection time, not a historical attestation of every prior run."}


def collect(root,output):
    output.mkdir(parents=True,exist_ok=True)
    checks={}
    for path in sorted((root/"build").rglob("results.xml")):
        checks[str(path.parent.relative_to(root))]={**xml_summary(path),"results_xml":str(path.relative_to(root))}
    unit=root/"build/python-results.xml"
    checks["python_unit"]={**xml_summary(unit),"results_xml":str(unit.relative_to(root))}
    regressions={}
    for pattern in ("core_*/regression.json","core_*/arithmetic/arithmetic.json","flash_system*/regression.json",
                    "sensor_system*/regression.json","sensor_system*/report.json","sensor_spectrum/report.json",
                    "spi_*/report.json","calibration_*/report.json"):
        for path in sorted((root/"build").glob(pattern)):
            key=str(path.relative_to(root))
            xml=path.parent/"results.xml"
            r=read_report(path)
            regressions[key]={"report":r,"evidence":file_evidence(path,root),"xml_verification":xml_summary(xml),
                              "current_input_hash_check":verify_input_hashes(r,root)}
    fixed_rate={}
    for path in sorted((root/"build").glob("core_*/fixed_rate/fixed_rate*.json")):
        report=read_report(path)
        # Timing/clock metadata is not a test case and has no status field.
        passing=all(isinstance(report.get(k),dict) and report[k].get("status")=="passed"
                    for k in ("normal","overload_and_recovery"))
        sources=[root/p for p in ("rtl/core/vibration_core.sv","rtl/core/vib_coeff_rom.sv","rtl/core/sync_fifo.sv",
                                  "sim/fixed_rate_tb.sv","sim/fixed_rate_main.cpp")]
        fixed_rate[str(path.relative_to(root))]={"status":"passed" if passing else "failed","report":report,
            "evidence":file_evidence(path,root),"newer_source_paths":newer_sources(path,sources,root),
            "run_kind":f"{report.get('normal',{}).get('output_frames','unknown')}-frame "+
                       ("timing measurement" if path.name=="fixed_rate_32.json" else "steady-state/recovery run"),
            "scope":"Native fixed-rate core harness; not full Flash or physical hardware. Timing and steady-state files are different runs. Source timestamp check is conservative, not a build content-hash binding."}
    formal=[]
    for path in sorted((root/"build/formal").glob("*/status")):
        value=path.read_text().strip()
        formal.append({"path":str(path.relative_to(root)),"status":"passed" if value.startswith("PASS") else "failed",
                       "raw_status":value,"bound_clock_steps":64,"scope":"FIFO BMC/cover for configured depths, not unbounded or system-level proof"})
    boards={}
    board_directories=list((root/"build").glob("board_*"))+list((root/"build").glob("sensor_board_*"))
    for directory in sorted(board_directories):
        if not directory.is_dir(): continue
        report_path=directory/"report.json"
        report=read_report(report_path)
        route_log=directory/"place_route.log"
        row={"status":"missing_success_report","physical_board_programmed":False}
        if report is not None:
            timing=read_report(directory/"timing.json") or {}
            binary=directory/"board.bin"
            hash_ok=binary.exists() and digest(binary)==report.get("bitstream_sha256")
            timing_ok=bool(timing.get("fmax")) and all(v["achieved"]>=v["constraint"] for v in timing["fmax"].values())
            utilization_ok=bool(timing.get("utilization")) and all(v["used"]<=v["available"] for v in timing["utilization"].values())
            common=["rtl/platform/spram16k.sv","rtl/io/spi_master.sv","rtl/io/flash_stream.sv"]
            if report.get("top")=="upduino_sensor":
                relevant=common+["rtl/io/adxl345_capture.sv","rtl/io/static_calibration.sv","rtl/upduino_sensor.sv"]
                if report.get("spectrum_included"):
                    relevant += ["rtl/io/sensor_spectrum.sv","rtl/core/vib_coeff_rom.sv","rtl/core/vibration_core.sv"]
            else:
                relevant=common+["rtl/core/vib_coeff_rom.sv","rtl/core/vibration_core.sv","rtl/core/sync_fifo.sv",
                                 "rtl/io/replay_source.sv","rtl/upduino_replay.sv"]
            source_paths=[root/p for p in relevant]
            stale=newer_sources(report_path,source_paths,root)
            source_hashes=verify_input_hashes(report,root,relevant)
            source_ok=source_hashes["status"]=="passed" or (source_hashes["status"]=="unavailable" and not stale)
            row={"status":"passed" if report.get("place_route_completed") and hash_ok and timing_ok and utilization_ok and source_ok else "failed_or_unverified",
                 "report":report,"bitstream_hash_verified":hash_ok,"timing_constraints_met":timing_ok,
                 "resource_limits_met":utilization_ok,"fmax":timing.get("fmax"),"utilization":timing.get("utilization"),
                 "newer_source_paths":stale,"build_input_hash_check":source_hashes,
                 "source_binding":"original build input hashes verified" if source_hashes["status"]=="passed" else
                    "original build hashes do not match" if source_hashes["status"]=="failed" else
                    "collection snapshot plus conservative source mtime check; no original build source hashes recorded"}
        if route_log.exists():
            row["place_route_log"]=file_evidence(route_log,root)
            row["errors_in_route_log"]=[line for line in route_log.read_text().splitlines() if "ERROR:" in line]
        boards[str(directory.relative_to(root))]=row
    model_path=root/"artifacts/model/model.json"
    frozen=read_report(root/"artifacts/reports/selection_frozen.json") or {}
    test=read_report(root/"artifacts/reports/test_evaluation.json")
    model_hash=digest(model_path) if model_path.exists() else None
    dataset=read_report(root/"data/cwru/manifest.json") or {}
    data_checks=[]
    for record in dataset.get("records",[]):
        path=root/f"data/cwru/{record['record_id']}.mat"
        data_checks.append({"record_id":record["record_id"],"sha_verified":path.exists() and digest(path)==record["sha256"]})
    neighbor=read_report(root/"artifacts/reports/neighbor_comparison.json")
    neighbor_output=root/"artifacts/reports/neighbor_test"
    neighbor_test={"status":"not_run"}
    if neighbor_output.exists():
        try:
            from vibfpga.neighbor_evaluation import verify_existing
            neighbor_test={**verify_existing(root,neighbor_output),
                "evaluation":read_report(neighbor_output/"evaluation.json"),
                "evidence":file_evidence(neighbor_output/"completion.json",root)}
        except (ImportError,ValueError,OSError,KeyError,TypeError) as error:
            neighbor_test={"status":"failed_or_incomplete","error":str(error)}
    ml={"model_sha256":model_hash,"freeze_hash_matches":model_hash is not None and model_hash==frozen.get("model_sha256"),
        "test_hash_matches":test is not None and model_hash==test.get("frozen_model_sha256"),
        "data_record_sha_checks":data_checks,"held_out_test":test,
        "normal_class_included":dataset.get("normal_included"),"test_access_note":frozen.get("data_audit_note"),
        "neighbor_train_validation_only_ablation":neighbor,
        "neighbor_frozen_test":neighbor_test}
    sources=[]
    for directory in ("src","rtl","scripts","sim","formal","configs"):
        sources.extend(p for p in (root/directory).rglob("*") if p.is_file() and p.suffix in (".py",".sv",".sby",".pcf",".json",".sh"))
    for model_directory in (root/"artifacts").glob("model*"):
        if model_directory.is_dir(): sources.extend(p for p in model_directory.glob("*") if p.is_file())
    sources.extend(p for p in (root/"artifacts/sensor_spectrum/model").glob("*") if p.is_file())
    locks={"collected_utc":datetime.now(timezone.utc).isoformat(),
        "meaning":"Current source/model snapshot, not proof that prior runs used every file in this snapshot",
        "files":[file_evidence(p,root) for p in sorted(set(sources))]}
    sva=read_report(root/"build/sva_smoke/result.json")
    sva_check={"status":"missing"} if sva is None else {
        "status":"passed" if sva.get("positive_pass") is True and sva.get("negative_control_detected") is True else "failed",
        "report":sva,"scope":"Only the named SVA subset and deliberate negative control, not complete language support or design proof"}
    spectrum_probe=read_report(root/"build/sensor_spectrum/probe_report.json")
    result={"schema_version":1,"collected_utc":locks["collected_utc"],"hardware_tested":False,
        "checks":checks,"regressions":regressions,"fixed_rate":fixed_rate,"formal":formal,"sva_smoke":sva_check,"board_builds":boards,"ml":ml,
        "sensor_spectrum_standalone_probe":spectrum_probe,
        "not_yet_evidenced":["physical board programming and Flash readback","actual ADXL345 captures, calibration or noise measurements",
                            "field-condition classifier accuracy","measured power","ASIC implementation/signoff or chip fabrication","JTAG use"],
        "interpretation":"Passing XML requires at least one non-skipped test and no failure/error. Missing evidence is never treated as success. Historical reports can outlive source edits; use source-lock and newer_source_paths appropriately."}
    for name,value in (("index.json",result),("source-lock.json",locks),("environment.json",environment(root))):
        (output/name).write_text(json.dumps(value,indent=2)+"\n")
    lines=["# Automatically collected project evidence","",f"Generated: {result['collected_utc']}","",
           "This report only reads saved results and does not rerun experiments. At this historical stage, there was no completion evidence for hardware tests, physical sensors, field classification, power measurements, or ASIC fabrication.","",
           "| Check | Result | Test count |","| --- | --- | --- |"]
    for name,value in checks.items(): lines.append(f"| {name} | {value['status']} | {value.get('tests','—')} |")
    lines.extend(["","## Complete FPGA builds","","A build passes only if its report, bitstream checksum, timing, and capacity checks all pass. A core probe is not a complete system build.",""])
    for name,value in boards.items(): lines.append(f"- {name}: {value['status']}; newer RTL files: {len(value.get('newer_source_paths',[]))}.")
    if not boards: lines.append("- No complete system build reports yet.")
    if test:
        lines.extend(["","## Held-out test of the original single-bin model","",f"INT8 accuracy {100*test['deployed_integer']['accuracy']:.2f}%, macro-F1 {100*test['deployed_integer']['macro_f1']:.2f}%.",
            f"RMS baseline accuracy {100*test['rms_three_leaf_threshold_baseline']['accuracy']:.2f}%. This does not support a claim that the MLP outperforms the baseline.",""])
    if neighbor_test["status"]=="passed":
        evaluation=neighbor_test["evaluation"]
        integer=evaluation["integer_metrics"]
        lines.extend(["","## Test evaluation after freezing the neighboring-bin candidate","",
            f"INT8 accuracy {100*integer['accuracy']:.2f}%, macro-F1 {100*integer['macro_f1']:.2f}%.",
            "Evaluation outputs, frozen input hashes, and saved predictions passed consistency checks. The 3 HP records were previously used to test the old model; this is not a new external dataset or a hardware/field measurement.",
            "The model and ROM remain frozen. Results are saved separately under artifacts/reports/neighbor_test; the historical test_evaluated=false model-JSON field is not rewritten.",""])
    elif neighbor_test["status"]!="not_run":
        lines.extend(["","## Neighboring-bin candidate test evaluation","",f"Evidence status: {neighbor_test['status']}; this does not establish a passing result.",""])
    lines.extend(["Detailed values, original evidence paths, and checksums are in index.json; the source snapshot is in source-lock.json; installed tool and dependency versions are in environment.json.",""])
    (output/"project-status.md").write_text("\n".join(lines))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,default=ROOT/"artifacts/evidence")
    a=p.parse_args()
    result=collect(ROOT,a.output.resolve())
    print(json.dumps({"output":str(a.output),"xml_reports":len(result["checks"]),
        "hardware_tested":False,"board_builds":{k:v["status"] for k,v in result["board_builds"].items()}},indent=2))


if __name__=="__main__": main()
