#!/usr/bin/env python3
"""Bounded short-time supervised development with whole-section holdouts."""
import json
from pathlib import Path
import joblib
import numpy as np
from sklearn.ensemble import ExtraTreesClassifier
from threadpoolctl import threadpool_limits
from evaluate_due_short_time import windows
from train_due_three_sections import ROOT, BASE
from experiment_acoustic_v2 import dump, sha
from diagnose_acoustic_v3 import metrics


def main():
    source = ROOT / "artifacts/acoustic-due-three-sections-v1/results.json"
    old = json.loads(source.read_text()); rows = old["records"]
    out = ROOT / "artifacts/acoustic-due-short-supervised-v1"
    out.mkdir(exist_ok=False)
    dump(out / "protocol.json", {
        "source_results_sha256": sha(source), "script_sha256": sha(Path(__file__)),
        "feature_source_sha256": sha(ROOT / "scripts/evaluate_due_short_time.py"),
        "feature": "32 log power bands, 5 consecutive spectra, 192 ms",
        "model": "ExtraTrees 200 trees, max_depth 12, min_samples_leaf 8, max_features .5, seed 71",
        "sampling": "every eighth context for fit and evaluation alike",
        "pooling": ["mean", "top10"], "threshold": "maximum source-section normal calibration score",
        "split": "existing whole-section 3-fold indices unchanged",
        "warning": "record labels assigned to contexts; localized fault context labels may be noisy",
        "final_test_opened": False})
    features = []
    for row in rows:
        path = BASE / "pcm" / (Path(row["name"]).stem + ".npy")
        assert sha(path) == old["pcm_sha256"][str(path.relative_to(ROOT))]
        features.append(windows(np.load(path, allow_pickle=False))[::8].astype(np.float32))
    x = np.stack(features); y = np.array([r["label"] for r in rows])
    results = []
    for fold in old["candidates"][0]["folds"]:
        fit, cal, val = [np.array(fold[k]) for k in ("fit_indices", "calibration_indices", "validation_indices")]
        held = fold["section"]
        assert all(rows[i]["section"] != held for i in np.r_[fit,cal])
        assert all(rows[i]["section"] == held for i in val)
        model = ExtraTreesClassifier(n_estimators=200, max_depth=12, min_samples_leaf=8,
            max_features=.5, random_state=71, n_jobs=2)
        model.fit(x[fit].reshape(-1,160), np.repeat(y[fit], x.shape[1]))
        path = out / f"hold-{held}.joblib"; joblib.dump(model,path)
        restored = joblib.load(path)
        cs = model.predict_proba(x[cal].reshape(-1,160))[:,1].reshape(len(cal),-1)
        vs = model.predict_proba(x[val].reshape(-1,160))[:,1].reshape(len(val),-1)
        np.testing.assert_allclose(vs, restored.predict_proba(x[val].reshape(-1,160))[:,1].reshape(len(val),-1),rtol=0,atol=1e-14)
        for pooling in ("mean", "top10"):
            def pool(z):
                return z.mean(1) if pooling=="mean" else np.sort(z,axis=1)[:,-int(np.ceil(z.shape[1]*.1)):].mean(1)
            scores = pool(vs); calibration = pool(cs)
            limit = float(calibration[y[cal]==0].max())
            result = metrics(y[val],scores,limit)
            result.update(section=held,pooling=pooling,scores=scores.tolist(),calibration_scores=calibration.tolist(),
                gate_passed=result["recall"]>.9 and result["fpr"]<.05 and result["auc"]>=.9)
            results.append(result)
            print(held,pooling,result["recall"],result["fpr"],result["auc"],flush=True)
        dump(out/"partial-results.json",results)
    dump(out/"results.json",{"folds":results,"all_passed":any(all(r["gate_passed"] for r in results if r["pooling"]==p) for p in ("mean","top10"))})


if __name__ == "__main__":
    with threadpool_limits(limits=2):
        main()
