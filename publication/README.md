# Publication integrity and reproduction

This is a generated English publication artifact, not a replacement for the original laboratory archive. The local source archive remains at commit `c36464fe24600fcf4a44828278496ac68ea40903`; it is intentionally not part of this published Git history.

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

The sole publication code adjustment beyond English output/path handling lets the EfficientAT training script read its pinned source commit from the included provenance file when vendored without nested Git metadata. It does not change model computation.
