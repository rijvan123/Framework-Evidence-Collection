**Table 1. BODMAS strata and the temporal split**

| Stratum | Benign | Malware | Role |
|---|---|---|---|
| Dated | 53,790 | 56,944 | primary stream (train / calibrate / test) |
| PreWindow | 13,834 | 0 | benign first seen before 2019-08-29; PreWindow arm only |
| Placeholder | 5,870 | 0 | January 2020 benign with placeholder timestamp; censored (KB5) |
| Bulk | 3,641 | 0 | February 2020 benign with batch timestamp; censored (KB5) |
| SpikeMal | 0 | 349 | malware on spike days (k = 10 rule); R-S1 only |
| Quarantine | 7 | 0 | benign with unparseable or conflicting time; excluded |
| Total | 77,142 | 57,293 | 134,435 files; 7 identical-vector groups logged (DUP) |

| Split (S7) | Benign | Malware | Files |
|---|---|---|---|
| Train: Dated, 29 Aug–30 Nov 2019 | 11,374 | 11,784 | 23,158 |
| Calibrate: Dated, December 2019 | 6,120 | 4,039 | 10,159 |
| Test: Dated, January–September 2020 | 36,296 | 41,121 | 77,417 |

Strata and split reproduced from S7 on the released metadata and vectors; identifiers unique across all rows (134,428 SHA-256 digests and the 7 VirusShare names of the Quarantine stratum). Certificates and FPR-dependent metrics use March–September 2020, the months with ≥ 500 dated benign files. {MoC}.
