# Revision scripts (TRACE-PE, revised manuscript)

These scripts produced every number and figure added in the revision. They read only the released run package
(`S10/`) and the evidence ledger; no model is re-fitted and no BODMAS file is read.

| Script | Produces | Inputs |
|---|---|---|
| `verify_release.py` | chain, Merkle-root and anchor-signature check of the ledger; size and SHA-256 check of every file bound by a REPORT or DOC record; Table A2 (model-update chronology); Table A3 (daily statement validity, expiry and renewal events); self-tests of the per-bound freshness rule | ledger, package folder |
| `revision_stats.py` | exact Clopper–Pearson intervals and Eq. (101) precision bounds (Tables 12, 13, 16; Fig. 6 text), Bonferroni-14 and design-effect bounds (Table A5), overdispersion, Holm adjustment (D19) | `out/e1_metrics.pkl` |
| `revision_extra.py` | pooled f₀ counts, chronology, validity segments (Table A3), errors and coverage among issued findings (Table A4), exposure under daily re-checking (84 finding-days) | ledger, `out/reval_L30_rho1.0.pkl`, `out/e1_metrics.pkl` |
| `make_figs.py` | redrawn Figs. 6, 11, 12 and 17 (values copied from the run's tables and outputs) | none (values in the script) |

## Run

```
python verify_release.py --ledger S10_ledger.jsonl.gz --package S10 --out verify_out
python revision_stats.py S10/out/e1_metrics.pkl revision_stats.json
python revision_extra.py S10_ledger.jsonl.gz S10/out/reval_L30_rho1.0.pkl S10/out/e1_metrics.pkl revision_extra.json
python make_figs.py
```

Python 3.10 or later with numpy, scipy, pandas and matplotlib; `cryptography` for the anchor signatures.

## Expected results

* 212,279 ledger records; chain and all 16 epoch Merkle roots verify; 16 of 16 anchor signatures valid; final head
  `9ba9f46dc0bba2a019c96cdf5d3bd8ba2f840a78fe2d43a4b3cea2028c3f0e39`; ledger file SHA-256
  `321b4e622083af76a36f6f1c72aa155ed20b8f221bdb9f1a63365c7f174d3804`.
* 186 of the 187 bound files match. The exception is `out/log_ledger_final.txt`, which was bound while still empty.
* Table A3: the statement is invalid from 1 March to 29 April 2020 (freshest FPR bound older than 60 days) and on
  30 September 2020 (August FPR bound above 0.5%); renewal on 30 April 2020. The 18,279 findings issued on invalid
  days equal the simulation's screening-only count with certificate gating.

## Notes

* The anchor key is derived from a public seed (`S10-simulated-anchor-key`) and the time-stamping authority was
  simulated, so valid signatures show that the chain and roots are intact, not that the records could not have been
  forged.
* The freshness rule checked here is the one of the manuscript (Section 7.6): each error rate is judged on its own
  freshest bound, which must be within tolerance and at most 60 days old. The consolidated reimplementation kept in
  `reconstruction/` is a separate, later rewrite; it is not the source of any reported number.
