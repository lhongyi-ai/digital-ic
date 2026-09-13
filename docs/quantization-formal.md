**Formal verification of quantization: function proofs tied to current RTL and a 64-cycle state-machine check**

This work completes the quantization portion of the planned “FIFO plus requantization” verification. The verification targets come from current `rtl/core/vibration_core.sv`. Core RTL, model, and ROMs were unchanged, and no physical-board operations were performed. Actual SymbiYosys runs passed both function proofs, function cover, serial-quantization BMC64, and its cover task. Both deliberately incorrect variants produced the expected counterexamples.

The claims cover exactly extracted arithmetic functions and the serial feature-quantization fragment. **The serial result is bounded evidence through 64 cycles, not an unbounded proof of the entire `vibration_core` or a functional proof of the whole model.** Other stages, memory arbitration, and connections at call sites still require existing whole-core simulation and other evidence.

**Binding the target to the real implementation.** [quant_extract.py](../formal/quant_extract.py) rereads production RTL on each run and extracts verbatim:

- The four functions `rne`, `sat12`, `sat16`, and `relu_quant`.
- The two combinational expressions `quant_rounded` and `quant_result`, and related register declarations.
- The three complete case branches `POWER_Q_INIT`, `POWER_Q_SHIFT`, and `POWER_QUANT`, including actual writes to `features[feature_index]`, debug outputs, and transitions to the next stage.
- State encodings, with checks of the four quantization working-register clear assignments in the original reset.

The generated `build/quantization_formal/generated/quant_extract.sv` contains these unchanged fragments. `extraction.json` in the same directory records source SHA256, generated-file SHA256, start/end lines, complete text, and SHA256 of each fragment. The script fails if required extraction boundaries are not unique or have changed. It also checks that the core source did not change during verification. Thus this does not prove a separately handwritten, approximately equivalent quantizer.

The core source SHA256 for this run was:

```text
1f9546be166957707f92a635e1e07834505db9b9d885d6fb3672cce6ac46872f
```

`vibration_core.sv` also retains a combinational `power_quant()` function, but the current feature datapath uses the serial state machine above. Checking only that helper function was not substituted for checking the actual serial implementation.

**Independent specifications and assertions.** [quant_harness.sv](../formal/quant_harness.sv) uses independent mathematical specifications:

| Target | Arbitrary inputs and assumptions | Checked property |
|---|---|---|
| Signed RNE | All signed 40-bit values; shift 0..39 | Equals the nearest integer after division by `2^shift`, ties to even; includes negatives and `-2^39` |
| `sat12` | All signed 40-bit values | Clamp below -2048 to -2048 and above 2047 to 2047; otherwise preserve input; correct output range |
| `sat16` | All signed 40-bit values | Clamp below -32768 to -32768 and above 32767 to 32767; otherwise preserve input |
| `relu_quant` | All signed 40-bit values; separate `HIDDEN_SHIFT=0` and 8 configurations | Output equals `clamp(RNE(value/2^HIDDEN_SHIFT),0,127)` |
| Serial feature quantization | Arbitrary unsigned 33-bit power, 8-bit shift 0..255, and feature index 0..15 | Actual features write and debug value both equal `clamp(RNE(power/2^shift),0,127)`; correct index and debug kind 5 |
| Serial control | First sampled clock is reset; subsequent reset/start arbitrary | No spontaneous result; uncanceled transactions complete in the specified cycle count; synchronous reset clears in-flight work and permits retry |

The production RNE function uses a signed quotient after arithmetic right shift and a two's-complement remainder. The specification first extends the input to 41 bits and takes its absolute value, then uses a positive quotient, reconstructed remainder, and comparison of twice the remainder with the divisor to choose rounding, before restoring the sign. The extra bit avoids overflow when taking the absolute value of the most negative input. The serial specification computes quotient and remainder directly; production RTL shifts `quant_work` over successive cycles and accumulates guard/sticky bits. Neither specification uses a production function as its answer.

Function shifts below 0 or above 39 are not covered; they are outside this verification contract for 40-bit input. Current deployed mean-removal, input-scaling, windowing, and DFT shifts all lie in 0..39. Hidden-layer checks explicitly cover 8, used by the current classifier, and 0, used by the separate spectrum configuration. Other `HIDDEN_SHIFT` parameter values are outside these two executed configurations.

The serial fragment's 33-bit input represents `[0,2^33-1]`. Every `POWER_Q_INIT` clears guard/sticky. Shifts 1..33 perform the corresponding number of right shifts; shift 0 or greater than 33 proceeds directly to output. For a nonnegative 33-bit input, shifting by more than 33 gives a value below 0.5, so RNE is 0. Output occurs `2+shift` clocks after transaction acceptance for shifts 1..33, and after 2 clocks otherwise, with a maximum of 35 clocks. Assertions check this exact count and completion deadline.

**Limitations of the serial cut boundary.** An outer wrapper accepts power, shift, and index while idle, stores them in the fragment's registers, and enters the actual `POWER_Q_INIT`. At completion, the real branch still transitions first to `NN_INIT` or `POWER_RE_MUL`; the wrapper then abstracts those out-of-scope subsequent operations as a return to idle. The initial reset is assumed; later reset can occur on any cycle, canceling the current transaction without requiring an output for canceled work.

Power, shift, and index form one arbitrary fixed tuple (`anyconst`) in each formal trace. These are symbolic checks over all the stated values, not a few manually selected examples, but later retries in the same trace use the same tuple. Consequently, this work **does not cover stale-value interference when power, shift, or index changes between adjacent transactions**. It also does not prove that preceding energy sums cannot overflow, the real ROM selection is correct, the complete FSM always reaches quantization, the downstream NN is correct, or the overall system cannot drop frames. Read-only review of the extraction boundary confirmed that these limitations match the harness.

**Executed results.** [quant.sby](../formal/quant.sby) defines the five positive tasks below. `prove` checks stateless-function equivalence using SMT base checks and induction; `bmc` checks only the specified clock depth. Counts 13 and 45 refer to explicit cover goals, not line, branch, or toggle coverage.

| Task | Mode / depth | Engine | Actual result |
|---|---|---|---|
| `functions_h8` | prove / 2 | smtbmc + Bitwuzla | PASS |
| `functions_h0` | prove / 2 | smtbmc + Bitwuzla | PASS |
| `functions_cover` | cover / 2 | smtbmc + Bitwuzla | PASS, 13/13 goals reachable |
| `serial_bmc` | bmc / 64 | ABC bmc3 | PASS, approximately 14.6 seconds |
| `serial_cover` | cover / 64 | smtbmc + Bitwuzla | PASS, 45/45 goals reachable, approximately 33 seconds |

The 13 function goals include even and odd half-way ties for both signs, the most negative value, large shifts of the most positive value, lower/upper 12-bit and 16-bit saturation, and zero, in-range, and saturated hidden-layer outputs.

The 45 serial goals include completion for every shift 0..33 (34 goals), plus out-of-range shift, both ties-to-even cases, rounding into saturation, maximum 33-bit power, exactly half and just over half for shift 33, the exported CWRU example `91 >> 2 → 23`, both successor branches at indices 0/15, and successful retry after mid-transaction reset (11 goals). These goals establish path reachability and prevent an output assertion from passing vacuously because no transaction occurs.

**Counterexample controls were also executed.** The runner creates incorrect variants only in separate build directories; production RTL and the normal extracted file remain unchanged. Both incorrect variants must return explicit FAIL and retain VCD counterexamples. FAIL is expected for these negative controls and does not mean the delivered RTL failed.

| Deliberately incorrect rule | Input actually found by the solver | Correct / incorrect result |
|---|---|---|
| Always increment when serial guard is 1, removing the even constraint | power=125, shift=1, index=3 | 62.5 should round to even 62; both debug and features become 63 in the incorrect variant |
| Signed RNE always adds 1 to the arithmetic quotient at a tie | value=-73851207680, shift=22 | -17607.5 should round to -17608; the incorrect variant outputs -17607 |

Counterexamples are in `build/quantization_formal/serial_tie_away/engine_0/trace.vcd` and `function_tie_away/engine_0/trace.vcd`. Negative controls directly use smtbmc + Bitwuzla. The local tool version had a reset-alias witness-conversion error when converting an ABC counterexample to SMT, so direct SMT generates replayable counterexamples. The runner does not treat tool ERROR as proof-discovered FAIL. The passing normal ABC BMC64 result does not require this counterexample conversion.

Tool versions for this run were Yosys `0.68+195 / 435977e97-dirty`, SBY `v0.68`, Bitwuzla `0.9.1`, and ABC `1.01` (compiled Sep 5 2026 06:19:43). The machine-readable report records full version strings, commands, source and harness fingerprints, per-task time and status, and cover/counterexample paths.

**Reproduction and deliverables.** Run the following command from the project root. It writes only to the separate `build/quantization_formal/` directory and reextracts current core source on every run. The complete command runs all five positive checks and both expected-failure controls; the overall runner exits 0 when they finish as expected.

```bash
cd "${PROJECT_ROOT}"
bash -c 'source scripts/env.sh; python formal/run_quant_formal.py --negative-controls'
```

The entry point is [run_quant_formal.py](../formal/run_quant_formal.py), and the final report is `build/quantization_formal/report.json`, retained locally if build evidence is omitted from publication. Together, `complete_positive_suite=true`, PASS for five positive tasks, and FAIL with `accepted_result=true` for both negative controls indicate that the complete flow finished as expected. Process exit alone is insufficient. If only some tasks are requested, the report lists only those tasks; that does not establish a rerun of the entire suite.

Each task directory retains SymbiYosys configuration, source copies, solver logs, and status; cover tasks also retain reachable traces. Rerun after source changes rather than reusing a conclusion tied to an old SHA. This evidence supports requantization rounding, saturation, and bounded-cycle control checks. It does not replace whole-chip ASIC signoff, physical measurements, or system validation.
