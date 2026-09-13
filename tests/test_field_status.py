import json
from pathlib import Path

import pytest

from vibfpga.field_status import SOURCE_FILES, digest, inspect_field


def frozen_fixture(tmp_path):
    root = tmp_path / "root"
    sources = root / "src/vibfpga"
    sources.mkdir(parents=True)
    for name in SOURCE_FILES:
        (sources / name).write_text("# synthetic source fixture\n")
    output = tmp_path / "run"
    (output / "model").mkdir(parents=True)
    manifest = {"source_kind": "synthetic_pipeline_fixture", "records": [
        {"split": "test", "path": str(tmp_path / "DO_NOT_OPEN_TEST.csv")} ]}
    (output / "manifest.json").write_text(json.dumps(manifest))
    for name in ("training.json", "float_weights.json", "baselines.json", "model/model.json"):
        (output / name).write_text("{}")
    (output / "vectors").mkdir()
    (output / "vectors/vectors.jsonl").write_text('{"fixture": true}\n')
    frozen = {"source_kind": "synthetic_pipeline_fixture", "files": {
        str(p.relative_to(output)): digest(p) for p in output.rglob("*") if p.is_file()},
        "source_sha256": {name: digest(sources / name) for name in SOURCE_FILES}}
    (output / "frozen.json").write_text(json.dumps(frozen))
    return root, output


def test_verify_does_not_open_test_waveform_or_modify_failed_attempt(tmp_path, monkeypatch):
    root, output = frozen_fixture(tmp_path)
    attempt = output / "test_attempt.json"
    attempt.write_text(json.dumps({"started_utc": "2026-09-01", "freeze_sha256": digest(output / "frozen.json")}))
    before = {p: digest(p) for p in output.rglob("*") if p.is_file()}
    original = Path.open
    def guarded(self, *args, **kwargs):
        assert self.suffix != ".csv", "status opened a waveform"
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Path, "open", guarded)
    result = inspect_field(output, root=root, verify=True)
    assert result["verification"] == "passed"
    assert result["status"] == "attempt_reserved_or_failed"
    assert not result["test_waveforms_opened"]
    assert {p: digest(p) for p in output.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("name", ["model/model.json", "manifest.json"])
def test_verify_rejects_changed_frozen_artifacts(tmp_path, name):
    root, output = frozen_fixture(tmp_path)
    with (output / name).open("a") as stream:
        stream.write(" ")
    result = inspect_field(output, root=root, verify=True)
    assert not result["valid"]
    assert any(name in error and "hash changed" in error for error in result["errors"])


def test_verify_refuses_escape_and_source_changes(tmp_path):
    root, output = frozen_fixture(tmp_path)
    freeze = output / "frozen.json"
    data = json.loads(freeze.read_text())
    data["files"]["../DO_NOT_OPEN_TEST.csv"] = "0" * 64
    freeze.write_text(json.dumps(data))
    (root / "src/vibfpga/field.py").write_text("# changed")
    result = inspect_field(output, root=root, verify=True)
    assert any("unsafe frozen artifact" in error for error in result["errors"])
    assert any("source changed: field.py" in error for error in result["errors"])


def test_verify_detects_result_and_attempt_binding_mismatch(tmp_path):
    root, output = frozen_fixture(tmp_path)
    (output / "test_attempt.json").write_text(json.dumps({"freeze_sha256": "0" * 64}))
    (output / "test.json").write_text(json.dumps({"freeze_sha256": "0" * 64, "model_sha256": "0" * 64}))
    result = inspect_field(output, root=root, verify=True)
    assert not result["valid"]
    assert "test attempt freeze hash mismatch" in result["errors"]
    assert "test result model hash mismatch" in result["errors"]
