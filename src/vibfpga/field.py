"""Record-separated ADXL345 training. Synthetic fixtures are never field evidence.

This profile deliberately uses raw counts (not calibrated mg): apply the
algorithm's [-1024,1023] input clamp, multiply by 32, then the shared N=256
DSP/MLP core. The static calibration experiment remains a separate chain.
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier

from .export import export_model, export_vectors
from .fixed import frontend_batch_powers, quantize_features
from .sensor import analyze_capture, read_capture
from .training import (MLP, feature_shifts, fit_mlp, float_features,
                       float_spectrum, make_integer_model, metrics,
                       predict_float, predict_integer)

N, ODR, CLOCK = 256, 800, 12_000_000
CLASS_NAMES = ["stopped", "rigid_support_running", "flexible_support_running"]
FIXTURE = "synthetic_pipeline_fixture"


def source_hashes():
    directory=Path(__file__).resolve().parent
    return {name:digest(directory/name) for name in ("field.py","fixed.py","training.py","sensor.py","export.py")}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def raw_to_core(raw):
    raw = np.asarray(raw)
    if not np.issubdtype(raw.dtype, np.integer) or np.any(raw < -32768) or np.any(raw > 32767):
        raise ValueError("raw counts must be signed int16 integers")
    return (np.clip(raw.astype(np.int64), -1024, 1023) * 32).astype(np.int16)


def load_manifest(path, *, allow_fixture=False):
    path = Path(path).resolve()
    m = json.loads(path.read_text())
    if m.get("schema_version") != 1 or m.get("odr_hz") != ODR or m.get("clock_hz") != CLOCK:
        raise ValueError("field profile requires schema 1, 800 Hz and 12 MHz")
    if m.get("axis") not in ("x", "y", "z") or m.get("class_names") != CLASS_NAMES:
        raise ValueError("unknown axis or field-state label mapping")
    fixture = m.get("source_kind") == FIXTURE
    if fixture and not allow_fixture:
        raise ValueError("synthetic fixture requires explicit --allow-fixture")
    if not fixture and m.get("source_kind") != "physical_adxl345":
        raise ValueError("source_kind must identify physical ADXL345 or synthetic fixture")
    if not m.get("apparatus"):
        raise ValueError("record the apparatus and mounting arrangement")
    seen = {k: {} for k in ("path", "sha256", "record_id", "session_id", "installation_id")}
    counts = Counter()
    for r in m.get("records", []):
        if r.get("split") not in ("train", "validation", "test") or r.get("label") not in (0, 1, 2):
            raise ValueError("invalid record split or label")
        r["path"] = str((path.parent / r["path"]).resolve())
        for key in seen:
            value = r.get(key)
            if not isinstance(value, str) or not value:
                raise ValueError(f"missing {key}")
            if key in ("path", "sha256", "record_id") and value in seen[key]:
                raise ValueError(f"duplicate record {key}")
            if value in seen[key] and seen[key][value] != r["split"]:
                raise ValueError(f"{key} leaks across record splits")
            seen[key][value] = r["split"]
        if len(r["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in r["sha256"]):
            raise ValueError("invalid declared SHA256")
        if not fixture:
            declared=r.get("sidecar_sha256", "")
            if len(declared)!=64 or any(c not in "0123456789abcdef" for c in declared):
                raise ValueError("physical records require a declared sidecar_sha256")
        counts[r["split"], r["label"]] += 1
    for split, minimum in (("train", 6), ("validation", 2), ("test", 2)):
        for label in range(3):
            if counts[split, label] < (1 if fixture else minimum):
                raise ValueError(f"insufficient independent {split} records for class {label}")
    m["manifest_path"], m["manifest_sha256"] = str(path), digest(path)
    return m


def load_split(manifest, split):
    frames, labels, provenance, reports = [], [], [], []
    for r in manifest["records"]:
        if r["split"] != split:
            continue
        path = Path(r["path"])
        if digest(path) != r["sha256"]:
            raise ValueError(f"capture hash changed: {r['record_id']}")
        if manifest["source_kind"] == "physical_adxl345":
            if not path.with_suffix(".json").is_file():
                raise ValueError("physical captures require the acquisition metadata sidecar")
            if digest(path.with_suffix(".json"))!=r["sidecar_sha256"]:
                raise ValueError("physical acquisition metadata hash changed")
            sidecar = json.loads(path.with_suffix(".json").read_text())
            required = {"csv_sha256", "odr_hz", "clock_hz", "axis", "error_flags",
                        "missed_service", "observed_sensor_overruns", "observed_samples"}
            if not required.issubset(sidecar):
                raise ValueError("incomplete physical acquisition metadata")
        quality = analyze_capture(path, odr=ODR, clock_hz=CLOCK, axis=manifest["axis"])
        if not quality["psd_valid_uniform_sampling_assumption"]:
            raise ValueError(f"capture has gaps/service errors: {r['record_id']}")
        # A project admission gate, not a claim about the sensor's ADC jitter or
        # guaranteed oscillator tolerance. Detect wrong ODR/clock metadata.
        if abs(quality["service_interval_cycles"]["mean"] / (CLOCK/ODR)-1)>0.05:
            raise ValueError(f"mean service rate differs from configured ODR by >5%: {r['record_id']}")
        data, _ = read_capture(path)
        if manifest["source_kind"] == "physical_adxl345" and len(data) < 30 * ODR:
            raise ValueError("physical training captures must contain at least 30 seconds")
        raw = data[f"{manifest['axis']}_raw"].astype(np.int16)
        count = len(raw) // N
        if not count:
            raise ValueError("capture shorter than one window")
        converted = raw_to_core(raw[:count*N]).reshape(count, N)
        frames.extend(converted)
        labels.extend([r["label"]] * count)
        provenance.extend([{k: r[k] for k in ("record_id", "label", "split", "sha256", "installation_id")}
                           | {"window_index": i} for i in range(count)])
        reports.append({"record_id": r["record_id"], "windows": count,
                        "discarded_tail_samples": len(raw) - count*N,
                        "clipped_samples": int(np.count_nonzero((raw < -1024) | (raw > 1023)))})
    return np.asarray(frames, dtype=np.int16), np.asarray(labels), provenance, reports


def select_bins(powers, labels):
    """Train-only Fisher score; three-bin separation prevents near duplicates."""
    x = np.log1p(powers[:, 1:N//2])
    mean = x.mean(axis=0)
    between, within = np.zeros(x.shape[1]), np.zeros(x.shape[1])
    for label in range(3):
        v = x[labels == label]
        between += len(v) * (v.mean(axis=0) - mean)**2
        within += ((v-v.mean(axis=0))**2).sum(axis=0)
    chosen = []
    for i in np.argsort(-(between/np.maximum(within, 1e-12)), kind="stable"):
        k = int(i+1)
        if all(abs(k-j) >= 3 for j in chosen):
            chosen.append(k)
        if len(chosen) == 16:
            return sorted(chosen)
    raise ValueError("not enough separated frequency bins")


def _powers(frames, bins):
    return np.concatenate([frontend_batch_powers(frames[i:i+64], bins, n=N)
                           for i in range(0, len(frames), 64)])


def _metrics(y, predicted):
    return metrics(y, predicted) | {"class_names": CLASS_NAMES}


def _rms(frames):
    x = frames.astype(np.float64)
    return np.sqrt(np.mean((x-x.mean(axis=1, keepdims=True))**2, axis=1))[:, None]


def _baseline_predictions(baseline, frames, features):
    rms = _rms(frames).ravel()
    tree = baseline["rms_tree"]
    predicted = []
    for value in rms:
        node = 0
        while tree["left"][node] != -1:
            node = tree["left"][node] if value <= tree["threshold"][node] else tree["right"][node]
        predicted.append(tree["class"][node])
    linear = np.asarray(features) @ np.asarray(baseline["linear_coef"]).T + baseline["linear_intercept"]
    return np.asarray(predicted), np.argmax(linear, axis=1)


def train(manifest_path, destination, *, allow_fixture=False, epochs=100, seed=7):
    if epochs < 1:
        raise ValueError("epochs must be positive")
    m = load_manifest(manifest_path, allow_fixture=allow_fixture)
    destination = Path(destination).resolve()
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("output must be new/empty; frozen experiments cannot be overwritten")
    # No test capture is opened during selection, feature fitting or training.
    tx, ty, meta, tr = load_split(m, "train")
    vx, vy, _, vr = load_split(m, "validation")
    tf, vf = float_spectrum(tx), float_spectrum(vx)
    bins = select_bins(tf, ty)
    tp, vp = _powers(tx, bins), _powers(vx, bins)
    shifts = feature_shifts(tp)
    tq, vq = quantize_features(tp, shifts), quantize_features(vp, shifts)
    torch.set_num_threads(1)
    network, history = fit_mlp(tq/128.0, ty, vq/128.0, vy, epochs=epochs, seed=seed)
    fixture = m["source_kind"] == FIXTURE
    config = {"n": N, "sample_rate_hz": ODR, "input_shift": 5, "dft_shift": 18,
              "bins": bins, "feature_shifts": shifts, "feature_mode": "single_bin",
              "class_names": CLASS_NAMES, "profile": "adxl345_field_states",
              "training_status": "synthetic_fixture_not_for_deployment" if fixture else "trained_field_records",
              "source_kind": m["source_kind"], "manifest_sha256": m["manifest_sha256"],
              "input_contract": "signed raw counts -> clip[-1024,1023] -> multiply by32; no mg calibration",
              "axis": m["axis"], "physical_board_tested": False}
    model = make_integer_model(network, tq/128.0, config)
    rms = DecisionTreeClassifier(max_leaf_nodes=3, random_state=seed).fit(_rms(tx), ty)
    linear = LogisticRegression(max_iter=1000, random_state=seed).fit(tq/128.0, ty)
    baseline = {"rms_tree": {"left": rms.tree_.children_left.tolist(), "right": rms.tree_.children_right.tolist(),
                            "threshold": rms.tree_.threshold.tolist(),
                            "class": np.argmax(rms.tree_.value[:, 0, :], axis=1).tolist()},
                "linear_coef": linear.coef_.tolist(), "linear_intercept": linear.intercept_.tolist()}
    destination.mkdir(parents=True, exist_ok=True)
    export_model(model, destination / "model")
    write_json(destination / "float_weights.json", {k: v.detach().numpy().tolist() for k,v in network.state_dict().items()})
    write_json(destination / "baselines.json", baseline)
    write_json(destination / "manifest.json", m)
    floating = predict_float(network, float_features(vf[:, bins], shifts))
    integer_dsp = predict_float(network, vq/128.0)
    integer = predict_integer(model, vq)[0]
    rp, lp = _baseline_predictions(baseline, vx, vq/128.0)
    report = {"schema_version": 1, "source_kind": m["source_kind"],
              "claim": "synthetic pipeline diagnostics only" if fixture else "held-out installation validation; no test selection",
              "physical_board_tested": False, "history": history,
              "optimizer": {"name": "AdamW", "learning_rate": 0.025, "weight_decay": 1e-5, "batch": "full training set"},
              "train_records": tr, "validation_records": vr, "test_captures_opened": False,
              "validation": {"rms_threshold": _metrics(vy,rp), "linear_spectrum": _metrics(vy,lp),
                             "float_dsp_float_nn": _metrics(vy,floating), "integer_dsp_float_nn": _metrics(vy,integer_dsp),
                             "integer_dsp_int8_nn": _metrics(vy,integer)},
              "quantization": "symmetric per-layer power-of-two PTQ; RNE; INT32 bounds checked",
              "qat_required_by_validation": _metrics(vy,integer_dsp)["macro_f1"] - _metrics(vy,integer)["macro_f1"] > 0.02}
    write_json(destination / "training.json", report)
    export_vectors(model, tx[:min(6,len(tx))], meta[:6], destination / "vectors", prefix="field")
    # Bind every deployment and comparison input before a separate test invocation.
    files = {str(p.relative_to(destination)): digest(p) for p in sorted(destination.rglob("*")) if p.is_file()}
    write_json(destination / "frozen.json", {"created_utc": datetime.now(timezone.utc).isoformat(),
                                            "source_kind": m["source_kind"], "files": files,
                                            "source_sha256":source_hashes(),
                                            "versions":{"numpy":np.__version__,"torch":torch.__version__}})
    return report


def evaluate(destination, *, allow_fixture=False):
    destination = Path(destination).resolve()
    if (destination / "test.json").exists():
        raise ValueError("test already evaluated; preserve the frozen result")
    frozen = json.loads((destination / "frozen.json").read_text())
    if frozen["source_sha256"]!=source_hashes():
        raise ValueError("frozen numerical/quality source code changed")
    for name, expected in frozen["files"].items():
        if digest(destination / name) != expected:
            raise ValueError(f"frozen experiment changed: {name}")
    m = load_manifest(destination / "manifest.json", allow_fixture=allow_fixture)
    # Exclusive reservation happens before any test capture is opened. Keep it
    # even after a failure: an interrupted evaluation is not an unseen test set.
    with (destination/"test_attempt.json").open("x") as attempt:
        json.dump({"started_utc":datetime.now(timezone.utc).isoformat(),
                   "freeze_sha256":digest(destination/"frozen.json")},attempt)
    frames, labels, provenance, records = load_split(m, "test")
    model = json.loads((destination / "model/model.json").read_text())
    network = MLP()
    network.load_state_dict({k: torch.tensor(v) for k,v in json.loads((destination / "float_weights.json").read_text()).items()})
    powers = _powers(frames, model["bins"])
    features = quantize_features(powers, model["feature_shifts"])
    prediction, logits, _ = predict_integer(model, features)
    baseline = json.loads((destination / "baselines.json").read_text())
    rp, lp = _baseline_predictions(baseline, frames, features/128.0)
    float_pred = predict_float(network, float_features(float_spectrum(frames)[:, model["bins"]], model["feature_shifts"]))
    int_dsp_pred = predict_float(network, features/128.0)
    report = {"source_kind": m["source_kind"], "physical_board_tested": False,
              "claim": "synthetic pipeline diagnostics only" if m["source_kind"] == FIXTURE else "held-out records/remounts of this apparatus only",
              "model_sha256": digest(destination / "model/model.json"), "freeze_sha256": digest(destination / "frozen.json"),
              "records": records, "rms_threshold": _metrics(labels,rp), "linear_spectrum": _metrics(labels,lp),
              "float_dsp_float_nn": _metrics(labels,float_pred), "integer_dsp_float_nn": _metrics(labels,int_dsp_pred),
              "integer_dsp_int8_nn": _metrics(labels,prediction),
              "predictions": [{**p, "prediction": int(c), "logits": l.tolist()} for p,c,l in zip(provenance,prediction,logits)]}
    write_json(destination / "test.json", report)
    return report
