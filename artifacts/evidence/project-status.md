# Automatically collected project evidence

Generated: 2026-09-06T03:25:07.223844+00:00

This report only reads saved results and does not rerun experiments. At this historical stage, there was no completion evidence for hardware tests, physical sensors, field classification, power measurements, or ASIC fabrication.

| Check | Result | Test count |
| --- | --- | --- |
| build/calibration_0 | passed | 1 |
| build/calibration_1 | passed | 1 |
| build/calibration_2 | passed | 1 |
| build/calibration_3 | passed | 1 |
| build/core_dsp_l1_artifacts | passed | 4 |
| build/core_dsp_l1_model_neighbor | passed | 4 |
| build/core_dsp_l4_artifacts | passed | 4 |
| build/core_dsp_l4_model_neighbor | passed | 4 |
| build/core_l1_artifacts | passed | 4 |
| build/core_l1_model_neighbor | passed | 4 |
| build/core_l4_artifacts/arithmetic | passed | 1 |
| build/core_l4_artifacts | passed | 4 |
| build/core_l4_fixtures | passed | 2 |
| build/core_l4_model_neighbor | passed | 4 |
| build/core_l4_quant_boundary | passed | 4 |
| build/fifo_d1 | passed | 1 |
| build/fifo_d3 | passed | 1 |
| build/fifo_d4 | passed | 1 |
| build/flash_system | passed | 1 |
| build/flash_system_neighbor | passed | 1 |
| build/flash_system_neighbor_full_scan | passed | 1 |
| build/sensor_spectrum | passed | 1 |
| build/sensor_system_nominal | passed | 1 |
| build/sensor_system_overflow | passed | 1 |
| build/sensor_system_spectrum | passed | 1 |
| build/spi_master_m0_h1 | passed | 2 |
| build/spi_master_m0_h6 | passed | 2 |
| build/spi_master_m1_h6 | passed | 2 |
| build/spi_master_m2_h6 | passed | 2 |
| build/spi_master_m3_h1 | passed | 2 |
| build/spi_master_m3_h6 | passed | 2 |
| build/spi_sensor_m3_h6 | passed | 2 |
| build/spi_sensor_m3_h6_r0a | passed | 2 |
| build/spi_sensor_m3_h6_r0c | passed | 2 |
| build/spi_sensor_m3_h6_r0d | passed | 2 |
| python_unit | passed | 57 |

## Complete FPGA builds

A build passes only if its report, bitstream checksum, timing, and capacity checks all pass. A core probe is not a complete system build.

- build/board_l1: passed; newer RTL files: 0。
- build/board_l4: passed; newer RTL files: 0。
- build/board_neighbor_l1: passed; newer RTL files: 0。
- build/board_neighbor_l4: passed; newer RTL files: 0。
- build/sensor_board_100hz_spectrum: passed; newer RTL files: 0。
- build/sensor_board_400hz_spectrum: passed; newer RTL files: 0。
- build/sensor_board_800hz: passed; newer RTL files: 0。
- build/sensor_board_800hz_spectrum: passed; newer RTL files: 0。

## Held-out test of the original single-bin model

INT8 accuracy 76.82%，macro-F1 77.13%。
RMS baseline accuracy 77.10%. This does not support a claim that the MLP outperforms the baseline.


## Test evaluation after freezing the neighboring-bin candidate

INT8 accuracy 93.18%，macro-F1 93.24%。
Evaluation outputs, frozen input hashes, and saved predictions passed consistency checks. The 3 HP records were previously used to test the old model; this is not a new external dataset or a hardware/field measurement.
The model and ROM remain frozen. Results are saved separately under artifacts/reports/neighbor_test; the historical test_evaluated=false model-JSON field is not rewritten.

Detailed values, original evidence paths, and checksums are in index.json; the source snapshot is in source-lock.json; installed tool and dependency versions are in environment.json.
