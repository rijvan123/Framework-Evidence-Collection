"""Synthetic releases in BODMAS and EMBER-raw format for smoke tests.

The BODMAS-format generator reproduces the *structure* the temporal-evidence screen must handle:
date-only benign timestamps, a placeholder day with VirusShare_ identifiers, bulk-ingest days with
second-level times, naive (offset-free) pre-window timestamps, exact duplicate pairs, near-empty
January/February benign months, unseen families and a drifting family in July. Feature vectors obey
the EMBER v2 intake invariants. Numbers computed on synthetic data are meaningless."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..evidence.hashing import sha256_file

CATS = {'trojan': 0.5, 'worm': 0.25, 'backdoor': 0.12, 'downloader': 0.05, 'ransomware': 0.04, 'dropper': 0.04}
KNOWN = ['wabot', 'ceeinject', 'zbot', 'tofsee', 'salgorea', 'wacatac', 'glupteba', 'upatre', 'sfone', 'berbew',
         'gamarue', 'virut', 'sality', 'ramnit', 'emotet', 'trickbot', 'dridex', 'qakbot', 'nanocore', 'remcos',
         'small', 'agent', 'kryptik']
UNSEEN = ['cosmicduke', 'blackmoon', 'phorpiex', 'smokeloader', 'lokibot', 'formbook']


def _features(y, fam_idx, drift, rng):
    """EMBER v2-shaped vectors that satisfy the intake invariants, with class, family and drift signal.
    A drifting family (from July 2020) and a few 'hard' samples per class look like the other class."""
    n = len(y)
    X = np.zeros((n, 2381), np.float32)
    nf = int(fam_idx.max()) + 2
    fam_imp = rng.integers(943, 2223, size=(nf, 40))            # family import signatures
    fam_hdr = rng.integers(627, 688 - 11, size=(nf, 5))
    ben_imp = rng.integers(943, 2223, size=60)
    mal = y == 1
    hard = rng.random(n) < np.where(mal, 0.06, 0.03)
    shifted = mal & (drift | hard)                                 # malware that looks benign
    malish = (mal & ~shifted) | (~mal & hard)                      # what the distributions treat as malicious
    # byte histogram
    base_b = rng.gamma(2.0, 1.0, size=256)
    base_m = rng.gamma(1.0, 1.0, size=256)
    alpha = np.where(malish[:, None], base_m[None, :], base_b[None, :])
    bh = rng.gamma(alpha + 0.05, 1.0)
    X[:, :256] = bh / bh.sum(axis=1, keepdims=True)
    # byte-entropy histogram (16 x 16): malware puts more mass in high-entropy rows
    w = np.ones((n, 16))
    w[:, 14:] += np.where(malish, 4.0, 0.3)[:, None] * rng.random((n, 1))
    beh = rng.gamma(1.0, 1.0, size=(n, 16, 16)) * w[:, :, None]
    beh = beh.reshape(n, 256)
    X[:, 256:512] = beh / beh.sum(axis=1, keepdims=True)
    # strings
    X[:, 512] = rng.poisson(np.where(malish, 800, 1500))
    X[:, 513] = rng.gamma(4.0, 2.0, size=n)
    X[:, 514] = rng.poisson(20000, size=n) + 1
    pdist = rng.gamma(1.0, 1.0, size=(n, 96))
    X[:, 515:611] = pdist / pdist.sum(axis=1, keepdims=True)
    X[:, 611] = rng.uniform(4.5, 6.5, size=n)
    X[:, 612:616] = rng.poisson([3, 1, 2, 2], size=(n, 4))
    # general file info (flags binary)
    X[:, 616] = np.round(rng.lognormal(np.where(malish, 12.0, 13.0), 1.0))
    X[:, 617] = X[:, 616] + np.round(rng.lognormal(10, 1, size=n))
    X[:, 618] = rng.random(n) < np.where(malish, 0.2, 0.6)
    X[:, 619] = rng.poisson(np.where(malish, 1, 5))
    X[:, 620] = rng.poisson(np.where(malish, 15, 60))
    X[:, 621] = rng.random(n) < 0.7
    X[:, 622] = rng.random(n) < np.where(malish, 0.6, 0.9)
    sig = rng.random(n) < np.where(malish, 0.05, 0.6)
    X[:, 623] = sig
    X[:, 624] = rng.random(n) < 0.2
    X[:, 625] = rng.poisson(2, size=n)
    # header: COFF timestamp (float32-representable integers), hashed blocks, versions
    X[:, 626] = np.round(rng.uniform(1.2e9, 1.6e9, size=n) / 128) * 128
    X[rng.random(n) < 0.03, 626] = 0
    for i in range(n):
        if malish[i] and mal[i]:
            cols = fam_hdr[fam_idx[i]]
        else:
            cols = rng.choice(np.arange(627, 677), size=5, replace=False)
        X[i, cols] = rng.choice([-1.0, 1.0], size=len(cols))
    X[:, 677:688] = rng.poisson(5, size=(n, 11))
    # sections
    nsec = rng.poisson(4, size=n) + 1
    X[:, 688] = nsec
    X[:, 689] = rng.binomial(nsec, 0.1)
    X[:, 690] = rng.binomial(nsec, 0.05)
    X[:, 691] = rng.binomial(nsec, 0.4)
    X[:, 692] = rng.binomial(nsec, 0.5)
    X[:, 693:743] = np.round(rng.normal(0, 1, size=(n, 50)) * (rng.random((n, 50)) < 0.08) * 1e4)
    X[:, 743:793] = rng.normal(0, 3, size=(n, 50)) * (rng.random((n, 50)) < 0.08)
    X[:, 793:843] = np.round(rng.normal(0, 1, size=(n, 50)) * (rng.random((n, 50)) < 0.08) * 1e4)
    X[:, 843:893] = rng.integers(-1, 2, size=(n, 50)) * (rng.random((n, 50)) < 0.06)
    X[:, 893:943] = rng.integers(-1, 2, size=(n, 50)) * (rng.random((n, 50)) < 0.06)
    # imports: family signature for malware, benign pool otherwise
    for i in range(n):
        if mal[i] and not shifted[i]:
            cols = rng.choice(fam_imp[fam_idx[i]], size=25, replace=False)
        elif mal[i]:                                   # weak residual family signal
            cols = np.r_[rng.choice(fam_imp[fam_idx[i]], size=4, replace=False), rng.choice(ben_imp, size=21, replace=False)]
        else:
            cols = rng.choice(ben_imp, size=25, replace=False)
        noise = rng.integers(943, 2223, size=15)
        X[i, cols] += rng.choice([-1.0, 1.0], size=len(cols))
        X[i, noise] += rng.choice([-1.0, 1.0], size=len(noise))
    X[:, 2223:2351] = rng.integers(-1, 2, size=(n, 128)) * (rng.random((n, 128)) < 0.02)
    # data directories (non-negative integers); certificate table iff signed
    X[:, 2351:2381] = np.round(rng.lognormal(6, 2, size=(n, 30)) * (rng.random((n, 30)) < 0.5))
    X[:, 2359] = np.where(sig, np.round(rng.lognormal(8, 1, size=n)), 0)
    X[:, 2360] = np.where(sig, np.round(rng.uniform(1e3, 1e6, size=n)), 0)
    return X


def make_synthetic_bodmas(out_dir, seed: int = 7, scale: float = 1.0) -> dict:
    rng = np.random.default_rng(seed)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    recs = []                                           # (timestamp string, y, family)

    def ts(day: pd.Timestamp, secs: int, offset: bool = True) -> str:
        t = day + pd.Timedelta(seconds=int(secs))
        return t.strftime('%Y-%m-%d %H:%M:%S') + ('+00:00' if offset else '')

    fam_names = KNOWN + UNSEEN
    pop = np.array([1 / (i + 1) ** 0.8 for i in range(len(KNOWN))])
    pop /= pop.sum()
    for day in pd.date_range('2019-08-29', '2020-09-30', freq='D'):
        mo = day.strftime('%Y-%m')
        lam_b = 0.35 * scale if mo in ('2020-01', '2020-02') else 4.0 * scale
        for _ in range(rng.poisson(lam_b)):
            midnight = mo not in ('2020-01', '2020-02')
            recs.append((ts(day, 0 if midnight else rng.integers(1, 86400)), 0, ''))
        for _ in range(rng.poisson(4.0 * scale)):
            if mo >= '2020-07' and rng.random() < 0.25:
                fam = rng.choice(UNSEEN)
            elif mo >= '2020-07' and rng.random() < 0.35:
                fam = 'wabot'
            else:
                fam = rng.choice(KNOWN, p=pop)
            recs.append((ts(day, rng.integers(1, 86400)), 1, fam))
    # placeholder day (benign at 00:00:00), bulk-ingest days (second-level times), a k=4-only spike
    ph = pd.Timestamp('2020-01-01')
    for _ in range(int(200 * scale)):
        recs.append((ts(ph, 0), 0, ''))
    for d in ('2020-02-19', '2020-02-26'):
        for _ in range(int(60 * scale)):
            recs.append((ts(pd.Timestamp(d), rng.integers(1, 86400)), 0, ''))
    for _ in range(int(16 * scale)):
        recs.append((ts(pd.Timestamp('2020-06-08'), rng.integers(1, 86400)), 1, rng.choice(KNOWN, p=pop)))
    # pre-window benign, 25% naive timestamps between 2016-10-30 and 2018-08-02
    for _ in range(int(600 * scale)):
        if rng.random() < 0.25:
            d = pd.Timestamp('2016-10-30') + pd.Timedelta(days=int(rng.integers(0, 640)))
            recs.append((ts(d, rng.integers(0, 86400), offset=False), 0, ''))
        else:
            d = pd.Timestamp('2007-01-01') + pd.Timedelta(days=int(rng.integers(0, 4600)))
            recs.append((ts(d, 0 if rng.random() < 0.5 else rng.integers(1, 86400)), 0, ''))
    df = pd.DataFrame(recs, columns=['timestamp', 'y', 'family'])
    df['fs'] = pd.to_datetime(df['timestamp'], utc=True, format='ISO8601')
    df = df.sort_values('fs', kind='stable').reset_index(drop=True)
    n = len(df)
    df['sha'] = [rng.bytes(32).hex() for _ in range(n)]
    # seven VirusShare_ identifiers on the placeholder day (benign)
    ph_rows = np.flatnonzero((df['timestamp'] == '2020-01-01 00:00:00+00:00').to_numpy() & (df['y'] == 0).to_numpy())
    vs = rng.choice(ph_rows, size=min(7, len(ph_rows)), replace=False)
    df.loc[vs, 'sha'] = ['VirusShare_' + rng.bytes(16).hex() for _ in vs]
    fam_idx = np.array([fam_names.index(f) if f else len(fam_names) for f in df['family']])
    drift = (df['family'] == 'wabot').to_numpy() & (df['fs'] >= pd.Timestamp('2020-07-01', tz='UTC')).to_numpy()
    y = df['y'].to_numpy().astype(np.int32)
    X = _features(y, fam_idx, drift, rng)
    # exact duplicates: four pre-window benign vectors reappear under VirusShare_ ids; three malware pairs
    pre = np.flatnonzero((df['fs'] < pd.Timestamp('2019-08-29', tz='UTC')).to_numpy())
    for a, b in zip(rng.choice(pre, size=min(4, len(vs)), replace=False), vs[:4]):
        X[b] = X[a]
    mal_rows = np.flatnonzero(y == 1)
    for _ in range(3):
        a = rng.choice(mal_rows)
        same = np.flatnonzero((df['timestamp'].str[:10] == df['timestamp'].iat[a][:10]).to_numpy() & (y == 1))
        same = same[same != a]
        if len(same):
            b = same[0]
            X[b] = X[a]
            df.loc[b, 'family'] = df.loc[a, 'family']
    cats = list(CATS)
    p = np.array(list(CATS.values()))
    fam_cat = {f: cats[rng.choice(len(cats), p=p / p.sum())] for f in fam_names}
    np.savez_compressed(out / 'bodmas.npz', X=X, y=y)
    df[['sha', 'timestamp', 'family']].to_csv(out / 'bodmas_metadata.csv', index=False)
    mal = df[df['y'] == 1]
    pd.DataFrame({'sha256': mal['sha'], 'category': [fam_cat[f] for f in mal['family']]}).to_csv(
        out / 'bodmas_malware_category.csv', index=False)
    digests = {f: sha256_file(out / f) for f in ('bodmas.npz', 'bodmas_metadata.csv', 'bodmas_malware_category.csv')}
    (out / 'SOURCE_SHA256.json').write_text(json.dumps(digests, indent=1))
    return dict(rows=n, malware=int(y.sum()), benign=int((y == 0).sum()), digests=digests, dir=str(out))


# ------------------------------------------------------------------ EMBER raw-feature format
def _raw_ember(rng, label: int, month: str) -> dict:
    mal = label == 1
    secs = []
    for name in (['.text', '.rdata', '.data', '.rsrc'] if not mal else ['.text', 'UPX1', '.data']):
        secs.append(dict(name=name, size=int(rng.integers(0, 200000)), entropy=float(rng.uniform(1, 8 if mal else 6.5)),
                         vsize=int(rng.integers(1000, 300000)),
                         props=['CNT_CODE', 'MEM_EXECUTE', 'MEM_READ'] if name in ('.text', 'UPX1') else ['MEM_READ', 'MEM_WRITE']))
    libs = ['KERNEL32.dll', 'USER32.dll', 'ADVAPI32.dll', 'WS2_32.dll', 'SHELL32.dll', 'WININET.dll']
    funcs = ['CreateFileA', 'WriteFile', 'ReadFile', 'VirtualAlloc', 'GetProcAddress', 'LoadLibraryA',
             'RegSetValueExA', 'InternetOpenA', 'send', 'recv', 'ShellExecuteA', 'MessageBoxA']
    imports = {}
    for lib in rng.choice(libs, size=int(rng.integers(1, 5)), replace=False):
        imports[str(lib)] = [str(f) for f in rng.choice(funcs, size=int(rng.integers(1, 6)), replace=False)]
    if mal:
        imports.setdefault('WININET.dll', []).append('InternetOpenA')
    hist = rng.integers(0, 5000, size=256)
    hist[0] += 10000
    signed = int(rng.random() < (0.1 if mal else 0.6))
    return dict(
        sha256=rng.bytes(32).hex(), md5=rng.bytes(16).hex(), appeared=month, label=label, avclass='',
        histogram=hist.tolist(), byteentropy=rng.integers(0, 3000, size=256).tolist(),
        strings=dict(numstrings=int(rng.integers(10, 3000)), avlength=float(rng.uniform(4, 20)),
                     printabledist=rng.integers(0, 500, size=96).tolist(), printables=int(rng.integers(1000, 40000)),
                     entropy=float(rng.uniform(4, 6.5)), paths=int(rng.integers(0, 5)), urls=int(rng.integers(0, 5)),
                     registry=int(rng.integers(0, 5)), MZ=int(rng.integers(0, 3))),
        general=dict(size=int(rng.integers(1e4, 5e6)), vsize=int(rng.integers(1e4, 6e6)), has_debug=int(rng.random() < 0.5),
                     exports=int(rng.integers(0, 10)), imports=int(rng.integers(0, 300)), has_relocations=int(rng.random() < 0.6),
                     has_resources=int(rng.random() < 0.8), has_signature=signed, has_tls=int(rng.random() < 0.2),
                     symbols=int(rng.integers(0, 10))),
        header=dict(coff=dict(timestamp=int(rng.integers(1.2e9, 1.55e9)), machine=str(rng.choice(['I386', 'AMD64'])),
                              characteristics=['CHARA_32BIT_MACHINE', 'EXECUTABLE_IMAGE']),
                    optional=dict(subsystem=str(rng.choice(['WINDOWS_GUI', 'WINDOWS_CUI'])),
                                  dll_characteristics=[str(c) for c in rng.choice(['DYNAMIC_BASE', 'NX_COMPAT', 'TERMINAL_SERVER_AWARE'],
                                                                                  size=int(rng.integers(0, 3)), replace=False)],
                                  magic=str(rng.choice(['PE32', 'PE32_PLUS'])), major_image_version=0, minor_image_version=0,
                                  major_linker_version=int(rng.integers(6, 15)), minor_linker_version=0,
                                  major_operating_system_version=int(rng.integers(4, 7)), minor_operating_system_version=0,
                                  major_subsystem_version=int(rng.integers(4, 7)), minor_subsystem_version=0,
                                  sizeof_code=int(rng.integers(1000, 1e6)), sizeof_headers=1024, sizeof_heap_commit=4096)),
        section=dict(entry='.text' if rng.random() < 0.8 else secs[-1]['name'], sections=secs),
        imports=imports, exports=[] if rng.random() < 0.8 else ['DllMain', 'ServiceMain'],
        datadirectories=[dict(name=nm, size=int(rng.integers(0, 4000)) if (nm != 'CERTIFICATE_TABLE' or signed) else 0,
                              virtual_address=int(rng.integers(0, 1e6)) if (nm != 'CERTIFICATE_TABLE' or signed) else 0)
                         for nm in ['EXPORT_TABLE', 'IMPORT_TABLE', 'RESOURCE_TABLE', 'EXCEPTION_TABLE', 'CERTIFICATE_TABLE',
                                    'BASE_RELOCATION_TABLE', 'DEBUG', 'ARCHITECTURE', 'GLOBAL_PTR', 'TLS_TABLE',
                                    'LOAD_CONFIG_TABLE', 'BOUND_IMPORT', 'IAT', 'DELAY_IMPORT_DESCRIPTOR', 'CLR_RUNTIME_HEADER']])


def make_synthetic_ember(out_dir, per_class_month: int = 40, seed: int = 8) -> dict:
    """EMBER-2018-style raw-feature JSON lines (train Jan-Oct, test Nov-Dec 2018) and a small 'published' model."""
    import lightgbm as lgb
    from .ember import vectorize
    rng = np.random.default_rng(seed)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    months = [f'2018-{m:02d}' for m in range(1, 13)]
    train, test = [], []
    for mo in months:
        for label in (0, 1):
            for _ in range(per_class_month):
                (test if mo >= '2018-11' else train).append(_raw_ember(rng, label, mo))
        for _ in range(per_class_month // 4):
            (test if mo >= '2018-11' else train).append(_raw_ember(rng, -1, mo) | {'label': -1})
    with open(out / 'train_features_0.jsonl', 'w') as f:
        for r in train:
            f.write(json.dumps(r) + '\n')
    with open(out / 'test_features.jsonl', 'w') as f:
        for r in test:
            f.write(json.dumps(r) + '\n')
    lab = [r for r in train if r['label'] >= 0]
    Xtr = vectorize(lab)
    ytr = np.array([r['label'] for r in lab])
    bst = lgb.train(dict(objective='binary', num_leaves=15, learning_rate=0.1, verbose=-1, seed=1, num_threads=1),
                    lgb.Dataset(Xtr, ytr), num_boost_round=30)
    bst.save_model(str(out / 'ember_model_2018.txt'))
    return dict(train=len(train), test=len(test), dir=str(out))
