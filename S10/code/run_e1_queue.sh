#!/bin/bash
# Sequential E1 queue (2 vCPU). Each job is its own process (per-model peak RSS).
cd /home/claude/s10/code
run(){ echo "=== $(date -u +%H:%M:%S) START $1 $2"; python3 s10_e1_run.py $1 $2 2>&1 | tail -2; echo "=== $(date -u +%H:%M:%S) END $1 $2"; }
for s in 23 37 41 53; do run lgbm_trace $s; done
run ember2018_pub 0
for s in 11 23 37 41 53; do run xgb $s; done
for mdl in nb lr lr_chi2 lr_ig lr_pca svm_lin knn lr_mrmr; do run $mdl 0; done
for s in 11 23 37 41 53; do run et $s; done
for s in 11 23 37 41 53; do run rf $s; done
for s in 11 23 37 41 53; do run lgbm_ember $s; done
for s in 11 23 37; do run mlp $s; done
for s in 11 23 37 41 53; do run stack $s; done
run svm_rbf 11
echo "=== QUEUE DONE $(date -u +%H:%M:%S)"
