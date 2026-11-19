**Table 9. Error structure of f₀ at θ@0.1%: entropy strata (P10), unseen versus known families (H3) and the families behind the July–September decay**

| High-entropy definition | Error | High stratum: errors/n = % | Low stratum: errors/n = % | Odds ratio [95% CI] | Fisher p |
|---|---|---|---|---|---|
| Eq. (19) packing indicator, τ_p = 1/32 | FNR | 3,040/23,587 = 12.888 | 903/9,104 = 9.919 | 1.34 [1.24, 1.45] | 5.9e-14 |
| Eq. (19) packing indicator, τ_p = 1/32 | FPR | 2/24,561 = 0.008 | 1/11,624 = 0.009 | 0.95 [0.09, 10.44] | 1.000 |
| byte mass in the two highest entropy bins > 0.5 | FNR | 2,675/18,839 = 14.199 | 1,268/13,852 = 9.154 | 1.64 [1.53, 1.76] | 1.3e-44 |
| byte mass in the two highest entropy bins > 0.5 | FPR | 2/18,117 = 0.011 | 1/18,068 = 0.006 | 1.99 [0.18, 22.00] | 1.000 |

| Month | Unseen-family malware | FNR unseen (%) | Known-family malware | FNR known (%) |
|---|---|---|---|---|
| Jan 2020 | 63 | 36.51 | 4,337 | 3.60 |
| Feb 2020 | 78 | 37.18 | 3,952 | 5.24 |
| Mar 2020 | 71 | 45.07 | 4,919 | 5.96 |
| Apr 2020 | 71 | 15.49 | 4,569 | 4.82 |
| May 2020 | 161 | 28.57 | 5,288 | 4.35 |
| Jun 2020 | 69 | 26.09 | 4,148 | 5.28 |
| Jul 2020 | 734 | 8.72 | 4,261 | 18.14 |
| Aug 2020 | 131 | 32.06 | 3,692 | 24.38 |
| Sep 2020 | 246 | 59.76 | 4,331 | 21.89 |

| Family (Jul–Sep 2020) | Seen in training | Malware files | False negatives | FNR (%) | Share of all Jul–Sep FN (%) |
|---|---|---|---|---|---|
| wabot | yes | 1,958 | 1,269 | 64.8 | 44.2 |
| ceeinject | yes | 814 | 272 | 33.4 | 9.5 |
| zbot | yes | 280 | 210 | 75.0 | 7.3 |
| tofsee | yes | 304 | 157 | 51.6 | 5.5 |
| salgorea | yes | 197 | 131 | 66.5 | 4.6 |
| wacatac | yes | 267 | 105 | 39.3 | 3.7 |
| glupteba | yes | 100 | 100 | 100.0 | 3.5 |
| cosmicduke | no | 57 | 57 | 100.0 | 2.0 |
| all families |  | 13,395 | 2,874 | 21.5 | 100.0 |

P10 is falsified for FPR (3 false positives in total; the odds-ratio CI spans 1) and holds for FNR. H3: Wilcoxon over months p = 0.0117, A12 = 0.926 (met), yet July–September FNR is driven by families present in training. Family labels are BODMAS family tokens (RecMaL [92] estimates about 20% of them shifted or wrong). {MoC}.
