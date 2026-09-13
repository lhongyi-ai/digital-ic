import numpy as np
from vibfpga.known_fixed import rne_shift,tables,prepare_windows,integer_power,power_log_q12,quantized_features

def test_signed_rounding_boundaries():
    np.testing.assert_array_equal(rne_shift(np.arange(-9,10,dtype=np.int64),1),
        [-4,-4,-4,-3,-2,-2,-2,-1,0,0,0,1,2,2,2,3,4,4,4])
    np.testing.assert_array_equal(rne_shift(np.array([0,1,2,3,2**63],dtype=np.uint64),1),[0,0,1,2,2**62])

def test_dc_and_extreme_inputs():
    for value in (-32768,0,32767):
        p,stats=integer_power(np.full((1,32),value,dtype=np.int16),16)
        assert not p.any() and stats['center_saturated']==0
    p,stats=integer_power(np.tile(np.array([-32768,32767],dtype=np.int16),16)[None,:],16)
    assert int(p[0,-1])>0 and stats['max_accumulator']<2**47

def test_matrix_matches_scalar_integer_multiply_accumulate():
    n=16;pcm=np.random.default_rng(71).integers(-32768,32768,(3,n*2),dtype=np.int16)
    p,stats=integer_power(pcm,n);windows,_=prepare_windows(pcm,n);cos=tables(n)[1]
    expected=np.zeros((3,n//2),dtype=np.uint64)
    def rounded(v,s):
        q,r=divmod(v,2**s);return q+int(r>2**(s-1) or (r==2**(s-1) and q%2))
    for f,w in enumerate(windows):
        for k in range(1,n//2+1):
            re=rounded(sum(int(w[t])*int(cos[(k*t)%n]) for t in range(n)),8)
            im=rounded(sum(int(w[t])*int(cos[(k*t+n//4)%n]) for t in range(n)),8)
            expected[f//2,k-1]+=rounded(re*re+im*im,8)
    np.testing.assert_array_equal(p,expected)

def test_log_lut_error_and_quantizer_saturation():
    p=np.array([[0,1,2**24,2**40,2**60-1]],dtype=np.uint64)
    out=power_log_q12(p)
    exact=np.log2(np.maximum(p.astype(float)/(156*2**24),1e-12))*4096
    assert np.max(np.abs(out-exact))<7
    q,mean,gain=quantized_features(np.array([[-2**20,0,2**20]]),np.zeros(3),.1,np.ones(3))
    np.testing.assert_array_equal(q,[[-127,0,127]])

def test_coherent_sine_absolute_power_scale():
    n=64;amplitude=10000
    x=np.rint(amplitude*np.sin(2*np.pi*3*np.arange(n)/n)).astype(np.int16)[None,:]
    p,stats=integer_power(x,n)
    measured=float(p[0,2])/2**stats['power_fraction_bits']
    expected=(amplitude/(4*32768))**2
    assert np.isclose(measured,expected,rtol=.002)
    # Training features use PCM counts squared, so the matching log includes +30 bits.
    log=power_log_q12(p,frames=1,n=n)[0,2]/4096
    assert abs(log-np.log2((amplitude/4)**2))<.004
