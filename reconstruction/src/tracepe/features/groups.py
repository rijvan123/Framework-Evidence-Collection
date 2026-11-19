"""EMBER feature version 2 group map (paper Table 'groupmap'; order of PEFeatureExtractor(feature_version=2)).

Every boundary is checked by invariants that fail when the boundary is shifted by one column, so the
invariant set doubles as an intake check that rejects vectors of another feature version (F4)."""
from __future__ import annotations

import numpy as np

GROUPS = [('ByteHistogram', 0, 256), ('ByteEntropyHistogram', 256, 512), ('StringExtractor', 512, 616),
          ('GeneralFileInfo', 616, 626), ('HeaderFileInfo', 626, 688), ('SectionInfo', 688, 943),
          ('ImportsInfo', 943, 2223), ('ExportsInfo', 2223, 2351), ('DataDirectories', 2351, 2381)]
GROUP_NAMES = [g for g, _, _ in GROUPS]
D = 2381
COFF_COL = 626                          # HeaderFileInfo[0] = COFF TimeDateStamp
GEN_FLAG_COLS = [618, 621, 622, 623, 624]   # has_debug, has_relocations, has_resources, has_signature, has_tls
PRINTABLES_COL = 514
PRINTABLE_DIST = (515, 611)
BEH = (256, 512)                         # 16 entropy bins x 16 byte (high-nibble) bins, row-major


def group_of_column() -> np.ndarray:
    g = np.empty(D, np.int64)
    for i, (_, a, b) in enumerate(GROUPS):
        g[a:b] = i
    return g


def group_sum(contrib: np.ndarray) -> np.ndarray:
    """Sum per-feature attributions (n x 2381, bias column removed) over the nine groups."""
    return np.stack([contrib[:, a:b].sum(axis=1) for _, a, b in GROUPS], axis=1)


def _chunked(X, fn, cols, chunk=20000):
    return np.concatenate([fn(np.asarray(X[s:s + chunk, cols], dtype=np.float64)) for s in range(0, X.shape[0], chunk)])


def check_invariants(X, chunk: int = 20000) -> tuple[dict, np.ndarray]:
    """Pass rates of the intake invariants and a per-row pass mask."""
    n = X.shape[0]
    sums = lambda a: a.sum(axis=1)
    integral = lambda a: np.all(a == np.round(a), axis=1)
    bh = _chunked(X, sums, slice(0, 256), chunk)
    be = _chunked(X, sums, slice(256, 512), chunk)
    printables = np.asarray(X[:, PRINTABLES_COL], dtype=np.float64)
    pdist = _chunked(X, sums, slice(*PRINTABLE_DIST), chunk)
    ok = {}
    ok['ByteHistogram_rows_sum_to_1'] = np.abs(bh - 1) <= 1e-4
    ok['ByteEntropyHistogram_rows_sum_to_1'] = np.abs(be - 1) <= 1e-4
    ok['printabledist_sums_to_1_when_printables_gt0'] = (printables <= 0) | (np.abs(pdist - 1) <= 1e-4)
    ok['GeneralFileInfo_integer'] = _chunked(X, integral, slice(616, 626), chunk)
    ok['GeneralFileInfo_flags_binary'] = _chunked(X, lambda a: np.all(np.isin(a, [0, 1]), axis=1), GEN_FLAG_COLS, chunk)
    ok['HeaderFileInfo_integer'] = _chunked(X, integral, slice(626, 688), chunk)
    ok['SectionInfo_general_integer'] = _chunked(X, integral, slice(688, 693), chunk)
    ok['SectionInfo_zero_size_le_count'] = np.asarray(X[:, 689]) <= np.asarray(X[:, 688])
    ok['ImportsInfo_integer'] = _chunked(X, integral, slice(943, 2223), chunk)
    ok['ExportsInfo_integer'] = _chunked(X, integral, slice(2223, 2351), chunk)
    ok['DataDirectories_integer_nonneg'] = _chunked(
        X, lambda a: np.all(a == np.round(a), axis=1) & np.all(a >= 0, axis=1), slice(2351, 2381), chunk)
    row_ok = np.ones(n, bool)
    for v in ok.values():
        row_ok &= v
    frac = lambda m: round(float(np.mean(m)), 6)
    report = {k: frac(v) for k, v in ok.items()}
    # shifted-window controls: these must FAIL for the true layout (boundary sensitivity)
    report['shift_plus1_ByteHistogram_sum_to_1'] = frac(np.abs(_chunked(X, sums, slice(1, 257), chunk) - 1) <= 1e-4)
    report['shift_minus1_ByteEntropy_sum_to_1'] = frac(np.abs(_chunked(X, sums, slice(255, 511), chunk) - 1) <= 1e-4)
    pd2 = _chunked(X, sums, slice(PRINTABLE_DIST[0] + 1, PRINTABLE_DIST[1] + 1), chunk)
    report['shift_plus1_printabledist_sum_to_1'] = frac(np.abs(pd2[printables > 0] - 1) <= 1e-4) if (printables > 0).any() else None
    report['SectionInfo_entropy_hashed_integer'] = frac(_chunked(X, integral, slice(743, 793), chunk))
    report['rows_with_printables_eq0'] = int((printables == 0).sum())
    report['rows_failing_any'] = int((~row_ok).sum())
    return report, row_ok


def packing_indicator(X, tau_p: float = 1 / 32) -> np.ndarray:
    """Eq. (19): max over byte bins u of the mass in the two highest entropy bins (r >= 14) exceeds tau_p."""
    beh = np.asarray(X[:, BEH[0]:BEH[1]], dtype=np.float64).reshape(-1, 16, 16)
    return beh[:, 14:, :].sum(axis=1).max(axis=1) > tau_p


def high_entropy_mass(X) -> np.ndarray:
    beh = np.asarray(X[:, BEH[0]:BEH[1]], dtype=np.float64).reshape(-1, 16, 16)
    return beh[:, 14:, :].sum(axis=(1, 2))
