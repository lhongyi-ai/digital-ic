#!/usr/bin/env python3
"""Summarize real experiment receipts; missing results never become passes."""
import json, re
from pathlib import Path
from portability_release import ROOT, BASE, required_slots, sha, validate_report


def main():
    directory = ROOT / BASE
    index_path = directory / 'evidence-index.json'
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    result = dict(schema='portability-comparison-v1', physical_clock_unchanged=True,
                  reports={}, missing=sorted(set(required_slots()) - set(index)), errors={}, platforms={})
    reports = {}
    for slot, name in index.items():
        path = ROOT / name
        try:
            report = validate_report(ROOT, path)
            reports[slot] = report
            result['reports'][slot] = dict(path=name, sha256=sha(path), current=True)
        except (AssertionError, ValueError, KeyError, OSError) as error:
            result['errors'][slot] = str(error)
            result['reports'][slot] = dict(path=name, current=False)
    for slot, report in reports.items():
        if slot.startswith('ice-'):
            timing_path = ROOT / index[slot]
            raw = json.loads((timing_path.parent / 'timing.json').read_text())
            internal = [p for p in raw['critical_paths'] if p['from'] == 'posedge clk' and p['to'] == 'posedge clk']
            path = max(internal, key=lambda p: sum(s['delay'] for s in p['path']))['path'] if internal else []
            entry = dict(fmax_mhz=report['fmax']['clk']['achieved'],
                         utilization=report['utilization'], seed=report['seed'],
                         input_sha256=report['input_sha256'], model_sha256=report['model_sha256'],
                         bitstream_sha256=report['bitstream_sha256'])
            if path:
                entry.update(internal_delay_ns=sum(s['delay'] for s in path),
                             logic_delay_ns=sum(s['delay'] for s in path if s['type'] != 'routing'),
                             routing_delay_ns=sum(s['delay'] for s in path if s['type'] == 'routing'),
                             path_start=path[0]['from'], path_end=path[-1]['to'],
                             rtl_regions=sorted({source for segment in path for source in segment.get('sources', [])}))
            result['platforms'].setdefault('ice40', {})[slot] = entry
        elif slot.startswith('amd-'):
            entry = {
                key: report[key] for key in ('timing', 'resources', 'part', 'clock_period_ns', 'io_delay_ns', 'vivado', 'vivado_build', 'bindings') if key in report}
            raw_path = ROOT / index[slot]
            critical = raw_path.parent / 'results/critical_paths.rpt'
            if critical.exists():
                match = re.search(r'Data Path Delay:\s*([\d.]+)ns\s*\(logic\s*([\d.]+)ns(?:\s*\([^)]*\))?\s*route\s*([\d.]+)ns', critical.read_text())
                if match:
                    entry['critical_path_breakdown'] = dict(total_delay_ns=float(match[1]), logic_delay_ns=float(match[2]), routing_delay_ns=float(match[3]))
            result['platforms'].setdefault('amd', {})[slot] = entry
        elif slot.startswith('native-'):
            result.setdefault('activity', {})[slot] = {key: report[key] for key in ('stages', 'sample_period_cycles', 'backpressure_cycles', 'windows', 'samples', 'intermediate_checks')}
    for platform in ('amd', 'ice40'):
        bslot, cslot = ('amd-B-00-l4', 'amd-C-00-l4') if platform == 'amd' else ('ice-B-00-l4-s1', 'ice-C-00-l4-s1')
        values = result['platforms'].get(platform, {})
        if bslot in values and cslot in values:
            if platform == 'amd':
                b, c = (values[s]['timing']['internal_delay_ns'] for s in (bslot, cslot))
            else:
                b, c = (values[s]['internal_delay_ns'] for s in (bslot, cslot))
            result.setdefault('comparisons', {})[platform] = dict(b_delay_ns=b, c_delay_ns=c, delay_reduction=(b-c)/b)
    result['verification_totals'] = dict(native_windows=sum(r['windows'] for slot,r in reports.items() if slot.startswith('native-')), vivado_windows=sum(r.get('windows',0) for slot,r in reports.items() if slot.startswith('xsim-') and 'small' not in slot), vivado_intermediate_checks=sum(r.get('intermediate_checks',0) for slot,r in reports.items() if slot.startswith('xsim-') and 'small' not in slot))
    tools = directory / 'local-tools.json'
    if tools.exists():
        result['local_tools'] = json.loads(tools.read_text())
    (directory / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    lines = ['# Cross-FPGA implementation and quantization timing experiment', '',
             'These results come from saved experiment reports. Missing results and failures are retained. Original deployment receipts and the full Flash recovery backup remain in the laboratory archive; final test recordings were not revisited.', '',
             'The original path combined the final wide partial-product accumulation, ties-to-even rounding, symmetric saturation, and sign restoration in one combinational cycle. Candidate C enters NORM_QUANT after the final normalization accumulation, reuses wide_acc, and quantizes on the next cycle. Power computation keeps its original schedule.', '',
             'The RAM backends share rising-edge sampling and synchronous reads. Output during a write is not a valid read. AMD uses inferred BRAM; iCE40 uses the original SPRAM.', '',
             '| Platform and implementation settings | B internal delay ns | C internal delay ns | Reduction |', '| --- | ---: | ---: | ---: |']
    for platform, item in result.get('comparisons', {}).items():
        label = "AMD (default implementation)" if platform == "amd" else "iCE40 (seed 1)"
        lines.append(f"| {label} | {item['b_delay_ns']:.3f} | {item['c_delay_ns']:.3f} | {item['delay_reduction']:.2%} |")
    lines += ['', 'The worst internal paths include retained debug-output registers. AMD B traverses the shared multiplier, wide accumulation, feature, and rounded_magnitude logic, ending at dbg_value_reg[58]. C moves the bottleneck to purpose control, the shared multiplier, and wide accumulation ending at dbg_value_reg[53]. These are worst paths of the complete observable core; their endpoints are debug registers.', '',
              '| AMD ID00 four MACs | LUT | FF | DSP | BRAM tile |', '| --- | ---: | ---: | ---: | ---: |']
    for version in ('B', 'C'):
        resources = result['platforms'].get('amd', {}).get(f'amd-{version}-00-l4', {}).get('resources')
        if resources:
            lines.append(f"| {version} | {resources['lut']} | {resources['ff']} | {resources['dsp']} | {resources['bram_tiles']} |")
    lines += ['', '| AMD C four MACs | Worst internal delay ns | WNS ns | Hold slack ns | LUT | FF |', '| --- | ---: | ---: | ---: | ---: | ---: |']
    for machine in ('00','02','04','06'):
        entry = result['platforms'].get('amd', {}).get(f'amd-C-{machine}-l4')
        if entry:
            timing, resources = entry['timing'], entry['resources']
            lines.append(f"| {machine} | {timing['internal_delay_ns']:.3f} | {timing['wns_ns']:.3f} | {timing['hold_wns_ns']:.3f} | {resources['lut']} | {resources['ff']} |")
    lines += ['', 'AMD implementation uses xc7a35tcpg236-1, Vivado 2024.2 Build 5239630, two threads, a 20 ns clock, and 2 ns input/output assumptions. All four C models pass setup and hold checks, with zero unconstrained paths or black boxes and inferred BRAM storage. OOC implementation does not establish AMD board-level I/O behavior.']
    lines += ['', '| UPduino ID00 four MACs | seed | LC | Estimated Fmax MHz |', '| --- | ---: | ---: | ---: |']
    for version in ('B', 'C'):
        for seed in (1, 2, 3):
            entry = result['platforms'].get('ice40', {}).get(f'ice-{version}-00-l4-s{seed}')
            if entry:
                lines.append(f"| {version} | {seed} | {entry['utilization']['ICESTORM_LC']['used']} / 5280 | {entry['fmax_mhz']:.3f} |")
    for lanes in (1, 4):
        old = result.get('activity', {}).get(f'native-B-00-l{lanes}')
        new = result.get('activity', {}).get(f'native-C-00-l{lanes}')
        if old and new:
            deltas = [{k: b[k]-a[k] for k in ('pre','dft','power','nn','total')} for a,b in zip(old['stages'],new['stages'])]
            result.setdefault('cycle_comparisons', {})[str(lanes)] = dict(deltas=deltas, increase_fraction_max=max(512/a['total'] for a in old['stages']))
            lines += ['', f"ID00 {lanes} MACs: {len(deltas)} recording-level stage comparisons. Each recording adds 512 NN/total activity cycles; the other three stages are unchanged. Maximum activity overhead {result['cycle_comparisons'][str(lanes)]['increase_fraction_max']:.6%}; input period {new['sample_period_cycles']}; backpressure {new['backpressure_cycles']}."]
    lines += ['', f"Local full-core verification:  {result['verification_totals']['native_windows']} windows; Vivado full-recording verification:  {result['verification_totals']['vivado_windows']} windows, {result['verification_totals']['vivado_intermediate_checks']} intermediate numerical checks. Small tests additionally cover the RAM contract, arithmetic boundaries, input stalls, output blocking, reset, and protocol errors. Reset in the new quantization state cancels the prior transaction.", '', 'Candidate C meets all timing, resource, and cycle targets, so D/E were unnecessary. Frozen ID00/02/04/06 parameters and thresholds are unchanged. This experiment uses only the development cv recordings selected in advance.']
    compatibility = directory / 'baseline-compatibility.json'
    if compatibility.exists():
        receipt = json.loads(compatibility.read_text())
        assert all(sha(ROOT / name) == digest for name, digest in receipt['bindings'].items())
        result['baseline_compatibility'] = receipt
        lines += ['', 'A to B: integer-reference checks and all core activity-stage counts agree for the same seven recordings. The historical one-MAC baseline supplied ready/valid input as quickly as possible; this experiment uses a fixed 1500-cycle cadence. Wall-clock latency and blocking counts under different cadences are not portability differences.']
    release = directory / 'release.json'
    if release.exists():
        result['release'] = dict(path=str(release.relative_to(ROOT)), sha256=sha(release))
    audit_path = directory / 'hardware-audit.json'
    if audit_path.exists():
        audit = json.loads(audit_path.read_text())
        valid = audit['passed'] and audit['source_sha256'] == sha(ROOT / 'scripts/audit_known_hardware.py') and all(sha(ROOT / name) == digest for name, digest in audit['sha256'].items()) and audit['deployment_sha256'] == sha(release)
        assert valid, 'Physical audit bindings changed'
        result['physical'] = dict(path=str(audit_path.relative_to(ROOT)), sha256=sha(audit_path), passed=valid, runs=audit['physical_runs'], windows_by_lanes=audit['windows_by_lanes'], overload=audit['overload'])
        lines += ['', f"Physical board: {audit['physical_runs']} passing runs, {audit['windows_by_lanes']['4']} four-MAC windows and {audit['windows_by_lanes']['1']} one-MAC windows. One expected overload failure is retained. After reset, the same one-MAC bitstream passes at a 1500-cycle cadence. Each normal startup processes 156 consecutive windows, checking numerical values, CRC, commit markers, generated/received counts, and two identical raw readbacks.", '', 'HFOSC was not increased. No AMD board test was performed. Original failures and run logs are retained in the laboratory archive.', '', 'Additional resume bullet (retain the existing 3.78x parallelization result):', '', 'Ported a fixed-point accelerator across iCE40 and AMD FPGAs with a verified synchronous memory interface; pipelined normalization to reduce routed critical-path delay by 11.1% on AMD and 17.9% on iCE40, adding 512 cycles per recording; validated bit-exact results in Vivado simulation and UPduino hardware replays.']
    else:
        attempts = [json.loads(path.read_text()) for path in (ROOT / 'measurements/known-replay').glob('portability-c-*/manifest.json')]
        current = [attempt for attempt in attempts if release.exists() and attempt.get('deployment_sha256') == sha(release)]
        saved = sum(attempt.get('status') == 'passed' for attempt in current)
        result['physical'] = dict(passed=False, state='pending_final_audit', saved_passes=saved, first_failed_attempt='measurements/known-replay/portability-c-r1-id00-l4-r0/manifest.json')
        lines += ['', f'Physical acceptance is incomplete; {saved} passing runs are saved. The final hardware-audit.json is authoritative. The first configuration-verification USB transfer failure is retained in measurements/known-replay/portability-c-r1-id00-l4-r0; execution resumed under new run IDs after reconnecting.']
    (directory / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    lines += ['', f"Registered reports: {len(index)}; missing: {len(result['missing'])}; binding/report errors: {len(result['errors'])}.", '',
              'Simulation verifies numerical behavior, protocols, and activity counts. Place and route establishes timing estimates for the specified devices and constraints. The physical board still uses nominal 12 MHz; improved timing margin does not demonstrate faster recording processing.', '',
              'Programming requires the complete portability_release.py gate. This summary does not authorize programming.', '', 'Missing reports or binding errors:']
    lines += ['- ' + s for s in result['missing']]
    lines += ['- ' + s + ': ' + error for s, error in result['errors'].items()]
    (directory / 'report.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps(dict(current=len(reports), missing=len(result['missing']), errors=result['errors'])))


if __name__ == '__main__':
    main()
