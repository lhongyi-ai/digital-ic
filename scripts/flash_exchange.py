#!/usr/bin/env python3
"""Prepare/read bounded Flash exchange files; hardware execution is explicit."""
import argparse
import json
from pathlib import Path
import shlex
import numpy as np
from vibfpga.board import (build_replay_image, parse_result_log, read_command,
                           write_commands, execute_commands, validate_profile, verify_replay_log)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile", default="configs/upduino-reference.json")
    sub = p.add_subparsers(dest="action", required=True)
    pack = sub.add_parser("pack")
    pack.add_argument("samples", help=".npy signed-int16 frames, shape [1..16,1024]")
    pack.add_argument("--model", default="artifacts/model/model.json")
    pack.add_argument("--output", default="build/replay.bin")
    pack.add_argument("--frames", type=int, default=1000)
    pack.add_argument("--period", type=int, default=1000)
    for action in ("write-input", "clear-log", "read-log"):
        sp = sub.add_parser(action)
        sp.add_argument("--file", default="build/replay.bin" if action == "write-input" else "build/log.bin")
        sp.add_argument("--execute", action="store_true")
    parse = sub.add_parser("parse-log")
    parse.add_argument("file")
    verify = sub.add_parser("verify")
    verify.add_argument("--image",type=Path,required=True)
    verify.add_argument("--log",type=Path,required=True)
    verify.add_argument("--model",type=Path,default=Path("artifacts/model/model.json"))
    args = p.parse_args()
    profile = json.loads(Path(args.profile).read_text())
    validate_profile(profile)
    if args.action == "pack":
        image, meta = build_replay_image(np.load(args.samples, allow_pickle=False), args.model,
                                         period_cycles=args.period, run_frames=args.frames)
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        if len(image) > profile["input_bytes"]:
            raise ValueError("image exceeds input partition")
        out.write_bytes(image)
        out.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n")
        print(json.dumps(meta, indent=2))
        return
    if args.action == "parse-log":
        print(json.dumps(parse_result_log(Path(args.file).read_bytes()), indent=2))
        return
    if args.action == "verify":
        print(json.dumps(verify_replay_log(args.image.read_bytes(),args.log.read_bytes(),args.model),indent=2))
        return
    path = Path(args.file)
    if args.action == "clear-log":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\xff" * profile["log_bytes"])
        commands = write_commands(profile, path, "log")
    elif args.action == "write-input":
        commands = write_commands(profile, path)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        commands = [read_command(profile, path)]
    for command in commands:
        print(shlex.join(command))
    if args.execute:
        execute_commands(commands, profile, writes=args.action != "read-log", execute=True)


if __name__ == "__main__":
    main()
