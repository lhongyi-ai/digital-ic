#!/usr/bin/env python3
"""Freeze known-machine recording splits from metadata only; no audio or fitting."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def order(name,tag): return hashlib.sha256(("known-machine-v1:"+tag+":"+name).encode()).hexdigest()

def main():
    destination=ROOT/'data/mimii-known-machines-v1'
    if destination.exists(): raise FileExistsError('Protocol exists; do not resplit')
    index_path=ROOT/'data/mimii/archive-index.json'
    index=json.loads(index_path.read_text()); seen=set(); old_test=set(); bindings={}
    for directory in sorted((ROOT/'data').glob('mimii*')):
        path=directory/'plan.json'
        if not path.exists():continue
        doc=json.loads(path.read_text()); records=doc.get('records',[])
        if not isinstance(records,list): continue
        relevant=[r for r in records if isinstance(r,dict) and r.get('name','').startswith('fan/id_')]
        if not relevant:continue
        bindings[str(path.relative_to(ROOT))]=sha(path)
        seen.update(r['name'] for r in relevant)
        old_test.update(r['name'] for r in relevant if r.get('split')=='test' or r.get('role')=='final_test')
        # Include downloaded named records even if absent from a selected-record list.
        for receipt in list(directory.glob('*.json'))+list((directory/'receipts').glob('*.json')):
            meta=json.loads(receipt.read_text())
            if isinstance(meta,dict) and meta.get('name','').startswith('fan/id_'):
                seen.add(meta['name']); bindings[str(receipt.relative_to(ROOT))]=sha(receipt)
    rows=[]; summary=[]
    for machine in ('00','02','04','06'):
        for label,state in ((0,'normal'),(1,'abnormal')):
            candidates={r['name']:r for r in index if r['name'].startswith(f'fan/id_{machine}/{state}/') and r['name'].endswith('.wav')}
            unused=sorted(set(candidates)-seen,key=lambda n:order(n,'final'))
            count=100 if label==0 else 80
            if len(unused)<count:raise ValueError('Insufficient untouched final recordings')
            final=set(unused[:count])
            available=set(candidates)-final-old_test
            development=sorted(available,key=lambda n:(n not in seen,order(n,'development')))[:128]
            if len(development)!=128:raise ValueError('Insufficient development recordings')
            development.sort(key=lambda n:order(n,'roles'))
            for i,name in enumerate(development):
                rows.append(dict(candidates[name],machine=machine,label=label,
                    role='calibration' if i<32 else 'cv',fold=None if i<32 else (i-32)%3))
            for name in sorted(final):rows.append(dict(candidates[name],machine=machine,label=label,role='final_test',fold=None))
            summary.append(dict(machine=machine,label=label,cv=96,calibration=32,final_test=count,unused_available=len(unused)))
    assert len(rows)==1744 and len({r['name'] for r in rows})==1744
    assert all(r['name'] not in seen for r in rows if r['role']=='final_test')
    assert not ({r['name'] for r in rows}&old_test)
    for machine in ('00','02','04','06'):
        for label in (0,1):
            for fold in range(3):
                assert sum(r['machine']==machine and r['label']==label and r['role']=='cv' and r['fold']==fold for r in rows)==32
    protocol=dict(schema=1,task='supervised known-machine fault classification on new recordings',
        claim_excludes='unseen-machine, unseen-model, independent-batch or unknown-fault guarantees',
        source='MIMII public 1.0 fan 0 dB, channel0, 16kHz, whole recordings',
        records=rows,counts=summary,prior_metadata_sha256=bindings,index_sha256=sha(index_path),
        script_sha256=sha(Path(__file__)),old_test_excluded=sorted(old_test),
        prior_selected_count=len(seen),audio_read=False,
        final_policy='metadata selected only; downloader must default to development, final PCM locked until quantized model/threshold/software frozen',
        grouping='all windows, channels and SNR versions of each name remain together; acquisition batch grouping requires verified metadata',
        models=['logistic_regression_32_to_1','mlp_32_to_16_to_1'],
        feature='shared 32 neighbor-power features from training-selected frequency centers; identical integer frontend for both candidates',
        gate=dict(recall_gt=.90,fpr_lt=.05,auc_ge=.90,scope='each machine AND pooled final recordings'),
        comparison='3 stratified within-machine recording folds; calibration excluded from fitting and fold validation; no final-test model selection',
        selection='if both meet development gates choose logistic; otherwise select passing MLP; neither passes: report failure, no automatic model expansion',
        final_refit='all CV records only; calibration kept separate; threshold and quantization frozen before final test')
    destination.mkdir()
    path=destination/'plan.json'; path.write_text(json.dumps(protocol,indent=2)+'\n')
    (destination/'freeze.json').write_text(json.dumps(dict(plan_sha256=sha(path),checks_passed=True,records=len(rows)),indent=2)+'\n')
    print(json.dumps(dict(path=str(path),records=len(rows),per_machine='192 CV + 64 calibration + 180 final',audio_read=False)))

if __name__=='__main__':main()
