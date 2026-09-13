# Acoustic v2: input and feature experiments (2026-09-11)

Offline comparisons of input quality, full frequency bands, temporal context, distance models, and small autoencoders are complete. **Detection improved but still missed the predefined gates. This iteration did not deploy a new model, modify RTL, or open the test set.** The previous frozen model and board evidence remain unchanged.

## Data and experiment scope

The fixed fan/id_00, 0 dB, channel-0 manifest was reused: 120 normal training recordings and 40 normal plus 30 abnormal validation recordings. Complete recordings were split first, then divided into nonoverlapping 1024-sample, 64 ms windows. No test recordings were read. Each round retained its protocol, parameters, per-recording scores, data hashes, and source hashes.

Two rounds each evaluated 45 candidates: five feature types × 1/4/8-window contexts × three models.

- Features: the sparse baseline of 16 three-neighbor-bin groups, complete 16/32 equal-width bands, and 16/32 triangular Mel filters.
- Round 1 used `log1p(energy)` compression; round 2 used standard logarithms, `ln(max(energy, 1e-12))`. Energy came from normalized PCM, DC removal, a periodic Hann window, and a complete real FFT. The two compression methods are distinct configurations.
- Contexts concatenated windows in time order with one-window stride, always within the same recording.
- Models were Euclidean centroid distance, diagonal Mahalanobis distance, and a single-hidden-layer autoencoder. Means and standard deviations used normal training data only. AE epoch selection used normal validation reconstruction error; abnormal validation labels were used only for candidate comparison.
- Each recording's score was the mean of its window scores. Normal validation scores set a threshold whose strictly-greater-than empirical false-positive rate was at most 5%. Candidates were ranked first by detection at that false-positive rate, then by AUC and cost.

All 90 candidates used the same small validation set, so selection is optimistically biased and does not establish independent test performance. With only 30 abnormal recordings, one extra detection changes the rate by 3.33 percentage points.

## Input checks

| Group | Fraction of samples clipped by 12-bit limiting | Maximum absolute value after DC removal | Median recording RMS |
|---|---:|---:|---:|
| Normal training | 0 | 2019 | 213.52 |
| Normal validation | 0 | 1350 | 214.23 |
| Abnormal validation | 0.000209% | 2968 | 205.10 |

Only one abnormal validation recording had a small amount of clipping. The minimum safe right shift selected from training remained 0; there is no evidence that severe clipping is the main bottleneck. This checks the v1 input limiter after per-window DC removal and is not equivalent to original ADC clipping.

The sparse features cover 48 of 512 non-DC bins, or 9.375%. They capture approximately 28.8%, 32.1%, and 41.9% of total spectral energy in normal training, normal validation, and abnormal validation, respectively. **Missing energy is not the same as missing fault information.** The band experiments only show that broader features offer some benefit on this validation task.

[Spectrum and feature comparison](../artifacts/acoustic-v2-analysis/feature-comparison.png)

## Main results

All results below are recording-level results at a 5% normal-validation false-positive rate.

| Method | AUC | Abnormal recordings detected |
|---|---:|---:|
| Previous integer AE, sparse bins | 0.6533 | 4/30 (13.3%) |
| Previous centroid baseline | 0.6383 | 8/30 (26.7%) |
| New sparse bins + log1p + centroid, one window | 0.4733 | 9/30 (30.0%) |
| Complete 16 bands + log1p + centroid, one window | 0.6883 | 13/30 (43.3%) |
| Complete 32 bands + log1p + centroid, one window | 0.6800 | 11/30 (36.7%) |
| Mel 16 + log1p + centroid, one window | 0.6775 | 13/30 (43.3%) |
| Best standard-log candidate: 16 equal-width bands + four-window AE | 0.6533 | 8/30 (26.7%) |

Old and new approaches change floating-point preprocessing, compression, and model processing together; the complete difference cannot be attributed to band coverage. Within round 1, sparse and complete features share floating-point processing, providing a more direct coverage comparison.

**The engineering candidate retained complete 16 bands, one window, and centroid distance.** Raw ranking selected an eight-window version because of an approximately 1e-16 floating-point AUC difference. The analysis treats differences within 1e-12 as ties and selects the smaller single-window version. Both detect 13 recordings and have identical AUC at reported precision.

Concatenating context for centroid distance and then averaging over a recording largely reweights the same windows, and may add little temporal discrimination. Although a small AE can mix time positions, it also showed no stable benefit here. This does not establish that all temporal models are ineffective. Standard logarithms/Mel did not improve this round; network size was not increased without evidence.

## Consecutive alarms are a separate acceptance criterion

The one-window centroid candidate uses the 99th percentile of normal validation window scores as its threshold, requiring three consecutive exceedances:

- Normal recordings with at least one alarm: 3/40, **7.5%** false positives.
- Abnormal recordings with at least one alarm: 8/30, **26.7%** detection.
- One-window context plus three consecutive windows gives an earliest decision time of 192 ms, plus computation and transport.

This is a different decision rule from the recording-mean 5% / 43.3% result and must not be mixed with it. The eight-window candidate's recording-level consecutive-alarm false-positive rate reached 15%, providing no clear benefit to justify greater context latency.

## Hardware decision

The quality gates remained validation AUC ≥0.8, detection ≥50%, and recording-level false positives ≤5%. This round failed. Quantization, FFT RTL, and reprogramming therefore did not proceed; existing hardware continued to run the previous algorithm.

Cost estimates support candidate selection only; they are not synthesis or measurement results:

- A 16-dimensional centroid distance requires 16 square multiplications per feature frame. Sixteen float32 mean parameters occupy 64 bytes. Compression, spectrum, thresholds, and other overhead are additional.
- Naively expanding the old 48-bin DFT to 512 bins gives an estimated one-MAC DFT time of approximately 262.3 ms under the original linear schedule. Ideal four-way division is still approximately 65.6 ms, exceeding the 64 ms window interval before other stages.
- A 1024-point complex radix-2 FFT contains 5120 butterflies, or an estimated 20480 real multiplications at four generic real multiplications per butterfly. This ignores memory, control, scaling, and special-twiddle optimizations, and cannot be presented as implemented latency or resource usage.
- If future algorithms meet the gates, evaluate an FFT rather than directly enlarging the sparse DFT. Complete resource use, fixed-point error, and timing remain unverified.

## Reproducible evidence and validation

- `artifacts/acoustic-v2-study/`: round-1 protocol, input audit, parameters for 45 candidates, scores, and hash receipts.
- `artifacts/acoustic-v2-logpower/`: the standard-log comparison over the same scope in round 2.
- `artifacts/acoustic-v2-analysis/comparison.csv`: classification, alarm, storage, and computation comparisons for 90 candidates.
- `artifacts/acoustic-v2-analysis/summary.json`: engineering candidate, tie rule, and hardware estimates.
- `tests/test_acoustic_experiment.py`: band coverage, omitted-bin examples, context order/boundaries, alarms, empirical thresholds, and refusal to read test data.
- Full Python regression: 243 passed, recorded in `build/acoustic-v2-python.log`. No RTL changed in this round, so old RTL/board regressions were not repeated. Omitted build evidence and bulk data remain local.

For reproduction, load `scripts/env.sh` from the project root. Run `scripts/experiment_acoustic_v2.py --output <new-directory>` or `scripts/experiment_acoustic_logpower.py --output <new-directory>`; existing output directories are rejected. `scripts/report_acoustic_v2.py` compares the two default rounds and also refuses to overwrite its analysis directory. Routine review should use existing reports without retraining.

The next proposed step was to examine missed recordings in the fixed validation set, investigate whether anomalies occur in short segments, and compare score means, upper quantiles, and short-duration event statistics. Any such study requires a separately saved, predefined protocol and retention of current failed results. At this historical stage, the test set remained unopened and the candidate was not presented as a reliable fault detector.
