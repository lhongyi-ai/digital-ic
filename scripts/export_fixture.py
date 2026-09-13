#!/usr/bin/env python3
"""Create clearly marked deterministic verification fixtures, NOT a trained model."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import numpy as np
from vibfpga.export import export_model, export_vectors

if __name__ == "__main__":
    n = 1024
    model = {"schema_version": 1, "training_status": "deterministic_verification_fixture_not_trained",
        "n": n, "bins": [4, 7, 10, 13, 16, 20, 24, 30, 40, 50, 64, 80, 100, 128, 192, 256],
        "input_shift": 5, "dft_shift": 20, "feature_shifts": [14] * 16,
        "w1": [[(i * 7 + j * 3) % 31 - 15 for j in range(16)] for i in range(16)],
        "b1": [128 * (i - 8) for i in range(16)], "hidden_shift": 5,
        "w2": [[(i * 11 + j * 5) % 23 - 11 for j in range(16)] for i in range(3)],
        "b2": [20, -30, 7], "scales": {}, "data_provenance": {"synthetic": True}}
    root = Path("artifacts/fixtures")
    export_model(model, root / "model")
    t = np.arange(n)
    frames = np.asarray([np.zeros(n), np.full(n, 32767),
        np.rint(12000 * np.sin(2 * np.pi * 13 * t / n) + 1700),
        np.where(t % 2 == 0, -32768, 32767),
        np.rint(6000 * np.sin(2*np.pi*24*t/n) + 3000 * np.cos(2*np.pi*50*t/n))], dtype=np.int16)
    export_vectors(model, frames, [{"kind": "synthetic_verification_only", "case": name} for name in
        ["zero", "dc_max", "tone_dc", "alternating_extrema", "two_tones"]], root / "vectors", "fixture")
