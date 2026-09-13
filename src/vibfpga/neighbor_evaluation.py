"""One-shot, immutable evaluation of the existing neighbor-energy candidate.

Verification imports no training framework and reads no original MAT waveform.
This is a subsequent evaluation on an already-used CWRU test split, not a new
external test set. It never trains, updates scales, or changes the candidate.
"""

import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import time

import numpy as np


CLASS_NAMES = ["inner_race", "outer_race", "ball"]
TEST_IDS = [108, 121, 133, 172, 188, 200, 212, 225, 237]
OUTPUT = Path("artifacts/reports/neighbor_test")
MODEL = Path("artifacts/model_neighbor")
SCOPE = (
    "Subsequent frozen-model evaluation on CWRU 12 kHz drive-end, 3 HP records. "
    "These same records were previously evaluated for the original single-bin model; "
    "they are not a fresh external or previously untouched test set. The split is "
    "cross-load on the same laboratory rig, with three seeded fault classes and "
    "no normal class. This run provides no physical-hardware or field accuracy evidence."
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def metric_summary(labels, predictions):
    labels, predictions = np.asarray(labels), np.asarray(predictions)
    if (labels.ndim != 1 or labels.shape != predictions.shape or not len(labels)
            or not np.issubdtype(labels.dtype, np.integer)
            or not np.issubdtype(predictions.dtype, np.integer)
            or np.any((labels < 0) | (labels > 2))
            or np.any((predictions < 0) | (predictions > 2))):
        raise ValueError("Expected nonempty equal-length integer class IDs 0..2")
    matrix = np.bincount(labels * 3 + predictions, minlength=9).reshape(3, 3)
    support = matrix.sum(axis=1)
    predicted_count = matrix.sum(axis=0)
    diagonal = np.diag(matrix)
    precision = np.divide(diagonal, predicted_count, out=np.zeros(3), where=predicted_count != 0)
    recall = np.divide(diagonal, support, out=np.zeros(3), where=support != 0)
    f1 = np.divide(2 * precision * recall, precision + recall,
                   out=np.zeros(3), where=precision + recall != 0)
    return {
        "windows": len(labels), "correct": int(diagonal.sum()),
        "accuracy": float(diagonal.sum() / len(labels)),
        "balanced_accuracy": float(recall[support > 0].mean()),
        "macro_f1": float(f1.mean()),
        "weighted_f1": float((f1 * support).sum() / len(labels)),
        "class_names": CLASS_NAMES,
        "confusion_matrix": matrix.tolist(),
        "confusion_matrix_axes": "rows=true class, columns=predicted class",
        "per_class": [{"class_id": i, "class_name": name, "support": int(support[i]),
                       "predicted_count": int(predicted_count[i]),
                       "precision": float(precision[i]), "recall": float(recall[i]),
                       "f1": float(f1[i])} for i, name in enumerate(CLASS_NAMES)],
        "zero_division": 0,
    }


def quantization_summary(labels, float_logits, integer_logits, logit_scale):
    labels = np.asarray(labels)
    fp, ip = float_logits.argmax(axis=1), integer_logits.argmax(axis=1)
    absolute = np.abs(integer_logits.astype(np.float64) * logit_scale - float_logits)
    fm, im = metric_summary(labels, fp), metric_summary(labels, ip)
    return {
        "prediction_disagreements": int(np.count_nonzero(fp != ip)),
        "prediction_agreement": float(np.mean(fp == ip)),
        "float_correct_integer_wrong": int(np.count_nonzero((fp == labels) & (ip != labels))),
        "float_wrong_integer_correct": int(np.count_nonzero((fp != labels) & (ip == labels))),
        "both_wrong_different_prediction": int(np.count_nonzero((fp != labels) & (ip != labels) & (fp != ip))),
        "accuracy_drop_percentage_points": 100 * (fm["accuracy"] - im["accuracy"]),
        "integer_minus_float_macro_f1_percentage_points": 100 * (im["macro_f1"] - fm["macro_f1"]),
        "per_class_integer_minus_float_recall_percentage_points": [
            100 * (i["recall"] - f["recall"]) for f, i in zip(fm["per_class"], im["per_class"])],
        "integer_logit_scale": logit_scale,
        "dequantized_logit_absolute_error": {
            "mean": float(absolute.mean()), "maximum": float(absolute.max()),
            "p99": float(np.percentile(absolute, 99)),
            "per_class_mean": absolute.mean(axis=0).tolist(),
            "units": "floating network logit units; integer logit multiplied by frozen logit_scale",
        },
        "interpretation": "Differences include input feature rounding, weight/bias quantization, hidden RNE and saturation; not weight quantization alone.",
    }


def _load_frozen_network(root, config):
    # No optimizer, training call, scale fit, or test data access is permitted here.
    import torch
    from .training import MLP

    expected = {"fc1.weight": (16, 16), "fc1.bias": (16,),
                "fc2.weight": (3, 16), "fc2.bias": (3,)}
    with np.load(root / MODEL / "float_parameters.npz", allow_pickle=False) as archive:
        if set(archive.files) != set(expected):
            raise ValueError("Unexpected floating parameter names")
        params = {key: archive[key].copy() for key in expected}
    checkpoint = torch.load(root / MODEL / "float_model.pt", map_location="cpu", weights_only=True)
    if set(checkpoint) != set(expected):
        raise ValueError("Checkpoint parameter names differ from NPZ")
    for key, shape in expected.items():
        value = params[key]
        tensor = checkpoint[key].detach().cpu().numpy()
        if (value.shape != shape or value.dtype != np.float32 or not np.isfinite(value).all()
                or tensor.shape != shape or tensor.dtype != value.dtype
                or tensor.tobytes() != value.tobytes()):
            raise ValueError(f"Checkpoint/NPZ mismatch: {key}")
    # Independently validate the pair using the ALREADY-FROZEN scales. This does
    # not create/export new parameters or fit any quantization scale.
    scale = config["scales"]
    comparisons = {
        "w1": np.clip(np.rint(params["fc1.weight"].astype(np.float64) / scale["w1_scale"]), -127, 127),
        "w2": np.clip(np.rint(params["fc2.weight"].astype(np.float64) / scale["w2_scale"]), -127, 127),
        "b1": np.rint(params["fc1.bias"].astype(np.float64) / (scale["input_scale"] * scale["w1_scale"])),
        "b2": np.rint(params["fc2.bias"].astype(np.float64) / (scale["hidden_scale"] * scale["w2_scale"])),
    }
    for name, expected_value in comparisons.items():
        if not np.array_equal(expected_value, config[name]):
            raise ValueError(f"Integer model does not match frozen float parameters/scales: {name}")
    if (config["hidden_shift"] != scale["hidden_exponent"] - (scale["input_exponent"] + scale["w1_exponent"])
            or scale["logit_scale"] != scale["hidden_scale"] * scale["w2_scale"]):
        raise ValueError("Inconsistent frozen activation/logit scales")
    network = MLP()
    network.load_state_dict({key: torch.from_numpy(value) for key, value in params.items()})
    network.eval()
    return network


def _batch_and_scalar_check(frames, config):
    from .fixed import frontend, frontend_batch_powers, infer, quantize_features
    from .training import predict_integer

    per_bin = np.concatenate([frontend_batch_powers(
        frames[start:start + 64], config["dft_bins"], n=1024, input_shift=5)
        for start in range(0, len(frames), 64)])
    powers = per_bin.reshape(-1, 16, 3).sum(axis=2, dtype=np.int64)
    features = quantize_features(powers, config["feature_shifts"])
    predicted, logits, hidden = predict_integer(config, features)
    for index, frame in enumerate(frames):
        scalar = frontend(frame, config)
        expected = infer(scalar["features"], config)
        for name, actual in (("dft_powers", per_bin[index]), ("powers", powers[index]),
                             ("features", features[index])):
            if not np.array_equal(scalar[name], actual):
                raise ValueError(f"Scalar/batch {name} mismatch at window {index}")
        for name, actual in (("hidden", hidden[index]), ("logits", logits[index]),
                             ("class_id", predicted[index])):
            if not np.array_equal(expected[name], actual):
                raise ValueError(f"Scalar/batch {name} mismatch at window {index}")
    return {"dft_powers": per_bin, "powers": powers, "features": features,
            "integer_prediction": predicted, "integer_logits": logits, "hidden": hidden}


def _preflight(root, config):
    n = 1024
    rng = np.random.default_rng(7521)
    index = np.arange(n)
    frames = [np.zeros(n, dtype=np.int16), np.full(n, 32767, dtype=np.int16),
              np.full(n, -32768, dtype=np.int16),
              np.where(index % 2, -32768, 32767).astype(np.int16),
              rng.integers(-32768, 32768, n, dtype=np.int16),
              np.rint(25000 * np.sin(2 * np.pi * config["bins"][0] * index / n)).astype(np.int16)]
    vectors = sorted((root / "artifacts/vectors_neighbor").glob("replay_*.json"))
    if len(vectors) != 9:
        raise ValueError("Expected the nine previously exported validation fixtures")
    for path in vectors:
        metadata = json.loads(path.read_text())
        if metadata["provenance"]["split"] != "validation":
            raise ValueError("Preflight fixtures must be validation-only")
        values = np.array([int(line, 16) for line in
                           (path.parent / metadata["samples_hex"]).read_text().splitlines()], dtype=np.int64)
        frames.append(np.where(values >= 32768, values - 65536, values).astype(np.int16))
    result = _batch_and_scalar_check(np.stack(frames), config)
    for offset, path in enumerate(vectors, start=6):
        expected = json.loads(path.read_text())["expected"]
        for field in ("powers", "features", "hidden"):
            if not np.array_equal(result[field][offset], expected[field]):
                raise ValueError(f"Frozen validation fixture {path.name}: {field} mismatch")
        if not np.array_equal(result["integer_logits"][offset], expected["logits"]):
            raise ValueError(f"Frozen validation fixture {path.name}: logits mismatch")
    return {"status": "passed", "synthetic_windows": 6, "frozen_validation_windows": len(vectors),
            "scalar_batch_equal": True, "frozen_validation_expected_equal": True,
            "checkpoint_npz_identical": True, "integer_parameters_match_frozen_float_scales": True,
            "test_waveforms_loaded": False, "random_seed": 7521}


def _input_paths(root):
    selected = list((root / MODEL).glob("*"))
    selected += list((root / "artifacts/vectors_neighbor").glob("replay_*.*"))
    selected += list((root / "artifacts/model").glob("*"))
    selected += [root / name for name in (
        "src/vibfpga/fixed.py", "src/vibfpga/dataset.py", "src/vibfpga/training.py",
        "src/vibfpga/neighbor_evaluation.py", "scripts/evaluate_neighbor.py",
        "scripts/compare_neighbor_features.py", "tests/test_neighbor_evaluation.py",
        "data/cwru/manifest.json", "artifacts/reports/neighbor_comparison.json",
        "artifacts/reports/test_evaluation.json", "artifacts/reports/test_predictions.npz",
        "artifacts/reports/window_manifest_test.json", "artifacts/reports/selection_frozen.json")]
    if any(not path.is_file() for path in selected):
        raise ValueError("A required frozen input/protected historical artifact is missing")
    return sorted(set(selected))


def _check_hashes(root, entries):
    for name, expected in entries.items():
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file() or digest(path) != expected:
            raise ValueError(f"Frozen file hash mismatch or missing file: {name}")


def _record_summaries(metadata, labels, fp, ip):
    ids = np.array([item["record_id"] for item in metadata])
    output = []
    for record_id in sorted(set(ids.tolist())):
        mask = ids == record_id
        true = np.unique(labels[mask])
        if len(true) != 1:
            raise ValueError("A record contains inconsistent true labels")
        first = metadata[int(np.flatnonzero(mask)[0])]
        row = {"record_id": record_id, "class_id": int(true[0]), "class_name": CLASS_NAMES[true[0]],
               "fault_inches": first["fault_inches"], "load_hp": first["load_hp"],
               "windows": int(mask.sum()), "prediction_disagreements": int(np.count_nonzero(fp[mask] != ip[mask]))}
        for name, predictions in (("floating", fp), ("integer", ip)):
            row[name] = {"correct": int(np.count_nonzero(predictions[mask] == labels[mask])),
                         "accuracy": float(np.mean(predictions[mask] == labels[mask])),
                         "predicted_class_counts": np.bincount(predictions[mask], minlength=3).tolist()}
        output.append(row)
    return output


def evaluate_once(root, output=None):
    """Reserve output before any work, freeze before reading test; never overwrite.

    An interrupted or failed reserved directory also refuses another evaluation.
    The CLI deliberately offers no alternate output path or force/retrain switch.
    """
    root = Path(root).resolve()
    output = Path(output) if output is not None else root / OUTPUT
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        output.mkdir(exist_ok=False)
    except FileExistsError as error:
        raise ValueError(f"Evaluation output already exists; only --verify is allowed: {output}") from error
    started = time.monotonic()
    try:
        input_hashes = {str(path.relative_to(root)): digest(path) for path in _input_paths(root)}
        config = json.loads((root / MODEL / "model.json").read_text())
        comparison = json.loads((root / "artifacts/reports/neighbor_comparison.json").read_text())
        model_hash = input_hashes[str(MODEL / "model.json")]
        if model_hash != comparison["candidate_model_sha256"]:
            raise ValueError("Candidate model differs from the historical frozen validation candidate")
        if (config["feature_mode"] != "neighbor3_energy" or config["n"] != 1024
                or config["input_shift"] != 5 or config["dft_shift"] != 20
                or config["class_names"] != CLASS_NAMES or len(config["bins"]) != 16
                or config["dft_bins"] != [k + delta for k in config["bins"] for delta in (-1, 0, 1)]):
            raise ValueError("Unexpected frozen candidate numerical contract")
        network = _load_frozen_network(root, config)
        preflight = _preflight(root, config)
        manifest = json.loads((root / "data/cwru/manifest.json").read_text())
        test_records = [row for row in manifest["records"] if row["split"] == "test"]
        if (sorted(row["record_id"] for row in test_records) != TEST_IDS
                or any(row["load_hp"] != 3 or row["sample_rate_hz"] != 12000
                       or row["channel"] != "DE" for row in test_records)
                or sum(row["samples"] // 1024 for row in test_records) != 1070):
            raise ValueError("Audited manifest differs from the predefined nine-record/1070-window split")
        _check_hashes(root, input_hashes)
        write_json(output / "preflight.json", preflight)
        # Snapshot small files for inspection/reproduction. Large original MAT
        # records are bound by the existing manifest, not opened before freeze.
        snapshots = {}
        for name in input_hashes:
            path = root / name
            if name.startswith(str(MODEL)) or name.startswith("src/") or name.startswith("scripts/") or name == "data/cwru/manifest.json":
                target = output / "frozen_inputs" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes())
                snapshots[str(target.relative_to(output))] = digest(target)
                if snapshots[str(target.relative_to(output))] != input_hashes[name]:
                    raise ValueError(f"Input changed during snapshot: {name}")
        frozen = {
            "schema_version": 1, "frozen_utc": utc_now(), "model_sha256": model_hash,
            "input_sha256": input_hashes, "snapshot_sha256": snapshots,
            "test_record_sha256": {str(row["record_id"]): row["sha256"] for row in test_records},
            "test_record_ids": TEST_IDS, "expected_windows": 1070,
            "checkpoint_npz_identical": True, "test_waveforms_loaded_by_this_evaluation_before_freeze": False,
            "prior_baseline_test_evaluated": True,
            "prior_data_audit_read_all_records": True,
            "scope": SCOPE, "model_training_or_tuning_in_this_run": False,
            "selection_after_test": False,
            "float_reference": "Saved FP32 MLP with unrounded scaled/clamped INTEGER DSP powers (same reference as validation); not a fully floating-point DSP pipeline.",
            "window_protocol": "Records split before nonoverlapping N=1024 windows; stride 1024; discard each record tail; frozen train-derived PCM scale; no window filtering.",
            "libraries": {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "torch", "scikit-learn")},
            "python": platform.python_version(), "platform": platform.platform(),
        }
        write_json(output / "freeze.json", frozen)
        freeze_hash = digest(output / "freeze.json")
        _check_hashes(root, input_hashes)
        # This is the first read of TEST waveforms in this evaluator. Everything
        # defining the model, protocol and evaluator is already frozen on disk.
        from .dataset import load_windows
        from .training import float_features
        import torch

        test_load_started = utc_now()
        frames, labels, metadata, clipping = load_windows(root / "data/cwru", "test", config["raw_scale"], n=1024)
        if (len(frames) != 1070 or sorted({row["record_id"] for row in metadata}) != TEST_IDS
                or any(row["split"] != "test" or row["load_hp"] != 3 for row in metadata)):
            raise ValueError("Loaded test data does not match frozen protocol")
        integer = _batch_and_scalar_check(frames, config)
        torch.set_num_threads(2)
        torch.use_deterministic_algorithms(True)
        with torch.no_grad():
            float_logits = network(torch.tensor(float_features(integer["powers"], config["feature_shifts"]),
                                                 dtype=torch.float32)).cpu().numpy()
        fp, ip = float_logits.argmax(axis=1), integer["integer_prediction"]
        fm, im = metric_summary(labels, fp), metric_summary(labels, ip)
        quant = quantization_summary(labels, float_logits, integer["integer_logits"], config["scales"]["logit_scale"])
        record_rows = _record_summaries(metadata, labels, fp, ip)
        write_json(output / "records.json", {"class_names": CLASS_NAMES, "records": record_rows,
                   "note": "Each record has one true class; accuracy and predicted-class counts are reported without a misleading three-class per-record macro F1."})
        np.savez_compressed(output / "predictions.npz", true_class=labels, float_prediction=fp,
                            float_logits=float_logits, **integer,
                            record_id=np.array([row["record_id"] for row in metadata], dtype=np.int64),
                            window_index=np.array([row["window_index"] for row in metadata], dtype=np.int64),
                            sample_start=np.array([row["sample_start"] for row in metadata], dtype=np.int64),
                            sample_stop=np.array([row["sample_stop"] for row in metadata], dtype=np.int64))
        with (output / "predictions.csv").open("x", newline="") as stream:
            columns = ["record_id", "split", "load_hp", "fault_inches", "window_index", "sample_start", "sample_stop",
                       "true_class", "true_class_name", "float_prediction", "integer_prediction",
                       "float_correct", "integer_correct", "prediction_disagrees"]
            columns += [f"{name}_logit_{i}" for name in ("float", "integer") for i in range(3)]
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            for i, item in enumerate(metadata):
                row = {key: item[key] for key in columns if key in item}
                row.update(true_class=int(labels[i]), true_class_name=CLASS_NAMES[labels[i]],
                           float_prediction=int(fp[i]), integer_prediction=int(ip[i]),
                           float_correct=bool(fp[i] == labels[i]), integer_correct=bool(ip[i] == labels[i]),
                           prediction_disagrees=bool(fp[i] != ip[i]))
                for name, logits in (("float", float_logits), ("integer", integer["integer_logits"])):
                    row.update({f"{name}_logit_{j}": logits[i, j].item() for j in range(3)})
                writer.writerow(row)
        _check_hashes(root, input_hashes)
        if digest(output / "freeze.json") != freeze_hash:
            raise ValueError("Freeze manifest changed during evaluation")
        report = {
            "schema_version": 1, "status": "passed", "evaluation_kind": "subsequent_frozen_neighbor_test",
            "model_sha256": model_hash, "freeze_sha256": freeze_hash,
            "frozen_utc": frozen["frozen_utc"], "test_load_started_utc": test_load_started,
            "completed_utc": utc_now(), "seconds": time.monotonic() - started,
            "windows": len(labels), "record_count": len(record_rows), "test_record_ids": TEST_IDS,
            "float_metrics": fm, "integer_metrics": im, "quantization_difference": quant,
            "scalar_batch_equivalence": {"status": "passed", "test_windows_checked": len(labels),
                "fields": ["dft_powers", "powers", "features", "hidden", "logits", "class_id"],
                "mismatches": 0, "uses_same_loaded_test_array": True},
            "checkpoint_npz_identical": True, "all_frozen_inputs_unchanged": True,
            "raw_conversion_and_record_tails": clipping,
            "prior_baseline_test_evaluated": True, "scope": SCOPE,
            "float_reference": frozen["float_reference"], "window_protocol": frozen["window_protocol"],
            "test_waveform_load_calls_in_this_evaluation": 1,
            "model_training_or_tuning_in_this_run": False, "model_files_updated": False,
            "historical_model_json_test_evaluated_field": config["test_evaluated"],
            "historical_status_note": "The existing model JSON and neighbor validation report retain their historical test_evaluated=false fields. This separate subsequent result is joined by model_sha256.",
            "physical_hardware_tested": False,
        }
        write_json(output / "evaluation.json", report)
        output_hashes = {str(path.relative_to(output)): digest(path) for path in sorted(output.rglob("*")) if path.is_file()}
        write_json(output / "completion.json", {"schema_version": 1, "status": "passed", "completed_utc": utc_now(),
                   "model_sha256": model_hash, "freeze_sha256": freeze_hash,
                   "output_sha256": output_hashes})
        return verify_existing(root, output)
    except Exception as error:
        # A failure is evidence too, and must not silently become a rerun.
        failure = output / "failure.json"
        if not failure.exists():
            write_json(failure, {"status": "failed", "utc": utc_now(), "error": str(error),
                                "rerun_allowed": False, "note": "Preserve this reserved directory; investigate before any explicit new experiment."})
        raise


def verify_existing(root, output=None):
    """Read-only artifact/hash/metric verification; no MAT load or inference.

    Returns status='passed' and checked counts, or raises ValueError. Source and
    model drift are errors, not permission to rerun test. Hashes establish file
    consistency, not cryptographic third-party certification of execution.
    """
    root = Path(root).resolve()
    output = Path(output) if output is not None else root / OUTPUT
    if not output.is_absolute():
        output = root / output
    try:
        completion = json.loads((output / "completion.json").read_text())
        if completion["status"] != "passed" or (output / "failure.json").exists():
            raise ValueError("No completed successful evaluation")
        hashes = completion["output_sha256"]
        required = {"freeze.json", "preflight.json", "evaluation.json", "predictions.csv", "predictions.npz", "records.json"}
        actual = {str(path.relative_to(output)) for path in output.rglob("*") if path.is_file()} - {"completion.json"}
        if not required.issubset(hashes) or actual != set(hashes):
            raise ValueError("Incomplete or unexpected evaluation output inventory")
        _check_hashes(output, hashes)
        frozen = json.loads((output / "freeze.json").read_text())
        report = json.loads((output / "evaluation.json").read_text())
        preflight = json.loads((output / "preflight.json").read_text())
        _check_hashes(root, frozen["input_sha256"])
        _check_hashes(output, frozen["snapshot_sha256"])
        model_hash = frozen["input_sha256"][str(MODEL / "model.json")]
        if (frozen["model_sha256"] != model_hash or completion["model_sha256"] != model_hash
                or report["model_sha256"] != model_hash
                or completion["freeze_sha256"] != digest(output / "freeze.json")
                or report["freeze_sha256"] != completion["freeze_sha256"]):
            raise ValueError("Model or freeze binding mismatch")
        if not (report["status"] == "passed" and preflight["status"] == "passed"
                and report["scalar_batch_equivalence"]["status"] == "passed"
                and report["scalar_batch_equivalence"]["test_windows_checked"] == 1070
                and frozen["checkpoint_npz_identical"] and report["checkpoint_npz_identical"]
                and not frozen["test_waveforms_loaded_by_this_evaluation_before_freeze"]
                and report["prior_baseline_test_evaluated"] and report["all_frozen_inputs_unchanged"]
                and frozen["prior_baseline_test_evaluated"]
                and not frozen["model_training_or_tuning_in_this_run"]
                and not report["model_training_or_tuning_in_this_run"]
                and not report["model_files_updated"] and not report["physical_hardware_tested"]
                and report["test_waveform_load_calls_in_this_evaluation"] == 1
                and report["scalar_batch_equivalence"]["mismatches"] == 0
                and report["test_load_started_utc"] >= frozen["frozen_utc"]):
            raise ValueError("Evaluation provenance assertions are inconsistent")
        with np.load(output / "predictions.npz", allow_pickle=False) as archive:
            values = {key: archive[key] for key in archive.files}
        labels, fp, ip = (values[key] for key in ("true_class", "float_prediction", "integer_prediction"))
        shapes = {"dft_powers": (1070, 48), "powers": (1070, 16), "features": (1070, 16),
                  "hidden": (1070, 16), "float_logits": (1070, 3), "integer_logits": (1070, 3)}
        shapes.update({name: (1070,) for name in ("true_class", "float_prediction", "integer_prediction",
                       "record_id", "window_index", "sample_start", "sample_stop")})
        if set(values) != set(shapes) or any(values[key].shape != shape for key, shape in shapes.items()):
            raise ValueError("Stored prediction array schema/shape mismatch")
        if (any(not np.issubdtype(value.dtype, np.integer) for key, value in values.items() if key != "float_logits")
                or values["float_logits"].dtype != np.float32
                or not np.isfinite(values["float_logits"]).all()):
            raise ValueError("Stored prediction dtype or finiteness mismatch")
        if (len(labels) != 1070 or report["windows"] != 1070 or report["record_count"] != 9
                or sorted(set(values["record_id"].tolist())) != TEST_IDS
                or not np.array_equal(fp, values["float_logits"].argmax(axis=1))
                or not np.array_equal(ip, values["integer_logits"].argmax(axis=1))):
            raise ValueError("Stored predictions violate frozen split or argmax contract")
        if (metric_summary(labels, fp) != report["float_metrics"]
                or metric_summary(labels, ip) != report["integer_metrics"]):
            raise ValueError("Saved metrics differ from saved predictions")
        config = json.loads((root / MODEL / "model.json").read_text())
        if quantization_summary(labels, values["float_logits"], values["integer_logits"],
                                config["scales"]["logit_scale"]) != report["quantization_difference"]:
            raise ValueError("Saved quantization differences disagree with saved predictions")
        manifest = json.loads((root / "data/cwru/manifest.json").read_text())
        specs = sorted((row for row in manifest["records"] if row["split"] == "test"), key=lambda row: row["record_id"])
        if (frozen["test_record_ids"] != TEST_IDS or report["test_record_ids"] != TEST_IDS
                or frozen["test_record_sha256"] != {str(row["record_id"]): row["sha256"] for row in specs}):
            raise ValueError("Test record manifest binding mismatch")
        metadata = [{"record_id": spec["record_id"], "split": "test", "class_id": spec["label"],
                     "load_hp": spec["load_hp"], "fault_inches": spec["fault_inches"],
                     "window_index": index, "sample_start": index * 1024, "sample_stop": (index + 1) * 1024}
                    for spec in specs for index in range(spec["samples"] // 1024)]
        for name in ("record_id", "window_index", "sample_start", "sample_stop"):
            if not np.array_equal(values[name], [row[name] for row in metadata]):
                raise ValueError(f"Record/window order or continuity mismatch: {name}")
        if not np.array_equal(labels, [row["class_id"] for row in metadata]):
            raise ValueError("Saved true labels differ from the frozen per-record labels")
        saved_records = json.loads((output / "records.json").read_text())
        if saved_records["records"] != _record_summaries(metadata, labels, fp, ip):
            raise ValueError("Per-record report differs from saved predictions")
        with (output / "predictions.csv").open(newline="") as stream:
            csv_rows = list(csv.DictReader(stream))
        if len(csv_rows) != 1070:
            raise ValueError("CSV prediction row count mismatch")
        for index, (row, item) in enumerate(zip(csv_rows, metadata)):
            for key in ("record_id", "load_hp", "window_index", "sample_start", "sample_stop"):
                if int(row[key]) != item[key]:
                    raise ValueError(f"CSV/NPZ provenance mismatch at window {index}: {key}")
            if (row["split"] != "test" or row["fault_inches"] != item["fault_inches"]
                    or int(row["true_class"]) != labels[index]
                    or row["true_class_name"] != CLASS_NAMES[labels[index]]
                    or int(row["float_prediction"]) != fp[index] or int(row["integer_prediction"]) != ip[index]
                    or row["float_correct"] != str(bool(fp[index] == labels[index]))
                    or row["integer_correct"] != str(bool(ip[index] == labels[index]))
                    or row["prediction_disagrees"] != str(bool(fp[index] != ip[index]))):
                raise ValueError(f"CSV/NPZ prediction mismatch at window {index}")
            for name in ("float", "integer"):
                cast = float if name == "float" else int
                if any(cast(row[f"{name}_logit_{j}"]) != values[f"{name}_logits"][index, j] for j in range(3)):
                    raise ValueError(f"CSV/NPZ logit mismatch at window {index}: {name}")
        return {"status": "passed", "model_sha256": model_hash, "windows": len(labels), "record_count": 9,
                "input_hashes_checked": len(frozen["input_sha256"]), "output_hashes_checked": len(hashes),
                "freeze_sha256": completion["freeze_sha256"], "completion_sha256": digest(output / "completion.json"),
                "saved_prediction_metrics_match": True, "record_windows_and_csv_match": True,
                "original_mat_read": False, "inference_run": False}
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot verify frozen neighbor evaluation: {error}") from error
