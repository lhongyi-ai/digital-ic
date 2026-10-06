"""Contract runner cannot turn compiler/simulator failures into passing evidence."""
import importlib.util,subprocess
from pathlib import Path
import pytest
SPEC=importlib.util.spec_from_file_location('portability_contracts',Path(__file__).resolve().parents[1]/'scripts/test_portability_contracts.py')
MODULE=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(MODULE)

def test_command_failure_preserves_log(tmp_path):
    log=tmp_path/'failed.log'
    with pytest.raises(RuntimeError,match='exit 3'):
        MODULE.run_checked(['python','-c','print("actual simulator failure");raise SystemExit(3)'],log,'PASS')
    assert 'actual simulator failure' in log.read_text()

def test_missing_completion_is_not_success(tmp_path):
    with pytest.raises(RuntimeError,match='missing CONTRACT_PASS'):
        MODULE.run_checked(['python','-c','print("stopped before checks")'],tmp_path/'incomplete.log','CONTRACT_PASS')

def test_rtl_rounding_cases_cover_distinct_boundaries():
    # The answers here are hand-calculated, not obtained from the RTL expression.
    cases=dict(MODULE.CASES)
    assert cases[0x800000]==0 and cases[0x1800000]==2 and cases[0x2800000]==2
    assert cases[(126<<24)+0x800000]==126
    assert cases[(126<<24)+0x800001]==127 and cases[128<<24]==127
