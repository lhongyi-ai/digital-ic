# Implemented computation and interface contract

This document describes the implemented single-bin and neighbor-energy variants. At the original contract stage, no hardware measurements had been performed. Later physical-board results require their own matching evidence; see `artifacts/evidence/current-status.md`.

## Computation

- Frame N=1024 (power-of-two parameter, tests may use smaller N); F=16 features; H=16 hidden units; C=3 classes. LANES=1 or 4. BANDS=1 or 3. CLK=12 MHz.
- Raw input signed 16 bit. Integer arithmetic uses round-to-nearest, ties-to-even (RNE), followed by explicit saturation where specified. Python uses unbounded/intermediate int64 arithmetic with width assertions, never implicit numpy int32 overflow.
- DC: RNE(sum(raw), log2(N)); center in at least 17 bits; RNE(center, 5), saturate signed 12 bits.
- Periodic Hann: coefficient round((0.5-0.5*cos(2*pi*n/N))*2^14), signed 16-bit storage. Windowed sample = sat12(RNE(sample*coefficient,14)).
- DFT coefficients: round(cos(2*pi*k*n/N)*2^14) and round(-sin(2*pi*k*n/N)*2^14), signed 16 bit. Accumulate signed 40 bit.
- Real and imaginary results: sat16(RNE(acc, log2(N)+10)); power = re*re + im*im, unsigned 32 bits (use >=33-bit temporary).
- BANDS=1 computes 16 DFT bins. BANDS=3 computes the 48 bins ordered as k-1, k, k+1 around each of the 16 centers, sums each three powers in a 34-bit unsigned intermediate, and still emits 16 features. It does not average already-quantized features.
- Each feature has a nonnegative power-of-two shift learned from TRAIN records only: feature_q = clamp(RNE(power, feature_shift),0,127). Float network input units are feature_q/128.0; the unrounded input reference is clamp(power/2^feature_shift,0,127)/128.0.
- MLP: int8 symmetric weights [-127,127], one power-of-two scale per layer, int32 biases/accumulators, hidden ReLU then RNE by exported nonnegative hidden_shift and clamp 0..127. Logits are int32 accumulators in a common layer scale (no per-channel output scales). Lowest class index wins ties.
- The physical accumulator is shared with the DFT and is 40 bits wide. The NN path checks its result against the INT32 range before storing the activation/logit. Four lanes broadcast one activation to four independently weighted output neurons; the read, multiply and accumulate states are separate cycles. This is fixed matrix-vector inference (16x16 and 3x16), not arbitrary-size GEMM, a 2x2 systolic array, or four completed MACs every clock.
- Compare a float front end and an integer front end separately; exported replay vectors always use this integer contract.
- Frame output: frame_id uint32, logits[3] int32, class_id uint2, stage cycles and error counters. Only count transfers on valid && ready. Out data stable until accepted. Reset cancels all outstanding work.

## Export boundary

The Python package src/vibfpga includes fixed.py, dataset.py, training.py. Public functions in fixed.py: round_shift_even(value, shift), saturate(value, bits), frontend(samples, config), infer(features, model), classify(samples, config, model). Functions accept lists/numpy arrays. classify returns the DC mean, centered/scaled/windowed samples, DFT accumulators and real/imaginary values, powers/features, hidden accumulators/activations, logits, and class_id. Neighbor mode additionally returns 48 individual dft_powers before summing into 16 powers.

artifacts/model/model.json: schema_version=1, n, bins[16], input_shift=5, dft_shift=log2(N)+10, feature_shifts[16], w1[16][16], b1[16], hidden_shift, w2[3][16], b2[3], scales and data provenance. w1/w2 index output neuron then input neuron.

artifacts/model/*.hex: bins.hex (16-bit), feature_shifts.hex (8-bit), hann.hex (16-bit), cos_quarter.hex (quarter wave, 256 entries for N1024 with endpoints handled by logic), w1.hex (8-bit row-major), b1.hex (32-bit), w2.hex (8-bit row-major), b2.hex (32-bit). hidden_shift in model.json and generated model_config.svh.

The neighbor model lives separately in artifacts/model_neighbor, adds dft_bins[48] and dft_bins.hex, and requires BANDS=3 plus its own matching model/ROM files when building. A model SHA256 binds the replay image, regression report and classification firmware to the selected parameters.

## Core port boundary

vibration_core #(N=1024, LANES=4, BANDS=1, MODEL_DIR="artifacts/model", HIDDEN_SHIFT=...) uses clk, rst (sync active-high), in_valid, in_ready, in_sample signed[15:0], in_frame_id[31:0], in_last; out_valid, out_ready, out_frame_id[31:0], out_logits packed[95:0] with class0 in bits31:0, out_class[1:0], out_error[7:0], cycles_pre[31:0], cycles_dft[31:0], cycles_power[31:0], cycles_nn[31:0], cycles_total[31:0]. Debug outputs dbg_valid, dbg_kind, dbg_index and signed 40-bit dbg_value expose mean (kind 0), windowed samples (1), real/imaginary values (2/3), summed feature powers (4), quantized features (5), hidden activations (6), and logits (7). Out fields/counters stay stable while stalled. A malformed in_last cancels that frame and records protocol error. During receive or drain a new frame_id cancels the old frame and treats the current sample as sample0 of the new frame; a subsequent wrong sample count still cancels that new frame. This lets a fixed-rate source recover after a lost sample or last marker.

## Data split

Official CWRU 12k Drive End, DE only, defects .007/.014/.021 inches, outer race @6:00. Train loads 0/1 HP, validation 2 HP, test 3 HP. Exact record-specific MAT key, no substring-first selection. Split records before nonoverlapping windows. Normal data excluded. Input float->int16 scale learned from train only and included in export.

## Evidence boundaries

Do not mark PCB, USB, FPGA, sensor, scope or real power tests passed without physical evidence. Scripts must be safe by default: no Flash programming without an explicit board profile and separate program action; no writes to configuration region for data/log operations. No purchases are authorized by implementation.
