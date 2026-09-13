#!/usr/bin/env python3
"""Diagnose layout-sensitive float32 reduction without retraining or test access."""
from pathlib import Path
import json
import numpy as np
import torch
from train_multimachine_cnn_v2 import Net,patches,predict
from vibfpga.multimachine import folds
from experiment_acoustic_v2 import sha,dump
from audit_multimachine import manual_metrics
ROOT=Path(__file__).resolve().parents[1]
def main():
    torch.set_num_threads(2);torch.use_deterministic_algorithms(True)
    out=ROOT/'artifacts/acoustic-cnn-v2';binding=json.loads((out/'bindings.json').read_text());assert all(sha(ROOT/p)==h for p,h in binding['sha256'].items())
    rows=[r for r in json.loads((ROOT/'data/mimii-multimachine/plan.json').read_text())['records'] if r['machine'] in ('00','02','04')];y=np.array([r['label'] for r in rows])
    raw=np.load(out/'patches.npy');dummy=np.stack([patches(np.arange(160000,dtype=np.int16))]*2)
    original_layout=np.ascontiguousarray(raw.transpose(0,1,3,2)).transpose(0,1,3,2)
    assert dummy.strides[1:]==original_layout.strides[1:]
    result=json.loads((out/'results.json').read_text());checks=[]
    for c in result['candidates']:
        arrays=[]
        for a in (raw,original_layout):
            x=a-a.mean(axis=(2,3),keepdims=True)
            if c['name']=='timecenter':x=x-x.mean(axis=3,keepdims=True)
            arrays.append(np.ascontiguousarray(x/4,dtype=np.float32))
        for saved,(held,fit,cal,val) in zip(c['folds'],folds(rows)):
            model=Net();model.load_state_dict(torch.load(out/(c['name']+'-'+held+'.pt'),weights_only=True))
            flat=predict(model,arrays[0][val]);recovered=predict(model,arrays[1][val]);fs=predict(model,arrays[1][fit]);ss=np.array(saved['validation_scores']);t=saved['threshold']
            checks.append({'representation':c['name'],'held':held,'fit_auc':manual_metrics(y[fit],fs,t)['auc'],
              'saved_layout_max_error':float(np.max(np.abs(flat-ss))),'original_layout_max_error':float(np.max(np.abs(recovered-ss))),
              'saved_layout_decision_changes':int(np.sum((flat>t)!=(ss>t))),'original_layout_decision_changes':int(np.sum((recovered>t)!=(ss>t))),
              'fit_loss_first':saved['training_loss'][0],'fit_loss_last':saved['training_loss'][-1]})
    target=out/'layout-diagnostic.json';assert not target.exists()
    dump(target,{'source_sha256':sha(Path(__file__)),'binding_sha256':sha(out/'bindings.json'),'dummy_original_strides':dummy.strides,'saved_strides':raw.strides,'test_opened':False,'checks':checks})
    print(json.dumps(checks,indent=2))
if __name__=='__main__':main()
