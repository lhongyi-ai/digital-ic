"""Read frozen field evidence without opening captures or importing training."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from .project_profile import ROOT, resolve_path

SOURCE_FILES = {"field.py", "fixed.py", "training.py", "sensor.py", "export.py"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inspect_field(output, *, root=ROOT, verify=False):
    directory = resolve_path(output, root)
    freeze_path = directory / "frozen.json"
    result = {"output": str(directory), "read_only": True, "test_waveforms_opened": False,
              "training_or_evaluation_run": False, "errors": [], "warnings": []}
    if not freeze_path.is_file():
        result.update(status="not_frozen", valid=False)
        return result
    try:
        frozen = json.loads(freeze_path.read_text())
        frozen_hash = digest(freeze_path)
        result.update(freeze_sha256=frozen_hash, source_kind=frozen["source_kind"],
                      real_field_model_trained=frozen["source_kind"] == "physical_adxl345")
        manifest = json.loads((directory / "manifest.json").read_text())
        result["record_counts"] = dict(Counter(r["split"] for r in manifest["records"]))
        # Summarize metadata only. Never follow any manifest capture path.
        attempt_path, test_path = directory / "test_attempt.json", directory / "test.json"
        result["status"] = "evaluated" if test_path.exists() else "attempt_reserved_or_failed" if attempt_path.exists() else "frozen_unattempted"
        if attempt_path.exists():
            attempt = json.loads(attempt_path.read_text())
            result["test_attempt"] = attempt
            result["test_attempt_sha256"] = digest(attempt_path)
            if attempt.get("freeze_sha256") != frozen_hash:
                result["errors"].append("test attempt freeze hash mismatch")
        if test_path.exists():
            report = json.loads(test_path.read_text())
            result["test_result_sha256"] = digest(test_path)
            result["test_claim"] = report.get("claim")
            if not attempt_path.exists():
                result["errors"].append("test result exists without preserved attempt")
            if report.get("freeze_sha256") != frozen_hash:
                result["errors"].append("test result freeze hash mismatch")
            if report.get("model_sha256") != digest(directory / "model/model.json"):
                result["errors"].append("test result model hash mismatch")
            if report.get("source_kind") != frozen["source_kind"]:
                result["errors"].append("test result source kind mismatch")
            result["warnings"].append("Legacy test.json has no separately frozen result digest; its current hash and bindings are reported, not retrospective tamper-proofing.")
        if manifest.get("source_kind") != frozen["source_kind"]:
            result["errors"].append("manifest source kind mismatch")
        if verify:
            hashes = frozen["files"]
            if not {"manifest.json", "training.json", "model/model.json", "float_weights.json", "baselines.json"}.issubset(hashes):
                result["errors"].append("frozen artifact set is incomplete")
            checked = 0
            for name, expected in hashes.items():
                relative = Path(name)
                # Only the existing freeze format's model, vector and metadata files.
                # A forged freeze must not trick verification into opening held-out CSVs.
                allowed = (len(relative.parts) == 1 and name in {"manifest.json", "training.json", "float_weights.json", "baselines.json"}
                           or len(relative.parts) == 2 and relative.parts[0] in {"model", "vectors"}
                           and relative.suffix in {".json", ".jsonl", ".hex", ".svh"})
                path = directory / relative
                if not allowed or not path.resolve().is_relative_to(directory):
                    result["errors"].append(f"unsafe frozen artifact path: {name}")
                elif not path.is_file() or digest(path) != expected:
                    result["errors"].append(f"frozen artifact missing or hash changed: {name}")
                else:
                    checked += 1
            source_hashes = frozen["source_sha256"]
            if set(source_hashes) != SOURCE_FILES:
                result["errors"].append("frozen numerical/quality source set mismatch")
            for name in SOURCE_FILES:
                source = Path(root) / "src/vibfpga" / name
                if not source.is_file() or digest(source) != source_hashes.get(name):
                    result["errors"].append(f"frozen numerical/quality source changed: {name}")
            result.update(frozen_files_checked=checked, source_files_checked=len(SOURCE_FILES))
        result["valid"] = not result["errors"]
        result["verification"] = "passed" if verify and result["valid"] else "failed" if verify else "not_requested"
    except (OSError, ValueError, KeyError, TypeError) as error:
        result.update(status="invalid", valid=False)
        result["errors"].append(str(error))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", "verify"))
    parser.add_argument("--output", default="build/field_fixture/trained")
    args = parser.parse_args(argv)
    report = inspect_field(args.output, verify=args.action == "verify")
    print(json.dumps(report, indent=2))
    return 0 if report["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
