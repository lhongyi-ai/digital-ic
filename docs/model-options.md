# Current Model and Upgrade Comparisons

The current model is a two-layer fully connected MLP trained from scratch: 16 neighbor-bin energy features → Linear(16,16) → ReLU → Linear(16,3). It has 304 weights and 19 biases, totaling 323 parameters. DSP first converts a raw 1024-sample waveform into 16 features; the network does not directly consume the raw waveform.

PyTorch training uses AdamW and class-weighted cross-entropy, learning rate 0.025, weight decay 1e-5, and seed 7. It runs 450 epochs and checks validation macro-F1 every ten epochs, selecting epoch 240. Floating-point validation macro-F1 at that epoch is 0.95041, falling to 0.91851 at epoch 450. The saved weights are from the better epoch 240; more training does not automatically improve results.

Deployment uses symmetric INT8 weights, nonnegative 0..127 activations, INT32 biases/numeric range, and explicit rounding/saturation rules. Actual RTL shares a physical 40-bit accumulator with DFT. The model uses PTQ, and current evidence does not identify quantization loss as the main bottleneck. Frozen-model test accuracy remains 93.18%; see the [original evaluation](neighbor-test-results.md).

## Limited comparisons actually run

The experiment fixed three configurations, seeds 7/17/29, and 450 epochs per run in advance: nine training runs total. All share the same neighbor-bin DSP, 16 features, frontend scales derived from training data, 0/1 HP training, and 2 HP validation. Test waveforms and predictions are not read. Every checkpoint is selected only by validation metrics. A/B additionally compute INT8 validation results with the same PTQ arithmetic; C has floating-point results only.

| Configuration | Hidden units | Learning rate / weight decay | Float validation macro-F1 mean ± sample standard deviation | Worst float result | INT8 validation macro-F1 mean ± sample standard deviation |
| --- | ---: | --- | ---: | ---: | ---: |
| A: existing training settings | 16 | 0.025 / 1e-5 | 94.82% ± 0.30 percentage points | 94.49% | 95.10% ± 0.13 percentage points |
| B: lower learning rate and stronger weight decay | 16 | 0.01 / 1e-3 | 93.93% ± 0.28 percentage points | 93.61% | 93.59% ± 0.47 percentage points |
| C: wider network with B's settings | 32 | 0.01 / 1e-3 | 94.51% ± 0.60 percentage points | 93.84% | Not quantized |

The experiment provides insufficient evidence to replace the current model. A/seed7 exactly reproduces the frozen model's floating-point and INT8 validation metrics. A/seed17 classifies only one additional validation window correctly in INT8; this did not prompt reselection of the deployed model or test-set access.

Limitations remain: B/C share optimizer settings, and C exceeds B's mean floating-point validation macro-F1 by about 0.575 percentage points. A/C change both width and training settings, so their difference cannot be attributed entirely to width. All three B runs select epoch 450; C selects 440/450/440. Conclusions therefore apply only to this training budget and do not establish full convergence. Standard deviations across three seeds reflect initialization variation, not independent-dataset error or generalization confidence intervals.

Experiment files: [protocol.md](../experiments/model_options/protocol.md), [run.py](../experiments/model_options/run.py), and [results.json](../experiments/model_options/results.json). They include nine checkpoints, per-epoch validation results, the 27 training/validation records actually read and their SHA256 values, and source/model snapshots. Existing models, ROMs, RTL, and historical reports remain unchanged.

## Directions worth investigating

1. **Improve features first.** An existing offline experiment used 16 FFT energy features covering wider frequency bands with the same-sized MLP and achieved floating-point validation macro-F1 of about 0.97287. This is a potential direction, but its floating-point FFT frontend differs from the current fixed-point selected-bin DFT. It is neither quantized nor deployed and cannot be presented as a direct replacement with 97% test performance. First investigate useful narrow bands or replace a few spectral features with mean-square/peak features while retaining 16 dimensions; benefits require offline validation.
2. **Check operating-condition stability.** Predefine validation groups by record or load within training/development records. Keep all bin selection and scale fitting within each fold's training portion, then compare training with amplitude changes, noise perturbations, and similar methods. Windows from one record must not be randomly spread across training and validation. Without independent bearing/machine data, do not claim cross-machine generalization. [scikit-learn grouped cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html#group-k-fold)
3. **Expand the hardware network only after showing a benefit.** A 16→32→3 network has 643 parameters and could continue time-sharing four multipliers. However, current RTL arrays, indices, biases, and layer scheduling are fixed-size; replacing JSON alone is insufficient. With the current three-cycle schedule, NN cycles are estimated to increase from 265 to about 525. This is not a synthesis or physical-board result.

The NN currently occupies only 265/77470 ≈ 0.342% of active processing cycles, while the complete four-MAC neighbor-bin design uses 5129/5280 LCs, leaving 151, plus 25/30 EBR and 4/8 DSP. Wider-network risks center on activation storage, selection logic, addressing, and routing margin rather than multiplication speed. Every deployment candidate requires new export, verification, and place-and-route; a small parameter count does not prove it will fit.

The next choice should follow training/validation evidence, INT8 consistency, and FPGA resources. Previously viewed 3 HP results remain historical evaluations. Using them for further tuning and reporting the same test again would leak test information into model selection. [scikit-learn validation and test-set guidance](https://scikit-learn.org/stable/modules/cross_validation.html)
