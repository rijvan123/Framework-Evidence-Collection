# Equations → code

Equation numbers (1)–(84) are those of the paper's analytical model; the definitions of the evidence layer and
the assurance plane are the S7 definitions (S7.1)–(S7.20), which the code docstrings number (85)–(104) in the
same order. "Library" means the objective is solved by the named library and is not re-implemented.

## Analytical model

| Eq. | Quantity | Code |
|---|---|---|
| (1)–(2) | evidence object; EMBER v2 feature map (nine groups, 2,381 dims) | `features.groups.GROUPS`, `data.ember.vectorize` |
| (3)–(4) | byte histogram; signed feature hashing | `data.ember` (`_fh`, scikit-learn `FeatureHasher`) |
| (5) | observed TPR/FPR under label noise η | `scripts/e03_calibration.py` (P11) |
| (6)–(8) | min–max, z-score; fit on the training window only | `features.preprocess`, model pipelines in `models.zoo`; violated on purpose in `e04_bias.py` (leakage arm) |
| (9)–(10) | binarised TF-IDF on hashed imports | not used in the experiments |
| (11) | invariance of exact trees to monotone maps | `e04_bias.py` (scaling arm, P9) |
| (12)–(18) | Shannon entropy, byte-entropy histogram | read from EMBER raw features (`byteentropy`), not recomputed from binaries |
| (19) | packing indicator pk(x) | `features.groups.packing_indicator`; `e05_errors_drift.py` (P10) |
| (20)–(22) | Euclidean, cosine, Jaccard | cosine in the near-duplicate audit (`e00_intake.py`) |
| (23) | cross-split de-duplication | `e00_intake.py` (duplicate audit, `dup_drop`) |
| (24)–(25) | Bayes rule; Gaussian NB | `models.zoo` (`gnb`) |
| (26)–(27) | sigmoid; softmax | `decision.calibration.sigmoid`; multiclass LightGBM in `e08_attribution.py` |
| (28)–(29) | Platt scaling; isotonic regression | `decision.calibration.Platt`, `Isotonic` |
| (30) | ECE (15 bins) | `decision.calibration.ece` |
| (31) | prior shift | `decision.calibration.prior_shift` |
| (32)–(39) | BCE, CE, hinge; SVM primal, kernels, RBF sub-sample | library (scikit-learn); sub-sampling in `models.zoo` |
| (40)–(42) | entropy, Gini, information gain | `features.preprocess.IGSelector` (binned mutual information); tree impurities: library |
| (43) | χ² feature score | `features.preprocess.chi2_steps` |
| (44) | mRMR (difference form) | `features.preprocess.MRMRSelector` |
| (45)–(49) | regularised boosting objective, second-order split gain | library (LightGBM, XGBoost) |
| (50) | convex ensemble weights | not used |
| (51) | temporally ordered stacking | `models.zoo.TemporalStack` |
| (52)–(54) | Bayes-cost decision, τ*, prevalence-adjusted odds | `decision.calibration.bayes_tau`; `e03_calibration.py` (P7, H6) |
| (55) | precision at prevalence π | `evaluation.metrics.precision_analytic` |
| (57) | expected cost | `decision.calibration.expected_cost` |
| (58) | empirical β-threshold | `decision.thresholds.empirical_threshold` |
| (59)–(61) | PCA by eigendecomposition of the standardised covariance | `features.preprocess.pca` (`svd_solver='covariance_eigh'`) |
| (62)–(63) | precision, TPR, FPR, FNR, F1, MCC | `evaluation.metrics.from_counts` |
| (64)–(65) | ROC AUC | `evaluation.metrics.auc`; DeLong in `evaluation.stats.delong` |
| (66) | average precision (at π via Eq. 70 weights) | `evaluation.metrics.auc_pr_at_pi` |
| (67) | macro-F1 | `e08_attribution.py` |
| (69) | AUT | `evaluation.metrics.aut` |
| (70) | benign re-weighting to prevalence π | `evaluation.metrics.benign_weight`, `from_counts` |
| (71)–(72) | unseen-family share; closed-world bound | `e08_attribution.py` |
| (73) | open-set attribution | `e08_attribution.py` (max-probability rejection at the December 5th percentile, as in the paper's table) |
| (74)–(75) | Jensen–Shannon drift per feature, per group, pooled | `drift.js` |
| (76)–(82) | hash chain, Merkle epochs, verification (S8 notation) | implemented as S7.1–S7.3 (see below; the protocol's reconciliation table fixes S7 as normative) |

## Evidence layer and assurance plane (S7 definitions)

| Def. | Code no. | Quantity | Code |
|---|---|---|---|
| S7.1 | (85) | canonical vector hash | `evidence.hashing.vector_hash`, `vector_hashes` |
| S7.2 | (86) | record hash and chain | `evidence.hashing.rec_hash`, `link`; `evidence.ledger.Ledger` |
| S7.3 | (87) | epoch Merkle tree and signed anchor | `evidence.merkle`; `Ledger.anchor`, `verify_ledger` |
| S7.4 | (88) | one-sided Clopper–Pearson bound | `decision.thresholds.cp_upper` |
| S7.5 | (89) | certified threshold (k*, θ) | `decision.thresholds.k_star`, `certified_threshold` |
| S7.6 | (90) | ICE credibility | `decision.conformal.ICE` |
| S7.7 | (91) | issuance state ISS / SCR / ABS | `e09_explain_issue.py`; `assurance.simulation.simulate` |
| S7.8–S7.12 | (92)–(96) | scope, density ratio, region, priority, outcome sets | `assurance.simulation` (`density_ratio`, `simulate`) |
| S7.13–S7.14 | (97)–(98) | error counts U, U^ev; exposures E_T, E^ev_T | `assurance.simulation.simulate`, `exposure_ci` |
| S7.15 | (99) | use-time error ε_Δ | not computed (not reported in the results) |
| S7.16 | (100) | review yield | `assurance.simulation.simulate` (`yield_`) |
| S7.17 | (101) | prevalence-conditional PPV bound | `decision.certificates.ppv_lower`; `scripts/report_finding.py` |
| S7.18 | (102) | statement-validity rate | `decision.certificates.svr`; `e02_certificates.py` |
| S7.19 | (103) | capped likelihood ratio | `decision.certificates.lr_cap` (Cllr: `cllr`) |
| S7.20 | (104) | prevalence weights | `decision.calibration.prevalence_weights`; prevalence streams in `evaluation.streams` |
