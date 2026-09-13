#!/usr/bin/env python3
"""Prepare a backup-first programming sequence for a verified physical board.

Default is a dry run. User explicitly selects --execute and a verified profile.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
from vibfpga.board import validate_profile, parse_replay_image, write_commands


def programming_plan(profile, bitstream, backup, replay_image=None):
    validate_profile(profile)
    bitstream=Path(bitstream).resolve()
    backup=Path(backup).resolve()
    report=json.loads(bitstream.with_name("report.json").read_text())
    if not 0<bitstream.stat().st_size<=profile["config_end"]:
        raise ValueError("bitstream exceeds reserved configuration area")
    if hashlib.sha256(bitstream.read_bytes()).hexdigest()!=report["bitstream_sha256"]:
        raise ValueError("bitstream does not match successful build report")
    if report.get("place_route_completed") is not True:
        raise ValueError("a completed board build is required")
    if backup.exists():
        raise ValueError("backup path already exists; select a new path")
    commands=[["iceprog","-d",profile["device"],"-R",str(profile["flash_bytes"]),str(backup)]]
    # Each iceprog invocation releases reset. Install the known, partition-bound
    # firmware first; clearing the log LAST is the final arming/reset operation.
    commands.append(["iceprog","-d",profile["device"],"-i",str(profile["erase_bytes"]//1024),"-o","0",str(bitstream)])
    if report["top"]=="upduino_replay":
        if replay_image is None:raise ValueError("replay firmware needs a matching input image")
        image=Path(replay_image).resolve()
        meta,_=parse_replay_image(image.read_bytes())
        if meta["model_sha256"]!=report["model_sha256"]:
            raise ValueError("input image and bitstream models differ")
        commands.extend(write_commands(profile,image,"input"))
    elif report["top"]!="upduino_sensor":
        raise ValueError("unsupported board firmware")
    erased=bitstream.parent/"erased-log.bin"
    erased.write_bytes(b"\xff"*profile["log_bytes"])
    commands.extend(write_commands(profile,erased,"log"))
    return commands


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile",type=Path,default=Path("configs/upduino-reference.json"))
    p.add_argument("--bitstream",type=Path,required=True)
    p.add_argument("--backup",type=Path,required=True)
    p.add_argument("--image",type=Path)
    p.add_argument("--execute",action="store_true")
    a=p.parse_args()
    profile=json.loads(a.profile.read_text())
    commands=programming_plan(profile,a.bitstream,a.backup,a.image)
    for command in commands:print(shlex.join(command))
    if not a.execute:return
    if profile.get("board_verified") is not True:
        raise ValueError("Physical board, oscillator, pinout and Flash geometry have not been verified")
    a.backup.parent.mkdir(parents=True,exist_ok=True)
    for index,command in enumerate(commands):
        subprocess.run(command,check=True)
        if index==0 and a.backup.stat().st_size!=profile["flash_bytes"]:
            raise ValueError("backup incomplete; programming cancelled")
    print("Programming completed. Capture/compute starts now; wait for the firmware done signal before reading its log.")


if __name__=="__main__":main()
