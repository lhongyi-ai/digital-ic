# Standalone ADXL345 capture and SEN1 log

This image contains sensor SPI acquisition, fixed-point static calibration,
sampling-reliability statistics, a hardware selected-frequency monitor, and a
Flash logger. Three SPRAM banks retain raw records; the final 32 words of the
third bank now store the latest completed spectrum. Spectrum writes take
priority; pending raw-record second words wait until that port is available.
`--no-spectrum` builds a smaller logger variant.
Neither sensor image exposes a vibration-classifier output.
No physical board, sensor, motor, calibration measurement, or power measurement
has been performed by these tests.

## Physical interface and operating contract

The sensor uses SPI mode 3 at 1 MHz with the external 12 MHz FPGA clock.
The generic byte SPI master also supports mode 0 for the onboard Flash,
keeps CS asserted between bytes, and finishes a transaction only on `tx_last`.
One system-clock CS hold interval follows the final SPI clock edge.

After a startup delay, capture checks DEVID=0xE5, enters standby, disables
interrupts, sets DATA_FORMAT=0x08 (full resolution, right justified, +/-2 g),
sets BW_RATE, chooses FIFO bypass, maps DATA_READY to INT1, enables its
interrupt, and enters measurement mode. RATE_CODE 0x0A/0x0C/0x0D means
100/400/800 Hz. INT1 passes through a two-register synchronizer. The module
reads INT_SOURCE before the six-byte XYZ burst because reading XYZ clears
DATA_READY and the overrun indication. A wrong ID requires reset to retry.
These register and interrupt semantics come from the
[Analog Devices ADXL345 data sheet](https://www.analog.com/media/en/technical-documentation/data-sheets/ADXL345.pdf).

Capture presents signed x/y/z and `service_cycle` under valid/ready. The cycle
timestamp is recorded when a complete XYZ result is committed to its output
buffer, not at the sensor's internal conversion instant. Output fields remain
stable under backpressure. `samples_captured` counts complete reads;
`missed_service` counts completed reads discarded because the output buffer
was occupied; `sensor_overruns` counts observations of INT_SOURCE's overrun
bit. The latter is not an exact count of lost conversions.

The logger observes one selected axis. It retains the first STORE_SAMPLES
raw records while statistics and calibration continue until TOTAL_SAMPLES
accepted samples. Defaults are 24,000 retained and 480,000 total at 800 Hz:
nominally 30 seconds retained and 10 minutes observed when conversions are
delivered without losses. Actual duration is computed from timestamps. A
one-second no-sample watchdog ends a stalled run with an error flag.

Calibration is `sat32(RNE((raw*256-OFFSET_Q8)*GAIN_Q20,28))` in milligravity.
The default offset 0 and gain 4,096,000 implement nominal 1000/256 mg per
count. These defaults are not a measured calibration. The final calibrated
value and a signed 64-bit sum cover every accepted sample, including samples
beyond the retained raw-data window.

With spectrum enabled, an independent branch consumes the same accepted raw
axis counts. It clamps to [-1024,1023], multiplies by 32 to compensate for the
shared frontend's input shift, and processes nonoverlapping 256-sample windows:
DC removal, periodic Hann window, selected-bin DFT, and squared magnitude.
The bins are `[1,2,3,4,5,8,12,16,24,32,40,48,64,80,96,120]`; each frequency
is `bin * actual_sample_rate / 256`. At 800 Hz they span 3.125–375 Hz.
Coefficients and arithmetic follow `artifacts/sensor_spectrum/model/model.json`
and the integer frontend contract. These integers are scaled raw-count-domain
DFT powers, not calibrated mg-squared PSD estimates or fault probabilities.
The calibrated mg statistics are a parallel branch; calibration is not applied
to the spectrum input.

The logger waits for every accepted complete window to finish before writing
Flash. An incomplete trailing window is omitted. The latest complete spectrum
can come from much later than the retained first 30 seconds; compare it with
the matching raw window, not automatically with the start of the log. Builds
with equal total and retained counts are useful for reference comparisons.

## Flash ownership and commit

The physical build checks all 128 KiB of `[0x300000,0x320000)` for 0xFF before
starting capture. Any existing or partial log prevents writing. It never
erases Flash; an explicit host operation must prepare the log region.
The Flash transport also rejects writes outside that region or across a
256-byte program-page boundary.

The logger writes the raw payload first, a header with an erased commit word
second, and the four-byte `COMT` token last. A Flash error prevents a completed
commit. A completed diagnostic log may still have acquisition error flags;
`status_done` therefore does not imply `status_error=0`.

## SEN1 header

The header begins at 0x300000. Each row below is a little-endian 32-bit word;
byte offset is four times the word index. The first 96 bytes are the base
SEN1 schema. The logger-only variant writes 128 bytes; the spectrum variant
writes 208 bytes. Word 31 distinguishes them.

| Word | Meaning |
|---:|---|
| 0 | Magic 0x314E4553, bytes `SEN1` |
| 1 | Schema version 1 |
| 2 | Number of stored raw records |
| 3 | Commit token 0x434F4D54, bytes `TMOC` as the defined little-endian word; erased until final program |
| 4 | Error flags described below |
| 5 | Accepted sample count across the complete observation |
| 6 | Configured TOTAL_SAMPLES |
| 7 | Configured STORE_SAMPLES |
| 8 | Clock frequency, 12,000,000 Hz |
| 9 | ADXL345 BW_RATE code |
| 10 | Axis: 0=x, 1=y, 2=z |
| 11 | Observed device ID |
| 12 | First accepted sample's 32-bit service-cycle timestamp |
| 13 | Last accepted sample's 32-bit service-cycle timestamp |
| 14 | Minimum interval in exact clock cycles, or 0 for fewer than two samples |
| 15 | Maximum interval in exact clock cycles |
| 16 | Complete XYZ reads reported by capture |
| 17 | Output-buffer discard count (`missed_service`) |
| 18 | Sensor overrun-flag observations |
| 19 | Intervals exceeding the retained record's range |
| 20 | Standard zlib/IEEE CRC32 of exactly the retained payload bytes |
| 21 | Record size, 4 bytes |
| 22 | Payload address, 0x301000 |
| 23 | Timestamp quantum, 4 FPGA clock cycles |
| 24 | Last calibrated milligravity value, signed int32 |
| 25–26 | Signed int64 sum of all calibrated mg values, low word first |
| 27 | Number of calibrated samples |
| 28 | Calibration offset Q8, signed int32 |
| 29 | Calibration gain Q20, positive uint32 |
| 30 | Observed 32-bit service-counter wrap count after the first accepted sample |
| 31 | Header length, 128 without spectrum or 208 with spectrum |
| 32 | Completed spectrum windows (208-byte form only) |
| 33 | Spectrum window length, 256 |
| 34 | Spectrum coefficient/bin configuration version, 1 |
| 35 | Raw inputs clamped by the spectrum frontend |
| 36–51 | Latest complete window's 16 uint32 powers, in model bin order |

If no complete spectrum window was processed, word 32 and all 16 power words
are zero. Spectrum results are streamed into SPRAM as two 16-bit writes per
power; no 512-bit spectrum register is instantiated.

The constant commit word matches the existing Flash protocol. Its wire bytes
are `54 4d 4f 43`; software must compare the defined word or exact bytes rather
than inferring an ASCII spelling from the label.

Error flag bits: 0 existing/nonblank log; 1 sensor ID failure; 2 interval
overflow; 3 discarded sensor outputs; 4 observed sensor overrun; 5 sample
watchdog; 6 Flash transport error; 7 invalid configuration or FSM fault.
A nonblank log is not overwritten to record its own error.

## Retained records and time reconstruction

Payload records are `<hH`: signed int16 raw count followed by uint16 interval.
The first record's interval is zero. Subsequent intervals are the difference
between `service_cycle >> 2` values, modulo 2^30. Quantizing the absolute
timestamps before differencing avoids accumulating rounding drift. Without
overflow, reconstruction as `first_service_cycle + 4*cumsum(interval)` differs
from the original service times by at most three clock cycles, even across
a 32-bit wrap.

If an exact interval exceeds 262,140 clock cycles, or the quantized interval
exceeds 65,535, the record stores 0xFFFF and sets the overflow count and flag.
The complete timing sequence cannot then be reconstructed from the compact
records alone. A decoder must expose this limitation.

The overall observation interval is
`(service_wrap_count << 32) + last_service_cycle - first_service_cycle`.
This is necessary for a 10-minute observation because the 12 MHz 32-bit
counter wraps after approximately 358 seconds. The watchdog ensures that
multiple complete wraps cannot occur unobserved between accepted samples.

## Reproduction and evidence

```sh
source scripts/env.sh
python sim/run_spi_sensor.py
python sim/run_sensor_system.py
python scripts/build_sensor.py --rate 800
python scripts/build_sensor.py --rate 800 --no-spectrum
```

The SPI regression checks all four modes at HALF_PERIOD=6, and modes 0/3
at HALF_PERIOD=1, with random bidirectional bytes, packet stalls, clock
spacing, CS continuity, and mid-transaction resets. Sensor unit tests cover
100/400/800 Hz register settings, signed XYZ bursts, output stability,
discard counting, overrun reading, reset/reinitialization, and wrong ID.

The system regression uses the actual capture, calibration, SPRAM wrappers,
and Flash transport. It shortens the run to 88 samples with 80 retained,
reduces the RAM bank address width to six bits to cross all three banks,
and checks an 8 KiB log range in 257-byte chunks. Physical builds retain the
full RAM width, 128 KiB scan, and configured sample counts. An alternate
four-sample test injects an interval overflow. A 256-sample spectrum case
checks every retained sample and every logged power against Python's integer
frontend, including waiting for the final complete window before committing.
The simulation counter starts
near rollover to check wrapping without simulating 358 seconds.

Each successful system test saves its simulated `sensor_log.bin`, source
values/timestamps in `sensor_stimulus.json`, and `report.json` under
`build/sensor_system_nominal`, `build/sensor_system_overflow`, or
`build/sensor_system_spectrum`. These are
synthetic peripheral-model results, suitable for testing the host decoder;
they are not measured sensor captures. The tests check raw values, compact
timestamps, calibrated sum, CRC, page boundaries, commit ordering, and
refusal to overwrite complete or partial logs.

The build generates an UP5K SG48 bitstream and a reference pin file. Its
sensor CS/SCLK/MOSI/MISO/INT1 pins are gpio_23/25/26/27/32, respectively.
The clock uses gpio_20 and requires the OSC jumper. These choices follow the
[official UPduino v3 pinout](https://upduino.readthedocs.io/en/latest/features/specs.html);
the user's actual board revision and wiring remain unverified. All status
pins are exposed GPIO, not the RGB LED. The build command never programs a
board.

Historical pre-optimization local result for the spectrum image: the complete 256-sample system
case passed, including logged-power comparison and forced 32-bit rollover.
The 800 Hz spectrum image placed and routed at 12 MHz using 4,874 of 5,280
logic cells, four SPRAM blocks, nine EBR blocks, and one DSP block. The
post-route maximum-frequency report was 17.33 MHz. These are tool results;
they do not establish measured board behavior. Generated evidence is in
`build/sensor_board_800hz_spectrum/report.json` and the system-test directories.
The separately rebuilt `--no-spectrum` variant uses 3,073 logic cells, three
SPRAM blocks, no EBR or DSP blocks, and reports 17.59 MHz post-route. Both
128-byte logger system cases were rerun after the optional spectrum branch
was added and passed. The SPI and sensor unit reports are under
`build/spi_sensor_results.json` and `build/spi_sensor_r0a_results.json`,
`build/spi_sensor_r0c_results.json`, and `build/spi_sensor_r0d_results.json`.

The current shared-spectrum-cache image uses 4,915 logic cells and three
SPRAM blocks, with nine EBR blocks and one DSP unchanged. A matched seed-1
800 Hz / 12 MHz build reports 16.53 MHz post-route, versus 17.33 MHz before
the change. This is a memory-capacity improvement with a modest logic/timing
tradeoff, not a measured energy improvement. SEN1 bytes are unchanged. New
reports and source/bitstream hashes are isolated under
`build/storage-optimization-2026-09-08/`; see
[storage optimization](storage-optimization-2026-09-08.md).

Evidence directories under `build/` referenced in this document are retained locally when omitted from this publication. Their reported results remain historical evidence, not fresh execution of the exported sources.
