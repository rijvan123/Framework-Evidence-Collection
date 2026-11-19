**Table 12. Secondary attribution leg: open-set family attribution, unseen-family detection and category back-off**

| Month | Non-generic malware | Unseen share ν_t (%) | Top-1 known (%) | Top-3 known (%) | Top-1 all (%) | Closed-world bound 1 − ν_t (%) | Macro-F1 closed / open (%) | Novelty AUROC | Novelty AUPRC (base rate) | Unknowns rejected (%) | Category acc. / macro-F1 (%) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Jan 2020 | 4,270 | 7.1 | 77.4 | 95.6 | 71.9 | 92.9 | 71.0 / 71.2 | 0.742 | 0.196 (0.071) | 7.6 | 92.7 / 87.1 |
| Feb 2020 | 3,612 | 9.3 | 78.4 | 84.7 | 71.1 | 90.7 | 65.7 / 66.1 | 0.815 | 0.382 (0.093) | 11.0 | 92.4 / 87.4 |
| Mar 2020 | 4,440 | 10.2 | 72.4 | 80.1 | 65.0 | 89.8 | 67.0 / 67.7 | 0.721 | 0.237 (0.102) | 10.1 | 88.0 / 82.2 |
| Apr 2020 | 4,297 | 10.3 | 77.0 | 86.3 | 69.1 | 89.7 | 66.7 / 67.0 | 0.586 | 0.214 (0.103) | 6.8 | 85.4 / 83.4 |
| May 2020 | 5,357 | 18.3 | 63.7 | 75.6 | 52.0 | 81.7 | 63.9 / 64.3 | 0.445 | 0.203 (0.183) | 2.9 | 77.1 / 76.8 |
| Jun 2020 | 3,938 | 10.5 | 56.4 | 68.0 | 50.5 | 89.5 | 63.9 / 64.2 | 0.572 | 0.246 (0.105) | 2.9 | 61.5 / 69.5 |
| Jul 2020 | 4,783 | 29.1 | 77.1 | 82.6 | 54.7 | 70.9 | 60.2 / 60.2 | 0.804 | 0.671 (0.291) | 2.4 | 81.1 / 77.8 |
| Aug 2020 | 3,366 | 26.4 | 81.3 | 86.1 | 59.8 | 73.6 | 60.8 / 61.9 | 0.813 | 0.589 (0.264) | 12.4 | 92.9 / 86.2 |
| Sep 2020 | 4,287 | 32.8 | 74.5 | 81.6 | 50.1 | 67.2 | 60.9 / 61.2 | 0.799 | 0.593 (0.328) | 9.7 | 89.8 / 82.5 |

LightGBM multiclass over 68 families with ≥ 20 training samples (9,886 files; 3,776 files with generic AV tokens excluded, D8). Open-set rejection at the December 5th-percentile max-probability (τ_open = 0.529). KB10 (July): AUROC 0.804 ≥ 0.80 but AUPRC 0.671 < 3 × 0.291 = 0.874 → kill met, attribution leg dropped. H7: open > closed macro-F1 in 9/9 months, Wilcoxon p = 0.0039, mean +0.42 pp (met; negligible effect). P6: slope of open-set macro-F1 -1.21 pp/month vs detection F1 -2.15 pp/month; difference +0.94 [0.24, 1.64] pp/month, the opposite sign to the prediction → falsified. A first fit with num_leaves = 15, lr = 0.1 diverged (training accuracy 27.5%) and was discarded before any test month was read (D12). {MoC}.
