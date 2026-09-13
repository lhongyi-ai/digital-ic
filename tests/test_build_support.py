"""Regression evidence must be fresh even when an HDL executable is reused."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_support as support
import build_sensor


def fixture_inputs(tmp_path):
    source = tmp_path / "core.sv"
    include = tmp_path / "config.svh"
    source.write_text('`include "config.svh"\nmodule core; localparam VALUE = 1; endmodule\n')
    include.write_text('`define VALUE 1\n')
    model = tmp_path / "model"
    model.mkdir()
    (model / "weights.hex").write_text("01\n")
    return source, include, model


def test_cache_key_binds_rtl_nested_includes_rom_parameters_tool_and_flags(tmp_path):
    source, include, model = fixture_inputs(tmp_path)
    params = {"LANES": 4, "MODEL_DIR": f'"{model}"'}
    def key(flags=("--assert",), tool="v1", parameters=None):
        return support.manifest_key(support.content_manifest([source], parameters or params, flags, tool=tool))
    initial = key()
    assert initial == key()
    for path in (source, include, model / "weights.hex"):
        previous = path.read_text()
        path.write_text(previous.replace("1", "2"))
        assert key() != initial
        path.write_text(previous)
    assert key(flags=("--coverage",)) != initial
    assert key(tool="v2") != initial
    assert key(parameters={**params, "LANES": 1}) != initial
    include.unlink()
    with pytest.raises(FileNotFoundError):
        key()


def test_named_runs_are_separate_and_reject_path_traversal(tmp_path):
    parser = argparse.ArgumentParser()
    support.add_run_arguments(parser)
    first = parser.parse_args(["--build-root", str(tmp_path), "--run-id", "first"])
    second = parser.parse_args(["--build-root", str(tmp_path), "--run-id", "second"])
    assert support.run_path(first, "core") != support.run_path(second, "core")
    first.run_id = "../escape"
    with pytest.raises(ValueError):
        support.run_path(first, "core")


def test_cached_compiler_always_runs_fresh_tests_and_detects_corrupt_executable(tmp_path, monkeypatch):
    source, _, model = fixture_inputs(tmp_path)
    calls = []
    class Runner:
        def build(self, **kwargs):
            calls.append("compile")
            (kwargs["build_dir"] / kwargs["hdl_toplevel"]).write_bytes(b"executable")
        def test(self, **kwargs):
            calls.append(str(kwargs["test_dir"]))
            assert not Path(kwargs["results_xml"]).exists(), "stale XML was not removed"
            Path(kwargs["results_xml"]).write_text('<testsuite><testcase name="fresh"/></testsuite>')
    monkeypatch.setattr(support, "get_space_safe_runner", Runner)
    monkeypatch.setattr(support, "tool_identity", lambda name: {"name": name, "version": "unit-test"})
    monkeypatch.delenv("VERILATOR_BIN", raising=False)
    monkeypatch.delenv("VERILATOR_ROOT", raising=False)
    config = dict(sources=[source], parameters={"MODEL_DIR": f'"{model}"'}, build_args=["--assert"], hdl_toplevel="core")
    for name in ("first", "second"):
        output = tmp_path / name
        runner = support.CachedRunner(tmp_path)
        runner.build(build_dir=output, **config)
        (output / "results.xml").write_text('<testsuite><testcase><failure/></testcase></testsuite>')
        runner.test(test_dir=output, hdl_toplevel="core", test_module="fresh")
        receipt = json.loads((output / "build_manifest.json").read_text())
        assert receipt["compiler_cache_hit"] is (name == "second")
        assert receipt["test_results_reused"] is False
    assert calls == ["compile", str(tmp_path / "first"), str(tmp_path / "second")]
    (runner.compiled / "core").write_bytes(b"corrupted executable")
    support.CachedRunner(tmp_path).build(build_dir=tmp_path / "third", **config)
    assert calls[-1] == "compile"


@pytest.mark.parametrize("xml", ['<testsuites/>', '<testsuite><testcase><skipped/></testcase></testsuite>',
                                 '<testsuite><testcase><failure/></testcase></testsuite>'])
def test_empty_skipped_or_failed_xml_is_not_passed_evidence(tmp_path, xml):
    path = tmp_path / "results.xml"
    path.write_text(xml)
    with pytest.raises(RuntimeError):
        support.require_xml_passed(path)


def sensor_setup(tmp_path, monkeypatch):
    out = tmp_path / "build/sensor_board_800hz_spectrum"
    out.mkdir(parents=True)
    (out / "report.json").write_text('{"place_route_completed": true}')
    for name in ("rtl/platform/spram16k.sv", "rtl/io/spi_master.sv", "rtl/io/flash_stream.sv",
                 "rtl/io/adxl345_capture.sv", "rtl/io/static_calibration.sv", "rtl/core/vib_coeff_rom.sv",
                 "rtl/core/vibration_core.sv", "rtl/io/sensor_spectrum.sv", "rtl/upduino_sensor.sv",
                 "artifacts/sensor_spectrum/model/model.json", "artifacts/sensor_spectrum/model/b1.hex"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n")
    monkeypatch.setattr(build_sensor, "ROOT", tmp_path)
    monkeypatch.setattr(build_sensor, "tool_identity", lambda name: {"name": name, "version": "test"})
    monkeypatch.setattr(sys, "argv", ["build_sensor.py", "--build-root", str(tmp_path / "build")])
    return out


def test_sensor_removes_old_success_before_failed_synthesis(tmp_path, monkeypatch):
    out = sensor_setup(tmp_path, monkeypatch)
    def fail(*args):
        raise RuntimeError("expected synthesis failure")
    monkeypatch.setattr(build_sensor, "logged", fail)
    with pytest.raises(RuntimeError, match="expected synthesis failure"):
        build_sensor.main()
    assert not (out / "report.json").exists()


@pytest.mark.parametrize("change_input", [False, True])
def test_sensor_report_binds_rom_rtl_constraints_and_refuses_midbuild_change(tmp_path, monkeypatch, change_input):
    out = sensor_setup(tmp_path, monkeypatch)
    def logged(command, log):
        log.write_text("tool test\n")
        if command[0] == "yosys":
            (out / "netlist.json").write_text('{"modules":{"upduino_sensor":{"cells":{}}}}')
        elif command[0] == "nextpnr-ice40":
            (out / "timing.json").write_text('{"fmax":{"clk":{"achieved":20,"constraint":12}},"utilization":{}}')
        else:
            (out / "board.bin").write_bytes(b"fixture bitstream")
            if change_input:
                (tmp_path / "rtl/upduino_sensor.sv").write_text("changed during tool run\n")
    monkeypatch.setattr(build_sensor, "logged", logged)
    if change_input:
        with pytest.raises(RuntimeError, match="input changed"):
            build_sensor.main()
        assert not (out / "report.json").exists()
    else:
        build_sensor.main()
        report = json.loads((out / "report.json").read_text())
        assert report["input_sha256"]["artifacts/sensor_spectrum/model/b1.hex"]
        assert report["input_sha256"][str((out / "reference.pcf").relative_to(tmp_path))]
        assert report["input_sha256"]["rtl/upduino_sensor.sv"]
        assert report["bitstream_sha256"] == support.sha(out / "board.bin")


def test_native_compile_failure_removes_old_paced_report(tmp_path, monkeypatch):
    import build_core
    out = tmp_path / "core_l4_artifacts/fixed_rate"
    out.mkdir(parents=True)
    report = out / "fixed_rate_1.json"
    report.write_text('{"status":"passed"}')
    monkeypatch.setattr(sys, "argv", ["build_core.py", "--model", str(ROOT / "artifacts/model/model.json"),
        "--lanes", "4", "--fixed-rate", "--frames", "1", "--build-root", str(tmp_path)])
    def fail(*args):
        raise RuntimeError("expected compile failure")
    monkeypatch.setattr(build_core, "cached_native_build", fail)
    with pytest.raises(RuntimeError, match="expected compile failure"):
        build_core.main()
    assert not report.exists()


def test_calibration_compile_failure_removes_old_case_and_aggregate(tmp_path, monkeypatch):
    import runpy
    out = tmp_path / "calibration_0"
    out.mkdir()
    report, aggregate = out / "report.json", tmp_path / "calibration_results.json"
    for path in (report, aggregate):
        path.write_text('{"passed":true}')
    class Runner:
        def __init__(self, *args):
            pass
        def build(self, **kwargs):
            raise RuntimeError("expected compile failure")
    monkeypatch.setattr(support, "CachedRunner", Runner)
    monkeypatch.setattr(sys, "argv", ["test_calibration.py", "--build-root", str(tmp_path)])
    with pytest.raises(RuntimeError, match="expected compile failure"):
        runpy.run_path(str(ROOT / "scripts/test_calibration.py"), run_name="__main__")
    assert not report.exists() and not aggregate.exists()


def test_release_missing_prerequisites_fail_with_actionable_message(tmp_path):
    import check_release_prerequisites
    with pytest.raises(RuntimeError, match="does not generate training fixtures"):
        check_release_prerequisites.check(tmp_path)


def test_quick_uses_profile_and_rejects_conflicting_model(tmp_path):
    import run_quick
    args=argparse.Namespace(profile="cwru-neighbor3",model=None,build_root=tmp_path,run_id="quick")
    command=run_quick.command(args)
    assert command[command.index("--model")+1] == str(ROOT/"artifacts/model_neighbor/model.json")
    assert command[command.index("--frames")+1] == "14"
    args.model=ROOT/"artifacts/model/model.json"
    with pytest.raises(ValueError,match="conflicts"):
        run_quick.command(args)


def test_current_release_prerequisites_do_not_require_paused_area_experiments(tmp_path):
    import check_release_prerequisites
    folder=tmp_path/"build/field_fixture/trained"
    files={}
    for name in ("model/model.json","training.json","test.json"):
        path=folder/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text("{}")
        files[name]=support.sha(path)
    source=tmp_path/"src/vibfpga/field.py"
    source.parent.mkdir(parents=True)
    source.write_text("# test fixture")
    (folder/"frozen.json").write_text(json.dumps({"files":files,"source_sha256":{"field.py":support.sha(source)}}))
    assert check_release_prerequisites.check(tmp_path)["ready"]
    with pytest.raises(RuntimeError,match="Missing build/field_area_experiments"):
        check_release_prerequisites.check(tmp_path,historical=True)
