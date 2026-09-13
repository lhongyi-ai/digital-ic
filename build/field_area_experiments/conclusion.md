# Bounded four-lane field-firmware resource experiments

Decision: do not integrate the experimental changes. Keep the single-MAC field version that already completed system verification and place-and-route.

| Variant | LUT4 | Packed LC / 5280 | EBR / 30 | Result |
|---|---:|---:|---:|---|
| Original four-lane field firmware | 4318 | 5852 | 16 | Over capacity |
| Synchronous timestamp EBR plus one frame ID | 4304 | 5828 | 20 | Over capacity |
| Remove inactive-period RAM read/write collision bypass | 4228 | 5619 | 20 | Over capacity |
| Also use byte-wise record selection and CRC | 4282 | 5664 | 20 | Over capacity |

All variants retain four DSPs, four SPRAMs, the complete model, and all field widths. The first experimental variant ran the existing classifier regression: four tests and 21 output checks passed. The last two variants had already failed resource screening, so full system functional regression was not run. No full-equivalence or deployability claim is made.

Even the best variant exceeds capacity by 339 LC (about 6.4%). Reaching four MACs would require substantial reorganization and renewed verification. The current single-MAC computation takes 26489 cycles, or about 2.207 ms at nominal 12 MHz, well below the 320 ms duration of a 256-sample window at 800 Hz. The three-experiment limit was reached; open-ended optimization was not continued.

All experimental edits were limited to RTL copies in this directory. SHA256 checks confirmed that all nine production source files remained unchanged. Logs, netlists, source files, PCF, and the formal L1 report digests are recorded in report.json.
