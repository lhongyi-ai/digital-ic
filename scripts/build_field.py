#!/usr/bin/env python3
"""Synthesize/route the separate N256 field-classification firmware; never flash."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from build_board import logged
from build_support import add_run_arguments, run_path, yosys_quote, input_hashes, require_unchanged, tool_identity

ROOT=Path(__file__).resolve().parents[1]
SOURCES=["rtl/platform/spram16k.sv","rtl/core/sync_fifo.sv","rtl/io/spi_master.sv",
         "rtl/io/flash_stream.sv","rtl/io/adxl345_capture.sv","rtl/core/vib_coeff_rom.sv",
         "rtl/core/vibration_core.sv","rtl/io/sensor_classifier.sv","rtl/upduino_field.sv"]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model",type=Path,required=True)
    p.add_argument("--lanes",type=int,choices=(1,4),default=1)
    p.add_argument("--allow-fixture",action="store_true")
    p.add_argument("--total-samples",type=int,default=480000)
    add_run_arguments(p)
    a=p.parse_args()
    path=a.model.resolve();m=json.loads(path.read_text())
    fixture=m.get("training_status")=="synthetic_fixture_not_for_deployment"
    if fixture and not a.allow_fixture:p.error("synthetic model needs --allow-fixture; not deployment evidence")
    if not fixture and m.get("training_status")!="trained_field_records":p.error("requires a separately trained field model")
    if m.get("n")!=256 or m.get("sample_rate_hz")!=800 or m.get("feature_mode")!="single_bin" or m.get("profile")!="adxl345_field_states":
        p.error("only the N256/800Hz/16x16x3 field profile is supported")
    if not 1<=a.total_samples<=480000:p.error("total-samples must be 1..480000")
    frozen_path=path.parent.parent/"frozen.json"
    frozen=json.loads(frozen_path.read_text())
    for name,sha in frozen["files"].items():
        if hashlib.sha256((frozen_path.parent/name).read_bytes()).hexdigest()!=sha:p.error(f"frozen artifact changed: {name}")
    model_hash=hashlib.sha256(path.read_bytes()).hexdigest()
    # MODEL_HASH is indexed least-significant byte first on the wire.
    hash_literal=int.from_bytes(bytes.fromhex(model_hash),"little")
    out=run_path(a, f"field_board_l{a.lanes}");out.mkdir(parents=True,exist_ok=True)
    script="read_verilog -defer -sv -DICE40 "+" ".join(SOURCES)+";\n"
    script+=(f'chparam -set LANES {a.lanes} -set MODEL_DIR "{path.parent}" -set HIDDEN_SHIFT {m["hidden_shift"]} '
             f"-set MODEL_HASH 256'h{hash_literal:064x} -set SYNTHETIC_MODEL {int(fixture)} "
             f'-set TOTAL_SAMPLES {a.total_samples} -set AXIS {"xyz".index(m["axis"])} upduino_field;\n'
             f"synth_ice40 -dsp -top upduino_field -json {yosys_quote(out/'netlist.json')};\nstat\n")
    (out/"synth.ys").write_text(script)
    (out/"reference.pcf").write_text("""# Provisional UPduino v3.x mapping; board revision and oscillator jumper must be checked physically.
set_io clk12 20
set_io flash_cs_n 16
set_io flash_sclk 15
set_io flash_mosi 14
set_io flash_miso 17
set_io sensor_cs_n 23
set_io sensor_sclk 25
set_io sensor_mosi 26
set_io sensor_miso 27
set_io sensor_drdy 32
set_io status_done 21
set_io status_error 12
set_io status_running 13
""")
    inputs=[ROOT/s for s in SOURCES]+[p for p in path.parent.iterdir() if p.is_file()]+[out/"reference.pcf"]
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    (out/"report.json").unlink(missing_ok=True)
    logged(["yosys","-Q","-T","-s",str(out/"synth.ys")],out/"synthesis.log")
    logged(["nextpnr-ice40","--up5k","--package","sg48","--freq","12","--seed","1",
            "--pcf",str(out/"reference.pcf"),"--json",str(out/"netlist.json"),"--asc",str(out/"board.asc"),
            "--report",str(out/"timing.json")],out/"place_route.log")
    logged(["icepack",str(out/"board.asc"),str(out/"board.bin")],out/"icepack.log")
    if hashes!={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}:raise RuntimeError("build inputs changed during execution")
    timing=json.loads((out/"timing.json").read_text())
    report={"top":"upduino_field","lanes":a.lanes,"n":256,"rate_hz":800,"target_samples":a.total_samples,
            "source_kind":m["source_kind"],"synthetic_model_not_for_deployment":fixture,"model_sha256":model_hash,
            "source_sha256":hashes,"target_clock_mhz":12,"seed":1,"utilization":timing["utilization"],
            "fmax":timing["fmax"],"place_route_completed":True,
            "tool_versions":{name:subprocess.check_output([name,"--version"],text=True,stderr=subprocess.STDOUT).strip() for name in ("yosys","nextpnr-ice40")},
            "bitstream_sha256":hashlib.sha256((out/"board.bin").read_bytes()).hexdigest(),
            "physical_board_programmed":False,"board_profile_verified":False,"power_measured":False,"log_format":"FCL1"}
    (out/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(out/"report.json")


if __name__=="__main__":main()
