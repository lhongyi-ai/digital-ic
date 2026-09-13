# N256 continuous field classification and FCL1 logs

The added `upduino_field` is separate firmware: ADXL345 SPI sampling → raw-count processing → N256 shared DFT/INT8 core → window results in SPRAM → Flash writes after acquisition stops. Existing `upduino_sensor` remains the path for raw acquisition, static calibration, and spectrum measurement; this version does not replace SEN1.

All inputs in this iteration came from mathematical signals or an SPI behavioral model. No real training data exists yet for the field model. The simulated model is explicitly labeled, and builds and logs retain that label.

## Control and resource tradeoffs

Input is single-axis data at 800 Hz, with 256-sample windows lasting 320 ms. Two timestamp slots represent at most two complete, undelivered windows. The same cycle may deliver an old output and accept the first sample of a new window. A known gap or an incoming source sample without available buffering cancels every complete/partial in-flight window, updates counters, and starts the next window with a new ID. Cancellation is a protocol event; output-stability assertions explicitly exclude reset/gap. Samples from opposite sides of a loss are never joined into a “continuous window.”

Acquisition does not slow down to wait for downstream ready. The top level continues reading the sensor, with dropped-sample/overload and service-error counts exposing problems. Recorded time is register-readout time, not the sensor's internal ADC sampling time.

A default run contains 480000 samples, nominally 10 minutes, with at most 1875 classified windows. Each result occupies 64 bytes, totaling 120000 bytes across four SPRAM blocks. A formal 10-minute physical run remains pending. This iteration's integration simulations used shorter sequences and cannot be reported as a measured 10-minute run.

One-lane core computation takes 26489 cycles and four-lane computation 7348 cycles: approximately 2.207 ms and 0.612 ms at 12 MHz. These are simulated computation times, excluding the 320 ms needed to form a window. One-lane computation occupies approximately 0.69% of an acquisition window and already meets the continuous field-classification processing budget.

Initial complete-firmware resource comparison: UP5K SG48, 12 MHz, seed 1, same simulated model.

| Configuration | LC / 5280 | DSP | EBR | SPRAM | Complete placement/routing |
|---|---:|---:|---:|---:|---|
| One MAC | 5125 | 1 | 10 | 4 | PASS, estimated Fmax 19.12 MHz |
| Four MACs | 5852 (packed requirement) | 4 | 16 | 4 | FAIL, exceeds logic capacity |

The current complete field firmware therefore uses one MAC. Four-MAC field algorithm/interface simulation passed, but this does not establish a complete field image that fits the UPduino. The original CWRU four-MAC firmware has separate successful placement/routing evidence and uses different peripherals and log organization.

Three bounded resource experiments used independent build copies: synchronous timestamp EBR plus merged frame IDs required 5828 LC; removing RAM-collision bypass logic that only affected invalid data required 5619 LC; switching further to bytewise log/CRC processing required 5664 LC. All failed capacity checks. The best remained 339 LC over budget, so these incompletely validated experimental copies were not merged into production RTL. Raw logs and hashes in `build/field_area_experiments/` are retained locally to explain the resource bottleneck.

These resource counts depend on the current simulated weights. A real field model requires new synthesis, placement/routing, and resource verification after training. The one-lane version has limited logic headroom, so arbitrary future weights cannot be promised to fit directly.

## FCL1 binary format

Flash retains log region `[0x300000,0x320000)`. The 256-byte header starts at 0x300000; results start at 0x301000, with 64 bytes per window. Configuration and input regions cannot be written. Production firmware scans the complete 128 KiB log region at startup and stops if any byte is not FF. The host must export existing logs before explicitly erasing the required log region.

All fields are little-endian 32-bit words. Main header word indices:

| Word index | Contents |
|---|---|
| 0–3 | FCL1 magic, version 1, result count, COMT completion marker |
| 4–15 | Errors, observed/target samples, 800 Hz/12 MHz/N256, axis, LANES, accepted/dropped/canceled/clip counters |
| 16–23 | Model JSON SHA256 in original 32-byte order |
| 24–29 | missed_service, sensor_overruns, first/last readout times, timestamp wrap count, samples in the incomplete trailing window |
| 30–37 | Payload CRC32, header256, record64, payload address, cancellation-event count, device ID, maximum 1875 records, simulated-model flag |

Each 16-word result contains, in order: frame_id; three signed32 logits; class/error; PRE/DFT/POWER/NN/TOTAL cycles; first/last sample-readout times; time the result became available for storage; and accepted/dropped/clip snapshots. The result timestamp is latched when storage starts, followed by 32 clocks to write the record. The core holds that output until the completed-record handshake.

Global error bits are: bit 0 existing log nonempty; 1 incorrect device ID; 2 acquisition timeout; 3 source gap/overload; 4 NN arithmetic error; 5 result-capacity overflow; 6 Flash error; 7 invalid parameters/state. A global error does not automatically invalidate every completed record. Classification scores may be interpreted only for uncanceled results whose own NN error is zero.

A record's CRC contributes to total CRC only after its complete 64-byte write. If a gap cancels an in-progress record, that record and its temporary CRC are discarded; the next complete record overwrites that position. After header and payload completion, COMT is written separately and last. Power loss/reset during a write leaves a nonempty, incomplete region that prevents automatic overwriting on the next run.

`src/vibfpga/field_log.py` checks completion marker, geometry, model hash when supplied by the caller, CRC, length, frame-ID order, and counter invariants. The 32-bit timer wraps at 12 MHz; adjacent timestamp differences use modulo 2³², while total acquisition duration also retains a wrap count.

```sh
source scripts/env.sh
python scripts/read_field_log.py build/field_system_l1/nominal/report.bin --output build/field-log-decoded.json
```

This command parses an existing file without connecting to hardware. Decoding FCL1 alone does not prove physical-device provenance; retain readback records and experiment sources.

## Checks actually performed in this iteration

Each LANES version ran six SPI-pin-level system tests:

- 773 simulated samples at 800 Hz, yielding three complete windows and five trailing samples. Scores and first/last timestamps matched an independent integer reference.
- One deliberately extended service interval canceled the affected partial window, then produced two correct windows, with error and recovery counters checked.
- Incorrect device ID and cessation-of-sampling timeout each generated an explicit error log with zero results.
- Reset after header write left no completion marker, and the next run did not overwrite the old region.
- A non-FF value in the last byte of the log region prevented execution using the full production 128 KiB scan.

All programming transactions also checked page boundaries, WREN/WIP, log-region boundaries, and configuration-region hash. Ordinary functional scenarios shortened blank scanning for simulation speed; the final-byte scenario used the complete scan. `ICE40` production builds prohibit shortened-scan parameters.

The separate classifier has eight additional tests, including long output stalls, continuous windows, simultaneous transmit/receive with full buffering, extrema clamping, explicit gap/overload, reset during processing, and timestamp wrap. The FCL1 parser has 54 handcrafted positive/negative binary cases. These checks are distinct from acceptance of physical SPI levels, sensor noise, absolute frequency response, or accuracy on real operating states.

Reproduce with `make field-sim`; build the complete one-lane image statically with `make field-board`. At this report's historical stage, default pins came from the v3.x reference, while the user's board revision, external-clock jumper, and Flash part were not yet confirmed, so no programming was performed.
