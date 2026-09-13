# Architecture comparison

Resources come from place-and-route of the full replay system; cycles come from RTL simulation. At this historical stage, no hardware or power measurements had been made.

| Features | MAC | LUT4 | Registers | Packed LC / 5280 | DSP | EBR / 30 | SPRAM / 4 | Post-route estimated Fmax |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| single_bin | 1 | 2708 | 1517 | 4088 | 1 | 19 | 3 | 20.57 MHz |
| single_bin | 4 | 3453 | 1663 | 4842 | 4 | 25 | 3 | 19.37 MHz |
| neighbor3 | 1 | 2915 | 1563 | 4306 | 1 | 19 | 3 | 21.91 MHz |
| neighbor3 | 4 | 3733 | 1709 | 5129 | 4 | 25 | 3 | 18.58 MHz |

| Features | MAC | DC removal/Hann | DFT | Power/quantization | MLP | Total active cycles | Active time at 12 MHz |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| single_bin | 1 | 3073 | 98368 | 140 | 950 | 102531 | 8.544 ms |
| single_bin | 4 | 3073 | 24616 | 140 | 265 | 28094 | 2.341 ms |
| neighbor3 | 1 | 3073 | 295104 | 284 | 950 | 299411 | 24.951 ms |
| neighbor3 | 4 | 3073 | 73848 | 284 | 265 | 77470 | 6.456 ms |

A separate 32-frame test records cycle-level timestamps. The following are actual simulation time differences, not estimates from theoretical throughput.

| Features | MAC | First sample to output | Last sample to output | Output frame interval |
| --- | ---: | ---: | ---: | ---: |
| single_bin | 1 | 93.795 ms | 8.545 ms | 85.333 ms |
| single_bin | 4 | 87.591 ms | 2.341 ms | 85.333 ms |
| neighbor3 | 1 | 110.201 ms | 24.951 ms | 85.333 ms |
| neighbor3 | 4 | 91.706 ms | 6.456 ms | 85.333 ms |

The timestamp test uses FIFO depth 4; the full-board replay uses two slots to save resources. Both reach maximum occupancy 1 at normal cadence. The full Flash chain has separate simulation evidence; overload results must retain their own configurations and cannot be conflated.

All comparisons use the same model, algorithm widths, and 12 MHz target clock. LUT4 counts differ from packed LC counts; assess UP5K capacity using LC.

`cycles_total` sums the active cycles of DC removal/windowing, DFT, power/quantization, and neural-network stages. It excludes input wait, queuing, output backpressure, and Flash transfers. It is not the total latency from host input to host result.

The fixed-cadence test produces one sample every 1000 clocks independently of ready. Replaying 1000 frames verifies sustained processing; it does not represent 1000 independent training/test recordings. Each window lasts 85.333 ms.

Detailed stage cycles, fixed-cadence counters, and latency distributions are in architecture.json. Power is unmeasured; place-and-route success is neither a hardware test pass nor ASIC sign-off.
