import json,os
from pathlib import Path
import numpy as np
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles,FallingEdge,RisingEdge,Timer,with_timeout
from vibfpga.acoustic import classify,Alarm

async def reset(d):
    d.rst.value=1;d.in_valid.value=0;d.out_ready.value=0;d.in_last.value=0;d.in_frame_id.value=0;d.in_sample.value=0
    await ClockCycles(d.clk,4);await FallingEdge(d.clk);d.rst.value=0

async def send(d,x,ident,gaps=False,complete=True):
    for i,v in enumerate(x):
        await FallingEdge(d.clk)
        if gaps and i%31==0:
            d.in_valid.value=0;await ClockCycles(d.clk,2);await FallingEdge(d.clk)
        d.in_valid.value=1;d.in_sample.value=int(v)&65535;d.in_frame_id.value=ident;d.in_last.value=complete and i==len(x)-1
        await Timer(1,unit='ns')
        if not int(d.in_ready.value):await with_timeout(RisingEdge(d.in_ready),20,'ms')
        await RisingEdge(d.clk)
    await FallingEdge(d.clk);d.in_valid.value=0;d.in_last.value=0

@cocotb.test()
async def arithmetic_stream_and_reset(d):
    m=json.loads(Path(os.environ['ACOUSTIC_MODEL']).read_text());n=m['n'];rng=np.random.default_rng(981)
    cases=[np.zeros(n,dtype=int),np.full(n,-32768),np.full(n,32767),np.where(np.arange(n)%2,-32768,32767),
           rng.integers(-32768,32768,n),np.rint(2000*np.sin(2*np.pi*m['bins'][0]*np.arange(n)/n)).astype(np.int16)]
    vd=Path(os.environ.get('ACOUSTIC_VECTORS','/nonexistent'))
    for p in sorted(vd.glob('replay_*.hex')):
        x=np.array([int(t,16) for t in p.read_text().split()],dtype=np.uint16).view(np.int16);cases.append(x)
    while len(cases)<int(os.environ.get('ACOUSTIC_FRAMES','0')):cases.append(rng.integers(-32768,32768,n))
    cocotb.start_soon(Clock(d.clk,10,unit='ns').start());await reset(d)
    alarm=Alarm(m['threshold'],m['alarm_windows']);checked=0
    async def receive(x,ident):
        nonlocal checked
        ref=classify(x,m)
        if not int(d.out_valid.value):await with_timeout(RisingEdge(d.out_valid),20,'ms')
        await Timer(1,unit='ns')
        word=int(d.out_logits.value);score=word&0xffffffff;threshold=(word>>32)&0xffffffff;streak=word>>64
        expected_alarm=alarm.accept(ident,ref['score'])
        assert score==ref['score'],(ident,score,ref['score'])
        assert threshold==m['threshold'] and streak==alarm.count
        assert int(d.out_class.value)==int(expected_alarm) and int(d.out_frame_id.value)==ident
        assert int(d.out_error.value)==0
        assert int(d.cycles_total.value)==sum(int(getattr(d,'cycles_'+k).value) for k in ['pre','dft','power','nn'])
        snapshot=[int(getattr(d,k).value) for k in ['out_logits','out_class','out_frame_id','out_error','cycles_total']]
        await ClockCycles(d.clk,17);await Timer(1,unit='ns')
        assert snapshot==[int(getattr(d,k).value) for k in ['out_logits','out_class','out_frame_id','out_error','cycles_total']]
        await FallingEdge(d.clk);d.out_ready.value=1;await RisingEdge(d.clk);await FallingEdge(d.clk);d.out_ready.value=0;checked+=1
    async def producer():
        for i,x in enumerate(cases):await send(d,x,i,gaps=True)
    producer_task=cocotb.start_soon(producer())
    for i,x in enumerate(cases):await receive(x,i)
    await producer_task
    # Reset during input, processing, and blocked output; cancel old transaction.
    for phase in ['input','processing','output']:
        await reset(d);alarm.reset()
        if phase=='input':await send(d,cases[4][:n//2],100,complete=False)
        else:
            await send(d,cases[4],100)
            if phase=='processing':await ClockCycles(d.clk,20)
            else:await with_timeout(RisingEdge(d.out_valid),20,'ms')
        await reset(d);await ClockCycles(d.clk,5);assert not int(d.out_valid.value)
        t=cocotb.start_soon(send(d,cases[4],200));await receive(cases[4],200);await t
    Path(os.environ['ACOUSTIC_REPORT']).write_text(json.dumps({'passed':True,'frames':checked,'scenarios':['zero','extremes','random','sinusoid','validation_waveforms','input_stalls','output_stalls','concurrent_frames','reset_input','reset_processing','reset_blocked_output'],'window_length':n,'unique_input_windows':len({np.asarray(x,dtype=np.int16).tobytes() for x in cases}),'physical_hardware':False},indent=2))

@cocotb.test()
async def intermediate_values(d):
    """Compare each exported internal stage, including every reconstruction term."""
    m=json.loads(Path(os.environ['ACOUSTIC_MODEL']).read_text());n=m['n']
    vectors=sorted(Path(os.environ['ACOUSTIC_VECTORS']).glob('replay_*.hex'))
    if vectors:x=np.array([int(t,16) for t in vectors[-1].read_text().split()],dtype=np.uint16).view(np.int16)
    else:x=np.random.default_rng(152).integers(-32768,32768,n)
    ref=classify(x,m)
    expected={0:[ref['mean']],1:ref['windowed'],2:ref['real'],3:ref['imag'],4:ref['powers'],5:ref['features'],
              6:ref['hidden'][:8],7:ref['output_acc'],8:ref['reconstruction'],9:ref['squared_errors']}
    seen={k:set() for k in expected}
    cocotb.start_soon(Clock(d.clk,10,unit='ns').start());await reset(d)
    producer=cocotb.start_soon(send(d,x,0))
    for _ in range(400000):
        await RisingEdge(d.clk);await Timer(1,unit='ns')
        if int(d.dbg_valid.value):
            kind,index=int(d.dbg_kind.value),int(d.dbg_index.value)
            value=int(d.dbg_value.value);value=value-(1<<40) if value&(1<<39) else value
            assert index not in seen[kind],('duplicate debug sample',kind,index)
            assert value==int(expected[kind][index]),(kind,index,value,int(expected[kind][index]))
            seen[kind].add(index)
        if int(d.out_valid.value):break
    else:raise AssertionError('intermediate trace timeout')
    await producer
    assert all(len(seen[k])==len(v) for k,v in expected.items()), {k:len(v) for k,v in seen.items()}
    path=Path(os.environ['ACOUSTIC_REPORT']);r=json.loads(path.read_text())
    r['intermediate_checks']={str(k):len(v) for k,v in seen.items()};r['intermediate_trace_source']=str(vectors[-1]) if vectors else 'synthetic random fixture'
    path.write_text(json.dumps(r,indent=2))
