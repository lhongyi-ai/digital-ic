"""Per-record modulation, transient and spectral-change features; no learned state."""
import numpy as np

def modulation_features(energy, rate=62.5):
    """Time x band nonnegative energy; gain-invariant temporal descriptors."""
    e=np.asarray(energy,dtype=np.float64)
    if e.ndim!=2 or len(e)<128 or np.any(e<0) or not np.isfinite(e).all():
        raise ValueError('expected finite nonnegative time x band energy')
    z=e/np.maximum(e.mean(0),1e-30)-1
    variance=np.mean(z*z,axis=0)
    kurt=np.mean(z**4,axis=0)/np.maximum(variance**2,1e-20)
    peak=np.quantile(z,.99,axis=0)
    flux=np.mean(np.abs(np.diff(z,axis=0)),axis=0)
    correlations=[]
    for seconds in (.5,1,2):
        lag=round(seconds*rate);a=z[:-lag];b=z[lag:]
        correlations.append(np.sum(a*b,axis=0)/np.maximum(np.sqrt(np.sum(a*a,axis=0)*np.sum(b*b,axis=0)),1e-20))
    power=np.abs(np.fft.rfft(z*np.hanning(len(z))[:,None],axis=0))**2
    hz=np.fft.rfftfreq(len(z),1/rate);total=np.maximum(power[1:].sum(0),1e-20)
    bands=[power[(hz>=lo)&(hz<hi)].sum(0)/total for lo,hi in ((.5,2),(2,8),(8,20))]
    return np.concatenate([np.log1p(variance),np.log1p(kurt),peak,flux,*correlations,*bands])

def extract(pcm):
    x=np.asarray(pcm,dtype=np.float64)
    if x.shape!=(160000,):raise ValueError('expected one 10-second 16 kHz recording')
    x=x-x.mean()
    frames=np.lib.stride_tricks.sliding_window_view(x,1024)[::256]
    power=np.abs(np.fft.rfft(frames*np.hanning(1024),axis=1))[:,1:]**2
    energy=power.reshape(len(power),32,16).sum(2)
    temporal=modulation_features(energy)
    log=np.log(np.maximum(energy,1e-20));shape=log.mean(0);shape-=shape.mean()
    return {'temporal':temporal,'combined':np.concatenate([temporal,shape])}
