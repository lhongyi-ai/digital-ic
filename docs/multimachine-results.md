# Three-machine training and held-out-machine test results

Training, independent development auditing, model freezing, and one test on 06 are complete. **Cross-machine recognition did not meet the gates.** These are software-model results, without quantization or UPduino deployment.

## Experiment scope

- 0 dB MIMII fans: 320 recordings each from 00, 02, and 04, totaling 960 development recordings; 768 for fitting and 192 for separate threshold calibration.
- Twelve candidates each underwent three whole-machine-held-out folds, totaling 36 development fits. Three complete-spectrum representations were compared with linear, RBF, and ExtraTrees models.
- The original 90 id_00 test recordings were excluded; id_02 explicitly became development data. The 80 normal plus 80 faulty recordings from 06 were read for evaluation only after the final freeze.
- Selected model `shape-linear_1`: a 1024-point spectrum, 512 non-DC log-power features, subtraction of each recording's overall spectral level, then standardization and logistic regression. Final threshold: 1.338819727090399.
- The selected model is the baseline chosen under a predefined rule. **None of the 12 candidates passed the high-standard gates in all three folds.**

## Per-machine results

| Held-out machine | Role | Faults detected | Normal false positives | AUC |
|---|---|---:|---:|---:|
| 00 | Development validation | 153/160 (95.6%) | 153/160 (95.6%) | 0.5979 |
| 02 | Development validation | 149/160 (93.1%) | 152/160 (95.0%) | 0.5410 |
| 04 | Development validation | 65/160 (40.6%) | 2/160 (1.3%) | 0.8336 |
| 06 | Final test after freezing | 64/80 (80.0%) | 60/80 (75.0%) | 0.6388 |

Each fold independently trained and calibrated on two source machines; differing development thresholds were therefore part of the predefined procedure. The 06 test used the fixed threshold obtained after training on all three source machines, without using 06 to set it. Its confusion matrix was `[[20,60],[16,64]]`, with rows true normal/fault and columns predicted normal/fault.

The high-standard gates were detection ≥90%, false positives ≤5%, and AUC≥0.90 for each machine. For 06, that means at least 72/80 detected and at most 4/80 false positives. The actual results failed.

## Interpretation and limitations

High detection does not compensate for high false positives. The 00 and 02 folds alarmed on almost all normal and faulty recordings alike. Machine 04 had fewer false positives but substantial missed faults. The low 06 AUC shows that a single alarm threshold is not the only issue: current scores also rank normal and abnormal recordings poorly on that machine.

These results support the conclusion that the current representations and models lack stable cross-machine generalization. Machine sound characteristics, operating conditions, and fault differences may shift distributions, but this experiment cannot separate their causal contributions. Added data underwent integrity and exact-duplicate checks, without exhaustive near-duplicate or acquisition-batch independence auditing. Four machines also cannot support a claim of general industrial-fan recognition.

This iteration added no new 0.5–2-second periodicity/impact features; inputs remained recording-average spectra, so the results do not rule out temporal features. A later study could investigate them using only 00/02/04 development data, or first narrow the task to independent recordings from known machines. **06 has been evaluated and cannot select models or tune thresholds again. New approaches need another confirmation set excluded from development.** The failed current model does not proceed to RTL deployment.

## Reviewable evidence

- [Training and data protocol](multimachine-training.md)
- [All development candidates](../artifacts/acoustic-multimachine-v1/development.json)
- [Independent development audit](../artifacts/acoustic-multimachine-v1/development-audit.json)
- [Final freeze manifest](../artifacts/acoustic-multimachine-v1/frozen.json)
- [06 per-recording predictions and metrics](../artifacts/acoustic-multimachine-v1/test.json)
- [Completion audit](../artifacts/acoustic-multimachine-v1/completion-audit.json)

Training entry point: `scripts/train_multimachine.py`; audit: `scripts/audit_multimachine.py`; one-time test: `scripts/test_multimachine.py`. Existing output directories and test-attempt markers must not be overwritten for reruns. Reproduction requires an independent copy while retaining original frozen evidence. Bulk training recordings and omitted model binaries remain local.
