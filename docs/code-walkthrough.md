**Follow one real validation frame through Python, the quantized model, and RTL**

This walkthrough follows the already exported `artifacts/vectors_neighbor/replay_000.json`; it does not select another test sample or retrain the model. The pipeline converts 1024 vibration samples into 16 frequency-domain features, then uses a 16→16→3 neural network to predict a fault class. The integer values below were recomputed with `scripts/trace_frame.py`, matched against all 15 intermediate-result fields in that JSON, and checked against 15 exported coefficient, weight, and bias ROM files.

These values are **Python reference results for real CWRU data**. Separate existing RTL simulation reports establish agreement between the implementation and the reference. They are neither physical UPduino measurements nor data from a newly attached sensor. The current model recognizes only inner-race, outer-race, and ball faults; it has no normal class. These results also do not establish household-fan fault recognition.

**Three concepts first.** Python prepares data, trains and quantizes the model, and generates reference answers. SystemVerilog is the language used to describe this project's RTL. RTL describes registers, memories, multipliers, and data transfers on each clock cycle. Synthesis converts synthesizable SystemVerilog into circuitry; placement and routing then produce an FPGA configuration file. The UPduino runs the configured circuit rather than interpreting Python or SystemVerilog source files inside the chip.

The parameters in this walkthrough are `N=1024, LANES=4, BANDS=3, HIDDEN_SHIFT=8`, with model directory `artifacts/model_neighbor`. `BANDS=3` means each feature sums the energy of a center frequency bin and its two immediate neighbors.

```text
1024 int16 samples
    → mean removal, scaling, Hann window
    → 48 selected DFT bins, each with real and imaginary components
    → sum energy in groups of 3 bins to obtain 16 features
    → 16 quantized features in 0..127
    → W1[16×16] × features[16×1] + b1 → ReLU, quantization
    → W2[3×16] × hidden[16×1] + b2
    → 3 integer logits → class with the largest value
```

| Level of understanding | File and entry point | Corresponding hardware behavior |
|---|---|---|
| Complete integer inference | [fixed.py](../src/vibfpga/fixed.py), `classify()` → `frontend()` → `infer()` | Bit-exact reference for the entire computation |
| Input and answer for one frame | [replay_000.json](../artifacts/vectors_neighbor/replay_000.json), and the `.hex` in the same directory | `.hex` supplies the input; JSON retains intermediate values and provenance |
| Frozen model parameters | [model.json](../artifacts/model_neighbor/model.json) | Bins, shifts, weights, biases, and class order |
| Arithmetic and scheduling | [vibration_core.sv](../rtl/core/vibration_core.sv) | Double input buffers, state machine, and shared multipliers |
| Coefficient storage | [vib_coeff_rom.sv](../rtl/core/vib_coeff_rom.sv) | Synchronous reads of a quarter-wave ROM and reconstruction of other quadrants |
| Implementation correctness | [test_core.py](../sim/test_core.py), `check_debug()`, `receive()` | Checks intermediate values, logits, handshakes, stalls, and resets |

**Step 1: Where do these 1024 numbers come from?** The source is `107.mat` in the official CWRU 12 kHz Drive End dataset, specifically MAT field `X107_DE_time`. The file belongs to validation and represents a 2 HP load with a 0.007-inch inner-race fault. Zero-based `window_index=2` selects `[2048:3072]` from the original recording: 1024 points, indices 2048 through 3071, at approximately `[0.170667, 0.256000)` seconds. The vector's `provenance` stores its source, window, and label; the label is not a hardware input.

`fit_raw_scale()` in `dataset.py` determines input gain using training recordings only. `load_windows()` converts the recording's floating-point values to int16:

```text
gain = 4915.122577220299
raw[n] = clip(RNE(original[n] × gain), -32768, 32767)
```

RNE means round to nearest, ties to even, including for negative values. The first original floating-point value is `-0.02940075848303393`, which becomes `raw[0]=-145`, or `ff6f` in 16-bit two's-complement HEX. HEX reading must restore signed values; `ff6f` must not be interpreted as positive 65391.

The walkthrough run also checked the local `107.mat` SHA256 and extracted this window again. All 1024 rescaled points exactly matched the exported HEX. This check covered only that validation recording. The original bulk MAT data is retained locally when omitted from this publication.

```text
107.mat SHA256:
111ba8996a115684661a13c913bd74d8029a59294492f88aec7b03e175fdd388
model_neighbor/model.json SHA256:
12abcdfd4a9072903915135e771c1fb9be0d430275e28acbf545660e1d7fa117
replay_000.hex SHA256:
b657431bcf0c4d96873c74c91334b1338a0ac2053d96768bfddbc91227f136b7
```

RTL accepts one sample only when `in_valid && in_ready` is true, and accumulates `input_sum`. The final accepted sample must also have `in_last=1`. The complete frame and its sample sum are stored in one of two input buffers. `full` means the frame has been received completely; `busy` means preprocessing is reading that buffer. Only a free buffer may accept the next frame. Model input does not mean connecting 1024 values to 1024 buses simultaneously.

**Step 2: Remove DC, scale, and apply a window.** The Python implementation is `frontend()`; RTL uses `PRE_MEAN` and repeated `PRE_READ → PRE_MUL → PRE_STORE` sequences.

```text
sum(raw) = 20020
mean = RNE(20020 / 1024) = RNE(19.55078125) = 20
centered[n] = raw[n] - 20
scaled[n] = sat12(RNE(centered[n] / 32))
hann_q14[n] = RNE((0.5 - 0.5 × cos(2πn/1024)) × 16384)
windowed[n] = sat12(RNE(scaled[n] × hann_q14[n] / 16384))
```

`sat12` limits the result to `[-2048,2047]`; the temporary mean-subtracted difference requires at least 17 bits. Coefficients are scaled by `2^14`, so a 14-bit right shift after multiplication restores the scale. The Hann window reduces spectral leakage from the finite observation window. It changes signal amplitude, so subsequent fixed-point normalization must match the training reference.

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

For n=64, RNE converts `4043/32` to 126. Multiplying by 624 gives `78624/16384≈4.7988`, which RNE converts to 5. `PRE_READ` reads the sample and Hann ROM; `PRE_MUL` uses lane 0 of the shared multipliers; `PRE_STORE` rounds, saturates, and writes `windowed` RAM. The original input buffer can be reused after preprocessing because the DFT subsequently reads a separate windowed-data buffer.

**Step 3: Compute 48 selected frequency bins.** Python uses `coefficients()` and the integer dot products in `frontend()`. RTL uses `DFT_INIT → (DFT_READ → DFT_MUL → DFT_ACC)×1024 → DFT_STORE`. This is a selected-bin DFT, not a complete 1024-point FFT.

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

Accumulators are 40 bits. The 20-bit right shift is part of this implementation's scaling contract and cannot simply be replaced with a floating-point FFT's default normalization. RTL obtains negative sine from a cosine ROM using a phase offset: imaginary phase starts at `N/4` and increases by k per sample, using `cos(θ+π/2)=-sin(θ)`. Each lane's ROM stores only a quarter wave. Quadrants and signs reconstruct the other coefficients; logic handles axis endpoints exactly.

The first feature is centered at k=80 and computes bins 79, 80, and 81. Bin spacing is 12 kHz/1024=11.71875 Hz.

| k | Frequency, Hz | real_acc | imag_acc | real | imag | P[k] |
|---:|---:|---:|---:|---:|---:|---:|
| 79 | 925.78125 | -4432855 | -297955 | -4 | 0 | 16 |
| 80 | 937.5 | 5133458 | -2840598 | 5 | -3 | 34 |
| 81 | 949.21875 | -5052589 | 4667455 | -5 | 4 | 41 |

For example, k=80 gives `5²+(-3)²=34`. Its windowed sample at index 64 is 5, and `p=(80×64) mod 1024=0`. That sample contributes `5×16384=81920` to the real accumulator and 0 to the imaginary accumulator. The accumulator values in the table sum contributions from all 1024 samples.

**Step 4: Reduce 48 bins to 16 neighboring-bin energies, then quantize.** Python's `neighbor3_energy` branch expands each center into `[k-1,k,k+1]`, runs the integer DFT, and sums every three bins. RTL uses multiplier lane 0 for squaring in `POWER_RE_MUL/ADD` and `POWER_IM_MUL/ADD`; `band_sum` sums the three bins.

```text
E[j] = P[center[j]-1] + P[center[j]] + P[center[j]+1]
q[j] = clamp(RNE(E[j] / 2^feature_shifts[j]), 0, 127)
```

Here, “neighboring bins” means **one bin on each side of the same center**, rather than dividing the entire positive-frequency range into 16 equal bands. Selected centers and scales come from the frozen model; reading this frame does not change them. The three-bin energy sum is not divided by 3.

| Feature j | Center bin | Three-bin energy E | Right-shift bits | Integer feature q |
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

For the first feature, `16+34+41=91`, and `91/4=22.75` rounds to 23. For the third, `54/4=13.5` rounds to even 14; for the twelfth, `22/4=5.5` rounds to 6. RTL's `POWER_Q_INIT → POWER_Q_SHIFT → POWER_QUANT` shifts one bit at a time, implements the same RNE rule with guard/sticky bits, and clamps to 127. Although q is stored in an 8-bit container, its range is 0 through 127. The corresponding real-valued network input scale is `q/128`. These frequency-domain energies are not physically calibrated PSD values in mg²/Hz.

**Step 5: First-layer 16×16 matrix-vector multiplication.** In Python this is `hidden_acc = w1 @ x + b1` in `infer()`. Indexing is `w1[output neuron][input feature]`: each row contains the 16 weights for one hidden neuron. Do not transpose this interpretation.

```text
q = [23,25,14,3,2,6,11,29,2,26,28,6,6,0,1,4]
W1 row 0 = [2,-6,-40,4,35,14,15,4,2,23,10,15,18,48,29,19]
Elementwise products = [46,-150,-560,12,70,84,165,116,4,598,280,90,108,0,29,76]
Dot product = 968
b1[0] = 6
hidden_acc[0] = 968+6 = 974
hidden[0] = clamp(RNE(max(974,0)/256),0,127) = 4
```

All 16 accumulator values and hidden outputs are:

```text
hidden_acc = [974,4241,-1135,584,-1126,2052,4882,-456,
              4542,909,-2459,104,-539,-805,-953,470]
hidden     = [4,17,0,2,0,8,19,0,18,4,0,0,0,0,0,2]
```

ReLU maps negative values to 0, such as neuron 2's -1135. Although 104 is positive, RNE of 104/256 still produces 0. Python checks that neural-network accumulator results fit int32. RTL reuses 40-bit accumulators and checks for values outside int32 range in `NN_STORE`.

Why shift by 8 bits? Input scale `1/128` times first-layer weight scale `1/16` gives accumulator scale `1/2048`. The hidden-layer scale is `1/8`, a factor of 256 apart. Thus `HIDDEN_SHIFT=8` follows from exported quantization scales and cannot be changed arbitrarily.

**Step 6: Second-layer 3×16 matrix-vector multiplication.** The second layer also reads one weight row and computes a dot product, but applies neither ReLU nor softmax.

| Output class | `W2[class]·hidden` | b2 | logit |
|---|---:|---:|---:|
| 0: inner_race | 2147 | -5 | 2142 |
| 1: outer_race | -712 | -170 | -882 |
| 2: ball | -4649 | 244 | -4405 |

The output is `logits=[2142,-882,-4405]`; the largest value is at index 0, so `class_id=0`. This prediction happens to match the validation window's known inner-race label. All logits share scale `1/256`, allowing direct integer comparison. They are not probabilities. In `FINISH`, RTL selects the largest value with comparators, breaking ties in favor of the lower index. It then enters `HOLD`, releasing the output only when `out_valid && out_ready`. Logits, class, and cycle count must remain stable during a stall.

**How four hardware lanes perform these computations.** `LANES=4` creates four signed 16-bit×16-bit multiplication paths, which FPGA synthesis can map to four DSP blocks. Hann windowing, DFT, squared-energy calculation, and both neural-network layers share these multipliers over time; each stage does not have its own separate set.

For the first four hidden neurons, `NN_INIT` initializes the four accumulators to biases `[6,341,-604,-16]`. When `nn_input=0`:

| State | Work performed by the four lanes |
|---|---|
| `NN_READ` | Read the same input `q[0]=23`; four weight banks supply `[2,18,-1,0]` |
| `NN_MUL` | Compute and register four products `[46,414,-23,0]` in parallel |
| `NN_ACC` | Each independent accumulator adds its product, producing `[52,755,-627,-16]` |

The same three cycles repeat for q[1] and continue until all 16 inputs have contributed. `NN_STORE` stores the four neuron results in turn, then processing moves to the next group. The first layer requires four groups; the second requires one. Only three second-layer outputs are valid, so lane 4 uses padded zero weights and its result is not exposed.

DFT also uses a three-cycle `READ → MUL → ACC` sequence, but the four accumulators represent four real/imaginary components. For example, the first group is `[Re79, Im79, Re80, Im80]`; the next group starts after the complete frame has been processed. **Four lanes means four products in a multiplication stage, not sustained throughput of four MACs per clock throughout processing.** Hann and squaring primarily use lane 0, and other stages also incur initialization, storage, and quantization overhead.

| Stage | Cycle calculation for four lanes and 48 bins | Existing RTL report |
|---|---|---:|
| DC removal and windowing | `1 + 3×1024` | 3073 |
| DFT | `(48×2/4) × (1+3×1024+4)` | 73848 |
| Three-bin energy and quantization | `16×(3×4+2) + sum(feature_shifts)`, shift sum 60 | 284 |
| Two network layers | `(16/4 + ceil(3/4)) × (1+3×16+4)` | 265 |
| Total core processing | Sum of the four stages above | 77470 |

The source is `build/core_l4_model_neighbor/regression.json`, whose model SHA matches this walkthrough. At a 12 MHz target clock, 77470 cycles correspond to approximately 6.456 ms, excluding the time spent collecting the input frame. Existing fixed-sample-rate simulation `fixed_rate_32.json` also records 1100474 cycles from first sample to result, 77474 cycles from last sample to result, and a steady-state output interval of 1024000 cycles. Its sample interval of 1000 cycles at 12 MHz corresponds to 12 kHz. The last-sample-to-result latency exceeds the internal 77470-cycle processing count by 4 cycles, including input FIFO and output handoff overhead; the first-sample latency also includes collecting the window. These are RTL simulation results and target-clock conversions, not oscilloscope measurements.

The project therefore implements a **matrix-vector engine with fixed topology**: fixed `16×16` and `3×16` matrices operate on one activation column vector. It does not provide arbitrary GEMM dimensions, tiled scheduling, or runtime matrix interfaces. It is also not a 2×2 systolic array: the four paths do not propagate data cell by cell through a two-dimensional array. A precise description is “a fixed-point DSP and MLP inference accelerator with four shared multiplier lanes.”

**How trained parameters become on-board ROM.** `MLP` and `fit_mlp()` in `training.py` train the floating-point model. `make_integer_model()` generates int8 weights, int32 biases, and shifts from the scales. The current neighbor model records PTQ; the presence of a separate QAT function in the code does not mean this model underwent QAT. The neighboring-bin experiment entry point is `scripts/compare_neighbor_features.py`. Training data determines training and feature scales; validation data selects the model. This walkthrough does not rerun that experiment or reevaluate the held-out test set.

`src/vibfpga/export.py::export_model()` exports `.hex` files. The four-lane design reads `weights_l4_0.hex` through `weights_l4_3.hex`, each prearranged by the neuron rows assigned to that bank. Bank 1 first stores hidden-neuron rows 0, 4, 8, and 12, then output-neuron row 0. Other banks follow the same pattern, with the fourth bank's invalid output row padded with zeros. `w1.hex/w2.hex` retain row-major matrices for manual inspection; current RTL actually reads the banked versions.

In `vibration_core.sv`, `$readmemh` initializes ROM during simulation and supplies memory initialization contents during FPGA synthesis. `vib_coeff_rom.sv` similarly reads the Hann and quarter-wave cosine tables. `scripts/build_board.py --model ...` sets `MODEL_DIR`, `BANDS=3`, and `HIDDEN_SHIFT=8`, then performs synthesis, placement/routing, and packing to create `board.bin`. Editing JSON or HEX on the computer does not change weights in an already configured FPGA. A matching configuration must be rebuilt and subsequently deployed through a physical-board operation.

Replay waveforms are a separate type of data. `scripts/prepare_replay.py` packages validation HEX into a Flash input image. Its header includes the model SHA, which RTL checks at startup against the configuration's `MODEL_HASH`. This Flash waveform region is not a runtime weight-upload interface. Build scripts only create files; the reproduction steps here do not program the board.

**Suggested reading and reproduction order.** Start with `features/hidden/logits` near the end of `replay_000.json` to see the answer. Then read `classify()`, `frontend()`, and `infer()` in `fixed.py`, and manually work through n=64 and neuron 0 above. Next open `vibration_core.sv` and find the port handshakes, state enumeration, operand selection for `multiply_enable`, and state transitions. Finally read `vib_coeff_rom.sv` and the weight-bank export code. Understanding the data flow makes cycle-by-cycle timing easier to follow.

The following quick, read-only walkthrough recomputes every value in this document. It checks existing validation vectors without training, data modification, or hardware access. By default, it prints selected sample points, all 48 bins, 16 features, and both layers' dot products. Add `--full` for complete intermediate arrays for all 1024 samples. If the original MAT is missing, it explicitly reports `original_mat_verified=false`; checks against the existing HEX and JSON can still run.

```bash
cd "${PROJECT_ROOT}"
bash -c 'source scripts/env.sh; python scripts/trace_frame.py'
bash -c 'source scripts/env.sh; python scripts/trace_frame.py --full'
```

To rerun RTL rather than only recompute Python, use the existing simulation entry points below. The first runs a 1000-frame regression: five artificial inputs and nine already exported real validation windows. It checks intermediate values for the first 14 distinct inputs, then checks continuous-frame outputs, handshakes, and stalls. The same test file also checks protocol errors, full buffers, and resets at each stage. `check_debug()` compares the mean, all 1024 windowed values, 48 real/imaginary pairs, 16 energies, 16 features, 16 hidden values, and three logits individually against the reference. Raw 40-bit DFT accumulations are stored in the Python export. The current passive debug port exposes normalized real/imaginary values, so it cannot be described as exporting every internal accumulator state on every cycle.

The second command runs 32 frames of this fixed validation frame at a 12 kHz cadence, with overspeed input and recovery checks. It verifies scheduling, dropped-sample accounting, and result consistency; it is not a classification-accuracy evaluation of 32 statistically independent samples. These commands update their build simulation reports but do not modify the frozen model or program the FPGA.

```bash
bash -c 'source scripts/env.sh; python scripts/build_core.py --model artifacts/model_neighbor/model.json --lanes 4 --frames 1000'
bash -c 'source scripts/env.sh; python scripts/build_core.py --model artifacts/model_neighbor/model.json --lanes 4 --fixed-rate --vector artifacts/vectors_neighbor/replay_000.hex --frames 32'
```

The corresponding evidence is `build/core_l4_model_neighbor/regression.json`, `results.xml` in the same directory, and `build/core_l4_model_neighbor/fixed_rate/fixed_rate_32.json`. At the time of writing, these reports were checked as passing, and the separate read-only trace checked the original MAT, HEX, 15 reference fields, and 15 ROM files. Build evidence omitted from the publication remains local. Physical validation requires an actual UPduino, matching wiring, and measurement records; Python recomputation or RTL simulation cannot substitute for it.
