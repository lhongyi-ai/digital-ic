# Additional Machine Data: Source Review and Development-Expansion Boundaries

The target remains unmet. This round read only official metadata and ZIP directories, without reading DUE audio or producing new training results.

## Original-data limitations

The [original MIMII release](https://zenodo.org/records/3384388), public1.0, contains only 00/02/04/06. The [original paper](https://arxiv.org/html/1909.09347) explains that machines may be different product models; fan anomaly examples include imbalance, voltage changes, and clogging. Public tables do not map each recording to a fault subtype. Different machines' positive classes therefore cannot be assumed to share fault mechanisms, and binary labels do not identify a specific fault cause. Noise is scaled and mixed using machine-level mean power; 0 dB does not mean constant instantaneous SNR in every recording.

## DUE directory verification

The [official DUE](https://zenodo.org/records/4740355) development fan ZIP is 1,072,486,301 bytes. This round read its 65,557-byte tail and 619,563-byte directory, without downloading the whole archive.

| Section | Source train normal | Target train normal | Source test normal/anomalous | Target test normal/anomalous |
| --- | ---: | ---: | ---: | ---: |
| 00 | 1000 | 3 | 100/100 | 100/100 |
| 01 | 1000 | 3 | 100/100 | 100/100 |
| 02 | 1000 | 3 | 100/100 | 100/100 |

The [DUE paper](https://arxiv.org/html/2105.02702) explains that sections roughly correspond to products, but fan01 contains two products from one manufacturer, and fan02's target-domain noise comes from a different factory. Source and target cannot be treated as two new machines. The paper lacks a mapping sufficient to determine whether DUE products share physical equipment with original MIMII.

[MIMII DG](https://zenodo.org/records/6529888) sections roughly correspond to domain-shift types and cannot directly be counted as additional independent machines. Officially documented overlap exists between DUE and the corresponding DCASE2021 data, and between DG and the corresponding DCASE2022 data; these cannot serve as mutually independent datasets.

## Fixed expansion list

The 800 labeled source_test/target_test recordings from DUE00 and 01 are explicitly reassigned to project development. Within each section/domain/class group of 100 recordings, a fixed hash split assigns 80 to fitting and 20 to calibration, totaling 640 fit plus 160 calibration. Selection does not use model scores. This is not an official DCASE test result. Official train recordings are initially excluded to avoid simply expanding the normal class and adding domain-label imbalance.

At this stage, the entire DUE02 section, including train and test, is reserved and its audio is not read. Final confirmation requires freezing the model and threshold first; a new section name alone does not establish complete independence from original machines.

Required steps after downloading are CRC and PCM-summary checks, cross-corpus duplicate screening against existing data, and splitting by whole section, without first randomly mixing windows. Old id00 test recordings are excluded, and id06 is not reopened. Until physical identities and acquisition relationships are resolved, new-data scores must not be presented as unqualified proof of independent-machine performance.

[Actual directory summary](../data/mimii-due-source-review/summary.json) and [fixed expansion list](../data/mimii-due-source-review/expansion-plan.json). This round establishes data availability, label distribution, and protection boundaries, not model acceptance.
