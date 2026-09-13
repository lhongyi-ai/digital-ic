# Missed-Anomaly Diagnosis and Improvement Attempts (2026-09-11)

This round added 33 predefined candidates, using only the original normal training and validation sets. None exceeded the existing 16-band centroid method's 13/30 detections. All failed records remain intact. Quantization, RTL, and the board model were unchanged, and the test set was not opened.

## Direct evidence

For the existing candidate, median recording-average scores were 0.01951 among 40 normal recordings, 0.02040 among 17 missed anomalous recordings, and 0.09455 among 13 detected anomalous recordings. Normal and missed anomalies have similar scores here. These are group statistics, not proof that raw sounds or every possible feature are inseparable.

This round did not support the hypothesis that averaging dilutes short anomalies. At the same empirical 5% false-positive rate on normal recordings:

| Aggregation (fixed existing centroid model) | AUC | Detected anomalies |
| --- | ---: | ---: |
| Mean of all window scores | 0.6883 | 13/30 |
| Mean of highest 10% of window scores | 0.6217 | 9/30 |
| Mean of strongest four consecutive windows | 0.5958 | 3/30 |

The median peak/mean score ratio is 5.28 for normal recordings and 4.58 for missed anomalies. Emphasizing high-score peaks also emphasizes normal variation and raises the normal threshold. Anomalous peaks cannot be shown without that cost.

## Actual results of other changes

The first group contains 27 candidates: original log1p features, log-spectral shape with overall spectral level removed, and shape with overall level added back. Each compares centroid distance, shrinkage-covariance distance, and four-center normal modes, using each of the three aggregations above.

- Original log1p with full covariance and recording-wide mean: AUC 0.6658, 4/30.
- Original log1p with four normal centers and recording-wide mean: AUC 0.6767, 6/30.
- The best detection rate from shape features did not exceed the baseline. Removing loudness-related information was not an effective fix for these data.

Score/RMS correlation is about 0.80 across all validation recordings, but about −0.23 among normal recordings alone. This does not establish the causal claim that the model only recognizes loudness: group differences and a few high-score anomalies affect the pooled correlation. Sound intensity may also contain useful anomaly information.

The second group contains six candidates: 32, 64, and 128 complete equal-width bands, each with centroid and shrinkage-covariance methods and fixed recording-wide mean aggregation. Centroid models at all three resolutions detect 11/30, with AUC 0.6800, 0.6458, and 0.6075 respectively; covariance models are lower. Finer bands did not resolve the problem and increase hardware and parameter costs.

## Supported conclusions and remaining hypotheses

Confirmed: current scores do not adequately separate normal recordings from missed anomalies. Changing aggregation, increasing complexity within these models, and subdividing these bands did not improve results. Prior evidence also did not support severe clipping in the old version or INT8 loss as the main bottleneck.

Still hypotheses: 0 dB background noise masks machine differences; current band energies omit periodic modulation/harmonic information; the normal training set does not cover operating variation. These require targeted controls and cannot be established directly from this round.

The earlier improvement from 4/30 to 13/30 changed the frontend, features, and model simultaneously, so it was not a single-factor gain from wider bands. A fairer old centroid baseline is 8/30 versus 13/30 for the new method. In the same round, floating-point sparse log1p centroid features gave 9/30, versus 13/30 with complete bands.

There are only 40 normal validation recordings, so 5% false positives means two recordings. Across 1000 bootstrap resamplings of normal validation scores for threshold selection, detection on the original validation set has 5th/50th/95th percentiles of 40%/43.3%/50%, and false-positive rates have corresponding percentiles of 0%/5%/15%. This illustrates threshold sensitivity; it is **not an independent-test confidence interval**, and model selection was not repeated. Many candidates have used the same validation set, so continued tuning increases overfitting risk.

## Subsequent priorities

1. If work continues on the same data, prioritize an explicit hypothesis about longer-timescale envelope modulation or spectral-change statistics, which differs from simply concatenating adjacent band features. Limit candidates, save a protocol, and evaluate before changing RTL.
2. If necessary, run paired higher-SNR diagnostics. They can help diagnose noise limitations but change experimental conditions. Higher-SNR results cannot stand in for original 0 dB performance, and mixed versions of the same original machine recording must not cross training/validation/test splits.
3. Freeze, quantize, and verify RTL only after a new approach shows sufficiently clear benefit. Keep the fixed test set for final confirmation.

## Reproduction and saved evidence

- `scripts/diagnose_acoustic_v3.py`: reuses hash-bound features and restores window sequences; runs 27 candidates, missed-anomaly diagnosis, and threshold-sensitivity checks.
- `scripts/diagnose_acoustic_resolution.py`: uses fixed training/validation PCM and runs six spectral-resolution candidates.
- `artifacts/acoustic-v3-diagnosis/` and `artifacts/acoustic-v3-resolution/`: protocols, parameters, per-recording/window scores, and SHA256 receipts. Existing output directories cannot be overwritten.
- Added tests verify that temporal-context reconstruction neither omits nor duplicates windows and that short-time aggregation never crosses recording boundaries. Recomputed earlier baseline scores match saved values; the 32-band comparison also reproduces the preceding round.

All results in this round are software validation and add no physical-board detection-performance claims.
