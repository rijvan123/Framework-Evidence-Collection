#!/bin/bash
export OMP_WAIT_POLICY=PASSIVE
cd /home/claude/s10/code
while kill -0 1369 2>/dev/null; do sleep 10; done
step(){ echo "=== $(date -u +%H:%M:%S) START $*"; "$@" > /home/claude/s10/out/log_$(echo "$*" | tr ' /' '__').txt 2>&1; echo "=== $(date -u +%H:%M:%S) END $* rc=$?"; }
step python3 s10_e5_bias.py t0
step python3 s10_analysis.py bias
step python3 s10_reval_analysis.py
echo "=== Q3 DONE $(date -u +%H:%M:%S)"
