"""DSP-only N256 raw-sensor frontend comparison; synthetic stimuli, not measurements."""
import json
import os
from pathlib import Path
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles,FallingEdge,RisingEdge,Timer
import numpy as np
from vibfpga.fixed import frontend


@cocotb.test()
async def synthetic_sensor_powers(dut):
    model=json.loads(Path(os.environ["SPECTRUM_MODEL"]).read_text())
    n=np.arange(256)
    rng=np.random.default_rng(613)
    frames=[np.zeros(256,dtype=np.int64),np.full(256,93,dtype=np.int64),
        np.rint(200*np.sin(2*np.pi*16*n/256)+50).astype(np.int64),
        np.rint(140*np.sin(2*np.pi*8*n/256)+60*np.cos(2*np.pi*40*n/256)).astype(np.int64),
        rng.integers(-32768,32768,256,dtype=np.int64)]
    expected=[frontend(np.clip(f,-1024,1023)*32,model)["powers"] for f in frames]
    cocotb.start_soon(Clock(dut.clk,10,unit="ns").start())
    dut.rst.value=1;dut.in_valid.value=0;dut.in_sample.value=0
    await ClockCycles(dut.clk,4)
    await FallingEdge(dut.clk);dut.rst.value=0
    observed=[];partial=[];completed=0
    async def monitor():
        nonlocal partial,completed
        while True:
            await RisingEdge(dut.clk);await Timer(1,unit="ns")
            if int(dut.power_valid.value):
                assert int(dut.power_index.value)==len(partial)
                partial.append(int(dut.power.value))
            if int(dut.window_done.value):
                assert len(partial)==16
                assert partial==expected[completed].tolist()
                observed.append(partial);partial=[];completed+=1
    task=cocotb.start_soon(monitor())
    for frame in frames:
        for sample in frame:
            await FallingEdge(dut.clk)
            dut.in_sample.value=int(sample)&0xffff;dut.in_valid.value=1
            await Timer(1,unit="ns")
            if not int(dut.in_ready.value):await RisingEdge(dut.in_ready)
            await RisingEdge(dut.clk)
    await FallingEdge(dut.clk);dut.in_valid.value=0
    for _ in range(150000):
        if completed==len(frames):break
        await RisingEdge(dut.clk)
    assert completed==len(frames)
    await Timer(2,unit="ns")
    assert not int(dut.busy.value)
    expected_clips=sum(int(np.count_nonzero((f < -1024)|(f>1023))) for f in frames)
    assert int(dut.clip_count.value)==expected_clips
    # Reset cancels a partial frame and starts its sample count from zero.
    await FallingEdge(dut.clk);dut.in_valid.value=1;dut.in_sample.value=55
    await ClockCycles(dut.clk,11)
    await FallingEdge(dut.clk);dut.rst.value=1;dut.in_valid.value=0
    await ClockCycles(dut.clk,3)
    await FallingEdge(dut.clk);dut.rst.value=0
    await Timer(1,unit="ns")
    assert int(dut.clip_count.value)==0 and not int(dut.busy.value)
    assert not int(dut.power_valid.value) and not int(dut.window_done.value)
    task.cancel()
    Path(os.environ["SPECTRUM_REPORT"]).write_text(json.dumps({"passed":True,"frames":len(frames),
        "powers_compared":len(frames)*16,"clip_count":expected_clips,"n":256,"bins":model["bins"],
        "synthetic_stimuli":True,"physical_hardware_tested":False,"classification_performed":False,
        "powers":observed,"reset_partial_frame":"passed"},indent=2)+"\n")
