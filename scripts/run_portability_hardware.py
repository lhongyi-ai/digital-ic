#!/usr/bin/env python3
"""Execute the fixed USB matrix only after the strict portability release gate."""
import argparse, json, re, subprocess, sys
from pathlib import Path
from portability_release import ROOT, BASE, verify_manifest, sha


def reuse_matches(saved, directory, release, report):
    """The attempt copy is reserialized JSON; bind its bytes and source value."""
    copy = directory / 'build-report.json'
    original = json.loads(report.read_text())
    return (saved.get('deployment_sha256') == sha(release)
            and saved.get('build_report_sha256') == sha(copy)
            and json.loads(copy.read_text()) == original
            and saved.get('bitstream_sha256') == original.get('bitstream_sha256')
            and sha(directory / 'board.bin') == saved.get('bitstream_sha256'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--run-prefix', required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', args.run_prefix):
        parser.error('run-prefix must be a single safe directory name')
    release = ROOT / BASE / 'release.json'
    verify_manifest(release, ROOT)
    index = json.loads((ROOT / BASE / 'evidence-index.json').read_text())
    jobs = [(m, 4, r, 750, '') for m in ('00', '02', '04', '06') for r in (0, 1)]
    jobs += [('00', 1, 0, 1500, ''), ('00', 1, 1, 1500, ''),
             ('00', 1, 0, 750, '-overload'), ('00', 1, 0, 1500, '-recovery')]
    overload = None
    for machine, lanes, record, period, suffix in jobs:
        run_id = f'{args.run_prefix}-id{machine}-l{lanes}-r{record}{suffix}'
        directory = ROOT / 'measurements/known-replay' / run_id
        report = ROOT / index[f'ice-C-{machine}-l{lanes}-s1']
        if suffix == '-overload':
            overload = directory.name
        if directory.exists():
            if not args.resume:
                raise RuntimeError(f'Existing attempt: {directory}')
            saved = json.loads((directory / 'manifest.json').read_text())
            if not reuse_matches(saved, directory, release, report):
                raise RuntimeError(f'Cannot reuse different release/build: {directory}')
            if suffix != '-overload' and saved.get('status') != 'passed':
                raise RuntimeError(f'Retained failed attempt needs diagnosis: {directory}')
            if suffix == '-overload' and not (saved.get('physical_hardware') and saved.get('status') == 'failed'):
                raise RuntimeError('Missing real expected-overload attempt')
            print('REUSED', run_id, flush=True)
            continue
        command = [sys.executable, str(ROOT / 'scripts/run_known_hardware.py'),
                   '--deployment-manifest', str(release), '--build-report', str(report),
                   '--run-id', run_id, '--record-index', str(record), '--period', str(period)]
        if args.execute:
            command.append('--execute')
        print('START', run_id, flush=True)
        code = subprocess.run(command, cwd=ROOT).returncode
        if not args.execute:
            if code:
                raise RuntimeError(f'Preparation failed: {run_id}')
            continue
        saved = json.loads((directory / 'manifest.json').read_text())
        if suffix == '-overload':
            # Keep the raw failing replay; its exact error and subsequent recovery
            # are validated together by the physical audit below.
            if code == 0 or not saved.get('physical_hardware') or saved.get('status') != 'failed':
                raise RuntimeError('Overload did not produce the prescribed physical failure')
        elif code or saved.get('status') != 'passed':
            raise RuntimeError(f'Physical replay failed; retained: {directory}')
    if args.execute:
        command = [sys.executable, str(ROOT / 'scripts/audit_known_hardware.py'),
                   '--deployment-manifest', str(release), '--expected-overload', overload,
                   '--output', str(ROOT / BASE / 'hardware-audit.json')]
        subprocess.run(command, cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
