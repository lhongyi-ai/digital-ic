"""Synthetic SEN1 fixtures only; these tests never register real training data."""
import json
from pathlib import Path
import struct
import zlib

import pytest

import vibfpga.capture_registration as registration
from vibfpga.capture_registration import FIXTURE, capture_contract, digest, plan_capture, register_capture


def fixture_log(path, *, seed=0, error_flags=0, delta=3750):
    n = 256
    payload = b"".join(struct.pack("<hH", (i + seed) % 150, delta if i else 0) for i in range(n))
    header = [0x314E4553, 1, n, 0x434F4D54, error_flags, n, n, n, 12000000, 0x0D, 2, 0xE5,
              0, (n - 1) * delta * 4, delta * 4, delta * 4, n, 0, 0, 0, zlib.crc32(payload), 4, 0x301000, 4]
    path.write_bytes(struct.pack("<24I", *header).ljust(4096, b"\x00") + payload)
    return path


def assignment(tmp_path, **changes):
    fields = dict(record_id="synthetic_001", state="stopped", split="train", session_id="synthetic_session",
                  installation_id="synthetic_mount_train", apparatus="mathematical SEN1 fixture only", source_kind=FIXTURE)
    fields.update(changes)
    destination = tmp_path / f"{fields['record_id']}.assignment.json"
    plan_capture(destination, **fields)
    return destination


def register(tmp_path, planned, log=None, **kwargs):
    return register_capture(log or fixture_log(tmp_path / "synthetic.bin"), planned,
                            tmp_path / "fixture-manifest.json", tmp_path / "attempts", **kwargs)


@pytest.mark.parametrize("key", ["session_id", "installation_id", "apparatus", "state"])
def test_missing_labels_fail_before_acquisition(tmp_path, key):
    with pytest.raises(ValueError, match="label|split"):
        assignment(tmp_path, **{key: ""})
    assert not list(tmp_path.glob("*.assignment.json"))


def test_plan_never_overwrites_and_fixture_requires_explicit_opt_in(tmp_path):
    planned = assignment(tmp_path)
    original = planned.read_bytes()
    with pytest.raises(FileExistsError):
        assignment(tmp_path)
    assert planned.read_bytes() == original
    result = register(tmp_path, planned)
    assert result["status"] == "rejected" and "--allow-fixture" in result["error"]
    assert not (tmp_path / "fixture-manifest.json").exists()
    assert Path(result["attempt_dir"]).is_dir()


def test_success_hashes_and_duplicate_failure_are_preserved(tmp_path):
    planned = assignment(tmp_path)
    result = register(tmp_path, planned, allow_fixture=True)
    assert result["status"] == "accepted"
    assert result["formal_real_data_eligible"] is False
    manifest_path = tmp_path / "fixture-manifest.json"
    original = manifest_path.read_bytes()
    manifest = json.loads(original)
    record = manifest["records"][0]
    csv = manifest_path.parent / record["path"]
    assert manifest["source_kind"] == FIXTURE
    assert record["sha256"] == digest(csv)
    assert record["sidecar_sha256"] == digest(csv.with_suffix(".json"))
    assert record["source_log_sha256"] == digest(Path(result["attempt_dir"]) / "source.bin")
    again = register(tmp_path, planned, allow_fixture=True)
    assert again["status"] == "rejected" and "duplicate" in again["error"]
    assert manifest_path.read_bytes() == original
    assert (Path(again["attempt_dir"]) / "source.bin").is_file()


@pytest.mark.parametrize("options,match", [({"error_flags": 1}, "errors"), ({"delta": 3000}, "5%")])
def test_quality_failures_preserve_source_and_quality(tmp_path, options, match):
    log = fixture_log(tmp_path / "invalid-synthetic.bin", **options)
    result = register(tmp_path, assignment(tmp_path), log, allow_fixture=True)
    assert result["status"] == "rejected" and match in result["error"]
    attempt = Path(result["attempt_dir"])
    assert (attempt / "source.bin").read_bytes() == log.read_bytes()
    assert (attempt / "quality.json").exists()
    assert not (tmp_path / "fixture-manifest.json").exists()


def test_crc_and_sidecar_hash_mismatch_reject_import(tmp_path, monkeypatch):
    log = fixture_log(tmp_path / "corrupt-synthetic.bin")
    data = bytearray(log.read_bytes()); data[-1] ^= 1; log.write_bytes(data)
    planned = assignment(tmp_path)
    result = register(tmp_path, planned, log, allow_fixture=True)
    assert result["status"] == "rejected" and "CRC" in result["error"]
    original = registration.sensor_log_to_csv
    def tamper(blob, destination):
        meta = original(blob, destination)
        meta["csv_sha256"] = "0" * 64
        return meta
    monkeypatch.setattr(registration, "sensor_log_to_csv", tamper)
    result = register(tmp_path, planned, allow_fixture=True)
    assert result["status"] == "rejected" and "SHA256" in result["error"]


def test_preassigned_session_and_installation_cannot_cross_splits(tmp_path):
    first = register(tmp_path, assignment(tmp_path), allow_fixture=True)
    assert first["status"] == "accepted"
    original = (tmp_path / "fixture-manifest.json").read_bytes()
    second = assignment(tmp_path, record_id="synthetic_002", split="test")
    result = register(tmp_path, second, fixture_log(tmp_path / "different.bin", seed=1), allow_fixture=True)
    assert result["status"] == "rejected" and "leaks" in result["error"]
    assert (tmp_path / "fixture-manifest.json").read_bytes() == original


def test_fixture_cannot_append_to_formal_physical_manifest(tmp_path):
    path = tmp_path / "fixture-manifest.json"
    physical = {"schema_version": 1, "source_kind": "physical_adxl345", **capture_contract(),
                "apparatus": "mathematical SEN1 fixture only", "records": []}
    path.write_text(json.dumps(physical))
    before = path.read_bytes()
    result = register(tmp_path, assignment(tmp_path), allow_fixture=True)
    assert result["status"] == "rejected" and "cannot mix" in result["error"]
    assert path.read_bytes() == before
