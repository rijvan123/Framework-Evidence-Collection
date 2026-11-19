#!/usr/bin/env python3
"""E0: open the S10 ledger (M1-M4): MAN0, PREREG (protocol hash), EXT, ACQ x n, SCR summary, DUP, ORC, ANC.
Runs before any model is trained or any 2020 sample is scored."""
import json, hashlib, time
import numpy as np, pandas as pd
import s10_common as C

t0 = time.perf_counter()
m = C.load_meta(); X = C.load_X()
files = {f: C.sha256_file(f'{C.SRC}/{f}') for f in ['bodmas.npz', 'bodmas_metadata.csv', 'bodmas_malware_category.csv']}
device = {'bodmas.npz': '0a833e46c22c096920c8068d4fb54b868067777c277c0a6eecf527c98d7e5a9e',
          'bodmas_metadata.csv': '5f1dc793cac4a540ef9e0c40fd7897142095621790d3c6f2d6637971806f4c50',
          'bodmas_malware_category.csv': '617fda69347ec907a79f198add431c8bb39102781de41cc03b7cd1718cff2198'}
assert files == device, 'F1: digest mismatch at intake'
proto = open(f'{C.ROOT}/S10_protocol.md', 'rb').read()
proto_h = hashlib.sha256(proto).hexdigest()
store = C.Store()
assert store.put(proto) == proto_h

C.ledger_init(dict(t='MAN0', files=files, source_sha256=device, feature_version=2, dims=C.D, case_id='S10-BODMAS',
                   extractor_claim='EMBER features.py v2 / LIEF 0.9.0 (declared by BODMAS dataset page; not re-executed)'))
C.ledger_append([dict(t='PREREG', protocol_sha256=proto_h, doc='S10_protocol.md', note='locked before test scoring'),
                 dict(t='EXT', feature_version=2, lief='0.9.0 (declared)', status='declared, not executed',
                      groups=[[g, a, b] for g, a, b in C.GROUPS], env=C.env_info())])
# ACQ per evidence item (vector hash binds the canonical float32 vector; N5 derivation gap stated in EXT)
recs = []; vh = []
t = time.perf_counter()
for i in range(len(m)):
    h = C.vec_hash(X[i]); vh.append(h)
    recs.append(dict(t='ACQ', q_src=i, sid=m['sha'].iat[i], vh=h, fs=m['ts_raw'].iat[i], off=bool(m['has_offset'].iat[i]),
                     st=m['stratum'].iat[i], ds=files['bodmas.npz'][:16]))
hash_s = time.perf_counter() - t
for s in range(0, len(recs), 20000):
    C.ledger_append(recs[s:s + 20000], epoch='setup')
np.save(f'{C.CACHE}/vh.npy', np.array(vh))
# SCR summary, duplicate audit (exact vectors), oracle snapshot
strata = {k: {str(y): int(v) for y, v in g.groupby('y').size().items()} for k, g in m.groupby('stratum')}
vhs = pd.Series(vh)
dup = vhs[vhs.duplicated(keep=False)]
groups = []
for h, idx in dup.groupby(dup).groups.items():
    idx = sorted(idx, key=lambda i: (m['ts'].iat[i], m['sha'].iat[i]))
    groups.append(dict(t='DUP', vh=h, keep=m['sha'].iat[idx[0]], drop=[m['sha'].iat[j] for j in idx[1:]],
                       strata=[m['stratum'].iat[j] for j in idx], labels=[int(m['y'].iat[j]) for j in idx]))
orc_leaves = [C.enc(dict(sid=m['sha'].iat[i], y=int(m['y'].iat[i]), fam=m['family_raw'].iat[i], cat=m['category'].iat[i]))
              for i in range(len(m))]
orc_root = C.merkle_root(orc_leaves).hex()
C.ledger_append([dict(t='SCR', kind='summary', strata=strata, spike_days_k10=m.attrs['spike10'], spike_days_k4=m.attrs['spike4'],
                      rule='all-sample daily count > median + 10 MAD (k=4 sensitivity)')] + groups +
                [dict(t='ORC', root=orc_root, oracle='BODMAS release labels', snapshot='2021 release as distributed', n=len(m))])
C.ledger_anchor('setup')
v = C.verify_main_ledger()
res = dict(files=files, source_match=True, protocol_sha256=proto_h, strata=strata, dup_groups=len(groups),
           oracle_root=orc_root, vec_hash_seconds=round(hash_s, 2), verify=v, seconds=round(time.perf_counter() - t0, 1))
C.jdump(res, f'{C.OUT}/e0_init.json')
print(json.dumps(res, indent=1, default=str))
