# Implementation notes

This repository is a consolidated re-implementation of the paper's design (S7), analytical model (S8),
harness specification (S9) and locked protocol (S10 Part 0, `docs/PREREGISTRATION.md`). It is organised
by experiment (E0–E15) rather than by the file layout of the paper's original run scripts. Where the paper
fixes a definition, the code follows it; where the paper leaves a detail open, the choice made here is listed
below (marked *impl.* in `configs/default.yaml`). These choices can move model-dependent numbers; they cannot
move the exact checkpoints of `results/paper_reference.json`.

## Evidence layer

* **Constructions** follow S7.1–S7.3 and the S7 probe code; `tests/test_screen_and_intake.py` runs E0 on a
  synthetic release and checks that the acquisition-chain head and the oracle Merkle root equal those of a
  verbatim transcription of the probe code (`tests/s7_reference.py`).
* **Float encoding.** Records carry reals as big-endian IEEE-754 hex. The S7 probe helper
  `np.float32(v).astype('>f4').tobytes()` silently produces native (little-endian) bytes because numpy
  scalars ignore byte order; the helpers here encode through a one-element array and are big-endian as
  documented. No reported number depends on this encoding.
* **Epochs.** Each stage closes its own epoch (`e0-intake`, `e1-zoo`, `e2-certificates`, `e7-assurance`,
  `iss-<month>`, `report`). A stage whose epoch is already anchored recomputes its outputs but does not append
  again, so re-running a step never duplicates evidence.
* **Store.** Models are stored in a content-addressed, read-only object store. LightGBM models are stored as
  model text; scikit-learn and XGBoost models as pickles, which are loaded only after their SHA-256 has been
  verified. Do not load a store from an untrusted source.
* **Simulated infrastructure.** The time-stamping authority is a local Ed25519 key with wall-clock time
  (`tsa: "simulated"`); WORM storage is emulated (LEDGER.md, non-guarantees N1–N5).

## Screen and split

* Spike-day benign files are **Placeholder** when at least 99% of them sit at 00:00:00 on that day,
  otherwise **Bulk** (*impl.*; on BODMAS this separates 2020-01-01 from the two February days).
* **Quarantine** = identifier not a 64-hex SHA-256 digest, or a row failing an intake invariant (no row fails
  on BODMAS; the 7 quarantined rows are VirusShare names).
* Duplicate vectors: the earliest row is kept; a calibration or test row whose vector occurs in an earlier
  split would be dropped from evaluation (none on BODMAS). Near-duplicates (cosine distance δ ∈ {10⁻⁶, 10⁻⁴,
  10⁻²}) are counted with blocking on the GeneralFileInfo signature (*impl.*).
* Intra-day order is lexicographic in SHA-256, so that order cannot leak the class.

## Models (E1)

* f₀ = LGBM-TRACE, seed 11: 200 rounds, 63 leaves, learning rate 0.05, feature fraction 0.5, bagging 0.8/1,
  min_data_in_leaf 20, `deterministic`, `force_row_wise`, 2 threads, `max_bin` 255, trained on the training
  rows in file order — the S7 probe configuration. Model identity = SHA-256 of the tree section of the model
  text (independent of the file header).
* *impl.*: XGBoost (400 trees, depth 8, η 0.1, subsample 0.8, colsample 0.5, `hist`), linear SVM C = 0.1,
  k-NN k = 10 on PCA-50, MLP one hidden layer of 256 on a 20,000-row stratified sub-sample, RBF-SVM on 10,000
  rows, temporal stacking with three time blocks (base learners LGBM-TRACE, extra trees with 100 trees, LR;
  logistic meta-learner on later blocks only). Linear models use a signed log1p transform and standardisation
  fitted inside the training window; IG and mRMR use 10 training-quantile bins.
* MLP scores are float64 logits of the output unit (deviation D17 of the paper).
* Seeds: {11, 23, 37, 41, 53} for LGBM-TRACE, XGBoost, RF and ET; {11, 23, 37} for LGBM-EMBER, MLP and
  stacking (D14); deterministic models one fit.

## Thresholds, certificates, metrics

* Certified threshold (S7.5): k* = largest k with the one-sided 95% Clopper–Pearson upper bound ≤ τ;
  θ = (k*+1)-th largest benign calibration margin; verdict malicious iff margin > θ. Empirical rule: θ = the
  (⌊βn⌋+1)-th largest benign score, allowing ⌊βn⌋ calibration false positives.
* FPR-dependent statements require ≥ 500 dated benign files in the month (n_min); table cells require ≥ 100.
* Metrics at prevalence π use the benign re-weighting of Eq. (70), algebraically equal to Eq. (55) (tested).
  F1 is undefined (reported as "—") when a model flags nothing.
* Bootstrap intervals of single fits are stratified binomial (B = 1,000); AUC intervals are DeLong, truncated
  to [0, 1].

## Calibration, drift and monitor

* Calibrators (isotonic, Platt) and ICE credibility are fitted on December 2019. κ is the largest value with
  ≤ 5% December abstention; per-class κ for the Transcendent baseline at 10% December rejection (D9).
* JS drift: 20 training-quantile bins per feature, base 2, averaged per EMBER group and weighted by group size.
* Monitor M8: weekly windows from 1 March; model-free statistics (PSI with 10 bins, C2ST = out-of-fold
  LightGBM AUC with 2 folds) against 86 sliding windows of October–December, model-dependent statistics (KS on
  margins, 1 − mean credibility) against 25 December windows (D1), per predicted class, COFF timestamp
  excluded; λ = maximum over the null; alarm after P = 2 consecutive windows with any exceedance, re-armed by a
  window without one. Page–Hinkley δ = 0.005 (*impl.*). Onset = first week with an unseen-family share > 5%
  from July.
* ACI: α = 10%, γ = 0.005; an alarm is raised when the miscoverage of the batch whose labels arrive that day
  exceeds α + 3·SE (*impl.*; the paper reports alarm counts without fixing this rule).

## Assurance-plane simulation (E7)

* Universe: Dated rows; issuance 1 March–30 September 2020, horizon 31 October; events on the first day of
  April–October. Each retrained issuer uses as calibration month m_cal the latest month that has fully matured
  (month end + L ≤ event) and has ≥ n_min covered benign files, and is trained on all matured rows before m_cal
  (*impl.*: the calibration month stays out of training).
* Certificates of an issuer become available at month end + L; the calibration month's certificate at the
  issuer's start. A prospective statement is valid when the latest available FNR bound and the latest powered
  FPR bound are within tolerance and the newest certified month is at most A_max = 60 days old. A statement whose
  issue-month certificate later fails expires (state EXP) when that certificate becomes available (*impl.*).
* Reconciliation at t + L sets the verdict to the matured label, except for findings reviewed by an analyst
  (Algorithm 6 as specified); `override=True` gives the oracle-overrides-analyst variant.
* Region selection uses a LightGBM domain classifier (window vs October–December reference) for the density
  ratio (S7.9); review order (q ↓, credibility ↑, identifier ↑) (S7.12); the PCT-adapted baseline warm-starts
  LightGBM with weight 2 on rows the previous model classified correctly (D9).
* KB1 compares the monthly sums of U(t) (all live wrong findings) of TRACE-PE and lowest-margin review;
  KS2 bounds harmful auto-amendments per update with the in-scope findings as denominator (D4).
* γ is chosen by the pre-test replay on 2019 data (D11) as the smallest grid value whose CP bound on harmful
  auto-amendments is ≤ τ_H.

## Comparisons and figures

* `e14_compare.py` uses native-ratio F1 when comparing with published F1 values (the published values are
  native); F1 at π = 10% elsewhere.
* The literature coverage figure (Fig. 22) is drawn from the author coding in `figures/literature/s11_rows.json`
  (labelled {Est} in the paper); row labels name the works, the citations are in the paper.

## Known behaviour worth knowing

* LightGBM is **not** exactly invariant to affine rescaling of features: its histogram binning treats exact
  zeros specially, so a shift can move bin boundaries (the paper's P9 result, 99.89–99.90% agreement).
* The synthetic generator is tuned so that every code path runs (including the July drift, certificate failures
  and abstentions); it is not a model of BODMAS.
