"""Offline acoustic feature experiments; deliberately separate from frozen v1."""
import numpy as np


def filterbank(bands, kind, n=1024, rate=16000):
    """DC excluded. Full bands cover bins 1..N/2, including Nyquist."""
    if bands not in (16, 32) or kind not in ('uniform', 'mel', 'sparse'):
        raise ValueError('unsupported filterbank')
    w = np.zeros((bands, n // 2 + 1), dtype=np.float64)
    if kind == 'uniform':
        for row, bins in zip(w, np.array_split(np.arange(1, n // 2 + 1), bands)):
            row[bins] = 1
    elif kind == 'sparse':
        if bands != 16:
            raise ValueError('sparse baseline has 16 bands')
        for row, k in zip(w, np.rint(np.linspace(3, 480, 16)).astype(int)):
            row[k-1:k+2] = 1
    else:
        # Analytic triangular Mel filters; no package-specific defaults.
        to_mel = lambda f: 2595 * np.log10(1 + f / 700)
        edges = 700 * (10 ** (np.linspace(0, to_mel(rate / 2), bands + 2) / 2595) - 1)
        hz = np.arange(n // 2 + 1) * rate / n
        for row, (a, b, c) in zip(w, zip(edges[:-2], edges[1:-1], edges[2:])):
            row[:] = np.maximum(0, np.minimum((hz-a)/(b-a), (c-hz)/(c-b)))
        w[:, 0] = 0
    return w


def context(x, count):
    """Causal concatenation, stride one, never crosses recording boundaries."""
    x = np.asarray(x)
    if x.ndim != 3 or count not in (1, 4, 8) or x.shape[1] < count:
        raise ValueError('expected records x windows x features, valid context')
    return np.concatenate([x[:, i:x.shape[1]-count+1+i] for i in range(count)], axis=2)


def consecutive_alarm(scores, threshold, count=3):
    """Reset at each record; one decision every 64 ms after context warmup."""
    exceed = np.asarray(scores) > threshold
    runs = np.zeros(exceed.shape[0], dtype=int)
    detected = np.zeros_like(exceed, dtype=bool)
    for k in range(exceed.shape[1]):
        runs = np.where(exceed[:, k], runs + 1, 0)
        detected[:, k] = runs >= count
    return detected


def normal_threshold(values, fpr=.05):
    # Conservative empirical threshold: at most floor(n*fpr) strictly above it.
    v = np.sort(np.asarray(values))
    if v.ndim != 1 or len(v) == 0 or not 0 <= fpr < 1:
        raise ValueError('invalid normal threshold input')
    return float(v[max(0, len(v) - int(np.floor(len(v)*fpr)) - 1)])
