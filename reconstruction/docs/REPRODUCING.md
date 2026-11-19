# Reproducing the paper

## 1. Environment

The paper's run used Python 3.13.16, NumPy 2.5.3, pandas 3.0.5, SciPy 1.18.1, scikit-learn 1.9.1,
LightGBM 4.7.0, XGBoost 3.4.1 on an Intel Xeon @ 2.10 GHz with 2 vCPU and about 8 GB RAM, no GPU.
`requirements-lock.txt` pins these versions.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-lock.txt && pip install -e ".[test]"
pytest                      # unit tests, a few seconds
```

LightGBM models are trained with `deterministic=True`, `force_row_wise=True`, `num_threads=2` and
`max_bin=255`, on the training rows in file order (as in the S7 probes). With the same LightGBM version the
tree section of f₀ — and therefore its model identity and every margin — is reproducible bit for bit; the
paper's cross-environment check (KB3) found identical tree hashes and scores under Python 3.10/NumPy 2.2 and
Python 3.13/NumPy 2.5 with LightGBM 4.7.0. Other libraries (scikit-learn, XGBoost) are deterministic for a
fixed seed and version but not across versions.

## 2. Data

Place the BODMAS files in `data/bodmas/` and, optionally, EMBER-2018 in `data/ember2018/`
([DATA.md](DATA.md)). Intake halts if a BODMAS digest differs from the paper's.

## 3. Run

```bash
bash scripts/run_all.sh                       # configs/default.yaml, outputs in runs/paper/
python scripts/compare_to_paper.py            # writes runs/paper/out/compare_to_paper.{json,md}
```

`run_all.sh` runs E0 → E15, renders tables and figures, seals the ledger (one `REPORT` record per output
file and a final anchor) and verifies it. Each step can be run alone (`python scripts/e07_assurance.py
--config configs/default.yaml --skip noise streams`), and model fitting can be split
(`python scripts/e01_zoo.py --models lgbm_trace xgboost`). Steps that already wrote ledger records do not
append them again when re-run.

Run time on 2 vCPU: several hours. The paper reports 4.65 h of summed wall-clock for its queued steps
(including re-runs), plus intake, the EMBER-2018 vectorisation and figure generation {estimate from the
paper's run}. The slowest steps are the model zoo (five seeds of four ensembles, LGBM-EMBER with 2,048
leaves), the bias controls and the assurance simulation.

## 4. What must match, and what may differ

`results/paper_reference.json` lists two kinds of values.

**Exact checkpoints (148)** are deterministic functions of the released files and the pre-registered
definitions; `compare_to_paper.py` marks each as `match` or `MISMATCH`:

* file digests and sizes, matrix shape, class counts, family and category counts;
* timestamp formats (130,723 with offset / 3,712 without), the spike rule (396 days, median 297.5, MAD 74.5,
  threshold 1,042.5; spike days 2020-01-01: 5,987, 2020-02-19: 1,445, 2020-02-26: 2,435; the k = 4 rule adds
  2020-06-08 and 2020-06-30);
* strata, split and monthly counts with their Clopper–Pearson bounds; k* = 1 / 21 / 48 on December
  (6,120 benign); the empirical 0.1% rule's 6 allowed false positives (bound 0.1934%);
* duplicate audit (7 identical-vector groups, 134,428 unique vectors), COFF-timestamp audit, invariants;
* the acquisition-chain head `0dcfe96d…e7939` and the oracle Merkle root `7dcfe2a8…bf98c`;
* the pre-registration digest `c783f8c4…c199c4`; a few pure counts computed later (June stream sizes under the
  two spike rules, December malware share, 68,876 issued findings, 77,417 ISS records).

`tests/test_screen_and_intake.py` runs E0 on a synthetic release and checks every one of these computations
(timestamps, spike rule, split, monthly counts and bounds, k*, duplicate and COFF audits, acquisition-chain head,
oracle root) against a verbatim transcription of the S7 probe code (`tests/s7_reference.py`), which produced the
paper's values on the real release.

**Model-dependent values (106)** — thresholds, monthly error rates, exposures, kill-criterion statistics,
timings — are reported with their differences and not judged. They depend on library versions, hardware
and the implementation choices of this re-implementation ([IMPLEMENTATION_NOTES.md](IMPLEMENTATION_NOTES.md)).

**Before publishing numbers produced with this code, run it on the real data and read
`out/compare_to_paper.md`.** A mismatch of an exact checkpoint means the input files or the screen differ; a
large difference in a model value deserves an explanation before it is reported.

## 5. Cross-environment re-execution (KB3)

```bash
# on machine A and on machine B, after E0 has populated the cache of the run
python scripts/xenv_fingerprint.py --config configs/default.yaml
# copy one JSON (and its scores file) to the other machine, then
python scripts/xenv_fingerprint.py --compare xenv/<A>.json xenv/<B>.json
```

KB3 is met when ≥ 99.9% of the 97,436 evaluation margins are bit-identical. `make_tables.py` adds the result to
Table 13 and `e15_register.py` to the register when `xenv/xenv_compare.json` exists.

## 6. Evidence reports and independent verification

```bash
python scripts/verify_ledger.py --config configs/default.yaml           # V1 chain/anchors + V2 objects
python scripts/report_finding.py --config configs/default.yaml --sid <sha256 of a test sample>
```

See [LEDGER.md](LEDGER.md).
