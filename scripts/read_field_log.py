#!/usr/bin/env python3
"""Decode an already-read FCL1 binary, without opening any physical device."""
import argparse
import json
from pathlib import Path
from vibfpga.field_log import parse_field_log

if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("log",type=Path)
    p.add_argument("--model-sha256")
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    result=json.dumps(parse_field_log(a.log.read_bytes(),expected_model_sha256=a.model_sha256),indent=2)+"\n"
    if a.output:a.output.write_text(result)
    else:print(result,end="")
