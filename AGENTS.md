# Digital IC project working rules

Work in this repository root. Preserve existing modifications and historical evidence.

## Locate before reading

- Start engineering work with `artifacts/evidence/current-status.md` and identify the goal, configuration, and acceptance criteria. Reuse previously read state when it has not changed.
- The status page indexes saved evidence; it does not prove current device connectivity or matching source. Check relevant input bindings before drawing current conclusions. Refresh with `python scripts/collect_current_status.py` only when needed.
- Use `rg` to locate relevant files, symbols, and lines. Expand scope when information is insufficient. Avoid reading all documentation, datasets, historical chats, or complete build logs by default.
- Select documentation for the task: `docs/code-walkthrough.md` for explanation; `docs/implementation-contract.md` and `docs/core-verification.md` for RTL and arithmetic; `docs/data-workflow.md` and `docs/field-training.md` for data; `docs/hardware-pinout-clock.md` and `docs/hardware-validation.md` for board work; `docs/workflow-efficiency.md` and `docs/collaboration-workflow.md` for verification and collaboration.

## Tool output

- Batch independent queries; sequence dependent operations. Wait reasonably for long tasks. Do not repeat reads or verification without changed files or new diagnostic evidence.
- Save complete build/test logs per run. Report real exit codes, pass/fail/skip counts, key metrics, and log paths. Successful output filtering is not successful execution.
- Preserve FPGA frame counts, numerical comparisons, dropped-sample/overflow checks, cycles, timing, and resource metrics. On failure, identify the case, expected/actual behavior, and relevant error context.

## Verification and stopping

- Load `scripts/env.sh` from the repository root. Select `make quick` or `make module MODULE=...` according to scope. Interface, quantization, and scheduling changes require corresponding complete module checks; prose changes require content and reference checks.
- Run `make release` when freezing a release or required by scope. Use one entry point for the same version's full regression. Reuse evidence only when source, model, configuration, and tool bindings match. Retry after a change or new diagnostic finding.
- Do not retrain frozen models or revisit final test data for tuning. Resume paused routes only when requested or justified by new evidence. Stop at agreed acceptance.
- Only one task may access the UPduino USB device at a time. Follow existing binding and backup procedures. Distinguish software, simulation, formal verification, place and route, and physical measurement; fixtures are not physical evidence.

## Collaboration and handoff

- Delegate only independent work with clear benefit, where the current runtime allows it. Provide goals, paths, interface constraints, edit scope, acceptance, and stopping criteria. Avoid duplicated overall planning or conflicting writes.
- Agents return conclusions, changed paths, verification, and unresolved issues; keep long reports in files. Review relevant changes without repeating completed checks without cause.
- Handoffs record goals, completed work, evidence, blockers, and next steps. Update the existing unified evidence index rather than creating parallel status pages. Keep this file limited to stable rules.
- Concise context must still retain code, interface constraints, error details, and verification necessary for correctness.
