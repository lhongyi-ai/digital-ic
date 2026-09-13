# English GitHub publication snapshot — September 13, 2026

Destination: the owner-authorized private repository `lhongyi-ai/digital-ic`.

This publication is prepared from the complete local archive at commit `c36464fe24600fcf4a44828278496ac68ea40903`. That archive contains earlier English/Chinese documentation and machine-specific records and remains local. It is not an ancestor of the published branch. Publishing a clean root commit prevents old Chinese files or private paths from remaining accessible through Git history.

## Included

- Complete project Python and SystemVerilog source, tests, simulation and formal harnesses, build/data scripts, and engineering configurations.
- English translations of the technical documentation, historical failures, acceptance criteria, implementation contracts, and reporting/UI strings.
- Frozen project models, model candidates, feature arrays, split manifests, prediction scores, metrics, and audits. Successful and unsuccessful research routes are both retained.
- Relevant FPGA bitstreams, netlists, timing/resource reports, logs, formal results, and original source snapshots from completed experiments.
- Actual hardware input images, result logs, paired readbacks, counters, and failure/recovery records. Original numerical payloads are preserved.
- Source manifests and download verification receipts, with bulk public audio/vibration caches obtained separately.
- Properly attributed third-party source and its licenses; project diagrams and the English walkthrough/video.

## Excluded or transformed

| Material | Decision and reason |
| --- | --- |
| Virtual environments, downloaded toolchains, interpreter/compilation caches, generated host executables and objects | Excluded; reproducible local tooling, not project results |
| Bulk `data/**/*.npy` and CWRU `.mat` downloads | Excluded; retain official provenance, manifests, and download workflows |
| Downloaded EfficientAT/PANNs checkpoints and upstream demo media | Excluded; retain source, licenses, exact checkpoint references and digests |
| Full pre-project 4 MiB Flash backup | Retained only locally; a device-recovery image can contain pre-existing contents outside this project. Original digest and backup receipts remain |
| Private assistant usage/task records, machine migration bookkeeping, local working-tree preparation diff | Excluded; not engineering evidence needed to understand the results |
| Home-directory names, private application IDs, temporary workspace paths | Replaced by portable project paths or neutral local placeholders |
| Chinese text and original local commit ancestry | English translations published; original records/history retained locally |
| Credentials and secret environment files | Excluded; publication is checked for known credential patterns |

These are publication decisions, not claims that every omitted item is legally prohibited from being uploaded. Third-party terms and restoration details are listed in [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md). No local source data, models, or backups were deleted.

## Evidence integrity

Translation and redaction can change file hashes. Original recorded experiment hashes are preserved as original provenance rather than rewritten to simulate a new audit. The [publication manifest](../publication/manifest.json) records the source-archive hash and publication hash for every included original file, plus an exclusion list. The [integrity guide](../publication/README.md) explains how to validate this export and what historical checks still require local originals.

No training, final-test reevaluation, hardware programming, or physical measurement was performed to produce this English snapshot. Publication verification checks content, syntax, language, privacy patterns, numerical preservation, and remote commit identity; these checks are distinct from original engineering verification.
