#!/usr/bin/env python3
"""Train real models, select with validation, export, then evaluate test once."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from vibfpga.training import run_training

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/cwru"))
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    parser.add_argument("--epochs", type=int, default=450)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    run_training(args.data,args.artifacts,epochs=args.epochs,seed=args.seed)
