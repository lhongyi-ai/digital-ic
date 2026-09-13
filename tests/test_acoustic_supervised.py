import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from train_acoustic_supervised import validate_extension,feature

def test_extension_cannot_reuse_validation_or_test():
    original={'records':[{'name':'train'},{'name':'validation'},{'name':'test'}]}
    for n in ['train','validation','test']:
        with pytest.raises(ValueError):validate_extension(original,{'records':[{'name':n,'split':'train','label':1}]})
    validate_extension(original,{'records':[{'name':'new','split':'train','label':1}]})

def test_features_independent_record_and_finite():
    rng=np.random.default_rng(7);x=rng.integers(-500,500,(2,16384))
    for k,d in [('band_mean_std',32),('spectrum1024',512),('spectrum4096',2048)]:
        f=feature(x,k);assert f.shape==(2,d) and np.isfinite(f).all()
        np.testing.assert_allclose(f[0],feature(x[:1],k)[0])
