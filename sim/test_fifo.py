"""Handshake-level scoreboard; coverage is scenario evidence, not code coverage."""
import json
import os
import random
from collections import Counter, deque
from pathlib import Path

import cocotb
from cocotb.triggers import Timer


@cocotb.test()
async def fifo_directed_random(dut):
    depth = int(os.environ.get("FIFO_DEPTH", "4"))
    width = len(dut.in_data)
    mask = (1 << width) - 1
    rng = random.Random(0xAD345 + depth)
    queue = deque()
    counts = Counter()
    writes_since_reset = 0
    held = None

    async def cycle(valid=0, data=0, ready=0, reset=0):
        nonlocal held, writes_since_reset
        dut.clk.value = 0
        dut.rst.value = reset
        dut.in_valid.value = valid
        dut.in_data.value = data & mask
        dut.out_ready.value = ready
        await Timer(5, unit="ns")
        before = len(queue)
        iv = int(dut.in_ready.value)
        ov = int(dut.out_valid.value)
        assert iv == int(not reset and (before < depth or ready))
        assert ov == int(not reset and before > 0)
        value = int(dut.out_data.value) if ov else None
        if ov:
            assert value == queue[0], f"FIFO order/data mismatch: {value} != {queue[0]}"
        if held is not None and not reset:
            assert ov and value == held, "Output changed while stalled"
        push = bool(valid and iv)
        pop = bool(ov and ready)
        if reset:
            counts["reset_nonempty" if before else "reset_empty"] += 1
            queue.clear()
            writes_since_reset = 0
        else:
            if before == 0 and ready:
                counts["empty_read_blocked"] += 1
            if before == depth and valid and not ready:
                counts["full_write_blocked"] += 1
            if before == depth and push and pop:
                counts["full_pop_push"] += 1
            if pop:
                assert queue.popleft() == value
                counts["pop"] += 1
            if push:
                queue.append(data & mask)
                writes_since_reset += 1
                counts["push"] += 1
                if writes_since_reset > 2 * depth:
                    counts["wraparound_traffic"] += 1
            if ov and not ready:
                counts["output_stall"] += 1
            if not valid:
                counts["input_gap"] += 1
        held = value if ov and not ready and not reset else None
        dut.clk.value = 1
        await Timer(5, unit="ns")
        assert int(dut.occupancy.value) == len(queue)
        counts["cycles"] += 1
        return push

    await cycle(reset=1)
    # Empty must not fall through, even when both sides are eager.
    await cycle(ready=1)
    for i in range(depth):
        await cycle(1, 0x100 + i, 0)
    for _ in range(5):
        await cycle(1, 0xBEEF, 0)
    for i in range(3 * depth + 2):
        await cycle(1, 0x8000 + i, 1)
    for _ in range(depth + 2):
        await cycle(ready=1)
    for i in range(depth):
        await cycle(1, mask - i, 0)
    await cycle(1, 123, 1, reset=1)
    await cycle(ready=1)

    # A compliant random producer holds its pending word until accepted.
    pending = None
    for _ in range(3000):
        reset = rng.random() < 0.025
        if pending is None and rng.random() < 0.72:
            pending = rng.getrandbits(width)
        pushed = await cycle(pending is not None, pending or 0,
                             rng.random() < 0.56, reset)
        if pushed or reset:
            pending = None
    # Drain all accepted words and verify there are no duplicates afterwards.
    for _ in range(depth + 3):
        await cycle(ready=1)
    assert not queue
    required = ["reset_nonempty", "reset_empty", "empty_read_blocked",
                "full_write_blocked", "full_pop_push", "wraparound_traffic",
                "output_stall", "input_gap", "push", "pop"]
    for key in required:
        assert counts[key] > 0, f"Scenario missing: {key}"
    path = Path(os.environ.get("FIFO_COVERAGE_FILE", "fifo_coverage.json"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": 1, "test": "fifo_directed_random",
                                "width": width, "depth": depth,
                                "seed": 0xAD345 + depth,
                                "scenario_counts": dict(counts)}, indent=2) + "\n")
