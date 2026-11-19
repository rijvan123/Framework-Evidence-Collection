#!/bin/bash
# Re-prioritised sequential queue (replaces run_master.sh after the monitor, PTR and L30 models finished).
export OMP_WAIT_POLICY=PASSIVE
cd /home/claude/s10/code
while kill -0 1345 2>/dev/null; do sleep 5; done
step(){ echo "=== $(date -u +%H:%M:%S) START $*"; "$@" > /home/claude/s10/out/log_$(echo "$*" | tr ' /' '__').txt 2>&1; echo "=== $(date -u +%H:%M:%S) END $* rc=$?"; }
e1(){ step python3 s10_e1_run.py $1 $2; }
step python3 s10_reval.py sim 30 1.0
for s in 23 37 41 53; do e1 et $s; done
for s in 11 23 37 41 53; do e1 rf $s; done
for x in random t0 no626 prewin; do step python3 s10_e5_bias.py $x; done
step python3 s10_e1_eval.py
step python3 s10_analysis.py certificates strata baserate calibration errors models drift lr bias
step python3 s10_attr.py
step python3 s10_explain.py
step python3 s10_ledger_tests.py
step python3 s10_ember.py
step python3 s10_lc_timing.py lc
for s in 11 23 37; do e1 lgbm_ember $s; done
for s in 11 23 37; do e1 mlp $s; done
for s in 11 23 37; do e1 stack $s; done
step python3 s10_reval.py models 60 1.0
step python3 s10_reval.py sim 60 1.0
for x in norm leak cv; do step python3 s10_e5_bias.py $x; done
step python3 s10_reval.py models 30 0.5
step python3 s10_reval.py sim 30 0.5
step python3 s10_reval.py models 90 1.0
step python3 s10_reval.py sim 90 1.0
step python3 s10_lc_timing.py timing
e1 svm_rbf 11
step python3 s10_e1_eval.py
step python3 s10_analysis.py
echo "=== Q2 DONE $(date -u +%H:%M:%S)"
