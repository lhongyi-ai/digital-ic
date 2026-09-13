#!/usr/bin/env python3
"""Render existing reports only; does not retrain or re-read test waveforms."""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

root = Path("artifacts/reports")
val = json.loads((root/"validation.json").read_text())
test = json.loads((root/"test_evaluation.json").read_text())
freq = json.loads((root/"frequency_comparison.json").read_text())
fig, axes = plt.subplots(1,3,figsize=(16,4.7),layout="constrained")
fig.suptitle("CWRU 12 kHz drive-end benchmark | train loads 0/1, validation 2, test 3 HP",fontsize=14)
names = ["Uniform bins","Log-spaced bins","Train-selected bins","Band energy\n(offline only)"]
axes[0].barh(names,[100*r["mlp_validation"]["macro_f1"] for r in freq],color=["#93a4b8","#93a4b8","#197a8c","#d09c50"])
axes[0].set_xlim(0,100)
axes[0].set_xlabel("Validation macro-F1 (%)")
axes[0].set_title("Feature comparison before test access")
labels = ["RMS thresholds","Linear","Float MLP","INT8 MLP"]
keys = ["rms_three_leaf_threshold_baseline","linear","floating_mlp","deployed_integer"]
x = np.arange(4)
axes[1].bar(x-.18,[100*val[k]["accuracy"] for k in keys],width=.36,label="Validation",color="#8aa3b8")
axes[1].bar(x+.18,[100*test[k]["accuracy"] for k in keys],width=.36,label="Held-out test",color="#197a8c")
axes[1].set_xticks(x,labels,rotation=25,ha="right")
axes[1].set_ylim(0,100)
axes[1].set_ylabel("Window accuracy (%)")
axes[1].set_title("MLP does not beat the RMS baseline")
axes[1].legend(frameon=False)
cm = np.asarray(test["deployed_integer"]["confusion_matrix"])
axes[2].imshow(cm,cmap="Blues")
for i in range(3):
    for j in range(3):
        axes[2].text(j,i,str(cm[i,j]),ha="center",va="center",color="white" if cm[i,j]>250 else "#182333")
axes[2].set_xticks(range(3),["Inner","Outer","Ball"])
axes[2].set_yticks(range(3),["Inner","Outer","Ball"])
axes[2].set_xlabel("Predicted")
axes[2].set_ylabel("True")
axes[2].set_title("INT8 test confusion matrix\n1,070 windows from 9 records")
for ax in axes[:2]:
    ax.spines[["top","right"]].set_visible(False)
fig.savefig(root/"training_results.png",dpi=180)
fig.savefig(root/"training_results.svg")
plt.close(fig)
