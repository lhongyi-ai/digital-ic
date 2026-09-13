"""Bit-exact reference for docs/implementation-contract.md.

All array arithmetic is explicitly int64, with signed-width checks at the
datapath boundaries. No implicit int8/int32 multiplication is used. Scalar
rounding uses Python integers, including for INT64_MIN.

frontend returns intermediate arrays as well as ``features``; infer returns
``hidden_acc``, ``hidden``, ``logits`` and scalar ``class_id``. classify merges
these dictionaries. Coefficients are generated once per frame length and use
IEEE round-to-nearest, ties-to-even during offline generation.
"""

from functools import lru_cache
import math
import numpy as np


def round_shift_even(value, shift):
    """Return RNE(value / 2**shift), preserving scalar/array shape.

    Shift must be a nonnegative integer. Arrays must contain integral values;
    shifts beyond 62 use Python integers to avoid overflow in masks/absolute.
    """
    if not isinstance(shift, (int, np.integer)) or shift < 0:
        raise ValueError("shift must be a nonnegative integer")
    shift = int(shift)
    if np.isscalar(value):
        if not isinstance(value, (int, np.integer)):
            raise TypeError("round_shift_even requires integers")
        v = int(value)
        if not shift:
            return v
        q, r = divmod(abs(v), 1 << shift)
        half = 1 << (shift - 1)
        q += int(r > half or (r == half and q & 1))
        return -q if v < 0 else q
    a = np.asarray(value)
    if not np.issubdtype(a.dtype, np.integer):
        raise TypeError("round_shift_even requires integer arrays")
    a = a.astype(np.int64)
    if not shift:
        return a.copy()
    if shift > 62 or np.any(a == np.iinfo(np.int64).min):
        return np.array([round_shift_even(int(v), shift) for v in a.flat], dtype=np.int64).reshape(a.shape)
    magnitude = np.abs(a)
    quotient = magnitude >> shift
    remainder = magnitude & ((1 << shift) - 1)
    half = 1 << (shift - 1)
    quotient += ((remainder > half) | ((remainder == half) & ((quotient & 1) != 0))).astype(np.int64)
    return np.where(a < 0, -quotient, quotient)


def saturate(value, bits):
    """Saturate to signed ``bits``-bit range (scalar or integral array)."""
    if not isinstance(bits, int) or not 1 <= bits <= 63:
        raise ValueError("bits must be between 1 and 63")
    lo, hi = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
    if np.isscalar(value):
        return max(lo, min(hi, int(value)))
    return np.clip(np.asarray(value, dtype=np.int64), lo, hi)


def _signed_width(a, bits, name):
    a = np.asarray(a, dtype=np.int64)
    if a.size and (a.min() < -(1 << (bits - 1)) or a.max() > (1 << (bits - 1)) - 1):
        raise OverflowError(f"{name} exceeds signed {bits}-bit range")
    return a


@lru_cache(maxsize=16)
def coefficients(n):
    """Return periodic Hann, cosine table and negative-sine table, int64."""
    if n < 4 or n & (n - 1):
        raise ValueError("n must be a power of two >= 4")
    angle = 2 * np.pi * np.arange(n, dtype=np.float64) / n
    hann = np.rint((0.5 - 0.5 * np.cos(angle)) * (1 << 14)).astype(np.int64)
    cosine = np.rint(np.cos(angle) * (1 << 14)).astype(np.int64)
    nsine = np.rint(-np.sin(angle) * (1 << 14)).astype(np.int64)
    for a in (hann, cosine, nsine):
        a.setflags(write=False)
    return hann, cosine, nsine


def _config(config):
    n = int(config.get("n", 1024))
    if n < 4 or n & (n - 1):
        raise ValueError("n must be a power of two >= 4")
    bins = np.asarray(config["bins"], dtype=np.int64)
    if bins.ndim != 1 or len(bins) == 0 or np.any(bins < 0) or np.any(bins >= n // 2):
        raise ValueError("bins must be a nonempty 1D sequence in [0,n/2)")
    shifts = np.asarray(config.get("feature_shifts", [0] * len(bins)), dtype=np.int64)
    if shifts.shape != bins.shape or np.any(shifts < 0) or np.any(shifts > 63):
        raise ValueError("feature_shifts must match bins and lie in [0,63]")
    return n, bins, shifts


def frontend(samples, config):
    n, bins, shifts = _config(config)
    mode = config.get("feature_mode", "single_bin")
    if mode == "neighbor3_energy":
        if np.any(bins < 1) or np.any(bins + 1 >= n//2):
            raise ValueError("neighbor centers need legal k-1/k/k+1 DFT bins")
        expanded = (bins[:,None]+np.array([-1,0,1])[None,:]).reshape(-1)
        if "dft_bins" in config and not np.array_equal(config["dft_bins"],expanded):
            raise ValueError("dft_bins must be center-major k-1/k/k+1")
        result = frontend(samples,{**config,"feature_mode":"single_bin","bins":expanded,
                                   "feature_shifts":np.zeros(len(expanded),dtype=np.int64)})
        result["dft_powers"] = result["powers"]
        powers = result["dft_powers"].reshape(len(bins),3).sum(axis=1,dtype=np.int64)
        if np.any(powers >= 1<<34):
            raise OverflowError("three-bin feature exceeds unsigned 34-bit range")
        result["powers"] = powers
        result["features"] = np.array([min(127,max(0,round_shift_even(int(p),int(s))))
                                        for p,s in zip(powers,shifts)],dtype=np.int64)
        return result
    if mode != "single_bin":
        raise ValueError("unsupported feature_mode")
    raw = np.asarray(samples)
    if raw.shape != (n,) or not np.issubdtype(raw.dtype, np.integer):
        raise ValueError(f"samples must be a 1D integer array of length {n}")
    raw = _signed_width(raw, 16, "raw input")
    mean = round_shift_even(int(raw.sum(dtype=np.int64)), n.bit_length() - 1)
    centered = raw - mean
    _signed_width(centered, 17, "DC-centered sample")
    scaled = saturate(round_shift_even(centered, int(config.get("input_shift", 5))), 12)
    hann, cosine, nsine = coefficients(n)
    windowed = saturate(round_shift_even(scaled * hann, 14), 12)
    indices = (bins[:, None] * np.arange(n, dtype=np.int64)[None, :]) % n
    real_acc = cosine[indices] @ windowed
    imag_acc = nsine[indices] @ windowed
    _signed_width(real_acc, 40, "DFT real accumulator")
    _signed_width(imag_acc, 40, "DFT imaginary accumulator")
    shift = int(config.get("dft_shift", n.bit_length() - 1 + 10))
    real = saturate(round_shift_even(real_acc, shift), 16)
    imag = saturate(round_shift_even(imag_acc, shift), 16)
    powers = real * real + imag * imag
    if np.any(powers > (1 << 32) - 1):
        raise OverflowError("power exceeds unsigned 32-bit range")
    features = np.array([min(127, max(0, round_shift_even(int(p), int(s)))) for p, s in zip(powers, shifts)], dtype=np.int64)
    return {"mean": int(mean), "centered": centered.astype(np.int32),
            "scaled": scaled.astype(np.int16), "windowed": windowed.astype(np.int16),
            "real": real.astype(np.int16), "imag": imag.astype(np.int16),
            "real_acc": real_acc, "imag_acc": imag_acc, "powers": powers,
            "features": features}


def infer(features, model):
    """Integer MLP; arrays are output-neuron-major and ties choose index 0."""
    x = np.asarray(features, dtype=np.int64)
    w1 = np.asarray(model["w1"], dtype=np.int64)
    w2 = np.asarray(model["w2"], dtype=np.int64)
    b1 = np.asarray(model["b1"], dtype=np.int64)
    b2 = np.asarray(model["b2"], dtype=np.int64)
    if x.ndim != 1 or w1.ndim != 2 or w2.ndim != 2 or w1.shape[1] != x.size or w2.shape[1] != w1.shape[0]:
        raise ValueError("invalid feature/weight matrix dimensions")
    if b1.shape != (w1.shape[0],) or b2.shape != (w2.shape[0],):
        raise ValueError("bias dimensions do not match weights")
    if np.any(x < 0) or np.any(x > 127):
        raise ValueError("features must lie in [0,127]")
    if np.any(abs(w1) > 127) or np.any(abs(w2) > 127):
        raise ValueError("weights must lie in [-127,127]")
    _signed_width(b1, 32, "b1")
    _signed_width(b2, 32, "b2")
    hidden_acc = _signed_width(w1 @ x + b1, 32, "hidden accumulator")
    hidden = np.clip(round_shift_even(np.maximum(hidden_acc, 0), int(model["hidden_shift"])), 0, 127)
    logits = _signed_width(w2 @ hidden + b2, 32, "output accumulator")
    return {"hidden_acc": hidden_acc, "hidden": hidden, "logits": logits,
            "class_id": int(np.argmax(logits))}


def classify(samples, config, model=None):
    """Run the full integer front end and classifier; model may include config."""
    model = config if model is None else model
    result = frontend(samples, config)
    result.update(infer(result["features"], model))
    return result


def frontend_batch_powers(samples, bins, n=1024, input_shift=5):
    """Vectorized dataset extraction, exactly matching frontend for all bins.

    Fixed quantized DFT coefficients are used, rather than substituting an FFT
    over floating-point coefficients. Chunk the caller's frames for memory use.
    """
    raw = _signed_width(samples, 16, "batch input")
    if raw.ndim != 2 or raw.shape[1] != n:
        raise ValueError("batch must have shape [frames,n]")
    mean = round_shift_even(raw.sum(axis=1, dtype=np.int64), n.bit_length() - 1)
    scaled = saturate(round_shift_even(raw - mean[:, None], input_shift), 12)
    hann, cosine, nsine = coefficients(n)
    windowed = saturate(round_shift_even(scaled * hann[None, :], 14), 12)
    bins = np.asarray(bins, dtype=np.int64)
    indices = bins[:, None] * np.arange(n, dtype=np.int64)[None, :] % n
    re_acc, im_acc = windowed @ cosine[indices].T, windowed @ nsine[indices].T
    _signed_width(re_acc, 40, "batch real accumulator")
    _signed_width(im_acc, 40, "batch imag accumulator")
    re = saturate(round_shift_even(re_acc, n.bit_length() - 1 + 10), 16)
    im = saturate(round_shift_even(im_acc, n.bit_length() - 1 + 10), 16)
    return re * re + im * im


def quantize_features(powers, shifts):
    p = np.asarray(powers, dtype=np.int64)
    return np.stack([np.clip(round_shift_even(p[:, i], int(s)), 0, 127) for i, s in enumerate(shifts)], axis=1)
