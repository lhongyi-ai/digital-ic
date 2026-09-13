#!/usr/bin/env python3
"""One bounded ablation: equal-total Fisher selection, three unchanged MLP fits."""
import json
from pathlib import Path
import numpy as np
import torch
from torch import nn
from threadpoolctl import threadpool_limits
from experiment_acoustic_v2 import dump, sha
from train_known_machine_models import frontend, passed, select_bands
from audit_known_machine_results import auc

ROOT = Path(__file__).resolve().parents[1]
IDS = ('00', '02', '04', '06')

def balanced(power, y, machine):
    log = np.log2(np.maximum(power[:, :-2]+power[:, 1:-1]+power[:, 2:], 1e-12))
    scores = []
    for m in IDS:
        a, b = log[(machine == m)&(y == 0)], log[(machine == m)&(y == 1)]
        f = (a.mean(0)-b.mean(0))**2/(a.var(0)+b.var(0)+1e-6)
        scores.append(f/max(float(f.sum()), 1e-12))
    combined = np.sum(scores, axis=0)
    chosen = []
    for i in np.lexsort((np.arange(510), -combined)):
        if all(abs(int(i)-j) >= 3 for j in chosen):
            chosen.append(int(i))
        if len(chosen) == 32:
            break
    return np.array(sorted(chosen))+2

def evaluate(folds, rows, policy):
    y = np.array([r['label'] for r in rows]); machine = np.array([r['machine'] for r in rows])
    votes = np.zeros(len(rows), int); decisions = np.zeros(len(rows), bool)
    areas = {m: [] for m in (*IDS, 'pooled')}; details = []
    for f in folds:
        fit = np.array(f['fit_indices']); val = np.array(f['validation_indices']); cal = np.array(f['calibration_indices'])
        assert not set(fit)&set(val) and not set(fit)&set(cal) and not set(val)&set(cal)
        assert all(rows[i]['role'] == 'cv' and rows[i]['fold'] == f['fold'] for i in val)
        assert all(rows[i]['role'] == 'calibration' for i in cal)
        s = np.array(f['validation_scores']); cs = np.array(f['calibration_scores'])
        limits = {m: float(np.sort(cs[(machine[cal] == m)&(y[cal] == 0)])[-2]) for m in IDS}
        threshold = np.array([max(limits.values()) if policy == 'common' else limits[m] for m in machine[val]])
        decisions[val] = s > threshold; votes[val] += 1
        groups = {}
        for m in areas:
            mask = np.ones(len(val), bool) if m == 'pooled' else machine[val] == m
            t = y[val][mask]; p = decisions[val][mask]
            area = auc(t, s[mask]); areas[m].append(area)
            groups[m] = dict(tp=int(p[t == 1].sum()), fp=int(p[t == 0].sum()), auc=area)
        details.append(dict(fold=f['fold'], thresholds=limits, groups=groups))
    assert all(votes[i] == int(r['role'] == 'cv') for i, r in enumerate(rows))
    groups = {}
    for m in areas:
        mask = (votes == 1)&(True if m == 'pooled' else machine == m)
        t, p = y[mask], decisions[mask]
        tp, fp = int(p[t == 1].sum()), int(p[t == 0].sum())
        n, a = int((t == 0).sum()), int((t == 1).sum())
        g = dict(tp=tp, fp=fp, normal=n, abnormal=a, recall=tp/a, fpr=fp/n, auc=float(np.mean(areas[m])))
        g['passed'] = passed(g); groups[m] = g
    return dict(groups=groups, folds=details, passed=all(g['passed'] for g in groups.values()))

def main():
    old = ROOT/'artifacts/acoustic-known-machines-v1'
    base = ROOT/'data/mimii-known-machines-v1'
    previous = json.loads((old/'results.json').read_text())
    audit = json.loads((old/'audit.json').read_text()); protocol = json.loads((old/'protocol.json').read_text())
    assert audit['passed'] and audit['results_sha256'] == sha(old/'results.json')
    assert audit['protocol_sha256'] == sha(old/'protocol.json')
    assert protocol['source_sha256'] == sha(ROOT/'scripts/train_known_machine_models.py')
    assert protocol['plan_sha256'] == sha(base/'plan.json') == json.loads((base/'freeze.json').read_text())['plan_sha256']
    rows = previous['records']; assert rows == json.loads((base/'development.json').read_text())['records']
    assert len(rows) == 1024 and not any(r['role'] == 'final_test' for r in rows)
    power = np.load(old/'development-power.npy', allow_pickle=False)
    assert power.shape == (1024, 512) and np.isfinite(power).all()
    y = np.array([r['label'] for r in rows]); machine = np.array([r['machine'] for r in rows])
    baseline = [f for f in previous['folds'] if f['model'] == 'mlp']
    assert len(baseline) == 3
    out = ROOT/'artifacts/acoustic-known-balanced-v1'; out.mkdir(exist_ok=False)
    dump(out/'protocol.json', dict(source_sha256=sha(Path(__file__)),
        baseline_results_sha256=sha(old/'results.json'), baseline_protocol_sha256=sha(old/'protocol.json'),
        cached_power_sha256=sha(old/'development-power.npy'), plan_sha256=sha(base/'plan.json'),
        selection='Each machine training Fisher vector divided by its sum (floor1e-12), then summed; unchanged greedy32 spacing3',
        training='MLP32-16-ReLU-1 Adam .001 batch64 epochs100 seed71; fixed last epoch; exactly3fits',
        threshold='Second highest of32 calibration normals per ID; common=max of4, per_machine=configured ID',
        scope='Development ablation only; no final audio, quantization, RTL or flashing', final_test_opened=False))
    folds = []
    for original in baseline:
        fold = original['fold']; fit = np.array(original['fit_indices']); val = np.array(original['validation_indices']); cal = np.array(original['calibration_indices'])
        np.testing.assert_array_equal(select_bands(power[fit], y[fit], machine[fit]), original['bins'])
        raw_old = frontend(power, np.array(original['bins']))
        np.testing.assert_array_equal(raw_old[fit].mean(0), original['mean'])
        np.testing.assert_array_equal(np.maximum(raw_old[fit].std(0), 1e-6), original['std'])
        bins = balanced(power[fit], y[fit], machine[fit]); raw = frontend(power, bins)
        mean = raw[fit].mean(0); std = np.maximum(raw[fit].std(0), 1e-6)
        z = ((raw-mean)/std).astype(np.float32)
        torch.manual_seed(71); model = nn.Sequential(nn.Linear(32,16), nn.ReLU(), nn.Linear(16,1))
        optimizer = torch.optim.Adam(model.parameters(), lr=.001)
        x = torch.from_numpy(z[fit]); target = torch.tensor(y[fit], dtype=torch.float32); losses = []
        for epoch in range(100):
            total = 0.
            for ids in torch.randperm(len(fit)).split(64):
                optimizer.zero_grad(); loss = nn.functional.binary_cross_entropy_with_logits(model(x[ids]).flatten(), target[ids])
                assert torch.isfinite(loss); loss.backward(); optimizer.step(); total += float(loss.detach())*len(ids)
            losses.append(total/len(fit))
        model.eval()
        with torch.no_grad(): score = model(torch.from_numpy(z)).flatten().numpy().astype(float)
        torch.save(model.state_dict(), out/f'mlp-fold{fold}.pt')
        restored = nn.Sequential(nn.Linear(32,16), nn.ReLU(), nn.Linear(16,1))
        restored.load_state_dict(torch.load(out/f'mlp-fold{fold}.pt', weights_only=True)); restored.eval()
        with torch.no_grad(): np.testing.assert_array_equal(score, restored(torch.from_numpy(z)).flatten().numpy().astype(float))
        folds.append(dict(model='mlp', fold=fold, bins=bins.tolist(), mean=mean.tolist(), std=std.tolist(),
            fit_indices=fit.tolist(), validation_indices=val.tolist(), calibration_indices=cal.tolist(),
            training_loss=losses, validation_scores=score[val].tolist(), calibration_scores=score[cal].tolist()))
        print('completed fold', fold, 'last loss', losses[-1], flush=True)
    comparison = {name: {policy: evaluate(fs, rows, policy) for policy in ('common','per_machine')}
                  for name, fs in (('baseline', baseline), ('balanced', folds))}
    for m, g in comparison['baseline']['common']['groups'].items():
        for key in ('recall','fpr','auc','passed'):
            assert g[key] == previous['summary']['mlp']['groups'][m][key]
    dump(out/'results.json', dict(folds=folds, comparison=comparison, records=rows, final_test_opened=False))
    lines = ['# Balanced frequency selection: three-fold ablation with a fixed MLP', '',
        'Only frequency selection within the training set changes: each machine Fisher vector is divided by its sum, then the vectors are added. The 32 dimensions, network, seed, 100 training epochs, splits, and calibration data are unchanged. Saved scores are reused for the old model; this round performs only three fits.', '',
        'The table reports development OOF counts; AUC is the mean across three folds. Each machine has 96 normal and 96 abnormal recordings; pooled totals are 384 normal and 384 abnormal. Thresholds use only independent normal calibration recordings, not validation labels.', '',
        '|Frequency selection|Threshold|Machine|Detected TP|False alarms FP|AUC|Passed|', '|---|---|---|---|---|---|---|']
    for name, policies in comparison.items():
        for policy, result in policies.items():
            for m,g in result['groups'].items():
                lines.append(f"|{name}|{policy}|{m}|{g['tp']}/{g['abnormal']} ({g['recall']:.2%})|{g['fp']}/{g['normal']} ({g['fpr']:.2%})|{g['auc']:.5f}|{g['passed']}|")
    lines += ['', '## Separating the benefits of two changes (percentage points)', '', '|Machine|Balanced bins with shared threshold: delta recall/FPR/AUC|Balanced bins with independent thresholds: delta recall/FPR/AUC|', '|---|---|---|']
    for m in (*IDS,'pooled'):
        cells=[]
        for policy in ('common','per_machine'):
            a=comparison['baseline'][policy]['groups'][m]; b=comparison['balanced'][policy]['groups'][m]
            cells.append('/'.join(f"{100*(b[k]-a[k]):+.2f}" for k in ('recall','fpr','auc')))
        lines.append(f"|{m}|{cells[0]}|{cells[1]}|")
    lines += ['', 'Every machine and the pooled set still require recall>90%, FPR<5%, and AUC>=0.9. Independent thresholds require a machine ID at deployment and do not establish generalization to unknown machines. Both threshold methods are reported for both frequency-selection methods; no candidates were added after viewing results.', '',
        'The final 720 test recordings remained sealed in this round. Only cached development powers and saved scores were read; no raw audio was opened. No quantization, RTL changes, or programming occurred. Independence of acquisition batches remains unproven.', '',
        'Evidence: artifacts/acoustic-known-balanced-v1/{protocol,results,audit}.json; script: scripts/experiment_known_machine_balanced.py.']
    (ROOT/'docs/known-machine-balanced-ablation.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({n:{p:r['passed'] for p,r in v.items()} for n,v in comparison.items()}), flush=True)

if __name__ == '__main__':
    torch.set_num_threads(2)
    with threadpool_limits(limits=2): main()
