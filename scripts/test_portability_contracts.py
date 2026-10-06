#!/usr/bin/env python3
"""Isolated RAM and actual RTL arithmetic checks; no end-to-end claim."""
import argparse,hashlib,json,subprocess,shutil,os
from build_support import safe_alias
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
# Explicit scalar answers, independent of RTL rounding implementation.
CASES=[(0,0),(1,0),(0x7fffff,0),(0x800000,0),(0x800001,1),
       (0x1800000,2),(0x2800000,2),(0x3800000,4),
       (126<<24,126),((126<<24)+0x800000,126),
       ((126<<24)+0x800001,127),(127<<24,127),
       ((127<<24)+0x800000,127),(128<<24,127),((1<<63)-1,127)]
def run_checked(command,path,marker=None):
    with path.open('w') as log:r=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    if r.returncode:raise RuntimeError(f'exit {r.returncode}: {path}')
    if marker and marker not in path.read_text():raise RuntimeError(f'missing {marker}: {path}')
def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);a=p.parse_args()
    out=ROOT/'build/vivado-portability'/a.run_id;out.mkdir(parents=True,exist_ok=False)
    alias=safe_alias(ROOT/'.tools/oss-cad-suite')
    os.environ['PATH']=str(alias/'bin')+os.pathsep+os.environ['PATH']
    primitive=ROOT/'.tools/oss-cad-suite/share/yosys/ice40/cells_sim.v'
    sources=[ROOT/'rtl/platform/spram16k.sv',ROOT/'sim/spram_contract_tb.sv',Path(__file__)]
    backends=[]
    for name,define in [('reference',None),('amd','AMD_FPGA'),('ice40','ICE40')]:
        exe=out/(name+'.vvp');args=[str(alias/'libexec/iverilog'),'-B',str(alias/'lib/ivl'),'-g2012','-s','spram_contract_tb','-o',str(exe)]
        if define:args+=['-D'+define]
        args+=list(map(str,sources[:2]))
        if name=='ice40':args.append(str(primitive))
        run_checked(args,out/(name+'-compile.log'))
        run_checked([str(alias/'libexec/vvp'),str(exe)],out/(name+'-test.log'),'CONTRACT_PASS');backends.append(name)
    with (out/'dual-macro.log').open('w') as log:
        r=subprocess.run([str(alias/'libexec/iverilog'),'-B',str(alias/'lib/ivl'),'-g2012','-DICE40','-DAMD_FPGA','-s','spram_contract_tb','-o',str(out/'invalid.vvp'),*map(str,sources[:2]),str(primitive)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    if r.returncode==0 or 'INVALID_SIMULTANEOUS_RAM_BACKENDS' not in (out/'dual-macro.log').read_text():raise RuntimeError('dual macro not rejected for expected reason')
    core_sources=[ROOT/'rtl/core/vib_coeff_rom.sv',ROOT/'rtl/core/known_capture.sv',ROOT/'rtl/core/known_spectral_core.sv']
    # Icarus requires point before release_bank; reorder only the elaboration copy.
    # Original RTL remains bound and unchanged; this introduces no logic.
    original_core=core_sources[-1]
    core_copy=out/'known_spectral_core_icarus.sv'
    code=original_core.read_text()
    declaration='    reg [P-1:0] point;'
    # Preserve other declarations on the original line when moving point.
    assert declaration in code
    code=code.replace(declaration,'',1)
    code=code.replace('    wire release_bank=',declaration+'\n    wire release_bank=',1)
    core_copy.write_text(code)
    compile_sources=core_sources[:-1]+[core_copy]
    for pipeline in (0,1):
        checks=[]
        for value,expected in CASES:
            for negative in (0,1):
                checks.append(f"force dut.wide_acc=64'd{value};force dut.norm_negative=1'b{negative};#1;if($signed(dut.quantized_feature)!={-expected if negative else expected})$fatal(1,\"quant case {value}/{negative}\");")
        tb=out/f'quant-{pipeline}.sv';tb.write_text('`timescale 1ns/1ps\nmodule quant_tb;reg clk=0;always #5 clk=~clk;\n'+f'known_spectral_core #(.N(16),.WINDOWS(2),.QUANT_PIPELINE({pipeline})) dut(.clk(clk),.rst(1\'b1),.in_valid(1\'b0),.in_sample(16\'d0),.in_frame_id(32\'d0),.in_last(1\'b0),.out_ready(1\'b0));\n'+'initial begin force dut.wide_term=0;\n'+'\n'.join(checks)+'\n$display("ARITHMETIC_UNIT_PASS");$finish;end\nendmodule\n')
        exe=out/f'quant-{pipeline}.vvp'
        run_checked([str(alias/'libexec/iverilog'),'-B',str(alias/'lib/ivl'),'-g2012','-s','quant_tb','-o',str(exe),str(tb),str(sources[0]),*map(str,compile_sources)],out/f'quant-{pipeline}-compile.log')
        run_checked([str(alias/'libexec/vvp'),str(exe)],out/f'quant-{pipeline}-test.log','ARITHMETIC_UNIT_PASS')
    bound=sources+core_sources+[primitive]+list((ROOT/'artifacts/acoustic-known-release-v1/id00').glob('*.hex'))
    bindings={str(x.relative_to(ROOT)):sha(x) for x in bound}
    report=dict(passed=True,contract='spram16k',backends=backends,ram_modes=backends,dual_macro_rejected=True,
        arithmetic_unit_only=True,arithmetic_cases=len(CASES)*2,quant_pipeline_modes=[0,1],
        cases=['rne','saturation'],physical_hardware=False,bindings=bindings,
        input_sha256=sha(sources[0]),harness_adjustment='Icarus-only declaration-order move of point; no RTL logic changed',
        generated_harness_sha256={x.name:sha(x) for x in [core_copy,*out.glob('quant-*.sv')]},tools={'iverilog':shutil.which('iverilog'),'vvp':shutil.which('vvp')})
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report|{'bindings':'see report.json'}))
if __name__=='__main__':main()
