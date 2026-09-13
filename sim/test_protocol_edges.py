"""Independent, directed checks for three uncovered frame-protocol branches.

No production RTL, original coverage database, or frozen vector is modified.
All monitored transfers are sampled after falling-edge drivers settle, before
the next rising edge; no reset occurs while this scoreboard is active.
"""
import hashlib
import json
import os
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge, Timer, with_timeout
import numpy as np

from vibfpga.fixed import classify

WRAP_IDS = [0x80000000, 0xF1234567, 0xFFFFFFFF, 0x00000000,
            0x80000001, 0x00000001, 0x7FFFFFFF]
OUTPUT_FIELDS = ["out_frame_id", "out_logits", "out_class", "out_error",
                 "cycles_pre", "cycles_dft", "cycles_power", "cycles_nn", "cycles_total"]
DEBUG_FIELDS = {1: "windowed", 2: "real", 3: "imag", 4: "powers",
                5: "features", 6: "hidden", 7: "logits"}


def signed(value, bits):
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def load_frames():
    path = Path(os.environ["EDGE_MODEL"])
    model = json.loads(path.read_text())
    directory = path.parent.parent / ("vectors_neighbor" if model.get("feature_mode") == "neighbor3_energy" else "vectors")
    entries = []
    for index in range(9):
        vector_path = directory / f"replay_{index:03d}.json"
        vector = json.loads(vector_path.read_text())
        assert vector["provenance"]["split"] == "validation"
        raw_path = directory / vector["samples_hex"]
        samples = [signed(int(word, 16), 16) for word in raw_path.read_text().split()]
        expected = classify(samples, model)
        for name, value in expected.items():
            np.testing.assert_array_equal(value, vector["expected"][name], err_msg=str(vector_path)+":"+name)
        entries.append({"samples": samples, "expected": expected,
                        "source_json": str(vector_path), "source_hex": str(raw_path),
                        "provenance": vector["provenance"],
                        "hex_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest()})
    identifiers = [0x60000002, 0xA0000003, *WRAP_IDS]
    for entry, identifier in zip(entries, identifiers):
        entry["frame_id"] = identifier
    return model, entries


class ProtocolScoreboard:
    def __init__(self, dut, expected):
        self.dut, self.expected = dut, expected
        self.cycles = self.accepted_beats = self.input_stall_cycles = 0
        self.outputs = []
        self.output_stall_cycles = 0
        self.debug_frames = 0
        self.debug_counts = {}
        self.debug_active = False
        self.held = None
        self.stop = False
        self.last_forced_stall = -1
        self.forced_stall_remaining = 0

    async def run(self):
        while not self.stop:
            await FallingEdge(self.dut.clk)
            # Hold each newly offered result for seven clocks as well as
            # periodic stalls. A periodic pattern alone can miss all results
            # when a configuration's latency happens to align with readiness.
            if int(self.dut.out_valid.value) and self.last_forced_stall != len(self.outputs):
                self.last_forced_stall = len(self.outputs)
                self.forced_stall_remaining = 7
            self.dut.out_ready.value = int(self.forced_stall_remaining == 0 and self.cycles % 23 >= 7)
            if self.forced_stall_remaining:
                self.forced_stall_remaining -= 1
            await Timer(2, unit="ns")
            self.cycles += 1
            if int(self.dut.in_valid.value):
                if int(self.dut.in_ready.value):
                    self.accepted_beats += 1
                else:
                    self.input_stall_cycles += 1
            if int(self.dut.dbg_valid.value):
                kind, index = int(self.dut.dbg_kind.value), int(self.dut.dbg_index.value)
                value = signed(int(self.dut.dbg_value.value), 40)
                assert self.debug_frames < len(self.expected), "Unexpected extra processing frame"
                reference = self.expected[self.debug_frames]["expected"]
                if kind == 0:
                    assert not self.debug_active, "New frame started before prior debug sequence completed"
                    self.debug_active = True
                    self.debug_counts = {key: 0 for key in range(8)}
                    assert index == 0 and value == int(reference["mean"])
                else:
                    assert self.debug_active, "Debug output before a frame's mean"
                    assert kind in DEBUG_FIELDS
                    assert index == self.debug_counts[kind], (kind, index, self.debug_counts)
                    assert value == int(reference[DEBUG_FIELDS[kind]][index]), (self.debug_frames,kind,index,value)
                self.debug_counts[kind] += 1
                if kind == 7 and index == 2:
                    assert self.debug_counts == {0: 1, 1: len(reference["windowed"]),
                        2: len(reference["real"]), 3: len(reference["imag"]),
                        4: 16, 5: 16, 6: 16, 7: 3}
                    self.debug_active = False
                    self.debug_frames += 1
            valid, ready = int(self.dut.out_valid.value), int(self.dut.out_ready.value)
            snapshot = {name: int(getattr(self.dut,name).value) for name in OUTPUT_FIELDS}
            if self.held is not None:
                assert valid and snapshot == self.held, "Output changed while stalled"
            if valid and not ready:
                self.output_stall_cycles += 1
                self.held = snapshot
            else:
                self.held = None
            if valid and ready:
                assert len(self.outputs) < len(self.expected), "Duplicate or canceled-frame output"
                entry = self.expected[len(self.outputs)]
                reference = entry["expected"]
                assert snapshot["out_frame_id"] == entry["frame_id"], (len(self.outputs),snapshot["out_frame_id"],entry["frame_id"])
                actual_logits = [signed((snapshot["out_logits"] >> (32*i)) & 0xffffffff,32) for i in range(3)]
                assert actual_logits == list(map(int,reference["logits"])), (entry["frame_id"],actual_logits)
                assert snapshot["out_class"] == int(reference["class_id"])
                assert snapshot["out_error"] == 0
                assert snapshot["cycles_total"] == sum(snapshot[name] for name in OUTPUT_FIELDS[-5:-1])
                self.outputs.append({**snapshot,"logits_signed":actual_logits})


async def drive(dut, samples, frame_id, *, last=True):
    """Hold each beat until an actual acceptance; last=False never ends it."""
    for index, sample in enumerate(samples):
        await FallingEdge(dut.clk)
        dut.in_valid.value = 1
        dut.in_sample.value = int(sample) & 0xffff
        dut.in_frame_id.value = frame_id
        dut.in_last.value = int(last and index == len(samples)-1)
        await Timer(1,unit="ns")
        if not int(dut.in_ready.value):
            await with_timeout(RisingEdge(dut.in_ready),10,"ms")
        await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.in_valid.value = 0
    dut.in_last.value = 0


async def wait_outputs(dut, scoreboard, count, monitor):
    async def wait():
        while len(scoreboard.outputs) < count:
            if monitor.done():
                monitor.result()
            await ClockCycles(dut.clk,256)
    await with_timeout(wait(),50,"ms")


@cocotb.test(timeout_time=100,timeout_unit="ms")
async def explicit_frame_protocol_edges(dut):
    model, frames = load_frames()
    n = model["n"]
    dut.rst.value = 1
    dut.in_valid.value = 0
    dut.in_sample.value = 0
    dut.in_frame_id.value = 0
    dut.in_last.value = 0
    dut.out_ready.value = 0
    cocotb.start_soon(Clock(dut.clk,10,unit="ns",impl="gpi").start())
    await ClockCycles(dut.clk,4)
    await FallingEdge(dut.clk)
    dut.rst.value = 0
    scoreboard = ProtocolScoreboard(dut,frames)
    monitor = cocotb.start_soon(scoreboard.run())
    checkpoints = []

    async def errors(name, expected):
        await Timer(1,unit="ns")
        actual = int(dut.protocol_errors.value)
        assert actual == expected, (name,actual,expected)
        checkpoints.append({"name":name,"protocol_errors":actual})

    # 1: The very first sample has in_last. It is canceled, then a full frame
    # recovers without reset or an extra error from a stale receiving state.
    await drive(dut,[12345],0x60000001)
    await errors("first_sample_in_last_canceled",1)
    await drive(dut,frames[0]["samples"],frames[0]["frame_id"])
    await wait_outputs(dut,scoreboard,1,monitor)
    await errors("recovered_after_first_sample_last",1)

    # 2: Missing last at N, then 18 additional non-last samples and one late
    # last, all with exactly the same ID. Idle gaps must not leave drain mode.
    drain_id = frames[1]["frame_id"]
    await drive(dut,frames[8]["samples"],drain_id,last=False)
    await errors("missing_last_at_N",2)
    tail = [32767,-32768,123,-456,0,1,-1,2047,-2048,999,-999,42,-42,17,-17,3,-3,2,-2]
    await drive(dut,tail[:7],drain_id,last=False)
    await ClockCycles(dut.clk,3)
    await errors("same_id_drain_after_7_extra_samples",2)
    await drive(dut,tail[7:-1],drain_id,last=False)
    await ClockCycles(dut.clk,5)
    await errors("same_id_drain_after_18_extra_samples",2)
    await drive(dut,tail[-1:],drain_id)
    await errors("same_id_late_last_closes_drain",2)
    assert len(scoreboard.outputs) == 1
    # Same ID again: recovery must be caused by the late last, not ID-change
    # resynchronization masking a stuck drain state.
    await drive(dut,frames[1]["samples"],drain_id)
    await wait_outputs(dut,scoreboard,2,monitor)
    await errors("same_id_full_frame_after_drain",2)

    # 3: Values deliberately cross the signed boundary, descend, and wrap
    # 0xffffffff->0. Expected ordering is acceptance order, not sorted order.
    for entry in frames[2:]:
        await drive(dut,entry["samples"],entry["frame_id"])
    await wait_outputs(dut,scoreboard,len(frames),monitor)
    await errors("high_bits_and_wrap_sequence_complete",2)
    # A further full processing interval catches queued duplicate/stale frames.
    quiet_cycles = scoreboard.outputs[-1]["cycles_total"]+32
    await ClockCycles(dut.clk,quiet_cycles)
    await FallingEdge(dut.clk)
    scoreboard.stop = True
    await monitor
    assert not int(dut.out_valid.value)
    assert len(scoreboard.outputs) == len(frames) == 9
    assert scoreboard.debug_frames == 9 and not scoreboard.debug_active
    assert scoreboard.accepted_beats == (10*n)+20
    assert scoreboard.input_stall_cycles > 0
    assert scoreboard.output_stall_cycles > 0
    assert int(dut.protocol_errors.value) == 2
    report = {"suite":"independent_protocol_edges","status":"passed",
              "n":n,"lanes":int(os.environ["EDGE_LANES"]),
              "bands":3 if model.get("feature_mode")=="neighbor3_energy" else 1,
              "input_accepted_beats":scoreboard.accepted_beats,
              "valid_frames":9,"canceled_malformed_frames":2,
              "output_handshakes":len(scoreboard.outputs),"debug_checked_frames":scoreboard.debug_frames,
              "protocol_errors":int(dut.protocol_errors.value),"error_checkpoints":checkpoints,
              "high_bit_and_wrap_ids_hex":[f"0x{x:08x}" for x in WRAP_IDS],
              "output_ids_hex":[f"0x{x['out_frame_id']:08x}" for x in scoreboard.outputs],
              "input_stall_cycles":scoreboard.input_stall_cycles,
              "output_stall_cycles":scoreboard.output_stall_cycles,
              "forced_stall_cycles_per_output":7,
              "post_output_quiet_cycles":quiet_cycles,"simulated_cycles":scoreboard.cycles,
              "drain_nonlast_extra_beats":18,"drain_late_last_beats":1,
              "reset_during_scenarios":False,"assertions_enabled":True,
              "checked_intermediates":["mean",*DEBUG_FIELDS.values()],
              "vector_sources":[{k:v for k,v in entry.items() if k not in ("samples","expected")} for entry in frames],
              "outputs":scoreboard.outputs,"physical_hardware_tested":False,
              "original_coverage_database_modified":False,"coverage_percentage_recomputed":False}
    Path(os.environ["EDGE_REPORT"]).write_text(json.dumps(report,indent=2)+"\n")
