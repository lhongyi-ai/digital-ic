import argparse
import json
import os
from pathlib import Path
from cocotb_tools.runner import get_runner

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--case",choices=["nominal","overflow","spectrum","all"],default="all")
    a=p.parse_args()
    cases=["nominal","overflow","spectrum"] if a.case=="all" else [a.case]
    for case in cases:
        total,retained=(88,80) if case=="nominal" else (256,256) if case=="spectrum" else (4,4)
        build=ROOT/"build"/f"sensor_system_{case}"
        build.mkdir(parents=True,exist_ok=True)
        report=build/"report.json";report.unlink(missing_ok=True)
        runner=get_runner("verilator")
        runner.build(sources=[ROOT/path for path in ["rtl/platform/spram16k.sv",
            "rtl/io/spi_master.sv","rtl/io/adxl345_capture.sv","rtl/io/static_calibration.sv",
            "rtl/io/flash_stream.sv","rtl/core/vib_coeff_rom.sv","rtl/core/vibration_core.sv",
            "rtl/io/sensor_spectrum.sv","rtl/upduino_sensor.sv"]],hdl_toplevel="sensor_system",
            parameters={"TOTAL_SAMPLES":total,"STORE_SAMPLES":retained,
                "LOG_SCAN_BYTES":8192,"SCAN_CHUNK_BYTES":257,"BANK_ADDR_BITS":8 if case=="spectrum" else 6,
                "ENABLE_SPECTRUM":int(case=="spectrum"),
                "SPECTRUM_MODEL_DIR":f'"{ROOT / "artifacts/sensor_spectrum/model"}"',
                "SERVICE_COUNTER_START":"32'hfff00000",
                "SENSOR_POWERUP_CYCLES":8,"WATCHDOG_CYCLES":600000},
            build_args=["--assert","-CFLAGS","-std=c++17"],always=True,
            build_dir=build,log_file=build/"build.log")
        runner.test(hdl_toplevel="sensor_system",test_module="test_sensor_system",test_dir=ROOT/"sim",
            build_dir=build,results_xml=build/"results.xml",log_file=build/"test.log",
            extra_env={"SENSOR_TOTAL":str(total),"SENSOR_STORE":str(retained),"SENSOR_CASE":case,
                "SENSOR_REPORT":str(report),"PYTHONPATH":os.pathsep.join([str(ROOT/"src"),str(ROOT/"sim")])})
        result=json.loads(report.read_text())
        if not result["passed"]:raise RuntimeError(result)
        print(report)


if __name__=="__main__":main()
