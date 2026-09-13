# Daily Development and Collaboration Agreement

Use the project root as the single source directory. The old `upduino-vibration` entry point is only a compatibility symlink; do not create a second editable source copy. Personal machine-specific source and migration paths are retained locally.

Check `artifacts/evidence/current-status.md` first, then select a unified profile. CWRU replay supports the main demonstration and one-/four-MAC architecture comparison; SEN1 serves physical-sensor measurements; FCL1 is trained after real capture data become available, while the current simulated model verifies only the workflow.

## Work Order

1. Fix this iteration's profile, input model, and problem.
2. Run quick checks after changes; interface, quantization, or scheduling changes require the corresponding complete module verification.
3. Before programming, check the current firmware's input binding, timing, and original Flash backup. Use the separate hardware entry point and retain failed and successful attempts.
4. Run complete current acceptance when freezing a release. Historical four-MAC field-resource experiments remain separate research records and are not retuned without a new requirement.
5. Refresh the unified status index. Reports must distinguish software, simulation, formal checks, static place-and-route, and physical-board results.

Register the actual state, session, installation batch, and split before capture. After capture, check quality before adding it to the manifest. Preserve training/validation separation during model selection and perform read-only review of existing frozen test results. Without ADXL345, continue digital replay; do not use the public bearing model to assign fault labels to manual movement.

## Subagent Responsibilities

The main task maintains the current goal, version, and final conclusion. Subagent assignments specify the input version, files allowed to change, output paths, verification method, and stopping condition. Separate implementation from independent verification; the main task integrates results. Every experiment uses its own run-id. Checks without isolation support run serially in their standard directories.

Only one task may access the same UPduino over USB at any time. One entry point coordinates complete regression. Other agents reuse evidence with matching content fingerprints rather than independently repeating training, complete regression, or the overall project plan. Explanations continue step by step around existing real windows and the same source.

The field one-MAC simulation takes 26489 core-computation cycles, approximately 2.207 ms at the target 12 MHz, far below the 320 ms capture window. This excludes capture, queuing, and Flash writing and is not a measured field end-to-end latency. Resume field four-MAC optimization only if real-model resources or measured latency impose a new constraint. Larger networks, envelope spectra, continuous host output, long-duration operation, and ASIC extensions enter later stages according to evidence.
