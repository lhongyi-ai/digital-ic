"""Actual capture/calibration/SPRAM/Flash RTL with pin-level sensor/NOR models."""
import hashlib
import json
import os
import random
import struct
from pathlib import Path
from types import SimpleNamespace
import zlib
import numpy as np

import cocotb
from cocotb.triggers import Timer

from test_spi_sensor import Adxl345Model, SpiPeripheral
from test_flash_system import SpiNor
from vibfpga.fixed import frontend

BASE,END,PAYLOAD=0x300000,0x320000,0x301000


class NorPins(SpiPeripheral):
    def __init__(self,dut):
        super().__init__(dut,0,0,1)
        self.nor=SpiNor(dut)

    def start(self):
        self.nor.opcode=None;self.nor.header=[];self.nor.data=[];self.nor.address=0
        return 0xff

    def receive(self,value):
        return self.nor.receive(value)

    def observe(self,reset=False):
        previous=self.cs
        super().observe(reset)
        if not reset and not previous and self.cs:
            self.nor.close()


class SystemHarness:
    def __init__(self,dut):
        self.dut=dut;self.cycles=0
        sensor=SimpleNamespace(cs_n=dut.sensor_cs_n,sclk=dut.sensor_sclk,
            mosi=dut.sensor_mosi,miso=dut.sensor_miso,drdy=dut.sensor_drdy)
        flash=SimpleNamespace(cs_n=dut.flash_cs_n,sclk=dut.flash_sclk,
            mosi=dut.flash_mosi,miso=dut.flash_miso)
        self.sensor=Adxl345Model(sensor,6)
        self.flash=NorPins(flash)

    async def tick(self,reset=False):
        self.dut.clk.value=0;self.dut.rst.value=int(reset)
        await Timer(5,unit="ns")
        self.dut.clk.value=1
        await Timer(5,unit="ns")
        self.sensor.observe(reset);self.flash.observe(reset)
        self.cycles+=1

    async def wait(self,predicate,limit=1000000):
        for _ in range(limit):
            if predicate():return
            await self.tick()
        raise AssertionError(f"sensor system timeout in state {int(self.dut.state.value)}")

    async def sample_run(self,total,*,overflow=False):
        await self.wait(lambda:int(self.dut.capture.init_done.value))
        rng=random.Random(345)
        raw=[];service=[]
        next_due=self.cycles+4
        for index in range(total):
            while self.cycles<next_due:await self.tick()
            sample=tuple(rng.randrange(-512,512) for _ in range(3))
            self.sensor.set_sample(sample)
            await self.wait(lambda:int(self.dut.observed_count.value)==index+1,limit=10000)
            raw.append(sample[0]);service.append(int(self.dut.capture.service_cycle.value))
            next_due+=(300100 if overflow and index==0 else 15000)
        await self.wait(lambda:int(self.dut.status_done.value),limit=100000)
        return raw,service


def rne_shift(value,shift):
    floor=value>>shift
    rem=value-(floor<<shift)
    half=1<<(shift-1)
    return floor+int(rem>half or rem==half and floor&1)


@cocotb.test()
async def capture_to_committed_flash(dut):
    total=int(os.environ["SENSOR_TOTAL"])
    retained=int(os.environ["SENSOR_STORE"])
    scenario=os.environ["SENSOR_CASE"]
    overflow=scenario=="overflow"
    spectrum=scenario=="spectrum"
    header_bytes=208 if spectrum else 128
    h=SystemHarness(dut)
    protected=hashlib.sha256(h.flash.nor.memory[:BASE]).hexdigest()
    await h.tick(reset=True)
    raw,service=await h.sample_run(total,overflow=overflow)
    memory=h.flash.nor.memory
    words=struct.unpack_from("<32I",memory,BASE)
    assert words[0:4]==(0x314e4553,1,retained,0x434f4d54)
    assert words[5:8]==(total,total,retained)
    assert words[8:12]==(12000000,0x0d,0,0xe5)
    assert words[12]==service[0] and words[13]==service[-1]
    deltas=[(b-a)&0xffffffff for a,b in zip(service,service[1:])]
    assert words[14]==min(deltas) and words[15]==max(deltas)
    assert words[16]==total and words[17]==0 and words[18]==0
    assert words[21:24]==(4,PAYLOAD,4)
    payload=bytes(memory[PAYLOAD:PAYLOAD+4*retained])
    assert words[20]==zlib.crc32(payload)
    records=list(struct.iter_unpack("<hH",payload))
    for index,(value,interval) in enumerate(records):
        expected=0 if index==0 else ((service[index]>>2)-(service[index-1]>>2))&0x3fffffff
        if index and deltas[index-1]>262140:expected=65535
        assert (value,interval)==(raw[index],expected), (index,value,interval,expected)
    calibrated=[rne_shift(value*256*4096000,28) for value in raw]
    assert words[24]==calibrated[-1]&0xffffffff
    signed_sum=words[25]|words[26]<<32
    if signed_sum>=1<<63:signed_sum-=1<<64
    assert signed_sum==sum(calibrated)
    wraps=sum(b<a for a,b in zip(service,service[1:]))
    assert words[27:32]==(total,0,4096000,wraps,header_bytes)
    assert (wraps<<32)+service[-1]-service[0]==sum(deltas)
    if not overflow:assert wraps==1, "The nominal run must cross the 32-bit cycle rollover"
    assert words[19]==int(overflow)
    assert words[4]==(4 if overflow else 0)
    assert int(dut.status_error.value)==int(overflow)
    programs=[op for op in h.flash.nor.operations if op["opcode"]==2]
    assert programs[-1]["address"]==BASE+12 and programs[-1]["data"]=="544d4f43"
    assert programs[-2]["address"]==BASE and programs[-2]["length"]==header_bytes
    for op in programs:
        assert BASE<=op["address"] and op["address"]+op["length"]<=END
        assert (op["address"]&255)+op["length"]<=256
    assert hashlib.sha256(memory[:BASE]).hexdigest()==protected
    successful_log=bytes(memory[BASE:END])
    spectral_powers=[]
    if spectrum:
        metadata=struct.unpack_from("<4I",memory,BASE+128)
        assert metadata==(1,256,1,0)
        spectral_powers=list(struct.unpack_from("<16I",memory,BASE+144))
        model_path=Path(__file__).resolve().parents[1]/"artifacts/sensor_spectrum/model/model.json"
        model=json.loads(model_path.read_text())
        expected=frontend(np.clip(np.array(raw[:256],dtype=np.int64),-1024,1023)*32,model)
        assert spectral_powers==[int(value) for value in expected["powers"]]
    if scenario=="nominal":
        assert len(programs)==4, "320-byte payload must span two NOR pages"
        assert int(dut.stored_count.value)==80
        # BANK_ADDR_BITS=6 makes 80 records cross all three physical RAM wrappers.
        assert records[31][0]==raw[31] and records[32][0]==raw[32]
        assert records[63][0]==raw[63] and records[64][0]==raw[64]
        before=len(programs)
        snapshot=bytes(memory[BASE:END])
        await h.tick(reset=True)
        await h.wait(lambda:int(dut.state.value)==9)
        assert int(dut.status_error.value) and not int(dut.status_done.value)
        assert bytes(memory[BASE:END])==snapshot
        assert len([op for op in h.flash.nor.operations if op["opcode"]==2])==before
        # An interrupted capture with an erased header and nonblank payload is
        # protected too. This is a partial-log guard test, not electrical power loss.
        memory[BASE:END]=b"\xff"*(END-BASE)
        memory[PAYLOAD+319]=0x42
        await h.tick(reset=True)
        await h.wait(lambda:int(dut.state.value)==9)
        assert int(dut.status_error.value) and not int(dut.status_done.value)
        assert memory[PAYLOAD+319]==0x42 and memory[BASE:BASE+128]==b"\xff"*128
        assert len([op for op in h.flash.nor.operations if op["opcode"]==2])==before
    report={"passed":True,"case":scenario,
        "total_samples":total,"stored_samples":retained,"cycles":h.cycles,
        "format":f"SEN1 with {header_bytes}-byte header","payload_crc32":words[20],
        "spectral_powers":spectral_powers,"spectrum_golden_match":spectrum,
        "calibration_last_mg":calibrated[-1],"calibration_sum_mg":signed_sum,
        "service_wrap_count":wraps,"service_counter_start":"0xfff00000 (simulation only)",
        "interval_overflow_flag":bool(words[19]),"commit_written_last":True,
        "three_ram_banks_and_page_continuation":scenario=="nominal",
        "nonblank_and_partial_log_guards":scenario=="nominal",
        "simulation_log_scan_bytes":8192,"simulation_bank_address_bits":8 if spectrum else 6,
        "hardware_measured":False}
    report_path=Path(os.environ["SENSOR_REPORT"])
    (report_path.parent/"sensor_log.bin").write_bytes(successful_log)
    (report_path.parent/"sensor_stimulus.json").write_text(json.dumps({
        "simulation_only":True,"raw_axis":raw,"service_cycles_u32":service,
        "store_samples":retained,"total_samples":total},indent=2)+"\n")
    report["simulated_log_file"]="sensor_log.bin"
    report_path.write_text(json.dumps(report,indent=2)+"\n")
