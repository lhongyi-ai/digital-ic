"""Meaningful record-isolation/quality/freeze checks for the new field profile."""
import importlib.util
import json
from pathlib import Path
import numpy as np
import pytest
from vibfpga.field import evaluate, load_manifest, load_split, raw_to_core, train, write_json, digest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("make_field_fixture", ROOT / "scripts/make_field_fixture.py")
fixture_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture_module)


@pytest.fixture
def manifest(tmp_path):
    return fixture_module.generate(tmp_path / "data", windows=2)


def test_sensor_clamp_contract():
    assert raw_to_core(np.array([-32768,-1025,-1024,-1,0,1023,1024,32767])).tolist() == [-32768,-32768,-32768,-32,0,32736,32736,32736]
    with pytest.raises(ValueError):
        raw_to_core([0.5])


def test_synthetic_opt_in_required(manifest):
    with pytest.raises(ValueError, match="explicit"):
        load_manifest(manifest)


@pytest.mark.parametrize("field", ["sha256", "path", "record_id", "session_id", "installation_id"])
def test_leakage_rejected(manifest, field):
    m = json.loads(manifest.read_text())
    target = next(r for r in m["records"] if r["split"] == "test")
    target[field] = m["records"][0][field]
    write_json(manifest,m)
    with pytest.raises(ValueError, match="duplicate|leaks"):
        load_manifest(manifest, allow_fixture=True)


def test_corrupt_capture_rejected(manifest):
    m = load_manifest(manifest, allow_fixture=True)
    path = Path(m["records"][0]["path"])
    path.write_text(path.read_text()+"\n")
    with pytest.raises(ValueError, match="hash changed"):
        load_split(m,"train")


def test_gap_rejected_even_with_matching_hash(manifest):
    m = load_manifest(manifest, allow_fixture=True)
    r = m["records"][0]
    path = Path(r["path"])
    rows = path.read_text().splitlines()
    del rows[13]
    path.write_text("\n".join(rows)+"\n")
    r["sha256"] = digest(path)
    with pytest.raises(ValueError, match="gaps/service"):
        load_split(m,"train")


def test_wrong_fast_timebase_rejected(manifest):
    m=load_manifest(manifest,allow_fixture=True)
    r=m["records"][0];path=Path(r["path"])
    data=np.loadtxt(path,delimiter=",",skiprows=1,dtype=np.int64)
    data[:,1]=data[:,0]+1
    np.savetxt(path,data,fmt="%d",delimiter=",",header="sample_index,service_cycle,z_raw",comments="")
    r["sha256"]=digest(path)
    with pytest.raises(ValueError,match="mean service rate"):
        load_split(m,"train")


def test_full_pipeline_and_freeze(manifest,tmp_path):
    output = tmp_path/"trained"
    report = train(manifest,output,allow_fixture=True,epochs=10)
    assert report["test_captures_opened"] is False
    assert (output/"model/weights_l4_3.hex").is_file()
    result = evaluate(output,allow_fixture=True)
    assert result["claim"] == "synthetic pipeline diagnostics only"
    assert result["integer_dsp_int8_nn"]["windows"] == 6
    with pytest.raises(ValueError, match="already evaluated"):
        evaluate(output,allow_fixture=True)
    with pytest.raises(ValueError, match="cannot be overwritten"):
        train(manifest,output,allow_fixture=True,epochs=10)


def test_training_does_not_open_test_captures(manifest,tmp_path):
    m = json.loads(manifest.read_text())
    for r in m["records"]:
        if r["split"] == "test":
            (manifest.parent/r["path"]).unlink()
    train(manifest,tmp_path/"trained",allow_fixture=True,epochs=1)


def test_modified_frozen_model_rejected(manifest,tmp_path):
    output = tmp_path/"trained"
    train(manifest,output,allow_fixture=True,epochs=1)
    path = output/"model/b1.hex"
    path.write_text("00000000\n")
    with pytest.raises(ValueError, match="frozen experiment changed"):
        evaluate(output,allow_fixture=True)


def test_physical_minimum_records_enforced(manifest):
    m = json.loads(manifest.read_text())
    m["source_kind"] = "physical_adxl345"
    for r in m["records"]:r["sidecar_sha256"]="0"*64
    write_json(manifest,m)
    with pytest.raises(ValueError, match="insufficient"):
        load_manifest(manifest)


def test_failed_test_attempt_is_reserved(manifest,tmp_path):
    output=tmp_path/"trained"
    train(manifest,output,allow_fixture=True,epochs=1)
    m=json.loads(manifest.read_text())
    r=next(r for r in m["records"] if r["split"]=="test")
    (manifest.parent/r["path"]).unlink()
    with pytest.raises(FileNotFoundError):evaluate(output,allow_fixture=True)
    assert (output/"test_attempt.json").is_file()
    with pytest.raises(FileExistsError):evaluate(output,allow_fixture=True)
