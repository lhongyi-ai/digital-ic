#!/usr/bin/env python3
"""Fixed normal-reference diagnostic; not zero-shot machine generalization."""
from pathlib import Path
import hashlib
import json

import joblib
import numpy as np
from sklearn.neighbors import NearestNeighbors

from train_due_three_sections import BASE, ROOT, feature
from diagnose_acoustic_v3 import metrics
from experiment_acoustic_v2 import dump, sha


def main():
    plan_path = BASE / "normal-reference-plan.json"
    plan = json.loads(plan_path.read_text())
    receipt = json.loads((BASE / "normal-reference-download.json").read_text())
    assert receipt["passed"] and receipt["plan_sha256"] == sha(plan_path)
    previous = ROOT / "artifacts/acoustic-due-three-sections-v1"
    prior = json.loads((previous / "results.json").read_text())
    out = ROOT / "artifacts/acoustic-due-normal-reference-v1"
    out.mkdir(exist_ok=False)
    dump(out / "protocol.json", {
        "task": "normal-reference commissioning diagnostic, NOT zero-shot",
        "feature": "existing 320-dimensional 64-band summaries",
        "fit": "150 source normals and 3 target normals per section",
        "calibration": "remaining 50 source normals; maximum score threshold",
        "split": "SHA256 due-reference-v1:name, before looking at audio scores",
        "models": "mean distance to 3 nearest normal references, standardized by source-fit std",
        "limitations": "first 200 source files may not cover all operating conditions; only 3 target references; threshold has no target-domain FPR guarantee",
        "evaluation": "all 400 previously used development recordings per section, domain results separate",
        "gate": "recall > .90, fpr < .05, auc >= .90 for each section; no final test claim",
        "final_sections_03_04_05_opened": False,
        "inputs": {str(plan_path): sha(plan_path), str(previous / "results.json"): sha(previous / "results.json")},
        "source_sha256": {str(Path(__file__)): sha(Path(__file__)),
            str(ROOT / "scripts/train_due_three_sections.py"): sha(ROOT / "scripts/train_due_three_sections.py")}})
    # Recompute evaluation features from verified PCM; cached row alignment is not assumed.
    seen = set()
    hashes = {}

    def load(row, expected_plan=None):
        stem = Path(row["name"]).stem
        path = BASE / "pcm" / f"{stem}.npy"
        meta = json.loads((BASE / "receipts" / f"{stem}.json").read_text())
        digest = sha(path)
        assert meta["name"] == row["name"] and meta["npy_sha256"] == digest
        if expected_plan is not None:
            assert meta["plan_sha256"] == expected_plan
        relative = str(path.relative_to(ROOT))
        if relative in prior["pcm_sha256"]:
            assert digest == prior["pcm_sha256"][relative]
        assert digest not in seen, "duplicate PCM across reference/evaluation"
        seen.add(digest); hashes[str(path.relative_to(ROOT))] = digest
        pcm = np.load(path, allow_pickle=False)
        assert pcm.shape == (160000,) and pcm.dtype == np.int16
        return feature(pcm)

    results = []
    for section in ("00", "01", "02"):
        source = sorted([r for r in plan["records"] if r["section"] == section and "_source_" in r["name"]],
            key=lambda r: hashlib.sha256(("due-reference-v1:" + r["name"]).encode()).hexdigest())
        target = [r for r in plan["records"] if r["section"] == section and "_target_" in r["name"]]
        assert len(source) == 200 and len(target) == 3
        reference = source[:150] + target
        calibration = source[150:]
        train = np.stack([load(r, sha(plan_path)) for r in reference])
        cal = np.stack([load(r, sha(plan_path)) for r in calibration])
        center = train[:150].mean(0)
        scale = np.maximum(train[:150].std(0), 1e-6)
        model = NearestNeighbors(n_neighbors=3).fit((train - center) / scale)
        score = lambda x: model.kneighbors((x - center) / scale)[0].mean(1)
        limit = float(score(cal).max())
        rows = [r for r in prior["records"] if r["section"] == section]
        x = np.stack([load(r, sha(BASE / "expansion-plan.json")) for r in rows])
        y = np.array([r["label"] for r in rows])
        scores = score(x)
        result = metrics(y, scores, limit)
        result.update(section=section, domains={})
        for domain in ("source", "target"):
            mask = np.array([r["domain"] == domain for r in rows])
            result["domains"][domain] = metrics(y[mask], scores[mask], limit)
        result.update(gate_passed=result["recall"] > .9 and result["fpr"] < .05 and result["auc"] >= .9,
            reference=[r["name"] for r in reference], calibration=[r["name"] for r in calibration],
            records=rows, scores=scores.tolist(), calibration_scores=score(cal).tolist())
        path = out / f"section-{section}.joblib"
        joblib.dump(dict(model=model, center=center, scale=scale, threshold=limit), path)
        reload = joblib.load(path)
        np.testing.assert_array_equal(scores, reload["model"].kneighbors((x-reload["center"])/reload["scale"])[0].mean(1))
        results.append(result)
        dump(out / f"section-{section}.json", result)
        print(section, result["recall"], result["fpr"], result["auc"], flush=True)
    dump(out / "results.json", {"sections": results, "all_passed": all(r["gate_passed"] for r in results),
        "pcm_sha256": hashes, "reload_exact": True, "exact_duplicate_check": "1809 unique PCM files; near duplicates not yet excluded"})


if __name__ == "__main__":
    main()
