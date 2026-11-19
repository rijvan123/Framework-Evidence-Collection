#!/usr/bin/env python3
"""EMBER-2018 corroboration (D10): (a) feature-pipeline check with the published EMBER-2018 LightGBM model on the vectorised
month-stratified subsample; (b) within-EMBER TESSERACT-style run mirroring TRACE-PE (train Jan-Apr 2018, calibrate May-Jun,
test Jul-Dec monthly; CP-certified thresholds; pi sweep; AUT); (c) random-split inflation arm; (d) forward transfer of the
EMBER-trained detector to BODMAS 2020 (C1-compliant) and backward application of f0 to EMBER (C1-violating, descriptive).
Output: out/ember.json"""
import json, time
import numpy as np, lightgbm as lgb
import s10_common as C, s10_models as Mz

t0 = time.perf_counter()
d = np.load(f'{C.CACHE}/ember2018_sub.npz', allow_pickle=True)
X = d['X']; y = d['y'].astype(int); mon = d['appeared'].astype(str); sha = d['sha'].astype(str)
months = ['2018-%02d' % k for k in range(1, 13)]
assert X.shape[1] == C.D
pub = lgb.Booster(model_file='/mnt/user-data/uploads/Datasets/ember2018/ember_model_2018.txt')
s_pub = pub.predict(X, raw_score=True)
res = dict(n=len(y), counts={mm: [int(np.sum((mon == mm) & (y == 0))), int(np.sum((mon == mm) & (y == 1)))] for mm in months})
nd = np.isin(mon, ['2018-11', '2018-12'])
res['published_model_on_EMBER_test_NovDec'] = dict(auc=C.auc_fast(y[nd], s_pub[nd]), tpr_at_fpr_1e3_testtuned=C.tpr_at_fpr_test(y[nd], s_pub[nd], 1e-3),
                                                     tpr_at_fpr_1e2_testtuned=C.tpr_at_fpr_test(y[nd], s_pub[nd], 1e-2))
res['published_model_on_EMBER_train_JanOct_insample'] = dict(auc=C.auc_fast(y[~nd], s_pub[~nd]))
# (b) within-EMBER temporal run
tr = np.isin(mon, months[:4]); ca = np.isin(mon, months[4:6]); te_m = months[6:]
b = Mz.fit_lgbm(X[tr], y[tr], C.LGB_TRACE, C.LGB_TRACE_ROUNDS, 11)
s = b.predict(X, raw_score=True)
out = {}
for tau in (0.001, 0.005):
    thr, k = C.certified_threshold(s[ca][y[ca] == 0], tau); rows = {}
    for mm in ['cal'] + te_m:
        sel = ca if mm == 'cal' else (mon == mm)
        tp, fn, fp, tn = C.counts(y[sel], s[sel], thr); r = C.rates_from_counts(tp, fn, fp, tn)
        r10 = C.rates_from_counts(tp, fn, fp, tn, C.kappa_for(0.10, tp + fn, fp + tn)); r1 = C.rates_from_counts(tp, fn, fp, tn, C.kappa_for(0.01, tp + fn, fp + tn))
        rows[mm] = dict(tp=tp, fn=fn, fp=fp, tn=tn, fnr=r['fnr'], fpr=r['fpr'], f1=r['f1'], f1_pi10=r10['f1'], prec_pi1=r1['prec'], prec_pi10=r10['prec'],
                        fpr_ub=C.cp_upper(fp, fp + tn), fnr_ub=C.cp_upper(fn, tp + fn), auc=C.auc_fast(y[sel], s[sel]), ap_pi10=C.ap_score(y[sel], s[sel], 0.10))
    out[str(tau)] = dict(thr=thr, kstar=k, months=rows, aut_f1_pi10=C.aut([rows[mm]['f1_pi10'] for mm in te_m]),
                         aut_tpr=C.aut([1 - rows[mm]['fnr'] for mm in te_m]), SVR_0_5_5=int(np.sum([rows[mm]['fpr_ub'] <= 0.005 and rows[mm]['fnr_ub'] <= 0.05 for mm in te_m])))
res['temporal'] = out
# (c) random-split arm with matched sizes (5 seeds)
pool = np.where(np.isin(mon, months[:4] + months[4:6] + te_m))[0]; arms = []
for seed in C.MODEL_SEEDS:
    rng = np.random.default_rng(seed); p = rng.permutation(pool)
    a, b_ = int(tr.sum()), int(ca.sum()); trr, car, ter = p[:a], p[a:a + b_], p[a + b_:]
    bb = Mz.fit_lgbm(X[trr], y[trr], C.LGB_TRACE, C.LGB_TRACE_ROUNDS, seed); sr = bb.predict(X[np.r_[car, ter]], raw_score=True)
    thr, _ = C.certified_threshold(sr[:len(car)][y[car] == 0], 0.001); st = sr[len(car):]
    tp, fn, fp, tn = C.counts(y[ter], st, thr); r10 = C.rates_from_counts(tp, fn, fp, tn, C.kappa_for(0.10, tp + fn, fp + tn))
    arms.append(dict(seed=seed, f1_pi10=r10['f1'], fnr=fn / (tp + fn), fpr=fp / (fp + tn), auc=C.auc_fast(y[ter], st)))
d10 = [100 * (a_['f1_pi10'] - out['0.001']['aut_f1_pi10']) for a_ in arms]
res['random_arm'] = dict(arms=arms, delta_pp_vs_temporal_aut=d10, mean_pp=float(np.mean(d10)), ci=C.boot_ci_mean(np.array(d10)))
# (d) transfer: EMBER-trained (Jan-Apr 2018) detector -> BODMAS 2020 test months (forward, C1-compliant);
#     f0 (BODMAS Aug-Nov 2019) -> EMBER 2018 (backward, C1-violating; descriptive only)
m = C.load_meta(); Xb = C.load_X(); yb = m['y'].to_numpy().astype(int); sp = m['split'].to_numpy(); mo = m['month'].to_numpy()
cal_b = np.where(sp == 'cal')[0]; sb_cal = b.predict(np.asarray(Xb[cal_b]), raw_score=True)
thr_b, _ = C.certified_threshold(sb_cal[yb[cal_b] == 0], 0.001); fwd = {}
for mm in C.CERT_MONTHS:
    sel = np.where((sp == 'test') & (mo == mm))[0]; sb = b.predict(np.asarray(Xb[sel]), raw_score=True)
    tp, fn, fp, tn = C.counts(yb[sel], sb, thr_b); r10 = C.rates_from_counts(tp, fn, fp, tn, C.kappa_for(0.10, tp + fn, fp + tn))
    fwd[mm] = dict(auc=C.auc_fast(yb[sel], sb), fnr=fn / (tp + fn), fpr=fp / (fp + tn), f1_pi10=r10['f1'])
res['forward_EMBER2018_to_BODMAS2020'] = dict(threshold='CP-certified 0.1% on BODMAS Dec-2019', months=fwd, aut_f1_pi10=C.aut([fwd[mm]['f1_pi10'] for mm in C.CERT_MONTHS]))
import json as _j
f0 = lgb.Booster(model_str=C.Store().get(_j.load(open(f'{C.CACHE}/scores/lgbm_trace_s11.json'))['model_obj']).decode())
s0 = f0.predict(X, raw_score=True)
res['backward_f0_to_EMBER2018'] = {mm: dict(auc=C.auc_fast(y[mon == mm], s0[mon == mm])) for mm in months}
# overlap check: SHA-256 shared between the EMBER subsample and BODMAS (cross-dataset duplicates)
res['sha_overlap_with_BODMAS'] = int(len(set(sha) & set(m['sha'])))
res['seconds'] = round(time.perf_counter() - t0, 1)
C.jdump(res, f'{C.OUT}/ember.json'); print(json.dumps({k: v for k, v in res.items() if k not in ('temporal', 'backward_f0_to_EMBER2018')}, indent=1, default=str))
print(json.dumps({t: dict(aut_f1_pi10=v['aut_f1_pi10'], aut_tpr=v['aut_tpr'], kstar=v['kstar']) for t, v in out.items()}, indent=1))
