"""EMBER v2 vectoriser: batched and per-sample implementations agree, and the layout matches the group map."""
import json

import numpy as np

from tracepe.data.ember import read_lines, scan_jsonl, vectorize, vectorize_one
from tracepe.data.synthetic import make_synthetic_ember
from tracepe.features.groups import D, GROUPS


def test_batch_equals_per_sample(tmp_path):
    info = make_synthetic_ember(tmp_path, per_class_month=3, seed=5)
    raws = [json.loads(l) for l in open(tmp_path / 'train_features_0.jsonl')]
    X = vectorize(raws)
    assert X.shape == (len(raws), D) and X.dtype == np.float32
    for i, r in enumerate(raws[:40]):
        assert np.array_equal(X[i], vectorize_one(r)), i
    assert info['train'] == len(raws)


def test_layout_invariants(tmp_path):
    make_synthetic_ember(tmp_path, per_class_month=2, seed=6)
    raws = [json.loads(l) for l in open(tmp_path / 'test_features.jsonl')]
    X = vectorize(raws)
    assert np.allclose(X[:, 0:256].sum(1), 1, atol=1e-5)          # ByteHistogram normalised
    assert np.allclose(X[:, 256:512].sum(1), 1, atol=1e-5)        # ByteEntropyHistogram normalised
    assert sum(b - a for _, a, b in GROUPS) == D == 2381


def test_scan_and_read(tmp_path):
    make_synthetic_ember(tmp_path, per_class_month=2, seed=7)
    rows = scan_jsonl([tmp_path / 'test_features.jsonl'])
    assert rows and all(len(r) == 5 for r in rows)
    sel = {}
    for f, ln, lab, app, sha in rows[:5]:
        sel.setdefault(f, []).append(ln)
    got = read_lines(sel)
    assert [g['sha256'] for g in got] == [r[4] for r in rows[:5]]
