# Completion Audit of the Offline Implementation

> This page retains acceptance records for the preceding CWRU/sensor-measurement version. Counts such as 57 Python tests belong to that historical snapshot. For quantization formal verification, NN boundaries, coverage, field-training entry points, and continuous classification added against the newly supplied plan, see the [offline completion audit for that round](offline-completion.md). Original measurement firmware and separate field-classification firmware have separate acceptance records.

This acceptance review addresses the user's request to determine whether signal processing, RTL, matrix operations, and training were complete, and to fill remaining offline gaps. The user explicitly stated that UPduino was unavailable and ADXL345 had not arrived, and requested completion of the other work first. This review therefore covers source, software experiments, simulation, formal checks, and FPGA builds. It is not physical-board or sensor-measurement acceptance under the four-week plan.

| Requirement | Current implementation and direct evidence | Conclusion |
| --- | --- | --- |
| Signal-processing algorithms | `src/vibfpga/fixed.py` and `rtl/core/vibration_core.sv`: mean removal, scaling, Hann, 16/48 DFT bins, power/neighbor energy, and feature quantization; dedicated inputs match stage by stage in four configurations | Offline implementation and verification complete |
| SystemVerilog RTL | Double input buffers, valid/ready, frame control, shared multipliers, DFT/NN scheduling, ReLU/quantization, error states, and cycle counters; original regression XML passes all four tests in each configuration | Complete; SystemVerilog is the language used to implement RTL |
| Matrix operations | Fixed 16×16 and 3×16 matrix-vector multiplication, shared one/four-MAC configurations; matching models produce identical integer results | Complete for the current vibration-classification design; previously discussed general tiled GEMM or a 2×2 systolic array is not implemented |
| Model training and quantization | Two actual PyTorch checkpoints, floating-point NPZ, INT8 weights/biases, scales, and ROMs; new evaluation preflight checks checkpoint/NPZ/INT8 correspondence | Trained and exported; current models use PTQ, with no claim that QAT was performed |
| Final offline neighbor-model evaluation | `artifacts/reports/neighbor_test/`: one frozen evaluation, nine 3 HP records, 1070 windows; INT8 accuracy 93.18%, macro-F1 0.93236; auditable per-record/window results | Meets this public-data experiment's macro-F1 ≥0.90 target; same old test split, not new external data |
| Core functional regression | 1000 frames per configuration across four configurations, 14 distinct inputs including nine from real validation records; intermediate values checked for every distinct input; ten additional noninteger-bin/phase/clipping/dual-tone frames per configuration | All passed; repeated thousand-frame runs do not represent a thousand independent machine records |
| Numerical and control boundaries | 6651 vectors through actual RTL arithmetic, quantization-shift boundaries, input/output stalls, full double buffers, erroneous frames, and reset during processing | Executed scope passed; complete requirements and NOT_RUN items are in the core verification matrix |
| Fixed sampling cadence | Each of four configurations generates 1,024,000 samples and outputs 1000 frames without loss; overload recovery; another 32 frames with edge timestamps | Simulation passed; four-lane neighbor-bin active computation is about 6.456 ms/frame |
| Formal checks | WIDTH16 FIFO at DEPTH1/3/4, three BMC64 and three cover64 checks; actual full states and arbitrary subsequent reset | All six passed; bounded FIFO checks only, not a formal proof of the whole core |
| Deployable configuration files | Four complete classifier top levels and four sensor configurations, eight bitstreams total, all placed/routed and meeting 12 MHz; input SHA values of four classifier builds match current source/ROM/models | Files generated, not programmed |
| ADXL345 offline pipeline | Independent simulation of SPI, initialization/error handling, raw acquisition, fixed-point calibration, N256 spectrum, Flash logging, and host parsing | Offline implementation complete; raw measurements and calibration parameters await real devices |
| Learning and reproduction | `docs/code-walkthrough.md` and `scripts/trace_frame.py`: validation window [2048:3072] from 107.mat, original-record check, 15 intermediate-result categories, and 15 ROMs; project environment loads in default macOS zsh and bash | Executed and passed |

The final Python unit-test run passed **57 tests**. The evidence index summarizes **36 XML reports**, eight FPGA builds, and six FIFO formal results, and passed verification of the new model-evaluation files. The index is not a new experiment itself; it preserves original report paths, hashes, and scope.

The most direct entry points for this stage are:

- [Real-window code walkthrough](code-walkthrough.md): algorithms, matrix-vector operations, and cycle-level scheduling.
- [Model test results](neighbor-test-results.md): classification metrics, quantization differences, and the records concentrating errors.
- [Core verification matrix](core-verification.md): requirements, cases, checkers, and specific evidence.
- [Automatic evidence summary](../artifacts/evidence/project-status.md): check outcomes and build status.

Once hardware arrives, the next step is to confirm board revision, external 12 MHz clock, and Flash geometry, run public-waveform replay and inspect physical logs, then connect ADXL345 for separate acquisition, static calibration, noise, and repeatability experiments. At this historical stage there is no physical-board accuracy, field-fault diagnosis, measured power, JTAG use, ASIC standard-cell implementation, or signoff result.
