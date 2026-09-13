import pytest
from vibfpga.mimii import make_plan,validate_plan

def test_split_is_deterministic_disjoint_and_normal_only():
    index=[{'name':f'fan/id_00/{label}/{i:08d}.wav'} for label in ['normal','abnormal'] for i in range(220)]
    p=make_plan(index,{});assert p==make_plan(list(reversed(index)),{})
    assert validate_plan(p) and len(p['records'])==280
    assert sum(r['split']=='train' for r in p['records'])==120
    p['records'].append(p['records'][0])
    with pytest.raises(ValueError,match='leakage'):validate_plan(p)

def test_training_anomaly_rejected():
    p={'records':[{'name':str(i),'label':int(i==0),'split':s} for i,s in enumerate(['train','validation','test'])]}
    with pytest.raises(ValueError,match='abnormal'):validate_plan(p)
