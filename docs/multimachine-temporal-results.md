# Temporal features: cross-machine development results

This iteration completed eight approaches and 24 training folds, but still missed detection >90%, false positives <5%, and AUC≥0.90. It did not reopen 06 or train a final deployment model.

## Features and grouping

Each ten-second recording independently uses 1024-point short-time spectra with 256-sample hop, splitting non-DC frequencies into 32 equal-width bands. Band energies provide relative fluctuation, kurtosis, 99th-percentile peaks, frame-to-frame change, correlations at 0.5/1/2-second lags, and modulation-energy fractions in 0.5–2/2–8/8–20 Hz bands. Temporal descriptors have 320 dimensions, or 352 when combined with a 32-dimensional mean spectral shape.

Features never cross recording boundaries. Modulation analysis summarizes a complete ten-second recording and is not an implemented 0.5–2-second low-latency online detector. Frequencies 0.5–2 Hz correspond to approximately 0.5–2-second periods, while lag correlation measures similarity at a specified time separation.

Only the 960 development recordings from 00/02/04 were used, retaining original fit/calibration roles and rotating whole-machine holdout. Each fold fits 512 recordings, calibrates on 128, and validates on 320. Thresholds come only from normal calibration recordings of source machines.

## Selected baseline results

The predefined rule prioritizes reducing the worst machine's gate violations. “Selected” therefore does not mean adequate performance or improvement in every metric over the old model.

| Held-out machine | Faults detected | Normal false positives | AUC |
|---|---:|---:|---:|
| 00 | 35/160 | 18/160 | 0.5705 |
| 02 | 21/160 | 22/160 | 0.5024 |
| 04 | 21/160 | 7/160 | 0.6938 |

Selected approach: temporal-linear_1. None of the eight candidates passed every gate. Across all candidates, 02 AUC was approximately 0.50–0.54, indicating that these temporal descriptors still lack stable cross-machine normal/fault ranking. Threshold changes cannot solve this.

## Validation and next steps

A synthetic signal with known 1 Hz modulation checked modulation-band localization, lag correlation, and gain invariance, along with silence and length boundaries. An independent audit reloaded all 24 models and checked grouping, normalization means, source-machine thresholds, predictions, and independently computed AUC/confusion counts. Synthetic inputs validated code only and were not presented as real training data.

The next proposed step was diagnosis: can the same features distinguish faults within one machine, and does cross-machine failure coincide with score/feature distribution shifts? This is development-set diagnosis, not cross-machine acceptance. If within-machine discrimination also fails, investigate models that retain finer time-frequency structure. New final conclusions still require independent data excluded from development and a review of source relationships.

Evidence: [all candidates](../artifacts/acoustic-multimachine-temporal-v1/results.json), [protocol](../artifacts/acoustic-multimachine-temporal-v1/protocol.json), and [independent audit](../artifacts/acoustic-multimachine-temporal-v1/audit.json).
