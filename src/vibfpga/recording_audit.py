"""Waveform similarity screening; no labels used for model fitting."""
import numpy as np
from scipy.fft import rfft,irfft,next_fast_len

def lag_screen(x,groups,min_overlap):
    """All cross-group pairs, all integer lags with required overlap, Pearson correlation."""
    x=np.asarray(x,dtype=float);m,n=x.shape
    if not 1<min_overlap<=n or len(groups)!=m:raise ValueError('invalid inputs')
    lags=np.arange(-(n-min_overlap),n-min_overlap+1);length=n-np.abs(lags)
    ia=np.maximum(-lags,0);ja=np.maximum(lags,0)
    sums=np.pad(np.cumsum(x,axis=1),((0,0),(1,0)));sq=np.pad(np.cumsum(x*x,axis=1),((0,0),(1,0)))
    fft_n=next_fast_len(2*n-1);f=rfft(x,n=fft_n,axis=1)
    result=[]
    for i in range(m):
        js=np.array([j for j in range(i+1,m) if groups[j]!=groups[i]],dtype=int)
        si=sums[i,ia+length]-sums[i,ia];vi=sq[i,ia+length]-sq[i,ia]-si*si/length
        for start in range(0,len(js),32):
            jj=js[start:start+32];sj=sums[jj[:,None],ja+length]-sums[jj[:,None],ja]
            vj=sq[jj[:,None],ja+length]-sq[jj[:,None],ja]-sj*sj/length
            cross=irfft(f[jj]*np.conj(f[i]),n=fft_n,axis=1)[:,lags%fft_n]
            corr=(cross-si*sj/length)/np.sqrt(np.maximum(vi*vj,1e-30));corr=np.clip(corr,-1,1)
            best=np.abs(corr).argmax(1)
            for j,k,c in zip(jj,best,corr):result.append((i,int(j),float(c[k]),int(lags[k]),int(length[k])))
    return result

def refined_correlation(a,b,lag_samples,radius=32):
    best=(0.,0,0)
    for lag in range(lag_samples-radius,lag_samples+radius+1):
        ia=max(-lag,0);jb=max(lag,0);n=min(len(a)-ia,len(b)-jb)
        if n<=0:continue
        u=a[ia:ia+n].astype(float);v=b[jb:jb+n].astype(float);u-=u.mean();v-=v.mean()
        den=np.sqrt((u@u)*(v@v));c=float(u@v/den) if den>0 else 0.
        if abs(c)>abs(best[0]):best=(c,lag,n)
    return best
