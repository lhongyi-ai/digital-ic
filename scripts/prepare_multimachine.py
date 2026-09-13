#!/usr/bin/env python3
"""Freeze 00/02/04 development and 06 test; download only requested stage."""
import argparse,io,json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import numpy as np
from vibfpga.mimii import extract_record,sha
from vibfpga.multimachine import stable_order,validate_plan
ROOT=Path(__file__).resolve().parents[1]
def digest(p):return sha(p.read_bytes())
def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['development','test'],default='development');a=p.parse_args()
    d=ROOT/'data/mimii-multimachine';d.mkdir(exist_ok=True);(d/'pcm').mkdir(exist_ok=True);(d/'receipts').mkdir(exist_ok=True)
    original=json.loads((ROOT/'data/mimii/plan.json').read_text());excluded={r['name'] for r in original['records'] if r['split']=='test'}
    available={}
    for sub in ['mimii','mimii-supervised','mimii-external-id02']:
        dd=ROOT/'data'/sub;plan_path=dd/'plan.json';pr=json.loads(plan_path.read_text())
        for r in pr['records']:
            if r['name'] not in excluded:available[r['name']]={'path':str((dd/r['local']).relative_to(ROOT)),'source_plan':str(plan_path.relative_to(ROOT))}
    path=d/'plan.json'
    if not path.exists():
        index=json.loads((ROOT/'data/mimii/archive-index.json').read_text());records=[]
        for machine in ('00','02','04','06'):
            for label in (0,1):
                state='abnormal' if label else 'normal';eligible=[r for r in index if r['name'].startswith(f'fan/id_{machine}/{state}/') and r['name'] not in excluded]
                # Reuse existing allowed development data, then fixed hash order; no scores are inspected.
                eligible.sort(key=lambda r:(r['name'] not in available,stable_order(r['name'])))
                chosen=eligible[:80 if machine=='06' else 160];chosen.sort(key=lambda r:stable_order('roles:'+r['name']))
                for j,r in enumerate(chosen):
                    local=available.get(r['name'],{}).get('path',f'data/mimii-multimachine/pcm/{machine}_{state}_{Path(r["name"]).stem}.npy')
                    records.append({**r,'machine':machine,'label':label,'role':'final_test' if machine=='06' else ('calibration' if j<32 else 'fit'),
                      'local':local,'existing_source':available.get(r['name'])})
        plan={'schema':1,'archive':original['archive'],'seed':'multimachine-v1','snr_db':0,'channel':0,'records':records,
          'excluded_old_test':sorted(excluded),'old_plan_sha256':digest(ROOT/'data/mimii/plan.json'),
          'id02_status':'explicitly reassigned from external evaluation to development by user','test_policy':'06 not downloaded until final model freeze',
          'sampling':'prefer existing non-test development records then stable hash; roles hash-assigned within machine/label',
          'threshold':'maximum of source-machine normal calibration thresholds; never use held-machine labels to calibrate',
          'goal':{'recall':.9,'max_fpr':.05,'auc':.9}}
        validate_plan(plan);path.write_text(json.dumps(plan,indent=2)+'\n')
    plan=json.loads(path.read_text());validate_plan(plan);ph=digest(path)
    if a.stage=='test':
        frozen=ROOT/'artifacts/acoustic-multimachine-v1/frozen.json'
        if not frozen.exists():raise ValueError('06 locked until final freeze')
        f=json.loads(frozen.read_text());assert f['plan_sha256']==ph
        for rel,h in f['sha256'].items():assert digest(ROOT/rel)==h
    rows=[r for r in plan['records'] if (r['role']=='final_test')==(a.stage=='test')]
    print(a.stage,len(rows),'reuse',sum(bool(r['existing_source']) for r in rows),'new compressed bytes',sum(r['compressed'] for r in rows if not r['existing_source']),flush=True)
    def get(r):
        pcm_path=ROOT/r['local'];rp=d/'receipts'/f"{r['machine']}_{r['label']}_{Path(r['name']).stem}.json"
        if rp.exists():
            m=json.loads(rp.read_text());assert m['plan_sha256']==ph and m['npy_sha256']==digest(pcm_path);return
        if r['existing_source']:
            m=json.loads(pcm_path.with_suffix('.json').read_text());assert m['plan_sha256']==digest(ROOT/r['existing_source']['source_plan']) and m['npy_sha256']==digest(pcm_path)
        else:
            pcm,m=extract_record(r,plan['archive']['links']['self']);b=io.BytesIO();np.save(b,pcm,allow_pickle=False)
            if pcm_path.exists():assert pcm_path.read_bytes()==b.getvalue()
            else:pcm_path.write_bytes(b.getvalue())
        m={**m,'plan_sha256':ph,'npy_sha256':digest(pcm_path),'name':r['name'],'local':r['local']};rp.write_text(json.dumps(m,indent=2)+'\n')
    with ThreadPoolExecutor(max_workers=4) as pool:
        for i,f in enumerate(as_completed([pool.submit(get,r) for r in rows]),1):
            f.result()
            if i%40==0:print('Verified',i,'/',len(rows),flush=True)
    (d/f'{a.stage}-download.json').write_text(json.dumps({'complete':True,'records':len(rows),'plan_sha256':ph},indent=2)+'\n')
if __name__=='__main__':main()
