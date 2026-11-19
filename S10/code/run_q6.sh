#!/bin/bash
# q6: after q5 (PID 1730): re-score the MLP with float64 logits (first scores saturated to +inf), then rebuild E1 metrics,
# analyses, tables, figures and the summary.
export OMP_WAIT_POLICY=PASSIVE
cd /home/claude/s10/code
O=/home/claude/s10/out; K=/home/claude/s10/cache
while kill -0 1730 2>/dev/null; do sleep 20; done
step(){ echo "=== $(date -u +%H:%M:%S) START $*"; "$@" > $O/log_$(echo "$*" | tr ' /,' '___').txt 2>&1; echo "=== $(date -u +%H:%M:%S) END $* rc=$?"; }
mkdir -p $K/scores_mlp_inf && mv $K/scores/mlp_s*.npz $K/scores/mlp_s*.json $K/scores_mlp_inf/ 2>/dev/null
for s in 11 23 37; do step python3 s10_e1_run.py mlp $s; done
step python3 s10_e1_eval.py
step python3 s10_analysis.py certificates strata baserate calibration errors models drift lr bias
step python3 s10_tables.py
step python3 s10_plots.py
step python3 s10_summary.py
echo "=== Q6 DONE $(date -u +%H:%M:%S)"
