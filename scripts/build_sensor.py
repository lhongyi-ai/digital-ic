"""Build the standalone UPduino sensor logger; never programs a physical board."""
import argparse
import hashlib
import json
import re
from pathlib import Path

from build_board import logged
from build_support import add_run_arguments, run_path, yosys_quote, input_hashes, require_unchanged, tool_identity

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rate",type=int,choices=[100,400,800],default=800)
    p.add_argument("--total-samples",type=int)
    p.add_argument("--store-samples",type=int)
    p.add_argument("--axis",type=int,choices=[0,1,2],default=0)
    p.add_argument("--cal-offset-q8",type=int,default=0)
    p.add_argument("--cal-gain-q20",type=int,default=4096000)
    p.add_argument("--seed",type=int,default=1)
    p.add_argument("--no-spectrum",action="store_true")
    add_run_arguments(p)
    a=p.parse_args()
    total=a.total_samples if a.total_samples is not None else a.rate*600
    retained=a.store_samples if a.store_samples is not None else a.rate*30
    if not 1<=retained<=min(total,24000) or not 1<=total<2**31:
        p.error("Require 1 <= store_samples <= min(total_samples, 24000), total < 2^31")
    if not -(2**31)<=a.cal_offset_q8<2**31 or not 0<a.cal_gain_q20<2**31:
        p.error("Calibration offset must fit int32 and gain must be positive and < 2^31")
    rate_code={100:0x0a,400:0x0c,800:0x0d}[a.rate]
    suffix="" if a.no_spectrum else "_spectrum"
    out=run_path(a, f"sensor_board_{a.rate}hz{suffix}")
    out.mkdir(parents=True,exist_ok=True)
    (out/"report.json").unlink(missing_ok=True)
    sources=["rtl/platform/spram16k.sv","rtl/io/spi_master.sv","rtl/io/flash_stream.sv",
             "rtl/io/adxl345_capture.sv","rtl/io/static_calibration.sv","rtl/core/vib_coeff_rom.sv",
             "rtl/core/vibration_core.sv","rtl/io/sensor_spectrum.sv","rtl/upduino_sensor.sv"]
    script=("read_verilog -defer -sv -DICE40 "+" ".join(sources)+";\n"
            f"chparam -set TOTAL_SAMPLES {total} -set STORE_SAMPLES {retained} "
            f"-set RATE_CODE 8'h{rate_code:02x} -set AXIS {a.axis} "
            f"-set ENABLE_SPECTRUM {int(not a.no_spectrum)} "
            f'-set SPECTRUM_MODEL_DIR "{ROOT / "artifacts/sensor_spectrum/model"}" '
            f"-set CAL_OFFSET_Q8 32'h{a.cal_offset_q8 & 0xffffffff:08x} "
            f"-set CAL_GAIN_Q20 {a.cal_gain_q20} upduino_sensor;\n"
            f"synth_ice40 -dsp -top upduino_sensor -json {yosys_quote(out/'netlist.json')};\nstat\n")
    (out/"synth.ys").write_text(script)
    pcf="""# UPduino v3.x reference only; not physically verified.
# https://upduino.readthedocs.io/en/latest/features/specs.html
# Requires the OSC jumper connecting the external 12 MHz oscillator to gpio_20.
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
"""
    (out/"reference.pcf").write_text(pcf)
    inputs = [ROOT/s for s in sources] + [out/"reference.pcf", out/"synth.ys", Path(__file__).resolve()]
    if not a.no_spectrum:
        inputs += [p for p in (ROOT/"artifacts/sensor_spectrum/model").iterdir() if p.is_file()]
    hashes = input_hashes(inputs)
    versions = {name: tool_identity(name) for name in ("yosys", "nextpnr-ice40")}
    logged(["yosys","-Q","-T","-s",str(out/"synth.ys")],out/"synthesis.log")
    logged(["nextpnr-ice40","--up5k","--package","sg48","--freq","12","--seed",str(a.seed),
            "--pcf",str(out/"reference.pcf"),"--json",str(out/"netlist.json"),
            "--asc",str(out/"board.asc"),"--report",str(out/"timing.json")],out/"place_route.log")
    logged(["icepack",str(out/"board.asc"),str(out/"board.bin")],out/"icepack.log")
    require_unchanged(hashes)
    cells=json.loads((out/"netlist.json").read_text())["modules"]["upduino_sensor"]["cells"]
    counts={}
    for cell in cells.values(): counts[cell["type"]]=counts.get(cell["type"],0)+1
    report={"schema_version":1,"input_sha256":{str(Path(p).relative_to(ROOT)) if Path(p).is_relative_to(ROOT) else p: value for p,value in hashes.items()},"tool_versions":versions,"top":"upduino_sensor","rate_hz":a.rate,"total_samples":total,
            "store_samples":retained,"axis":a.axis,"cal_offset_q8":a.cal_offset_q8,
            "cal_gain_q20":a.cal_gain_q20,"target_clock_mhz":12,"seed":a.seed,
            "synthesis_cells":counts,"place_route_completed":True,
            "post_route_fmax":json.loads((out/"timing.json").read_text())["fmax"],
            "utilization":json.loads((out/"timing.json").read_text())["utilization"],
            "max_frequency_messages":re.findall(r"Max frequency.*",(out/"place_route.log").read_text()),
            "bitstream_sha256":hashlib.sha256((out/"board.bin").read_bytes()).hexdigest(),
            "physical_board_programmed":False,"board_profile_verified":False,"power_measured":False,
            "classifier_included":False,"spectrum_included":not a.no_spectrum,
            "log_format":f"SEN1, {128 if a.no_spectrum else 208}-byte header, 4-byte raw records"}
    (out/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))


if __name__=="__main__":main()
