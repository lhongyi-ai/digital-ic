"""Offline causal temporal features, 8 ms envelope steps, independent records."""
import numpy as np

def temporal_features(pcm, block):
    if block not in (64,128,256) or pcm.ndim!=2 or pcm.shape[1]<block*128:
        raise ValueError('records x samples; block must be 64,128,256 envelope frames')
    raw=pcm[:,:pcm.shape[1]//128*128].reshape(len(pcm),-1,128).astype(float)/32768
    raw=raw-raw.mean(2,keepdims=True)
    hann=.5-.5*np.cos(2*np.pi*np.arange(128)/128)
    p=np.abs(np.fft.rfft(raw*hann,axis=2))**2
    bands=p[:,:,1:].reshape(len(pcm),-1,16,4).sum(3)
    envelope=(raw**2).mean(2)
    eps=1e-16;result={k:[] for k in ['static','modulation','impact','flux','combined']}
    for start in range(0,bands.shape[1]-block+1,64):
        b=bands[:,start:start+block];e=envelope[:,start:start+block]
        static=np.log1p(b.mean(1))
        relative=b/np.maximum(b.mean(1,keepdims=True),eps)-1
        taper=.5-.5*np.cos(2*np.pi*np.arange(block)/block)
        spectrum=np.abs(np.fft.rfft(relative*taper[None,:,None],axis=1))**2/block**2
        freq=np.fft.rfftfreq(block,.008)
        mod=np.concatenate([np.log1p(spectrum[:,(freq>=lo)&(freq<hi)].sum(1)) for lo,hi in [(1,8),(8,24),(24,62.50001)]],axis=1)
        # Time-domain impacts: full block moments + normalized envelope autocorrelations.
        x=raw[:,start:start+block].reshape(len(pcm),-1);v=np.maximum((x*x).mean(1),eps)
        kurt=np.log1p((x**4).mean(1)/v**2)
        crest=np.log1p((x*x).max(1)/v)
        centered=e-e.mean(1,keepdims=True);denom=np.maximum((centered**2).mean(1),eps)
        correlations=[(centered[:,:-lag]*centered[:,lag:]).mean(1)/denom for lag in (2,4,8,16)]
        impact=np.stack([kurt,crest,np.log1p(e.std(1)/np.maximum(e.mean(1),eps)),*correlations],axis=1)
        shape=b/np.maximum(b.sum(2,keepdims=True),eps)
        delta=np.diff(shape,axis=1)
        flux=np.concatenate([np.abs(delta).mean(1),np.sqrt((delta*delta).mean(1))],axis=1)
        for name,extra in [('static',None),('modulation',mod),('impact',impact),('flux',flux),('combined',np.concatenate([mod,impact,flux],axis=1))]:
            result[name].append(static if extra is None else np.concatenate([static,extra],axis=1))
    return {k:np.stack(v,axis=1) for k,v in result.items()}
