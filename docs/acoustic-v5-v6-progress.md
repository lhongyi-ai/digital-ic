# High-standard target: full-spectrum and pretrained-representation progress

The target remains at least 27/30 abnormal detections, at most 2/40 normal false positives, and AUC≥0.90 on the original fixed 0 dB fan/id_00 validation recordings. It has not been met. Threshold rules were unchanged, and the test set remained unopened at this historical stage.

Two new routes were completed, totaling 30 candidates, with all protocols and evidence retained.

## Complete spectra: 24 candidates

The earlier 16 bands might merge useful detail, so this study directly used 1024-, 4096-, and 16384-point spectra with resolutions of 15.625, 3.90625, and 0.9765625 Hz respectively. Each recording's complete power spectrum was averaged first. Normal training recordings fitted standardized distance, five-nearest-neighbor distance, 16-dimensional PCA residuals, and regularized covariance. Absolute log spectra were compared with log-spectral shape after removing overall level.

The best candidate by detection used 1024-point absolute log spectra plus five-nearest-neighbor distance: 6/30 detections, AUC 0.655, and 2/40 normal false positives. It did not exceed the existing 13/30 result. The 16384-point PCA residual reached AUC 0.7083 but detected only 4/30. Complete narrow-resolution spectra alone did not resolve normal/abnormal distribution overlap.

## Externally pretrained audio representations: six candidates

This study used CNN6 from the [official PANNs AudioSet-pretrained networks](https://github.com/qiuqiangkong/audioset_tagging_cnn), with official weights from [Zenodo](https://zenodo.org/records/3987831). The Git commit was pinned, official weight MD5 verified, and weights loaded with weights_only. Parameters were frozen without MIMII fine-tuning. Input was resampled for the official 32 kHz configuration, producing 512-dimensional representations.

Only the 120 normal training recordings fitted squared distance, five-nearest-neighbor distance, and shrinkage covariance, comparing raw and unit-length representations. The best candidate detected only 2/30, with AUC 0.5433 and 2/40 false positives. These AudioSet representations did not transfer useful fault discrimination in this experiment. Output norms were nonzero and variable, ruling out a simple all-zero feature failure. This does not establish that every pretrained audio model is ineffective.

CNN6 is an offline exploratory model, not circuitry that can be placed directly on UPduino. Even if a future teacher model passes, small-model distillation, quantization, and hardware costs require separate verification.

## Evidence and next step

- `artifacts/acoustic-v5-finespectrum/`: 24 candidates, fitted normal-model parameters, all validation scores, and data/source receipts.
- `artifacts/acoustic-v6-panns/`: six candidates, training/validation representations, model parameters, and bindings.
- `third_party/panns/source.json`: official source commit, weight information, and SHA256; MIT licensing is retained. Upstream source/weight copies omitted from publication remain local.
- Entry points: `scripts/experiment_acoustic_finespectrum.py` and `scripts/experiment_acoustic_panns.py`. Both refuse to overwrite existing results, and their data-loading entry point prohibits the test set.

The best existing result remains 13/30 and AUC 0.6883; this iteration did not complete the target. A materially different next route was known-fault recognition using fully separate fault-training recordings. The user subsequently explicitly authorized that route, preserving the original validation/test sets and making the task change explicit. The independent fault-training extension is under `data/mimii-supervised`, with bulk data retained locally; current validation anomalies were not converted into training data. Supervised results must be labeled known-fault recognition rather than normal-only training for unknown-anomaly detection.
