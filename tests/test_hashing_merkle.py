"""Canonical encoding, vector hashing, hash chain and Merkle trees (paper Section 4.3, Eqs. 76-80)."""
import hashlib
import random

import numpy as np
import pytest

import s7_reference as S7
from tracepe.evidence import hashing as hh
from tracepe.evidence.merkle import inclusion_proof, merkle_levels, merkle_root, mth_rfc9162, verify_inclusion


def test_enc_is_canonical_and_rejects_floats():
    a = hh.enc({'b': 1, 'a': [1, 2, {'z': 'x', 'y': True}]})
    b = hh.enc({'a': [1, 2, {'y': True, 'z': 'x'}], 'b': 1})
    assert a == b == b'{"a":[1,2,{"y":true,"z":"x"}],"b":1}'
    with pytest.raises(TypeError):
        hh.enc({'x': 0.5})
    assert hh.enc({'s': 'é'}) == b'{"s":"\\u00e9"}'          # ASCII only


def test_enc_matches_s7_probe_encoding():
    rng = random.Random(1)
    for _ in range(200):
        rec = {f'k{rng.randint(0, 9)}': rng.choice([rng.randint(-10**9, 10**9), 'abc', True, None, [1, 'x']]) for _ in range(5)}
        assert hh.enc(rec) == S7.enc(rec)
        e = hh.enc(rec)
        assert hh.rec_hash(e) == S7.rec_hash(e)
        prev = hashlib.sha256(e).digest()
        assert hh.link(prev, hh.rec_hash(e)) == S7.link(prev, S7.rec_hash(e))
    assert hh.GENESIS_SEED == S7.H(S7.DOM + b'genesis\x00')


def test_canonical_vector_and_hash():
    x = np.array([0.0, -0.0, 1.5, 3.0], np.float32)
    c = hh.canonical_vector(x)
    assert not np.signbit(c[1])                               # -0.0 mapped to +0.0
    assert hh.vector_hash(x) == hh.vector_hash(np.array([0.0, 0.0, 1.5, 3.0], np.float32))
    expected = hashlib.sha256(hh.vec_prefix(4) + np.array([0, 0, 1.5, 3], '<f4').tobytes()).hexdigest()
    assert hh.vector_hash(x) == expected
    with pytest.raises(ValueError):
        hh.canonical_vector(np.array([np.nan], np.float32))
    y = x.copy()
    y[2] = np.nextafter(y[2], np.float32(np.inf))             # one ulp changes the hash
    assert hh.vector_hash(y) != hh.vector_hash(x)


def test_vector_hashes_batch_equals_single():
    X = np.random.default_rng(0).normal(size=(57, 13)).astype(np.float32)
    X[3, 2] = -0.0
    assert list(hh.vector_hashes(X, chunk=10)) == [hh.vector_hash(r) for r in X]


def test_float_hex_round_trip():
    for v in (0.0, 1.0, -2.5, 6.348, 1e-30):
        assert hh.hex2f64(hh.f64hex(v)) == v
        assert hh.hex2f32(hh.f32hex(v)) == float(np.float32(v))


@pytest.mark.parametrize('n', list(range(0, 70)) + [127, 128, 129, 255, 256, 257, 300])
def test_merkle_root_equals_rfc9162(n):
    leaves = [hashlib.sha256(str(i).encode()).digest() for i in range(n)]
    assert merkle_root(leaves) == mth_rfc9162(leaves) == S7.merkle_root(leaves)


def test_inclusion_proofs():
    leaves = [f'record {i}'.encode() for i in range(301)]
    levels = merkle_levels(leaves)
    root = merkle_root(leaves)
    for i in (0, 1, 2, 150, 299, 300):
        pr = inclusion_proof(levels, i)
        assert verify_inclusion(leaves[i], pr, root)
        assert not verify_inclusion(b'other', pr, root)
    assert len(inclusion_proof(levels, 7)) <= 9
