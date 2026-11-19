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


**Table 1b. Unified pre-registered register (S10 Part 0): measured outcomes**

| ID | Statement | Measured | Outcome |
|---|---|---|---|
| U1 (P1/H1) | Random split inflates F1 vs temporal AUT | +6.93 pp [4.59, 8.72] at π = 10% | not falsified |
| U2 (P2/H2) | Precision follows Eq. (55) | analytic value outside measured CI in 0% of 28 cells; clause 2 untestable (no month with FPR ≥ 0.1%) | not falsified |
| U3 (P3) | Pre-split selection/PCA inflates LR/SVM; scaling leaves trees unchanged | χ² selection leak: ΔAUC +0.140 pp (LR), +0.128 pp (SVM), DeLong p ≤ 1.4e-14; F1 at π = 10% +9.18/+16.29 pp. PCA leak: ΔAUC -0.139/-0.461 pp. Scaling leak: ΔAUC +0.100/-0.032 pp; LightGBM under leaky z-scaling agrees on 99.90% of verdicts (not identical) | selection clause not falsified; PCA clause not supported; tree clause fails |
| U4 (P4) | Isotonic/Platt lower ECE; prior shift lowers Brier/EC at π ≤ 1% | isotonic raised ECE by 2.09 pp [0.71, 3.50]; prior shift lowers Brier at π = 0.1% (p = 0.016), not at 1% (p = 0.812) | falsified |
| U5 (P5/H4) | ρ(JS drift, F1) ≤ −0.5 | ρ = -0.32, p = 0.49, CI upper 0.76 | falsified |
| U6 (P6) | Open-set macro-F1 declines faster than detection F1 | slope difference +0.94 [0.24, 1.64] pp/month (opposite sign) | falsified |
| U7 (P7/H6) | τ* beats 0.5 on expected cost at π ≤ 1% | τ* lower EC in 1 of 6 (π, ratio) cells (π = 1%, ratio 100: 7/7 months) | not falsified (rule); weak |
| U8 (P8/H8) | Chain detects all injected edits; verification linear | 60,000/60,000 detected; slope 0.973 | not falsified |
| U9 (P9) | Trees invariant to monotone scaling; LR/kNN not | exact trees (DT, RF): 99.37–99.83% agreement; LightGBM agreement 99.90%, 99.89%; LR/kNN raw vs z-score: 83.84%, 88.42% agreement | falsified as stated (float32 resolution); ordering holds |
| U10 (P10) | FNR and FPR higher in the high-entropy stratum | FNR OR 1.34 [1.24, 1.45]; FPR OR 0.95 [0.09, 10.44] (3 FPs) | falsified for FPR |
| U11 (P11) | Observed TPR/FPR follow Eq. (5) under injected label noise | prediction inside bootstrap CI at η = 1% and 5% | not falsified |
| U12 (H3) | Unseen-family FNR > known-family FNR | Wilcoxon p = 0.0117, A12 = 0.926 | met |
| U13 (H5) | GBDT leads on AUT | Friedman χ² = 95.0, p = 4.3e-14, W = 0.969 | met |
| U14 (H7) | Open-set rejection raises open-set macro-F1 | p = 0.0039; mean +0.42 pp | met (negligible effect) |
| U15 (H9) | No COFF-timestamp artefact | ΔAUT = -0.42 pp | met |
| U16 (H10) | Calibration degrades over time | ρ(month, ECE) = 0.47, p = 0.21 | met by sign rule; n.s. |
| K1 | Full re-scoring changes ≤ B in ≥ 6/7 updates | 7/7 updates; 0 changes in scope | kill met |
| K2 | CP-95% upper bound of h < 0.1% in every update | 0 harmful flips; upper bounds 0.026–0.058% | kill met |
| K3 | Upper CI of relative E^ev reduction vs (viii) < 10% (L = 30 d) | 0.0% [0.0, 0.0] | kill met → A2 |
| KT | Alarm ≤ 14 d after July onset and ≤ 1 false alarm per stable month | one alarm (2020-03-15); none after onset (2020-07-05) | kill met → scheduled |
| KB1 | Yield ≥ 1.5× (vii) and lower U(t) in ≥ 6/7 months | yield 0.44% vs 0.88% (×0.50); lower U in 2/7 | not met |
| KB3 | ≥ 99.9% bit-identical re-execution | 100.0% (tree hash, scores, vector digest) | met |
| KB4 | Static 80:20 understates FPR or FNR in ≥ 5/7 months | FNR understated in 7/7 | met |
| KB5 | Censored stratum shifts FPR > bootstrap half-width | shift 0.186 and 0.324 pp vs half-width 0 (0/49, 0/62 FPs) | met literally; inconclusive |
| KB7 | Yield advantage keeps its sign at r = 2% | advantage -0.44 pp at r = 0 already negative | not met (moot) |
| KB9 | Ambiguity beats margin by ≥ 0.05 AUPRC | not executed (D13) | moot after A2 |
| KB10 | Novel-family AUROC ≥ 0.80 and AUPRC ≥ 3× base (July) | AUROC 0.804; AUPRC 0.671 < 0.874 | kill met → leg dropped |
| KB11 | Cliff's δ (stability, correct vs wrong) ≥ 0.147 | δ = 0.168 | met |
| KB12 | Cllr ≥ 1 in ≥ 3 months | Cllr 0.016–0.107; 0 months ≥ 1 | kill not triggered |
| KS1 | SVR ≥ 6/7 at τ_FPR = 0.5% | 4/7 | not met |
| KS2 | CP upper bound of r_H ≤ 0.5% per update | 0.058% maximum | met |

Decision rules as locked in S10_protocol.md. "Kill met" means the pre-registered consequence applies. All values {MoC}.


**Table 2. Model zoo on the pooled March–September 2020 stream at the CP-certified 0.1% threshold**

| Model | Seeds | AUC-ROC (%) | AUC-PR @π=10% (%) | F1 @π=10% (%) | MCC @π=10% (%) | Precision @π=1% (%) | TPR (%) | FPR (%) | FNR (%) | AUT(F1@π=10%), Mar–Sep |
|---|---|---|---|---|---|---|---|---|---|---|
| LGBM-TRACE (f₀ family) | 5 | 99.970 (99.968–99.971) | 99.79 (99.77–99.80) | 91.32 (89.52–93.55) | 90.87 (89.07–93.11) | 99.10 (98.73–99.34) | 84.12 (81.07–87.94) | 0.008 (0.006–0.011) | 15.88 (12.06–18.93) | 0.910 (0.890–0.933) |
| LGBM-EMBER | 3 | 99.978 (99.978–99.979) | 99.85 (99.85–99.85) | 93.41 (92.58–94.05) | 92.98 (92.13–93.63) | 99.17 (99.06–99.39) | 87.71 (86.25–88.80) | 0.007 (0.006–0.008) | 12.29 (11.20–13.75) | 0.933 (0.924–0.939) |
| XGBoost | 5 | 99.972 (99.966–99.975) | 99.82 (99.77–99.84) | 86.05 (80.85–88.43) | 85.77 (80.94–88.01) | 99.58 (99.31–100.00) | 75.64 (67.85–79.30) | 0.003 (0.000–0.006) | 24.36 (20.70–32.15) | 0.854 (0.799–0.880) |
| Random forest | 5 | 99.958 (99.954–99.960) | 99.71 (99.68–99.73) | 86.30 (85.38–87.30) | 85.98 (85.10–86.92) | 99.36 (99.27–99.64) | 75.95 (74.53–77.50) | 0.005 (0.003–0.006) | 24.05 (22.50–25.47) | 0.853 (0.843–0.864) |
| Extra trees | 5 | 99.962 (99.959–99.963) | 99.77 (99.75–99.79) | 89.85 (88.12–90.79) | 89.41 (87.72–90.33) | 99.80 (99.66–100.00) | 81.60 (78.77–83.15) | 0.002 (0.000–0.003) | 18.40 (16.85–21.23) | 0.892 (0.873–0.903) |
| LR | 1 | 99.529 [99.475, 99.583] | 97.15 | 29.14 [28.57, 29.73] | 39.28 [38.75, 39.79] | 88.65 [81.72, 95.44] | 17.09 [16.69, 17.49] | 0.022 [0.008, 0.039] | 82.91 [82.51, 83.31] | 0.276 |
| LR + χ²(256) | 1 | 99.667 [99.626, 99.707] | 97.83 | 53.04 [52.50, 53.59] | 57.99 [57.55, 58.44] | 97.06 [94.25, 99.26] | 36.13 [35.62, 36.64] | 0.011 [0.003, 0.022] | 63.87 [63.36, 64.38] | 0.526 |
| LR + IG(256) | 1 | 99.408 [99.355, 99.461] | 94.97 | 2.00 [1.78, 2.20] | 8.65 [7.87, 9.42] | 34.58 [23.02, 63.42] | 1.01 [0.90, 1.11] | 0.019 [0.006, 0.033] | 98.99 [98.89, 99.10] | 0.019 |
| LR + mRMR(128) | 1 | 99.629 [99.593, 99.666] | 96.82 | 49.31 [48.75, 49.87] | 54.95 [54.46, 55.41] | 90.22 [85.62, 95.21] | 32.83 [32.33, 33.33] | 0.036 [0.017, 0.055] | 67.17 [66.67, 67.67] | 0.473 |
| LR + PCA(0.95) | 1 | 99.160 [99.084, 99.236] | 94.26 | 0.02 [0.01, 0.05] | 0.47 [-0.10, 1.39] | 4.28 [0.56, 100.00] | 0.01 [0.00, 0.02] | 0.003 [0.000, 0.008] | 99.99 [99.98, 100.00] | — |
| Linear SVM | 1 | 99.390 [99.328, 99.452] | 95.50 | 10.82 [10.40, 11.28] | 22.31 [21.71, 22.90] | 72.37 [59.99, 87.35] | 5.73 [5.50, 5.99] | 0.022 [0.008, 0.039] | 94.27 [94.01, 94.50] | 0.107 |
| RBF-SVM (PoC, 10k) | 1 | 99.750 [99.730, 99.771] | 98.43 | 55.63 [55.09, 56.16] | 60.06 [59.64, 60.47] | 100.00 [100.00, 100.00] | 38.53 [38.01, 39.05] | 0.000 [0.000, 0.000] | 61.47 [60.95, 61.99] | 0.539 |
| k-NN (PCA-50) | 1 | 99.650 [99.610, 99.689] | 96.72 | — | — | — | 0.00 [0.00, 0.00] | 0.000 [0.000, 0.000] | 100.00 [100.00, 100.00] | — |
| Gaussian NB | 1 | 92.101 [91.889, 92.313] | 71.14 | 18.82 [18.29, 19.36] | 28.82 [28.05, 29.54] | 42.52 [36.41, 50.51] | 10.52 [10.20, 10.86] | 0.144 [0.105, 0.185] | 89.48 [89.14, 89.80] | 0.184 |
| MLP (PoC, 20k) | 3 | 99.677 (99.613–99.713) | 98.18 (97.57–98.62) | 34.82 (7.90–49.79) | 42.58 (19.14–55.47) | 93.32 (88.26–96.81) | 22.62 (4.11–33.18) | 0.011 (0.006–0.017) | 77.38 (66.82–95.89) | 0.341 (0.081–0.486) |
| Temporal stacking | 3 | 99.980 (99.980–99.980) | 99.87 (99.86–99.87) | 94.38 (93.36–94.94) | 93.97 (92.92–94.55) | 99.00 (98.51–99.38) | 89.44 (87.58–90.48) | 0.009 (0.006–0.014) | 10.56 (9.52–12.42) | 0.941 (0.929–0.948) |
| EMBER-2018 GBDT (published model) | 1 | 99.956 [99.950, 99.963] | 99.67 | 94.66 [94.46, 94.86] | 94.25 [94.03, 94.45] | 96.77 [94.82, 98.51] | 90.11 [89.79, 90.43] | 0.030 [0.014, 0.050] | 9.89 [9.57, 10.21] | 0.947 |

Dated stratum, 32,691 malware / 36,185 benign. Threshold certified on December 2019 (τ_FPR = 0.1%, 95% CP). Single-fit models: point estimate with 95% CI (stratified binomial bootstrap, B = 1,000; DeLong for AUC). Multi-seed models: seed mean (min–max). π-dependent cells use Eq. (70). AUT over the seven monthly F1 values (Eq. 69). "—": undefined (no positive verdict at the threshold). All values {MoC}.


**Table 3. Evidentiary detector f₀ by month at the certified threshold**

| Month | Benign | Malware | FN | FP | FNR (%) | FPR (%) | F1 @π=10% (%) | Precision @π=1% (%) | AUC-ROC (%) | MCC native (%) |
|---|---|---|---|---|---|---|---|---|---|---|
| Dec 2019 (cal) | 6,120 | 4,039 | 97 | 1 | 2.40 [1.96, 2.87] | 0.016 [0.000, 0.049] | 98.71 [98.41, 98.98] | 98.37 [95.25, 100.00] | 99.989 [99.984, 99.994] | 98.00 [97.59, 98.36] |
| Jan 2020 | 49 | 4,400 | 179 | 0 | 4.07 [3.45, 4.61] | — (n < 100) | — | — | 99.989 [99.976, 100.000] | 45.41 [43.07, 48.51] |
| Feb 2020 | 62 | 4,030 | 236 | 0 | 5.86 [5.14, 6.55] | — (n < 100) | — | — | 99.815 [99.654, 99.975] | 44.26 [42.16, 46.76] |
| Mar 2020 | 3,577 | 4,990 | 325 | 1 | 6.51 [5.81, 7.17] | 0.028 [0.000, 0.084] | 96.51 [96.05, 96.94] | 97.12 [91.81, 100.00] | 99.929 [99.892, 99.966] | 92.55 [91.84, 93.32] |
| Apr 2020 | 5,201 | 4,640 | 231 | 0 | 4.98 [4.37, 5.58] | 0.000 [0.000, 0.000] | 97.45 [97.13, 97.76] | 100.00 [100.00, 100.00] | 99.984 [99.977, 99.991] | 95.38 [94.84, 95.93] |
| May 2020 | 6,121 | 5,449 | 276 | 1 | 5.07 [4.48, 5.62] | 0.016 [0.000, 0.049] | 97.33 [97.00, 97.67] | 98.32 [95.12, 100.00] | 99.991 [99.986, 99.997] | 95.29 [94.79, 95.83] |
| Jun 2020 | 8,182 | 4,217 | 237 | 0 | 5.62 [4.93, 6.31] | 0.000 [0.000, 0.000] | 97.11 [96.74, 97.47] | 100.00 [100.00, 100.00] | 99.993 [99.990, 99.997] | 95.77 [95.26, 96.29] |
| Jul 2020 | 6,392 | 4,995 | 837 | 0 | 16.76 [15.74, 17.78] | 0.000 [0.000, 0.000] | 90.86 [90.24, 91.46] | 100.00 [100.00, 100.00] | 99.969 [99.955, 99.983] | 85.79 [84.97, 86.62] |
| Aug 2020 | 2,514 | 3,823 | 942 | 0 | 24.64 [23.31, 26.00] | 0.000 [0.000, 0.000] | 85.95 [85.06, 86.81] | 100.00 [100.00, 100.00] | 99.967 [99.943, 99.992] | 74.04 [72.82, 75.25] |
| Sep 2020 | 4,198 | 4,577 | 1,095 | 1 | 23.92 [22.68, 25.13] | 0.024 [0.000, 0.071] | 86.31 [85.49, 87.11] | 96.99 [91.41, 100.00] | 99.949 [99.920, 99.978] | 77.65 [76.64, 78.68] |

f₀ = LGBM-TRACE, seed 11; θ = 6.348 (margin), certified on December 2019 at τ_FPR = 0.1% (k* = 1). 95% CIs in brackets. January and February 2020 hold 49 and 62 dated benign files, so FPR-dependent cells are not reported for them. Bootstrap intervals collapse to a point when a month has zero false positives; Table 4 gives the exact Clopper–Pearson bounds used for certification. {MoC}.


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


**Table 5. Censored benign strata, spike-day malware and the spike-rule sensitivity (f₀, θ@0.1%)**

| Month | Censored stratum | Dated benign | FPR dated (%) | Censored benign | FPR censored (%) (95% CP upper) | FPR pooled (%) | Shift (pp) | Bootstrap half-width (pp) |
|---|---|---|---|---|---|---|---|---|
| Jan 2020 | Placeholder | 49 | 0.00 | 5,870 | 0.187 (≤ 0.310) | 0.186 | 0.186 | 0.000 |
| Feb 2020 | Bulk | 62 | 0.00 | 3,641 | 0.330 (≤ 0.533) | 0.324 | 0.324 | 0.000 |

| Month | SpikeMal files | FNR spike-day malware (%) | FNR dated (%) | FNR pooled (%) |
|---|---|---|---|---|
| Jan 2020 | 110 | 0.91 | 4.07 | 3.99 |
| Feb 2020 | 239 | 19.25 | 5.86 | 6.61 |

| June 2020 rule | Files | FNR (%) | FPR (%) | F1 native (%) |
|---|---|---|---|---|
| spike rule k = 10 (primary) | 12,399 | 5.62 | 0.000 | 97.11 |
| spike rule k = 4 (sensitivity) | 10,985 | 5.86 | 0.000 | 96.98 |

Placeholder (January) and Bulk (February) benign files carry batch timestamps and are excluded from the Dated stream (S7). The KB5 rule (shift > bootstrap half-width) is met literally in both months, but the half-width is zero because the dated stratum has 0/49 and 0/62 false positives; the test is degenerate and reported as inconclusive. Both censored strata alone fail the 0.1% FPR certificate (CP upper 0.31% and 0.53%). {MoC}.


**Table 6. Precision (%) under deployment prevalence π: measured streams versus Eq. (55)**

| Month | π = 1% | π = 2% | π = 5% | π = 10% | Default θ: Prec @π=0.1% | Default θ: Prec @π=1% |
|---|---|---|---|---|---|---|
| Mar 2020 | 97.07 [96.82, 97.30] / 97.12 | 98.55 [98.48, 98.62] / 98.56 | 99.43 [99.41, 99.44] / 99.44 | 99.73 [99.72, 99.74] / 99.73 | 8.53 | 48.49 |
| Apr 2020 | 100.00 [100.00, 100.00] / 100.00 | 100.00 [100.00, 100.00] / 100.00 | 100.00 [100.00, 100.00] / 100.00 | 100.00 [100.00, 100.00] / 100.00 | 5.45 | 36.77 |
| May 2020 | 98.31 [98.19, 98.39] / 98.32 | 99.17 [99.14, 99.19] / 99.16 | 99.67 [99.67, 99.68] / 99.67 | 99.85 [99.84, 99.85] / 99.85 | 33.69 | 83.68 |
| Jun 2020 | 100.00 [100.00, 100.00] / 100.00 | 100.00 [100.00, 100.00] / 100.00 | 100.00 [100.00, 100.00] / 100.00 | 100.00 [100.00, 100.00] / 100.00 | 27.05 | 78.91 |
| Jul 2020 | 100.00 [100.00, 100.00] / 100.00 | 100.00 [100.00, 100.00] / 100.00 | 100.00 [100.00, 100.00] / 100.00 | 100.00 [100.00, 100.00] / 100.00 | 29.76 | 81.05 |
| Aug 2020 | 100.00 [100.00, 100.00] / 100.00 | 100.00 [100.00, 100.00] / 100.00 | 100.00 [100.00, 100.00] / 100.00 | 100.00 [100.00, 100.00] / 100.00 | 23.84 | 75.96 |
| Sep 2020 | 96.91 [96.43, 97.30] / 96.99 | 98.50 [98.37, 98.63] / 98.49 | 99.41 [99.38, 99.44] / 99.41 | 99.72 [99.71, 99.73] / 99.72 | 20.67 | 72.44 |

Certified θ@0.1% columns: mean [2.5, 97.5 percentile] over 20 prevalence-resampled streams / analytic value from the month's measured TPR and FPR. Analytic value outside the measured interval in 0% of the 28 cells (P2 not falsified). No month had realised FPR ≥ 0.1% at the certified threshold, so the second clause of P2 is untestable. Default θ (p = 0.5): analytic precision from the month's measured rates. {MoC}.


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


**Table 9. Error structure of f₀ at θ@0.1%: entropy strata (P10), unseen versus known families (H3) and the families behind the July–September decay**

| High-entropy definition | Error | High stratum: errors/n = % | Low stratum: errors/n = % | Odds ratio [95% CI] | Fisher p |
|---|---|---|---|---|---|
| Eq. (19) packing indicator, τ_p = 1/32 | FNR | 3,040/23,587 = 12.888 | 903/9,104 = 9.919 | 1.34 [1.24, 1.45] | 5.9e-14 |
| Eq. (19) packing indicator, τ_p = 1/32 | FPR | 2/24,561 = 0.008 | 1/11,624 = 0.009 | 0.95 [0.09, 10.44] | 1.000 |
| byte mass in the two highest entropy bins > 0.5 | FNR | 2,675/18,839 = 14.199 | 1,268/13,852 = 9.154 | 1.64 [1.53, 1.76] | 1.3e-44 |
| byte mass in the two highest entropy bins > 0.5 | FPR | 2/18,117 = 0.011 | 1/18,068 = 0.006 | 1.99 [0.18, 22.00] | 1.000 |

| Month | Unseen-family malware | FNR unseen (%) | Known-family malware | FNR known (%) |
|---|---|---|---|---|
| Jan 2020 | 63 | 36.51 | 4,337 | 3.60 |
| Feb 2020 | 78 | 37.18 | 3,952 | 5.24 |
| Mar 2020 | 71 | 45.07 | 4,919 | 5.96 |
| Apr 2020 | 71 | 15.49 | 4,569 | 4.82 |
| May 2020 | 161 | 28.57 | 5,288 | 4.35 |
| Jun 2020 | 69 | 26.09 | 4,148 | 5.28 |
| Jul 2020 | 734 | 8.72 | 4,261 | 18.14 |
| Aug 2020 | 131 | 32.06 | 3,692 | 24.38 |
| Sep 2020 | 246 | 59.76 | 4,331 | 21.89 |

| Family (Jul–Sep 2020) | Seen in training | Malware files | False negatives | FNR (%) | Share of all Jul–Sep FN (%) |
|---|---|---|---|---|---|
| wabot | yes | 1,958 | 1,269 | 64.8 | 44.2 |
| ceeinject | yes | 814 | 272 | 33.4 | 9.5 |
| zbot | yes | 280 | 210 | 75.0 | 7.3 |
| tofsee | yes | 304 | 157 | 51.6 | 5.5 |
| salgorea | yes | 197 | 131 | 66.5 | 4.6 |
| wacatac | yes | 267 | 105 | 39.3 | 3.7 |
| glupteba | yes | 100 | 100 | 100.0 | 3.5 |
| cosmicduke | no | 57 | 57 | 100.0 | 2.0 |
| all families |  | 13,395 | 2,874 | 21.5 | 100.0 |

P10 is falsified for FPR (3 false positives in total; the odds-ratio CI spans 1) and holds for FNR. H3: Wilcoxon over months p = 0.0117, A12 = 0.926 (met), yet July–September FNR is driven by families present in training. Family labels are BODMAS family tokens (RecMaL [92] estimates about 20% of them shifted or wrong). {MoC}.


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


**Table 11. Assurance-plane simulation (S7 Algorithm 6): exposure, kill criteria K1–K3, label-delay and label-rate sensitivity, analyst noise and prevalence-resampled streams**

| Policy | E^ev_T, finding-days [95% CI] | E_T [95% CI] | E^ev / E^ev(viii) | Abstained at issue | Screening-only at issue | Evaluative coverage (%) | Reviews | Corrections by review | Yield (%) | Harmful auto-amendments |
|---|---|---|---|---|---|---|---|---|---|---|
| A2: frozen f₀, no safeguards | 56,550 [39,658–74,039] | 56,550 [39,658–74,039] | 628.33× | 0 | 0 | 100.0 | 0 | 0 | — | 0 |
| (viii-f) frozen f₀ + κ + certificates | 600 [310–963] | 1,140 [791–1,504] | 6.67× | 7,234 | 24,094 | 74.6 | 0 | 0 | — | 0 |
| A2: monthly retrain only | 8,730 [7,053–10,517] | 8,730 [7,053–10,517] | 97.00× | 0 | 0 | 100.0 | 0 | 0 | — | 0 |
| A2: retrain + certificate gating | 4,740 [3,438–6,119] | 8,730 [7,053–10,517] | 52.67× | 0 | 18,279 | 76.1 | 0 | 0 | — | 0 |
| A2: retrain + κ abstention | 510 [263–808] | 510 [263–808] | 5.67× | 5,466 | 0 | 100.0 | 0 | 0 | — | 0 |
| (viii) retrain + κ + certificates, no review | 90 [48–137] | 510 [263–808] | 1.00× | 5,466 | 16,814 | 76.1 | 0 | 0 | — | 0 |
| TRACE-PE (budgeted re-validation) | 90 [48–137] | 481 [248–767] | 1.00× | 5,466 | 16,814 | 75.6 | 680 | 3 | 0.44 | 0 |
| (i) re-score, auto-accept | 90 [48–137] | 510 [263–808] | 1.00× | 5,466 | 16,814 | 76.1 | 0 | 0 | — | 0 |
| (ii) review changes | 90 [48–137] | 510 [263–808] | 1.00× | 5,466 | 16,814 | 76.1 | 0 | 0 | — | 0 |
| (iii) calendar re-validation | 90 [48–137] | 510 [263–808] | 1.00× | 5,466 | 16,814 | 76.1 | 0 | 0 | — | 0 |
| (iv) Transcendent 10% | 30 [7–58] | 270 [115–456] | 0.33× | 10,614 | 15,741 | 76.0 | 0 | 0 | — | 0 |
| (v) PCT-adapted, auto | 90 [48–137] | 510 [263–808] | 1.00× | 5,466 | 16,814 | 76.1 | 0 | 0 | — | 0 |
| (vi) random review | 90 [48–137] | 510 [263–808] | 1.00× | 5,466 | 16,814 | 76.2 | 680 | 0 | 0.00 | 0 |
| (vii) lowest-margin review | 90 [48–137] | 448 [234–711] | 1.00× | 5,466 | 16,814 | 76.2 | 680 | 6 | 0.88 | 0 |
| ablation: no region selection | 90 [48–137] | 436 [219–695] | 1.00× | 5,466 | 16,814 | 76.2 | 680 | 6 | 0.88 | 0 |
| ablation: no flagging | 90 [48–137] | 481 [248–767] | 1.00× | 5,466 | 16,814 | 76.2 | 680 | 3 | 0.44 | 0 |
| ablation: no harm gate | 90 [48–137] | 481 [248–767] | 1.00× | 5,466 | 16,814 | 75.6 | 680 | 3 | 0.44 | 0 |
| ablation: no auto-amendment | 90 [48–137] | 481 [248–767] | 1.00× | 5,466 | 16,814 | 75.6 | 680 | 3 | 0.44 | 0 |

| Update | In-scope findings N | Budget B | Verdict changes on full re-scoring | Harmful flips | CP-95% upper bound of h (%) |
|---|---|---|---|---|---|
| 2020-04-01 | 7,409 | 85 | 0 | 0 | 0.040 |
| 2020-05-01 | 8,772 | 99 | 0 | 0 | 0.034 |
| 2020-06-01 | 10,354 | 112 | 0 | 0 | 0.029 |
| 2020-07-01 | 11,608 | 124 | 0 | 0 | 0.026 |
| 2020-08-01 | 8,889 | 110 | 0 | 0 | 0.034 |
| 2020-09-01 | 5,141 | 62 | 0 | 0 | 0.058 |
| 2020-10-01 | 7,919 | 88 | 0 | 0 | 0.038 |

| Update | Re-scored findings (incl. abstained) | Abstained at issue | Verdict flips | Flips among abstained | Harmful: malware → benign | Harmful: benign → malicious | Corrective flips |
|---|---|---|---|---|---|---|---|
| 2020-04-01 | 8,040 | 631 | 27 | 27 | 4 | 0 | 23 |
| 2020-05-01 | 9,548 | 776 | 49 | 49 | 0 | 35 | 14 |
| 2020-06-01 | 10,767 | 413 | 17 | 17 | 1 | 0 | 16 |
| 2020-07-01 | 12,058 | 450 | 23 | 23 | 0 | 15 | 8 |
| 2020-08-01 | 10,476 | 1,587 | 15 | 15 | 0 | 9 | 6 |
| 2020-09-01 | 5,889 | 748 | 3 | 3 | 1 | 0 | 2 |
| 2020-10-01 | 8,455 | 536 | 8 | 8 | 1 | 1 | 6 |

| Scenario | Issued as evaluative | E^ev (viii) | E^ev TRACE-PE | K3: rel. reduction (%) [CI] | E^ev (vii) margin (rel.) | E^ev TRACE-PE without region (rel.) | K1: updates with changes ≤ B | K2 | E^ev retrain only | E^ev frozen, no safeguards |
|---|---|---|---|---|---|---|---|---|---|---|
| L = 30 d, ρ_L = 1.0 (primary) | 46,596 | 90 | 90 | 0.0 [0.0, 0.0] | 90 (+0.0%) | 90 (+0.0%) | 7/7 (changes: 0) | met (harmful: 0) | 8,730 | 56,550 |
| L = 60 d, ρ_L = 1.0 | 1,361 | 480 | 399 | 16.9 [4.7, 29.3] | 16 (-96.7%) | 190 (-60.4%) | 7/7 (changes: 0) | met (harmful: 0) | 21,135 | 107,144 |
| L = 90 d, ρ_L = 1.0 | 0 | 0 | 0 | 0.0 [0.0, 0.0] | 0 | 0 | 7/7 (changes: 5) | met (harmful: 4) | 31,800 | 140,496 |
| L = 30 d, ρ_L = 0.5 | 38,177 | 182 | 182 | 0.0 [0.0, 0.0] | 182 (+0.0%) | 29 (-84.1%) | 7/7 (changes: 0) | met (harmful: 0) | 33,083 | 121,446 |

| Analyst error r | TRACE-PE | (vii) margin | (vi) random | TRACE-PE, oracle overrides analyst at maturity | (vii), oracle overrides analyst | (viii) no review |
|---|---|---|---|---|---|---|
| 0.5% | 467.1 | 467.1 | 488.6 | 135.3 | 129.3 | 90.0 |
| 1% | 865.4 | 865.4 | 948.1 | 173.6 | 164.4 | 90.0 |
| 2% | 1,745.0 | 1,745.0 | 1,849.1 | 294.8 | 281.5 | 90.0 |

| Stream π | E^ev (viii), mean [2.5, 97.5 pct] | E^ev TRACE-PE | E^ev (vii) | E^ev (i) | Findings per stream |
|---|---|---|---|---|---|
| 10% | 39.0 [30, 60] | 39.0 | 36.1 | 39.0 | 40,204 |
| 5% | 33.0 [30, 60] | 33.0 | 32.0 | 33.0 | 38,089 |

Native Dated stream: 68,876 findings issued 1 Mar–30 Sep 2020, horizon 31 Oct; τ_FPR = 0.5%, τ_FNR = 5%; B = 1% of the previous 30 days' issuances; γ = 0.5 from the pre-test replay on 2019 data. E^ev_T counts wrong findings held in evaluative states (issued, confirmed, corrected, reconciled) per day; E_T counts all live wrong findings. CIs: 95% day-block bootstrap. Evaluative coverage = mean daily share of live findings held in evaluative states. (iv) lowers exposure by abstaining on about twice as many findings. A2 ablation: certificates + abstention reduce E^ev by 98.97% versus monthly retraining alone and 99.84% versus a frozen detector without safeguards. K1, K2 and K3 are all met at L = 30 d, so the pre-registered fallback to A2 applies. Sensitivity rows: relative changes of E^ev are versus (viii) in the same scenario (negative = reduction); with L ≥ 60 d few or no certificates are valid at issue (validity horizon A_max = 60 d), so almost all findings are issued as screening-only. Noise rows: mean over 10 seeds. {MoC} (simulation on real BODMAS scores and labels).


**Table 12. Secondary attribution leg: open-set family attribution, unseen-family detection and category back-off**

| Month | Non-generic malware | Unseen share ν_t (%) | Top-1 known (%) | Top-3 known (%) | Top-1 all (%) | Closed-world bound 1 − ν_t (%) | Macro-F1 closed / open (%) | Novelty AUROC | Novelty AUPRC (base rate) | Unknowns rejected (%) | Category acc. / macro-F1 (%) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Jan 2020 | 4,270 | 7.1 | 77.4 | 95.6 | 71.9 | 92.9 | 71.0 / 71.2 | 0.742 | 0.196 (0.071) | 7.6 | 92.7 / 87.1 |
| Feb 2020 | 3,612 | 9.3 | 78.4 | 84.7 | 71.1 | 90.7 | 65.7 / 66.1 | 0.815 | 0.382 (0.093) | 11.0 | 92.4 / 87.4 |
| Mar 2020 | 4,440 | 10.2 | 72.4 | 80.1 | 65.0 | 89.8 | 67.0 / 67.7 | 0.721 | 0.237 (0.102) | 10.1 | 88.0 / 82.2 |
| Apr 2020 | 4,297 | 10.3 | 77.0 | 86.3 | 69.1 | 89.7 | 66.7 / 67.0 | 0.586 | 0.214 (0.103) | 6.8 | 85.4 / 83.4 |
| May 2020 | 5,357 | 18.3 | 63.7 | 75.6 | 52.0 | 81.7 | 63.9 / 64.3 | 0.445 | 0.203 (0.183) | 2.9 | 77.1 / 76.8 |
| Jun 2020 | 3,938 | 10.5 | 56.4 | 68.0 | 50.5 | 89.5 | 63.9 / 64.2 | 0.572 | 0.246 (0.105) | 2.9 | 61.5 / 69.5 |
| Jul 2020 | 4,783 | 29.1 | 77.1 | 82.6 | 54.7 | 70.9 | 60.2 / 60.2 | 0.804 | 0.671 (0.291) | 2.4 | 81.1 / 77.8 |
| Aug 2020 | 3,366 | 26.4 | 81.3 | 86.1 | 59.8 | 73.6 | 60.8 / 61.9 | 0.813 | 0.589 (0.264) | 12.4 | 92.9 / 86.2 |
| Sep 2020 | 4,287 | 32.8 | 74.5 | 81.6 | 50.1 | 67.2 | 60.9 / 61.2 | 0.799 | 0.593 (0.328) | 9.7 | 89.8 / 82.5 |

LightGBM multiclass over 68 families with ≥ 20 training samples (9,886 files; 3,776 files with generic AV tokens excluded, D8). Open-set rejection at the December 5th-percentile max-probability (τ_open = 0.529). KB10 (July): AUROC 0.804 ≥ 0.80 but AUPRC 0.671 < 3 × 0.291 = 0.874 → kill met, attribution leg dropped. H7: open > closed macro-F1 in 9/9 months, Wilcoxon p = 0.0039, mean +0.42 pp (met; negligible effect). P6: slope of open-set macro-F1 -1.21 pp/month vs detection F1 -2.15 pp/month; difference +0.94 [0.24, 1.64] pp/month, the opposite sign to the prediction → falsified. A first fit with num_leaves = 15, lr = 0.1 diverged (training accuracy 27.5%) and was discarded before any test month was read (D12). {MoC}.


**Table 13. Explanation evidence and ledger integrity (KB11, P8, KB3, V1–V3)**

| EMBER group | Mean abs. grouped SHAP (margin) | Abs. SHAP share (%) | Gain share (%) | LR abs. coefficient share (%) | Mean abs. Δ margin on group deletion |
|---|---|---|---|---|---|
| ByteHistogram | 1.079 | 11.4 | 8.6 | 10.8 | 1.024 |
| ByteEntropyHistogram | 0.272 | 2.9 | 3.2 | 10.0 | 0.307 |
| StringExtractor | 1.142 | 12.0 | 13.7 | 6.5 | 1.087 |
| GeneralFileInfo | 0.385 | 4.0 | 3.6 | 1.1 | 0.272 |
| HeaderFileInfo | 2.674 | 28.1 | 36.6 | 4.3 | 1.700 |
| SectionInfo | 0.749 | 7.9 | 3.1 | 9.3 | 0.668 |
| ImportsInfo | 0.796 | 8.4 | 9.7 | 52.8 | 0.605 |
| ExportsInfo | 0.002 | 0.0 | 0.0 | 2.6 | 0.000 |
| DataDirectories | 2.403 | 25.3 | 21.6 | 2.7 | 1.134 |

| Check | Result |
|---|---|
| Grouped TreeSHAP cost | 4.09 ms per finding; local accuracy max residual 4.3e-14 |
| Deletion faithfulness (Spearman, SHAP rank vs Δ margin) | mean 0.62, median 0.70 |
| KB11 stability (top-3 group Jaccard across seeds) | correct 0.906 vs wrong 0.856 (n = 373); Cliff's δ = 0.168 ≥ 0.147 → gate allowed |
| Issued-finding records (ISS) | 77,417 records with monthly epoch anchors (341 s) |
| V1 chain verification | 211,960 records verified in 2.13 s |
| V2 content-addressed objects | 28 objects, 0 failures |
| V3 re-execution (1,000 sampled findings) | vector hash 1,000/1,000; margin bit-identical 1,000/1,000; SHAP local accuracy 1,000/1,000 |
| P8 tamper injection | bit flip 10,000/10,000; deletion 10,000/10,000; insertion 10,000/10,000; swap 10,000/10,000; timestamp edit 10,000/10,000; actor edit 10,000/10,000 |
| P8 verification scaling | n = 1,000: 0.0015 s; n = 10,000: 0.0218 s; n = 100,000: 0.1356 s; n = 1,000,000: 1.4649 s; log–log slope 0.973 ∈ [0.9, 1.1] |
| KB3 cross-environment re-execution | tree hash, 97,436 scores, 134,435-vector digest identical (100.0%); container Python 3.13.16 / NumPy 2.5.3 vs device Python 3.10.12 / NumPy 2.2.6, LightGBM 4.7.0 on both |
| Acquisition | 134,435 ACQ records; 7 duplicate groups; oracle Merkle root 7dcfe2a8d1c034ff… |

Grouped TreeSHAP: exact LightGBM pred_contrib summed over EMBER v2 groups, 6,020 month×class-stratified March–September findings. The anchor signature is Ed25519 with a simulated timestamping authority; WORM storage is emulated by a content-addressed write-once store. {MoC}.


**Table 14. EMBER-2018 corroboration (D10)**

| Published EMBER-2018 model on Nov–Dec 2018 | Release notebook {RfP} (full test set) | This vectorisation {MoC} (stratified sub-sample) | Δ (pp) |
|---|---|---|---|
| AUC-ROC (%) | 99.643 | 99.659 | +0.016 |
| TPR at 0.1% FPR, test-tuned (%) | 86.81 | 85.49 | -1.32 |
| TPR at 1% FPR, test-tuned (%) | 96.50 | 96.23 | -0.26 |

| Month | Benign / malware | FNR @θ0.1% (%) | FPR @θ0.1% (%) | F1 @π=10%, θ0.1% (%) | FNR @θ0.5% (%) | FPR @θ0.5% (%) | AUC-ROC (%) |
|---|---|---|---|---|---|---|---|
| May–Jun 2018 (cal) | 5,898 / 6,054 | 51.72 | 0.017 | 65.06 | 28.10 | 0.339 | 98.666 |
| Jul 2018 | 3,066 / 2,969 | 52.48 | 0.033 | 64.30 | 27.89 | 0.457 | 99.071 |
| Aug 2018 | 3,098 / 3,042 | 59.50 | 0.032 | 57.53 | 33.23 | 0.226 | 98.343 |
| Sep 2018 | 3,050 / 2,918 | 72.48 | 0.066 | 42.96 | 42.70 | 0.492 | 97.385 |
| Oct 2018 | 2,941 / 2,970 | 61.48 | 0.272 | 54.65 | 36.03 | 1.156 | 97.198 |
| Nov 2018 | 2,995 / 2,983 | 58.13 | 0.100 | 58.65 | 31.01 | 0.835 | 97.556 |
| Dec 2018 | 3,012 / 2,938 | 66.68 | 0.066 | 49.76 | 38.97 | 1.162 | 96.665 |

| Corroboration check | Result |
|---|---|
| Within-EMBER temporal AUT(F1@π=10%) (%), θ@0.1% / θ@0.5% | 54.17 / 75.60 |
| SVR at (0.5%, 5%), Jul–Dec 2018 | θ@0.1%: 0/6; θ@0.5%: 0/6 |
| Random-split inflation (5 seeds), F1@π=10% vs temporal AUT | +19.86 pp [18.17, 21.81] |
| Forward transfer: EMBER-trained (Jan–Apr 2018) → BODMAS Mar–Sep 2020, AUT(F1@π=10%) (%) | 77.61; monthly FNR 22.4–58.3% |
| Backward application: f₀ (BODMAS 2019) → EMBER 2018, monthly AUC-ROC (C1-violating, descriptive) | 73.4–93.0% |
| SHA-256 overlap between the EMBER sub-sample and BODMAS | 4 files |

Month-stratified sub-sample of the EMBER-2018 labelled release vectorised with the EMBER v2 extractor (72,009 files, about 3,000 per class per month). Within-EMBER protocol mirrors TRACE-PE: train January–April, calibrate May–June (CP-certified θ), test July–December monthly. The release-notebook values are computed on the full 200,000-file test set with test-tuned thresholds; ours on the stratified Nov–Dec sub-sample.


**Table 15. Comparison with existing methods and published baselines: absolute (pp) and relative differences**

| Metric | Published source | Published value | This work | Δ absolute (pp) | Δ relative | Protocol note |
|---|---|---|---|---|---|---|
| Monthly F1 (%), range | [1] T. II, EMBER-GBDT | 92.14–97.76 {RfP} | 98.09–99.51 {MoC} | +5.95 / +1.75 | +6.5% / +1.8% | [1]: GBDT trained by [1] on EMBER (5 seeds), threshold at 0.1% FPR on its own validation split, Oct 2019–Sep 2020; ours: the published EMBER-2018 model file, threshold at the 0.1% empirical quantile of BODMAS Dec 2019 benign, Mar–Sep 2020 Dated (realised pooled FPR 0.193%) |
| Monthly F1 (%), range | [1] T. II, EMBER-GBDT | 92.14–97.76 {RfP} | 88.65–98.27 {MoC} LGBM-TRACE, 5-seed mean | -3.49 / +0.51 | -3.8% / +0.5% | LGBM-TRACE trained on BODMAS Aug–Nov 2019 at [1]'s operating point (0.1% empirical on Dec 2019) |
| Monthly F1 (%), range | [1] T. II, EMBER-GBDT | 92.14–97.76 {RfP} | 82.93–96.82 {MoC} LGBM-TRACE, 5-seed mean | -9.21 / -0.94 | -10.0% / -1.0% | LGBM-TRACE at the CP-certified 0.1% threshold (k* = 1) |
| Monthly F1 (%), range | [1] T. II, SOREL-GBDT | 95.70–98.94 {RfP} | 82.93–96.82 {MoC} LGBM-TRACE, 5-seed mean | -12.77 / -2.12 | -13.3% / -2.1% | SOREL-20M-trained GBDT ([1]) vs LGBM-TRACE certified |
| Monthly FNR (%), range | [1] T. III | 1.71–7.23 {RfP} | 1.91–20.45 {MoC} | +0.20 / +13.22 | +11.5% / +182.9% | T0 replication, Dated: [1]'s protocol on our strata |
| Monthly FPR (%), range | [1] T. III | 0.00–0.51 {RfP} | 0.000–0.108 {MoC} | +0.00 / -0.40 | — / -78.9% | T0 replication, Dated |
| Max monthly FNR, unseen families (%) | [1] T. III | 43.04 {RfP} | 42.17 {MoC} | -0.87 | -2.0% | T0 replication, Dated |
| Monthly FNR (%), range | [1] T. III | 1.71–7.23 {RfP} | 1.19–3.43 {MoC} | -0.52 / -3.80 | -30.5% / -52.6% | T0 replication, Dated + PreWindow: [1]'s protocol on our strata |
| Monthly FPR (%), range | [1] T. III | 0.00–0.51 {RfP} | 0.000–0.119 {MoC} | +0.00 / -0.39 | — / -76.6% | T0 replication, Dated + PreWindow |
| Max monthly FNR, unseen families (%) | [1] T. III | 43.04 {RfP} | 29.09 {MoC} | -13.95 | -32.4% | T0 replication, Dated + PreWindow |
| Monthly FNR (%), range | [1] T. III | 1.71–7.23 {RfP} | 5.07–29.05 {MoC} LGBM-TRACE, 5-seed mean | +3.36 / +21.82 | +196.7% / +301.9% | LGBM-TRACE certified, Jan–Sep 2020 |
| F1 (%), random split | [1] T. II, EMBER-GBDT validation | 98.62 {RfP} | 98.03 {MoC} LGBM-TRACE random arm, 5 seeds | -0.59 | -0.6% | random split inflates both; ours: BODMAS random 5-seed arm |
| F1 (%) | [94] D3QN, BODMAS | 98.64 {RfP} | 90.98 {MoC} LGBM-TRACE temporal AUT, 5-seed mean | -7.66 | -7.8% | [94] reports no temporal split; ours: temporal AUT, native ratio |
| F1 (%) | [94] D3QN, EMBER-2018 | 85.07 {RfP} | 75.60 {MoC} within-EMBER AUT, θ@0.5% | -9.47 | -11.1% | different protocol; π = 10% re-weighting |
| AUC-ROC (%) | EMBER-2018 release notebook [2] | 99.64 {RfP} | 99.66 {MoC} | +0.02 | +0.0% | same published model; full test set vs our stratified sub-sample |
| TPR at 0.1% FPR (%) | EMBER-2018 release notebook [2] | 86.81 {RfP} | 85.49 {MoC} | -1.32 | -1.5% | test-tuned threshold in both |
| TPR at 0.1% FPR (%) | [2] EMBER-2017 LightGBM | 92.99 {RfP} | 84.12 {MoC} LGBM-TRACE, 5-seed mean | -8.87 | -9.5% | EMBER-2017 test set, test-tuned threshold, vs LGBM-TRACE on BODMAS Mar–Sep 2020 at a threshold fixed on December 2019 |
| Malware regressing after an update (%) | [30] Ghiani, Android CL | 3.00–6.00 {RfP} | 0.023 {MoC} naive re-scoring | -2.98 / -5.98 | -99.2% / -99.6% | [30]: continual-learning Android detectors; ours: monthly full retraining of LGBM-TRACE, BODMAS PE, findings of the 30 d before each of 7 updates, certified 0.5% thresholds, abstained findings included |
| Goodware flips per update (%) | [89] Kozák, full AT | 1.22 {RfP, computed from counts} | 0.174 {MoC} naive re-scoring | -1.046 | -85.8% | [89]: EMBER-GBDT after full adversarial retraining; ours: benign findings turned malicious by the next monthly model |
| Malware flips per update (%) | [89] Kozák, full AT | 0.18 {RfP, computed from counts} | 0.023 {MoC} naive re-scoring | -0.157 | -87.3% | as above, malware findings turned benign; [89] denominator uncertain (27/14,997 = 0.18% as in S6; 27/1,785 = 1.51%) |

Δ = this work − published; relative Δ = Δ / published. Ranges are compared end-to-end (lower/upper). Protocols differ in training data, test months, base rate and operating point, as stated per row; rows with matched protocol are the release-notebook rows (same EMBER-2018 model file) and the T0 replication. LGBM-TRACE values are 5-seed means. {RfP} = reproduced-from-paper or release artifact; {MoC} = measured-on-Claude.


**Table 16. CPU cost per model (uncontended, sequential)**

| Model | Training (s) | Inference (µs per file) | Peak RSS (GB) |
|---|---|---|---|
| EMBER-2018 GBDT (published model) | 0.0 | 335.5 | 1.17 |
| Gaussian NB | 1.3 | 41.6 | 1.63 |
| LR + χ²(256) | 2.1 | 21.6 | 1.78 |
| LR | 3.1 | 25.9 | 1.63 |
| k-NN (PCA-50) | 3.9 | 81.5 | 1.63 |
| LR + IG(256) | 4.7 | 26.9 | 1.57 |
| LR + PCA(0.95) | 16.2 | 52.5 | 2.11 |
| RBF-SVM (PoC, 10k) | 26.7 | 3,306.2 | 1.80 |
| MLP (PoC, 20k) | 26.7 | 54.9 | 1.67 |
| Extra trees | 29.1 | 53.5 | 1.00 |
| LGBM-TRACE (f₀ family) | 35.8 | 13.4 | 1.39 |
| Random forest | 53.5 | 40.7 | 0.98 |
| LR + mRMR(128) | 76.3 | 17.3 | 1.83 |
| Linear SVM | 78.1 | 32.3 | 2.38 |
| XGBoost | 82.2 | 9.9 | 1.81 |
| Temporal stacking | 121.7 | 69.9 | 1.90 |
| LGBM-EMBER | 151.7 | 102.5 | 2.37 |

Training window 23,158 × 2,381 (S7); inference on 20,000 rows. Intel Xeon @ 2.10 GHz, 2 vCPU, Python 3.13.16, LightGBM 4.7.0, XGBoost 3.4.1, scikit-learn 1.9.1. One run per model; the published EMBER-2018 model is scored only; RBF-SVM values come from its E1 run (10,000-row training sub-sample, 97,436 rows scored); the MLP was re-timed after D17. {MoC}.


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
