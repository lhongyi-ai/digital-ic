# Architecture comparison under matched conditions and physical-board measurements

This is an operating plan and an entry point for blank records; it contains no measured power results. Use the same UPduino board throughout and associate every value with the actual input, firmware, and instrument.

## 1. Separate the two comparisons

| Comparison | Keep fixed | Main variable | Key criteria |
|---|---|---|---|
| Before/after memory optimization | Same sensor top level, 800 S/s, N256, bins/integer arithmetic, 12 MHz, raw count, input, tool versions, and build seed | 64 B spectrum buffer and memory arbitration | Same data and protocol, reduced SPRAM; record actual logic, timing, and stalls |
| One MAC/four MACs | Same CWRU file, frozen model hash, widths, 12 MHz, input cadence, output mode, test duration, and board supply | Parallelism | All logits bit-exact; report throughput, latency, and energy separately |

Do not treat N256 sensor firmware and N1024 CWRU firmware as a single-variable comparison. Do not change the model/features and memory architecture together and attribute all improvement to one optimization.

“Identical input” means bit-identical input in simulation and digital replay. Two physical-sensor mechanical experiments cannot guarantee bit-identical input. Fix mounting, excitation, and sampling settings first, perform alternating paired experiments, and report the input differences. If a strict board-level memory-architecture comparison is required, use an external SPI digital test source to replay the same recording. Two hand taps or two free-vibration runs are not identical inputs.

## 2. Area and timing

Record packed LC/5280, EBR/30, SPRAM/4, DSP/8, placement/routing tool and version, and SHA256 values for parameters, sources, model, and bitstream. List LUT4 and LC separately to avoid mixing accounting conventions.

Compare complete top levels. Fix the 12 MHz constraint and use the same seed; retain failed builds. If routing stability needs evaluation, use a predefined common set of multiple seeds. Fmax is a tool estimate, not the maximum usable frequency measured on the board. Off-chip SPI setup/hold requires separate validation.

## 3. Latency and throughput

For each traceable frame, record `run_id, frame_id, first_accept_cycle, last_accept_cycle, core_done_cycle, result_valid_cycle, packet_sent_cycle`. On the current path without a result queue, `result_valid_cycle` is when the core output becomes valid; on a future queued path, it means successful enqueueing of the complete result. `core_done_cycle` always means core completion. Handle counter wrap using extended bits or a reliable epoch. Current logs do not yet contain every field; a separate debug build or future interface implementation is needed. Do not invent other timestamps from core active-cycle counts.

- Processing latency = (result_valid − last_accept)/fclk, including queueing and result-delivery waiting.
- First-sample latency = (result_valid − first_accept)/fclk.
- Steady-state throughput = complete valid frames within the specified measurement interval / interval duration in seconds.
- Report host display latency separately, including median, p95, p99, maximum, and test environment. It is not an FPGA deadline.

Retain worst-case values and abnormal frames. Mark first sample, last sample, and result with debug GPIOs, then cross-check counters using an oscilloscope or logic analyzer. Debug builds can differ in resource usage and switching activity; identify them separately from power-comparison firmware.

## 4. Board-level power measurement boundary

The most reproducible primary metric measures V(t) and I(t) on the UPduino's sole input-power path. Use the same supply topology and USB connection state. A sensor powered from the UPduino's 3.3 V rail is included, along with FTDI, regulator losses, and other circuits on that path. Record visible LED states. Avoid simultaneous USB and bench-supply power that introduces unmeasured branches or backfeeding.

Name the result “UPduino board input power/energy, including listed peripherals.” Only a separately measured FPGA supply rail may be called FPGA rail power. USB input power is not chip-core power.

At a fixed sampling cadence, compare average power and energy per valid result over a common wall-clock interval:

`E_total = integral(V(t) * I(t), dt)`

`P_average = E_total / duration`

`E_per_valid_frame = E_total / valid_frames`

Integrate discrete measurements using timestamps. Do not directly average power samples with nonuniform time spacing. If startup, acquisition, or Flash writes are measured, report each phase separately and retain total energy for the complete task.

An additional matched-idle calculation is allowed: `E_excess = E_total − P_idle * duration`. This is only the increment relative to that idle baseline, not an exact measure of FPGA dynamic energy. Idle noise may make the difference insignificant.

Faster four-lane computation does not establish lower energy, and removing one SPRAM block does not establish lower board power. If one-lane and four-lane designs run at the same frame rate, compare input energy over the same duration and number of valid results.

## 5. Instruments and repeatability

The user has confirmed access to a school-laboratory oscilloscope, bench supply, and multimeter. Complete the following measurements with those instrument types first; do not assume a current probe, differential probe, or automatic logging is available.

| Measurement | Connections and procedure with available instruments | Supported conclusion |
|---|---|---|
| Steady-state average board power | Program and verify firmware, then disconnect computer USB. Use a USB power breakout with verified pinout to connect bench-supply 5 V to board-side VBUS/GND as the sole supply. Verify rated input and current limit for the board revision; power the sensor from board 3.3 V. Measure load-side voltage with a multimeter. Prefer sufficiently resolved supply current readback; if needed, place the multimeter in series with the positive supply lead and measure voltage with an oscilloscope or second meter. | Total board input power including FTDI, regulator, and sensor; both versions must share the computer-disconnected state. |
| Average energy per frame | Prefer timestamped V/I export and integration, divided by valid results in that interval. If only steady-state averages are available, report an estimate of average power / valid frame rate and state the sampling method. | Mean energy per frame under matched conditions, not a single-frame transient waveform. |
| Latency and throughput | Debug firmware marks first sample, last sample, and result on GPIOs. Measure intervals with the oscilloscope and cross-check cycle counts. A two-channel instrument may measure groups using a common trigger. | Internal FPGA processing deadline, first-sample deadline, and result period, excluding host-display waiting. |
| SPI electrical timing | Use 10× probes and short grounds. Inspect CS/SCLK, MOSI/SCLK, and MISO/SCLK in groups at both sensor and FPGA receiving ends. Verify probe and scope bandwidth can resolve the reported margins. | Clock and chip-select intervals, plus data setup/hold margins. Screenshots must retain time scales and probe locations. |

If host connection is required to read results, use a power adapter that explicitly isolates computer VBUS while retaining required data and ground connections. Verify there is no second power path. Do not attach a bench supply to the same 5 V net while normal computer USB power remains connected. Verify first-time wiring against the actual board revision rather than guessing header positions from another UPduino revision.

Bench-supply display refresh and resolution may not capture millisecond computation pulses. The available instruments support average-power experiments, but resolving small differences depends on model and range. For transient current, borrow a current probe or suitable shunt/differential measurement setup, then follow these wiring precautions.

- An oscilloscope with an appropriate current probe, or a low-side shunt/differential measurement, can examine millisecond phase waveforms. Check shunt voltage drop and probe connections; never short a high-side supply using the oscilloscope ground clip.
- A logging bench supply, power analyzer, or multimeter is appropriate for steady averages. Record sample rate, range, accuracy, load-side voltage, and calibration status.
- A basic USB current meter with inadequate resolution or refresh rate supports only rough averages, not claims of microjoule-level per-frame improvement.

Allow thermal stabilization, then use at least three independent pairs in A/B/A/B/A/B order, adding more if practical. Keep input, run length, and measurement boundary identical, and retain every round rather than only the best. Report individual runs, mean, dispersion, and instrument uncertainty. If the difference is below resolution, conclude “no significant power difference detected.” Memory savings remain a separate engineering benefit.

## 6. SPI timing budget and measurements

[ADXL345 Rev G, Table 10](https://www.analog.com/media/en/technical-documentation/data-sheets/ADXL345.pdf) specifies maximum SCLK 5 MHz, at least 5 ns from CS falling to first SCLK falling, at least 5 ns from last SCLK rising to CS rising, at least 150 ns CS high between transactions, and at least 5 ns each for SDI setup and hold. Consult the datasheet for table conditions and voltage, and record actual measured levels and loads.

The current 12 MHz clock with six cycles per half-period produces 1 MHz SCLK, approximately 500 ns per half-period. A slow nominal clock does not automatically satisfy every constraint. In particular, measure the actual controller's inter-transaction CS-high interval; the generic SPI module alone does not guarantee every caller meets 150 ns.

Measure CS, SCLK, and MOSI at the ADXL345 pins, checking polarity/phase, setup/hold, and transaction spacing. At the FPGA, check MISO margin relative to the sampling edge. Include FPGA output delay, cable/level-shifter delay, sensor output delay, FPGA input path, and sampling setup in the budget. Retain actual short-wire connections and probe bandwidth/sample rate. Correct logic-analyzer decoding does not replace evidence of nanosecond timing margin.

## 7. Per-run record template

Use an experiment directory such as `measurements/upgrade/<run_id>/`, containing at least:

- Metadata: date, operator, board and sensor models, supply and wiring, mounting, ODR, and tool versions.
- Version: source/model/input/firmware hashes, build parameters, and every P&R result.
- Results: raw logs, parsed results, frame-by-frame numerical comparisons, error counts, and latency statistics.
- Measurements: raw timestamped voltage/current, integration interval, valid-frame count, oscilloscope screenshots, and instrument configuration.
- Conclusion: pass/fail/not measured, abnormalities, and retry reasons. Never overwrite failed raw records.

During board work, record specific instrument models, ranges, accuracies, sample rates, and probes to establish the smallest resolvable difference. Do not mark measurements as passing or fabricate power data before the physical board is available.
