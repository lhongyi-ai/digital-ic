# Current project status

Generated: 2026-09-13T09:32:23.580686+00:00

Project directory: `.`。

This page checks saved evidence and current hashes only. It does not start hardware, builds, training, or model inference.

Saved physical replay passes bound to the current source: **5**; representing **5** actual replays and **2015** deduplicated frames. Retained failed attempts: **3**. Read-only recovery belongs to the original replay and does not add an independent trial.

## Configurations and models

| Profile | N / Hz / MAC | Model and recorded digest match | Status |
| --- | --- | --- | --- |
| cwru-neighbor3 | 1024 / 12000 / 4 | True | trained_on_official_cwru_train_validation_only_candidate |
| sen1-spectrum | 256 / 800 / 1 | True | not_a_classifier_DSP_coefficient_profile |
| fcl1-fixture | 256 / 800 / 1 | True | synthetic_fixture_not_for_deployment |

## Current primary evaluation target: new recordings from covered fans

Frozen split: 1744 recordings; manifest hash valid: True. Early comparisons used logistic regression and a 32-to-16-to-1 MLP; see the integer pipeline selected later below. Every fan and the pooled set require recall>90%, FPR<5%, and AUC>=0.9.
All four IDs participate in training. Three folds are stratified by complete recordings, excluding the old final test. The frozen version completed one final evaluation; results appear below。Hardware testing of the new version has started, with 22 saved passing runs; see the independent audit below。
Protocol: docs/known-machine-evaluation.md. Historical cross-machine experiments remain supplementary and are not the main acceptance criterion for this version.

Development-data receipts: 1024/1024; complete development manifest present: True. Receipt counts do not prove that a process is running.

Six fits of the two early candidates are complete; candidate meeting every gate: None. This earlier comparison failed; see experiment audit.json for 40 recomputed checks.

Three MLP fits for balanced-frequency ablation are complete; evidence binding valid: True. All-machine pass status for four comparisons: {'baseline': {'common': False, 'per_machine': False}, 'balanced': {'common': False, 'per_machine': False}}。
This round compares development data only and includes no RTL or programming. Report: docs/known-machine-balanced-ablation.md.

Follow-up optimization for known machines includes machine-specific parameters, individual frequency retention, full spectra, and linear compression comparisons. Machine 00 has 256 additional training recordings.
Per-machine gates and final-test isolation remain in effect. Further evidence, calibration expansion, and outstanding work are in docs/known-machine-optimization-progress.md. Pooled success does not imply that every machine passes.

Full integer DSP plus INT8 linear classifier passes development gates: True; evidence binding valid: True。
The frozen version completed one final evaluation; results appear below. Development success does not replace final confirmation. Integer interface contract: docs/known-integer-deployment.md.

Final refitted parameters for four machines are exported; frozen-model binding valid: True. This confirms parameter freezing only, not final testing or hardware completion.
New RTL, the full Flash application, and verification results follow. Only evidence bound to the current source is listed; earlier attempts and failures remain in JSON and build directories.

| Evidence | Scope |
|---|---|
| build/known-core/compact-l1-final/report.json | Simulation: 1 MAC，6 windows, fixture=True |
| build/known-core/compact-l4-final/report.json | Simulation: 4 MAC，6 windows, fixture=True |
| build/known-native/l1-1092-backpressure-r2/report.json | Simulation: 1 MAC，1092 windows, fixture=see report |
| build/known-native/l4-1092-fixed16k-r2/report.json | Simulation: 4 MAC，1092 windows, fixture=see report |
| build/known-flash/full-id00-l1-r1/report.json | Simulation: 1 MAC，156 windows, fixture=False |
| build/known-flash/full-id00-l4-r1/report.json | Simulation: 4 MAC，156 windows, fixture=False |
| build/known-flash/full-id02-l4-r1/report.json | Simulation: 4 MAC，156 windows, fixture=False |
| build/known-flash/full-id04-l4-r1/report.json | Simulation: 4 MAC，156 windows, fixture=False |
| build/known-flash/full-id06-l4-r1/report.json | Simulation: 4 MAC，156 windows, fixture=False |
| build/known-flash/small-r4/report.json | Simulation: ? MAC，4 windows, fixture=True |
| build/known-board/l1-id00-dff-r1/report.json | Full-board build, ID00，1 MAC，LC 4682/5280; final Fmax {'clk': {'achieved': 13.898927688598633, 'constraint': 13.20009994506836}} |
| build/known-board/l4-id00-r8/report.json | Full-board build, ID00，4 MAC，LC 5178/5280; final Fmax {'clk': {'achieved': 13.313806533813477, 'constraint': 13.20009994506836}} |
| build/known-board/l4-id02-dff-r1/report.json | Full-board build, ID02，4 MAC，LC 5181/5280; final Fmax {'clk': {'achieved': 14.169925689697266, 'constraint': 13.20009994506836}} |
| build/known-board/l4-id04-dff-r1/report.json | Full-board build, ID04，4 MAC，LC 5179/5280; final Fmax {'clk': {'achieved': 13.886573791503906, 'constraint': 13.20009994506836}} |
| build/known-board/l4-id06-dff-r1/report.json | Full-board build, ID06，4 MAC，LC 5180/5280; final Fmax {'clk': {'achieved': 14.241971969604492, 'constraint': 13.20009994506836}} |

The frozen version completed one final evaluation; results appear below。Hardware testing of the new version has started, with 22 saved passing runs; see the independent audit below. Overfitting diagnostics: docs/known-overfitting-audit.md.

Final holdout download receipts: 720/720; status: final_evaluation_finished。

|Final test machine|Detected|False alarms|AUC|Passed|
|---|---|---|---|---|
|00|77/80|3/100|0.99250|True|
|02|80/80|1/100|1.00000|True|
|04|80/80|1/100|1.00000|True|
|06|80/80|3/100|0.99975|True|
|pooled|317/320|8/400|0.99841|True|

All quality gates passed: True; independent score-audit binding valid: True。

New-model hardware audit: passed=True; current binding valid=True；22 actual passing replays across 13 distinct recordings.
Single-MAC total: 1248 windows; four-MAC total: 2184 windows; four-MAC machine coverage: ['00', '02', '04', '06']. Each startup processes 156 consecutive windows; totals across startups are not one continuous run.
Intentional overload and recovery with the same core: True. Details: docs/known-hardware-results.md.


Local compatibility link: `.`; points to the project: True. The migration record is retained locally and omitted from publication.

## Board and field workflow

Saved USB/JEDEC identification: UPduino v3.1 / EF4016; full original Flash backup hash verified: True. The current connection was not reread during this status check.

Internal HFOSC uses nominal frequency; physical frequency, external-clock calibration, and power are unmeasured. ADXL345 acquisition and a real field-trained model remain incomplete.

Synthetic field fixture: passed; real field training complete: False。

## Physical attempts (all retained)

| Attempt | Saved status | Evidence currently valid | Notes |
| --- | --- | --- | --- |
| l1-1000 | passed | True | provenance_validated_saved_physical_replay；two consecutive identical unaltered saved reads |
| l1-overload | failed | False | normal replay accepted_samples mismatch: observed 3074, expected 4096 |
| l1-post-overload-5 | passed | True | provenance_validated_saved_physical_replay；two consecutive identical unaltered saved reads |
| l4-1000 | failed | False | result log is absent, uncommitted, or has the wrong version |
| l4-1000-readback-recovery | passed | True | provenance_validated_readback_recovery_of_same_physical_trial; read-only recovery of the original replay, with no new run；two consecutive identical unaltered saved reads |
| l4-5 | failed | False | result log is absent, uncommitted, or has the wrong version |
| l4-5-preview | dry_run | False | failed, dry or incomplete attempt; no current passing claim |
| l4-5-wake | passed | True | provenance_validated_saved_physical_replay；legacy single saved read; no two-read consensus receipt |
| l4-final-5 | passed | True | provenance_validated_saved_physical_replay；two consecutive identical unaltered saved reads |

Passing score claims come from saved integer-reference comparison receipts. This check verifies their binding to the same model, input, and output-log hashes and normal counters; it does not rerun inference.

## Replay firmware builds

This table checks upduino_replay only. Other SEN1/FCL1 reports are listed separately under other_build_reports in the JSON and are not evaluated using the replay-firmware input rules.

| Build | MAC | Inputs and bitstream still match | Routed Fmax (MHz) | LC / DSP / RAM |
| --- | --- | --- | --- | --- |
| l1 | 1 | False | system_clk: 20.79953384399414 | 4274 / 1 / 19 |
| l1-wake | 1 | True | system_clk: 21.934154510498047 | 4335 / 1 / 19 |
| l4-v2 | 4 | False | system_clk: 18.631689071655273 | 5070 / 4 / 25 |
| l4-v3 | 4 | False | system_clk: 18.631689071655273 | 5070 / 4 / 25 |
| l4-wake | 4 | True | system_clk: 19.506486892700195 | 5149 / 4 / 25 |

Routed Fmax is a tool estimate, not a measured board clock. Invalidity reasons, file digests, stage cycles, and local compatibility-link status are in current-status.json in the same directory.

Refresh using `python scripts/collect_current_status.py`. Original evidence and failure records are not modified.

## MIMII acoustic prototype (separate from the CWRU results above)

Frozen-model binding valid: True. Validation AUC: 0.6533; false-positive rate: 5.0%; recall: 13.3%. Algorithm feasibility gates passed: False。
Test set evaluated: False; microphone measured: False. The test set remained reserved for a later formal version at this stage.

| Acoustic hardware attempt | Status | Evidence currently valid |
| --- | --- | --- |
| l1-1000 | passed | True |
| l1-5 | passed | True |
| l1-preview | dry_run | False |

Software/RTL implementation, verification scope, and next steps are in docs/acoustic-v1.md. Passing hardware numerical checks does not establish adequate detection quality.

## Acoustic feature improvement experiments

90 training/validation candidates compared; evidence binding valid: True. Engineering candidate: uniform16-log-c1-centroid（log1p）。
Validation AUC 0.6883; recording-level false-positive rate 5.0%; recall 43.3%; quality gate passed: False。
The new scheme was not quantized, implemented in RTL, or programmed; the test set remained unopened in this round. Full results: docs/acoustic-v2-study.md.

## Investigation of missed acoustic detections

Missed-detection analysis, temporal features, full spectra, and pretrained representations did not exceed 13/30 detections. The new validation criteria require at least 27/30 detections, at most 2/40 false alarms, and AUC>=0.90; these were not met.
- acoustic-v3-diagnosis：27 candidates; evidence binding valid True; test set opened False。
- acoustic-v3-resolution：6 candidates; evidence binding valid True; test set opened False。
- acoustic-v4-temporal：30 candidates; evidence binding valid True; test set opened False。
- acoustic-v5-finespectrum：24 candidates; evidence binding valid True; test set opened False。
- acoustic-v6-panns：6 candidates; evidence binding valid True; test set opened False。

Grouped diagnostics: docs/acoustic-v3-diagnosis.md; higher criteria and temporal experiments: docs/acoustic-v4-temporal.md; full-spectrum and pretrained work: docs/acoustic-v5-v6-progress.md. Quantization and RTL were unchanged.

## Supervised known-fault classification: passing same-machine version

Separate fault-training data were authorized; evidence binding valid: True。
The primary model detected 30/30 with 2/40 false alarms and AUC 1.000 on the original validation set. With the threshold frozen, the holdout test detected 50/50 with 1/40 false alarms and AUC 1.000. All three criteria passed.
The linear baseline produced 5/40 test false alarms and failed. This model version was not deployed to FPGA. Full report: docs/acoustic-supervised-results.md.
Statements that the test set was unopened refer to each earlier experiment at its historical stage. This supervised version completed one formal holdout evaluation.

## Generalization audit: cross-machine criteria failed

Audit evidence binding valid: True. No exact duplicates were found among the old 400 clips. All 267 candidates from 44,700 cross-split comparisons were checked again at the original sample rate; no near-duplicates met the threshold. Acquisition-batch independence is still not fully confirmed.
Frozen model/threshold on fan/id_02: 23/30 detections, 24/40 false alarms, AUC 0.6033; higher criteria failed. No retraining or threshold tuning was performed.
The original AUC 1.000 is a same-machine result, not evidence of cross-machine generalization. Report: docs/acoustic-generalization-audit.md.

## Three-machine training and whole-machine 06 holdout test

960 development clips and 160 final-test clips; old test clips excluded: 90. Saved data-verification receipts: 1120. Model frozen: True; machine 06 evaluated: True。
Candidate shape-linear_1; frozen binding valid True; all three development folds pass False。

| Held-out machine | AUC | Recall | False-positive rate |
|---|---:|---:|---:|
| 00 | 0.5979 | 95.6% | 95.6% |
| 02 | 0.5410 | 93.1% | 95.0% |
| 04 | 0.8336 | 40.6% | 1.2% |

Machine 06 final test: AUC 0.6388; recall 80.0%; false-positive rate 75.0%; higher criteria passed False。

Workflow and sources: docs/multimachine-training.md. These are software evaluations and do not establish hardware deployment of a new model.

## Cross-machine temporal-feature experiments

Completed 8 schemes and 24 training folds; binding valid: True; independent audit: True. Selected: temporal-linear_1; all machines pass: False. Machine 06 was not accessed again.

The higher criteria remain unmet. Full results: docs/multimachine-temporal-results.md. New independent confirmation data are needed; already evaluated machine 06 must not be used for tuning.

## Machine-shift diagnostics

Same-machine controls and 27 folds of source-shift-reduction training are complete. Selected: pc16-rbf_10; all pass: False; binding valid: True; audit: True. Machine 06 was not accessed again.

Report: docs/machine-shift-results.md. The higher criteria remain unmet.

## Time-frequency CNN experiments

CNN v3 source-machine perturbation across three folds; all pass: False; binding valid: True; reload audit passed: True. The normalization layout issue was fixed; all three reloaded models produce exactly matching scores. No quantization or hardware deployment; machine 06 was not accessed.

Report: docs/cnn-normalization-and-augmentation.md. Older CNN reports are retained. The higher criteria remain unmet.

## Official pretrained acoustic features

EfficientAT mn10_as extracted features for 960 development recordings and completed nine classifier-head training folds. All pass: False; binding valid: True; classifier-head audit: True. Machine 06 was not accessed; no hardware deployment.

Report: docs/pretrained-acoustic-results.md. The higher criteria remain unmet; the next step is to investigate data and additional machine sources.

## Review of additional machine sources

The 1200 recordings from DUE 00/01/02 were used in three-fold development; both candidates failed. Sections 03/04/05 have not been evaluated in this project. The historical reserved_section_02_opened=false field in results.json was inherited incorrectly; use the actual records and development-v2.json.

Physical-device correspondence with the original MIMII dataset is unconfirmed. Normal-reference calibration is not a zero-shot cross-machine success. Source review: docs/additional-machine-source-review.md; training and actual results: docs/due-training-results.md.

Normal-reference experiment complete; all three metrics pass: False. See the training report above.

acoustic-due-short-time-v1 complete; all pass: False; detailed metrics are in the training report.

acoustic-due-short-supervised-v1 complete; all pass: False; detailed metrics are in the training report.

128-band Mel autoencoder comparison: False。

Post-hoc threshold diagnostics on saved development scores: at FPR<5%, best single-group recall 17.5%. This is an optimistic diagnostic, not a formal result.

A supplement of 192 clearer training recordings was fixed; download-completion record present: True。

Six noise-version augmentation experiments complete; all pass: False. Actual metrics are in the training report.

Six paired-spectrum restoration experiments complete; all pass: False. Machine 02 shows a local improvement; this does not satisfy all three-machine acceptance gates.

Normal-reference versus development overlap screening: 243600 pairs; high-correlation raw-waveform flags: 0 pairs. Method limitations are in the report; this does not prove acquisition-batch independence.
