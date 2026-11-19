#!/usr/bin/env python3
"""Cross-check numbers quoted in the S10 prose against the result files. Each check: (label, value quoted in text, recomputed value, tolerance).
Prints every mismatch; exit code 1 if any."""
import sys, json, re, os
import numpy as np, pandas as pd
sys.path.insert(0, '/home/claude/s10/code')
import s10_common as C

O = C.OUT; J = lambda n: json.load(open(f'{O}/{n}'))
df = pd.read_pickle(f'{O}/e1_metrics.pkl')
def e1v(model, set_, metric, pi, thr, seed=None, agg='mean'):
    q = df[(df.model == model) & (df.set == set_) & (df.metric == metric) & (df.pi == str(pi)) & (df.thr == thr)]
    if seed is not None: q = q[q.seed == seed]
    return float(getattr(q['value'], agg)())
checks = []
def chk(label, quoted, actual, tol=0.006):
    checks.append((label, quoted, actual, abs(quoted - actual) <= tol))

# f0 pooled
chk('f0 TPR', 87.94, 100 * e1v('lgbm_trace', 'pool_MarSep', 'rec', 'native', 'cert_0.1', 11))
chk('f0 F1 pi10', 93.55, 100 * e1v('lgbm_trace', 'pool_MarSep', 'f1', '0.1', 'cert_0.1', 11))
chk('f0 prec pi1', 99.08, 100 * e1v('lgbm_trace', 'pool_MarSep', 'prec', '0.01', 'cert_0.1', 11))
chk('f0 MCC', 89.04, 100 * e1v('lgbm_trace', 'pool_MarSep', 'mcc', 'native', 'cert_0.1', 11))
chk('f0 AUC', 99.971, 100 * e1v('lgbm_trace', 'pool_MarSep', 'auc', 'native', '-', 11), 0.0006)
for mm, q in zip(C.TEST_MONTHS, [4.07, 5.86, 6.51, 4.98, 5.07, 5.62, 16.76, 24.64, 23.92]):
    chk(f'f0 FNR {mm}', q, 100 * e1v('lgbm_trace', mm, 'fnr', 'native', 'cert_0.1', 11))
# seed-mean
chk('LGBM TPR seed mean', 84.12, 100 * e1v('lgbm_trace', 'pool_MarSep', 'rec', 'native', 'cert_0.1'))
chk('ET TPR', 81.60, 100 * e1v('et', 'pool_MarSep', 'rec', 'native', 'cert_0.1'))
chk('RF TPR', 75.95, 100 * e1v('rf', 'pool_MarSep', 'rec', 'native', 'cert_0.1'))
chk('XGB TPR', 75.64, 100 * e1v('xgb', 'pool_MarSep', 'rec', 'native', 'cert_0.1'))
chk('LR chi2 TPR (max linear)', 36.13, 100 * e1v('lr_chi2', 'pool_MarSep', 'rec', 'native', 'cert_0.1'))
chk('pub FPR cert', 0.030, 100 * e1v('ember2018_pub', 'pool_MarSep', 'fpr', 'native', 'cert_0.1'), 0.0006)
chk('pub FPR emp', 0.193, 100 * e1v('ember2018_pub', 'pool_MarSep', 'fpr', 'native', 'emp_0.1'), 0.0006)
chk('f0 prec pi1 default', 64.38, 100 * e1v('lgbm_trace', 'pool_MarSep', 'prec', '0.01', 'default', 11))
chk('f0 prec pi0.1 cert', 91.39, 100 * e1v('lgbm_trace', 'pool_MarSep', 'prec', '0.001', 'cert_0.1', 11))
chk('f0 prec pi0.1 default', 15.19, 100 * e1v('lgbm_trace', 'pool_MarSep', 'prec', '0.001', 'default', 11))
chk('f0 F1 native default', 99.39, 100 * e1v('lgbm_trace', 'pool_MarSep', 'f1', 'native', 'default', 11))
chk('f0 TPR emp', 90.19, 100 * e1v('lgbm_trace', 'pool_MarSep', 'rec', 'native', 'emp_0.1', 11))
chk('f0 prec pi1 emp', 98.80, 100 * e1v('lgbm_trace', 'pool_MarSep', 'prec', '0.01', 'emp_0.1', 11))
# AUT
aut = pd.DataFrame(J('analysis_models.json')['aut'])
chk('AUT f0', 0.933, float(aut[(aut.model == 'lgbm_trace') & (aut.seed == 11)].aut_f1_pi10.iloc[0]), 0.0006)
chk('AUT lgbm mean', 0.910, float(aut[aut.model == 'lgbm_trace'].aut_f1_pi10.mean()), 0.0006)
chk('AUT pub', 0.947, float(aut[aut.model == 'ember2018_pub'].aut_f1_pi10.mean()), 0.0006)
# certificates
ce = J('analysis_certificates.json'); c5 = ce['thr0.005|tau0.005/0.05']['months']; c1 = ce['thr0.001|tau0.001/0.02']['months']
chk('FNR ub Jul 0.5', 8.42, 100 * c5['2020-07']['fnr_ub']); chk('FNR ub Aug 0.5', 13.93, 100 * c5['2020-08']['fnr_ub'])
chk('FPR ub Aug 0.1', 0.119, 100 * c1['2020-08']['fpr_ub'], 0.0006)
chk('SVR 0.5', 4, ce['thr0.005|tau0.005/0.05']['SVR_months'], 0)
# base rate
br = pd.DataFrame(J('analysis_baserate.json')['default_threshold_sweep'])
chk('default prec Apr pi1', 36.77, 100 * float(br[(br.month == '2020-04') & np.isclose(br.pi, 0.01)].prec.iloc[0]))
chk('default prec Mar pi1', 48.49, 100 * float(br[(br.month == '2020-03') & np.isclose(br.pi, 0.01)].prec.iloc[0]))
# bias
b = J('analysis_bias.json')
chk('P1 mean', 6.93, b['P1']['mean_pp_pi10']); chk('P1 rel', 7.66, b['P1']['rel_pct_pi10'])
chk('H9', -0.42, b['H9']['delta_pp'])
# assurance
t = J('reval_analysis.json')['L30_rho1.0']; P = t['policies']
for p_, q in (('a2_naive_frozen', 56550), ('a2_naive', 8730), ('a2_cert', 4740), ('a2_abst', 510), ('viii_reconcile', 90), ('viii_frozen', 600), ('iv_transcendent', 30)):
    chk(f'E_ev {p_}', q, P[p_]['E_ev'], 0)
chk('reviews tracepe', 680, P['tracepe']['reviews'], 0); chk('hits tracepe', 3, P['tracepe']['hits'], 0); chk('hits vii', 6, P['vii_margin']['hits'], 0)
fl = J('flips.json')['L30_rho1.0']['totals']
chk('flips', 142, fl['flips'], 0); chk('flips abstained', 142, fl['flips_abstained'], 0); chk('abstained', 5141, fl['abstained'], 0)
chk('mal regress', 7, fl['mal_regress'], 0); chk('ben regress', 60, fl['ben_regress'], 0)
chk('in-scope N', 60092, sum(u['N'] for u in t['K1']['updates']), 0)
# monitor, attribution, explain, ledger, ember
mo = J('monitor.json'); chk('aci7', 115, mo['aci']['7']['alarms'], 0); chk('aci30', 92, mo['aci']['30']['alarms'], 0)
a = J('attr.json'); chk('KB10 auprc', 0.671, a['KB10']['auprc'], 0.0006); chk('n_known', 68, a['n_known'], 0)
e = J('explain.json'); chk('KB11 delta', 0.168, e['KB11']['cliffs_delta'], 0.0006); chk('faith', 0.62, e['faithfulness']['mean_spearman'], 0.006)
L = J('ledger_tests.json'); chk('slope', 0.973, L['loglog_slope'], 0.0006)
E = J('ember.json'); chk('ember random pp', 19.86, E['random_arm']['mean_pp']); chk('ember fwd AUT', 0.776, E['forward_EMBER2018_to_BODMAS2020']['aut_f1_pi10'], 0.0006)
chk('ember pub AUC', 99.659, 100 * E['published_model_on_EMBER_test_NovDec']['auc'], 0.0006)
# ---- additions for the final draft (sensitivity, flips, statistics, bias arms, T0, cost, learning curves, wall-clock)
FL = J('flips.json')
chk('flips L60', 304, FL['L60_rho1.0']['totals']['flips'], 0); chk('flips L60 abst', 304, FL['L60_rho1.0']['totals']['flips_abstained'], 0)
chk('flips L90', 626, FL['L90_rho1.0']['totals']['flips'], 0); chk('flips L90 abst', 622, FL['L90_rho1.0']['totals']['flips_abstained'], 0)
chk('flips L90 conf ben->mal', 4, FL['L90_rho1.0']['totals']['ben_regress_conf'], 0)
chk('flips rho0.5', 218, FL['L30_rho0.5']['totals']['flips'], 0); chk('flips rho0.5 abst', 218, FL['L30_rho0.5']['totals']['flips_abstained'], 0)
chk('flips L30 N', 65233, FL['L30_rho1.0']['totals']['N'], 0); chk('corrective', 75, FL['L30_rho1.0']['summary']['corrective'], 0)
chk('mal regress rate %', 0.023, 100 * FL['L30_rho1.0']['summary']['mal_regress_rate'], 0.0006)
chk('ben flip rate %', 0.174, 100 * FL['L30_rho1.0']['summary']['ben_flip_rate'], 0.0006)
RA = J('reval_analysis.json'); t6 = RA['L60_rho1.0']; P6_ = t6['policies']
chk('L60 issued evaluative', 1361, P6_['viii_reconcile']['iss'], 0)
for k_, q in (('viii_reconcile', 480), ('tracepe', 399), ('vii_margin', 16), ('abl_noregion', 190)):
    chk(f'L60 E_ev {k_}', q, P6_[k_]['E_ev'], 0)
chk('L60 K3 rel', 16.9, 100 * t6['K3']['rel_red'], 0.06); chk('L60 K3 lo', 4.7, 100 * t6['K3']['ci'][0], 0.06); chk('L60 K3 hi', 29.3, 100 * t6['K3']['ci'][1], 0.06)
chk('L60 margin rel', -96.7, 100 * (P6_['vii_margin']['E_ev'] / P6_['viii_reconcile']['E_ev'] - 1), 0.06)
chk('L60 noregion rel', -60.4, 100 * (P6_['abl_noregion']['E_ev'] / P6_['viii_reconcile']['E_ev'] - 1), 0.06)
chk('L90 issued evaluative', 0, RA['L90_rho1.0']['policies']['viii_reconcile']['iss'], 0)
tr = RA['L30_rho0.5']['policies']; chk('rho0.5 viii', 182, tr['viii_reconcile']['E_ev'], 0); chk('rho0.5 tracepe', 182, tr['tracepe']['E_ev'], 0)
chk('rho0.5 noregion rel', -84.1, 100 * (tr['abl_noregion']['E_ev'] / tr['viii_reconcile']['E_ev'] - 1), 0.06)
chk('K2 max ub all scenarios %', 0.058, 100 * max(u['h_ub'] for tt in RA.values() for u in tt['K2']['updates']), 0.0006)
chk('A2 vs retrain %', -98.97, 100 * (P['viii_reconcile']['E_ev'] / P['a2_naive']['E_ev'] - 1), 0.006)
chk('A2 vs frozen %', -99.84, 100 * (P['viii_reconcile']['E_ev'] / P['a2_naive_frozen']['E_ev'] - 1), 0.006)
chk('frozen safeguards %', -98.9, 100 * (P['viii_frozen']['E_ev'] / P['a2_naive_frozen']['E_ev'] - 1), 0.06)
# violation counts (recomputed from per-month counts)
q = df[(df.metric == 'tp_fn_fp_tn') & df.set.isin(C.CERT_MONTHS)]
qv = df[(df.metric == 'fpr') & (df.pi == 'native') & df.set.isin(C.CERT_MONTHS)]
for thr_, tau, n_q in (('emp_0.1', 0.001, 14), ('cert_0.1', 0.001, 2), ('emp_1', 0.01, 44), ('cert_1', 0.01, 21)):
    g = q[q.thr == thr_]; chk(f'violations {thr_}', n_q, int(((g.fp / (g.fp + g.tn)) > tau).sum()), 0); chk(f'cells {thr_}', 273, len(g), 0)
    chk(f'violations {thr_} (fpr rows)', n_q, int((qv[qv.thr == thr_]['value'] > tau).sum()), 0)
g = q[q.thr == 'emp_0.1']; chk('violations emp_0.1 CP lower', 6, int(sum(C.cp_lower(int(a), int(a + b)) > 0.001 for a, b in zip(g.fp, g.tn))), 0)
# statistics
FR = J('analysis_models.json')['friedman']; chk('Friedman chi2', 94.97, FR['chi2'], 0.006); chk('Kendall W', 0.969, FR['W'], 0.0006)
chk('rank stack', 1.57, FR['mean_ranks']['stack'], 0.006); chk('rank lgbm_trace', 4.00, FR['mean_ranks']['lgbm_trace'], 0.006)
# leakage and monotone scaling
LK = J('e5_leak.json'); A_ = LK['arms']
chk('chi2 overlap', 215, LK['overlap_chi2_clean_vs_leaky'], 0); chk('pca k clean', 1151, LK['pca_k']['clean'], 0); chk('pca k leaky', 1328, LK['pca_k']['leaky'], 0)
chk('LR chi2 FNR clean', 66.44, 100 * A_['lr|chi2_clean']['pool_MarSep']['fnr']); chk('LR chi2 FNR leaky', 57.71, 100 * A_['lr|chi2_leaky']['pool_MarSep']['fnr'])
chk('SVM chi2 FNR clean', 77.42, 100 * A_['svm|chi2_clean']['pool_MarSep']['fnr']); chk('SVM chi2 FNR leaky', 63.80, 100 * A_['svm|chi2_leaky']['pool_MarSep']['fnr'])
chk('LR chi2 dF1', 9.18, 100 * (A_['lr|chi2_leaky']['pool_MarSep']['f1_pi10'] - A_['lr|chi2_clean']['pool_MarSep']['f1_pi10']))
chk('SVM chi2 dF1', 16.29, 100 * (A_['svm|chi2_leaky']['pool_MarSep']['f1_pi10'] - A_['svm|chi2_clean']['pool_MarSep']['f1_pi10']))
NM = J('e5_norm.json')['agreement']
for k_, q in (('dt|raw_vs_minmax', 489), ('dt|raw_vs_zscore', 305), ('rf|raw_vs_minmax', 183), ('rf|raw_vs_zscore', 131), ('lgbm|raw_vs_minmax', 75),
              ('lgbm|raw_vs_zscore', 82), ('lr|raw_vs_zscore', 3231), ('knn|raw_vs_zscore', 2315)):
    chk(f'norm {k_}', q, NM[k_]['disagree'], 0)
# T0 replication
T0 = J('e5_t0.json')['t0']
def t0r(key, metric, months=None):
    v = [m_[metric] for mm, m_ in T0[key]['months'].items() if months is None or mm in months]
    return 100 * min(v), 100 * max(v)
JS = ('2020-07', '2020-08', '2020-09')
lo_, hi_ = t0r('dated+prewindow|lgbm_ember', 'fnr'); chk('T0 PW FNR lo', 1.19, lo_); chk('T0 PW FNR hi', 3.43, hi_)
lo_, hi_ = t0r('dated+prewindow|lgbm_ember', 'fnr', JS); chk('T0 PW JulSep lo', 1.88, lo_); chk('T0 PW JulSep hi', 2.64, hi_)
lo_, hi_ = t0r('dated|lgbm_ember', 'fnr', JS); chk('T0 dated JulSep lo', 13.25, lo_); chk('T0 dated JulSep hi', 20.45, hi_)
chk('T0 PW thr', -0.115, T0['dated+prewindow|lgbm_ember']['thr'], 0.0006); chk('T0 dated thr', 8.946, T0['dated|lgbm_ember']['thr'], 0.0006)
fpw = [m_['fpr'] for m_ in T0['dated+prewindow|lgbm_trace']['months'].values()]
chk('T0 PW trace months FPR>0.1%', 7, sum(f > 0.001 for f in fpw), 0); chk('T0 PW trace max FPR', 1.019, 100 * max(fpw), 0.0006)
chk('T0 PW ember months FPR>0.1%', 3, sum(m_['fpr'] > 0.001 for m_ in T0['dated+prewindow|lgbm_ember']['months'].values()), 0)
chk('T0 PW unseen max', 29.09, 100 * max(m_['fnr_unseen'] for m_ in T0['dated+prewindow|lgbm_ember']['months'].values()))
# cost, learning curves, certificate F1 cost, wall-clock
TM = {j['model']: j for j in J('timing_clean.json')['jobs']}
for m_, fs, pu in (('lgbm_trace', 35.8, 13.4), ('lgbm_ember', 151.7, 102.5), ('xgb', 82.2, 9.9), ('stack', 121.7, 69.9), ('mlp', 26.7, 54.9)):
    chk(f'fit {m_}', fs, TM[m_]['fit_s'], 0.06); chk(f'pred {m_}', pu, TM[m_]['pred_us'], 0.06)
chk('rss lgbm_trace', 1.39, TM['lgbm_trace']['rss_gb'], 0.006); chk('max rss', 2.38, max(j['rss_gb'] for j in TM.values()), 0.006)
LC = J('learning_curves.json'); lcv = {(r['model'], r['n']): r for r in LC}
chk('lc lgbm full fit', 33.9, lcv[('lgbm_trace', 23158)]['fit_s'], 0.06); chk('lc xgb full fit', 74.7, lcv[('xgb', 23158)]['fit_s'], 0.06)
chk('lc ap 1158', 98.39, 100 * lcv[('lgbm_trace', 1158)]['ap_test_pi10']); chk('lc ap full', 99.79, 100 * lcv[('lgbm_trace', 23158)]['ap_test_pi10'])
chk('lc fnr 1158', 40.0, 100 * lcv[('lgbm_trace', 1158)]['fnr_test'], 0.06); chk('lc fnr full', 12.06, 100 * lcv[('lgbm_trace', 23158)]['fnr_test'])
chk('lc LR min FNR > 82', 1, int(min(r['fnr_test'] for r in LC if r['model'] == 'lr') > 0.82), 0)
f1m = df[(df.model == 'lgbm_trace') & (df.metric == 'f1') & (df.pi == '0.1') & df.set.isin(C.CERT_MONTHS)].groupby(['set', 'thr'])['value'].mean().unstack()
dd = 100 * (f1m['emp_0.1'] - f1m['cert_0.1']); chk('cert F1 cost lo', 1.45, dd.min()); chk('cert F1 cost hi', 9.04, dd.max())
import datetime as _dt
tot = 0.0
for lf in ('master.log', 'q2.log', 'q4.log', 'q5.log', 'q6.log', 'e1_queue.log'):
    op = {}
    for line in open(f'{O}/{lf}'):
        mm_ = re.match(r'=== (\d\d:\d\d:\d\d) (START|END) (.*?)( rc=\d+)?$', line.strip())
        if mm_:
            tt_ = _dt.datetime.strptime(mm_.group(1), '%H:%M:%S')
            if mm_.group(2) == 'START': op[mm_.group(3)] = tt_
            elif mm_.group(3) in op: tot += (tt_ - op.pop(mm_.group(3))).total_seconds()
chk('wall-clock h', 4.65, tot / 3600, 0.006)
bad = [c for c in checks if not c[3]]
for c in checks:
    print(('OK  ' if c[3] else 'BAD ') + f'{c[0]}: quoted {c[1]} actual {c[2]:.4f}')
print(f'{len(checks)} checks, {len(bad)} mismatches')
sys.exit(1 if bad else 0)
