"""Flash exchange format and bounded programmer operations.

No function executes hardware commands implicitly. Addresses are partition-bound;
the reference profile intentionally cannot authorize writes.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zlib

import numpy as np

IMAGE_MAGIC = b"VIB1"
LOG_MAGIC = b"VLG1"
COMMIT = 0x434F4D54
HEADER_BYTES = 4096
RECORD_BYTES = 64
MAX_SOURCE_FRAMES = 16
MAX_RUN_FRAMES = 1000


def validate_profile(profile: dict) -> None:
    if profile.get("schema_version") != 1:
        raise ValueError("unsupported board profile schema")
    capacity, erase = int(profile["flash_bytes"]), int(profile["erase_bytes"])
    if erase not in (4096, 32768, 65536) or capacity <= 0:
        raise ValueError("invalid Flash geometry")
    intervals = [(0, int(profile["config_end"]), "configuration")]
    for name in ("input", "log"):
        start, size = int(profile[f"{name}_offset"]), int(profile[f"{name}_bytes"])
        if start < 0 or size <= 0 or start % erase or size % erase:
            raise ValueError(f"unaligned {name} partition")
        if start + size > capacity:
            raise ValueError(f"{name} partition exceeds Flash capacity")
        intervals.append((start, start + size, name))
    intervals.sort()
    if intervals[0][1] <= 0 or intervals[0][1] > capacity:
        raise ValueError("invalid configuration partition")
    for a, b in zip(intervals, intervals[1:]):
        if a[1] > b[0]:
            raise ValueError(f"overlapping {a[2]} and {b[2]} partitions")
    fixed = {"config_end": 0x40000, "input_offset": 0x40000, "input_bytes": 0x10000,
             "log_offset": 0x300000, "log_bytes": 0x20000}
    if any(int(profile[k]) != v for k, v in fixed.items()):
        raise ValueError("profile layout must match the implemented VIB1/SEN1 RTL partitions")


def build_replay_image(samples, model_path: str | Path, *, period_cycles=1000,
                       run_frames=1000) -> tuple[bytes, dict]:
    values = np.asarray(samples)
    if values.ndim != 2 or values.shape[1] != 1024 or not 1 <= len(values) <= MAX_SOURCE_FRAMES:
        raise ValueError("expected 1..16 frames, each containing 1024 raw samples")
    if not np.issubdtype(values.dtype, np.integer) or np.any(values < -32768) or np.any(values > 32767):
        raise ValueError("samples must be signed 16-bit integers")
    if not 1 <= int(run_frames) <= MAX_RUN_FRAMES or not 4 <= int(period_cycles) <= 65535:
        raise ValueError("invalid run length or sample period")
    model_raw = Path(model_path).read_bytes()
    model = json.loads(model_raw)
    if model.get("n") != 1024:
        raise ValueError("board replay currently requires the N1024 model")
    payload = values.astype("<i2").tobytes()
    digest = hashlib.sha256(model_raw).digest()
    crc = zlib.crc32(payload)
    # Header is little-endian. Unused bytes are erased Flash, not zero-filled.
    header = struct.pack("<4s7I32s", IMAGE_MAGIC, 1, 1024, len(values),
                         int(run_frames), int(period_cycles), len(payload), crc, digest)
    image = header.ljust(HEADER_BYTES, b"\xff") + payload
    meta = {"schema_version": 1, "mode": "replay", "n": 1024,
            "source_frames": len(values), "run_frames": int(run_frames),
            "period_cycles": int(period_cycles), "payload_crc32": f"{crc:08x}",
            "model_sha256": digest.hex(), "image_sha256": hashlib.sha256(image).hexdigest(),
            "repeated_frames_are_independent_experiments": False}
    return image, meta


def parse_replay_image(blob: bytes) -> tuple[dict, np.ndarray]:
    if len(blob) < HEADER_BYTES:
        raise ValueError("truncated replay image")
    magic, version, n, count, runs, period, size, crc, model_digest = struct.unpack_from("<4s7I32s", blob)
    if magic != IMAGE_MAGIC or version != 1 or n != 1024:
        raise ValueError("invalid replay header")
    if not 1 <= count <= MAX_SOURCE_FRAMES or not 1 <= runs <= MAX_RUN_FRAMES or not 4 <= period <= 65535:
        raise ValueError("invalid replay parameters")
    if size != count * n * 2 or len(blob) < HEADER_BYTES + size:
        raise ValueError("invalid replay payload size")
    payload = blob[HEADER_BYTES:HEADER_BYTES + size]
    if zlib.crc32(payload) != crc:
        raise ValueError("replay payload checksum mismatch")
    return {"n": n, "source_frames": count, "run_frames": runs,
            "period_cycles": period, "model_sha256": model_digest.hex()}, np.frombuffer(payload, dtype="<i2").reshape(count, n)


def write_commands(profile: dict, image_path: str | Path, partition="input") -> list[list[str]]:
    validate_profile(profile)
    if partition not in ("input", "log"):
        raise ValueError("configuration writes are not supported by this data utility")
    path = Path(image_path).resolve()
    if not path.is_file() or not 0 < path.stat().st_size <= int(profile[f"{partition}_bytes"]):
        raise ValueError("image does not fit the selected partition")
    # Force 4-KiB/32-KiB/64-KiB erase geometry so iceprog cannot erase configuration.
    return [["iceprog", "-d", profile["device"], "-i", str(int(profile["erase_bytes"]) // 1024),
             "-o", str(int(profile[f"{partition}_offset"])), str(path)]]


def read_command(profile: dict, output_path: str | Path, partition="log") -> list[str]:
    validate_profile(profile)
    if partition not in ("input", "log"):
        raise ValueError("unknown partition")
    return ["iceprog", "-d", profile["device"], "-o", str(int(profile[f"{partition}_offset"])),
            "-R", str(int(profile[f"{partition}_bytes"])), str(Path(output_path).resolve())]


def execute_commands(commands, profile, *, writes=False, execute=False):
    """Validate exact bounded operations; execution is a separate opt-in.

    `writes` is retained for callers, but command structure determines whether a
    write occurs. Passing writes=False cannot bypass profile verification.
    """
    validate_profile(profile)
    actual_writes = False
    for command in commands:
        matched = False
        if not isinstance(command, list) or len(command) != 8:
            raise ValueError("unsupported programmer command")
        for partition in ("input", "log"):
            if command == read_command(profile, command[-1], partition):
                matched = True
                break
            if command[3] == "-i" and command[5:7] == ["-o", str(profile[f"{partition}_offset"])] and command == write_commands(profile, command[-1], partition)[0]:
                matched = True
                actual_writes = True
                break
        if not matched:
            raise ValueError("command is outside the supported partition operations")
    if not execute:
        return commands
    if actual_writes and profile.get("board_verified") is not True:
        raise ValueError("writes refused: actual board and Flash geometry have not been verified")
    for command in commands:
        subprocess.run(command, check=True)


def parse_result_log(blob: bytes) -> dict:
    if len(blob) < 64:
        raise ValueError("truncated result log")
    magic, version, count, commit = struct.unpack_from("<4sIII", blob)
    if magic != LOG_MAGIC or version != 1 or commit != COMMIT:
        raise ValueError("result log is absent, uncommitted, or has the wrong version")
    if count > MAX_RUN_FRAMES or len(blob) < HEADER_BYTES + count * RECORD_BYTES:
        raise ValueError("truncated or oversized result records")
    records = []
    for i in range(count):
        words = struct.unpack_from("<16I", blob, HEADER_BYTES + i * RECORD_BYTES)
        logits = struct.unpack("<3i", struct.pack("<3I", *words[1:4]))
        records.append({"frame_id": words[0], "logits": list(logits), "class_id": words[4] & 3,
                        "error": (words[4] >> 8) & 255, "cycles_pre": words[5], "cycles_dft": words[6],
                        "cycles_power": words[7], "cycles_nn": words[8], "cycles_total": words[9],
                        "max_fifo": words[10], "generated_samples": words[11],
                        "accepted_samples": words[12], "protocol_errors": words[13]})
    flags, generated, accepted, overflow, protocol, maximum, period, runs = struct.unpack_from("<8I", blob, 16)
    return {"schema_version": 1, "committed": True, "record_count": count, "records": records,
            "error_flags": flags, "generated_samples": generated, "accepted_samples": accepted,
            "overflow_count": overflow, "protocol_errors": protocol, "max_fifo": maximum,
            "period_cycles": period, "requested_frames": runs,
            "complete_without_reported_errors": flags == 0 and count == runs}


def verify_replay_log(image, log, model_path):
    """Compare every returned integer score with the frozen Python reference."""
    from .fixed import classify
    meta, samples=parse_replay_image(image)
    model_bytes=Path(model_path).read_bytes()
    if hashlib.sha256(model_bytes).hexdigest()!=meta["model_sha256"]:
        raise ValueError("reference model does not match replay image")
    parsed=parse_result_log(log)
    if not parsed["complete_without_reported_errors"] or parsed["record_count"]!=meta["run_frames"]:
        raise ValueError("replay incomplete or hardware error flags set")
    model=json.loads(model_bytes)
    expected=[classify(frame,model,model) for frame in samples]
    for index,record in enumerate(parsed["records"]):
        reference=expected[index%len(samples)]
        if record["frame_id"]!=index or record["error"]!=0 or record["logits"]!=reference["logits"].tolist() or record["class_id"]!=int(reference["class_id"]):
            raise ValueError(f"frame {index} does not match the bit-exact reference")
    return {"passed":True,"checked_frames":len(parsed["records"]),"model_sha256":meta["model_sha256"],
            "input_image_sha256":hashlib.sha256(image).hexdigest(),"result_log_sha256":hashlib.sha256(log).hexdigest(),
            "scope":"Numerical comparison of supplied files. Physical acquisition provenance is recorded separately."}
