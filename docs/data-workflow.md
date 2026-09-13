# Project Profiles, Capture Registration, and Frozen-Result Checks

These entry points do not connect to USB, train models, or reevaluate the test set. A real ADXL345 field model has not yet been trained; `fcl1-fixture` validates the synthetic-data workflow only.

## Unified Project Profiles

`configs/project-profiles.json` stores workflow selection and model references. Bins, weights, and quantization shifts remain authoritative in existing model JSON and are not duplicated in the profile. `src/vibfpga/project_profile.py` validates N, sample rate, feature mode, training status, and axis between model and system, and resolves relative paths against the project root.

|Name|System|Default configuration|Purpose|
|---|---|---|---|
|`cwru-neighbor3`|CWRU classification|12 kHz, N1024, four MACs|Frozen neighbor3 model|
|`sen1-spectrum`|SEN1 measurement|800 Hz, N256, z axis, one MAC|Raw counts and bin energies; no classifier|
|`fcl1-fixture`|FCL1 classification workflow|800 Hz, N256, z axis, one MAC|Synthetic fixture; not real field-performance evidence|

Run from the project root:

```sh
source scripts/env.sh
python scripts/project_profile.py status --profile cwru-neighbor3
python scripts/project_profile.py export --profile sen1-spectrum --format shell
python scripts/project_profile.py commands --profile fcl1-fixture
```

The entry script can also be invoked by absolute path from another working directory. Relative CLI arguments always resolve against the project root. `commands` only prints reviewable commands; it does not execute them, access hardware, or automatically train a fixture. `export` supports JSON and shell output with correctly quoted paths containing spaces. `metadata_verified` means model metadata match; `frozen_artifacts_verified=false` and `hardware_evidence_checked=false` explicitly distinguish full frozen-artifact validation and physical verification. Missing models produce an error rather than a replacement model.

Hardware connections and measurement status are in `docs/hardware-pinout-clock.md`. A board file referenced by a project profile cannot replace a report from a specific hardware-verification run.

The CWRU command list prints both core verification and board build commands, retaining `external12` by default. For an internally clocked board, explicitly run `python scripts/project_profile.py commands --clock-source hfosc12`; the same option applies to status/export. This changes only the exported clock selection; it neither establishes a measured frequency nor programs the board. The SEN1 build script enables spectrum by default, and exported commands do not pass `--no-spectrum`.

## Assign Labels and Splits Before Registering SEN1

Before acquisition, the operator specifies a real, reproducible apparatus state, session, installation batch, and split. The three states follow `class_names` in `data/field/manifest.template.json`. A session or installation batch must not cross train/validation/test. Do not change splits according to results.

First set the following variables to the actual experiment's records. Empty values and `REPLACE` placeholders are rejected:

```sh
python scripts/register_capture.py plan \
  --output "data/field/plans/$RECORD_ID.json" \
  --record-id "$RECORD_ID" --state "$STATE" --split "$SPLIT" \
  --session-id "$SESSION_ID" --installation-id "$INSTALLATION_ID" \
  --apparatus "$APPARATUS" --source-kind physical_adxl345
```

`STATE` must be `stopped`, `rigid_support_running`, or `flexible_support_running`; `SPLIT` must be `train`, `validation`, or `test`. Plan files are created exclusively and cannot overwrite an existing file. They record the operator's preassignment declaration and timestamp. SEN1 has no byte field proving physical origin or label truth; software cannot confirm provenance for the operator or prove that the plan was not backfilled after acquisition.

After acquisition and obtaining a local SEN1 binary through the existing read-only workflow:

```sh
python scripts/register_capture.py register \
  --log "$SEN1_LOG" --assignment "data/field/plans/$RECORD_ID.json" \
  --manifest data/field/manifest.json
```

The default audit location is `data/field/registration_attempts/attempt_*`. Every attempt uses a new directory and preserves original `source.bin`, a plan copy, decoded CSV, capture sidecar, quality report, and `attempt.json`. If a step fails, existing outputs remain and the process returns nonzero. A process terminated midway also leaves its `started` marker. Do not remove failed/interrupted records to conceal attempts.

Registration reuses `sensor_log_to_csv` checks for SEN1 commit, CRC, and timestamp reconstruction, and `analyze_capture` checks for acquisition counters, indices, axis, ODR, clock, and service intervals. Physical records require at least 24,000 samples, or 30 seconds at 800 Hz, with mean service-interval deviation no greater than 5%. This 5% is a project data-admission gate; service timestamps do not measure ADC aperture jitter.

Only passing records are appended to the manifest. Each record binds SHA256 of the original log, CSV, sidecar, and plan. Updates use file locking and atomic replacement, preserving older records. Every successful registration retains before/after manifest snapshots and hashes. Duplicate record IDs, paths, CSVs, or source logs, and session/installation batches crossing splits, are rejected. Existing files are never overwritten as new capture outputs.

For a new manifest, use a not-yet-existing `data/field/manifest.json`; do not treat the template with placeholder records as a registered manifest. Registration permits an incomplete record count; the existing training entry point still requires at least train/validation/test = 6/2/2 real independent recordings per class. Capture admission may read the new recording but performs no model inference, selection, or test evaluation.

Synthetic verification must select `--source-kind synthetic_pipeline_fixture` in the plan and explicitly pass `--allow-fixture` during registration, with separate manifest and attempts directories, preferably under `build/`. Fixtures need at least 256 samples and carry explicit synthetic markers. They must not enter the physical manifest; formal training/evaluation continue to reject fixtures unless explicitly permitted. Never declare a known simulated log to be a physical capture.

## Read-Only Field Freeze Status

```sh
python scripts/field_status.py status --output build/field_fixture/trained
python scripts/field_status.py verify --output build/field_fixture/trained
```

`status` distinguishes not frozen, frozen with no attempt, attempted with no completed result, evaluated, and invalid states. Existing failure/interruption markers are not removed. `verify` additionally checks SHA256 of each frozen file and five frozen numerical/admission source files, plus freeze/model/source bindings in existing `test_attempt.json` and `test.json`. Reads are limited to existing metadata, frozen models/training reference vectors, and saved results. It does not follow capture paths in the manifest, open test CSVs, import training modules, or rerun evaluation.

The historical format did not freeze a separate digest of `test.json`, so the report gives its current SHA256 and bindings without claiming retrospective tamper evidence. Numerical-source or frozen-content mismatches fail directly; the check does not repair hashes, refreeze, or modify old results.

Read-only check on 2026-09-10: all 34 frozen files, five source hashes, and existing attempt/result bindings in `build/field_fixture/trained` passed. Source kind remains `synthetic_pipeline_fixture`. Added unit tests cover profile mismatch, empty labels, explicit fixture gates, duplicate registration, capture anomalies/CRC/sidecar hash errors, split leakage, physical/synthetic isolation, prohibition on reading test waveforms, and retention of failure markers. Omitted captures and build evidence remain local.
