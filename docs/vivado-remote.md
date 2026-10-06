# Remote Vivado environment and reproducible runs

The remote environment was verified on October 6, 2026, through an existing SSH connection to the university Linux laboratory. Vivado was not installed on the Mac. Separate Cadence projects and their connection environment were left unchanged.

## Environment

- Architecture: x86_64; Rocky Linux 8.10 container.
- Module: `xilinx24`, explicitly selected from the laboratory module directory.
- Vivado 2024.2, SW Build 5239630; target `xc7a35tcpg236-1`.
- The module provides the university Xilinx license configuration.
- An independent nine-bit adder synthesis smoke test passed with zero errors and zero critical warnings. It mapped to 3 CARRY4, 8 LUT2, and 9 FDRE and emitted `VIVADO_SYNTHESIS_SMOKE_PASS`. It had no timing constraints and is not timing-closure evidence.

Personal SSH aliases, user names, allocation-account records, license-server addresses, and authenticated desktop URLs are omitted from this publication. Configure a local SSH alias and set `VIVADO_SSH_HOST` before using the runner. Container and module paths may need adjustment for another installation.

## Batch entry point

`scripts/run_known_vivado.py prepare` creates a unique package containing the shared RTL, model ROMs, vectors, reference values, Tcl, constraints, and SHA256 manifest. `submit` checks upload digests and submits Slurm work; `collect` preserves the terminal job state, real exit code, raw reports, and output hashes. Failure never becomes a passing receipt.

Implementation uses the laboratory partition, two CPUs, 16 GiB, and four hours. Simulation uses up to eight hours. Heavy work runs in the allocation, rather than on the staging host. The runner requires one unambiguous numeric job ID and does not generate a passing report while a job remains active.

XSim uses `xelab -timescale 1ns/1ps -mt 2`. Full-recording simulation supplies input as quickly as the ready/valid protocol permits and checks each integer intermediate event. Fixed sample cadence is separately checked by full-size local simulations and physical replays.

## Constraints and acceptance

The core is synthesized out of context. The 20 ns clock and 2 ns input/output delays are explicit module-interface assumptions. Reset is synchronous; no false-path or multicycle exception hides a single-cycle path. Core/debug/cycle ports remain observable. All B/C implementations use the same tool version, thread count, and default directives, without incremental implementation.

`make portability-check` validates the required evidence and targets. `make portability-release` generates an independent pre-programming receipt only after the gates pass. The original laboratory receipts remain preserved. Published English/path-redacted derivatives must be interpreted through the publication manifest; they are not substituted into historical byte-level gates.

## Visible GUI inspection

Vivado GUI was opened in a separate directory in the existing remote interactive desktop session and loaded the actual C ID00 four-MAC routed checkpoint. The timing and internal-path reports showed a 15.018 ns internal path: 6.961 ns logic and 8.057 ns routing, with 4.929 ns setup slack. These are implementation results; USB board verification ran separately on the Mac.

To reopen, use the current interactive-session launch button and open the corresponding checkpoint. Do not save authenticated desktop URLs or session passwords in source control. No AMD board was used, so passing OOC constraints do not establish board-level I/O timing.
