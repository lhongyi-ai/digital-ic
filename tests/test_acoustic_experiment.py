import numpy as np
import pytest
from vibfpga.acoustic_experiment import filterbank, context, consecutive_alarm, normal_threshold

def test_uniform_covers_every_non_dc_bin_once():
    for n in (16,32):
        w=filterbank(n,'uniform')
        np.testing.assert_array_equal(w.sum(0),[0]+[1]*512)
        assert (w>=0).all()
    assert np.count_nonzero(filterbank(16,'sparse').sum(0))==48

def test_mel_nonnegative_and_frequency_local():
    w=filterbank(32,'mel')
    assert (w>=0).all() and (w.sum(1)>0).all()
    assert np.all(np.diff(w.argmax(1))>0)
    assert not w[:,0].any()

def test_context_record_boundary_and_order():
    x=np.arange(2*10*2).reshape(2,10,2)
    for k in (1,4,8):
        y=context(x,k)
        assert y.shape==(2,11-k,2*k)
        for r in range(2):
            for t in range(11-k):np.testing.assert_array_equal(y[r,t],x[r,t:t+k].reshape(-1))
    with pytest.raises(ValueError):context(x,11)

def test_alarm_strict_threshold_and_record_reset():
    s=np.array([[0,2,2,2],[2,2,1,2]])
    np.testing.assert_array_equal(consecutive_alarm(s,1),[[0,0,0,1],[0,0,0,0]])

def test_threshold_caps_empirical_fpr_and_handles_ties():
    for x in (np.arange(40),np.ones(40),np.arange(7)):
        assert np.mean(x>normal_threshold(x))<=.05

def test_feasibility_loader_rejects_test_before_any_io():
    import importlib.util
    from pathlib import Path
    for name in ('experiment_acoustic_v2','experiment_acoustic_logpower'):
        spec=importlib.util.spec_from_file_location(name,Path(__file__).resolve().parents[1]/'scripts'/f'{name}.py')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        with pytest.raises(ValueError,match='test access prohibited'):
            m.load('test',{},'unused')

def test_band_assignment_tone_between_sparse_points():
    p=np.zeros(513);p[16]=100
    assert (filterbank(16,'sparse')@p).sum()==0
    assert (filterbank(16,'uniform')@p).sum()==100
