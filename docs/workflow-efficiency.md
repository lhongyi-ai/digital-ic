# Routine checks, independent run directories, and compilation reuse

Run `source scripts/env.sh` from the project root. The project was moved to a directory containing spaces. The environment script and build helpers create tool-only path aliases in the system temporary directory; source, models, caches, and results remain in the project or designated build directory. There is no need to move the project or copy frozen models.

## Choose an entry point by scope

```sh
make profile-status PROFILE=cwru-neighbor3
make profile-commands PROFILE=cwru-neighbor3
make quick RUN_ID=dev-001
make module MODULE=core BUILD_ROOT=build/local RUN_ID=core-001
make release-prerequisites
make release
```

| Entry point | Actual work |
| --- | --- |
| `quick` | Runs all Python tests once and a 14-frame core check for `PROFILE`, retaining protocol errors, output backpressure, and reset checks for each stage. Defaults to four-MAC `cwru-neighbor3`; an explicit conflicting `MODEL` fails. Use the respective SEN1/FCL1 modules. |
| `module MODULE=…` | Runs the module's existing complete checks. Supports test, core, dsp-cases, paced, formal, flash, board, neighbor, sensor, nn-edges, protocol-edges, quant-formal, coverage, field-sim, field-board, and replay-fifo-formal. |
| `release` / `verify` | Runs all original offline regressions, plus NN/protocol boundaries, quantization formal checks and negative controls, bounded checks of the actual replay FIFO, HDL coverage, one-/four-MAC FCL1 simulations, a complete one-MAC build, and frozen-file checks. Retains the original 1000-frame runs and full case counts. Python tests run only once. |
| `evidence` | Refreshes the general index from existing results without rerunning pytest. Historical results retain individual status. |
| `release-evidence` | Read-only verification of currently required release reports and original-input bindings; generates `build/release/summary.json` and `artifacts/evidence/current-release.json`. |
| `offline-evidence` | Retains the complete historical audit, including the four-MAC field capacity failure and old area experiments; may report historical evidence mismatches after source changes. |

`PROFILE` drives configuration inspection and quick checks. Benchmark `core`/`paced` still default to the original single-bin `MODEL=artifacts/model/model.json`, while `neighbor` explicitly covers the neighboring-bin configuration. This preserves the original two-model release matrix. To run a particular profile separately, inspect `profile-commands` first.

`release` accepts the current active route offline; it does not declare physical-board, sensor-acquisition, or real-field accuracy acceptance. Four-MAC field area optimization is paused. Its historical experiments neither block the current release nor rerun automatically. Before release, the **synthetic field fixture** must already have been generated, trained, frozen, and processed through its original test flow. `release-prerequisites` checks its files and numerical-source hashes before expensive checks. If absent, prepare it separately following `field-training.md`. Release does not regenerate/retrain existing frozen models, tune parameters, or reopen the formal test set. Python unit tests still train/evaluate small synthetic fixtures in temporary directories to check process isolation and freezing rules. The old complete historical audit remains separately runnable.

## Separate outputs from compiler caches

The four builders `build_core.py`, `build_board.py`, `build_sensor.py`, and `build_field.py`, plus core, Flash, FIFO, SPI, calibration, sensor-spectrum, SEN1, FCL1, and boundary regressions support:

```sh
python scripts/build_core.py --model artifacts/model_neighbor/model.json \
  --lanes 4 --frames 14 --build-root build/local --run-id first
python scripts/build_core.py --model artifacts/model_neighbor/model.json \
  --lanes 4 --dsp-cases --frames 10 --build-root build/local --run-id directed
python sim/run_sensor_system.py --case nominal --build-root build/local --run-id sensor-001
python sim/run_field_system.py --lanes 1 --build-root build/local --run-id field-001
```

Results reside in `BUILD_ROOT/runs/RUN_ID/<original-directory-name>/`, or `BUILD_ROOT/<original-directory-name>/` when run ID is omitted. Use a new ID to retain independent records or run concurrently. Reusing an ID explicitly refreshes that run's outputs and is unsuitable for concurrent writes to the same directory. The core's existing `--build-dir` remains supported but cannot be combined with `--run-id`.

The coverage script's existing `--build-root` identifies its suite directory and additionally accepts `--run-id`; Make passes `BUILD_ROOT/rtl_coverage`. Formal checks and general evidence collection currently support only standard `build/` paths. Passing a custom root or run ID to those modules through Make fails immediately to avoid silently writing to the standard directory. Full release uses standard directories for strict collection of evidence at existing fixed paths.

## Reuse rules and failure handling

- cocotb and native paced compilation artifacts are stored in `BUILD_ROOT/.compiler-cache/`, keyed by content. Keys bind RTL, recursive includes, all model-directory files/ROMs, raw-vector file parameters, top-level parameters, assertion/coverage/compiler options, actual Verilator executable and headers, C++ tools, and relevant environment. cocotb also binds its runner, test-entry C++, and VPI library.
- Ordinary core, DSP-specific, and protocol-specific checks with the same configuration may share compilation artifacts. Frame count, test module, and test outputs never justify skipping execution. Every test actually reruns and uses current XML, reports, and coverage. Empty XML, failed cases, and skipped cases are not passing evidence.
- Compilation is locked per key. A completion marker is published only after success with unchanged inputs. A cache hit rechecks the executable hash. Source, ROM, parameter, tool, or option changes trigger recompilation. Mid-run input changes fail the run.
- The NN boundary suite deliberately replaces untrained ROMs between tests. It uses the same path handling without content caching. Board synthesis/P&R executes every time; this change did not cache successful board reports.
- Old success reports for the current run are deleted before compilation. Sensor builds bind RTL, ROMs, generated constraints/scripts, tool identities, and bitstream hash, and reject input changes during the build. Suite aggregate reports are also invalidated at startup.
- Temporary tool aliases can be recreated and target current absolute paths. Cache compatibility is not guessed from old paths. Environment migration or tool replacement invalidates caches. Caches grow; deleting `.compiler-cache` within a specified build root loses compilation reuse only, without deleting run reports. Do not clean it while compilation/tests are active.

Board option `--clock-source external12|hfosc12` applies only to the replay builder. HFOSC uses a separate directory suffix, nominal 12 MHz, and an unmeasured physical frequency. It explicitly constrains 13.2 MHz and verifies the routed report actually used that constraint. Static building does not automatically access USB.

## Bounded validation performed for this change

Evidence is in `build/workflow-efficiency-check/summary.json` and its `logs/` directory, retained locally if omitted from publication. Fourteen Python tests passed for caches, input drift, independent outputs, stale-report removal after compilation failure, configuration conflicts, and release prerequisites. Actual baseline and default-neighbor 14-frame core runs each passed four cocotb cases. One depth-3 FIFO scenario regression passed. The SVA positive control passed, and its deliberate assertion violation was detected.

Actual compilation demonstrations using the same configuration and different run IDs:

| Compilation type | First compilation | Cache-hit reuse | Tests |
| --- | ---: | ---: | --- |
| Actual RTL arithmetic boundaries | 1.737 s | 0.001 s | Reran and passed both times |
| Native paced core | 2.121 s | 0.001 s | One frame per run; overload/recovery passed both times, with 4115 drops detected in each |

These timings cover compilation/reuse only, excluding hash preparation and test execution. They are not a complete-release speedup. Expanded release commands contain pytest only once. Formal modules without named-output support were actually verified to reject such options early. **This efficiency-validation round did not execute a full release, every P&R build, or retraining/evaluation.** Physical-board and post-Flash-wake system regressions have separate records.
