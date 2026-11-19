"""Clopper-Pearson bounds and threshold rules (paper Eqs. (58), (88), (89)).

The certified threshold is the (k*+1)-th largest benign calibration score, where k* is the largest number
of calibration false positives whose one-sided 95% Clopper-Pearson upper bound stays within tau_FPR.
The verdict is ``score > theta``, so at most k* calibration benign files are flagged."""
from __future__ import annotations

import math

import numpy as np
from scipy.stats import beta


def cp_upper(k: int, n: int, conf: float = 0.95) -> float:
    """One-sided Clopper-Pearson upper bound (Eq. (88)); 1 when k = n; NaN when n = 0."""
    if n <= 0:
        return float('nan')
    if k >= n:
        return 1.0
    return float(beta.ppf(conf, k + 1, n - k))


def cp_lower(k: int, n: int, conf: float = 0.95) -> float:
    if n <= 0:
        return float('nan')
    if k <= 0:
        return 0.0
    return float(beta.ppf(1 - conf, k, n - k + 1))


def k_star(n_b: int, tau: float, conf: float = 0.95) -> int:
    """Largest k with CP upper bound <= tau (-1 if even k = 0 cannot be certified)."""
    if n_b <= 0:
        return -1
    lo, hi = -1, n_b - 1
    # cp_upper is increasing in k: binary search for the last k with bound <= tau
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if cp_upper(mid, n_b, conf) <= tau:
            lo = mid
        else:
            hi = mid - 1
    return lo


def certified_threshold(benign_scores, tau: float, conf: float = 0.95) -> dict:
    s = np.sort(np.asarray(benign_scores, dtype=np.float64))[::-1]
    n = len(s)
    k = k_star(n, tau, conf)
    if n == 0:
        return dict(theta=float('inf'), k_star=-1, n_b=0, ub=float('nan'), certified=False, tau=tau)
    if k < 0:   # not certifiable at this tau: flag nothing that scored like a calibration benign file
        return dict(theta=float(s[0]), k_star=-1, n_b=n, ub=cp_upper(0, n, conf), certified=False, tau=tau)
    return dict(theta=float(s[k]), k_star=int(k), n_b=n, ub=cp_upper(k, n, conf), certified=True, tau=tau)


def empirical_threshold(benign_scores, beta_rate: float) -> dict:
    """Empirical beta-quantile of benign calibration scores ([1]'s protocol): allows floor(beta*n) FPs."""
    s = np.sort(np.asarray(benign_scores, dtype=np.float64))[::-1]
    n = len(s)
    k = int(math.floor(beta_rate * n))
    k = min(k, n - 1)
    return dict(theta=float(s[k]), k=int(k), n_b=n, ub=cp_upper(k, n), beta=beta_rate)


def f1_threshold(scores, y, pi: float) -> float:
    """Threshold maximising F1 at deployment prevalence pi (Eq. (70) re-weighting) on calibration data."""
    from ..evaluation.metrics import benign_weight
    scores = np.asarray(scores, dtype=np.float64)
    y = np.asarray(y).astype(int)
    order = np.argsort(-scores, kind='stable')
    s, yy = scores[order], y[order]
    tp = np.cumsum(yy)
    fp = np.cumsum(1 - yy)
    n_pos, n_neg = int(y.sum()), int((1 - y).sum())
    w = benign_weight(n_pos, n_neg, pi)
    last = np.r_[s[1:] != s[:-1], True]          # evaluate thresholds between distinct scores
    tp, fp, s = tp[last], fp[last], s[last]
    prec = tp / np.maximum(tp + w * fp, 1e-12)
    rec = tp / max(n_pos, 1)
    f1 = np.where(prec + rec > 0, 2 * prec * rec / np.maximum(prec + rec, 1e-12), 0)
    i = int(np.argmax(f1))
    nxt = s[i + 1] if i + 1 < len(s) else s[i] - 1.0
    return float((s[i] + nxt) / 2)         # verdict score > theta keeps exactly the top block
