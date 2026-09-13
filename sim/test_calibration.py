import os
import json
from pathlib import Path
import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from vibfpga.fixed import round_shift_even


@cocotb.test()
async def arithmetic_stalls_reset(dut):
    offset = int(os.environ["CAL_OFFSET"])
    gain = int(os.environ["CAL_GAIN"])
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst.value=1;dut.in_valid.value=0;dut.in_raw.value=0;dut.out_ready.value=0
    for _ in range(3):await RisingEdge(dut.clk)
    await Timer(1,unit="ns");dut.rst.value=0
    rng=random.Random(903)
    samples=[0,1,-1,32767,-32768,256,-256,26,276,-224]+[rng.randint(-32768,32767) for _ in range(190)]
    for sample in samples:
        while not dut.in_ready.value:await RisingEdge(dut.clk);await Timer(1,unit="ns")
        dut.in_raw.value=sample;dut.in_valid.value=1
        await RisingEdge(dut.clk);await Timer(1,unit="ns");dut.in_valid.value=0
        for count in range(35):
            if dut.out_valid.value:break
            await RisingEdge(dut.clk);await Timer(1,unit="ns")
        else:raise AssertionError("calibration timeout")
        expected=max(-(1<<31),min((1<<31)-1,round_shift_even((sample*256-offset)*gain,28)))
        assert dut.out_mg.value.to_signed()==expected
        for _ in range(rng.randrange(1,8)):
            await RisingEdge(dut.clk);await Timer(1,unit="ns")
            assert dut.out_valid.value and dut.out_mg.value.to_signed()==expected
        dut.out_ready.value=1
        await RisingEdge(dut.clk);await Timer(1,unit="ns");dut.out_ready.value=0
    dut.in_raw.value=32767;dut.in_valid.value=1
    await RisingEdge(dut.clk);await Timer(1,unit="ns");dut.in_valid.value=0
    for _ in range(9):await RisingEdge(dut.clk)
    await Timer(1,unit="ns");dut.rst.value=1
    await RisingEdge(dut.clk);await Timer(1,unit="ns");dut.rst.value=0
    for _ in range(35):
        await RisingEdge(dut.clk);await Timer(1,unit="ns")
        assert not dut.out_valid.value
    Path(os.environ["CAL_REPORT"]).write_text(json.dumps({"passed":True,"samples":len(samples),"offset_q8":offset,
        "gain_q20":gain,"stalled_output_stable":True,"reset_cancels_inflight":True},indent=2)+"\n")
