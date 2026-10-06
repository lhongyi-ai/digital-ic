# Cross-FPGA implementation and quantization timing experiment

These results come from saved experiment reports. Missing results and failures are retained. Original deployment receipts and the full Flash recovery backup remain in the laboratory archive; final test recordings were not revisited.

The original path combined the final wide partial-product accumulation, ties-to-even rounding, symmetric saturation, and sign restoration in one combinational cycle. Candidate C enters NORM_QUANT after the final normalization accumulation, reuses wide_acc, and quantizes on the next cycle. Power computation keeps its original schedule.

The RAM backends share rising-edge sampling and synchronous reads. Output during a write is not a valid read. AMD uses inferred BRAM; iCE40 uses the original SPRAM.

| Platform / seed | B internal delay ns | C internal delay ns | Reduction |
| --- | ---: | ---: | ---: |
| amd / 1 | 16.888 | 15.018 | 11.07% |
| ice40 / 1 | 71.220 | 58.507 | 17.85% |

The worst internal paths include retained debug-output registers. AMD B traverses the shared multiplier, wide accumulation, feature, and rounded_magnitude logic, ending at dbg_value_reg[58]. C moves the bottleneck to purpose control, the shared multiplier, and wide accumulation ending at dbg_value_reg[53]. These are worst paths of the complete observable core; their endpoints are debug registers.

| AMD ID00 four MACs | LUT | FF | DSP | BRAM tile |
| --- | ---: | ---: | ---: | ---: |
| B | 1814 | 1306 | 7 | 5.5 |
| C | 1739 | 1308 | 7 | 5.5 |

| AMD C four MACs | Worst internal delay ns | WNS ns | Hold slack ns | LUT | FF |
| --- | ---: | ---: | ---: | ---: | ---: |
| 00 | 15.018 | 4.929 | 0.136 | 1739 | 1308 |
| 02 | 14.317 | 5.628 | 0.143 | 1739 | 1302 |
| 04 | 14.992 | 4.955 | 0.125 | 1743 | 1305 |
| 06 | 14.448 | 5.549 | 0.151 | 1749 | 1309 |

AMD implementation uses xc7a35tcpg236-1, Vivado 2024.2 Build 5239630, two threads, a 20 ns clock, and 2 ns input/output assumptions. All four C models pass setup and hold checks, with zero unconstrained paths or black boxes and inferred BRAM storage. OOC implementation does not establish AMD board-level I/O behavior.

| UPduino ID00 four MACs | seed | LC | Estimated Fmax MHz |
| --- | ---: | ---: | ---: |
| B | 1 | 5168 / 5280 | 14.041 |
| B | 2 | 5168 / 5280 | 13.770 |
| B | 3 | 5168 / 5280 | 14.005 |
| C | 1 | 5221 / 5280 | 17.092 |
| C | 2 | 5221 / 5280 | 17.138 |
| C | 3 | 5221 / 5280 | 17.406 |

ID00 1 MACs: 7 recording-level stage comparisons. Each recording adds 512 NN/total activity cycles; the other three stages are unchanged. Maximum activity overhead 0.000306%; input period 1500; backpressure 0.

ID00 4 MACs: 7 recording-level stage comparisons. Each recording adds 512 NN/total activity cycles; the other three stages are unchanged. Maximum activity overhead 0.001158%; input period 750; backpressure 0.

Local full-core verification:  5304 windows; Vivado full-recording verification:  1716 windows, 5282827 intermediate numerical checks. Small tests additionally cover the RAM contract, arithmetic boundaries, input stalls, output blocking, reset, and protocol errors. Reset in the new quantization state cancels the prior transaction.

Candidate C meets all timing, resource, and cycle targets, so D/E were unnecessary. Frozen ID00/02/04/06 parameters and thresholds are unchanged. This experiment uses only the development cv recordings selected in advance.

A to B: integer-reference checks and all core activity-stage counts agree for the same seven recordings. The historical one-MAC baseline supplied ready/valid input as quickly as possible; this experiment uses a fixed 1500-cycle cadence. Wall-clock latency and blocking counts under different cadences are not portability differences.

Physical board: 11 passing runs, 1248 four-MAC windows and 468 one-MAC windows. One expected overload failure is retained. After reset, the same one-MAC bitstream passes at a 1500-cycle cadence. Each normal startup processes 156 consecutive windows, checking numerical values, CRC, commit markers, generated/received counts, and two identical raw readbacks.

HFOSC was not increased on the physical board. No AMD board test was performed. Original failures and run logs remain in the laboratory archive.

Additional resume bullet (retain the existing 3.78x parallelization result):

Ported a fixed-point accelerator across iCE40 and AMD FPGAs with a verified synchronous memory interface; pipelined normalization to reduce routed critical-path delay by 11.1% on AMD and 17.9% on iCE40, adding 512 cycles per recording; validated bit-exact results in Vivado simulation and UPduino hardware replays.

Registered reports: 39; missing: 0; binding/report errors: 0.

Simulation verifies numerical behavior, protocols, and activity counts. Place and route establishes timing estimates for the specified devices and constraints. The physical board still uses nominal 12 MHz; improved timing margin does not demonstrate faster recording processing.

Programming requires the complete portability_release.py gate. This summary does not authorize programming.

Missing reports or binding errors:
