# DUE Cross-Machine Training and Normal-Reference Experiments

## Current conclusion

Neither model in the three-machine rotation met anomaly detection >90%, normal false-positive rate <5%, and AUC ≥0.9. No new model is ready for release under these criteria, so RTL has not been modified or programmed for these candidates.

The table below comes from `artifacts/acoustic-due-three-sections-v1/results.json`. Each row evaluates 200 normal and 200 anomalous recordings.

| Model | Held-out section | Anomalies detected | Normal false positives | AUC |
| --- | --- | --- | --- | --- |
| RBF SVM | 00 | 16/200 | 13/200 | 0.45595 |
| RBF SVM | 01 | 68/200 | 90/200 | 0.45100 |
| RBF SVM | 02 | 12/200 | 13/200 | 0.49885 |
| Extra Trees | 00 | 55/200 | 60/200 | 0.43449 |
| Extra Trees | 01 | 3/200 | 1/200 | 0.49028 |
| Extra Trees | 02 | 0/200 | 2/200 | 0.53265 |

A low false-positive rate may simply mean the model rarely raises an alarm; detection must be examined at the same time. AUC is also low here, so threshold adjustment alone cannot meet the target.

## How these models were trained

1. DUE fan sections 00, 01, and 02 each supply 400 complete recordings, including source/target acquisition conditions and normal/anomalous labels. Official test files were explicitly reassigned to development in this project; they are no longer this project's final test set.
2. Each recording is processed with a 1024-sample Hann window and a 512-sample hop. Every eight frequency bins are summed into one band, producing log energies for 64 bands.
3. The mean, standard deviation, 10th percentile, 90th percentile, and adjacent-window change are calculated for each band over the recording, giving 320 values. The model therefore sees the energy distribution and some variation statistics, but not the complete temporal sequence.
4. Each fold fits the model on 640 recordings from two machines and calibrates on another 160. The third machine's 400 recordings are used only for that fold's validation. Normalization is fitted only on training data; the threshold is the maximum score among normal calibration recordings.
5. SVM learns a normal/anomalous decision boundary; Extra Trees learns multiple tree-based decision rules. Both use fault labels and are therefore not unknown-fault detectors trained only on normal data.

## Completed improvement experiment: a separate normal reference for each machine

The hypothesis was that inherent differences between machine sounds might exceed fault-related differences. Recording a machine's normal operation first, then measuring deviations from that baseline, may better match deployment.

The fixed experiment uses another 200 source-normal recordings and three target-normal recordings per machine. A filename-hash split is fixed in advance: 150 source plus three target recordings form the reference bank, while the remaining 50 source recordings determine only the threshold. The same 320-dimensional features are used, with no new network. The anomaly score is the average standardized distance to the three nearest normal references.

This is detection after calibration on normal sounds; it does not establish generalization without any exposure to the new machine. Three target references also cannot guarantee the target-condition false-positive rate, so results must be reported by condition. Even passing development results would still require model freezing, an independent final evaluation, an FPGA-suitable fixed-point implementation, and physical-board evidence.

Results from `artifacts/acoustic-due-normal-reference-v1/results.json`:

| Section | Anomalies detected | Normal false positives | AUC |
| --- | --- | --- | --- |
| 00 | 1/200 | 0/200 | 0.605475 |
| 01 | 23/200 | 35/200 | 0.535900 |
| 02 | 1/200 | 0/200 | 0.573725 |

All three sections failed the criteria. All 1809 input PCM files passed hash and exact-duplicate checks, and reloading the three saved models reproduced every score exactly. Section 01's source/target false-positive rates were 11%/24%, showing that the normal reference did not adequately resolve acquisition-condition changes. This rules out the proposal that adding a normal reference to the existing whole-recording statistics is sufficient; it does not rule out other features or models. The next justified question was whether whole-recording statistics hide local anomalies: retain short-time features, score short segments, and then aggregate, rather than first compressing the entire recording into one vector.

## Short-time feature diagnostic results

Two fixed experiments have been completed; neither passed:

| Method | 00 AUC (mean/top 10%) | 01 AUC | 02 AUC |
| --- | --- | --- | --- |
| Normal-reference covariance distance | 0.632 / 0.563 | 0.517 / 0.499 | 0.574 / 0.537 |
| Fault-supervised training with an entire machine held out | 0.496 / 0.476 | 0.490 / 0.497 | 0.414 / 0.433 |

Both use 32 log bands and five consecutive frames of context (192 ms). The first fits a shrinkage covariance model to normal references, calculates a distance per segment, and sets the threshold using 50 separate normal calibration recordings. The second uses the original three development folds and fault labels to train 200 Extra Trees, taking one of every eight contexts for fitting and evaluation. Recording labels are assigned to their segments, which may introduce segment-label noise. Mean aggregation and top-10%-segment aggregation were both fixed in advance.

Evidence: `artifacts/acoustic-due-short-time-v1/results.json` and `artifacts/acoustic-due-short-supervised-v1/results.json`. These short-time features and models did not solve cross-machine fault discrimination. More training or a lower threshold cannot simply be promised to meet the target. Neither experiment accessed final test recordings or USB. Further work should first check differences from published methods in inputs and evaluation protocols, instead of expanding parameter searches without evidence.

## Published-baseline review and Mel autoencoder comparison

The [official DCASE2021 description](https://dcase.community/challenge2021/task-unsupervised-detection-of-anomalous-sounds) uses 128 log-Mel bands and five consecutive frames for a 640-dimensional input, an eight-dimensional autoencoder bottleneck, and 100 training epochs. Its protocol allows normal training sounds from the section under test; official results cannot be presented as performance on a completely unseen machine. Its threshold rule also differs from this project's strict 5% false-positive acceptance criterion.

The additional experiment in `scripts/train_due_mel_ae.py` therefore uses that feature size and network structure, fits on the existing 153 normal references per section, calibrates on 50 separate normal recordings, and evaluates 400 development recordings. The PyTorch implementation, separate model per section, reference count, and threshold rule differ from the official procedure, so this is a comparison based on the official design, not a complete reproduction. The final epoch of a fixed 100-epoch run is used; epochs are not selected using development fault scores. Log: `build/due-mel-ae.log`; output: `artifacts/acoustic-due-mel-ae-v1`.

This experiment tests whether finer Mel features and a reconstruction model outperform the recent uniform-band methods. It neither changes the original high standards nor replaces independent final testing and FPGA deployment verification.

All three sections completed 100 epochs. Reloading each saved model reproduced outputs for 16 probe inputs exactly; this is only a save/reload consistency check, not full deployment validation.

| Section | Detection rate | False-positive rate | AUC |
| --- | --- | --- | --- |
| 00 | 1.5% | 0.5% | 0.63755 |
| 01 | 6.0% | 5.0% | 0.58475 |
| 02 | 3.0% | 0.5% | 0.65705 |

The model still fails the three criteria. Finer Mel features and reconstruction improved on the previous round, but that does not imply more epochs will meet the target. Section 01's false-positive rate is exactly 5%, which also fails the strict requirement of less than 5%. Full results: `artifacts/acoustic-due-mel-ae-v1/results.json`.

## Threshold or score ranking: a diagnostic without retraining

`artifacts/acoustic-due-score-audit-v1/results.json` examines the 24 saved sets of development scores above and independently checks AUC. Even if development labels are used retrospectively to choose the most favorable threshold, allowing at most nine false positives among 200 normal recordings (strictly below 5%), the best single result detects only 35/200 anomalies (17.5%, Mel AE section 02). These fixed scores therefore cannot meet the target solely by changing thresholds.

This is an optimistic diagnostic using evaluation labels, not a deployable threshold, an independent validation result, or an upper bound on other models. Model thresholds were not changed, and final test data were not opened.

To avoid unsupported experiments, the next step was limited to probing the +6 dB counterparts of original MIMII training recordings: [official dataset page](https://zenodo.org/records/3384388). The first six recordings were fixed: one normal and one anomalous fit recording from each of 00/02/04, without reading calibration, old test recordings, or 06. Noise variants must remain in the same group; they are not additional independent machines, and results on clearer data cannot replace results under the original validation conditions. Probe results: `data/mimii-snr-probe`.

The six probes were completed. Same-name 0/+6 dB waveform correlations were 0.477–0.871. This proves neither samplewise separation of a clean signal nor independence of the versions. The subsequent fixed supplement comprises 192 fit recordings (32 per machine and class, selected by filename hash). `scripts/download_mimii_snr_fit.py` supports verified resume. `scripts/train_mimii_snr_augmented.py` uses the original 512-bin spectral-shape features and compares only logistic regression and Extra Trees. Each fold adds 128 clearer training recordings from the other two machines; original 0 dB calibration and validation remain intact. Supplementary recordings from the validation machine are unused in that fold. Training was to start only after downloads finished; the existence of a script was not treated as a completed result.

## Clearer training-sound supplement: completed results

All 192 +6 dB training recordings were downloaded and verified. Both models completed all three folds, still evaluated under the original 0 dB conditions. Each fold uses 512 original training recordings plus 128 supplementary recordings; calibration and validation recordings are unchanged. Reloaded models reproduced all six sets of validation scores exactly.

| Model | Held-out machine | Detection rate | False-positive rate | AUC |
| --- | --- | --- | --- | --- |
| Logistic regression | 00 | 95.00% | 96.25% | 0.58305 |
| Logistic regression | 02 | 95.00% | 96.875% | 0.50754 |
| Logistic regression | 04 | 43.75% | 1.875% | 0.81660 |
| Extra Trees | 00 | 100.00% | 99.375% | 0.57516 |
| Extra Trees | 02 | 90.625% | 70.00% | 0.78201 |
| Extra Trees | 04 | 94.375% | 54.375% | 0.88131 |

No fold met all three criteria simultaneously. Extra Trees improved AUC on 04 from 0.77479 to 0.88131, but false positives rose from 21.875% to 54.375%; 00 did not improve. Reporting only high detection would be misleading, and this supplement did not solve noise sensitivity or cross-machine generalization. Results: `artifacts/acoustic-mimii-snr-augmented-v1/results.json`. The final test set was not reevaluated, and no new model was programmed.

## Paired-spectrum restoration diagnostic

The same 192 recordings were reused. In each fold, only the 128 paired 0/+6 dB training spectra from the other two machines fit a standardized ridge regression (alpha=10), followed by logistic regression or Extra Trees fitted to the restored original training features. Paired sounds from the validation machine do not participate in fitting; original calibration and validation records remain unchanged. Script: `scripts/train_mimii_paired_denoising.py`; results: `artifacts/acoustic-mimii-paired-denoising-v1/results.json`.

| Model | Held-out machine | Detection rate | False-positive rate | AUC |
| --- | --- | --- | --- | --- |
| Logistic regression | 00 | 91.25% | 88.75% | 0.60031 |
| Extra Trees | 00 | 99.375% | 96.875% | 0.57488 |
| Logistic regression | 02 | 94.375% | 90.00% | 0.67645 |
| Extra Trees | 02 | 67.50% | 1.25% | 0.90873 |
| Logistic regression | 04 | 36.25% | 2.50% | 0.77770 |
| Extra Trees | 04 | 5.00% | 15.625% | 0.40188 |

None of the six results passed all criteria. Section 02 improved substantially, but 04 deteriorated substantially, so 02 alone cannot establish success. Reload checks found validation-score errors no greater than 1e-10 and identical threshold decisions. This is a software development experiment, not an independent final test or hardware evidence. Parameter-search expansion for this batch of paired-noise experiments stops here; there is no evidence that a common noise correction resolves differences across all machines.

## RTL constraint review before deploying new features

The current `rtl/core/acoustic_core.sv` fixes the feature count, hidden layer, and reconstruction output to 16 in several places; a 512-dimensional spectral classifier cannot be deployed merely by replacing weight files. It also outputs results per short window, while the current software averages power over the recording before taking logarithms. These operations cannot be reordered. Deployment must implement identical recording-level power accumulation, logarithms, and mean removal, with a new integer reference and bit-exact verification.

Using the existing state-machine formula `DFT_MAX=(2*bins/LANES)*(3*N+LANES+1)`, expansion to 512 bins, N1024, four lanes, and 12 MHz requires about 787712 cycles for DFT alone, or 65.64 ms. This already exceeds the 64 ms nonoverlapping window interval at 16 kS/s, before preprocessing and classification. This is an estimate from the state-machine formula, not a measurement of a new version. The architecture cannot simply be claimed to process the full spectrum in real time.

Coefficient storage already uses quarter-cycle ROM per lane, so complete sine/cosine tables need not be stored for all 512 bins. Scheduling, cycle counts, and feature storage require renewed verification. If the algorithm passes, subsequent options include pipelined scheduling or FFT; a higher clock also requires place-and-route timing validation. Pausing sampling must not hide insufficient throughput. Extra Trees is currently an algorithmic comparison, with no assumption that it fits directly on the board. Logistic regression is easier to express as fixed-point multiply-accumulate operations, but its frontend cost still needs to be resolved.

## Overlap checks between normal references and development recordings

`artifacts/acoustic-due-reference-overlap-v1/results.json` completes the checks between 203 normal reference/calibration recordings and 400 development recordings in each of three sections. Each section screens 81200 pairs, totaling 243600, using antialiased downsampling to 500 Hz and all integer time shifts with at least two seconds of overlap. No initial candidate reached an absolute correlation of 0.8. The top 20 pairs per section were nevertheless checked on the original 16 kHz waveforms: 60 pairs total, with a maximum absolute correlation of about 0.517, all below the 0.98 flagging threshold.

The 1809 recordings contain no exact whole-waveform duplicates. Nonconstant one-second segments sampled every 0.5 seconds also contain no exact segment duplicates between reference and development uses. These checks do not train models, change thresholds, or read final test data.

Limitations: time-shift near-duplicate screening is performed only within each section; low-frequency screening may miss reuse confined to high frequencies; nonexact overlaps shorter than two seconds are not covered. The results do not establish independent acquisition batches or rule out shared physical machines between original MIMII and DUE.

## Data and evidence limitations

- DUE02 has been reassigned to development. `reserved_section_02_opened=false` in the old three-fold results file is an inherited-field error; actual records, fold indices, and `development-v2.json` explicitly include 02.
- Original MIMII id06 has already been tested and must not be reused for model or threshold selection. DCASE2021 sections 03/04/05 have not been evaluated in this project.
- Normal-reference and development recordings have completed the limited exact/near-duplicate checks above. This does not exclude every near-duplicate, acquisition-batch relationship, or physical-machine overlap between the two datasets.
- Normal-reference selection does not depend on model scores. The operating-condition labels in filenames of the first 200 source files match those in all 1000, but those labels alone cannot establish adequate coverage of conditions and acquisition batches.
- All results here concern software algorithm development; accuracy, speedup, and physical-board conclusions from the old CWRU model do not transfer to these experiments.
