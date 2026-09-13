#!/usr/bin/env python3
"""Generate reproducible synthetic pipeline stimuli, NOT measured training data."""
import argparse
from pathlib import Path
import numpy as np
from vibfpga.field import CLASS_NAMES, CLOCK, FIXTURE, ODR, digest, write_json


def generate(destination, windows=4):
    destination = Path(destination).resolve()
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("fixture destination must be new/empty")
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    rng = np.random.default_rng(250908)
    for split in ("train", "validation", "test"):
        for label in range(3):
            for rep in range(2 if split == "train" else 1):
                name = f"{split}_{label}_{rep}"
                t = np.arange(windows*256)
                raw = rng.normal(0, 2, len(t)) + 240
                if label:
                    frequency = (18 if label == 1 else 43) + rng.uniform(-0.25, 0.25)
                    raw += (110 + 5*rep)*np.sin(2*np.pi*frequency*t/256 + rng.uniform(0, 6.28))
                    raw += 20*np.cos(2*np.pi*2*frequency*t/256)
                path = destination / f"{name}.csv"
                np.savetxt(path, np.column_stack((t, (t*(CLOCK//ODR)+100) % 2**32, np.rint(raw))),
                           fmt="%d", delimiter=",", header="sample_index,service_cycle,z_raw", comments="")
                records.append({"path": path.name, "record_id": name, "label": label, "split": split,
                                "session_id": name, "installation_id": f"synthetic_{split}", "sha256": digest(path)})
    manifest = {"schema_version": 1, "source_kind": FIXTURE, "odr_hz": ODR, "clock_hz": CLOCK,
                "axis": "z", "class_names": CLASS_NAMES,
                "apparatus": "mathematical sine/noise fixture; no physical apparatus or fault evidence",
                "records": records}
    write_json(destination / "manifest.json", manifest)
    return destination / "manifest.json"


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=Path("build/field_fixture/data"))
    p.add_argument("--windows", type=int, default=4)
    a = p.parse_args()
    if a.windows < 1:
        p.error("windows must be positive")
    print(generate(a.output, a.windows))
