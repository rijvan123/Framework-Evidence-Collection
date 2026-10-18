"""Prevalence-resampled streams (paper Section 7.3): keep all benign files of a month, sample malware to pi."""
from __future__ import annotations

import numpy as np


def prevalence_sample(benign_idx, malware_idx, pi: float, rng) -> np.ndarray:
    nb, nm = len(benign_idx), len(malware_idx)
    k = int(round(pi * nb / (1 - pi)))
    if k <= nm:
        sel_m = rng.choice(malware_idx, size=k, replace=False) if k > 0 else np.array([], dtype=np.asarray(malware_idx).dtype)
        return np.sort(np.concatenate([np.asarray(benign_idx), sel_m]))
    kb = int(round(nm * (1 - pi) / pi))
    sel_b = rng.choice(benign_idx, size=min(kb, nb), replace=False)
    return np.sort(np.concatenate([sel_b, np.asarray(malware_idx)]))
