# UPduino 3.1 physical pinout and clock verification (2026-09-10)

USB enumeration returned UPduino v3.1 / tinyVision.ai / 0403:6014, and a read-only iceprog operation returned JEDEC EF4016. The original 4 MiB Flash was backed up; its file and SHA256 are recorded in `measurements/2026-09-10-upduino31/backup.json`. Raw device backups are retained locally and excluded from publication. The actual connected-board configuration is `configs/upduino31-connected.json`. No ADXL345 was connected.

## Flash interface correction

The reference PCF originally swapped MOSI and MISO. The [official PCB bearing UPduino 3.1 silkscreen](https://github.com/tinyvision-ai-inc/UPduino-v3.0/blob/master/Board/v3.01/UPduino_v3.01.kicad_pcb) shows U2 pad14 / FPGA_SO through R12 to U5 pad5 / FLASH_MOSI, and U2 pad17 / FPGA_SI through R13 to U5 pad2 / FLASH_MISO. Correct mapping is CS16, SCLK15, MOSI14, MISO17. The webpage's ASCII table reverses those two entries relative to the PCB.

This correction applies to replay, SEN1 measurement, and FCL1 classification builds. Earlier placement/routing reports remain historical evidence; bitstreams with the old pins are no longer candidates for programming.

## Replay without the external-clock jumper

The [official external-oscillator instructions](https://upduino.readthedocs.io/en/latest/tutorials/oscillator.html) require bridging OSC/R16 to connect 12 MHz to GPIO20. That jumper had not been verified in this iteration, so the replay top level added explicit option `INTERNAL_OSC=1`, using `SB_HFOSC` divided by four, `CLKHF_DIV="0b10"`. The default external-clock version remains available.

[Lattice Technology Library §7.4.1](https://www.latticesemi.com/-/media/LatticeSemi/Documents/TechnicalBriefs/FPGA-TN-02026-3-3-iCE40-Technology-Library.ashx?document_id=52206) specifies UltraPlus HFOSC as nominally 48 MHz, ±10%, with approximately 100 µs startup stabilization. The design holds startup reset for 120000 cycles, approximately 10 ms, before accessing Flash. The internal 12 MHz build uses a 13.2 MHz placement/routing constraint to cover the faster-clock condition. External port clk12 retains its input constraint but is unused in internal-clock mode.

The internal clock frequency remains physically unmeasured. Cycle counts can be read accurately, but latency converted using 12 MHz and 12 kS/s at one sample per 1000 cycles are nominal values only. They do not establish accurately measured 12 kS/s acquisition or ADC sampling-jitter validation.

## Flash capacity and operations

The [Winbond W25Q32JV datasheet](https://www.winbond.com/resource-files/w25q32jv%20revg%2003272018%20plus.pdf), pp. 4/21/37, identifies EF4016 with a 4 MiB family, 256 B programming pages, and 4 KiB erase sectors. JEDEC alone does not identify the specific package suffix. Existing input range 0x40000..0x50000 and log range 0x300000..0x320000 fit within capacity.

Operate only within bounded configuration, input, and log regions; retain the complete original backup and avoid chip erase. Erasing logs last starts the new replay. Readback resets the FPGA, so readback duration is not an exact end-to-end latency. Completed logs should remain unchanged after reset.

## Startup gap exposed by the first board run

On 2026-09-10, the first four-MAC programming and verification succeeded, but all 131072 bytes of the result region were FF and no committed log appeared. Failed evidence is retained in `measurements/2026-09-10-upduino31/l4-5/`.

[Lattice configuration documentation §9, Figure 9.5](https://www.latticesemi.com/-/media/LatticeSemi/Documents/ApplicationNotes/IK/FPGA-TN-02001-3-4-iCE40-Programming-Configuration.ashx?document_id=46502) explains that configuration completion may send Flash the B9 deep-power-down command. Original `flash_stream` sent a 03 read directly without waking Flash. The old model was always readable and omitted this environmental condition.

The fix sends AB after every reset, then holds CS high for 256 FPGA cycles before allowing a command handshake. Winbond maximum tRES1 is 3 µs; 256 cycles at 13.2 MHz are approximately 19.39 µs. The new model starts asleep and accepts normal reads/writes only after AB plus at least 40 wait cycles. Dedicated tests check correct wakeup, FF reads after deliberate reentry into sleep, and reset recovery. Three model-boundary tests and the actual RTL-specific test passed.

After the fix, four-MAC physical replay passed five frames: all 5120 samples accepted, bit-exact scores, and zero overflow/protocol errors. See `measurements/2026-09-10-upduino31/l4-5-wake/manifest.json`. The unified status index lists subsequent long replays. Omitted raw measurement evidence remains local.

## USB readback anomaly and evidence preservation

The first readback of the four-MAC 1000-frame run shifted the entire data block right by one byte. JEDEC output in the same session also had a leading byte. Original failed files and manifest remain intact in `measurements/2026-09-10-upduino31/l4-1000/`. This supports a host USB/FTDI readback-session alignment anomaly. Its exact underlying cause remains unknown; the retry mechanism is not a demonstrated fix to the underlying driver.

Abnormal files were neither rewritten nor stripped. Two later independent, unmodified reads were identical and passed all 1000-frame numerical and counter checks. A subsequent read-only recovery using the updated driver is saved in `l4-1000-readback-recovery/`. Its manifest links the original failed attempt and explicitly identifies recovery evidence from the same physical replay; it is not counted as another experiment.

The new hardware entry point verifies JEDEC and write checks at every step. It reads at most three times and generates the final result only after two consecutive raw files are identical and structurally valid. Transfer anomalies and compute-core errors are recorded separately. Every run saves a driver snapshot, firmware/model/input hashes, raw readbacks, and operation records. The recovery entry point only reads; it neither programs nor starts a new replay.

For complete one-/four-MAC results and measurement scope, see the [2026-09-10 physical-board report](hardware-results-2026-09-10.md).
