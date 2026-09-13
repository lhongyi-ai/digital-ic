import argparse
import json
import sys
import os
from pathlib import Path

from cocotb_tools.runner import get_runner

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "sim")]
from build_support import CachedRunner, add_run_arguments, run_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sensor-only", action="store_true")
    parser.add_argument("--rate-code", type=lambda value: int(value, 0), default=0x0D,
                        choices=[0x0A, 0x0C, 0x0D])
    add_run_arguments(parser)
    args = parser.parse_args()
    configs = [] if args.sensor_only else [
        ("master", 0, 0, 6), ("master", 1, 1, 6),
        ("master", 0, 1, 6), ("master", 1, 0, 6),
        ("master", 0, 0, 1), ("master", 1, 1, 1)]
    configs.append(("sensor", 1, 1, 6))
    reports = []
    filename = f"spi_sensor_r{args.rate_code:02x}_results.json" if args.sensor_only else "spi_sensor_results.json"
    path = run_path(args, filename)
    path.unlink(missing_ok=True)
    for kind, cpol, cpha, half in configs:
        suffix = f"_r{args.rate_code:02x}" if kind == "sensor" else ""
        build = run_path(args, f"spi_{kind}_m{2*cpol+cpha}_h{half}{suffix}")
        build.mkdir(parents=True, exist_ok=True)
        report = build / "report.json"
        report.unlink(missing_ok=True)
        sources = [ROOT / "rtl/io/spi_master.sv"]
        if kind == "sensor":
            sources.append(ROOT / "rtl/io/adxl345_capture.sv")
            parameters = {"HALF_PERIOD": half, "POWERUP_CYCLES": 8,
                          "RATE_CODE": f"8'h{args.rate_code:02x}"}
            top = "adxl345_capture"
        else:
            parameters = {"CPOL": cpol, "CPHA": cpha, "HALF_PERIOD": half}
            top = "spi_master"
        runner = CachedRunner(args.build_root)
        runner.build(sources=sources, hdl_toplevel=top, parameters=parameters,
                     build_args=["--assert", "-CFLAGS", "-std=c++17"],
                     build_dir=build, always=True, log_file=build / "build.log")
        runner.test(hdl_toplevel=top, test_module="test_spi_sensor", test_dir=build,
                    build_dir=build, results_xml=build / "results.xml", log_file=build / "test.log",
                    extra_env={"SPI_TEST_KIND": kind, "SPI_CPOL": str(cpol),
                               "SPI_CPHA": str(cpha), "SPI_HALF_PERIOD": str(half),
                               "SPI_RATE_CODE": str(args.rate_code),
                               "SPI_REPORT_FILE": str(report)})
        reports.append(json.loads(report.read_text()))
    path.write_text(json.dumps({"hardware_measured": False, "results": reports}, indent=2) + "\n")
    print(path)


if __name__ == "__main__":
    main()
