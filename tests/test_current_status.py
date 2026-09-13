"""Synthetic metadata/log fixtures exercise status checks; no physical operations."""
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("current_status", ROOT / "scripts/collect_current_status.py")
status = importlib.util.module_from_spec(spec)
spec.loader.exec_module(status)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def synthetic_attempt(tmp_path):
    root = tmp_path / "synthetic-root"
    for name in status.REQUIRED_INPUTS:
        source = root / name
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("synthetic test source\n")
    model = root / "artifacts/model/model.json"
    write_json(model, {"n": 1024, "fixture": True})
    (model.parent / "weights.hex").write_text("00\n")
    build = root / "build/run"
    build.mkdir(parents=True)
    (build / "board.bin").write_bytes(b"synthetic bitstream")
    (build / "clock_constraint.py").write_text("# synthetic constraint\n")
    sources = [*(root / name for name in status.REQUIRED_INPUTS), model, model.parent / "weights.hex", build / "clock_constraint.py"]
    report = {"input_sha256": {str(path.relative_to(root)): status.digest(path) for path in sources},
              "model_sha256": status.digest(model), "bitstream_sha256": status.digest(build / "board.bin"),
              "clock_source": "hfosc12", "lanes": 4, "place_route_completed": True}
    write_json(build / "report.json", report)
    attempt = root / "measurements/synthetic-attempt"
    attempt.mkdir(parents=True)
    for original, name in ((model, "model.json"), (build / "report.json", "build-report.json"), (build / "board.bin", "board.bin")):
        shutil.copy2(original, attempt / name)
    backup = root / "synthetic-backup.bin"
    backup.write_bytes(b"synthetic backup bytes")
    profile = {"board_verified": True, "device": "synthetic-device", "expected_flash_id": "EF4016",
               "backup_sha256": status.digest(backup), "log_bytes": 4160, "clock_source": "hfosc12"}
    write_json(attempt / "profile.json", profile)
    model_hash = status.digest(model)
    header = struct.pack("<4s7I32s", b"VIB1", 1, 1024, 1, 1, 1000, 2048, 0, bytes.fromhex(model_hash))
    (attempt / "replay.bin").write_bytes(header.ljust(4096, b"\xff") + bytes(2048))
    log_header = struct.pack("<4s11I", b"VLG1", 1, 1, 0x434F4D54, 0, 1024, 1024, 0, 0, 0, 1000, 1)
    log_record = struct.pack("<16I", 0, 10, 20, 30, 2, 1, 2, 3, 4, 10, 0, 1024, 1024, 0, 0, 0)
    (attempt / "result-log.bin").write_bytes(log_header.ljust(4096, b"\xff") + log_record)
    data = {"status": "passed", "passed": True, "execute_requested": True, "hardware_operations_started": True,
            "clock_source": "hfosc12",
            "observed_flash_id": "EF4016", "expected_flash_id": "EF4016", "device": "synthetic-device",
            "backup_path": str(backup), "backup_sha256": status.digest(backup),
            "input_sha256": {name: status.digest(attempt / name) for name in ("board.bin", "build-report.json", "model.json", "profile.json", "replay.bin")},
            "result_log_sha256": status.digest(attempt / "result-log.bin"),
            "verification": {"passed": True, "checked_frames": 1, "model_sha256": model_hash,
                             "input_image_sha256": status.digest(attempt / "replay.bin"), "result_log_sha256": status.digest(attempt / "result-log.bin")},
            "replay_parameters": {"n": 1024, "source_frames": 1, "run_frames": 1, "period_cycles": 1000, "model_sha256": model_hash},
            "counters": {"record_count": 1, "generated_samples": 1024, "accepted_samples": 1024,
                         "overflow_count": 0, "protocol_errors": 0, "error_flags": 0, "period_cycles": 1000}}
    write_json(attempt / "manifest.json", data)
    return root, attempt


def test_status_validates_saved_receipt_without_running_inference(tmp_path, monkeypatch):
    root, attempt = synthetic_attempt(tmp_path)
    def forbidden(*args, **kwargs):
        raise AssertionError("status must not rerun inference or physical verification")
    monkeypatch.setattr("vibfpga.board.verify_replay_log", forbidden)
    monkeypatch.setattr("run_hardware_replay.verify_normal", forbidden)
    before = {p: status.digest(p) for p in root.rglob("*") if p.is_file()}
    result = status.inspect_attempt(attempt / "manifest.json", root)
    assert result["current_physical_pass"] and not result["inference_rerun"]
    assert {p: status.digest(p) for p in root.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("name", ["result-log.bin", "model.json", "build-report.json"])
def test_tampered_or_missing_attempt_artifact_cannot_claim_pass(tmp_path, name):
    root, attempt = synthetic_attempt(tmp_path)
    (attempt / name).unlink()
    result = status.inspect_attempt(attempt / "manifest.json", root)
    assert not result["current_physical_pass"] and result["errors"]


def test_changed_source_marks_saved_pass_stale(tmp_path):
    root, attempt = synthetic_attempt(tmp_path)
    (root / "rtl/io/flash_stream.sv").write_text("changed source")
    result = status.inspect_attempt(attempt / "manifest.json", root)
    assert not result["current_physical_pass"]
    assert "attempt's build is stale or invalid against current inputs" in result["errors"]


@pytest.mark.parametrize("section,key,value", [("verification", "result_log_sha256", "0" * 64), ("counters", "accepted_samples", 1023)])
def test_receipt_binding_and_counter_tampering_rejected(tmp_path, section, key, value):
    root, attempt = synthetic_attempt(tmp_path)
    path = attempt / "manifest.json"
    data = json.loads(path.read_text())
    data[section][key] = value
    write_json(path, data)
    result = status.inspect_attempt(path, root)
    assert not result["current_physical_pass"] and result["errors"]


@pytest.mark.parametrize("state", ["running", "failed", "dry_run"])
def test_incomplete_failed_and_dry_attempts_never_count(tmp_path, state):
    path = tmp_path / "manifest.json"
    write_json(path, {"status": state, "passed": True, "error": "retained failure"})
    before = path.read_bytes()
    result = status.inspect_attempt(path, tmp_path)
    assert not result["current_physical_pass"]
    assert result["status"] == state and path.read_bytes() == before


def test_readback_receipts_do_not_double_count_physical_trials():
    receipt = {"current_physical_pass": True, "physical_trial_id": "same-programmed-run",
               "replay_parameters": {"run_frames": 1000}, "manifest": "original/manifest.json"}
    recovery = {**receipt, "manifest": "recovery/manifest.json"}
    failed = {**receipt, "current_physical_pass": False, "physical_trial_id": "failed-other-run"}
    trials = status.summarize_trials([receipt, recovery, failed])
    assert len(trials) == 1 and trials[0]["frames"] == 1000
    assert len(trials[0]["receipts"]) == 2


def add_consensus(attempt, data):
    driver = attempt / "run_hardware_replay.py"
    driver.write_text("# synthetic driver snapshot\n")
    data.update(driver_snapshot=driver.name, driver_sha256=status.digest(driver))
    reads = []
    for index in (1, 2):
        name, transcript = f"read-log-0{index}.bin", f"read_log_{index}.txt"
        shutil.copy2(attempt / "result-log.bin", attempt / name)
        (attempt / transcript).write_text("synthetic successful read transcript")
        reads.append({"step": f"read_log_{index}", "file": name, "sha256": status.digest(attempt / name),
                      "transcript": transcript, "transcript_sha256": status.digest(attempt / transcript),
                      "observed_flash_id": "EF4016", "returncode": 0, "transport_valid": True, "format_valid": True})
    data["steps"] = [{"name": read["step"], "returncode": 0, "argv": ["iceprog", "-R", "4160", str(attempt / read["file"])],
                      "transcript": read["transcript"], "transcript_sha256": read["transcript_sha256"]} for read in reads]
    data.update(schema_version=2, readback_attempts=reads,
                readback_consensus={"files": [read["file"] for read in reads], "sha256": data["result_log_sha256"],
                                    "result_file": "result-log.bin", "unaltered": True})
    return data


def synthetic_recovery(tmp_path):
    root, origin = synthetic_attempt(tmp_path)
    original = status.read_json(origin / "manifest.json")
    original.update(status="failed", passed=False, steps=[])
    for name in ("jedec", "configuration", "input", "clear_log_and_start"):
        transcript = origin / f"{name}.txt"
        transcript.write_text("synthetic successful programming transcript")
        original["steps"].append({"name": name, "returncode": 0, "argv": ["iceprog", "synthetic-step", name], "transcript": transcript.name})
    write_json(origin / "manifest.json", original)
    origin_hash = status.digest(origin / "manifest.json")
    trial_id = f"origin-manifest-sha256:{origin_hash}"
    recovery = root / "measurements/synthetic-recovery"
    shutil.copytree(origin, recovery)
    shutil.copy2(origin / "manifest.json", recovery / "origin-manifest.json")
    data = add_consensus(recovery, {**original, "status": "passed", "passed": True})
    data.update(attempt_mode="readback_only_recovery", physical_trial_id=trial_id,
                recovery_origin={"path": str(origin), "manifest_sha256": origin_hash, "physical_trial_id": trial_id},
                origin_programming_steps=[{**step, "transcript": str(origin / step["transcript"]),
                                           "transcript_sha256": status.digest(origin / step["transcript"])} for step in original["steps"]])
    write_json(recovery / "manifest.json", data)
    return root, origin, recovery


def test_recovery_preserves_origin_and_inherits_one_physical_trial(tmp_path):
    root, origin, recovery = synthetic_recovery(tmp_path)
    before = {p: status.digest(p) for p in origin.iterdir() if p.is_file()}
    result = status.inspect_attempt(recovery / "manifest.json", root)
    original_result = status.inspect_attempt(origin / "manifest.json", root)
    assert result["current_physical_pass"], result["errors"]
    assert result["recovery_of_existing_trial"]
    assert result["physical_trial_id"] == original_result["physical_trial_id"]
    assert len(status.summarize_trials([result, original_result])) == 1
    assert {p: status.digest(p) for p in origin.iterdir() if p.is_file()} == before


@pytest.mark.parametrize("change", ["raw_read", "origin_manifest", "origin_transcript", "write_step", "same_read_twice", "nonconsecutive"])
def test_recovery_rejects_missing_or_forged_provenance(tmp_path, change):
    root, origin, recovery = synthetic_recovery(tmp_path)
    manifest = recovery / "manifest.json"
    data = status.read_json(manifest)
    if change == "raw_read":
        (recovery / "read-log-02.bin").write_bytes(b"changed bytes")
    elif change == "origin_manifest":
        with (origin / "manifest.json").open("a") as stream:
            stream.write(" ")
    elif change == "origin_transcript":
        (origin / "configuration.txt").write_text("changed transcript")
    elif change == "write_step":
        data["steps"].append({"argv": ["iceprog", "-i", "4", "board.bin"]})
    elif change == "same_read_twice":
        data["readback_consensus"]["files"] = ["read-log-01.bin", "read-log-01.bin"]
    else:
        data["readback_attempts"].insert(1, {"file": "invalid-middle-read.bin", "transport_valid": False})
    write_json(manifest, data)
    result = status.inspect_attempt(manifest, root)
    assert not result["current_physical_pass"] and result["errors"]


def test_schema_two_normal_attempt_also_requires_consensus(tmp_path):
    root, attempt = synthetic_attempt(tmp_path)
    manifest = attempt / "manifest.json"
    data = status.read_json(manifest)
    data.update(schema_version=2, attempt_mode="program_and_replay", physical_trial_id="synthetic-normal-trial")
    write_json(manifest, data)
    assert not status.inspect_attempt(manifest, root)["current_physical_pass"]
    write_json(manifest, add_consensus(attempt, data))
    result = status.inspect_attempt(manifest, root)
    assert result["current_physical_pass"], result["errors"]


def test_markdown_exposes_single_read_and_consensus_distinction():
    data = {"generated_utc": "synthetic timestamp", "project_root": "/synthetic-project", "current_physical_passes": 2,
            "current_physical_trial_count": 2, "current_physical_unique_frames": 1005, "failed_attempts_retained": 0,
            "profiles": [], "migration": {"compatibility_path": "/synthetic-alias", "compatibility_symlink_valid": True},
            "board": {"backup_hash_verified": True}, "field_fixture": {"status": "evaluated", "verification": "passed"},
            "builds": [], "physical_attempts": []}
    for name, evidence in (("legacy", "legacy single saved read; no two-read consensus receipt"),
                           ("consensus", "two consecutive identical unaltered saved reads")):
        data["physical_attempts"].append({"manifest": f"/synthetic-project/{name}/manifest.json", "status": "passed",
                                         "current_physical_pass": True, "errors": [], "claim": "saved pass",
                                         "readback_evidence": evidence})
    rendered = status.markdown(data)
    assert "legacy single saved read; no two-read consensus receipt" in rendered
    assert "two consecutive identical unaltered saved reads" in rendered
