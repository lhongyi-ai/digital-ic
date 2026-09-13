import numpy as np
import pytest
from vibfpga.acoustic import log_features,infer,Alarm

def test_log_power_boundaries():
    for e in range(33):
        p=1<<e
        if e<33:assert log_features([p])[0]==min(127,4*e)
        if e>1:assert log_features([p+(p//2)])[0]==min(127,4*e+2)
    assert log_features([0,1,2,3]).tolist()==[0,0,4,6]

def test_reconstruction_rounding_and_score():
    m={'w1':np.eye(16,dtype=int),'b1':np.zeros(16,dtype=int),'w2':np.eye(16,dtype=int),'b2':np.zeros(16,dtype=int),'hidden_shift':0,'output_shift':1}
    x=np.arange(16);r=infer(x,m);expected=np.rint(x/2).astype(int)
    assert np.array_equal(r['reconstruction'],expected)
    assert r['score']==sum((int(a)-int(b))**2 for a,b in zip(x,expected))

def test_alarm_strict_threshold_gaps_reset():
    a=Alarm(10,3)
    assert [a.accept(i,s) for i,s in enumerate([11,11,11,10,11])]==[False,False,True,False,False]
    assert not a.accept(7,11)
    assert not a.accept(8,11,error=True)
    a.reset();assert not a.accept(0,11)
