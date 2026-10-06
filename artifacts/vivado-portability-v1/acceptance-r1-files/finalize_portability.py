#!/usr/bin/env python3
"""Bind the physical acceptance to the immutable pre-programming release."""
import json
from pathlib import Path

from portability_release import ROOT, BASE, need, sha, verify_manifest, bound_files
import summarize_portability


def finalize(root=ROOT):
    directory = root / BASE
    release_path = directory / 'release.json'
    verify_manifest(release_path, root)
    audit_path = directory / 'hardware-audit.json'
    audit = json.loads(audit_path.read_text())
    need(audit.get('passed') is True and audit.get('current_source_claim') is True,
         'Physical acceptance has not passed for the current release')
    need(audit['deployment_sha256'] == sha(release_path), 'Different physical deployment')
    need(audit['source_sha256'] == sha(root / 'scripts/audit_known_hardware.py'),
         'Physical auditor changed')
    bound_files(root, audit['sha256'])
    need(audit['physical_runs'] >= 11 and audit['windows_by_lanes']['4'] >= 1248
         and audit['windows_by_lanes']['1'] >= 468, 'Incomplete physical matrix')
    need(audit['main_machines'] == ['00', '02', '04', '06']
         and audit['overload']['passed'] is True, 'Missing model or overload/recovery proof')
    need(all(row['samples'] == row['generated'] == row['accepted'] == 159744
             and row['windows'] == 156 and row['errors'] == 0
             and row['core_error'] == 0 and row['protocol_errors'] == 0
             for row in audit['records']), 'Invalid normal replay counters')
    compatibility_path = directory / 'baseline-compatibility.json'
    compatibility = json.loads(compatibility_path.read_text())
    bound_files(root, compatibility['bindings'])
    for pair in compatibility['pairs']:
        original = json.loads((root / pair['archive_report']).read_text())
        baseline = json.loads((root / pair['current_report']).read_text())
        need(original['records'] == baseline['records'] and original['passed']
             and baseline['passed'], 'A/B recording or numerical evidence differs')
        need(original['intermediate_checks'] == baseline['intermediate_checks'],
             'A/B numerical check coverage differs')
        need(len(original['stages']) == len(baseline['stages']) == 7,
             'A/B clip count differs')
        need(all(all(a[k] == b[k] for k in ('pre', 'dft', 'power', 'nn', 'total'))
                 for a, b in zip(original['stages'], baseline['stages'])),
             'A/B active stage counts differ')
    return dict(schema='portability-acceptance-v1', passed=True, candidate='C',
                pre_programming_release_sha256=sha(release_path),
                physical_audit_sha256=sha(audit_path),
                physical_runs=audit['physical_runs'],
                windows_by_lanes=audit['windows_by_lanes'],
                amd_board_tested=False, hfosc_increased=False)


def main():
    result = finalize()
    summarize_portability.main()
    directory = ROOT / BASE
    names = ('release.json', 'hardware-audit.json', 'baseline-compatibility.json',
             'comparison.json', 'report.md', 'physical-report.md')
    result['sha256'] = {str((directory / name).relative_to(ROOT)): sha(directory / name)
                        for name in names}
    for name in ('scripts/finalize_portability.py', 'scripts/summarize_portability.py',
                 'scripts/run_portability_hardware.py'):
        result['sha256'][name] = sha(ROOT / name)

    output = directory / 'acceptance.json'
    need(not output.exists(), 'Refusing to replace final acceptance receipt')
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
