#!/usr/bin/env python3
"""Audit saved physical replay artifacts and recompute expected scores. No USB."""
import argparse,collections,json,struct
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from vibfpga.known_board import parse_log
from vibfpga.known_fixed import integer_power,power_log_q12,rne_shift
from run_hardware_replay import require_jedec
from experiment_acoustic_v2 import sha,dump
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--expected-overload');a=p.parse_args()
    root=ROOT/'measurements/known-replay';passed=[];failures=[];cache={};bindings={}
    freeze=ROOT/'artifacts/acoustic-known-deployment-v1/freeze.json';f=json.loads(freeze.read_text())
    assert all(sha(ROOT/p)==h for p,h in f['sha256'].items())
    for path in sorted(root.glob('*/manifest.json')):
        m=json.loads(path.read_text());directory=path.parent
        if m['status']=='prepared':continue
        if m['status']!='passed':failures.append(dict(path=str(path.relative_to(ROOT)),status=m['status'],error=m.get('error')));continue
        assert m['physical_hardware'] and m['deployment_sha256']==sha(freeze)
        assert m['final_audit_sha256']==sha(ROOT/'artifacts/acoustic-known-final-v1/audit.json')
        assert m['source_sha256']==sha(ROOT/'scripts/run_known_hardware.py')
        for filename,key in [('board.bin','bitstream_sha256'),('input.bin','input_sha256'),('model.json','model_sha256'),
                             ('profile.json','profile_sha256'),('build-report.json','build_report_sha256'),('result-log.bin','result_sha256')]:
            assert sha(directory/filename)==m[key];bindings[str((directory/filename).relative_to(ROOT))]=m[key]
        bindings[str(path.relative_to(ROOT))]=sha(path)
        report=json.loads((directory/'build-report.json').read_text());assert report['passed'] and report['model_sha256']==m['model_sha256']
        assert all(sha(ROOT/p)==h for p,h in report['input_sha256'].items())
        for step in m['steps']:
            transcript=directory/step['transcript'];assert sha(transcript)==step['transcript_sha256']
            bindings[str(transcript.relative_to(ROOT))]=sha(transcript)
            if not step['name'].startswith('read-'):
                assert step['returncode']==0;require_jedec(transcript.read_text(),'EF4016')
        pair=m['read_consensus'];assert len(pair)==2 and pair[0]!=pair[1]
        log=(directory/'result-log.bin').read_bytes()
        for filename in pair:
            assert (directory/filename).read_bytes()==log
            step=next(s for s in m['steps'] if s['name']==Path(filename).stem)
            assert step['returncode']==0;require_jedec((directory/step['transcript']).read_text(),'EF4016')
            bindings[str((directory/filename).relative_to(ROOT))]=sha(directory/filename)
        model_bytes=(directory/'model.json').read_bytes();model=json.loads(model_bytes);image=(directory/'input.bin').read_bytes()
        result=parse_log(log,model_bytes,lanes=m['lanes'],period=m['period'])
        assert result['expected_crc']==struct.unpack('<I',image[24:28])[0]
        row=m['record'];source=ROOT/row['local'];assert sha(source)==row['npy_sha256']
        original=np.load(source,allow_pickle=False)[:159744].astype('<i2').tobytes();assert original==image[64:]
        key=(row['npy_sha256'],m['model_sha256'])
        if key not in cache:
            raw=np.frombuffer(original,dtype='<i2');power,_=integer_power(raw[None,:]);logq=power_log_q12(power)[0]
            feature=np.clip(rne_shift((logq-np.array(model['mean_q12']))*np.array(model['gain_q24']),24),-127,127)
            cache[key]=sum(int(x)*int(w) for x,w in zip(feature,model['weights']))+model['bias']
        assert result['score']==cache[key]==m['expected_score']
        passed.append(dict(path=str(path.relative_to(ROOT)),machine=m['machine'],lanes=m['lanes'],record=row['name'],
            source_sha256=row['npy_sha256'],period=m['period'],windows=156,samples=159744,**result))
    counts={str(l):sum(r['windows'] for r in passed if r['lanes']==l) for l in (1,4)}
    machines=sorted({r['machine'] for r in passed if r['lanes']==4})
    comparisons=[];compared=set()
    for baseline in [r for r in passed if r['lanes']==1]:
        pair_key=(baseline['machine'],baseline['source_sha256'])
        if pair_key in compared:continue
        other=next((r for r in passed if r['lanes']==4 and r['source_sha256']==baseline['source_sha256'] and r['machine']==baseline['machine']),None)
        if other:
            compared.add(pair_key)
            comparisons.append(dict(record=baseline['record'],single_cycles=baseline['cycles_total'],four_cycles=other['cycles_total'],
                compute_speedup=baseline['cycles_total']/other['cycles_total']))
    overload=None
    if a.expected_overload:
        directory=root/a.expected_overload;m=json.loads((directory/'manifest.json').read_text());assert m['status']=='failed' and m['physical_hardware']
        valid=[]
        for path in sorted(directory.glob('read-*.bin')):
            try:
                step=next(s for s in m['steps'] if s['name']==path.stem);require_jedec((directory/step['transcript']).read_text(),'EF4016')
                data=path.read_bytes();r=parse_log(data,(directory/'model.json').read_bytes(),lanes=1,period=750,allow_error=True)
                valid.append((path,data,r))
            except (ValueError,AssertionError):valid=[]
        assert len(valid)>=2 and valid[-1][1]==valid[-2][1]
        r=valid[-1][2];assert r['errors']==16 and r['generated']==r['accepted']+1 and r['protocol_errors']==0
        recovery=next((r for r in passed if r['lanes']==1 and r['machine']=='00' and r['period']==1500 and
            json.loads((ROOT/r['path']).read_text())['started_utc']>m['finished_utc']),None)
        assert recovery,'A successful same-core run after the overload is required'
        overload=dict(passed=True,attempt=a.expected_overload,result=r,recovery_attempt=recovery['path'],
            scope='intentional single-MAC input backpressure at period750, reset and normal period1500 recovery')
        for path in [directory/'manifest.json',valid[-1][0],valid[-2][0]]:bindings[str(path.relative_to(ROOT))]=sha(path)
    complete=counts['1']>=1000 and counts['4']>=1000 and machines==['00','02','04','06'] and len(comparisons)>=7
    resources={}
    for lanes,run in [(1,'l1-id00-dff-r1'),(4,'l4-id00-r8')]:
        directory=ROOT/'build/known-board'/run;report=json.loads((directory/'report.json').read_text())
        cells=json.loads((directory/'netlist.json').read_text())['modules']['upduino_known']['cells']
        kinds=collections.Counter(c['type'] for c in cells.values())
        resources[str(lanes)]=dict(post_route_lc=report['utilization']['ICESTORM_LC']['used'],synth_lut4=kinds['SB_LUT4'],
            synth_standalone_ff=sum(v for k,v in kinds.items() if k.startswith('SB_DFF')),
            dsp=report['utilization']['ICESTORM_DSP']['used'],ebr=report['utilization']['ICESTORM_RAM']['used'],
            spram=report['utilization']['ICESTORM_SPRAM']['used'],post_route_fmax_mhz=report['fmax']['clk']['achieved'])
        for path in (directory/'report.json',directory/'netlist.json'):bindings[str(path.relative_to(ROOT))]=sha(path)
    out=ROOT/'artifacts/evidence/known-hardware-audit.json'
    audit=dict(passed=complete,physical_runs=len(passed),unique_recordings=len({r['record'] for r in passed}),windows_by_lanes=counts,
        main_machines=machines,records=passed,comparisons=comparisons,failures_retained=failures,overload=overload,
        sha256=bindings,source_sha256=sha(Path(__file__)),deployment_sha256=sha(freeze),resources=resources,
        scope='Actual Flash replay; each boot156 continuous windows, counts summed across boots. Separate RTL regression demonstrates1092 continuous windows.',
        clock_frequency_measured=False)
    dump(out,audit)
    lines=['# UPduino 3.1 hardware replay of the frozen model','',f'Completed {len(passed)} passing replays covering {audit["unique_recordings"]} distinct public recordings. Each startup processes 156 consecutive windows; totals accumulate distinct physical runs.',
        'The four-MAC evidence for 1092 consecutive windows at a fixed input cadence comes from a separate RTL regression. Hardware windows accumulated across restarts are not one continuous run.','',
        '|MAC lanes|Passing hardware windows|','|---|---|',f'|1|{counts["1"]}|',f'|4|{counts["4"]}|','',
        'Every run checks the full Flash backup, JEDEC ID, and model/bitstream/input hashes. Results require two identical raw readbacks and passing commit-marker, CRC, counter, stage-cycle, and integer-score checks. Initial incorrect or misaligned reads are retained without truncating or patching bytes.',
        '', '|Same recording|Single-MAC active cycles|Four-MAC active cycles|Compute speedup|','|---|---|---|---|']
    for r in comparisons:lines.append(f'|{r["record"]}|{r["single_cycles"]}|{r["four_cycles"]}|{r["compute_speedup"]:.4f}|')
    lines+=['','|MAC|Placed LC|Synthesized LUT4|Synthesized standalone FF|DSP|EBR|SPRAM|Final Fmax MHz|','|---|---|---|---|---|---|---|---|']
    for lanes,r in resources.items():lines.append(f'|{lanes}|{r["post_route_lc"]}|{r["synth_lut4"]}|{r["synth_standalone_ff"]}|{r["dsp"]}|{r["ebr"]}|{r["spram"]}|{r["post_route_fmax_mhz"]:.4f}|')
    lines+=['','LC is the placed combined logic resource, not a pure LUT count. Standalone FF counts exclude registers inside DSP/RAM macros. Both versions use the same ABC9 register-mapping options and a 13.2 MHz constraint.']
    lines+=['','Speedup compares active computation cycles for the same recording. Four-MAC input arrives every 750 cycles; the single-MAC normal baseline uses 1500 cycles per sample. Different acquisition durations are not counted as pure compute speedup.',
        'Both clocks use nominal 12 MHz HFOSC. Actual frequency and power have not been measured. Results are actual FPGA replays of public audio, not microphone or field fan tests.',
        '',f'Intentional overload check: {overload["passed"] if overload else "not yet recorded"}; detailed errors and recovery runs are retained in the audit JSON.',
        'The final 720-recording quality metrics are in known-final-test.md and are reported separately from hardware numerical verification on development recordings.']
    (ROOT/'docs/known-hardware-results.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:audit[k] for k in ('passed','physical_runs','unique_recordings','windows_by_lanes','main_machines')}))
if __name__=='__main__':
    with threadpool_limits(limits=2):main()
