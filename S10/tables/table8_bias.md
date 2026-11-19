**Table 8. Experimental-bias controls: random versus temporal split (P1), static 80:20 versus temporal certificates (KB4), timestamp artefact (H9), pre-window benign, leakage (P3) and monotone-scaling invariance (P9)**

| Arm | Random-split F1 @π=10% (%) | Temporal AUT(F1@π=10%) (%) | Inflation (pp) | Random-split FNR (%) | Random-split FPR (%) |
|---|---|---|---|---|---|
| seed 11 | 96.04 | 93.35 | +2.69 | 7.55 | 0.008 |
| seed 23 | 98.76 | 89.52 | +9.24 | 1.66 | 0.090 |
| seed 37 | 98.81 | 91.36 | +7.45 | 1.97 | 0.043 |
| seed 41 | 97.99 | 89.03 | +8.97 | 3.73 | 0.024 |
| seed 53 | 97.80 | 91.51 | +6.29 | 4.16 | 0.016 |
| mean [95% CI] |  |  | +6.93 [4.59, 8.72] |  |  |

| Month | Static 80:20 FNR (%) | Temporal FNR (%) | Static FPR (%) | Temporal FPR (%) | Static understates |
|---|---|---|---|---|---|
| Mar 2020 | 1.58 | 6.51 | 0.018 | 0.028 | yes |
| Apr 2020 | 1.58 | 4.98 | 0.018 | 0.000 | yes |
| May 2020 | 1.58 | 5.07 | 0.018 | 0.016 | yes |
| Jun 2020 | 1.58 | 5.62 | 0.018 | 0.000 | yes |
| Jul 2020 | 1.58 | 16.76 | 0.018 | 0.000 | yes |
| Aug 2020 | 1.58 | 24.64 | 0.018 | 0.000 | yes |
| Sep 2020 | 1.58 | 23.92 | 0.018 | 0.024 | yes |

| Variant | Effect | Δ | Outcome |
|---|---|---|---|
| Without COFF timestamp (feature 626), H9 | AUT(F1@π=10%) 93.35 → 92.93 | -0.42 pp | met (absolute Δ < 1 pp) |
| +13,834 PreWindow benign in training | pooled FNR 12.06% → 8.40%; FPR 2/36,185 | -3.66 pp FNR | descriptive (S7 excluded PreWindow from the primary split) |

| Model | CV folds | Random 5-fold CV: F1 @π=10% (%) mean (min–max) | Temporal months Mar–Sep: F1 @π=10% (%) mean (min–max) | Δ CV − temporal (pp) | CV FNR (%) | Temporal FNR (%) | CV FPR (%) |
|---|---|---|---|---|---|---|---|
| LGBM-TRACE (f₀ family) | 5 | 99.30 (99.23–99.46) | 90.72 (82.83–96.82) | +8.58 | 1.10 | 16.25 | 0.032 |
| XGBoost | 5 | 99.39 (99.29–99.49) | 85.17 (75.51–92.93) | +14.22 | 0.79 | 24.81 | 0.046 |
| Extra trees (100 trees in CV) | 5 | 99.20 (99.04–99.33) | 89.38 (77.86–95.47) | +9.82 | 1.17 | 18.59 | 0.046 |
| Random forest (100 trees in CV) | 5 | 99.06 (98.91–99.26) | 85.50 (71.26–93.72) | +13.56 | 1.39 | 24.37 | 0.054 |
| LR | 5 | 25.39 (0.35–60.45) | 27.66 (16.18–48.28) | -2.27 | 83.48 | 83.47 | 0.019 |
| Gaussian NB | 5 | 22.74 (0.02–41.54) | 18.90 (4.76–31.16) | +3.84 | 85.86 | 89.13 | 0.035 |

| T0 replication of [1] Table III (train < 2019-10-01, 80:20 random split, empirical 0.1% validation threshold; test Oct 2019–Sep 2020) | Training / threshold | FNR Jul–Sep 2020 (%) | Monthly FNR (%) | Monthly FPR (%) | Months FPR > 0.1% | Unseen-family FNR (%) | Seen-family FNR (%) |
|---|---|---|---|---|---|---|---|
| [1] Table III {RfP} | BODMAS before 2019-10-01 | — | 1.71–7.23 | 0.00–0.51 | — | ≤ 43.04 | within 6 |
| Dated only, LGBM-EMBER {MoC} | 6,778 train / 1,694 val; θ = 8.946 (k = 0) | 13.25–20.45 | 1.91–20.45 | 0.000–0.108 | 1/12 | ≤ 42.17 | ≤ 20.92 |
| Dated only, LGBM-TRACE params {MoC} | 6,778 train / 1,694 val; θ = 5.849 (k = 0) | 15.36–22.84 | 2.92–22.84 | 0.000–0.065 | 0/12 | ≤ 54.22 | ≤ 23.41 |
| Dated + PreWindow, LGBM-EMBER {MoC} | 17,845 train / 4,461 val; θ = -0.115 (k = 3) | 1.88–2.64 | 1.19–3.43 | 0.000–0.119 | 3/12 | ≤ 29.09 | ≤ 2.93 |
| Dated + PreWindow, LGBM-TRACE params {MoC} | 17,845 train / 4,461 val; θ = -0.791 (k = 3) | 2.09–2.82 | 0.87–3.45 | 0.000–1.019 | 7/12 | ≤ 26.67 | ≤ 3.03 |

| Model | Pre-split fit | AUC-ROC (%) clean → leaky | AUC-PR @π=10% (%) clean → leaky | FNR @θ0.1% (%) clean → leaky | ΔAUC (pp) | DeLong p |
|---|---|---|---|---|---|---|
| LR | z-score scaler | 99.529 → 99.628 | 97.15 → 97.40 | 82.92 → 86.28 | +0.100 | 6.3e-10 |
| LR | χ² selector (256) | 99.668 → 99.808 | 97.84 → 98.39 | 66.44 → 57.71 | +0.140 | 1.6e-16 |
| LR | PCA (0.95) | 99.158 → 99.018 | 94.23 → 90.64 | 99.99 → 99.85 | -0.139 | 1.6e-04 |
| Linear SVM | z-score scaler | 99.389 → 99.357 | 95.49 → 95.16 | 94.27 → 94.48 | -0.032 | 0.004 |
| Linear SVM | χ² selector (256) | 99.683 → 99.811 | 97.92 → 98.30 | 77.42 → 63.80 | +0.128 | 1.4e-14 |
| Linear SVM | PCA (0.95) | 98.988 → 98.528 | 93.22 → 86.68 | 99.38 → 99.93 | -0.461 | 1.1e-25 |

LightGBM under clean versus leaky z-scaling: margins differ (maximum absolute difference 2.02); decision agreement 99.903%.

| Model | Comparison | Disagreements | Agreement (%) |
|---|---|---|---|
| Decision tree | raw vs min-max | 489/77,417 | 99.368 |
| Decision tree | raw vs z-score | 305/77,417 | 99.606 |
| Random forest (100 trees) | raw vs min-max | 183/77,417 | 99.764 |
| Random forest (100 trees) | raw vs z-score | 131/77,417 | 99.831 |
| LightGBM | raw vs min-max | 75/77,417 | 99.903 |
| LightGBM | raw vs z-score | 82/77,417 | 99.894 |
| LR | raw vs z-score | 3,231/20,000 | 83.845 |
| k-NN | raw vs z-score | 2,315/20,000 | 88.425 |

Random arm: same model and training size, rows drawn uniformly from the pooled Dated stream, certified threshold on a random calibration hold-out (biased by construction). Relative inflation of the mean: +7.66%. Leakage arms fit the scaler, χ² selector (labels included) or PCA on all Dated rows (train + calibration + test) before training. {MoC}.
