"""Statistical tests with effect sizes (paper Section 7.5)."""
from __future__ import annotations

import math

import numpy as np
from scipy import stats as st


# ------------------------------------------------------------------ DeLong (fast, Sun & Xu 2014)
def _midrank(x):
    J = np.argsort(x, kind='mergesort')
    Z = x[J]
    N = len(x)
    T = np.zeros(N)
    i = 0
    while i < N:
        j = i
        while j < N and Z[j] == Z[i]:
            j += 1
        T[i:j] = 0.5 * (i + j - 1) + 1
        i = j
    T2 = np.empty(N)
    T2[J] = T
    return T2


def _fast_delong(preds_sorted, m):
    n = preds_sorted.shape[1] - m
    k = preds_sorted.shape[0]
    tx = np.empty((k, m))
    ty = np.empty((k, n))
    tz = np.empty((k, m + n))
    for r in range(k):
        tx[r] = _midrank(preds_sorted[r, :m])
        ty[r] = _midrank(preds_sorted[r, m:])
        tz[r] = _midrank(preds_sorted[r])
    aucs = tz[:, :m].sum(axis=1) / m / n - (m + 1.0) / 2.0 / n
    v01 = (tz[:, :m] - tx) / n
    v10 = 1.0 - (tz[:, m:] - ty) / m
    sx = np.atleast_2d(np.cov(v01))
    sy = np.atleast_2d(np.cov(v10))
    return aucs, sx / m + sy / n


def delong(y, s1, s2=None) -> dict:
    """AUC(s) with DeLong variance; with s2, the two-sided test of AUC1 = AUC2 on correlated scores."""
    y = np.asarray(y).astype(int)
    order = np.argsort(-y, kind='stable')
    m = int(y.sum())
    preds = np.vstack([np.asarray(s1, np.float64)] + ([np.asarray(s2, np.float64)] if s2 is not None else []))[:, order]
    aucs, cov = _fast_delong(preds, m)
    if s2 is None:
        se = math.sqrt(max(cov[0, 0], 0))
        # normal-approximation interval, truncated to [0, 1]
        return dict(auc=float(aucs[0]), se=se, ci=[float(max(0.0, aucs[0] - 1.959964 * se)), float(min(1.0, aucs[0] + 1.959964 * se))])
    var = cov[0, 0] + cov[1, 1] - 2 * cov[0, 1]
    z = (aucs[0] - aucs[1]) / math.sqrt(var) if var > 0 else 0.0
    return dict(auc1=float(aucs[0]), auc2=float(aucs[1]), diff=float(aucs[0] - aucs[1]), z=float(z),
                p=float(2 * st.norm.sf(abs(z))))


# ------------------------------------------------------------------ paired and rank tests
def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    return 1.0 if n == 0 else float(min(1.0, 2 * st.binom.cdf(min(b, c), n, 0.5)))


def holm(pvals) -> list[float]:
    p = np.asarray(pvals, np.float64)
    order = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    running = 0.0
    for r, i in enumerate(order):
        running = max(running, min(1.0, (m - r) * p[i]))
        adj[i] = running
    return adj.tolist()


def wilcoxon_p(x, y=None) -> float:
    x = np.asarray(x, np.float64)
    d = x if y is None else x - np.asarray(y, np.float64)
    d = d[~np.isnan(d)]
    if len(d) == 0 or np.all(d == 0):
        return 1.0
    return float(st.wilcoxon(d, zero_method='wilcox', alternative='two-sided').pvalue)


def friedman(matrix) -> dict:
    """matrix: n_blocks x k (higher is better). Friedman chi2, p, Kendall's W and mean ranks (1 = best)."""
    M = np.asarray(matrix, np.float64)
    n, k = M.shape
    ranks = np.vstack([st.rankdata(-row) for row in M])
    chi2, p = st.friedmanchisquare(*[M[:, j] for j in range(k)])
    W = chi2 / (n * (k - 1))
    return dict(chi2=float(chi2), p=float(p), kendall_w=float(W), mean_ranks=ranks.mean(axis=0).tolist(), n=n, k=k)


def cliffs_delta(a, b) -> float:
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    if len(a) == 0 or len(b) == 0:
        return float('nan')
    gt = (a[:, None] > b[None, :]).sum()
    lt = (a[:, None] < b[None, :]).sum()
    return float((gt - lt) / (len(a) * len(b)))


def cliffs_delta_large(a, b) -> float:
    """Cliff's delta for large samples via ranks (O(n log n))."""
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    bs = np.sort(b)
    lt = np.searchsorted(bs, a, side='left').sum()          # #{b < a}
    le = np.searchsorted(bs, a, side='right').sum()         # #{b <= a}
    gt_b = len(a) * len(b) - le                              # #{b > a}
    return float((lt - gt_b) / (len(a) * len(b)))


def a12(a, b) -> float:
    """Vargha-Delaney A12 = P(a > b) + 0.5 P(a = b)."""
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    if len(a) == 0 or len(b) == 0:
        return float('nan')
    gt = (a[:, None] > b[None, :]).sum()
    eq = (a[:, None] == b[None, :]).sum()
    return float((gt + 0.5 * eq) / (len(a) * len(b)))


def fisher_or(a: int, b: int, c: int, d: int) -> dict:
    """2x2 table [[a, b], [c, d]]; sample odds ratio with Woolf (log) 95% CI, Fisher exact p."""
    p = float(st.fisher_exact([[a, b], [c, d]])[1])
    if min(a, b, c, d) == 0:
        aa, bb, cc, dd = a + 0.5, b + 0.5, c + 0.5, d + 0.5
    else:
        aa, bb, cc, dd = a, b, c, d
    orr = (aa * dd) / (bb * cc)
    se = math.sqrt(1 / aa + 1 / bb + 1 / cc + 1 / dd)
    return dict(odds_ratio=float(orr), ci=[float(math.exp(math.log(orr) - 1.96 * se)), float(math.exp(math.log(orr) + 1.96 * se))], p=p)


def spearman(x, y, n_perm: int = 10000, seed: int = 0, B: int = 2000) -> dict:
    x = np.asarray(x, np.float64)
    y = np.asarray(y, np.float64)
    ok = ~(np.isnan(x) | np.isnan(y))
    x, y = x[ok], y[ok]
    rho, p = st.spearmanr(x, y)
    rng = np.random.default_rng(seed)
    perm = np.array([st.spearmanr(x, rng.permutation(y))[0] for _ in range(n_perm)])
    p_perm = float((np.sum(np.abs(perm) >= abs(rho)) + 1) / (n_perm + 1))
    boots = []
    for _ in range(B):
        i = rng.integers(0, len(x), len(x))
        if len(np.unique(x[i])) > 1 and len(np.unique(y[i])) > 1:
            boots.append(st.spearmanr(x[i], y[i])[0])
    ci = [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))] if boots else [None, None]
    return dict(rho=float(rho), p=float(p), p_perm=p_perm, ci=ci, n=int(len(x)))


def boot_mean_ci(values, B: int = 10000, seed: int = 0) -> list[float]:
    v = np.asarray(values, np.float64)
    v = v[~np.isnan(v)]
    if len(v) == 0:
        return [None, None]
    rng = np.random.default_rng(seed)
    means = v[rng.integers(0, len(v), size=(B, len(v)))].mean(axis=1)
    return [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))]


def block_bootstrap_sums(series_list, block: int = 7, B: int = 1000, seed: int = 0) -> np.ndarray:
    """Moving-block bootstrap over days; returns B x len(series_list) resampled sums (same blocks for all)."""
    S = np.vstack([np.asarray(s, np.float64) for s in series_list])
    T = S.shape[1]
    rng = np.random.default_rng(seed)
    nb = int(math.ceil(T / block))
    out = np.empty((B, S.shape[0]))
    for b in range(B):
        starts = rng.integers(0, max(T - block + 1, 1), size=nb)
        idx = (starts[:, None] + np.arange(block)[None, :]).ravel()[:T]
        out[b] = S[:, idx].sum(axis=1)
    return out
