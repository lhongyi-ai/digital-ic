# AUC=1 and Overfitting Checks

AUC=1 means only that fault scores exceed normal scores in these finite validation recordings. A fixed threshold may still yield false positives. It neither proves overfitting nor establishes field generalization. The checks below kept the final test reserved and did not modify the model.

|Machine|Mean three-fold training AUC|Mean three-fold validation AUC|Mean AUC across 40 label shuffles|Range of shuffled mean AUC|
|---|---:|---:|---:|---|
|00|1.00000|0.98828|0.49144|0.38737–0.61068|
|02|1.00000|1.00000|0.51124|0.36035–0.60775|
|04|1.00000|1.00000|0.48309|0.34505–0.59147|
|06|1.00000|1.00000|0.49813|0.37858–0.63314|

The 40 controls shuffle labels within each machine and CV fold, using shuffled labels for both training and validation. Spectral inputs contain neither filenames nor labels, and normalization uses only the training fold. Near-random control performance supports an association between labels and sound being used by the model, but does not prove that the association is the physical fault mechanism.

Remaining limitations: repeated use of development data for approach selection risks adaptively optimistic scores; recordings from the same rig and machine may share acquisition conditions; near-duplicate screening does not establish session independence; four fans and a single noise condition do not represent unfamiliar models or field environments.

Tail counts from 40 Monte Carlo runs are development diagnostics only. They have limited resolution and do not cover the preceding adaptive model-selection process; they are not independent significance evidence or proof against overfitting.

Final confirmation has since completed: after freezing the model, integer algorithm, RTL, and thresholds, the 720 reserved recordings were evaluated only once. Every machine and the pooled result passed the original gates; pooled AUC is 0.99841. Splits, models, thresholds, and success criteria were not changed against test results. Per-recording scores and grouped metrics passed 725 review checks. See [final test results](known-final-test.md).

A shuffled-label AUC near 0.5 is not a reason to retrain. Passing the reserved test increases confidence in new recordings from the same source, but cannot rule out background cues from shared acquisition conditions. It does not prove acquisition-session independence or real field generalization.
