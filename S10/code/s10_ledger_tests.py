#!/usr/bin/env python3
"""P8 (U8): tamper detection by injection (10^4 trials per type x 6 types) and verification-time scaling
(n in {10^3, 10^4, 10^5, 10^6}; log-log slope). Synthetic ISS-like records; chain construction as S7_probes.py.
Output: out/ledger_tests.json"""
import json, time, hashlib
import numpy as np
import s10_common as C

rng = np.random.default_rng(8)


def make_records(n):
    recs = []
    for i in range(n):
        recs.append(C.enc(dict(t='ISS', q=i, sid=hashlib.sha256(i.to_bytes(8, 'little')).hexdigest(), s=C.f32hex(rng.normal()),
                               yhat=int(rng.integers(0, 2)), actor='analyst-%02d' % int(rng.integers(0, 20)),
                               ts='2020-%02d-%02dT00:00:00Z' % (int(rng.integers(3, 10)), int(rng.integers(1, 29))))))
    return recs


def build(recs):
    g = C.enc(dict(t='MAN0', case='tamper-test')); h = C.link(C.H(C.DOM + b'genesis\x00'), C.rec_hash(g)); heads = []
    for e in recs:
        h = C.link(h, C.rec_hash(e)); heads.append(h)
    return g, heads


def verify(g, recs, heads, start=0):
    """Recompute from `start` (heads before `start` are trusted as already verified) and compare against stored heads
    and the anchored final head; any length change is caught by the anchored head/record count."""
    h = C.link(C.H(C.DOM + b'genesis\x00'), C.rec_hash(g)) if start == 0 else heads[start - 1]
    for j in range(start, len(recs)):
        h = C.link(h, C.rec_hash(recs[j]))
        if j >= len(heads) or h != heads[j]:
            return False
    return len(recs) == len(heads) and h == heads[-1]


N = 2000; recs = make_records(N); g, heads = build(recs)
assert verify(g, recs, heads)
types = ['bitflip', 'delete', 'insert', 'swap', 'ts_edit', 'actor_edit']; res = {}
t0 = time.perf_counter()
for ty in types:
    det = 0; trials = 10000
    for _ in range(trials):
        j = int(rng.integers(0, N - 1)); r2 = list(recs)
        if ty == 'bitflip':
            b = bytearray(r2[j]); pos = int(rng.integers(0, len(b))); b[pos] ^= 1 << int(rng.integers(0, 7)); r2[j] = bytes(b)
        elif ty == 'delete':
            del r2[j]
        elif ty == 'insert':
            r2.insert(j, C.enc(dict(t='ISS', q=-1, sid='0' * 64, s=C.f32hex(0.0), yhat=1, actor='insider', ts='2020-05-05T00:00:00Z')))
        elif ty == 'swap':
            r2[j], r2[j + 1] = r2[j + 1], r2[j]
        elif ty == 'ts_edit':
            d = json.loads(r2[j]); d['ts'] = d['ts'].replace('T00', 'T01'); r2[j] = C.enc(d)
        elif ty == 'actor_edit':
            d = json.loads(r2[j]); d['actor'] = 'analyst-99'; r2[j] = C.enc(d)
        det += (not verify(g, r2, heads, start=j))
    res[ty] = dict(trials=trials, detected=det, rate=det / trials)
    print(ty, res[ty], flush=True)
inj_s = time.perf_counter() - t0
untouched_ok = verify(g, recs, heads)
# verification-time scaling
scal = []
for n in (1000, 10000, 100000, 1000000):
    rr = [C.enc(dict(t='ISS', q=i, s=C.f32hex(0.5))) for i in range(n)]
    g2, h2 = build(rr)
    t = time.perf_counter(); ok = verify(g2, rr, h2); sec = time.perf_counter() - t
    scal.append(dict(n=n, seconds=sec, ok=ok)); print('scale', n, round(sec, 3), ok, flush=True)
    del rr, h2
ln = np.log10([s['n'] for s in scal]); lt = np.log10([s['seconds'] for s in scal]); slope = float(np.polyfit(ln, lt, 1)[0])
out = dict(injections=res, all_detected=all(v['detected'] == v['trials'] for v in res.values()), untouched_verifies=untouched_ok,
           injection_seconds=inj_s, scaling=scal, loglog_slope=slope, P8_pass=bool(all(v['detected'] == v['trials'] for v in res.values()) and 0.9 <= slope <= 1.1))
C.jdump(out, f'{C.OUT}/ledger_tests.json'); print(json.dumps(out, indent=1))
