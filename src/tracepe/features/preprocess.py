"""Leakage-safe preprocessing (Eq. (8)): every transform is fitted on training-window rows only.

Signed log1p, standardisation, chi-square / information-gain / mRMR selection and PCA are wrapped
as scikit-learn transformers so they are refitted inside each training window."""
from __future__ import annotations

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.decomposition import PCA
from sklearn.feature_selection import SelectKBest, chi2
from sklearn.preprocessing import MinMaxScaler, StandardScaler


class SignedLog1p(BaseEstimator, TransformerMixin):
    """sign(x) * log1p(|x|): compresses sizes and timestamps; monotone, so trees are unaffected in exact arithmetic."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X = np.asarray(X, dtype=np.float32)
        return np.sign(X) * np.log1p(np.abs(X))


def binned_mutual_information(X, y, bins: int = 10, chunk: int = 256) -> np.ndarray:
    """Information gain I(x_k; y) on training-quantile bins (entropy in bits), Eqs. (40)-(42)."""
    X = np.asarray(X, dtype=np.float32)
    y = np.asarray(y).astype(np.int64)
    n, d = X.shape
    py = np.bincount(y, minlength=2) / n
    hy = -np.sum([p * np.log2(p) for p in py if p > 0])
    qs = np.linspace(0, 1, bins + 1)[1:-1]
    mi = np.zeros(d)
    for j in range(d):
        col = X[:, j]
        edges = np.unique(np.quantile(col, qs))
        b = np.searchsorted(edges, col, side='right')
        nb = len(edges) + 1
        joint = np.bincount(b * 2 + y, minlength=nb * 2).reshape(nb, 2) / n
        pb = joint.sum(axis=1)
        with np.errstate(divide='ignore', invalid='ignore'):
            cond = np.where(joint > 0, joint * np.log2(joint / pb[:, None]), 0.0)
        mi[j] = hy + cond.sum()
    return np.maximum(mi, 0)


class IGSelector(BaseEstimator, TransformerMixin):
    def __init__(self, k: int = 256, bins: int = 10):
        self.k, self.bins = k, bins

    def fit(self, X, y):
        self.scores_ = binned_mutual_information(X, y, self.bins)
        self.support_ = np.sort(np.argsort(-self.scores_, kind='stable')[:self.k])
        return self

    def transform(self, X):
        return np.asarray(X)[:, self.support_]


class MRMRSelector(BaseEstimator, TransformerMixin):
    """Greedy mRMR (Eq. (44), difference form): relevance = binned MI, redundancy = mean |Pearson r| with the
    selected set (the Pearson redundancy is an approximation, stated in the paper)."""

    def __init__(self, k: int = 128, bins: int = 10, pool: int = 1024):
        self.k, self.bins, self.pool = k, bins, pool

    def fit(self, X, y):
        X = np.asarray(X, dtype=np.float32)
        rel = binned_mutual_information(X, y, self.bins)
        cand = np.argsort(-rel, kind='stable')[:min(self.pool, X.shape[1])]
        Z = X[:, cand].astype(np.float64)
        Z = (Z - Z.mean(axis=0)) / (Z.std(axis=0) + 1e-12)
        n = len(Z)
        selected = [0]
        red_sum = np.abs(Z.T @ Z[:, 0]) / n
        for _ in range(1, min(self.k, len(cand))):
            score = rel[cand] - red_sum / len(selected)
            score[selected] = -np.inf
            j = int(np.argmax(score))
            selected.append(j)
            red_sum += np.abs(Z.T @ Z[:, j]) / n
        self.support_ = np.sort(cand[selected])
        self.scores_ = rel
        return self

    def transform(self, X):
        return np.asarray(X)[:, self.support_]


def chi2_steps(k: int):
    """chi-square selection needs non-negative input: min-max scaling fitted on the training window."""
    return [('mm', MinMaxScaler()), ('sel', SelectKBest(chi2, k=k))]


def pca(n_components, seed: int = 0):
    try:
        return PCA(n_components=n_components, svd_solver='covariance_eigh', random_state=seed)
    except TypeError:  # pragma: no cover - older scikit-learn
        return PCA(n_components=n_components, svd_solver='full', random_state=seed)


def standardize():
    return StandardScaler()
