# UPduino Upgrade Requirements and Acceptance Agreement

This document converts upgrade suggestions into testable requirements. Numbers are proposed design targets for this iteration and, unless explicitly linked to a report, do not imply implementation or measured success. The UPduino main board remains unchanged. This iteration implemented a sensor spectrum-buffer storage optimization and added a 64-cycle bounded formal check of the actual replay_fifo. Continuous output, a new sensor classification model, unbounded proofs, and complete physical-board acceptance remain future work.

## 1. Two Operating Modes and Latency Definitions

|Item|R: Public-recording replay baseline|S: Target monitoring of a real low-frequency sensor|
|---|---|---|
|Signal|Fixed CWRU PCM16 file|ADXL345, one axis, 800 S/s, SPI mode 3 / 1 MHz|
|Clock|External 12 MHz|External 12 MHz|
|Window|N=1024, hop=1024|N=256, hop=256; no overlapping windows initially|
|Processing task|Existing frozen neighbor3 + INT8 MLP|Verify the fixed-point spectrum first, then independently train a low-frequency operating-condition model|
|Nominal result rate|11.71875 frames/s, one frame every 85.333 ms|3.125 frames/s, one frame every 320 ms|
|Core requirement|Bit-for-bit equality across configurations with identical inputs and model|Spectrum matches the integer reference bit-for-bit; classification quality evaluated separately|
|Last sample accepted → internal result valid|Proposed maximum 30 ms|Proposed maximum 40 ms, including queuing, computation, and result enqueue|
|First sample accepted → internal result valid|Proposed maximum 120 ms|Proposed maximum 360 ms|
|Status|Existing offline replay system and simulation|Currently only independent capture, spectrum processing, and end-of-run Flash logs; complete continuous monitoring remains unimplemented|

“First sample” means when the FPGA accepts the first sample of the window; “last sample” is defined similarly. “Internal result valid” means core output valid in the current path without a result queue, and successful enqueue of the complete result in a future queued path. Record core completion separately and do not conflate the two. The first-to-last sampling span is 1023/12000=85.25 ms in R mode and 255/800=318.75 ms in S mode. N/fs is the period between adjacent nonoverlapping windows and must not be confused with (N−1)/fs.

Record separately when the internal result becomes valid, when the link finishes transmitting its packet, and when the host receives and displays it. Current SEN1 writes Flash only after the run ends and does not meet real-time host-result requirements. A future UART could use 115200 baud, 8N1; serialization alone takes approximately 5.56 ms for a 64 B packet. This excludes host scheduling delays and is not complete end-to-end latency.

The existing one-MAC R-mode simulation reports 24.951 ms core computation and 110.201 ms from first sample to output, meeting the loose internal deadlines above. Tightening the first-sample deadline to 100 ms would disqualify the existing one-MAC design; the existing four-MAC simulation value is approximately 91.706 ms. Compare architectures against unchanged requirements rather than assuming either architecture must be best. Older cycle tests differ from the complete board FIFO configuration; final checking must use the complete top level. [Existing architecture report](../artifacts/reports/architecture.md)

Actual S-mode ODR must be measured. Report the 40 ms processing deadline independently. The first-sample deadline assumes nominal ODR; record capture-duration changes caused by ODR deviation separately. Service timestamps are not the sensor's internal ADC sampling instants and cannot establish measured aperture jitter.

## 2. Data Integrity and Fault-Handling Targets

Normal operating conditions mean the specified input rate, correct wiring and power, a host able to receive continuously, and fixed input/output buffer capacities and link configuration. Under those conditions, the target is no missing, repeated, or reordered samples after FPGA acceptance, and no observable sensor overrun or service-interval anomaly.

The ADXL345 has no monotonic sequence number for each conversion, and overrun is a status bit. Consequently, “no evidence of lost samples observed” on physical hardware does not prove that every internal conversion was read. Verify exact loss counting with a digital test source that provides known sequence numbers. On physical hardware, record known discard counts and sensor overload events whose losses cannot be counted exactly.

The future continuous system shall use these explicit policies:

|Event|Target behavior|Check and pass criterion|
|---|---|---|
|Normal input|Capture in order and process complete windows|Match every item with fixed test input; account for all accepted sequence numbers|
|Input buffer full|Preserve stored data, reject new input, and count known discards|Test full/simultaneous read-write/reset boundaries; unread data must not be overwritten|
|Sensor overrun, known discard, or abnormal interval|Invalidate the current window, clear its partial data, and collect a new complete contiguous window|Do not classify a normal window assembled across a gap; record the invalidation reason|
|Host temporarily stops receiving|Continue capture; when the result queue fills, discard newly completed results and preserve complete queued packets|Record dropped_results; frame sequence numbers reveal gaps to the host; fix and report queue depth|
|Result-packet/command CRC failure|Receiver rejects the packet and searches for the next synchronization boundary|Inject flips/truncation into every field and payload; a corrupt packet must not become a normal result|
|No newly accepted sample for 1 second|Mark acquisition failed and stop producing valid classifications|Time from the last accepted sample; enter error handling within bounded control cycles after the threshold|
|Wrong device ID / configuration readback mismatch|Prevent normal acquisition or classification|Reject injected 0x00, 0xFF, incorrect IDs, and configuration mismatches|
|Reset during a run|Cancel partial input windows and incomplete packets, reinitialize, and use a different run_id for the new run|Do not mix old run_id sequence numbers/results; preserve the old Flash log|

Some handshakes, error counters, CRC, watchdog, and commit protection already exist. This table specifies their extension to a continuous system; it does not mean every policy has been implemented. An ID error currently requires reset, and there is no automatic reconnection state machine after watchdog failure. The physical top level has startup reset only, so manual recovery currently requires FPGA reconfiguration or a power cycle. A runtime reset interface and run_id remain to be implemented. When an old Flash log exists, restarting rejects new capture: first back up and explicitly clear the log, or implement new log partition management. If automatic recovery is implemented later, specify retry counts, backoff, and log protection then.

SPI sensor reads have no ACK or payload CRC. CRC protects subsequent result packets only and cannot prove that the acceleration read from the sensor is correct. Periodic checks of DEVID/key configuration, DRDY, and signal plausibility improve detection but cannot guarantee discovery of every bit error that produces a plausible value.

## 3. Small-Module Verification Scope

1. Establish ordering, occupancy, stable-output, and no-duplication properties for the actual `replay_fifo`; existing `sync_fifo` BMC64 is not its proof.
2. Check mutual exclusion among frame-buffer writing, processing, and release, including reset/abort transitions. State environmental assumptions for liveness/deadline claims, such as eventual consumer acceptance.
3. Attempt unbounded induction for small modules where feasible. If incomplete, label BMC depth, parameters, and coverage boundaries accurately. Do not claim proof of the entire classifier.
4. Digital-source tests use known sequence numbers; physical-sensor tests retain the observational limitations of service timestamps and overrun.

Added in this iteration: `formal/run_replay_fifo_formal.py` reads the actual 49-bit, two-entry `replay_fifo` from `rtl/upduino_replay.sv`. BMC64 and cover64 pass with five reachable scenarios. The independent report is `build/replay_fifo_upgrade/report.json`. This fills the bounded-check gap for the actual queue; it is not a proof for arbitrary run lengths or formal verification of the complete sensor chain.

## 4. Storage-Optimization Interface Constraints

Preserve the SEN1 format, the ordering of its 16 uint32 powers, raw-record contents, and latest-complete-window semantics.

The existing raw buffer is 3×32768=98304 B. The default raw log uses 24000×4=96000 B, leaving 2304 B. Moving the 64 B spectrum buffer into the tail of the third block leaves 2240 B and eliminates the fourth physical SPRAM instance. This saves one quarter of the SPRAM block count; it is not a 25% board-level power saving.

Required checks: address limits and nonoverlap; complete two-word writes for raw sample/interval pairs; complete low/high-half writes for spectrum power; single-port memory arbitration; export only after the final spectrum window completes; reset and spectrum-disabled configurations. Include any added handshake stalls in worst-case service-time verification.

Acceptance: a complete build under matching conditions decreases from four to three SPRAM blocks, stays within logic capacity, passes 12 MHz timing, preserves bit-accurate raw/spectrum output, and adds no error counts. Area and timing may trade off; report actual results without assuming every metric improves.

## 5. Staged Physical-Board Acceptance

|Stage|Evidence to retain|
|---|---|
|Board startup|Board version, wiring diagram, Flash ID, firmware hash, DEVID=0xE5, configuration readback|
|Digital replay|Same frozen model/input; per-frame comparisons, cycles, and error counters|
|10-minute sensor run|Retained raw-data range, whole-run statistics, actual ODR, interval distribution, and the window represented by the final spectrum|
|1-hour continuous system|Run only after continuous output and timer-wrap handling are implemented; retain the full result sequence and reasons for gaps|
|24-hour continuous system|Complete short tests in three independent sessions first; long tests record environment, resets/discards/anomalies, and actual runtime|

Current 10-minute firmware retains only the first 30 seconds of raw data and the last spectrum frame; it cannot substitute for 24 hours of continuous recording. Before long tests, review run-length configuration, all counter widths, and wrap handling. service_wrap_count already exists. Although 24 hours×800 S/s=69,120,000 samples fits a 32-bit count, this does not imply all time fields need no handling. A 32-bit cycle counter at 12 MHz wraps approximately every 357.914 seconds.

An anomaly-free physical test establishes success only for that board under the tested conditions. Repeated fixed frames stress the system but are not additional independent machine-learning data. Group new-model training/testing by date, remounting, and complete acquisition session.

## 6. Sensor Selection

Keep the ADXL345 as the default, at 800 S/s for actual low-frequency operating conditions. For procurement, first verify the Digilent Pmod ACL **410-097** (not ACL2) version with installed connectors; SPI and INT1 must both be exposed. [DigiKey product page](https://www.digikey.com/en/products/detail/digilent-inc/410-097/3902808), [manufacturer information](https://digilent.com/shop/pmod-acl-3-axis-accelerometer/). Another explicitly pre-soldered-header product is the [ShillehTek ADXL345](https://shillehtek.com/products/shillehtek-adxl345-pre-soldered); verify the exact version and INT1 when purchasing.

Local interface agreement: [physical connections and verification steps](hardware-validation.md). ADXL345 at 800 S/s cannot support the original CWRU model's 0.94–5.50 kHz features. A higher-bandwidth sensor route requires separate driver, sampling, and model verification. Solder-free I2C through a four-wire STEMMA QT / Qwiic connector is not the solder-free SPI+INT1 interface currently required.

## 7. Related Files

- [Measurement and power comparison under matching conditions](upgrade-measurement-plan.md)
- [Completed storage optimization, build tradeoffs, and six regression groups](storage-optimization-2026-09-08.md)
- [Existing sensor log format](sensor-log-format.md)
- [Existing verification matrix](core-verification.md)
