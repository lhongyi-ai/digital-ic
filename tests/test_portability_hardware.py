"""No USB command may precede successful frozen release validation."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import run_portability_hardware as runner


def test_execute_without_release_never_starts_hardware(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    monkeypatch.setattr(runner.subprocess, 'run', lambda *a, **k: calls.append(a))
    monkeypatch.setattr(sys, 'argv', ['runner', '--execute', '--run-prefix', 'real-matrix'])
    with pytest.raises(FileNotFoundError):
        runner.main()
    assert calls == []
    assert not (tmp_path / 'measurements').exists()


def test_unsafe_run_prefix_is_rejected_before_validation(monkeypatch):
    calls = []
    monkeypatch.setattr(runner, 'verify_manifest', lambda *a: calls.append(a))
    monkeypatch.setattr(sys, 'argv', ['runner', '--execute', '--run-prefix', '../another-project'])
    with pytest.raises(SystemExit) as failure:
        runner.main()
    assert failure.value.code == 2
    assert calls == []


def test_audit_receives_one_overload_directory_name(tmp_path, monkeypatch):
    import json
    from types import SimpleNamespace
    base = tmp_path / runner.BASE
    base.mkdir(parents=True)
    index = {f'ice-C-{machine}-l{lanes}-s1': f'build/{machine}-{lanes}/report.json'
             for machine, lanes in [('00', 4), ('02', 4), ('04', 4), ('06', 4), ('00', 1)]}
    (base / 'evidence-index.json').write_text(json.dumps(index))
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    monkeypatch.setattr(runner, 'verify_manifest', lambda *a: {})
    monkeypatch.setattr(sys, 'argv', ['runner', '--execute', '--run-prefix', 'matrix'])
    commands = []
    def execute(command, **kwargs):
        commands.append(command)
        if '--run-id' in command:
            name = command[command.index('--run-id') + 1]
            path = tmp_path / 'measurements/known-replay' / name
            path.mkdir(parents=True)
            overload = name.endswith('-overload')
            (path / 'manifest.json').write_text(json.dumps({'status': 'failed' if overload else 'passed', 'physical_hardware': True}))
            return SimpleNamespace(returncode=int(overload))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(runner.subprocess, 'run', execute)
    runner.main()
    assert len(commands) == 13
    audit = commands[-1]
    assert audit[audit.index('--expected-overload') + 1] == 'matrix-id00-l1-r0-overload'


def test_resume_accepts_reserialization_but_rejects_mutated_bytes(tmp_path):
    import json
    directory = tmp_path / 'attempt'
    directory.mkdir()
    release = tmp_path / 'release.json'
    release.write_text('{}')
    board = directory / 'board.bin'
    board.write_bytes(b'bound bitstream')
    value = {'bitstream_sha256': runner.sha(board), 'quant_pipeline': 1}
    original = tmp_path / 'report.json'
    original.write_text(json.dumps(value))
    copy = directory / 'build-report.json'
    copy.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    saved = dict(deployment_sha256=runner.sha(release),
                 build_report_sha256=runner.sha(copy), bitstream_sha256=runner.sha(board))
    assert runner.reuse_matches(saved, directory, release, original)
    copy.write_text(copy.read_text() + ' ')
    assert not runner.reuse_matches(saved, directory, release, original)
    saved['build_report_sha256'] = runner.sha(copy)
    assert runner.reuse_matches(saved, directory, release, original)
    copy.write_text(json.dumps({**value, 'quant_pipeline': 0}))
    saved['build_report_sha256'] = runner.sha(copy)
    assert not runner.reuse_matches(saved, directory, release, original)
    copy.write_text(json.dumps(value))
    saved['build_report_sha256'] = runner.sha(copy)
    board.write_bytes(b'mutated bitstream')
    assert not runner.reuse_matches(saved, directory, release, original)
