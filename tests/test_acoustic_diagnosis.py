import importlib.util
from pathlib import Path
import numpy as np
spec=importlib.util.spec_from_file_location('diag',Path(__file__).resolve().parents[1]/'scripts/diagnose_acoustic_v3.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def test_recover_context_preserves_all_frames():
    from vibfpga.acoustic_experiment import context
    x=np.arange(2*156*16).reshape(2,156,16)
    np.testing.assert_array_equal(m.uncontext(context(x,8)),x)
def test_transient_pooling_no_cross_record():
    x=np.zeros((2,156));x[0,-4:]=8
    np.testing.assert_allclose(m.pool(x,'max4'),[8,0])
    np.testing.assert_allclose(m.pool(x,'top10'),[2,0])
    np.testing.assert_allclose(m.pool(x,'mean'),[32/156,0])
