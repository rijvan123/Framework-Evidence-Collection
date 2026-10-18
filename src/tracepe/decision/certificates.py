"""Time-indexed error certificates (M11; Eqs. (88), (101)-(103)).

A retrospective certificate C^R_{v,m,stratum} holds counts, one-sided 95% Clopper-Pearson bounds and the
tolerances; FPR is certified only where at least n_min dated benign files support it."""
from __future__ import annotations

import math

import numpy as np

from .thresholds import cp_upper
from ..evidence.hashing import f64hex


def retrospective(fp: int, n_b: int, fn: int, n_m: int, tau_fpr: float, tau_fnr: float,
                  n_min: int = 500, conf: float = 0.95) -> dict:
    fpr_ub = cp_upper(fp, n_b, conf) if n_b >= n_min else None
    fnr_ub = cp_upper(fn, n_m, conf) if n_m > 0 else None
    fpr_ok = fpr_ub is not None and fpr_ub <= tau_fpr
    fnr_ok = fnr_ub is not None and fnr_ub <= tau_fnr
    return dict(fp=int(fp), n_b=int(n_b), fn=int(fn), n_m=int(n_m),
                fpr=(fp / n_b if n_b else None), fpr_ub=fpr_ub, fnr=(fn / n_m if n_m else None), fnr_ub=fnr_ub,
                tau_fpr=tau_fpr, tau_fnr=tau_fnr, fpr_ok=bool(fpr_ok), fnr_ok=bool(fnr_ok),
                valid=bool(fpr_ok and fnr_ok), fpr_powered=n_b >= n_min)


def ppv_lower(fn: int, n_m: int, fp: int, n_b: int, pi: float) -> float:
    """Eq. (101): Bonferroni-split 97.5% bounds on TPR and FPR."""
    tpr_lb = 1 - cp_upper(fn, n_m, 0.975)
    fpr_ub = cp_upper(fp, n_b, 0.975)
    den = tpr_lb * pi + fpr_ub * (1 - pi)
    return float(tpr_lb * pi / den) if den > 0 else float('nan')


def lr_cap(fn: int, n_m: int, fp: int, n_b: int) -> float:
    """Eq. (103), left: capped likelihood ratio of a positive verdict, limited by data resolution."""
    tpr_lb = 1 - cp_upper(fn, n_m, 0.975)
    fpr_ub = cp_upper(fp, n_b, 0.975)
    return float(tpr_lb / fpr_ub) if fpr_ub > 0 else float('inf')


def cllr(lr, y) -> float:
    """Log-likelihood-ratio cost Cllr (Brümmer and du Preez), used for KB12 with the capped LR of (S7.19)."""
    lr = np.clip(np.asarray(lr, dtype=np.float64), 1e-12, 1e12)
    y = np.asarray(y).astype(bool)
    pos = np.log2(1 + 1 / lr[y]).mean() if y.any() else 0.0
    neg = np.log2(1 + lr[~y]).mean() if (~y).any() else 0.0
    return float(0.5 * (pos + neg))


def svr(valid_flags) -> float:
    v = [bool(x) for x in valid_flags]
    return sum(v) / len(v) if v else float('nan')


def certificate_record(model_id: str, month: str, stratum: str, cert: dict, theta: float, kind: str) -> dict:
    """Ledger CERT record (no floats: bounds in parts-per-billion integers)."""
    ppb = lambda v: None if v is None or (isinstance(v, float) and math.isnan(v)) else int(round(v * 1e9))
    return dict(t='CERT', model=model_id, month=month, stratum=stratum, kind=kind, fp=cert['fp'], n_b=cert['n_b'],
                fn=cert['fn'], n_m=cert['n_m'], fpr_ub_ppb=ppb(cert['fpr_ub']), fnr_ub_ppb=ppb(cert['fnr_ub']),
                tau_fpr_ppb=ppb(cert['tau_fpr']), tau_fnr_ppb=ppb(cert['tau_fnr']), valid=cert['valid'],
                theta=f64hex(theta))
