#!/usr/bin/env python3
"""Build an UP5K SG48 reference bitstream. Never programs a board."""
import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from build_support import add_run_arguments, run_path, yosys_quote

ROOT = Path(__file__).resolve().parents[1]


def logged(command, destination):
    with destination.open("w") as f:
        result = subprocess.run(command, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT)
    if result.returncode:
        print(destination.read_text()[-6000:])
        raise SystemExit(f"Command failed; see {destination}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lanes", type=int, choices=(1, 4), default=4)
    p.add_argument("--model", type=Path, default=ROOT / "artifacts/model/model.json")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--clock-source", choices=("external12", "hfosc12"), default="external12")
    add_run_arguments(p)
    a = p.parse_args()
    model_path = a.model.resolve()
    model_bytes = model_path.read_bytes()
    model = json.loads(model_bytes)
    if model["n"] != 1024:
        raise ValueError("board replay requires N1024")
    bands=3 if model.get("feature_mode")=="neighbor3_energy" else 1
    out = run_path(a, f"board_{'neighbor_' if bands==3 else ''}l{a.lanes}{'_hfosc12' if a.clock_source == 'hfosc12' else ''}")
    out.mkdir(parents=True, exist_ok=True)
    sources = ["rtl/core/vib_coeff_rom.sv", "rtl/core/vibration_core.sv", "rtl/core/sync_fifo.sv",
               "rtl/platform/spram16k.sv", "rtl/io/spi_master.sv", "rtl/io/flash_stream.sv",
               "rtl/io/replay_source.sv", "rtl/upduino_replay.sv"]
    pcf = ROOT / "configs/upduino-replay.pcf"
    clock_script = out / "clock_constraint.py"
    if a.clock_source == "hfosc12":
        clock_script.write_text('ctx.addClock("system_clk", 13.2)\n')
    digest = hashlib.sha256(model_bytes).digest()
    inputs={(str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [*(ROOT / s for s in sources),ROOT / "configs/upduino-replay.pcf",pcf,Path(__file__).resolve(),*([clock_script] if a.clock_source == "hfosc12" else []),*model_path.parent.glob("*.hex"),model_path]}
    (out / "report.json").unlink(missing_ok=True)
    script = ("read_verilog -defer -sv -DICE40 " + " ".join(sources) + ";\n"
              f'chparam -set LANES {a.lanes} -set BANDS {bands} -set MODEL_DIR "{model_path.parent}" '
              f'-set HIDDEN_SHIFT {model["hidden_shift"]} -set INTERNAL_OSC {int(a.clock_source == "hfosc12")} '
              f"-set MODEL_HASH 256'h{digest[::-1].hex()} upduino_replay;\n"
              f"synth_ice40 -dsp -top upduino_replay -json {yosys_quote(out / 'netlist.json')};\nstat\n")
    (out / "synth.ys").write_text(script)
    logged(["yosys", "-Q", "-T", "-s", str(out / "synth.ys")], out / "synthesis.log")
    logged(["nextpnr-ice40", "--up5k", "--package", "sg48", "--freq", "13.2" if a.clock_source == "hfosc12" else "12", "--seed", str(a.seed),
            *(["--pre-pack", str(clock_script)] if a.clock_source == "hfosc12" else []),
            "--pcf", str(pcf), "--json", str(out / "netlist.json"),
            "--asc", str(out / "board.asc"), "--report", str(out / "timing.json")], out / "place_route.log")
    logged(["icepack", str(out / "board.asc"), str(out / "board.bin")], out / "icepack.log")
    if any(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=digest for p,digest in inputs.items()):
        raise RuntimeError("A build input changed during synthesis; rebuild from stable sources")
    design = json.loads((out / "netlist.json").read_text())
    cells = design["modules"]["upduino_replay"]["cells"]
    counts = {}
    for cell in cells.values():
        counts[cell["type"]] = counts.get(cell["type"], 0) + 1
    text = (out / "place_route.log").read_text()
    timing=json.loads((out / "timing.json").read_text())
    target = 13.2 if a.clock_source == "hfosc12" else 12
    if not timing["fmax"] or any(row["achieved"] < target or row["constraint"] < target - 0.001 for row in timing["fmax"].values()):
        raise RuntimeError(f"Routing did not meet and enforce the requested {target} MHz clock constraint")
    report = {"schema_version": 1, "top": "upduino_replay", "lanes": a.lanes,"bands":bands,
              "built_utc":datetime.now(timezone.utc).isoformat(),"input_sha256":inputs,
              "target_clock_mhz": 13.2 if a.clock_source == "hfosc12" else 12, "clock_source": a.clock_source, "nominal_clock_hz": 12000000,
              "clock_frequency_measured": False, "external_clock_input_used": a.clock_source == "external12", "seed": a.seed, "model_sha256": digest.hex(),
              "bitstream_sha256": hashlib.sha256((out / "board.bin").read_bytes()).hexdigest(),
              "synthesis_cells": counts,
              "post_route_fmax":timing["fmax"],"utilization":timing["utilization"],
              "max_frequency_messages": re.findall(r"Max frequency.*", text),
              "place_route_completed": True, "physical_board_programmed": False,
              "board_profile_verified": False, "power_measured": False}
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
