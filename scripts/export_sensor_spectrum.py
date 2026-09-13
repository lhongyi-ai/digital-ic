#!/usr/bin/env python3
"""Generate N256 DSP coefficients and inert zero NN parameters, not a classifier."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from vibfpga.export import export_model


def main():
    model={"schema_version":1,"training_status":"not_a_classifier_DSP_coefficient_profile",
        "n":256,"bins":[1,2,3,4,5,8,12,16,24,32,40,48,64,80,96,120],
        "feature_shifts":[0]*16,"input_shift":5,"dft_shift":18,"hidden_shift":0,
        "w1":[[0]*16 for _ in range(16)],"b1":[0]*16,"w2":[[0]*16 for _ in range(3)],"b2":[0]*3,
        "intended_output":"16 selected DFT-bin powers only; NN outputs disconnected",
        "sensor_input_transform":"clamp raw counts to [-1024,1023], multiply by 32 in signed16",
        "power_units":"squared fixed-point DFT coefficient units; not calibrated physical PSD",
        "physical_sensor_measured":False,"not_for_classification":True}
    target=ROOT/"artifacts/sensor_spectrum/model"
    export_model(model,target)
    print(target)


if __name__=="__main__":main()
