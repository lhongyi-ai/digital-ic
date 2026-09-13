"""Bit-exact frame tests against the independent exported integer model.

CORE_FRAMES defaults to 1000. Synthetic inputs and all exported validation
records repeat with unique IDs; every distinct input gets a full debug check.
"""
import json
import hashlib
import os
from pathlib import Path

import cocotb
import numpy as np
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge, Timer, with_timeout

from vibfpga.fixed import classify


def additional_dsp_cases(model):
    """Named finite DSP edge cases; these are not new classifier test records."""
    n=model["n"]
    t=np.arange(n,dtype=np.float64)
    k=int(model["bins"][3])
    entries=[]

    def add(name, wave, **description):
        rounded=np.rint(wave)
        clip_count=int(np.count_nonzero((rounded < -32768) | (rounded > 32767)))
        samples=np.clip(rounded,-32768,32767).astype(np.int64)
        entries.append((samples,{"name":name,"input_clipped_samples":clip_count,
                                "samples_sha256":hashlib.sha256(samples.astype("<i2").tobytes()).hexdigest(),
                                **description}))

    add("zero",np.zeros(n))
    add("constant_negative_DC",np.full(n,-1537))
    for phase in (0.0,np.pi/2,2.3):
        add(f"off_bin_phase_{phase:.6f}",14000*np.sin(2*np.pi*(k+0.375)*t/n+phase),
            frequency_bins=[k+0.375],phase_radians=phase)
    add("integer_bin_nonzero_phase",14000*np.sin(2*np.pi*k*t/n+np.pi/3),
        frequency_bins=[k],phase_radians=float(np.pi/3))
    for name,offset,amplitude in (("positive_clipped_sine",18000,24000),
                                  ("negative_clipped_sine",-18000,24000),
                                  ("both_polarities_clipped_sine",0,48000)):
        add(name,offset+amplitude*np.sin(2*np.pi*(k+0.375)*t/n+0.7),
            frequency_bins=[k+0.375],phase_radians=0.7,offset=offset,amplitude=amplitude)
        assert entries[-1][1]["input_clipped_samples"]>0
    f2=int(model["bins"][8])-0.375
    add("off_bin_two_tone",10000*np.sin(2*np.pi*(k+0.25)*t/n+0.2)+
        6000*np.sin(2*np.pi*f2*t/n+1.1),frequency_bins=[k+0.25,f2])
    assert len(entries)==10
    return [x for x,_ in entries],[d for _,d in entries]


def load_cases():
    model_path = Path(os.environ["CORE_MODEL"])
    model = json.loads(model_path.read_text())
    if os.environ.get("CORE_DSP_CASES")=="1":
        cases,_=additional_dsp_cases(model)
        return model,cases,[classify(x,model,model) for x in cases]
    n = model["n"]
    phase = np.arange(n, dtype=np.float64)
    rng = np.random.default_rng(8291)
    cases = [
        np.zeros(n, dtype=np.int64),
        np.full(n, -1537, dtype=np.int64),
        np.rint(14000 * np.sin(2 * np.pi * model["bins"][3] * phase/n)).astype(np.int64),
        np.where(np.arange(n) % 2 == 0, -32768, 32767).astype(np.int64),
        rng.integers(-32768, 32768, size=n, dtype=np.int64),
    ]
    # Include all available exported validation records, not their labels as inputs.
    vector_dir = "vectors_neighbor" if model.get("feature_mode") == "neighbor3_energy" else "vectors"
    for vector in sorted((model_path.parent.parent / vector_dir).glob("replay_*.json")):
        record = json.loads(vector.read_text())
        raw = [int(word, 16) for word in (vector.parent / record["samples_hex"]).read_text().split()]
        cases.append(np.array([x-65536 if x >= 32768 else x for x in raw], dtype=np.int64))
    return model, cases, [classify(x, model, model) for x in cases]


def signed(value, bits):
    value = int(value)
    return value - (1 << bits) if value & (1 << (bits-1)) else value


async def reset(dut):
    dut.rst.value = 1
    dut.in_valid.value = 0
    dut.in_sample.value = 0
    dut.in_frame_id.value = 0
    dut.in_last.value = 0
    dut.out_ready.value = 0
    await ClockCycles(dut.clk, 4)
    await FallingEdge(dut.clk)
    dut.rst.value = 0


async def send_samples(dut, samples, frame_id, *, last_at=None, gap_seed=None):
    rng = np.random.default_rng(gap_seed) if gap_seed is not None else None
    for index, sample in enumerate(samples):
        await FallingEdge(dut.clk)
        if rng is not None and index % 97 == 0:
            dut.in_valid.value = 0
            await ClockCycles(dut.clk, int(rng.integers(1, 4)))
            await FallingEdge(dut.clk)
        dut.in_valid.value = 1
        dut.in_sample.value = int(sample) & 0xffff
        dut.in_frame_id.value = frame_id
        dut.in_last.value = int(index == (len(samples)-1 if last_at is None else last_at))
        await Timer(1, unit="ns")
        if not int(dut.in_ready.value):
            await with_timeout(RisingEdge(dut.in_ready), 10, "ms")
        await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.in_valid.value = 0
    dut.in_last.value = 0


def output_snapshot(dut):
    fields = ["out_frame_id", "out_logits", "out_class", "out_error", "cycles_pre",
              "cycles_dft", "cycles_power", "cycles_nn", "cycles_total"]
    return {name: int(getattr(dut, name).value) for name in fields}


async def receive(dut, expected, frame_id, stalls=0):
    if not int(dut.out_valid.value):
        await with_timeout(RisingEdge(dut.out_valid), 10, "ms")
    await Timer(1, unit="ns")
    result = output_snapshot(dut)
    assert result["out_frame_id"] == frame_id
    actual_logits = [signed((result["out_logits"] >> (32*i)) & 0xffffffff, 32) for i in range(3)]
    assert actual_logits == list(map(int, expected["logits"])), (frame_id, actual_logits, expected["logits"])
    assert result["out_class"] == int(expected["class_id"])
    assert result["out_error"] == 0
    assert result["cycles_total"] == sum(result[k] for k in ("cycles_pre", "cycles_dft", "cycles_power", "cycles_nn"))
    for _ in range(stalls):
        await FallingEdge(dut.clk)
        assert int(dut.out_valid.value) == 1
        assert output_snapshot(dut) == result, "output payload changed during stall"
    await FallingEdge(dut.clk)
    dut.out_ready.value = 1
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    dut.out_ready.value = 0
    return result


async def check_debug(dut, expected_cases, frame_count):
    names = {1: "windowed", 2: "real", 3: "imag", 4: "powers", 5: "features", 6: "hidden", 7: "logits"}
    frame = -1
    counts = {}
    while True:
        await FallingEdge(dut.clk)
        if not int(dut.dbg_valid.value):
            continue
        kind = int(dut.dbg_kind.value)
        index = int(dut.dbg_index.value)
        value = signed(dut.dbg_value.value, 40)
        if kind == 0:
            frame += 1
            counts = {}
        expected = expected_cases[frame % len(expected_cases)]
        target = int(expected["mean"] if kind == 0 else expected[names[kind]][index])
        assert value == target, (frame, kind, index, value, target)
        counts[kind] = counts.get(kind, 0) + 1
        if kind == 7 and index == 2:
            n = len(expected["windowed"])
            assert counts == {0: 1, 1: n, 2: len(expected["real"]), 3: len(expected["imag"]), 4: 16, 5: 16, 6: 16, 7: 3}, counts
            if frame+1 == frame_count:
                return


@cocotb.test()
async def bit_exact_continuous_frames(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns", impl="gpi").start())
    await reset(dut)
    model, cases, expected = load_cases()
    frame_count = int(os.environ.get("CORE_FRAMES", "1000"))
    debug_count = min(len(cases), frame_count)
    debug_task = cocotb.start_soon(check_debug(dut, expected, debug_count))

    async def producer():
        for frame in range(frame_count):
            await send_samples(dut, cases[frame % len(cases)], frame, gap_seed=frame if frame < len(cases) else None)

    send_task = cocotb.start_soon(producer())
    result = None
    for frame in range(frame_count):
        result = await receive(dut, expected[frame % len(cases)], frame, stalls=(frame*13) % 9)
    await send_task
    await debug_task
    assert int(dut.protocol_errors.value) == 0
    await ClockCycles(dut.clk, 10)
    assert int(dut.out_valid.value) == 0
    report = {"n": model["n"], "lanes": int(os.environ["CORE_LANES"]),
              "bands": 3 if model.get("feature_mode") == "neighbor3_energy" else 1,
              "frames": frame_count, "distinct_inputs": len(cases), "debug_frames": debug_count,
              "model_sha256": hashlib.sha256(Path(os.environ["CORE_MODEL"]).read_bytes()).hexdigest(),
              "assertions_enabled": True, "status": "passed",
              "cycles": {k: v for k, v in result.items() if k.startswith("cycles_")}}
    if os.environ.get("CORE_DSP_CASES")=="1":
        _,descriptions=additional_dsp_cases(model)
        root=Path(__file__).resolve().parents[1]
        report.update({"suite":"additional_DSP_directed","cases":descriptions,
                       "checked_intermediates":["mean","windowed","real","imag","powers","features","hidden","logits"],
                       "input_sha256":{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in [root/"rtl/core/vibration_core.sv",root/"rtl/core/vib_coeff_rom.sv",
                                     Path(__file__).resolve(),root/"src/vibfpga/fixed.py",
                                     *Path(os.environ["CORE_MODEL"]).parent.glob("*.hex")]}})
    Path(os.environ["CORE_REPORT"]).write_text(json.dumps(report, indent=2)+"\n")


@cocotb.test()
async def malformed_frames_and_reset(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns", impl="gpi").start())
    await reset(dut)
    _, cases, expected = load_cases()
    n = len(cases[0])
    # Early last; missing last followed by a different frame ID; mid-frame ID change.
    await send_samples(dut, cases[0][:7], 100)
    await send_samples(dut, cases[0], 101, last_at=n+1)
    await send_samples(dut, cases[1][:5], 102, last_at=n+1)
    send_task = cocotb.start_soon(send_samples(dut, cases[2], 103))
    await receive(dut, expected[2], 103, stalls=11)
    await send_task
    assert int(dut.protocol_errors.value) >= 3
    # Reset aborts a partially received frame.
    await send_samples(dut, cases[3][:17], 104, last_at=n+1)
    await reset(dut)
    send_task = cocotb.start_soon(send_samples(dut, cases[4], 105))
    await receive(dut, expected[4], 105)
    await send_task
    # Reset while preprocessing/DFT is active; the stale frame cannot escape.
    await send_samples(dut, cases[2], 106)
    await ClockCycles(dut.clk, n*3+30)
    await reset(dut)
    send_task = cocotb.start_soon(send_samples(dut, cases[1], 107))
    await receive(dut, expected[1], 107)
    await send_task
    # Reset cancels an output held under backpressure.
    await send_samples(dut, cases[2], 108)
    await with_timeout(RisingEdge(dut.out_valid), 10, "ms")
    await reset(dut)
    assert int(dut.out_valid.value) == 0
    send_task = cocotb.start_soon(send_samples(dut, cases[0], 109))
    await receive(dut, expected[0], 109)
    await send_task


@cocotb.test()
async def full_buffers_during_output_stall(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns", impl="gpi").start())
    await reset(dut)
    _, cases, expected = load_cases()

    async def producer():
        for frame in range(5):
            await send_samples(dut, cases[frame], 200+frame)

    sender = cocotb.start_soon(producer())
    await with_timeout(RisingEdge(dut.out_valid), 10, "ms")
    await Timer(1, unit="ns")
    held = output_snapshot(dut)
    # The two raw buffers must fill while the first result remains blocked.
    await ClockCycles(dut.clk, 2*len(cases[0])+20)
    await FallingEdge(dut.clk)
    assert int(dut.in_ready.value) == 0
    assert output_snapshot(dut) == held
    await ClockCycles(dut.clk, 1000)
    for frame in range(5):
        await receive(dut, expected[frame], 200+frame)
    await sender
    await ClockCycles(dut.clk, 20)
    assert int(dut.out_valid.value) == 0
    assert int(dut.protocol_errors.value) == 0


@cocotb.test()
async def reset_cancels_each_processing_stage(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns", impl="gpi").start())
    await reset(dut)
    _, cases, expected = load_cases()
    # Deliberate white-box reset injection at RAM read/write, DFT, power and NN.
    for number, target_state in enumerate((2, 4, 8, 15, 20, 22)):
        await send_samples(dut, cases[4], 300+2*number)
        for _ in range(400000):
            if int(dut.state.value) == target_state:
                break
            await FallingEdge(dut.clk)
        else:
            raise AssertionError(f"processing state {target_state} was never reached")
        await reset(dut)
        sender = cocotb.start_soon(send_samples(dut, cases[2], 301+2*number))
        await receive(dut, expected[2], 301+2*number)
        await sender
