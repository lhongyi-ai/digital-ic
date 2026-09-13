# Core DSP / INT8 RTL Verification Matrix

This table documents actual evidence for `rtl/core/vibration_core.sv`. The core implements the complete integer path from raw PCM16 frames through mean removal, Hann windowing, selected-bin DFT, energy quantization, a 16→16→3 MLP, and classification. Four configurations combine `LANES=1/4` and `BANDS=1/3`; production replay uses N=1024. PASS means the specified configuration and cases passed; it does not extend to every input, parameter, or physical device.

## Requirement—Case—Checker—Result

|ID / requirement|Actual cases|Checker and pass condition|Actual result and evidence|
|---|---|---|---|
|DSP-ZERO / DC|All zero; constant -1537|Compare mean, windowed, Re/Im, powers, features, hidden, and logits item by item with the Python integer reference, plus class/error|PASS; original four-configuration regression and supplemental DSP regression|
|DSP-EXTREME|Alternating -32768/32767; seeded full-range random PCM16|As above; check arithmetic boundaries interacting with whole-frame control|PASS; one of 14 distinct inputs in the original regression, not 1000 independent random waveforms|
|DSP-INTEGER-TONE|Integer-bin sine; additional phase π/3|As above; an integer-bin tone is not assumed to produce only one nonzero output bin; Hann and fixed-point quantization are included in the reference|PASS; original and supplemental DSP regressions|
|DSP-OFF-BIN / PHASE|Bin k+0.375, k=model.bins[3]=207, phases 0, π/2, and 2.3 rad|Compare complete intermediates for each input against its integer reference; different phases need not produce identical outputs|PASS; supplemental four-configuration DSP regression|
|DSP-CLIP|Sines with positive-offset positive clipping, negative-offset negative clipping, and bipolar clipping|Explicit clipping during PCM16 quantization; generator asserts that clipping actually occurs, then checks the complete processing chain|PASS; 298 / 295 / 537 clipped input samples per frame respectively; all stages match in all four configurations|
|DSP-MULTITONE|Off-bin tones k+0.25 and model.bins[8]-0.375 with different phases|Feed identical raw integer samples quantized after summation into the reference and RTL|PASS; supplemental four-configuration DSP regression|
|DSP-REAL|Nine validation recordings, one exported window each|Recompute the integer reference from original sample hex; compare complete intermediates and logits|PASS; original four-configuration regression. This verifies hardware equivalence for nine windows only; classification quality is evaluated separately|
|DSP-BAND|Single-bin energy for BANDS1; sum of k-1/k/k+1 energies for every BANDS3 center|For BANDS3, check all 48 Re/Im pairs and 16 aggregated powers; assert that the 34-bit temporary sum fits 33-bit storage|PASS; original and supplemental DSP regressions|
|ARITH-RNE / SAT|Positive/negative ties, odd/even quotients, 12-/16-bit saturation boundaries, shifts 0..40, seeded random vectors|Call actual RTL arithmetic functions directly and compare with Python ties-to-even and saturate|PASS; 6651 vectors, `build/core_l4_artifacts/arithmetic/arithmetic.json` and XML|
|ARITH-SERIAL-QUANT|Feature shifts 0,1,2,3,7,8,15,16,24,30,31,32,33,34,40,63|An explicitly untrained boundary profile runs the actual power-quantization state machine and complete core with stagewise comparison|PASS; five frames, `build/core_l4_quant_boundary/regression.json` and XML. Not trained-model performance|
|NN-MATVEC|Two layers with 16×16 and 3×16 weights, biases, hidden RNE/ReLU/clipping|Independent integer MLP reference; compare three logits, class, and error every frame, and hidden values for each distinct input|PASS; original four-configuration and supplemental DSP regressions. Fixed-shape matrix-vector multiplication; no general GEMM or systolic-array claim|
|IF-CONTINUOUS|1000 continuous frames rotating 14 distinct inputs, unique frame_id, input gaps and short output stalls|Exactly one output per complete valid frame, ordered by ID, matching logits, no extra outputs or protocol errors|PASS; 1000 frames per configuration; all intermediates also checked for each configuration's first 14 frames|
|IF-MALFORMED|Early last, missing last, ID changes mid-frame|Cancel malformed frames, increment protocol count, recover with a new ID, and emit no partial-frame result|PASS; `malformed_frames_and_reset` XML in all four configurations|
|IF-PROTOCOL-EDGES|last on first beat; missing last with the same ID and continued draining until a late last; high frame-ID bits and FFFFFFFF→0 wrap|Nine real validation windows per configuration; bit-accurate complete intermediates/outputs, exactly two protocol errors, stable stalled outputs|PASS; 36 frames total; see [independent protocol checks](protocol-edge-verification.md). Original coverage percentages were not recomputed|
|IF-BUFFERS / STALL|Prolonged output backpressure while continuing to fill both raw input buffers|out_valid/all output fields remain stable; in_ready eventually falls; after release, each complete frame outputs once|PASS; `full_buffers_during_output_stall` XML in all configurations; core SVA also checks buffer ownership/output stability|
|IF-RESET|Reset during a partial input frame, PRE_READ, PRE_STORE, DFT_ACC, POWER_Q_SHIFT, NN_ACC, FINISH, and output wait|Cancel old frames; new frames after reset produce correct results; no old-frame leakage|PASS; two reset cases in each configuration|
|RATE-NOMINAL|Source independent of ready, one sample every 1000 clocks, 1000 frames|Accept all 1,024,000 samples per configuration, 1000 ordered correct outputs, zero loss/protocol errors, processing ≤1024×1000 cycles|PASS; `fixed_rate/fixed_rate.json` in all configurations|
|RATE-OVERLOAD|One sample per cycle for the first eight frames, then normal cadence for four frames|Explicit loss count and protocol errors; recover the final three frames without reset and produce matching logits|PASS; same reports. This stress harness uses FIFO depth 4; production replay uses depth 2, so loss counts do not directly apply to the board|
|RATE-LATENCY|Separate 32-frame normal run measuring source first/last offered-sample edges to output handshake and output intervals|C++ counts actual edges rather than replacing end-to-end latency with core stage counters|PASS; `fixed_rate/fixed_rate_32.json` in all configurations. Normal maximum FIFO occupancy=1|
|FLASH-E2E|Behavioral SPI NOR → two source frames repeated for five outputs → result pages → final commit; hash/CRC/page boundaries/WIP/old-log protection|Actual SPI byte model, final-log parsing, integer logits reference, and prohibition on writes outside the partition|PASS; complete four-lane BANDS1/3 systems in `build/flash_system*/regression.json`. Ordinary E2E shortens blank scanning; separate `flash_system_neighbor_full_scan` checks rejection at the final byte of the full 128 KiB region|
|BUILD-FIT / TIMING|Four complete `upduino_replay` top levels, UP5K SG48, 12 MHz, seed=1|Complete synthesis, actual place-and-route, and packing; report input SHAs corresponding to current RTL/ROM/model/PCF|PASS; four `build/board*/report.json` files, detailed below. Static timing estimates, not physical measurements|
|FORMAL-QUANT|Verbatim extraction of RNE, saturation, ReLU, and three serial feature-quantization states from production RTL|Independent mathematical specification; HIDDEN_SHIFT0/8 function proofs, serial BMC64, reachability, and deliberate-mutation negative controls|PASS; five positive tasks, 58 cover targets, counterexamples for both faulty versions; see [quantization formal checks](quantization-formal.md)|
|FORMAL-CORE|Formal equivalence of the entire DSP/MLP for all inputs|No unbounded proof of the entire core yet|NOT_RUN; fragment proofs and simulation SVA are not a whole-core formal proof|
|NN-TIE / OVERFLOW-INJECTION|Four maximum-logit tie patterns; both layers inside, at, and outside positive/negative INT32 limits; recovery, stalls, and reset|Eight test-only models×two LANES configurations; compare actual 40-bit accumulators, 32-bit results, error flags, and lowest-index tie-breaking|PASS; 16 tests, 72 output checks, 1368 accumulator values; frozen model unchanged. See [NN boundary verification](nn-edge-verification.md)|
|COVERAGE-METRICS|Actual Verilator line/branch/toggle/expr database, LCOV, and every uncovered point|Four configurations with 14 normal inputs plus 10 dedicated inputs; function/high-shift profiles reported separately, retaining uncovered denominators|PASS; 37 tests, line 87.36%–90.32%, branch 85.59%–87.66%; scope and gaps in [RTL coverage](rtl-coverage.md)|
|COVERAGE-FSM|Automatic FSM/user cover counts and illegal-state fault injection|Current tool generated neither automatic FSM nor user cover count points|N/A; no FSM coverage percentage may be reported; no illegal-state fault injection performed|
|PHYSICAL|Physical Flash/SPI, power supply, sensor noise/frequency response/aliasing, and measured power|Requires a specific connected device and retained measurement records|NOT_RUN in this historical matrix; the user had explicitly deferred the hardware stage|

Independent FIFO checks pass BMC64 and cover64 for WIDTH16 and DEPTH1/3/4; assumptions and scope are in [verification-plan.md](verification-plan.md). This is not a formal proof of core arithmetic. Physical SPI timing, sensor frequency response, and numerical verification of a quantized sine are different evidence levels.

## Archived Evidence for Four Configurations

The `artifacts` label refers to the original single-bin model; `model_neighbor` refers to the three-neighbor-bin candidate. Each core directory contains `regression.json`, four-case `results.xml`, and build records. Repeating 1000 frames is an endurance/protocol test and does not add independent statistical samples. Build directories referenced here are retained locally when omitted from the publication.

|BANDS / LANES|Original regression directory|Supplemental DSP directory: 10 inputs, all stages checked in all 10 frames|Core processing cycles|Complete-board LC / 5280|Place-and-route estimated Fmax|
|---|---|---|---:|---:|---:|
|1 / 1|`build/core_l1_artifacts`|`build/core_dsp_l1_artifacts`|102531|4088|20.57 MHz|
|1 / 4|`build/core_l4_artifacts`|`build/core_dsp_l4_artifacts`|28094|4842|19.37 MHz|
|3 / 1|`build/core_l1_model_neighbor`|`build/core_dsp_l1_model_neighbor`|299411|4306|21.91 MHz|
|3 / 4|`build/core_l4_model_neighbor`|`build/core_dsp_l4_model_neighbor`|77470|5129|18.58 MHz|

For example, the three-neighbor-bin four-lane version reports PRE3073, DFT73848, POWER284, and NN265 stage cycles. Actual RTL edge counting across 32 frames gives 77474 cycles from last sample to result, 1100474 from first sample to result, and 1024000 between outputs; at 12 MHz these are approximately 6.456 ms, 91.706 ms, and 85.333 ms. Core stage counts exclude waiting to capture a complete frame, input queuing, and output backpressure.

## Reproducing the Supplemental DSP Regression

```sh
source scripts/env.sh
python scripts/build_core.py --lanes 1 --model artifacts/model/model.json --dsp-cases --frames 10
python scripts/build_core.py --lanes 4 --model artifacts/model/model.json --dsp-cases --frames 10
python scripts/build_core.py --lanes 1 --model artifacts/model_neighbor/model.json --dsp-cases --frames 10
python scripts/build_core.py --lanes 4 --model artifacts/model_neighbor/model.json --dsp-cases --frames 10
```

The generator rounds the continuous waveform ties-to-even before clipping to PCM16. Reports retain each case's bins, phases, clipped-sample count, input-sample SHA, and SHAs of the current core, reference implementation, test code, and ROM. The Python fixed-point reference recomputes expectations; cocotb reads and compares every RTL passive-debug value. The runner succeeds only when all four XML tests pass. Model weights and core RTL were not modified for the new cases, and the original 1000-frame reports were not overwritten.
