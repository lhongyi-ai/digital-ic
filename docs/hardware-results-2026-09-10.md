# UPduino 3.1 Physical-Board Results (2026-09-10)

One- and four-MAC versions each completed a 1000-frame digital replay of real waveforms. All returned scores matched the Python integer reference bit for bit. Each version generated and accepted 1,024,000 samples, with no overflow or protocol errors. Each final long-replay result is supported by two consecutive identical, unmodified Flash reads. A complete 4 MiB backup of the original Flash was independently checked and retained.

The run used the frozen CWRU neighbor-bin model: DC removal/Hann → 48 selected bins → 16 groups of neighbor-bin energy → INT8 16→16→3 network. The computer preloaded raw waveforms; the FPGA performed all DSP and inference. Inputs repeat nine existing real validation windows to form 1000 frames for stability and throughput testing. They are not 1000 independent samples, and the run neither reevaluates nor improves the existing 93.18% classification accuracy.

## Comparison with the same inputs, model, and nominal clock

| Metric | One MAC | Four MACs |
| --- | ---: | ---: |
| Correct physical replay | 1000/1000 frames | 1000/1000 frames |
| DC removal/windowing | 3,073 cycles | 3,073 cycles |
| DFT | 295,104 cycles | 73,848 cycles |
| Power and feature processing | 284 cycles | 284 cycles |
| Neural network | 950 cycles | 265 cycles |
| Total computation stages | **299,411 cycles** | **77,470 cycles** |
| Conversion at nominal 12 MHz | **24.951 ms** | **6.456 ms** |
| Peak frontend FIFO occupancy in normal replay | 1/2 | 1/2 |
| Place-and-route LC | 4,335/5,280 | 5,149/5,280 |
| Synthesis LUT4 | 2,942 | 3,754 |
| DSP / EBR / SPRAM | 1 / 19 / 3 | 4 / 25 / 3 |
| Place-and-route Fmax estimate | 21.93 MHz | 19.51 MHz |
| Internal-clock constraint for this run | 13.2 MHz, passed | 13.2 MHz, passed |

Four MACs give a computation-cycle speedup of **3.865×**, reducing cycles by **74.13%**. Speedup is below four because preprocessing, power processing, and some scheduling do not parallelize proportionally. DFT accounts for about 95.3% of four-MAC computation cycles; enlarging the network is not the first priority for performance optimization.

The four-MAC version meets the nominal target of ≤10 ms computation per frame, but uses 97.52% of LCs, leaving 131. One MAC also keeps up with the fixed input cadence used here. Four MACs are useful for an architecture comparison; additional features require resource checks rather than an assumption of ample space.

A sample is generated every 1000 FPGA cycles, without slowing down in response to core ready. A 1024-sample window spans 1,024,000 cycles, or 85.333 ms at nominal 12 MHz. Both versions completed these 1000-frame runs without sample loss. The physical HFOSC frequency was not measured, so 12 kS/s and millisecond conversions are not calibrated measurements. Cycle totals cover computation only, excluding window acquisition, queuing, Flash loading/writeback, and host transfers. Full physical first/last-sample-to-result latency has no independent timestamps yet. The frontend FIFO peak is not the peak occupancy of every system buffer.

Timing and resources are static tool results; cycles and logs were read back from the physical board. Tool-estimated Fmax is not an on-board frequency sweep, and DSP count does not establish power consumption.

## Overload and recovery

Predicted conditions were saved first, then the same one-MAC firmware received four frames at one sample every four cycles. Results exactly matched the prior RTL-derived prediction: 4096 generated, 3074 accepted, 1022 overflowed, and FIFO occupancy reached 2/2. Completed frame IDs were 0, 1, and 2, with scores still bit-exact. Error flag 0x28 denotes overflow and a trailing-frame wait timeout, with no extra error bits.

The normal acceptance entry point correctly rejected this incomplete result; its original manifest remains failed. The separate [overload verification record](../measurements/2026-09-10-upduino31/overload-verification.json) checks whether errors match expectations. It cannot turn overload into a no-loss pass. The same one-MAC firmware was then reconfigured with normal input, and all five frames/5120 samples passed. This is recovery after restarting, not automatic rate adjustment or recovery without reset.

Finally, four-MAC firmware and the frozen model were reinstalled and passed another five-frame check with two unmodified readbacks. The board retains that committed log and will not overwrite it automatically on reset; the next run must be explicitly initiated through the restricted hardware entry point.

## Fixes and retained failures

1. Official PCB inspection corrected the Flash MOSI/MISO mapping. The design uses internal HFOSC rather than relying on an unconfirmed external-clock jumper.
2. Flash remained asleep after initial configuration, a condition missing from the original model. AB wake and a wait were added, and the simulation model now starts asleep. Checks cover direct wake, deliberate sleep, and reset recovery.
3. The first readback sessions for both long replays showed byte-alignment anomalies; JEDEC reads also had leading bytes. The revised entry point rejects such results and obtains two consecutive identical unmodified reads. The underlying USB/FTDI cause remains unresolved. The retry policy improves detection and recovery but does not establish a driver fix. Original failed files were neither stripped of bytes nor overwritten.

Sources and failed-run directories are in the [pin, clock, and Flash notes](hardware-pinout-clock.md). The four-MAC long replay uses a read-only recovery record linked to the original failed attempt as the same physical run, without double-counting.

## Reproducible evidence and remaining scope

- [Machine-readable comparison](../measurements/2026-09-10-upduino31/architecture-comparison.json): firmware, model, input, result-manifest hashes, and metrics.
- [One-MAC 1000 frames](../measurements/2026-09-10-upduino31/l1-1000/manifest.json), [four-MAC 1000-frame readback recovery](../measurements/2026-09-10-upduino31/l4-1000-readback-recovery/manifest.json), and [final board state](../measurements/2026-09-10-upduino31/l4-final-5/manifest.json). Each directory includes raw reads, operation records, and a driver snapshot.
- The [current status index](../artifacts/evidence/current-status.md) checks saved evidence read-only, distinguishing old single-read records, dual-read records, and failures. Expected overload failure is covered by the dedicated report above.
- The full Python regression passed 229 checks. One status-display check was subsequently added, and the final readback/status subset passed 65 checks. The sets overlap and must not be added. After the Flash fix, 20 system simulation runs passed 22 HDL cases across replay, SEN1, and FCL1 paths.
- SEN1 and FCL1 one-MAC firmware passed renewed place-and-route, but ADXL345 hardware was not available. Physical acquisition, calibration, noise, repeated installation, and the field model remain unfinished. SEN1/FCL1 currently use an external 12 MHz clock; jumper and clock configuration must be confirmed before use. This replay's internal-clock assumptions do not apply directly.
- Actual clock frequency, electrical SPI waveforms, cold power-cycle startup, power, and complete end-to-end latency remain unmeasured. This round did not rerun a full release, retrain frozen models, or rerun the existing test set.

Daily development uses the [quick/module/release entry points](workflow-efficiency.md), retaining experiments under new run IDs. Hardware operations go through `scripts/run_hardware_replay.py`. All physical-board records reside in `measurements/2026-09-10-upduino31/`.
