import sys
from pathlib import Path
import numpy as np
import pytest
from vibfpga.multimachine import validate_plan,folds,source_threshold
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from train_multimachine import spectra,transform

def fixture():
    rows=[]
    for m in ['00','02','04','06']:
        for label in [0,1]:
            for i in range(80 if m=='06' else 160):
                state='abnormal' if label else 'normal'
                rows.append({'name':f'fan/id_{m}/{state}/{i}.wav','machine':m,'label':label,'role':'final_test' if m=='06' else ('calibration' if i<32 else 'fit')})
    return {'records':rows,'excluded_old_test':['old-test.wav']}

def test_split_and_fold_isolation():
    p=fixture();validate_plan(p);rows=[r for r in p['records'] if r['machine']!='06']
    for held,fit,cal,val in folds(rows):
        assert (len(fit),len(cal),len(val))==(512,128,320)
        assert all(rows[i]['machine']!=held for i in np.r_[fit,cal])
        assert all(rows[i]['machine']==held for i in val)
    with pytest.raises(ValueError):list(folds(p['records']))
    with pytest.raises(ValueError):spectra([{'role':'final_test'}],'not-read')

def test_old_test_and_identity_blocked():
    p=fixture();p['excluded_old_test']=[p['records'][0]['name']]
    with pytest.raises(ValueError):validate_plan(p)
    p=fixture();p['records'][-1]['role']='fit'
    with pytest.raises(ValueError):validate_plan(p)

def test_threshold_uses_worst_source_and_transforms_per_record():
    scores=np.r_[np.arange(32),np.arange(32)+100];labels=np.zeros(64);groups=np.array(['00']*32+['04']*32)
    t=source_threshold(scores,labels,groups)
    assert t==130 and all(np.mean(scores[groups==g]>t)<=.05 for g in ['00','04'])
    rng=np.random.default_rng(7);x=rng.normal(size=(3,512))
    for kind in ['absolute','shape','localcontrast']:
        np.testing.assert_allclose(transform(x,kind)[1],transform(x[1:2],kind)[0])
