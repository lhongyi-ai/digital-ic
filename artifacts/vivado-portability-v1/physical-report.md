# Frozen-model UPduino 3.1 physical replays

Eleven physical replays passed across eight distinct public recordings. Each startup processes 156 consecutive windows; totals accumulate across separate physical runs.
The four-MAC evidence for 1092 consecutive windows at fixed cadence comes from a separate RTL regression. Physical windows accumulated across restarts are not one continuous run.

|MACs|Passing physical windows|
|---|---|
|1|468|
|4|1248|

Every run checks a complete Flash recovery backup, JEDEC identification, and model/bitstream/input hashes. Results require two identical raw readbacks and valid commit markers, CRC, counters, stage cycles, and integer scores. Initial erroneous or misaligned readbacks are retained without truncating or repairing bytes.

|Matched recording|One-MAC activity cycles|Four-MAC activity cycles|Compute speedup|
|---|---|---|---|
|fan/id_00/normal/00000304.wav|167266175|44223359|3.7823|
|fan/id_00/abnormal/00000094.wav|167266156|44223340|3.7823|

|MAC|Post-route LC|Synthesis LUT4|Synthesis standalone FF|DSP|EBR|SPRAM|Final Fmax MHz|
|---|---|---|---|---|---|---|---|
|1|4765|3700|1497|1|25|1|16.9526|
|4|5221|4176|1653|4|28|1|17.0920|

LC is the post-route combined resource unit, rather than a pure LUT count. Standalone FF counts exclude registers inside DSP/RAM macros. Both versions use the same ABC9 register-mapping options and 13.2 MHz constraint.

Speedup compares activity cycles for matched recordings. Four MACs receive one sample every 750 cycles; the normal one-MAC baseline uses 1500 cycles. Their different acquisition durations are not pure compute speedup.
Both clocks are configured for nominal 12 MHz HFOSC. Physical frequency and power are unmeasured. These are physical FPGA replays of public audio, rather than microphone or field-fan tests.

Intentional overload checked: True. Detailed error and recovery records are in the audit JSON.
Quality metrics on the final 720 recordings are in known-final-test.md and are counted separately from numerical board verification using development recordings.
