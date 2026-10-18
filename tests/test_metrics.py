"""Metric definitions (Eqs. 55, 59-70) against independent implementations."""
import numpy as np
import pytest
from sklearn.metrics import matthews_corrcoef, roc_auc_score

from tracepe.evaluation import metrics as M
from tracepe.evaluation.stats import cliffs_delta, delong, friedman, holm, mcnemar_exact


def random_counts(rng):
    return dict(tp=int(rng.integers(1, 5000)), fp=int(rng.integers(0, 300)), fn=int(rng.integers(0, 2000)), tn=int(rng.integers(100, 9000)))


def test_prevalence_reweighting_equals_eq55():
    rng = np.random.default_rng(0)
    for _ in range(100):
        c = random_counts(rng)
        for pi in (0.001, 0.01, 0.1, 0.5):
            m = M.from_counts(**c, pi_report=pi, pi_prec=pi)
            tpr = c['tp'] / (c['tp'] + c['fn'])
            fpr = c['fp'] / (c['fp'] + c['tn'])
            assert m['precision_pi_report'] == pytest.approx(M.precision_analytic(tpr, fpr, pi), rel=1e-10)


def test_native_mcc_matches_sklearn():
    rng = np.random.default_rng(1)
    y = rng.integers(0, 2, 5000)
    p = np.where(rng.random(5000) < 0.85, y, 1 - y)
    c = M.counts(p.astype(float), y, 0.5)
    m = M.from_counts(c['tp'], c['fp'], c['fn'], c['tn'])
    assert m['mcc_native'] == pytest.approx(matthews_corrcoef(y, p), abs=1e-12)


def test_auc_matches_sklearn_and_delong():
    rng = np.random.default_rng(2)
    y = rng.integers(0, 2, 3000)
    s = y + rng.normal(scale=1.2, size=3000)
    assert M.auc(s, y) == pytest.approx(roc_auc_score(y, s), abs=1e-12)
    d = delong(y, s)
    assert d['auc'] == pytest.approx(roc_auc_score(y, s), abs=1e-12)
    assert 0 <= d['ci'][0] < d['auc'] < d['ci'][1] <= 1


def test_aut():
    assert M.aut([0.9] * 7) == pytest.approx(0.9)
    assert M.aut([1.0, 0.0]) == pytest.approx(0.5)
    assert M.aut([1.0, 0.5, 0.0]) == pytest.approx(0.5)
    assert np.isnan(M.aut([0.9, float('nan')]))


def test_statistics_helpers():
    assert holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    assert mcnemar_exact(0, 0) == 1.0 and mcnemar_exact(20, 2) < 0.001
    assert cliffs_delta([2, 3, 4], [0, 1, 1]) == 1.0
    r = friedman(np.array([[1, 2, 3], [1, 2, 3], [1, 2, 3], [1, 2, 3]], float))
    assert r['kendall_w'] == pytest.approx(1.0)
