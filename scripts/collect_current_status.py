#!/usr/bin/env python3
"""Summarize current, hash-bound evidence without builds, inference or hardware I/O."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from vibfpga.board import parse_result_log
from vibfpga.field_status import inspect_field
from vibfpga.project_profile import load_profile
from run_hardware_replay import REQUIRED_INPUTS


def digest(path):
    hasher = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def rooted(path, root):
    value = Path(path)
    return (value if value.is_absolute() else root / value).resolve()


def matched(path, expected):
    return isinstance(expected, str) and len(expected) == 64 and Path(path).is_file() and digest(path) == expected


def inspect_build(path, root=ROOT, required_inputs=None):
    """Check a report's current source/model/ROM inputs and its colocated bitstream."""
    path, root = Path(path), Path(root).resolve()
    out = {"report": str(path), "current": False, "errors": []}
    try:
        start_hash = digest(path)
        report = read_json(path)
        out.update(report_sha256=start_hash, built_utc=report.get("built_utc"), lanes=report.get("lanes"),
                   clock_source=report.get("clock_source"), model_sha256=report.get("model_sha256"),
                   bitstream_sha256=report.get("bitstream_sha256"), utilization=report.get("utilization", {}),
                   post_route_fmax=report.get("post_route_fmax", {}), target_clock_mhz=report.get("target_clock_mhz"),
                   timing_is_place_route_estimate=True, clock_frequency_measured=False)
        inputs = report.get("input_sha256", {})
        if not isinstance(inputs, dict) or not inputs:
            raise ValueError("missing build input hashes")
        normalized = {rooted(name, root): expected for name, expected in inputs.items()}
        missing = [name for name in (REQUIRED_INPUTS if required_inputs is None else required_inputs) if rooted(name, root) not in normalized]
        if missing:
            out["errors"].append("missing required build provenance: " + ", ".join(missing))
        out["changed_or_missing_inputs"] = [str(name) for name, expected in normalized.items() if not matched(name, expected)]
        if out["changed_or_missing_inputs"]:
            out["errors"].append("build source/model inputs are stale or missing")
        models = [name for name, expected in normalized.items() if name.name == "model.json" and expected == report.get("model_sha256")]
        if len(models) != 1:
            out["errors"].append("build must bind exactly one model JSON")
        else:
            roms = list(models[0].parent.glob("*.hex"))
            if not roms or any(p.resolve() not in normalized for p in roms):
                out["errors"].append("model ROM provenance is incomplete")
        if report.get("clock_source") == "hfosc12" and not any(p.name == "clock_constraint.py" for p in normalized):
            out["errors"].append("internal-clock constraint provenance is missing")
        if not matched(path.parent / "board.bin", report.get("bitstream_sha256")):
            out["errors"].append("missing or changed bitstream")
        if report.get("place_route_completed") is not True:
            out["errors"].append("place and route is incomplete")
        if digest(path) != start_hash:
            out["errors"].append("build report changed during collection")
        out["current"] = not out["errors"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        out["errors"].append(str(error))
    return out


def inspect_attempt(path, root=ROOT, required_inputs=None):
    """Validate saved score-verification bindings and counters; never rerun inference."""
    path, root = Path(path), Path(root).resolve()
    out = {"manifest": str(path), "current_physical_pass": False, "errors": [], "inference_rerun": False}
    out.update(recovery_of_existing_trial=False)
    try:
        start_hash = digest(path)
        data = read_json(path)
        out["physical_trial_id"] = data.get("physical_trial_id") or f"origin-manifest-sha256:{start_hash}"
        out.update(manifest_sha256=start_hash, status=data.get("status", "unknown"),
                   started_utc=data.get("started_utc"), finished_utc=data.get("finished_utc"),
                   recorded_error=data.get("error"), recorded_pass=data.get("passed", False),
                   clock_source=data.get("clock_source"), nominal_clock_hz=data.get("nominal_clock_hz"),
                   actual_clock_measured=data.get("actual_clock_measured", False),
                   clock_timing_basis=data.get("clock_timing_basis"),
                   replay_parameters=data.get("replay_parameters", {}))
        if data.get("status") != "passed":
            out["claim"] = "failed, dry or incomplete attempt; no current passing claim"
            return out
        if data.get("passed") is not True or data.get("execute_requested") is not True or data.get("hardware_operations_started") is not True:
            raise ValueError("pass lacks recorded physical execution")
        if not data.get("observed_flash_id") or data["observed_flash_id"] != data.get("expected_flash_id"):
            raise ValueError("observed JEDEC binding is missing or mismatched")
        inputs = data.get("input_sha256", {})
        for name in ("board.bin", "build-report.json", "model.json", "profile.json", "replay.bin"):
            if not matched(path.parent / name, inputs.get(name)):
                out["errors"].append(f"attempt artifact missing or changed: {name}")
        if not matched(path.parent / "result-log.bin", data.get("result_log_sha256")):
            out["errors"].append("result log missing or changed")
        if out["errors"]:
            return out
        out.update(validate_readback_provenance(path, data, root))
        profile = read_json(path.parent / "profile.json")
        if (profile.get("board_verified") is not True or profile.get("device") != data.get("device")
                or profile.get("expected_flash_id") != data.get("observed_flash_id")):
            out["errors"].append("physical device/JEDEC profile binding mismatch")
        backup = rooted(data.get("backup_path", "missing-backup"), root)
        if data.get("backup_sha256") != profile.get("backup_sha256") or not matched(backup, data.get("backup_sha256")):
            out["errors"].append("original Flash backup binding missing or changed")
        build = inspect_build(path.parent / "build-report.json", root, required_inputs)
        out.update(build_current=build["current"], build_errors=build["errors"], lanes=build.get("lanes"))
        if not build["current"]:
            out["errors"].append("attempt's build is stale or invalid against current inputs")
        if build.get("model_sha256") != inputs["model.json"] or build.get("bitstream_sha256") != inputs["board.bin"]:
            out["errors"].append("build/model/bitstream bindings disagree")
        if data.get("clock_source") != profile.get("clock_source") or data.get("clock_source") != build.get("clock_source"):
            out["errors"].append("attempt/profile/build clock source mismatch")
        verified = data.get("verification", {})
        expected_bindings = {"passed": True, "model_sha256": inputs["model.json"],
                             "input_image_sha256": inputs["replay.bin"], "result_log_sha256": data["result_log_sha256"]}
        if any(verified.get(key) != value for key, value in expected_bindings.items()):
            out["errors"].append("saved score verification receipt does not bind the same model/image/log")
        # Read only replay metadata; sample payload is streamed for its digest above.
        with (path.parent / "replay.bin").open("rb") as stream:
            header = stream.read(64)
        magic, version, n, source_frames, runs, period, size, crc, model_hash = struct.unpack("<4s7I32s", header)
        if (magic, version, n) != (b"VIB1", 1, 1024) or not 1 <= runs <= 1000 or not 1 <= source_frames <= 16:
            raise ValueError("invalid saved replay header")
        meta = {"n": n, "source_frames": source_frames, "run_frames": runs, "period_cycles": period, "model_sha256": model_hash.hex()}
        if meta != data.get("replay_parameters") or meta["model_sha256"] != inputs["model.json"]:
            out["errors"].append("replay metadata/model binding mismatch")
        log = (path.parent / "result-log.bin").read_bytes()
        if len(log) != profile.get("log_bytes"):
            out["errors"].append("saved log byte count does not match profile")
        parsed = parse_result_log(log)
        expected = {"record_count": runs, "generated_samples": n * runs, "accepted_samples": n * runs,
                    "overflow_count": 0, "protocol_errors": 0, "error_flags": 0, "period_cycles": period}
        if any(parsed[key] != value or data.get("counters", {}).get(key) != value for key, value in expected.items()):
            out["errors"].append("normal replay counters disagree with requested frames or saved counters")
        if parsed["requested_frames"] != runs or verified.get("checked_frames") != runs:
            out["errors"].append("verified frame count mismatch")
        for index, record in enumerate(parsed["records"]):
            if (record["frame_id"] != index or record["error"] or record["protocol_errors"]
                    or record["cycles_total"] != sum(record[f"cycles_{stage}"] for stage in ("pre", "dft", "power", "nn"))):
                out["errors"].append(f"record {index} has inconsistent completion/stage counters")
                break
        out.update(counters=expected, stage_timing=data.get("stage_timing", {}),
                   score_claim="saved integer-reference comparison; same input/model/log hashes validated, inference not rerun")
        if digest(path) != start_hash:
            out["errors"].append("attempt manifest changed during collection")
        out["current_physical_pass"] = not out["errors"]
        out["claim"] = ("provenance_validated_readback_recovery_of_same_physical_trial" if out.get("recovery_of_existing_trial")
                        else "provenance_validated_saved_physical_replay") if out["current_physical_pass"] else "saved pass is not current evidence"
    except (OSError, ValueError, KeyError, TypeError, struct.error) as error:
        out["errors"].append(str(error))
    return out


def validate_readback_provenance(path, data, root):
    """Bind schema-2 consensus reads and recovery to the original programmed trial."""
    mode = data.get("attempt_mode", "program_and_replay")
    recovery = mode in ("readback_only_recovery", "acoustic_readback_only_recovery")
    if data.get("schema_version", 1) < 2 and not recovery:
        return {"readback_evidence": "legacy single saved read; no two-read consensus receipt"}
    if mode not in ("program_and_replay", "readback_only_recovery", "acoustic_readback_only_recovery") or not data.get("physical_trial_id"):
        raise ValueError("schema-2 attempt mode or physical trial ID missing")
    driver = data.get("driver_snapshot", "")
    if not driver or Path(driver).name != driver or not matched(path.parent / driver, data.get("driver_sha256")):
        raise ValueError("schema-2 driver snapshot missing or changed")
    for name, expected in data.get("input_sha256", {}).items():
        if Path(name).name != name or not matched(path.parent / name, expected):
            raise ValueError("schema-2 input snapshot missing or changed")
    reads = data.get("readback_attempts", [])
    consensus = data.get("readback_consensus", {})
    files = consensus.get("files", [])
    if not 2 <= len(reads) <= 3 or len(files) != 2 or len(set(files)) != 2:
        raise ValueError("readback consensus requires two distinct reads, at most three attempts")
    if (consensus.get("unaltered") is not True or consensus.get("result_file") != "result-log.bin"
            or consensus.get("sha256") != data.get("result_log_sha256")):
        raise ValueError("readback consensus does not bind the unaltered result log")
    indices = []
    for name in files:
        matches = [(index, read) for index, read in enumerate(reads) if read.get("file") == name]
        if len(matches) != 1 or Path(name).name != name:
            raise ValueError("ambiguous or unsafe consensus read filename")
        index, read = matches[0]
        indices.append(index)
        if (read.get("returncode") != 0 or read.get("transport_valid") is not True or read.get("format_valid") is not True
                or read.get("observed_flash_id") != data.get("expected_flash_id")
                or read.get("sha256") != consensus["sha256"] or not matched(path.parent / name, read.get("sha256"))):
            raise ValueError("consensus raw read missing, changed, invalid or from mismatched device")
        transcript = path.parent / read.get("transcript", "missing")
        if not matched(transcript, read.get("transcript_sha256")):
            raise ValueError("consensus read transcript missing or changed")
        steps = [step for step in data.get("steps", []) if step.get("name") == read.get("step")]
        if len(steps) != 1:
            raise ValueError("consensus read lacks a unique recorded hardware read step")
        step = steps[0]
        argv = step.get("argv", [])
        if (step.get("returncode") != 0 or not argv or Path(argv[0]).name != "iceprog" or "-R" not in argv or "-i" in argv
                or Path(argv[-1]).resolve() != (path.parent / name).resolve()
                or step.get("transcript") != read.get("transcript") or step.get("transcript_sha256") != read.get("transcript_sha256")):
            raise ValueError("consensus read command/transcript binding mismatch")
    if indices[1] != indices[0] + 1:
        raise ValueError("consensus reads must be consecutive")
    out = {"readback_evidence": "two consecutive identical unaltered saved reads", "readback_consensus_files": files,
           "recovery_of_existing_trial": recovery}
    if not recovery:
        return out
    origin_ref = data.get("recovery_origin", {})
    origin_dir = rooted(origin_ref.get("path", "missing-origin"), root)
    origin_path = origin_dir / "manifest.json"
    if origin_dir == path.parent.resolve() or not matched(origin_path, origin_ref.get("manifest_sha256")):
        raise ValueError("recovery origin manifest missing, changed or self-referential")
    if not matched(path.parent / "origin-manifest.json", origin_ref.get("manifest_sha256")):
        raise ValueError("saved recovery origin manifest snapshot missing or changed")
    origin = read_json(origin_path)
    if origin.get("status") not in ("failed", "passed"):
        raise ValueError("recovery origin must be a completed attempt with a retained final manifest")
    if origin.get("attempt_mode", "program_and_replay") != "program_and_replay":
        raise ValueError("recovery origin must be the original programmed replay")
    trial = origin.get("physical_trial_id") or f"origin-manifest-sha256:{origin_ref['manifest_sha256']}"
    if data["physical_trial_id"] != trial or origin_ref.get("physical_trial_id") != trial:
        raise ValueError("readback recovery does not inherit the original physical trial ID")
    if origin.get("execute_requested") is not True or origin.get("hardware_operations_started") is not True:
        raise ValueError("recovery origin has no recorded hardware execution")
    for key in ("device", "expected_flash_id", "observed_flash_id", "clock_source", "replay_parameters", "backup_sha256"):
        if origin.get(key) != data.get(key):
            raise ValueError(f"recovery origin {key} binding mismatch")
    for name, expected in origin["input_sha256"].items():
        if Path(name).name != name or expected != data["input_sha256"].get(name) or not matched(origin_dir / name, expected):
            raise ValueError("original attempt input snapshot missing or changed")
    if origin.get("result_log_sha256") and not matched(origin_dir / "result-log.bin", origin["result_log_sha256"]):
        raise ValueError("original failed result log missing or changed")
    for read in origin.get("readback_attempts", []):
        if read.get("sha256") and not matched(origin_dir / read["file"], read["sha256"]):
            raise ValueError("original failed raw read missing or changed")
    steps = {step.get("name"): step for step in origin.get("steps", [])}
    copied = {step.get("name"): step for step in data.get("origin_programming_steps", [])}
    for name in ("jedec", "configuration", "input", "clear_log_and_start"):
        original, saved = steps.get(name, {}), copied.get(name, {})
        if original.get("returncode") != 0 or saved.get("returncode") != 0 or original.get("argv") != saved.get("argv"):
            raise ValueError(f"recovery origin lacks successful {name} provenance")
        transcript = origin_dir / original.get("transcript", "missing")
        if Path(saved.get("transcript", "missing")).resolve() != transcript.resolve() or not matched(transcript, saved.get("transcript_sha256")):
            raise ValueError(f"recovery origin {name} transcript missing or changed")
        if saved.get("input_file") and not matched(Path(saved["input_file"]), saved.get("input_sha256")):
            raise ValueError(f"recovery origin {name} command input missing or changed")
    for step in data.get("steps", []):
        argv = step.get("argv", [])
        if not argv or Path(argv[0]).name != "iceprog" or "-i" in argv or not ("-R" in argv or "-t" in argv):
            raise ValueError("readback-only recovery contains a non-read hardware step")
    out.update(physical_trial_id=trial, recovery_origin_manifest=str(origin_path),
               recovery_origin_manifest_sha256=origin_ref["manifest_sha256"])
    return out


def summarize_trials(attempts):
    """Readback receipts for one programmed replay are not independent trials."""
    trials = {}
    for attempt in attempts:
        if not attempt.get("current_physical_pass"):
            continue
        trial_id = attempt["physical_trial_id"]
        frames = attempt["replay_parameters"]["run_frames"]
        if trial_id not in trials:
            trials[trial_id] = {"physical_trial_id": trial_id, "frames": frames, "receipts": []}
        elif trials[trial_id]["frames"] != frames:
            raise ValueError("same physical trial has inconsistent frame counts")
        trials[trial_id]["receipts"].append(attempt["manifest"])
    return list(trials.values())


def identify_board(directory):
    out = {"identified_from_saved_evidence": False, "connection_rechecked": False, "backup_hash_verified": False,
           "clock_frequency_measured": False, "power_measured": False, "errors": []}
    try:
        usb = read_json(directory / "usb-identification.json")
        board = [entry for entry in usb if entry.get("idVendor") == 0x403 and entry.get("idProduct") == 0x6014]
        if len(board) != 1:
            raise ValueError("saved USB evidence does not identify exactly one target board")
        flash_text = (directory / "flash-identification.txt").read_text()
        match = re.search(r"flash ID:\s*((?:0x[0-9a-fA-F]{2}\s*)+)", flash_text)
        flash_id = "".join(re.findall(r"0x([0-9a-fA-F]{2})", match[1]))[:6].upper() if match else None
        backup = read_json(directory / "backup.json")
        backup_path = directory / "original-flash-4MiB.bin"
        out.update(board=board[0]["USB Product Name"], flash_id=flash_id, flash_bytes=backup.get("bytes"),
                   backup_sha256=backup.get("sha256"), evidence_directory=str(directory))
        if not flash_id or flash_id != backup.get("flash_id"):
            raise ValueError("Flash identification and backup metadata disagree")
        out["identified_from_saved_evidence"] = True
        out["backup_hash_verified"] = (backup_path.stat().st_size == backup.get("bytes") == 4194304
                                        and matched(backup_path, backup.get("sha256")))
        if not out["backup_hash_verified"]:
            out["errors"].append("full original Flash backup hash/size mismatch")
        independent = directory / "backup-independent-check.json"
        out["independent_backup_comparison_recorded"] = independent.is_file() and read_json(independent).get("passed") is True
        out["evidence_sha256"] = {name: digest(directory / name) for name in ("usb-identification.json", "flash-identification.txt", "backup.json")}
    except (OSError, ValueError, KeyError, TypeError) as error:
        out["errors"].append(str(error))
    return out


def collect(root=ROOT):
    root = Path(root).resolve()
    migration_path = root / "artifacts/evidence/migration-2026-09-10.json"
    migration = read_json(migration_path) if migration_path.exists() else {}
    compatibility = Path(migration["source"]) if migration.get("source") else None
    data = {"schema_version": 1, "generated_utc": datetime.now(timezone.utc).isoformat(), "project_root": str(root),
            "collection_scope": "saved evidence only; no hardware I/O, builds, training, inference or test waveform loading",
            "migration": {"evidence": str(migration_path), "moved_at_utc": migration.get("moved_at_utc"),
                          "compatibility_path": str(compatibility) if compatibility else None,
                          "compatibility_symlink_valid": bool(compatibility and compatibility.is_symlink() and compatibility.resolve() == root)},
            "profiles": [], "pending": ["ADXL345 sensor acquisition and real field training", "external clock connection/frequency calibration",
                                          "HFOSC physical frequency measurement", "electrical timing and power measurement"]}
    for name in ("cwru-neighbor3", "sen1-spectrum", "fcl1-fixture"):
        try:
            profile = load_profile(name, root=root)
            relative = str(Path(profile["model"]).relative_to(root))
            expected = migration.get("sha256", {}).get(relative)
            if name == "fcl1-fixture":
                expected = read_json(Path(profile["run_dir"]) / "frozen.json")["files"]["model/model.json"]
            data["profiles"].append({key: profile.get(key) for key in ("name", "description", "n", "sample_rate_hz", "lanes", "model", "model_sha256", "model_training_status")} |
                                    {"recorded_model_sha256": expected, "matches_recorded_model_digest": profile["model_sha256"] == expected if expected else None})
        except (OSError, ValueError, KeyError, TypeError) as error:
            data["profiles"].append({"name": name, "error": str(error)})
    measurements = root / "measurements/2026-09-10-upduino31"
    data["board"] = identify_board(measurements)
    data["builds"], data["other_build_reports"] = [], []
    for path in sorted((root / "build/hardware-2026-09-10/runs").glob("**/report.json")):
        try:
            top = read_json(path).get("top")
            if top == "upduino_replay":
                data["builds"].append(inspect_build(path, root))
            else:
                data["other_build_reports"].append({"report": str(path), "top": top, "scope": "not checked by this replay-build status table"})
        except (OSError, ValueError) as error:
            data["other_build_reports"].append({"report": str(path), "scope": "unreadable or incomplete report", "error": str(error)})
    data["physical_attempts"] = [inspect_attempt(path, root) for path in sorted(measurements.glob("*/manifest.json"))]
    data["field_fixture"] = inspect_field(root / "build/field_fixture/trained", root=root, verify=True)
    data["current_physical_passes"] = sum(attempt["current_physical_pass"] for attempt in data["physical_attempts"])
    data["current_physical_trials"] = summarize_trials(data["physical_attempts"])
    data["current_physical_trial_count"] = len(data["current_physical_trials"])
    data["current_physical_unique_frames"] = sum(trial["frames"] for trial in data["current_physical_trials"])
    data["failed_attempts_retained"] = sum(attempt.get("status") == "failed" for attempt in data["physical_attempts"])
    acoustic = root / "artifacts/acoustic"
    if (acoustic / "frozen.json").exists():
        from run_acoustic_hardware import REQUIRED_INPUTS as acoustic_inputs
        frozen = read_json(acoustic / "frozen.json")
        validation = read_json(acoustic / "validation.json")
        data["acoustic"] = {
            "freeze_current": all(matched(root / rel, h) for rel,h in frozen["sha256"].items()),
            "validation": validation,
            "test_evaluated": (acoustic / "test.json").exists(),
            "microphone_tested": False,
            "builds": [inspect_build(p,root,acoustic_inputs) for p in sorted((root / "build/runs/acoustic-v1").glob("*/report.json"))],
            "physical_attempts": [inspect_attempt(p,root,acoustic_inputs) for p in sorted((root / "measurements/2026-09-11-acoustic").glob("*/manifest.json"))],
        }
    study_root = root / "artifacts/acoustic-v2-analysis"
    if (study_root / "summary.json").exists():
        summary = read_json(study_root / "summary.json")
        receipt = read_json(study_root / "receipt.json")
        valid = all(matched(root / rel, h) for rel, h in receipt["sha256"].items())
        for folder in ("acoustic-v2-study", "acoustic-v2-logpower"):
            folder = root / "artifacts" / folder
            r = read_json(folder / "receipt.json")
            protocol = read_json(folder / "protocol.json")
            valid = valid and all(matched(root / rel, h) for rel, h in r["sha256"].items())
            valid = valid and all(matched(root / rel, h) for rel, h in protocol["source_sha256"].items())
        data["acoustic_feature_study"] = {"current": valid, "summary": summary}
    diagnoses = []
    for name in ("acoustic-v3-diagnosis", "acoustic-v3-resolution", "acoustic-v4-temporal", "acoustic-v5-finespectrum", "acoustic-v6-panns"):
        folder = root / "artifacts" / name
        if (folder / "receipt.json").exists():
            receipt = read_json(folder / "receipt.json"); protocol = read_json(folder / "protocol.json")
            current = all(matched(root / rel, h) for rel, h in receipt["sha256"].items())
            current = current and all(matched(root / rel, h) for rel, h in protocol["source_sha256"].items())
            result = read_json(folder / "validation.json")
            diagnoses.append({"name": name, "current": current, "selected": result["selected"], "candidates": len(result["candidates"]), "test_opened": result["test_opened"]})
    if diagnoses:
        data["acoustic_diagnosis"] = diagnoses
    supervised = root / "artifacts/acoustic-v7-supervised-r2"
    if (supervised / "goal-completion-audit.json").exists():
        audit = read_json(supervised / "goal-completion-audit.json")
        freeze = read_json(supervised / "frozen.json")
        valid = all(matched(root / rel, h) for rel, h in audit["sha256"].items())
        valid = valid and all(matched(root / rel, h) for rel, h in freeze["sha256"].items())
        data["acoustic_supervised"] = {"current": valid, "audit": audit, "test": read_json(supervised / "test.json")}
    external = root / "artifacts/acoustic-external-id02"
    completion = root / "artifacts/acoustic-recording-audit-completion"
    near = root / "artifacts/acoustic-recording-audit"
    if (external / "receipt.json").exists() and (completion / "receipt.json").exists():
        valid = True
        for folder in (external, completion, near):
            receipt = read_json(folder / "receipt.json")
            valid = valid and all(matched(root / rel, h) for rel, h in receipt["sha256"].items())
        protocol = read_json(near / "protocol.json")
        valid = valid and all(matched(root / rel, h) for rel, h in protocol["source_sha256"].items())
        data["acoustic_generalization"] = {"current": valid, "external": read_json(external / "results.json"),
            "near_duplicate_completion": read_json(completion / "results.json"), "external_independence": read_json(external / "independence-audit.json")}
    mp = root / "data/mimii-multimachine/plan.json"
    if mp.exists():
        plan = read_json(mp); folder = root / "artifacts/acoustic-multimachine-v1"
        mm = {"development_records": 960, "test_records": 160, "old_test_excluded": len(plan["excluded_old_test"]),
              "verified_receipts": len(list((mp.parent / "receipts").glob("*.json"))), "frozen": False, "test_evaluated": False}
        if (folder / "frozen.json").exists():
            f = read_json(folder / "frozen.json"); d = read_json(folder / "development.json")["selected"]
            mm.update(frozen=True, current=all(matched(root / rel, h) for rel,h in f["sha256"].items()), candidate=f["candidate"],
                      all_development_folds_passed=d["all_folds_passed"], threshold=f["threshold"],
                      folds=[{k:r[k] for k in ("machine","auc","recall","fpr","gate_passed")} for r in d["folds"]])
        if (folder / "test.json").exists():
            t = read_json(folder / "test.json")
            mm.update(test_evaluated=True, test={k:t[k] for k in ("auc","recall","fpr","confusion_matrix","high_standard_passed","threshold_unchanged")})
        data["multimachine"] = mm
    temporal = root / "artifacts/acoustic-multimachine-temporal-v1"
    if (temporal / "results.json").exists():
        result = read_json(temporal / "results.json")
        binding = read_json(temporal / "bindings.json")
        data["temporal_study"] = {"selected": result["selected"], "candidates": len(result["candidates"]),
            "current": all(matched(root / p,h) for p,h in {**binding["sha256"], **binding["source_sha256"]}.items()),
            "audit_passed": (temporal / "audit.json").exists() and read_json(temporal / "audit.json")["passed"], "test_opened": False}
    shift = root / "artifacts/acoustic-source-invariant-v1"
    if (shift / "results.json").exists():
        result = read_json(shift / "results.json"); b = read_json(shift / "bindings.json")
        data["source_invariant"] = {"selected": result["selected"]["name"], "all_passed": result["selected"]["all_passed"],
            "current": all(matched(root / p,h) for p,h in b["sha256"].items()) and matched(root / "scripts/train_source_invariant.py",b["source_sha256"]),
            "audit_passed": (shift / "audit.json").exists() and read_json(shift / "audit.json")["passed"]}
    cnn = root / "artifacts/acoustic-cnn-v3"
    if (cnn / "results.json").exists():
        c=read_json(cnn / "results.json"); b=read_json(cnn / "bindings.json")
        data["cnn_study"]={"all_passed":c["all_passed"], "current":all(matched(root / p,h) for p,h in b["sha256"].items()),
            "audit_passed":(cnn / "audit.json").exists() and read_json(cnn / "audit.json")["passed"]}
    pre = root / "artifacts/acoustic-pretrained-v1"
    if (pre / "results.json").exists():
        d=read_json(pre / "results.json");b=read_json(pre / "bindings.json")
        data["pretrained_study"]={"all_passed":d["all_passed"],"current":all(matched(root / p,h) for p,h in b["sha256"].items()),"audit_passed":(pre / "audit.json").exists() and read_json(pre / "audit.json")["passed"]}
    due = root / "data/mimii-due-source-review/expansion-plan.json"
    if due.exists():
        p=read_json(due)
        result = root / "artifacts/acoustic-due-three-sections-v1/results.json"
        opened = (due.parent / "development-download.json").exists()
        data["due_source_review"]={"fit":sum(x["role"]=="fit" for x in p["records"]),"calibration":sum(x["role"]=="calibration" for x in p["records"]),"audio_opened":opened,"physical_identity":p["physical_identity_with_original_mimii"], "three_section_results": result.exists(), "all_passed":read_json(result)["all_passed"] if result.exists() else False}
        reference_result = root / "artifacts/acoustic-due-normal-reference-v1/results.json"
        if reference_result.exists():
            data["due_source_review"]["normal_reference_all_passed"] = read_json(reference_result)["all_passed"]
        for variant in ("acoustic-due-short-time-v1", "acoustic-due-short-supervised-v1"):
            result_path = root / "artifacts" / variant / "results.json"
            if result_path.exists():
                data["due_source_review"][variant] = read_json(result_path)["all_passed"]
        mel = root / "artifacts/acoustic-due-mel-ae-v1"
        if (mel / "protocol.json").exists():
            data["due_source_review"]["mel_ae"] = read_json(mel / "results.json")["all_passed"] if (mel / "results.json").exists() else "No completed result; process status must be checked separately"
        separation = root / "artifacts/acoustic-due-score-audit-v1/results.json"
        if separation.exists():
            data["due_source_review"]["optimistic_recall"] = max(f["optimistic_development_recall"] for f in read_json(separation)["findings"])
        snr = root / "data/mimii-snr-fit"
        if (snr / "plan.json").exists():
            data["due_source_review"]["snr_download_completed"] = (snr / "complete.json").exists()
        snr_result = root / "artifacts/acoustic-mimii-snr-augmented-v1/results.json"
        if snr_result.exists():
            data["due_source_review"]["snr_all_passed"] = read_json(snr_result)["all_passed"]
        paired = root / "artifacts/acoustic-mimii-paired-denoising-v1/results.json"
        if paired.exists():
            data["due_source_review"]["paired_all_passed"] = read_json(paired)["all_passed"]
        overlap = root / "artifacts/acoustic-due-reference-overlap-v1/results.json"
        if overlap.exists():
            audit = read_json(overlap)
            data["due_source_review"]["overlap_pairs"] = sum(s["screened_pairs"] for s in audit["sections"])
            data["due_source_review"]["overlap_flags"] = sum(s["flagged_pairs"] for s in audit["sections"])
    known = root / "data/mimii-known-machines-v1"
    if (known / "freeze.json").exists():
        record = read_json(known / "freeze.json")
        data["known_machine_protocol"] = {"records": record["records"],
            "current": matched(known / "plan.json", record["plan_sha256"]),
            "development_complete": (known / "development.json").exists(),
            "development_receipts":len(list((known / "receipts").glob('*.json')))}
        result_path = root / "artifacts/acoustic-known-machines-v1/results.json"
        if result_path.exists():
            results = read_json(result_path)
            data["known_machine_protocol"]["training_completed"] = True
            data["known_machine_protocol"]["selected"] = results["selected"]
    balanced = root / "artifacts/acoustic-known-balanced-v1"
    if (balanced / "audit.json").exists():
        audit = read_json(balanced / "audit.json")
        result = read_json(balanced / "results.json")
        protocol = read_json(balanced / "protocol.json")
        data["known_balanced_ablation"] = {
            "current": audit["passed"] and matched(balanced / "results.json", audit["results_sha256"])
                and matched(balanced / "protocol.json", audit["protocol_sha256"])
                and matched(root / "scripts/experiment_known_machine_balanced.py", protocol["source_sha256"]),
            "passed": {name: {policy: value["passed"] for policy, value in policies.items()}
                       for name, policies in result["comparison"].items()}}
    optimization = {}
    for tag in ("local", "detail", "capacity", "extra00", "calibration00"):
        directory = root / f"artifacts/acoustic-known-{tag}-{'v2' if tag == 'calibration00' else 'v1'}"
        if (directory / "results.json").exists():
            result = read_json(directory / "results.json")
            audit = read_json(directory / "audit.json") if (directory / "audit.json").exists() else {}
            optimization[tag] = {
                "final_test_opened": result["final_test_opened"],
                "audit_results_bound": bool(audit.get("passed")) and matched(directory / "results.json", audit.get("results_sha256")),
                "summary": result.get("summary", {k: {"groups": v["groups"], "passed": v["passed"]}
                                                   for k, v in result.get("outcomes", {}).items()})}
    if optimization:
        data["known_optimization"] = optimization
    integer = root / "artifacts/acoustic-known-integer-pipeline-v2"
    if (integer / "audit.json").exists():
        result = read_json(integer / "results.json")
        audit = read_json(integer / "audit.json")
        protocol = read_json(integer / "protocol.json")
        data["known_integer_pipeline"] = {
            "current": audit["passed"] and matched(integer / "results.json", audit["results_sha256"])
                       and matched(integer / "protocol.json", audit["protocol_sha256"])
                       and matched(root / "src/vibfpga/known_fixed.py", protocol["fixed_source_sha256"]),
            "passed": result["passed"], "groups": result["groups"], "scope": "development software only"}
    release = root / "artifacts/acoustic-known-release-v1/model-freeze.json"
    if release.exists():
        frozen = read_json(release)
        deployment = {"model_current": all(matched(root / p,h) for p,h in frozen["sha256"].items()),
                      "models": frozen["models"], "reports": []}
        # Read only relevant saved reports. No audio, inference, rebuild or USB.
        for directory in ("known-core", "known-native", "known-flash", "known-board"):
            for path in sorted((root / "build" / directory).glob("*/report.json")):
                report = read_json(path)
                bindings = report.get("bindings", report.get("input_sha256", {}))
                current = bool(report.get("passed") and bindings) and all(matched(root / p,h) for p,h in bindings.items())
                if "bitstream_sha256" in report:
                    current = current and matched(path.parent / "board.bin", report["bitstream_sha256"])
                if "output_sha256" in report:
                    current = current and matched(path.parent / "output.bin", report["output_sha256"])
                deployment["reports"].append({"path":str(path.relative_to(root)),"current":current,
                    **{k:report[k] for k in ("passed","fixture","lanes","machine","windows","samples","intermediate_checks","fmax","utilization") if k in report}})
        data["known_deployment"] = deployment
    final_data = root / "data/mimii-known-final-v1"
    final_results = root / "artifacts/acoustic-known-final-v1"
    bundle = root / "artifacts/acoustic-known-deployment-v1/freeze.json"
    if bundle.exists():
        final = {"stage":"deployment_frozen_holdout_unopened", "downloaded":0}
        if final_data.exists():
            final.update(stage="holdout_download_started",downloaded=len(list((final_data/"receipts").glob("*.json"))))
        if (final_data/"manifest.json").exists(): final["stage"]="holdout_downloaded_not_evaluated"
        if (final_results/"attempt.json").exists(): final["stage"]="final_evaluation_started"
        if (final_results/"results.json").exists():
            r=read_json(final_results/"results.json")
            final.update(stage="final_evaluation_finished",passed=r["passed"],groups=r["groups"],
                         deployment_bound=matched(bundle,r["deployment_sha256"]))
        if (final_results/"audit.json").exists():
            a=read_json(final_results/"audit.json")
            final["audit_current"]=a["passed"] and matched(final_results/"results.json",a["results_sha256"])
        data["known_final"]=final
    physical_dir=root/"measurements/known-replay"
    if physical_dir.exists():
        attempts=[read_json(p) for p in physical_dir.glob("*/manifest.json")]
        data["known_physical_progress"]={"saved_passes":sum(a.get("status")=="passed" for a in attempts),
            "started":any(a.get("physical_hardware") or a.get("hardware_operations_started") for a in attempts)}
    physical_audit=root/"artifacts/evidence/known-hardware-audit.json"
    if physical_audit.exists():
        a=read_json(physical_audit)
        data["known_physical_audit"]={k:a[k] for k in ("passed","physical_runs","unique_recordings","windows_by_lanes","main_machines","overload")}
        data["known_physical_audit"]["current"]=a["passed"] and matched(root/"scripts/audit_known_hardware.py",a["source_sha256"]) and all(matched(root/p,h) for p,h in a["sha256"].items())
    return data


def markdown(data):
    final_status = {"deployment_frozen_holdout_unopened":"Deployment is frozen; the 720 final recordings have not been read",
        "holdout_download_started":"Final holdout download started after freezing; test metrics have not been computed",
        "holdout_downloaded_not_evaluated":"The 720 holdout recordings are downloaded but not evaluated",
        "final_evaluation_started":"Final evaluation of the frozen version has started; results are incomplete",
        "final_evaluation_finished":"The frozen version completed one final evaluation; results appear below"}.get(data.get("known_final",{}).get("stage"),"The 720 final recordings have not been read")
    physical=data.get("known_physical_progress",{})
    physical_status=f"Hardware testing of the new version has started, with {physical.get('saved_passes',0)} saved passing runs; see the independent audit below" if physical.get("started") else "The new version has not yet been tested on hardware"
    lines = ["# Current project status", "", f"Generated: {data['generated_utc']}", "", f"Project directory: `{data['project_root']}`.", "",
             "This page checks saved evidence and current hashes only. It does not start hardware, builds, training, or model inference.", "",
             f"Saved physical replay passes bound to the current source: **{data['current_physical_passes']}**; representing **{data['current_physical_trial_count']}** actual replays and **{data['current_physical_unique_frames']}** deduplicated frames. Retained failed attempts: **{data['failed_attempts_retained']}**. Read-only recovery belongs to the original replay and does not add an independent trial.", "",
             "## Configurations and models", "", "| Profile | N / Hz / MAC | Model and recorded digest match | Status |", "| --- | --- | --- | --- |"]
    for p in data["profiles"]:
        lines.append(f"| {p['name']} | {p.get('n', '?')} / {p.get('sample_rate_hz', '?')} / {p.get('lanes', '?')} | {p.get('matches_recorded_model_digest')} | {p.get('model_training_status', p.get('error'))} |")
    if "known_machine_protocol" in data:
        k = data["known_machine_protocol"]
        lines += ["", "## Current primary evaluation target: new recordings from covered fans", "",
            f"Frozen split: {k['records']} recordings; manifest hash valid: {k['current']}. Early comparisons used logistic regression and a 32-to-16-to-1 MLP; see the integer pipeline selected later below. Every fan and the pooled set require recall>90%, FPR<5%, and AUC>=0.9.",
            f"All four IDs participate in training. Three folds are stratified by complete recordings, excluding the old final test. {final_status}.{physical_status}.",
            "Protocol: docs/known-machine-evaluation.md. Historical cross-machine experiments remain supplementary and are not the main acceptance criterion for this version.", ""]
        lines += [f"Development-data receipts: {k['development_receipts']}/1024; complete development manifest present: {k['development_complete']}. Receipt counts do not prove that a process is running.", ""]
        if k.get("training_completed"):
            lines += [f"Six fits of the two early candidates are complete; candidate meeting every gate: {k['selected']}. This earlier comparison failed; see experiment audit.json for 40 recomputed checks.", ""]
    if "known_balanced_ablation" in data:
        b = data["known_balanced_ablation"]
        lines += [f"Three MLP fits for balanced-frequency ablation are complete; evidence binding valid: {b['current']}. All-machine pass status for four comparisons: {b['passed']}.",
                  "This round compares development data only and includes no RTL or programming. Report: docs/known-machine-balanced-ablation.md.", ""]
    if "known_optimization" in data:
        lines += ["Follow-up optimization for known machines includes machine-specific parameters, individual frequency retention, full spectra, and linear compression comparisons. Machine 00 has 256 additional training recordings.",
                  "Per-machine gates and final-test isolation remain in effect. Further evidence, calibration expansion, and outstanding work are in docs/known-machine-optimization-progress.md. Pooled success does not imply that every machine passes.", ""]
    if "known_integer_pipeline" in data:
        k = data["known_integer_pipeline"]
        lines += [f"Full integer DSP plus INT8 linear classifier passes development gates: {k['passed']}; evidence binding valid: {k['current']}.",
                  f"{final_status}. Development success does not replace final confirmation. Integer interface contract: docs/known-integer-deployment.md.", ""]
    if "known_deployment" in data:
        d = data["known_deployment"]
        lines += [f"Final refitted parameters for four machines are exported; frozen-model binding valid: {d['model_current']}. This confirms parameter freezing only, not final testing or hardware completion.",
                  "New RTL, the full Flash application, and verification results follow. Only evidence bound to the current source is listed; earlier attempts and failures remain in JSON and build directories.", "",
                  "| Evidence | Scope |", "|---|---|"]
        for r in d["reports"]:
            if not r["current"]: continue
            if "utilization" in r:
                info=f"Full-board build, ID{r.get('machine')}, {r.get('lanes')} MAC, LC {r['utilization']['ICESTORM_LC']['used']}/5280; final Fmax {r['fmax']}"
            else:
                info=f"Simulation: {r.get('lanes','?')} MAC, {r.get('windows','?')} windows, fixture={r.get('fixture','see report')}"
            lines.append(f"| {r['path']} | {info} |")
        lines += ["", f"{final_status}.{physical_status}. Overfitting diagnostics: docs/known-overfitting-audit.md.", ""]
    if "known_final" in data:
        f=data["known_final"]
        lines += [f"Final holdout download receipts: {f['downloaded']}/720; status: {f['stage']}.", ""]
        if "groups" in f:
            lines += ["|Final test machine|Detected|False alarms|AUC|Passed|","|---|---|---|---|---|"]
            for machine,g in f["groups"].items():
                lines.append(f"|{machine}|{g['tp']}/{g['abnormal']}|{g['fp']}/{g['normal']}|{g['auc']:.5f}|{g['passed']}|")
            lines += ["",f"All quality gates passed: {f['passed']}; independent score-audit binding valid: {f.get('audit_current',False)}.", ""]
    if "known_physical_audit" in data:
        a=data["known_physical_audit"]
        lines += [f"New-model hardware audit: passed={a['passed']}; current binding valid={a['current']}; {a['physical_runs']} actual passing replays across {a['unique_recordings']} distinct recordings.",
            f"Single-MAC total: {a['windows_by_lanes']['1']} windows; four-MAC total: {a['windows_by_lanes']['4']} windows; four-MAC machine coverage: {a['main_machines']}. Each startup processes 156 consecutive windows; totals across startups are not one continuous run.",
            f"Intentional overload and recovery with the same core: {bool(a['overload'] and a['overload']['passed'])}. Details: docs/known-hardware-results.md.", ""]
    migration = data["migration"]
    lines += ["", f"Local compatibility link: `{migration.get('compatibility_path')}`; points to the project: {migration['compatibility_symlink_valid']}. The migration record is retained locally and omitted from publication."]
    board = data["board"]
    lines += ["", "## Board and field workflow", "", f"Saved USB/JEDEC identification: {board.get('board', 'unverified')} / {board.get('flash_id', 'unverified')}; full original Flash backup hash verified: {board['backup_hash_verified']}. The current connection was not reread during this status check.", "",
              "Internal HFOSC uses nominal frequency; physical frequency, external-clock calibration, and power are unmeasured. ADXL345 acquisition and a real field-trained model remain incomplete.", "",
              f"Synthetic field fixture: {data['field_fixture'].get('verification', data['field_fixture']['status'])}; real field training complete: {data['field_fixture'].get('real_field_model_trained', False)}.", "",
              "## Physical attempts (all retained)", "", "| Attempt | Saved status | Evidence currently valid | Notes |", "| --- | --- | --- | --- |"]
    for a in data["physical_attempts"]:
        note = "; ".join(a["errors"]) or a.get("recorded_error") or a.get("claim", "")
        if a.get("recovery_of_existing_trial"):
            note += "; read-only recovery of the original replay, with no new run"
        if a.get("current_physical_pass") and a.get("readback_evidence"):
            note += "; " + a["readback_evidence"]
        lines.append(f"| {Path(a['manifest']).parent.name} | {a.get('status')} | {a['current_physical_pass']} | {note} |")
    lines += ["", "Passing score claims come from saved integer-reference comparison receipts. This check verifies their binding to the same model, input, and output-log hashes and normal counters; it does not rerun inference.", "",
              "## Replay firmware builds", "", "This table checks upduino_replay only. Other SEN1/FCL1 reports are listed separately under other_build_reports in the JSON and are not evaluated using the replay-firmware input rules.", "",
              "| Build | MAC | Inputs and bitstream still match | Routed Fmax (MHz) | LC / DSP / RAM |", "| --- | --- | --- | --- | --- |"]
    for b in data["builds"]:
        util = b.get("utilization", {})
        cells = " / ".join(str(util.get(key, {}).get("used", "?")) for key in ("ICESTORM_LC", "ICESTORM_DSP", "ICESTORM_RAM"))
        fmax = ", ".join(f"{name}: {value.get('achieved', '?')}" for name, value in b.get("post_route_fmax", {}).items())
        lines.append(f"| {Path(b['report']).parent.parent.name} | {b.get('lanes', '?')} | {b['current']} | {fmax} | {cells} |")
    lines += ["", "Routed Fmax is a tool estimate, not a measured board clock. Invalidity reasons, file digests, stage cycles, and local compatibility-link status are in current-status.json in the same directory.", "",
              "Refresh using `python scripts/collect_current_status.py`. Original evidence and failure records are not modified.", ""]
    if "acoustic" in data:
        a=data["acoustic"];v=a["validation"];selected=v["selected"]
        lines += ["## MIMII acoustic prototype (separate from the CWRU results above)", "",
                  f"Frozen-model binding valid: {a['freeze_current']}. Validation AUC: {selected['auc']:.4f}; false-positive rate: {selected['fpr']:.1%}; recall: {selected['recall']:.1%}. Algorithm feasibility gates passed: {v['feasibility_passed']}.",
                  f"Test set evaluated: {a['test_evaluated']}; microphone measured: {a['microphone_tested']}. The test set remained reserved for a later formal version at this stage.", "",
                  "| Acoustic hardware attempt | Status | Evidence currently valid |", "| --- | --- | --- |"]
        for attempt in a["physical_attempts"]:
            lines.append(f"| {Path(attempt['manifest']).parent.name} | {attempt['status']} | {attempt['current_physical_pass']} |")
        lines += ["", "Software/RTL implementation, verification scope, and next steps are in docs/acoustic-v1.md. Passing hardware numerical checks does not establish adequate detection quality.", ""]
    if "acoustic_feature_study" in data:
        study = data["acoustic_feature_study"]; summary = study["summary"]; candidate = summary["engineering_candidate"]
        lines += ["## Acoustic feature improvement experiments", "",
                  f"90 training/validation candidates compared; evidence binding valid: {study['current']}. Engineering candidate: {candidate['name']} ({candidate['compression']}).",
                  f"Validation AUC {candidate['auc']:.4f}; recording-level false-positive rate {candidate['fpr']:.1%}; recall {candidate['recall']:.1%}; quality gate passed: {summary['quality_gate_passed']}.",
                  "The new scheme was not quantized, implemented in RTL, or programmed; the test set remained unopened in this round. Full results: docs/acoustic-v2-study.md.", ""]
    if "acoustic_diagnosis" in data:
        lines += ["## Investigation of missed acoustic detections", "", "Missed-detection analysis, temporal features, full spectra, and pretrained representations did not exceed 13/30 detections. The new validation criteria require at least 27/30 detections, at most 2/40 false alarms, and AUC>=0.90; these were not met."]
        for r in data["acoustic_diagnosis"]:
            lines.append(f"- {r['name']}: {r['candidates']} candidates; evidence binding valid {r['current']}; test set opened {r['test_opened']}.")
        lines += ["", "Grouped diagnostics: docs/acoustic-v3-diagnosis.md; higher criteria and temporal experiments: docs/acoustic-v4-temporal.md; full-spectrum and pretrained work: docs/acoustic-v5-v6-progress.md. Quantization and RTL were unchanged.", ""]
    if "acoustic_supervised" in data:
        supervised = data["acoustic_supervised"]
        lines += ["## Supervised known-fault classification: passing same-machine version", "",
                  f"Separate fault-training data were authorized; evidence binding valid: {supervised['current']}.",
                  "The primary model detected 30/30 with 2/40 false alarms and AUC 1.000 on the original validation set. With the threshold frozen, the holdout test detected 50/50 with 1/40 false alarms and AUC 1.000. All three criteria passed.",
                  "The linear baseline produced 5/40 test false alarms and failed. This model version was not deployed to FPGA. Full report: docs/acoustic-supervised-results.md.",
                  "Statements that the test set was unopened refer to each earlier experiment at its historical stage. This supervised version completed one formal holdout evaluation.", ""]
    if "acoustic_generalization" in data:
        g = data["acoustic_generalization"]; r = g["external"]
        lines += ["## Generalization audit: cross-machine criteria failed", "",
                  f"Audit evidence binding valid: {g['current']}. No exact duplicates were found among the old 400 clips. All 267 candidates from 44,700 cross-split comparisons were checked again at the original sample rate; no near-duplicates met the threshold. Acquisition-batch independence is still not fully confirmed.",
                  f"Frozen model/threshold on fan/id_02: 23/30 detections, 24/40 false alarms, AUC {r['auc']:.4f}; higher criteria failed. No retraining or threshold tuning was performed.",
                  "The original AUC 1.000 is a same-machine result, not evidence of cross-machine generalization. Report: docs/acoustic-generalization-audit.md.", ""]
    if "multimachine" in data:
        mm = data["multimachine"]
        lines += ["## Three-machine training and whole-machine 06 holdout test", "", f"960 development clips and 160 final-test clips; old test clips excluded: {mm['old_test_excluded']}. Saved data-verification receipts: {mm['verified_receipts']}. Model frozen: {mm['frozen']}; machine 06 evaluated: {mm['test_evaluated']}."]
        if mm["frozen"]:
            lines += [f"Candidate {mm['candidate']}; frozen binding valid {mm['current']}; all three development folds pass {mm['all_development_folds_passed']}.", "", "| Held-out machine | AUC | Recall | False-positive rate |", "|---|---:|---:|---:|"]
            for r in mm["folds"]: lines.append(f"| {r['machine']} | {r['auc']:.4f} | {r['recall']:.1%} | {r['fpr']:.1%} |")
        if mm["test_evaluated"]:
            t=mm["test"];lines += ["", f"Machine 06 final test: AUC {t['auc']:.4f}; recall {t['recall']:.1%}; false-positive rate {t['fpr']:.1%}; higher criteria passed {t['high_standard_passed']}."]
        lines += ["", "Workflow and sources: docs/multimachine-training.md. These are software evaluations and do not establish hardware deployment of a new model.", ""]
    if "temporal_study" in data:
        t = data["temporal_study"]; chosen = t["selected"]
        lines += ["## Cross-machine temporal-feature experiments", "", f"Completed {t['candidates']} schemes and 24 training folds; binding valid: {t['current']}; independent audit: {t['audit_passed']}. Selected: {chosen['name']}; all machines pass: {chosen['all_passed']}. Machine 06 was not accessed again.", "", "The higher criteria remain unmet. Full results: docs/multimachine-temporal-results.md. New independent confirmation data are needed; already evaluated machine 06 must not be used for tuning.", ""]
    if "source_invariant" in data:
        z=data["source_invariant"]
        lines += ["## Machine-shift diagnostics", "", f"Same-machine controls and 27 folds of source-shift-reduction training are complete. Selected: {z['selected']}; all pass: {z['all_passed']}; binding valid: {z['current']}; audit: {z['audit_passed']}. Machine 06 was not accessed again.", "", "Report: docs/machine-shift-results.md. The higher criteria remain unmet.", ""]
    if "cnn_study" in data:
        c=data["cnn_study"]
        lines += ["## Time-frequency CNN experiments", "", f"CNN v3 source-machine perturbation across three folds; all pass: {c['all_passed']}; binding valid: {c['current']}; reload audit passed: {c['audit_passed']}. The normalization layout issue was fixed; all three reloaded models produce exactly matching scores. No quantization or hardware deployment; machine 06 was not accessed.", "", "Report: docs/cnn-normalization-and-augmentation.md. Older CNN reports are retained. The higher criteria remain unmet.", ""]
    if "pretrained_study" in data:
        p=data["pretrained_study"]
        lines += ["## Official pretrained acoustic features", "", f"EfficientAT mn10_as extracted features for 960 development recordings and completed nine classifier-head training folds. All pass: {p['all_passed']}; binding valid: {p['current']}; classifier-head audit: {p['audit_passed']}. Machine 06 was not accessed; no hardware deployment.", "", "Report: docs/pretrained-acoustic-results.md. The higher criteria remain unmet; the next step is to investigate data and additional machine sources.", ""]
    if "due_source_review" in data:
        d=data["due_source_review"]
        state = ("The 1200 recordings from DUE 00/01/02 were used in three-fold development; both candidates failed. Sections 03/04/05 have not been evaluated in this project. The historical reserved_section_02_opened=false field in results.json was inherited incorrectly; use the actual records and development-v2.json." if d['three_section_results'] else f"Section 00/01 manifest: {d['fit']} fit plus {d['calibration']} calibration; audio download complete: {d['audio_opened']}.")
        lines += ["## Review of additional machine sources", "", state, "", "Physical-device correspondence with the original MIMII dataset is unconfirmed. Normal-reference calibration is not a zero-shot cross-machine success. Source review: docs/additional-machine-source-review.md; training and actual results: docs/due-training-results.md.", ""]
        if "normal_reference_all_passed" in d:
            lines += [f"Normal-reference experiment complete; all three metrics pass: {d['normal_reference_all_passed']}. See the training report above.", ""]
        for variant in ("acoustic-due-short-time-v1", "acoustic-due-short-supervised-v1"):
            if variant in d:
                lines += [f"{variant} complete; all pass: {d[variant]}; detailed metrics are in the training report.", ""]
        if "mel_ae" in d:
            lines += [f"128-band Mel autoencoder comparison: {d['mel_ae']}.", ""]
        if "optimistic_recall" in d:
            lines += [f"Post-hoc threshold diagnostics on saved development scores: at FPR<5%, best single-group recall {d['optimistic_recall']:.1%}. This is an optimistic diagnostic, not a formal result.", ""]
        if "snr_download_completed" in d:
            lines += [f"A supplement of 192 clearer training recordings was fixed; download-completion record present: {d['snr_download_completed']}.", ""]
        if "snr_all_passed" in d:
            lines += [f"Six noise-version augmentation experiments complete; all pass: {d['snr_all_passed']}. Actual metrics are in the training report.", ""]
        if "paired_all_passed" in d:
            lines += [f"Six paired-spectrum restoration experiments complete; all pass: {d['paired_all_passed']}. Machine 02 shows a local improvement; this does not satisfy all three-machine acceptance gates.", ""]
        if "overlap_pairs" in d:
            lines += [f"Normal-reference versus development overlap screening: {d['overlap_pairs']} pairs; high-correlation raw-waveform flags: {d['overlap_flags']} pairs. Method limitations are in the report; this does not prove acquisition-batch independence.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/evidence")
    args = parser.parse_args(argv)
    data = collect()
    output = rooted(args.output_dir, ROOT)
    output.mkdir(parents=True, exist_ok=True)
    for name, text in (("current-status.json", json.dumps(data, indent=2, ensure_ascii=False) + "\n"), ("current-status.md", markdown(data))):
        temporary = output / (name + ".tmp")
        temporary.write_text(text)
        temporary.replace(output / name)
    print(json.dumps({"output": str(output), "current_physical_passes": data["current_physical_passes"], "failed_attempts_retained": data["failed_attempts_retained"]}))


if __name__ == "__main__":
    main()
