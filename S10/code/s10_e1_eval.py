#!/usr/bin/env python3
"""E1/E2 evaluation: thresholds and calibration fitted on December 2019 only; monthly metrics with 95% CIs;
analytic prevalence sweep (Eq. 70) and measured prevalence-resampled streams; AUT (Eq. 69).
Output: out/e1_metrics.pkl (tidy), out/e1_streams.pkl, out/e1_thresholds.json."""
import os, sys, glob, json, math
import numpy as np, pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
import s10_common as C

m = C.load_meta(); y_all = m['y'].to_numpy().astype(int); month_all = m['month'].to_numpy()
split_all = m['split'].to_numpy(); stratum_all = m['stratum'].to_numpy()
PROB_SCORES = {'rf', 'et', 'knn'}                 # scores already in [0, 1]


def default_thr(name):
    return 0.5 if name in PROB_SCORES else 0.0


def thresholds(name, s_cal, y_cal):
    b = s_cal[y_cal == 0]
    out = {}
    out['cert_0.1'], out['kstar_0.1'] = C.certified_threshold(b, 0.001)
    out['cert_0.5'], out['kstar_0.5'] = C.certified_threshold(b, 0.005)
    out['cert_1'], out['kstar_1'] = C.certified_threshold(b, 0.01)
    out['emp_0.1'], out['kemp_0.1'] = C.empirical_threshold(b, 0.001)
    out['emp_1'], out['kemp_1'] = C.empirical_threshold(b, 0.01)
    out['default'] = default_thr(name)
    # F1-max under pi* = 10% on December (S9 pi*-aware threshold), Eq. 70 re-weighting
    cand = np.unique(np.quantile(s_cal, np.linspace(0.0, 1.0, 801)))
    k = C.kappa_for(0.10, int(y_cal.sum()), int((1 - y_cal).sum()))
    best = (-1, None)
    for t in cand:
        tp, fn, fp, tn = C.counts(y_cal, s_cal, t)
        f = C.rates_from_counts(tp, fn, fp, tn, k)['f1']
        if f == f and f > best[0]:
            best = (f, t)
    out['f1pi10'] = float(best[1])
    return {k_: (float(v) if not isinstance(v, (int, np.integer)) else int(v)) for k_, v in out.items()}


def calibrators(s_cal, y_cal):
    iso = IsotonicRegression(out_of_bounds='clip', y_min=0, y_max=1).fit(s_cal, y_cal)
    platt = LogisticRegression(C=1e6, max_iter=1000).fit(s_cal.reshape(-1, 1), y_cal)
    return iso, platt


def month_rows(name, seed, s, idx, thr, iso, platt, B=1000, ap_ci=False, primary_thr='cert_0.1'):
    """Tidy rows (dict) for every month (Jan-Sep 2020) + pooled sets, every threshold, native and pi-weighted."""
    rows = []
    yy = y_all[idx]; mo = month_all[idx]; sp = split_all[idx]
    sets = {mm: (sp == 'test') & (mo == mm) for mm in C.TEST_MONTHS}
    sets['pool_MarSep'] = (sp == 'test') & np.isin(mo, C.CERT_MONTHS)
    sets['pool_JanSep'] = (sp == 'test')
    sets['cal_Dec'] = (sp == 'cal')
    q_iso = iso.predict(s); q_pl = platt.predict_proba(s.reshape(-1, 1))[:, 1]
    for key, sel in sets.items():
        ys = yy[sel]; ss = s[sel]; n_pos = int(ys.sum()); n_neg = int((1 - ys).sum())
        base = dict(model=name, seed=seed, set=key, n_pos=n_pos, n_neg=n_neg)
        auc, (alo, ahi) = C.auc_ci(ys, ss) if (n_pos and n_neg) else (float('nan'), (float('nan'),) * 2)
        rows.append(dict(base, thr='-', pi='native', metric='auc', value=auc, lo=alo, hi=ahi))
        for pi in ['native', 0.10, 0.01]:
            ap = C.ap_score(ys, ss, None if pi == 'native' else pi) if (n_pos and n_neg) else float('nan')
            lo = hi = float('nan')
            if ap_ci and n_pos and n_neg and key in ('pool_MarSep',) + tuple(C.CERT_MONTHS):
                lo, hi = C.boot_ap_ci(ys, ss, B=200, seed=1, pi=None if pi == 'native' else pi)
            rows.append(dict(base, thr='-', pi=str(pi), metric='ap', value=ap, lo=lo, hi=hi))
        rows.append(dict(base, thr='iso', pi='native', metric='ece', value=C.ece_binary(ys, q_iso[sel]), lo=np.nan, hi=np.nan))
        rows.append(dict(base, thr='platt', pi='native', metric='ece', value=C.ece_binary(ys, q_pl[sel]), lo=np.nan, hi=np.nan))
        rows.append(dict(base, thr='iso', pi='native', metric='brier', value=C.brier(ys, q_iso[sel]), lo=np.nan, hi=np.nan))
        if n_pos and n_neg:
            rows.append(dict(base, thr='test-tuned', pi='native', metric='tpr@fpr1e-3', value=C.tpr_at_fpr_test(ys, ss, 1e-3), lo=np.nan, hi=np.nan))
            rows.append(dict(base, thr='test-tuned', pi='native', metric='tpr@fpr1e-2', value=C.tpr_at_fpr_test(ys, ss, 1e-2), lo=np.nan, hi=np.nan))
        for tname in ['cert_0.1', 'cert_0.5', 'cert_1', 'emp_0.1', 'emp_1', 'default', 'f1pi10']:
            tp, fn, fp, tn = C.counts(ys, ss, thr[tname])
            rows.append(dict(base, thr=tname, pi='counts', metric='tp_fn_fp_tn', value=np.nan, lo=np.nan, hi=np.nan,
                             tp=tp, fn=fn, fp=fp, tn=tn))
            pis = ['native'] + C.PIS
            for pi in pis:
                k = 1.0 if pi == 'native' else C.kappa_for(pi, tp + fn, fp + tn)
                r = C.rates_from_counts(tp, fn, fp, tn, k)
                ci = C.boot_threshold_metrics(tp, fn, fp, tn, B=B, seed=7, pi=None if pi == 'native' else pi) \
                    if (tname == primary_thr or pi in ('native', 0.10, 0.01)) and (tp + fn) and (fp + tn) else None
                for met in ['prec', 'rec', 'f1', 'fpr', 'fnr', 'mcc', 'bal_acc']:
                    if pi != 'native' and met in ('rec', 'fpr', 'fnr', 'bal_acc'):
                        continue                    # prevalence-invariant
                    lo, hi = ci[met] if ci else (np.nan, np.nan)
                    rows.append(dict(base, thr=tname, pi=str(pi), metric=met, value=r[met], lo=lo, hi=hi))
    return rows


def measured_streams(name, seed, s, idx, thr_val, seeds=C.STREAM_SEEDS):
    """Prevalence-resampled streams (S7 Part 6.8): per month keep all dated benign, sub-sample malware to pi."""
    out = []
    yy = y_all[idx]; mo = month_all[idx]; sp = split_all[idx]
    for mm in C.CERT_MONTHS:
        sel = np.where((sp == 'test') & (mo == mm))[0]
        ib = sel[yy[sel] == 0]; im = sel[yy[sel] == 1]
        for pi in C.PIS_MEASURED:
            k = int(round(pi * len(ib) / (1 - pi)))
            for ss in seeds:
                rng = np.random.default_rng(ss * 1000 + int(pi * 1000) + int(mm[-2:]))
                if k <= len(im):
                    pick = np.r_[ib, rng.choice(im, k, replace=False)]
                else:
                    nb = int(round(len(im) * (1 - pi) / pi)); pick = np.r_[rng.choice(ib, nb, replace=False), im]
                tp, fn, fp, tn = C.counts(yy[pick], s[pick], thr_val)
                r = C.rates_from_counts(tp, fn, fp, tn)
                out.append(dict(model=name, seed=seed, month=mm, pi=pi, stream_seed=ss, n_mal=tp + fn, n_ben=fp + tn,
                                tp=tp, fn=fn, fp=fp, tn=tn, prec=r['prec'], rec=r['rec'], f1=r['f1'], mcc=r['mcc'],
                                ap=C.ap_score(yy[pick], s[pick])))
    return out


def run(files):
    rows = []; streams = []; thr_all = {}
    for f in files:
        base = os.path.basename(f)[:-4]; name, seed = base.rsplit('_s', 1); seed = int(seed)
        d = np.load(f); idx = d['idx']; s = d['s']
        cal = split_all[idx] == 'cal'
        thr = thresholds(name, s[cal], y_all[idx][cal]); iso, platt = calibrators(s[cal], y_all[idx][cal])
        thr_all[base] = thr
        primary = (name == 'lgbm_trace' and seed == 11)
        rows += month_rows(name, seed, s, idx, thr, iso, platt, B=1000, ap_ci=primary)
        streams += measured_streams(name, seed, s, idx, thr['cert_0.1'])
        print('done', base, flush=True)
    return pd.DataFrame(rows), pd.DataFrame(streams), thr_all


if __name__ == '__main__':
    files = sorted(glob.glob(f'{C.CACHE}/scores/*.npz'))
    if len(sys.argv) > 1:
        files = [f for f in files if any(os.path.basename(f).startswith(a + '_s') for a in sys.argv[1:])]
    df, st, thr = run(files)
    tag = '' if len(sys.argv) == 1 else '_' + '_'.join(sys.argv[1:])
    df.to_pickle(f'{C.OUT}/e1_metrics{tag}.pkl'); st.to_pickle(f'{C.OUT}/e1_streams{tag}.pkl')
    C.jdump(thr, f'{C.OUT}/e1_thresholds{tag}.json')
    print('rows', len(df), 'stream rows', len(st))
