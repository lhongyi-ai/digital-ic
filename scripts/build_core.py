#!/usr/bin/env python3
"""Run the core's actual HDL regression or UP5K synthesis; no board access."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import xml.etree.ElementTree as ET

from build_support import CachedRunner, add_run_arguments, run_path, yosys_quote, cached_native_build, require_unchanged

ROOT = Path(__file__).resolve().parents[1]


def require_passed(build, report):
    """A simulator exit status alone is not sufficient cocotb evidence."""
    tree = ET.parse(build / "results.xml")
    cases = list(tree.iter("testcase"))
    if not cases or list(tree.iter("failure")) or list(tree.iter("error")) or all(c.find("skipped") is not None for c in cases):
        raise RuntimeError(f"HDL regression did not pass: {build / 'results.xml'}")
    if json.loads(report.read_text()).get("status") != "passed":
        raise RuntimeError(f"missing successful regression report: {report}")


def clear_previous(build, report):
    for path in (build / "results.xml", report):
        path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lanes", type=int, choices=(1, 4), default=4)
    parser.add_argument("--model", type=Path, default=ROOT / "artifacts/fixtures/model/model.json")
    parser.add_argument("--frames", type=int, default=1000)
    parser.add_argument("--synth", action="store_true")
    parser.add_argument("--pnr", action="store_true", help="Route a low-pin core probe, not the application top")
    parser.add_argument("--fixed-rate", action="store_true", help="Native C++ 12 kHz paced replay plus overload/recovery")
    parser.add_argument("--arithmetic", action="store_true", help="Direct boundary tests of actual RTL arithmetic functions")
    parser.add_argument("--quant-boundary", action="store_true", help="Use an explicitly untrained boundary-shift profile in build/")
    parser.add_argument("--dsp-cases", action="store_true", help="Ten explicit phase/off-bin/clipped-waveform cases, in a separate report directory; use --frames 10 for one pass")
    parser.add_argument("--coverage", action="store_true", help="Verilator HDL coverage for cocotb runs; writes coverage.dat in the selected build directory")
    parser.add_argument("--build-dir", type=Path, help="Independent build directory; defaults remain unchanged when omitted")
    parser.add_argument("--vector", type=Path, default=ROOT / "artifacts/vectors/replay_000.hex")
    add_run_arguments(parser)
    args = parser.parse_args()
    if args.build_dir and args.run_id:
        parser.error("--build-dir and --run-id select different output layouts; choose one")
    if args.coverage and (args.fixed_rate or args.synth or args.pnr):
        parser.error("--coverage is currently supported only for the cocotb core/arithmetic regressions")
    coverage_args = ["--coverage", "--coverage-per-instance"] if args.coverage else []
    model_path = args.model.resolve()
    if args.quant_boundary:
        destination = (args.build_dir.resolve() / "boundary_model") if args.build_dir else run_path(args, "quant_boundary/model")
        destination.mkdir(parents=True, exist_ok=True)
        for path in model_path.parent.iterdir():
            if path.is_file() and path.resolve() != (destination / path.name).resolve():
                shutil.copyfile(path, destination / path.name)
        boundary_model = json.loads(model_path.read_text())
        boundary_model["feature_shifts"] = [0,1,2,3,7,8,15,16,24,30,31,32,33,34,40,63]
        boundary_model["verification_only"] = "deliberate quantizer boundary profile, not a trained evaluation model"
        (destination / "feature_shifts.hex").write_text("".join(f"{x:02x}\n" for x in boundary_model["feature_shifts"]))
        model_path = destination / "model.json"
        model_path.write_text(json.dumps(boundary_model, indent=2)+"\n")
    model = json.loads(model_path.read_text())
    bands = 3 if model.get("feature_mode") == "neighbor3_energy" else 1
    tag = model_path.parent.name if model_path.parent.name != "model" else model_path.parent.parent.name
    build = args.build_dir.resolve() if args.build_dir else run_path(args, f"core_{'dsp_' if args.dsp_cases else ''}l{args.lanes}_{tag}")
    build.mkdir(parents=True, exist_ok=True)
    if args.coverage:
        (build / "coverage.dat").unlink(missing_ok=True)
    sources = [ROOT / "rtl/core/vib_coeff_rom.sv", ROOT / "rtl/core/vibration_core.sv"]
    if args.fixed_rate:
        if model["n"] != 1024:
            parser.error("the native fixed-rate regression requires N=1024")
        sys.path.insert(0, str(ROOT / "src"))
        from vibfpga.fixed import classify
        samples = [int(line, 16) for line in args.vector.read_text().split()]
        samples = [x-65536 if x >= 32768 else x for x in samples]
        expected = classify(samples, model, model)
        native_build = build / "fixed_rate"
        native_build.mkdir(exist_ok=True)
        fixed_report = native_build / ("fixed_rate.json" if args.frames == 1000 else f"fixed_rate_{args.frames}.json")
        fixed_report.unlink(missing_ok=True)
        native_sources = [*sources, ROOT / "rtl/core/sync_fifo.sv", ROOT / "sim/fixed_rate_tb.sv", ROOT / "sim/fixed_rate_main.cpp"]
        native_parameters = {"LANES": args.lanes, "BANDS": bands, "HIDDEN_SHIFT": model["hidden_shift"],
                             "MODEL_DIR": f'"{model_path.parent}"', "RAW_FILE": f'"{args.vector.resolve()}"'}
        native_flags = ["--cc", "--exe", "-O3", "--assert", "-DVIB_ASSERT", "-Wno-fatal", "-Wno-WIDTHEXPAND",
                        "-Wno-WIDTHTRUNC", "--top-module", "fixed_rate_tb", "-CFLAGS", "-std=c++17 -O3"]
        executable, native_hashes = cached_native_build(args.build_root, native_build, native_sources, native_parameters,
            native_flags, lambda compiled: ["verilator", *native_flags, "--Mdir", str(compiled),
                *[f"-G{name}={value}" for name, value in native_parameters.items()], *map(str, native_sources)], "fixed_rate_tb")
        subprocess.run([str(executable), str(args.frames),
                        *map(str, expected["logits"]), str(expected["class_id"]),
                        str(fixed_report)], check=True, cwd=ROOT)
        require_unchanged(native_hashes)
        return
    if args.synth or args.pnr:
        top = "core_pnr_probe" if args.pnr else "vibration_core"
        prefix = "probe" if args.pnr else "core"
        if args.pnr:
            sources.append(ROOT / "sim/core_pnr_probe.sv")
        script = (f'read_verilog -defer -sv {" ".join(yosys_quote(p) for p in sources)}; '
                  f'chparam -set N {model["n"]} -set LANES {args.lanes} -set BANDS {bands} '
                  f'-set HIDDEN_SHIFT {model["hidden_shift"]} -set MODEL_DIR "{model_path.parent}" {top}; '
                  f'synth_ice40 -dsp -top {top} -json {yosys_quote(build / (prefix+".json"))}; stat')
        subprocess.run(["yosys", "-Q", "-T", "-l", str(build / (prefix+"_synth.log")), "-p", script], check=True, cwd=ROOT)
        if args.pnr:
            subprocess.run(["nextpnr-ice40", "--up5k", "--package", "sg48", "--json", str(build / "probe.json"),
                            "--pcf-allow-unconstrained", "--freq", "12", "--seed", "1",
                            "--report", str(build / "probe_timing.json"), "--asc", str(build / "probe.asc")],
                           check=True, cwd=ROOT)
        return
    from cocotb_tools.runner import get_runner
    os.environ["COCOTB_TRUST_INERTIAL_WRITES"] = "1"
    sys.path[:0] = [str(ROOT / "src"), str(ROOT / "sim")]
    runner = CachedRunner(args.build_root)
    if args.arithmetic:
        arithmetic_build = build / "arithmetic"
        clear_previous(arithmetic_build, arithmetic_build / "arithmetic.json")
        if args.coverage:
            (arithmetic_build / "coverage.dat").unlink(missing_ok=True)
        runner.build(sources=[*sources, ROOT / "sim/arithmetic_tb.sv"], hdl_toplevel="arithmetic_tb", build_dir=arithmetic_build,
                     parameters={"HIDDEN_SHIFT": model["hidden_shift"], "MODEL_DIR": f'"{model_path.parent}"'},
                     build_args=[*coverage_args, "-Wno-fatal", "-Wno-WIDTHEXPAND", "-Wno-WIDTHTRUNC", "-CFLAGS", "-std=c++17"], always=True)
        runner.test(hdl_toplevel="arithmetic_tb", test_module="test_arithmetic", test_dir=arithmetic_build,
                    test_args=["--coverage-per-instance"] if args.coverage else [],
                    extra_env={"CORE_HIDDEN_SHIFT": str(model["hidden_shift"]),
                               "CORE_REPORT": str(arithmetic_build / "arithmetic.json"),
                               "PYTHONPATH": os.pathsep.join([str(ROOT / "src"), str(ROOT / "sim")])})
        require_passed(arithmetic_build, arithmetic_build / "arithmetic.json")
        if args.coverage and not (arithmetic_build / "coverage.dat").is_file():
            raise RuntimeError("Verilator did not write the requested arithmetic coverage.dat")
        return
    clear_previous(build, build / "regression.json")
    runner.build(sources=sources, hdl_toplevel="vibration_core", build_dir=build,
                 parameters={"N": model["n"], "LANES": args.lanes, "BANDS": bands,
                             "HIDDEN_SHIFT": model["hidden_shift"], "MODEL_DIR": f'"{model_path.parent}"'},
                 build_args=[*coverage_args, "--assert", "-DVIB_ASSERT", "-Wno-fatal", "-Wno-WIDTHEXPAND", "-Wno-WIDTHTRUNC", "-CFLAGS", "-std=c++17"],
                 always=True)
    runner.test(hdl_toplevel="vibration_core", test_module="test_core", test_dir=build,
                test_args=["--coverage-per-instance"] if args.coverage else [],
                extra_env={"CORE_MODEL": str(model_path), "CORE_LANES": str(args.lanes),
                           "CORE_DSP_CASES":str(int(args.dsp_cases)),
                           "CORE_FRAMES": str(args.frames), "CORE_REPORT": str(build / "regression.json"),
                           "PYTHONPATH": os.pathsep.join([str(ROOT / "src"), str(ROOT / "sim")]),
                           "COCOTB_TRUST_INERTIAL_WRITES": "1"})
    require_passed(build, build / "regression.json")
    if args.coverage and not (build / "coverage.dat").is_file():
        raise RuntimeError("Verilator did not write the requested coverage.dat")


if __name__ == "__main__":
    main()
