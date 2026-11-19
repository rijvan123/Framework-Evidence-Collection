#!/usr/bin/env python3
"""E10 - ledger tamper injection and verification scaling (prediction P8; paper Section 8.9).

Six modification types are injected into a chain of synthetic finding records; a modification is detected
when the recomputed chain no longer reaches the anchored head. Verification time is measured for chains of
10^3 to 10^6 records (log-log slope)."""
import copy
import time

import numpy as np

import _common  # noqa: F401
from tracepe.config import cli
from tracepe.evidence.hashing import GENESIS_SEED, enc, link, rec_hash
from tracepe.evidence.merkle import inclusion_proof, merkle_levels, merkle_root, verify_inclusion
from tracepe.run import Run
from tracepe.utils import log


def record(i, rng):
    return dict(t='ISS', q=i, sid=rng.bytes(32).hex(), vh=rng.bytes(32).hex(), z=rng.bytes(8).hex(), yhat=int(rng.integers(0, 2)),
                state='ISS', actor='issuer-01', ts=f'2020-{1 + i % 9:02d}-{1 + i % 28:02d}T00:00:00Z')


def heads_of(encs, start=GENESIS_SEED):
    out, h = [], start
    for e in encs:
        h = link(h, rec_hash(e))
        out.append(h)
    return out


def main():
    cfg, args = cli(__doc__)
    run = Run(cfg)
    T = cfg['ledger_tests']
    rng = np.random.default_rng(20261006)
    n = int(T['chain_len'])
    recs = [record(i, rng) for i in range(n)]
    encs = [enc(r) for r in recs]
    heads = heads_of(encs)
    anchored = heads[-1]

    def detected(j, new_tail):
        start = heads[j - 1] if j > 0 else GENESIS_SEED
        h = start
        for e in new_tail:
            h = link(h, rec_hash(e))
        return h != anchored

    results = {}
    for kind in ('bit_flip', 'deletion', 'insertion', 'swap', 'timestamp_edit', 'actor_edit'):
        det = 0
        for _ in range(int(T['per_type'])):
            j = int(rng.integers(0, n - 1))
            tail = list(encs[j:])
            if kind == 'bit_flip':
                b = bytearray(tail[0])
                pos = int(rng.integers(0, len(b)))
                b[pos] ^= 1 << int(rng.integers(0, 8))
                tail[0] = bytes(b)
            elif kind == 'deletion':
                tail = tail[1:]
            elif kind == 'insertion':
                tail = [enc(record(10 ** 6 + j, rng))] + tail
            elif kind == 'swap':
                tail[0], tail[1] = tail[1], tail[0]
            else:
                r = copy.deepcopy(recs[j])
                fld = 'ts' if kind == 'timestamp_edit' else 'actor'
                r[fld] = r[fld] + 'x' if kind == 'actor_edit' else r[fld].replace('T00', 'T01')
                tail[0] = enc(r)
            det += detected(j, tail)
        results[kind] = dict(detected=int(det), injected=int(T['per_type']))
        log(f'  {kind}: {det}/{T["per_type"]}')
    # Merkle receipts and a modified leaf
    leaves = [rec_hash(e) for e in encs]
    levels = merkle_levels(leaves)
    root = levels[-1][0]
    ok = all(verify_inclusion(leaves[i], inclusion_proof(levels, i), root) for i in rng.choice(n, size=min(200, n), replace=False))
    mod = list(leaves)
    mod[0] = rec_hash(b'tampered')
    merkle_detect = merkle_root(mod) != root
    # verification scaling
    scaling = []
    for size in T['scaling']:
        size = int(size)
        base = [enc(dict(t='ISS', q=i, sid=f'{i:064x}', state='ISS')) for i in range(size)]
        hs = heads_of(base)
        t0 = time.perf_counter()
        h = GENESIS_SEED
        good = True
        for e, ref in zip(base, hs):
            h = link(h, rec_hash(e))
            if h != ref:
                good = False
                break
        dt = time.perf_counter() - t0
        scaling.append(dict(n=size, seconds=round(dt, 4), ok=good))
        log(f'  verify {size} records: {dt:.4f} s')
    xs = np.log10([s['n'] for s in scaling])
    ys = np.log10([max(s['seconds'], 1e-9) for s in scaling])
    slope = float(np.polyfit(xs, ys, 1)[0]) if len(scaling) >= 2 else None
    R = dict(chain_len=n, tamper=results, all_detected=all(v['detected'] == v['injected'] for v in results.values()),
             receipts_verified=bool(ok), merkle_leaf_modification_detected=bool(merkle_detect), scaling=scaling, loglog_slope=slope)
    R['P8'] = dict(met=bool(R['all_detected'] and slope is not None and 0.9 <= slope <= 1.1))
    run.save('e10_ledger_tests', R)
    log('E10 done: all detected', R['all_detected'], 'slope', slope)


if __name__ == '__main__':
    main()
