import importlib.util
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from experiment_acoustic_finespectrum import spectrum

def test_frequency_peak_and_dc_invariance():
    for n in [1024,4096]:
        t=np.arange(n*3);x=100*np.sin(2*np.pi*16*t/n)
        p=spectrum(np.stack([x,x+1000]),n)
        assert p.shape==(2,n//2)
        assert p[0].argmax()==15
        np.testing.assert_allclose(p[0],p[1],rtol=1e-10,atol=1e-10)
