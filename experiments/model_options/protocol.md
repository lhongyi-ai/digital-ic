# Fixed training/validation comparison

This protocol is written before the nine training runs. Its purpose is to assess
validation performance and sensitivity to initialization, without changing any
existing model, report, ROM, or RTL. All outputs stay in this experiment directory.
No test waveform or test prediction file is read. The existing test split is not
an independent unseen benchmark for future model selection.

## Fixed data and preprocessing

- Official CWRU 12 kHz drive-end fault records: loads 0/1 HP for training, 2 HP for
  validation. Record split precedes nonoverlapping N=1024 windows. No normal class.
- Read the already frozen `artifacts/model_neighbor/model.json`. Keep its global
  train-derived PCM gain, selected 16 centers, 48 center-major neighboring DFT bins,
  integer DSP arithmetic, and 16 train-derived feature shifts exactly unchanged.
- Sum k-1/k/k+1 powers after each bin's contracted Re/Im rounding and saturation.
  Float inputs are clip(power / 2**feature_shift, 0, 127) / 128. Integer inputs
  apply the existing RNE and clamp to 0..127. Do not fit new frontend scales.
- Every accessed MAT is SHA256 checked against the existing audit manifest. Save
  train/validation metadata and file hashes, source copies, frozen model copy,
  environment versions, and new checkpoints in this experiment directory.

## Exactly nine runs

| Configuration | Hidden units | AdamW learning rate | Weight decay | Seeds |
|---|---:|---:|---:|---|
| A | 16 | 0.025 | 0.00001 | 7, 17, 29 |
| B | 16 | 0.01 | 0.001 | 7, 17, 29 |
| C | 32 | 0.01 | 0.001 | 7, 17, 29 |

Every run uses full-batch weighted cross entropy, with class weights
N_train/(3*N_class), one ReLU hidden layer, CPU float32, exactly 450 epochs, and
the same AdamW defaults. Set the seed immediately before network creation.
Evaluate validation every 10 epochs; choose maximum validation macro F1, breaking
ties by lower full-batch training loss. No early stopping, schedules, or search
extensions. All best checkpoints and the full 45-point selection histories are
saved; reporting is over all three seeds, never only the best seed.

For A and B, apply the existing `make_integer_model` PTQ method to each selected
checkpoint and training input, then evaluate INT8 on validation. New NN weight
and activation scales follow the same train-only PTQ rule; frozen frontend
scales remain unchanged. Save these integer candidates only in this experiment,
without ROM export or deployment. C is FP32 only: quantization and compatible
32-hidden RTL are not implemented or evaluated here.

## Reporting and interpretation

Report each seed's selected epoch and validation float/INT8 metrics, plus macro-F1
mean, sample standard deviation (ddof=1), minimum and maximum for each applicable
configuration. Report quantization accuracy loss and macro-F1 differences. Check
A/seed7 against the frozen candidate's existing validation metrics as a numerical
reproduction check; do not change code or settings to obtain a desired score.

A versus B changes both learning rate and weight decay. A versus C is not a pure
width comparison. B versus C holds these optimizer settings fixed and changes
width, but three seeds and repeatedly used validation data do not establish
out-of-distribution or deployment improvement. No score from this experiment is
a new test accuracy or a physical-hardware result. Do not run train-record folds,
read the test split, extend the search, or retrain the deployed model afterward.
