"""Audited official CWRU subset, with a record-first load-held-out split."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import time
import urllib.request
import numpy as np
from scipy.io import loadmat

SOURCE_PAGE = "https://engineering.case.edu/bearingdatacenter/12k-drive-end-bearing-fault-data"
BASE_URL = "https://engineering.case.edu/sites/default/files"
CLASS_NAMES = ["inner_race", "outer_race", "ball"]


@dataclass(frozen=True)
class Record:
    record_id: int
    label: int
    class_name: str
    fault_inches: str
    load_hp: int
    split: str
    mat_key: str
    sample_rate_hz: int = 12000
    channel: str = "DE"
    outer_position: str | None = None

    @property
    def url(self):
        return f"{BASE_URL}/{self.record_id}.mat"


def records():
    # Each row is explicitly transcribed from the official 12k DE table;
    # outer-race data is restricted to its @6:00 column.
    groups = [
        (0, "0.007", [105, 106, 107, 108]),
        (0, "0.014", [169, 170, 171, 172]),
        (0, "0.021", [209, 210, 211, 212]),
        (1, "0.007", [130, 131, 132, 133]),
        (1, "0.014", [197, 198, 199, 200]),
        (1, "0.021", [234, 235, 236, 237]),
        (2, "0.007", [118, 119, 120, 121]),
        (2, "0.014", [185, 186, 187, 188]),
        (2, "0.021", [222, 223, 224, 225]),
    ]
    result = []
    for label, diameter, ids in groups:
        for load_hp, record_id in enumerate(ids):
            split = "train" if load_hp < 2 else "validation" if load_hp == 2 else "test"
            result.append(Record(record_id, label, CLASS_NAMES[label], diameter,
                                 load_hp, split, f"X{record_id:03d}_DE_time",
                                 outer_position="6:00" if label == 1 else None))
    return sorted(result, key=lambda r: r.record_id)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def _audit_payload(payload, record):
    mat = loadmat(io.BytesIO(payload))
    if record.mat_key not in mat:
        raise ValueError(f"{record.record_id}: missing exact MAT key {record.mat_key}")
    x = np.asarray(mat[record.mat_key], dtype=np.float64).reshape(-1)
    if not x.size or not np.isfinite(x).all():
        raise ValueError(f"{record.record_id}: empty or nonfinite data")
    rpm = mat.get(f"X{record.record_id:03d}RPM")
    return {**asdict(record), "url": record.url, "source_page": SOURCE_PAGE,
            "bytes": len(payload), "sha256": sha256(payload), "samples": int(x.size),
            "sample_rate_basis": "official 12k Drive End Bearing Fault Data table; no inferred MAT sampling-rate field",
            "mat_variables": [k for k in mat if not k.startswith("__")],
            "rpm": float(np.ravel(rpm)[0]) if rpm is not None else None,
            "max_absolute": float(np.abs(x).max()),
            "constant_run_max": int(_longest_constant_run(x))}


def _longest_constant_run(x):
    if x.size < 2:
        return x.size
    boundaries = np.flatnonzero(np.r_[True, np.diff(x) != 0, True])
    return np.diff(boundaries).max(initial=0)


def download_and_audit(directory, workers=4):
    """Download all 36 records; cache hashes are checked before reuse.

    Normal records are intentionally excluded because their original sampling
    rate was not individually established from the official source metadata.
    No record is silently removed because of signal-quality observations.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / "manifest.json"
    previous = {}
    if manifest_path.exists():
        previous = {r["record_id"]: r for r in json.loads(manifest_path.read_text())["records"]}

    def one(record):
        path = directory / f"{record.record_id}.mat"
        if path.exists():
            payload = path.read_bytes()
            if record.record_id in previous and sha256(payload) != previous[record.record_id]["sha256"]:
                raise ValueError(f"cached SHA mismatch for {record.record_id}; investigate before replacing it")
        else:
            for attempt in range(3):
                try:
                    request = urllib.request.Request(record.url, headers={"User-Agent": "vibfpga-research/1.0"})
                    payload = urllib.request.urlopen(request, timeout=90).read()
                    _audit_payload(payload, record)
                    temporary = path.with_suffix(".part")
                    temporary.write_bytes(payload)
                    temporary.replace(path)
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    time.sleep(1 + attempt)
        result = _audit_payload(payload, record)
        print(f"audited {record.record_id}: {record.split}, {result['samples']} samples", flush=True)
        return result

    audited = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(one, record) for record in records()]
        for future in as_completed(futures):
            audited.append(future.result())
    manifest = {"schema_version": 1, "audited_utc": datetime.now(timezone.utc).isoformat(),
                "source_page": SOURCE_PAGE, "class_names": CLASS_NAMES,
                "normal_included": False,
                "normal_exclusion_reason": "normal record sampling rates not individually verified from official metadata",
                "split_protocol": "train loads 0/1; validation load 2; test load 3; split before nonoverlapping windows",
                "records": sorted(audited, key=lambda row: row["record_id"])}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def load_record(directory, record):
    path = Path(directory) / f"{record.record_id}.mat"
    manifest_path = Path(directory) / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError("run audited download before loading dataset")
    manifest = json.loads(manifest_path.read_text())
    item = next(r for r in manifest["records"] if r["record_id"] == record.record_id)
    payload = path.read_bytes()
    if sha256(payload) != item["sha256"]:
        raise ValueError(f"SHA mismatch while loading {path}")
    mat = loadmat(io.BytesIO(payload))
    return np.asarray(mat[record.mat_key], dtype=np.float64).reshape(-1)


def fit_raw_scale(directory):
    """One global float-to-PCM16 gain, learned only from train records."""
    train = [r for r in records() if r.split == "train"]
    maximum = max(float(np.abs(load_record(directory, r)).max()) for r in train)
    if maximum <= 0:
        raise ValueError("training recordings have zero amplitude")
    return {"gain": 32700.0 / maximum, "method": "32700 / maximum absolute TRAIN sample",
            "train_max_absolute": maximum, "training_record_ids": [r.record_id for r in train],
            "rounding": "nearest_ties_even", "saturation": [-32768, 32767]}


def load_windows(directory, split, raw_scale, n=1024):
    """Load one split into PCM16 frames, labels and record/window provenance."""
    if split not in {"train", "validation", "test"}:
        raise ValueError("unknown split")
    frames, labels, metadata, clipping = [], [], [], []
    for record in records():
        if record.split != split:
            continue
        x = load_record(directory, record)
        pcm_float = np.rint(x * float(raw_scale["gain"]))
        clipped = (pcm_float < -32768) | (pcm_float > 32767)
        pcm = np.clip(pcm_float, -32768, 32767).astype(np.int16)
        count = len(pcm) // n
        frames.append(pcm[:count * n].reshape(count, n))
        labels.extend([record.label] * count)
        for index in range(count):
            metadata.append({"record_id": record.record_id, "split": split,
                             "window_index": index, "sample_start": index * n,
                             "sample_stop": (index + 1) * n, "class_id": record.label,
                             "load_hp": record.load_hp, "fault_inches": record.fault_inches})
        clipping.append({"record_id": record.record_id, "samples": len(pcm),
                         "clipped_samples": int(clipped.sum()), "windows": count,
                         "discarded_tail_samples": len(pcm) - count * n})
    return np.concatenate(frames), np.asarray(labels, dtype=np.int64), metadata, clipping
