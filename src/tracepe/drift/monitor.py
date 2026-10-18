"""Label-free drift monitor M8 (paper Section 4.6): KS on margins, mean PSI, credibility, Page-Hinkley and a
classifier two-sample test, per predicted class, against a temporally blocked null; alarms need
exceedances in P consecutive windows and re-arm after a quiet window."""
from __future__ import annotations

import numpy as np
from scipy.stats import ks_2samp
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


def psi_mean(ref, win, bins: int = 10, eps: float = 1e-4, cols=None) -> float:
    ref = np.asarray(ref, np.float32)
    win = np.asarray(win, np.float32)
    cols = range(ref.shape[1]) if cols is None else cols
    qs = np.linspace(0, 1, bins + 1)[1:-1]
    vals = []
    for j in cols:
        edges = np.unique(np.quantile(ref[:, j], qs))
        pr = np.bincount(np.searchsorted(edges, ref[:, j], side='right'), minlength=len(edges) + 1) / len(ref)
        pw = np.bincount(np.searchsorted(edges, win[:, j], side='right'), minlength=len(edges) + 1) / len(win)
        pr = np.clip(pr, eps, None)
        pw = np.clip(pw, eps, None)
        vals.append(np.sum((pw - pr) * np.log(pw / pr)))
    return float(np.mean(vals))


def ks(a, b) -> float:
    if len(a) == 0 or len(b) == 0:
        return float('nan')
    return float(ks_2samp(a, b).statistic)


def c2st_auc(A, B, params: dict, folds: int = 2, seed: int = 1) -> float:
    """Out-of-fold AUC of a LightGBM domain classifier separating A from B (C2ST)."""
    import lightgbm as lgb
    A = np.asarray(A, np.float32)
    B = np.asarray(B, np.float32)
    if len(A) < folds * 2 or len(B) < folds * 2:
        return float('nan')
    Z = np.vstack([A, B])
    dz = np.r_[np.zeros(len(A)), np.ones(len(B))]
    oof = np.zeros(len(dz))
    p = dict(objective='binary', num_leaves=params.get('num_leaves', 31), learning_rate=params.get('learning_rate', 0.1),
             feature_fraction=0.5, seed=7, deterministic=True, force_row_wise=True,
             num_threads=params.get('threads', 2), verbose=-1)
    for trn, tst in StratifiedKFold(folds, shuffle=True, random_state=seed).split(Z, dz):
        clf = lgb.train(p, lgb.Dataset(Z[trn], label=dz[trn]), num_boost_round=params.get('rounds', 100))
        oof[tst] = clf.predict(Z[tst])
    return float(roc_auc_score(dz, oof))


def page_hinkley(series, delta: float = 0.005) -> np.ndarray:
    """Page-Hinkley statistic for an increase in the mean of ``series``."""
    x = np.asarray(series, np.float64)
    out = np.zeros(len(x))
    m_t, mean, min_m = 0.0, 0.0, 0.0
    for t, v in enumerate(x):
        mean += (v - mean) / (t + 1)
        m_t += v - mean - delta
        min_m = min(min_m, m_t)
        out[t] = m_t - min_m
    return out


def alarm_rule(exceed_any: np.ndarray, persistence: int = 2) -> list[int]:
    """Alarm at window w if every one of the last P windows has an exceedance; re-arm after a quiet window."""
    alarms, armed, run = [], True, 0
    for w, e in enumerate(exceed_any):
        run = run + 1 if e else 0
        if not e:
            armed = True
        if armed and run >= persistence:
            alarms.append(w)
            armed = False
    return alarms
