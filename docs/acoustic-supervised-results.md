# Known Fan Fault Recognition: High-Standard Gates Met

**This work completed software-model validation and reserved testing, not FPGA deployment of the new model.** The user explicitly authorized independent fault-training recordings, changing the task from “learn unknown anomalies using normal sound only” to “supervised recognition of known faults.” Data remain original MIMII fan/id_00, 0 dB, channel 0; original validation/test recordings were not replaced.

## Frozen Results

|Model and data|Anomalies detected|Normal false positives|AUC|High-standard gates|
|---|---:|---:|---:|---|
|Main model, original validation set|**30/30 (100%)**|**2/40 (5%)**|**1.000**|Pass|
|Main model, reserved test set|**50/50 (100%)**|**1/40 (2.5%)**|**1.000**|Pass|
|Linear candidate, original validation set|29/30 (96.7%)|2/40 (5%)|0.995|Pass|
|Linear candidate, reserved test set|50/50 (100%)|**5/40 (12.5%)**|0.999|**Fail**|

Criteria were fixed before the experiment: at least 27/30 anomalies detected, at most 2/40 normal false positives, and AUC at least 0.90 on the original validation set. The test uses the same rate requirements. Both main and linear models use thresholds frozen during their validation stage, without adjustment based on test results.

Main model: **1024-point complete mean power spectrum → 512-dimensional log power → standardization → ExtraTrees classifier**. It uses 300 trees, minimum leaf size 2, and 0.5 feature fraction per split; tree depth was selected using internal training-set cross-validation. Five-fold training CV AUC is approximately 0.9976; validation selected it as the main model. The linear model was fixed as a hardware-friendly control before opening the test set and cannot be retuned based on test results.

## Why the Improvement Was Substantial

Earlier 16 broad bands merged spectral detail. A normal-only detector knew where a recording differed from normal, but not which differences were actually associated with faults. This experiment retained the complete spectrum and added independent fault examples so the classifier could learn discriminative frequency differences.

Controls support this interpretation but do not prove absolute causality:

- Supervised 32-dimensional band mean/standard-deviation features remained weak, detecting at most 13/30.
- With supervised 512-dimensional complete spectra, the linear model detected 29/30 and the tree model 30/30.
- The preceding model also used the complete spectrum but fitted only normal-recording distributions and did not meet the high-standard gates.

Thus the gain is not simply from increasing model size. Both fault supervision and retained spectral detail matter. The old 13/30 and new 30/30 use identical validation recordings, but the learning task changed; do not advertise the difference as a pure improvement to normal-only anomaly detection.

## Data Separation and Audit

Training consists of the original 120 normal recordings plus 120 added fault recordings. New recordings were selected in predetermined hash order, excluding all 280 recordings in the original manifest. Validation scores did not select training recordings. Added data come from the same official ZIP, with member CRC, original-WAV digest, and local-PCM digest verified.

Hyperparameters were selected by five-fold CV within the training set, with standardization fitted inside each training fold. The model was then fitted on all 240 training recordings. The original 40 normal+30 fault validation recordings were used only for candidate comparison and normal-threshold calibration. Only after selecting the main model and linear control and freezing processing/thresholds were the reserved 40 normal+50 fault test recordings opened once.

`scripts/audit_acoustic_supervised.py` independently reloads the main model and recomputes validation predictions, calculates AUC by pairwise score ranking, and checks training/validation/test filename separation plus all input digests. `goal-audit.json` confirms all three requirements are true. The reserved-test program independently recomputes AUC as well.

The first training attempt stopped because floating-point addition order during parallel tree inference caused reloaded scores to differ bitwise. The failed directory and log were retained. The second attempt fixed inference to one worker, retained strict equality checking, and passed. Failure records were neither deleted nor rewritten.

## Saved Locations

- Extended manifest and fault-training data: `data/mimii-supervised/`.
- Complete passing experiment: `artifacts/acoustic-v7-supervised-r2/`.
- `validation.json`: nine predetermined candidates and original validation-recording scores.
- `goal-audit.json`: independent validation-metric audit.
- `frozen.json`: main model, linear control, thresholds, and source bindings.
- `test-attempt.json`, `test.json`: one-time reserved-test record and per-recording predictions.
- `goal-completion-audit.json`: final requirement checks and result-digest bindings.
- Failed attempt: `artifacts/acoustic-v7-supervised/` and `build/acoustic-v7-supervised.log`.

Omitted raw recordings and build logs remain local. These results cover only a recording-level split within one machine ID and SNR. They cannot be extrapolated to 100% detection in factories or performance on unseen machines. Test AUC=1 does not mean zero false positives: one normal recording still exceeds the fixed threshold.

## Relationship to UPduino

At this experiment's stage, the board still ran the older acoustic prototype. The new tree model had not been quantized, synthesized, deployed, or verified on hardware. A mean spectrum over a complete recording also differs from the existing 64 ms real-time classification flow.

The next engineering task should study an FPGA-suitable deployment form from these frozen results, such as a tree-inference controller or small-model compression using independent development data. The linear candidate fails the test false-positive gate and cannot be deployed while claiming the main model's results. This test set has now served formal evaluation; later tuning must not turn it into validation data, and a new approach requires new independent confirmation data.
