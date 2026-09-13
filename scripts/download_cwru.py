#!/usr/bin/env python3
"""Download and audit the official 36-record CWRU 12k DE subset."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from vibfpga.dataset import download_and_audit

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--directory", type=Path, default=Path("data/cwru"))
    p.add_argument("--workers", type=int, default=4)
    args = p.parse_args()
    download_and_audit(args.directory, workers=args.workers)
