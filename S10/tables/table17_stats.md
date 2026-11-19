**Table 17. Statistical comparison of detectors (U13/H5)**

| Model | Mean monthly ΔF1@π=10%, LGBM-TRACE (seed mean) − model (pp) | Cliff's δ | Wilcoxon p | Holm p | McNemar vs f₀: f₀-only / model-only errors | Months with DeLong p_Holm < 0.05 vs f₀ |
|---|---|---|---|---|---|---|
| EMBER-2018 GBDT (published model) | -3.70 | -0.306 | 0.078 | 0.219 | 2,990 / 2,288 (p = 4.3e-22) | 2/7 |
| Extra trees | +1.34 | +0.265 | 0.219 | 0.219 | 652 / 2,448 (p = 1.0e-242) | 0/7 |
| LGBM-EMBER | -2.13 | -0.429 | 0.016 | 0.219 | 516 / 477 (p = 0.228) | 2/7 |
| LR | +63.06 | +1.000 | 0.016 | 0.219 | 176 / 23,343 (p = 0.0e+00) | 6/7 |
| LR + χ²(256) | +38.59 | +1.000 | 0.016 | 0.219 | 165 / 17,103 (p = 0.0e+00) | 7/7 |
| LR + IG(256) | +88.74 | +1.000 | 0.016 | 0.219 | 40 / 28,461 (p = 0.0e+00) | 7/7 |
| LR + mRMR(128) | +43.38 | +1.000 | 0.016 | 0.219 | 185 / 18,211 (p = 0.0e+00) | 7/7 |
| MLP (PoC, 20k) | +56.68 | +1.000 | 0.016 | 0.219 | 256 / 18,159 (p = 0.0e+00) | 6/7 |
| Gaussian NB | +71.82 | +1.000 | 0.016 | 0.219 | 47 / 25,404 (p = 0.0e+00) | 7/7 |
| Random forest | +5.23 | +0.510 | 0.016 | 0.219 | 96 / 4,478 (p = 0.0e+00) | 3/7 |
| Temporal stacking | -3.25 | -0.510 | 0.016 | 0.219 | 834 / 75 (p = 6.9e-163) | 2/7 |
| Linear SVM | +80.14 | +1.000 | 0.016 | 0.219 | 103 / 26,982 (p = 0.0e+00) | 7/7 |
| RBF-SVM (PoC, 10k) | +36.32 | +1.000 | 0.016 | 0.219 | 121 / 16,270 (p = 0.0e+00) | 7/7 |
| XGBoost | +5.55 | +0.510 | 0.016 | 0.219 | 237 / 3,201 (p = 0.0e+00) | 0/7 |

| Test | Result |
|---|---|
| Friedman over 7 months | χ² = 94.97, p = 4.3e-14, Kendall W = 0.969 |
| Mean ranks (1 = best) | Temporal stacking 1.57; EMBER-2018 GBDT (published model) 2.29; LGBM-EMBER 2.57; LGBM-TRACE (f₀ family) 4.00; Extra trees 4.57; Random forest 6.43; XGBoost 6.57; RBF-SVM (PoC, 10k) 8.57; LR + χ²(256) 9.00; LR + mRMR(128) 9.57; MLP (PoC, 20k) 11.57; LR 11.86; Gaussian NB 12.57; Linear SVM 13.86; LR + IG(256) 15.00 |

Monthly F1 at π = 10% and the certified 0.1% threshold, March–September 2020 (n = 7 months; seeds averaged before testing; single-fit models use their one fit; kNN and LR + PCA are excluded from the Friedman test because F1 is undefined when no file is flagged). McNemar and DeLong compare against f₀ (seed 11) and the first seed of each model; DeLong p-values are Holm-adjusted over all model × month tests. With n = 7 the smallest two-sided Wilcoxon p is 0.0156, so no pairwise comparison can pass Holm correction over 14 comparisons (minimum 0.219): a power limit of the month-level design, not evidence of equivalence. McNemar uses the pooled March–September verdicts. {MoC}.
