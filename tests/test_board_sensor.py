import json
from pathlib import Path
import struct
import hashlib

import numpy as np
import pytest
from vibfpga.board import build_replay_image, parse_replay_image, validate_profile, write_commands, execute_commands, parse_result_log, COMMIT
from vibfpga.sensor import fit_static, correct_mg, validate_static, analyze_capture

ROOT = Path(__file__).resolve().parents[1]


def test_replay_image_roundtrip_and_corruption():
    samples = np.arange(2048, dtype=np.int16).reshape(2, 1024) - 1024
    blob, meta = build_replay_image(samples, ROOT / "artifacts/fixtures/model/model.json")
    parsed, result = parse_replay_image(blob)
    assert parsed["model_sha256"] == meta["model_sha256"]
    assert np.array_equal(samples, result)
    broken = bytearray(blob)
    broken[-1] ^= 1
    with pytest.raises(ValueError, match="checksum"):
        parse_replay_image(broken)
    with pytest.raises(ValueError):
        parse_replay_image(blob[:4100])


def test_flash_partition_guard_and_no_default_write(tmp_path):
    profile = json.loads((ROOT / "configs/upduino-reference.json").read_text())
    validate_profile(profile)
    payload = tmp_path / "data.bin"
    payload.write_bytes(b"a" * 8192)
    cmds = write_commands(profile, payload)
    assert "-b" not in cmds[0]
    with pytest.raises(ValueError):
        write_commands(profile, payload, "configuration")
    with pytest.raises(ValueError, match="overlap"):
        validate_profile({**profile, "input_offset": 0})
    with pytest.raises((ValueError, RuntimeError)):
        execute_commands(cmds, profile, writes=True, execute=True)
    assert execute_commands(cmds, profile) == cmds
    with pytest.raises(ValueError):
        execute_commands([["iceprog", "-b", "anything"]], profile, execute=True)


def test_log_requires_last_commit_and_decodes_signed_logits():
    header = struct.pack("<4sIII", b"VLG1", 1, 1, COMMIT).ljust(4096, b"\xff")
    record = struct.pack("<16I", 9, 0xFFFFFFFF, 50, 20, 1, 4, 5, 6, 7, 22, 0, 1024, 1024, 0, 0, 0)
    parsed = parse_result_log(header + record)
    assert parsed["records"][0]["logits"] == [-1, 50, 20]
    bad = bytearray(header + record)
    bad[12:16] = b"\xff" * 4
    with pytest.raises(ValueError):
        parse_result_log(bad)


def test_command_write_detection_cannot_be_bypassed(tmp_path,monkeypatch):
    profile=json.loads((ROOT/"configs/upduino-reference.json").read_text())
    payload=tmp_path/"bounded.bin"
    payload.write_bytes(b"\xff"*4096)
    commands=write_commands(profile,payload)
    calls=[]
    monkeypatch.setattr("vibfpga.board.subprocess.run",lambda *a,**k:calls.append((a,k)))
    assert execute_commands(commands,profile,writes=True)==commands
    with pytest.raises(ValueError,match="not been verified"):
        execute_commands(commands,profile,writes=False,execute=True)
    with pytest.raises(ValueError,match="layout"):
        validate_profile({**profile,"input_offset":0x50000})
    assert calls==[]


def capture(path, z, cycles=None, indices=None):
    z = np.asarray(z)
    n = len(z)
    values = np.c_[np.arange(n) if indices is None else indices,
                   np.arange(n) * 15000 if cycles is None else cycles,
                   np.zeros(n), np.zeros(n), z]
    np.savetxt(path, values, delimiter=",", header="sample_index,service_cycle,x_raw,y_raw,z_raw", comments="", fmt="%d")
    return path


def test_two_point_calibration_heldout_and_rounding(tmp_path):
    p = capture(tmp_path / "plus.csv", [275, 275, 277, 277])
    m = capture(tmp_path / "minus.csv", [-225, -223, -225, -223])
    cal = fit_static(p, m)
    assert cal["offset_counts"] == 26
    assert cal["counts_per_g"] == 250
    assert correct_mg(np.array([26, 276, -224]), cal).tolist() == [0, 1000, -1000]
    with pytest.raises(ValueError, match="held-out"):
        validate_static(p, cal, 1)
    new = capture(tmp_path / "heldout.csv", [276, 276, 276, 276])
    result = validate_static(new, cal, 1)
    assert result["after_rmse_mg"] < result["before_rmse_mg"]


def test_psd_known_tone_wrap_and_missing_samples(tmp_path):
    n = 1024
    z = np.rint(100 * np.sin(2 * np.pi * 50 * np.arange(n) / 800)).astype(int)
    cycles = (0xFFFF0000 + np.arange(n) * 15000) % (1 << 32)
    path = capture(tmp_path / "tone.csv", z, cycles)
    report = analyze_capture(path, odr=800)
    peak = report["psd_frequency_hz"][int(np.argmax(report["psd"]))]
    assert peak == 50
    assert report["psd_valid_uniform_sampling_assumption"]
    assert report["adc_aperture_jitter_measured"] is False
    gaps = np.arange(n); gaps[500:] += 1
    bad = capture(tmp_path / "gap.csv", z, cycles, gaps)
    result = analyze_capture(bad, odr=800)
    assert result["detectable_index_gaps"] == 1
    assert not result["psd_valid_uniform_sampling_assumption"]


def test_measurement_metadata_prevents_wrong_frequency_axis(tmp_path):
    path=capture(tmp_path/"capture.csv",np.arange(256))
    meta={"csv_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"odr_hz":800,"clock_hz":12_000_000,"axis":"z"}
    path.with_suffix(".json").write_text(json.dumps(meta))
    with pytest.raises(ValueError,match="ODR"):
        analyze_capture(path,odr=100)
    with pytest.raises(ValueError,match="clock"):
        analyze_capture(path,odr=800,clock_hz=6_000_000)
    report=analyze_capture(path,odr=800)
    assert report["odr_source"]=="acquisition_metadata"
    path.write_text(path.read_text()+"256,3840000,0,0,30\n")
    with pytest.raises(ValueError,match="SHA256"):
        analyze_capture(path,odr=800)
