import numpy as np
from vibfpga.recording_audit import lag_screen,refined_correlation

def test_shift_gain_offset_and_split_filter():
    rng=np.random.default_rng(8);a=rng.normal(size=500);b=np.r_[rng.normal(size=37),2*a[:-37]+3];other=rng.normal(size=500)
    rows=lag_screen(np.stack([a,b,other]),['train','test','train'],200)
    pair=next(r for r in rows if r[:2]==(0,1))
    assert pair[2]>.999999 and pair[3]==37
    assert not any(r[:2]==(0,2) for r in rows)
    c,lag,n=refined_correlation(a,b,35,4);assert c>.999999 and lag==37 and n==463

def test_no_silence_false_positive():
    rows=lag_screen(np.zeros((2,100)),['train','test'],50)
    assert rows[0][2]==0

def test_fullrate_fractional_screen_shift_is_recovered():
    from scipy.signal import resample_poly
    rng=np.random.default_rng(17);a=rng.normal(size=48000)
    b=np.r_[rng.normal(size=37),1.4*a[:-37]+2]
    low=np.stack([resample_poly(x,1,32) for x in [a,b]])
    row=lag_screen(low,['train','test'],1000)[0]
    assert row[2]>.8
    c,lag,n=refined_correlation(a,b,row[3]*32,32)
    assert c>.999999 and lag==37
