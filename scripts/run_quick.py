#!/usr/bin/env python3
"""Run a short core regression using the selected authoritative profile."""
import argparse
from pathlib import Path
import subprocess
import sys

from build_support import ROOT, add_run_arguments
sys.path.insert(0, str(ROOT/"src"))
from vibfpga.project_profile import load_profile


def command(args):
    profile=load_profile(args.profile)
    if profile["kind"]!="cwru_classifier":
        raise ValueError("quick core smoke requires a CWRU classifier profile; use module sensor or field-sim for SEN1/FCL1")
    model=Path(profile["model"]).resolve()
    if args.model and args.model.resolve()!=model:
        raise ValueError("MODEL conflicts with PROFILE; use the matching profile or an explicit core module command")
    result=[sys.executable,str(ROOT/"scripts/build_core.py"),"--model",str(model),
            "--lanes",str(profile["lanes"]),"--frames","14","--build-root",str(args.build_root)]
    if args.run_id:result += ["--run-id",args.run_id]
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile",default="cwru-neighbor3")
    parser.add_argument("--model",type=Path,help="Optional explicit model; must match the selected profile")
    add_run_arguments(parser)
    args=parser.parse_args()
    try:
        selected=command(args)
    except ValueError as error:
        parser.error(str(error))
    subprocess.run(selected,check=True,cwd=ROOT)


if __name__=="__main__":main()
