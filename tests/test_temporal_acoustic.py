import numpy as np
from vibfpga.temporal_acoustic import modulation_features,extract

def test_modulation_detects_one_hz_and_is_gain_invariant():
    t=np.arange(624)/62.5;e=(2+np.sin(2*np.pi*t))[:,None]
    a=modulation_features(e)
    np.testing.assert_allclose(a,modulation_features(e*100),atol=1e-10)
    assert a[7]>.95 and a[8]<.01 and a[9]<.01
    assert a[4]<-.9 and a[5]>.99 and a[6]>.99

def test_silence_and_boundary():
    r=extract(np.zeros(160000));assert r['temporal'].shape==(320,)
    assert r['combined'].shape==(352,) and np.isfinite(r['combined']).all()
    import pytest
    with pytest.raises(ValueError):extract(np.zeros(159999))
