"""Inductive conformal evaluation (Eq. (90)) and abstention (Eq. (91)).

Non-conformity alpha = 1 - p(yhat | x) with p from the calibrator; the credibility of a verdict is the
conformal p-value of the predicted label against calibration samples whose true label equals it."""
from __future__ import annotations

import numpy as np


def nonconformity(p1, yhat) -> np.ndarray:
    p1 = np.asarray(p1, dtype=np.float64)
    yhat = np.asarray(yhat).astype(int)
    return 1.0 - np.where(yhat == 1, p1, 1.0 - p1)


class ICE:
    def fit(self, p1_cal, y_cal):
        y_cal = np.asarray(y_cal).astype(int)
        a = nonconformity(p1_cal, y_cal)
        self.cal = {c: np.sort(a[y_cal == c]) for c in (0, 1)}
        return self

    def credibility(self, p1, yhat) -> np.ndarray:
        a = nonconformity(p1, yhat)
        yhat = np.asarray(yhat).astype(int)
        out = np.empty(len(a))
        for c in (0, 1):
            m = yhat == c
            cal = self.cal[c]
            n = len(cal)
            ge = n - np.searchsorted(cal, a[m], side='left')       # #{alpha_j >= alpha}
            out[m] = (1 + ge) / (1 + n)
        return out


def kappa_for_rate(cred, rate: float) -> float:
    """Largest kappa such that at most ``rate`` of the given credibilities fall below it."""
    c = np.sort(np.asarray(cred, dtype=np.float64))
    k = int(np.floor(rate * len(c)))
    if k >= len(c):
        return float(c[-1]) + 1e-12
    return float(c[k])


def per_class_kappa(cred, yhat, rate: float) -> dict:
    yhat = np.asarray(yhat).astype(int)
    return {c: kappa_for_rate(np.asarray(cred)[yhat == c], rate) if (yhat == c).any() else 0.0 for c in (0, 1)}
