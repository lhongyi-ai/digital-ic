#!/usr/bin/env python3
"""UP5K area/timing probe, no application bitstream and no USB access."""
import argparse,json,subprocess
from pathlib import Path
from build_support import yosys_quote
from experiment_acoustic_v2 import sha,dump
ROOT=Path(__file__).resolve().parents[1]

def run(cmd,path):
    with path.open('w') as f:r=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    if r.returncode:raise RuntimeError(f'{cmd[0]} failed({r.returncode}); see {path}')

def main():
    p=argparse.ArgumentParser();p.add_argument('--lanes',type=int,choices=(1,4),default=4);p.add_argument('--run-id',required=True);a=p.parse_args()
    model=ROOT/'artifacts/acoustic-known-release-v1/id00';m=json.loads((model/'model.json').read_text())
    out=ROOT/'build/known-probe'/a.run_id;out.mkdir(parents=True,exist_ok=False)
    sources=[ROOT/s for s in ['rtl/core/vib_coeff_rom.sv','rtl/platform/spram16k.sv','rtl/core/known_capture.sv','rtl/core/known_spectral_core.sv','sim/known_pnr_probe.sv']]
    bindings={str(p.relative_to(ROOT)):sha(p) for p in [*sources,*model.glob('*.hex'),model/'model.json',Path(__file__)]}
    script='read_verilog -defer -sv -DICE40 '+ ' '.join(str(p.relative_to(ROOT)) for p in sources)+';\n'
    script+=f'chparam -set LANES {a.lanes} -set MODEL_DIR "{model}" -set BIAS 32\'h{m["bias"]&0xffffffff:08x} -set THRESHOLD 32\'h{m["threshold"]&0xffffffff:08x} -set LOG_CONSTANT {m["log_constant_q12"]} known_pnr_probe;\n'
    script+=f'synth_ice40 -dsp -top known_pnr_probe -json {yosys_quote(out/"netlist.json")};\nstat\n'
    (out/'synth.ys').write_text(script);dump(out/'attempt.json',dict(stage='started',input_sha256=bindings,scope='core implementation probe only'))
    run(['yosys','-Q','-T','-s',str(out/'synth.ys')],out/'synthesis.log')
    run(['nextpnr-ice40','--up5k','--package','sg48','--freq','13.2','--seed','1',
         '--json',str(out/'netlist.json'),'--asc',str(out/'probe.asc'),'--report',str(out/'timing.json')],out/'place_route.log')
    assert all(sha(ROOT/p)==h for p,h in bindings.items())
    timing=json.loads((out/'timing.json').read_text())
    dump(out/'report.json',dict(passed=True,input_sha256=bindings,lanes=a.lanes,utilization=timing['utilization'],fmax=timing['fmax'],
        scope='core plus low-pin observation probe, not board top',physical_hardware=False))
    print(json.dumps(dict(passed=True,utilization=timing['utilization'],fmax=timing['fmax'])))
if __name__=='__main__':main()
