#!/bin/bash
# Follow-up queue (v2): waits for the q4 runner (PID 223); re-runs the memory-safe leak and norm arms (first versions
# OOM-killed), flips for all label-delay scenarios, an uncontended learning-curve rerun, tables, figures and the summary.
export OMP_WAIT_POLICY=PASSIVE
cd /home/claude/s10/code
O=/home/claude/s10/out
while kill -0 223 2>/dev/null; do sleep 20; done
step(){ echo "=== $(date -u +%H:%M:%S) START $*"; "$@" > $O/log_$(echo "$*" | tr ' /,' '___').txt 2>&1; echo "=== $(date -u +%H:%M:%S) END $* rc=$?"; }
need(){ [ ! -s "$1" ]; }
need $O/e5_leak.json && step python3 s10_e5_bias.py leak
need $O/e5_norm.json && step python3 s10_e5_bias.py norm
step python3 s10_flips.py L30_rho1.0 L60_rho1.0 L90_rho1.0 L30_rho0.5
step python3 s10_lc_timing.py lc
step python3 s10_tables.py
step python3 s10_plots.py
step python3 s10_summary.py
echo "=== Q5 DONE $(date -u +%H:%M:%S)"
