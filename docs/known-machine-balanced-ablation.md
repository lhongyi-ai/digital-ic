# Balanced Bin Selection: Fixed-MLP Three-Fold Ablation

Conclusion: balanced bins improve development results, but none of the four approaches meets acceptance for every machine. This iteration stopped as agreed without adding independent-model experiments.

- Keep the shared-threshold rule and change only bin selection: pooled detection 22.66%→80.47%, false positives 0%→2.60%, AUC 0.96033→0.97255. Threshold values are recomputed with the same calibration rule, rather than retaining the old numeric threshold.
- Keep old bins and change only threshold policy: pooled detection 22.66%→76.56%, false positives 0%→4.43%.
- Keep balanced bins and change only threshold policy: pooled detection 80.47%→90.89%, false positives 2.60%→8.33%. Threshold changes do not change AUC.
- Machine 00 improves from AUC 0.81413 to 0.89095 and detection 14/96→67/96, but has 8/96 false positives. Separability improves without meeting the gates. Not all detection improvement can be attributed to ranking: the threshold also changes with calibration scores.
- Machine 04 alone passes with balanced bins plus a shared threshold. Overall acceptance requires every machine; reporting only this machine would be selective.

Review: 23 check groups passed, covering saved-model reload, reconstruction of training-fold bins/normalization, both threshold policies, and independent sklearn metric recomputation; see audit.json. These are development observations at this iteration's fixed seed, not independent test conclusions, and multiseed variance was not measured.

Only training-set bin selection changed: divide each machine's Fisher vector by its sum, then add the vectors. Dimensions (32), network, seed, 100 training epochs, splits, and calibration data remain unchanged. Old-model scores were reused; this iteration performed only three fits.

The table gives development out-of-fold counts; AUC is the mean across three folds. Each machine has 96 normals and 96 anomalies, totaling 384 normals and 384 anomalies. Thresholds use only independent normal calibration recordings and were not selected against validation labels.

|Bins|Threshold|Machine|Detected TP|False positives FP|AUC|Pass|
|---|---|---|---|---|---|---|
|baseline|common|00|14/96 (14.58%)|0/96 (0.00%)|0.81413|False|
|baseline|common|02|23/96 (23.96%)|0/96 (0.00%)|0.98958|False|
|baseline|common|04|38/96 (39.58%)|0/96 (0.00%)|0.99512|False|
|baseline|common|06|12/96 (12.50%)|0/96 (0.00%)|0.98958|False|
|baseline|common|pooled|87/384 (22.66%)|0/384 (0.00%)|0.96033|False|
|baseline|per_machine|00|14/96 (14.58%)|0/96 (0.00%)|0.81413|False|
|baseline|per_machine|02|93/96 (96.88%)|4/96 (4.17%)|0.98958|True|
|baseline|per_machine|04|94/96 (97.92%)|5/96 (5.21%)|0.99512|False|
|baseline|per_machine|06|93/96 (96.88%)|8/96 (8.33%)|0.98958|False|
|baseline|per_machine|pooled|294/384 (76.56%)|17/384 (4.43%)|0.96033|False|
|balanced|common|00|67/96 (69.79%)|8/96 (8.33%)|0.89095|False|
|balanced|common|02|79/96 (82.29%)|0/96 (0.00%)|0.98112|False|
|balanced|common|04|91/96 (94.79%)|2/96 (2.08%)|0.99577|True|
|balanced|common|06|72/96 (75.00%)|0/96 (0.00%)|0.99772|False|
|balanced|common|pooled|309/384 (80.47%)|10/384 (2.60%)|0.97255|False|
|balanced|per_machine|00|67/96 (69.79%)|8/96 (8.33%)|0.89095|False|
|balanced|per_machine|02|92/96 (95.83%)|8/96 (8.33%)|0.98112|False|
|balanced|per_machine|04|95/96 (98.96%)|6/96 (6.25%)|0.99577|False|
|balanced|per_machine|06|95/96 (98.96%)|10/96 (10.42%)|0.99772|False|
|balanced|per_machine|pooled|349/384 (90.89%)|32/384 (8.33%)|0.97255|False|


## Separating the Gains of the Two Changes (Percentage Points)

|Machine|Balanced-bin gain: shared threshold Δdetection/Δfalse positives/ΔAUC|Balanced-bin gain: per-machine threshold Δdetection/Δfalse positives/ΔAUC|
|---|---|---|
|00|+55.21/+8.33/+7.68|+55.21/+8.33/+7.68|
|02|+58.33/+0.00/-0.85|-1.04/+4.17/-0.85|
|04|+55.21/+2.08/+0.07|+1.04/+1.04/+0.07|
|06|+62.50/+0.00/+0.81|+2.08/+2.08/+0.81|
|pooled|+57.81/+2.60/+1.22|+14.32/+3.91/+1.22|

Every machine and the pooled result still require recall>90%, FPR<5%, and AUC≥0.9. Per-machine thresholds require a configured machine ID at deployment and do not establish generalization to unknown machines. Both bin selections report both threshold policies; no candidates were added after observing results.

The final 720 test recordings remained reserved in this iteration. Only development power caches and existing scores were read; no raw audio was opened. No quantization, RTL changes, or programming occurred. Acquisition-session independence remains unproven.

Evidence: `artifacts/acoustic-known-balanced-v1/{protocol,results,audit}.json`; script `scripts/experiment_known_machine_balanced.py`.
