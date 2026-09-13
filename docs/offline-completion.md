# Offline Completion Audit Against the Project Plan

This work reviewed the repository against the user's supplied overall plan and completed missing items that did not require UPduino hardware. Scope includes the public CWRU-record pipeline and the planned separate ADXL345 field-model/continuous-classification pipeline. It does not use the subsequently discussed impact-response assembly-validation approach, and no physical device was connected, programmed, or measured.

## Completed additions

| Previously missing item | Delivery in this round | Actual verification |
| --- | --- | --- |
| Dedicated NN tie and overflow tests | Eight verification-only models, two MAC configurations; signed INT32 boundaries in both layers, minimum-index tie handling, and recovery after errors | 16 HDL tests passed, 72 outputs and 1368 final accumulator values checked; [details](nn-edge-verification.md) |
| Formal requantization checks | Functions and actual serial-quantization states extracted exactly from current RTL, independent mathematical specifications, explicit assumptions/depth | Two function proofs, two cover runs, and BMC64 passed; 58 covers reached; both faulty variants produced counterexamples; [details](quantization-formal.md) |
| HDL coverage | Verilator database, LCOV, source annotations, every unhit point and its explanation | 37 tests passed; four configurations achieved line 87.36%–90.32%, branch 85.59%–87.66%; no false 100% or FSM-coverage claim; [details](rtl-coverage.md) |
| Protocol gaps found in coverage review | First-sample last, same-ID drain until late last, high frame IDs, and FFFFFFFF→0 wrap | Independent supplemental tests in four configurations; new cases are not directly added to old coverage percentages; [details](protocol-edge-verification.md) |
| Field-model training entry point | ADXL800Hz/N256 manifests, record/installation-batch isolation, quality checks, baselines and MLP training, INT8/ROM export, and separate testing after freezing | Complete simulated-fixture workflow passed; 15 Python tests cover isolation, incorrect timebases, corruption, freezing, and interrupted-evaluation protection; [details](field-training.md) |
| Continuous field-classification RTL | Raw counts → shared DSP/INT8 core, two timestamp slots, window IDs, cancellation/recovery, and counters | Eight HDL tests across two MAC configurations passed, checking 42 outputs; [details](field-classifier-verification.md) |
| Field-result storage and readback | Separate FCL1 firmware, four-SPRAM result buffer, CRC, Flash partition protection, completion marker written last, and host parsing | Six SPI pin-level tests per MAC configuration passed; bit-exact normal/drop recovery, device error/timeout, interrupted logs, and final-byte protection for a complete 128 KiB region; 54 parser tests passed; [details](field-system.md) |

The final Python regression in this round passed **126 tests**. Both original CWRU models and ROMs remain unchanged. The original neighbor-bin test report received read-only integrity verification; test waveforms were not reopened for model selection. Existing DFT/MLP, four-configuration 1000-frame regressions, fixed-cadence sampling, CWRU static builds, and sensor-acquisition/calibration software remain intact.

## Resource checks changed the field-firmware choice

The new complete one-MAC field firmware completed place-and-route with 5125/5280 LC, one DSP, ten EBR, and four SPRAM; the 12 MHz target passed, with estimated Fmax 19.12 MHz. The four-MAC version requires 5852 LCs, exceeding UP5K capacity. The complete field version therefore currently uses one MAC. Four-MAC field computation and interfaces were simulated, but no usable complete field bitstream exists.

This choice still meets the field task: one-MAC computation takes 26489 cycles per window, about 2.207 ms, while acquiring a 256-sample window takes 320 ms. The original CWRU four-MAC version completed place-and-route with its own peripheral configuration. Resource numbers from different top levels must not be mixed.

Three additional resource experiments without production-RTL changes reached a best result of 5619 LCs, still above 5280. The one-MAC field firmware that passed system verification and place-and-route is therefore retained. Experiment report: `build/field_area_experiments/report.json`.

These new builds use a model trained on simulated data and have limited logic margin. A real field model requires fresh synthesis and place-and-route; current success does not imply every new weight configuration will automatically fit.

## Items still requiring hardware or real data

1. Confirm the exact UPduino revision, 12 MHz clock, Flash device, and wiring; program it and perform real-waveform replay/result readback.
2. Perform ADXL345 raw acquisition, positive/negative gravity calibration, stationary-noise tests at 100/400/800 Hz, oscilloscope SPI-level/timing checks, ten-minute reliability testing, and at least three reinstallations.
3. Define the actual apparatus and reproducible states, collect independent recordings per class, train/freeze/evaluate a real field model, export its ROMs, and reverify. Such raw data is currently absent and cannot be replaced by mathematical sine fixtures.
4. Measure sustained physical operation, actual classification performance, and power. No field-fault accuracy or power measurement currently exists.

ASIC standard-cell synthesis and OpenROAD/STA were explicitly extensions beyond the original four-week acceptance plan. Unbounded full-core formal equivalence, illegal-FSM-state injection, envelope spectra, and JTAG are not claimed complete. Existing SPI programming is not JTAG, and static FPGA timing is not ASIC signoff.

## Reproduction and evidence entry points

After `source scripts/env.sh` at the project root:

```sh
make nn-edges
make quant-formal
make coverage
python scripts/test_protocol_edges.py
make field-sim
make field-board
python -m pytest tests --junitxml=build/offline-completion/python-results.xml -q
python scripts/evaluate_neighbor.py --verify
python scripts/collect_offline_completion.py
```

See [field training](field-training.md) for initial fixture creation, formal-data templates, and freeze rules. Training commands cannot overwrite existing fixtures. Real-model entry points and simulated tests are clearly distinguished.

Machine-readable index for this round: `build/offline-completion/summary.json`. It checks reports against source/model SHA values, Python XML, individual statuses, and new bitstream hashes, and rechecks saved FCL1 logs with the current parser. Raw reports, simulation logs, formal counterexamples, and build timing remain in their respective build directories.

Index snapshot suitable for retention with source: [offline-completion-2026-09-07.json](../artifacts/evidence/offline-completion-2026-09-07.json).

The SEN1 storage optimization and upgrade plans already present before this work are retained. This round adds separate field firmware without overwriting those changes or modifying the frozen CWRU core and weights.
