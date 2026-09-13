"""Frozen multi-machine split and source-only threshold rules."""
import hashlib
import numpy as np
from vibfpga.acoustic_experiment import normal_threshold

def stable_order(name):return hashlib.sha256(('multimachine-v1:'+name).encode()).hexdigest()

def validate_plan(plan):
    rows=plan['records'];names=[r['name'] for r in rows]
    if len(names)!=len(set(names)) or set(names)&set(plan['excluded_old_test']):raise ValueError('duplicate or old test reuse')
    for r in rows:
        if r['machine'] not in ('00','02','04','06') or r['label'] not in (0,1):raise ValueError('invalid record')
        if r['machine']=='06' and r['role']!='final_test':raise ValueError('06 cannot enter development')
        if r['machine']!='06' and r['role'] not in ('fit','calibration'):raise ValueError('invalid development role')
        state='abnormal' if r['label'] else 'normal'
        if not r['name'].startswith(f"fan/id_{r['machine']}/{state}/"):raise ValueError('identity mismatch')
    for machine in ('00','02','04'):
        for label in (0,1):
            counts={role:sum(r['machine']==machine and r['label']==label and r['role']==role for r in rows) for role in ('fit','calibration')}
            if counts!={'fit':128,'calibration':32}:raise ValueError('development counts changed')
    for label in (0,1):
        if sum(r['machine']=='06' and r['label']==label for r in rows)!=80:raise ValueError('test counts changed')

def folds(rows):
    if any(r['machine']=='06' for r in rows):raise ValueError('final test cannot enter folding')
    for held in ('00','02','04'):
        fit=np.array([i for i,r in enumerate(rows) if r['machine']!=held and r['role']=='fit'])
        cal=np.array([i for i,r in enumerate(rows) if r['machine']!=held and r['role']=='calibration'])
        val=np.array([i for i,r in enumerate(rows) if r['machine']==held])
        if set(fit)&set(cal) or set(fit)&set(val) or set(cal)&set(val):raise ValueError('fold leakage')
        yield held,fit,cal,val

def source_threshold(scores,labels,machines):
    thresholds=[normal_threshold(np.asarray(scores)[(np.asarray(labels)==0)&(np.asarray(machines)==m)]) for m in sorted(set(machines))]
    return max(thresholds)

def violation(row):
    return max(0,row['fpr']-.05)/.05+max(0,.9-row['recall'])/.9+max(0,.9-row['auc'])/.9
