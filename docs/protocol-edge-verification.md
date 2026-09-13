# Independent Supplemental Tests for Three Frame-Protocol Gaps

These tests address three protocol scenarios identified by the coverage review as not yet directly verified. They run the existing `vibration_core.sv` and `vib_coeff_rom.sv` directly. The test file is `sim/test_protocol_edges.py`, with entry point `scripts/test_protocol_edges.py`. All builds, simulation logs, and results are written only under `build/protocol_edges/`.

## Test Scope

|Scenario|Input sequence|Required result|
|---|---|---|
|End on the first sample|Assert `in_valid` and `in_last` on the first beat, then send a complete valid frame immediately after the actual handshake|Cancel the incomplete frame and raise the protocol-error total to 1; the following complete frame is bit-accurate and the count stays at 1|
|Continue discarding after a missing end marker|Accept N=1024 consecutive samples with one `frame_id` and `in_last=0` throughout; send another 18 nonfinal samples with idle cycles interspersed, then one late `in_last=1` beat|Raise exactly one error on beat N; extra samples and the late end marker add no error or result; a subsequent complete frame with **the same ID** recovers correctly without relying on an ID change to leave discard state|
|High frame-ID bits and wrap|Consecutive complete frames use hexadecimal IDs `80000000, f1234567, ffffffff, 00000000, 80000001, 00000001, 7fffffff`|Preserve all 32 ID bits and output strictly in accepted-input order, including `ffffffff→0` and decreasing numeric values; each frame's logits, class, and intermediates are correct|

Each configuration includes nine valid frames and two canceled incomplete frames. Total accepted input samples must be `9×1024 + 1 + 1024 + 18 + 1 = 10260`. The error count must equal exactly 2; checking merely “nonzero” is insufficient. Every output may consume only the next frame in the expected queue. After the last result, observe a full computation duration plus 32 cycles to detect extra outputs or residual computation.

## Numerical Reference and Handshake Checks

Tests use only existing frozen validation vectors `replay_000` through `replay_008`, without reselecting test-set samples or training a model. Baseline model/vector directories are `artifacts/model/` and `artifacts/vectors/`; three-neighbor-energy directories are `artifacts/model_neighbor/` and `artifacts/vectors_neighbor/`. The nine frames come respectively from recordings 107, 120, 132, 171, 187, 199, 211, 224, and 236. Each is validation window 2, sample range `[2048,3072)`. Every configuration report retains original provenance, input-HEX SHA-256, and SHAs of model, RTL, ROM, and reference code.

First recompute frozen inputs using `vibfpga.fixed.classify` and confirm agreement with reference values in existing JSON. Then compare RTL debug outputs item by item: mean, all 1024 windowed samples, all real/imag values, 16 powers, 16 features, 16 hidden values, and three logits. The result interface additionally checks the complete ID, three signed logits, class, `out_error=0`, and the sum of stage cycle counters. Numeric IDs do not index reference data; the reference queue advances only in expected actual acceptance order.

The output is blocked for seven out of every 23 cycles, with an additional guaranteed seven-cycle block when each new result first appears, checking stable `out_valid` and the complete payload. The latter ensures every configuration encounters backpressure despite differing compute times; periodic blocking alone could miss every result. The input driver holds the same beat when `in_ready=0`. Reports require actual input and output stalls. Compilation enables `--assert` and `VIB_ASSERT`, so existing core assertions run too.

The driver updates signals at the falling edge. The scoreboard reads stable signals 2 ns later; recorded handshakes will be accepted by the core at the immediately following rising edge. The clock period is 10 ns. No reset or asynchronous cancellation occurs during these scenarios, and the driver does not withdraw signals between the two sampling points. This sampling convention is valid for this test but does not automatically apply to benches with asynchronous cancellation or rising-edge input driving.

## Reproduction and Evidence

Run from the project root:

```sh
source scripts/env.sh
python scripts/test_protocol_edges.py
```

The complete entry point runs both frozen models×`LANES=1/4`, for four configurations. To rerun a single configuration:

```sh
python scripts/test_protocol_edges.py --model neighbor --lanes 4
```

A single-configuration command marks the summary as an incomplete suite. For a four-configuration summary, run the complete unfiltered command last. Each configuration directory contains `build.log`, `simulation.log`, `results.xml`, and `report.json`; the aggregate is `build/protocol_edges/report.json`. The entry point requires cocotb XML to contain exactly one passing test with no failure or skip, and verifies that tested sources, frozen models, and vectors remained unchanged throughout. Build evidence omitted from this publication remains local.

## Actual Results

The complete four-configuration run finished on 2026-09-07 Pacific time. The aggregate records UTC `2026-09-08T01:39:28.580428+00:00` and `complete_four_configuration_suite=true`. All four configurations passed, each with 10,260 input handshakes, nine bit-accurate outputs, nine complete intermediate-value frame checks, and exactly two protocol errors. Across the suite, 36 valid-frame outputs were checked with none missing or duplicated.

|Frozen model|LANES|Actual input-stall cycles|Actual output-stall cycles|Scoreboard observation cycles|Result|
|---|---:|---:|---:|---:|---|
|baseline, BANDS=1|1|408114|67|1029883|PASS|
|baseline, BANDS=1|4|110377|86|285485|PASS|
|neighbor, BANDS=3|1|1195634|67|2998603|PASS|
|neighbor, BANDS=3|4|307893|115|779417|PASS|

Tools were Verilator `5.051 devel rev v5.050-312-gb1c06fdb0 (mod)` and cocotb `2.1.0`. Summary `tools.python=3.12.14` is the entry-point Python version. Simulation logs explicitly show that cocotb loaded Python dynamic library `3.12.10`. Both are preserved in the original evidence; do not mislabel the entry-point version as the embedded simulation version.

Tested `vibration_core.sv` SHA-256: `1f9546be166957707f92a635e1e07834505db9b9d885d6fb3672cce6ac46872f`. Baseline model JSON: `a43243dfb2045cc455093c465d646b432a81eef3bce90691cf41250f53daa588`. Neighbor model JSON: `12abcdfd4a9072903915135e771c1fb9be0d430275e28acbf545660e1d7fa117`. Each configuration reports `source_inputs_unchanged=true`; its `input_sha256` lists every file.

## Limits of the Conclusion

This is independent, targeted simulation of three specific protocol scenarios, not a formal proof over every possible stream. It does not cover mid-run reset, arbitrary frame lengths/ID sequences, illegal-state injection, or physical hardware behavior; other regressions support their own declared scenarios. Post-output observation is also finite.

These tests did not enable Verilator coverage, merge or modify previous coverage databases/scripts/reports, or recompute previous percentages. They add evidence that the three scenarios actually ran, not permission to rewrite original coverage as 100%. No UPduino programming or physical measurement occurred.
