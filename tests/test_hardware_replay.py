import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
from types import SimpleNamespace

import numpy as np
import pytest

from vibfpga.board import COMMIT, build_replay_image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_hardware_replay", ROOT / "scripts/run_hardware_replay.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


@pytest.fixture
def assets(tmp_path, monkeypatch):
    root = tmp_path / "source with spaces"
    root.mkdir()
    monkeypatch.setattr(runner, "ROOT", root)
    for name in runner.REQUIRED_INPUTS:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("test source " + name)
    model = root / "artifacts/model/model.json"
    model.parent.mkdir(parents=True)
    model.write_text('{"n":1024}')
    rom = model.with_name("coeff.hex")
    rom.write_text("00\n")
    build = root / "build/run"
    build.mkdir(parents=True)
    binary = build / "board.bin"
    binary.write_bytes(b"test bitstream, never sent to real hardware")
    pcf = build / "clock_constraint.py"
    pcf.write_text('ctx.addClock("system_clk", 13.2)\n')
    paths = [*(root / name for name in runner.REQUIRED_INPUTS), model, rom, pcf]
    report = {"schema_version": 1, "top": "upduino_replay", "place_route_completed": True,
              "clock_source": "hfosc12", "nominal_clock_hz": 12000000,
              "post_route_fmax": {"clk": {"achieved": 20.0, "constraint": 13.2}},
              "bitstream_sha256": runner.sha(binary.read_bytes()),
              "model_sha256": runner.sha(model.read_bytes()),
              "input_sha256": {str(path.relative_to(root)): runner.sha(path.read_bytes()) for path in paths}}
    binary.with_name("report.json").write_text(json.dumps(report))
    image = build / "image.bin"
    image.write_bytes(build_replay_image(np.zeros((1, 1024), dtype=np.int16), model, run_frames=1)[0])
    backup = root / "backup.bin"
    backup.write_bytes(b"\xff" * 4194304)
    profile = json.loads((ROOT / "configs/upduino-reference.json").read_text())
    profile.update(board_verified=True, clock_source="hfosc12", nominal_clock_hz=12000000,
                   expected_flash_id="EF4016", backup_path="backup.bin", backup_sha256=runner.sha(backup.read_bytes()))
    profile_path = root / "profile.json"
    profile_path.write_text(json.dumps(profile))
    args = argparse.Namespace(profile=profile_path, bitstream=binary, image=image,
                              output=root / "attempt", backup=None, backup_sha256=None, execute=False)
    return SimpleNamespace(root=root, args=args, profile=profile, backup=backup, report=report, model=model)


def valid_log(**overrides):
    header = dict(error_flags=0, generated_samples=1024, accepted_samples=1024,
                  overflow_count=0, protocol_errors=0, max_fifo=1, period_cycles=1000, requested_frames=1)
    header.update(overrides)
    data = bytearray(b"\xff" * 131072)
    struct.pack_into("<4sIII", data, 0, b"VLG1", 1, 1, COMMIT)
    struct.pack_into("<8I", data, 16, *header.values())
    struct.pack_into("<16I", data, 4096, 0, 0, 0, 0, 0, 1, 1, 1, 1, 4, 1, 1024, 1024, 0, 0, 0)
    return bytes(data)


def test_dry_run_has_no_usb_and_bounded_command_order(assets, monkeypatch):
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: pytest.fail("dry-run accessed USB"))
    manifest = runner.run_attempt(assets.args)
    assert manifest["status"] == "dry_run" and not manifest["passed"]
    assert not manifest["hardware_operations_started"]
    commands = [row["argv"] for row in manifest["commands"]]
    assert [int(command[command.index("-o") + 1]) for command in commands[1:]] == [0, 0x40000, 0x300000, 0x300000, 0x300000, 0x300000]
    assert all(command[3:5] == ["-i", "4"] for command in commands[1:4])
    assert commands[-1][5:7] == ["-R", "131072"]
    assert all("-b" not in command and "-p" not in command and "-S" not in command for command in commands)
    assert (assets.args.output / "erased-log.bin").read_bytes() == b"\xff" * 131072
    with pytest.raises(FileExistsError):
        runner.run_attempt(assets.args)


@pytest.mark.parametrize("change", ["unverified", "partition", "clock", "flash_id", "geometry"])
def test_invalid_profile_refuses_before_usb(assets, monkeypatch, change):
    updates = {"unverified": {"board_verified": False}, "partition": {"log_offset": 0},
               "clock": {"clock_source": "external12"}, "flash_id": {"expected_flash_id": "FFFFFF"},
               "geometry": {"erase_bytes": 65536}}
    assets.profile.update(updates[change])
    assets.args.profile.write_text(json.dumps(assets.profile))
    assets.args.execute = True
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: pytest.fail("invalid preflight accessed USB"))
    with pytest.raises(ValueError):
        runner.run_attempt(assets.args)
    manifest = json.loads((assets.args.output / "manifest.json").read_text())
    assert manifest["status"] == "failed" and not manifest["hardware_operations_started"]


@pytest.mark.parametrize("change", ["binary", "rtl", "rom", "missing_provenance", "backup_size", "backup_digest", "image_model"])
def test_provenance_and_backup_failures(assets, change):
    if change == "binary":
        assets.args.bitstream.write_bytes(b"changed")
    elif change == "rtl":
        (assets.root / "rtl/upduino_replay.sv").write_text("changed")
    elif change == "rom":
        assets.model.with_name("coeff.hex").write_text("changed")
    elif change == "missing_provenance":
        assets.report["input_sha256"].pop("rtl/upduino_replay.sv")
        assets.args.bitstream.with_name("report.json").write_text(json.dumps(assets.report))
    elif change == "backup_size":
        assets.backup.write_bytes(b"short")
    elif change == "backup_digest":
        assets.profile["backup_sha256"] = "0" * 64
        assets.args.profile.write_text(json.dumps(assets.profile))
    else:
        image = bytearray(assets.args.image.read_bytes())
        image[32] ^= 1
        assets.args.image.write_bytes(image)
    with pytest.raises(ValueError):
        runner.run_attempt(assets.args)
    assert json.loads((assets.args.output / "manifest.json").read_text())["passed"] is False


@pytest.mark.parametrize("field,value", [("generated_samples", 1023), ("accepted_samples", 1023),
    ("overflow_count", 1), ("protocol_errors", 1), ("period_cycles", 999), ("requested_frames", 2)])
def test_normal_counter_mismatch_cannot_pass(assets, monkeypatch, field, value):
    monkeypatch.setattr(runner, "verify_replay_log", lambda *a: pytest.fail("counter validation must precede numerical success"))
    with pytest.raises(ValueError, match=field):
        runner.verify_normal(assets.args.image.read_bytes(), valid_log(**{field: value}), assets.model)


def test_execute_preserves_transcripts_and_requires_two_reads(assets, monkeypatch):
    calls = []
    def fake_run(command, *, stdout, **kwargs):
        calls.append(command)
        stdout.write("flash ID: 0xEF 0x40 0x16 0x00\n")
        if "-R" in command:
            Path(command[-1]).write_bytes(valid_log())
        else:
            stdout.write("VERIFY OK\n")
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    sleeps = []
    monkeypatch.setattr(runner.time, "sleep", sleeps.append)
    monkeypatch.setattr(runner, "verify_replay_log", lambda *a: {"passed": True, "checked_frames": 1})
    assets.args.execute = True
    result = runner.run_attempt(assets.args)
    assert result["passed"] and result["observed_flash_id"] == "EF4016"
    assert len(calls) == 6 and sum("-R" in command for command in calls) == 2
    assert result["readback_consensus"]["files"] == ["read-log-01.bin", "read-log-02.bin"]
    assert not result["readback_recovery_needed"] and not result["read_transport_issue"]
    assert sum(sleeps) >= 1024 * 1000 / 10800000 + 6
    assert all((assets.args.output / step["transcript"]).is_file() for step in result["steps"])
    assert result["actual_clock_measured"] is False


def test_wrong_jedec_stops_before_any_write(assets, monkeypatch):
    calls = []
    def fake_run(command, *, stdout, **kwargs):
        calls.append(command)
        stdout.write("flash ID: 0xFF 0xFF 0xFF 0xFF\n")
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    assets.args.execute = True
    with pytest.raises(ValueError, match="JEDEC mismatch"):
        runner.run_attempt(assets.args)
    assert len(calls) == 1 and "-t" in calls[0]
    assert json.loads((assets.args.output / "manifest.json").read_text())["status"] == "failed"


@pytest.mark.parametrize("change", ["missing_clock_constraint", "changed_clock_constraint", "nominal_only_constraint"])
def test_hfosc_requires_clock_constraint_provenance_and_timing_margin(assets, change):
    constraint = assets.args.bitstream.with_name("clock_constraint.py")
    if change == "missing_clock_constraint":
        assets.report["input_sha256"].pop(str(constraint.relative_to(assets.root)))
    elif change == "changed_clock_constraint":
        constraint.write_text('ctx.addClock("system_clk", 12.0)\n')
    else:
        assets.report["post_route_fmax"]["clk"]["constraint"] = 12.0
    assets.args.bitstream.with_name("report.json").write_text(json.dumps(assets.report))
    with pytest.raises(ValueError):
        runner.run_attempt(assets.args)
    assert json.loads((assets.args.output / "manifest.json").read_text())["passed"] is False


GOOD_ID = "flash ID: 0xEF 0x40 0x16 0x00\n"
BAD_ID = "flash ID: 0xFF 0xEF 0x40 0x16 0x00\n"


def fake_hardware(monkeypatch, reads, *, bad_write=None):
    calls = []
    pending = iter(reads)
    def run(command, *, stdout, **kwargs):
        calls.append(command)
        if "-R" in command:
            item = next(pending)
            raw, identity = item if isinstance(item, tuple) else (item, GOOD_ID)
            stdout.write(identity)
            Path(command[-1]).write_bytes(raw)
        else:
            stdout.write(BAD_ID if len(calls) == bad_write else GOOD_ID)
            if "-i" in command:
                stdout.write("address progress\rVERIFY OK\n")
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(runner.subprocess, "run", run)
    monkeypatch.setattr(runner.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(runner, "verify_replay_log", lambda *a: {"passed": True, "checked_frames": 1})
    return calls


@pytest.mark.parametrize("first", [b"\x00" + valid_log()[:-1], (valid_log(), BAD_ID), valid_log(max_fifo=2)])
def test_third_read_recovers_only_an_identical_unaltered_pair(assets, monkeypatch, first):
    calls = fake_hardware(monkeypatch, [first, valid_log(), valid_log()])
    assets.args.execute = True
    result = runner.run_attempt(assets.args)
    assert result["passed"] and result["readback_recovery_needed"] and result["read_transport_issue"]
    assert result["core_verification_error"] is None
    assert result["readback_consensus"]["files"] == ["read-log-02.bin", "read-log-03.bin"]
    assert (assets.args.output / "result-log.bin").read_bytes() == valid_log()
    assert (assets.args.output / "read-log-01.bin").read_bytes() == (first[0] if isinstance(first, tuple) else first)
    assert sum("-R" in command for command in calls) == 3


@pytest.mark.parametrize("reads", [
    [valid_log(), valid_log(max_fifo=2), valid_log(max_fifo=3)],
    [b"\xff" * 131072] * 3,
    [(valid_log(), BAD_ID)] * 3,
    [valid_log(), b"\xff" * 131072, valid_log()],
])
def test_no_consecutive_consensus_cannot_publish_result(assets, monkeypatch, reads):
    calls = fake_hardware(monkeypatch, reads)
    assets.args.execute = True
    with pytest.raises(ValueError, match="no two consecutive"):
        runner.run_attempt(assets.args)
    assert sum("-R" in command for command in calls) == 3
    assert not (assets.args.output / "result-log.bin").exists()
    assert len(list(assets.args.output.glob("read-log-*.bin"))) == 3
    result = json.loads((assets.args.output / "manifest.json").read_text())
    assert not result["passed"] and result["read_transport_issue"]
    assert result["core_verification_error"] is None


@pytest.mark.parametrize("bad_write", [2, 3, 4])
def test_every_programming_transcript_id_is_checked_before_next_operation(assets, monkeypatch, bad_write):
    calls = fake_hardware(monkeypatch, [], bad_write=bad_write)
    assets.args.execute = True
    with pytest.raises(ValueError, match="JEDEC mismatch"):
        runner.run_attempt(assets.args)
    assert len(calls) == bad_write


def test_identical_wrong_core_counters_are_separate_from_transport_failure(assets, monkeypatch):
    fake_hardware(monkeypatch, [valid_log(accepted_samples=1023)] * 2)
    assets.args.execute = True
    with pytest.raises(ValueError, match="accepted_samples"):
        runner.run_attempt(assets.args)
    result = json.loads((assets.args.output / "manifest.json").read_text())
    assert result["core_verification_error"] and not result["read_transport_issue"]
    assert result["readback_consensus"] and not result["passed"]


def failed_origin(assets, monkeypatch):
    fake_hardware(monkeypatch, [(valid_log(), BAD_ID)] * 3)
    assets.args.execute = True
    with pytest.raises(ValueError, match="no two consecutive"):
        runner.run_attempt(assets.args)
    origin = assets.args.output
    assets.args.output = assets.root / "recovery"
    assets.args.read_only_from = origin
    return origin


def test_read_only_recovery_uses_only_fresh_reads_and_preserves_original(assets, monkeypatch):
    origin = failed_origin(assets, monkeypatch)
    before = {p.name: p.read_bytes() for p in origin.iterdir() if p.is_file()}
    calls = fake_hardware(monkeypatch, [valid_log(), valid_log()])
    result = runner.run_attempt(assets.args)
    assert len(calls) == 2 and all("-R" in command and "-i" not in command for command in calls)
    assert result["passed"] and result["attempt_mode"] == "readback_only_recovery"
    assert result["recovery_origin"]["manifest_sha256"] == runner.sha(before["manifest.json"])
    assert result["physical_trial_id"] == json.loads(before["manifest.json"])["physical_trial_id"]
    assert result["input_sha256"] == json.loads(before["manifest.json"])["input_sha256"]
    assert {p.name: p.read_bytes() for p in origin.iterdir() if p.is_file()} == before
    assert len(result["origin_programming_steps"]) == 4
    assert result["driver_sha256"] == runner.sha((assets.args.output / result["driver_snapshot"]).read_bytes())


@pytest.mark.parametrize("tamper", ["board", "erased", "transcript", "command", "not_read", "ongoing", "backup", "rtl"])
def test_recovery_rejects_tampered_or_incomplete_origin_before_usb(assets, monkeypatch, tamper):
    origin = failed_origin(assets, monkeypatch)
    manifest_path = origin / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if tamper == "board":
        (origin / "board.bin").write_bytes(b"changed")
    elif tamper == "erased":
        (origin / "erased-log.bin").write_bytes(b"changed")
    elif tamper == "transcript":
        (origin / "input.txt").write_text(BAD_ID + "VERIFY OK\n")
    elif tamper == "command":
        manifest["steps"][2]["argv"][-1] = str(assets.args.image)
    elif tamper == "not_read":
        manifest["steps"] = manifest["steps"][:4]
    elif tamper == "ongoing":
        manifest["status"] = "running"
    elif tamper == "backup":
        assets.backup.write_bytes(b"changed")
    else:
        (assets.root / "rtl/upduino_replay.sv").write_text("changed")
    manifest_path.write_text(json.dumps(manifest))
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: pytest.fail("recovery preflight accessed USB"))
    with pytest.raises(ValueError):
        runner.run_attempt(assets.args)
    assert not json.loads((assets.args.output / "manifest.json").read_text())["hardware_operations_started"]


def test_read_only_dry_run_never_accesses_usb(assets, monkeypatch):
    failed_origin(assets, monkeypatch)
    assets.args.execute = False
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: pytest.fail("read-only dry run accessed USB"))
    result = runner.run_attempt(assets.args)
    assert result["status"] == "dry_run" and not result["passed"]
    assert all("-R" in row["argv"] for row in result["commands"])
