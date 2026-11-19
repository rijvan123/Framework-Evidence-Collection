**Table 10. Feature drift (Eqs. 74–75) and the label-free monitor M8 (KT)**

| Month | 𝒟(t) ×10³ (bits) | benign-class 𝒟 ×10³ | malware-class 𝒟 ×10³ | FNR f₀ at θ@0.1% (%) |
|---|---|---|---|---|
| Dec 2019 | 3.03 | 2.74 | 7.72 | 2.40 |
| Jan 2020 | 15.76 | 35.53 | 5.45 | 4.07 |
| Feb 2020 | 19.26 | 52.04 | 10.65 | 5.86 |
| Mar 2020 | 5.34 | 2.05 | 11.99 | 6.51 |
| Apr 2020 | 4.11 | 4.98 | 8.45 | 4.98 |
| May 2020 | 8.00 | 6.58 | 17.24 | 5.07 |
| Jun 2020 | 11.44 | 6.03 | 32.84 | 5.62 |
| Jul 2020 | 8.65 | 4.03 | 24.40 | 16.76 |
| Aug 2020 | 10.12 | 4.92 | 28.84 | 24.64 |
| Sep 2020 | 4.79 | 4.82 | 20.13 | 23.92 |

| Statistic | Class | λ (max over blocked null) | Test windows above λ |
|---|---|---|---|
| C2ST AUC (T5) | pred. benign | 0.779 | 22/31 |
| C2ST AUC (T5) | pred. malicious | 0.882 | 28/31 |
| KS on margins (T1) | pred. benign | 0.221 | 5/31 |
| KS on margins (T1) | pred. malicious | 0.192 | 24/31 |
| mean PSI (T2) | pred. benign | 0.068 | 5/31 |
| mean PSI (T2) | pred. malicious | 0.169 | 9/31 |
| 1 − mean credibility (T3) | pred. benign | 0.602 | 2/31 |
| 1 − mean credibility (T3) | pred. malicious | 0.557 | 21/31 |

| Signal | Alarms Mar–Sep | First alarm | First alarm after 5 Jul onset |
|---|---|---|---|
| M8 rule (P = 2 consecutive exceedances, re-arm) | 1 | 2020-03-15 | — (none) |
| ACI, label delay 7 d | 115 | 2020-03-09 | 2020-07-07 |
| ACI, label delay 30 d | 92 | 2020-04-01 | 2020-07-05 |

January–February benign-class values rest on 49 and 62 dated benign files and are inflated by small-sample JS bias. P5: Spearman ρ(𝒟, F1@π=10%) = −0.32 (p = 0.49), falsified. Exploratory (not pre-registered): ρ(malware-class 𝒟, FNR), Mar–Sep = 0.54 (permutation p = 0.241, n = 7). Monitor: 31 weekly test windows; every window exceeds at least one λ; one alarm (2020-03-15), no alarm within 14 d of the July onset week (2020-07-05); false alarms in stable months: Mar 2020 1, Apr 2020 0, May 2020 0, Jun 2020 0. KT met → trigger claim withdrawn. {MoC}.
