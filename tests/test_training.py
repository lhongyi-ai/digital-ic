import numpy as np
import pytest
import torch
from vibfpga.fixed import infer
from vibfpga.training import MLP, make_integer_model, predict_integer, run_training


def test_quantized_linear_algebra_matches_scalar_inference():
    torch.manual_seed(12)
    model = MLP()
    rng = np.random.default_rng(5)
    x = rng.integers(0,128,(50,16),dtype=np.int64)
    quant = make_integer_model(model,x/128.0,{"n":1024})
    pred,logits,hidden = predict_integer(quant,x)
    for i,row in enumerate(x):
        reference = infer(row,quant)
        np.testing.assert_array_equal(logits[i],reference["logits"])
        np.testing.assert_array_equal(hidden[i],reference["hidden"])
        assert pred[i] == reference["class_id"]


def test_test_set_cannot_be_silently_reused(tmp_path):
    reports = tmp_path/"reports"
    reports.mkdir()
    (reports/"test_evaluation.json").write_text("{}")
    with pytest.raises(RuntimeError,match="held-out test report"):
        run_training(tmp_path/"missing_data",tmp_path)
