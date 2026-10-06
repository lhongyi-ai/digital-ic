SHELL := /bin/bash
export BASH_ENV := $(CURDIR)/scripts/env.sh
MODEL ?= artifacts/model/model.json
PROFILE ?= cwru-neighbor3
MODULE ?= core
BUILD_ROOT ?= build
RUN_ID ?=
RUN_ARGS = --build-root "$(BUILD_ROOT)" $(if $(RUN_ID),--run-id "$(RUN_ID)",)
PYTHON_RESULTS = $(if $(RUN_ID),$(BUILD_ROOT)/runs/$(RUN_ID)/python-results.xml,$(BUILD_ROOT)/python-results.xml)

.PHONY: help test core dsp-cases paced formal flash board neighbor sensor evidence verify replay-image neighbor-report nn-edges protocol-edges quant-formal coverage field-sim field-board offline-evidence quick python-test module release profile-status profile-commands field-status field-verify replay-fifo-formal canonical-output release-prerequisites release-evidence
.NOTPARALLEL: release verify
help:
	@printf '%s\n' 'make quick      Python tests + 14-frame four-MAC RTL smoke check' 'make module MODULE=core  Select one complete module regression' 'make release    Complete offline verification, including edge/quantization/coverage/field tests' 'make profile-status PROFILE=cwru-neighbor3  Read-only profile check'
	@printf '%s\n' 'make test       Python, arithmetic, FIFO, SPI, and calibration unit tests' 'make core       1000-frame numerical checks for one and four MACs' 'make paced      1000 frames at 12 kS/s, overload and recovery' 'make formal     64-cycle bounded FIFO checks and SVA compatibility' 'make flash      Complete SPI NOR replay-chain simulation' 'make board      Full place-and-route and bitstream for one/four MACs' 'make neighbor   Complete neighboring-bin validation and build' 'make sensor     Sensor acquisition/calibration/spectrum simulation and build' 'make verify     All offline verification; no hardware operations' 'make evidence   Refresh the index from saved results' 'make replay-image  Prepare a real validation-record replay image'
	@printf '%s\n' 'make dsp-cases  Four-configuration non-bin-centered/phase/clipping/two-tone regression' 'make neighbor-report  Read-only verification of saved neighboring-bin reports; no reevaluation or training'
	@printf '%s\n' 'make nn-edges    Tied-score/INT32-overflow and recovery verification' 'make quant-formal  Formal checks and negative controls for actual quantization RTL' 'make coverage   Collect Verilator coverage' 'make field-sim  N256 field classifier and SPI/Flash simulation; prepare the fixture using docs/field-training.md' 'make field-board Build the single-MAC field-firmware test configuration; no programming'

nn-edges:
	python scripts/test_nn_edges.py $(RUN_ARGS)

protocol-edges:
	python scripts/test_protocol_edges.py $(RUN_ARGS)

offline-evidence: canonical-output
	python scripts/collect_offline_completion.py

quant-formal: canonical-output
	python formal/run_quant_formal.py --negative-controls

coverage:
	python scripts/run_core_coverage.py --build-root "$(BUILD_ROOT)/rtl_coverage" $(if $(RUN_ID),--run-id "$(RUN_ID)",)

field-sim:
	python sim/run_sensor_classifier.py $(RUN_ARGS)
	python sim/run_field_system.py --lanes 1 $(RUN_ARGS)
	python sim/run_field_system.py --lanes 4 $(RUN_ARGS)

field-board:
	python scripts/build_field.py --model build/field_fixture/trained/model/model.json --lanes 1 --allow-fixture $(RUN_ARGS)

python-test:
	@python -c 'from pathlib import Path; import sys; Path(sys.argv[1]).parent.mkdir(parents=True, exist_ok=True)' "$(PYTHON_RESULTS)"
	python -m pytest tests --junitxml="$(PYTHON_RESULTS)" -q

quick: python-test
	python scripts/run_quick.py --profile "$(PROFILE)" $(if $(filter command line environment,$(origin MODEL)),--model "$(MODEL)",) $(RUN_ARGS)

module:
	@case "$(MODULE)" in acoustic|test|core|dsp-cases|paced|formal|flash|board|neighbor|sensor|nn-edges|protocol-edges|quant-formal|coverage|field-sim|field-board|replay-fifo-formal) $(MAKE) "$(MODULE)" ;; *) printf '%s\n' 'Unknown MODULE; see make help and docs/workflow-efficiency.md'; exit 2 ;; esac

profile-status:
	python scripts/project_profile.py status --profile "$(PROFILE)"

profile-commands:
	python scripts/project_profile.py commands --profile "$(PROFILE)"

field-status:
	python scripts/field_status.py status

field-verify:
	python scripts/field_status.py verify

replay-fifo-formal: canonical-output
	python formal/run_replay_fifo_formal.py

test: python-test
	python sim/run_fifo.py $(RUN_ARGS)
	python sim/run_spi_sensor.py $(RUN_ARGS)
	python sim/run_spi_sensor.py --sensor-only --rate-code 0x0a $(RUN_ARGS)
	python sim/run_spi_sensor.py --sensor-only --rate-code 0x0c $(RUN_ARGS)
	python scripts/test_calibration.py $(RUN_ARGS)
	python scripts/build_core.py --model "$(MODEL)" --lanes 4 --arithmetic $(RUN_ARGS)
	python scripts/build_core.py --model "$(MODEL)" --lanes 4 --quant-boundary $(RUN_ARGS)

core:
	python scripts/build_core.py --model "$(MODEL)" --lanes 1 --frames 1000 $(RUN_ARGS)
	python scripts/build_core.py --model "$(MODEL)" --lanes 4 --frames 1000 $(RUN_ARGS)

dsp-cases:
	python scripts/build_core.py --model "$(MODEL)" --lanes 1 --dsp-cases --frames 10 $(RUN_ARGS)
	python scripts/build_core.py --model "$(MODEL)" --lanes 4 --dsp-cases --frames 10 $(RUN_ARGS)
	python scripts/build_core.py --model artifacts/model_neighbor/model.json --lanes 1 --dsp-cases --frames 10 $(RUN_ARGS)
	python scripts/build_core.py --model artifacts/model_neighbor/model.json --lanes 4 --dsp-cases --frames 10 $(RUN_ARGS)

neighbor-report:
	python scripts/evaluate_neighbor.py --verify

paced:
	python scripts/build_core.py --model "$(MODEL)" --lanes 1 --frames 1000 --fixed-rate $(RUN_ARGS)
	python scripts/build_core.py --model "$(MODEL)" --lanes 4 --frames 1000 --fixed-rate $(RUN_ARGS)

formal: canonical-output
	python formal/run_sva_smoke.py
	python formal/run_fifo_formal.py

flash:
	python sim/run_flash_system.py $(RUN_ARGS)
	python sim/run_flash_system.py --model artifacts/model_neighbor/model.json --full-log-scan $(RUN_ARGS)

board:
	python scripts/build_board.py --lanes 1 $(RUN_ARGS)
	python scripts/build_board.py --lanes 4 $(RUN_ARGS)

neighbor:
	python scripts/build_core.py --model artifacts/model_neighbor/model.json --lanes 1 --frames 1000 $(RUN_ARGS)
	python scripts/build_core.py --model artifacts/model_neighbor/model.json --lanes 4 --frames 1000 $(RUN_ARGS)
	python scripts/build_core.py --model artifacts/model_neighbor/model.json --lanes 1 --frames 1000 --fixed-rate $(RUN_ARGS)
	python scripts/build_core.py --model artifacts/model_neighbor/model.json --lanes 4 --frames 1000 --fixed-rate $(RUN_ARGS)
	python sim/run_flash_system.py --model artifacts/model_neighbor/model.json $(RUN_ARGS)
	python scripts/build_board.py --model artifacts/model_neighbor/model.json --lanes 1 $(RUN_ARGS)
	python scripts/build_board.py --model artifacts/model_neighbor/model.json --lanes 4 $(RUN_ARGS)

sensor:
	python sim/run_sensor_spectrum.py $(RUN_ARGS)
	python sim/run_sensor_system.py $(RUN_ARGS)
	python scripts/build_sensor.py --rate 800 $(RUN_ARGS)

evidence: canonical-output
	python scripts/report_architecture.py
	python scripts/collect_evidence.py

replay-image:
	python scripts/prepare_replay.py

canonical-output:
	@test "$(BUILD_ROOT)" = build -a -z "$(RUN_ID)" || { printf '%s\n' 'This formal/evidence module only supports canonical build/ output; omit BUILD_ROOT and RUN_ID'; exit 2; }

release-evidence: canonical-output
	python scripts/collect_offline_completion.py --scope current-release

release-prerequisites:
	python scripts/check_release_prerequisites.py

# The known-machine release reuses its source-bound RTL/P&R receipts; the legacy
# default remains unchanged. Both routes run the common Python contract tests.
ifeq ($(PROFILE),known)
release: python-test
	python scripts/finalize_known_model.py freeze
else
# Canonical collectors read build/ paths. Named runs are for individual modules.
release: canonical-output release-prerequisites
	@test "$(BUILD_ROOT)" = build -a -z "$(RUN_ID)" || { printf '%s\n' 'release uses canonical build/ evidence; use named run IDs with individual modules'; exit 2; }
	$(MAKE) test core dsp-cases paced formal flash board neighbor sensor neighbor-report
	$(MAKE) nn-edges protocol-edges quant-formal replay-fifo-formal coverage field-sim field-board field-verify
	@mkdir -p build/offline-completion
	cp build/python-results.xml build/offline-completion/python-results.xml
	$(MAKE) evidence release-evidence
endif

verify: release


.PHONY: acoustic
# Acoustic checks only; never downloads, retrains or programs hardware.
acoustic:
	python scripts/prepare_acoustic_fixtures.py
	python scripts/test_acoustic_rtl.py --model build/acoustic-fixture/log4/model.json --lanes 1 --frames 1000 --run-id acoustic-module-log
	python scripts/test_acoustic_rtl.py --model build/acoustic-fixture/linear/model.json --lanes 4 --frames 1000 --run-id acoustic-module-linear
	python scripts/test_acoustic_rtl.py --lanes 1 --run-id acoustic-module-trained
