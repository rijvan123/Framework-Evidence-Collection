**Table 14. EMBER-2018 corroboration (D10)**

| Published EMBER-2018 model on Nov–Dec 2018 | Release notebook {RfP} (full test set) | This vectorisation {MoC} (stratified sub-sample) | Δ (pp) |
|---|---|---|---|
| AUC-ROC (%) | 99.643 | 99.659 | +0.016 |
| TPR at 0.1% FPR, test-tuned (%) | 86.81 | 85.49 | -1.32 |
| TPR at 1% FPR, test-tuned (%) | 96.50 | 96.23 | -0.26 |

| Month | Benign / malware | FNR @θ0.1% (%) | FPR @θ0.1% (%) | F1 @π=10%, θ0.1% (%) | FNR @θ0.5% (%) | FPR @θ0.5% (%) | AUC-ROC (%) |
|---|---|---|---|---|---|---|---|
| May–Jun 2018 (cal) | 5,898 / 6,054 | 51.72 | 0.017 | 65.06 | 28.10 | 0.339 | 98.666 |
| Jul 2018 | 3,066 / 2,969 | 52.48 | 0.033 | 64.30 | 27.89 | 0.457 | 99.071 |
| Aug 2018 | 3,098 / 3,042 | 59.50 | 0.032 | 57.53 | 33.23 | 0.226 | 98.343 |
| Sep 2018 | 3,050 / 2,918 | 72.48 | 0.066 | 42.96 | 42.70 | 0.492 | 97.385 |
| Oct 2018 | 2,941 / 2,970 | 61.48 | 0.272 | 54.65 | 36.03 | 1.156 | 97.198 |
| Nov 2018 | 2,995 / 2,983 | 58.13 | 0.100 | 58.65 | 31.01 | 0.835 | 97.556 |
| Dec 2018 | 3,012 / 2,938 | 66.68 | 0.066 | 49.76 | 38.97 | 1.162 | 96.665 |

| Corroboration check | Result |
|---|---|
| Within-EMBER temporal AUT(F1@π=10%) (%), θ@0.1% / θ@0.5% | 54.17 / 75.60 |
| SVR at (0.5%, 5%), Jul–Dec 2018 | θ@0.1%: 0/6; θ@0.5%: 0/6 |
| Random-split inflation (5 seeds), F1@π=10% vs temporal AUT | +19.86 pp [18.17, 21.81] |
| Forward transfer: EMBER-trained (Jan–Apr 2018) → BODMAS Mar–Sep 2020, AUT(F1@π=10%) (%) | 77.61; monthly FNR 22.4–58.3% |
| Backward application: f₀ (BODMAS 2019) → EMBER 2018, monthly AUC-ROC (C1-violating, descriptive) | 73.4–93.0% |
| SHA-256 overlap between the EMBER sub-sample and BODMAS | 4 files |

Month-stratified sub-sample of the EMBER-2018 labelled release vectorised with the EMBER v2 extractor (72,009 files, about 3,000 per class per month). Within-EMBER protocol mirrors TRACE-PE: train January–April, calibrate May–June (CP-certified θ), test July–December monthly. The release-notebook values are computed on the full 200,000-file test set with test-tuned thresholds; ours on the stratified Nov–Dec sub-sample.
