#!/usr/bin/env python3
"""Diagnostic upper bound on saved development scores, never a deploy threshold."""
import json
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score
from experiment_acoustic_v2 import dump, sha

ROOT = Path(__file__).resolve().parents[1]


def main():
    base = ROOT / "artifacts"
    names = ["acoustic-due-three-sections-v1", "acoustic-due-normal-reference-v1",
        "acoustic-due-short-time-v1", "acoustic-due-short-supervised-v1", "acoustic-due-mel-ae-v1"]
    sources = {n:json.loads((base/n/"results.json").read_text()) for n in names}
    original = sources[names[0]]
    rows = original["records"]
    findings = []
    for name, result in sources.items():
        entries = [(c["name"],f) for c in result["candidates"] for f in c["folds"]] if "candidates" in result else [(f.get("pooling","default"),f) for f in result.get("sections",result.get("folds",[]))]
        for model, f in entries:
            indices = f.get("validation_indices", [i for i,r in enumerate(rows) if r["section"]==f["section"]])
            labels = np.array([rows[i]["label"] for i in indices])
            scores = np.array(f.get("validation_scores",f.get("scores")))
            assert scores.shape == labels.shape and np.isfinite(scores).all()
            assert abs(roc_auc_score(labels,scores)-f["auc"])<1e-12
            normal = np.sort(scores[labels==0]); max_fp = int(np.ceil(.05*len(normal)))-1
            threshold = normal[-max_fp-1]
            predicted = scores>threshold
            fp = int(predicted[labels==0].sum()); tp = int(predicted[labels==1].sum())
            assert fp <= max_fp
            findings.append(dict(experiment=name,model=model,section=f["section"],auc=f["auc"],
                actual_recall=f["recall"],actual_fpr=f["fpr"],
                optimistic_development_recall=tp/int((labels==1).sum()),
                optimistic_tp=tp,optimistic_fp=fp,normal_count=len(normal),
                anomaly_count=int((labels==1).sum()),
                interpretation="uses evaluation labels: diagnostic only, NOT deployable or independently validated"))
    out = base/"acoustic-due-score-audit-v1"; out.mkdir(exist_ok=False)
    dump(out/"results.json",dict(findings=findings,source_sha256={n:sha(base/n/"results.json") for n in names},
        script_sha256=sha(Path(__file__)),final_test_accessed=False,
        limit="fixed scores only; no upper bound on other models or future data"))
    for f in findings:
        print(f['experiment'],f['model'],f['section'],f['optimistic_tp'],f['optimistic_fp'],flush=True)


if __name__ == "__main__": main()
