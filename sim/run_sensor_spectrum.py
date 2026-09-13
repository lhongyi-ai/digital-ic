import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from cocotb_tools.runner import get_runner
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_support import CachedRunner, add_run_arguments, run_path, yosys_quote


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--synth",action="store_true")
    parser.add_argument("--pnr",action="store_true",help="Route a standalone low-pin probe, not the sensor application")
    add_run_arguments(parser)
    a=parser.parse_args()
    model=ROOT/"artifacts/sensor_spectrum/model/model.json"
    build=run_path(a, "sensor_spectrum")
    build.mkdir(parents=True,exist_ok=True)
    sources=[ROOT/p for p in ("rtl/core/vib_coeff_rom.sv","rtl/core/vibration_core.sv","rtl/io/sensor_spectrum.sv")]
    if a.synth or a.pnr:
        top="sensor_spectrum_probe" if a.pnr else "sensor_spectrum"
        if a.pnr:sources.append(ROOT/"sim/sensor_spectrum_probe.sv")
        netlist=build/("probe.json" if a.pnr else "netlist.json")
        script=f'read_verilog -defer -sv {" ".join(yosys_quote(p) for p in sources)}; chparam -set MODEL_DIR "{model.parent}" {top}; synth_ice40 -dsp -top {top} -json {yosys_quote(netlist)}; stat'
        with (build/"synthesis.log").open("w") as log:
            subprocess.run(["yosys","-Q","-T","-p",script],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        design=json.loads(netlist.read_text())
        counts={}
        for cell in design["modules"][top]["cells"].values():counts[cell["type"]]=counts.get(cell["type"],0)+1
        (build/("probe_synthesis_report.json" if a.pnr else "synthesis_report.json")).write_text(json.dumps({"top":top,"cells":counts,
            "standalone_synthesis_only":True,"integrated_sensor_fit_proven":False,"physical_hardware_tested":False},indent=2)+"\n")
        if a.pnr:
            with (build/"probe_place_route.log").open("w") as log:
                subprocess.run(["nextpnr-ice40","--up5k","--package","sg48","--pcf-allow-unconstrained",
                    "--freq","12","--seed","1","--json",str(netlist),"--asc",str(build/"probe.asc"),
                    "--report",str(build/"probe_timing.json")],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
            timing=json.loads((build/"probe_timing.json").read_text())
            (build/"probe_report.json").write_text(json.dumps({"top":top,"probe_only_not_integrated_sensor":True,
                "fmax":timing["fmax"],"utilization":timing["utilization"],"physical_hardware_tested":False},indent=2)+"\n")
        print(counts);return
    report=build/"report.json";report.unlink(missing_ok=True)
    sys.path[:0]=[str(ROOT/"src"),str(ROOT/"sim")]
    runner=CachedRunner(a.build_root)
    runner.build(sources=sources,hdl_toplevel="sensor_spectrum",build_dir=build,
        parameters={"MODEL_DIR":f'"{model.parent}"'},
        build_args=["--assert","-DVIB_ASSERT","-Wno-fatal","-Wno-WIDTHEXPAND","-Wno-WIDTHTRUNC","-CFLAGS","-std=c++17"],
        always=True,log_file=build/"build.log")
    runner.test(hdl_toplevel="sensor_spectrum",test_module="test_sensor_spectrum",test_dir=build,
        results_xml=build/"results.xml",log_file=build/"test.log",
        extra_env={"SPECTRUM_MODEL":str(model),"SPECTRUM_REPORT":str(report),
            "PYTHONPATH":os.pathsep.join([str(ROOT/"src"),str(ROOT/"sim")])})
    if json.loads(report.read_text()).get("passed") is not True:raise RuntimeError("sensor spectrum failed")
    print(report)


if __name__=="__main__":main()
