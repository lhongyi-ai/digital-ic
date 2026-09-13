# Cross-Machine Time-Frequency CNN Experiments

Two architecture versions, each with two input representations, completed 12 whole-machine holdout models. The cross-machine target was not met, and 06 was not accessed.

The first version uses 32 bands, global frequency pooling, and a fixed 30 epochs. Training AUC is only about 0.50–0.63, indicating substantial underfitting. The revised version uses 128 bands, preserves frequency position, and trains for a fixed 60 epochs. Both train on fit-role recordings from two source machines and set thresholds from source-normal calibration-role recordings. The held-out machine is used for neither early stopping nor calibration.

Each recording contributes four 32-column time-frequency blocks, with a 64 ms column hop. Each block spans 2.096 seconds of original waveform; adjacent blocks overlap by 48 ms in waveform support, using the first 8.24 seconds in total. The first protocol's wording, “disjoint 2.048s / first8.192s,” described feature columns rather than waveform support and was inaccurate; it is corrected here. All blocks from one recording always remain in the same group, preventing segment leakage across splits.

## Revised-version results

| Representation | Held-out machine | Detected /160 | False positives /160 | AUC |
| --- | --- | ---: | ---: | ---: |
| relative | 00 | 158 | 154 | 0.5469 |
| relative | 02 | 62 | 38 | 0.5727 |
| relative | 04 | 6 | 3 | 0.8090 |
| timecenter | 00 | 3 | 4 | 0.4846 |
| timecenter | 02 | 7 | 6 | 0.5371 |
| timecenter | 04 | 1 | 1 | 0.4825 |

relative retains relative spectra and temporal variation. timecenter additionally subtracts each band's temporal mean, mostly preserving fluctuations. No approach achieves detection >90%, false positives <5%, and AUC ≥0.90 on every machine.

## Verification limitations

The first version's saved metrics recompute correctly, but reloading shows small floating-point differences and AUC changes near score ties; it is not bit-exact. For the revised version, cross-process reload changed the threshold decision on one of 320 recordings in one fold. The strict reload audit therefore failed, and complete validation cannot be claimed. Original logs remain: build/cnn-audit.log, cnn-audit-deterministic.log, cnn-audit-tolerance.log, and cnn-audit-final.log.

The revised-version table contains results saved by the original training process, not stable deployment results. Numerical execution conditions and near-threshold stability need correction or clarification before any deployment. Performance itself already fails the target, and quantization has not started.

This round did not demonstrate that the CNN route works. Subsequent work should first diagnose revised-version training fit and low-confidence scores, then consider architecture/training changes. Repeated inspection of 06 must not be used to seek higher scores. New final-confirmation data remains necessary.

Evidence: [first-version results](../artifacts/acoustic-cnn-v1/results.json), [revised-version results](../artifacts/acoustic-cnn-v2/results.json), [first-version audit](../artifacts/acoustic-cnn-v1/audit.json), and [revised-version audit failure](../artifacts/acoustic-cnn-v2/audit.json).
