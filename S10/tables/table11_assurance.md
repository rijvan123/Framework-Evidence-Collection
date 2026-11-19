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
