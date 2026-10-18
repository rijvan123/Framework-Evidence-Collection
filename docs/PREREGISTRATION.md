# S10 Part 0 — Reconciled, pre-registered protocol (locked before any test-period computation)

Locked: 2026-10-06, before any model was scored on a 2020 sample. The SHA-256 of this file is the first
PREREG record of the S10 ledger. Any later change is a logged deviation.

## 0.1 Precedence rule
S7 (`S7_OUTPUT.md`, measured on the real BODMAS release) governs design, strata, split and parameters.
S8 governs equations and the falsifiable predictions P1–P11. S9 governs the harness specification and
hypotheses H1–H10 where S7/S8 are silent. S6 kill criteria are retained unchanged except where S7 moved the
assurance-plane start to 2020-03-01 (fractions re-scaled, D3). S8 and S9 were written without access to S7;
their assumed module names, fallback split and placeholders are superseded.

## 0.2 Reconciliation table
| Item | S7 | S8 | S9 | S10 decision |
|---|---|---|---|---|
| Modules | M1–M13 | assumed M1–M8 | — | S7 M1–M13. S8 map: ACQ→M1, CUST→M4+ledger, FEAT→M3/M5, PREP→M5, DET→M6/M7, ATTR→M7 leg, DRIFT→M8, XREP→M7/M12 |
| Strata | Dated, Placeholder, Bulk, SpikeMal, Quarantine, PreWindow | — | — | S7 (counts reproduced, §0.5) |
| Split | train Dated < 2019-12-01; cal Dec-2019; test Jan–Sep 2020 | fallback (train ≤ Oct, cal Nov) | T1 (same windows), T0 (BODMAS replication) | S7 primary; T0 as BODMAS Table III replication only |
| Model seeds | — | {11, 23, 37, 41, 53} | {0..4} | {11, 23, 37, 41, 53}; evidentiary model f₀ = LGBM-TRACE seed 11 |
| Stream seeds | 20 | — | {100..109} | {100..119} |
| π grid | {1, 2, 5, 10}% (5, 10 measured) | {0.1, 0.5, 1, 5, 10}% + 42.62% | {1, 5, 10, 50}% | analytic {0.1, 0.5, 1, 2, 5, 10, 50}% + native; measured streams {1, 2, 5, 10}% × 20 seeds |
| Detector threshold | CP-certified, τ_FPR = 0.1% (k* = 1) | τ_β empirical; cost τ* | FPR 10⁻³/10⁻² on validation; F1@π* | primary CP-certified 0.1%; comparators: empirical 0.1% quantile ([1] protocol), CP 1%, 0.5, cost τ*(π, C), F1@π* |
| Calibration | isotonic on Dec | Platt + isotonic | sigmoid (SVM) | isotonic primary; Platt and prior-shift (Eq. 31) in P4 |
| Drift | KS, PSI, cred, PH, C2ST (monitor) | JS per group (Eqs. 74–75) | JSD + PSI | monitor per S7; JS per group for drift→decay (P5/H4) |
| Hash chain | S7.2 as implemented in S7_probes.py | Eq. 77 | h_i = H(h_{i−1}‖rec) | S7 implementation (domain-separated); S8 Eq. 77 notation to be aligned in S12 |
| Tamper test | functional | 10⁴ per type × 6 types; time n ∈ 10³..10⁶, slope ∈ [0.9, 1.1] | 1,000/1,000 | S8 (stricter) |
| Near-dup δ | 10⁻⁶ | 10⁻⁴ | — | 10⁻⁶ primary; counts at {10⁻⁶, 10⁻⁴, 10⁻²} |
| Hypotheses | kills + handoff predictions | P1–P11 | H1–H10 | unified register §0.3 |

## 0.3 Unified prediction and kill register
| U | Source | Statement | Decision rule |
|---|---|---|---|
| U1 | S8 P1 = S9 H1 | Random split inflates GBDT F1 vs temporal AUT | falsified if Δ < 2 pp or 95% CI includes 0 |
| U2 | S8 P2 = S9 H2 | Precision at π follows Eq. 55; Prec(0.1%) < 0.6 when realised FPR ≥ 0.1% | falsified if measured outside CI in > 20% of month×π cells |
| U3 | S8 P3 | Pre-split scaling/selection/PCA inflates AUC and AP@π for LR/SVM; scaling leak leaves trees unchanged | falsified if the selection leak is n.s. for every model |
| U4 | S8 P4 | Isotonic/Platt lower ECE; prior shift (Eq. 31) lowers Brier and EC at π ≤ 1% | falsified if CI of the reduction includes 0 |
| U5 | S8 P5 = S9 H4 | Spearman ρ(JS drift, F1) ≤ −0.5 | falsified if ρ ≥ 0 or CI upper > −0.1 |
| U6 | S8 P6 | Open-set macro-F1 declines faster than detection F1 | falsified if CI of slope difference includes 0 |
| U7 | S8 P7 = S9 H6 | τ* (Eq. 53/54) beats 0.5 on EC at C_FN/C_FP ∈ {10, 50, 100}, π ≤ 1% | falsified if EC(τ*) ≥ EC(0.5) at all ratios |
| U8 | S8 P8 = S9 H8 | Chain detects 100% of injected edits; verify time linear | any miss, or log–log slope ∉ [0.9, 1.1] |
| U9 | S8 P9 | Trees invariant to monotone scaling; LR/SVM/kNN not | any exact-tree disagreement |
| U10 | S8 P10 | FNR and FPR higher in the high-entropy stratum | Fisher OR CI includes 1 |
| U11 | S8 P11 | Observed TPR/FPR follow Eq. 5 under injected η ∈ {1, 5}% | prediction outside bootstrap CI |
| U12 | S9 H3 | Unseen-family FNR > known-family FNR | Wilcoxon over months, p_Holm < 0.05 and A12 > 0.71 |
| U13 | S9 H5 | GBDT leads on AUT | Friedman p < 0.05 and Kendall W ≥ 0.5 |
| U14 | S9 H7 | Open-set rejection raises open-set macro-F1 | Wilcoxon over months p < 0.05 |
| U15 | S9 H9 | No COFF-timestamp artefact | \|ΔAUT\| < 1 pp without feature 626 |
| U16 | S9 H10 | Calibration degrades over time | Spearman(month, ECE) ρ > 0 |
| K1 | S6 KILL-1 | Full re-scoring changes ≤ B in ≥ 75% of updates (6 of 7, D3) | → drop region-selection claim |
| K2 | S6 KILL-2 | CP-95% upper bound of h < 0.1% in every update | → drop harm-gating claim; K1 ∧ K2 → A2 fallback |
| K3 | S7 KILL-3 | L = 30 d: upper 95% CI of relative E^ev_T reduction vs (viii) < 10% | → withdraw re-validation claim (A2) |
| KT | S6/S7 trigger kill | an alarm within 14 d of July onset AND ≤ 1 false alarm in every stable month (Mar–Jun) | else scheduled re-validation; trigger claim withdrawn |
| KB1 | S6 Block 1 | TRACE-PE yield ≥ 1.5× lowest-margin (vii) and lower U(t) in ≥ 6 of 7 months | prediction |
| KB3 | S6 Block 3 | ≥ 99.9% bit-identical re-execution across two environments | else tolerance mode |
| KB4 | S6 Block 4 | static random 80:20 understates FPR or FNR vs temporal certificates in ≥ 5/7 months | else certificates = sanity table |
| KB5 | S6 Block 5 | censored stratum shifts monthly FPR > bootstrap half-width in ≥ 1 month | else I10 contribution dropped |
| KB7 | S6 Block 7 | sign of yield advantage holds at analyst noise r = 2% | else oracle-relative claims confined to r = 0 |
| KB9 | S6 Block 9 | ambiguity beats margin by ≥ 0.05 AUPRC for next-update flips | else I02 dropped |
| KB10 | S6 Block 10 | novel-family AUROC ≥ 0.80 and AUPRC ≥ 3× base rate (July) | else attribution leg dropped |
| KB11 | S6 Block 11 | Cliff's δ (stability: correct vs wrong) ≥ 0.147 | else stability not a gate |
| KB12 | S6 Block 12 | Cllr ≥ 1 in ≥ 3 months | → LR reporting moved to follow-on |
| KS1 | S7 handoff | SVR ≥ 6 of 7 months at τ_FPR = 0.5% | prediction |
| KS2 | S7 DR8 | CP upper bound of r_H ≤ τ_H = 0.5% per update | prediction |

## 0.4 Pre-registered parameters
κ: largest value with December abstention ≤ 5%; κ' = κ (D5). W = 7 d; P = 2; Ref = 2019-10-01..12-31 (86 sliding
windows) for model-free statistics. c_R = 10; ω = 1; B = ⌈1% of findings issued in the 30 days before the event⌉;
τ_H = 0.5%; (τ_FPR, τ_FNR) = (0.5%, 5%) for certificate validity in the simulation, (0.1%, 2%) sensitivity;
A_max = 60 d; n_min = 500; L ∈ {30, 60, 90} d (+ L = 0 analytic); ρ_L ∈ {1.0, 0.5}; Δ_use ∈ {7, 14, 30} d;
analyst noise r ∈ {0, 0.5, 1, 2}%; δ = 10⁻⁶; ε_num = 10⁻⁹; horizon T = 2020-10-31; events at the first day of
Apr..Oct 2020 (7) plus label-free alarms if KT passes; γ by pre-test replay (PTR) on 2019 data only.

## 0.5 Deviations and clarifications (logged before test computation)
| D | Item | Decision | Reason |
|---|---|---|---|
| D1 | Monitor reference for model-dependent statistics (KS on margins, credibility, Page–Hinkley) | December 2019 only (25 sliding null windows); model-free statistics (PSI, C2ST) keep Oct–Dec (86) | Oct–Nov margins are in-sample for f₀ and would bias the null |
| D2 | Baseline (viii) | matched counterfactual: same issuer-model sequence as TRACE-PE, no re-opening; frozen-f₀ variant reported as (viii-f) | isolates re-validation from model updating |
| D3 | "≥ 6/8 updates/months" (K1, KB1) | ≥ 75% of available updates/months = 6 of 7 | S7 moved the assurance start to 2020-03-01 |
| D4 | r_H denominator | harmful auto-amendments / \|S_a\| (as S6 h); per-amendment share also reported | consistency with K2 |
| D5 | κ' | κ' = κ | S7 lists κ' without a value |
| D6 | Prevalence-resampled streams | re-validators trained on the native matured stream; resampling applies to issued findings | CPU budget; approximation stated |
| D7 | Seeds | model {11, 23, 37, 41, 53}; stream {100..119} | S8 hand-off; S7's 20 seeds |
| D8 | Generic family tokens | regex rule: small, agent, vb, trojan, kryptik, win32, downloader, worm, malware, generic, cve-*, [a-z]{1,3}\d{4,}* | S6/S7 name examples only; heuristic, flagged |
| D9 | Baseline details | (ii) random order among changes; (iv) per-class ICE thresholds at December 10% rejection; (v) LightGBM warm start + 2× weight on previously-correct samples ("adapted"); (vii) margin under f_{v+1} | S6/S7 name the baselines without operational detail |
| D10 | EMBER-2018 corroboration | published EMBER-2018 LightGBM model scored on BODMAS (forward in time); within-EMBER temporal run on a vectorised month-stratified sub-sample if CPU allows | raw-feature CSVs only; no vectorised EMBER-2018 arrays exist locally |
| D11 | PTR design | f_PTR,0: train Aug 29–Sep 30, calibrate Oct 1–15, issue Oct 16–Nov 30; f_PTR,1 at Nov 30 (L = 30): train Aug 29–Oct 15, calibrate Oct 16–31; scope = Nov findings | S7 gives dates only |
