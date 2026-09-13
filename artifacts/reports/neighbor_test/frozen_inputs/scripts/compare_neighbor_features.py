#!/usr/bin/env python3
"""Predefined k-1/k/k+1 feature comparison, TRAIN/VALIDATION ONLY.

The original frozen single-bin model and all held-out test artifacts remain
unchanged. Candidate promotion here means eligible for an RTL resource/timing
experiment, not deployment or a new held-out test result.
"""
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from vibfpga.dataset import load_windows
from vibfpga.export import export_model,export_vectors
from vibfpga.fixed import quantize_features
from vibfpga.training import candidate_bins,float_spectrum,fit_mlp,float_features,feature_shifts,int_powers,make_integer_model,metrics,predict_float,predict_integer


def main():
    started=time.time()
    base_path=ROOT/"artifacts/model/model.json"
    original_bytes=base_path.read_bytes()
    base=json.loads(original_bytes)
    report_path=ROOT/"artifacts/reports/neighbor_comparison.json"
    if report_path.exists():
        raise RuntimeError("Neighbor experiment already exists; preserve its predefined validation result instead of silently repeating selection")
    data=ROOT/"data/cwru"
    train,ty,tm,_=load_windows(data,"train",base["raw_scale"],1024)
    val,vy,vm,_=load_windows(data,"validation",base["raw_scale"],1024)
    # Predefined Fisher algorithm recomputed strictly from TRAIN. Do not inherit
    # the historical v1 validation-based choice among feature strategies.
    centers=candidate_bins(float_spectrum(train),ty,1024)[0]["train_fisher_separated"]
    assert centers==base["bins"],"Predefined train-only centers differ from historical v1; do not silently change comparison"
    expanded=[k+offset for k in centers for offset in (-1,0,1)]
    print(f"48 fixed-coefficient DFT bins -> 16 neighbor-energy features; TRAIN={len(train)}, VALIDATION={len(val)}; no TEST loaded",flush=True)
    tp=int_powers(train,expanded,1024).reshape(-1,16,3).sum(axis=2,dtype=np.int64)
    vp=int_powers(val,expanded,1024).reshape(-1,16,3).sum(axis=2,dtype=np.int64)
    shifts=feature_shifts(tp)
    tx,vx=float_features(tp,shifts),float_features(vp,shifts)
    torch.set_num_threads(2)
    mlp,history=fit_mlp(tx,ty,vx,vy,epochs=450,seed=7)
    config={k:base[k] for k in ("n","input_shift","dft_shift","class_names","sample_rate_hz","raw_scale")}
    config.update({"schema_version":1,"training_status":"trained_on_official_cwru_train_validation_only_candidate",
        "feature_mode":"neighbor3_energy","bins":centers,"dft_bins":expanded,"neighbor_offsets":[-1,0,1],
        "feature_shifts":shifts,"feature_energy_accumulator_bits":34,
        "data_provenance":{**base["data_provenance"],"quantization_method":"PTQ",
            "base_single_bin_model_sha256":hashlib.sha256(original_bytes).hexdigest(),
            "experiment":"predefined same centers k-1/k/k+1 energy, train/validation only",
            "frequency_selection_method":"predefined train_fisher_separated algorithm recomputed from train waveforms only"},
        "deployment_status":"candidate only; requires matching 48-bin RTL plus resource/timing validation",
        "test_evaluated":False,"physical_board_tested":False})
    integer=make_integer_model(mlp,tx,config)
    float_val=metrics(vy,predict_float(mlp,vx))
    fixed_val=metrics(vy,predict_integer(integer,quantize_features(vp,shifts))[0])
    old_float=base["validation_metrics"]["floating_mlp"]
    old_fixed=base["validation_metrics"]["deployed_integer"]
    delta=100*(float_val["macro_f1"]-old_float["macro_f1"])
    fixed_delta=100*(fixed_val["macro_f1"]-old_fixed["macro_f1"])
    drop=100*(float_val["accuracy"]-fixed_val["accuracy"])
    eligible=delta>=2 and drop<=2
    report={"schema_version":1,"experiment":"selected center +/-1 three-bin power sum",
        "test_evaluated":False,"original_frozen_model_sha256":hashlib.sha256(original_bytes).hexdigest(),
        "centers":centers,"dft_bins":expanded,"feature_shifts":shifts,"energy_accumulator_bits":34,
        "frequency_selection_method":"predefined train_fisher_separated algorithm recomputed from train waveforms only",
        "centers_equal_historical_v1":True,
        "train_windows":len(train),"validation_windows":len(val),
        "baseline_single_bin_float_validation":old_float,"baseline_single_bin_integer_validation":old_fixed,
        "neighbor_float_validation":float_val,"neighbor_integer_validation":fixed_val,
        "float_macro_f1_delta_percentage_points":delta,"integer_macro_f1_delta_percentage_points":fixed_delta,
        "PTQ_accuracy_drop_percentage_points":drop,
        "gate":"float validation macro-F1 improvement >=2 percentage points AND PTQ validation accuracy loss <=2 percentage points",
        "eligible_for_RTL_resource_timing_experiment":eligible,"candidate_exported":eligible,
        "training_history":history,"seconds":time.time()-started,
        "scope":"Predefined train/validation ablation; no new held-out test accuracy, FPGA fit or physical measurement claim"}
    integer["validation_metrics"]={"floating_mlp":float_val,"deployed_integer":fixed_val,
        "PTQ_accuracy_drop_percentage_points":drop,"test_evaluated":False}
    if eligible:
        output=ROOT/"artifacts/model_neighbor"
        export_model(integer,output)
        torch.save(mlp.state_dict(),output/"float_model.pt")
        np.savez_compressed(output/"float_parameters.npz",**{k:v.detach().numpy() for k,v in mlp.state_dict().items()})
        chosen=[next(i for i,m in enumerate(vm) if m["record_id"]==r and m["window_index"]==2)
                for r in sorted({m["record_id"] for m in vm})]
        export_vectors(integer,val[chosen],[vm[i] for i in chosen],ROOT/"artifacts/vectors_neighbor")
        report["candidate_model_sha256"]=hashlib.sha256((output/"model.json").read_bytes()).hexdigest()
    assert base_path.read_bytes()==original_bytes,"Original model changed during experiment"
    report_path.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:report[k] for k in ("neighbor_float_validation","neighbor_integer_validation",
        "float_macro_f1_delta_percentage_points","integer_macro_f1_delta_percentage_points",
        "PTQ_accuracy_drop_percentage_points","eligible_for_RTL_resource_timing_experiment")},indent=2),flush=True)


if __name__=="__main__":main()
