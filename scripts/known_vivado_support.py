"""Immutable package manifests and fail-closed Vivado result validation."""
import hashlib,json,re
from pathlib import Path

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n')
def manifest(directory):return {p.relative_to(directory).as_posix():sha(p) for p in sorted(Path(directory).rglob('*')) if p.is_file() and p.name not in ('package.json','outputs.json')}
def verify(directory,bindings):
    for name,digest in bindings.items():
        p=Path(name)
        if p.is_absolute() or '..' in p.parts:raise ValueError('unsafe manifest path')
        if not (Path(directory)/p).is_file() or sha(Path(directory)/p)!=digest:raise ValueError('binding mismatch: '+name)
def valid_run_id(value):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}',value):raise ValueError('unsafe run id')
    return value

def validate_result(directory,stage):
    directory=Path(directory)
    status=json.loads((directory/'status.json').read_text())
    if status.get('exit_code')!=0:raise RuntimeError('remote tool exit '+str(status.get('exit_code')))
    verify(directory,json.loads((directory/'outputs.json').read_text()))
    log=(directory/'run.log').read_text()
    if 'vivado v2024.2' not in log or 'SW Build 5239630' not in log:raise RuntimeError('unexpected Vivado version/build')
    if 'VIVADO_PORTABILITY_COMPLETE' not in log:raise RuntimeError('missing completion marker')
    if stage=='sim':
        result=json.loads((directory/'simulation.json').read_text())
        if result.get('passed') is not True:raise RuntimeError('simulation not passed')
    elif stage=='impl':
        result=json.loads((directory/'metrics.json').read_text())
        for key in ('internal_delay_ns','wns_ns','tns_ns','hold_wns_ns','hold_tns_ns'):
            if not isinstance(result.get(key),(int,float)):raise RuntimeError('missing '+key)
        details=(directory/'critical_paths.rpt').read_text()
        match=re.search(r'Data Path Delay:\s*([0-9.]+)ns\s*\(logic\s*([0-9.]+)ns\s*route\s*([0-9.]+)ns',details)
        if match:result.update(logic_delay_ns=float(match[2]),route_delay_ns=float(match[3]))
        for name in ('timing_summary.rpt','critical_paths.rpt','hold_paths.rpt','check_timing.rpt','drc.rpt','routed.dcp'):
            if not (directory/name).is_file():raise RuntimeError('missing '+name)
    else:result={'synthesis_completed':True}
    if not (directory/'utilization.rpt').is_file() and stage!='sim':raise RuntimeError('missing utilization')
    return result
