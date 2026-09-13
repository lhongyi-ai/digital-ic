#!/usr/bin/env python3
"""Read one existing validation vector and print a reproducible integer trace.

This script never trains, selects a test example, writes artifacts, builds RTL,
or contacts hardware. If its original MAT file is present, that one validation
record is integrity-checked and compared with the exported PCM16 samples too.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from vibfpga.dataset import load_record, records
from vibfpga.fixed import classify, coefficients


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_hex(path, bits, signed=True):
    values = [int(word, 16) for word in path.read_text().split()]
    if any(value < 0 or value >= 1 << bits for value in values):
        raise ValueError(f"Value outside {bits}-bit storage in {path}")
    if signed:
        values = [value - (1 << bits) if value >= 1 << (bits - 1) else value for value in values]
    return np.asarray(values, dtype=np.int64)


def plain(value):
    return value.tolist() if isinstance(value, np.ndarray) else int(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vector", type=Path, default=ROOT / "artifacts/vectors_neighbor/replay_000.json")
    parser.add_argument("--model", type=Path, default=ROOT / "artifacts/model_neighbor/model.json")
    parser.add_argument("--data", type=Path, default=ROOT / "data/cwru")
    parser.add_argument("--full", action="store_true", help="Also print every recomputed intermediate array")
    args = parser.parse_args()
    vector = json.loads(args.vector.read_text())
    model = json.loads(args.model.read_text())
    provenance = vector["provenance"]
    if provenance["split"] != "validation":
        parser.error("This learning trace only accepts an already-exported validation vector")
    if model.get("feature_mode") != "neighbor3_energy":
        parser.error("This walkthrough requires the exported neighbor3_energy model")
    sample_path = args.vector.parent / vector["samples_hex"]
    raw = read_hex(sample_path, 16)
    result = classify(raw, model)
    if set(result) != set(vector["expected"]):
        raise AssertionError("Exported/reference intermediate fields differ")
    for name, value in result.items():
        np.testing.assert_array_equal(value, vector["expected"][name], err_msg=name)

    hann, cosine, nsine = coefficients(model["n"])
    roms = [("feature_shifts.hex", model["feature_shifts"], 8, False),
            ("bins.hex", model["bins"], 16, False),
            ("dft_bins.hex", model["dft_bins"], 16, False),
            ("hann.hex", hann, 16, True),
            ("hann_quarter.hex", hann[:model["n"] // 4], 16, True),
            ("cos_quarter.hex", cosine[:model["n"] // 4], 16, True),
            ("w1.hex", model["w1"], 8, True), ("w2.hex", model["w2"], 8, True),
            ("b1.hex", model["b1"], 32, True), ("b2.hex", model["b2"], 32, True)]
    w1, w2 = np.asarray(model["w1"], dtype=np.int64), np.asarray(model["w2"], dtype=np.int64)
    for lanes in (1, 4):
        for lane in range(lanes):
            bank = []
            for weights in (w1, w2):
                for group in range((len(weights) + lanes - 1) // lanes):
                    row = group * lanes + lane
                    bank.extend(weights[row].tolist() if row < len(weights) else [0] * weights.shape[1])
            roms.append((f"weights_l{lanes}_{lane}.hex", bank, 8, True))
    for filename, values, bits, signed in roms:
        np.testing.assert_array_equal(read_hex(args.model.parent / filename, bits, signed),
                                      np.asarray(values).reshape(-1), err_msg=filename)

    source_record = next(item for item in model["data_provenance"]["records"]
                         if item["record_id"] == provenance["record_id"])
    source_path = args.data / f"{provenance['record_id']}.mat"
    source = {**provenance, "mat_key": source_record["mat_key"],
              "mat_sha256_expected": source_record["sha256"],
              "sample_rate_hz": model["sample_rate_hz"],
              "original_mat_verified": False}
    original = None
    if source_path.exists():
        if digest(source_path) != source_record["sha256"]:
            raise AssertionError("Original MAT does not match model provenance SHA256")
        record = next(item for item in records() if item.record_id == provenance["record_id"])
        original = load_record(args.data, record)[provenance["sample_start"]:provenance["sample_stop"]]
        pcm = np.clip(np.rint(original * model["raw_scale"]["gain"]), -32768, 32767).astype(np.int64)
        np.testing.assert_array_equal(pcm, raw, err_msg="original MAT window -> PCM16")
        source["original_mat_verified"] = True

    indices = sorted(set(i for i in (0, 1, 2, 64, 128, 256, 511, 512, 768, model["n"] - 1) if i < len(raw)))
    sample_trace = []
    for index in indices:
        row = {"n": index, "raw": int(raw[index]), "centered": int(result["centered"][index]),
               "scaled": int(result["scaled"][index]), "hann_q14": int(hann[index]),
               "hann_product": int(result["scaled"][index] * hann[index]),
               "windowed": int(result["windowed"][index])}
        if original is not None:
            row["source_value"] = float(original[index])
        sample_trace.append(row)
    feature_trace = []
    for feature, center in enumerate(model["bins"]):
        bins = []
        for dft_index in range(feature * 3, feature * 3 + 3):
            k = model["dft_bins"][dft_index]
            bins.append({"k": k, "frequency_hz": k * model["sample_rate_hz"] / model["n"],
                         **{name: int(result[name][dft_index])
                            for name in ("real_acc", "imag_acc", "real", "imag", "dft_powers")}})
        feature_trace.append({"feature": feature, "center": center, "bins": bins,
                              "energy": int(result["powers"][feature]),
                              "right_shift": model["feature_shifts"][feature],
                              "quantized": int(result["features"][feature])})
    x, h = result["features"], result["hidden"]
    neuron0_products = w1[0] * x
    outputs = [{"class_id": i, "class_name": model["class_names"][i], "weights": w2[i].tolist(),
                "products": (w2[i] * h).tolist(), "dot_product": int(w2[i] @ h),
                "bias": model["b2"][i], "logit": int(result["logits"][i])} for i in range(3)]
    trace = {
        "kind": "read_only_python_recomputation_of_existing_validation_vector",
        "physical_measurement": False, "rtl_executed_by_this_script": False,
        "source": source,
        "sha256": {"model_json": digest(args.model), "vector_json": digest(args.vector),
                   "samples_hex": digest(sample_path)},
        "checks": {"all_exported_intermediates_equal": True,
                   "exported_intermediate_fields": len(result), "rom_files_equal": len(roms)},
        "raw_gain": model["raw_scale"]["gain"], "sum_raw": int(raw.sum()), "mean": result["mean"],
        "sample_trace": sample_trace, "feature_trace": feature_trace,
        "features": x.tolist(),
        "first_hidden_neuron": {"weights": w1[0].tolist(), "products": neuron0_products.tolist(),
                                "dot_product": int(neuron0_products.sum()), "bias": model["b1"][0],
                                "accumulator": int(result["hidden_acc"][0]), "right_shift": model["hidden_shift"],
                                "hidden": int(h[0])},
        "first_four_lanes_at_input0": {"activation": int(x[0]), "weights": w1[:4, 0].tolist(),
                                       "products": (w1[:4, 0] * x[0]).tolist(), "initial_biases": model["b1"][:4]},
        "hidden_acc": result["hidden_acc"].tolist(), "hidden": h.tolist(),
        "output_neurons": outputs, "logits": result["logits"].tolist(),
        "class_id": result["class_id"], "class_name": model["class_names"][result["class_id"]],
    }
    if args.full:
        trace["all_intermediates"] = {name: plain(value) for name, value in result.items()}
    print(json.dumps(trace, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
