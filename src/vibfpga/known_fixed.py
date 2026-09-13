"""Integer full-spectrum front end for the known-machine linear classifier.

Float64 GEMM is used only as a fast exact integer dot implementation: integer
products and every possible partial sum are bounded below 2**53. No FFT is used.
"""
import numpy as np

def rne_shift(value, shift):
    value=np.asarray(value)
    if shift==0:return value.copy()
    quotient=value>>shift
    remainder=value & ((1<<shift)-1)
    half=1<<(shift-1)
    return quotient+((remainder>half)|((remainder==half)&((quotient&1)!=0))).astype(value.dtype)

def tables(n=1024):
    assert n>=4 and n&(n-1)==0
    quarter=np.rint(32767*np.cos(2*np.pi*np.arange(n//4)/n)).astype(np.int64)
    cosine=np.empty(n,dtype=np.int64)
    for phase in range(n):
        quadrant,index=divmod(phase,n//4)
        if quadrant==0:cosine[phase]=quarter[index]
        elif quadrant==1:cosine[phase]=0 if index==0 else -quarter[n//4-index]
        elif quadrant==2:cosine[phase]=-quarter[index]
        else:cosine[phase]=0 if index==0 else quarter[n//4-index]
    hann=rne_shift(32767-cosine,1)
    phases=(np.arange(n)[:,None]*np.arange(1,n//2+1)[None,:])%n
    # cos(theta+pi/2) is -sin(theta), the imaginary DFT coefficient.
    coefficients=np.concatenate([cosine[phases],cosine[(phases+n//4)%n]],axis=1).astype(np.float64)
    return quarter,cosine,hann,coefficients

def prepare_windows(pcm,n=1024):
    pcm=np.asarray(pcm)
    assert pcm.ndim==2 and pcm.dtype==np.int16 and pcm.shape[1]%n==0
    samples=rne_shift(pcm.astype(np.int64).reshape(-1,n),1)
    means=rne_shift(samples.sum(1),int(np.log2(n)))
    centered=samples-means[:,None]
    clipped=int(((centered>32767)|(centered< -32768)).sum())
    centered=np.clip(centered,-32768,32767)
    hann=tables(n)[2]
    windowed=rne_shift(centered*hann,15)
    return windowed,clipped

def integer_power(pcm,n=1024):
    frames=pcm.shape[1]//n;windowed,clipped=prepare_windows(pcm,n)
    # The absolute dot bound is <= n*32768*32767, well within exact float64 integers.
    assert n*32768*32767<2**53
    acc=windowed.astype(np.float64)@tables(n)[3]
    np.testing.assert_array_equal(acc,np.rint(acc))
    acc=acc.astype(np.int64);assert np.abs(acc).max(initial=0)<2**47
    complex_q=rne_shift(acc,8);assert np.abs(complex_q).max(initial=0)<2**31
    re,im=np.split(complex_q,2,axis=1)
    power=(re*re).astype(np.uint64)+(im*im).astype(np.uint64)
    power=rne_shift(power,8).reshape(len(pcm),frames,n//2).sum(1,dtype=np.uint64)
    # Samples shifted1, coefficients Q15, DFT result shifted8, square shifted8:
    # for N=1024, normalized power = total / (frames * 2**54).
    return power,dict(center_saturated=clipped,max_accumulator=int(np.abs(acc).max(initial=0)),frames=frames,
                      power_fraction_bits=2*(14+15+int(np.log2(n))-8)-8)

def power_log_q12(power,frames=156,n=1024):
    """Log power in raw PCM-count squared units, matching the trained spectrum()."""
    values=np.asarray(power,dtype=np.uint64)
    assert values.ndim==2 and frames>0
    lut=np.rint(np.log2(1+np.arange(1024)/1024)*4096).astype(np.int64)
    # The model used raw int16 counts, not samples divided by32768: restore 30 bits.
    constant=round((2*(14+15+int(np.log2(n))-8)-8-30+np.log2(frames))*4096)
    floor=round(np.log2(1e-12)*4096)
    out=np.empty(values.shape,dtype=np.int64)
    for index,v in np.ndenumerate(values):
        p=int(v)
        if p==0:out[index]=floor;continue
        exponent=p.bit_length()-1
        mantissa=(p>>(exponent-10)) if exponent>=10 else (p<<(10-exponent))
        out[index]=max(floor,exponent*4096+int(lut[mantissa-1024])-constant)
    return out

def quantized_features(log_q12,mean,input_scale,std):
    mean_q12=np.rint(np.asarray(mean)*4096).astype(np.int64)
    gain_q24=np.rint(2**24/(4096*np.asarray(std)*input_scale)).astype(np.int64)
    assert np.all(gain_q24>0) and gain_q24.max()<2**31
    product=(np.asarray(log_q12,dtype=np.int64)-mean_q12)*gain_q24
    assert np.abs(product).max(initial=0)<2**62
    features=np.clip(rne_shift(product,24),-127,127).astype(np.int8)
    return features,mean_q12,gain_q24
