# Fixed Evaluation Target and Two-Model Comparison

Subsequent status: the user authorized further optimization until every machine passes, followed by RTL changes, programming, and physical measurements. The original three folds, calibration recordings, and 720-recording final-test list remain unchanged. Additional training/calibration data are registered separately without rewriting this frozen list. See [optimization progress](known-machine-optimization-progress.md) for newer experiments and remaining gaps. The “two-model stopping condition” below was a historical constraint of the first experiment; subsequent work follows the newer authorization without lowering numerical acceptance standards.

## Results of This Iteration: Retraining Completed, Programming Gates Not Met

All 1024 development recordings were prepared and verified. Across four machines, 98304 cross-group recording pairs were screened. There were no exact complete-waveform duplicates or exact cross-group segment duplicates. Machine 00 produced 183 low-frequency similarity candidates; the initial review covered only the first 100, so the training entry point rejected the initial attempt. The remaining 83 were subsequently reviewed, none reached the raw-waveform correlation flag threshold of 0.98, and only then did training begin. The incomplete initial review, rejection log, and completion records are all retained. This screening does not establish acquisition-session independence.

All six fits, two models×three folds, completed, and reloaded models reproduced every saved score exactly. A separate direct pairwise comparison of positive/negative scores independently recomputed 40 AUC/count statistics, all matching. No model met the gates, so no final-model refit, fixed-point deployment, RTL modification, or programming took place in this iteration. The 720 final-test recordings had not yet been read.

|Model|Machine|Anomaly detection rate|Normal false-positive rate|Mean fold AUC|
|---|---|---|---|---|
|Logistic regression|00|22/96 = 22.92%|7/96 = 7.29%|0.71908|
|Logistic regression|02|29/96 = 30.21%|0/96|0.95117|
|Logistic regression|04|29/96 = 30.21%|0/96|0.98796|
|Logistic regression|06|21/96 = 21.88%|0/96|0.92285|
|Logistic regression|Pooled|101/384 = 26.30%|7/384 = 1.82%|0.89968|
|MLP|00|14/96 = 14.58%|0/96|0.81413|
|MLP|02|23/96 = 23.96%|0/96|0.98958|
|MLP|04|38/96 = 39.58%|0/96|0.99512|
|MLP|06|12/96 = 12.50%|0/96|0.98958|
|MLP|Pooled|87/384 = 22.66%|0/384|0.96033|

Detection and false-positive rates pool out-of-fold predictions, with each recording counted once. AUC is the mean across three equally sized folds, not a final independent test result. The MLP ranks samples substantially better on 02, 04, and 06 but remains weak on 00. Normal calibration scores from 00 determine the shared threshold in all three folds. The MLP's shared fold thresholds are approximately 3.103, 5.037, and 3.973; candidate thresholds calibrated separately for every other machine are negative, so the shared threshold increases misses on the other machines. This does not justify immediately switching to per-machine thresholds and declaring success: 00 still has a ranking problem, and the current protocol specifies a shared model and shared threshold.

This iteration followed its fixed stopping condition, without automatically adding models or expanding the search. Further optimization should begin with bounded diagnosis of 00's inputs, bin selection, and erroneous recordings. This failure does not establish that every same-machine approach is infeasible.

Evidence entry points: `artifacts/acoustic-known-machines-v1/results.json`, `audit.json`, and `protocol.json`. Data reviews: `data/mimii-known-machines-v1/development-audit.json` and `development-audit-completion.json`. Training log: `build/known-machine-training-after-audit.log`. Omitted raw data and build logs remain local.

This version uses the user-confirmed scope: training covers MIMII fan IDs 00, 02, 04, and 06; evaluation uses new recordings from those covered devices. Training may use normal and known-fault labels. Historical cross-machine results remain as applicability limits and are no longer this version's release gate. No claim is made for unfamiliar models or unknown faults.

## Frozen Recording Lists

`data/mimii-known-machines-v1/plan.json` stores roles and fold assignments for 1744 complete recordings; `freeze.json` stores their digest. At freezing, only directory listings and historical manifests/receipts were read, not new final-test waveforms.

|Use per machine|Normal|Anomalous|Total|
|---|---|---|---|
|Three-fold cross-validation pool|96|96|192|
|Independent threshold-calibration pool|32|32|64|
|Final test|100|80|180|

Across four machines: 768 cross-validation recordings, 256 calibration recordings, and 720 final-test recordings. All historical final-test recordings are excluded. Final-test files were chosen from files never selected in the reviewed historical manifests and download receipts, without selection based on audio or scores. Development preferentially reuses recordings historically permitted for use and cannot be called wholly new independent validation.

Each complete file and its windows, channels, and noise versions stay in the same group. Without reliable acquisition-session mapping, claim recording-level separation only, not independence across sessions. Near-duplicate screening must cover the new list. If cross-group duplication is found, quarantine the complete group before training/scoring according to predetermined filename order, record the revision, and never replace files based on accuracy.

## How the Three Folds Run

In each fold, each machine contributes 128 CV-pool recordings for fitting and 64 for validation. All four machines appear in both training and validation, but no recording crosses groups. Rotate three times so each CV recording receives exactly one prediction from a model not trained on it. The calibration pool is never used to fit weights, select bins, or fit normalization.

Each fold's bins and scale parameters are determined solely from that fold's training recordings. The alarm threshold uses normal recordings from the independent calibration pool: take the second-highest of 32 normal scores for each machine, then the maximum across the four machines. A fault requires a score strictly greater than the threshold. This controls empirical calibration-set false positives only; it does not guarantee a false-positive rate on new recordings. Anomalous calibration recordings are used only for fixed reporting, not threshold tuning. Each model has this single threshold rule.

## Only Two Candidates

|Candidate|Configuration|FPGA computation|
|---|---|---|
|Logistic regression|32 inputs → 1 score; L2, C=1, maximum 3000 iterations|32 multiply-accumulates; no sigmoid required on the board|
|Small MLP|32 → 16 ReLU → 1 score|528 multiply-accumulates and ReLU|

Both share three-neighbor power features around 32 center bins: N1024, 16 kHz, nonoverlapping windows, DC removal, and periodic Hann. For each 10-second recording, take the first 156 complete windows (9.984 seconds), average band power first, then apply a common energy compression and quantization. Taking logarithms before averaging is not an equivalent implementation.

Candidate bins are selected by normal/anomalous discrimination in training data, aggregated over all four devices, with exactly 32 nonoverlapping neighbor groups. Lock the numerical contract, overflow checks, and selection formula separately before implementation rather than repeatedly changing them against validation results. Both candidates use exactly the same front end, no machine-ID input, and no separately trained model for each machine.

The initial floating-point feasibility implementation is now fixed: center bins 2..511, minimum spacing 3. For each of the four IDs, compute squared normal/anomalous mean difference divided by the sum of within-class variances plus 1e-6; sum the scores across IDs and rank them, preferring lower bins on ties. Features are log2 of the sum of the three neighboring bins' mean powers, with power floor 1e-12, normalized by training mean and standard deviation with standard-deviation floor 1e-6. This is explicitly a floating-point feasibility comparison, not completed fixed-point-front-end or RTL equivalence work.

The MLP configuration fixes seed 71, Adam learning rate 0.001, batch size 64, 100 epochs, binary logit loss, and the final epoch's model. The initial scope is two models×three folds = six fits; do not automatically add networks, pretrained models, tree models, or hyperparameter grids. Logistic regression also uses seed 71. This paragraph records the originally scheduled configuration and does not itself establish completed training; completed results are reported above.

## Selection, Acceptance, and Stopping Conditions

First combine each machine's three-fold predictions made without that recording in training. Report detection rate, false-positive rate, AUC, and confusion matrix for each machine, as well as pooled results and fold variation. The three unchanged gates are detection >90%, false-positive rate <5%, and AUC≥0.9. Every machine and the pooled result must pass; the average alone is insufficient.

Detection and false-positive rates pool out-of-training predictions at each fold's independently calibrated threshold. Development AUC is the mean of AUCs from three equally sized folds, avoiding ranking distortion from mixing differently fitted models' score scales. Also report AUC of directly pooled scores as a diagnostic. The final test uses one frozen model, so its AUC is computed directly from that model's scores.

Entry points run in order: `prepare_known_machine_development.py`, `audit_known_machine_development.py`, and `train_known_machine_models.py`, all in `scripts`. The training entry point requires passing overlap review for the new development manifest. None of these three scripts exposes a downloader for the new final-test recordings.

If both candidates meet development gates, prefer logistic regression for lower computation. If only the MLP passes, select the MLP. If neither passes, report specific gaps, stop automatically expanding model search, and diagnose data or the fixed front end first. Development results already used for selection cannot be treated as independent final results.

After selection, refit only on the complete CV pool and freeze the threshold with the calibration pool. Use INT8 weights and INT32 accumulation, with explicit bit widths, rounding, and saturation for the front end and intermediates. Complete integer-reference/RTL equivalence, resource, and throughput checks on development data first; freeze the deployment version, then open the 720 test recordings. For each machine, at most 4/100 normal false positives and at least 73/80 anomalies detected are required, together with AUC≥0.9. Report confidence intervals; finite-sample success is not a population-performance guarantee.

If the final test fails, report it unchanged; do not reuse these recordings to select models or thresholds. Final delivery still includes simulation, synthesis/timing, and UPduino measurements for a matching version. Freezing this split does not mean the model passes or board deployment is complete.

## FPGA Scope

Thirty-two three-neighbor groups require 96 bins and retain shared multiply-accumulate and quarter-cycle coefficient-ROM concepts; the existing 16-dimensional core still requires modification. The existing state-machine formula estimates approximately 12.3 ms of DFT per 64 ms window for four lanes at 12 MHz. Other stages are not included, so this is only an initial budget and requires measurement of the new version. Without a microphone, verify by replaying real recordings and do not call it field acoustic capture.
