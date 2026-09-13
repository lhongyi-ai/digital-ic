import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
from vibfpga.board import build_replay_image

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("program_board",ROOT/"scripts/program_board.py")
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def assets(tmp_path):
    profile=json.loads((ROOT/"configs/upduino-reference.json").read_text())
    binary=tmp_path/"board.bin"
    binary.write_bytes(b"test bitstream placeholder, never sent to hardware")
    model=ROOT/"artifacts/model/model.json"
    blob,meta=build_replay_image(np.zeros((1,1024),dtype=np.int16),model)
    image=tmp_path/"image.bin";image.write_bytes(blob)
    binary.with_name("report.json").write_text(json.dumps({"top":"upduino_replay","place_route_completed":True,
        "bitstream_sha256":hashlib.sha256(binary.read_bytes()).hexdigest(),"model_sha256":meta["model_sha256"]}))
    return profile,binary,image


def test_program_order_arms_only_after_new_firmware_and_input(tmp_path):
    profile,binary,image=assets(tmp_path)
    commands=module.programming_plan(profile,binary,tmp_path/"backup.bin",image)
    assert commands[0][3]=="-R"
    offsets=[int(c[c.index("-o")+1]) for c in commands[1:]]
    assert offsets==[0,0x40000,0x300000]
    assert all("-b" not in c for c in commands)
    assert not (tmp_path/"backup.bin").exists()


def test_program_rejects_changed_binary_and_existing_backup(tmp_path):
    profile,binary,image=assets(tmp_path)
    backup=tmp_path/"backup.bin";backup.write_bytes(b"previous capture")
    with pytest.raises(ValueError,match="already exists"):
        module.programming_plan(profile,binary,backup,image)
    binary.write_bytes(b"changed")
    with pytest.raises(ValueError,match="match successful"):
        module.programming_plan(profile,binary,tmp_path/"new.bin",image)
