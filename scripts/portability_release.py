#!/usr/bin/env python3
"""Strict pre-programming evidence gate for the portability experiment. No USB.

Evidence index maps the slots returned by required_slots() to report paths.
Reports remain raw producer outputs; the gate recomputes coverage and goals.
"""
import argparse, hashlib, json, math, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
BASE = Path('artifacts/vivado-portability-v1')

class GateError(ValueError):
    pass

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def need(ok, message):
    if not ok:
        raise GateError(message)

def project_path(root, name):
    path = (root / name).resolve()
    need(path.is_relative_to(root.resolve()), f'Path outside project: {name}')
    return path

def bound_files(root, bindings):
    need(isinstance(bindings, dict) and bool(bindings), 'Missing artifact bindings')
    for name, digest in bindings.items():
        path = project_path(root, name)
        need(path.is_file() and sha(path) == digest, f'Binding mismatch: {name}')

def archive_context(root=ROOT):
    path = root / BASE / 'baseline/manifest.json'
    protocol = json.loads((root / BASE / 'protocol.json').read_text())
    need(sha(path) == protocol['baseline_manifest_sha256'], 'Baseline manifest changed')
    entries = json.loads(path.read_text())['files']
    for name, entry in entries.items():
        archived = project_path(root, entry['archive'])
        need(archived.is_file() and sha(archived) == entry['sha256'], f'Archived dependency changed: {name}')
    def old(name):
        need(name in entries, f'Missing historical dependency: {name}')
        return json.loads(project_path(root, entries[name]['archive']).read_text())
    freeze_name = 'artifacts/acoustic-known-deployment-v1/freeze.json'
    freeze = old(freeze_name)
    for name, digest in freeze['sha256'].items():
        need(name in entries and entries[name]['sha256'] == digest, f'Historical freeze dependency missing: {name}')
    results_name = 'artifacts/acoustic-known-final-v1/results.json'
    audit_name = 'artifacts/acoustic-known-final-v1/audit.json'
    results, audit = old(results_name), old(audit_name)
    need(audit['passed'] and results['passed'] and all(g['passed'] for g in results['groups'].values()), 'Historical quality gates failed')
    need(audit['results_sha256'] == entries[results_name]['sha256'], 'Historical audit/results mismatch')
    need(results['deployment_sha256'] == entries[freeze_name]['sha256'], 'Historical quality/freeze mismatch')
    for item in (audit, results):
        for name, digest in item.get('sha256', {}).items():
            need(name in entries and entries[name]['sha256'] == digest, f'Historical audit dependency missing: {name}')
    for machine, digest in protocol['models'].items():
        name = f'artifacts/acoustic-known-release-v1/id{machine}/model.json'
        need(entries[name]['sha256'] == digest and sha(root / name) == digest, f'Frozen model changed: {machine}')
    # ROMs and the frozen model receipt remain immutable too.
    for name, entry in entries.items():
        if name.startswith('artifacts/acoustic-known-release-v1/') and (name.endswith('.hex') or name.endswith('model-freeze.json')):
            need(sha(root / name) == entry['sha256'], f'Frozen model/ROM changed: {name}')
    return protocol, entries

def required_slots():
    slots = ['ram-contract', 'edge-contract', 'flash-fixture']
    for v in ('B', 'C'):
        slots += [f'native-{v}-00-l{l}' for l in (1, 4)]
        slots += [f'ice-{v}-00-l4-s{s}' for s in (1, 2, 3)]
        slots += [f'amd-{v}-00-l4', f'xsim-{v}-small', f'xsim-{v}-00-l4']
    for m in ('02', '04', '06'):
        slots += [f'native-C-{m}-l4', f'ice-C-{m}-l4-s1', f'amd-C-{m}-l4', f'xsim-C-{m}-l4']
    slots += ['ice-C-00-l1-s1', 'amd-C-00-l1', 'xsim-C-00-l1']
    slots += [f'flash-C-{m}-l4' for m in ('00', '02', '04', '06')] + ['flash-C-00-l1']
    return slots

def parse_vivado_utilization(text):
    """Read explicit report tables; a missing section never means zero cells."""
    rows = []
    for line in text.splitlines():
        if line.strip().startswith('|'):
            cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
            if len(cells) >= 2:
                rows.append(cells)
    def numeric(value, label):
        try:
            result = float(value.replace(',', ''))
        except ValueError as error:
            raise GateError('Invalid utilization count: ' + label) from error
        need(math.isfinite(result) and result >= 0, 'Invalid utilization count: ' + label)
        return int(result) if result.is_integer() else result
    def value(*labels):
        for row in rows:
            if row[0].rstrip('*').strip() in labels:
                return numeric(row[1], row[0])
        return None
    resources = {
        'lut': value('Slice LUTs', 'CLB LUTs'),
        'ff': value('Slice Registers', 'CLB Registers'),
        'dsp': value('DSPs', 'DSP48E1', 'DSP48E2'),
        'bram_tiles': value('Block RAM Tile'),
        'ramb18': value('RAMB18', 'RAMB18E1', 'RAMB18E2'),
        'ramb36': value('RAMB36/FIFO', 'RAMB36', 'RAMB36E1', 'RAMB36E2'),
    }
    need(resources['bram_tiles'] is not None, 'Missing explicit Block RAM Tile utilization')
    need(resources['ramb18'] is not None and resources['ramb36'] is not None,
         'Missing explicit RAMB18/RAMB36 utilization')
    resources['bram_count'] = resources['ramb18'] + resources['ramb36']
    need(resources['bram_tiles'] == resources['ramb36'] + resources['ramb18'] / 2,
         'Inconsistent Block RAM Tile/RAMB utilization')
    blackboxes = value('Black Boxes', 'Blackboxes', 'BlackBox')
    if blackboxes is None:
        headings = list(re.finditer(r'(?m)^\s*\d+\.\s+([^\n]+)\n-+\n', text))
        for index, heading in enumerate(headings):
            if heading.group(1).strip() != 'Black Boxes':
                continue
            stop = headings[index + 1].start() if index + 1 < len(headings) else len(text)
            section = text[heading.end():stop]
            section_rows = [[cell.strip() for cell in line.strip().strip('|').split('|')]
                            for line in section.splitlines() if line.strip().startswith('|')]
            need(any(len(row) >= 2 and row[0] == 'Ref Name' and row[1] == 'Used' for row in section_rows),
                 'Malformed Black Boxes utilization section')
            need('+' in section, 'Truncated Black Boxes utilization table')
            data = [row for row in section_rows if row[0] != 'Ref Name']
            blackboxes = sum(numeric(row[1], row[0]) for row in data)
            break
    need(blackboxes is not None, 'Missing explicit Black Boxes utilization')
    resources['blackboxes'] = blackboxes
    return resources

def validate_report(root, path):
    report = json.loads(path.read_text())
    need(report.get('passed') is True, f'Report did not pass: {path}')
    bindings = report.get('bindings', report.get('input_sha256'))
    bound_files(root, bindings)
    need('rtl/core/known_spectral_core.sv' in bindings or report.get('contract') == 'spram16k', f'Report lacks core binding: {path}')
    outputs = report.get('output_sha256')
    expanded = {}
    if isinstance(outputs, dict):
        output_root = path.parent / 'results' if report.get('tool') == 'Vivado' else root
        need(bool(outputs), 'No raw tool output bindings')
        for name, digest in outputs.items():
            item = project_path(output_root, name)
            need(item.is_file() and sha(item) == digest, f'Output changed: {item}')
            expanded[str(item.relative_to(root))] = digest
    elif isinstance(outputs, str):
        item = path.parent / 'output.bin'
        need(sha(item) == outputs, f'Output changed: {path}')
        expanded[str(item.relative_to(root))] = outputs
    if report.get('tool') == 'Vivado':
        package = path.parent / 'package'
        for name, digest in report['input_sha256'].items():
            item = project_path(package, name)
            need(item.is_file() and sha(item) == digest, f'Package changed: {item}')
            expanded[str(item.relative_to(root))] = digest
        log = (path.parent / 'results/run.log').read_text()
        match = re.search(r'SW Build\s+(\d+)', log)
        report['vivado'] = report.get('version')
        report['vivado_build'] = match.group(1) if match else None
        report['completion_marker'] = 'VIVADO_PORTABILITY_COMPLETE' in log
        package_info = json.loads((package / 'package.json').read_text())
        need(package_info['bindings'] == report['bindings'] and package_info['params'] == report['params'], 'Package/report provenance mismatch')
        expanded[str((package / 'package.json').relative_to(root))] = sha(package / 'package.json')
        report['records'] = package_info['records']
        if report.get('mode') == 'simulation':
            report.update(report['result'])
        else:
            report['timing'] = report.get('timing', report.get('result'))
            report['io_delay_ns'] = report.get('io_delay_ns', None)
            raw_util = path.parent / 'results/utilization.rpt'
            need(str(raw_util.relative_to(root)) in expanded, 'Utilization report is not hash-bound')
            resources = parse_vivado_utilization(raw_util.read_text())
            report['resources'] = resources
            for key in ('blackboxes', 'bram_count'):
                if key in report:
                    need(report[key] == resources[key], f'Vivado mapping report mismatch: {key}')
                report[key] = resources[key]
    report['_bound_outputs'] = expanded
    return report

def validate_identity(report, slot, protocol):
    if '-' not in slot or slot in ('ram-contract', 'edge-contract', 'flash-fixture'):
        return
    parts = slot.split('-'); version = parts[1]
    need(report.get('quant_pipeline') == int(version == 'C'), f'Wrong pipeline variant: {slot}')
    if parts[2] == 'small':
        return
    machine, lanes = parts[2], int(parts[3][1:])
    need(str(report.get('machine')) == machine and report.get('lanes') == lanes, f'Wrong machine/lanes: {slot}')
    if 'model_sha256' in report:
        need(report['model_sha256'] == protocol['models'][machine], f'Wrong frozen model: {slot}')
    if slot.startswith('ice-'):
        need(report.get('seed') == int(parts[4][1:]), f'Wrong seed: {slot}')

def finite(value, label):
    need(isinstance(value, (int, float)) and math.isfinite(value), f'Invalid numeric value: {label}')
    return value

def validate_coverage(report, machine, count, protocol, slot):
    need(report.get('windows', 0) == count * 156 and report.get('samples', 0) == count * 159744, f'Incomplete coverage: {slot}')
    records = report.get('records', [report['record']] if 'record' in report else [])
    expected = protocol['records'][machine][:count]
    need([(r['name'], r['npy_sha256']) for r in records] == [(r['name'], r['npy_sha256']) for r in expected], f'Data list differs: {slot}')
    need(report.get('intermediate_checks', 0) > 0 or report.get('actual_rtl_core') is True, f'No computation checks: {slot}')
    need(report.get('dropped_samples', 0) == 0, f'Dropped samples: {slot}')

def validate_board(root, path, report):
    need(report.get('abc_dff') is True and report.get('nominal_clock_hz') == 12000000, 'Wrong board settings')
    need(sha(path.parent / 'board.bin') == report.get('bitstream_sha256'), 'Bitstream changed')
    need(bool(report.get('fmax')), 'Missing board timing')
    for clk in report['fmax'].values():
        need(clk['achieved'] >= 13.2 and clk['constraint'] >= 13.199, 'UPduino timing failed')
    for resource in report['utilization'].values():
        need(0 <= resource['used'] <= resource['available'], 'UPduino resource overflow')

def check_release(root=ROOT, index_path=None):
    root = root.resolve()
    protocol, _ = archive_context(root)
    index_path = index_path or root / BASE / 'evidence-index.json'
    need(index_path.is_file(), f'Missing evidence index: {index_path}')
    index = json.loads(index_path.read_text())
    need(set(index) == set(required_slots()), 'Evidence index mismatch; missing=' + ','.join(sorted(set(required_slots())-set(index))) + '; unexpected=' + ','.join(sorted(set(index)-set(required_slots()))))
    reports, files = {}, {}
    for slot in required_slots():
        path = project_path(root, index[slot]); need(path.is_file(), f'Missing report: {slot}')
        report = validate_report(root, path); validate_identity(report, slot, protocol)
        reports[slot] = report; files[str(path.relative_to(root))] = sha(path)
        files.update(report.get('bindings', report.get('input_sha256', {})))
        files.update(report['_bound_outputs'])
        if slot.startswith('ice-'):
            validate_board(root, path, report)
            files[str((path.parent / 'board.bin').relative_to(root))] = report['bitstream_sha256']
        if slot.startswith(('native-', 'xsim-')) and not slot.endswith('small'):
            machine = slot.split('-')[2]; count = 7 if slot.startswith('native-') and machine == '00' else 2
            if slot == 'xsim-C-00-l1': count = 1
            validate_coverage(report, machine, count, protocol, slot)
        if slot.startswith('native-'):
            need(report['sample_period_cycles'] == (1500 if report['lanes'] == 1 else 750), f'Wrong input cadence: {slot}')
            need(report['backpressure_cycles'] == 0, f'Input backpressure: {slot}')
        if slot.startswith('flash-C-'):
            validate_coverage(report, slot.split('-')[2], 1, protocol, slot)
            need(report['actual_spi_transport'] and report['actual_rtl_core'] and not report['fixture'], 'Flash simulation not full-sized')
            need(report.get('period') == (1500 if report['lanes'] == 1 else 750), 'Wrong Flash simulation cadence')
            result = report.get('result', {})
            need(result.get('errors') == 0 and result.get('protocol_errors') == 0 and result.get('generated') == result.get('accepted') == 159744, 'Flash simulation counters failed')
        if slot.startswith(('amd-', 'xsim-')):
            need(report.get('returncode') == 0 and report.get('vivado') == '2024.2' and str(report.get('vivado_build')) == '5239630', f'Vivado execution failed/wrong version: {slot}')
        if slot.startswith('xsim-'):
            need(report.get('completion_marker') is True, f'Vivado completion missing: {slot}')
        if slot.startswith('amd-'):
            need(report['part'] == protocol['part'] and report['clock_period_ns'] == 20 and report['io_delay_ns'] == 2, f'Wrong AMD configuration: {slot}')
            need(report.get('blackboxes') == 0 and report.get('bram_count', 0) > 0, 'AMD RAM mapping failed')
            if slot != 'amd-C-00-l1':
                t = report['timing']
                for key in ('wns_ns', 'tns_ns', 'hold_wns_ns', 'hold_tns_ns'):
                    finite(t[key], slot + ':' + key)
                need(t['unconstrained_paths'] == 0, f'AMD paths lack constraints: {slot}')
                # B characterizes the initial design; timing closure is a C goal.
                if slot.startswith('amd-C-'):
                    need(t['wns_ns'] >= 0 and t['tns_ns'] == 0 and t['hold_wns_ns'] >= 0 and t['hold_tns_ns'] == 0, f'AMD final timing failed: {slot}')
                need(finite(t['internal_delay_ns'], slot) > 0, 'Missing AMD internal delay')
    need(reports['ram-contract'].get('contract') == 'spram16k' and set(reports['ram-contract'].get('backends', [])) >= {'reference', 'amd'}, 'Missing RAM backend contract')
    edge = reports['edge-contract']
    need(set(edge.get('cases', [])) >= {'rne', 'saturation', 'stall', 'reset_quant', 'frame_id', 'back_to_back'}, 'Missing edge scenarios')
    need(reports['flash-fixture'].get('fixture') is True, 'Missing fixture protocol regression')
    for lanes in (1, 4):
        b, c = reports[f'native-B-00-l{lanes}'], reports[f'native-C-00-l{lanes}']
        need(len(b['stages']) == len(c['stages']) == 7, 'Incomplete cycle receipts')
        for old, new in zip(b['stages'], c['stages']):
            need(all(new[k] == old[k] for k in ('pre', 'dft', 'power')), 'Unexpected stage change')
            need(new['nn'] == old['nn'] + 512 and new['total'] == old['total'] + 512, 'Wrong pipeline cycle delta')
            need((new['total'] - old['total']) / old['total'] <= protocol['goals']['cycles_increase_max'], 'Cycle cost exceeds goal')
    # Cross-simulator receipts must agree on every active-stage counter,
    # not merely on their sum or a printed completion marker.
    for slot, xsim in reports.items():
        if not slot.startswith('xsim-') or slot.endswith('small'):
            continue
        _, version, machine, lanes = slot.split('-')
        native = reports[f'native-{version}-{machine}-{lanes}']
        stages = xsim.get('stages', [])
        count = xsim['windows'] // 156
        need(len(stages) == count, f'Missing Vivado stage receipts: {slot}')
        need(len(native.get('stages', [])) >= count, f'Missing native stage receipts: {slot}')
        for index, (observed, expected) in enumerate(zip(stages, native['stages'])):
            for key in ('pre', 'dft', 'power', 'nn', 'total'):
                need(key in observed and finite(observed[key], slot + ':' + key) >= 0, f'Invalid Vivado stage receipt: {slot}')
                need(observed[key] == expected[key], f'Vivado/native stage mismatch: {slot} clip {index} {key}')
            need(sum(observed[key] for key in ('pre', 'dft', 'power', 'nn')) == observed['total'], f'Vivado stage sum mismatch: {slot}')
    b, c = (reports[f'amd-{v}-00-l4']['timing']['internal_delay_ns'] for v in ('B', 'C'))
    gain = (b - c) / b
    need(gain >= protocol['goals']['amd_delay_reduction_min'], 'AMD delay improvement below goal')
    b, c = (reports[f'ice-{v}-00-l4-s1']['fmax']['clk']['achieved'] for v in ('B', 'C'))
    regression = b / c - 1
    need(regression <= protocol['goals']['ice40_delay_regression_max'], 'UPduino delay regression exceeds goal')
    # Gate scripts themselves are part of the programming authorization.
    for name in ('scripts/run_known_hardware.py', 'scripts/audit_known_hardware.py', 'scripts/portability_release.py'):
        files[name] = sha(root / name)
    files[str((root / BASE / 'protocol.json').relative_to(root))] = sha(root / BASE / 'protocol.json')
    files[str(index_path.relative_to(root))] = sha(index_path)
    tools_receipt = root / BASE / 'local-tools.json'
    if tools_receipt.exists():
        files[str(tools_receipt.relative_to(root))] = sha(tools_receipt)
    return dict(schema='portability-release-v1', passed=True, candidate='C', physical_hardware=False,
                baseline_manifest_sha256=protocol['baseline_manifest_sha256'], model_sha256=protocol['models'],
                evidence_index=str(index_path.relative_to(root)), sha256=files,
                metrics=dict(amd_delay_reduction=gain, ice40_delay_regression=regression),
                scope='pre-programming gate; physical acceptance is a separate audit')

def verify_manifest(path, root=ROOT, build_report=None):
    root = root.resolve()
    release = json.loads(path.read_text())
    need(release.get('schema') == 'portability-release-v1' and release.get('passed') is True, 'Invalid portability release')
    bound_files(root, release['sha256'])
    rebuilt = check_release(root, project_path(root, release['evidence_index']))
    need(rebuilt == release, 'Release no longer matches checked evidence')
    if build_report is not None:
        name = str(build_report.resolve().relative_to(root))
        need(release['sha256'].get(name) == sha(build_report), 'Build is outside frozen release')
        report = json.loads(build_report.read_text())
        need(report.get('quant_pipeline') == 1, 'Only winning pipeline may be programmed')
    return release

def main():
    p = argparse.ArgumentParser(); action = p.add_mutually_exclusive_group(required=True)
    action.add_argument('--check', action='store_true'); action.add_argument('--freeze', action='store_true')
    p.add_argument('--index', type=Path); p.add_argument('--output', type=Path, default=ROOT / BASE / 'release.json')
    a = p.parse_args()
    try:
        result = check_release(ROOT, a.index.resolve() if a.index else None)
    except (GateError, KeyError, OSError, ValueError) as error:
        print(json.dumps(dict(passed=False, error=str(error)))); raise SystemExit(1)
    if a.freeze:
        need(not a.output.exists(), 'Refusing to replace frozen release')
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(passed=True, metrics=result['metrics'], frozen=a.freeze)))

if __name__ == '__main__':
    main()
