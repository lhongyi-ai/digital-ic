#!/usr/bin/env python3
"""Train/freeze and separately evaluate the ADXL345-specific field model."""
import argparse
import json
from vibfpga.field import evaluate, train

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("train", "evaluate"))
    p.add_argument("--manifest")
    p.add_argument("--output", required=True)
    p.add_argument("--epochs", type=int, default=100)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--allow-fixture", action="store_true", help="explicitly allow synthetic smoke tests; never field performance evidence")
    a = p.parse_args()
    if a.action == "train" and not a.manifest:
        p.error("training requires --manifest")
    r = train(a.manifest, a.output, allow_fixture=a.allow_fixture, epochs=a.epochs, seed=a.seed) if a.action == "train" else evaluate(a.output, allow_fixture=a.allow_fixture)
    print(json.dumps({k:v for k,v in r.items() if k not in ("predictions", "history")}, indent=2))
