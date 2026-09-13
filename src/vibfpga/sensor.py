"""ADXL345 measurement analysis; never substitutes simulation for measurements.

CSV columns: sample_index, service_cycle, x_raw, y_raw, z_raw. The service
timestamp is an FPGA register-read timestamp, not the sensor ADC aperture.
"""
from __future__ import annotations

import hashlib
import json
import struct
import zlib
from pathlib import Path

import numpy as np
from scipy.signal import welch

from .fixed import round_shift_even


def read_capture(path):
    path = Path(path)
    data = np.genfromtxt(path, delimiter=",", names=True)
    required = {"sample_index", "service_cycle"}
    if data.dtype.names is None or not required.issubset(data.dtype.names):
        raise ValueError(f"capture requires columns {sorted(required)}")
    data = np.atleast_1d(data)
    axes = {f"{a}_raw" for a in "xyz"}.intersection(data.dtype.names)
    if not axes:
        raise ValueError("capture needs at least one measured axis")
    required |= axes
    if len(data) < 2:
        raise ValueError("at least two samples required")
    for name in required:
        if not np.all(np.isfinite(data[name])) or np.any(data[name] != np.floor(data[name])):
            raise ValueError(f"non-integral or invalid {name}")
    for axis in axes:
        if np.any(np.abs(data[axis]) > 32767 + (data[axis] < 0)):
            raise ValueError("raw data outside int16")
    return data, {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                  "samples": len(data)}


def fit_static(positive, negative, axis="z", nominal_counts_per_g=256):
    """Fit one axis from distinct +g/-g captures, export fixed-point mg units.

    correction_mg = RNE((raw*256 - offset_q8)*gain_q20, 28)
    offset_q8 represents counts*256; gain_q20 represents mg/count*2**20.
    Parameters fit a static two-point scale only, not an absolute AC response.
    """
    if axis not in "xyz" or len(axis) != 1:
        raise ValueError("axis must be x, y or z")
    p, pm = read_capture(positive)
    n, nm = read_capture(negative)
    if f"{axis}_raw" not in p.dtype.names or f"{axis}_raw" not in n.dtype.names:
        raise ValueError("requested axis is absent from capture")
    if pm["sha256"] == nm["sha256"]:
        raise ValueError("+g and -g captures must be different records")
    hi, lo = float(np.mean(p[f"{axis}_raw"])), float(np.mean(n[f"{axis}_raw"]))
    scale = (hi - lo) / 2
    if scale <= 0 or not np.isfinite(scale):
        raise ValueError("+g mean must exceed -g mean; check orientation and axis")
    offset = (hi + lo) / 2
    return {"schema_version": 1, "axis": axis, "method": "single_axis_two_point_static_gravity",
            "offset_counts": offset, "counts_per_g": scale,
            "nominal_counts_per_g": nominal_counts_per_g,
            "offset_q8": int(np.rint(offset * 256)),
            "gain_q20": int(np.rint(1000 / scale * (1 << 20))),
            "output_unit": "mg", "rounding": "nearest_ties_even", "shift": 28,
            "fit_records": [pm, nm], "absolute_frequency_response_calibrated": False}


def correct_mg(raw, calibration):
    raw = np.asarray(raw)
    if not np.issubdtype(raw.dtype, np.integer) or np.any(raw < -32768) or np.any(raw > 32767):
        raise ValueError("expected signed int16 raw values")
    centered = raw.astype(np.int64) * 256 - int(calibration["offset_q8"])
    gain = int(calibration["gain_q20"])
    if not 0 < gain < (1 << 31) or not -(1 << 31) <= int(calibration["offset_q8"]) < (1 << 31):
        raise ValueError("calibration coefficients exceed hardware range")
    return np.clip(round_shift_even(centered * gain, 28), -(1 << 31), (1 << 31) - 1)


def validate_static(path, calibration, expected_g):
    data, meta = read_capture(path)
    if meta["sha256"] in {r["sha256"] for r in calibration["fit_records"]}:
        raise ValueError("validation must use a held-out capture, not a fit record")
    if expected_g not in (-1, 0, 1):
        raise ValueError("static reference orientation must be -1, 0 or +1 g")
    values = data[f'{calibration["axis"]}_raw'].astype(np.int64)
    before = values * (1000 / calibration["nominal_counts_per_g"])
    after = correct_mg(values, calibration)
    reference = expected_g * 1000
    return {"record": meta, "expected_g": expected_g,
            "before_mean_error_mg": float(np.mean(before) - reference),
            "after_mean_error_mg": float(np.mean(after) - reference),
            "before_rmse_mg": float(np.sqrt(np.mean((before - reference)**2))),
            "after_rmse_mg": float(np.sqrt(np.mean((after - reference)**2)))}


def analyze_capture(path, *, odr, clock_hz=12_000_000, calibration=None, axis="z"):
    if odr not in (100, 400, 800) or clock_hz <= 0:
        raise ValueError("supported ODRs: 100, 400, 800 samples/s")
    data, meta = read_capture(path)
    if f"{axis}_raw" not in data.dtype.names:
        raise ValueError("requested axis is absent from capture")
    # uint32 wraps every 357.9 s at 12 MHz; unwrap each adjacent interval.
    cycles = data["service_cycle"].astype(np.int64)
    delta = np.diff(cycles) % (1 << 32)
    if np.any(delta == 0) or np.any(delta >= (1 << 31)):
        raise ValueError("service timestamps repeated, reversed, or too far apart")
    indices = data["sample_index"].astype(np.int64)
    gaps = np.diff(indices)
    if np.any(gaps <= 0):
        raise ValueError("sample indices must increase")
    raw = data[f"{axis}_raw"].astype(np.int64)
    if calibration is not None and calibration["axis"] != axis:
        raise ValueError("axis does not match calibration")
    values = correct_mg(raw, calibration) if calibration else raw.astype(float)
    units = "mg" if calibration else "counts"
    freq, psd = welch(values, fs=odr, nperseg=min(256, len(values)), detrend="constant")
    gap_count = int(np.sum(gaps - 1))
    service_anomalies = int(np.count_nonzero(delta > 1.5 * clock_hz / odr))
    sidecar_path=Path(path).with_suffix(".json")
    sidecar=json.loads(sidecar_path.read_text()) if sidecar_path.exists() else {}
    if sidecar.get("csv_sha256") and sidecar["csv_sha256"]!=meta["sha256"]:
        raise ValueError("capture CSV does not match its acquisition metadata SHA256")
    if "odr_hz" in sidecar and sidecar["odr_hz"]!=odr:
        raise ValueError("requested ODR does not match acquisition metadata")
    if "clock_hz" in sidecar and sidecar["clock_hz"]!=clock_hz:
        raise ValueError("requested FPGA clock does not match acquisition metadata")
    if "axis" in sidecar and sidecar["axis"]!=axis:
        raise ValueError("requested axis does not match acquisition metadata")
    capture_anomalies=bool(sidecar.get("error_flags",0) or sidecar.get("missed_service",0) or sidecar.get("observed_sensor_overruns",0))
    return {"schema_version": 1, "record": meta, "axis": axis, "odr_hz": odr,
            "unit": units, "mean": float(np.mean(values)), "std_ddof1": float(np.std(values, ddof=1)),
            "nominal_record_seconds": len(values) / odr,
            "service_elapsed_seconds": float(delta.sum() / clock_hz),
            "service_interval_cycles": {"minimum": int(delta.min()), "maximum": int(delta.max()),
                                        "mean": float(delta.mean()), "std": float(delta.std())},
            "detectable_index_gaps": gap_count, "late_service_intervals": service_anomalies,
            "adc_aperture_jitter_measured": False,
            "psd_valid_uniform_sampling_assumption": gap_count == 0 and service_anomalies == 0 and not capture_anomalies,
            "capture_hardware_counters": {k:sidecar[k] for k in ("error_flags","missed_service","observed_sensor_overruns","observed_samples") if k in sidecar},
            "odr_source":"acquisition_metadata" if "odr_hz" in sidecar else "user_supplied_assumption",
            "psd_frequency_hz": freq.tolist(), "psd": psd.tolist(),
            "psd_units": f"{units}^2/Hz",
            "limitations": ["Service timestamps are register-read times, not ADC sample times.",
                            "Undetectable sensor overwrites cannot be excluded from timestamps alone.",
                            "PSD assumes samples at configured ODR; gaps invalidate this assumption."]}


def parse_sensor_log(blob):
    """Decode a committed SEN1 record; preserve capture-wide anomaly counters."""
    if len(blob) < 4096:
        raise ValueError("truncated sensor log")
    h = struct.unpack_from("<24I", blob)
    if h[0] != 0x314E4553 or h[1] != 1 or h[3] != 0x434F4D54:
        raise ValueError("sensor log missing, uncommitted, or unsupported")
    if h[8]!=12_000_000 or not 0<=h[2]<=h[7]<=min(h[6],24000) or not h[2]<=h[5]<=h[6] or h[6]==0:
        raise ValueError("inconsistent SEN1 sample counts or clock frequency")
    if h[2] > 24000 or h[21:24] != (4, 0x301000, 4) or h[10] > 2:
        raise ValueError("invalid SEN1 record geometry")
    if h[9] not in (0x0A, 0x0C, 0x0D):
        raise ValueError("unknown sensor rate")
    payload = blob[4096:4096 + 4*h[2]]
    if len(payload) != 4*h[2] or zlib.crc32(payload) != h[20]:
        raise ValueError("sensor payload truncated or CRC mismatch")
    records = np.frombuffer(payload, dtype=np.dtype([("raw", "<i2"), ("delta_q4", "<u2")]))
    if len(records) and records[0]["delta_q4"] != 0:
        raise ValueError("first service delta must be zero")
    times = (int(h[12]) + np.cumsum(records["delta_q4"].astype(np.uint64))*4) % (1 << 32)
    meta = {"schema_version": 1, "committed": True, "stored_samples": h[2], "error_flags": h[4],
            "observed_samples": h[5], "target_samples": h[6], "storage_limit": h[7], "clock_hz": h[8],
            "odr_hz": {0x0A:100,0x0C:400,0x0D:800}[h[9]], "axis": "xyz"[h[10]], "device_id": h[11],
            "first_service_cycle": h[12], "last_service_cycle": h[13], "min_service_delta": h[14],
            "max_service_delta": h[15], "samples_captured": h[16], "missed_service": h[17],
            "observed_sensor_overruns": h[18], "interval_overflows": h[19],
            "timestamps_reconstructable": h[19] == 0, "timestamp_quantum_cycles": 4,
            "stored_duration_seconds": h[2] / {0x0A:100,0x0C:400,0x0D:800}[h[9]],
            "capture_target_seconds": h[6] / {0x0A:100,0x0C:400,0x0D:800}[h[9]],
            "adc_aperture_jitter_measured": False}
    extension=struct.unpack_from("<8I",blob,96)
    if extension[7]>=128 and extension[7]<=4096:
        signed=lambda v:v-(1<<32) if v&(1<<31) else v
        sum_unsigned=extension[1]+(extension[2]<<32)
        sum_signed=sum_unsigned-(1<<64) if sum_unsigned&(1<<63) else sum_unsigned
        elapsed=(extension[6]<<32)+h[13]-h[12]
        meta.update({"header_bytes":extension[7],"last_calibrated_mg":signed(extension[0]),
                     "sum_calibrated_mg":sum_signed,"calibrated_samples":extension[3],
                     "cal_offset_q8":signed(extension[4]),"cal_gain_q20":extension[5],
                     "service_wrap_count":extension[6],"full_service_elapsed_seconds":elapsed/h[8],
                     "calibration_provenance":"Parameters in firmware; static-fit evidence must be supplied separately."})
        if extension[7]>=208:
            windows,n,mode,clipped=struct.unpack_from("<4I",blob,128)
            if n!=256 or mode!=1:
                raise ValueError("unsupported on-board spectrum configuration")
            bins=[1,2,3,4,5,8,12,16,24,32,40,48,64,80,96,120]
            meta["spectrum"]={"complete_windows":windows,"n":n,"clipped_input_samples":clipped,
                "bin_indices":bins,"frequency_hz":[k*meta["odr_hz"]/n for k in bins],
                "powers":list(struct.unpack_from("<16I",blob,144)),
                "valid_complete_window":windows>0,
                "domain":"raw sensor counts, clipped to [-1024,1023], scaled x32 before contracted integer frontend",
                "scaling":"DFT Re/Im = sat16(RNE(acc,18)); power = Re^2 + Im^2",
                "is_psd_per_hz":False,"calibrated_mg_domain":False}
    return meta, records["raw"].astype(np.int16), times.astype(np.uint32)


def sensor_log_to_csv(blob, destination):
    meta, raw, times = parse_sensor_log(blob)
    if not meta["timestamps_reconstructable"]:
        raise ValueError("interval overflow: raw data available through parse_sensor_log, reliable timestamps unavailable")
    values = np.column_stack([np.arange(len(raw)), times, raw])
    np.savetxt(destination, values, delimiter=",", fmt="%d", comments="",
               header=f"sample_index,service_cycle,{meta['axis']}_raw")
    meta["source_log_sha256"]=hashlib.sha256(blob).hexdigest()
    meta["csv_sha256"]=hashlib.sha256(Path(destination).read_bytes()).hexdigest()
    Path(destination).with_suffix(".json").write_text(json.dumps(meta,indent=2)+"\n")
    return meta
