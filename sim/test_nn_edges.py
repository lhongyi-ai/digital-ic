"""Directed full-frame tests using untrained build-local NN boundary fixtures."""
import hashlib
import json
import os
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge, Timer, ValueChange, with_timeout


def signed(value, bits):
    value = int(value)
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def bytes16(value):
    value = int(value)
    return [(value >> (8 * i)) & 255 for i in range(16)]


async def reset(dut):
    await FallingEdge(dut.clk)
    dut.rst.value = 1
    dut.in_valid.value = 0
    dut.in_last.value = 0
    dut.out_ready.value = 0
    await ClockCycles(dut.clk, 4)
    await FallingEdge(dut.clk)
    dut.rst.value = 0
    await Timer(1, unit="ns")
    assert int(dut.out_valid.value) == 0
    assert int(dut.out_error.value) == 0
    assert int(dut.probe_error.value) == 0
    assert int(dut.protocol_errors.value) == 0
    for _ in range(12):
        await FallingEdge(dut.clk)
        assert int(dut.out_valid.value) == 0, "a cancelled frame reappeared after reset"


async def send(dut, raw, frame_id):
    for index, sample in enumerate(raw):
        await FallingEdge(dut.clk)
        dut.in_valid.value = 1
        dut.in_sample.value = int(sample) & 65535
        dut.in_frame_id.value = frame_id
        dut.in_last.value = int(index == len(raw) - 1)
        await Timer(1, unit="ns")
        if not int(dut.in_ready.value):
            await with_timeout(RisingEdge(dut.in_ready), 20, "ms")
        await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.in_valid.value = 0
    dut.in_last.value = 0


async def inspect_nn_stores(dut, expected):
    """Compare the actual pre-store 40-bit result for every real NN output.

    These are passive simulation-only hierarchy probes, not added deployment
    debug outputs. Wait through the DSP without per-cycle Python polling.
    """
    records = []
    seen = set()
    while len(records) < 19:
        if not int(dut.probe_store.value):
            await with_timeout(RisingEdge(dut.probe_store), 20, "ms")
        await FallingEdge(dut.clk)
        if not int(dut.probe_store.value):
            continue
        layer, index = int(dut.probe_layer.value), int(dut.probe_index.value)
        assert (layer, index) not in seen, "NN output was stored twice"
        seen.add((layer, index))
        actual = signed(dut.probe_accumulator.value, 40)
        target = expected["hidden_acc" if layer == 0 else "output_acc"][index]
        assert actual == target, (layer, index, actual, target)
        assert bytes16(dut.probe_features.value) == expected["features"]
        records.append({"layer": layer, "index": index, "accumulator": actual})
    assert seen == {(0, i) for i in range(16)} | {(1, i) for i in range(3)}
    return records


def snapshot(dut):
    names = ("out_frame_id", "out_logits", "out_class", "out_error", "cycles_pre",
             "cycles_dft", "cycles_power", "cycles_nn", "cycles_total")
    return {name: int(getattr(dut, name).value) for name in names}


async def check_frame(dut, vector, frame_id, purpose, transfer=True):
    expected = vector["expected"]
    inspection = cocotb.start_soon(inspect_nn_stores(dut, expected))
    await send(dut, vector["raw"], frame_id)
    if not int(dut.out_valid.value):
        await with_timeout(RisingEdge(dut.out_valid), 20, "ms")
    await Timer(1, unit="ns")
    output = snapshot(dut)
    actual_logits = [signed((output["out_logits"] >> (32 * i)) & 0xffffffff, 32) for i in range(3)]
    assert output["out_frame_id"] == frame_id
    assert actual_logits == expected["logits"], (purpose, actual_logits, expected["logits"])
    assert output["out_class"] == expected["class_id"], (purpose, output, expected)
    assert output["out_error"] == expected["error"], (purpose, output, expected)
    assert int(dut.probe_error.value) == expected["error"]
    assert bytes16(dut.probe_hidden.value) == expected["hidden"]
    assert output["cycles_total"] == sum(output[k] for k in ("cycles_pre", "cycles_dft", "cycles_power", "cycles_nn"))
    assert int(dut.protocol_errors.value) == 0
    stores = await inspection
    # Hold both valid and invalid outputs; the error flag belongs to the payload.
    stall_cycles = 11
    for _ in range(stall_cycles):
        await FallingEdge(dut.clk)
        assert int(dut.out_valid.value) == 1
        assert snapshot(dut) == output, "error/class/logits/counters changed under output stall"
    if transfer:
        await FallingEdge(dut.clk)
        dut.out_ready.value = 1
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")
        dut.out_ready.value = 0
        assert int(dut.out_valid.value) == 0
        for _ in range(7):
            await FallingEdge(dut.clk)
            assert int(dut.out_valid.value) == 0, "duplicate output after its handshake"
    return {"frame_id": frame_id, "purpose": purpose, "input": vector["name"],
            "raw_sha256": vector["raw_sha256"], "output": output, "logits": actual_logits,
            "expected": expected, "nn_stores": stores,
            "stall_cycles_checked": stall_cycles, "accepted": transfer,
            "classification_usable": expected["error"] == 0}


@cocotb.test()
async def directed_nn_edges(dut):
    manifest_path = Path(os.environ["NN_EDGE_MANIFEST"])
    manifest = json.loads(manifest_path.read_text())
    fixture = Path(manifest["fixture_dir"])
    model = json.loads((fixture / "model.json").read_text())
    assert hashlib.sha256((fixture / "model.json").read_bytes()).hexdigest() == manifest["model_sha256"]
    vectors = {v["name"]: v for v in json.loads((fixture / "vectors.json").read_text())}
    dut.rst.value = 1
    dut.in_valid.value = 0
    dut.in_sample.value = 0
    dut.in_frame_id.value = 0
    dut.in_last.value = 0
    dut.out_ready.value = 0
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns", impl="gpi").start())
    await reset(dut)
    outputs, cancellations = [], []
    if "edge_layer" not in model:
        for frame_id, name in enumerate(("below", "overflow"), 1):
            # 'overflow' names the waveform amplitude, not an overflowing tie model.
            assert vectors[name]["expected"]["error"] == 0
            outputs.append(await check_frame(dut, vectors[name], frame_id, "lowest_index_tie"))
            assert outputs[-1]["output"]["out_class"] == model["expected_tie_winner"]
    else:
        for frame_id, (name, purpose) in enumerate((("below", "one_inside_INT32"),
                                                   ("boundary", "exact_INT32_boundary"),
                                                   ("overflow", "one_outside_INT32"),
                                                   ("below", "recovery_without_reset")), 1):
            outputs.append(await check_frame(dut, vectors[name], frame_id, purpose))
        # Reset after the overflow flag was raised in NN_STORE, before FINISH.
        await send(dut, vectors["overflow"]["raw"], 5)
        assert int(dut.probe_error.value) == 0
        await with_timeout(ValueChange(dut.probe_error), 20, "ms")
        await Timer(1, unit="ns")
        assert int(dut.probe_error.value) == 1
        assert int(dut.out_valid.value) == 0, "mid-NN reset test arrived after an output"
        cancellations.append({"frame_id": 5, "point": "error_raised_before_FINISH",
                              "arithmetic_error_before_reset": 1, "output_observed": False})
        await reset(dut)
        outputs.append(await check_frame(dut, vectors["below"], 6, "recovery_after_mid_NN_reset"))
        # A second reset cancels an already-valid, stalled invalid output.
        outputs.append(await check_frame(dut, vectors["overflow"], 7, "error_output_reset_while_stalled", transfer=False))
        assert int(dut.out_valid.value) == 1 and int(dut.out_error.value) == 1
        cancellations.append({"frame_id": 7, "point": "HOLD_with_unaccepted_error_output",
                              "arithmetic_error_before_reset": 1, "output_observed": True})
        await reset(dut)
        outputs.append(await check_frame(dut, vectors["boundary"], 8, "recovery_after_HOLD_reset"))
    for _ in range(32):
        await FallingEdge(dut.clk)
        assert int(dut.out_valid.value) == 0
    result = {**manifest, "suite": "NN_directed_INT32_edges_and_ties", "status": "passed",
              "checked_outputs": outputs, "accepted_outputs": sum(x["accepted"] for x in outputs),
              "reset_cancellations": cancellations,
              "checks": ["complete_raw_frames", "features_exact", "19_NN_final_dot_results_exact",
                         "hidden_activation_exact", "packed_INT32_logits_exact", "argmax_exact",
                         "error_mask_exact", "output_stall_stability", "no_duplicate_output",
                         "stage_cycle_sum", "zero_protocol_errors"],
              "overflow_output_policy": "low_32_bits_and_error_bit0; classification_is_invalid",
              "scope": "finite directed simulation; no trained-model evaluation, formal proof, or hardware execution"}
    Path(os.environ["NN_EDGE_REPORT"]).write_text(json.dumps(result, indent=2) + "\n")
