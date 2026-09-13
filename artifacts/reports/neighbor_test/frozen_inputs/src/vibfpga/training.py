"""Real CWRU training, train-only feature design and fixed-point export.

Model/feature selection only sees train and validation. The held-out load-3
test split is evaluated after selection is frozen; subsequent invocations
refuse to silently rerun or tune against that test report.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import time
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score, recall_score
from sklearn.tree import DecisionTreeClassifier
import torch
from torch import nn

from .dataset import CLASS_NAMES, fit_raw_scale, load_windows, records, sha256
from .export import export_model, export_vectors
from .fixed import frontend_batch_powers, infer, quantize_features, round_shift_even


def metrics(labels, predicted):
    return {"accuracy": float(accuracy_score(labels, predicted)),
            "balanced_accuracy": float(balanced_accuracy_score(labels, predicted)),
            "macro_f1": float(f1_score(labels, predicted, average="macro", labels=[0,1,2], zero_division=0)),
            "per_class_recall": recall_score(labels, predicted, labels=[0,1,2], average=None, zero_division=0).tolist(),
            "confusion_matrix": confusion_matrix(labels, predicted, labels=[0,1,2]).tolist(),
            "windows": len(labels), "class_names": CLASS_NAMES}


def float_spectrum(frames):
    """Independent float DSP reference from the same PCM16 input frames."""
    n = frames.shape[1]
    x = frames.astype(np.float64)
    x = np.clip((x - x.mean(axis=1, keepdims=True)) / 32.0, -2048, 2047)
    h = 0.5 - 0.5 * np.cos(2*np.pi*np.arange(n)/n)
    transform = np.fft.rfft(x * h[None, :], axis=1) * 16.0 / n
    # Match the contracted output range, without integer rounding.
    re, im = np.clip(transform.real, -32768, 32767), np.clip(transform.imag, -32768, 32767)
    return re * re + im * im


def candidate_bins(train_spectrum, labels, n):
    candidates = {
        "uniform": np.rint(np.linspace(4, n//2 - 16, 16)).astype(int).tolist(),
        "logarithmic": np.unique(np.rint(np.geomspace(3, n//2 - 16, 16)).astype(int)).tolist(),
    }
    x = np.log1p(train_spectrum[:, 1:n//2])
    overall = x.mean(axis=0)
    between, within = np.zeros(x.shape[1]), np.zeros(x.shape[1])
    for label in range(3):
        values = x[labels == label]
        between += len(values) * (values.mean(axis=0) - overall)**2
        within += ((values - values.mean(axis=0))**2).sum(axis=0)
    score = between / np.maximum(within, 1e-12)
    chosen = []
    for zero_index in np.argsort(-score, kind="stable"):
        k = int(zero_index + 1)
        if all(abs(k - earlier) >= 6 for earlier in chosen):
            chosen.append(k)
            if len(chosen) == 16:
                break
    if len(chosen) != 16:
        raise ValueError("frame length too small for 16 separated feature bins")
    candidates["train_fisher_separated"] = sorted(chosen)
    return candidates, score


def feature_shifts(train_powers, percentile=99.5):
    """Train-only scales; percentile is a fixed design setting, not test-tuned."""
    peak = np.percentile(train_powers, percentile, axis=0)
    return [max(0, int(math.ceil(math.log2(max(float(p), 1.0) / 120.0)))) for p in peak]


def float_features(powers, shifts):
    return np.clip(powers.astype(np.float64) / np.exp2(shifts)[None, :], 0, 127) / 128.0


def int_powers(frames, bins, n):
    return np.concatenate([frontend_batch_powers(frames[i:i+64], bins, n=n)
                           for i in range(0, len(frames), 64)])


class MLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1, self.fc2 = nn.Linear(16, 16), nn.Linear(16, 3)

    def forward(self, x):
        return self.fc2(torch.relu(self.fc1(x)))


def predict_float(model, inputs):
    model.eval()
    with torch.no_grad():
        return model(torch.tensor(inputs, dtype=torch.float32)).argmax(dim=1).cpu().numpy()


def fit_mlp(train_x, train_y, val_x, val_y, epochs=450, seed=7):
    torch.manual_seed(seed)
    model = MLP()
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.025, weight_decay=1e-5)
    counts = np.bincount(train_y, minlength=3)
    loss_fn = nn.CrossEntropyLoss(weight=torch.tensor(len(train_y)/(3*counts), dtype=torch.float32))
    tx, ty = torch.tensor(train_x, dtype=torch.float32), torch.tensor(train_y, dtype=torch.long)
    best, best_score, best_epoch = None, (-1.0, -float("inf")), 0
    curve = []
    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()
        loss = loss_fn(model(tx), ty)
        loss.backward()
        optimizer.step()
        if (epoch + 1) % 10 == 0 or epoch == epochs - 1:
            measured = metrics(val_y, predict_float(model, val_x))
            score = (measured["macro_f1"], -float(loss.item()))
            curve.append({"epoch": epoch+1, "train_loss": float(loss.item()),
                          "validation_macro_f1": measured["macro_f1"]})
            if score > best_score:
                best, best_score, best_epoch = deepcopy(model.state_dict()), score, epoch+1
    model.load_state_dict(best)
    model.eval()
    return model, {"epochs_run": epochs, "selected_epoch": best_epoch, "seed": seed,
                   "selection": "validation macro F1, ties broken by lower training loss", "learning_curve": curve}


def _pow2_exponent(maximum, limit=127):
    return int(math.ceil(math.log2(max(float(maximum), 1e-12) / limit)))


def make_integer_model(float_model, train_x, config, frozen_scales=None):
    params = {k: v.detach().cpu().numpy().astype(np.float64) for k, v in float_model.state_dict().items()}
    if frozen_scales is None:
        e1 = _pow2_exponent(abs(params["fc1.weight"]).max())
        e2 = _pow2_exponent(abs(params["fc2.weight"]).max())
        hidden = np.maximum(train_x @ params["fc1.weight"].T + params["fc1.bias"], 0)
        eh = max(_pow2_exponent(hidden.max(), 120), -7 + e1)
    else:
        e1, e2, eh = (int(frozen_scales[k]) for k in ["w1_exponent", "w2_exponent", "hidden_exponent"])
    sx, sw1, sw2, sh = 2.0**-7, 2.0**e1, 2.0**e2, 2.0**eh
    w1 = np.clip(np.rint(params["fc1.weight"] / sw1), -127, 127).astype(np.int64)
    w2 = np.clip(np.rint(params["fc2.weight"] / sw2), -127, 127).astype(np.int64)
    b1 = np.rint(params["fc1.bias"] / (sx*sw1)).astype(np.int64)
    b2 = np.rint(params["fc2.bias"] / (sh*sw2)).astype(np.int64)
    # Verify a conservative accumulator bound over all legal nonnegative int8 inputs.
    for name, weights, bias in [("hidden", w1, b1), ("output", w2, b2)]:
        if np.any(np.sum(abs(weights), axis=1)*127 + abs(bias) > 2**31-1):
            raise OverflowError(f"{name} layer cannot guarantee int32 accumulators")
    return {**config, "w1": w1.tolist(), "b1": b1.tolist(),
            "hidden_shift": eh - (-7 + e1), "w2": w2.tolist(), "b2": b2.tolist(),
            "scales": {"input_scale": sx, "input_exponent": -7,
                       "w1_scale": sw1, "w1_exponent": e1, "w2_scale": sw2, "w2_exponent": e2,
                       "hidden_scale": sh, "hidden_exponent": eh, "logit_scale": sh*sw2,
                       "weight_granularity": "per_layer_power_of_two", "zero_points": 0,
                       "rounding": "nearest_ties_even", "hidden_saturation": [0,127],
                       "weights_range": [-127,127], "output_tie_break": "lowest_class_index"}}


def predict_integer(model, features):
    x = np.asarray(features, dtype=np.int64)
    hidden_acc = x @ np.asarray(model["w1"], dtype=np.int64).T + np.asarray(model["b1"], dtype=np.int64)
    hidden = np.clip(round_shift_even(np.maximum(hidden_acc, 0), int(model["hidden_shift"])), 0, 127)
    logits = hidden @ np.asarray(model["w2"], dtype=np.int64).T + np.asarray(model["b2"], dtype=np.int64)
    if max(abs(hidden_acc).max(initial=0), abs(logits).max(initial=0)) > 2**31-1:
        raise OverflowError("integer batch accumulator overflow")
    return np.argmax(logits, axis=1), logits, hidden


def qat_finetune(float_model, initial_integer, train_q, train_y, val_q, val_y, epochs=180):
    """Optional contract-specific QAT with frozen power-of-two scales.

    Forward simulates quantized weights/biases/hidden activations; STE supplies
    gradients. Selection uses exported integer inference, not a packed CPU
    quantization operator. All evaluation remains on the validation split.
    """
    model = deepcopy(float_model)
    scale = initial_integer["scales"]
    s1, s2, sh = [float(scale[k]) for k in ("w1_scale", "w2_scale", "hidden_scale")]

    def fq(value, step, lower, upper):
        rounded = torch.clamp(torch.round(value/step), lower, upper)*step
        return value + (rounded-value).detach()

    def forward(x):
        w1 = fq(model.fc1.weight, s1, -127, 127)
        b1 = fq(model.fc1.bias, s1/128, -(2**31), 2**31-1)
        h = torch.relu(nn.functional.linear(x, w1, b1))
        h = fq(h, sh, 0, 127)
        return nn.functional.linear(h, fq(model.fc2.weight, s2, -127, 127),
                                     fq(model.fc2.bias, sh*s2, -(2**31), 2**31-1))

    optimizer = torch.optim.Adam(model.parameters(), lr=0.003)
    x = torch.tensor(train_q/128.0, dtype=torch.float32)
    y = torch.tensor(train_y, dtype=torch.long)
    counts = np.bincount(train_y, minlength=3)
    loss_fn = nn.CrossEntropyLoss(weight=torch.tensor(len(y)/(3*counts), dtype=torch.float32))
    best_model = deepcopy(model.state_dict())
    best_integer = initial_integer
    best_score = metrics(val_y, predict_integer(initial_integer, val_q)[0])["macro_f1"]
    best_epoch, curve = 0, []
    for epoch in range(epochs):
        optimizer.zero_grad()
        loss = loss_fn(forward(x), y)
        loss.backward()
        optimizer.step()
        if (epoch+1) % 5 == 0:
            quant = make_integer_model(model, train_q/128.0, initial_integer, frozen_scales=scale)
            m = metrics(val_y, predict_integer(quant, val_q)[0])
            curve.append({"epoch": epoch+1, "validation_macro_f1": m["macro_f1"], "loss": float(loss.item())})
            if m["macro_f1"] > best_score:
                best_score, best_epoch = m["macro_f1"], epoch+1
                best_model, best_integer = deepcopy(model.state_dict()), quant
    model.load_state_dict(best_model)
    return model, best_integer, {"method": "custom STE QAT matching exported integer contract",
                               "epochs_run": epochs, "selected_epoch": best_epoch, "learning_curve": curve}


def _record_metrics(y, pred, meta):
    ids = np.array([m["record_id"] for m in meta])
    # A record has only one true class, so a three-class macro-F1 per record
    # is misleading. Report recall/accuracy of that class and prediction counts.
    return [{"record_id": int(r), "true_class": int(y[ids == r][0]),
             "windows": int(np.sum(ids == r)),
             "accuracy": float(np.mean(y[ids == r] == pred[ids == r])),
             "predicted_class_counts": np.bincount(pred[ids == r], minlength=3).tolist()}
            for r in sorted(set(ids))]


def run_training(data_directory, artifact_directory, epochs=450, seed=7):
    started = time.time()
    data_directory, artifact_directory = Path(data_directory), Path(artifact_directory)
    reports, model_dir = artifact_directory/"reports", artifact_directory/"model"
    reports.mkdir(parents=True, exist_ok=True)
    if (reports/"test_evaluation.json").exists():
        raise RuntimeError("A held-out test report already exists. This pipeline will not silently tune/re-evaluate test data; preserve the existing experiment and use a new explicitly documented run directory if needed.")
    torch.set_num_threads(2)
    np.random.seed(seed)
    n = 1024
    raw_scale = fit_raw_scale(data_directory)
    train, ty, tm, train_clip = load_windows(data_directory, "train", raw_scale, n)
    val, vy, vm, val_clip = load_windows(data_directory, "validation", raw_scale, n)
    print(f"TRAIN {len(train)} windows; VALIDATION {len(val)} windows; test waveform not loaded", flush=True)
    train_spectrum, val_spectrum = float_spectrum(train), float_spectrum(val)
    bin_options, fisher = candidate_bins(train_spectrum, ty, n)
    # This is the predefined train-only frequency rule for future runs.
    # Other candidates remain illustrative validation comparisons only.
    selected_name = "train_fisher_separated"
    rows, stored = [], {}
    for name, bins in bin_options.items():
        print(f"frequency candidate {name}: {bins}", flush=True)
        tp, vp = int_powers(train, bins, n), int_powers(val, bins, n)
        shifts = feature_shifts(tp)
        tx, vx = float_features(tp, shifts), float_features(vp, shifts)
        mlp, history = fit_mlp(tx, ty, vx, vy, epochs=epochs, seed=seed)
        linear = LogisticRegression(C=10.0, max_iter=3000, class_weight="balanced", random_state=seed).fit(tx, ty)
        row = {"name": name, "bins": bins, "frequencies_hz": [b*12000/n for b in bins],
               "feature_shifts": shifts, "deployable": True,
               "mlp_validation": metrics(vy, predict_float(mlp, vx)),
               "linear_validation": metrics(vy, linear.predict(vx)),
               "training_history": history}
        rows.append(row)
        stored[name] = {"mlp": mlp, "linear": linear, "tp": tp, "vp": vp, "tx": tx, "vx": vx, "row": row}
        print(f"  MLP validation accuracy={row['mlp_validation']['accuracy']:.4f}, macroF1={row['mlp_validation']['macro_f1']:.4f}", flush=True)
    chosen = stored[selected_name]
    bins, shifts = chosen["row"]["bins"], chosen["row"]["feature_shifts"]

    # An offline-only band-energy baseline explicitly quantifies the tradeoff
    # between sixteen individual DFT bins and a richer multi-bin representation.
    edges = np.rint(np.linspace(1, n//2, 17)).astype(int)
    bt = np.stack([train_spectrum[:, a:b].sum(axis=1) for a,b in zip(edges[:-1], edges[1:])], axis=1)
    bv = np.stack([val_spectrum[:, a:b].sum(axis=1) for a,b in zip(edges[:-1], edges[1:])], axis=1)
    bs = feature_shifts(bt)
    band_mlp, band_history = fit_mlp(float_features(bt, bs), ty, float_features(bv, bs), vy, epochs=epochs, seed=seed)
    band_row = {"name": "uniform_band_energy_offline_only", "deployable": False,
                "reason": "sums many FFT bins; not the deployed sixteen-bin RTL datapath",
                "bin_edges": edges.tolist(), "feature_shifts": bs,
                "mlp_validation": metrics(vy, predict_float(band_mlp, float_features(bv, bs))),
                "training_history": band_history}
    rows.append(band_row)

    def rms(frames):
        x = frames.astype(np.float64)
        return np.sqrt(np.mean((x-x.mean(axis=1, keepdims=True))**2, axis=1))[:,None]
    rms_model = DecisionTreeClassifier(max_leaf_nodes=3, class_weight="balanced", random_state=seed).fit(rms(train), ty)
    rms_val = metrics(vy, rms_model.predict(rms(val)))
    base = {"schema_version": 1, "training_status": "trained_on_official_cwru",
            "n": n, "bins": bins, "input_shift": 5, "dft_shift": 20,
            "feature_shifts": shifts, "class_names": CLASS_NAMES,
            "sample_rate_hz": 12000, "raw_scale": raw_scale}
    integer = make_integer_model(chosen["mlp"], chosen["tx"], base)
    tq, vq = quantize_features(chosen["tp"], shifts), quantize_features(chosen["vp"], shifts)
    ptq_val = metrics(vy, predict_integer(integer, vq)[0])
    float_val = chosen["row"]["mlp_validation"]
    ptq_drop = float_val["accuracy"] - ptq_val["accuracy"]
    qat_report = None
    deployed_float = chosen["mlp"]
    if ptq_drop > 0.02:
        print(f"PTQ validation loss {100*ptq_drop:.2f} pp; attempting contract-specific QAT", flush=True)
        deployed_float, integer, qat_report = qat_finetune(chosen["mlp"], integer, tq, ty, vq, vy)
    deployed_val = metrics(vy, predict_integer(integer, vq)[0])
    validation_report = {"selected_frequency_candidate": selected_name,
        "selection_basis": "predefined train-only Fisher-separated centers chosen before model fitting; validation selects epochs only, other feature strategies are illustrative comparisons",
        "floating_mlp": float_val, "floating_mlp_quantized_feature_input": metrics(vy, predict_float(chosen["mlp"], vq/128.0)),
        "floating_frontend_floating_mlp": metrics(vy, predict_float(chosen["mlp"], float_features(val_spectrum[:, bins], shifts))),
        "ptq": ptq_val, "ptq_accuracy_drop_percentage_points": 100*ptq_drop,
        "deployed_integer": deployed_val, "deployed_accuracy_drop_percentage_points": 100*(float_val["accuracy"]-deployed_val["accuracy"]),
        "quantization_target_met_on_validation": (float_val["accuracy"]-deployed_val["accuracy"] <= 0.02),
        "qat": qat_report, "rms_three_leaf_threshold_baseline": rms_val,
        "linear": chosen["row"]["linear_validation"],
        "integer_vs_float_feature_mean_abs_error": float(np.mean(abs(chosen["vx"]-vq/128.0))),
        "feature_saturation_fraction_validation": float(np.mean(vq == 127))}
    audit = json.loads((data_directory/"manifest.json").read_text())
    integer["data_provenance"] = {"dataset": "CWRU official 12k DE, 36 records; no normal class",
        "source_page": audit["source_page"], "source_manifest_sha256": sha256((data_directory/"manifest.json").read_bytes()),
        "records": [{k: r[k] for k in ["record_id","split","mat_key","sha256","sample_rate_hz"]} for r in audit["records"]],
        "window_length": n, "window_stride": n, "split_before_windowing": True,
        "train_loads_hp": [0,1], "validation_loads_hp": [2], "test_loads_hp": [3],
        "feature_selection_records": [r.record_id for r in records() if r.split == "train"],
        "feature_scale_method": "power-of-two shift from training 99.5th percentile / 120, lower-bounded at zero",
        "selected_frequency_candidate": selected_name, "training_seed": seed,
        "quantization_method": "contract_specific_QAT" if qat_report and qat_report["selected_epoch"] > 0 else "PTQ"}
    integer["validation_metrics"] = validation_report
    export_model(integer, model_dir)
    torch.save(chosen["mlp"].state_dict(), model_dir/"float_model.pt")
    if qat_report:
        torch.save(deployed_float.state_dict(), model_dir/"qat_model.pt")
    np.savez_compressed(model_dir/"float_parameters.npz", **{k:v.detach().numpy() for k,v in chosen["mlp"].state_dict().items()})
    (reports/"frequency_comparison.json").write_text(json.dumps(rows, indent=2)+"\n")
    (reports/"validation.json").write_text(json.dumps(validation_report, indent=2)+"\n")
    (reports/"window_manifest_train_validation.json").write_text(json.dumps({"train":tm,"validation":vm}, indent=2)+"\n")
    (reports/"baseline_models.json").write_text(json.dumps({"linear_coef": chosen["linear"].coef_.tolist(),
        "linear_intercept": chosen["linear"].intercept_.tolist(),
        "rms_tree_thresholds": rms_model.tree_.threshold.tolist(),
        "rms_tree_children_left": rms_model.tree_.children_left.tolist(),
        "rms_tree_children_right": rms_model.tree_.children_right.tolist(),
        "rms_tree_class_values": rms_model.tree_.value.tolist()}, indent=2)+"\n")
    frozen_hash = sha256((model_dir/"model.json").read_bytes())
    (reports/"selection_frozen.json").write_text(json.dumps({"utc":datetime.now(timezone.utc).isoformat(),
        "model_sha256": frozen_hash, "test_waveform_loaded_by_training_before_freeze": False,
        "data_audit_note": "Downloader parsed all files for integrity/provenance before training; test waveform statistics were not used for model/feature/scale selection",
        "selected_candidate": selected_name, "epochs": epochs, "seed": seed}, indent=2)+"\n")
    print(f"MODEL FROZEN {frozen_hash}; now accessing held-out load-3 test once", flush=True)

    test, zy, zm, test_clip = load_windows(data_directory, "test", raw_scale, n)
    zp = int_powers(test, bins, n)
    zq, zx = quantize_features(zp, shifts), float_features(zp, shifts)
    pred, logits, hidden = predict_integer(integer, zq)
    float_pred = predict_float(chosen["mlp"], zx)
    zspec = float_spectrum(test)
    test_report = {"evaluation_count": 1, "evaluated_utc": datetime.now(timezone.utc).isoformat(),
        "frozen_model_sha256": frozen_hash, "test_used_for_model_selection": False,
        "rms_three_leaf_threshold_baseline": metrics(zy, rms_model.predict(rms(test))),
        "linear": metrics(zy, chosen["linear"].predict(zx)),
        "floating_mlp": metrics(zy, float_pred),
        "floating_frontend_floating_mlp": metrics(zy, predict_float(chosen["mlp"], float_features(zspec[:,bins], shifts))),
        "deployed_integer": metrics(zy, pred),
        "quantization_accuracy_drop_percentage_points": 100*(accuracy_score(zy,float_pred)-accuracy_score(zy,pred)),
        "per_record_integer": _record_metrics(zy, pred, zm),
        "limitation": "held-out operating load/records on the same public rig, not independently unseen bearing specimens or field validation",
        "physical_board_tested": False}
    (reports/"test_evaluation.json").write_text(json.dumps(test_report, indent=2)+"\n")
    (reports/"window_manifest_test.json").write_text(json.dumps(zm, indent=2)+"\n")
    np.savez_compressed(reports/"test_predictions.npz", labels=zy, predicted=pred, logits=logits,
                        features=zq, hidden=hidden, record_ids=np.array([m["record_id"] for m in zm]))
    (reports/"raw_input_clipping.json").write_text(json.dumps({"train":train_clip,"validation":val_clip,"test":test_clip},indent=2)+"\n")
    # Fixed validation windows make replay independent of the held-out test.
    replay_indices = [next(i for i,m in enumerate(vm) if m["record_id"] == record_id and m["window_index"] == 2)
                      for record_id in sorted({m["record_id"] for m in vm})]
    export_vectors(integer, val[replay_indices], [vm[i] for i in replay_indices], artifact_directory/"vectors")
    summary = {"schema_version":1,"seconds":time.time()-started,"python":platform.python_version(),
               "numpy":np.__version__,"torch":torch.__version__,"train_windows":len(train),
               "validation_windows":len(val),"test_windows":len(test),"selected_bins":bins,
               "hidden_shift":integer["hidden_shift"],"validation":validation_report,"test":test_report}
    (reports/"training_summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps({"selected":selected_name,"bins":bins,"validation_accuracy":deployed_val["accuracy"],
                      "test_accuracy":test_report["deployed_integer"]["accuracy"],
                      "test_macro_f1":test_report["deployed_integer"]["macro_f1"],
                      "test_quantization_drop_pp":test_report["quantization_accuracy_drop_percentage_points"],
                      "hidden_shift":integer["hidden_shift"],"seconds":summary["seconds"]},indent=2),flush=True)
    return summary
