#!/usr/bin/env python3
"""
s10_common.py -- shared data access, strata, metrics, statistics, certificates and ledger for S10.

Every function here is deterministic given its inputs. Numbers produced by code that imports this
module are measured-on-Claude {MoC} unless the caller labels them otherwise.

Locked inputs (S6 split lock, S7 strata, S8 equations, S9 harness spec; reconciled in S10 Part 0):
  * common window [2019-08-29, 2020-10-01) UTC, UTC-day resolution, intra-day order by SHA-256 (S7 R-T4)
  * spike rule: all-sample daily counts, median + 10*MAD (S6/S7 R-T3)
  * strata: Dated / Placeholder / Bulk / SpikeMal / Quarantine / PreWindow (S7 Table 4.1)
  * primary split: train = Dated < 2019-12-01; calibration = Dated 2019-12; test = Dated >= 2020-01-01
"""
import os, sys, json, time, hashlib, platform, resource, math
import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import beta as _beta

ROOT = '/home/claude/s10'
SRC = '/mnt/user-data/uploads/Datasets/BODMAS'
CACHE = f'{ROOT}/cache'; OUT = f'{ROOT}/out'; FIGS = f'{ROOT}/figs'; TABLES = f'{ROOT}/tables'
MODELS = f'{ROOT}/models'; LEDGER_DIR = f'{ROOT}/ledger'
for _d in (CACHE, OUT, FIGS, TABLES, MODELS, LEDGER_DIR):
    os.makedirs(_d, exist_ok=True)

# ---------------------------------------------------------------- constants (S7 Table 5.1, S8 Eq. 2)
GROUPS = [('ByteHistogram', 0, 256), ('ByteEntropyHistogram', 256, 512), ('StringExtractor', 512, 616),
          ('GeneralFileInfo', 616, 626), ('HeaderFileInfo', 626, 688), ('SectionInfo', 688, 943),
          ('ImportsInfo', 943, 2223), ('ExportsInfo', 2223, 2351), ('DataDirectories', 2351, 2381)]
GSHORT = ['BH', 'BEH', 'STR', 'GEN', 'HDR', 'SEC', 'IMP', 'EXP', 'DD']
D = 2381
COFF_COL = 626                                    # COFF TimeDateStamp (S7 Table 5.1)
MODEL_SEEDS = [11, 23, 37, 41, 53]                # S8 hand-off seeds (supersede S9's {0..4}; S10 Part 0)
STREAM_SEEDS = list(range(100, 120))              # 20 stream seeds (S7 Part 6.8; superset of S9's {100..109})
W0 = pd.Timestamp('2019-08-29', tz='UTC'); W1 = pd.Timestamp('2020-10-01', tz='UTC')
TRAIN_END = pd.Timestamp('2019-12-01', tz='UTC'); TEST_START = pd.Timestamp('2020-01-01', tz='UTC')
ASSURE_START = pd.Timestamp('2020-03-01', tz='UTC')        # S7 Part 6.8 (assurance-plane simulation start)
TEST_MONTHS = ['2020-%02d' % m for m in range(1, 10)]
CERT_MONTHS = ['2020-%02d' % m for m in range(3, 10)]       # FPR-certifiable months (S6/S7)
PIS = [0.001, 0.005, 0.01, 0.02, 0.05, 0.10, 0.50]          # analytic prevalence sweep (S7 ∪ S8 ∪ S9 grids)
PIS_MEASURED = [0.01, 0.02, 0.05, 0.10]                     # resampled-stream prevalences (20 seeds each)
LGB_TRACE = dict(objective='binary', num_leaves=63, learning_rate=0.05, feature_fraction=0.5,
                 bagging_fraction=0.8, bagging_freq=1, min_data_in_leaf=20, verbose=-1,
                 deterministic=True, force_row_wise=True, num_threads=2)       # S7 probe configuration
LGB_TRACE_ROUNDS = 200
LGB_EMBER = dict(boosting='gbdt', objective='binary', learning_rate=0.05, num_leaves=2048, max_depth=15,
                 min_data_in_leaf=50, feature_fraction=0.5, verbose=-1, deterministic=True,
                 force_row_wise=True, num_threads=2, histogram_pool_size=1024)   # elastic/ember init_ember.py;
# histogram_pool_size bounds LightGBM's histogram cache (MB) -- a memory setting that does not change the fitted trees.
# Without it the 2,048-leaf cache exceeded the 8 GB container (OOM-kill of the first T0 run).
LGB_EMBER_ROUNDS = 1000
DOM = b'TRACE-PE/v1/'
T0 = time.perf_counter()


def log(*a):
    print(f'[{time.perf_counter() - T0:8.1f}s]', *a, flush=True)


def peak_rss_gb():
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024, 3)


def env_info():
    import sklearn, scipy, lightgbm
    d = dict(python=sys.version.split()[0], numpy=np.__version__, pandas=pd.__version__, scipy=scipy.__version__,
             sklearn=sklearn.__version__, lightgbm=lightgbm.__version__, platform=platform.platform(),
             nproc=os.cpu_count())
    try:
        import xgboost; d['xgboost'] = xgboost.__version__
    except Exception:
        pass
    try:
        d['cpu_model'] = [l.split(':', 1)[1].strip() for l in open('/proc/cpuinfo') if l.startswith('model name')][0]
    except Exception:
        d['cpu_model'] = 'unavailable'
    return d


def jdump(obj, path):
    with open(path, 'w') as f:
        json.dump(obj, f, indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))


# ---------------------------------------------------------------- data
def load_X(mmap=True):
    """float32 134,435 x 2,381 feature matrix. Converted once from bodmas.npz to an .npy for memory mapping."""
    p = f'{CACHE}/X.npy'
    if not os.path.exists(p):
        X = np.load(f'{SRC}/bodmas.npz')['X']
        assert X.dtype == np.float32 and X.shape == (134435, D)
        np.save(p, X)
        del X
    return np.load(p, mmap_mode='r' if mmap else None)


def _mad_rule(series, k):
    med = float(series.median()); mad = float((series - med).abs().median())
    return med + k * mad


def load_meta():
    """Metadata with S7 strata, splits and stream order. Cached as parquet-free pickle."""
    p = f'{CACHE}/meta.pkl'
    if os.path.exists(p):
        return pd.read_pickle(p)
    y = np.load(f'{SRC}/bodmas.npz')['y'].astype(np.int8)
    meta = pd.read_csv(f'{SRC}/bodmas_metadata.csv', dtype=str, keep_default_na=False)
    cat = pd.read_csv(f'{SRC}/bodmas_malware_category.csv', dtype=str, keep_default_na=False)
    m = pd.DataFrame({'sha': meta['sha'], 'ts_raw': meta['timestamp'], 'family_raw': meta['family']})
    m['y'] = y
    assert ((m['y'] == 1) == (m['family_raw'] != '')).all()                    # row alignment (F2)
    m['family'] = m['family_raw'].str.lower()
    m['category'] = m['sha'].map(dict(zip(cat['sha256'], cat['category']))).fillna('')
    m['has_offset'] = m['ts_raw'].str.len() == 25
    m['ts'] = pd.to_datetime(m['ts_raw'], utc=True, format='ISO8601')
    m['day'] = m['ts'].dt.floor('D')
    m['month'] = m['ts'].dt.strftime('%Y-%m')
    m['quarantine'] = ~m['sha'].str.fullmatch(r'[0-9a-f]{64}')
    m['in_win'] = (m['ts'] >= W0) & (m['ts'] < W1)
    daily = m.loc[m['in_win']].groupby('day').size()
    thr10 = _mad_rule(daily, 10); thr4 = _mad_rule(daily, 4)
    spike10 = set(daily[daily > thr10].index); spike4 = set(daily[daily > thr4].index)
    m['spike10'] = m['in_win'] & m['day'].isin(spike10)
    m['spike4'] = m['in_win'] & m['day'].isin(spike4)
    st = np.full(len(m), 'PreWindow', dtype=object)
    st[m['in_win']] = 'Dated'
    st[m['spike10'] & (m['y'] == 1)] = 'SpikeMal'
    st[m['spike10'] & (m['y'] == 0) & (m['day'] == pd.Timestamp('2020-01-01', tz='UTC'))] = 'Placeholder'
    st[m['spike10'] & (m['y'] == 0) & (m['day'] != pd.Timestamp('2020-01-01', tz='UTC'))] = 'Bulk'
    st[m['quarantine'].to_numpy()] = 'Quarantine'
    m['stratum'] = st
    dated = m['stratum'] == 'Dated'
    sp = np.full(len(m), '', dtype=object)
    sp[dated & (m['ts'] < TRAIN_END)] = 'train'
    sp[dated & (m['month'] == '2019-12')] = 'cal'
    sp[dated & (m['ts'] >= TEST_START)] = 'test'
    m['split'] = sp
    m['idx'] = np.arange(len(m))
    m.attrs['spike10'] = sorted(str(d.date()) for d in spike10)
    m.attrs['spike4'] = sorted(str(d.date()) for d in spike4)
    m.to_pickle(p)
    return m


def stream_order(m, mask):
    """Indices of rows in `mask`, ordered by (UTC day, SHA-256) -- S7 R-T4 (order cannot leak the class)."""
    sub = m.loc[mask, ['day', 'sha', 'idx']].sort_values(['day', 'sha'])
    return sub['idx'].to_numpy()


def signed_log1p(X):
    X = np.asarray(X, dtype=np.float32)
    return np.sign(X) * np.log1p(np.abs(X))


# ---------------------------------------------------------------- Clopper-Pearson, certified threshold (S7.4, S7.5)
def cp_upper(k, n, conf=0.95):
    if n <= 0:
        return float('nan')
    if k >= n:
        return 1.0
    return float(_beta.ppf(conf, k + 1, n - k))


def cp_lower(k, n, conf=0.95):
    if n <= 0:
        return float('nan')
    if k <= 0:
        return 0.0
    return float(_beta.ppf(1 - conf, k, n - k + 1))


def k_star(n_b, tau, conf=0.95):
    k = -1
    while cp_upper(k + 1, n_b, conf) <= tau:
        k += 1
    return k


def certified_threshold(scores_benign_cal, tau, conf=0.95):
    """theta = (k*+1)-th largest benign calibration score; decision 1[s > theta] (S7.5)."""
    s = np.sort(np.asarray(scores_benign_cal, dtype=np.float64))[::-1]
    k = k_star(len(s), tau, conf)
    if k < 0:
        return float(s[0]) + 1e-12, k
    return float(s[k]), k


def empirical_threshold(scores_benign_cal, fpr):
    """BODMAS [1] protocol: largest k with k/n_b <= fpr; theta = (k+1)-th largest benign score."""
    s = np.sort(np.asarray(scores_benign_cal, dtype=np.float64))[::-1]
    k = int(math.floor(fpr * len(s) + 1e-12))
    return float(s[min(k, len(s) - 1)]), k


# ---------------------------------------------------------------- metrics (S8 Eqs. 30, 55, 62-70)
def counts(y, s, thr):
    y = np.asarray(y).astype(bool); p = np.asarray(s) > thr
    tp = int(np.sum(p & y)); fn = int(np.sum(~p & y)); fp = int(np.sum(p & ~y)); tn = int(np.sum(~p & ~y))
    return tp, fn, fp, tn


def rates_from_counts(tp, fn, fp, tn, kappa=1.0):
    """Metrics with benign counts re-weighted by kappa (Eq. 70); kappa = 1 gives the plain Eq. 62/63 values."""
    fpw, tnw = fp * kappa, tn * kappa
    P = tp + fn; N = fp + tn
    tpr = tp / P if P else float('nan'); fpr = fp / N if N else float('nan')
    prec = tp / (tp + fpw) if (tp + fpw) > 0 else float('nan')
    f1 = 2 * prec * tpr / (prec + tpr) if (prec == prec and tpr == tpr and (prec + tpr) > 0) else float('nan')
    den = math.sqrt(max((tp + fpw) * (tp + fn) * (tnw + fpw) * (tnw + fn), 0.0))
    mcc = (tp * tnw - fpw * fn) / den if den > 0 else float('nan')
    bal = 0.5 * (tpr + (1 - fpr)) if (P and N) else float('nan')
    return dict(prec=prec, rec=tpr, f1=f1, fpr=fpr, fnr=1 - tpr if P else float('nan'), mcc=mcc, bal_acc=bal)


def kappa_for(pi, n_pos, n_neg):
    """Eq. 70: kappa = ((1-pi)/pi) * (n+/n-). Benign counts are re-weighted so that the effective prevalence is pi."""
    if pi is None or n_neg == 0 or n_pos == 0:
        return 1.0
    return ((1 - pi) / pi) * (n_pos / n_neg)


def auc_fast(y, s):
    from sklearn.metrics import roc_auc_score
    y = np.asarray(y)
    if y.min() == y.max():
        return float('nan')
    return float(roc_auc_score(y, s))


def ap_score(y, s, pi=None):
    """Step-wise AP (Eq. 66). With pi given, the PR curve is computed with benign weights kappa (Eq. 70)."""
    from sklearn.metrics import average_precision_score
    y = np.asarray(y).astype(int)
    if y.min() == y.max():
        return float('nan')
    if pi is None:
        return float(average_precision_score(y, s))
    k = kappa_for(pi, int(y.sum()), int((1 - y).sum()))
    w = np.where(y == 1, 1.0, k)
    return float(average_precision_score(y, s, sample_weight=w))


def ece_binary(y, q, bins=15):
    """Eq. 30 on the positive-class probability with equal-width bins."""
    y = np.asarray(y, dtype=float); q = np.clip(np.asarray(q, dtype=float), 0, 1)
    idx = np.minimum((q * bins).astype(int), bins - 1)
    e = 0.0
    for b in range(bins):
        sel = idx == b
        if sel.any():
            e += sel.mean() * abs(y[sel].mean() - q[sel].mean())
    return float(e)


def brier(y, q):
    return float(np.mean((np.asarray(q, float) - np.asarray(y, float)) ** 2))


def tpr_at_fpr_test(y, s, fpr_target):
    """Descriptive only (threshold chosen on the test month itself)."""
    y = np.asarray(y).astype(bool); s = np.asarray(s)
    sb = np.sort(s[~y])[::-1]
    k = int(math.floor(fpr_target * len(sb)))
    thr = sb[min(k, len(sb) - 1)]
    return float(np.mean(s[y] > thr))


def aut(values):
    """Eq. 69 (TESSERACT Area Under Time) over N consecutive slots."""
    v = np.asarray(values, dtype=float)
    if len(v) < 2:
        return float(v[0]) if len(v) else float('nan')
    return float(np.sum((v[1:] + v[:-1]) / 2) / (len(v) - 1))


def ppv_bound(fp, n_b, fn, n_m, pi):
    """S7.17: lower bound on PPV at prevalence pi using 97.5% one-sided CP bounds (Bonferroni)."""
    tpr_lb = 1 - cp_upper(fn, n_m, 0.975); fpr_ub = cp_upper(fp, n_b, 0.975)
    return tpr_lb * pi / (tpr_lb * pi + fpr_ub * (1 - pi))


# ---------------------------------------------------------------- bootstrap / CIs
def boot_threshold_metrics(tp, fn, fp, tn, B=1000, seed=0, pi=None):
    """Stratified bootstrap of a fixed-threshold confusion matrix: TP* ~ Bin(n+, TPR), FP* ~ Bin(n-, FPR).
    Exact equivalent of resampling positives and negatives separately. Returns dict of (lo, hi) 95% CIs."""
    rng = np.random.default_rng(seed)
    P = tp + fn; N = fp + tn
    tps = rng.binomial(P, tp / P, B) if P else np.zeros(B, int)
    fps = rng.binomial(N, fp / N, B) if N else np.zeros(B, int)
    k = kappa_for(pi, P, N) if pi is not None else 1.0
    out = {kk: [] for kk in ['prec', 'rec', 'f1', 'fpr', 'fnr', 'mcc', 'bal_acc']}
    for a, b in zip(tps, fps):
        r = rates_from_counts(int(a), int(P - a), int(b), int(N - b), k)
        for kk in out:
            out[kk].append(r[kk])
    return {kk: (float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))) for kk, v in out.items()}


def _midrank(x):
    J = np.argsort(x); Z = x[J]; N = len(x); T = np.zeros(N, dtype=float); i = 0
    while i < N:
        j = i
        while j < N and Z[j] == Z[i]:
            j += 1
        T[i:j] = 0.5 * (i + j - 1) + 1
        i = j
    T2 = np.empty(N, dtype=float); T2[J] = T
    return T2


def delong_cov(y, preds):
    """Fast DeLong (Sun & Xu 2014). preds: (k, n). Returns AUCs (k,) and covariance (k, k)."""
    y = np.asarray(y).astype(bool)
    preds = np.atleast_2d(np.asarray(preds, dtype=float))
    pos = preds[:, y]; neg = preds[:, ~y]; m = pos.shape[1]; n = neg.shape[1]; k = preds.shape[0]
    tx = np.empty((k, m)); ty = np.empty((k, n)); tz = np.empty((k, m + n))
    for r in range(k):
        tx[r] = _midrank(pos[r]); ty[r] = _midrank(neg[r]); tz[r] = _midrank(np.r_[pos[r], neg[r]])
    aucs = tz[:, :m].sum(axis=1) / m / n - (m + 1.0) / 2.0 / n
    v01 = (tz[:, :m] - tx) / n; v10 = 1.0 - (tz[:, m:] - ty) / m
    sx = np.atleast_2d(np.cov(v01)); sy = np.atleast_2d(np.cov(v10))
    return aucs, sx / m + sy / n


def auc_ci(y, s):
    a, c = delong_cov(y, s)
    se = math.sqrt(max(c[0, 0], 0))
    return float(a[0]), (float(max(0, a[0] - 1.96 * se)), float(min(1, a[0] + 1.96 * se)))


def delong_test(y, s1, s2):
    a, c = delong_cov(y, np.vstack([s1, s2]))
    var = c[0, 0] + c[1, 1] - 2 * c[0, 1]
    z = (a[0] - a[1]) / math.sqrt(var) if var > 0 else 0.0
    return float(a[0] - a[1]), float(2 * stats.norm.sf(abs(z)))


def boot_ap_ci(y, s, B=200, seed=0, pi=None):
    rng = np.random.default_rng(seed); y = np.asarray(y).astype(int); s = np.asarray(s)
    ip = np.where(y == 1)[0]; ineg = np.where(y == 0)[0]; vals = []
    for _ in range(B):
        sel = np.r_[rng.choice(ip, len(ip)), rng.choice(ineg, len(ineg))]
        vals.append(ap_score(y[sel], s[sel], pi))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


# ---------------------------------------------------------------- statistics (S9 Part 3.5)
def holm(pvals):
    p = np.asarray(pvals, float); order = np.argsort(p); m = len(p); adj = np.empty(m); run = 0.0
    for r, i in enumerate(order):
        run = max(run, (m - r) * p[i]); adj[i] = min(1.0, run)
    return adj


def friedman_kendall(M):
    """M: (n_blocks, k_treatments). Returns chi2, p, Kendall's W, mean ranks (higher value = better rank 1)."""
    M = np.asarray(M, float); n, k = M.shape
    ranks = np.vstack([stats.rankdata(-row) for row in M])
    chi2, p = stats.friedmanchisquare(*[M[:, j] for j in range(k)])
    W = chi2 / (n * (k - 1))
    return float(chi2), float(p), float(W), ranks.mean(axis=0)


def cliffs_delta(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    if len(a) == 0 or len(b) == 0:
        return float('nan')
    gt = sum(np.sum(x > b) for x in a); lt = sum(np.sum(x < b) for x in a)
    return float((gt - lt) / (len(a) * len(b)))


def a12(a, b):
    return 0.5 * (cliffs_delta(a, b) + 1)


def wilcoxon_p(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float); d = a - b
    if np.allclose(d, 0):
        return 1.0
    try:
        return float(stats.wilcoxon(a, b, zero_method='wilcox', alternative='two-sided', method='exact').pvalue)
    except Exception:
        return float(stats.wilcoxon(a, b).pvalue)


def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return 1.0
    return float(stats.binomtest(min(b, c), n, 0.5).pvalue)


def spearman_perm(x, y, n_perm=10000, seed=0):
    x = np.asarray(x, float); y = np.asarray(y, float)
    rho = stats.spearmanr(x, y).statistic
    rng = np.random.default_rng(seed)
    null = np.array([stats.spearmanr(x, rng.permutation(y)).statistic for _ in range(n_perm)])
    p = (np.sum(np.abs(null) >= abs(rho)) + 1) / (n_perm + 1)
    return float(rho), float(p)


def boot_ci_mean(v, B=2000, seed=0):
    v = np.asarray(v, float); rng = np.random.default_rng(seed)
    bs = [np.mean(rng.choice(v, len(v))) for _ in range(B)]
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


# ---------------------------------------------------------------- hashing, canonical encoding, ledger (S7.1-S7.3)
def H(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(chunk), b''):
            h.update(b)
    return h.hexdigest()


def enc(obj) -> bytes:
    """Canonical JSON: sorted keys, no whitespace, ASCII; floats are not allowed (carry binary32 hex)."""
    def _chk(o):
        if isinstance(o, float):
            raise TypeError('float in record; use f32hex')
        if isinstance(o, dict):
            for v in o.values():
                _chk(v)
        if isinstance(o, (list, tuple)):
            for v in o:
                _chk(v)
    _chk(obj)
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def f32hex(v) -> str:
    return np.float32(v).astype('>f4').tobytes().hex()


def hex2f32(h: str) -> float:
    return float(np.frombuffer(bytes.fromhex(h), dtype='>f4')[0])


VEC_PREFIX = DOM + b'vec\x00' + int(D).to_bytes(4, 'little')


def vec_hash(row) -> str:
    row = np.asarray(row, dtype=np.float32) + np.float32(0)
    return hashlib.sha256(VEC_PREFIX + row.astype('<f4', copy=False).tobytes()).hexdigest()


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


def tree_section_hash(model_str: str) -> str:
    """Model identity = SHA-256 of the LightGBM tree section (S7 Part 6.1; invariant to [num_threads])."""
    a = model_str.find('Tree=0'); b = model_str.find('end of trees')
    assert a >= 0 and b > a
    return hashlib.sha256(model_str[a:b + len('end of trees')].encode()).hexdigest()


class Store:
    """Content-addressed write-once object store objects/<h[0:2]>/<h> (S7 Part 4.4; write-once is policy only)."""
    def __init__(self, root=f'{LEDGER_DIR}/objects'):
        self.root = root; os.makedirs(root, exist_ok=True)

    def put(self, data: bytes) -> str:
        h = hashlib.sha256(data).hexdigest(); d = f'{self.root}/{h[:2]}'; os.makedirs(d, exist_ok=True)
        p = f'{d}/{h}'
        if not os.path.exists(p):
            with open(p, 'xb') as f:
                f.write(data); f.flush(); os.fsync(f.fileno())
            os.chmod(p, 0o444)
        return h

    def get(self, h: str) -> bytes:
        with open(f'{self.root}/{h[:2]}/{h}', 'rb') as f:
            data = f.read()
        if hashlib.sha256(data).hexdigest() != h:
            raise ValueError(f'store read-verify failure {h}')          # F8
        return data


class Ledger:
    """Append-only hash chain (S7.2 as implemented in S7_probes.py) with epoch Merkle roots and Ed25519 anchors.
    Each line: {"q": seq, "e": <canonical record as str>, "rh": hex, "h": hex}."""
    def __init__(self, path, genesis: dict, sk=None):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        self.path = path
        self.sk = sk or Ed25519PrivateKey.from_private_bytes(H(b'S10-simulated-anchor-key')[:32])
        self.pk = self.sk.public_key()
        self.f = open(path, 'w')
        g = enc(genesis); self.genesis = g
        self.head = link(H(DOM + b'genesis\x00'), rec_hash(g))
        self.q = 0; self.epoch_hashes = {}; self.cur_epoch = 'setup'
        self._write(g, rec_hash(g))

    def _write(self, e, rh):
        self.f.write(json.dumps({'q': self.q, 'e': e.decode('ascii'), 'rh': rh.hex(), 'h': self.head.hex()}) + '\n')

    def append(self, rec: dict, epoch=None):
        if epoch is not None:
            self.cur_epoch = epoch
        rec = dict(rec); rec.setdefault('ep', self.cur_epoch)          # epoch membership is part of the record
        e = enc(rec); rh = rec_hash(e); self.head = link(self.head, rh); self.q += 1
        self._write(e, rh)
        self.epoch_hashes.setdefault(rec['ep'], []).append(rh)
        return self.q, rh.hex(), self.head.hex()

    def anchor(self, epoch):
        """ANC record: epoch Merkle root, chain head, Ed25519 signature; RFC 3161 TSA is simulated (local key)."""
        root = merkle_root(self.epoch_hashes.get(epoch, []))
        msg = epoch.encode() + root + self.head
        sig = self.sk.sign(msg).hex()
        tst = hashlib.sha256(b'TSA-simulated' + H(self.head)).hexdigest()
        return self.append(dict(t='ANC', epoch=epoch, root=root.hex(), head=self.head.hex(), sig=sig,
                                tsa='simulated-local', tst=tst, n=len(self.epoch_hashes.get(epoch, []))))

    def close(self):
        self.f.flush(); os.fsync(self.f.fileno()); self.f.close(); os.chmod(self.path, 0o444)


def verify_ledger(path, pk=None):
    """V1: recompute every record hash and chain link, every epoch root and anchor signature.
    Returns (ok, first_bad_seq, n_records, seconds)."""
    t = time.perf_counter()
    with open(path) as f:
        lines = [json.loads(l) for l in f]
    g = lines[0]['e'].encode('ascii')
    head = link(H(DOM + b'genesis\x00'), rec_hash(g))
    if lines[0]['h'] != head.hex():
        return False, 0, len(lines), time.perf_counter() - t
    ep_hashes = {}
    for L in lines[1:]:
        e = L['e'].encode('ascii'); rh = rec_hash(e); head = link(head, rh)
        if rh.hex() != L['rh'] or head.hex() != L['h']:
            return False, L['q'], len(lines), time.perf_counter() - t
        r = json.loads(L['e'])
        if r.get('t') == 'ANC':
            root = merkle_root(ep_hashes.get(r['epoch'], []))
            if root.hex() != r['root']:
                return False, L['q'], len(lines), time.perf_counter() - t
            if pk is not None:
                try:
                    pk.verify(bytes.fromhex(r['sig']), r['epoch'].encode() + root + bytes.fromhex(r['head']))
                except Exception:
                    return False, L['q'], len(lines), time.perf_counter() - t
        ep_hashes.setdefault(r.get('ep', 'setup'), []).append(rh)
    return True, -1, len(lines), time.perf_counter() - t


# ---------------------------------------------------------------- main S10 ledger (multi-process append with a file lock)
MAIN_LEDGER = f'{LEDGER_DIR}/s10_ledger.jsonl'
ANCHOR_SK_SEED = b'S10-simulated-anchor-key'


def _sk():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    return Ed25519PrivateKey.from_private_bytes(H(ANCHOR_SK_SEED)[:32])


def anchor_pk():
    return _sk().public_key()


def ledger_init(genesis: dict, path=MAIN_LEDGER):
    if os.path.exists(path):
        raise FileExistsError(path)
    g = enc(genesis); head = link(H(DOM + b'genesis\x00'), rec_hash(g))
    with open(path, 'w') as f:
        f.write(json.dumps({'q': 0, 'e': g.decode('ascii'), 'rh': rec_hash(g).hex(), 'h': head.hex()}) + '\n')
    return head.hex()


def _last_line(path):
    with open(path, 'rb') as f:
        f.seek(0, 2); size = f.tell(); step = min(size, 1 << 16)
        while True:
            f.seek(size - step); buf = f.read(step)
            lines = buf.rstrip(b'\n').split(b'\n')
            if len(lines) > 1 or step == size:
                return json.loads(lines[-1])
            step = min(size, step * 2)


def ledger_append(recs, epoch='setup', path=MAIN_LEDGER):
    """Append records (list of dict) under an exclusive lock; returns [(q, rh, head)]."""
    import fcntl
    out = []
    with open(path, 'a') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        last = _last_line(path); head = bytes.fromhex(last['h']); q = last['q']
        lines = []
        for r in recs:
            r = dict(r); r.setdefault('ep', epoch)
            e = enc(r); rh = rec_hash(e); head = link(head, rh); q += 1
            lines.append(json.dumps({'q': q, 'e': e.decode('ascii'), 'rh': rh.hex(), 'h': head.hex()}))
            out.append((q, rh.hex(), head.hex()))
        f.write('\n'.join(lines) + '\n'); f.flush(); os.fsync(f.fileno())
        fcntl.flock(f, fcntl.LOCK_UN)
    return out


def ledger_anchor(epoch, path=MAIN_LEDGER):
    """ANC record over all non-ANC records of `epoch` so far: Merkle root, chain head, Ed25519 signature.
    RFC 3161 time-stamping is simulated (local key) and labelled so."""
    leaves = []
    with open(path) as f:
        for L in f:
            d = json.loads(L)
            if d['q'] == 0:
                continue
            r = json.loads(d['e'])
            if r.get('ep') == epoch and r.get('t') != 'ANC':
                leaves.append(bytes.fromhex(d['rh']))
            last = d
    root = merkle_root(leaves); head = bytes.fromhex(last['h'])
    sig = _sk().sign(epoch.encode() + root + head).hex()
    return ledger_append([dict(t='ANC', epoch=epoch, root=root.hex(), head=head.hex(), sig=sig, n=len(leaves),
                               tsa='simulated-local', tst=hashlib.sha256(b'TSA-simulated' + head).hexdigest(),
                               ep='anchors')], path=path)


def verify_main_ledger(path=MAIN_LEDGER, check_sig=True):
    """V1 for the main ledger: every record hash, every link, every epoch root and anchor signature."""
    t = time.perf_counter(); pk = anchor_pk() if check_sig else None
    with open(path) as f:
        lines = [json.loads(l) for l in f]
    g = lines[0]['e'].encode('ascii'); head = link(H(DOM + b'genesis\x00'), rec_hash(g))
    if lines[0]['h'] != head.hex():
        return dict(ok=False, first_bad=0, n=len(lines), seconds=time.perf_counter() - t)
    ep = {}
    for L in lines[1:]:
        e = L['e'].encode('ascii'); rh = rec_hash(e)
        if rh.hex() != L['rh']:
            return dict(ok=False, first_bad=L['q'], n=len(lines), seconds=time.perf_counter() - t)
        r = json.loads(L['e'])
        if r.get('t') == 'ANC':
            root = merkle_root(ep.get(r['epoch'], []))
            if root.hex() != r['root'] or bytes.fromhex(r['head']) != head:
                return dict(ok=False, first_bad=L['q'], n=len(lines), seconds=time.perf_counter() - t)
            if pk is not None:
                try:
                    pk.verify(bytes.fromhex(r['sig']), r['epoch'].encode() + root + head)
                except Exception:
                    return dict(ok=False, first_bad=L['q'], n=len(lines), seconds=time.perf_counter() - t)
        else:
            ep.setdefault(r.get('ep', 'setup'), []).append(rh)
        head = link(head, rh)
        if head.hex() != L['h']:
            return dict(ok=False, first_bad=L['q'], n=len(lines), seconds=time.perf_counter() - t)
    return dict(ok=True, first_bad=-1, n=len(lines), seconds=round(time.perf_counter() - t, 4))
