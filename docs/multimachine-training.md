# Three-Machine Development and Whole-Machine Reserved Testing

Follow the user-specified workflow: rotate 00, 02, and 04 as whole-machine validation holdouts, select an approach, fit the final model using all three machines' development data, freeze it, then evaluate 06 once as the reserved test. The task remains supervised known-fault recognition, single-channel, at 0 dB.

## Data and Leakage Prevention

- Each development machine contributes 160 normal+160 fault recordings, totaling 960. Fixed hashing divides each class into 128 fit and 32 calibration recordings, yielding 768 model-fit and 192 threshold-calibration recordings overall.
- Fix 80 normal+80 fault recordings from 06 in advance. Do not download or open 06 recordings before the final model is frozen.
- Continue excluding the old id_00 test set of 90 recordings. id_02 has explicitly become development data and cannot still be called a new test.
- Reuse existing recordings authorized for development first, then select additions in fixed hash order. Do not select data by model scores. All original recordings and derived data follow machine grouping.
- Verify data using ZIP-member CRC and local-PCM digests. Machine/file IDs alone cannot fully establish absence of near duplicates or acquisition-session independence. This iteration does not claim an exhaustive near-duplicate audit of added data.

## Three-Fold Development

Each fold uses 256 fit and 64 calibration recordings from each of two source machines, with all 320 recordings from the other machine used only for that fold's validation. Standardization is fitted only on fit data. Each source machine's normal calibration scores determine a threshold with empirical false positives ≤5%; use the higher threshold of the two. The held-out machine never sets the threshold.

Twelve predetermined candidates combine three representations—complete log-power spectrum, removal of overall spectrum level, and removal of local spectral baseline—with linear models at two regularization strengths, an RBF classifier, and 300-tree ExtraTrees. The spectrum uses 1024 samples and retains 512 non-DC bins.

Selection first minimizes the worst machine's violation of the three high-standard gates, then compares worst detection and mean AUC. The exact formula, fixed hyperparameters, and source digests are written into protocol.json before training. Reporting only a mixed three-fold average must not hide failure on a machine.

High-standard gates remain detection ≥90%, false positives ≤5%, and AUC≥0.90 for every held-out machine. Three-fold results are used for development selection and are not themselves an unbiased final performance estimate.

## Final Model and Test

After selection, fit the final model on the three machines' 768 fit recordings. The 192 calibration recordings determine only the final threshold; do not reuse them for model fitting while still claiming independent threshold calibration. The final threshold is the maximum of the three normal-calibration thresholds.

An independent audit reloads the selected three-fold models and checks that each held-out machine entered neither fitting nor calibration, standardization means derive from the correct fit recordings, and threshold calculations/predictions match. Then freeze source, parameters, threshold, manifest, and development results.

Evaluate 06 only once: detect at least 72/80 fault recordings, allow at most 4/80 normal false positives, and require AUC≥0.90. Under the predetermined plan, retain the final baseline's 06 confirmation even if development fails, rather than selectively suppressing failure. Do not adjust model or threshold after evaluation.

This iteration delivers software training and generalization evaluation without changing UPduino firmware.

## Leads for Additional Fan Data

- [Official MIMII DUE release](https://zenodo.org/records/4740355): six sections per machine type, roughly corresponding to products, with source/target condition shifts; fan development archive approximately 1.1 GB.
- [Official MIMII DG release](https://zenodo.org/records/6529888): three sections per machine type, roughly corresponding to domain-shift types; fan archive approximately 928.5 MB.

Sections must not directly be counted as additional independent machines. Machine identity, original recordings, and relationships among versions still require review before setting training/validation/test boundaries. This iteration only registered these two sources; it did not download, mix them in, or use them to replace the 06 test.
