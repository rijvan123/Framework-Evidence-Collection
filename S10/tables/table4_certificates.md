**Table 4. Retrospective time-indexed error certificates (Eq. S7.4) and target-FPR violations by threshold rule**

| Month | θ@0.1%: FP/benign = FPR % (95% CP upper) | θ@0.1%: FNR % (upper) | θ@0.5%: FP/benign = FPR % (upper) | θ@0.5%: FNR % (upper) | θ@0.5% valid at (0.5%, 5%) |
|---|---|---|---|---|---|
| Dec 2019 (cal) | 1/6,120 = 0.016 (≤ 0.077) | 2.40 (≤ 2.84) | 21/6,120 = 0.343 (≤ 0.494) | 0.92 (≤ 1.20) | n/a |
| Jan 2020 | 0/49 = 0.000 (≤ 5.931) | 4.07 (≤ 4.59) | 0/49 = 0.000 (≤ 5.931) | 0.82 (≤ 1.08) | n/a |
| Feb 2020 | 0/62 = 0.000 (≤ 4.717) | 5.86 (≤ 6.50) | 3/62 = 4.839 (≤ 12.034) | 1.86 (≤ 2.25) | n/a |
| Mar 2020 | 1/3,577 = 0.028 (≤ 0.133) | 6.51 (≤ 7.12) | 3/3,577 = 0.084 (≤ 0.217) | 2.10 (≤ 2.47) | yes |
| Apr 2020 | 0/5,201 = 0.000 (≤ 0.058) | 4.98 (≤ 5.54) | 3/5,201 = 0.058 (≤ 0.149) | 1.75 (≤ 2.10) | yes |
| May 2020 | 1/6,121 = 0.016 (≤ 0.077) | 5.07 (≤ 5.58) | 3/6,121 = 0.049 (≤ 0.127) | 1.71 (≤ 2.02) | yes |
| Jun 2020 | 0/8,182 = 0.000 (≤ 0.037) | 5.62 (≤ 6.24) | 7/8,182 = 0.086 (≤ 0.161) | 2.56 (≤ 3.00) | yes |
| Jul 2020 | 0/6,392 = 0.000 (≤ 0.047) | 16.76 (≤ 17.65) | 6/6,392 = 0.094 (≤ 0.185) | 7.77 (≤ 8.42) | no |
| Aug 2020 | 0/2,514 = 0.000 (≤ 0.119) | 24.64 (≤ 25.81) | 1/2,514 = 0.040 (≤ 0.189) | 13.00 (≤ 13.93) | no |
| Sep 2020 | 1/4,198 = 0.024 (≤ 0.113) | 23.92 (≤ 24.98) | 5/4,198 = 0.119 (≤ 0.250) | 12.78 (≤ 13.62) | no |

| Threshold rule (fitted on December 2019) | Model×month cells (Mar–Sep) | Realised FPR > τ | CP lower bound > τ | Cells above τ by model |
|---|---|---|---|---|
| empirical 0.1% quantile of Dec benign ([1] protocol) | 273 | 14 (5.1%) | 6 | EMBER-2018 GBDT (published model) 6; RBF-SVM (PoC, 10k) 3; Gaussian NB 2; LR + χ²(256) 1; LR + PCA(0.95) 1; LR + IG(256) 1 |
| CP-certified, τ = 0.1% (k*) | 273 | 2 (0.7%) | 2 | Gaussian NB 2 |
| empirical 1% quantile | 273 | 44 (16.1%) | 25 | XGBoost 10; LGBM-TRACE (f₀ family) 8; EMBER-2018 GBDT (published model) 6; LGBM-EMBER 5; Random forest 5; Temporal stacking 3; LR + PCA(0.95) 2; Extra trees 1; Gaussian NB 1; MLP (PoC, 20k) 1; LR + mRMR(128) 1; Linear SVM 1 |
| CP-certified, τ = 1% | 273 | 21 (7.7%) | 15 | LGBM-TRACE (f₀ family) 5; EMBER-2018 GBDT (published model) 4; LGBM-EMBER 3; XGBoost 3; MLP (PoC, 20k) 1; LR + mRMR(128) 1; Gaussian NB 1; Random forest 1; Temporal stacking 1; Linear SVM 1 |

θ@0.1% = 6.348 (k* = 1), θ@0.5% = 2.899 (k* = 21), both certified on December 2019. A month is valid when both one-sided 95% Clopper–Pearson upper bounds are within tolerance. SVR (Mar–Sep): θ@0.1% with (0.1%, 2%): 0/7 (FPR-only 4/7 Mar–Sep; FNR-only 0/9 Jan–Sep); θ@0.5% with (0.5%, 5%): 4/7 (FPR-only 7/7 Mar–Sep; FNR-only 6/9 Jan–Sep). KS1 (≥ 6/7 at 0.5%) not met. January–February are not certifiable (49 and 62 dated benign). Second panel: all models and seeds; a cell violates the target when the month's realised FPR exceeds τ. {MoC}.
