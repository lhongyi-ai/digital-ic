"""Layout-independent normalization for cached spectrogram patches."""
import numpy as np

def normalize(raw):
    a=np.array(raw,dtype=np.float64,order='C',copy=True)
    if a.ndim!=4 or not np.isfinite(a).all():raise ValueError('expected finite record/patch/frequency/time tensor')
    a-=a.mean(axis=(2,3),keepdims=True)
    return np.ascontiguousarray(a/4,dtype=np.float32)
