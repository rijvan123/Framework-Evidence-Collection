#!/bin/bash
# Resumable queue after the container restart at ~15:48 (processes of run_q2/run_q3 were lost; finished outputs kept).
# Each step is skipped when its output already exists, so the queue can be re-launched safely.
export OMP_WAIT_POLICY=PASSIVE
cd /home/claude/s10/code
O=/home/claude/s10/out; K=/home/claude/s10/cache
step(){ echo "=== $(date -u +%H:%M:%S) START $*"; "$@" > $O/log_$(echo "$*" | tr ' /,' '___').txt 2>&1; echo "=== $(date -u +%H:%M:%S) END $* rc=$?"; }
need(){ [ ! -s "$1" ]; }
e1(){ need $K/scores/${1}_s${2}.json && step python3 s10_e1_run.py $1 $2; }
mods(){ need $K/reval_L${1}_rho${2}/models.pkl && step python3 s10_reval.py models $1 $2; }
sim(){ need $O/reval_L${1}_rho${2}.pkl && step python3 s10_reval.py sim $1 $2; }
bias(){ need $O/e5_$1.json && step python3 s10_e5_bias.py $1; }
need $O/timing_clean.json && step python3 s10_lc_timing.py timing      # first: uncontended timing (R5 training-time figure)
bias cv                                                               # R5 CV box plots
mods 60 1.0; sim 60 1.0
bias leak; bias norm; bias t0
mods 90 1.0; sim 90 1.0
mods 30 0.5; sim 30 0.5
for s in 11 23 37; do e1 lgbm_ember $s; done
for s in 11 23 37; do e1 mlp $s; done
for s in 11 23 37; do e1 stack $s; done
e1 svm_rbf 11
step python3 s10_e1_eval.py
step python3 s10_analysis.py certificates strata baserate calibration errors models drift lr bias
step python3 s10_reval_analysis.py
echo "=== Q4 DONE $(date -u +%H:%M:%S)"
