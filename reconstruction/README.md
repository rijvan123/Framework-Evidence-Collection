# Consolidated reimplementation (not the code behind the paper's numbers)

This folder holds a consolidated reimplementation of the TRACE-PE pipeline that was written after the study and run end
to end only on synthetic data. It is kept for reference. Every number reported in the paper comes from the original run
in `S10/`, whose files are bound by SHA-256 in the released evidence ledger (`python revision/verify_release.py`).

Known differences from the original run:

* Update rule: the reimplementation trains each monthly update only on rows dated before its calibration month; the
  original run trains on all dated rows whose labels have matured (first seen at least 30 days before the update),
  excluding only the calibration month (paper, Section 7.6 and Table A2).
* Certificate freshness: `statement_valid` checks the age of the newest available certificate only; the analysis checks
  the age of the freshest FPR bound and of the freshest FNR bound separately (paper, Section 7.6 and Table A3).
