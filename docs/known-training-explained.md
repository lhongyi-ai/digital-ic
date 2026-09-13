# How the current model is trained and deployed to UPduino

The current deployment model is **supervised logistic regression with one parameter set per installed fan**: 512 spectral input features produce one fault score. Development experiments found that retaining spectral detail helped more than enlarging the network, so the final choice was a linear model with simpler computation and interpretation.

## Data and task

The source is original MIMII fan data at 0 dB for machine IDs 00, 02, 04, and 06. Each recording originally has eight channels; this project fixes channel 0 at 16 kHz. The task distinguishes normal recordings from labeled faults on these covered devices. It does not recognize unfamiliar fans and has not established recognition of unseen fault types.

Complete recordings are split before windowing. A recording never appears in both training and validation. Each machine has 192 CV-development recordings, 96 normal and 96 faulty, rotating through three folds. Every development recording receives exactly one prediction from a model that did not train on it. Separate normal recordings are used only to set the alarm threshold: 160 for 00 and 32 for each other machine. The final held-out set contains 100 normal and 80 faulty recordings per machine, 720 total.

Final models are refit using each machine's complete set of 192 CV recordings. The earlier 256 additional training recordings for 00 were not used by the selected route; failed experiments are retained. The final 720 recordings are reserved for a single confirmation after parameters, RTL, and firmware are frozen. They cannot select bins, models, scales, or thresholds.

## Turning one recording into 512 numbers

1. Take the first 159744 samples and divide them into 156 nonoverlapping 1024-sample windows, totaling 9.984 seconds.
2. Remove DC, apply a Hann window, and compute full-DFT bins 1 through 512 in every window. Excluding DC, these bins cover 15.625 Hz through 8 kHz at the dataset's 16 kHz sample rate.
3. Compute real squared plus imaginary squared for each bin, average across 156 windows, and take log2. This produces a 512-dimensional spectral-power vector per recording.
4. Normalize using means and standard deviations computed from training recordings, preventing a bin from dominating solely because of its scale. Validation, calibration, and final-test statistics do not fit these parameters.

These features describe the recording's overall spectral energy distribution without preserving exact impact times. This is not an implemented complex temporal network or envelope diagnostic.

## What training optimizes

The model learns 512 weights and one bias, with score `s = w·x + b`. During training, logistic regression maps the score to normal/fault probability, minimizes classification loss, and adds an L2 weight penalty. This project fixes C=1, max_iter=3000, and seed=71. Training runs on a computer using NumPy and scikit-learn.

Each machine has its own weights because normal spectra differ. The installed device ID must be specified at runtime; the same FPGA circuit is programmed with the corresponding parameters. It does not automatically identify which fan is connected.

The threshold uses only normal calibration scores, under a fixed finite-sample quantile rule with alpha=0.04. For 00 it selects the 155th of 160 ordered scores; for other machines it selects the maximum of 32. A fault is reported only when score strictly exceeds threshold. This rule cannot guarantee false positives below 5% on every finite test set or compensate for changed acquisition conditions.

## Quantization and hardware deployment

Weights and input features are mapped to signed INT8, while bias and classification accumulation use INT32. Training data determines parameter scales. Exported tables include weights, biases, normalization coefficients, thresholds, cosines, and log2.

The FPGA does not run the training program. SystemVerilog describes the arithmetic circuit, and parameter tables are written to on-board Flash with the configuration bitstream. After power-up, the FPGA independently performs raw-PCM DC removal, windowing, DFT, power accumulation, logarithm, normalization, and classification. The host only supplies raw samples and reads results; precomputed features must not be presented as on-board signal processing.

Four 16-bit multipliers are shared over time for windowing, DFT, decomposed squaring, normalization, and INT8 classification MACs. The one-MAC version uses the same algorithm and numerical rules. All rounding is nearest, ties to even, with negative-value and saturation handling. Python integer references are compared bit-for-bit with RTL intermediate results.

One recording produces one score. The four-MAC version passed fixed-cadence simulation at nominal 16 kS/s; it does not update an alarm every 64 ms. The one-MAC baseline computes the same algorithm more slowly, and its throughput limits must be reported explicitly. Actual HFOSC frequency remains unmeasured; time converted using 12 MHz is nominal only.

## Interpreting overfitting and AUC=1

AUC=1 means every faulty recording in that evaluation scored above every normal recording. It does not guarantee zero false positives at a fixed threshold or 100% field accuracy. Temporary shuffled-label control models gave AUC approximately 0.48–0.51: the control returned to chance, rather than the formal model degrading.

This control still cannot rule out exploitation of background noise or acquisition batches. Repeated development-set comparisons make final held-out testing essential. Even a passing final test remains limited to four known devices, one noise condition, and unverified acquisition-batch independence. Every machine must separately meet detection >90%, false positives <5%, and AUC≥0.9; pooled averages cannot hide a failing device.

Final-test and physical-board results are recorded separately. Simulation, development performance, and actual programming are distinct evidence. The entry point is `artifacts/evidence/current-status.md`; the detailed numerical contract is `docs/known-integer-deployment.md`.

Learning and presentation resources: [playable per-recording walkthrough](../artifacts/known-recording-walkthrough/index.html), [stepwise numerical-to-RTL mapping](known-recording-walkthrough.md), and [architecture diagram, performance tables, and interview debugging examples](known-interview-pack.md). Audio omitted from the publication is retained locally.
