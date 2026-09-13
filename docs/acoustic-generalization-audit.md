# Near duplicates, acquisition relationships, and cross-machine testing (2026-09-11)

**Conclusion: no cross-split duplicate recordings met this audit's criteria, but the frozen model failed substantially on a new machine. The original AUC 1.000 is a same-machine, same-noise-condition result and cannot be presented as general fan-fault recognition performance.**

There was no retraining, feature adjustment, or threshold change. The old test set was read only for duplicate auditing, not model tuning. The new test machine, sampling rule, sample counts, and frozen-model digest were fixed before downloading or evaluating its data.

## 1. Near-duplicate recording audit

Existing data comprised 240 training, 70 validation, and 90 old-test recordings, totaling 400.

| Check | Scope | Result |
|---|---|---|
| Exact full-PCM digest | All 400 recordings | No exact duplicates |
| Exact one-second segments | Original 16 kHz, segment starts every 0.5 seconds, cross-split comparison | No identical segments |
| Arbitrary-shift correlation screen | 44,700 cross-split recording pairs, downsampled to 500 Hz, samplewise shifts, at least two seconds overlap | 267 pairs with absolute correlation ≥0.8 |
| Original-rate verification | All 267 pairs, fine search within ±32 original samples of the screened offset | No match with absolute correlation ≥0.98 |

The first batch checked 100 pairs, followed by the remaining 167; no candidates were left unverified. Correlation checks included positive/negative gain, DC offsets, and time shifts. Synthetic tests validated these cases, including an original-rate shift of 37 samples that is not an integer downsampling step.

The new machine's 70 recordings were additionally compared with the old 400 over 28,000 pairs: no exact full-recording match and no 500 Hz candidate reaching 0.8. The 20 most similar pairs were nevertheless checked at original rate, with no match reaching 0.98.

**This is not proof that every form of leakage is absent.** Only channel 0 was audited. Low-frequency screening may miss reuse confined to high frequencies; shifted correlation requires at least two seconds overlap. The same clean machine sound mixed with different noise may miss near-duplicate thresholds. Distinct files or an absence of detected near duplicates do not establish different acquisition dates, run batches, or background-noise recordings.

## 2. What can be established about acquisition batches

The [official paper](https://arxiv.org/html/1909.09347) describes ten-second machine recordings captured by an eight-channel microphone array. Machines were recorded separately, then mixed with background noise from real factories. Different IDs represent individual machines that may belong to different product models. Background noise is selected and mixed afterward, so its source relationships also affect statistical independence.

However, the [public dataset](https://zenodo.org/records/3384388) and obtained fan-archive file listing do not provide per-recording acquisition dates, run-batch IDs, clean-source-segment IDs, or mixed-noise IDs. File numbers cannot be assumed chronological, and archive timestamps are not acquisition timestamps.

Consequently:

- Old training, validation, and test recordings all come from fan/id_00; batch-level independence is not established.
- id_02 supplies a different machine and therefore a different acquisition condition, but its background noise cannot be guaranteed fully independent of id_00.
- No new field recordings were collected. This is a frozen cross-machine evaluation on public data, not field validation on a new date or in a new factory.

## 3. New-machine test results

The protocol fixed fan/id_02, 0 dB, channel 0, selecting 40 normal and 30 faulty recordings by hash order. None fitted normalization, model parameters, or threshold. The original main model `spectrum1024-trees` and threshold `0.28277777777777774` were retained.

| Evaluation condition | Faults detected | Normal false positives | AUC |
|---|---:|---:|---:|
| Original id_00 validation | 30/30 (100%) | 2/40 (5%) | 1.000 |
| Original id_00 held-out test | 50/50 (100%) | 1/40 (2.5%) | 1.000 |
| **New id_02 cross-machine test** | **23/30 (76.7%)** | **24/40 (60%)** | **0.6033** |

The new-test confusion matrix is `[[16,24],[7,23]]`, with rows true normal/fault and columns predicted normal/fault. All three high-standard gates were missed.

This directly establishes inadequate cross-machine transfer by the current model, but does not by itself prove training-sample memorization or label leakage. Intrinsic machine spectra, operating conditions, or fault-type distributions may differ. The supported description is “effective supervised recognition on the same machine; cross-machine generalization did not pass.”

The AUC drop from 1.000 to 0.6033 also shows that the problem is more than a shifted threshold. Raising or lowering the threshold alone cannot restore ranking quality. No threshold tuning or training was attempted on id_02 during this audit, avoiding silently converting it into development data.

## 4. Implications for subsequent work

If the project targets a fixed model and installation, state that scope and confirm reliability using new recordings from genuinely independent operating batches. A claim of general recognition across fans requires multi-machine training and machine IDs completely excluded from development. Tuning with already evaluated id_02 and calling it independent testing again is not valid.

No such training was added in this audit. The id_02 result remains a single external evaluation, with original validation/test results and model-freeze records preserved.

## Reproducible evidence

- `artifacts/acoustic-recording-audit/`: initial 400-recording duplicate audit, all 44,700 screened pairs, and source digests.
- `artifacts/acoustic-recording-audit-completion/`: original-rate checks completing the remaining 167 pairs.
- `data/mimii-external-id02/plan.json`: new-machine sample manifest fixed before evaluation; retained locally where omitted with bulk data.
- `artifacts/acoustic-external-id02/independence-audit.json`: 28,000 new/old pair checks and limitations.
- `artifacts/acoustic-external-id02/results.json`: all 70 predictions, frozen threshold, and cross-machine metrics.
- `scripts/audit_acoustic_recordings.py`, `scripts/complete_acoustic_recording_audit.py`, and `scripts/evaluate_acoustic_external.py`: corresponding entry points, refusing to overwrite existing results. Completed evaluations need not be rerun.
- `tests/test_recording_audit.py`: three algorithm checks passed.
