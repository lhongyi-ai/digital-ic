import json
from pathlib import Path
import numpy as np
from vibfpga.export import export_model, write_hex
from vibfpga.fixed import infer


def test_twos_complement_widths(tmp_path):
    path = tmp_path/"numbers.hex"
    write_hex(path,[-128,-1,0,127],8)
    assert path.read_text().splitlines() == ["80","ff","00","7f"]


def test_lane_weight_banks_match_neuron_major_contract(tmp_path):
    model = {"n":1024,"bins":list(range(1,17)),"feature_shifts":[3]*16,
             "w1":np.arange(256).reshape(16,16).tolist(),"w2":np.arange(48).reshape(3,16).tolist(),
             "b1":[0]*16,"b2":[0]*3,"hidden_shift":3,"dft_shift":20}
    export_model(model,tmp_path)
    read = lambda name:[int(x,16) for x in (tmp_path/name).read_text().splitlines()]
    assert read("hann_quarter.hex") == read("hann.hex")[:256]
    assert len(read("weights_l1_0.hex")) == 304
    for bank in range(4):
        values = read(f"weights_l4_{bank}.hex")
        assert len(values) == 80
        expected = np.array(model["w1"])[bank::4].ravel().tolist()
        expected += model["w2"][bank] if bank < 3 else [0]*16
        assert values == expected


def test_real_artifact_is_trained_and_frozen():
    root = Path(__file__).resolve().parents[1]
    path = root/"artifacts/model/model.json"
    if not path.exists():
        return  # Offline unit suite remains usable before data acquisition.
    model = json.loads(path.read_text())
    assert model["training_status"] == "trained_on_official_cwru"
    assert len(model["w1"]) == len(model["w1"][0]) == 16
    assert len(model["w2"]) == 3
    assert model["hidden_shift"] >= 0
    assert model["scales"]["weight_granularity"] == "per_layer_power_of_two"
    from vibfpga.dataset import sha256
    frozen = json.loads((root/"artifacts/reports/selection_frozen.json").read_text())
    assert sha256(path.read_bytes()) == frozen["model_sha256"]
    assert frozen["test_waveform_loaded_by_training_before_freeze"] is False
