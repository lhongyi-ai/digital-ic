#!/usr/bin/env python3
"""Copy hash-verified, successfully routed firmware into a portable directory."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
out=ROOT/"artifacts/firmware"
out.mkdir(exist_ok=True)
manifest={"schema_version":1,"hardware_programmed":False,"board_profile_verified":False,
          "required_hardware":"UPduino v3.x reference, iCE40UP5K SG48, external 12 MHz on gpio_20, verified Flash geometry",
          "images":[]}
for directory in sorted([*(ROOT/"build").glob("board_*"),*(ROOT/"build").glob("sensor_board_*")]):
    report_path=directory/"report.json"
    if not report_path.exists():continue
    report=json.loads(report_path.read_text())
    binary=directory/"board.bin"
    if not report.get("place_route_completed") or hashlib.sha256(binary.read_bytes()).hexdigest()!=report["bitstream_sha256"]:
        raise ValueError(f"Unverified firmware {directory}")
    timing=json.loads((directory/"timing.json").read_text())
    if not all(x["achieved"]>=x["constraint"] for x in timing["fmax"].values()):
        raise ValueError(f"Timing target missed: {directory}")
    if not all(x["used"]<=x["available"] for x in timing["utilization"].values()):
        raise ValueError(f"Capacity exceeded: {directory}")
    destination=out/directory.name
    destination.mkdir(exist_ok=True)
    for name in ("board.bin","report.json","reference.pcf","timing.json"):
        path=directory/name
        if path.exists():shutil.copy2(path,destination/name)
    manifest["images"].append({"directory":directory.name,"top":report["top"],"bitstream_sha256":report["bitstream_sha256"],
        "model_sha256":report.get("model_sha256"),"target_clock_mhz":report["target_clock_mhz"],
        "post_route_fmax_mhz":min(v["achieved"] for v in timing["fmax"].values()),
        "packed_lc":timing["utilization"]["ICESTORM_LC"]["used"]})
for name in ("replay.bin","replay.json","replay_neighbor.bin","replay_neighbor.json"):
    path=ROOT/"build"/name
    if path.exists():shutil.copy2(path,out/name)
(out/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
print(out)
