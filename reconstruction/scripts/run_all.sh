#!/usr/bin/env bash
# Run the complete pipeline in dependency order. Usage: bash scripts/run_all.sh [config.yaml]
# On the real data this takes several hours on 2 vCPU (estimate from the paper's run: 4.65 h of summed
# wall-clock for the queued steps, plus intake, EMBER-2018 vectorisation and figure generation).
set -euo pipefail
CFG="${1:-configs/default.yaml}"
cd "$(dirname "$0")/.."
PY="${PYTHON:-python}"
run() { echo; echo "=== $1"; shift; "$PY" "$@" --config "$CFG"; }
run "E0 intake and screen"            scripts/e00_intake.py
run "E1 model zoo"                    scripts/e01_zoo.py
run "E1 evaluation"                   scripts/e01_evaluate.py
run "E2 certificates"                 scripts/e02_certificates.py
run "E3 calibration and cost"         scripts/e03_calibration.py
run "E4 bias controls"                scripts/e04_bias.py
run "E5 error structure and drift"    scripts/e05_errors_drift.py
run "E6 label-free monitor"           scripts/e06_monitor.py
run "E7 assurance plane"              scripts/e07_assurance.py
run "E8 attribution leg"              scripts/e08_attribution.py
run "E9 explanations and issuance"    scripts/e09_explain_issue.py
run "E10 ledger tests"                scripts/e10_ledger_tests.py
run "E11 EMBER-2018 corroboration"    scripts/e11_ember2018.py
run "E12 cost and learning curves"    scripts/e12_cost_learning.py
run "E13 statistics"                  scripts/e13_statistics.py
run "E14 comparison"                  scripts/e14_compare.py
run "E15 register and decision"       scripts/e15_register.py
run "tables"                          scripts/make_tables.py
run "figures"                         scripts/make_figures.py
run "seal ledger"                     scripts/seal_ledger.py
run "verify ledger"                   scripts/verify_ledger.py
echo; echo "done: outputs in $("$PY" -c "import sys; sys.path.insert(0,'src'); from tracepe.config import load_config, resolve; print(resolve(load_config(['$CFG'])['run']['dir']))")"
