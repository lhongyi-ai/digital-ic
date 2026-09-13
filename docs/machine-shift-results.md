# Machine-Shift Diagnosis and Source-Variation Removal

This round completed 18 same-machine fault-diagnosis models, three machine-identity models, and 27 folds of variation-removal training. The high cross-machine standards remain unmet; 06 was not revisited.

## Same-machine controls

Fixed development data was reassigned to 192 fit, 32 normal-calibration, and 64 validation recordings per machine, with 32 normal/32 faulty validation examples. Same-machine validation diagnoses feature usefulness but does not replace cross-machine acceptance. The sample is small and has previously participated in development; this is not a new test.

Mean spectrum plus a linear model:

| Machine | Detected /32 | False positives /32 | AUC |
| --- | ---: | ---: | ---: |
| 00 | 28 | 2 | 0.9014 |
| 02 | 32 | 3 | 1.0000 |
| 04 | 32 | 0 | 1.0000 |

The same spectra identify machine identity with 100% accuracy on held-out development recordings (192/192); temporal features achieve 73.4%. Combined with whole-machine holdout failure, this supports machine differences as an explanation for limited generalization. It does not establish causal contributions from specific noise, product models, or fault mechanisms.

## Variation-removal experiments

Using only normal recordings assigned the fit role on source machines in each fold, the method learns either the direction between two normal-machine means or the first 4/16 principal components of normal data, then subtracts those projections from full spectral-shape features. The validation machine does not participate in projection, standardization, or threshold fitting. Three transforms and three models give nine approaches and 27 folds.

Selected approach: pc16-rbf_10. No candidate passed on all three machines.

| Held-out machine | Detected /160 | False positives /160 | AUC |
| --- | ---: | ---: | ---: |
| 00 | 151 | 135 | 0.6347 |
| 02 | 148 | 141 | 0.6845 |
| 04 | 32 | 3 | 0.9139 |

Additionally, pc4-rbf_10 reaches AUC 0.9571 on 04 but detects only 18/160 with 0/160 false positives at the fixed source-calibrated threshold. This illustrates a mismatch between score ranking and the fixed operating point; selecting that AUC alone cannot establish success.

All 27 models were audited: projections were recomputed only from source-fit normal data; grouping was correct; source-calibrated thresholds, serialized predictions, and independent metrics agreed. Original baseline and 06 results remain intact.

The next step requires models that retain finer time-frequency structure and train against machine differences. Any new version's final acceptance also requires new independent confirmation data. Same-machine diagnostics, development-set selection, or high AUC on one machine do not complete the original cross-machine objective.

Evidence: [same-machine diagnosis](../artifacts/acoustic-machine-shift-v1/results.json), [all variation-removal candidates](../artifacts/acoustic-source-invariant-v1/results.json), and [variation-removal audit](../artifacts/acoustic-source-invariant-v1/audit.json).
