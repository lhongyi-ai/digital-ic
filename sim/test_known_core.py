import json,os
from pathlib import Path
import numpy as np
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles,FallingEdge,RisingEdge,Timer,with_timeout
from vibfpga.known_fixed import prepare_windows,tables,rne_shift,integer_power,power_log_q12

M=json.loads(Path(os.environ['KNOWN_MODEL']).read_text());N=M['n'];WINDOWS=M['windows'];F=N//2

def reference(pcm):
    p,_=integer_power(pcm.reshape(1,-1),N);log=power_log_q12(p,WINDOWS,N)[0]
    value=(log-np.array(M['mean_q12'][:F]))*np.array(M['gain_q24'][:F])
    q=np.clip(rne_shift(value,24),-127,127)
    score=int(q@np.array(M['weights'][:F])+M['bias'])
    windows,_=prepare_windows(pcm.reshape(1,-1),N);c=rne_shift((windows.astype(float)@tables(N)[3]).astype(np.int64),8)
    powers=[]
    for w in pcm.reshape(WINDOWS,N):powers.append(integer_power(w[None,:],N)[0][0])
    return dict(score=score,log=log,features=q,windowed=windows,components=c,powers=np.array(powers),accum=np.cumsum(powers,axis=0))

async def reset(d):
    d.rst.value=1;d.in_valid.value=0;d.in_sample.value=0;d.in_frame_id.value=0;d.in_last.value=0;d.out_ready.value=0
    await ClockCycles(d.clk,4);await FallingEdge(d.clk);d.rst.value=0

async def send(d,pcm,start=0,gaps=True,partial=False):
    for i,s in enumerate(pcm):
        await FallingEdge(d.clk)
        if gaps and i%19==0:d.in_valid.value=0;await ClockCycles(d.clk,2);await FallingEdge(d.clk)
        d.in_valid.value=1;d.in_sample.value=int(s)&65535;d.in_frame_id.value=start+i//N;d.in_last.value=(i%N==N-1) and not partial
        await Timer(1,unit='ns')
        if not int(d.in_ready.value):await with_timeout(RisingEdge(d.in_ready),1000,'ms')
        await RisingEdge(d.clk)
    await FallingEdge(d.clk);d.in_valid.value=0;d.in_last.value=0

async def receive(d,expected,ident):
    if not int(d.out_valid.value):await with_timeout(RisingEdge(d.out_valid),1000,'ms')
    await Timer(1,unit='ns')
    actual=d.out_score.value.to_signed();assert actual==expected,(actual,expected)
    assert int(d.out_frame_id.value)==ident and int(d.out_class.value)==int(expected>M['threshold'])
    assert int(d.out_error.value)==0
    assert int(d.cycles_total.value)==sum(int(getattr(d,'cycles_'+s).value) for s in ('pre','dft','power','nn'))
    fields=['out_score','out_frame_id','out_class','out_error','cycles_total'];snapshot=[int(getattr(d,k).value) for k in fields]
    await ClockCycles(d.clk,17);await Timer(1,unit='ns');assert snapshot==[int(getattr(d,k).value) for k in fields]
    await FallingEdge(d.clk);d.out_ready.value=1;await RisingEdge(d.clk);await FallingEdge(d.clk);d.out_ready.value=0

@cocotb.test()
async def stages_and_backpressure(d):
    rng=np.random.default_rng(37)
    clips=[np.zeros(N*WINDOWS,dtype=np.int16),rng.integers(-32768,32768,N*WINDOWS,dtype=np.int16),
           np.rint(10000*np.sin(2*np.pi*3*np.arange(N*WINDOWS)/N)).astype(np.int16)]
    refs=[reference(x) for x in clips];expected={}
    for clip,ref in enumerate(refs):
        for w in range(WINDOWS):
            ident=clip*WINDOWS+w
            for kind,values in [(0,ref['windowed'][w]),(1,ref['components'][w,:F]),(2,ref['components'][w,F:]),(3,ref['powers'][w]),(4,ref['accum'][w])]:
                for k,value in enumerate(values):expected[ident,kind,k]=int(value)
            if w==WINDOWS-1:
                for kind,values in [(5,ref['log']),(6,ref['features']),(7,[ref['score']])]:
                    for k,value in enumerate(values):expected[ident,kind,k]=int(value)
    cocotb.start_soon(Clock(d.clk,10,unit='ns').start());await reset(d);seen=set();running=True
    async def trace():
        while running:
            await RisingEdge(d.clk);await Timer(1,unit='ns')
            if int(d.dbg_valid.value):
                key=(int(d.dbg_frame.value),int(d.dbg_kind.value),int(d.dbg_index.value));actual=d.dbg_value.value.to_signed()
                assert key in expected and key not in seen,(key,'unexpected/duplicate')
                assert actual==expected[key],(key,actual,expected[key], 'mean',d.mean.value.to_signed(),'raw',d.raw_q.value.to_signed());seen.add(key)
    monitor=cocotb.start_soon(trace())
    async def produce():
        for k,x in enumerate(clips):await send(d,x,k*WINDOWS)
    producer=cocotb.start_soon(produce())
    for k,r in enumerate(refs):await receive(d,r['score'],k*WINDOWS)
    await producer;running=False;await monitor
    assert seen==set(expected),(len(seen),len(expected));assert int(d.protocol_errors.value)==0
    Path(os.environ['KNOWN_REPORT']).write_text(json.dumps(dict(stages_passed=True,clips=len(clips),windows=len(clips)*WINDOWS,
        intermediate_checks=len(seen),physical_hardware=False,n=N,clip_windows=WINDOWS),indent=2))

@cocotb.test()
async def reset_cancels_transactions(d):
    x=np.random.default_rng(91).integers(-16000,16000,N*WINDOWS,dtype=np.int16);ref=reference(x)
    cocotb.start_soon(Clock(d.clk,10,unit='ns').start())
    for phase in ('input','processing','blocked_output'):
        await reset(d)
        if phase=='input':await send(d,x[:N//2],100,False,True)
        elif phase=='processing':await send(d,x[:N],100,False);await ClockCycles(d.clk,10)
        else:
            t=cocotb.start_soon(send(d,x,100,False));await with_timeout(RisingEdge(d.out_valid),1000,'ms');await t
        await reset(d);await ClockCycles(d.clk,5);assert not int(d.out_valid.value)
        t=cocotb.start_soon(send(d,x,200,False));await receive(d,ref['score'],200);await t
    p=Path(os.environ['KNOWN_REPORT']);r=json.loads(p.read_text());r['reset_phases']=['input','processing','blocked_output'];p.write_text(json.dumps(r,indent=2))
