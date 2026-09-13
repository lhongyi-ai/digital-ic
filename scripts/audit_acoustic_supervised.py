#!/usr/bin/env python3
"""Independently recount fixed-validation predictions from saved supervised model."""
from pathlib import Path
import json
import joblib
import numpy as np
from train_acoustic_supervised import validate_extension
from experiment_acoustic_v2 import sha
ROOT=Path(__file__).resolve().parents[1]
def main():
    out=ROOT/'artifacts/acoustic-v7-supervised-r2';protocol=json.loads((out/'protocol.json').read_text());receipt=json.loads((out/'receipt.json').read_text())
    for rel,h in receipt['sha256'].items():
        if sha(ROOT/rel)!=h:raise ValueError('artifact changed '+rel)
    for rel,h in protocol['source_sha256'].items():
        if sha(ROOT/rel)!=h:raise ValueError('source changed '+rel)
    pp=ROOT/'data/mimii/plan.json';ep=ROOT/'data/mimii-supervised/plan.json'
    assert sha(pp)==protocol['plan_sha256'] and sha(ep)==protocol['extension_sha256']
    plan=json.loads(pp.read_text());ext=json.loads(ep.read_text());validate_extension(plan,ext)
    expected={str(Path('data/mimii')/r['local']) for r in plan['records'] if r['split'] in ('train','validation')}
    expected|={str(Path('data/mimii-supervised')/r['local']) for r in ext['records']}
    assert set(receipt['pcm_sha256'])==expected
    for rel,h in receipt['pcm_sha256'].items():
        assert sha(ROOT/rel)==h
    report=json.loads((out/'validation.json').read_text());selected=report['selected'];name=selected['name'];kind=name.rsplit('-',1)[0]
    f=np.load(out/(kind+'-features.npz'));assert f['train'].shape[0]==240 and f['validation'].shape[0]==70
    assert np.array_equal(f['train_labels'],np.r_[np.zeros(120),np.ones(120)])
    rows=[r for r in plan['records'] if r['split']=='validation'];labels=np.array([r['label'] for r in rows]);assert (labels==0).sum()==40 and (labels==1).sum()==30
    assert report['records']==[{'name':r['name'],'label':r['label']} for r in rows]
    model=joblib.load(out/(name+'.joblib'))
    scores=model.predict_proba(f['validation'])[:,1] if name.endswith('-trees') else model.decision_function(f['validation'])
    np.testing.assert_array_equal(scores,np.array(selected['scores']))
    pred=scores>selected['threshold'];tp=int(np.sum(pred&(labels==1)));fp=int(np.sum(pred&(labels==0)))
    an=scores[labels==1];no=scores[labels==0];auc=float(((an[:,None]>no).sum()+.5*(an[:,None]==no).sum())/(len(an)*len(no)))
    assert abs(auc-selected['auc'])<1e-12
    result={'model':name,'tp':tp,'fn':30-tp,'fp':fp,'tn':40-fp,'auc_pairwise':auc,'requirements':{'tp_at_least_27':tp>=27,'fp_at_most_2':fp<=2,'auc_at_least_0_90':auc>=.9},
       'high_standard_passed':tp>=27 and fp<=2 and auc>=.9,'task':'supervised known-fault recognition','test_opened':False,
       'receipt_sha256':sha(out/'receipt.json'),'verifier_sha256':sha(Path(__file__).resolve())}
    with (out/'goal-audit.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
