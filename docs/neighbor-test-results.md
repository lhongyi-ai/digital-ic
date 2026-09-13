# Neighbor-Bin Energy Model: Post-Freeze Test Results

Model parameters, bins, scales, and RTL were already complete. This work only evaluates the frozen candidate, without retraining. Results below use 3 HP records from the same CWRU test rig. These records were previously used to test the old model; they are not a new external test set, physical-board accuracy, or field accuracy.

| Version | Correct / total windows | Accuracy | Macro-F1 |
| --- | ---: | ---: | ---: |
| Floating-point network | 994 / 1070 | 92.90% | 0.92964 |
| INT8 deployment parameters | 997 / 1070 | 93.18% | 0.93236 |

This public-data experiment meets the macro-F1 ≥0.90 target. Weights retain the previously exported candidate version and were not changed in response to these test results. The model still contains only three labeled defect classes and no normal class.

## Per-class results

| Class | Windows | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: |
| Inner race | 357 | 87.21% | 95.52% | 91.18% |
| Outer race | 357 | 99.70% | 93.56% | 96.53% |
| Ball | 356 | 93.60% | 90.45% | 92.00% |

Confusion-matrix rows are true classes and columns are predictions:

| True / predicted | Inner race | Outer race | Ball |
| --- | ---: | ---: | ---: |
| Inner race | 341 | 1 | 15 |
| Outer race | 16 | 334 | 7 |
| Ball | 34 | 0 | 322 |

The largest directional confusion is 34 ball-fault windows classified as inner-race faults. Outer-race precision exceeds recall: windows predicted as outer-race faults are usually correct, but some actual outer-race windows are missed.

## Checks by original record

| MAT record | Class | Defect size, inch | Correct / windows | INT8 accuracy |
| --- | --- | --- | ---: | ---: |
| 108 | Inner race | 0.007 | 120 / 120 | 100.00% |
| 121 | Ball | 0.007 | 118 / 118 | 100.00% |
| 133 | Outer race | 0.007 | 119 / 119 | 100.00% |
| 172 | Inner race | 0.014 | 102 / 118 | 86.44% |
| 188 | Ball | 0.014 | 108 / 119 | 90.76% |
| 200 | Outer race | 0.014 | 99 / 119 | 83.19% |
| 212 | Inner race | 0.021 | 119 / 119 | 100.00% |
| 225 | Ball | 0.021 | 96 / 119 | 80.67% |
| 237 | Outer race | 0.021 | 116 / 119 | 97.48% |

Errors are uneven: 225.mat (0.021-inch ball fault) reaches 80.67%, and 200.mat (0.014-inch outer-race fault) reaches 83.19%. The pooled 93.18% does not establish equal performance for each class, defect size, or machine. This describes the error distribution without retuning the model from it.

## Quantization and numerical consistency

Floating-point and INT8 classes differ on 13 windows: five change from correct to incorrect, eight from incorrect to correct, for a net gain of three correct windows and about 0.28 percentage points of accuracy. This difference includes input rounding, weight/bias quantization, and hidden-layer rounding/saturation, not weight quantization alone. The floating-point network still uses power features from the same integer DSP; this is not a comparison between complete floating-point and complete fixed-point DSP pipelines.

All 1070 windows were checked for agreement between the per-window reference and batched implementation across 48 DFT powers, 16 energies/features, hidden layer, logits, and class. This is a Python software numerical check. The [core verification matrix](core-verification.md) covers the 1000-frame RTL and noninteger-bin/phase/clipping tests.

## Freeze and verification

- Model SHA256: `12abcdfd4a9072903915135e771c1fb9be0d430275e28acbf545660e1d7fa117`.
- Freeze time: `2026-09-06T03:22:07.878604+00:00`; first test-waveform access in this evaluation: `2026-09-06T03:22:07.901365+00:00`.
- Floating-point checkpoint and exported NPZ match parameter by parameter; INT8 parameters match frozen floating-point scales. The original model, ROMs, old test reports, and evaluation source are bound by SHA256.
- New outputs are saved separately as [evaluation.json](../artifacts/reports/neighbor_test/evaluation.json), [per-window CSV](../artifacts/reports/neighbor_test/predictions.csv), and [per-record JSON](../artifacts/reports/neighbor_test/records.json), with completion.json written last. Historical test_evaluated=false in model JSON was not rewritten.

```sh
source scripts/env.sh
python scripts/evaluate_neighbor.py --verify
```

This command checks existing outputs, input hashes, and saved predictions only. It does not read raw MAT files, rerun inference, or train. The actual evaluation command refuses to overwrite an existing directory.

At this stage, the next hardware acceptance task is to confirm UPduino revision, clock, and Flash, then program matching four-MAC neighbor-bin firmware and inspect real replay logs. Separate acquisition/static-calibration/noise experiments follow after ADXL345 arrives. All physical-board statuses at the time of this report remain unmeasured.
