"""Jensen-Shannon drift per feature on training-quantile bins, averaged per EMBER group (Eqs. (74)-(75))."""
from __future__ import annotations

import numpy as np

from ..features.groups import GROUPS, D


def quantile_edges(Xtr, bins: int = 20) -> list[np.ndarray]:
    qs = np.linspace(0, 1, bins + 1)[1:-1]
    Xtr = np.asarray(Xtr, dtype=np.float32)
    return [np.unique(np.quantile(Xtr[:, j], qs)) for j in range(Xtr.shape[1])]


def histograms(X, edges) -> list[np.ndarray]:
    X = np.asarray(X, dtype=np.float32)
    out = []
    for j, e in enumerate(edges):
        b = np.searchsorted(e, X[:, j], side='right')
        out.append(np.bincount(b, minlength=len(e) + 1) / max(len(X), 1))
    return out


def js_bits(P, Q) -> float:
    P = np.asarray(P, np.float64)
    Q = np.asarray(Q, np.float64)
    M = 0.5 * (P + Q)
    with np.errstate(divide='ignore', invalid='ignore'):
        kl = lambda A: np.sum(np.where(A > 0, A * np.log2(A / M), 0.0))
        return float(0.5 * kl(P) + 0.5 * kl(Q))


def drift(ref_hist, X, edges) -> dict:
    """Per-feature JS divergence of X against reference histograms, group means and pooled D(t) (Eq. 75)."""
    h = histograms(X, edges)
    js = np.array([js_bits(r, q) for r, q in zip(ref_hist, h)])
    groups = {g: float(js[a:b].mean()) for g, a, b in GROUPS}
    pooled = float(sum((b - a) / D * groups[g] for g, a, b in GROUPS))
    return dict(pooled=pooled, groups=groups, per_feature=js)
