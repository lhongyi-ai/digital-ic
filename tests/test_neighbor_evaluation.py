"""Evaluator tests never load actual test MAT data.

The completed fixture deliberately mocks waveform loading and inference so the
one-shot bookkeeping/verification can be exercised in temporary directories.
Actual numerical preflight separately uses synthetic and existing VAL vectors.
"""
import copy
import csv
import json
from pathlib import Path
import shutil

import numpy as np
import pytest

from vibfpga import neighbor_evaluation as ne

ROOT = Path(__file__).resolve().parents[1]


def model():
    return json.loads((ROOT / ne.MODEL / "model.json").read_text())


def copy_inputs(destination):
    for source in ne._input_paths(ROOT):
        target = destination / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def rehash_output(output):
    completion = json.loads((output / "completion.json").read_text())
    completion["output_sha256"] = {str(path.relative_to(output)): ne.digest(path)
        for path in output.rglob("*") if path.is_file() and path.name != "completion.json"}
    (output / "completion.json").write_text(json.dumps(completion))


@pytest.fixture
def completed(tmp_path, monkeypatch):
    """Temporary SYNTHETIC run, never the authorized real evaluation output."""
    from vibfpga import dataset
    from vibfpga.fixed import infer

    copy_inputs(tmp_path)
    output = tmp_path / ne.OUTPUT
    calls = []
    specs = [row for row in json.loads((tmp_path / "data/cwru/manifest.json").read_text())["records"]
             if row["split"] == "test"]
    metadata = [{"record_id": row["record_id"], "split": "test", "load_hp": 3,
                 "class_id": row["label"], "fault_inches": row["fault_inches"],
                 "window_index": i, "sample_start": i * 1024, "sample_stop": (i + 1) * 1024}
                for row in specs for i in range(row["samples"] // 1024)]

    def mock_load(directory, split, raw_scale, n):
        assert split == "test" and n == 1024
        # This assertion executes at the exact boundary where a real run would
        # first open test MAT records. No such files exist in this temp project.
        freeze = json.loads((output / "freeze.json").read_text())
        assert freeze["test_waveforms_loaded_by_this_evaluation_before_freeze"] is False
        ne._check_hashes(tmp_path, freeze["input_sha256"])
        assert raw_scale == model()["raw_scale"]
        calls.append(split)
        return (np.zeros((1070, 1024), dtype=np.int16),
                np.array([row["class_id"] for row in metadata]), metadata, [])

    def mock_batch(frames, config):
        count = len(frames)
        result = infer(np.zeros(16, dtype=np.int64), config)
        return {"dft_powers": np.zeros((count, 48), dtype=np.int64),
                "powers": np.zeros((count, 16), dtype=np.int64),
                "features": np.zeros((count, 16), dtype=np.int64),
                "hidden": np.tile(result["hidden"], (count, 1)),
                "integer_logits": np.tile(result["logits"], (count, 1)),
                "integer_prediction": np.full(count, result["class_id"], dtype=np.int64)}

    monkeypatch.setattr(dataset, "load_windows", mock_load)
    monkeypatch.setattr(ne, "_preflight", lambda *args: {"status": "passed", "test_waveforms_loaded": False})
    monkeypatch.setattr(ne, "_batch_and_scalar_check", mock_batch)
    result = ne.evaluate_once(tmp_path)
    assert result["status"] == "passed" and calls == ["test"]
    assert not list(tmp_path.rglob("*.mat"))
    return tmp_path, output


def test_metric_precision_recall_and_quantization_counts():
    labels = np.array([0, 0, 1, 1, 2, 2])
    predictions = np.array([0, 1, 1, 2, 2, 2])
    measured = ne.metric_summary(labels, predictions)
    assert measured["confusion_matrix"] == [[1, 1, 0], [0, 1, 1], [0, 0, 2]]
    assert [row["precision"] for row in measured["per_class"]] == pytest.approx([1, .5, 2 / 3])
    assert [row["recall"] for row in measured["per_class"]] == [.5, .5, 1]
    assert [row["f1"] for row in measured["per_class"]] == pytest.approx([2 / 3, .5, .8])
    float_logits = np.eye(3, dtype=np.float32)[labels]
    integer_logits = np.eye(3, dtype=np.int64)[predictions]
    quant = ne.quantization_summary(labels, float_logits, integer_logits, 1.0)
    assert quant["prediction_disagreements"] == 2
    assert quant["float_correct_integer_wrong"] == 2
    assert quant["accuracy_drop_percentage_points"] == pytest.approx(100 / 3)


def test_real_candidate_preflight_uses_only_synthetic_and_validation(monkeypatch):
    from vibfpga import dataset

    def prohibited(*args, **kwargs):
        raise AssertionError("Preflight must not load any MAT waveform")

    monkeypatch.setattr(dataset, "load_windows", prohibited)
    monkeypatch.setattr(dataset, "load_record", prohibited)
    config = model()
    ne._load_frozen_network(ROOT, config)
    report = ne._preflight(ROOT, config)
    assert report["status"] == "passed" and report["frozen_validation_windows"] == 9
    assert report["synthetic_windows"] == 6 and not report["test_waveforms_loaded"]


def test_scalar_batch_disagreement_is_rejected(monkeypatch):
    from vibfpga import fixed

    original = fixed.frontend_batch_powers
    monkeypatch.setattr(fixed, "frontend_batch_powers", lambda *args, **kwargs: original(*args, **kwargs) + 1)
    with pytest.raises(ValueError, match="Scalar/batch dft_powers mismatch"):
        ne._batch_and_scalar_check(np.zeros((1, 1024), dtype=np.int16), model())


def test_checkpoint_npz_and_integer_mismatches_rejected(tmp_path):
    target = tmp_path / ne.MODEL
    shutil.copytree(ROOT / ne.MODEL, target)
    with np.load(target / "float_parameters.npz", allow_pickle=False) as archive:
        params = {key: archive[key].copy() for key in archive.files}
    params["fc1.weight"][0, 0] += np.float32(.25)
    np.savez_compressed(target / "float_parameters.npz", **params)
    with pytest.raises(ValueError, match="Checkpoint/NPZ mismatch"):
        ne._load_frozen_network(tmp_path, model())
    changed = copy.deepcopy(model())
    changed["w1"][0][0] += 1
    with pytest.raises(ValueError, match="Integer model does not match"):
        ne._load_frozen_network(ROOT, changed)


def test_existing_output_refuses_before_loading_any_inputs(tmp_path, monkeypatch):
    output = tmp_path / ne.OUTPUT
    output.mkdir(parents=True)
    (output / "incomplete.txt").write_text("Reserved previous attempt")

    def prohibited(*args):
        raise AssertionError("Existing-output guard must run first")

    monkeypatch.setattr(ne, "_input_paths", prohibited)
    with pytest.raises(ValueError, match="already exists"):
        ne.evaluate_once(tmp_path)
    assert list(output.iterdir()) == [output / "incomplete.txt"]


def test_freeze_precedes_single_load_and_verify_is_read_only(completed, monkeypatch):
    root, output = completed
    from vibfpga import dataset

    def prohibited(*args, **kwargs):
        raise AssertionError("Read-only verification cannot load MAT or run inference")

    before = {str(path): ne.digest(path) for path in output.rglob("*") if path.is_file()}
    for owner, name in ((dataset, "load_windows"), (dataset, "load_record"),
                        (ne, "_load_frozen_network"), (ne, "_batch_and_scalar_check")):
        monkeypatch.setattr(owner, name, prohibited)
    verified = ne.verify_existing(root)
    assert verified["record_windows_and_csv_match"] and not verified["inference_run"]
    assert not verified["original_mat_read"]
    assert before == {str(path): ne.digest(path) for path in output.rglob("*") if path.is_file()}
    with pytest.raises(ValueError, match="already exists"):
        ne.evaluate_once(root)


def test_output_and_input_hash_tamper_rejected(completed):
    root, output = completed
    path = output / "records.json"
    original = path.read_bytes()
    path.write_bytes(original + b" ")
    with pytest.raises(ValueError, match="hash mismatch"):
        ne.verify_existing(root)
    path.write_bytes(original)
    model_path = root / ne.MODEL / "model.json"
    model_path.write_bytes(model_path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="hash mismatch"):
        ne.verify_existing(root)


@pytest.mark.parametrize("field", ["status", "checked_count", "physical_claim", "model_binding"])
def test_rehashed_report_inconsistencies_rejected(completed, field):
    root, output = completed
    path = output / "evaluation.json"
    report = json.loads(path.read_text())
    if field == "status":
        report["status"] = "failed"
    elif field == "checked_count":
        report["scalar_batch_equivalence"]["test_windows_checked"] = 1
    elif field == "physical_claim":
        report["physical_hardware_tested"] = True
    else:
        report["model_sha256"] = "0" * 64
    path.write_text(json.dumps(report))
    rehash_output(output)
    with pytest.raises(ValueError, match="provenance|binding"):
        ne.verify_existing(root)


def test_duplicate_window_rejected_even_with_correct_total_and_ids(completed):
    root, output = completed
    path = output / "predictions.npz"
    with np.load(path, allow_pickle=False) as archive:
        arrays = {key: archive[key].copy() for key in archive.files}
    arrays["window_index"][1] = arrays["window_index"][0]
    np.savez_compressed(path, **arrays)
    rehash_output(output)
    with pytest.raises(ValueError, match="continuity mismatch"):
        ne.verify_existing(root)


@pytest.mark.parametrize("artifact", ["records", "csv"])
def test_record_and_csv_crosschecks_reject_rehashed_inconsistency(completed, artifact):
    root, output = completed
    if artifact == "records":
        path = output / "records.json"
        value = json.loads(path.read_text())
        value["records"][0]["floating"]["accuracy"] = -1
        path.write_text(json.dumps(value))
    else:
        path = output / "predictions.csv"
        with path.open(newline="") as stream:
            reader = csv.DictReader(stream)
            columns, rows = reader.fieldnames, list(reader)
        rows[0]["float_logit_0"] = "-99999"
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
    rehash_output(output)
    with pytest.raises(ValueError, match="Per-record|CSV/NPZ"):
        ne.verify_existing(root)
