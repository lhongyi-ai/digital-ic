# CNN normalization fix and source-machine perturbation experiment

The high-standard gates remain unmet; 06 was not accessed.

## Diagnosing reload differences

Saving the cache changed array memory layout, altering float32 mean-reduction order and causing small score differences. Restoring the original layout exactly reproduced predictions for all six v2 models, without decision changes. The original strict-audit failure record remains retained. This was distinct from corrupted weights.

A unified normalization routine now explicitly uses C layout, float64 mean and subtraction, then conversion to float32. Tests cover original layout, transposed layout, and save/reload, with exactly identical outputs.

## Fitting diagnosis

Training-set AUCs for v2 models retaining spectral information were 0.9906, 0.9151, and 0.9591, with substantially weaker cross-machine performance. Time-centered models had training AUC only 0.52–0.55. Training performance is diagnostic, not generalization evidence.

## v3 experiment

The experiment retained whole-machine grouping, 60 epochs, the same network, and source-calibration rules. Only normal source-machine recordings with the fit role estimated the difference between the two machines' mean frequency profiles. Each training sample was perturbed by that difference multiplied by a random coefficient in [-1,1]. Target machines did not fit perturbations or thresholds.

| Held-out machine | Detected/160 | False positives/160 | AUC |
|---|---:|---:|---:|
| 00 | 156 | 155 | 0.5705 |
| 02 | 82 | 55 | 0.6028 |
| 04 | 6 | 0 | 0.8471 |

All three models reproduced scores exactly after reload in separate processes. Checks of source-perturbation direction, grouping, calibration thresholds, independent AUC, and counts passed. False positives/missed faults remained severe, so model acceptance cannot be claimed.

Evidence: [reload diagnosis](../artifacts/acoustic-cnn-v2/layout-diagnostic.json), [v3 results](../artifacts/acoustic-cnn-v3/results.json), and [v3 audit](../artifacts/acoustic-cnn-v3/audit.json).

Subsequent work should assess transferable pretrained acoustic representations and additional machine data with clear source relationships, rather than rely only on training networks from scratch on the current small sample. Any new final confirmation requires data excluded from development. 06 cannot select models or tune thresholds again.
