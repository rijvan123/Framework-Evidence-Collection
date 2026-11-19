# TRACE-PE: forensic evidence framework for static ML malware detection (Windows PE)

Code, outputs and evidence ledger for R. Beg, "A Forensic Evidence Framework for Static Machine-Learning-Based Malware
Detection in Windows PE Files" (submitted manuscript). Release v1.1 corresponds to the revised manuscript.

## Contents

| Path | What it is |
|---|---|
| `S10/` | The original run that produced every number in the paper, unchanged: experiment scripts and run queues (`code/`; configuration constants in `code/s10_common.py`), the prespecified protocol (`S10_protocol.md`), all result files including the simulation outputs with certificate tables and per-event summaries (`out/`), execution logs (`out/logs/`), generated tables and figures, and the run report (`S10_OUTPUT.md`). |
| `S10_ledger.jsonl.gz` | The sealed evidence ledger: 212,279 records, final chain head `9ba9f46dc0bba2a0…`, file SHA-256 `321b4e622083af76a36f6f1c72aa155ed20b8f221bdb9f1a63365c7f174d3804`. Its REPORT records bind 186 files of `S10/` by SHA-256. |
| `revision/` | Scripts that computed the analyses added in revision (Appendix A, Tables A1–A5) and redrew Figs. 6, 11, 12 and 17, and `verify_release.py`, which checks this release. |
| `reconstruction/` | A consolidated reimplementation written after the study and run end to end only on synthetic data. It is not the source of any reported number; see `reconstruction/README.md`. |

## Verify the release

```
pip install numpy scipy pandas cryptography
python revision/verify_release.py --ledger S10_ledger.jsonl.gz --package S10 --out verify_out
```

Expected: the hash chain and all 16 epoch Merkle roots verify; 16 of 16 anchor signatures are valid; 186 of the 187
files bound by REPORT and DOC records match (the exception is `out/log_ledger_final.txt`, bound while still empty; logs
are stored under `S10/out/logs/` and are found by file name); the statement-validity check prints `(equal)`.

The anchor key is derived from a public seed and the time-stamping authority was simulated, so valid signatures show
that the chain is intact, not that it could not have been forged.

## Data

BODMAS is distributed by its authors; EMBER-2018 and SOREL-20M are public. Trained model files and per-model score arrays
are not included: the code in `S10/code/` regenerates them deterministically from BODMAS, and the regenerated models can be
checked against the model identities and Merkle roots recorded in the ledger.

## Licence and citation

MIT licence (`LICENSE`); the datasets keep their own licences. Citation metadata: `CITATION.cff`.
