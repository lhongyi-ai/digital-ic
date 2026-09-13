# Known-Machine Recognition: Acceptance and Deployment Progress

The target remains unchanged: each covered machine 00/02/04/06 and the pooled results must achieve anomaly detection >90%, normal false-positive rate <5%, and AUC ≥0.9. Matching-version physical-board acceptance starts only after the algorithm, integer reference, and RTL are frozen and final confirmation passes. The unified status page defines held-out-data access/evaluation status. The table below contains development results only.

## Current outcome: final testing and physical validation of matching firmware are complete

The one-time evaluation of 720 held-out recordings after freezing passed: pooled detection 317/320 (99.06%), false positives 8/400 (2.00%), and AUC 0.99841. All four machines also passed their original criteria individually. All 725 integer-score and metric checks passed. See the [final test](known-final-test.md) for counts and limitations.

UPduino 3.1 completed 22 raw-PCM replays: 1248 cumulative windows with one MAC and 2184 with four MACs, matching the integer reference. Each boot processes 156 consecutive windows; totals across restarts must not be described as a single continuous test. Deliberate one-MAC overload explicitly reported errors, followed by successful reset recovery. Machine 00's four-MAC firmware was restored last. See [physical-board results](known-hardware-results.md).

The following development-stage results are retained separately from final-test statistics.

The selected model is a separate full-512-bin linear model per machine, using the original training volume. Machine 00's normal calibration set was expanded to 160 recordings. The extra-256-training-recording route remains a failed comparison and is not mixed into the selected model. Three folds are fixed, and every CV recording receives exactly one prediction from a model that did not train on it.

| Machine | Integer-chain detection | Integer-chain false positives | Mean fold AUC |
| --- | ---: | ---: | ---: |
| 00 | 90/96 =93.75% | 4/96 =4.17% | 0.98796 |
| 02 | 96/96 =100% | 0/96 | 1.00000 |
| 04 | 96/96 =100% | 2/96 =2.08% | 1.00000 |
| 06 | 96/96 =100% | 2/96 =2.08% | 1.00000 |
| Pooled | 378/384 =98.44% | 8/384 =2.08% | 0.99862 |

The chain includes integer DC removal, Hann windowing, full DFT, power, accumulation over 156 windows, a logarithm LUT, integer normalization, INT8 weights, and an INT32 classification score. The table contains software development results. New RTL, bit-exact simulation, and board builds progressed separately; the table is not a final test or a physical-board result. Methods and boundaries are in the [integer deployment contract](known-integer-deployment.md).

The floating-point development approach passed 34 independent recomputation checks; the INT8 classifier retained the acceptance criteria; the complete integer software passed another 17 checks on thresholds, scores, and grouped metrics. Five fixed-point unit tests cover positive/negative rounding, extreme/DC inputs, an independent scalar MAC, logarithm error, and absolute power of a known sinusoid. Integer features were generated for 1152 development/calibration recordings, with zero centering saturations.

Retained failure: integer DSP v1 mistakenly used normalized-power units although training used squared PCM counts, shifting log2 features by 30. Units were corrected, an independent scale test was added, and rebuilt v2 passed. The failed directory was not overwritten.

## Completed changes supported by evidence

| Experiment | Machine 00 detected /96 | False positives /96 | Mean fold AUC | Assessment |
| --- | ---: | ---: | ---: | --- |
| Balanced 32 three-neighbor groups, shared MLP | 67 | 8 | 0.89095 | Balanced scoring helped, but 00 still failed |
| Separate 32 three-neighbor groups and MLP per machine | 71 | 5 | 0.95247 | 00 still missed faults; 02 had 5/96 false positives; 04 and 06 passed |
| Separate 32 single bins and MLP per machine | 87 | 9 | 0.95801 | Avoiding neighbor aggregation increased detection, but false positives remained high |
| Full-512-bin linear model, old calibration rule | 95 | 7 | 0.98828 | Preserving spectral detail helped substantially, but criteria were not met |
| Full-512-bin MLP, corrected calibration rule | 49 | 1 | 0.96582 | A larger network did not beat the linear model; no further network expansion |
| Select 64 bins by training-only linear weights, then refit; corrected rule | 76 | 4 | 0.97201 | 02/04/06 all passed; 00 remained insufficient |
| Add 256 training recordings for 00, full-512 linear model, corrected rule | 78 | 2 | 0.98991 | Strong discrimination, but insufficient detection at the current threshold |

These are not a unified one-factor-at-a-time ablation. Threshold-rule changes are listed explicitly; all metric differences cannot be attributed to the network. The first report that varies factors individually is the [balanced-bin ablation](known-machine-balanced-ablation.md). Exact configurations, fold IDs, scores, and models are stored in each corresponding protocol/results.json.

## Correcting normal-calibration rules

The old rule selected the second-highest of 32 normal calibration scores. It yields an empirical calibration false-positive rate of 1/32, not a guarantee below 5% for future recordings. With a fixed model, continuous scores, and exchangeable samples, that rank corresponds to a future marginal exceedance probability of 2/33, about 6.06%.

The finite-sample quantile is the `ceil((n+1)*(1-alpha))`th score in ascending order, with strict decision `score > threshold`. For n=32 and alpha=.05, this is the 32nd score, the maximum. The method requires exchangeability, and a marginal guarantee does not ensure that every finite test set passes. Repeated development selection and missing acquisition-batch information mean this project cannot claim a population false-positive-rate guarantee. [Method source: Angelopoulos and Bates](https://arxiv.org/abs/2107.07511)

This round additionally fixed 128 normal calibration recordings in advance, retaining the original 32 for a total of 160. Before scoring, the rule was registered as alpha=.04, giving the 155th score, or sixth highest. Models were not retrained during calibration expansion. Saved full-spectrum linear models with original and expanded training volumes were compared separately, with all results recorded. Other IDs still use 32 normal calibration recordings and their maximum score as threshold. Original anomalous calibration recordings do not determine thresholds.

## Data and validation boundaries

- Added training: 128 normal and 128 faulty recordings from machine 00. Filename SHA256 fixes their order; the complete original frozen list and every historical test recording are excluded. Selection does not use scores. They are appended to the training pool in each fold, leaving original validation and calibration unchanged. Per-fold training for 00 increases from 128 to 384 recordings.
- The added training data and original 00 development data were screened across 65,536 pairs. All 350 candidates were reviewed at the original sampling rate, with no flags at the 0.98 threshold or exact cross-group duplicates. Checks cover only the specified lengths and bandwidths and do not establish acquisition-batch independence.
- The 128 added normal calibration recordings are distinct from original development and added training data; another 65,536-pair overlap review is required before use.
- Separate machine parameters require configuring the installed machine ID. All four machines share one computation circuit and load their own parameters. This is not generalization to an unfamiliar machine.
- Subsequent pooled AUC uses the explicit alarm score `logit - machine_threshold`, while also reporting AUC of raw logits. Per-machine AUC is unchanged by subtracting a fixed threshold.

Model reload, metric, split, and normalization checks completed for local/detail/capacity groups, with 16/32/32 checks respectively. The first audit failed because the auditor forced a different matrix memory layout, changing floating-point accumulation order. It was rerun with the original layout and unchanged tolerance; the original failure log remains. Final fixed-point/RTL verification still requires bit-exact agreement.

## Development evidence and final delivery

- `artifacts/acoustic-known-{local,detail,capacity}-v1/`: fixed per-machine and spectral candidates and audits.
- `data/mimii-known-extra00-v1/`: fixed extra-training list, download receipts, and complete near-duplicate review.
- `artifacts/acoustic-known-extra00-v1/`: three-fold models and results with expanded training.
- `data/mimii-known-calibration00-v1/`: additional normal-calibration list, download receipts, and review before use.
- `artifacts/acoustic-known-calibration00-v2/`: generated after calibration-expansion scoring completed; its earlier planned existence was not evidence of completion or passing. The first v1 attempt stopped because of the same matrix-layout recomputation difference. The corrected run used v2, retaining the failed directory and logs.

Final model refitting and parameter export, new RTL, 1092-window stage-by-stage regressions for each of one/four MACs, the first complete Flash application build, and end-to-end simulation of real recordings are complete. `artifacts/evidence/current-status.md` summarizes currently valid reports; failed resource-optimization attempts are also retained. The [overfitting audit](known-overfitting-audit.md) explains AUC=1 and shuffled-label controls. A control AUC near 0.5 is not deterioration of the formal model.

Four-MAC firmware for all four machines and the one-MAC baseline for 00 passed final resource/timing checks and complete Flash-replay simulation. `make release PROFILE=known` passed 272 Python checks and froze the models, RTL, and firmware. `run_known_hardware.py` completed physical execution after final-test and audit gates passed. See the [model training explanation](known-training-explained.md).

This round completed software quality gates, RTL verification, synthesis/place-and-route, and physical replay with matching firmware. Actual clock frequency, power, microphone/field-fan performance, and acquisition-batch independence remain unverified. These results do not establish unfamiliar-machine generalization or fully exclude overfitting.
