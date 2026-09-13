# Verification plan and evidence boundaries

The committed checks below exercise the synchronous FIFO. The SPI, sensor,
calibration, spectrum, and Flash system checks are documented separately in
[sensor-log-format.md](sensor-log-format.md). FIFO checks do not by themselves
validate the vibration datapath, SPI sensor, board wiring, or any physical device.
The implementation contract defines the system-level interfaces and arithmetic.
The actual DSP/MLP requirements, directed waveform checks, four-configuration
regressions and explicit remaining gaps are mapped in [core-verification.md](core-verification.md).

## FIFO contract

`sync_fifo #(WIDTH=16, DEPTH=4)` accepts `in_data` only at a rising clock edge
with `in_valid && in_ready`. It removes `out_data` only with
`out_valid && out_ready`. All ports share one clock. `rst` is active high with
synchronous state clearing; asserting reset suppresses both handshake outputs
immediately, and the following rising edge clears pointers and occupancy.

Legal parameters are integer WIDTH >= 1 and DEPTH >= 1, with COUNT_W left at
its default `$clog2(DEPTH+1)`. There is no empty bypass: a write to an empty
FIFO first becomes valid after the accepting edge. When full, an accepted pop
permits an accepted push on the same edge, preserving full occupancy. Output
data remain stable while valid and stalled unless reset cancels the transfer.
Output data are unspecified when out_valid=0; payload RAM is not reset.
The `out_ready -> in_ready` path is combinational and must not be connected
into a combinational ready loop in a larger system. This is not an async FIFO
and provides no clock-domain crossing protection.

## Requirements and checks

| Requirement | Required behavior | Simulation evidence | Formal safety property |
|---|---|---|---|
| FIFO-RESET | Empty and occupied reset cancel all data | Directed occupied reset, random mid-stream resets, post-reset drain | First sampled edge assumes reset; every subsequent reset is unconstrained and must clear occupancy |
| FIFO-BOUNDARY | No underflow, overflow, or empty bypass | Empty read attempts, stalled full writes, occupancy scoreboard | Count bounds and exact valid/ready equations |
| FIFO-EXCHANGE | Full pop+push is accepted without a bubble | Repeated full exchanges at depths 1, 3, 4 | Tracked word and independent count agreement on simultaneous transfers |
| FIFO-STALL | Hold the output under sink backpressure | Five-cycle full stall and random ready gaps | Previous valid+stalled implies valid and stable data, unless reset |
| FIFO-ORDER | Accepted words emerge once in FIFO order | Deque scoreboard; more than two buffer wraps; final drain | An arbitrary accepted word reaches the head after exactly its predecessor words are removed |

Simulation uses deterministic random seeds `0xAD345 + DEPTH`, WIDTH=16,
DEPTH=1/3/4, and 3,000 random cycles per configuration after directed checks.
All comparisons happen at the handshake edge; unused/invalid output data are
not compared. Random producer data are held until accepted. The directed
tests also show that a blocked write cannot change storage.

The formal harness has a free input payload, input valid, sink ready, and reset.
Its only environmental assumption is reset on the first sampled clock edge.
It does not need to assume a compliant producer holds data during a stall:
the FIFO stores only accepted words. WIDTH=16 and DEPTH=1/3/4 are separate
elaborations. These results are not a proof for all possible parameters.
An unconstrained `watch` signal chooses an arbitrary accepted word. The
harness stores all 16 bits of that word and the number of accepted words
ahead of it. Each pop removes one predecessor; once none remain, the output
must be valid and equal to the saved word. Because the choice is unconstrained,
any accepted word can be checked. This uses an abstract transaction model,
without reimplementing the DUT's ring pointers or assuming a particular
payload. The independent count model checks occupancy and transfer controls.

The SymbiYosys BMC tasks use ABC `bmc3` and check all assertions through bound
64. Cover tasks use SMTBMC with Bitwuzla
at the same bound request five reachable scenarios: full occupancy, full
pop+push, draining after full, at least three buffer lengths of accepted
writes with an exchange, and reset while occupied followed by empty.
Passing BMC is bounded safety evidence, not an unbounded inductive proof or
liveness guarantee under arbitrary backpressure.

## Reproduce

Source `scripts/env.sh` to activate the project Python environment and add
the installed OSS CAD Suite `bin` directory to PATH. These commands build and run tools; none program
hardware or modify Flash.

```sh
source scripts/env.sh
.venv/bin/python sim/run_fifo.py
.venv/bin/python formal/run_fifo_formal.py
.venv/bin/python formal/run_sva_smoke.py
.venv/bin/python formal/report_fifo_evidence.py
```

The simulation writes `build/fifo_scenario_coverage.json` and per-depth
`results.xml`. Formal produces per-task logs, statuses, and witness traces
under `build/formal/`. SVA smoke records the actual Verilator version,
compiles a clocked property using `disable iff`, nonoverlapping implication,
and `$past`, then runs positive and deliberately failing negative controls.
Only this tested assertion subset is claimed; this is not full SVA support.

`formal/report_fifo_evidence.py` maps generated results to the table above.
Missing evidence remains NOT_RUN rather than being inferred from source code.
Regenerate evidence after source changes. Scenario hit counts are functional
scenario coverage, not measured HDL line, branch, toggle, or FSM coverage.

## Broader project scope

System arithmetic still requires comparisons to the independent integer
reference at each stage, including rounding ties, saturation, and class ties.
Integration requires framing errors, input and output stalls, reset during
computation, and replayed complete frames. These are owned by the datapath and
integration tests, not proved by this FIFO harness. RTL lint, synthesis and
timing reports are distinct evidence from functional verification.

SPI programming must not be described as JTAG debugging. This project can
demonstrate RTL design and pre-silicon verification methods on an FPGA, but
does not establish ASIC signoff, transistor-level analog verification, CDC
signoff, board bring-up, measured power, or sensor acquisition without the
corresponding additional evidence.

## Executed results

Initial local run, 2026-09-05:

- Simulator: Verilator `5.051 devel rev v5.050-312-gb1c06fdb0 (mod)`,
  cocotb 2.1.0, Python 3.12.10. The runner explicitly selects C++17 for
  compatibility with the local Apple compiler.
- WIDTH=16, DEPTH=1/3/4 simulation: all three tests passed. Respectively
  3,023 / 3,037 / 3,044 cycles, totaling 9,104 cycles. Every required
  scenario counter was hit for every configuration.
- Verilator `--lint-only -Wall` for the default FIFO: passed without warnings.
- SVA positive control passed; injected count-step error exited with code 1
  and the expected `SVA_INCREMENT_FAILURE` message. The recorded version and
  logs are in `build/sva_smoke/`.
- Formal WIDTH=16, DEPTH=1/3/4: all three BMC64 tasks and all three cover
  tasks passed. All five requested cover statements were reached in each
  configuration. Required depth-4 BMC completed in approximately 50 seconds.
  Tools: Yosys `0.68+195` (git `435977e97-dirty`), SBY `v0.68`, ABC `bmc3`,
  and Bitwuzla `0.9.1` for cover. The `dirty` suffix is the bundled build's
  reported version, not a claim about this project's source control.

Evidence directories under `build/` referenced in this document are retained locally when omitted from this publication. Their reported results remain historical evidence, not fresh execution of the exported sources.
