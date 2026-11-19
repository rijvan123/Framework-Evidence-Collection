**Table 7. Calibration under drift, prior shift and cost-sensitive thresholds (P4, P7, H6, H10)**

| Month | ECE raw sigmoid (%) | ECE isotonic (%) | ECE Platt (%) | Brier ×10³ @π=1%: iso / prior-shift | Brier ×10³ @π=0.1%: iso / prior-shift | EC ×10³ @π=1%, C_FN/C_FP = 100: τ* / 0.5 |
|---|---|---|---|---|---|---|
| Mar 2020 | 0.63 | 1.38 | 1.05 | 2.38 / 0.81 | 2.25 / 0.13 | 19.2 / 26.7 |
| Apr 2020 | 0.68 | 0.80 | 0.59 | 2.61 / 0.49 | 2.54 / 0.10 | 10.7 / 23.2 |
| May 2020 | 0.18 | 0.96 | 0.75 | 0.72 / 0.61 | 0.61 / 0.12 | 12.3 / 25.9 |
| Jun 2020 | 0.17 | 0.70 | 0.54 | 1.05 / 0.56 | 0.94 / 0.11 | 11.8 / 33.0 |
| Jul 2020 | 0.54 | 3.10 | 2.15 | 1.10 / 1.64 | 0.75 / 0.30 | 28.5 / 96.0 |
| Aug 2020 | 1.41 | 6.80 | 4.95 | 1.32 / 2.36 | 0.77 / 0.32 | 53.0 / 155.5 |
| Sep 2020 | 1.18 | 5.66 | 4.21 | 1.74 / 2.52 | 1.20 / 0.56 | 59.4 / 153.4 |

| π | C_FN/C_FP | mean EC(τ*) ×10³ | mean EC(0.5) ×10³ | months τ* lower | Wilcoxon p |
|---|---|---|---|---|---|
| 1% | 10 | 11.19 | 7.76 | 0/7 | 0.016 |
| 1% | 50 | 37.11 | 36.92 | 1/7 | 0.062 |
| 1% | 100 | 27.86 | 73.38 | 7/7 | 0.016 |
| 0.1% | 10 | 1.35 | 1.20 | 3/7 | 0.297 |
| 0.1% | 50 | 5.65 | 4.12 | 0/7 | 0.016 |
| 0.1% | 100 | 11.19 | 7.76 | 0/7 | 0.016 |

Calibrators fitted on December 2019 (π_cal = 39.8%). Isotonic ECE exceeded raw ECE in every month (isotonic raised ECE by 2.09 pp on average, 95% CI [0.71, 3.50]; Wilcoxon p = 0.016), so P4's calibrator clause is falsified. Prior shift (Eq. 31) lowered Brier at π = 0.1% (p = 0.016) but not at π = 1% (p = 0.812). P7 survives on one of six (π, ratio) cells. H6 (F1 at π* = 10% with the π*-aware threshold vs 0.5): mean -3.29 pp (p = 0.297), not supported. H10: Spearman ρ(month, isotonic ECE) = 0.47 (p = 0.21); met by the pre-registered sign rule, not significant. {MoC}.
