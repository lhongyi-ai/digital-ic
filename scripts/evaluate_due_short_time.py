#!/usr/bin/env python3
"""Short-time normal Gaussian diagnostic using the existing commissioning split."""
from pathlib import Path
import json
import joblib
import numpy as np
from sklearn.covariance import LedoitWolf
from threadpoolctl import threadpool_limits
from train_due_three_sections import ROOT, BASE
from experiment_acoustic_v2 import dump, sha
from diagnose_acoustic_v3 import metrics


def windows(pcm):
    frames = np.lib.stride_tricks.sliding_window_view(pcm.astype(np.float64), 1024)[::512]
    power = np.abs(np.fft.rfft(frames * np.hanning(1024), axis=1))[:, 1:] ** 2
    bands = np.log(np.maximum(power.reshape(len(power), 32, 16).sum(2), 1e-20))
    # Five consecutive spectra span 192 ms, within this recording only.
    return np.stack([bands[i:i+5].reshape(-1) for i in range(len(bands)-4)])


def pooled(scores):
    return {"mean": float(scores.mean()), "top10": float(np.sort(scores)[-int(np.ceil(len(scores)*.1)):].mean())}


def main():
    previous = ROOT / "artifacts/acoustic-due-normal-reference-v1/results.json"
    prior = json.loads(previous.read_text())
    out = ROOT / "artifacts/acoustic-due-short-time-v1"
    out.mkdir(exist_ok=False)
    dump(out / "protocol.json", {
        "task": "normal-reference commissioning, not zero-shot",
        "input_sha256": sha(previous), "source_sha256": sha(Path(__file__)),
        "features": "32 uniform log power bands, five consecutive frames, 192 ms",
        "fit": "existing 150 source plus 3 target normal reference files; every fourth context",
        "model": "source-reference standardization then LedoitWolf covariance",
        "pooling": ["mean", "top10"], "threshold": "maximum of 50 source-normal calibration scores",
        "evaluation": "same 400 development records per section, unchanged",
        "final_test_opened": False,
        "gate": "recall > .90, fpr < .05, auc >= .90 for all sections"})
    def load(name):
        path = BASE / "pcm" / (Path(name).stem + ".npy")
        assert sha(path) == prior["pcm_sha256"][str(path.relative_to(ROOT))]
        pcm = np.load(path, allow_pickle=False)
        assert pcm.dtype == np.int16 and pcm.shape == (160000,)
        return windows(pcm)
    results = []
    for section in prior["sections"]:
        train = np.concatenate([load(n)[::4] for n in section["reference"]])
        center = train.mean(0); scale = np.maximum(train.std(0), 1e-6)
        model = LedoitWolf().fit((train-center)/scale)
        path = out / ("section-" + section["section"] + ".joblib")
        joblib.dump(dict(model=model, center=center, scale=scale), path)
        restored = joblib.load(path)
        probe = (train[:20]-center)/scale
        np.testing.assert_array_equal(model.mahalanobis(probe), restored["model"].mahalanobis(probe))
        def score(name):
            return pooled(model.mahalanobis((load(name)-center)/scale))
        cal = [score(n) for n in section["calibration"]]
        val = [score(r["name"]) for r in section["records"]]
        y = np.array([r["label"] for r in section["records"]])
        for pooling in ("mean", "top10"):
            scores = np.array([s[pooling] for s in val])
            limit = max(s[pooling] for s in cal)
            result = metrics(y, scores, limit)
            result.update(section=section["section"], pooling=pooling,
                scores=scores.tolist(), calibration_scores=[s[pooling] for s in cal],
                domains={d:metrics(y[m], scores[m], limit) for d in ("source", "target")
                    for m in [np.array([r["domain"] == d for r in section["records"]])]},
                gate_passed=result["recall"] > .9 and result["fpr"] < .05 and result["auc"] >= .9)
            results.append(result)
            print(section["section"], pooling, result["recall"], result["fpr"], result["auc"], flush=True)
        dump(out / "partial-results.json", results)
    dump(out / "results.json", {"folds": results,
        "all_passed": any(all(r["gate_passed"] for r in results if r["pooling"]==p) for p in ("mean","top10")),
        "reload_probe_exact": True})


if __name__ == "__main__":
    with threadpool_limits(limits=2):
        main()
