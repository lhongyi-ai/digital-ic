"""SPI-NOR protocol model and Flash -> actual N1024 RTL -> committed log tests.

This is functional simulation, not vendor Flash electrical/timing validation.
The NOR model starts in deep power-down and requires AB release plus settling
before 03 read, 06 WREN, 02 page-program and 05 WIP status commands work.
Programming performs NOR bitwise AND and page wrapping, making unintended
overwrites or page-crossing visible rather than acting like ideal byte RAM.
"""
import hashlib
import json
import os
from pathlib import Path
import struct

import cocotb
from cocotb.triggers import FallingEdge, First, RisingEdge, Timer
from cocotb.utils import get_sim_time
import numpy as np

from vibfpga.board import build_replay_image, parse_result_log
from vibfpga.fixed import classify

INPUT_BASE, LOG_BASE, LOG_END = 0x40000, 0x300000, 0x320000


class SpiNor:
    # ceil(3 us * 13.2 MHz): tRES1 at the fastest supported HFOSC corner.
    # The autonomous harness uses 10 ns per *modeled FPGA cycle*, not a 100 MHz
    # physical board clock. Tick-driven sensor/field harnesses supply a counter.
    MIN_WAKE_CYCLES=40

    def __init__(self,dut,*,powered_down=True,cycle=None):
        self.dut=dut
        self.cycle=cycle or (lambda:int(get_sim_time(unit="ns")//10))
        self.powered_down=powered_down
        self.wake_ready_cycle=0
        self.wake_events=[]
        self.ignored_commands=[]
        self.command_events=[]
        self.memory=bytearray(b"\xff")*0x400000
        self.wel=False
        self.wip=0
        self.program_busy_polls=2
        self.operations=[]
        self.opcode=None
        self.header=[]
        self.data=[]
        self.address=0
        self.read_bytes=0
        self.ignored=False
        self.start_cycle=0

    def begin(self):
        self.opcode=None;self.header=[];self.data=[];self.address=0;self.read_bytes=0
        self.ignored=False
        self.start_cycle=self.cycle()
        return 0xff

    def awake(self,cycle=None):
        return not self.powered_down and (self.cycle() if cycle is None else cycle)>=self.wake_ready_cycle

    def receive(self,value):
        if self.opcode is None:
            self.opcode=value
            # Ignore the entire transaction if CS was asserted while asleep or
            # still settling, even if its opcode finishes after the deadline.
            self.ignored=value!=0xab and not self.awake(self.start_cycle)
            if self.ignored:
                return 0xff
            assert value in (0x03,0x06,0x02,0x05,0xab), f"unsupported NOR opcode {value:#x}"
            if value!=0xab:
                self.command_events.append({"opcode":value,"start_cycle":self.start_cycle})
            return int(self.wip>0) if value==0x05 else 0xff
        if self.ignored or self.opcode==0xab:
            return 0xff
        if self.opcode in (0x03,0x02) and len(self.header)<3:
            self.header.append(value)
            self.address=(self.address<<8)|value
            if len(self.header)==3 and self.opcode==0x03:
                return self.memory[self.address]
            return 0xff
        if self.opcode==0x03:
            self.address+=1
            self.read_bytes+=1
            return self.memory[self.address]
        if self.opcode==0x02:
            self.data.append(value)
            return 0xff
        if self.opcode==0x05:
            if self.wip: self.wip-=1
            return int(self.wip>0)
        return 0xff

    def close(self):
        if self.ignored:
            self.ignored_commands.append({"opcode":self.opcode,"start_cycle":self.start_cycle})
            return
        if self.opcode==0xab:
            self.powered_down=False
            self.wake_ready_cycle=self.cycle()+self.MIN_WAKE_CYCLES
            self.wake_events.append({"opcode":0xab,"cs_rise_cycle":self.cycle(),
                                     "ready_cycle":self.wake_ready_cycle})
            return
        if self.opcode==0x06:
            assert not self.wip,"WREN while busy"
            self.wel=True
        if self.opcode==0x02:
            assert self.wel and not self.wip,"program without WREN or while busy"
            assert len(self.header)==3 and self.data
            base=self.address&~255
            for i,value in enumerate(self.data):
                self.memory[base+((self.address+i)&255)] &= value
            self.operations.append({"opcode":2,"address":self.address,"length":len(self.data),"data":bytes(self.data).hex()})
            self.wel=False
            self.wip=self.program_busy_polls
        elif self.opcode==0x03:
            self.operations.append({"opcode":3,"address":int.from_bytes(bytes(self.header),"big"),"length":self.read_bytes})

    async def run(self):
        self.dut.flash_miso.value=1
        while True:
            await FallingEdge(self.dut.flash_cs_n)
            self.begin()
            rx,bits,tx=0,0,0xff
            self.dut.flash_miso.value=1
            while True:
                await First(RisingEdge(self.dut.flash_sclk),RisingEdge(self.dut.flash_cs_n))
                if int(self.dut.flash_cs_n.value):
                    self.close()
                    break
                rx=(rx<<1)|int(self.dut.flash_mosi.value)
                bits+=1
                if bits==8:
                    tx=self.receive(rx);rx=0;bits=0
                await First(FallingEdge(self.dut.flash_sclk),RisingEdge(self.dut.flash_cs_n))
                if int(self.dut.flash_cs_n.value):
                    self.close()
                    break
                self.dut.flash_miso.value=(tx>>(7-bits))&1


async def reset(dut, *, direct=False):
    dut.rst.value=1
    dut.direct_mode.value=int(direct)
    dut.cmd_valid.value=0;dut.cmd_write.value=0;dut.cmd_address.value=0;dut.cmd_length.value=0
    dut.wr_valid.value=0;dut.wr_data.value=0;dut.rd_ready.value=1
    await Timer(100,unit="ns")
    await FallingEdge(dut.clk)
    dut.rst.value=0
    await Timer(1,unit="ns")


async def command(dut,address,length,*,data=None,invalid=False):
    await FallingEdge(dut.clk)
    # flash_stream performs its own release/settling sequence after each reset.
    for _ in range(2048):
        if int(dut.cmd_ready.value):
            break
        await FallingEdge(dut.clk)
    else:
        raise AssertionError("flash command interface did not become ready after wake-up")
    dut.cmd_address.value=address;dut.cmd_length.value=length
    dut.cmd_write.value=int(data is not None)
    dut.cmd_valid.value=1
    await RisingEdge(dut.clk)
    await Timer(1,unit="ns")
    if invalid:
        assert int(dut.done.value) and int(dut.error.value)
    await FallingEdge(dut.clk)
    dut.cmd_valid.value=0
    if invalid:
        await Timer(1,unit="ns")
        return None
    result=[]
    if data is not None:
        for value in data:
            dut.wr_valid.value=1;dut.wr_data.value=value
            await Timer(1,unit="ns")
            if not int(dut.wr_ready.value): await RisingEdge(dut.wr_ready)
            await RisingEdge(dut.clk)
            await FallingEdge(dut.clk)
        dut.wr_valid.value=0
    else:
        for _ in range(length):
            await RisingEdge(dut.rd_valid)
            await Timer(1,unit="ns")
            result.append(int(dut.rd_data.value))
    if not int(dut.done.value): await RisingEdge(dut.done)
    await Timer(1,unit="ns")
    return bytes(result),bool(int(dut.error.value))


async def wait_halt(dut,timeout_us=70000):
    for _ in range(timeout_us//100):
        await Timer(100,unit="us")
        # Errors during RUN can still lead to a diagnostic log; only accept HALT.
        if int(dut.system.state.value)==15:
            return
    raise AssertionError(f"replay failed to halt; state={dut.system.state.value}")


@cocotb.test()
async def flash_wakes_before_direct_read(dut):
    """Reproduce all-FF reads without wake, then prove reset wakes the chip."""
    dut.rst.value=1;dut.direct_mode.value=1
    nor=SpiNor(dut)
    nor.memory[INPUT_BASE:INPUT_BASE+4]=b"VIB1"
    cocotb.start_soon(nor.run())
    await reset(dut,direct=True)
    assert not int(dut.cmd_ready.value),"interface exposed before startup wake"
    value,error=await command(dut,INPUT_BASE,4)
    assert not error and value==b"VIB1"
    assert len(nor.wake_events)==1 and not nor.ignored_commands
    assert nor.command_events[0]["start_cycle"]>=nor.wake_events[0]["ready_cycle"]
    # A controller that only sends READ (the previous implementation) sees FF
    # while the chip is asleep, even though non-FF image bytes are present.
    nor.powered_down=True
    operations=len(nor.operations)
    value,error=await command(dut,INPUT_BASE,4)
    assert not error and value==b"\xff"*4
    assert len(nor.operations)==operations and nor.ignored_commands[-1]["opcode"]==3
    await reset(dut,direct=True)
    value,error=await command(dut,INPUT_BASE,4)
    assert not error and value==b"VIB1" and len(nor.wake_events)==2


@cocotb.test()
async def flash_roundtrip_and_guards(dut):
    dut.rst.value=1;dut.direct_mode.value=1
    nor=SpiNor(dut)
    cocotb.start_soon(nor.run())
    scan_shift=int(os.environ.get("FLASH_SCAN_SHIFT","15"))
    scan_chunk=1<<scan_shift
    scan_bytes=4*scan_chunk
    if os.environ.get("FLASH_FULL_SCAN")=="1":
        assert scan_bytes==LOG_END-LOG_BASE
        # Only the very last byte is dirty: checking a prefix or stopping after
        # fewer than all four production chunks must make this test fail.
        nor.memory[LOG_END-1]=0x7f
        before=hashlib.sha256(nor.memory).hexdigest()
        await reset(dut)
        started_ns=get_sim_time(unit="ns")
        await First(RisingEdge(dut.status_error),Timer(50000,unit="us"))
        await Timer(1,unit="ns")
        elapsed_ns=get_sim_time(unit="ns")-started_ns
        assert int(dut.system.state.value)==15
        assert int(dut.status_error.value) and not int(dut.status_done.value)
        assert nor.operations==[{"opcode":3,"address":LOG_BASE+i*scan_chunk,"length":scan_chunk} for i in range(4)]
        assert hashlib.sha256(nor.memory).hexdigest()==before
        Path(os.environ["FLASH_REPORT"]).write_text(json.dumps({
            "passed":True,"physical_hardware_tested":False,
            "scope":"Full production log partition behavioral SPI scan; no electrical timing validation",
            "scenarios":["full_131072_byte_log_scan_rejects_dirty_final_byte_without_any_write"],
            "log_scan_bytes":scan_bytes,"log_scan_chunk_bytes":scan_chunk,
            "scan_to_rejection_simulation_ns":elapsed_ns,
            "scan_to_rejection_equivalent_at_12mhz_ms":elapsed_ns/10/12000,
            "measurement_excludes_power_up_startup_counter":True,
            "flash_initially_powered_down":True,"wake_events":nor.wake_events,
            "wake_minimum_fpga_cycles":nor.MIN_WAKE_CYCLES,
            "operations":nor.operations},indent=2)+"\n")
        return
    await reset(dut,direct=True)
    checked=["initial_deep_power_down_requires_AB_release_and_settling"]
    # Partition and page guards must reject before any SPI command or mutation.
    for address,length in [(0x10000,4),(LOG_BASE-1,1),(LOG_END,1),(LOG_END-1,2),
                           (LOG_BASE+255,2),(LOG_BASE,257),(LOG_BASE,0)]:
        before=len(nor.operations)
        await command(dut,address,length,data=b"x"*max(1,length),invalid=True)
        assert len(nor.operations)==before
    checked.append("write_partition_page_length_guards")
    payload=bytes(range(256))
    _,error=await command(dut,LOG_BASE+0x100,256,data=payload)
    assert not error
    actual,error=await command(dut,LOG_BASE+0x100,256)
    assert not error and actual==payload
    checked.append("full_page_program_WREN_WIP_and_readback")
    nor.program_busy_polls=8
    _,error=await command(dut,LOG_BASE+0x300,1,data=b"\x52")
    assert error,"bounded WIP poll limit not enforced"
    nor.wip=0;nor.program_busy_polls=2
    checked.append("WIP_poll_timeout")

    root=Path(os.environ["FLASH_ROOT"])
    model_path=Path(os.environ["FLASH_MODEL"])
    model=json.loads(model_path.read_text())
    frames=[]
    for i in range(2):
        vals=np.array([int(v,16) for v in (Path(os.environ["FLASH_VECTORS"])/f"replay_{i:03d}.hex").read_text().split()],dtype=np.int64)
        vals[vals>=32768]-=65536
        frames.append(vals)
    frames=np.stack(frames)
    # Five outputs from two source frames also exercise source-ring wrap and
    # record-page continuation (320 bytes spans two 256-byte program pages).
    run_frames=5
    image,_=build_replay_image(frames,model_path,period_cycles=1000,run_frames=run_frames)
    nor.memory[INPUT_BASE:INPUT_BASE+len(image)]=image
    nor.memory[LOG_BASE:LOG_END]=b"\xff"*(LOG_END-LOG_BASE)
    nor.operations=[]
    protected_hash=hashlib.sha256(nor.memory[:LOG_BASE]).hexdigest()
    await reset(dut)
    await wait_halt(dut)
    assert int(dut.status_done.value) and not int(dut.status_error.value)
    assert nor.operations[:4]==[{"opcode":3,"address":LOG_BASE+i*scan_chunk,"length":scan_chunk} for i in range(4)]
    log=parse_result_log(bytes(nor.memory[LOG_BASE:LOG_END]))
    assert log["record_count"]==run_frames
    for i,record in enumerate(log["records"]):
        reference=classify(frames[i%len(frames)],model)
        assert record["frame_id"]==i
        assert record["logits"]==reference["logits"].tolist(),(record,reference["logits"].tolist())
        assert record["class_id"]==reference["class_id"]
        assert record["error"]==0 and record["protocol_errors"]==0
        assert record["cycles_total"]==sum(record[k] for k in ("cycles_pre","cycles_dft","cycles_power","cycles_nn"))
    stats=struct.unpack_from("<8I",nor.memory,LOG_BASE+16)
    assert stats[0:5]==(0,run_frames*1024,run_frames*1024,0,0),stats
    programs=[op for op in nor.operations if op["opcode"]==2]
    assert programs[-1]=={"opcode":2,"address":LOG_BASE+12,"length":4,"data":"544d4f43"}
    assert all(LOG_BASE<=op["address"]<LOG_END and (op["address"]&255)+op["length"]<=256 for op in programs)
    assert hashlib.sha256(nor.memory[:LOG_BASE]).hexdigest()==protected_hash
    checked.append("two_real_source_frames_five_outputs_boot_CRC_compute_log_reference_match")
    checked.append("source_ring_wrap_and_record_page_continuation")
    # A reset must not erase or overwrite a committed log.
    old_log=bytes(nor.memory[LOG_BASE:LOG_END]);old_programs=len(programs)
    await reset(dut)
    await wait_halt(dut,timeout_us=2000)
    assert int(dut.status_error.value) and not int(dut.status_done.value)
    assert bytes(nor.memory[LOG_BASE:LOG_END])==old_log
    assert len([op for op in nor.operations if op["opcode"]==2])==old_programs
    checked.append("reset_preserves_existing_committed_log")
    for kind,offset in [("wrong_model_hash",32),("wrong_payload_CRC",4096)]:
        nor.memory[LOG_BASE:LOG_END]=b"\xff"*(LOG_END-LOG_BASE)
        corrupt=bytearray(image);corrupt[offset]^=1
        nor.memory[INPUT_BASE:INPUT_BASE+len(corrupt)]=corrupt
        before=len([op for op in nor.operations if op["opcode"]==2])
        await reset(dut)
        await wait_halt(dut,timeout_us=3000)
        assert int(dut.status_error.value) and not int(dut.status_done.value),kind
        assert len([op for op in nor.operations if op["opcode"]==2])==before
        assert nor.memory[LOG_BASE:LOG_END]==b"\xff"*(LOG_END-LOG_BASE)
        checked.append(kind+"_refuses_run_and_log_write")
    # Interrupted header programming must also block future overwrites, even
    # though an incomplete record cannot be parsed as a committed result log.
    nor.memory[INPUT_BASE:INPUT_BASE+len(image)]=image
    nor.memory[LOG_BASE:LOG_END]=b"\xff"*(LOG_END-LOG_BASE)
    nor.memory[LOG_BASE:LOG_BASE+4]=b"VLG1"
    before=bytes(nor.memory[LOG_BASE:LOG_END])
    old_programs=len([op for op in nor.operations if op["opcode"]==2])
    await reset(dut)
    await wait_halt(dut,timeout_us=2000)
    assert int(dut.status_error.value) and not int(dut.status_done.value)
    assert bytes(nor.memory[LOG_BASE:LOG_END])==before
    assert len([op for op in nor.operations if op["opcode"]==2])==old_programs
    checked.append("existing_uncommitted_partial_header_preserved")
    # First bytes remain erased, but a residual byte at the end of the final
    # simulated chunk must prevent all input reads, compute and log writes.
    nor.memory[LOG_BASE:LOG_END]=b"\xff"*(LOG_END-LOG_BASE)
    nor.memory[LOG_BASE+scan_bytes-1]=0xfe
    before=bytes(nor.memory[LOG_BASE:LOG_END]);nor.operations=[]
    await reset(dut)
    await wait_halt(dut,timeout_us=2000)
    assert int(dut.status_error.value) and not int(dut.status_done.value)
    assert bytes(nor.memory[LOG_BASE:LOG_END])==before
    assert nor.operations==[{"opcode":3,"address":LOG_BASE+i*scan_chunk,"length":scan_chunk} for i in range(4)]
    checked.append("four_chunk_log_scan_rejects_dirty_tail_with_erased_header")
    Path(os.environ["FLASH_REPORT"]).write_text(json.dumps({"passed":True,"physical_hardware_tested":False,
        "scope":"Behavioral SPI NOR functional simulation; not electrical or vendor timing validation",
        "scenarios":checked,"model_sha256":hashlib.sha256(model_path.read_bytes()).hexdigest(),
        "source_frames":len(frames),"run_frames":run_frames,
        "log_scan_bytes":scan_bytes,"log_scan_chunk_bytes":scan_chunk,
        "production_log_scan_bytes":LOG_END-LOG_BASE,
        "log_scan_accelerated_for_E2E":scan_bytes!=LOG_END-LOG_BASE,
        "flash_initially_powered_down":True,"wake_events":nor.wake_events,
        "wake_minimum_fpga_cycles":nor.MIN_WAKE_CYCLES,
        "log":log,"header_stats":list(stats),"programs":programs},indent=2)+"\n")
