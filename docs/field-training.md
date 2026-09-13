# ADXL345 field model: data intake and frozen training workflow

This iteration added separate N256 field-training tools, stored independently of the frozen CWRU model. No real ADXL345 acquisition records are currently available. `build/field_fixture/` is only a workflow test generated from mathematical sine waves and noise, and is not evidence of field-recognition accuracy or fault diagnosis.

The planned formal-model classes are `stopped`, `rigid_support_running`, and `flexible_support_running`. These are controllable, recordable experimental states, not bearing-fault labels. Once the actual apparatus is selected, confirm that all three states can be established safely and repeatably, and retain apparatus and mounting documentation.

## Data and hardware contract

- 800 S/s, one axis, nonoverlapping 256-sample windows, 320 ms per window.
- Raw ADXL counts are algorithmically clamped to [-1024,1023], then multiplied by 32 for the signed 16-bit core. This clamp is an algorithm contract, not the sensor's physical ±2g range.
- DC removal, input scaling, periodic Hann window, Q14 coefficients, 40-bit DFT accumulation, 18-bit RNE shift, Re²+Im², and 16 INT8 features; followed by 16→16 ReLU→3 classification.
- Classification uses the raw-count domain. Static-calibration mg parameters belong to a separate measurement path and cannot directly replace classification input units.
- The field version initially uses 16 single bins. The CWRU three-neighbor-bin model and evaluation remain unchanged. Changing field spectral features requires new field train/validation comparisons and corresponding RTL verification.

## Formal acquisition manifest

The editable 30-record template is `data/field/manifest.template.json`. Each class needs at least ten independent 30-second recordings: six training, two validation, and two test. Each record contains path, label, acquisition session, mounting batch, and CSV/sidecar SHA256.

A session or mounting batch must not cross train/validation/test splits. Paths, record_id values, and CSV hashes must not repeat. Split recordings before windowing. Each 24000-sample recording yields 93 complete windows; discard and report the remaining 192 samples. Window count does not replace the count of independent experimental recordings.

CSV requires at least `sample_index,service_cycle,z_raw`, with x/y axes also supported. A same-stem `.json` acquisition sidecar must contain `csv_sha256,odr_hz,clock_hz,axis,error_flags,missed_service,observed_sensor_overruns,observed_samples`. Existing SEN1 decoding can generate these files.

Data admission checks cover hashes, axis, configured sample rate, clock, increasing gap-free indices, absence of acquisition errors, and absence of late-read anomalies. Mean read interval must be within 5% of 15000 clocks. That 5% is this project's data-check gate, not an ADXL clock specification or ADC jitter claim. Investigate abnormal recordings instead of directly computing spectra under a nominal 800 Hz assumption.

## Training, quantization, and testing

`src/vibfpga/field.py` performs these steps:

1. Open only training and validation CSVs. Select frequency bins using training-set Fisher scores, with at least three bins spacing; derive normalization shifts from the training 99.5th percentile.
2. Train an RMS three-leaf threshold tree, a spectral linear classifier, and a 16→16→3 MLP. The MLP uses the existing verified AdamW training function with lr0.025, weight_decay1e-5, full-batch training, and 100 default epochs, selecting checkpoints by validation macro-F1. Actual settings are recorded; this is not described as the earlier draft's Adam/minibatch setup.
3. Apply symmetric PTQ with per-layer power-of-two scales to the MLP. Use INT8 weights and correspondingly scaled biases, and statically check worst-case INT32 accumulation bounds for both layers. Hidden-layer RNE, ReLU, and 0..127 saturation match RTL.
4. Report floating-point DSP + floating-point network, integer DSP + floating-point network, and integer DSP + INT8 network. If quantization reduces validation performance by more than two percentage points, report `qat_required_by_validation=true`. Decide whether to run the existing QAT workflow only after real data is available; a simulated fixture cannot establish field-model acceptance.
5. Export model JSON, weight/coefficient ROMs, stagewise integer reference vectors, floating-point weights, and both baselines. `frozen.json` binds all files, numerical/data-admission source code, and version records.
6. Open test CSVs only through a separate evaluation command. Exclusively create `test_attempt.json` before reading tests, retaining it even after failure or interruption to prevent silent retries. Completed evaluation generates per-class recall, confusion matrix, macro-F1, and per-window predictions.

Formal run, from the project root after filling a real manifest; do not execute without a device:

```sh
source scripts/env.sh
python scripts/train_field.py train --manifest data/field/manifest.json --output artifacts/field_run_001
python scripts/train_field.py evaluate --output artifacts/field_run_001
```

The output directory must be absent or empty; frozen results cannot be overwritten. Changes to input preprocessing, source, or ROMs cause frozen evaluation to refuse continuation. Retain and explain failed test attempts; do not delete markers to pretend the test set is being accessed for the first time.

## Workflow tests without hardware

```sh
source scripts/env.sh
python scripts/make_field_fixture.py --output build/field_fixture/data
python scripts/train_field.py train --manifest build/field_fixture/data/manifest.json --output build/field_fixture/trained --allow-fixture
python scripts/train_field.py evaluate --output build/field_fixture/trained --allow-fixture
make field-sim
make field-board
```

These fixtures already existed in the recorded run. For reproduction, change paths to a new directory; do not retrain into an existing frozen directory. `--allow-fixture` explicitly marks simulated data, and builders and FCL1 logs retain the flag. It does not make simulated training deployable. Existing bulk fixture data and build outputs remain local where omitted from publication.

Python tests in this iteration actually covered duplicate data, session/mounting leakage, CSV modification, acquisition gaps, incorrect timebase, successful training when test files do not exist, frozen-ROM changes, repeated/interrupted test attempts, and the complete train/export/evaluate path. For RTL validation see [field-classifier verification](field-classifier-verification.md); for whole-system SPI and logging see [FCL1 system](field-system.md).
