"""Adaptive conformal inference (Gibbs & Candes 2021) with delayed labels, used as an alarm baseline.

Prediction sets: label c is included when its ICE p-value exceeds alpha_t. Labels of day s arrive at
s + delay; alpha_t is updated finding by finding (alpha <- alpha + gamma (alpha* - err)). An alarm is
raised on a day when an arriving label batch has a miscoverage rate above alpha* by more than three
binomial standard errors (implementation choice; the paper does not fix the alarm rule)."""
from __future__ import annotations

import numpy as np


def aci_alarms(days, pvals, y, alpha: float = 0.10, gamma: float = 0.005, delay: int = 7) -> dict:
    """days: issue day per finding (sorted); pvals: n x 2 conformal p-values; y: true labels."""
    days = np.asarray(days)
    y = np.asarray(y).astype(int)
    a_t = alpha
    alarms = []
    alpha_path = {}
    uniq = np.unique(days)
    pending = {}
    for d in uniq:
        # labels issued at d - delay arrive now
        arrive = d - delay
        if arrive in pending:
            idx, a_used = pending.pop(arrive)
            covered = pvals[idx, y[idx]] > a_used
            err = 1 - covered.astype(float)
            n = len(idx)
            rate = err.mean() if n else 0.0
            if n and rate > alpha + 3 * np.sqrt(alpha * (1 - alpha) / n):
                alarms.append(int(d))
            for e in err:
                a_t = a_t + gamma * (alpha - e)
        idx = np.flatnonzero(days == d)
        pending[int(d)] = (idx, a_t)
        alpha_path[int(d)] = a_t
    return dict(alarms=alarms, alpha_path=alpha_path)
