"""Verbatim transcription of the ledger construction of the S7 design-validation probes (S7_probes.py, section
P6) on the real BODMAS release. The tests compare the package against it: if both agree on any release-format
input, the paper's acquisition-chain head and oracle Merkle root are reproduced on the real files."""
import hashlib
import json

import numpy as np
import pandas as pd

DOM = b'TRACE-PE/v1/'


def H(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def enc(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def rec_hash(e: bytes) -> bytes:
    return H(DOM + b'rec\x00' + e)


def link(prev: bytes, rh: bytes) -> bytes:
    return H(DOM + b'chain\x00' + prev + rh)


def merkle_root(leaves):
    level = [H(b'\x00' + x) for x in leaves]
    if not level:
        return H(b'')
    while len(level) > 1:
        nxt = [H(b'\x01' + level[i] + level[i + 1]) for i in range(0, len(level) - 1, 2)]
        if len(level) % 2:
            nxt.append(level[-1])
        level = nxt
    return level[0]


def acquisition_checkpoints(src_dir, file_digests: dict, extractor_claim: str):
    """Acquisition-chain head (MAN0 + one ACQ record per row) and oracle root, exactly as in S7 P3/P4/P6."""
    import os
    npz = np.load(os.path.join(src_dir, 'bodmas.npz'))
    X = npz['X']
    y = npz['y'].astype(np.int64)
    n, d = X.shape
    meta = pd.read_csv(os.path.join(src_dir, 'bodmas_metadata.csv'), dtype=str, keep_default_na=False)
    catf = pd.read_csv(os.path.join(src_dir, 'bodmas_malware_category.csv'), dtype=str, keep_default_na=False)
    cat = meta['sha'].map(dict(zip(catf['sha256'], catf['category']))).fillna('').to_numpy()
    fam_raw = meta['family'].to_numpy()
    VEC_PREFIX = DOM + b'vec\x00' + int(d).to_bytes(4, 'little')
    zero32 = np.float32(0)
    vh = [hashlib.sha256(VEC_PREFIX + (X[i] + zero32).astype('<f4', copy=False).tobytes()).hexdigest() for i in range(n)]
    ts_raw = meta['timestamp']
    has_offset = (ts_raw.str.len() == 25).to_numpy()
    fs = pd.to_datetime(ts_raw, utc=True, format='ISO8601')
    W0 = pd.Timestamp('2019-08-29', tz='UTC')
    W1 = pd.Timestamp('2020-10-01', tz='UTC')
    in_win = ((fs >= W0) & (fs < W1)).to_numpy()
    day = fs.dt.floor('D')
    daily_all = pd.Series(1, index=day[in_win]).groupby(level=0).sum()
    med = float(daily_all.median())
    mad = float((daily_all - med).abs().median())
    thr = med + 10 * mad
    spike_days = set(daily_all[daily_all > thr].index)
    censored = in_win & day.isin(spike_days).to_numpy()
    manifest = dict(t='MAN0', files=dict(file_digests), feature_version=2, dims=d, extractor_claim=extractor_claim)
    h_prev = link(H(DOM + b'genesis\x00'), rec_hash(enc(manifest)))
    DSID = file_digests['bodmas.npz'][:16]
    for i in range(n):
        r = dict(t='ACQ', q=i + 1, sid=meta['sha'].iat[i], vh=vh[i], fs=ts_raw.iat[i], off=bool(has_offset[i]),
                 win=bool(in_win[i]), cen=bool(censored[i]), ds=DSID)
        h_prev = link(h_prev, rec_hash(enc(r)))
    orc = merkle_root([enc(dict(sid=meta['sha'].iat[i], y=int(y[i]), fam=fam_raw[i], cat=cat[i])) for i in range(n)])
    return h_prev.hex(), orc.hex()


def cp_upper(k, n, conf=0.95):
    from scipy.stats import beta
    if n <= 0:
        return float('nan')
    if k >= n:
        return 1.0
    return float(beta.ppf(conf, k + 1, n - k))


def screen_checkpoints(src_dir, taus=(0.001, 0.005, 0.01)):
    """S7 probe sections P3 (duplicates), P4 (timestamps, spike rule, split, monthly CP bounds, k*) and P5
    (COFF audit), transcribed verbatim apart from the input paths."""
    import os
    npz = np.load(os.path.join(src_dir, 'bodmas.npz'))
    X = npz['X']
    y = npz['y'].astype(np.int64)
    n, d = X.shape
    meta = pd.read_csv(os.path.join(src_dir, 'bodmas_metadata.csv'), dtype=str, keep_default_na=False)
    fam_raw = meta['family'].to_numpy()
    VEC_PREFIX = DOM + b'vec\x00' + int(d).to_bytes(4, 'little')
    zero32 = np.float32(0)
    vh = np.array([hashlib.sha256(VEC_PREFIX + (X[i] + zero32).astype('<f4', copy=False).tobytes()).hexdigest() for i in range(n)])
    R = {}
    ts_raw = meta['timestamp']
    has_offset = (ts_raw.str.len() == 25).to_numpy()
    fs = pd.to_datetime(ts_raw, utc=True, format='ISO8601')
    R['timestamp_formats'] = dict(with_utc_offset=int(has_offset.sum()), without_offset=int((~has_offset).sum()))
    W0 = pd.Timestamp('2019-08-29', tz='UTC')
    W1 = pd.Timestamp('2020-10-01', tz='UTC')
    in_win = ((fs >= W0) & (fs < W1)).to_numpy()
    day = fs.dt.floor('D')
    daily_all = pd.Series(1, index=day[in_win]).groupby(level=0).sum()
    daily_ben = pd.Series(1, index=day[in_win & (y == 0)]).groupby(level=0).sum()

    def mad_rule(series, k):
        med = float(series.median())
        mad = float((series - med).abs().median())
        return med, mad, med + k * mad
    spike = {}
    for nm, ser in [('all', daily_all), ('benign', daily_ben)]:
        med, mad, thr10 = mad_rule(ser, 10)
        _, _, thr4 = mad_rule(ser, 4)
        spike[nm] = dict(days=int(len(ser)), median=med, mad=mad, threshold_k10=thr10, threshold_k4=thr4,
                         spike_days_k10={str(k.date()): int(v) for k, v in ser[ser > thr10].items()},
                         spike_days_k4={str(k.date()): int(v) for k, v in ser[ser > thr4].items()})
    R['spike'] = spike
    spike_days = set(pd.Timestamp(k, tz='UTC') for k in spike['all']['spike_days_k10'])
    censored = in_win & day.isin(spike_days).to_numpy()
    dated = in_win & ~censored
    month = fs.dt.strftime('%Y-%m').to_numpy()
    split = np.full(n, 'pre_window', dtype=object)
    split[censored] = 'censored'
    split[dated & (fs < pd.Timestamp('2019-12-01', tz='UTC')).to_numpy()] = 'train'
    split[dated & (month == '2019-12')] = 'calibration'
    split[dated & (fs >= pd.Timestamp('2020-01-01', tz='UTC')).to_numpy()] = 'test'
    R['split_counts'] = {s: {'benign': int(((split == s) & (y == 0)).sum()), 'malware': int(((split == s) & (y == 1)).sum())}
                         for s in ['pre_window', 'train', 'calibration', 'test', 'censored']}
    mon = pd.DataFrame({'month': month, 'y': y, 'dated': dated, 'censored': censored})
    monthly = {}
    for mo in sorted(set(month[in_win])):
        sel = mon['month'] == mo
        b = int((sel & mon['dated'] & (mon['y'] == 0)).sum())
        mw = int((sel & mon['dated'] & (mon['y'] == 1)).sum())
        cb = int((sel & mon['censored'] & (mon['y'] == 0)).sum())
        cm = int((sel & mon['censored'] & (mon['y'] == 1)).sum())
        monthly[mo] = dict(dated_benign=b, dated_malware=mw, censored_benign=cb, censored_malware=cm,
                           fpr_ub0=round(cp_upper(0, b) * 100, 4), fpr_ub1=round(cp_upper(1, b) * 100, 4),
                           fnr_ub0=round(cp_upper(0, mw) * 100, 4))
    R['monthly'] = monthly
    nb_dec = monthly['2019-12']['dated_benign']
    cert = {}
    for tau in taus:
        k = -1
        while cp_upper(k + 1, nb_dec) <= tau:
            k += 1
        cert[str(tau)] = dict(k_star=k, ub_at_k_star=round(cp_upper(max(k, 0), nb_dec) * 100, 4) if k >= 0 else None)
    R['certified'] = cert
    df = pd.DataFrame({'vh': vh, 'y': y, 'fam': fam_raw, 'split': split, 'month': month})
    sizes = df.groupby('vh').size()
    dup_keys = sizes[sizes > 1].index
    dd = df[df['vh'].isin(dup_keys)]
    g2 = dd.groupby('vh')
    train_v = set(df.loc[df['split'] == 'train', 'vh'])
    cal_v = set(df.loc[df['split'] == 'calibration', 'vh'])
    R['duplicates'] = dict(
        unique_vectors=int(sizes.shape[0]), duplicate_groups=int(len(dup_keys)),
        groups_label_conflict=int((g2['y'].nunique() > 1).sum()),
        groups_spanning_splits=int((g2['split'].nunique() > 1).sum()),
        test_rows_vector_in_train=int(((df['split'] == 'test') & df['vh'].isin(train_v)).sum()),
        test_rows_vector_in_train_or_cal=int(((df['split'] == 'test') & df['vh'].isin(train_v | cal_v)).sum()),
        calibration_rows_vector_in_train=int(((df['split'] == 'calibration') & df['vh'].isin(train_v)).sum()))
    coff = X[:, 626].astype(np.float64)
    fs_epoch = (fs - pd.Timestamp('1970-01-01', tz='UTC')).dt.total_seconds().to_numpy()
    aud = {}
    for cls, nm in [(0, 'benign'), (1, 'malware')]:
        selc = in_win & (y == cls)
        c_, f_ = coff[selc], fs_epoch[selc]
        frac = lambda mask: round(float(np.mean(mask)), 6)
        aud[nm] = dict(n=int(selc.sum()), coff_zero=frac(c_ == 0), coff_after_first_seen_plus1d=frac((c_ > f_ + 86400) & (c_ > 0)),
                       coff_before_1992=frac((c_ > 0) & (c_ < 694224000)))
    R['coff_audit'] = aud
    return R
