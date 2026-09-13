# Data, Fixed-Point Models, and Reproducible Experiments

The current artifacts include a genuinely trained three-class CWRU model and an integer reference aligned with handwritten RTL. Public-data replay does not establish fault recognition on a real deployed machine. The normal class is excluded; class order is fixed to `0 inner_race`, `1 outer_race`, and `2 ball`.

## Data eligibility and splits

Data comes from the [official CWRU 12k Drive End Bearing Fault Data table](https://engineering.case.edu/bearingdatacenter/12k-drive-end-bearing-fault-data). Only the DE channel, 0.007/0.014/0.021-inch faults, and the outer-race @6:00 position are used. The 36 MAT files reside in `data/cwru/`; `manifest.json` records each original URL, SHA256, exact MAT variable, sample count, load, and sampling-rate source. Sampling rates come from the official table; no sampling-rate field is assumed to exist in the MAT files. Normal recordings are excluded because a reliable source for each file's original sampling rate was not established; they were not silently resampled.

| Class | 0.007 inch: 0/1/2/3 HP | 0.014 inch: 0/1/2/3 HP | 0.021 inch: 0/1/2/3 HP |
| --- | --- | --- | --- |
| Inner race | 105/106/107/108 | 169/170/171/172 | 209/210/211/212 |
| Outer race @6:00 | 130/131/132/133 | 197/198/199/200 | 234/235/236/237 |
| Ball | 118/119/120/121 | 185/186/187/188 | 222/223/224/225 |

Complete records are split first, then divided into 1024-sample windows with a 1024-sample hop. Loads 0/1 HP form training (18 records, 2134 windows); 2 HP forms validation (nine records, 1066 windows); 3 HP forms a single held-out test (nine records, 1070 windows). Incomplete trailing windows are discarded and recorded. No overlapping windows cross splits, and no records are silently removed because of unusual waveforms or incorrect predictions.

The common PCM16 input gain is `32700 / maximum_absolute_sample_in_training_records`. Validation and test use the same gain; all three splits currently have zero clipped samples. DC removal uses each window's own mean, which can be calculated during deployment without statistics from the entire test recording.

The downloader parses all files in advance to check integrity, variables, and quality; these test-record statistics were not used to select models, bins, or scales. The training script freezes the model and writes SHA256 before loading test waveforms for inference. If `test_evaluation.json` exists, the script refuses to overwrite it or evaluate again.

## From floating-point training to integer RTL

The processing chain is PCM16 → per-window mean removal → right shift by five and saturation to signed 12 bits → Q14 periodic Hann → 16 selected DFT bins → sum of squared real/imaginary components → per-feature power-of-two scaling → 16→16→3 MLP. The deployed frontend is a selected-bin DFT; the offline FFT band-energy comparison is not presented as deployed functionality.

All specified right shifts use round-to-nearest, ties-to-even: both positive and negative half-integers round to the nearest even integer. Saturation locations are explicit. DFT accumulators are signed 40-bit, real/imaginary outputs signed 16-bit, and energy unsigned 32-bit. Exact formulas are in `implementation-contract.md` and `src/vibfpga/fixed.py`.

PyTorch training uses floating-point weights. Inputs are energies from integer DSP, transformed by feature scales determined on training data and represented as floating-point values for the network. Weights use symmetric per-layer quantization, zero point 0, and power-of-two scales, with range [-127,127]. First-layer bias units are `input_scale × w1_scale`; second-layer units are `hidden_scale × w2_scale`. Hidden-layer ReLU, RNE right shift, and saturation produce [0,127]. The three int32 logits share one scale and feed a direct argmax, with ties resolved to the lower class index. Logits are not probabilities.

Python, exported ROMs, and SystemVerilog jointly define this custom quantized arithmetic. No framework's built-in INT8 operator is assumed automatically equivalent to the custom RTL. If PTQ loses more than two percentage points on validation, the script attempts custom QAT with fixed scales and STE. Current PTQ meets the criterion; QAT code was not used for the final model.

## Completed model comparisons

Training data selects scales and candidate Fisher bins. Validation selects among uniform, logarithmic, and train-only Fisher sets of 16 bins, and selects the training epoch. A separate 16-band energy model was trained for offline comparison; it sums more bins and does not participate in current RTL model selection.

Selected DFT bins: `80,177,188,207,300,308,315,321,328,339,346,355,439,451,457,469`. Each corresponds to `bin × 12000 / 1024 Hz`. Selection takes the deployable candidate with the highest validation macro-F1. All candidates use seed 7 and a 450-epoch budget. The final setting is `hidden_shift=8`.

The frozen v1 actually used validation to choose the bin-selection strategy, deviating from the original requirement that all bin selection use training data only. Historical reports and models retain that record. For future experiments, the corrected training script fixes the train-only Fisher-separated algorithm before fitting models; other bin strategies are comparisons only, while validation can still select epochs. The winning v1 strategy happened to be Fisher, so the corrected rule yields the same centers. No retesting was used to rewrite v1 history.

| Method | Held-out test accuracy | Held-out test macro-F1 |
| --- | ---: | ---: |
| Three-leaf RMS threshold tree | 77.10% | 76.17% |
| Linear model on the same 16 features | 76.92% | 77.18% |
| Floating-point MLP | 76.45% | 76.81% |
| Deployed INT8 MLP | 76.82% | 77.13% |

Validation accuracy changed from 88.37% floating-point to 87.15% PTQ, a loss of 1.22 percentage points. INT8 held-out test accuracy was about 0.37 percentage points higher than floating-point. This describes only this experiment, not a general benefit of quantization. **The MLP did not outperform the RMS/linear baselines.** These results support a demonstration of hardware implementation and quantization correctness, not a claim of superior recognition performance.

These are cross-load/record tests on one public test rig. Different records may come from the same damaged specimen, so they do not establish performance on unseen bearings, machines, or field conditions. The 1070 windows are not 1070 independent bearing experiments. Actual ADXL345 operating data should form a separate dataset with separate training and evaluation; CWRU sampling rates, bins, and accuracy cannot simply be transferred.

## Predefined three-neighbor-bin comparison: training/validation only

An additional comparison retained the same 16 centers and used three DFT bins `k-1,k,k+1` per group. Each bin uses the same Q14 coefficients, 40-bit accumulation, RNE, sat16, and real/imaginary squared sum. Its three energies are then summed in an unsigned temporary of at least 34 bits, before feature scaling and quantization. The 48 DFT bins still produce 16 features, so the MLP size is unchanged. New feature scales use training records only; the budget remains seed 7 and 450 epochs.

Candidate validation accuracy was **95.03%** floating-point and **95.12%** INT8; validation macro-F1 was **95.04%** floating-point and **95.12%** INT8. Floating-point validation macro-F1 improved by **6.90 percentage points** relative to the single-bin version; PTQ validation accuracy loss was **-0.094 percentage points**. The candidate met the predefined requirements of at least 2 pp higher validation macro-F1 and no more than 2 pp PTQ accuracy loss. This feature comparison did not reevaluate the test set: 95.12% always refers to validation. The subsequent independent evaluation of the frozen model is described below.

The centers were also independently recomputed from training waveforms with the predefined Fisher-separated algorithm and asserted equal to those above. The script and experiment report record the method; validation was not used to select the center strategy again. This check neither refitted the candidate nor accessed the test set.

The candidate is saved separately in `artifacts/model_neighbor`, with nine validation replay vectors in `artifacts/vectors_neighbor`; the original single-bin model and test report remain intact. `feature_mode=neighbor3_energy`; `bins[16]` contains the centers, and `dft_bins[48]` and `dft_bins.hex` list k-1/k/k+1 for each center. Python returns 48 values for real, imag, real_acc, imag_acc, and dft_powers, and 16 for powers/features. The candidate requires matching 48-bin RTL, resource checks, and timing checks; replacing weights in a single-bin bitstream is insufficient. Its FPGA implementation status is defined by actual build/verification evidence in `artifacts/evidence`.

## Subsequent testing after freezing the neighbor-bin model

The same candidate model and evaluation protocol were frozen. After writing `freeze.json`, the 3 HP test records were loaded once, covering all nine records and 1070 nonoverlapping windows. There was no retraining, bin selection, quantization-scale adjustment, or window filtering. INT8 accuracy was **93.18%**, macro-F1 **0.93236**; floating-point network accuracy was **92.90%**, macro-F1 **0.92964**. Quantization changed predictions on 13 windows: five correct predictions became incorrect and eight incorrect predictions became correct. The net gain of three correct results in this experiment does not establish that quantization generally improves a model.

The floating-point reference matches the original validation contract: inputs are integer-DSP powers converted with frozen scales before feature rounding, and network weights are the saved FP32 parameters. It is not a fully floating-point DSP frontend. The per-window integer reference matched the batched implementation element for element across all 1070 windows. This is a software numerical check; separate evidence covers the thousand-frame RTL and dedicated DSP regressions.

These 3 HP records were previously used for the original single-bin model, so they are not a new, never-accessed external test set. Nor are their windows 1070 independent bearing or field experiments. The original model, candidate parameters, and earlier reports remain unchanged; the new report links to the model by SHA256. `test_evaluated=false` in the model JSON and original neighbor-bin comparison report retains its historical meaning; this section and the separate evaluation report describe the later status.

Full results: [neighbor-bin test report](neighbor-test-results.md) and `artifacts/reports/neighbor_test/`. `python scripts/evaluate_neighbor.py --verify` checks frozen input/output hashes, per-window data, and metrics read-only, without reading MAT files or running inference. `--evaluate` refuses to overwrite an existing evaluation directory; repeated inspection of the same test set must not guide parameter adjustment.

## Reproduction from the project root

With an existing `.venv` and local OSS CAD Suite, use the following commands. None writes to hardware.

```sh
export PYTHONPATH="$PWD/src"
export PATH="$PWD/.tools/oss-cad-suite/bin:$PATH"
.venv/bin/python -m pytest tests --junitxml=build/python-results.xml -q
.venv/bin/python sim/run_flash_system.py
.venv/bin/python scripts/collect_evidence.py
```

Retrieve data again from official sources:

```sh
.venv/bin/python scripts/download_cwru.py --directory data/cwru
```

A cached-file SHA256 mismatch raises an error rather than automatically overwriting the file. Reauditing updates the manifest timestamp, so new experiments should record their own manifest hash. The frozen experiment can currently be checked without downloading or training again.

To verify reproducibility, create a new, explicitly named experiment directory and retain the original experiment. The command below actually retrains, selects, and evaluates once; different results must not trigger repeated test-set inspection for tuning.

```sh
.venv/bin/python scripts/train_export.py --data data/cwru --artifacts experiments/reproduction-001 --epochs 450 --seed 7
```

Model/vector interface: `classify(samples, model)` accepts `[1024]` integer samples and returns mean, centered, scaled, windowed, real/imag, real_acc/imag_acc, powers, features, hidden_acc, hidden, logits, and class_id. Every `artifacts/vectors/replay_*.json` stores complete intermediate values and record/window provenance. The nine replay vectors come from validation, one window per validation record. `artifacts/fixtures` uses deterministic weights explicitly marked untrained, solely for fixed-point boundary tests.

`artifacts/model/` retains full Hann and quarter-wave Hann/cos ROMs, original neuron-major weights, and L1/L4 bank files. `model.json` defines scales and class order. `artifacts/reports/` retains selection, freeze, test predictions, and confusion matrices; `artifacts/evidence/` stores summaries of actual reports and the current tool/source snapshot. Hardware measurements without evidence are not automatically marked as passing in the summary.
