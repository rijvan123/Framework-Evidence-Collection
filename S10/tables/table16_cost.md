**Table 16. CPU cost per model (uncontended, sequential)**

| Model | Training (s) | Inference (µs per file) | Peak RSS (GB) |
|---|---|---|---|
| EMBER-2018 GBDT (published model) | 0.0 | 335.5 | 1.17 |
| Gaussian NB | 1.3 | 41.6 | 1.63 |
| LR + χ²(256) | 2.1 | 21.6 | 1.78 |
| LR | 3.1 | 25.9 | 1.63 |
| k-NN (PCA-50) | 3.9 | 81.5 | 1.63 |
| LR + IG(256) | 4.7 | 26.9 | 1.57 |
| LR + PCA(0.95) | 16.2 | 52.5 | 2.11 |
| RBF-SVM (PoC, 10k) | 26.7 | 3,306.2 | 1.80 |
| MLP (PoC, 20k) | 26.7 | 54.9 | 1.67 |
| Extra trees | 29.1 | 53.5 | 1.00 |
| LGBM-TRACE (f₀ family) | 35.8 | 13.4 | 1.39 |
| Random forest | 53.5 | 40.7 | 0.98 |
| LR + mRMR(128) | 76.3 | 17.3 | 1.83 |
| Linear SVM | 78.1 | 32.3 | 2.38 |
| XGBoost | 82.2 | 9.9 | 1.81 |
| Temporal stacking | 121.7 | 69.9 | 1.90 |
| LGBM-EMBER | 151.7 | 102.5 | 2.37 |

Training window 23,158 × 2,381 (S7); inference on 20,000 rows. Intel Xeon @ 2.10 GHz, 2 vCPU, Python 3.13.16, LightGBM 4.7.0, XGBoost 3.4.1, scikit-learn 1.9.1. One run per model; the published EMBER-2018 model is scored only; RBF-SVM values come from its E1 run (10,000-row training sub-sample, 97,436 rows scored); the MLP was re-timed after D17. {MoC}.
