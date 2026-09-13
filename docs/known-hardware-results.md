# UPduino 3.1 Physical Replay of the Frozen Model

There were 22 actual passing replays involving 13 different public recordings. Each boot processes 156 consecutive windows; totals accumulate across distinct physical runs.
The four-MAC evidence for 1092 continuous fixed-cadence windows comes from a separate RTL regression. Physical windows accumulated over restarts must not be described as one continuous run.

| MAC count | Passing physical-board windows |
| --- | --- |
| 1 | 1248 |
| 4 | 2184 |

Every run checks the complete Flash backup, JEDEC, and model/bitstream/input hashes. Results require two identical raw readbacks and passing checks for commit marker, CRC, counts, stage cycles, and integer score. Initial erroneous or misaligned readbacks are retained without trimming or repairing bytes.

| Same recording | One-MAC active cycles | Four-MAC active cycles | Computation speedup |
| --- | --- | --- | --- |
| fan/id_00/normal/00000304.wav | 167265663 | 44222847 | 3.7823 |
| fan/id_00/abnormal/00000094.wav | 167265644 | 44222828 | 3.7823 |
| fan/id_00/normal/00000778.wav | 167265233 | 44222417 | 3.7824 |
| fan/id_00/abnormal/00000391.wav | 167265981 | 44223165 | 3.7823 |
| fan/id_00/normal/00000259.wav | 167265572 | 44222756 | 3.7823 |
| fan/id_00/abnormal/00000372.wav | 167266030 | 44223214 | 3.7823 |
| fan/id_00/normal/00000892.wav | 167266513 | 44223697 | 3.7823 |

| MACs | Post-placement LC | Synthesis LUT4 | Synthesis standalone FF | DSP | EBR | SPRAM | Final Fmax, MHz |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 4682 | 3713 | 1497 | 1 | 25 | 1 | 13.8989 |
| 4 | 5178 | 4192 | 1653 | 4 | 28 | 1 | 13.3138 |

LC is a combined post-placement resource unit, not a pure LUT count. Standalone FF counts exclude registers inside DSP/RAM macros. Both versions use the same ABC9 register-mapping option and a 13.2 MHz constraint.

Speedup compares only active computation cycles for the same recording. Four-MAC input has one sample every 750 cycles; the normal one-MAC baseline has one every 1500 cycles. Their different acquisition durations must not be counted as pure computation speedup.
Both clocks are configured as nominal 12 MHz HFOSC; actual frequency and power were not measured. Results come from real FPGA replay of public sounds, not microphone or field-fan testing.

Deliberate overload check: True. See the audit JSON for detailed errors and recovery runs.
Quality metrics for the final 720 recordings are reported separately in known-final-test.md and are not mixed with physical numerical validation on development recordings.
