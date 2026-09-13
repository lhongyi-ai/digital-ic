"""Synthetic pin-level functional tests, never physical accuracy measurements."""
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles,Timer
from test_spi_sensor import Adxl345Model
from test_sensor_system import NorPins
from vibfpga.field import raw_to_core
from vibfpga.field_log import parse_field_log
from vibfpga.fixed import classify

BASE,END=0x300000,0x320000


class Harness:
    def __init__(self,dut):
        self.dut=dut;self.cycles=0
        self.sensor=Adxl345Model(SimpleNamespace(cs_n=dut.sensor_cs_n,sclk=dut.sensor_sclk,
            mosi=dut.sensor_mosi,miso=dut.sensor_miso,drdy=dut.sensor_drdy),6)
        self.flash=NorPins(SimpleNamespace(cs_n=dut.flash_cs_n,sclk=dut.flash_sclk,
            mosi=dut.flash_mosi,miso=dut.flash_miso))

    async def tick(self,reset=False):
        self.dut.clk.value=0;self.dut.rst.value=int(reset)
        await Timer(5,unit="ns")
        self.dut.clk.value=1
        await Timer(5,unit="ns")
        self.sensor.observe(reset);self.flash.observe(reset);self.cycles+=1

    async def wait(self,predicate,limit=150000):
        for _ in range(limit):
            if predicate():return
            await self.tick()
        raise AssertionError(f"timeout state={int(self.dut.state.value)} observed={int(self.dut.observed_count.value)}")

    async def idle(self,cycles):
        # Fast clock-only interval: no DRDY/pending data, both SPI buses idle.
        # The actual classifier and RAM continue executing every clock.
        assert int(self.dut.state.value)==2 and not self.sensor.pending
        assert int(self.dut.sensor_cs_n.value) and int(self.dut.flash_cs_n.value)
        if cycles<=0:return
        task=cocotb.start_soon(Clock(self.dut.clk,10,unit="ns").start(start_high=False))
        await ClockCycles(self.dut.clk,cycles)
        await Timer(5,unit="ns")
        task.cancel()
        self.cycles+=cycles;self.sensor.tick_count+=cycles;self.flash.tick_count+=cycles
        assert int(self.dut.sensor_cs_n.value) and int(self.dut.flash_cs_n.value)


@cocotb.test()
async def sensor_to_classification_log(dut):
    case=os.environ["FIELD_CASE"];total=int(os.environ["FIELD_TOTAL"])
    model_path=Path(os.environ["FIELD_MODEL"]);model=json.loads(model_path.read_text())
    model_hash=hashlib.sha256(model_path.read_bytes()).hexdigest()
    h=Harness(dut)
    if case=="wrong_id":h.sensor.regs[0]=0x42
    if case=="dirty_log":h.flash.nor.memory[END-1]=0
    protected=hashlib.sha256(h.flash.nor.memory[:BASE]).hexdigest()
    await h.tick(reset=True)
    raw=[];service=[]
    if case=="dirty_log":
        await h.wait(lambda:int(dut.state.value)==10,limit=10000000)
        assert int(dut.error_flags.value)==1 and not int(dut.status_done.value)
        assert not h.sensor.transactions
        assert not [x for x in h.flash.nor.operations if x["opcode"]==2]
        report={"passed":True,"case":case,"nonblank_log_preserved":True,"full_128k_partition_scan":True}
    elif case in ("wrong_id","watchdog"):
        await h.wait(lambda:int(dut.status_done.value),limit=250000)
        parsed=parse_field_log(bytes(h.flash.nor.memory[BASE:END]),expected_model_sha256=model_hash)
        assert parsed["record_count"]==0
        assert parsed["error_flags"]==(2 if case=="wrong_id" else 4)
        report={"passed":True,"case":case,"zero_result_error_log":True,"error_flags":parsed["error_flags"]}
    else:
        await h.wait(lambda:int(dut.capture_init.value))
        t=np.arange(total)
        samples=np.rint(240+150*np.sin(2*np.pi*18*t/256)+30*np.cos(2*np.pi*43*t/256)).astype(np.int16)
        samples[4]=2047 # explicit clamp coverage in the actual integrated path
        next_due=h.cycles+4
        for index,sample in enumerate(samples):
            if case=="gap" and index==16:next_due+=15000
            if index:await h.idle(max(0,next_due-h.cycles))
            else:
                while h.cycles<next_due:await h.tick()
            h.sensor.set_sample((0,0,int(sample)))
            await h.wait(lambda:int(dut.observed_count.value)==index+1,limit=5000)
            raw.append(int(sample));service.append(int(dut.service_cycle.value))
            # Capture ACK/release takes a few clocks beyond sample_valid.
            for _ in range(4):await h.tick()
            next_due+=15000
        if case=="interrupted":
            await h.wait(lambda:any(x["opcode"]==2 for x in h.flash.nor.operations),limit=150000)
            # Reset after header page, before final commit. The dirty partition
            # must remain protected on restart, even though no valid log exists.
            await h.tick(reset=True)
            await h.wait(lambda:int(dut.state.value)==10)
            assert int(dut.error_flags.value)&1 and not int(dut.status_done.value)
            try:parse_field_log(bytes(h.flash.nor.memory[BASE:END]))
            except ValueError as e:assert "uncommitted" in str(e)
            else:raise AssertionError("interrupted write appeared committed")
            report={"passed":True,"case":case,"interrupted_log_not_overwritten":True}
        else:
            await h.wait(lambda:int(dut.status_done.value),limit=200000)
            blob=bytes(h.flash.nor.memory[BASE:END])
            parsed=parse_field_log(blob,expected_model_sha256=model_hash)
            start=17 if case=="gap" else 0
            expected_count=(total-start)//256
            assert parsed["record_count"]==expected_count
            assert parsed["observed_samples"]==total
            assert parsed["trailing_partial_samples"]==(total-start)%256
            assert parsed["error_flags"]==(8 if case=="gap" else 0)
            if case=="gap":
                assert parsed["canceled_frames"]==1 and parsed["dropped_samples"]==1
                assert parsed["source_cancellation_events"]==1
            for i,r in enumerate(parsed["records"]):
                lo=start+256*i
                expected=classify(raw_to_core(np.asarray(raw[lo:lo+256])),model)
                assert r["logits"]==expected["logits"].tolist()
                assert r["class_id"]==expected["class_id"] and r["error_flags"]==0
                assert r["first_service_cycle"]==service[lo] and r["last_service_cycle"]==service[lo+255]
                assert 0<r["last_sample_to_result_cycles_mod32"]<150000
            Path(os.environ["FIELD_REPORT"]).with_suffix(".bin").write_bytes(blob)
            report={"passed":True,"case":case,"records_bit_exact":expected_count,
                    "model_sha256":model_hash,"parsed":parsed,"independent_800hz_input":True}
    operations=[x for x in h.flash.nor.operations if x["opcode"]==2]
    for x in operations:
        assert BASE<=x["address"] and x["address"]+x["length"]<=END
        assert x["address"]//256==(x["address"]+x["length"]-1)//256
    assert hashlib.sha256(h.flash.nor.memory[:BASE]).hexdigest()==protected
    if int(dut.status_done.value):assert operations[-1]["address"]==BASE+12 and operations[-1]["data"]=="544d4f43"
    report.update({"physical_hardware_tested":False,"source_kind":"synthetic_pin_level_stimuli",
                   "configuration_flash_preserved":True,"nor_page_boundary_checks":True,"cycles":h.cycles})
    Path(os.environ["FIELD_REPORT"]).write_text(json.dumps(report,indent=2)+"\n")
