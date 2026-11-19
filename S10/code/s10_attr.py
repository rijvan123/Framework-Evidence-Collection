#!/usr/bin/env python3
"""Attribution leg (S6 Block 10, S7 Part 6.3; S8 P6, Eqs. 67, 71-73; S9 H7): open-set family attribution with
generic-token exclusion (D8), closed-world bound (Eq. 72), novelty detection (KB10), category back-off.
Output: out/attr.json"""
import re, json, time
import numpy as np, pandas as pd, lightgbm as lgb
from sklearn.metrics import f1_score
import s10_common as C, s10_models as Mz

t0 = time.perf_counter()
m = C.load_meta(); X = C.load_X(); y = m['y'].to_numpy().astype(int)
fam = m['family'].to_numpy(); cat = m['category'].to_numpy(); sp = m['split'].to_numpy(); mo = m['month'].to_numpy()
GEN = re.compile(r'^(small|agent|vb|trojan|kryptik|win32|downloader|worm|malware|generic|cve-\d{4}-\d+|[a-z]{1,3}\d{4,}[a-z0-9]*)$')
generic = np.array([bool(GEN.match(f)) if f else False for f in fam])
mal = y == 1
tr = np.where((sp == 'train') & mal & ~generic)[0]
vc = pd.Series(fam[tr]).value_counts(); known = sorted(vc[vc >= 20].index)            # S9: >= 20 training samples
kidx = {f: i for i, f in enumerate(known)}
trk = tr[np.isin(fam[tr], known)]
ytr = np.array([kidx[f] for f in fam[trk]])
params = dict(objective='multiclass', num_class=len(known), num_leaves=31, learning_rate=0.05, feature_fraction=0.5,
              min_data_in_leaf=20, verbose=-1, deterministic=True, force_row_wise=True, num_threads=2, seed=11)
# NOTE: a first run with num_leaves=15, lr=0.1, min_data_in_leaf=5 diverged (training accuracy 27.5%, all max-probabilities 1.0);
# it was discarded as a numerical failure, not a result. Settings above: training accuracy 97.5%, December accuracy 78.2% at 40 rounds.
t = time.perf_counter()
b = lgb.train(params, lgb.Dataset(np.asarray(X[trk]), label=ytr, params={'max_bin': 63, 'verbose': -1}), num_boost_round=150)
fit_s = time.perf_counter() - t
ev = np.where(np.isin(sp, ['cal', 'test']) & mal & ~generic)[0]
P = np.vstack([b.predict(np.asarray(X[ev[i:i + 10000]])) for i in range(0, len(ev), 10000)])
pmax = P.max(1); top = np.argsort(-P, axis=1)[:, :3]
isknown = np.isin(fam[ev], known); truth = np.array([kidx.get(f, -1) for f in fam[ev]])
cal = sp[ev] == 'cal'
tau_open = {q: float(np.quantile(pmax[cal & isknown], q)) for q in (0.01, 0.05, 0.10)}   # 99/95/90% sensitivity check
# ICE credibility for attribution (Eq. 73), pooled non-conformity over known-family December samples
alpha_cal = np.sort(1 - P[cal & isknown, :][np.arange(int((cal & isknown).sum())), truth[cal & isknown]])
alpha = 1 - pmax
credv = (1 + (len(alpha_cal) - np.searchsorted(alpha_cal, alpha, side='left'))) / (1 + len(alpha_cal))
rows = []
rng = np.random.default_rng(3)
for mm in C.TEST_MONTHS:
    sel = (sp[ev] == 'test') & (mo[ev] == mm); n = int(sel.sum()); nu = int((sel & ~isknown).sum())
    k_sel = sel & isknown
    acc1 = float(np.mean(top[k_sel, 0] == truth[k_sel])); acc2 = float(np.mean((top[k_sel, :2] == truth[k_sel, None]).any(1)))
    acc3 = float(np.mean((top[k_sel, :3] == truth[k_sel, None]).any(1)))
    acc1_all = float(np.mean(top[sel, 0] == truth[sel])); acc3_all = float(np.mean((top[sel, :3] == truth[sel, None]).any(1)))
    # closed-set macro-F1 (unknown samples are always wrong) vs open-set macro-F1 with rejection (tau_open at 5%)
    yt = np.where(isknown[sel], truth[sel], len(known))           # label 'unknown' = len(known)
    pred_closed = top[sel, 0]
    pred_open = np.where(pmax[sel] < tau_open[0.05], len(known), top[sel, 0])
    labs = np.unique(yt)
    f_closed = f1_score(yt, pred_closed, labels=labs, average='macro', zero_division=0)
    f_open = f1_score(yt, pred_open, labels=labs, average='macro', zero_division=0)
    # families with >= 50 samples this month only (S6/S7 power rule)
    big = [l for l in labs if np.sum(yt == l) >= 50]
    f_open50 = f1_score(yt, pred_open, labels=big, average='macro', zero_division=0) if big else float('nan')
    nov = ~isknown[sel]; score_nov = 1 - pmax[sel]
    auroc = C.auc_fast(nov.astype(int), score_nov) if 0 < nov.sum() < n else float('nan')
    auprc = C.ap_score(nov.astype(int), score_nov) if 0 < nov.sum() < n else float('nan')
    rows.append(dict(month=mm, n=n, n_unknown=nu, nu=nu / n, top1_known=acc1, top2_known=acc2, top3_known=acc3,
                     top1_all=acc1_all, top3_all=acc3_all, upper_bound_all=1 - nu / n, macroF1_closed=f_closed, macroF1_open=f_open,
                     macroF1_open_n50=f_open50, n_fam50=len(big), novelty_auroc=auroc, novelty_auprc=auprc, novelty_base=nu / n,
                     unknown_recall=float(np.mean(pmax[sel][nov] < tau_open[0.05])) if nov.any() else float('nan'),
                     known_rejected=float(np.mean(pmax[sel][~nov] < tau_open[0.05])),
                     cred_unknown_recall=float(np.mean(credv[sel][nov] < 0.05)) if nov.any() else float('nan')))
    print(mm, {k: round(v, 3) if isinstance(v, float) else v for k, v in rows[-1].items()}, flush=True)
R = pd.DataFrame(rows)
jul = R[R.month == '2020-07'].iloc[0]
KB10 = dict(auroc=float(jul.novelty_auroc), auprc=float(jul.novelty_auprc), base=float(jul.novelty_base),
            pass_=bool(jul.novelty_auroc >= 0.80 and jul.novelty_auprc >= 3 * jul.novelty_base))
H7 = dict(p=C.wilcoxon_p(R.macroF1_open, R.macroF1_closed), mean_delta_pp=100 * float((R.macroF1_open - R.macroF1_closed).mean()),
          pass_=bool(C.wilcoxon_p(R.macroF1_open, R.macroF1_closed) < 0.05 and (R.macroF1_open > R.macroF1_closed).mean() > 0.5))
# P6: slope of open-set macro-F1 vs slope of detection F1 (f0, cert 0.1%, pi = 10%) over Mar..Sep; bootstrap in months' samples
df = pd.read_pickle(f'{C.OUT}/e1_metrics.pkl'); g = df[(df.model == 'lgbm_trace') & (df.seed == 11) & (df.thr == 'cert_0.1')]
det = np.array([g[(g.set == mm) & (g.metric == 'f1') & (g.pi == '0.1')]['value'].iloc[0] for mm in C.CERT_MONTHS])
opn = R.set_index('month').loc[C.CERT_MONTHS, 'macroF1_open'].to_numpy()
xm = np.arange(len(C.CERT_MONTHS)); slope = lambda v: float(np.polyfit(xm, v, 1)[0])
bs = []
for _ in range(1000):
    vals = []
    for mm in C.CERT_MONTHS:
        sel = np.where((sp[ev] == 'test') & (mo[ev] == mm))[0]; ii = rng.choice(sel, len(sel))
        yt = np.where(isknown[ii], truth[ii], len(known)); pr = np.where(pmax[ii] < tau_open[0.05], len(known), top[ii, 0])
        vals.append(f1_score(yt, pr, labels=np.unique(yt), average='macro', zero_division=0))
    bs.append(slope(np.array(vals)) - slope(det))
P6 = dict(slope_open=slope(opn), slope_det=slope(det), diff=slope(opn) - slope(det), ci=(float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))),
          falsified=bool(np.percentile(bs, 2.5) <= 0 <= np.percentile(bs, 97.5)))
# category back-off (trojan / worm / backdoor / other), S6 Block 10
cats = ['trojan', 'worm', 'backdoor']
tc = np.where((sp == 'train') & mal)[0]; yc = np.array([cats.index(c) if c in cats else 3 for c in cat[tc]])
bc = lgb.train(dict(params, num_class=4), lgb.Dataset(np.asarray(X[tc]), label=yc, params={'max_bin': 63, 'verbose': -1}), num_boost_round=120)
evc = np.where((sp == 'test') & mal)[0]; Pc = bc.predict(np.asarray(X[evc])); ycc = np.array([cats.index(c) if c in cats else 3 for c in cat[evc]])
cat_rows = []
for mm in C.TEST_MONTHS:
    sel = mo[evc] == mm
    cat_rows.append(dict(month=mm, acc=float(np.mean(Pc[sel].argmax(1) == ycc[sel])),
                         macroF1=float(f1_score(ycc[sel], Pc[sel].argmax(1), average='macro', zero_division=0))))
out = dict(n_known=len(known), n_train=len(trk), generic_tokens=sorted(set(fam[generic])), n_generic=int(generic.sum()), fit_s=fit_s,
           tau_open=tau_open, months=rows, KB10=KB10, H7=H7, P6=P6, category=cat_rows,
           recmal_band_pp=20, seconds=round(time.perf_counter() - t0, 1))
C.jdump(out, f'{C.OUT}/attr.json'); print(json.dumps(dict(KB10=KB10, H7=H7, P6=P6), indent=1))
