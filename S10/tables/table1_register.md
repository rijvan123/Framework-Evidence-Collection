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
