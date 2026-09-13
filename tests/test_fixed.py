from fractions import Fraction
import math
import numpy as np
import pytest
from vibfpga.fixed import (classify, coefficients, frontend, frontend_batch_powers,
                           infer, quantize_features, round_shift_even, saturate)


def test_round_shift_signed_ties_and_large_values():
    values = list(range(-200, 201)) + [-(2**63), -(2**40)-3, 2**40+3]
    for shift in [0, 1, 2, 5, 10, 40, 63, 64]:
        expected = [round(Fraction(v, 2**shift)) for v in values]
        assert [round_shift_even(v, shift) for v in values] == expected
        assert round_shift_even(np.array(values,dtype=np.int64),shift).tolist() == expected


def test_rounding_rejects_accidental_float_and_negative_shift():
    with pytest.raises(TypeError):
        round_shift_even(np.array([1.5]), 1)
    with pytest.raises(ValueError):
        round_shift_even(1, -1)


def test_saturation_limits():
    assert saturate(np.array([-9999, -2048, -1, 0, 2047, 9999]), 12).tolist() == [-2048,-2048,-1,0,2047,2047]


def test_dc_input_removes_constant_at_both_sensor_extrema():
    for level in [-32768, 32767, 43]:
        result = frontend(np.full(1024,level,dtype=np.int16), {"n":1024,"bins":[1,13,511]})
        assert result["mean"] == level
        assert not result["powers"].any()


def test_frontend_matches_independent_scalar_equations():
    n = 16
    samples = np.array([-32768,32767,1000,-2000,3000,19,23,-7,183,30001,-29901,62,11,-13,9,7],dtype=np.int16)
    bins = [0,1,3,7]
    result = frontend(samples,{"n":n,"bins":bins,"feature_shifts":[0,3,7,11]})
    mean = round(Fraction(sum(map(int,samples)),n))
    scaled = [max(-2048,min(2047,round(Fraction(int(x)-mean,32)))) for x in samples]
    hann = [round((0.5-0.5*math.cos(2*math.pi*i/n))*16384) for i in range(n)]
    window = [max(-2048,min(2047,round(Fraction(x*h,16384)))) for x,h in zip(scaled,hann)]
    for j,k in enumerate(bins):
        real_sum = sum(x*round(math.cos(2*math.pi*k*i/n)*16384) for i,x in enumerate(window))
        imag_sum = sum(x*round(-math.sin(2*math.pi*k*i/n)*16384) for i,x in enumerate(window))
        re = max(-32768,min(32767,round(Fraction(real_sum,n*1024))))
        im = max(-32768,min(32767,round(Fraction(imag_sum,n*1024))))
        assert result["real_acc"][j] == real_sum
        assert result["imag_acc"][j] == imag_sum
        assert result["powers"][j] == re*re+im*im
    assert result["windowed"].tolist() == window


def test_batch_feature_extraction_is_bit_exact():
    rng = np.random.default_rng(43)
    frames = rng.integers(-32768,32768,(11,64),dtype=np.int16)
    bins = [1,3,9,17,30]
    powers = frontend_batch_powers(frames,bins,n=64)
    expected = np.stack([frontend(frame,{"n":64,"bins":bins})["powers"] for frame in frames])
    np.testing.assert_array_equal(powers,expected)
    shifts = [0,10,12,14,20]
    quantized = quantize_features(powers,shifts)
    for i,frame in enumerate(frames):
        np.testing.assert_array_equal(quantized[i],frontend(frame,{"n":64,"bins":bins,"feature_shifts":shifts})["features"])


def test_coefficient_quarter_rom_reconstruction_all_addresses():
    for n in [16,64,1024]:
        hann, cosine, nsine = coefficients(n)
        quarter = cosine[:n//4]
        reconstructed = []
        for address in range(n):
            quadrant, offset = divmod(address,n//4)
            if quadrant in (1,3):
                magnitude = 0 if offset == 0 else quarter[n//4-offset]
            else:
                magnitude = quarter[offset]
            reconstructed.append(-int(magnitude) if quadrant in (1,2) else int(magnitude))
        np.testing.assert_array_equal(reconstructed,cosine)
        np.testing.assert_array_equal(np.roll(cosine,-n//4),nsine)
        hquarter = hann[:n//4]
        reconstructed_hann = []
        for address in range(n):
            quadrant, offset = divmod(address,n//4)
            if quadrant == 0:
                value = hquarter[offset]
            elif quadrant == 1:
                value = 8192 if offset == 0 else 16384-hquarter[n//4-offset]
            elif quadrant == 2:
                value = 16384-hquarter[offset]
            else:
                value = 8192 if offset == 0 else hquarter[n//4-offset]
            reconstructed_hann.append(value)
        np.testing.assert_array_equal(reconstructed_hann,hann)


def test_neural_output_order_relu_rounding_and_ties():
    model = {"w1":[[1,0],[0,-1],[0,0]],"b1":[1,0,5],"hidden_shift":1,
             "w2":[[1,1,1],[1,1,1],[-1,0,1]],"b2":[0,0,2]}
    result = infer([4,127],model)
    assert result["hidden_acc"].tolist() == [5,-127,5]
    assert result["hidden"].tolist() == [2,0,2]
    assert result["logits"].tolist() == [4,4,2]
    assert result["class_id"] == 0


def test_accumulator_overflow_is_not_silently_wrapped():
    model = {"w1":[[127]],"b1":[2**31-1],"hidden_shift":0,"w2":[[1]],"b2":[0]}
    with pytest.raises(OverflowError):
        infer([127],model)
