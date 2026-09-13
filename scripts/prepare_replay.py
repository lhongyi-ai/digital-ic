#!/usr/bin/env python3
"""Pack the exported validation waveforms for standalone Flash replay."""
import argparse
import json
from pathlib import Path
import numpy as np
from vibfpga.board import build_replay_image

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument("--model",type=Path,default=ROOT/"artifacts/model/model.json")
p.add_argument("--vectors",type=Path,default=ROOT/"artifacts/vectors")
p.add_argument("--output",type=Path,default=ROOT/"build/replay.bin")
p.add_argument("--run-frames",type=int,default=1000)
p.add_argument("--period",type=int,default=1000)
a=p.parse_args()
files=sorted(a.vectors.glob("replay_*.hex"))[:16]
if not files:raise ValueError("no exported validation waveform files")
frames=np.asarray([[int(word,16) for word in path.read_text().split()] for path in files],dtype=np.uint16).view(np.int16)
blob,meta=build_replay_image(frames,a.model,period_cycles=a.period,run_frames=a.run_frames)
meta["source_files"]=[str(p.resolve()) for p in files]
a.output.parent.mkdir(parents=True,exist_ok=True)
a.output.write_bytes(blob)
a.output.with_suffix(".json").write_text(json.dumps(meta,indent=2)+"\n")
np.save(a.output.with_suffix(".npy"),frames)
print(a.output)
