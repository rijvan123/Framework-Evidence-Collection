**Table 15. Comparison with existing methods and published baselines: absolute (pp) and relative differences**

| Metric | Published source | Published value | This work | Δ absolute (pp) | Δ relative | Protocol note |
|---|---|---|---|---|---|---|
| Monthly F1 (%), range | [1] T. II, EMBER-GBDT | 92.14–97.76 {RfP} | 98.09–99.51 {MoC} | +5.95 / +1.75 | +6.5% / +1.8% | [1]: GBDT trained by [1] on EMBER (5 seeds), threshold at 0.1% FPR on its own validation split, Oct 2019–Sep 2020; ours: the published EMBER-2018 model file, threshold at the 0.1% empirical quantile of BODMAS Dec 2019 benign, Mar–Sep 2020 Dated (realised pooled FPR 0.193%) |
| Monthly F1 (%), range | [1] T. II, EMBER-GBDT | 92.14–97.76 {RfP} | 88.65–98.27 {MoC} LGBM-TRACE, 5-seed mean | -3.49 / +0.51 | -3.8% / +0.5% | LGBM-TRACE trained on BODMAS Aug–Nov 2019 at [1]'s operating point (0.1% empirical on Dec 2019) |
| Monthly F1 (%), range | [1] T. II, EMBER-GBDT | 92.14–97.76 {RfP} | 82.93–96.82 {MoC} LGBM-TRACE, 5-seed mean | -9.21 / -0.94 | -10.0% / -1.0% | LGBM-TRACE at the CP-certified 0.1% threshold (k* = 1) |
| Monthly F1 (%), range | [1] T. II, SOREL-GBDT | 95.70–98.94 {RfP} | 82.93–96.82 {MoC} LGBM-TRACE, 5-seed mean | -12.77 / -2.12 | -13.3% / -2.1% | SOREL-20M-trained GBDT ([1]) vs LGBM-TRACE certified |
| Monthly FNR (%), range | [1] T. III | 1.71–7.23 {RfP} | 1.91–20.45 {MoC} | +0.20 / +13.22 | +11.5% / +182.9% | T0 replication, Dated: [1]'s protocol on our strata |
| Monthly FPR (%), range | [1] T. III | 0.00–0.51 {RfP} | 0.000–0.108 {MoC} | +0.00 / -0.40 | — / -78.9% | T0 replication, Dated |
| Max monthly FNR, unseen families (%) | [1] T. III | 43.04 {RfP} | 42.17 {MoC} | -0.87 | -2.0% | T0 replication, Dated |
| Monthly FNR (%), range | [1] T. III | 1.71–7.23 {RfP} | 1.19–3.43 {MoC} | -0.52 / -3.80 | -30.5% / -52.6% | T0 replication, Dated + PreWindow: [1]'s protocol on our strata |
| Monthly FPR (%), range | [1] T. III | 0.00–0.51 {RfP} | 0.000–0.119 {MoC} | +0.00 / -0.39 | — / -76.6% | T0 replication, Dated + PreWindow |
| Max monthly FNR, unseen families (%) | [1] T. III | 43.04 {RfP} | 29.09 {MoC} | -13.95 | -32.4% | T0 replication, Dated + PreWindow |
| Monthly FNR (%), range | [1] T. III | 1.71–7.23 {RfP} | 5.07–29.05 {MoC} LGBM-TRACE, 5-seed mean | +3.36 / +21.82 | +196.7% / +301.9% | LGBM-TRACE certified, Jan–Sep 2020 |
| F1 (%), random split | [1] T. II, EMBER-GBDT validation | 98.62 {RfP} | 98.03 {MoC} LGBM-TRACE random arm, 5 seeds | -0.59 | -0.6% | random split inflates both; ours: BODMAS random 5-seed arm |
| F1 (%) | [94] D3QN, BODMAS | 98.64 {RfP} | 90.98 {MoC} LGBM-TRACE temporal AUT, 5-seed mean | -7.66 | -7.8% | [94] reports no temporal split; ours: temporal AUT, native ratio |
| F1 (%) | [94] D3QN, EMBER-2018 | 85.07 {RfP} | 75.60 {MoC} within-EMBER AUT, θ@0.5% | -9.47 | -11.1% | different protocol; π = 10% re-weighting |
| AUC-ROC (%) | EMBER-2018 release notebook [2] | 99.64 {RfP} | 99.66 {MoC} | +0.02 | +0.0% | same published model; full test set vs our stratified sub-sample |
| TPR at 0.1% FPR (%) | EMBER-2018 release notebook [2] | 86.81 {RfP} | 85.49 {MoC} | -1.32 | -1.5% | test-tuned threshold in both |
| TPR at 0.1% FPR (%) | [2] EMBER-2017 LightGBM | 92.99 {RfP} | 84.12 {MoC} LGBM-TRACE, 5-seed mean | -8.87 | -9.5% | EMBER-2017 test set, test-tuned threshold, vs LGBM-TRACE on BODMAS Mar–Sep 2020 at a threshold fixed on December 2019 |
| Malware regressing after an update (%) | [30] Ghiani, Android CL | 3.00–6.00 {RfP} | 0.023 {MoC} naive re-scoring | -2.98 / -5.98 | -99.2% / -99.6% | [30]: continual-learning Android detectors; ours: monthly full retraining of LGBM-TRACE, BODMAS PE, findings of the 30 d before each of 7 updates, certified 0.5% thresholds, abstained findings included |
| Goodware flips per update (%) | [89] Kozák, full AT | 1.22 {RfP, computed from counts} | 0.174 {MoC} naive re-scoring | -1.046 | -85.8% | [89]: EMBER-GBDT after full adversarial retraining; ours: benign findings turned malicious by the next monthly model |
| Malware flips per update (%) | [89] Kozák, full AT | 0.18 {RfP, computed from counts} | 0.023 {MoC} naive re-scoring | -0.157 | -87.3% | as above, malware findings turned benign; [89] denominator uncertain (27/14,997 = 0.18% as in S6; 27/1,785 = 1.51%) |

Δ = this work − published; relative Δ = Δ / published. Ranges are compared end-to-end (lower/upper). Protocols differ in training data, test months, base rate and operating point, as stated per row; rows with matched protocol are the release-notebook rows (same EMBER-2018 model file) and the T0 replication. LGBM-TRACE values are 5-seed means. {RfP} = reproduced-from-paper or release artifact; {MoC} = measured-on-Claude.
