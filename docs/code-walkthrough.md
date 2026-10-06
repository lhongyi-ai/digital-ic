**Understand Python, the quantized model, and RTL by following a real validation frame**

This walkthrough follows the previously exported `artifacts/vectors_neighbor/replay_000.json`. It does not select new test samples or retrain the model. The pipeline converts 1024 vibration samples into 16 frequency-domain features, then uses a 16→16→3 neural network to predict a fault class. The integer values below were recomputed with `scripts/trace_frame.py`: all 15 intermediate-result fields in the JSON matched, and all 15 exported coefficient, weight, and bias ROM files were checked.

These values are **Python reference results from real CWRU data**. Separate RTL simulation reports establish agreement between the implementation and reference. They are not physical UPduino measurements or data from a newly connected sensor. The current classes are inner-race, outer-race, and rolling-element faults; there is no normal class. These results do not establish household-fan fault recognition.

**Start with three concepts.** Python prepares data, trains and quantizes the model, and generates reference answers. SystemVerilog is the language used to describe this project's RTL. RTL describes registers, memories, multipliers, and data movement on each clock. Synthesis converts synthesizable SystemVerilog into a circuit, and place and route produces an FPGA configuration file. The UPduino runs the configured circuit; it does not interpret Python or SystemVerilog source code inside the chip.

The configuration here is `N=1024, LANES=4, BANDS=3, HIDDEN_SHIFT=8`, with the model in `artifacts/model_neighbor`. `BANDS=3` means each feature sums the energy of a center bin and its immediate neighbors.

```text
1024 int16 samples
    → mean removal, scaling, Hann window
    → 48 selected DFT bins, each with real and imaginary components
    → energy summed in groups of 3 bins, producing 16 features
    → 16 quantized features in 0..127
    → W1[16×16] × features[16×1] + b1 → ReLU, quantization
    → W2[3×16] × hidden[16×1] + b2
    → 3 integer logits → class with the largest value
```

| Level of understanding | File and entry point | Hardware behavior |
|---|---|---|
| Complete integer inference | [fixed.py](../src/vibfpga/fixed.py), `classify()` → `frontend()` → `infer()` | Bit-exact reference for the entire calculation |
| One frame's input and answers | [replay_000.json](../artifacts/vectors_neighbor/replay_000.json) and the adjacent `.hex` | HEX supplies input; JSON retains intermediate values and provenance |
| Fixed model parameters | [model.json](../artifacts/model_neighbor/model.json) | Bins, shifts, weights, biases, and class order |
| Arithmetic and scheduling | [vibration_core.sv](../rtl/core/vibration_core.sv) | Double input buffers, state machine, and shared multipliers |
| Coefficient storage | [vib_coeff_rom.sv](../rtl/core/vib_coeff_rom.sv) | Synchronous quarter-cycle ROM reads and quadrant reconstruction |
| Implementation correctness | [test_core.py](../sim/test_core.py), `check_debug()` and `receive()` | Intermediate values, logits, handshakes, stalls, and resets |

**Step 1: Where do the 1024 samples come from?** The source is `107.mat` from the official CWRU 12 kHz Drive End dataset, using the exact MAT field `X107_DE_time`. It belongs to validation, has a 2 HP load, and contains a 0.007-inch inner-race fault. Zero-based `window_index=2` selects `[2048:3072]`: 1024 samples from indices 2048 through 3071, approximately `[0.170667, 0.256000)` seconds. Source, window, and label are recorded in the vector's `provenance`; the label is not a hardware input.

In `dataset.py`, `fit_raw_scale()` determines input gain using training records only. `load_windows()` converts the original floating-point samples to int16:

```text
gain = 4915.122577220299
raw[n] = clip(RNE(original[n] × gain), -32768, 32767)
```

RNE means round to nearest, ties to even, including negative values. The first original value is `-0.02940075848303393`, becoming `raw[0]=-145`, represented by `ff6f` in 16-bit two's-complement HEX. HEX decoding must restore signed values rather than treating `ff6f` as positive 65391.

The walkthrough run also verified the local `107.mat` SHA256 and extracted this window again. All 1024 rescaled samples matched the exported HEX. That check accessed only this validation record.

```text
107.mat SHA256:
111ba8996a115684661a13c913bd74d8029a59294492f88aec7b03e175fdd388
model_neighbor/model.json SHA256:
12abcdfd4a9072903915135e771c1fb9be0d430275e28acbf545660e1d7fa117
replay_000.hex SHA256:
b657431bcf0c4d96873c74c91334b1338a0ac2053d96768bfddbc91227f136b7
```

RTL accepts a sample only when `in_valid && in_ready`, while accumulating `input_sum`. The last accepted sample must also assert `in_last=1`. A complete frame and its sample sum occupy one of two input buffers. `full` indicates that a frame has arrived; `busy` indicates that preprocessing is reading it. Only an available buffer can accept the next frame. The model does not receive all 1024 samples simultaneously over 1024 buses.

**Step 2: Remove DC, scale, and window.** Python uses `frontend()`; RTL uses `PRE_MEAN` followed by repeated `PRE_READ → PRE_MUL → PRE_STORE`.

```text
sum(raw) = 20020
mean = RNE(20020 / 1024) = RNE(19.55078125) = 20
centered[n] = raw[n] - 20
scaled[n] = sat12(RNE(centered[n] / 32))
hann_q14[n] = RNE((0.5 - 0.5 × cos(2πn/1024)) × 16384)
windowed[n] = sat12(RNE(scaled[n] × hann_q14[n] / 16384))
```

`sat12` clamps to `[-2048,2047]`; the temporary mean-subtracted value needs at least 17 bits. Coefficients are scaled by `2^14`, and the product is shifted right by 14 to restore scale. The Hann window reduces spectral leakage from finite-window extraction. It changes signal amplitude, so subsequent fixed-point normalization must match the training reference.

| Sample index n | raw | centered | scaled | Integer Hann coefficient | scaled×Hann | windowed |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | -145 | -165 | -5 | 0 | 0 | 0 |
| 1 | -1123 | -1143 | -36 | 0 | 0 | 0 |
| 2 | 325 | 305 | 10 | 1 | 10 | 0 |
| 64 | 4063 | 4043 | 126 | 624 | 78624 | 5 |
| 128 | -1569 | -1589 | -50 | 2399 | -119950 | -7 |
| 256 | 1314 | 1294 | 40 | 8192 | 327680 | 20 |
| 511 | 4077 | 4057 | 127 | 16384 | 2080768 | 127 |
| 512 | 4241 | 4221 | 132 | 16384 | 2162688 | 132 |
| 768 | 1424 | 1404 | 44 | 8192 | 360448 | 22 |
| 1023 | -1415 | -1435 | -45 | 0 | 0 | 0 |

For n=64, RNE turns `4043/32` into 126. Multiplication by 624 gives `78624/16384≈4.7988`, rounded to 5. `PRE_READ` reads the sample and Hann ROM; `PRE_MUL` uses multiplier lane 0; `PRE_STORE` rounds, saturates, and writes `windowed` RAM. The raw input buffer can be reused after preprocessing because DFT reads the separate windowed buffer.

**Step 3: Compute 48 selected frequency bins.** Python uses `coefficients()` and integer dot products in `frontend()`. RTL uses `DFT_INIT → (DFT_READ → DFT_MUL → DFT_ACC)×1024 → DFT_STORE`. This is a selected-bin DFT, not a full 1024-point FFT.

For bin k, let `p=(k×n) mod 1024`:

```text
C[p] = RNE(cos(2πp/1024) × 16384)
S[p] = RNE(-sin(2πp/1024) × 16384)
real_acc[k] = Σ windowed[n] × C[p]
imag_acc[k] = Σ windowed[n] × S[p]
real[k] = sat16(RNE(real_acc[k] / 2^20))
imag[k] = sat16(RNE(imag_acc[k] / 2^20))
P[k] = real[k]^2 + imag[k]^2
```

The accumulators are 40 bits. The 20-bit shift is this implementation's scaling contract and cannot simply be replaced by a floating-point FFT library's default normalization. RTL generates negative sine from a cosine ROM using a phase offset: imaginary phase begins at `N/4`, increases by k per sample, and uses `cos(θ+π/2)=-sin(θ)`. Each lane stores only a quarter cycle and restores other quadrants and signs. Axis endpoints receive exact logic treatment.

The first feature centers on k=80 and computes bins 79, 80, and 81. Bin spacing is 12 kHz/1024=11.71875 Hz.

| k | Frequency, Hz | real_acc | imag_acc | real | imag | P[k] |
|---:|---:|---:|---:|---:|---:|---:|
| 79 | 925.78125 | -4432855 | -297955 | -4 | 0 | 16 |
| 80 | 937.5 | 5133458 | -2840598 | 5 | -3 | 34 |
| 81 | 949.21875 | -5052589 | 4667455 | -5 | 4 | 41 |

For k=80, `5²+(-3)²=34`. Its windowed sample at n=64 is 5 and `p=(80×64) mod 1024=0`, contributing `5×16384=81920` to the real accumulator and 0 to the imaginary accumulator. The table gives the sum across all 1024 samples.

**Step 4: Reduce 48 bins to 16 neighboring-bin energies and quantize.** Python's `neighbor3_energy` branch expands each center to `[k-1,k,k+1]`, runs integer DFT, and sums each group of three. RTL squares values using multiplier lane 0 in `POWER_RE_MUL/ADD` and `POWER_IM_MUL/ADD`; `band_sum` accumulates the three bins.

```text
E[j] = P[center[j]-1] + P[center[j]] + P[center[j]+1]
q[j] = clamp(RNE(E[j] / 2^feature_shifts[j]), 0, 127)
```

Neighboring bins here mean **one bin on each side of the same center**, not 16 equal bands across all positive frequencies. Selected centers and scaling come from the frozen model; inspecting this frame does not change them. The energy sum is not divided by three.

| Feature j | Center bin | Three-bin energy E | Right shift | Integer feature q |
|---:|---:|---:|---:|---:|
| 0 | 80 | 91 | 2 | 23 |
| 1 | 177 | 25 | 0 | 25 |
| 2 | 188 | 54 | 2 | 14 |
| 3 | 207 | 103 | 5 | 3 |
| 4 | 300 | 1078 | 9 | 2 |
| 5 | 308 | 1499 | 8 | 6 |
| 6 | 315 | 712 | 6 | 11 |
| 7 | 321 | 1825 | 6 | 29 |
| 8 | 328 | 106 | 6 | 2 |
| 9 | 339 | 208 | 3 | 26 |
| 10 | 346 | 112 | 2 | 28 |
| 11 | 355 | 22 | 2 | 6 |
| 12 | 439 | 49 | 3 | 6 |
| 13 | 451 | 7 | 4 | 0 |
| 14 | 457 | 4 | 2 | 1 |
| 15 | 469 | 4 | 0 | 4 |

The first entry is `16+34+41=91`, with `91/4=22.75` rounding to 23. The third has `54/4=13.5`, rounding to even 14; the twelfth has `22/4=5.5`, rounding to 6. RTL performs serial shifts in `POWER_Q_INIT → POWER_Q_SHIFT → POWER_QUANT`, using guard/sticky bits for identical RNE before clamping to 127. Although q is stored in an 8-bit container, its range is 0 through 127. Its neural-network real-value scale is `q/128`. These energies are not physically calibrated PSD in mg²/Hz.

**Step 5: First-layer 16×16 matrix-vector multiplication.** Python uses `hidden_acc = w1 @ x + b1` in `infer()`. `w1[output_neuron][input_feature]` means each row contains one hidden neuron's 16 weights; do not reverse rows and columns.

```text
q = [23,25,14,3,2,6,11,29,2,26,28,6,6,0,1,4]
W1 row 0 = [2,-6,-40,4,35,14,15,4,2,23,10,15,18,48,29,19]
Products = [46,-150,-560,12,70,84,165,116,4,598,280,90,108,0,29,76]
Dot product = 968
b1[0] = 6
hidden_acc[0] = 968+6 = 974
hidden[0] = clamp(RNE(max(974,0)/256),0,127) = 4
```

All 16 accumulator results and hidden outputs are:

```text
hidden_acc = [974,4241,-1135,584,-1126,2052,4882,-456,
              4542,909,-2459,104,-539,-805,-953,470]
hidden     = [4,17,0,2,0,8,19,0,18,4,0,0,0,0,0,2]
```

ReLU maps negative values to zero, such as neuron 2's -1135. Even positive 104 rounds to zero after division by 256. Python checks that neural-network accumulator values fit int32; RTL reuses 40-bit accumulators and checks int32 overflow in `NN_STORE`.

Why shift by eight? Input scale `1/128` times first-layer weight scale `1/16` gives accumulator scale `1/2048`; hidden scale is `1/8`. Their ratio is 256. Thus `HIDDEN_SHIFT=8` follows the exported quantization scales and must not be changed arbitrarily.

**Step 6: Second-layer 3×16 matrix-vector multiplication.** This layer also computes a weight-row dot product, without ReLU or softmax.

| Output class | `W2[class]·hidden` | b2 | logit |
|---|---:|---:|---:|
| 0: inner_race | 2147 | -5 | 2142 |
| 1: outer_race | -712 | -170 | -882 |
| 2: ball | -4649 | 244 | -4405 |

The output is `logits=[2142,-882,-4405]`, with the maximum at index 0, so `class_id=0`. This prediction matches the validation window's known inner-race label. All logits share scale `1/256`, enabling direct integer comparison; they are not probabilities. RTL chooses the largest in `FINISH`, breaking ties toward the smaller index, then enters `HOLD` until `out_valid && out_ready`. Logits, class, and cycle counts must remain stable during output stalls.

**How four hardware lanes perform these operations.** `LANES=4` creates four signed 16-bit×16-bit multiply paths that FPGA synthesis can map to four DSPs. Hann, DFT, power squaring, and both neural-network layers share them over time; there is not a separate multiplier set per algorithm stage.

For the first four hidden neurons, `NN_INIT` loads biases `[6,341,-604,-16]`. When `nn_input=0`:

| State | Four-lane activity |
|---|---|
| `NN_READ` | Read shared input `q[0]=23`; the four weight banks read `[2,18,-1,0]` |
| `NN_MUL` | Generate and register four parallel products `[46,414,-23,0]` |
| `NN_ACC` | Add each product to its own accumulator, producing `[52,755,-627,-16]` |

The same three clocks repeat for q[1] and all remaining inputs. `NN_STORE` saves the four neurons sequentially, then moves to the next group. The first layer needs four groups; the second needs one. Only three outputs are valid in the second layer, so lane 4 has zero-padded weights and is not externally reported.

DFT also uses `READ → MUL → ACC`, but its accumulators represent four real/imaginary components. For example, its first group is `[Re79, Im79, Re80, Im80]`; the next group starts after processing the entire frame. **Four lanes mean four products in a multiply stage, not four MACs every clock throughout processing.** Hann and squaring mainly use lane 0, and initialization, storage, and quantization also cost cycles.

| Stage | Cycle formula for four lanes and 48 bins | Existing RTL report |
|---|---|---:|
| Mean removal and Hann | `1 + 3×1024` | 3073 |
| DFT | `(48×2/4) × (1+3×1024+4)` | 73848 |
| Three-bin energy and quantization | `16×(3×4+2) + sum(feature_shifts)`, with shift sum 60 | 284 |
| Two-layer network | `(16/4 + ceil(3/4)) × (1+3×16+4)` | 265 |
| Core processing total | Sum of the four stages | 77470 |

The source is `build/core_l4_model_neighbor/regression.json`, whose model SHA matches this document. At the 12 MHz target clock, 77470 cycles is about 6.456 ms, excluding input-frame collection. Existing fixed-rate simulation in `fixed_rate_32.json` also reports 1100474 cycles from first sample to result, 77474 from last sample to result, and a steady output interval of 1024000 cycles. Its sampling interval of 1000 clocks at 12 MHz represents 12 kHz. The extra four clocks between the internal processing count and last-sample latency cover input FIFO and output handoff overhead; first-sample latency also includes window collection. These are RTL simulations and target-clock conversions, not oscilloscope measurements.

The project therefore implements a **fixed-topology matrix-vector engine**: fixed `16×16` and `3×16` matrices operate on a column activation vector. It has no arbitrary GEMM dimensions, tiled scheduler, or runtime matrix interface. It is not a 2×2 systolic array: data does not propagate cell by cell through a two-dimensional lane array. An accurate description is a fixed-point DSP and MLP inference accelerator using four shared multiplier lanes.

**How trained parameters become board ROMs.** `MLP` and `fit_mlp()` in `training.py` train floating-point models; `make_integer_model()` generates int8 weights, int32 biases, and shifts from their scales. The current neighbor model records PTQ. The presence of a separate QAT function does not establish that this model used QAT. Neighbor experiments use `scripts/compare_neighbor_features.py`, with training data for training and feature scaling and validation data for selection. This walkthrough does not rerun that experiment or evaluate held-out test data.

`src/vibfpga/export.py::export_model()` writes HEX files. The four-lane design reads `weights_l4_0.hex` through `weights_l4_3.hex`, each prearranged by assigned neuron rows. Bank 1 stores hidden rows 0, 4, 8, 12, then output row 0; other banks follow the same pattern, and bank 4 pads its invalid output row with zeros. `w1.hex/w2.hex` retain row-major matrices for inspection, while RTL reads the banked versions.

`$readmemh` in `vibration_core.sv` initializes ROMs in simulation and provides initial memory content to FPGA synthesis. `vib_coeff_rom.sv` similarly loads Hann and quarter-cycle cosine tables. `scripts/build_board.py --model ...` sets `MODEL_DIR`, `BANDS=3`, and `HIDDEN_SHIFT=8`, then synthesizes, routes, and packs `board.bin`. Changing JSON or HEX on the host does not change an already configured FPGA's weights; a matching configuration must be rebuilt and subsequently deployed.

Replay waveforms are separate data. `scripts/prepare_replay.py` packs validation HEX into a Flash input image. Its header contains the model SHA, which RTL checks against the configured `MODEL_HASH` at startup. This Flash waveform region is not a runtime weight-upload interface. Build scripts only generate files; the reproduction commands below do not program hardware.

**Suggested reading and recomputation order.** Inspect `features/hidden/logits` at the end of `replay_000.json` first. Then read `classify()`, `frontend()`, and `infer()` in `fixed.py`, manually checking n=64 and neuron 0 above. In `vibration_core.sv`, locate port handshakes, state enumeration, operand selection under `multiply_enable`, and state transitions. Finish with `vib_coeff_rom.sv` and weight-bank export code. Understanding data flow first makes clock-by-clock scheduling easier.

The following read-only walkthrough reproduces every value above. It checks an existing validation vector without training, data changes, or hardware access. By default it prints selected samples, all 48 bins, 16 features, and both layer dot products; `--full` prints all intermediate 1024-point arrays. If the original MAT file is missing, it explicitly reports `original_mat_verified=false`; HEX and JSON checks can still run.

```bash
# Run from the repository root.
bash -c 'source scripts/env.sh; python scripts/trace_frame.py'
bash -c 'source scripts/env.sh; python scripts/trace_frame.py --full'
```

To rerun RTL instead of only the Python reference, use the existing simulation entries below. The first runs a 1000-frame regression: five synthetic inputs and nine exported real validation windows provide 14 distinct inputs with intermediate-value checks, followed by continuous-frame output, handshake, and stall checks. The same test file covers protocol errors, buffer saturation, and resets in each stage. `check_debug()` compares mean, all 1024 windowed values, 48 real/imaginary pairs, 16 energies, 16 features, 16 hidden values, and three logits. Raw 40-bit DFT accumulations are saved in Python exports, but the passive debug port outputs normalized real/imaginary values; it does not export every internal accumulator state clock by clock.

The second command repeats this fixed validation frame for 32 frames at 12 kHz cadence, including overload and recovery. It checks scheduling, dropped-sample statistics, and output agreement; it is not classification accuracy on 32 independent statistical samples. These commands update their build reports without modifying the frozen model or programming the FPGA.

```bash
bash -c 'source scripts/env.sh; python scripts/build_core.py --model artifacts/model_neighbor/model.json --lanes 4 --frames 1000'
bash -c 'source scripts/env.sh; python scripts/build_core.py --model artifacts/model_neighbor/model.json --lanes 4 --fixed-rate --vector artifacts/vectors_neighbor/replay_000.hex --frames 32'
```

Evidence is in `build/core_l4_model_neighbor/regression.json`, the adjacent `results.xml`, and `build/core_l4_model_neighbor/fixed_rate/fixed_rate_32.json`. At writing time these reported passes; an additional read-only trace verified the original MAT, HEX, 15 reference fields, and 15 ROM files. Physical validation requires an actual UPduino, matching wiring, and measurement records; Python recomputation or RTL simulation cannot substitute for it.
