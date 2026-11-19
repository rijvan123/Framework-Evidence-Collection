**Table 5. Censored benign strata, spike-day malware and the spike-rule sensitivity (f₀, θ@0.1%)**

| Month | Censored stratum | Dated benign | FPR dated (%) | Censored benign | FPR censored (%) (95% CP upper) | FPR pooled (%) | Shift (pp) | Bootstrap half-width (pp) |
|---|---|---|---|---|---|---|---|---|
| Jan 2020 | Placeholder | 49 | 0.00 | 5,870 | 0.187 (≤ 0.310) | 0.186 | 0.186 | 0.000 |
| Feb 2020 | Bulk | 62 | 0.00 | 3,641 | 0.330 (≤ 0.533) | 0.324 | 0.324 | 0.000 |

| Month | SpikeMal files | FNR spike-day malware (%) | FNR dated (%) | FNR pooled (%) |
|---|---|---|---|---|
| Jan 2020 | 110 | 0.91 | 4.07 | 3.99 |
| Feb 2020 | 239 | 19.25 | 5.86 | 6.61 |

| June 2020 rule | Files | FNR (%) | FPR (%) | F1 native (%) |
|---|---|---|---|---|
| spike rule k = 10 (primary) | 12,399 | 5.62 | 0.000 | 97.11 |
| spike rule k = 4 (sensitivity) | 10,985 | 5.86 | 0.000 | 96.98 |

Placeholder (January) and Bulk (February) benign files carry batch timestamps and are excluded from the Dated stream (S7). The KB5 rule (shift > bootstrap half-width) is met literally in both months, but the half-width is zero because the dated stratum has 0/49 and 0/62 false positives; the test is degenerate and reported as inconclusive. Both censored strata alone fail the 0.1% FPR certificate (CP upper 0.31% and 0.53%). {MoC}.
