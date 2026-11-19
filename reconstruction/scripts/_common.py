"""Shared helpers for the experiment scripts (makes the package importable without installation)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / 'src') not in sys.path:
    sys.path.insert(0, str(ROOT / 'src'))

import numpy as np  # noqa: E402

from tracepe.utils import month_list  # noqa: E402


def test_months(cfg):
    a, b = cfg['screen']['test_months']
    return month_list(a, b)


def certify_months(cfg):
    a, b = cfg['screen']['certify_months']
    return month_list(a, b)


def f0(cfg):
    return 'lgbm_trace', int(cfg['seeds']['f0'])


def primary_tau(cfg):
    return float(cfg['thresholds']['certified_tau'][0])


def rule_names(cfg):
    th = cfg['thresholds']
    return ([f'cp{t:g}' for t in th['certified_tau']] + [f'emp{b:g}' for b in th['empirical_beta']] + ['default', 'f1pi'])


def score_rows(model, run, idx, chunk: int = 20000) -> np.ndarray:
    out = np.empty(len(idx), np.float64)
    for s in range(0, len(idx), chunk):
        out[s:s + chunk] = model._score(np.asarray(run.X[idx[s:s + chunk]], dtype=np.float32))
    return out


def margin_rows(booster, run, idx, chunk: int = 20000) -> np.ndarray:
    """Raw LightGBM margins for rows ``idx`` of the cached matrix, read in chunks (bounded memory)."""
    idx = np.asarray(idx)
    out = np.empty(len(idx), np.float64)
    for s in range(0, len(idx), chunk):
        out[s:s + chunk] = booster.predict(np.asarray(run.X[idx[s:s + chunk]], dtype=np.float32), raw_score=True)
    return out


def fmt_pct(v, nd=2):
    return '—' if v is None or (isinstance(v, float) and np.isnan(v)) else f'{100 * v:.{nd}f}'
