import numpy as np
from vibfpga.cnn_normalization import normalize

def test_layout_and_cache_invariance(tmp_path):
    a=np.random.default_rng(9).normal(25,3,(3,4,128,32)).astype(np.float32)
    b=np.ascontiguousarray(a.transpose(0,1,3,2)).transpose(0,1,3,2)
    np.testing.assert_array_equal(normalize(a),normalize(b))
    path=tmp_path/'patch.npy';np.save(path,b)
    np.testing.assert_array_equal(normalize(np.load(path)),normalize(b))

def test_constant_and_nonfinite():
    import pytest
    assert np.all(normalize(np.full((1,4,128,32),25))==0)
    with pytest.raises(ValueError):normalize(np.full((1,4,128,32),np.nan))
