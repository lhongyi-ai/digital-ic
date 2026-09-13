# Directed NN Tie and INT32 Overflow Verification

This work completed with Verilator 5.051 devel / cocotb 2.1.0, **without physical FPGA hardware**. One- and four-MAC configurations each ran eight independent model cases, and **all 16 cocotb tests passed**. All 72 valid outputs were checked individually; 64 completed the output handshake. Another 16 input frames were canceled by reset at two specified points. A valid output here means `out_valid=1`, not that its classification is usable.

## Actual RTL contract

- For each neuron, the core checks the final 40-bit accumulator against INT32 range `[-2147483648, 2147483647]`. The check occurs in `NN_STORE`, not per product or immediately after each out-of-range intermediate addition.
- A final value outside that range sets the frame's `out_error[0]`. The hidden layer still applies ReLU, RNE, and clipping to `0..127` using the full accumulator value.
- The output layer stores the accumulator's low 32 bits and interprets them as signed INT32. Overflow **does not saturate to an INT32 endpoint**. For example, `2147483648` is stored as `-2147483648`. `out_class` is still calculated from stored logits, but classifications from erroneous frames must not be used.
- Ties select the smaller class index. The error flag remains stable with the output and clears when processing the next frame begins. Synchronous reset cancels unaccepted outputs and computations in progress.

Implementation: `NN_INIT`, `NN_ACC`, `NN_STORE`, `FINISH`, `HOLD`, and reset branches in `rtl/core/vibration_core.sv`. That file was unchanged in this work; its SHA256 was:

```text
1f9546be166957707f92a635e1e07834505db9b9d885d6fb3672cce6ac46872f
```

## Cases and actual results

| Requirement | Independent test model/input | Checker | One MAC | Four MACs |
| --- | --- | --- | --- | --- |
| All three classes tied | logits `[0,0,0]` | Class must be 0 | PASS | PASS |
| Classes 0 and 1 tied for maximum | logits `[-7,-7,-9]` | Signed comparison; class must be 0 | PASS | PASS |
| Classes 0 and 2 tied for maximum | logits `[11,0,11]` | Class must be 0 | PASS | PASS |
| Classes 1 and 2 tied for maximum | logits `[-8,-3,-3]` | Must not always choose 0; class must be 1 | PASS | PASS |
| Hidden-layer positive boundary/overflow | Final values `2147483646, 2147483647, 2147483648` | Exact raw 40-bit final values; error bits `0,0,1` | PASS | PASS |
| Hidden-layer negative boundary/overflow | Final values `-2147483647, -2147483648, -2147483649` | Exact raw 40-bit final values; error bits `0,0,1` | PASS | PASS |
| Output-layer positive boundary/overflow | Same three positive values | Raw values, signed32 stored values, and error bits all checked | PASS | PASS |
| Output-layer negative boundary/overflow | Same three negative values | Raw values, signed32 stored values, and error bits all checked | PASS | PASS |
| Recovery without reset | Numerically valid frame after an erroneous frame | New frame ID, complete logits, `out_error=0`, and no duplicate output | PASS | PASS |
| Backpressure on erroneous output | Hold every output for 11 clock cycles | Logits, class, error, ID, and cycle count all stable | PASS | PASS |
| Reset after an internal NN error | Reset after the error bit becomes 1, before `FINISH` | Old frame canceled; complete next-frame result correct, with no stale output | PASS | PASS |
| Reset while an erroneous output awaits acceptance | `out_valid=1, out_ready=0` in `HOLD` | Unaccepted old output canceled; subsequent legal-endpoint frame succeeds | PASS | PASS |

Each tie model uses two different raw input frames. Each overflow model checks three adjacent boundary values, normal recovery, and two forms of reset recovery. Each MAC configuration therefore checks 36 outputs, accepts 32, and cancels eight frames; combined counts are 72/64/16. Of the 16 cancellations, eight occur before output generation and eight after an output has been checked but before handshaking. These counts must not be added as independent output populations.

Every one of the 72 checked outputs verifies 16 input features, 16 hidden activations, 19 final neuron accumulators, three logits, the class, and the exact error mask, totaling **1368 final NN accumulator comparisons**. Every output also checks the sum of stage cycle counts and zero protocol errors. Existing core assertions are enabled through `--assert -DVIB_ASSERT`.

## Reaching boundaries without modifying deployed models

Parameters are fixed to `N=1024, BANDS=1, HIDDEN_SHIFT=0`, with separate builds for `LANES=1` and `LANES=4`. This parameter/model combination is dedicated to numerical verification, not accuracy evaluation of a trained model.

Tests send complete signed16 raw waveforms through the real input interface, traversing the existing DC removal, Hann, DFT, power quantization, and NN paths. Integer-bin cosine windows with amplitudes `0,256,320` produce first-feature values `0,1,2`. Test weights are `+1` or `-1`, and biases are one unit inside an INT32 endpoint, so final accumulators land exactly one unit inside, on, and one unit outside that endpoint. Output-layer tests first copy the input feature through the hidden layer, then reach the output accumulator boundary.

`sim/nn_edges_tb.sv` adds only passive simulation probes to observe actual accumulator values before `NN_STORE` and the feature/hidden arrays. It neither forces internal states, injects features directly, nor replaces computation logic, and it is absent from deployed bitstreams. The padded fourth output lane in the four-lane implementation is not counted as a neuron.

Standard `vibfpga.fixed.infer()` rejects INT32 overflow, and this test preserves that behavior. Legal vectors are checked against the standard reference. Deliberately out-of-range vectors must be rejected by that reference, then an independent Python integer checker explicitly computes error flags, hidden-activation clipping, low-32-bit storage, and argmax. The formal inference function was not modified to accommodate erroneous inputs.

All eight models, ROMs, raw inputs, and expected values reside in `build/nn_edges/fixtures/`, labeled `verification_fixture_not_trained`. Each MAC configuration compiles once, then executes `$readmemh` from its own `active_model` directory at each independent simulation startup. Each result binds to the individual fixture's file hashes; numerical checks also detect loading the wrong model.

## Reproduction and evidence

Run in the project directory:

```bash
source scripts/env.sh
python scripts/test_nn_edges.py
```

Options `--lanes 1` and `--lanes 4` select one configuration. The default runs both and does not overwrite existing 1000-frame regressions, paced replay, supplemental DSP tests, or place-and-route reports.

- `build/nn_edges/summary.json`: summary of 16 runs, result/XML hashes, source hashes, and frozen-model file hashes.
- `build/nn_edges/l{1,4}/<fixture>/manifest.json`: parameters, simulator version, and hashes for source and all fixture files.
- `result.json` in the same directory: every output, all final accumulators, raw-input hashes, expected values, output stalls, and cancellation positions.
- `results.xml` and `simulation.log` in the same directory: actual cocotb outcomes and logs; each MAC configuration also has `compile.log`.

The test script first removes stale completion reports, requires exactly one actually executed passing test in each XML, and rejects failure/error/skipped outcomes before writing the summary. At the end, all source files are rechecked, along with **37 unchanged files** in `artifacts/model` and `artifacts/model_neighbor`. No test set was accessed, model retrained, or production RTL modified.

## Scope of the conclusion

This is finite directed simulation. It is not a proof over every input, 100% coverage, another long regression for all four deployment configurations, or physical FPGA acceptance. The observed quantities are **each neuron's final 40-bit accumulator values**, not a cycle-by-cycle proof of every intermediate multiply-accumulate. No production-system 40-bit debug interface was added. Cases where adjacent operations temporarily exceed INT32 and later return within range are outside this test suite; the current implementation checks only final accumulator values.
