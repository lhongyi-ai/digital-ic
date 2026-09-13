#!/usr/bin/env python3
"""Explain one saved development replay; never train, evaluate a test set or use USB.

Recompute intermediate values, compare the frozen RTL-regression vector and
original board log, then export portable figures and plain CSV/JSON tables.
"""
import csv
import hashlib
import json
import struct
import wave
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from threadpoolctl import threadpool_limits

from vibfpga.known_board import parse_log
from vibfpga.known_fixed import integer_power, power_log_q12, prepare_windows, rne_shift, tables

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/known-recording-walkthrough'
RUN = ROOT / 'measurements/known-replay/id00-l4-record1-r1'
N, WINDOWS, FS = 1024, 156, 16000


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scalar_rne(value, bits):
    quotient, remainder = divmod(int(value), 1 << bits)
    half = 1 << (bits - 1)
    return quotient + int(remainder > half or (remainder == half and quotient % 2))


def write_csv(name, columns, rows):
    with (OUT / name).open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)


def save_figure(fig, name):
    fig.savefig(OUT / f'{name}.png', dpi=160, bbox_inches='tight')
    fig.savefig(OUT / f'{name}.svg', bbox_inches='tight')
    plt.close(fig)


def main():
    freeze_path = ROOT / 'artifacts/acoustic-known-deployment-v1/freeze.json'
    freeze = json.loads(freeze_path.read_text())
    assert all(sha(ROOT / p) == h for p, h in freeze['sha256'].items()), 'Frozen input changed'
    manifest = json.loads((RUN / 'manifest.json').read_text())
    assert manifest['status'] == 'passed' and manifest['physical_hardware']
    assert manifest['deployment_sha256'] == sha(freeze_path)
    record = manifest['record']
    assert record['role'] == 'cv', 'Only a development recording may be used'
    model_path = RUN / 'model.json'
    model = json.loads(model_path.read_text())
    assert sha(model_path) == manifest['model_sha256']
    raw_path = ROOT / record['local']
    assert sha(raw_path) == record['npy_sha256']
    raw = np.load(raw_path, allow_pickle=False)[:N * WINDOWS]
    image_path = RUN / 'input.bin'
    assert sha(image_path) == manifest['input_sha256']
    assert image_path.read_bytes()[64:] == raw.astype('<i2').tobytes()

    windowed, saturation = prepare_windows(raw[None, :])
    _, cosine, hann, coefficients = tables(N)
    shifted = rne_shift(raw.astype(np.int64).reshape(WINDOWS, N), 1)
    means = rne_shift(shifted.sum(axis=1), 10)
    centered = np.clip(shifted - means[:, None], -32768, 32767)
    acc_float = windowed.astype(np.float64) @ coefficients
    np.testing.assert_array_equal(acc_float, np.rint(acc_float))
    acc = acc_float.astype(np.int64)
    real, imag = np.split(rne_shift(acc, 8), 2, axis=1)
    power = rne_shift((real * real).astype(np.uint64) + (imag * imag).astype(np.uint64), 8)
    sums = np.cumsum(power, axis=0, dtype=np.uint64)
    total, stats = integer_power(raw[None, :])
    np.testing.assert_array_equal(total[0], sums[-1])
    logq = power_log_q12(total)[0]
    meanq = np.array(model['mean_q12'], dtype=np.int64)
    gainq = np.array(model['gain_q24'], dtype=np.int64)
    norm_product = (logq - meanq) * gainq
    qx = np.clip(rne_shift(norm_product, 24), -127, 127)
    weights = np.array(model['weights'], dtype=np.int64)
    products = qx * weights
    cumulative = model['bias'] + np.cumsum(products)
    score = int(cumulative[-1])
    assert -(1 << 31) <= cumulative.min() <= cumulative.max() < (1 << 31)

    # Existing regression stores the exact per-stage reference that RTL checked.
    report_path = ROOT / 'build/known-native/l4-1092-fixed16k-r2/report.json'
    report = json.loads(report_path.read_text())
    assert report['passed'] and all(sha(ROOT / p) == h for p, h in report['bindings'].items())
    clip_index = next(i for i, row in enumerate(report['records']) if row['name'] == record['name'])
    vector_path = report_path.parent / 'vectors.bin'
    fields = [(raw, '<i2'), (windowed, '<i2'), (real, '<i4'), (imag, '<i4'),
              (power, '<u8'), (sums, '<u8'), (logq, '<i4'), (qx, 'i1'), (np.array([score]), '<i4')]
    with vector_path.open('rb') as f:
        magic, n, windows, count, threshold = struct.unpack('<IIIIi', f.read(20))
        assert (magic, n, windows, count, threshold) == (0x3150534B, N, WINDOWS, 7, model['threshold'])
        size = sum(value.size * np.dtype(dtype).itemsize for value, dtype in fields)
        f.seek(20 + clip_index * size)
        for value, dtype in fields:
            saved = np.frombuffer(f.read(value.size * np.dtype(dtype).itemsize), dtype=dtype)
            np.testing.assert_array_equal(saved, value.ravel())

    log_path = RUN / 'result-log.bin'
    assert sha(log_path) == manifest['result_sha256']
    for name in manifest['read_consensus']:
        assert (RUN / name).read_bytes() == log_path.read_bytes()
    board = parse_log(log_path.read_bytes(), model_path.read_bytes(), lanes=4, period=750)
    assert board['score'] == score == manifest['expected_score']
    assert board == manifest['result']
    assert board['classification'] == int(score > model['threshold'])

    # Pick a positive contribution only for teaching, after choosing the record.
    # The deployed model still uses every bin; this does not select model features.
    j = int(np.argmax(products))
    k = j + 1
    phase = np.arange(N) * k % N
    re_terms = windowed[0] * cosine[phase]
    im_terms = windowed[0] * cosine[(phase + N // 4) % N]
    for test_k in sorted({1, 64, k, 512}):
        for component, offset in [(0, 0), (1, N // 4)]:
            exact = sum(int(windowed[0, t]) * int(cosine[(t * test_k + offset) % N]) for t in range(N))
            assert exact == int(acc[0, test_k - 1 + component * N // 2])
            assert scalar_rne(exact, 8) == int((real if component == 0 else imag)[0, test_k - 1])
    scalar_features = [max(-127, min(127, scalar_rne(int(logq[i] - meanq[i]) * int(gainq[i]), 24))) for i in range(N // 2)]
    np.testing.assert_array_equal(scalar_features, qx)
    assert sum(x * int(w) for x, w in zip(scalar_features, weights)) + model['bias'] == score

    OUT.mkdir(parents=True, exist_ok=True)
    write_csv('window-000.csv', ['sample', 'raw_pcm16', 'shifted_rne1', 'centered', 'hann_q15',
              'hann_product', 'windowed_rne15', 'selected_real_product', 'selected_imag_product'],
              zip(range(N), raw[:N], shifted[0], centered[0], hann, centered[0] * hann, windowed[0], re_terms, im_terms))
    frequencies = np.arange(1, N // 2 + 1) * FS / N
    write_csv('features-and-mac.csv', ['k', 'frequency_hz', 'first_window_real', 'first_window_imag',
              'first_window_power', 'power_sum_156', 'log_q12', 'mean_q12', 'gain_q24',
              'normalization_product', 'feature_int8', 'weight_int8', 'product', 'score_after_bin'],
              zip(range(1, 513), frequencies, real[0], imag[0], power[0], total[0], logq,
                  meanq, gainq, norm_product, qx, weights, products, cumulative))
    write_csv('selected-bin-across-windows.csv', ['window', 'real', 'imag', 'power', 'running_power_sum'],
              zip(range(WINDOWS), real[:, j], imag[:, j], power[:, j], sums[:, j]))

    plt.rcParams.update({'font.family': 'DejaVu Sans', 'axes.spines.top': False,
                         'axes.spines.right': False, 'axes.grid': True, 'grid.alpha': .18})
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), constrained_layout=True)
    blocks = raw.reshape(WINDOWS, N)
    t = (np.arange(WINDOWS) + .5) * N / FS
    axes[0].fill_between(t, blocks.min(1), blocks.max(1), color='#147d92', alpha=.65)
    axes[0].set(title='Recording: min/max envelope per 64 ms window (not every sample)', xlabel='Time (s)', ylabel='PCM counts')
    ms = np.arange(N) * 1000 / FS
    axes[1].plot(ms, raw[:N], lw=.8, color='#147d92')
    axes[1].set(title='Window 0: all 1,024 raw samples', xlabel='Time (ms)', ylabel='PCM counts')
    axes[2].plot(ms, centered[0], lw=.8, label='After input scaling and DC removal', alpha=.55)
    axes[2].plot(ms, windowed[0], lw=.9, label='After Q15 Hann window', color='#cf623c')
    axes[2].set(xlabel='Time (ms)', ylabel='Integer amplitude');axes[2].legend(loc='upper right')
    save_figure(fig, '01-waveform')

    fig, axes = plt.subplots(2, 1, figsize=(10, 6), constrained_layout=True)
    axes[0].plot(frequencies, power_log_q12(power[:1], frames=1)[0] / 4096, lw=.8, label='Window 0')
    axes[0].plot(frequencies, logq / 4096, lw=1, label='Power averaged over 156 windows, then log2')
    axes[0].axvline(frequencies[j], color='#cf623c', ls='--', label=f'Example: k={k}, {frequencies[j]:g} Hz')
    axes[0].set(xlabel='Frequency (Hz)', ylabel='log2 power (PCM-count units)', title='Full DFT: bins 1–512; no DC bin');axes[0].legend(fontsize=8)
    axes[1].plot(frequencies, qx, lw=.8, color='#147d92');axes[1].axhline(127, color='gray', ls=':');axes[1].axhline(-127, color='gray', ls=':')
    axes[1].set(xlabel='Frequency (Hz)', ylabel='INT8 feature', ylim=(-135, 135), title='Training normalization and symmetric quantization')
    save_figure(fig, '02-spectrum-features')

    fig, axes = plt.subplots(2, 1, figsize=(10, 6), constrained_layout=True)
    axes[0].bar(np.arange(1, 513), products, width=1, color=np.where(products >= 0, '#cf623c', '#147d92'))
    axes[0].set(xlabel='Frequency bin k', ylabel='feature × weight', title='Positive contributions raise the fault score; negative contributions lower it')
    axes[1].plot(np.arange(513), np.r_[model['bias'], cumulative], color='#147d92')
    axes[1].axhline(model['threshold'], ls='--', color='#cf623c', label=f'Threshold = {model["threshold"]}')
    axes[1].scatter([512], [score], color='#147d92');axes[1].annotate(f'Final = {score}', (512, score), xytext=(-100, 15), textcoords='offset points')
    axes[1].set(xlabel='Accumulated frequency bins', ylabel='INT32 score', title=f'Start at bias {model["bias"]}; emit once after all 156 windows');axes[1].legend()
    save_figure(fig, '03-mac-score')

    sample_index = 256
    example = dict(k=k, frequency_hz=float(frequencies[j]), first_real_acc=int(acc[0, j]),
        first_imag_acc=int(acc[0, j + 512]), first_real=int(real[0, j]), first_imag=int(imag[0, j]),
        first_power=int(power[0, j]), power_sum=int(total[0, j]), log_q12=int(logq[j]),
        mean_q12=int(meanq[j]), gain_q24=int(gainq[j]), norm_product=int(norm_product[j]),
        feature=int(qx[j]), weight=int(weights[j]), product=int(products[j]), score_after_bin=int(cumulative[j]))
    sample = dict(index=sample_index, raw=int(raw[sample_index]), shifted=int(shifted[0, sample_index]),
        mean=int(means[0]), centered=int(centered[0, sample_index]), hann=int(hann[sample_index]),
        hann_product=int(centered[0, sample_index] * hann[sample_index]), windowed=int(windowed[0, sample_index]))
    summary = dict(record=record, raw_samples=int(raw.size), window_count=WINDOWS, sample_rate_hz=FS,
        first_window_sum=int(shifted[0].sum()), first_window_mean=int(means[0]), selected_sample=sample,
        selected_bin=example, sum_products=int(products.sum()), bias=model['bias'], score=score,
        threshold=model['threshold'], score_margin=score-model['threshold'], board=board,
        feature_saturated=int(np.count_nonzero(np.abs(rne_shift(norm_product, 24)) > 127)),
        center_saturated=saturation, stats=stats, exact_vector_fields=len(fields),
        checks=dict(frozen_inputs=True, development_record=True, saved_rtl_vector_equal=True,
                    original_board_log_equal=True, scalar_checks=True),
        scope='New Python teaching trace; uses saved RTL and physical evidence. No new RTL run, USB, training or test-set evaluation.',
        source_sha256=sha(Path(__file__)),
        input_sha256={str(p.relative_to(ROOT)): sha(p) for p in [freeze_path, raw_path, model_path, RUN/'manifest.json',
                       image_path, log_path, report_path, vector_path]},
        output_sha256={p.name: sha(p) for p in sorted(OUT.iterdir()) if p.suffix in ('.csv', '.png', '.svg')})
    audio_records = []
    for title, run_name, audio_name in [('Normal recording', 'id00-l4-normal-r1', 'normal.wav'),
                                       ('Fault recording', RUN.name, 'fault.wav')]:
        directory = RUN.parent / run_name
        saved = json.loads((directory / 'manifest.json').read_text())
        assert saved['status'] == 'passed' and saved['physical_hardware']
        assert saved['deployment_sha256'] == sha(freeze_path) and saved['record']['role'] == 'cv'
        pcm_path = ROOT / saved['record']['local']
        assert sha(pcm_path) == saved['record']['npy_sha256']
        pcm = np.load(pcm_path, allow_pickle=False)[:N * WINDOWS].astype('<i2').tobytes()
        assert sha(directory / 'input.bin') == saved['input_sha256']
        assert (directory / 'input.bin').read_bytes()[64:] == pcm
        assert sha(directory / 'model.json') == saved['model_sha256'] == manifest['model_sha256']
        assert sha(directory / 'result-log.bin') == saved['result_sha256']
        for read_name in saved['read_consensus']:
            assert (directory / read_name).read_bytes() == (directory / 'result-log.bin').read_bytes()
        result = parse_log((directory / 'result-log.bin').read_bytes(), model_path.read_bytes(), lanes=4, period=750)
        assert result == saved['result']
        with wave.open(str(OUT / audio_name), 'wb') as audio:
            audio.setparams((1, 2, FS, N * WINDOWS, 'NONE', 'not compressed'))
            audio.writeframes(pcm)
        with wave.open(str(OUT / audio_name), 'rb') as audio:
            assert audio.readframes(N * WINDOWS) == pcm
        audio_records.append(dict(title=title, file=audio_name, source=saved['record']['name'],
            score=result['score'], threshold=result['threshold'], classification=result['classification'],
            run=run_name, recorded_at=saved['finished_utc'], duration_seconds=N*WINDOWS/FS,
            pcm_sha256=hashlib.sha256(pcm).hexdigest()))
        for p in [directory/'manifest.json', directory/'model.json', directory/'input.bin', directory/'result-log.bin', pcm_path]:
            summary['input_sha256'][str(p.relative_to(ROOT))] = sha(p)
    summary['audio'] = audio_records
    template = ROOT / 'docs/templates/known-recording-demo.html'
    page_data = dict(audio=audio_records, selected_bin=k, features=[dict(k=i+1, frequency=float(frequencies[i]),
        power_sum=str(int(total[0,i])), log_q12=int(logq[i]), mean_q12=int(meanq[i]), gain_q24=int(gainq[i]),
        feature=int(qx[i]), weight=int(weights[i]), product=int(products[i]), cumulative=int(cumulative[i])) for i in range(512)])
    (OUT / 'index.html').write_text(template.read_text().replace('__TRACE_DATA__', json.dumps(page_data, ensure_ascii=False).replace('<', '\\u003c')))
    summary['input_sha256'][str(template.relative_to(ROOT))] = sha(template)
    summary['output_sha256'].update({p.name:sha(p) for p in OUT.iterdir() if p.suffix in ('.html', '.wav')})
    (OUT/'trace.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps({k:summary[k] for k in ('score','threshold','selected_sample','selected_bin','checks')}, ensure_ascii=False))


if __name__ == '__main__':
    with threadpool_limits(limits=2):
        main()
