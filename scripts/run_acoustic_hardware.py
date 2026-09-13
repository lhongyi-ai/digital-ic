#!/usr/bin/env python3
"""Run a backup-verified UPduino replay attempt; default mode never accesses USB."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import shlex
import subprocess
import time
import uuid

from vibfpga.board import parse_replay_image, parse_result_log, read_command, validate_profile, write_commands
from vibfpga.acoustic_board import verify_acoustic_log as verify_replay_log

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_INPUTS = (
    "rtl/core/vib_coeff_rom.sv", "rtl/core/acoustic_core.sv", "rtl/core/sync_fifo.sv",
    "rtl/platform/spram16k.sv", "rtl/io/spi_master.sv", "rtl/io/flash_stream.sv",
    "rtl/io/replay_source.sv", "rtl/upduino_acoustic.sv", "configs/upduino-replay.pcf",
    "scripts/build_acoustic_board.py", "src/vibfpga/acoustic.py", "src/vibfpga/acoustic_board.py", "src/vibfpga/fixed.py",
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def save_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def project_path(path):
    value = Path(path)
    return (value if value.is_absolute() else ROOT / value).resolve()


def prepare(profile_path, bitstream_path, image_path, *, backup_path=None, backup_sha256=None, execute=False, report_path=None, constraint_path=None):
    """Validate every prerequisite before returning immutable bytes for an attempt."""
    profile_path, bitstream_path, image_path = map(lambda p: Path(p).resolve(), (profile_path, bitstream_path, image_path))
    profile_raw = profile_path.read_bytes()
    profile = json.loads(profile_raw)
    validate_profile(profile)
    if profile["flash_bytes"] != 4 * 1024 * 1024 or profile["erase_bytes"] != 4096:
        raise ValueError("this runner requires verified 4 MiB Flash with 4 KiB erase sectors")
    if execute and profile.get("board_verified") is not True:
        raise ValueError("board_verified must be true before execution")
    if not isinstance(profile.get("device"), str) or not profile["device"]:
        raise ValueError("a programmer device identifier is required")
    clock_source = profile.get("clock_source")
    if clock_source not in ("external12", "hfosc12"):
        raise ValueError("profile clock_source must be external12 or hfosc12")
    if profile.get("nominal_clock_hz", profile.get("clock_hz")) != 12000000:
        raise ValueError("profile nominal clock must be 12000000 Hz")
    expected_id = str(profile.get("expected_flash_id", "")).upper().replace("0X", "")
    expected_id = re.sub(r"[\s:]", "", expected_id)
    if expected_id != "EF4016":
        raise ValueError("this runner requires expected_flash_id EF4016")

    backup = project_path(backup_path or profile.get("backup_path", ""))
    expected_backup = backup_sha256 or profile.get("backup_sha256")
    if not isinstance(expected_backup, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected_backup):
        raise ValueError("an independently recorded backup SHA256 is required")
    if backup_sha256 and profile.get("backup_sha256") and backup_sha256.lower() != profile["backup_sha256"].lower():
        raise ValueError("explicit and profile backup SHA256 values differ")
    backup_raw = backup.read_bytes()
    if len(backup_raw) != profile["flash_bytes"] or sha(backup_raw) != expected_backup.lower():
        raise ValueError("backup size or SHA256 mismatch; no programming permitted")

    report_path = Path(report_path) if report_path is not None else bitstream_path.with_name("report.json")
    report_raw = report_path.read_bytes()
    report = json.loads(report_raw)
    if report.get("schema_version") != 1 or report.get("top") != "upduino_acoustic" or report.get("place_route_completed") is not True:
        raise ValueError("a successful replay board build report is required")
    if report.get("clock_source") != clock_source or report.get("nominal_clock_hz") != 12000000:
        raise ValueError("profile and build clock_source/nominal clock mismatch")
    target = 13.2 if clock_source == "hfosc12" else 12.0
    fmax = report.get("post_route_fmax", {})
    if not fmax or any(float(row["achieved"]) < target or float(row.get("constraint", 0)) < target - 0.001 for row in fmax.values()):
        raise ValueError("build timing does not cover the selected oscillator frequency range")
    bitstream = bitstream_path.read_bytes()
    if not 0 < len(bitstream) <= profile["config_end"]:
        raise ValueError("bitstream exceeds configuration partition")
    if sha(bitstream) != report.get("bitstream_sha256"):
        raise ValueError("bitstream SHA256 does not match build report")
    inputs = report.get("input_sha256", {})
    if not isinstance(inputs, dict) or not inputs:
        raise ValueError("build input_sha256 manifest is missing")
    normalized = {project_path(name): digest for name, digest in inputs.items()}
    missing = [name for name in REQUIRED_INPUTS if project_path(name) not in normalized]
    if missing:
        raise ValueError("build provenance is missing required inputs: " + ", ".join(missing))
    for path, digest in normalized.items():
        if not path.is_file() or sha(path.read_bytes()) != digest:
            raise ValueError(f"build input changed or missing: {path}")
    models = [path for path, digest in normalized.items() if path.name == "model.json" and digest == report.get("model_sha256")]
    if len(models) != 1:
        raise ValueError("build report must identify exactly one matching model.json")
    model_path = models[0]
    if not list(model_path.parent.glob("*.hex")) or any(path.resolve() not in normalized for path in model_path.parent.glob("*.hex")):
        raise ValueError("build report does not cover the current model ROM files")
    if clock_source == "hfosc12" and Path(constraint_path or bitstream_path.with_name("clock_constraint.py")).resolve() not in normalized:
        raise ValueError("internal-clock clock_constraint.py is missing from build provenance")
    image = image_path.read_bytes()
    meta, _ = parse_replay_image(image)
    if len(image) > profile["input_bytes"] or meta["model_sha256"] != report["model_sha256"]:
        raise ValueError("input image partition or model SHA256 mismatch")
    slow_hz = 10800000 if clock_source == "hfosc12" else 12000000
    # Six seconds cover boot scan, payload loading, tail compute and log page writes.
    wait_seconds = math.ceil(meta["run_frames"] * meta["n"] * meta["period_cycles"] / slow_hz + 6)
    return {"profile": profile, "profile_raw": profile_raw, "report": report, "report_raw": report_raw,
            "bitstream": bitstream, "image": image, "model": model_path.read_bytes(), "meta": meta,
            "backup_path": str(backup), "backup_sha256": expected_backup.lower(),
            "profile_path": str(profile_path), "bitstream_path": str(bitstream_path),
            "image_path": str(image_path), "model_path": str(model_path),
            "wait_seconds": wait_seconds, "expected_flash_id": expected_id}


def commands_for(profile, output):
    """Configuration, input, then complete log clearing; each write verifies by default."""
    return [
        ("jedec", ["iceprog", "-d", profile["device"], "-t"]),
        ("configuration", ["iceprog", "-d", profile["device"], "-i", "4", "-o", "0", str(output / "board.bin")]),
        ("input", write_commands(profile, output / "replay.bin", "input")[0]),
        ("clear_log_and_start", write_commands(profile, output / "erased-log.bin", "log")[0]),
    ] + [(f"read_log_{index}", read_command(profile, output / f"read-log-{index:02d}.bin"))
         for index in range(1, 4)]


def verify_normal(image, log, model_path):
    meta, _ = parse_replay_image(image)
    parsed = parse_result_log(log)
    expected_samples = meta["n"] * meta["run_frames"]
    expected = {"generated_samples": expected_samples, "accepted_samples": expected_samples,
                "overflow_count": 0, "protocol_errors": 0, "error_flags": 0,
                "period_cycles": meta["period_cycles"], "requested_frames": meta["run_frames"],
                "record_count": meta["run_frames"]}
    for name, value in expected.items():
        if parsed[name] != value:
            raise ValueError(f"normal replay {name} mismatch: observed {parsed[name]}, expected {value}")
    for record in parsed["records"]:
        if record["protocol_errors"] or record["cycles_total"] != sum(record[f"cycles_{name}"] for name in ("pre", "dft", "power", "nn")):
            raise ValueError(f"frame {record['frame_id']} protocol or stage cycle accounting mismatch")
    verification = verify_replay_log(image, log, model_path)
    return parsed, verification


def observed_ids(transcript):
    matches = re.findall(r"flash ID:\s*((?:0x[0-9a-fA-F]{2}[ \t]*)+)", transcript, re.IGNORECASE)
    return ["".join(re.findall(r"0x([0-9a-fA-F]{2})", value))[:6].upper() for value in matches]


def require_jedec(transcript, expected):
    ids = observed_ids(transcript)
    if not ids or any(value != expected for value in ids):
        raise ValueError(f"JEDEC mismatch: observed {ids or None}, expected {expected}")
    return expected


def snapshot_file(directory, name):
    if not isinstance(name, str) or Path(name).name != name or name in (".", ".."):
        raise ValueError("attempt manifest contains an unsafe artifact path")
    path = directory / name
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"attempt artifact missing or not a regular snapshot: {path}")
    return path


def prepare_recovery(origin_path, *, execute=False, backup_path=None, backup_sha256=None):
    """Bind a completed physical run without writing to it or re-running it."""
    origin = Path(origin_path).resolve()
    original_raw = snapshot_file(origin, "manifest.json").read_bytes()
    original = json.loads(original_raw)
    if (original.get("schema_version") not in (1, 2) or original.get("status") != "failed"
            or not original.get("finished_utc") or original.get("execute_requested") is not True
            or original.get("hardware_operations_started") is not True
            or original.get("attempt_mode", "program_and_replay") != "program_and_replay"):
        raise ValueError("read-only recovery requires a finished failed physical programming/replay attempt")
    digests = original.get("input_sha256", {})
    required = ("profile.json", "build-report.json", "board.bin", "replay.bin", "model.json")
    if any(name not in digests for name in required):
        raise ValueError("origin artifact hash manifest is incomplete")
    for name, digest in digests.items():
        if sha(snapshot_file(origin, name).read_bytes()) != digest:
            raise ValueError(f"origin artifact SHA256 mismatch: {name}")
    bitstream_origin = project_path(original["original_paths"]["bitstream_path"])
    ready = prepare(origin / "profile.json", origin / "board.bin", origin / "replay.bin",
                    backup_path=backup_path or original.get("backup_path"),
                    backup_sha256=backup_sha256 or original.get("backup_sha256"), execute=execute,
                    report_path=origin / "build-report.json",
                    constraint_path=bitstream_origin.with_name("clock_constraint.py"))
    if (ready["model"] != (origin / "model.json").read_bytes()
            or ready["profile"].get("board_verified") is not True
            or ready["profile"]["device"] != original.get("device")
            or ready["meta"] != original.get("replay_parameters")
            or ready["backup_sha256"] != original.get("backup_sha256")
            or ready["profile"]["flash_bytes"] != original.get("backup_bytes")):
        raise ValueError("origin metadata does not match its validated snapshots")
    erased = snapshot_file(origin, "erased-log.bin").read_bytes()
    if erased != b"\xff" * ready["profile"]["log_bytes"]:
        raise ValueError("origin log-clearing command input is not the complete erased partition")
    expected_steps = commands_for(ready["profile"], origin)[:4]
    steps = original.get("steps", [])
    planned = original.get("commands", [])
    if len(steps) < 5 or len(planned) < 5:
        raise ValueError("origin did not reach log readback after completed programming")
    references = []
    previous_finished = None
    for index, (name, command) in enumerate(expected_steps):
        step = steps[index]
        if (step.get("name") != name or step.get("argv") != command or step.get("returncode") != 0
                or not step.get("finished_utc") or planned[index] != {"step": name, "argv": command}):
            raise ValueError(f"origin {name} programming step was not successfully completed as planned")
        started = datetime.fromisoformat(step["started_utc"])
        finished = datetime.fromisoformat(step["finished_utc"])
        if finished < started or previous_finished is not None and started < previous_finished:
            raise ValueError("origin programming timestamps are inconsistent")
        previous_finished = finished
        path = snapshot_file(origin, step["transcript"])
        raw = path.read_bytes()
        if step.get("transcript_sha256", sha(raw)) != sha(raw):
            raise ValueError(f"origin {name} transcript SHA256 mismatch")
        require_jedec(raw.decode(), ready["expected_flash_id"])
        if name != "jedec" and "VERIFY OK" not in raw.decode():
            raise ValueError(f"origin {name} lacks programmer byte-verification evidence")
        reference = {**step, "transcript": str(path), "transcript_sha256": sha(raw),
                     "observed_flash_id": ready["expected_flash_id"]}
        if name != "jedec":
            input_path = Path(command[-1])
            digest = sha(input_path.read_bytes())
            if step.get("input_sha256", digest) != digest:
                raise ValueError(f"origin {name} command input SHA256 mismatch")
            reference.update(input_file=str(input_path), input_sha256=digest)
        references.append(reference)
    read_step = steps[4]
    if (not str(read_step.get("name", "")).startswith("read_log") or not read_step.get("started_utc")
            or read_step.get("argv") != read_command(ready["profile"], origin / Path(read_step.get("argv", [""])[-1]).name)
            or datetime.fromisoformat(read_step["started_utc"]) < previous_finished):
        raise ValueError("origin never started a correctly bounded log read")
    if original.get("result_log_sha256"):
        if sha(snapshot_file(origin, "result-log.bin").read_bytes()) != original["result_log_sha256"]:
            raise ValueError("origin result log SHA256 mismatch")
    for read in original.get("readback_attempts", []):
        if read.get("sha256") and sha(snapshot_file(origin, read["file"]).read_bytes()) != read["sha256"]:
            raise ValueError("origin raw read SHA256 mismatch")
    # Source/build paths continue to describe the original physical programming.
    ready.update({key: value for key, value in original["original_paths"].items()})
    digest = sha(original_raw)
    ready["recovery_origin"] = {"path": str(origin), "manifest_sha256": digest,
                                "physical_trial_id": original.get("physical_trial_id", "origin-manifest-sha256:" + digest)}
    ready["origin_programming_steps"] = references
    ready["origin_manifest_raw"] = original_raw
    return ready


def execute_step(name, command, output, manifest):
    step = {"name": name, "started_utc": utc_now(), "argv": command}
    if "-i" in command:
        step.update(input_file=command[-1], input_sha256=sha(Path(command[-1]).read_bytes()))
    manifest["steps"].append(step)
    manifest.update(status="running", hardware_operations_started=True)
    save_json(output / "manifest.json", manifest)
    print(f"Starting {name}...", flush=True)
    started = time.monotonic()
    transcript = output / f"{name}.txt"
    try:
        with transcript.open("x") as stream:
            result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT,
                                    text=True, timeout=180, check=False)
        step["returncode"] = result.returncode
    except Exception as error:
        step.update(returncode=None, execution_error=f"{type(error).__name__}: {error}")
    text = transcript.read_bytes().decode() if transcript.is_file() else ""
    step.update(elapsed_seconds=time.monotonic() - started, finished_utc=utc_now(),
                transcript=transcript.name, transcript_sha256=sha(text.encode()),
                observed_flash_id=observed_ids(text)[0] if observed_ids(text) else None)
    save_json(output / "manifest.json", manifest)
    print("\n".join(text.splitlines()[-6:]), flush=True)
    return step, text


def read_consensus(ready, output, manifest, commands):
    previous = None
    manifest["readback_attempts"] = []
    for name, command in commands:
        step, text = execute_step(name, command, output, manifest)
        path = Path(command[-1])
        read = {"step": name, "file": path.name, "transcript": step["transcript"],
                "transcript_sha256": step["transcript_sha256"], "returncode": step["returncode"],
                "observed_flash_id": step["observed_flash_id"], "transport_valid": False, "format_valid": False}
        manifest["readback_attempts"].append(read)
        raw = path.read_bytes() if path.is_file() else None
        if raw is not None:
            read.update(sha256=sha(raw), bytes=len(raw))
        try:
            if step["returncode"] != 0:
                raise ValueError(f"read command failed: {step.get('execution_error', step['returncode'])}")
            require_jedec(text, ready["expected_flash_id"])
            if raw is None or len(raw) != ready["profile"]["log_bytes"]:
                raise ValueError("result log read has incorrect byte count")
            read["transport_valid"] = True
            parse_result_log(raw)
            read["format_valid"] = True
        except (ValueError, KeyError) as error:
            read["error"] = str(error)
            manifest["read_transport_issue"] = True
            manifest["read_transport_errors"].append({"step": name, "error": str(error)})
            manifest["readback_recovery_needed"] = True
            previous = None
            save_json(output / "manifest.json", manifest)
            print(f"Readback rejected: {error}; retaining {path.name}.", flush=True)
            continue
        if previous is not None and previous[1] == raw:
            manifest["readback_consensus"] = {"files": [previous[0], path.name], "sha256": sha(raw),
                                              "result_file": "result-log.bin", "unaltered": True}
            (output / "result-log.bin").write_bytes(raw)
            save_json(output / "manifest.json", manifest)
            return raw
        if previous is not None:
            read["agreement_error"] = "consecutive valid raw reads differ"
            manifest["read_transport_issue"] = True
            manifest["read_transport_errors"].append({"step": name, "error": read["agreement_error"]})
            manifest["readback_recovery_needed"] = True
        previous = (path.name, raw)
        save_json(output / "manifest.json", manifest)
    raise ValueError("readback failed: no two consecutive identical valid unaltered reads within three attempts")


def run_attempt(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    recovery = getattr(args, "read_only_from", None)
    manifest = {"schema_version": 2, "started_utc": utc_now(), "status": "preflight",
                "attempt_mode": "acoustic_readback_only_recovery" if recovery else "program_and_replay",
                "physical_trial_id": str(uuid.uuid4()), "execute_requested": args.execute,
                "hardware_operations_started": False, "passed": False, "steps": [],
                "actual_clock_measured": False, "readback_recovery_needed": bool(recovery),
                "read_transport_issue": False, "read_transport_errors": [], "core_verification_error": None,
                "readback_policy": "two consecutive identical unaltered valid reads; at most three attempts",
                "measurement_scope": "Flash-fed digital replay; no sensor acquisition or calibrated timing"}
    save_json(output / "manifest.json", manifest)
    try:
        if recovery:
            ready = prepare_recovery(recovery, backup_path=args.backup,
                                     backup_sha256=args.backup_sha256, execute=args.execute)
            manifest.update(recovery_origin=ready["recovery_origin"],
                            physical_trial_id=ready["recovery_origin"]["physical_trial_id"],
                            origin_programming_steps=ready["origin_programming_steps"],
                            measurement_scope="Readback-only recovery of the same physical Flash-fed replay; no reprogramming or new trial")
            (output / "origin-manifest.json").write_bytes(ready["origin_manifest_raw"])
        else:
            ready = prepare(args.profile, args.bitstream, args.image, backup_path=args.backup,
                            backup_sha256=args.backup_sha256, execute=args.execute)
        snapshots = (("profile.json", ready["profile_raw"]), ("build-report.json", ready["report_raw"]),
                     ("board.bin", ready["bitstream"]), ("replay.bin", ready["image"]), ("model.json", ready["model"]),
                     ("erased-log.bin", b"\xff" * ready["profile"]["log_bytes"]))
        for name, data in snapshots:
            (output / name).write_bytes(data)
        driver = Path(__file__).read_bytes()
        (output / "run_hardware_replay.py").write_bytes(driver)
        manifest.update({"status": "prepared", "device": ready["profile"]["device"],
                         "board": ready["profile"].get("board"), "expected_flash_id": ready["expected_flash_id"],
                         "clock_source": ready["profile"]["clock_source"], "nominal_clock_hz": 12000000,
                         "clock_timing_basis": "nominal only; physical oscillator frequency unmeasured",
                         "wait_seconds": ready["wait_seconds"], "replay_parameters": ready["meta"],
                         "backup_path": ready["backup_path"], "backup_sha256": ready["backup_sha256"],
                         "backup_bytes": ready["profile"]["flash_bytes"],
                         "driver_snapshot": "run_hardware_replay.py", "driver_sha256": sha(driver),
                         "original_paths": {name: ready[name] for name in ("profile_path", "bitstream_path", "image_path", "model_path")},
                         "input_sha256": {name: sha(data) for name, data in snapshots},
                         "source_provenance": "build-report.json input_sha256; all listed files verified before this attempt"})
        commands = commands_for(ready["profile"], output)
        if recovery:
            commands = commands[4:]
        manifest["commands"] = [{"step": name, "argv": command} for name, command in commands]
        save_json(output / "manifest.json", manifest)
        for name, command in commands:
            print(f"{name}: {shlex.join(command)}", flush=True)
        if not recovery:
            print(f"Wait after clear: {ready['wait_seconds']} seconds. Actual clock frequency remains unmeasured.", flush=True)
        if not args.execute:
            manifest["status"] = "dry_run"
            return manifest
        if not recovery:
            for name, command in commands[:4]:
                step, text = execute_step(name, command, output, manifest)
                if step["returncode"] != 0:
                    raise RuntimeError(f"{name} failed: {step.get('execution_error', step['returncode'])}")
                try:
                    observed = require_jedec(text, ready["expected_flash_id"])
                except ValueError as error:
                    manifest["read_transport_issue"] = True
                    manifest["read_transport_errors"].append({"step": name, "error": str(error)})
                    raise
                manifest["observed_flash_id"] = observed
                if name != "jedec":
                    if "VERIFY OK" not in text or sha(Path(command[-1]).read_bytes()) != step["input_sha256"]:
                        raise ValueError(f"{name} did not verify its unchanged command input")
            remaining = ready["wait_seconds"]
            while remaining:
                print(f"Replay running: waiting {remaining} seconds before verified log readback.", flush=True)
                chunk = min(10, remaining)
                time.sleep(chunk)
                remaining -= chunk
        read_commands = commands if recovery else commands[4:]
        log = read_consensus(ready, output, manifest, read_commands)
        manifest.update(result_log_sha256=sha(log), observed_flash_id=ready["expected_flash_id"])
        parsed = parse_result_log(log)
        save_json(output / "parsed-log.json", parsed)
        try:
            parsed, verified = verify_normal(ready["image"], log, output / "model.json")
        except ValueError as error:
            manifest["core_verification_error"] = str(error)
            raise
        timing = {}
        for name in ("pre", "dft", "power", "nn", "total"):
            values = [record[f"cycles_{name}"] for record in parsed["records"]]
            timing[name] = {"min_cycles": min(values), "max_cycles": max(values),
                            "mean_cycles": sum(values) / len(values),
                            "mean_seconds_at_nominal_clock": sum(values) / len(values) / 12000000}
        manifest.update(status="passed", passed=True, verification=verified,
                        counters={name: parsed[name] for name in ("record_count", "error_flags", "generated_samples", "accepted_samples", "overflow_count", "protocol_errors", "period_cycles")},
                        stage_timing=timing)
        print(f"PASS: {verified['checked_frames']} physical replay frames match the integer reference; two raw reads agree.", flush=True)
        return manifest
    except BaseException as error:
        manifest.update(status="failed", passed=False, error_type=type(error).__name__, error=str(error))
        raise
    finally:
        manifest.update(finished_utc=utc_now(), elapsed_seconds=time.monotonic() - started)
        save_json(output / "manifest.json", manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--bitstream", type=Path)
    parser.add_argument("--image", type=Path)
    parser.add_argument("--read-only-from", type=Path, help="Recover a finished failed physical attempt using only fresh log reads")
    parser.add_argument("--output", type=Path, required=True, help="New attempt directory; existing directories are rejected")
    parser.add_argument("--backup", type=Path, help="Defaults to profile backup_path")
    parser.add_argument("--backup-sha256", help="Independent backup digest; defaults to profile backup_sha256")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.read_only_from and any((args.profile, args.bitstream, args.image)):
        parser.error("--read-only-from uses the original snapshots; omit --profile, --bitstream and --image")
    if not args.read_only_from and not all((args.profile, args.bitstream, args.image)):
        parser.error("normal replay requires --profile, --bitstream and --image")
    try:
        run_attempt(args)
    except Exception as error:
        parser.exit(1, f"Replay attempt failed: {error}\nEvidence directory: {args.output.resolve()}\n")


if __name__ == "__main__":
    main()
