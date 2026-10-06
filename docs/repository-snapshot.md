# Repository snapshot and publication scope

This update publishes completed engineering work through October 6, 2026, on top of the existing English GitHub history. The private laboratory Git history is not merged or pushed. The laboratory archive retains original pre-translation sources, receipts, failed attempts, and device recovery material.

## Included progress

The shared fixed-point accelerator has iCE40 SPRAM, AMD inferred-BRAM, and reference memory implementations with one verified synchronous contract. Candidate C pipelines final normalization without changing the frozen models or thresholds. It passes the complete planned correctness, resource, timing, input-cadence, and physical replay gates. Additional D/E optimization candidates were unnecessary.

The [experiment report](../artifacts/vivado-portability-v1/report.md) and [physical report](../artifacts/vivado-portability-v1/physical-report.md) separate simulation, implementation estimates, and actual board evidence. Original 3.78x MAC parallelization and historical model-quality findings remain distinct. Final test data was not reevaluated for this work.

## Privacy and omissions

Excluded material includes private captures, personal chat/account usage audits, local connection settings, authenticated desktop links, scheduler-account diagnostics, license-server configuration, the original Flash recovery image, virtual environments, downloaded toolchains, compiler caches, and generated host executables. Bulk downloaded datasets and external checkpoints remain excluded as in the previous publication. Regenerable large simulation vectors, tool databases, netlists, and checkpoints containing local tool metadata are retained locally; their original hashes can appear in historical receipts.

Published input/result payloads used in this experiment originate from the documented public development recordings. No private audio or sensor capture is included. A small fixed subset of public development PCM dependencies is included with the baseline archive. Source manifests and download recipes describe how to restore the remaining public dependencies.

## Evidence integrity

The publication manifest records original and published digests. Historical experimental hashes remain historical; translation and path redaction are not presented as original experiment bytes. The completed pre-programming release, physical audit, and final acceptance receipt describe the preserved laboratory version. Published derivatives may not pass those original byte-level gates; use `python3 scripts/verify_publication.py` to verify this snapshot, and run fresh engineering validation after restoring dependencies before programming a board.

All included text, decoded JSON metadata, Markdown, source comments, labels, and file names are checked for CJK content and private local paths. The language/privacy check is separate from engineering tests and does not access the final evaluation dataset or USB hardware.
