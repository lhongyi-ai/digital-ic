#!/usr/bin/env python3
"""Fail before an expensive release when its existing fixture/history is absent."""
import json
from pathlib import Path
import re
import sys

from build_support import sha, require_unchanged

ROOT = Path(__file__).resolve().parents[1]


def check(root=ROOT, *, historical=False):
    failures = []
    frozen_path = root / "build/field_fixture/trained/frozen.json"
    area_path = root / "build/field_area_experiments/report.json"
    for path in ((frozen_path, area_path) if historical else (frozen_path,)):
        if not path.is_file():
            failures.append(f"Missing {path.relative_to(root)}")
    if frozen_path.is_file():
        try:
            frozen = json.loads(frozen_path.read_text())
            require_unchanged({str(frozen_path.parent/name): checksum for name, checksum in frozen["files"].items()})
            require_unchanged({str(root/"src/vibfpga"/name): checksum for name, checksum in frozen["source_sha256"].items()})
            for name in ("model/model.json", "training.json", "test.json"):
                if not (frozen_path.parent/name).is_file():
                    failures.append(f"Missing field fixture {name}")
        except (KeyError, ValueError, OSError, RuntimeError) as error:
            failures.append(f"Field fixture is incomplete or changed: {error}")
    if historical and area_path.is_file():
        try:
            area = json.loads(area_path.read_text())
            if area["status"] != "completed_no_fit" or not area["production_source_files_unchanged"]:
                failures.append("Existing field area experiment report is not a completed source-bound result")
            require_unchanged({str(root/name): checksum for name, checksum in area["production_source_sha256"].items()})
        except (KeyError, ValueError, OSError, RuntimeError) as error:
            failures.append(f"Existing field area evidence does not bind current production inputs: {error}")
    board = root / "build/field_board_l4"
    if historical and not (board/"report.json").is_file():
        log = board/"place_route.log"
        if not log.is_file() or not re.search(r"ERROR:.*ICESTORM_LCs", log.read_text()):
            failures.append("Missing existing field L4 resource-limit log (or successful field L4 report)")
    if failures:
        raise RuntimeError("Release prerequisites are not ready:\n- " + "\n- ".join(failures) +
            "\nSee docs/workflow-efficiency.md and docs/field-training.md. "
            "Release does not generate training fixtures or repeat historical area experiments automatically.")
    return {"ready": True, "preexisting_dependencies": [str(frozen_path)] + ([str(area_path), str(board)] if historical else []),
            "scope": "field fixture is verified; current release reruns offline checks and L1 build; historical L4/area experiments are excluded"}


if __name__ == "__main__":
    try:
        print(json.dumps(check(), indent=2))
    except RuntimeError as error:
        print(error, file=sys.stderr)
        raise SystemExit(2)
