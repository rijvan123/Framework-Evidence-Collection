"""Calibration, prior shift and cost-sensitive decisions (Eqs. (28)-(31), (52)-(57), (104))."""
from __future__ import annotations

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.asarray(z, dtype=np.float64)))


class Isotonic:
    def fit(self, z, y):
        self.m = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds='clip').fit(np.asarray(z, np.float64), y)
        return self

    def predict(self, z):
        return self.m.predict(np.asarray(z, np.float64))


class Platt:
    def fit(self, z, y):
        self.m = LogisticRegression(C=1e6, max_iter=1000).fit(np.asarray(z, np.float64).reshape(-1, 1), y)
        return self

    def predict(self, z):
        return self.m.predict_proba(np.asarray(z, np.float64).reshape(-1, 1))[:, 1]


def ece(p, y, bins: int = 15, weight=None) -> float:
    """Eq. (30): expected calibration error with equal-width bins."""
    p = np.asarray(p, np.float64)
    y = np.asarray(y, np.float64)
    w = np.ones_like(p) if weight is None else np.asarray(weight, np.float64)
    b = np.minimum((p * bins).astype(int), bins - 1)
    tot = w.sum()
    e = 0.0
    for k in range(bins):
        m = b == k
        if m.any():
            wk = w[m].sum()
            e += wk / tot * abs(np.average(y[m], weights=w[m]) - np.average(p[m], weights=w[m]))
    return float(e)


def brier(p, y, weight=None) -> float:
    p = np.asarray(p, np.float64)
    y = np.asarray(y, np.float64)
    return float(np.average((p - y) ** 2, weights=weight))


def prior_shift(q, pi_tr: float, pi: float):
    """Eq. (31) (Saerens et al.): move a posterior calibrated at prevalence pi_tr to prevalence pi."""
    q = np.clip(np.asarray(q, np.float64), 1e-12, 1 - 1e-12)
    a = (pi / pi_tr) * q
    b = ((1 - pi) / (1 - pi_tr)) * (1 - q)
    return a / (a + b)


def prevalence_weights(y, pi: float):
    """Eq. (104): sample weights that move a set with native prevalence to prevalence pi."""
    y = np.asarray(y).astype(int)
    pi_hat = y.mean()
    return np.where(y == 1, pi / pi_hat, (1 - pi) / (1 - pi_hat))


def expected_cost(fnr: float, fpr: float, pi: float, c_fn: float, c_fp: float = 1.0) -> float:
    """Eq. (57)."""
    return c_fn * pi * fnr + c_fp * (1 - pi) * fpr


def bayes_tau(c_fn: float, c_fp: float = 1.0) -> float:
    """Eq. (53): decide malicious when the deployment posterior is >= C_FP / (C_FP + C_FN)."""
    return c_fp / (c_fp + c_fn)


def score_lr(q, pi_cal: float):
    """Score-based likelihood ratio from a posterior calibrated at prevalence pi_cal (posterior odds / prior odds)."""
    q = np.clip(np.asarray(q, np.float64), 1e-6, 1 - 1e-6)
    return (q / (1 - q)) / (pi_cal / (1 - pi_cal))
