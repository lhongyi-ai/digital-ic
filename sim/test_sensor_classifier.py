"""Directed transaction and integer-reference checks for the field wrapper."""
import hashlib
import json
import os
from pathlib import Path

import cocotb
import numpy as np
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge, Timer, with_timeout

from vibfpga.field import raw_to_core
from vibfpga.fixed import classify

COUNTERS = ("accepted_samples", "dropped_samples", "canceled_frames", "clip_count", "protocol_errors")


def signed(value, bits=32):
    value = int(value)
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def configuration():
    manifest = json.loads(Path(os.environ["SENSOR_CLASSIFIER_MANIFEST"]).read_text())
    model_path = Path(manifest["model"])
    assert hashlib.sha256(model_path.read_bytes()).hexdigest() == manifest["model_sha256"]
    return manifest, json.loads(model_path.read_text())


def counters(dut):
    return {name: int(getattr(dut, name).value) for name in COUNTERS}


def output_snapshot(dut):
    names = ("out_frame_id", "out_logits", "out_class", "out_error", "cycles_pre", "cycles_dft",
             "cycles_power", "cycles_nn", "cycles_total", "out_first_service_cycle", "out_last_service_cycle")
    return {name: int(getattr(dut, name).value) for name in names}


def raw_cases(model):
    t = np.arange(256)
    rng = np.random.default_rng(847)
    return [np.zeros(256, dtype=np.int64), np.full(256, -153, dtype=np.int64),
            np.rint(200 * np.cos(2*np.pi*model["bins"][3]*t/256 + 0.31)).astype(np.int64),
            np.rint(450 * np.sin(2*np.pi*(model["bins"][5]+0.375)*t/256 + 1.2)).astype(np.int64),
            np.resize(np.array([-32768, -1025, -1024, -1023, 1022, 1023, 1024, 32767]), 256),
            rng.integers(-1200, 1201, size=256, dtype=np.int64)]


def expected(raw, model):
    result = classify(raw_to_core(np.asarray(raw, dtype=np.int64)), model)
    return {"logits": list(map(int, result["logits"])), "class_id": int(result["class_id"]),
            "raw_sha256": hashlib.sha256(np.asarray(raw, dtype="<i2").tobytes()).hexdigest(),
            "clip_count": int(np.count_nonzero((np.asarray(raw) < -1024) | (np.asarray(raw) > 1023)))}


async def reset(dut):
    await FallingEdge(dut.clk)
    dut.rst.value = 1
    dut.gap.value = 0
    dut.in_valid.value = 0
    dut.out_ready.value = 0
    await ClockCycles(dut.clk, 4)
    await FallingEdge(dut.clk)
    dut.rst.value = 0
    await Timer(1, unit="ns")
    assert counters(dut) == dict.fromkeys(COUNTERS, 0)
    assert int(dut.partial_samples.value) == 0 and int(dut.busy.value) == 0
    assert int(dut.out_valid.value) == 0


async def initialize(dut):
    dut.rst.value = 1
    dut.gap.value = 0
    dut.in_valid.value = 0
    dut.in_sample.value = 0
    dut.in_service_cycle.value = 0
    dut.out_ready.value = 0
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns", impl="gpi").start())
    await reset(dut)


async def send(dut, raw, first_cycle, *, stride=15000, pause_seed=None, respect_ready=True):
    rng = np.random.default_rng(pause_seed) if pause_seed is not None else None
    for index, value in enumerate(raw):
        await FallingEdge(dut.clk)
        dut.in_valid.value = 0
        if rng is not None and index % 13 == 0:
            await ClockCycles(dut.clk, int(rng.integers(1, 4)))
            await FallingEdge(dut.clk)
        if respect_ready and not int(dut.in_ready.value):
            await with_timeout(RisingEdge(dut.in_ready), 20, "ms")
            await FallingEdge(dut.clk)
        if respect_ready:
            assert int(dut.in_ready.value) == 1
        dut.in_sample.value = int(value) & 65535
        dut.in_service_cycle.value = (first_cycle + index * stride) & 0xffffffff
        dut.in_valid.value = 1
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")
        dut.in_valid.value = 0


async def receive(dut, reference, frame_id, first_cycle, *, stride=15000, stalls=13, transfer=True):
    if not int(dut.out_valid.value):
        await with_timeout(RisingEdge(dut.out_valid), 20, "ms")
    await Timer(1, unit="ns")
    result = output_snapshot(dut)
    logits = [signed((result["out_logits"] >> (32*i)) & 0xffffffff) for i in range(3)]
    assert result["out_frame_id"] == frame_id
    assert logits == reference["logits"], (frame_id, logits, reference)
    assert result["out_class"] == reference["class_id"] and result["out_error"] == 0
    assert result["out_first_service_cycle"] == first_cycle & 0xffffffff
    assert result["out_last_service_cycle"] == (first_cycle + 255*stride) & 0xffffffff
    assert result["cycles_total"] == sum(result[k] for k in ("cycles_pre", "cycles_dft", "cycles_power", "cycles_nn"))
    assert int(dut.busy.value) == 1
    for _ in range(stalls):
        await FallingEdge(dut.clk)
        assert int(dut.out_valid.value) == 1
        assert output_snapshot(dut) == result
    if transfer:
        await FallingEdge(dut.clk)
        dut.out_ready.value = 1
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")
        dut.out_ready.value = 0
        assert int(dut.out_valid.value) == 0
    return {"frame_id": frame_id, "reference": reference, "output": result,
            "logits": logits, "stall_cycles_checked": stalls, "accepted": transfer}


async def cancel(dut, *, explicit, sample=None, simultaneous_ready=False):
    await FallingEdge(dut.clk)
    dut.gap.value = int(explicit)
    dut.in_valid.value = int(sample is not None)
    dut.in_sample.value = (sample or 0) & 65535
    dut.in_service_cycle.value = 98765
    dut.out_ready.value = int(simultaneous_ready)
    await Timer(1, unit="ns")
    assert int(dut.in_ready.value) == 0
    assert int(dut.out_valid.value) == 0, "cancel must suppress a same-edge output handshake"
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    dut.gap.value = 0
    dut.in_valid.value = 0
    dut.out_ready.value = 0
    await Timer(1, unit="ns")
    assert int(dut.out_valid.value) == 0
    assert int(dut.partial_samples.value) == 0 and int(dut.busy.value) == 0
    assert int(dut.in_ready.value) == 1, "next-cycle sample must be able to start a new window"


async def quiet(dut):
    for _ in range(25):
        await FallingEdge(dut.clk)
        assert int(dut.out_valid.value) == 0


def report(name, dut, outputs, **extra):
    manifest, _ = configuration()
    result = {**manifest, "case": name, "status": "passed", "outputs": outputs,
              "final_counters": counters(dut), "physical_board_tested": False, **extra}
    (Path(os.environ["SENSOR_CLASSIFIER_BUILD"]) / f"case_{name}.json").write_text(json.dumps(result, indent=2) + "\n")


@cocotb.test()
async def continuous_numeric_and_timestamp_wrap(dut):
    await initialize(dut)
    _, model = configuration()
    cases = raw_cases(model) * 2
    refs = [expected(raw, model) for raw in cases]
    starts = [(0xfffff000 + i*256*15000) & 0xffffffff for i in range(len(cases))]

    async def producer():
        for i, raw in enumerate(cases):
            await send(dut, raw, starts[i], pause_seed=i)

    task = cocotb.start_soon(producer())
    outputs = [await receive(dut, ref, i, starts[i], stalls=(i*17)%61)
               for i, ref in enumerate(refs)]
    await task
    await quiet(dut)
    assert counters(dut) == {"accepted_samples": 12*256, "dropped_samples": 0, "canceled_frames": 0,
                             "clip_count": sum(r["clip_count"] for r in refs), "protocol_errors": 0}
    assert int(dut.partial_samples.value) == 0 and int(dut.busy.value) == 0
    assert outputs[0]["output"]["out_last_service_cycle"] < outputs[0]["output"]["out_first_service_cycle"]
    report("continuous", dut, outputs, distinct_inputs=6, input_frames=12,
           timestamp_wrap_checked=True, deterministic_random_input_pauses=True)


@cocotb.test()
async def long_stall_overrun_cancels_and_recovers(dut):
    await initialize(dut)
    _, model = configuration()
    a, b, c = raw_cases(model)[1:4]
    await send(dut, a, 1000)
    await send(dut, b, 5000000)
    first = await receive(dut, expected(a, model), 0, 1000, transfer=False)
    assert int(dut.in_ready.value) == 0
    held = output_snapshot(dut)
    await ClockCycles(dut.clk, 30000)
    await FallingEdge(dut.clk)
    assert int(dut.out_valid.value) == 1 and output_snapshot(dut) == held
    await cancel(dut, explicit=False, sample=32767)
    assert counters(dut) == {"accepted_samples": 512, "dropped_samples": 1, "canceled_frames": 2,
                             "clip_count": 0, "protocol_errors": 1}
    # The first sample of the replacement frame is on the next clock after cancel.
    await send(dut, c, 0xfffffff0, respect_ready=False)
    recovered = await receive(dut, expected(c, model), 2, 0xfffffff0)
    await quiet(dut)
    assert counters(dut) == {"accepted_samples": 768, "dropped_samples": 1, "canceled_frames": 2,
                             "clip_count": 0, "protocol_errors": 1}
    # Explicitly exercise the full-queue credit path: the same edge delivers
    # one output and accepts the first sample of a replacement window.
    await send(dut, a, 10000000)
    await send(dut, b, 14000000)
    credit_output = await receive(dut, expected(a, model), 3, 10000000, transfer=False)
    assert int(dut.in_ready.value) == 0
    await FallingEdge(dut.clk)
    dut.in_valid.value = 1
    dut.in_sample.value = int(c[0]) & 65535
    dut.in_service_cycle.value = 18000000
    dut.out_ready.value = 1
    await Timer(1, unit="ns")
    assert int(dut.in_ready.value) == 1 and int(dut.out_valid.value) == 1
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    dut.in_valid.value = 0
    dut.out_ready.value = 0
    assert int(dut.partial_samples.value) == 1
    assert int(dut.accepted_samples.value) == 1281
    assert int(dut.protocol_errors.value) == 1
    credit_output["accepted"] = True
    credit_output["same_edge_new_window_credit"] = True
    await send(dut, c[1:], 18000000 + 15000)
    fourth = await receive(dut, expected(b, model), 4, 14000000)
    fifth = await receive(dut, expected(c, model), 5, 18000000)
    await quiet(dut)
    assert counters(dut) == {"accepted_samples": 1536, "dropped_samples": 1, "canceled_frames": 2,
                             "clip_count": 0, "protocol_errors": 1}
    report("overrun", dut, [first, recovered, credit_output, fourth, fifth], long_output_stall_cycles=30000,
           canceled_ids=[0, 1], recovery_id=2, discarded_sample_not_counted_as_clip=True,
           full_metadata_queue_same_edge_output_and_first_input=True)


@cocotb.test()
async def explicit_gap_cancels_complete_partial_and_stalled_output(dut):
    await initialize(dut)
    _, model = configuration()
    a, b, c = raw_cases(model)[1:4]
    await send(dut, a, 700)
    await send(dut, b[:37], 9000000)
    first = await receive(dut, expected(a, model), 0, 700, transfer=False)
    assert int(dut.partial_samples.value) == 37
    await cancel(dut, explicit=True, sample=32767, simultaneous_ready=True)
    assert counters(dut) == {"accepted_samples": 293, "dropped_samples": 1, "canceled_frames": 2,
                             "clip_count": 0, "protocol_errors": 1}
    await send(dut, c, 123, respect_ready=False)
    recovered = await receive(dut, expected(c, model), 2, 123)
    # A gap without an accompanying sample is an event, not a dropped sample.
    await cancel(dut, explicit=True)
    assert counters(dut) == {"accepted_samples": 549, "dropped_samples": 1, "canceled_frames": 2,
                             "clip_count": 0, "protocol_errors": 2}
    await send(dut, a, 999)
    last = await receive(dut, expected(a, model), 3, 999)
    await quiet(dut)
    assert counters(dut) == {"accepted_samples": 805, "dropped_samples": 1, "canceled_frames": 2,
                             "clip_count": 0, "protocol_errors": 2}
    report("gap", dut, [first, recovered, last], canceled_ids=[0, 1],
           simultaneous_out_ready_cannot_deliver_cancelled_frame=True,
           gap_without_sample_increments_event_only=True)


@cocotb.test()
async def partial_reset_clears_counters_and_restarts_ids(dut):
    await initialize(dut)
    _, model = configuration()
    partial = raw_cases(model)[4][:13]
    await send(dut, partial, 400)
    assert int(dut.accepted_samples.value) == 13 and int(dut.partial_samples.value) == 13
    assert int(dut.clip_count.value) == int(np.count_nonzero((partial < -1024) | (partial > 1023)))
    assert int(dut.busy.value) == 0
    await reset(dut)
    raw = np.resize(np.array([-1024, 1023], dtype=np.int64), 256)
    await send(dut, raw, 0xfffffff0)
    output = await receive(dut, expected(raw, model), 0, 0xfffffff0)
    await quiet(dut)
    assert counters(dut) == {"accepted_samples": 256, "dropped_samples": 0, "canceled_frames": 0,
                             "clip_count": 0, "protocol_errors": 0}
    report("reset", dut, [output], partial_samples_cancelled_by_reset=13,
           exact_clip_endpoints_not_counted_as_clipping=True, reset_restarts_frame_id=0)
