# Official AudioSet-pretrained feature experiment

Feature extraction for 960 development recordings and nine training runs, three classifier heads × three held-out machines, are complete. The original high-standard gates were not met, and 06 was not accessed.

The experiment used mn10_as weights from the [official EfficientAT implementation](https://github.com/fschmid56/EfficientAT), described upstream as pretrained on AudioSet. The encoder was fixed; only source-machine normalization and classifier heads were fitted. This was not retraining on AudioSet, and target machines did not calibrate the model. The protocol and binding manifest record the upstream commit, weight digest, and code digests. Source attribution does not replace an exhaustive overlap audit of pretraining data.

A separate .venv-efficientat environment used torch/torchaudio 2.8.0 and torchvision 0.23.0 without changing the original project environment. Resampling 16 kHz recordings to the official 32 kHz input does not restore high-frequency content absent from the originals.

## All candidates

| Classifier head | Held-out machine | Detected/160 | False positives/160 | AUC |
|---|---|---:|---:|---:|
| linear_01 | 00 | 144 | 156 | 0.4289 |
| linear_01 | 02 | 73 | 91 | 0.4453 |
| linear_01 | 04 | 3 | 0 | 0.5658 |
| linear_1 | 00 | 139 | 151 | 0.4275 |
| linear_1 | 02 | 75 | 89 | 0.4500 |
| linear_1 | 04 | 5 | 0 | 0.5714 |
| rbf_10 | 00 | 156 | 157 | 0.4516 |
| rbf_10 | 02 | 110 | 118 | 0.4736 |
| rbf_10 | 04 | 3 | 0 | 0.5563 |

Verification passed for all nine heads' grouping, fit-set normalization means, source-calibration thresholds, reloaded scores, and independently computed metrics. This does not establish that the pretrained model suits industrial fault tasks; actual performance did not improve. Quantization/RTL deployment did not proceed.

This round evaluated only official mn10_as globally averaged embeddings with small classifier heads. It does not rule out every pretrained model or temporal resolution. However, failed mean-spectrum, temporal-descriptor, small-CNN, source-perturbation, and transfer-feature experiments do not support adding model complexity without evidence. The next step should examine data and task identifiability and verify the provenance of additional independent machine data.

Evidence: [protocol](../artifacts/acoustic-pretrained-v1/protocol.json), [all results](../artifacts/acoustic-pretrained-v1/results.json), [binding manifest](../artifacts/acoustic-pretrained-v1/bindings.json), and [audit](../artifacts/acoustic-pretrained-v1/audit.json). Omitted environments, upstream weight copies, and bulk audio remain local.
