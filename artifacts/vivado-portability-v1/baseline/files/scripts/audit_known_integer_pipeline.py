#!/usr/bin/env python3
"""Independent fixed-normalizer, score, threshold and metric checks on all folds."""
import json,math
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score
from experiment_acoustic_v2 import sha,dump
ROOT=Path(__file__).resolve().parents[1]

def main():
    out=ROOT/'artifacts/acoustic-known-integer-pipeline-v2';r=json.loads((out/'results.json').read_text());p=json.loads((out/'protocol.json').read_text())
    dsp=ROOT/'artifacts/acoustic-known-integer-dsp-v2';reference=ROOT/'artifacts/acoustic-known-int8-v1'
    assert p['script_sha256']==sha(ROOT/'scripts/evaluate_known_integer_pipeline.py')
    assert p['fixed_source_sha256']==sha(ROOT/'src/vibfpga/known_fixed.py')
    assert p['int8_reference_sha256']==sha(reference/'results.json') and p['dsp_receipt_sha256']==sha(dsp/'receipt.json')
    receipt=json.loads((dsp/'receipt.json').read_text());assert receipt['log_sha256']==sha(dsp/'log-q12.npy')
    qlog=np.load(dsp/'log-q12.npy');rows=r['records'];y=np.array([v['label'] for v in rows]);ms=np.array([v['machine'] for v in rows])
    original=json.loads((ROOT/'artifacts/acoustic-known-detail-v1/results.json').read_text());ptq=json.loads((reference/'results.json').read_text())
    votes=np.zeros(len(rows),int);pred=np.zeros(len(rows),bool);scores=np.full(len(rows),np.nan);checks=0
    for f in r['folds']:
        m,fold=f['machine'],f['fold'];before=next(v for v in ptq['folds'] if v['machine']==m and v['fold']==fold)
        source=next(v for v in original['folds'] if v['model']=='full512' and v['machine']==m and v['fold']==fold)
        assert f['weights']==before['weights'] and f['bias']==before['bias']
        np.testing.assert_array_equal(f['mean_q12'],np.rint(np.array(before['mean'])*4096).astype(np.int64))
        np.testing.assert_array_equal(f['gain_q24'],np.rint(2**24/(4096*np.array(before['std'])*before['input_scale'])).astype(np.int64))
        products=(qlog-np.array(f['mean_q12']))*np.array(f['gain_q24']);quotient,remainder=np.divmod(products,2**24)
        rounded=quotient+((remainder>2**23)|((remainder==2**23)&(quotient%2==1)))
        features=np.minimum(127,np.maximum(-127,rounded));weights=np.array(f['weights']);s=np.sum(features*weights,axis=1)+f['bias']
        val=np.array(f['validation_indices']);assert val.tolist()==source['validation_indices']
        np.testing.assert_array_equal(s[val],f['validation_scores'])
        cal=np.array(source['calibration_indices']);normal=s[cal[y[cal]==0]]
        if m=='00':normal=np.r_[normal,s[1024:]]
        np.testing.assert_array_equal(normal,f['normal_calibration_scores'])
        limit=int(sorted(normal)[math.ceil((len(normal)+1)*.96)-1]);assert limit==f['threshold']
        pred[val]=s[val]>limit;scores[val]=(s[val]-limit)*f['input_scale']*f['weight_scale'];votes[val]+=1
        assert int(pred[val][y[val]==1].sum())==f['tp'] and int(pred[val][y[val]==0].sum())==f['fp'];checks+=1
    assert all(votes[i]==int(row['role']=='cv') for i,row in enumerate(rows))
    for m,g in r['groups'].items():
        mask=(votes==1)&(True if m=='pooled' else ms==m);tp=int(pred[mask&(y==1)].sum());fp=int(pred[mask&(y==0)].sum())
        assert (tp,fp)==(g['tp'],g['fp']);assert g['recall']==tp/g['abnormal'] and g['fpr']==fp/g['normal']
        values=[]
        for fold in range(3):
            idx=np.array([i for i,row in enumerate(rows) if mask[i] and row['fold']==fold]);values.append(roc_auc_score(y[idx],scores[idx]))
        assert abs(np.mean(values)-g['auc'])<1e-12
        assert g['passed']==(g['recall']>.9 and g['fpr']<.05 and g['auc']>=.9);checks+=1
    assert r['passed']==all(g['passed'] for g in r['groups'].values()) and r['passed']
    dump(out/'audit.json',dict(passed=True,checks=checks,results_sha256=sha(out/'results.json'),protocol_sha256=sha(out/'protocol.json'),
        script_sha256=sha(Path(__file__)),all_scores_integer_exact=True,final_audio_read=False,scope='integer software, no RTL or board claim'))
    print('PASS',checks,'all integer scores exact; development gates passed')
if __name__=='__main__':main()
