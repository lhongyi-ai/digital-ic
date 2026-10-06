#!/usr/bin/env python3
"""Run the fixed local experiment matrix, retaining all subprocess exits/logs."""
import argparse, fcntl, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/vivado-portability-v1'

def register(slot, report):
    with (BASE / 'index.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = BASE / 'evidence-index.json'
        index = json.loads(path.read_text()) if path.exists() else {}
        index[slot] = str(report.relative_to(ROOT))
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(index, indent=2) + '\n')
        temporary.replace(path)

def jobs(suite):
    if suite == 'small':
        for v, q in [('B', 0), ('C', 1)]:
            for lanes in (1, 4):
                yield None, 'core', ['--lanes', str(lanes), '--quant-pipeline', str(q)], f'portability-{v.lower()}-small-l{lanes}'
    elif suite == 'native':
        for v, q in [('B', 0), ('C', 1)]:
            for lanes in (1, 4):
                yield f'native-{v}-00-l{lanes}', 'native', ['--machine', '00', '--clips', '7', '--lanes', str(lanes), '--period', str(1500 if lanes == 1 else 750), '--quant-pipeline', str(q)], f'portability-{v.lower()}-id00-l{lanes}'
        for machine in ('02', '04', '06'):
            yield f'native-C-{machine}-l4', 'native', ['--machine', machine, '--clips', '2', '--lanes', '4', '--period', '750', '--quant-pipeline', '1'], f'portability-c-id{machine}-l4'
    elif suite == 'flash':
        yield 'flash-fixture', 'flash', ['--quant-pipeline', '1'], 'portability-c-flash-fixture'
        for machine, lanes in [('00', 4), ('02', 4), ('04', 4), ('06', 4), ('00', 1)]:
            yield f'flash-C-{machine}-l{lanes}', 'flash', ['--production', '--machine', machine, '--label', '0', '--lanes', str(lanes), '--period', str(1500 if lanes == 1 else 750), '--quant-pipeline', '1'], f'portability-c-flash-id{machine}-l{lanes}'
    elif suite == 'board':
        for v, q in [('B', 0), ('C', 1)]:
            for seed in (1, 2, 3):
                yield f'ice-{v}-00-l4-s{seed}', 'board', ['--machine', '00', '--lanes', '4', '--abc-dff', '--seed', str(seed), '--quant-pipeline', str(q)], f'portability-{v.lower()}-id00-l4-s{seed}'
        for machine, lanes in [('02', 4), ('04', 4), ('06', 4), ('00', 1)]:
            yield f'ice-C-{machine}-l{lanes}-s1', 'board', ['--machine', machine, '--lanes', str(lanes), '--abc-dff', '--seed', '1', '--quant-pipeline', '1'], f'portability-c-id{machine}-l{lanes}-s1'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--suite', choices=('small', 'native', 'flash', 'board'), required=True)
    parser.add_argument('--resume', action='store_true', help='Reuse only existing source-bound passes; failed runs are never silently retried')
    parser.add_argument('--revision', default='', help='Suffix for a diagnosed source revision; preserves earlier runs')
    args = parser.parse_args()
    logs = ROOT / 'build/vivado-portability/local'
    logs.mkdir(parents=True, exist_ok=True)
    from experiment_acoustic_v2 import sha
    for slot, kind, flags, run_id in jobs(args.suite):
        if args.revision:
            run_id += '-' + args.revision
        directory = ROOT / f'build/known-{kind}' / run_id
        report = directory / 'report.json'
        if directory.exists():
            if not args.resume or not report.exists():
                raise RuntimeError(f'Existing incomplete run: {directory}; diagnose before using a new run ID')
            data = json.loads(report.read_text())
            bindings = data.get('bindings', data.get('input_sha256', {}))
            if not data.get('passed') or not bindings or not all((ROOT / p).is_file() and sha(ROOT / p) == h for p, h in bindings.items()):
                raise RuntimeError(f'Cannot reuse unbound pass: {report}')
            if slot:
                register(slot, report)
            print(f'REUSED {run_id}', flush=True)
            continue
        script = {'core': 'test_known_core.py', 'native': 'test_known_native.py', 'flash': 'test_known_flash.py', 'board': 'build_known_board.py'}[kind]
        command = [sys.executable, str(ROOT / 'scripts' / script), *flags, '--run-id', run_id]
        with (logs / f'{run_id}.log').open('w') as log:
            process = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        (logs / f'{run_id}.exit.json').write_text(json.dumps({'command': command, 'returncode': process.returncode}) + '\n')
        print(f'{run_id}: exit={process.returncode}', flush=True)
        if process.returncode:
            raise RuntimeError(f'Failed: {logs / (run_id + ".log")}')
        if slot:
            register(slot, report)

if __name__ == '__main__':
    main()
