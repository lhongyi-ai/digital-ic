#!/usr/bin/env python3
"""Run only the nine prespecified train/validation comparisons in protocol.md."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import sys
import time

import numpy as np
import torch
from torch import nn

EXPERIMENT = Path(__file__).resolve().parent
ROOT = EXPERIMENT.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from vibfpga import dataset
from vibfpga.fixed import quantize_features
from vibfpga.training import float_features, int_powers, make_integer_model, metrics, predict_float, predict_integer

CONFIGS = {"A": {"hidden": 16, "lr": .025, "weight_decay": 1e-5},
           "B": {"hidden": 16, "lr": .01, "weight_decay": 1e-3},
           "C": {"hidden": 32, "lr": .01, "weight_decay": 1e-3}}
SEEDS = [7, 17, 29]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def inventory():
    # Stat only: never read any existing test waveform/prediction/report. The
    # runner's only write destinations are under EXPERIMENT.
    paths = [path for group in ("artifacts/model", "artifacts/model_neighbor", "artifacts/reports")
             for path in (ROOT / group).rglob("*") if path.is_file()]
    return {str(path.relative_to(ROOT)): [path.stat().st_size, path.stat().st_mtime_ns] for path in paths}


class Network(nn.Module):
    def __init__(self, hidden):
        super().__init__()
        self.fc1, self.fc2 = nn.Linear(16, hidden), nn.Linear(hidden, 3)

    def forward(self, x):
        return self.fc2(torch.relu(self.fc1(x)))


def train_one(settings, seed, tx, ty, vx, vy):
    torch.manual_seed(seed)
    network = Network(settings["hidden"])
    optimizer = torch.optim.AdamW(network.parameters(), lr=settings["lr"], weight_decay=settings["weight_decay"])
    counts = np.bincount(ty, minlength=3)
    loss_fn = nn.CrossEntropyLoss(weight=torch.tensor(len(ty) / (3 * counts), dtype=torch.float32))
    inputs, labels = torch.tensor(tx, dtype=torch.float32), torch.tensor(ty, dtype=torch.long)
    best, best_score, best_epoch = None, (-1.0, -float("inf")), None
    history = []
    for epoch in range(1, 451):
        network.train()
        optimizer.zero_grad()
        loss = loss_fn(network(inputs), labels)
        loss.backward()
        optimizer.step()
        if epoch % 10 == 0:
            val = metrics(vy, predict_float(network, vx))
            measured_loss = float(loss.detach().item())
            score = (val["macro_f1"], -measured_loss)
            history.append({"epoch": epoch, "train_loss": measured_loss,
                            "validation_macro_f1": val["macro_f1"], "validation_accuracy": val["accuracy"]})
            if score > best_score:
                best, best_score, best_epoch = deepcopy(network.state_dict()), score, epoch
    network.load_state_dict(best)
    network.eval()
    return network, best_epoch, history


def summary(values):
    return {"mean": float(np.mean(values)), "sample_std_ddof1": float(np.std(values, ddof=1)),
            "minimum": float(np.min(values)), "maximum": float(np.max(values)), "seeds": len(values)}


def main():
    # Simple one-experiment guard; all configuration is fixed in this source.
    (EXPERIMENT / "runs").mkdir(exist_ok=False)
    started = time.monotonic()
    protected = inventory()
    base_path = ROOT / "artifacts/model_neighbor/model.json"
    base = json.loads(base_path.read_text())
    assert base["feature_mode"] == "neighbor3_energy" and base["n"] == 1024
    assert base["input_shift"] == 5 and base["dft_shift"] == 20
    assert base["dft_bins"] == [k + d for k in base["bins"] for d in (-1, 0, 1)]
    manifest_path = ROOT / "data/cwru/manifest.json"
    manifest = json.loads(manifest_path.read_text())
    used = [row for row in manifest["records"] if row["split"] in {"train", "validation"}]
    snapshots = {}
    for path in [base_path, Path(__file__), EXPERIMENT / "protocol.md"] + [ROOT / "src/vibfpga" / name
                  for name in ("fixed.py", "training.py", "dataset.py")]:
        target = EXPERIMENT / "snapshot" / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        snapshots[str(path.relative_to(ROOT))] = sha(target)
    write(EXPERIMENT / "snapshot/manifest_train_validation.json", {"records": used})
    write(EXPERIMENT / "pre_run.json", {
        "started_utc": datetime.now(timezone.utc).isoformat(), "protocol_sha256": sha(EXPERIMENT / "protocol.md"),
        "model_sha256": sha(base_path), "manifest_sha256": sha(manifest_path), "source_model_snapshot_sha256": snapshots,
        "configurations": CONFIGS, "seeds": SEEDS, "epochs": 450, "validation_every_epochs": 10,
        "python": platform.python_version(), "platform": platform.platform(),
        "libraries": {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "torch", "scikit-learn")},
        "existing_model_report_stat_inventory": protected,
        "test_waveform_or_prediction_access_permitted": False,
        "scope": "Validation exploration only; no deployment and no new test result."})

    accesses = []
    original_loader = dataset.load_record

    def train_validation_only(directory, record):
        if record.split not in {"train", "validation"} or record.load_hp not in {0, 1, 2}:
            raise ValueError("Test waveform access is forbidden in this experiment")
        path = Path(directory) / f"{record.record_id}.mat"
        accesses.append({"record_id": record.record_id, "split": record.split, "sha256": sha(path)})
        return original_loader(directory, record)

    dataset.load_record = train_validation_only
    train, ty, tm, tc = dataset.load_windows(ROOT / "data/cwru", "train", base["raw_scale"], 1024)
    val, vy, vm, vc = dataset.load_windows(ROOT / "data/cwru", "validation", base["raw_scale"], 1024)
    assert len(train) == 2134 and len(val) == 1066 and len(accesses) == 27
    powers = [int_powers(frames, base["dft_bins"], 1024).reshape(-1, 16, 3).sum(axis=2, dtype=np.int64)
              for frames in (train, val)]
    tx, vx = [float_features(values, base["feature_shifts"]) for values in powers]
    val_q = quantize_features(powers[1], base["feature_shifts"])
    write(EXPERIMENT / "data_access.json", {"mat_files_read": accesses, "test_waveforms_read": False,
          "test_predictions_read": False, "train_windows": len(train), "validation_windows": len(val),
          "train_window_metadata": tm, "validation_window_metadata": vm,
          "raw_conversion_train": tc, "raw_conversion_validation": vc})
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    run_results = []
    for name, settings in CONFIGS.items():
        for seed in SEEDS:
            network, epoch, history = train_one(settings, seed, tx, ty, vx, vy)
            folder = EXPERIMENT / "runs" / f"{name}_seed{seed}"
            folder.mkdir()
            torch.save(network.state_dict(), folder / "checkpoint.pt")
            np.savez_compressed(folder / "float_parameters.npz", **{
                key: value.detach().cpu().numpy() for key, value in network.state_dict().items()})
            result = {"configuration": name, "settings": settings, "seed": seed, "selected_epoch": epoch,
                      "float_validation": metrics(vy, predict_float(network, vx)), "history": history,
                      "checkpoint_sha256": sha(folder / "checkpoint.pt"),
                      "float_parameters_sha256": sha(folder / "float_parameters.npz")}
            if name in {"A", "B"}:
                integer = make_integer_model(network, tx, {**base,
                    "training_status": "experimental_train_validation_only",
                    "deployment_status": "not deployed; experiment-local candidate only"})
                # Do not copy historical validation metrics into this new candidate.
                integer.pop("validation_metrics", None)
                result["integer_validation"] = metrics(vy, predict_integer(integer, val_q)[0])
                result["PTQ_accuracy_drop_percentage_points"] = 100 * (
                    result["float_validation"]["accuracy"] - result["integer_validation"]["accuracy"])
                result["integer_minus_float_macro_f1_percentage_points"] = 100 * (
                    result["integer_validation"]["macro_f1"] - result["float_validation"]["macro_f1"])
                result["PTQ_scales"] = integer["scales"]
                write(folder / "integer_candidate.json", integer)
            else:
                result["integer_validation"] = None
                result["scope"] = "FP32 only; 32-hidden PTQ and RTL not implemented/evaluated."
            write(folder / "result.json", result)
            run_results.append(result)
            print(f"{name}/seed{seed}: epoch={epoch}, float val macro-F1={result['float_validation']['macro_f1']:.6f}" +
                  (f", INT8={result['integer_validation']['macro_f1']:.6f}" if result["integer_validation"] else " (FP32 only)"), flush=True)
    aggregated = {}
    for name in CONFIGS:
        group = [row for row in run_results if row["configuration"] == name]
        row = {"settings": CONFIGS[name], "float_validation_macro_f1": summary([r["float_validation"]["macro_f1"] for r in group]),
               "float_validation_accuracy": summary([r["float_validation"]["accuracy"] for r in group])}
        if name in {"A", "B"}:
            row["integer_validation_macro_f1"] = summary([r["integer_validation"]["macro_f1"] for r in group])
            row["integer_validation_accuracy"] = summary([r["integer_validation"]["accuracy"] for r in group])
            row["PTQ_accuracy_drop_percentage_points"] = summary([r["PTQ_accuracy_drop_percentage_points"] for r in group])
        aggregated[name] = row
    a7 = run_results[0]
    reproduction = {"float_metrics_equal": a7["float_validation"] == base["validation_metrics"]["floating_mlp"],
                    "integer_metrics_equal": a7["integer_validation"] == base["validation_metrics"]["deployed_integer"]}
    unchanged = inventory() == protected
    assert unchanged, "An existing model/report file changed during this experiment"
    assert all(sha(ROOT / name) == checksum for name, checksum in snapshots.items())
    result = {"status": "completed", "protocol_sha256": sha(EXPERIMENT / "protocol.md"),
              "frozen_frontend_model_sha256": sha(base_path), "configurations": aggregated, "runs": run_results,
              "A_seed7_reproduces_frozen_validation_metrics": reproduction,
              "existing_models_reports_stat_unchanged": unchanged, "test_waveforms_read": False,
              "test_predictions_read": False, "deployed_model_changed": False,
              "seconds": time.monotonic() - started,
              "scope": "Nine prespecified train/validation-only runs. No new test, external generalization, RTL fit or hardware claims.",
              "causal_limit": "A/C changes width AND optimizer settings; only B/C holds optimizer settings fixed."}
    write(EXPERIMENT / "results.json", result)
    write(EXPERIMENT / "output_hashes.json", {str(path.relative_to(EXPERIMENT)): sha(path)
          for path in sorted(EXPERIMENT.rglob("*")) if path.is_file()})
    print(json.dumps({"summary": aggregated, "reproduction": reproduction, "seconds": result["seconds"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
