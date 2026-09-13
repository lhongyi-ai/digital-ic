# Offline Verification of the Independent N256 Field-Sampling Classifier Interface

`rtl/io/sensor_classifier.sv` has been implemented and simulated offline with one and four MAC lanes: **all eight cocotb tests passed; 42 outputs were checked against the integer reference, of which 38 were accepted downstream**. The other four outputs remained stalled after checking and were subsequently withdrawn by cancellation events; they must not be counted as delivered classifications.

This is interface and numerical verification driven by synthetic data. The default model is `build/field_fixture/trained/model/model.json`, with `training_status` of `synthetic_fixture_not_for_deployment`. There is no actual ADXL345 sampling, physical SPI transfer, field classification accuracy, or board-deployment evidence here. The original CWRU N1024 model, core implementation, sensor spectrum, and board top were not modified for this module.

## Input, Output, and Cancellation Contract

Parameters are `LANES=1/4`, `MODEL_DIR`, and `HIDDEN_SHIFT`; windows are fixed at 256 samples, with 16 single-bin power features, 16 hidden units, and three classes. Model and ROM must match this independent profile; CWRU model files are not interchangeable.

- `in_sample` is signed16 raw accelerometer counts. The core actually receives `clip(raw,-1024,1023) * 32`, matching `vibfpga.field.raw_to_core()`. No mg calibration conversion occurs here.
- `in_valid` is a sample event. Acceptance requires `in_valid && in_ready` and no cancellation event. If the source emits a sample while `in_ready=0`, that is a lost sample and triggers cancellation of the entire pending batch. A legal upstream source waiting for ready must first withdraw valid, rather than holding the same valid sample until ready.
- A cycle with `gap=1` cancels with priority and discards any sample even if `in_valid=1`. Explicit gap and source overrun clear the core, partial window, and timestamp queue on the same edge and withdraw every complete undelivered window, **including an output already at `out_valid=1` and `out_ready=0`**.
- The first sample of a new window can be accepted on the next clock after cancellation; fragments across a loss are never joined into 256 samples. Allocate a frame ID when accepting each window's first sample; canceled IDs are not reused. Ordinary `rst` clears frame IDs and every cumulative counter. IDs and counters are uint32 and eventually wrap at their bit width.
- During output stalls, ID, logits, class, error, stage cycles, and both timestamps stay stable except for ordinary reset, explicit gap, or overrun cancellation.
- `out_error` indicates only a core arithmetic error in a complete classification frame. Cancellations are observable through cumulative counters; canceled frames produce no placeholder classification.

`in_service_cycle` is an upstream-provided uint32 service timestamp. The module stores the first and last timestamp of each complete window unchanged, without sorting, and therefore supports timer wrap. **It does not infer missing samples automatically from timestamp differences**; upstream must provide gap for known loss. When output is invalid, the timestamp FIFO data bus has no required interpretation.

## Buffering and Cumulative Counters

The module retains at most two complete undelivered windows, with a two-slot timestamp FIFO of 64 bits per slot. `busy` means at least one complete window remains undelivered and excludes a window containing only partial samples. `partial_samples` is the current partial window's `0..255` sample count.

Ready depends on the module's window count, partial-window state, and same-cycle output-release credit, avoiding a combinational loop of `overrun → core reset → core ready → overrun`. Every externally announced acceptance asserts that the underlying core is actually ready. Assertions also check metadata FIFO space at window completion, matching metadata at core output, and zero core framing errors. When both slots are full, delivering an old output on an edge can coincide with accepting the next window's first sample.

|Counter|Meaning|Cleared by gap/overrun?|
|---|---|---|
|`accepted_samples`|Total samples actually accepted and sent to the core; later cancellation does not subtract them|No|
|`dropped_samples`|Samples actually present but discarded on the cancellation-event cycle|No|
|`canceled_frames`|Complete undelivered windows withdrawn by the event, plus any nonempty partial window|No|
|`clip_count`|Accepted samples strictly below -1024 or above 1023|No|
|`protocol_errors`|Cumulative cancellation events; simultaneous explicit gap and overrun count only once|No|

Previously accepted samples invalidated by cancellation are not added again to `dropped_samples`; their transaction loss is represented by `canceled_frames`. `gap=1` with no sample increments the event count but not dropped. Only ordinary `rst` clears all counters. `gap` should be an event pulse; if held high, every high-level clock edge is a cancellation event.

## Actual Cases and Results

|Case|Numerical and protocol checks|One MAC|Four MACs|
|---|---|---|---|
|12 continuous complete windows|Six inputs repeated twice: zero, constant, phased coherent-bin sine, off-bin sine, clipping boundaries/extremes, and seeded random data. Every frame's logits/class/error match `raw_to_core + classify`; IDs and both timestamps match one-to-one|PASS|PASS|
|Input pauses and output stalls|Deterministic random input pauses; output stalls of 0..60 cycles; no lost, repeated, or incorrectly reordered samples|PASS|PASS|
|Timestamp wrap|Window with first timestamp `4294963200` and last `3820904`, plus recovery windows crossing other uint32 boundaries|PASS|PASS|
|Clipping count|3072 inputs in the continuous test, 304 clipped; exact endpoints -1024/1023 are not counted as clipping|PASS|PASS|
|Source overrun after a long output stall|Stall for 30000 cycles; force a sample while two complete windows are undelivered; cancel both old windows and verify all values for new window ID 2|PASS|PASS|
|Same-edge release/acceptance|With both slots full, deliver an old output and accept the new window's first sample simultaneously; no overrun; subsequent timestamps/results for both windows are correct|PASS|PASS|
|Explicit gap|Cancel one stalled complete output and a 37-sample partial window together; discard the same-cycle sample; raising out_ready simultaneously cannot deliver the canceled frame|PASS|PASS|
|Gap with no sample|Increment only the event count, not dropped or canceled when no transaction exists; the next complete frame retains increasing IDs|PASS|PASS|
|Ordinary reset|Cancel a 13-sample partial window that has already clipped samples, clear all cumulative counts, and restart subsequent window IDs at 0 with correct results|PASS|PASS|

Each configuration actually checks 21 outputs and accepts 19. The long-stall test ends at accepted=1536, dropped=1, canceled=2, clip=0, events=1. The explicit-gap test ends at accepted=805, dropped=1, canceled=2, clip=0, events=2. Tests use `--assert -DVIB_ASSERT`, including the cancellation exception to output-stability assertions.

Simulation inputs can run much faster than the physical 800 Hz rate to create buffering pressure. Service timestamps are independent test-input values and must not be treated as measured ADXL345 timing. Core stage cycles for normal simulated results are:

|Configuration|PRE|DFT|POWER|NN|Total core computation cycles|
|---|---:|---:|---:|---:|---:|
|LANES=1|769|24640|130|950|26489|
|LANES=4|769|6184|130|265|7348|

At the target 12 MHz clock, these correspond to approximately 2.207 ms and 0.612 ms. They include only core computation, excluding complete-window capture, queue waiting, Flash writing, and output stalls. They are not measured end-to-end latencies and do not establish resource/timing acceptance for a new board top containing this module.

## Reproduction and Evidence Files

```bash
source scripts/env.sh
python sim/run_sensor_classifier.py
```

The default runs both lane configurations; `--lanes 1`, `--lanes 4`, and explicit `--model` are also supported. Each run first removes the previous completion report, requires all four tests to execute with no XML failure/error/skipped entries, then verifies that source and all model files stayed unchanged before writing the summary.

- `build/sensor_classifier_l1/regression.json` and `build/sensor_classifier_l4/regression.json`: 4/4 tests, summary of 21 checked outputs, parameters, model/source hashes, and evidence limits.
- `manifest.json` in each directory: model path, SHA256 of every model file, SHA256 of compilation/reference sources, and simulator version.
- `case_continuous.json`, `case_overrun.json`, `case_gap.json`, and `case_reset.json`: each checked output, reference logits, raw signed16 input hashes, timestamps, and final cumulative counts.
- `results.xml`, `simulation.log`, and `compile.log` in the same directories: actual execution results and logs.

These build outputs are retained locally when omitted from the publication. Default fixture model SHA256 for these tests:

```text
7881d621cc8075cbc2e280771a628f4662c234011830650dbf2fcc5ec12a61fe
```

Wrapper SHA256:

```text
36f5ae97676910d1f2ad14ca947ae61beee95cffbda8529ac4345d4fb224d254
```

## Outside This Report's Scope

Training on real sensor data, separability on real machinery, integration from SPI acquisition to this module, Flash classification logs, place-and-route for a deployment top, and physical measurements require their own evidence. This report also does not claim a formal proof of the entire classifier, exhaustive coverage of every possible timing pattern, or full-period simulation of UINT32 cumulative-counter wrap.
