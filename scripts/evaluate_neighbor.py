#!/usr/bin/env python3
"""Evaluate once with --evaluate; --verify never loads MAT or runs inference."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--evaluate", action="store_true", help="Freeze and perform the one authorized evaluation; refuses any existing output")
    mode.add_argument("--verify", action="store_true", help="Read-only hash and stored prediction checks; no waveform load/inference")
    args = parser.parse_args()
    from vibfpga.neighbor_evaluation import evaluate_once, verify_existing
    try:
        result = evaluate_once(ROOT) if args.evaluate else verify_existing(ROOT)
    except (ValueError, FileNotFoundError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
