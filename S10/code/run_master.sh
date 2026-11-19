#!/bin/bash
# Master sequential queue (2 vCPU; one OpenMP job at a time).
export OMP_WAIT_POLICY=PASSIVE
cd /home/claude/s10/code
while kill -0 821 2>/dev/null; do sleep 5; done
step(){ echo "=== $(date -u +%H:%M:%S) START $*"; "$@" 2>&1 | tail -40; echo "=== $(date -u +%H:%M:%S) END $*"; }
e1(){ echo "=== $(date -u +%H:%M:%S) START e1 $1 $2"; python3 s10_e1_run.py $1 $2 2>&1 | tail -1; echo "=== $(date -u +%H:%M:%S) END e1 $1 $2"; }
step python3 s10_monitor.py
step python3 s10_reval.py ptr
step python3 s10_reval.py models 30 1.0
for mdl in knn lr_mrmr; do e1 $mdl 0; done
for s in 11 23 37 41 53; do e1 et $s; done
for s in 11 23 37 41 53; do e1 rf $s; done
step python3 s10_reval.py sim 30 1.0
for s in 11 23 37 41 53; do e1 lgbm_ember $s; done
for s in 11 23 37; do e1 mlp $s; done
for s in 11 23 37 41 53; do e1 stack $s; done
step python3 s10_reval.py models 60 1.0
step python3 s10_reval.py sim 60 1.0
step python3 s10_reval.py models 90 1.0
step python3 s10_reval.py sim 90 1.0
step python3 s10_reval.py models 30 0.5
step python3 s10_reval.py sim 30 0.5
for x in random t0 no626 prewin norm leak cv; do step python3 s10_e5_bias.py $x; done
e1 svm_rbf 11
echo "=== MASTER DONE $(date -u +%H:%M:%S)"
