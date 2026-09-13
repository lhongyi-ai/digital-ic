"""Small-dimension algorithm fixture, production SPI and full 4 KiB boot scan."""
import json,os
from pathlib import Path
import numpy as np
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles,FallingEdge,Timer,with_timeout
from test_flash_system import SpiNor
from vibfpga.known_board import build_image,parse_log,INPUT_BASE,LOG_BASE,LOG_BYTES
from vibfpga.known_fixed import integer_power,power_log_q12,rne_shift

@cocotb.test()
async def recording_transport(d):
    path=Path(os.environ['KNOWN_MODEL']);model_bytes=path.read_bytes();m=json.loads(model_bytes)
    n=m['n'];w=m['windows'];f=n//2
    raw=np.random.default_rng(719).integers(-30000,30001,n*w,dtype=np.int16)
    power,_=integer_power(raw[None,:],n);log=power_log_q12(power,w,n)[0]
    feature=np.clip(rne_shift((log-np.array(m['mean_q12'][:f]))*np.array(m['gain_q24'][:f]),24),-127,127)
    expected=int(feature@np.array(m['weights'][:f])+m['bias'])
    image=build_image(raw,model_bytes,n=n,windows=w)
    nor=SpiNor(d);d.rst.value=1;cocotb.start_soon(Clock(d.clk,10,unit='ns').start());task=cocotb.start_soon(nor.run())
    results=[]
    async def boot(img=None,blank=True,dirty=False):
        await FallingEdge(d.clk);d.rst.value=1;await ClockCycles(d.clk,5)
        if blank:nor.memory[LOG_BASE:LOG_BASE+LOG_BYTES]=b'\xff'*LOG_BYTES
        if dirty:nor.memory[LOG_BASE+LOG_BYTES-1]=0
        if img is not None:nor.memory[INPUT_BASE:INPUT_BASE+len(img)]=img
        nor.wel=False;nor.wip=0;nor.powered_down=True
        await FallingEdge(d.clk);d.rst.value=0
    async def finish(committed=True):
        for _ in range(4000):
            await ClockCycles(d.clk,100);await Timer(1,unit='ns')
            if int(d.controller.state.value)==14:break
        else:raise AssertionError(('timeout',int(d.controller.state.value),int(d.controller.errors.value),int(d.controller.loaded.value),int(d.controller.generated.value)))
        assert bool(int(d.status_done.value))==committed
        assert task.exception() is None if task.done() else True
    async def success(name):
        await boot(image);await finish()
        log=bytes(nor.memory[LOG_BASE:LOG_BASE+LOG_BYTES]);r=parse_log(log,model_bytes,n=n,windows=w)
        assert r['score']==expected and r['threshold']==m['threshold'],(r,expected)
        assert not int(d.status_error.value)
        writes=[v for v in nor.operations if v['opcode']==2]
        assert [(v['address'],v['length']) for v in writes[-2:]]==[(LOG_BASE,252),(LOG_BASE+252,4)]
        results.append(dict(case=name,**r));return log
    previous=await success('raw_pcm_to_committed_log')
    writes_before=len([v for v in nor.operations if v['opcode']==2])
    await boot(blank=False);await finish(False)
    assert bytes(nor.memory[LOG_BASE:LOG_BASE+LOG_BYTES])==previous
    assert len([v for v in nor.operations if v['opcode']==2])==writes_before
    results.append(dict(case='completed_log_preserved'))
    await boot(image,dirty=True);await finish(False)
    assert nor.memory[LOG_BASE:LOG_BASE+LOG_BYTES-1]==b'\xff'*(LOG_BYTES-1)
    assert nor.memory[LOG_BASE+LOG_BYTES-1]==0
    results.append(dict(case='partial_log_last_byte_preserved'))
    for name,damaged,mask,period in [
        ('model_hash_mismatch',image[:32]+bytes([image[32]^1])+image[33:],2,750),
        ('payload_crc_mismatch',image[:-1]+bytes([image[-1]^1]),4,750),
        ('fixed_rate_overload',build_image(raw,model_bytes,period=4,n=n,windows=w),24,4)]:
        await boot(damaged);await finish()
        r=parse_log(bytes(nor.memory[LOG_BASE:LOG_BASE+LOG_BYTES]),model_bytes,n=n,windows=w,period=period,allow_error=True)
        assert r['errors']&mask,(name,r)
        results.append(dict(case=name,**r))
    await success('reset_after_overload_recovers')
    Path(os.environ['KNOWN_REPORT']).write_text(json.dumps(dict(passed=True,cases=results,n=n,windows=w,fixture=True,
        actual_rtl_core=True,actual_spi_transport=True,full_sector_scan=True,physical_hardware=False),indent=2))
