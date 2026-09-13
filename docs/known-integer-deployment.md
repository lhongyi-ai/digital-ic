# Complete-Spectrum Linear Model: Integer Deployment Contract

The software reference is `src/vibfpga/known_fixed.py`, RTL is `rtl/core/known_spectral_core.sv`, and complete development-pipeline evidence is in `artifacts/acoustic-known-integer-pipeline-v2/`. The new core and Flash application are implemented; see `artifacts/evidence/current-status.md` for valid bindings of existing simulation/synthesis evidence. The original AE core's 16 features and per-window reconstruction score are not directly interchangeable.

## Algorithm and Model

Each machine ID deploys its own parameters. The host/installation configuration specifies the ID; unfamiliar models are not identified automatically. A raw 10-second recording contributes its first 159744 samples: 156 nonoverlapping 1024-sample windows at 16 kHz, totaling 9.984 seconds. Host training fits a 512-input→1-score L2 logistic regression per machine, with C=1, max_iter=3000, and seed71. The board computes only the linear score; no sigmoid is required. The MLP did not outperform this route during development.

Models were refitted on all 192 CV recordings per machine and exported to `artifacts/acoustic-known-release-v1/`. The selected route does not include 00's additional 256 training recordings. Calibration retains the original 32 plus 128 added normal recordings for 00, and 32 normal recordings for every other ID. Take the threshold from position `ceil((n+1)*.96)` in the ascending complete-integer score list; trigger only for a strictly greater score. Frozen parameter files do not establish completed deployment acceptance and must not be adjusted against the final test.

## Fixed Operation Order

1. RNE right-shift original signed16 PCM by 1. Sum each window, RNE-divide by 1024 to obtain its mean, subtract the mean, and saturate to signed16. Development inputs caused zero centering saturations, but RTL must retain detection.
2. Sine/cosine use a symmetric Q15 quarter-cycle table with amplitude 32767. Generate Hann as `RNE((32767-cos_q15)/2)`; RNE right-shift the sample-window product by 15.
3. Compute real and imaginary components for bins 1..512. Accumulate in 48 bits, then RNE right-shift by 8 into signed32 per bin. Although the fast software matrix multiplication calls float64 BLAS, all operands are integers and every possible partial sum is below 2^53, giving exact integer dot products. A separate scalar integer dot-product check also exists. RTL uses integer multiply-accumulate.
4. Compute each bin's `Re²+Im²` in unsigned64, RNE right-shift by 8, then sum across 156 windows in unsigned64. For N1024, this sum corresponds to normalized power Q54. The trained model uses squared raw PCM counts, so conversion requires an additional factor of 2^30.
5. Derive the integer exponent from the leading bit and use ten mantissa bits to index a 1024-entry log2 table, producing Q12. For each recording's per-bin power sum, `log_q12=exp*4096+LUT[mantissa]-round((24+log2(156))*4096)`, then floor at `round(log2(1e-12)*4096)`. Taking logs before averaging is not equivalent.
6. Normalize to INT8: `mean_q12=round(mean*4096)`; `gain_q24=round(2^24/(4096*std*input_scale))`; `qx=saturate_INT8_symmetric(RNE((log_q12-mean_q12)*gain_q24 >>24))`, range [-127,127]. The product uses a 64-bit reference.
7. input_scale is the maximum absolute standardized training feature divided by 127; weight_scale is the maximum absolute weight divided by 127. Weights use symmetric INT8 and bias is quantized to INT32 using the product of both scales. Classification is a 512-term multiply-accumulate plus bias, with INT32 range checking and comparison against the integer calibration threshold.

RNE always means round to nearest with positive and negative ties to even. An arithmetic right shift of a negative value must not silently substitute for RNE.

## RTL Implementation and Remaining Acceptance

- Replace/augment the existing 16-dimensional AE core with a parameterized complete-spectrum linear core, retaining old firmware and evidence. Power accumulation over 156 windows is required; changing only 16 weights does not deploy the complete model.
- Share MACs across windowing, DFT, square decomposition, normalization, and classification. Prioritize a read/multiply/accumulate DFT pipeline to avoid the estimated bottleneck where three serial cycles per bin make four MACs with 512 bins exceed 64 ms. Confirm actual frequency and throughput through synthesis, simulation, and physical deployment.
- Allocate input double buffers, power sums, and parameters in SPRAM/EBR; do not default large arrays to registers and ignore UP5K capacity.
- Verify complete handshakes, continuous windows, input stalls, resets, overflow, and recording boundaries; produce exactly one classification per 156-window recording. Retain at least 1000 windows of functional regression plus stagewise integer diagnostics.
- Export final models, establish integer/RTL bit accuracy, verify resources/timing and fixed cadence, then freeze deployment files and evaluate the 720 final recordings only once. After passing, back up/check Flash binding and program the board. Replay real recordings covering at least all four IDs and retain digests of model, bitstream, input, and readback logs.

Core optimizations preserve the bit-accurate contract: real and imaginary squares share one 64-bit accumulator; quantization applies magnitude RNE and saturation before restoring sign; real/imaginary paths share phase counters; stage counters use per-recording bounds and extend to 32-bit outputs. Only control/valid state requires reset; initiating states write internal arithmetic registers before reading them. Complete real-recording regressions cover 1092 windows each for one and four MACs, with 3,361,799 stagewise checks. Post-optimization regressions are saved under `build/known-native/*-r2/`.

`rtl/upduino_known.sv` uses nominal 12 MHz HFOSC and a 13.2 MHz synthesis constraint. The first passing complete application is `build/known-board/l4-id00-r8/`: 5178 LCs, four DSPs, 28 EBRs, one SPRAM, final routed Fmax 13.3138 MHz. Use final `timing.json`, not a higher intermediate placement estimate. ABC9 mapping includes registers; other machines and one MAC use the same options. Failed resource attempts r1–r7 remain retained locally, as do omitted build reports.

### Single-Recording Flash Replay Protocol

Each startup replays one complete raw PCM recording. The host runs recordings in batches and switches installed-machine parameters. The compute core still supports continuous windows/recordings; one-/four-MAC comparisons use the same recording batch.

- Input region `0x100000`: 64-byte KSR1 header containing version, N, 156 windows, sampling period, length, CRC32, and model SHA256, followed by 319488 bytes of raw PCM16. Supports 4..12000 cycles/sample; the primary version uses 750. Slower one-MAC replay can use 1500 and must separately report that it cannot sustain 16 kS/s.
- A 256-sample synchronous prefetch queue absorbs Flash read latency. The sample-generation timer is independent of core ready; missing samples or backpressure immediately record errors, rather than slowing the source to appear to pass.
- Log region `0x300000` is 4 KiB. Startup scans the entire region; any non-FF byte preserves completed or partially written logs. The normal path writes the 252-byte result body first, then separately writes the four-byte commit marker.
- The KSL1 body stores raw-input CRC, model SHA256, generated/accepted counts, errors, score, classification, stage cycles, and first-sample/last-sample/output times. CRC32 additionally protects the body. The host parser rejects misaligned, corrupt, uncommitted, and mismatched logs.
- `scripts/test_known_flash.py` defaults to a small algorithm fixture for seven complete SPI/error paths. `--production` uses a real development recording at the full 1024×156 size. The first production-size check is `build/known-flash/full-id00-l4-r1/report.json`: 159744 samples without error, score=-6361, matching the integer reference. This is simulation, not physical-board evidence.

`make release PROFILE=known` freezes deployment, reusing valid RTL reports and running common Python checks. The final test may be evaluated only once using the frozen version; consult the unified status page for whether download/evaluation has occurred. Matching-version physical-board acceptance is the final gate; old on-board AE results are not hardware evidence for this version.
