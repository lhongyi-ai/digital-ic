#!/usr/bin/env python3
"""Analyze actual sensor CSV captures; does not fabricate measurement data."""
import argparse
import json
from pathlib import Path
from vibfpga.sensor import fit_static, validate_static, analyze_capture, sensor_log_to_csv


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    decode = sub.add_parser("decode")
    decode.add_argument("log", type=Path)
    decode.add_argument("--output", type=Path, required=True)
    fit = sub.add_parser("calibrate")
    fit.add_argument("--positive", required=True)
    fit.add_argument("--negative", required=True)
    fit.add_argument("--axis", choices=list("xyz"), default="z")
    fit.add_argument("--output", type=Path, required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("capture")
    validate.add_argument("--calibration", type=Path, required=True)
    validate.add_argument("--expected-g", type=int, choices=(-1, 0, 1), required=True)
    validate.add_argument("--output", type=Path, required=True)
    noise = sub.add_parser("noise")
    noise.add_argument("capture")
    noise.add_argument("--odr", type=int, choices=(100, 400, 800), required=True)
    noise.add_argument("--axis", choices=list("xyz"), default="z")
    noise.add_argument("--calibration", type=Path)
    noise.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.command == "decode":
        a.output.parent.mkdir(parents=True,exist_ok=True)
        meta = sensor_log_to_csv(a.log.read_bytes(), a.output)
        a.output.with_suffix(".json").write_text(json.dumps(meta,indent=2)+"\n")
        print(a.output)
        return
    if a.command == "calibrate":
        result = fit_static(a.positive, a.negative, a.axis)
    else:
        cal = json.loads(a.calibration.read_text()) if a.calibration else None
        result = validate_static(a.capture, cal, a.expected_g) if a.command == "validate" else analyze_capture(a.capture, odr=a.odr, axis=a.axis, calibration=cal)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    if a.command == "calibrate":
        a.output.with_suffix(".svh").write_text(
            f"localparam signed [31:0] CAL_OFFSET_Q8 = 32'sh{result['offset_q8'] & 0xffffffff:08x};\n"
            f"localparam signed [31:0] CAL_GAIN_Q20 = 32'sd{result['gain_q20']};\n")
    print(a.output)


if __name__ == "__main__":
    main()
