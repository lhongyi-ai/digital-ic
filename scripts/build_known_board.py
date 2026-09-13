#!/usr/bin/env python3
"""Synthesize and route the complete KSR1/KSL1 application. No USB access."""
import argparse,json
from pathlib import Path
from build_support import yosys_quote
from build_known_probe import run
from experiment_acoustic_v2 import sha,dump
ROOT=Path(__file__).resolve().parents[1]
SOURCES=['rtl/core/vib_coeff_rom.sv','rtl/platform/spram16k.sv','rtl/core/known_capture.sv',
         'rtl/core/known_spectral_core.sv','rtl/io/spi_master.sv','rtl/io/flash_stream.sv',
         'rtl/io/known_replay_controller.sv','rtl/upduino_known.sv']

def main():
    p=argparse.ArgumentParser();p.add_argument('--machine',choices=('00','02','04','06'),default='00')
    p.add_argument('--lanes',type=int,choices=(1,4),default=4);p.add_argument('--run-id',required=True)
    p.add_argument('--abc-dff',action='store_true',help='Include flip-flops in ABC9 mapping');a=p.parse_args()
    model=ROOT/f'artifacts/acoustic-known-release-v1/id{a.machine}';m=json.loads((model/'model.json').read_text())
    freeze=json.loads((model.parent/'model-freeze.json').read_text())
    assert all(sha(ROOT/p)==h for p,h in freeze['sha256'].items()),'Frozen model input changed'
    out=ROOT/'build/known-board'/a.run_id;out.mkdir(parents=True,exist_ok=False)
    clock=out/'clock.py';clock.write_text('ctx.addClock("clk", 13.2)\n')
    bindings={str(p.relative_to(ROOT)):sha(p) for p in [*[ROOT/s for s in SOURCES],*model.glob('*.hex'),model/'model.json',
              model.parent/'model-freeze.json',ROOT/'configs/upduino-known.pcf',Path(__file__),ROOT/'scripts/build_known_probe.py',clock]}
    params=dict(BIAS=m['bias'],THRESHOLD=m['threshold'],LOG_CONSTANT=m['log_constant_q12'],LOG_FLOOR=m['log_floor_q12'])
    script='read_verilog -defer -sv -DICE40 '+' '.join(SOURCES)+';\n'
    script+=f'chparam -set LANES {a.lanes} -set MODEL_DIR "{model}" '
    script+=' '.join(f"-set {k} 32'h{v&0xffffffff:08x}" for k,v in params.items())
    script+=f" -set MODEL_HASH 256'h{bytes.fromhex(sha(model/'model.json'))[::-1].hex()} upduino_known;\n"
    script+=f'synth_ice40 -dsp {"-dff" if a.abc_dff else ""} -top upduino_known -json {yosys_quote(out/"netlist.json")};\nstat\n'
    (out/'synth.ys').write_text(script);dump(out/'attempt.json',dict(stage='started',input_sha256=bindings))
    try:
        run(['yosys','-Q','-T','-s',str(out/'synth.ys')],out/'synthesis.log')
        run(['nextpnr-ice40','--up5k','--package','sg48','--freq','13.2','--seed','1','--pre-pack',str(clock),
             '--pcf',str(ROOT/'configs/upduino-known.pcf'),'--json',str(out/'netlist.json'),
             '--asc',str(out/'board.asc'),'--report',str(out/'timing.json')],out/'place_route.log')
        timing=json.loads((out/'timing.json').read_text())
        assert timing['fmax'] and all(v['achieved']>=13.2 and v['constraint']>=13.199 for v in timing['fmax'].values())
        run(['icepack',str(out/'board.asc'),str(out/'board.bin')],out/'icepack.log')
        assert all(sha(ROOT/p)==h for p,h in bindings.items())
        report=dict(passed=True,input_sha256=bindings,machine=a.machine,lanes=a.lanes,utilization=timing['utilization'],
                    fmax=timing['fmax'],bitstream_sha256=sha(out/'board.bin'),model_sha256=sha(model/'model.json'),
                    nominal_clock_hz=12000000,clock_frequency_measured=False,physical_hardware=False,abc_dff=a.abc_dff,
                    scope='complete Flash replay application; not yet authorized by final-test gate')
        dump(out/'report.json',report);print(json.dumps(report|{'input_sha256':'saved'}))
    except BaseException as exc:
        dump(out/'failure.json',dict(error=str(exc),input_sha256=bindings));raise
if __name__=='__main__':main()
