# MIMII acoustic prototype: implementation and validation on 2026-09-11

This iteration completed a hardware path from real recordings through FPGA DSP, an INT8 autoencoder, anomaly scoring, and consecutive-window alarms. **Algorithmic feasibility did not pass.** This report records implementation and limitations; `artifacts/evidence/current-status.md` remains the single project-status entry point.

## Dataset scope and split

The source is `0_dB_fan.zip` from the [official MIMII record](https://zenodo.org/records/3384388), restricted to fan/id_00, 0 dB, channel 0. Official WAVs are 16 kHz, eight-channel, 16-bit recordings approximately 10 seconds long. Locally, only channel-0 PCM is retained. No microphone, faulty fan, or external interface board is required.

Complete recordings are split by stable hash ordering, then divided into nonoverlapping 1024-sample windows: 156 windows per recording, discarding the final 256 samples. Training contains 120 normal recordings; validation contains 40 normal plus 30 abnormal; test contains 40 normal plus 50 abnormal. Training uses normal data only. Normal validation data selects the epoch and threshold; labeled validation data compares candidates. Test waveforms were not loaded for model evaluation at this stage.

`data/mimii/plan.json` fixes complete filenames, splits, and purposes. `download.json` records 280 successfully verified recordings. Selected members were fetched using the official ZIP index and HTTP Range: approximately 511 MB compressed data and approximately 90 MB local single-channel PCM, without downloading the entire 10.4 GB archive. ZIP CRC32 was checked per member, with original-WAV and local-NPY SHA256 recorded. **The complete archive MD5 was not verified.** Data is used under the official CC BY-SA 4.0 license; derivatives require retained licensing and attribution before publication. Bulk audio and its local acquisition records are retained locally where omitted from this publication.

This is a feasibility study for one machine ID and one SNR. Isolation by complete recording does not establish isolation across devices or independent acquisition sessions.

## Algorithm and observed problems

Data path: DC removal → 12-bit scaling/saturation → Hann window → 48 DFT components → 16 three-neighbor-bin powers → feature quantization → 16→8 ReLU → 16 reconstructed outputs → sum of 16 squared errors.

Four input variants combined uniform/geometric frequency layouts with linear/exponent-plus-two-mantissa-bit compression. Each was compared using centroid distance, diagonal Mahalanobis distance, and a small autoencoder. Compressed features are a fixed-point logarithm approximation, **not log-Mel spectra**. PyTorch trains the AE with input scale 1/128, INT8 weights, INT32 accumulation, RNE rounding, saturation to 0…127, and exported shifts/biases. Eight active hidden neurons use a 16-slot ROM layout to reuse the storage organization.

Validation metrics use the mean window score per recording. The threshold is fixed at the 95th percentile of normal validation recording scores, with a strictly-greater-than decision.

| Same validation set | AUC | Normal false-positive rate | Anomaly detection rate |
| --- | --- | --- | --- |
| Centroid distance, uniform linear features | 0.6383 | 5.0% | 26.7% |
| Diagonal Mahalanobis distance, uniform linear features | 0.6408 | 5.0% | 20.0% |
| INT8 AE, uniform linear features | 0.6533 | 5.0% | 13.3% |

The AE was selected as the hardware prototype by AUC; floating-point AUC was 0.6517. INT8 did not materially reduce AUC, but AE detection at this false-positive rate was below the distance baselines, so it cannot be called the better detector. Its confusion matrix was `[[38,2],[26,4]]`: rows are true normal/abnormal, columns predicted normal/abnormal. Predeclared AUC≥0.8 and detection≥0.5 gates were not met.

The board uses a separate temporal rule: per-window error strictly above 8722 for three consecutive windows triggers an alarm. A normal window, error, frame-ID discontinuity, or reset interrupts the count. Threshold 8722 is the 99th percentile of normal validation window scores. Using “any alarm during the recording” as the recording-level decision gives validation confusion matrix `[[37,3],[26,4]]`: 7.5% false positives and 13.3% detection. **This differs from mean-score ROC evaluation.** Raw results are in `artifacts/acoustic/validation.json` and `validation-alarm.json`.

`artifacts/acoustic/frozen.json` freezes the model, ROMs, split, validation results, reference code, and exported waveforms. This model is not retrained. The test set had not been evaluated at this historical stage and was not consumed merely to finish the task. The prototype validates implementation and is not an application release.

## RTL and validation

Added `rtl/core/acoustic_core.sv` and `rtl/upduino_acoustic.sv`, retaining the original CWRU RTL. Shared multipliers execute windowing, DFT, spectral power, neural-network operations, and reconstruction squared error. Outputs include frame ID, error, threshold, consecutive count, alarm, and per-stage cycles.

Flash reuses the protected partitions and VIB1/VLG1 transport, with a separate acoustic checker interpreting the 96-bit result as `[error,threshold,consecutive_count]`. The old CWRU checker must not interpret these results. `src/vibfpga/acoustic.py` is the bit-exact reference, and `acoustic_board.py` verifies readback. On-board Flash input/log exchange requires no USB serial adapter.

| Requirement | Executed check | Scope |
| --- | --- | --- |
| Fixed-point arithmetic | Zero, extrema, random, sine, and RNE/saturation fixtures | Both encodings, 1000 distinct N32 windows each, plus three reset-recovery windows |
| Real recordings | N1024, six validation-recording windows plus boundary inputs, 15 outputs total | One-MAC RTL bit-exact comparison |
| Intermediate values | Mean, 1024 windowed values, 48 real/imaginary values, 16 powers/features, eight hidden values, 16 output accumulations/reconstructions/squared errors | Exact comparison for real validation windows and both fixture encodings |
| Flow control/reset | Input stalls, concurrent input/output, 17-cycle output backpressure, resets during input/computation/blocked output | Stable output, cancellation of old transactions, recovery on the next frame |
| Python | All project tests | 236 passed, including split, integer reference, alarm, and corrupt-readback rejection |
| Physical board | Five-frame smoke test plus 1000-frame fixed-cadence replay | Two consecutive identical raw readbacks; every frame matched the integer reference |

Simulation reports: `build/acoustic/regression-log-final/core_l1/report.json`, `regression-linear-final/core_l4/report.json`, and `traced-final/core_l1/report.json`. N32 random stress cases are not 1000 independent real N1024 recordings. Omitted build evidence is retained locally.

## Physical-board results and resources

Board: UPduino 3.1, Flash EF4016, with the original 4 MiB backup retained locally. The one-MAC acoustic build used 4517/5280 LC, 1/8 DSP, 19/30 EBR, and 3/4 SPRAM after placement/routing. It met the 13.2 MHz constraint; estimated Fmax was 21.51 MHz. Internal HFOSC is nominally 12 MHz. **Physical frequency and power were not measured.**

The 1000 frames cyclically replay six real validation windows, with one input sample every 750 cycles, nominally 16 kS/s. Generated and accepted counts were both 1,024,000 samples; dropped samples, overflows, and protocol errors were all 0. All scores, thresholds, consecutive counts, and alarms matched bit-for-bit. Raw evidence is in `measurements/2026-09-11-acoustic/l1-1000/`, retained locally where omitted. This is not an accuracy evaluation of 1000 independent recordings.

| Stage | Cycles/window |
| --- | ---: |
| DC removal/windowing | 3073 |
| DFT | 295104 |
| Power/features | 358 |
| AE and reconstruction error | 848 |
| Total computation | 299383 |

At nominal clock, total computation is approximately 24.95 ms, below the 64 ms window interval. This excludes collecting a complete window and Flash readback. No four-MAC acoustic board speedup was measured; the old vibration project's 3.865× ratio cannot be reused. At this report's historical endpoint, the last programmed image was the acoustic L1 prototype; reset recognizes the completed log and does not overwrite it automatically.

## Reproduction entry points and remaining work

From the project root, load `source scripts/env.sh`.

- Data: `python scripts/prepare_mimii.py --download` supports verified resume and fetches only the fixed manifest.
- Training: `python scripts/train_acoustic.py` refuses to overwrite existing frozen results. New experiments require a separate version; do not delete the freeze to tune parameters.
- Module validation: `make module MODULE=acoustic` creates explicitly labeled arithmetic fixtures, runs 1000 windows for both encodings, and checks the real model. No training or USB operations.
- Python: `make python-test RUN_ID=acoustic-python`.
- Build: `python scripts/build_acoustic_board.py --run-id acoustic-v1`; builds only, without programming.
- Board replay: configure acoustic model/vectors in `scripts/prepare_replay.py`; `scripts/run_acoustic_hardware.py` defaults to preview. Existing physical-trial commands are recorded in manifests. New execution requires a new directory and explicit `--execute`, retaining backups and failure records.
- Status: `python scripts/collect_current_status.py`.

**The next priority was offline feature experiments.** Sparse bands are a plausible bottleneck to investigate, but the results do not establish a unique cause. Compare fuller-spectrum band energies/log-Mel and temporal context on the same train/validation split, and inspect channel, signal amplitude, and saturation before adding RTL. Retain distance baselines: a larger model is not automatically better, and network expansion needs supporting results. Redesign the approach and gates before one formal test-set evaluation.

Microphone experiments remain optional and unperformed. They can validate acquisition, replay, and domain differences, but do not automatically provide reliable fault labels. No additional components are needed at this stage. The new acoustic core has not undergone whole-core formal proof, an ASIC flow, a four-MAC placement/routing comparison, or full product-level anomaly-detection acceptance. Historical FIFO formal results do not replace these tasks. Because the algorithm missed feasibility gates, no complete release was declared and the old route's full release suite was not used as acoustic acceptance.
