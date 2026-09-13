#!/usr/bin/env python3
"""Independently check saved overload and restart evidence; never access USB."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from vibfpga.board import parse_replay_image, parse_result_log, read_command, write_commands
from vibfpga.fixed import classify

BINDINGS = {}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def bound(path, digest=None):
    path = Path(path).resolve()
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    require(digest is None or digest == actual, f"SHA256 mismatch: {path}")
    BINDINGS[str(path)] = actual
    return raw


def json_file(path, digest=None):
    return json.loads(bound(path, digest))


def artifact(directory, name):
    require(isinstance(name, str) and Path(name).name == name, "unsafe artifact name")
    return directory / name


def check_attempt(directory):
    manifest = json_file(directory / "manifest.json")
    require(manifest["schema_version"] == 2 and manifest["attempt_mode"] == "program_and_replay",
            "expected an actual schema-2 programming/replay trial")
    require(manifest["execute_requested"] and manifest["hardware_operations_started"] and manifest.get("finished_utc"),
            "physical attempt is unfinished")
    for name, digest in manifest["input_sha256"].items():
        bound(artifact(directory, name), digest)
    bound(artifact(directory, manifest["driver_snapshot"]), manifest["driver_sha256"])
    profile = json_file(directory / "profile.json")
    require(profile["device"] == manifest["device"] and profile["board_verified"] is True, "unverified device")
    image = bound(directory / "replay.bin")
    meta, samples = parse_replay_image(image)
    model_raw = bound(directory / "model.json")
    require(hashlib.sha256(model_raw).hexdigest() == meta["model_sha256"], "image/model mismatch")
    require(meta == manifest["replay_parameters"], "manifest/image parameters differ")
    build = json_file(directory / "build-report.json")
    require(build["bitstream_sha256"] == manifest["input_sha256"]["board.bin"]
            and build["model_sha256"] == meta["model_sha256"], "build bindings differ")
    expected_writes = [
        ("jedec", ["iceprog", "-d", profile["device"], "-t"]),
        ("configuration", ["iceprog", "-d", profile["device"], "-i", "4", "-o", "0", str(directory / "board.bin")]),
        ("input", write_commands(profile, directory / "replay.bin", "input")[0]),
        ("clear_log_and_start", write_commands(profile, directory / "erased-log.bin", "log")[0]),
    ]
    steps = manifest["steps"]
    for index, (name, command) in enumerate(expected_writes):
        require(steps[index]["name"] == name and steps[index]["argv"] == command, "programming sequence mismatch")
    for step in steps:
        require(step["returncode"] == 0 and step.get("finished_utc"), "unsuccessful programmer operation")
        text = bound(artifact(directory, step["transcript"]), step["transcript_sha256"]).decode()
        responses = re.findall(r"flash ID:\s*((?:0x[0-9a-fA-F]{2}[ \t]*)+)", text, re.I)
        ids = ["".join(re.findall(r"0x([0-9a-fA-F]{2})", response))[:6].upper() for response in responses]
        require(ids and all(value == "EF4016" for value in ids), "programmer JEDEC mismatch")
        require(step["observed_flash_id"] == "EF4016", "step JEDEC receipt mismatch")
        if "-i" in step["argv"]:
            require("VERIFY OK" in text, "programming lacks byte verification")
            bound(Path(step["argv"][-1]), step["input_sha256"])
    consensus = manifest["readback_consensus"]
    names = consensus["files"]
    require(consensus["unaltered"] is True and len(names) == 2 and names[0] != names[1], "invalid read consensus")
    reads = manifest["readback_attempts"]
    indices = [next(i for i, read in enumerate(reads) if read["file"] == name) for name in names]
    require(indices[1] == indices[0] + 1 and len(reads) <= 3, "reads were not consecutive")
    raw_pair = []
    for index in indices:
        read = reads[index]
        require(read["transport_valid"] and read["format_valid"] and read["returncode"] == 0
                and read["observed_flash_id"] == "EF4016", "invalid accepted read receipt")
        raw = bound(artifact(directory, read["file"]), read["sha256"])
        require(len(raw) == profile["log_bytes"] == 131072, "incorrect raw read length")
        step = next(step for step in steps if step["name"] == read["step"])
        require(step["argv"] == read_command(profile, directory / read["file"]), "read command differs from receipt")
        require(step["transcript"] == read["transcript"] and step["transcript_sha256"] == read["transcript_sha256"],
                "read transcript differs from receipt")
        raw_pair.append(raw)
    log = bound(directory / "result-log.bin", manifest["result_log_sha256"])
    require(raw_pair[0] == raw_pair[1] == log and hashlib.sha256(log).hexdigest() == consensus["sha256"],
            "unaltered raw files do not agree with final log")
    parsed = parse_result_log(log)
    model = json.loads(model_raw)
    for record in parsed["records"]:
        reference = classify(samples[record["frame_id"] % len(samples)], model, model)
        require(record["logits"] == reference["logits"].tolist() and record["class_id"] == reference["class_id"],
                f"score/class mismatch for frame {record['frame_id']}")
        require(record["error"] == 0 and record["protocol_errors"] == 0, "record error")
        require(record["cycles_total"] == sum(record[f"cycles_{name}"] for name in ("pre", "dft", "power", "nn")),
                "stage cycle accounting mismatch")
    return manifest, meta, parsed, build


def main():
    report = {"schema_version": 1, "passed": False, "overload_checks_passed": False,
              "created_utc": datetime.now(timezone.utc).isoformat(), "hardware_access_by_checker": False,
              "scope": "Expected physical digital overload and recovery after reconfiguration; no in-stream recovery claim",
              "clock_frequency_measured": False}
    output = BASE / "overload-verification.json"
    require(not output.exists(), "verification output already exists; preserve the existing result")
    try:
        bound(__file__)
        for name in ("board.py", "fixed.py"):
            bound(ROOT / "src/vibfpga" / name)
        expectations = json_file(BASE / "overload-expectations.json")
        manifest, meta, parsed, build = check_attempt(BASE / "l1-overload")
        require(manifest["status"] == "failed" and manifest["passed"] is False
                and manifest["core_verification_error"] and not manifest["read_transport_issue"],
                "normal driver did not reject the expected overload cleanly")
        require(build["lanes"] == expectations["lanes"] and meta["run_frames"] == expectations["run_frames"]
                and meta["period_cycles"] == expectations["period_cycles"], "overload parameters differ from declaration")
        for key, value in expectations["expected_counters"].items():
            require(parsed[key] == value, f"predeclared counter mismatch: {key}")
        require(parsed["requested_frames"] == meta["run_frames"] and parsed["period_cycles"] == meta["period_cycles"],
                "log period/frame request mismatch")
        require(parsed["accepted_samples"] + parsed["overflow_count"] == parsed["generated_samples"], "sample conservation failure")
        require([record["frame_id"] for record in parsed["records"]] == expectations["expected_frame_ids"], "frame IDs differ")
        for record in parsed["records"]:
            require(record["generated_samples"] == parsed["generated_samples"]
                    and record["accepted_samples"] == parsed["accepted_samples"], "overload record sample snapshots differ")
        report.update(overload_checks_passed=True, original_normal_manifest_remains_failed=True,
                      overload_trial_id=manifest["physical_trial_id"], counters={k: parsed[k] for k in expectations["expected_counters"]},
                      frame_ids=expectations["expected_frame_ids"], exact_score_records=len(parsed["records"]),
                      error_flag_interpretation={"0x08": "input FIFO overflow", "0x20": "tail timeout waiting for incomplete frame"})
        restart_dir = BASE / "l1-post-overload-5"
        restart_path = restart_dir / "manifest.json"
        state = json.loads(restart_path.read_bytes()) if restart_path.is_file() else {}
        if state.get("status") == "passed" and state.get("finished_utc"):
            restart, restart_meta, recovered, restart_build = check_attempt(restart_dir)
            require(restart["passed"] is True and restart["physical_trial_id"] != manifest["physical_trial_id"], "restart is not a separate successful trial")
            require(datetime.fromisoformat(restart["started_utc"]) > datetime.fromisoformat(manifest["finished_utc"]), "restart predates overload completion")
            require(restart["input_sha256"]["board.bin"] == manifest["input_sha256"]["board.bin"]
                    and restart_meta["model_sha256"] == meta["model_sha256"], "restart firmware/model differs")
            require(restart_meta["run_frames"] == 5 and restart_meta["period_cycles"] == 1000, "unexpected normal restart parameters")
            require(recovered["generated_samples"] == recovered["accepted_samples"] == 5120
                    and recovered["record_count"] == recovered["requested_frames"] == 5
                    and recovered["period_cycles"] == 1000, "normal restart counts differ")
            require(all(recovered[key] == 0 for key in ("error_flags", "overflow_count", "protocol_errors")), "restart retained an error")
            require([record["frame_id"] for record in recovered["records"]] == list(range(5)), "restart frame IDs differ")
            report.update(passed=True, required_evidence_complete=True,
                          recovery_after_reconfiguration={"status": "passed", "physical_trial_id": restart["physical_trial_id"],
                                                         "exact_score_records": 5, "same_bitstream": True, "in_stream_recovery": False})
        else:
            report.update(required_evidence_complete=False,
                          recovery_after_reconfiguration={"status": "not_evaluated", "observed_status": state.get("status"),
                                                         "reason": "subsequent successful run is not finished; parent must verify it"})
        for path, digest in list(BINDINGS.items()):
            bound(path, digest)
    except Exception as error:
        report.update(passed=False, error_type=type(error).__name__, error=str(error))
        raise
    finally:
        report["artifact_sha256"] = BINDINGS
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        with output.open("x") as stream:
            json.dump(report, stream, indent=2, sort_keys=True)
            stream.write("\n")
    print(json.dumps({key: report[key] for key in ("passed", "overload_checks_passed", "recovery_after_reconfiguration")}, indent=2))


if __name__ == "__main__":
    main()
