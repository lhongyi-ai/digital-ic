#!/usr/bin/env python3
"""Prepare a reviewable KSR1 replay; USB execution requires final-test success."""
import argparse,fcntl,json,math,plistlib,struct,subprocess,time
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from vibfpga.board import validate_profile
from vibfpga.known_board import build_image,parse_log,INPUT_BASE,LOG_BASE,LOG_BYTES
from vibfpga.known_fixed import integer_power,power_log_q12,rne_shift
from run_hardware_replay import execute_step,require_jedec,save_json,utc_now
from experiment_acoustic_v2 import sha
ROOT=Path(__file__).resolve().parents[1]

def verified_report(path):
    report=json.loads(path.read_text())
    assert report['passed'] and report['abc_dff'] and report['nominal_clock_hz']==12000000
    assert report['fmax'] and all(v['achieved']>=13.2 and v['constraint']>=13.199 for v in report['fmax'].values())
    assert all(sha(ROOT/p)==h for p,h in report['input_sha256'].items())
    assert sha(path.parent/'board.bin')==report['bitstream_sha256']
    return report

def final_gate(report_path):
    base=ROOT/'artifacts/acoustic-known-final-v1';audit=json.loads((base/'audit.json').read_text())
    result=json.loads((base/'results.json').read_text())
    assert audit['passed'] and audit['results_sha256']==sha(base/'results.json')
    assert result['passed'] and all(g['passed'] for g in result['groups'].values()),'Final quality gates failed; no programming'
    freeze=ROOT/'artifacts/acoustic-known-deployment-v1/freeze.json'
    assert result['deployment_sha256']==sha(freeze)
    frozen=json.loads(freeze.read_text());assert all(sha(ROOT/p)==h for p,h in frozen['sha256'].items())
    for path in (report_path,Path(__file__)):
        assert frozen['sha256'].get(str(path.relative_to(ROOT)))==sha(path),'Unfrozen deployment input'
    return sha(base/'audit.json'),sha(freeze)

def check_usb():
    tree=plistlib.loads(subprocess.check_output(['ioreg','-a','-p','IOUSB','-l']))
    found=[]
    def walk(node):
        if isinstance(node,list):
            for item in node:walk(item)
        elif isinstance(node,dict):
            if node.get('idVendor')==0x0403 and node.get('idProduct')==0x6014:
                found.append(node.get('USB Product Name',node.get('IORegistryEntryName','')))
            walk(node.get('IORegistryEntryChildren',[]))
    walk(tree)
    assert len(found)==1 and 'UPduino' in found[0],f'USB target is ambiguous or absent: {found}'
    return found[0]

def main():
    p=argparse.ArgumentParser();p.add_argument('--build-report',type=Path,required=True);p.add_argument('--run-id',required=True)
    p.add_argument('--record-index',type=int,default=0);p.add_argument('--period',type=int,default=750);p.add_argument('--execute',action='store_true');a=p.parse_args()
    report_path=a.build_report.resolve();report=verified_report(report_path)
    model=ROOT/f'artifacts/acoustic-known-release-v1/id{report["machine"]}/model.json';model_bytes=model.read_bytes();m=json.loads(model_bytes)
    assert sha(model)==report['model_sha256']
    profile_path=ROOT/'configs/upduino31-connected.json';profile=json.loads(profile_path.read_text())
    # The saved profile validator deliberately enforces the old VIB1 layout.
    # Verify its device/backup context before applying this protocol's constants.
    validate_profile(profile)
    profile.update(input_offset=INPUT_BASE,input_bytes=0x200000,log_offset=LOG_BASE,log_bytes=LOG_BYTES)
    assert profile['board_verified'] and profile['clock_source']=='hfosc12' and profile['expected_flash_id']=='EF4016'
    assert profile['flash_bytes']==4194304 and profile['erase_bytes']==4096
    assert 0<(report_path.parent/'board.bin').stat().st_size<=profile['config_end']<=INPUT_BASE
    backup=ROOT/profile['backup_path'];assert backup.stat().st_size==4194304 and sha(backup)==profile['backup_sha256']
    rows=json.loads((ROOT/'data/mimii-known-machines-v1/development.json').read_text())['records']
    pools={y:[r for r in rows if r['machine']==m['machine'] and r['role']=='cv' and r['label']==y] for y in (0,1)}
    assert 0<=a.record_index<2*min(map(len,pools.values()))
    row=pools[a.record_index%2][a.record_index//2];pcm=ROOT/row['local'];assert sha(pcm)==row['npy_sha256']
    raw=np.load(pcm,allow_pickle=False)[:159744];image=build_image(raw,model_bytes,a.period)
    power,_=integer_power(raw[None,:]);qlog=power_log_q12(power)[0]
    feature=np.clip(rne_shift((qlog-np.array(m['mean_q12']))*np.array(m['gain_q24']),24),-127,127)
    expected=int(feature@np.array(m['weights'])+m['bias'])
    out=ROOT/'measurements/known-replay'/a.run_id;out.mkdir(parents=True,exist_ok=False)
    for name,data in [('board.bin',(report_path.parent/'board.bin').read_bytes()),('input.bin',image),('model.json',model_bytes),('erased-log.bin',b'\xff'*LOG_BYTES)]:
        (out/name).write_bytes(data)
    save_json(out/'profile.json',profile);save_json(out/'build-report.json',report)
    commands=[('jedec',['iceprog','-d',profile['device'],'-t']),
        ('configuration',['iceprog','-d',profile['device'],'-i','4','-o','0',str(out/'board.bin')]),
        ('input',['iceprog','-d',profile['device'],'-i','4','-o',str(INPUT_BASE),str(out/'input.bin')]),
        ('clear_log_and_start',['iceprog','-d',profile['device'],'-i','4','-o',str(LOG_BASE),str(out/'erased-log.bin')])]
    wait=math.ceil(159744*a.period/10800000+2)
    manifest=dict(status='prepared',physical_hardware=False,started_utc=utc_now(),machine=m['machine'],lanes=report['lanes'],
        record=row,expected_score=expected,period=a.period,wait_seconds=wait,steps=[],commands=commands,
        source_sha256=sha(Path(__file__)),model_sha256=sha(model),bitstream_sha256=report['bitstream_sha256'],input_sha256=sha(out/'input.bin'),
        backup_sha256=profile['backup_sha256'],profile_sha256=sha(out/'profile.json'),build_report_sha256=sha(out/'build-report.json'))
    save_json(out/'manifest.json',manifest)
    if not a.execute:print('Prepared; no USB access:',out);return
    try:
        audit_hash,freeze_hash=final_gate(report_path);manifest.update(final_audit_sha256=audit_hash,deployment_sha256=freeze_hash)
        with (ROOT/'build/known-usb.lock').open('w') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);manifest['usb_product']=check_usb()
            for name,command in commands:
                step,text=execute_step(name,command,out,manifest)
                assert step['returncode']==0,f'{name} failed; see retained transcript'
                require_jedec(text,'EF4016')
            manifest.update(status='awaiting_result',physical_hardware=True);save_json(out/'manifest.json',manifest)
            print('Waiting',wait,'seconds for recorded replay',flush=True);time.sleep(wait)
            previous=None;reads=[]
            for index in range(1,4):
                path=out/f'read-{index}.bin'
                command=['iceprog','-d',profile['device'],'-o',str(LOG_BASE),'-R',str(LOG_BYTES),str(path)]
                step,text=execute_step(f'read-{index}',command,out,manifest)
                try:
                    assert step['returncode']==0;require_jedec(text,'EF4016');data=path.read_bytes()
                    r=parse_log(data,model_bytes,lanes=report['lanes'],period=a.period)
                    assert r['score']==expected and r['threshold']==m['threshold']
                    assert r['expected_crc']==struct.unpack('<I',image[24:28])[0]
                    reads.append(dict(file=path.name,sha256=sha(path),valid=True))
                    if previous and previous[1]==data:
                        (out/'result-log.bin').write_bytes(data)
                        manifest.update(status='passed',result=r,read_consensus=[previous[0],path.name],result_sha256=sha(out/'result-log.bin'));break
                    previous=(path.name,data)
                except (AssertionError,ValueError) as error:
                    reads.append(dict(file=path.name,valid=False,error=str(error)));previous=None
            manifest['reads']=reads
            assert manifest['status']=='passed','No two consecutive valid unmodified readbacks; retain this attempt for read-only recovery'
    except BaseException as error:
        manifest.update(status='failed',error=f'{type(error).__name__}: {error}');raise
    finally:
        manifest['finished_utc']=utc_now();save_json(out/'manifest.json',manifest)
    print('PHYSICAL PASS',out,flush=True)
if __name__=='__main__':
    with threadpool_limits(limits=2):main()
