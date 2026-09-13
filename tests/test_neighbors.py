import json
from pathlib import Path
import numpy as np
import pytest
from vibfpga.fixed import frontend,frontend_batch_powers,quantize_features


def test_neighbor_sums_integer_powers_before_feature_quantization():
    rng=np.random.default_rng(1107)
    frames=rng.integers(-32768,32768,size=(5,64),dtype=np.int64)
    centers=[5,11]
    expanded=[4,5,6,10,11,12]
    shifts=[9,14]
    batch=frontend_batch_powers(frames,expanded,n=64)
    expected=batch.reshape(-1,2,3).sum(axis=2,dtype=np.int64)
    config={"n":64,"bins":centers,"dft_bins":expanded,"feature_mode":"neighbor3_energy","feature_shifts":shifts}
    for i,frame in enumerate(frames):
        result=frontend(frame,config)
        np.testing.assert_array_equal(result["dft_powers"],batch[i])
        np.testing.assert_array_equal(result["powers"],expected[i])
        np.testing.assert_array_equal(result["features"],quantize_features(expected,shifts)[i])
        assert result["real"].shape==(6,)
    with pytest.raises(ValueError,match="neighbor centers"):
        frontend(frames[0],{**config,"bins":[0,31]})
    with pytest.raises(ValueError,match="dft_bins"):
        frontend(frames[0],{**config,"dft_bins":list(reversed(expanded))})


def test_neighbor_candidate_has_validation_only_provenance_and_correct_dimensions():
    root=Path(__file__).resolve().parents[1]
    path=root/"artifacts/model_neighbor/model.json"
    if not path.exists(): pytest.skip("Predefined neighbor experiment has not been run")
    model=json.loads(path.read_text())
    assert model["test_evaluated"] is False
    assert model["feature_energy_accumulator_bits"]==34
    assert len(model["bins"])==16 and len(model["dft_bins"])==48
    assert len(model["w1"])==16 and len(model["w1"][0])==16
    for path in sorted((root/"artifacts/vectors_neighbor").glob("replay_*.json")):
        vector=json.loads(path.read_text())
        assert vector["provenance"]["split"]=="validation"
        assert len(vector["expected"]["real"])==48
        assert len(vector["expected"]["powers"])==16
        assert len(vector["expected"]["features"])==16
