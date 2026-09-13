# Final Test on 720 Recordings After Freezing

Each machine contributes 100 normal and 80 fault recordings. Neither models nor thresholds were adjusted against test results.

|Machine|Detected|False positives|AUC|Pass|
|---|---|---|---|---|
|00|77/80 (96.25%)|3/100 (3.00%)|0.99250|True|
|02|80/80 (100.00%)|1/100 (1.00%)|1.00000|True|
|04|80/80 (100.00%)|1/100 (1.00%)|1.00000|True|
|06|80/80 (100.00%)|3/100 (3.00%)|0.99975|True|
|pooled|317/320 (99.06%)|8/400 (2.00%)|0.99841|True|

Recording-level 95% binomial intervals are saved in results.json and depend on independent recordings; unverified acquisition-session relationships limit their interpretation.
This result supports only new recordings from covered devices and the same public data source. It does not establish generalization to unfamiliar fans or field environments. AUC=1 does not automatically indicate overfitting and cannot exclude background cues.

Per-recording integer scores and grouped metrics passed 725 review checks. Model and RTL were frozen in `artifacts/acoustic-known-deployment-v1/freeze.json`.
This report is final software evaluation; matching-version physical-board results are in the [physical replay report](known-hardware-results.md).
