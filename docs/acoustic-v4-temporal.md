# High-Standard Gates and Temporal-Feature Experiment (2026-09-11)

## Success Criteria: Specify Before Running

The fixed validation set contains 30 anomalous and 40 normal recordings. Validation must simultaneously meet:

- At least **27/30 (90%)** anomalies detected.
- At most **2/40 (5%)** normal false positives.
- **ROC-AUC ≥0.90**.

This is a strict project target, not a guarantee that the existing data and small hardware can attain it. Do not report anomaly detection while omitting false positives, lower gates for presentation, or remove difficult samples.

Only after validation passes may formal frozen confirmation begin: retain all processing, model, and threshold choices, then evaluate the test set once, requiring anomaly detection ≥90%, normal false-positive rate ≤5%, and AUC≥0.90. The test contains 50 anomalies and 40 normals, corresponding to at least 45/50 and at most 2/40. Multiple selection rounds have already used validation; even 27/30 establishes only validation success, not generalization. Sample counts are limited; future field validation is separate.

The iteration's `artifacts/acoustic-v4-temporal/protocol.json` was written before reading training/validation data and fitting parameters. Earlier experiments retain their historical gates; new standards do not retroactively rewrite them.

## Difference from Concatenating Windows

Use 128-sample (8 ms) short windows to produce 16-band energies and a waveform-energy envelope updated at 125 Hz. Analyze contiguous spans of 0.512, 1.024, or 2.048 seconds with fixed 0.512-second stride, never crossing recording boundaries.

- **Modulation features:** analyze changes in each band's energy relative to its own mean, summing modulation energy over 1–8, 8–24, and 24–62.5 Hz. This describes repeated loudness changes, not the pitch of the sound waveform itself.
- **Impact features:** waveform kurtosis, crest factor, envelope coefficient of variation, and envelope autocorrelation at lags of 16/32/64/128 ms, measuring concentrated impacts and repetition patterns.
- **Spectral change:** normalize each frame's spectrum and compute mean absolute and RMS changes of every band between adjacent frames.
- Retain static means as a control; concatenate dynamic and static features and also compare all dynamic-feature combinations.

Three durations×five feature combinations×two models produce 30 predetermined candidates. Models are standardized squared distance and shrinkage-covariance distance, with parameters learned only from normal training data. Recording scores remain means of segment scores. Thresholds use normal validation recordings and are not adjusted using anomaly labels.

The 125 Hz envelope update supports modulation frequencies only up to 62.5 Hz and cannot cover every mechanical impact repetition rate. Short-window energy also smooths changes; do not claim complete professional envelope diagnosis. All segments inherit their recording label without annotated anomaly onset times, so this does not establish identification of specific fault events.

## Results

None of the 30 candidates met the high-standard gates or exceeded the existing static 16-band centroid model's 13/30.

|Approach|AUC|Detected anomalies at 2/40 normal false positives|
|---|---:|---:|
|Existing static 16-band centroid|0.6883|13/30|
|Impact features selected with detection prioritized, 2.048 s, squared distance|0.6450|9/30|
|Spectral change, 2.048 s, covariance distance|0.7408|5/30|

The hypothesis that temporal changes necessarily improve performance was not supported. Some approaches improve overall ranking, but the high-score tail of normal recordings still limits detection under strict false-positive constraints. AUC does not replace detection at the operating threshold. This iteration provides no evidence supporting implementation of these features in RTL.

The 30 temporal candidates also differ from the older approach in short-window front ends, 128 versus 1024 samples. Failure to improve overall cannot be generalized to all temporal algorithms, nor attributed solely to the presence or absence of temporal information.

## Deliverables and Verification

- Source: `src/vibfpga/acoustic_temporal.py`, `scripts/experiment_acoustic_temporal.py`.
- Records: `artifacts/acoustic-v4-temporal/`, including the high-standard protocol, 30 models' parameters, segment/recording scores, selection results, and SHA256 receipts.
- Tests: `tests/test_acoustic_temporal.py` checks numerical stability for silence, feature dimensions, 4 Hz modulation response, impact response, and recording isolation. Three tests passed.
- Existing output directories are not overwritten; the default script can load only training/validation data. Consult saved results for routine review rather than retraining.
- This iteration did not read test data, quantize, modify RTL, or program the board. Original models and hardware evidence remained unchanged.

Further work requires a new testable hypothesis, not continued large searches against the same validation set. Priorities include analyzing noise conditions in false-positive and missed-anomaly recordings or designing paired diagnostics at different SNRs. A changed SNR or machine scope must be reported as a new experiment, not improvement of the original 0 dB task. All added data must be grouped by original recording to prevent leakage of different mixtures across sets.
