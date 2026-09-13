#!/usr/bin/env python3
"""Freeze deployment, fetch the predetermined holdout, evaluate once, audit saved scores.

No training and no threshold selection occur after freeze. Download retries may
resume verified receipts; evaluation cannot overwrite an existing attempt.
"""
import argparse,collections,concurrent.futures,json,math
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scipy.stats import beta
from sklearn.metrics import roc_auc_score,confusion_matrix
from threadpoolctl import threadpool_limits
from vibfpga.known_fixed import integer_power,power_log_q12,rne_shift
from vibfpga.mimii import extract_record
from experiment_acoustic_v2 import sha,dump
ROOT=Path(__file__).resolve().parents[1]
IDS=('00','02','04','06')
BUNDLE=ROOT/'artifacts/acoustic-known-deployment-v1'
FINAL=ROOT/'artifacts/acoustic-known-final-v1'
DATA=ROOT/'data/mimii-known-final-v1'
PLAN=ROOT/'data/mimii-known-machines-v1/plan.json'
BOARD_RUNS=['l4-id00-r8','l4-id02-dff-r1','l4-id04-dff-r1','l4-id06-dff-r1','l1-id00-dff-r1']
REPORTS=[*(f'build/known-board/{r}/report.json' for r in BOARD_RUNS),
    *(f'build/known-native/{r}/report.json' for r in ('l4-1092-fixed16k-r2','l1-1092-backpressure-r2')),
    *(f'build/known-core/compact-l{l}-final/report.json' for l in (1,4)),
    'build/known-flash/small-r4/report.json',
    *(f'build/known-flash/full-id{m}-l4-r1/report.json' for m in IDS),
    'build/known-flash/full-id00-l1-r1/report.json']

def read(path):return json.loads(path.read_text())
def bind(mapping):
    assert mapping and all((ROOT/p).is_file() and sha(ROOT/p)==h for p,h in mapping.items()),'Evidence changed'

def final_rows():
    plan=read(PLAN);assert sha(PLAN)==read(PLAN.parent/'freeze.json')['plan_sha256']
    rows=[r for r in plan['records'] if r['role']=='final_test'];names={r['name'] for r in rows}
    assert len(rows)==len(names)==720
    assert not names&{r['name'] for r in plan['records'] if r['role']!='final_test'}
    assert not names&set(plan['old_test_excluded'])
    counts=collections.Counter((r['machine'],r['label']) for r in rows)
    assert counts=={(m,y):100 if y==0 else 80 for m in IDS for y in (0,1)}
    return rows

def frozen():
    f=read(BUNDLE/'freeze.json');bind(f['sha256']);assert f['test_count']==len(final_rows())
    return f

def freeze():
    assert not FINAL.exists() and not DATA.exists(),'Holdout access already started'
    final_rows();release=ROOT/'artifacts/acoustic-known-release-v1';mf=read(release/'model-freeze.json');bind(mf['sha256'])
    selected=ROOT/'artifacts/acoustic-known-integer-pipeline-v2';s=read(selected/'results.json');a=read(selected/'audit.json')
    assert s['passed'] and a['passed'] and a['results_sha256']==sha(selected/'results.json')
    unit_report=ROOT/'build/python-results.xml';tree=ET.parse(unit_report).getroot()
    assert list(tree.iter('testcase')) and not list(tree.iter('failure')) and not list(tree.iter('error'))
    paths=set(mf['sha256'])|{str(p.relative_to(ROOT)) for p in [release/'model-freeze.json',PLAN,PLAN.parent/'freeze.json',
        Path(__file__),ROOT/'scripts/run_known_hardware.py',ROOT/'scripts/run_hardware_replay.py',ROOT/'src/vibfpga/board.py',
        ROOT/'src/vibfpga/known_board.py',ROOT/'src/vibfpga/known_fixed.py',ROOT/'src/vibfpga/mimii.py',
        ROOT/'configs/upduino31-connected.json',selected/'results.json',selected/'audit.json',ROOT/'Makefile',unit_report]}
    for relative in REPORTS:
        p=ROOT/relative;r=read(p);assert r['passed'];bindings=r.get('bindings',r.get('input_sha256',{}));bind(bindings)
        paths.update(bindings);paths.add(relative)
        if 'bitstream_sha256' in r:
            assert r['abc_dff'] and all(v['achieved']>=13.2 and v['constraint']>=13.199 for v in r['fmax'].values())
            assert sha(p.parent/'board.bin')==r['bitstream_sha256'];paths.add(str((p.parent/'board.bin').relative_to(ROOT)))
        if 'output_sha256' in r:
            assert sha(p.parent/'output.bin')==r['output_sha256'];paths.add(str((p.parent/'output.bin').relative_to(ROOT)))
    # Recompute final calibration from saved integer DSP features, independently
    # of the exporter. No final audio is read during this check.
    dsp=ROOT/'artifacts/acoustic-known-integer-dsp-v2';receipt=read(dsp/'receipt.json');rows=receipt['rows']
    assert receipt['source_sha256']==sha(ROOT/'src/vibfpga/known_fixed.py') and receipt['log_sha256']==sha(dsp/'log-q12.npy')
    qlog=np.load(dsp/'log-q12.npy',allow_pickle=False)
    assert rows[:1024]==read(ROOT/'artifacts/acoustic-known-machines-v1/results.json')['records']
    for machine in IDS:
        m=read(release/f'id{machine}/model.json')
        fit=[i for i,r in enumerate(rows) if r['role']=='cv' and r['machine']==machine]
        cal=[i for i,r in enumerate(rows) if r['machine']==machine and r['role'] in ('calibration','calibration_extra') and r['label']==0]
        assert fit==m['train_indices'] and len(fit)==192 and cal==m['calibration_indices']
        x=np.clip(rne_shift((qlog-np.array(m['mean_q12']))*np.array(m['gain_q24']),24),-127,127)
        scores=x@np.array(m['weights'],dtype=np.int64)+m['bias']
        np.testing.assert_array_equal(scores,np.load(release/f'id{machine}/development-scores.npy'))
        assert sorted(int(scores[i]) for i in cal)[math.ceil((len(cal)+1)*.96)-1]==m['threshold']
        assert abs(m['bias'])+512*127*127<2**31
    paths.update(str(p.relative_to(ROOT)) for p in (dsp/'receipt.json',dsp/'log-q12.npy'))
    BUNDLE.mkdir(exist_ok=False)
    dump(BUNDLE/'freeze.json',dict(sha256={p:sha(ROOT/p) for p in sorted(paths)},test_count=720,
        reports=REPORTS,models=mf['models'],evaluation='known installed machines; independent held-out recording filenames; batches unverified',
        gates='Every ID and pooled: recall>0.90, FPR<0.05, AUC>=0.90; no post-test tuning',
        pooled_auc='(integer_score - integer_threshold) * input_scale * weight_scale',
        rate_intervals='95% Clopper-Pearson, conditional on independent Bernoulli recordings; batch independence unverified',
        scope='Final holdout can now be read once; hardware still requires final evaluation AND audit to pass'))
    print('DEPLOYMENT FROZEN; holdout still unopened',flush=True)

def download():
    frozen();assert not FINAL.exists(),'Evaluation already started';rows=final_rows();DATA.mkdir(exist_ok=True)
    for sub in ('pcm','receipts'):(DATA/sub).mkdir(exist_ok=True)
    source=read(ROOT/'data/mimii-multimachine/plan.json')['archive']['links']['self']
    freeze_hash=sha(BUNDLE/'freeze.json')
    if (DATA/'protocol.json').exists():assert read(DATA/'protocol.json')['deployment_sha256']==freeze_hash
    else:dump(DATA/'protocol.json',dict(deployment_sha256=freeze_hash,plan_sha256=sha(PLAN),records=rows,source=source))
    def one(row):
        stem=f"{row['machine']}_{row['label']}_{Path(row['name']).stem}";receipt=DATA/'receipts'/f'{stem}.json'
        if receipt.exists():
            r=read(receipt);assert r['deployment_sha256']==freeze_hash and r['name']==row['name']
            assert sha(ROOT/r['local'])==r['npy_sha256'];return dict(row,local=r['local'],npy_sha256=r['npy_sha256'])
        pcm,meta=extract_record(row,source);assert pcm.shape==(160000,) and pcm.dtype==np.int16
        path=DATA/'pcm'/f'{stem}.npy';temp=path.with_suffix('.part.npy');np.save(temp,pcm);temp.replace(path)
        result=dict(row,local=str(path.relative_to(ROOT)),npy_sha256=sha(path))
        dump(receipt,dict(meta,**result,deployment_sha256=freeze_hash));return result
    # On a network failure finish in-flight requests but cancel queued work;
    # successful receipts make a network-only resume deterministic.
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        completed=[]
        try:
            for count,row in enumerate(pool.map(one,rows),1):
                completed.append(row)
                if count%40==0:print('verified final downloads',count,'/720',flush=True)
        except BaseException:
            pool.shutdown(wait=True,cancel_futures=True);raise
    dump(DATA/'manifest.json',dict(deployment_sha256=freeze_hash,records=completed,passed=True))
    print('720 FINAL RECORDINGS DOWNLOADED; no scores computed',flush=True)

def interval(k,n):return [0. if k==0 else float(beta.ppf(.025,k,n-k+1)),1. if k==n else float(beta.ppf(.975,k+1,n-k))]
def metrics(rows,scores):
    y=np.array([r['label'] for r in rows]);ms=np.array([r['machine'] for r in rows]);threshold=[];margin=[]
    models={m:read(ROOT/f'artifacts/acoustic-known-release-v1/id{m}/model.json') for m in IDS}
    for row,score in zip(rows,scores):
        m=models[row['machine']]
        threshold.append(m['threshold']);margin.append((int(score)-m['threshold'])*m['input_scale']*m['weight_scale'])
    predicted=scores>np.array(threshold);groups={}
    for machine in (*IDS,'pooled'):
        mask=np.ones(len(rows),bool) if machine=='pooled' else ms==machine
        t=y[mask];p=predicted[mask];normal=int((t==0).sum());abnormal=int((t==1).sum())
        tp=int(p[t==1].sum());fp=int(p[t==0].sum());area=float(roc_auc_score(t,np.array(margin)[mask]))
        groups[machine]=dict(tp=tp,fp=fp,normal=normal,abnormal=abnormal,recall=tp/abnormal,fpr=fp/normal,auc=area,
            recall_ci95=interval(tp,abnormal),fpr_ci95=interval(fp,normal),passed=tp/abnormal>.9 and fp/normal<.05 and area>=.9)
    return groups

def evaluate():
    frozen();manifest=read(DATA/'manifest.json');assert manifest['passed'] and manifest['deployment_sha256']==sha(BUNDLE/'freeze.json')
    rows=manifest['records'];assert [{k:r[k] for k in original} for r,original in zip(rows,final_rows())]==final_rows() and len(rows)==720
    FINAL.mkdir(exist_ok=False)
    dump(FINAL/'attempt.json',dict(stage='started',deployment_sha256=sha(BUNDLE/'freeze.json'),manifest_sha256=sha(DATA/'manifest.json'),
        policy='one evaluation; no overwrite, model change or threshold adjustment based on this test'))
    logs=[];centered_saturation=0
    for start in range(0,len(rows),8):
        batch=rows[start:start+8];waves=[]
        for row in batch:
            path=ROOT/row['local'];assert sha(path)==row['npy_sha256'];waves.append(np.load(path,allow_pickle=False)[:159744])
        power,stats=integer_power(np.stack(waves));logs.extend(power_log_q12(power));centered_saturation+=int(stats['center_saturated'])
        if (start+8)%80==0:print('integer DSP',start+8,'/720',flush=True)
    qlog=np.array(logs);np.save(FINAL/'log-q12.npy',qlog);scores=np.zeros(len(rows),dtype=np.int64)
    for machine in IDS:
        m=read(ROOT/f'artifacts/acoustic-known-release-v1/id{machine}/model.json');indices=[i for i,r in enumerate(rows) if r['machine']==machine]
        qx=np.clip(rne_shift((qlog[indices]-np.array(m['mean_q12']))*np.array(m['gain_q24']),24),-127,127)
        scores[indices]=qx@np.array(m['weights'],dtype=np.int64)+m['bias']
    assert np.abs(scores).max()<2**31;np.save(FINAL/'scores.npy',scores);groups=metrics(rows,scores)
    dump(FINAL/'results.json',dict(passed=all(g['passed'] for g in groups.values()),groups=groups,records=rows,
        deployment_sha256=sha(BUNDLE/'freeze.json'),log_sha256=sha(FINAL/'log-q12.npy'),scores_sha256=sha(FINAL/'scores.npy'),
        centered_saturation=centered_saturation,final_test_opened=True,physical_hardware=False))
    print('FINAL RESULTS',json.dumps(groups),flush=True)

def audit():
    frozen();result=read(FINAL/'results.json');assert result['deployment_sha256']==sha(BUNDLE/'freeze.json')
    assert result['scores_sha256']==sha(FINAL/'scores.npy') and result['log_sha256']==sha(FINAL/'log-q12.npy')
    scores=np.load(FINAL/'scores.npy');logs=np.load(FINAL/'log-q12.npy');rows=result['records'];checks=0
    assert len(rows)==720 and [r['name'] for r in rows]==[r['name'] for r in final_rows()]
    # Scalar Python integer rounding/dot product; does not reuse the vectorized
    # quantizer or re-evaluate audio, and checks every saved recording score.
    models={m:read(ROOT/f'artifacts/acoustic-known-release-v1/id{m}/model.json') for m in IDS}
    for row,log,score in zip(rows,logs,scores):
        m=models[row['machine']];total=m['bias']
        for value,mean,gain,weight in zip(log,m['mean_q12'],m['gain_q24'],m['weights']):
            product=(int(value)-mean)*gain;q,rem=divmod(product,1<<24)
            q+=int(rem>(1<<23) or (rem==(1<<23) and q%2!=0));total+=max(-127,min(127,q))*weight
        assert total==int(score);checks+=1
    for machine,g in result['groups'].items():
        indices=[i for i,r in enumerate(rows) if machine=='pooled' or r['machine']==machine]
        y=[rows[i]['label'] for i in indices];prediction=[int(scores[i])>models[rows[i]['machine']]['threshold'] for i in indices]
        tn,fp,fn,tp=map(int,confusion_matrix(y,prediction,labels=[0,1]).ravel())
        margin=[(int(scores[i])-models[rows[i]['machine']]['threshold'])*models[rows[i]['machine']]['input_scale']*models[rows[i]['machine']]['weight_scale'] for i in indices]
        area=float(roc_auc_score(y,margin))
        assert (tp,fp,tn+fp,tp+fn)==(g['tp'],g['fp'],g['normal'],g['abnormal']) and area==g['auc']
        assert g['recall']==tp/(tp+fn) and g['fpr']==fp/(tn+fp)
        assert g['passed']==bool(tp/(tp+fn)>.9 and fp/(tn+fp)<.05 and area>=.9);checks+=1
    assert result['passed']==all(g['passed'] for g in result['groups'].values())
    dump(FINAL/'audit.json',dict(passed=True,quality_passed=result['passed'],checks=checks,results_sha256=sha(FINAL/'results.json'),
        deployment_sha256=sha(BUNDLE/'freeze.json'),source_sha256=sha(Path(__file__))))
    lines=['# Final test on 720 recordings after freezing','', 'Each machine has 100 normal and 80 faulty recordings. The model and thresholds were not changed based on test results.', '',
        '|Machine|Detected|False alarms|AUC|Passed|','|---|---|---|---|---|']
    for machine,g in result['groups'].items():lines.append(f'|{machine}|{g["tp"]}/{g["abnormal"]} ({g["recall"]:.2%})|{g["fp"]}/{g["normal"]} ({g["fpr"]:.2%})|{g["auc"]:.5f}|{g["passed"]}|')
    lines+=['','Recording-level 95% binomial intervals are saved in results.json and assume independent recordings. Unverified relationships between acquisition batches limit interpretation.',
        'These results support new recordings from covered devices and the same public data source only. They do not establish generalization to unknown fans or field environments. AUC=1 neither proves overfitting nor rules out background cues.',
        f'','Per-recording integer scores and grouped metrics reviewed: {checks} checks passed. Model and RTL are frozen in artifacts/acoustic-known-deployment-v1/freeze.json.',
        'This is the final software evaluation; hardware results are reported separately. A failed gate must not be presented as successful deployment after programming.']
    (ROOT/'docs/known-final-test.md').write_text('\n'.join(lines)+'\n');print('AUDIT PASS; quality passed =',result['passed'],flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('freeze','download','evaluate','audit'));args=parser.parse_args()
    with threadpool_limits(limits=2):globals()[args.action]()
