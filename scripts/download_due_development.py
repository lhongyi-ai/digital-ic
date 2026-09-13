#!/usr/bin/env python3
"""Download only the frozen DUE 00/01 development records."""
import concurrent.futures
import argparse
import io
import json
import os
import struct
import time
import wave
import zlib
from pathlib import Path

import numpy as np

from vibfpga.mimii import fetch_range, sha

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/mimii-due-source-review"


def extract(info, url):
    header = fetch_range(url, info["offset"], 30)
    fields = struct.unpack("<4s5H3I2H", header)
    assert fields[0] == b"PK\x03\x04" and fields[3] == info["method"]
    name_n, extra_n = fields[-2:]
    blob = fetch_range(url, info["offset"] + 30, name_n + extra_n + info["compressed"])
    assert blob[:name_n].decode() == info["name"]
    packed = blob[name_n + extra_n :]
    raw = zlib.decompress(packed, -15) if info["method"] == 8 else packed
    assert len(raw) == info["size"] and zlib.crc32(raw) == info["crc"]
    with wave.open(io.BytesIO(raw)) as wav:
        assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, 16000)
        pcm = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2").copy()
    assert pcm.shape == (160000,)
    return pcm, sha(raw)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--section02", action="store_true")
    parser.add_argument("--normal-reference", action="store_true")
    args = parser.parse_args()
    plan_path = BASE / "expansion-plan.json"
    plan = json.loads(plan_path.read_text())
    plan_hash = sha(plan_path.read_bytes())
    if args.normal_reference:
        inventory = json.loads((BASE / "inventory.json").read_text())["entries"]
        rows = []
        for section in ("00", "01", "02"):
            source = [dict(row, section=section) for row in inventory if
                f"section_{section}_source_train_normal_" in row["name"]]
            target = [dict(row, section=section) for row in inventory if
                f"section_{section}_target_train_normal_" in row["name"]]
            source.sort(key=lambda row: row["name"])
            assert len(source) == 1000 and len(target) == 3
            rows += source[:200] + target
        reference_plan = BASE / "normal-reference-plan.json"
        if not reference_plan.exists():
            reference_plan.write_text(json.dumps({"selection": "first 200 source names plus all 3 target names per section",
                "selected_from_audio_or_scores": False, "records": rows}, indent=2) + "\n")
        assert json.loads(reference_plan.read_text())["records"] == rows
        plan_hash = sha(reference_plan.read_bytes())
    elif args.section02:
        rows = [row for row in plan["records"] if row["section"] == "02" and "_test_" in row["name"]]
        assert len(rows) == 400
    else:
        rows = [row for row in plan["records"] if row["role"] in ("fit", "calibration")]
        assert len(rows) == 800 and {row["section"] for row in rows} == {"00", "01"}
    pcm_dir, receipt_dir = BASE / "pcm", BASE / "receipts"
    pcm_dir.mkdir(exist_ok=True)
    receipt_dir.mkdir(exist_ok=True)

    def get(row):
        stem = Path(row["name"]).stem
        out = pcm_dir / f"{stem}.npy"
        receipt = receipt_dir / f"{stem}.json"
        if out.exists() and receipt.exists():
            meta = json.loads(receipt.read_text())
            assert meta["plan_sha256"] == plan_hash and meta["npy_sha256"] == sha(out.read_bytes())
            return
        pcm, wav_hash = extract(row, plan["archive"]["links"]["self"])
        temp = out.with_suffix(".part.npy")
        np.save(temp, pcm)
        os.replace(temp, out)
        receipt.write_text(json.dumps({"name": row["name"], "plan_sha256": plan_hash,
            "wav_sha256": wav_hash, "npy_sha256": sha(out.read_bytes())}, indent=2) + "\n")
        time.sleep(0.15)

    # ponytail: one worker is slower but avoids Zenodo rate limits and resumes cleanly.
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        for count, _ in enumerate(pool.map(get, rows), 1):
            if count % 100 == 0:
                print(f"verified {count}/{len(rows)}", flush=True)
    completion = ("normal-reference-download.json" if args.normal_reference else
        "section02-development-download.json" if args.section02 else "development-download.json")
    (BASE / completion).write_text(json.dumps({"passed": True,
        "records": len(rows), "plan_sha256": plan_hash,
        "section02_opened_for_development": args.section02,
        "normal_reference_only": args.normal_reference}, indent=2) + "\n")


if __name__ == "__main__":
    main()
