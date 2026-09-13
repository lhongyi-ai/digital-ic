"""The functional NOR model must reproduce a configuration-slept real chip."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim"))
from test_flash_system import SpiNor


def transaction(nor, values):
    nor.begin()
    responses = [nor.receive(value) for value in values]
    nor.close()
    return responses


def test_sleep_ignores_read_wren_and_program_without_mutating_memory():
    clock = [0]
    nor = SpiNor(None, cycle=lambda: clock[0])
    nor.memory[0x100:0x104] = b"VIB1"
    assert transaction(nor, [3, 0, 1, 0, 0]) == [255] * 5
    transaction(nor, [6])
    transaction(nor, [2, 0, 1, 0, 0])
    assert bytes(nor.memory[0x100:0x104]) == b"VIB1"
    assert not nor.wel and not nor.operations and not nor.wake_events
    assert [event["opcode"] for event in nor.ignored_commands] == [3, 6, 2]


def test_release_wait_is_measured_from_cs_rise_and_enforced_at_cs_assertion():
    clock = [0]
    nor = SpiNor(None, cycle=lambda: clock[0])
    nor.memory[0x100:0x104] = b"VIB1"
    nor.begin()
    nor.receive(0xab)
    clock[0] = 16
    nor.close()
    assert nor.wake_events == [{"opcode": 0xab, "cs_rise_cycle": 16, "ready_cycle": 56}]
    assert not nor.operations
    clock[0] = 55
    nor.begin()  # Starting one cycle too early invalidates the transaction.
    clock[0] = 56  # Completing its opcode at the deadline must not rescue it.
    assert [nor.receive(value) for value in (3, 0, 1, 0, 0)] == [255] * 5
    nor.close()
    clock[0] = 56
    assert transaction(nor, [3, 0, 1, 0, 0])[3] == ord("V")
    assert nor.operations == [{"opcode": 3, "address": 0x100, "length": 1}]
    assert nor.command_events == [{"opcode": 3, "start_cycle": 56}]


def test_explicitly_awake_model_preserves_existing_program_and_read_operations():
    nor = SpiNor(None, powered_down=False, cycle=lambda: 0)
    transaction(nor, [6])
    transaction(nor, [2, 0, 1, 0, 0x52])
    assert nor.memory[0x100] == 0x52
    assert nor.operations == [{"opcode": 2, "address": 0x100, "length": 1, "data": "52"}]
    assert not nor.wake_events and not nor.ignored_commands
