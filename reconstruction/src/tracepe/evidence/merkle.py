"""RFC 9162-style Merkle tree hash (leaf = H(0x00||x), node = H(0x01||l||r)).

The level-wise construction with promotion of an unpaired right node is identical to the recursive
MTH of RFC 9162 Section 2.1.1 (tests/test_hashing_merkle.py checks this for n = 0..300)."""
from __future__ import annotations

from .hashing import H


def leaf_hash(x: bytes) -> bytes:
    return H(b'\x00' + x)


def node_hash(left: bytes, right: bytes) -> bytes:
    return H(b'\x01' + left + right)


def merkle_levels(leaves) -> list[list[bytes]]:
    level = [leaf_hash(x) for x in leaves]
    levels = [level]
    while len(level) > 1:
        nxt = [node_hash(level[i], level[i + 1]) for i in range(0, len(level) - 1, 2)]
        if len(level) % 2:
            nxt.append(level[-1])
        level = nxt
        levels.append(level)
    return levels


def merkle_root(leaves) -> bytes:
    leaves = list(leaves)
    if not leaves:
        return H(b'')
    return merkle_levels(leaves)[-1][0]


def mth_rfc9162(leaves) -> bytes:
    """Reference recursive definition (RFC 9162, 2.1.1): split at the largest power of two < n."""
    n = len(leaves)
    if n == 0:
        return H(b'')
    if n == 1:
        return leaf_hash(leaves[0])
    k = 1
    while k * 2 < n:
        k *= 2
    return node_hash(mth_rfc9162(leaves[:k]), mth_rfc9162(leaves[k:]))


def inclusion_proof(levels, idx: int) -> list[tuple[str, bytes]]:
    proof = []
    for level in levels[:-1]:
        sib = idx ^ 1
        if sib < len(level):
            proof.append(('L' if sib < idx else 'R', level[sib]))
        idx //= 2
    return proof


def verify_inclusion(leaf: bytes, proof, root: bytes) -> bool:
    h = leaf_hash(leaf)
    for side, s in proof:
        h = node_hash(s, h) if side == 'L' else node_hash(h, s)
    return h == root
