#!/usr/bin/env python3
"""Prepare, submit and collect immutable Vivado packages over WashU SSH."""
import argparse,json,math,os,re,shlex,subprocess,sys,tarfile,time
from pathlib import Path
from known_vivado_support import sha,dump,manifest,verify,valid_run_id,validate_result
ROOT=Path(__file__).resolve().parents[1]
HOST= PRIVATE_VALUE_OMITTED
SOURCES=['rtl/core/vib_coeff_rom.sv','rtl/platform/spram16k.sv','rtl/core/known_capture.sv','rtl/core/known_spectral_core.sv']

def command(argv,**kwargs):
    result=subprocess.run(argv,text=True,**kwargs)
    if result.returncode:
        raise RuntimeError(f'command failed ({result.returncode}): {result.stderr or result.stdout or argv[0]}')
    return result
def ssh(code):return command(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=12',HOST,code],capture_output=True).stdout

def prepare(a):
    import numpy as np
    from threadpoolctl import threadpool_limits
    from vibfpga.known_fixed import prepare_windows,tables,rne_shift,power_log_q12
    out=ROOT/'build/vivado-portability'/valid_run_id(a.run_id);out.mkdir(parents=True,exist_ok=False)
    package=out/'package';package.mkdir();(package/'model').mkdir()
    model_dir=ROOT/f'artifacts/acoustic-known-release-v1/id{a.machine}'
    model=json.loads((model_dir/'model.json').read_text());freeze=json.loads((model_dir.parent/'model-freeze.json').read_text());verify(ROOT,freeze['sha256'])
    n,w=a.n,a.windows;f=n//2
    params=dict(N=n,WINDOWS=w,LANES=a.lanes,QUANT_PIPELINE=a.quant_pipeline,MODEL_DIR='model',BIAS=model['bias'],THRESHOLD=model['threshold'],LOG_CONSTANT=round((4+2*math.log2(n)+math.log2(w))*4096),LOG_FLOOR=model['log_floor_q12'])
    def hexfile(path,values,bits):path.write_text(''.join(f'{int(v)&((1<<bits)-1):0{(bits+3)//4}x}\n' for v in values))
    for name,bits in [('mean_q12',32),('gain_q24',32),('weights',8)]:hexfile(package/'model'/f'{name}.hex',model[name][:f],bits)
    hexfile(package/'model/cos_quarter.hex',tables(n)[0],16);hexfile(package/'model/log_lut.hex',np.rint(np.log2(1+np.arange(1024)/1024)*4096),12)
    bindings={str((model_dir/'model.json').relative_to(ROOT)):sha(model_dir/'model.json'),str((model_dir.parent/'model-freeze.json').relative_to(ROOT)):sha(model_dir.parent/'model-freeze.json')};records=[]
    for name in SOURCES+['sim/known_vivado_tb.sv','vivado/implement.tcl','vivado/core.xdc','scripts/run_known_vivado.py','scripts/known_vivado_support.py','src/vibfpga/known_fixed.py']:
        source=ROOT/name;bindings[name]=sha(source)
        if name in SOURCES:target=package/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes())
    (package/'implement.tcl').write_bytes((ROOT/'vivado/implement.tcl').read_bytes());(package/'core.xdc').write_bytes((ROOT/'vivado/core.xdc').read_bytes())
    (package/'known_vivado_tb.sv').write_bytes((ROOT/'sim/known_vivado_tb.sv').read_bytes())
    if a.stage=='sim':
        protocol=json.loads((ROOT/'artifacts/vivado-portability-v1/protocol.json').read_text());rows=protocol['records'][a.machine][:a.clips]
        if len(rows)!=a.clips:raise ValueError('insufficient frozen development records')
        raw_all=[];expected_frames=[];expected_final=[];scores=[]
        with threadpool_limits(limits=2):
            for row in rows:
                if row['role']!='cv':raise ValueError('not development record')
                path=ROOT/row['local'];assert sha(path)==row['npy_sha256'];bindings[row['local']]=sha(path);records.append(row)
                raw=np.load(path,allow_pickle=False)[:n*w];windowed,_=prepare_windows(raw[None,:],n)
                acc=(windowed.astype(np.float64)@tables(n)[3]).astype(np.int64);re,im=np.split(rne_shift(acc,8),2,axis=1)
                powers=rne_shift((re*re).astype(np.uint64)+(im*im).astype(np.uint64),8);sums=np.cumsum(powers,axis=0,dtype=np.uint64)
                logs=power_log_q12(sums[-1:],w,n)[0];qx=np.clip(rne_shift((logs-np.array(model['mean_q12'][:f]))*np.array(model['gain_q24'][:f]),24),-127,127)
                score=int(qx@np.array(model['weights'][:f])+model['bias']);scores.append(score);raw_all.extend(raw)
                for j in range(w):expected_frames.extend([*windowed[j],*re[j],*im[j],*powers[j],*sums[j]])
                expected_final.extend([*logs,*qx,score])
        hexfile(package/'raw.hex',raw_all,16);hexfile(package/'expected.hex',expected_frames+expected_final,64);hexfile(package/'scores.hex',scores,32)
        (package/'config.svh').write_text(''.join(f'`define {k} {v}\n' for k,v in (params|{'CLIPS':a.clips}).items() if k!='MODEL_DIR'))
        (package/'sim.tcl').write_text('run all\nquit\n')
    generics=' '.join(f'{k}={v}' for k,v in params.items())
    (package/'config.tcl').write_text(f'set stage {a.stage}\nset sources {{{" ".join(SOURCES)}}}\nset generics {{{generics}}}\n')
    # All compute runs in Slurm allocation; the login host only stages files.
    task='vivado -mode batch -source implement.tcl -log vivado.log -journal vivado.jou' if a.stage!='sim' else 'xvlog -sv -d AMD_FPGA -i . '+ ' '.join(SOURCES)+' known_vivado_tb.sv && xelab known_vivado_tb -timescale 1ns/1ps -mt 2 -s known_sim && xsim known_sim -tclbatch sim.tcl'
    inner='set -e; source /etc/profile.d/modules.sh; module use /project/linuxlab/environment.8/etc/modulefiles; module load xilinx24; vivado -version; '+task
    runner=f'''#!/bin/bash
#SBATCH --partition=linuxlab
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time={'08' if a.stage=='sim' else '04'}:00:00
#SBATCH --output=slurm.log
set -uo pipefail
cd "$SLURM_SUBMIT_DIR"
/usr/bin/apptainer exec --bind /project/engineering,/project/linuxlab /engrfs/cluster/containers/rocky-8.10.fl26.2.sif bash -c {shlex.quote(inner)} > run.log 2>&1
rc=$?
printf '{{"exit_code":%s}}\\n' "$rc" > status.json
python3 - <<'END'
import hashlib,json,pathlib
p=pathlib.Path('.')
files={{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(p.rglob('*')) if f.is_file() and str(f) not in ('outputs.json','slurm.log')}}
p.joinpath('outputs.json').write_text(json.dumps(files,indent=2))
END
exit "$rc"
'''
    (package/'job.sh').write_text(runner)
    info=dict(stage=a.stage,machine=a.machine,params=params,records=records,bindings=bindings,package_bindings=manifest(package),remote_dir='digital_ic_vivado/'+a.run_id)
    dump(package/'package.json',info);dump(out/'attempt.json',dict(info,preparation='prepared'));print(out);return out

def submit(out):
    info=json.loads((out/'package/package.json').read_text());verify(ROOT,info['bindings']);verify(out/'package',info['package_bindings'])
    assoc=ssh('sacctmgr -n -P show assoc where user="$USER" format=Cluster,Account,User,Partition,QOS; sinfo -h -p linuxlab -o "%P %a"')
    (out/'association.log').write_text(assoc)
    rows=[r.split('|') for r in assoc.splitlines() if '|' in r]
    if not any(len(r)>=4 and r[3] in ('','linuxlab') for r in rows) or 'linuxlab' not in assoc:raise RuntimeError('no confirmed linuxlab association')
    remote=info['remote_dir'];ssh('mkdir -p digital_ic_vivado; mkdir '+shlex.quote(remote))
    with tarfile.open(out/'package.tar','w') as archive:
        for p in (out/'package').rglob('*'):archive.add(p,arcname=p.relative_to(out/'package'),recursive=False)
    command(['scp',str(out/'package.tar'),HOST+':'+remote+'/package.tar'])
    checker="import json,hashlib,pathlib; p=pathlib.Path('.'); m=json.load(open('package.json'))['package_bindings']; assert all(hashlib.sha256((p/n).read_bytes()).hexdigest()==h for n,h in m.items())"
    accounts=sorted({r[1] for r in rows if len(r)>=4 and r[3] in ('','linuxlab')}); account='engr-class-any' if 'engr-class-any' in accounts else accounts[0]
    job=ssh('cd '+shlex.quote(remote)+' && tar xf package.tar && python3 -c '+shlex.quote(checker)+' && sbatch --parsable -A '+shlex.quote(account)+' job.sh').strip()
    (out/'submission.log').write_text(job+'\n')
    identifiers=re.findall(r'^([0-9]+)(?:;[^\n]+)?$',job,re.M)
    if len(identifiers)!=1:raise RuntimeError('no unique job ID; inspect submission.log before retrying')
    dump(out/'submission.json',dict(job_id=identifiers[0],remote_dir=remote));print(identifiers[0])

def collect(out):
    sub=json.loads((out/'submission.json').read_text());state=ssh('sacct -n -P -j '+sub['job_id']+' --format=JobID,State,ExitCode');(out/'slurm-state.log').write_text(state)
    terminal=next((r for r in state.splitlines() if r.startswith(sub['job_id']+'|')),None)
    if not terminal or any(s in terminal for s in ('|RUNNING|','|PENDING|','|COMPLETING|')):raise RuntimeError('job still active; see slurm-state.log')
    results=out/'results';results.mkdir(exist_ok=False)
    command(['scp','-r',HOST+':'+sub['remote_dir']+'/.',str(results)])
    info=json.loads((out/'package/package.json').read_text());verify(results,info['package_bindings'])
    if '|COMPLETED|0:0' not in terminal:
        dump(out/'failure.json',dict(passed=False,slurm_state=terminal,remote_job=sub,raw_results=str(results)))
        raise RuntimeError('remote job failed; raw results preserved')
    verify(ROOT,info['bindings'])
    result=validate_result(results,info['stage']);dump(out/'report.json',dict(passed=True,stage=info['stage'],params=info['params'],bindings=info['bindings'],remote_job=sub,result=result,mode={'impl':'implementation','sim':'simulation','synth':'synthesis'}[info['stage']],machine=info['machine'],lanes=info['params']['LANES'],quant_pipeline=info['params']['QUANT_PIPELINE'],input_sha256=info['package_bindings'],output_sha256=json.loads((results/'outputs.json').read_text()),records=info['records'],vivado='2024.2',vivado_build='5239630',completion_marker=True,io_delay_ns=2,timing=result if info['stage']=='impl' else None,windows=result.get('windows'),samples=result.get('samples'),intermediate_checks=result.get('intermediate_checks'),returncode=0,tool='Vivado',version='2024.2',part='xc7a35tcpg236-1',clock_period_ns=20,physical_hardware=False));print(json.dumps(result))

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','submit','collect','run']);p.add_argument('--run-id',required=True);p.add_argument('--stage',choices=['synth','impl','sim'],default='impl');p.add_argument('--machine',choices=['00','02','04','06'],default='00');p.add_argument('--lanes',type=int,choices=[1,4],default=4);p.add_argument('--quant-pipeline',type=int,choices=[0,1],default=0);p.add_argument('--clips',type=int,default=2);p.add_argument('--n',type=int,choices=[16,1024],default=1024);p.add_argument('--windows',type=int,default=156);a=p.parse_args()
    if not 1<=a.windows<=156 or not 1<=a.clips<=7:p.error('invalid clips/windows')
    out=ROOT/'build/vivado-portability'/valid_run_id(a.run_id)
    if a.action in ('prepare','run'):out=prepare(a)
    if a.action in ('submit','run'):submit(out)
    if a.action=='collect':collect(out)
if __name__=='__main__':main()
