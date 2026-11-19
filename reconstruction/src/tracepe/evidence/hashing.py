"""Hash constructions of the evidence layer (paper Eqs. (85)-(87); S7 definitions S7.1-S7.3).

All hashes are SHA-256 (FIPS 180-4) with the domain prefix ``TRACE-PE/v1/<type>\\0`` so that equal byte
strings of different record types cannot collide. The constructions are byte-for-byte those of the
paper's S7 probe code, so the acquisition-chain head and the oracle root are reproducible checkpoints.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np

DOM = b'TRACE-PE/v1/'


def H(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(chunk), b''):
            h.update(b)
    return h.hexdigest()


def tagged(tag: str, payload: bytes) -> bytes:
    """Domain-separated hash H(DOM || tag || 0x00 || payload)."""
    return H(DOM + tag.encode('ascii') + b'\x00' + payload)


# ---------------------------------------------------------------- canonical vectors (Eq. 85 / S7.1)
def vec_prefix(d: int) -> bytes:
    return DOM + b'vec\x00' + int(d).to_bytes(4, 'little')


_ZERO32 = np.float32(0)


def canonical_vector(x) -> np.ndarray:
    """float32, little-endian, IEEE -0.0 mapped to +0.0; non-finite values are rejected."""
    x = np.asarray(x, dtype=np.float32)
    if not np.all(np.isfinite(x)):
        raise ValueError('non-finite value in feature vector (rejected at intake)')
    return (x + _ZERO32).astype('<f4', copy=False)


def vector_hash(x) -> str:
    x = canonical_vector(x)
    return hashlib.sha256(vec_prefix(x.shape[-1]) + x.tobytes()).hexdigest()


def vector_hashes(X, chunk: int = 20000) -> np.ndarray:
    """Hash every row of X (memory-mapped arrays are read in chunks)."""
    n, d = X.shape
    pre = vec_prefix(d)
    out = np.empty(n, dtype=object)
    for s in range(0, n, chunk):
        blk = np.asarray(X[s:s + chunk], dtype=np.float32)
        if not np.all(np.isfinite(blk)):
            raise ValueError(f'non-finite values in rows {s}..{s + len(blk)}')
        blk = (blk + _ZERO32).astype('<f4', copy=False)
        for i in range(len(blk)):
            out[s + i] = hashlib.sha256(pre + blk[i].tobytes()).hexdigest()
    return out


# ---------------------------------------------------------------- records and chain (Eq. 86 / S7.2)
def _check_no_float(o, path='$'):
    if isinstance(o, float):
        raise TypeError(f'float at {path}: records carry floats as binary32/binary64 hex strings')
    if isinstance(o, dict):
        for k, v in o.items():
            _check_no_float(v, f'{path}.{k}')
    elif isinstance(o, (list, tuple)):
        for i, v in enumerate(o):
            _check_no_float(v, f'{path}[{i}]')


def enc(obj, check: bool = True) -> bytes:
    """Canonical JSON: keys sorted, no whitespace, ASCII only, no floats (deterministic subset of RFC 8785)."""
    if check:
        _check_no_float(obj)
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def rec_hash(e: bytes) -> bytes:
    return H(DOM + b'rec\x00' + e)


def link(prev: bytes, rh: bytes) -> bytes:
    return H(DOM + b'chain\x00' + prev + rh)


GENESIS_SEED = H(DOM + b'genesis\x00')   # h_0; the first record (MAN0) is linked to it


def chain_heads(encoded_records, start: bytes = GENESIS_SEED) -> list[bytes]:
    heads, h = [], start
    for e in encoded_records:
        h = link(h, rec_hash(e))
        heads.append(h)
    return heads


# ---------------------------------------------------------------- floats as hex
def f32hex(v) -> str:
    """IEEE-754 binary32, big-endian hex (display values such as scores and attributions).

    Note: a numpy *scalar* ignores the byte order of ``astype('>f4')`` (scalars are always native), so the
    encoding goes through a one-element array to be big-endian on every platform."""
    return np.array([v], dtype='>f4').tobytes().hex()


def f64hex(v) -> str:
    """IEEE-754 binary64, big-endian hex (bit-exact re-execution of margins and thresholds)."""
    return np.array([v], dtype='>f8').tobytes().hex()


def hex2f32(s: str) -> float:
    return float(np.frombuffer(bytes.fromhex(s), dtype='>f4')[0])


def hex2f64(s: str) -> float:
    return float(np.frombuffer(bytes.fromhex(s), dtype='>f8')[0])
