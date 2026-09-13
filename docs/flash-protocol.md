# Flash Replay Protocol v1

This is the byte protocol currently implemented by `src/vibfpga/board.py` and `rtl/upduino_replay.sv`. All multibyte integers are little-endian; each byte on the Flash SPI wire remains MSB-first in mode 0. Addresses below are fixed in RTL. At the reference-profile stage documented here, the actual board, Flash capacity, and wiring had not yet been physically verified.

|Partition|Start|Length|Purpose|
|---|---|---|---|
|Reserved configuration region|0x000000|0x040000|Data/log tools must not write here|
|Replay image|0x040000|0x010000|4 KiB header area plus raw samples|
|Log region|0x300000|0x020000|4 KiB header area plus up to 1000 results|

## VIB1 Input Image

Image-relative bytes 0..63 use `<4s7I32s`; the rest of the header area is padded with 0xff. Payload starts at image offset 4096, absolute address 0x041000.

|Byte offset|Type|Meaning|
|---:|---|---|
|0|4 bytes|ASCII `VIB1`|
|4|uint32|Version 1|
|8|uint32|Samples per frame; must be 1024|
|12|uint32|source_frames, 1..16|
|16|uint32|run_frames, 1..1000|
|20|uint32|period_cycles, 4..65535; 12 MHz/1000=12 ksample/s|
|24|uint32|Payload bytes; must equal source_frames×2048|
|28|uint32|zlib/IEEE CRC32 of payload|
|32|32 bytes|SHA256 digest of the exact `model.json` file contents|
|4096|int16[]|Raw PCM16 samples stored frame by frame|

The RTL `MODEL_HASH[255:0]` parameter uses `int.from_bytes(digest, 'little')`, so the header's first digest byte maps to bits 7:0. The build script and replay image must use the same model file; even reordering JSON text changes the hash. CRC starts at 0xffffffff, uses reflected polynomial 0xedb88320 per byte, and ends with XOR 0xffffffff, matching `zlib.crc32(payload)`.

Startup first checks that the complete 128 KiB log partition is 0xff, reading four 32768-byte blocks beginning at 0x300000, 0x308000, 0x310000, and 0x318000, including the final byte 0x31ffff. If a non-0xff byte is found, it stops at the end of the current block. Only after all four blocks are blank does it validate the input header/model hash, load the complete payload into SPRAM, and check CRC. Periodic sample generation begins only after passing. source_frames can repeat to support longer run_frames; these repetitions test throughput/protocol and are not new independent classification samples. The source has no ready input; insufficient consumption causes counted sample loss and frame-marker-based core recovery.

The full scan's behavioral simulation takes approximately 218.48 ms when converted at 12 MHz; see `build/flash_system_neighbor_full_scan/regression.json`. This excludes the top level's default 10 ms startup wait, input-image loading, subsequent computation, and log writing. It is startup overhead derived from RTL cycles, not physical timing, and is excluded from per-frame core processing latency.

## VLG1 Log

The log header is 64 bytes. Result records start at log-relative offset 4096, absolute address 0x301000, with 64 bytes per record.

|Header offset|Type|Meaning|
|---:|---|---|
|0|4 bytes|ASCII `VLG1`|
|4|uint32|Version 1|
|8|uint32|Actual stored-result count|
|12|uint32|Commit written last: 0x434f4d54, wire bytes `54 4d 4f 43`|
|16|uint32|System error_flags|
|20|uint32|generated_samples|
|24|uint32|accepted_samples|
|28|uint32|overflow_count|
|32|uint32|protocol_errors|
|36|uint32|Maximum FIFO occupancy|
|40|uint32|period_cycles|
|44|uint32|Requested run_frames|
|48..63|bytes|0xff, reserved|

Each result contains these 16 consecutive 32-bit words:

|Word index|Contents|
|---:|---|
|0|frame_id|
|1/2/3|Three signed int32 logits for classes 0/1/2|
|4|bits 1:0 class_id; bits 15:8 core_error; all other bits zero|
|5/6/7/8|cycles_pre / cycles_dft / cycles_power / cycles_nn|
|9|cycles_total, the sum of the preceding four counts|
|10|Maximum FIFO occupancy at recording time|
|11/12|generated_samples / accepted_samples at recording time|
|13|protocol_errors at recording time|
|14/15|Zero, reserved|

Stage cycle counts measure processing after frame completion, not end-to-end latency including full-frame capture and all queue waiting. Counters are snapshotted when each frame result arrives, so generated_samples for an intermediate frame may already include samples of the next frame.

error_flags bit 0 means an existing log; bit 1 invalid input header/model hash; bit 2 payload CRC error; bit 3 input FIFO overflow; bit 4 core error; bit 5 tail timeout; bit 6 Flash programming/busy-wait failure; and bit 7 illegal state. `status_done` means only that commit completed; a diagnostic log can also contain errors, so readers must inspect errors and sample-loss counts.

## Writing and Recovery

`flash_stream` supports 0x03 READ, 0x06 WREN, 0x02 PAGE PROGRAM, and 0x05 READ STATUS. Writes must be entirely within [0x300000,0x320000), have length 1..256, and not cross a 256-byte page. Invalid commands are rejected before any SPI transaction. Each program is preceded by WREN and followed by WIP polling with a bounded timeout. The FPGA never erases; the host must erase the entire log region.

Write order is header with commit left at 0xffffffff → result pages → separate commit word. Startup stops if any log-partition byte is non-0xff, preserving committed logs, partial headers, and residual tails even when the header is blank. It never automatically erases and reruns. The host must clear the complete partition. Power failure can leave uncommitted data, which the parser rejects; this is not an atomicity guarantee against every possible Flash electrical failure.

`scripts/flash_exchange.py` write-input / clear-log / read-log generate and print commands by default. Actual execution requires explicit `--execute`; writes also face the rejection gate for an unverified reference profile. `clear-log` generates a local 0xff file by default but does not touch hardware. There is no bulk-erase command. The erase-block size is explicitly passed to iceprog and constrained by partition alignment.

`sim/run_flash_system.py` uses an SPI Flash model with WREN/WIP, NOR bitwise-AND programming, and page-wrap behavior. It covers source wrap using the real model, cross-page result writing, bitwise logits comparison, final commit, wrong hash/CRC, invalid write addresses/lengths, busy-wait timeout, reset, and partial-log protection. Ordinary E2E regression shortens scanning to four 256-byte blocks to accelerate repeated startup and explicitly reports that parameter. The production top fixes four 32768-byte blocks. The separate `--full-log-scan` regression uses the complete production region, injects a non-0xff byte only at 0x31ffff, and checks actual starts/lengths of all four reads, startup rejection, and no write anywhere in Flash. It verifies the functional protocol, not real Flash startup timing, electrical interfaces, write endurance, or physical-board readback. Omitted build reports remain local.

## Independent SEN1 Sensor Log

Sensor firmware uses the same log partition but magic `SEN1`. The header is 128 bytes without spectrum and 208 bytes with spectrum. Payload still starts at log offset 4096. Each raw record is `<hH`: selected single-axis raw int16 plus uint16 service-time delta in units of four FPGA clocks. The first delta is zero. Unrepresentable intervals saturate and increment the whole-run overflow count. These are read-service timestamps, not ADC aperture timestamps.

Header fields by uint32 word index follow; signed fields are noted:

|Word|Contents|
|---|---|
|0..3|`SEN1`, version 1, stored raw-record count, COMT written last|
|4..7|error_flags, whole-run observed_samples, target_samples, storage_limit|
|8..11|Clock 12000000, ADXL345 RATE_CODE, axis 0/1/2, read device_id|
|12..15|First/last service cycles, whole-run minimum/maximum service intervals|
|16..19|samples_captured, missed_service, sensor_overruns, interval_overflows|
|20..23|Raw payload CRC32, record width 4, absolute payload address 0x301000, delta quantization period 4|
|24|Latest calibrated value, signed int32 mg|
|25..26|Whole-run calibrated-value sum, signed int64, low word first|
|27..31|Calibrated sample count, offset_q8 int32, gain_q20, service-timer wrap count, header bytes|
|32..35 (208 B)|Complete spectrum-window count, N=256, spectrum configuration version 1, spectrum-input clip_count|
|36..51 (208 B)|16 uint32 DFT powers for the latest complete window, ordered by sensor_spectrum model.bins|

Whole-run statistics can span longer than raw storage, for example a 10-minute run retaining only the first 30 seconds of raw samples. Parsing must preserve these distinct scopes. Host CSV contains only the axis actually measured. A same-name JSON sidecar retains whole-run anomaly counts, source-log SHA, and CSV SHA. Raw data remain readable when service intervals overflow, but the converter refuses to generate a CSV with apparently reliable timestamps. Calibration parameters in firmware do not establish physical calibration evidence.

The spectrum branch receives raw counts, clips them to [-1024,1023], then multiplies by 32 to compensate for the shared core's input right shift of 5. The raw log retains original counts. N256 bins are `1,2,3,4,5,8,12,16,24,32,40,48,64,80,96,120`, with frequency `bin × actual ODR / 256 Hz`. Power is the sum of squared fixed-point DFT coefficients, not calibrated mg²/Hz PSD. This branch uses untrained zero NN parameters and disconnects classification outputs; it reports spectrum only and cannot inherit CWRU model accuracy.
