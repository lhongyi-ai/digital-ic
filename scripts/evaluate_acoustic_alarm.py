#!/usr/bin/env python3
"""Evaluate the already frozen temporal rule on validation only; no threshold selection."""
import json,hashlib
from pathlib import Path
import numpy as np
from vibfpga.acoustic import features_from_powers,Alarm
from vibfpga.fixed import round_shift_even
ROOT=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
out=ROOT/'artifacts/acoustic';freeze=json.loads((out/'frozen.json').read_text())
for rel,h in freeze['sha256'].items():
    if sha((ROOT/rel).read_bytes())!=h:raise ValueError('frozen artifact changed')
m=json.loads((out/'model/model.json').read_text());plan=json.loads((ROOT/'data/mimii/plan.json').read_text())
items=[r for r in plan['records'] if r['split']=='validation'];frames=[]
for row in items:
    p=ROOT/'data/mimii'/row['local'];receipt=json.loads(p.with_suffix('.json').read_text())
    if sha(p.read_bytes())!=receipt['npy_sha256']:raise ValueError('PCM changed')
    x=np.load(p);frames.append(x[:len(x)//1024*1024].reshape(-1,1024))
frames=np.stack(frames)
kind=json.loads((out/'validation.json').read_text())['selected']['name'].split('-')[0]
c=np.load(ROOT/f'build/acoustic-powers-{kind}-validation.npz')
if str(c['key'])!=sha(frames.tobytes()+np.array(m['bins']).tobytes()+b'input_shift=0;N=1024'):raise ValueError('cache input binding mismatch')
x=features_from_powers(c['powers'],m);flat=x.reshape(-1,16)
h=np.clip(round_shift_even(np.maximum(flat@np.array(m['w1']).T+m['b1'],0),m['hidden_shift']),0,127)
y=np.clip(round_shift_even(h@np.array(m['w2']).T+m['b2'],m['output_shift']),0,127)
scores=((flat-y)**2).sum(1).reshape(x.shape[:-1]);counts=np.zeros((2,2),dtype=int);records=[]
for item,ss in zip(items,scores):
    rule=Alarm(m['threshold'],m['alarm_windows']);hits=[i for i,s in enumerate(ss) if rule.accept(i,int(s))]
    flag=bool(hits);counts[item['label'],int(flag)]+=1
    records.append({'record':item['name'],'label':item['label'],'alarm':flag,'first_alarm_window':hits[0] if hits else None})
r={'scope':'Validation only: any K-consecutive-window alarm within each complete recording; reset at recording boundary. This is separate from mean-score clip ROC.',
   'frozen_sha256':sha((out/'frozen.json').read_bytes()),'window_threshold':m['threshold'],'consecutive_windows':m['alarm_windows'],
   'confusion_matrix':counts.tolist(),'fpr':float(counts[0,1]/counts[0].sum()),'recall':float(counts[1,1]/counts[1].sum()),'records':records}
(out/'validation-alarm.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='records'}))
