import numpy as np
import pytest
from vibfpga.acoustic_temporal import temporal_features

def test_silence_finite_and_dimensions():
    for b in (64,128,256):
        r=temporal_features(np.zeros((2,32768)),b)
        for k,d in [('static',16),('modulation',64),('impact',23),('flux',48),('combined',103)]:
            assert r[k].shape==(2,(256-b)//64+1,d)
            assert np.isfinite(r[k]).all()

def test_modulated_carrier_detects_modulation_and_record_isolation():
    t=np.arange(32768)/16000
    steady=1000*np.sin(2*np.pi*1500*t)
    mod=steady*(1+.8*np.sin(2*np.pi*4*t))
    r=temporal_features(np.stack([steady,mod]),256)
    assert r['modulation'][1,0,16:32].sum()>r['modulation'][0,0,16:32].sum()+.01
    single=temporal_features(mod[None],256)
    for k in r:np.testing.assert_allclose(r[k][1:],single[k],rtol=1e-10,atol=1e-10)

def test_impulse_and_spectral_change_features():
    t=np.arange(32768)/16000
    x=1000*np.sin(2*np.pi*1500*t);spikes=x.copy();spikes[::1024]+=12000
    r=temporal_features(np.stack([x,spikes]),256)
    assert r['impact'][1,0,16]>r['impact'][0,0,16]
    assert r['flux'][1,0,16:].sum()>r['flux'][0,0,16:].sum()
    with pytest.raises(ValueError):temporal_features(x[None],12)
