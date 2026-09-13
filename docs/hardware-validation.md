# Physical-board and sensor acceptance

These procedures are for execution after real hardware is connected. On 2026-09-10, UPduino 3.1 identification, a complete backup, 1000-frame replays for both one and four MACs, overload detection, and restart recovery were completed. Results and measurement boundaries are in the [physical-board report](hardware-results-2026-09-10.md). Sensor operation, electrical timing, actual clock frequency, and power remain unmeasured. `.bin` or `.csv` files produced by Python/RTL peripheral models validate the toolchain only and do not replace the experiments below.

## Connections and initial startup

1. Confirm the UPduino revision, iCE40UP5K device, Flash capacity, and soldered headers. External-clock firmware targets v3.x, SG48, and a 12 MHz oscillator, with the OSC jumper connected to GPIO20. Replay can instead select internal HFOSC/4 without that jumper; time and sample rate are then nominal only. Use the [verified PCB and startup notes](hardware-pinout-clock.md) for Flash pins. The v3.0 GND/12 MHz silkscreen swap is documented officially; do not rely only on the silkscreen. [Official pins and errata](https://upduino.readthedocs.io/en/latest/features/specs.html)
2. Read JEDEC ID, back up the original configuration, and confirm capacity covers at least address `0x320000`. `configs/upduino-reference.json` is only a 4 MiB reference configuration and does not itself establish the actual board's properties.
3. Use a Digilent Pmod ACL (410-097, ADXL345) with its interface fitted, or an ADXL345 module explicitly supplied with soldered headers. Pmod ACL2 uses a different sensor and is not a direct substitute. [Official Pmod ACL page](https://digilent.com/shop/pmod-acl-3-axis-accelerometer/)

Reference sensor wiring follows. UPduino numbers are PCF/GPIO numbers, not header positions counted from the top.

| Sensor signal | UPduino signal |
| --- | --- |
| VCC | 3.3 V |
| GND | GND, common ground |
| CS | GPIO 23 |
| SCLK | GPIO 25 |
| SDI / MOSI | GPIO 26 |
| SDO / MISO | GPIO 27 |
| INT1 / DATA_READY | GPIO 32 |

Firmware first reads DEVID and requires `0xE5`, then sets full resolution, ±2g, normal power, FIFO bypass, and INT1 DATA_READY. SPI uses mode 3 with six main-clock cycles per half-period; a 12 MHz main clock produces 1 MHz SCLK. [ADXL345 datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/ADXL345.pdf)

Status outputs `done/error/running` are GPIO 21/12/13 respectively. These are ordinary GPIOs, not the on-board RGB LED. Observe them with a logic analyzer or suitable LEDs with current-limiting resistors.

## Public-data replay

First complete `make replay-image` and the selected model's complete build. The model SHA256 in the host input image must match the model compiled into the bitstream.

Sequence: back up Flash → write the new project configuration → write the input partition → erase the log partition last and release reset to start → wait for completion → read logs. Each `iceprog` command releases reset when it ends, so log erasure must be the final startup action, preventing old firmware from running prematurely between commands. Do not use chip erase for configuration writes; constrain each operation to its own partition.

Formal acceptance records should include board/Flash identification photos, wiring, bitstream and model SHA256, input image, actual readback logs, and per-frame reference comparisons. Run five frames first, then 1000 frames at one sample per 1000 FPGA cycles; with this internal clock the rate is only nominally 12 kS/s. One- and four-MAC versions use the same input and model. Record `error_flags`, generated/accepted sample counts, output-frame count, and overflow count. Overload experiments use separate logs and retain error evidence.

Existing Flash behavioral simulations checked protocol and commit order. Real SPI timing, supply conditions, and the particular Flash device still require physical validation.

## Static two-point calibration

Fix the sensor, choose one measurement axis, and collect new recordings with that axis oriented toward +g and -g. Do not fabricate zero measurements for the other two axes; a single-axis CSV contains only its corresponding axis column.

Compute:

`offset = (mean_plus + mean_minus) / 2`

`counts_per_g = (mean_plus - mean_minus) / 2`

Export Q8 offset and Q20 gain. RTL uses the same ties-to-even rounding as Python and outputs mg. After deployment, validate mean error and RMSE using new +g, -g, and near-0g recordings. Analysis tools refuse to reuse fitting recordings as validation recordings.

Defaults OFFSET=0 and GAIN=4096000 only represent nominal 256 counts/g and must not be described as calibrated. Save the actual fit JSON, build parameters, and calibration-firmware hash in the same experiment directory.

## Noise, interface, and reliability

Remount the sensor for each round, then perform 100, 400, and 800 S/s ODR measurements, for at least three rounds. Keep the fixture, orientation, supply, and documented environment consistent.

| Item | Actual evidence to retain |
| --- | --- |
| Stationary noise | Raw CSV, mean, standard deviation, Welch PSD, ODR, calibration parameters |
| SPI electrical behavior | Oscilloscope screenshots, 3.3 V levels, CS/SCLK/MOSI/MISO relationships, setup/hold times |
| Continuous acquisition | At least 10 minutes of statistics: observed samples, output drops, visible overruns, longest service interval |
| Time reconstruction | First/last service times, 32-bit timer wraps, unrepresentable-interval count |
| Repeatability | New raw recordings after remounting and output from the same analysis script, rather than a single comparison |

By default, raw data is saved for the first 30 seconds while counters continue for 10 minutes. This does not mean all raw samples for 10 minutes were saved. Each SEN1 record contains raw int16 and a uint16 service-time delta, in units of four FPGA clocks; unrepresentable deltas are flagged. Reports must include full-run counters, rather than infer loss-free operation from only the first 30 seconds.

Service time is when the FPGA finishes reading sensor registers. Its interval is not the sensor ADC's aperture jitter. The number of observed sensor-overrun bits is also not an exact count of lost samples. When service anomalies occur, mark uniformly sampled PSD assumptions as invalid.

Software PSD and on-board selected-bin spectra are different outputs. Software Welch PSD uses windowing/averaging and per-Hz normalization; the board reports fixed-point selected-bin `Re²+Im²`. Without a calibrated shaker or reference accelerometer, do not claim absolute frequency-response calibration.

## Physical measurement report template

A round directory such as `measurements/round01/` should record date, board revision, sensor model, mounting, supply, ODR, axis, firmware/model/calibration hashes, acquisition duration, raw records, analysis output, oscilloscope screenshots, anomalies, and retry reasons. Raw acquisition and instrument files omitted from publication remain local.

Keep unperformed items marked “not measured” until hardware is connected and the experiment is executed. This project does not require deliberately damaging a motor or attaching weights to rotating parts.
