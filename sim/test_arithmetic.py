import json
import os
from pathlib import Path
import random

import cocotb
from cocotb.triggers import Timer
from vibfpga.fixed import round_shift_even, saturate


def signed(value, width):
    raw = int(value)
    return raw-(1 << width) if raw & (1 << (width-1)) else raw


@cocotb.test()
async def rounding_saturation_and_quantization(dut):
    rng = random.Random(178)
    cases = []
    # Every tested shift gets exact ties of both signs and both quotient parities.
    for shift in range(41):
        for quotient in (-129, -128, -3, -2, -1, 0, 1, 2, 3, 126, 127, 128):
            half = (1 << (shift-1)) if shift else 0
            for offset in (-1, 0, 1):
                value = (quotient << shift) + half + offset
                if -(1 << 39) <= value < (1 << 39):
                    cases.append((value, shift, rng.randrange(1 << 33)))
    for value in (-32769, -32768, -32767, -2049, -2048, -2047, -1, 0, 1,
                  2046, 2047, 2048, 32766, 32767, 32768):
        cases.append((value, 0, 0))
    for shift in range(41):
        for value in (0, 1, 126, 127, 128, (1 << 31)-1, 1 << 31, (1 << 33)-1):
            cases.append((0, shift, value))
    for _ in range(5000):
        cases.append((rng.randrange(-(1 << 39), 1 << 39), rng.randrange(41), rng.randrange(1 << 33)))
    hidden_shift = int(os.environ["CORE_HIDDEN_SHIFT"])
    for value, shift, power in cases:
        dut.value.value = value & ((1 << 64)-1)
        dut.shift.value = shift
        dut.power_value.value = power
        await Timer(1, unit="ns")
        assert signed(dut.rounded.value, 64) == round_shift_even(value, shift), (value, shift)
        assert signed(dut.clipped12.value, 16) == saturate(value, 12), value
        assert signed(dut.clipped16.value, 16) == saturate(value, 16), value
        assert int(dut.power_quantized.value) == min(127, round_shift_even(power, shift)), (power, shift)
        assert int(dut.hidden_quantized.value) == min(127, max(0, round_shift_even(value, hidden_shift)))
    Path(os.environ["CORE_REPORT"]).write_text(json.dumps({"status": "passed", "vectors": len(cases),
        "rne_shifts": [0, 40], "hidden_shift": hidden_shift, "seed": 178}, indent=2)+"\n")
