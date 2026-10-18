"""Detection metrics (Eqs. (55), (62)-(70)).

Prevalence-dependent metrics are computed at a *stated* deployment prevalence pi by re-weighting each
benign file with w = (1 - pi)/pi * n+/n- (Eq. (70)), which is algebraically equal to Eq. (55)."""
from __future__ import annotations

import math

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score, roc_curve


def counts(scores, y, theta: float) -> dict:
    s = np.asarray(scores, np.float64)
    y = np.asarray(y).astype(bool)
    pred = s > theta
    return dict(tp=int((pred & y).sum()), fp=int((pred & ~y).sum()), fn=int((~pred & y).sum()), tn=int((~pred & ~y).sum()))


def benign_weight(n_pos: int, n_neg: int, pi: float) -> float:
    if n_neg == 0 or pi <= 0:
        return float('nan')
    return (1 - pi) / pi * (n_pos / n_neg)


def _div(a, b):
    return a / b if b else float('nan')


def from_counts(tp, fp, fn, tn, pi_report=0.10, pi_prec=0.01) -> dict:
    n_pos, n_neg = tp + fn, fp + tn
    tpr, fpr = _div(tp, n_pos), _div(fp, n_neg)
    out = dict(tp=tp, fp=fp, fn=fn, tn=tn, n_pos=n_pos, n_neg=n_neg, tpr=tpr, fpr=fpr,
               fnr=(1 - tpr) if not math.isnan(tpr) else float('nan'))
    prec = _div(tp, tp + fp)
    out['precision_native'] = prec
    out['f1_native'] = _div(2 * tp, 2 * tp + fp + fn)
    out['mcc_native'] = mcc(tp, fp, fn, tn)
    for pi, tag in ((pi_report, 'report'), (pi_prec, 'prec')):
        w = benign_weight(n_pos, n_neg, pi)
        p_pi = _div(tp, tp + w * fp) if not math.isnan(w) else float('nan')
        out[f'precision_pi_{tag}'] = p_pi
        if tag == 'report':
            out['f1_pi'] = _div(2 * p_pi * tpr, p_pi + tpr) if (tp > 0 and not math.isnan(p_pi)) else (float('nan') if tp == 0 else 0.0)
            out['mcc_pi'] = mcc(tp, w * fp, fn, w * tn) if not math.isnan(w) else float('nan')
    out['pi_report'], out['pi_prec'] = pi_report, pi_prec
    return out


def mcc(tp, fp, fn, tn) -> float:
    den = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return (tp * tn - fp * fn) / den if den > 0 else float('nan')


def point_metrics(scores, y, theta, pi_report=0.10, pi_prec=0.01) -> dict:
    c = counts(scores, y, theta)
    return from_counts(c['tp'], c['fp'], c['fn'], c['tn'], pi_report, pi_prec)


def precision_analytic(tpr: float, fpr: float, pi: float) -> float:
    """Eq. (55): precision at prevalence pi from TPR and FPR (Axelsson's Bayesian detection rate)."""
    den = tpr * pi + fpr * (1 - pi)
    return tpr * pi / den if den > 0 else float('nan')


def auc(scores, y) -> float:
    y = np.asarray(y).astype(int)
    if y.min() == y.max():
        return float('nan')
    return float(roc_auc_score(y, scores))


def auc_pr_at_pi(scores, y, pi: float) -> float:
    y = np.asarray(y).astype(int)
    n_pos, n_neg = int(y.sum()), int((1 - y).sum())
    if n_pos == 0 or n_neg == 0:
        return float('nan')
    w = np.where(y == 1, 1.0, benign_weight(n_pos, n_neg, pi))
    return float(average_precision_score(y, scores, sample_weight=w))


def aut(values) -> float:
    """Eq. (69): TESSERACT Area Under Time (trapezoid over consecutive periods, normalised)."""
    v = [x for x in values]
    if len(v) < 2 or any(x is None or (isinstance(x, float) and math.isnan(x)) for x in v):
        return float('nan')
    return float(sum((v[k] + v[k + 1]) / 2 for k in range(len(v) - 1)) / (len(v) - 1))


def bootstrap_counts(tp, fp, fn, tn, B=1000, seed=0, pi_report=0.10, pi_prec=0.01) -> dict:
    """Stratified binomial bootstrap of a confusion matrix: TP* ~ Bin(n+, TPR), FP* ~ Bin(n-, FPR)."""
    rng = np.random.default_rng(seed)
    n_pos, n_neg = tp + fn, fp + tn
    tps = rng.binomial(n_pos, tp / n_pos, size=B) if n_pos else np.zeros(B, int)
    fps = rng.binomial(n_neg, fp / n_neg, size=B) if n_neg else np.zeros(B, int)
    keys = ['tpr', 'fpr', 'fnr', 'f1_pi', 'mcc_pi', 'precision_pi_prec', 'f1_native', 'mcc_native']
    vals = {k: [] for k in keys}
    for a, b in zip(tps, fps):
        m = from_counts(int(a), int(b), int(n_pos - a), int(n_neg - b), pi_report, pi_prec)
        for k in keys:
            vals[k].append(m[k])
    out = {}
    for k, v in vals.items():
        v = np.asarray(v, np.float64)
        v = v[~np.isnan(v)]
        out[k] = [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] if len(v) else [None, None]
    return out


def roc_points(scores, y, n: int = 300) -> dict:
    """ROC curve downsampled on a log-spaced FPR grid (for figures)."""
    y = np.asarray(y).astype(int)
    if y.min() == y.max():
        return dict(fpr=[], tpr=[])
    fpr, tpr, _ = roc_curve(y, scores)
    grid = np.unique(np.r_[0.0, np.logspace(-5, 0, n)])
    return dict(fpr=grid.tolist(), tpr=np.interp(grid, fpr, tpr).tolist())


def pr_points(scores, y, pi: float, n: int = 300) -> dict:
    """Precision-recall curve at prevalence pi (benign re-weighting), downsampled on a recall grid."""
    y = np.asarray(y).astype(int)
    s = np.asarray(scores, np.float64)
    order = np.argsort(-s, kind='stable')
    yy = y[order]
    tp = np.cumsum(yy)
    fp = np.cumsum(1 - yy)
    n_pos, n_neg = int(y.sum()), int((1 - y).sum())
    if n_pos == 0 or n_neg == 0:
        return dict(recall=[], precision=[])
    w = benign_weight(n_pos, n_neg, pi)
    rec = tp / n_pos
    prec = tp / np.maximum(tp + w * fp, 1e-12)
    grid = np.linspace(0, 1, n)
    idx = np.minimum(np.searchsorted(rec, grid, side='left'), len(rec) - 1)
    return dict(recall=grid.tolist(), precision=prec[idx].tolist())
