# Publication integrity and reproduction

This is the October 6, 2026 English publication update, built on the existing English GitHub history. It is not a replacement for the original laboratory archive. The local source archive remains at commit `c36464fe24600fcf4a44828278496ac68ea40903`; it is intentionally not part of this published Git history.

## Validate the publication

From the repository root, run:

```bash
python3 scripts/verify_publication.py
```

The verifier checks included file digests, the manifest digest anchor, language-bearing text and structured metadata, forbidden local paths, and basic JSON/Python syntax. It does not execute models, train, touch USB, or rerun final evaluation. Its report is printed to standard output.

`publication/manifest.json` binds every published file to its SHA256 value. For files originating in the local archive, it also retains the original SHA256 and transformation classification. The manifest itself is anchored by `publication/manifest.sha256`; this anchor is outside the manifest to avoid self-reference. The Git commit binds both.

## Interpret historical experimental hashes

Original audit receipts bind the exact original experiment inputs. English prose, output labels, or local paths can change in the published copy, and the original files are not reconstructed by the publication verifier. A translated file therefore may not pass a historical byte-for-byte audit script. Consult the original/published hash pair and transformation classification rather than changing an old receipt to claim a new experiment.

RTL, model parameters, numerical arrays, bitstreams, and raw result-readback payloads have been compared to the local source archive. Preserved numerical results remain historical results; no new physical measurement or new model-quality result is claimed. Translation-only reporting edits are checked separately from the arithmetic implementation.

Bulk datasets, external checkpoints, and the pre-project Flash recovery image are deliberately absent. Source manifests and licenses explain how to restore downloads. A recovery image must be made and verified for the actual target board; an archived board profile is not proof that a new board is connected or safe to program.

The publication now also makes the remote SSH destination configurable through `VIVADO_SSH_HOST`, without including a personal alias. The earlier publication code adjustment beyond English output/path handling lets the EfficientAT training script read its pinned source commit from the included provenance file when vendored without nested Git metadata. It does not change model computation.

## October portability evidence

The completed cross-FPGA experiment and physical runs predate this translation. Their receipts preserve original experimental hashes. The manifest separately binds published English/redacted bytes. Private scheduler-account logs, connection identity, checkpoints with local metadata, and device recovery images are omitted. Required report summaries, timing/resource reports, failed-attempt evidence, model parameters, and raw physical result bytes are included. Regenerable bulk vectors and compiler state remain local.

Software tests were rerun on the exported English tree. These tests and the publication scan do not reopen final recordings, retrain models, or access the board. See `publication/validation.json` for the current checks; earlier publication findings are retained there as historical context.
