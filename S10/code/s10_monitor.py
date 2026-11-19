#!/usr/bin/env python3
"""M8 label-free monitor (S7 Part 6.4, Algorithm 4) with the blocked null and the D1 reference rule; trigger kill KT;
adapted ACI baseline; label-based lapse bound. Model f0 = LGBM-TRACE seed 11, threshold theta0 = CP-certified 0.1%.
Output: out/monitor.json, out/monitor_windows.pkl"""
import json, time, os
import numpy as np, pandas as pd, lightgbm as lgb
from scipy.stats import ks_2samp
import s10_common as C

t00 = time.perf_counter()
m = C.load_meta(); X = C.load_X(); y = m['y'].to_numpy().astype(int)
day = m['day'].to_numpy(); fam = m['family'].to_numpy()
DAYN = ((m['day'].dt.tz_convert(None) - pd.Timestamp('1970-01-01')).dt.days).to_numpy()
dn = lambda d: int((pd.Timestamp(str(pd.Timestamp(d).date())) - pd.Timestamp('1970-01-01')).days)
d0 = np.load(f'{C.CACHE}/scores/lgbm_trace_s11.npz'); meta0 = json.load(open(f'{C.CACHE}/scores/lgbm_trace_s11.json'))
b0 = lgb.Booster(model_str=C.Store().get(meta0['model_obj']).decode())
score = np.full(len(m), np.nan); score[d0['idx']] = d0['s']
dated = (m['stratum'] == 'Dated').to_numpy()
ts = m['ts']
ref_mf = np.where(dated & (ts >= pd.Timestamp('2019-10-01', tz='UTC')).to_numpy() & (ts < pd.Timestamp('2020-01-01', tz='UTC')).to_numpy())[0]
oct_nov = ref_mf[np.isnan(score[ref_mf])]
score[oct_nov] = b0.predict(np.asarray(X[oct_nov]), raw_score=True)          # in-sample for f0 (flagged)
cal = np.where(m['split'] == 'cal')[0]
theta0, kst = C.certified_threshold(score[cal][y[cal] == 0], 0.001)
yhat = (score > theta0).astype(int)
insample_acc = float(np.mean(yhat[oct_nov] == y[oct_nov]))
ref_md = cal                                                                 # December only (D1)
# ICE credibility (S7.6): alpha = 1 - p(yhat|x), p = sigmoid(margin); calibration sets by TRUE label (Dec)
p1 = 1 / (1 + np.exp(-score))
alpha_cal = {c: np.sort(np.where(c == 1, 1 - p1[cal], p1[cal])[y[cal] == c]) for c in (0, 1)}


def cred(idx):
    out = np.empty(len(idx))
    for c in (0, 1):
        sel = yhat[idx] == c
        a = np.where(c == 1, 1 - p1[idx[sel]], p1[idx[sel]])
        ac = alpha_cal[c]
        out[sel] = (1 + (len(ac) - np.searchsorted(ac, a, side='left'))) / (1 + len(ac))
    return out


cr = np.full(len(m), np.nan)
mon_idx = np.where(dated & (ts >= pd.Timestamp('2019-12-01', tz='UTC')).to_numpy())[0]
cr[mon_idx] = cred(mon_idx)
# kappa (pre-registered): largest value with December abstention <= 5%
cdec = np.sort(cr[cal]); kappa = float(cdec[int(np.floor(0.05 * len(cdec)))])
abst_dec = float(np.mean(cr[cal] < kappa))

feat = np.r_[0:C.COFF_COL, C.COFF_COL + 1:C.D]                              # column 626 excluded from monitoring


def windows(start, end, step):
    out = []; d = pd.Timestamp(start, tz='UTC')
    while d < pd.Timestamp(end, tz='UTC'):
        out.append((d, min(d + pd.Timedelta(days=7), pd.Timestamp(end, tz='UTC')))); d += pd.Timedelta(days=step)
    return out


null_mf = [w for w in windows('2019-10-01', '2020-01-01', 1) if (w[1] - w[0]).days == 7]
null_md = [w for w in windows('2019-12-01', '2020-01-01', 1) if (w[1] - w[0]).days == 7]
test_w = windows('2020-03-01', '2020-10-01', 7)
ts_np = ts.to_numpy()
unseen_all = ~np.isin(fam, list(set(fam[(m['split'] == 'train').to_numpy() & (y == 1)])))
ts_naive = ts.dt.tz_convert(None).to_numpy()


def rows_in(w, pool):
    a = np.datetime64(w[0].tz_convert(None)); b = np.datetime64(w[1].tz_convert(None))
    t = ts_naive[pool]
    return pool[(t >= a) & (t < b)]


# ---- PSI machinery: reference quantile edges per class from the full model-free reference (Oct-Dec)
qs = np.linspace(0, 1, 11)[1:-1]
Xref = {c: np.asarray(X[ref_mf[yhat[ref_mf] == c]])[:, feat] for c in (0, 1)}
edges = {c: [np.unique(np.quantile(Xref[c][:, j], qs)) for j in range(len(feat))] for c in (0, 1)}


def bin_counts(Xs, c):
    out = np.zeros((len(feat), 10), dtype=np.int64)
    for j, e in enumerate(edges[c]):
        out[j, :len(e) + 1] = np.bincount(np.searchsorted(e, Xs[:, j], side='right'), minlength=len(e) + 1)
    return out


ref_counts = {c: bin_counts(Xref[c], c) for c in (0, 1)}


def psi_from_counts(cw, cr_):
    pw = cw / max(cw.sum(1, keepdims=True).max(), 1); prf = cr_ / max(cr_.sum(1, keepdims=True).max(), 1)
    pw = np.clip(pw, 1e-4, None); prf = np.clip(prf, 1e-4, None)
    v = ((pw - prf) * np.log(pw / prf)).sum(1)
    return v


def c2st(Xw, Xr, seed):
    rng = np.random.default_rng(seed)
    if len(Xw) > 1500:
        Xw = Xw[rng.choice(len(Xw), 1500, replace=False)]
    if len(Xr) > 3000:
        Xr = Xr[rng.choice(len(Xr), 3000, replace=False)]
    Z = np.vstack([Xw, Xr]); dz = np.r_[np.ones(len(Xw)), np.zeros(len(Xr))]
    from sklearn.model_selection import StratifiedKFold
    oof = np.zeros(len(dz))
    for a, b in StratifiedKFold(2, shuffle=True, random_state=seed).split(Z, dz):
        clf = lgb.train(dict(objective='binary', num_leaves=31, learning_rate=0.1, feature_fraction=0.5, seed=7,
                             deterministic=True, force_row_wise=True, num_threads=2, verbose=-1),
                        lgb.Dataset(Z[a], label=dz[a], params={'max_bin': 63, 'verbose': -1}), num_boost_round=100)
        oof[b] = clf.predict(Z[b])
    return C.auc_fast(dz, oof)


def stats_for(widx, ref_md_idx, ref_mf_idx, c, null_mode, seed):
    wc = widx[yhat[widx] == c]
    out = dict(n=len(wc), ks=np.nan, psi=np.nan, cred=np.nan, c2st=np.nan)
    if len(wc) < 20:
        return out
    if null_mode in ('md', 'test'):                       # model-dependent statistics (December reference, D1)
        rmd = ref_md_idx[yhat[ref_md_idx] == c]
        out['ks'] = float(ks_2samp(score[wc], score[rmd]).statistic)
        out['cred'] = float(1 - np.mean(cr[wc]))
    if null_mode in ('mf', 'test'):                       # model-free statistics (Oct-Dec reference)
        Xw = np.asarray(X[wc])[:, feat]
        cw = bin_counts(Xw, c)
        crf = ref_counts[c] - (cw if null_mode == 'mf' else 0)
        out['psi'] = float(np.mean(psi_from_counts(cw, crf)))
        rmf = ref_mf_idx[yhat[ref_mf_idx] == c]
        out['c2st'] = float(c2st(Xw, np.asarray(X[rmf])[:, feat], seed))
    return out


rows = []
RESUME = os.path.exists(f'{C.OUT}/monitor_windows.pkl')
for kind, wins in ([] if RESUME else [('null_mf', null_mf), ('null_md', null_md), ('test', test_w)]):
    for wi, w in enumerate(wins):
        if kind == 'null_mf':
            widx = rows_in(w, ref_mf); rmd = ref_md; rmf = np.setdiff1d(ref_mf, widx)
        elif kind == 'null_md':
            widx = rows_in(w, ref_md); rmd = np.setdiff1d(ref_md, widx); rmf = ref_mf
        else:
            widx = rows_in(w, mon_idx); rmd = ref_md; rmf = ref_mf
        for c in (0, 1):
            st = stats_for(widx, rmd, rmf, c, 'mf' if kind == 'null_mf' else ('md' if kind == 'null_md' else 'test'), 1000 + wi)
            mal = widx[y[widx] == 1]
            rows.append(dict(kind=kind, w=wi, start=str(w[0].date()), end=str(w[1].date()), cls=c, **st,
                             unseen_share=float(np.mean(unseen_all[mal])) if len(mal) else np.nan,
                             n_win=len(widx)))
        print(kind, wi, str(w[0].date()), {k: round(v, 3) if isinstance(v, float) else v for k, v in rows[-1].items() if k in ('n', 'ks', 'psi', 'cred', 'c2st')}, flush=True)
W = pd.read_pickle(f'{C.OUT}/monitor_windows.pkl') if RESUME else pd.DataFrame(rows)
W.to_pickle(f'{C.OUT}/monitor_windows.pkl')
# ---- Page-Hinkley on daily mean credibility (T4): decrease detection, delta = 0.005, reference mean from December
def ph_series(x, mu0, delta=0.005):
    U = np.cumsum(mu0 - x - delta); return U - np.minimum.accumulate(np.minimum(U, 0))


ph = {}
for c in (0, 1):
    dec_days = pd.date_range('2019-12-01', '2019-12-31', tz='UTC')
    def daily(days, pool):
        v = []
        for d in days:
            sel = pool[(DAYN[pool] == dn(d)) & (yhat[pool] == c)]
            v.append(np.mean(cr[sel]) if len(sel) else np.nan)
        return np.array(v)
    xd = daily(dec_days, ref_md); mu0 = np.nanmean(xd)
    lam_ph = np.nanmax(ph_series(np.nan_to_num(xd, nan=mu0), mu0))
    test_days = pd.date_range('2020-03-01', '2020-09-30', tz='UTC')
    xt = daily(test_days, mon_idx); pht = ph_series(np.nan_to_num(xt, nan=mu0), mu0)
    ph[c] = dict(lam=float(lam_ph), mu0=float(mu0), series=pht.tolist(), days=[str(d.date()) for d in test_days])
# ---- thresholds (max over the blocked null) and alarms
lam = {}
for c in (0, 1):
    for k in ('ks', 'cred'):
        lam[(k, c)] = float(W[(W.kind == 'null_md') & (W.cls == c)][k].max())
    for k in ('psi', 'c2st'):
        lam[(k, c)] = float(W[(W.kind == 'null_mf') & (W.cls == c)][k].max())
T = W[W.kind == 'test'].copy()
exc = []
for wi, g in T.groupby('w'):
    e = {}
    for _, r in g.iterrows():
        for k in ('ks', 'psi', 'cred', 'c2st'):
            e[f'{k}{r.cls}'] = bool(r[k] > lam[(k, r.cls)]) if r[k] == r[k] else False
        # PH: exceed if PH series exceeds lambda on any day inside the window
        s0 = pd.Timestamp(g['start'].iloc[0], tz='UTC'); idx0 = (s0 - pd.Timestamp('2020-03-01', tz='UTC')).days
        seg = ph[r.cls]['series'][idx0:idx0 + 7]
        e[f'ph{r.cls}'] = bool(max(seg) > ph[r.cls]['lam']) if len(seg) else False
    exc.append(dict(w=wi, start=g['start'].iloc[0], end=g['end'].iloc[0], any=any(e.values()), **e,
                    unseen_share=float(g['unseen_share'].iloc[0])))
E = pd.DataFrame(exc)
alarms = []; prev = False; armed = True
for _, r in E.iterrows():
    if r['any'] and prev and armed:
        alarms.append(r['end']); armed = False; prev = False; continue
    if not r['any']:
        armed = True
    prev = r['any']
E['alarm'] = E['end'].isin(alarms)
onset = E[(E.unseen_share > 0.05)]
onset_july = onset[onset.start >= '2020-07-01']
onset_d = onset_july['start'].iloc[0] if len(onset_july) else None
first_after = [a for a in alarms if onset_d and a >= onset_d]
delay = (pd.Timestamp(first_after[0]) - pd.Timestamp(onset_d)).days if first_after else None
fa = {mm: sum(1 for a in alarms if a[:7] == mm) for mm in ['2020-03', '2020-04', '2020-05', '2020-06']}
KT_pass = (delay is not None and delay <= 14) and all(v <= 1 for v in fa.values())
# ---- adapted ACI baseline (Gibbs & Candes) on ICE prediction sets, labels delayed by L
def aci(L, alpha=0.05, eta=0.005):
    pool = mon_idx[DAYN[mon_idx] >= dn('2020-03-01')]
    order = C.stream_order(m, np.isin(np.arange(len(m)), pool))
    # p-values for each candidate label
    pv = {}
    for c in (0, 1):
        a = np.where(c == 1, 1 - p1[order], p1[order]); ac = alpha_cal[c]
        pv[c] = (1 + (len(ac) - np.searchsorted(ac, a, side='left'))) / (1 + len(ac))
    a_t = alpha; dts = DAYN[order]; pending = []; al = []; first = None; series = []
    for i, ix in enumerate(order):
        # labels of findings issued >= L days ago arrive now
        while pending and (dts[i] - pending[0][0]) >= L:
            _, err = pending.pop(0); a_t = a_t + eta * (alpha - err)
        inset = pv[y[ix]][i] > a_t
        pending.append((dts[i], 0 if inset else 1))
        if a_t <= 0:
            al.append(str((pd.Timestamp('1970-01-01') + pd.Timedelta(days=int(dts[i]))).date())); a_t = alpha   # alarm, then reset
        series.append(a_t)
    months = {}
    for a in al:
        months[a[:7]] = months.get(a[:7], 0) + 1
    return dict(L=L, alarms=len(al), first=al[0] if al else None, per_month=months,
                first_after_onset=next((a for a in al if onset_d and a >= onset_d), None))
aci_res = {L: aci(L) for L in (7, 30)}
res = dict(theta0=theta0, kstar=kst, kappa=kappa, abstention_dec=abst_dec, insample_acc_octnov=insample_acc,
           n_null_mf=len(null_mf), n_null_md=len(null_md), n_test_windows=len(test_w),
           lam={f'{k}{c}': v for (k, c), v in lam.items()}, ph_lam={c: ph[c]['lam'] for c in (0, 1)},
           alarms=alarms, onset_july_week=onset_d, delay_days=delay, false_alarms_stable=fa, KT_pass=bool(KT_pass),
           exceed_any_share=float(E['any'].mean()), aci=aci_res,
           label_based_lower_bound_days={L: L for L in (7, 30, 60)}, seconds=round(time.perf_counter() - t00, 1))
W.to_pickle(f'{C.OUT}/monitor_windows.pkl'); E.to_pickle(f'{C.OUT}/monitor_exceed.pkl')
C.jdump(dict(res, ph={c: ph[c] for c in (0, 1)}), f'{C.OUT}/monitor.json')
np.save(f'{C.CACHE}/cred_f0.npy', cr)
print(json.dumps(res, indent=1, default=str))
