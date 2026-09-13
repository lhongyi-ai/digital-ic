#!/usr/bin/env python3
"""Minimal supervised DUE 00/01 whole-section development experiment."""
from pathlib import Path
import json

import joblib
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.ensemble import ExtraTreesClassifier

from audit_multimachine import manual_metrics
from diagnose_acoustic_v3 import metrics
from experiment_acoustic_v2 import dump, sha

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/mimii-due-source-review"


def feature(pcm):
    frames = np.lib.stride_tricks.sliding_window_view(pcm.astype(np.float64), 1024)[::512]
    power = np.abs(np.fft.rfft(frames * np.hanning(1024), axis=1))[:, 1:] ** 2
    bands = np.log(np.maximum(power.reshape(len(power), 64, 8).sum(2), 1e-20))
    # ponytail: five robust summaries retain level, spread, extremes, and change.
    return np.concatenate((bands.mean(0), bands.std(0),
        np.quantile(bands, .1, axis=0), np.quantile(bands, .9, axis=0),
        np.abs(np.diff(bands, axis=0)).mean(0)))


def threshold(scores, labels):
    normal = np.sort(scores[labels == 0])
    return float(normal[-1])  # 40 calibration normals: strict <5% means at most one; use zero.


def main():
    out = ROOT / "artifacts/acoustic-due-minimal-v1"
    out.mkdir(exist_ok=False)
    plan_path = BASE / "expansion-plan.json"
    plan = json.loads(plan_path.read_text())
    receipt = json.loads((BASE / "development-download.json").read_text())
    assert receipt["passed"] and receipt["plan_sha256"] == sha(plan_path)
    rows = [row for row in plan["records"] if row["role"] in ("fit", "calibration")]
    assert len(rows) == 800 and {row["section"] for row in rows} == {"00", "01"}

    existing = set()
    old = ROOT / "artifacts/acoustic-multimachine-v1/frozen.json"
    if old.exists():
        existing = set(json.loads(old.read_text())["pcm_sha256"].values())
    features, hashes = [], {}
    for index, row in enumerate(rows, 1):
        stem = Path(row["name"]).stem
        path = BASE / "pcm" / f"{stem}.npy"
        meta = json.loads((BASE / "receipts" / f"{stem}.json").read_text())
        digest = sha(path)
        assert digest == meta["npy_sha256"] and digest not in existing and digest not in hashes.values()
        pcm = np.load(path, allow_pickle=False)
        assert pcm.shape == (160000,) and pcm.dtype == np.int16
        features.append(feature(pcm)); hashes[str(path.relative_to(ROOT))] = digest
        if index % 200 == 0:
            print(f"features {index}/800", flush=True)
    x = np.stack(features); np.save(out / "features.npy", x)
    y = np.array([row["label"] for row in rows])
    section = np.array([row["section"] for row in rows])
    role = np.array([row["role"] for row in rows])
    candidates = []
    for name, estimator in (
        ("rbf", SVC(C=10, gamma="scale", probability=False)),
        ("trees", ExtraTreesClassifier(n_estimators=400, min_samples_leaf=2,
            max_features=.5, random_state=71, n_jobs=2)),
    ):
        folds = []
        for held in ("00", "01"):
            fit = np.flatnonzero((section != held) & (role == "fit"))
            cal = np.flatnonzero((section != held) & (role == "calibration"))
            val = np.flatnonzero(section == held)
            assert (len(fit), len(cal), len(val)) == (320, 80, 400)
            model = make_pipeline(StandardScaler(), estimator)
            model.fit(x[fit], y[fit])
            score = (model.decision_function if name == "rbf" else
                lambda z: model.predict_proba(z)[:, 1])
            cal_score, val_score = score(x[cal]), score(x[val])
            limit = threshold(cal_score, y[cal])
            result = metrics(y[val], val_score, limit)
            check = manual_metrics(y[val], val_score, limit)
            assert check["tp"] == result["confusion_matrix"][1][1]
            assert check["fp"] == result["confusion_matrix"][0][1]
            result.update(section=held, fit_indices=fit.tolist(), calibration_indices=cal.tolist(),
                validation_indices=val.tolist(), calibration_scores=cal_score.tolist(),
                validation_scores=val_score.tolist(), gate_passed=result["recall"] > .9 and
                result["fpr"] < .05 and result["auc"] >= .9)
            joblib.dump(model, out / f"{name}-hold{held}.joblib")
            folds.append(result)
            print(name, held, result["recall"], result["fpr"], result["auc"], flush=True)
        candidates.append({"name": name, "folds": folds,
            "all_passed": all(item["gate_passed"] for item in folds)})
    dump(out / "results.json", {"candidates": candidates,
        "all_passed": any(item["all_passed"] for item in candidates),
        "records": [{key: row[key] for key in ("name", "section", "domain", "role", "label")}
            for row in rows], "pcm_sha256": hashes, "reserved_section_02_opened": False})
    dump(out / "protocol.json", {"plan_sha256": sha(plan_path),
        "feature": "64-band log energy mean/std/p10/p90/mean absolute delta",
        "models": ["rbf", "trees"], "fold": "hold out section 00 or 01 in full",
        "threshold": "maximum source-section normal calibration score",
        "gate": "recall > .90, fpr < .05, auc >= .90 on both sections",
        "test": "DUE section 02 unopened", "source_sha256": sha(Path(__file__))})


if __name__ == "__main__":
    main()
