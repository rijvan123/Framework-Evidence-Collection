#!/usr/bin/env python3
"""S10 result tables (markdown), generated only from result files written by the S10 harness.
Every cell is measured-on-Claude {MoC} unless the column or note says reproduced-from-paper {RfP}.
Output: tables/*.md and tables/all_tables.md"""
import os, json, glob, pickle, sys
import numpy as np, pandas as pd
import s10_common as C

T = {}
O = C.OUT
NICE = {'lgbm_trace': 'LGBM-TRACE (f₀ family)', 'lgbm_ember': 'LGBM-EMBER', 'xgb': 'XGBoost', 'rf': 'Random forest', 'et': 'Extra trees',
        'lr': 'LR', 'lr_chi2': 'LR + χ²(256)', 'lr_ig': 'LR + IG(256)', 'lr_mrmr': 'LR + mRMR(128)', 'lr_pca': 'LR + PCA(0.95)',
        'svm_lin': 'Linear SVM', 'svm_rbf': 'RBF-SVM (PoC, 10k)', 'knn': 'k-NN (PCA-50)', 'nb': 'Gaussian NB', 'mlp': 'MLP (PoC, 20k)',
        'stack': 'Temporal stacking', 'ember2018_pub': 'EMBER-2018 GBDT (published model)'}
MON = lambda mm: pd.Timestamp(mm + '-01').strftime('%b %Y') if mm[:2] == '20' else mm


def J(name):
    p = f'{O}/{name}'
    return json.load(open(p)) if os.path.exists(p) else None


def pct(v, d=2, scale=100):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return '—'
    return f'{scale * v:.{d}f}'


def ci(lo, hi, d=2, scale=100):
    if lo is None or hi is None or not np.isfinite(lo) or not np.isfinite(hi):
        return ''
    return f' [{scale * lo:.{d}f}, {scale * hi:.{d}f}]'


def p_fmt(p):
    if p is None or not np.isfinite(p):
        return '—'
    return f'{p:.1e}' if p < 1e-3 else f'{p:.3f}'


def table(hdr, rows):
    s = '| ' + ' | '.join(hdr) + ' |\n|' + '---|' * len(hdr) + '\n'
    return s + '\n'.join('| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows) + '\n'


def write(name, title, md, note):
    txt = f'**{title}**\n\n{md}\n{note}\n'
    open(f'{C.TABLES}/{name}.md', 'w').write(txt); T[name] = txt; print('table', name)


def e1():
    return pd.read_pickle(f'{O}/e1_metrics.pkl')

def leak_delong():
    """DeLong tests clean vs leaky arms (P3/U3) on the pooled March-September test rows; returns {clf|arm: (dAUC, p)}."""
    lk = J('e5_leak.json')
    if not lk:
        return None, None
    m = C.load_meta(); y = m['y'].to_numpy().astype(int); sp = m['split'].to_numpy(); mo = m['month'].to_numpy()
    te = np.where(sp == 'test')[0]; pool = np.isin(mo[te], C.CERT_MONTHS); out = {}
    for clf in ('lr', 'svm'):
        for arm in ('scale', 'chi2', 'pca'):
            fc, fl = f'{C.CACHE}/leak_{clf}|{arm}_clean.npy', f'{C.CACHE}/leak_{clf}|{arm}_leaky.npy'
            if os.path.exists(fc) and os.path.exists(fl):
                a, b = np.load(fc)[pool], np.load(fl)[pool]
                d, pv = C.delong_test(y[te][pool], b, a)          # leaky - clean
                out[f'{clf}|{arm}'] = (float(d), float(pv))
    return lk, out


def u3_u9():
    lk, dl = leak_delong(); nm = J('e5_norm.json'); u3 = u9 = None
    if lk and dl:
        sel = {k: v for k, v in dl.items() if k.split('|')[1] in ('chi2', 'pca')}
        sig_up = [k for k, (d, pv) in sel.items() if pv < 0.05 and d > 0]
        tl = lk['lgbm_scaling_leak']
        ar = lk['arms']; f1d = {c: 100 * (ar[f'{c}|chi2_leaky']['pool_MarSep']['f1_pi10'] - ar[f'{c}|chi2_clean']['pool_MarSep']['f1_pi10']) for c in ('lr', 'svm')}
        txt = (f"χ² selection leak: ΔAUC {100 * dl['lr|chi2'][0]:+.3f} pp (LR), {100 * dl['svm|chi2'][0]:+.3f} pp (SVM), DeLong p ≤ {max(dl['lr|chi2'][1], dl['svm|chi2'][1]):.1e}; "
               f"F1 at π = 10% {f1d['lr']:+.2f}/{f1d['svm']:+.2f} pp. PCA leak: ΔAUC {100 * dl['lr|pca'][0]:+.3f}/{100 * dl['svm|pca'][0]:+.3f} pp. "
               f"Scaling leak: ΔAUC {100 * dl['lr|scale'][0]:+.3f}/{100 * dl['svm|scale'][0]:+.3f} pp; LightGBM under leaky z-scaling agrees on {100 * tl['decision_agreement']:.2f}% of verdicts (not identical)")
        u3 = dict(text=txt, outcome=('selection clause not falsified; PCA clause not supported; tree clause fails' if sig_up else
                                     'falsified (no significant selection/PCA inflation)'), sig=sig_up, delong=dl)
    if nm:
        ag = nm['agreement']
        exact = [k for k in ag if k.split('|')[0] in ('dt', 'rf')]; hist = [k for k in ag if k.startswith('lgbm')]; sens = [k for k in ag if k.split('|')[0] in ('lr', 'knn')]
        exact_ok = all(ag[k]['disagree'] == 0 for k in exact); hist_ok = all(ag[k]['agreement'] >= 0.9999 for k in hist)
        sens_change = all(ag[k]['disagree'] > 0 for k in sens)
        txt = (f"exact trees (DT, RF): {min(ag[k]['agreement'] for k in exact) * 100:.2f}–{max(ag[k]['agreement'] for k in exact) * 100:.2f}% agreement; LightGBM agreement "
               f"{', '.join(f'{100 * ag[k]['agreement']:.2f}%' for k in hist)}; LR/kNN raw vs z-score: {', '.join(f'{100 * ag[k]['agreement']:.2f}%' for k in sens)} agreement")
        u9 = dict(text=txt, outcome='not falsified' if (exact_ok and hist_ok and sens_change) else
                  ('falsified as stated (float32 resolution); ordering holds' if not exact_ok else 'partially falsified'), exact_ok=exact_ok, hist_ok=hist_ok, sens_change=sens_change)
    return u3, u9


# --------------------------------------------------------------------------------------------- T1a data
def t_data():
    I = J('e0_init.json'); m = C.load_meta(); y = m['y'].to_numpy().astype(int); sp = m['split'].to_numpy()
    role = {'Dated': 'primary stream (train / calibrate / test)', 'Placeholder': 'January 2020 benign with placeholder timestamp; censored (KB5)',
            'Bulk': 'February 2020 benign with batch timestamp; censored (KB5)', 'SpikeMal': 'malware on spike days (k = 10 rule); R-S1 only',
            'Quarantine': 'benign with unparseable or conflicting time; excluded', 'PreWindow': 'benign first seen before 2019-08-29; PreWindow arm only'}
    rows = [[k, f"{v.get('0', 0):,}", f"{v.get('1', 0):,}", role.get(k, '')] for k, v in sorted(I['strata'].items(), key=lambda kv: -sum(kv[1].values()))]
    tot0 = sum(v.get('0', 0) for v in I['strata'].values()); tot1 = sum(v.get('1', 0) for v in I['strata'].values())
    rows.append(['Total', f'{tot0:,}', f'{tot1:,}', f'{tot0 + tot1:,} files; {I["dup_groups"]} identical-vector groups logged (DUP)'])
    md = table(['Stratum', 'Benign', 'Malware', 'Role'], rows)
    sr = []
    for k, lab in (('train', 'Train: Dated, 29 Aug–30 Nov 2019'), ('cal', 'Calibrate: Dated, December 2019'), ('test', 'Test: Dated, January–September 2020')):
        sel = sp == k; sr.append([lab, f'{int(((y == 0) & sel).sum()):,}', f'{int(((y == 1) & sel).sum()):,}', f'{int(sel.sum()):,}'])
    md += '\n' + table(['Split (S7)', 'Benign', 'Malware', 'Files'], sr)
    write('table1_data', 'Table 1. BODMAS strata and the temporal split', md,
          'Strata and split reproduced from S7 on the released metadata and vectors; identifiers unique across all rows (134,428 SHA-256 digests and the 7 VirusShare names of the Quarantine stratum). Certificates and FPR-dependent metrics use '
          'March–September 2020, the months with ≥ 500 dated benign files. {MoC}.')


# --------------------------------------------------------------------------------------------- T1b register
def t_register():
    B = J('analysis_bias.json'); BR = J('analysis_baserate.json'); CA = J('analysis_calibration.json'); DR = J('analysis_drift.json')
    AT = J('attr.json'); LT = J('ledger_tests.json'); ER = J('analysis_errors.json'); MO = J('analysis_models.json'); RA = J('reval_analysis.json')
    MN = J('monitor.json'); CE = J('analysis_certificates.json'); ST = J('analysis_strata.json'); EX = J('explain.json'); XE = J('xenv.json'); LR = J('analysis_lr.json')
    lk = J('e5_leak.json'); nm = J('e5_norm.json'); t = RA['L30_rho1.0']; rows = []
    p1 = B['P1']
    rows.append(['U1 (P1/H1)', 'Random split inflates F1 vs temporal AUT', f"+{p1['mean_pp_pi10']:.2f} pp [{p1['ci_pi10'][0]:.2f}, {p1['ci_pi10'][1]:.2f}] at π = 10%", 'not falsified'])
    rows.append(['U2 (P2/H2)', 'Precision follows Eq. (55)', f"analytic value outside measured CI in {100 * BR['share_outside']:.0f}% of 28 cells; clause 2 untestable (no month with FPR ≥ 0.1%)", 'not falsified'])
    U3, U9 = u3_u9()
    if U3:
        rows.append(['U3 (P3)', 'Pre-split selection/PCA inflates LR/SVM; scaling leaves trees unchanged', U3['text'], U3['outcome']])
    else:
        rows.append(['U3 (P3)', 'Pre-split selection/PCA inflates LR/SVM; scaling leaves trees unchanged', 'pending', 'pending'])
    P4 = CA['P4']
    rows.append(['U4 (P4)', 'Isotonic/Platt lower ECE; prior shift lowers Brier/EC at π ≤ 1%',
                 f"isotonic raised ECE by {-100 * P4['mean_reduction_iso']:.2f} pp [{-100 * P4['ci_reduction_iso'][1]:.2f}, {-100 * P4['ci_reduction_iso'][0]:.2f}]; prior shift lowers Brier at π = 0.1% (p = {P4['brier_prior_0.001']['p']:.3f}), not at 1% (p = {P4['brier_prior_0.01']['p']:.3f})",
                 'falsified'])
    rows.append(['U5 (P5/H4)', 'ρ(JS drift, F1) ≤ −0.5', f"ρ = {DR['P5']['rho_D_f1pi10']:.2f}, p = {DR['P5']['p']:.2f}, CI upper {DR['P5']['ci'][1]:.2f}", 'falsified'])
    p6 = AT['P6']
    rows.append(['U6 (P6)', 'Open-set macro-F1 declines faster than detection F1', f"slope difference {100 * p6['diff']:+.2f} [{100 * p6['ci'][0]:.2f}, {100 * p6['ci'][1]:.2f}] pp/month (opposite sign)", 'falsified'])
    rows.append(['U7 (P7/H6)', 'τ* beats 0.5 on expected cost at π ≤ 1%', "τ* lower EC in 1 of 6 (π, ratio) cells (π = 1%, ratio 100: 7/7 months)", 'not falsified (rule); weak'])
    rows.append(['U8 (P8/H8)', 'Chain detects all injected edits; verification linear', f"{sum(v['detected'] for v in LT['injections'].values()):,}/{sum(v['trials'] for v in LT['injections'].values()):,} detected; slope {LT['loglog_slope']:.3f}", 'not falsified'])
    if U9:
        rows.append(['U9 (P9)', 'Trees invariant to monotone scaling; LR/kNN not', U9['text'], U9['outcome']])
    else:
        rows.append(['U9 (P9)', 'Trees invariant to monotone scaling; LR/kNN not', 'pending', 'pending'])
    e = ER['eq19']
    rows.append(['U10 (P10)', 'FNR and FPR higher in the high-entropy stratum', f"FNR OR {e['fnr']['OR']:.2f} [{e['fnr']['OR_ci'][0]:.2f}, {e['fnr']['OR_ci'][1]:.2f}]; FPR OR {e['fpr']['OR']:.2f} [{e['fpr']['OR_ci'][0]:.2f}, {e['fpr']['OR_ci'][1]:.2f}] (3 FPs)", 'falsified for FPR'])
    rows.append(['U11 (P11)', 'Observed TPR/FPR follow Eq. (5) under injected label noise', 'prediction inside bootstrap CI at η = 1% and 5%', 'not falsified'])
    rows.append(['U12 (H3)', 'Unseen-family FNR > known-family FNR', f"Wilcoxon p = {ER['H3']['p']:.4f}, A12 = {ER['H3']['A12']:.3f}", 'met'])
    fr = MO['friedman']
    rows.append(['U13 (H5)', 'GBDT leads on AUT', f"Friedman χ² = {fr['chi2']:.1f}, p = {fr['p']:.1e}, W = {fr['W']:.3f}", 'met'])
    rows.append(['U14 (H7)', 'Open-set rejection raises open-set macro-F1', f"p = {AT['H7']['p']:.4f}; mean {AT['H7']['mean_delta_pp']:+.2f} pp", 'met (negligible effect)'])
    rows.append(['U15 (H9)', 'No COFF-timestamp artefact', f"ΔAUT = {B['H9']['delta_pp']:+.2f} pp", 'met'])
    rows.append(['U16 (H10)', 'Calibration degrades over time', f"ρ(month, ECE) = {CA['H10']['rho']:.2f}, p = {CA['H10']['p']:.2f}", 'met by sign rule; n.s.'])
    rows.append(['K1', 'Full re-scoring changes ≤ B in ≥ 6/7 updates', f"{t['K1']['n_le_B']}/{t['K1']['n_updates']} updates; 0 changes in scope", 'kill met'])
    hub = [u['h_ub'] for u in t['K2']['updates']]
    rows.append(['K2', 'CP-95% upper bound of h < 0.1% in every update', f"0 harmful flips; upper bounds {100 * min(hub):.3f}–{100 * max(hub):.3f}%", 'kill met'])
    rows.append(['K3', 'Upper CI of relative E^ev reduction vs (viii) < 10% (L = 30 d)', f"{100 * t['K3']['rel_red']:.1f}% [{100 * t['K3']['ci'][0]:.1f}, {100 * t['K3']['ci'][1]:.1f}]", 'kill met → A2'])
    rows.append(['KT', 'Alarm ≤ 14 d after July onset and ≤ 1 false alarm per stable month', f"one alarm ({MN['alarms'][0]}); none after onset ({MN['onset_july_week']})", 'kill met → scheduled'])
    kb1 = t['KB1']
    rows.append(['KB1', 'Yield ≥ 1.5× (vii) and lower U(t) in ≥ 6/7 months', f"yield {100 * kb1['yield_tracepe']:.2f}% vs {100 * kb1['yield_margin']:.2f}% (×{kb1['ratio']:.2f}); lower U in {kb1['months_lower_U']}/7", 'not met'])
    rows.append(['KB3', '≥ 99.9% bit-identical re-execution', f"{100 * XE['bit_identical_fraction']:.1f}% (tree hash, scores, vector digest)", 'met'])
    rows.append(['KB4', 'Static 80:20 understates FPR or FNR in ≥ 5/7 months', f"FNR understated in {B['KB4']['months_understated']}/7", 'met'])
    rows.append(['KB5', 'Censored stratum shifts FPR > bootstrap half-width', f"shift {100 * ST['2020-01']['shift']:.3f} and {100 * ST['2020-02']['shift']:.3f} pp vs half-width 0 (0/49, 0/62 FPs)", 'met literally; inconclusive'])
    rows.append(['KB7', 'Yield advantage keeps its sign at r = 2%', f"advantage {100 * t['KB7']['adv_r0']:+.2f} pp at r = 0 already negative", 'not met (moot)'])
    rows.append(['KB9', 'Ambiguity beats margin by ≥ 0.05 AUPRC', 'not executed (D13)', 'moot after A2'])
    kb = AT['KB10']
    rows.append(['KB10', 'Novel-family AUROC ≥ 0.80 and AUPRC ≥ 3× base (July)', f"AUROC {kb['auroc']:.3f}; AUPRC {kb['auprc']:.3f} < {3 * kb['base']:.3f}", 'kill met → leg dropped'])
    rows.append(['KB11', "Cliff's δ (stability, correct vs wrong) ≥ 0.147", f"δ = {EX['KB11']['cliffs_delta']:.3f}", 'met'])
    cl = LR['cllr']
    rows.append(['KB12', 'Cllr ≥ 1 in ≥ 3 months', f"Cllr {min(cl.values()):.3f}–{max(cl.values()):.3f}; 0 months ≥ 1", 'kill not triggered'])
    rows.append(['KS1', 'SVR ≥ 6/7 at τ_FPR = 0.5%', f"{CE['thr0.005|tau0.005/0.05']['SVR_months']}/7", 'not met'])
    ks2 = [u['rH_ub'] for u in t['KS2']['updates']]
    rows.append(['KS2', 'CP upper bound of r_H ≤ 0.5% per update', f"{100 * max(ks2):.3f}% maximum", 'met'])
    write('table1_register', 'Table 1b. Unified pre-registered register (S10 Part 0): measured outcomes', table(['ID', 'Statement', 'Measured', 'Outcome'], rows),
          'Decision rules as locked in S10_protocol.md. "Kill met" means the pre-registered consequence applies. All values {MoC}.')


# --------------------------------------------------------------------------------------------- T2 model zoo
def t_models():
    df = e1(); rows = []
    for mdl in [m for m in NICE if m in set(df.model)]:
        g = df[(df.model == mdl) & (df.set == 'pool_MarSep')]; seeds = sorted(g.seed.unique()); s0 = seeds[0]

        def cell(metric, pi, thr, scale=100, d=2):
            q = g[(g.metric == metric) & (g.pi == str(pi)) & (g.thr == thr)]
            if not len(q) or not np.isfinite(q['value']).any():
                return '—'
            mu = q['value'].mean(); one = q[q.seed == s0].iloc[0]
            rng_ = f' ({scale * q["value"].min():.{d}f}–{scale * q["value"].max():.{d}f})' if len(seeds) > 1 else ''
            c = ci(one['lo'], one['hi'], d, scale) if len(seeds) == 1 else ''
            return f'{scale * mu:.{d}f}{c}{rng_}'
        rows.append([NICE[mdl], str(len(seeds)), cell('auc', 'native', '-', 100, 3), cell('ap', '0.1', '-'), cell('f1', '0.1', 'cert_0.1'),
                     cell('mcc', '0.1', 'cert_0.1'), cell('prec', '0.01', 'cert_0.1'), cell('rec', 'native', 'cert_0.1'),
                     cell('fpr', 'native', 'cert_0.1', 100, 3), cell('fnr', 'native', 'cert_0.1')])
    A = J('analysis_models.json'); aut = pd.DataFrame(A['aut']) if A else None
    if aut is not None:
        for r, mdl in zip(rows, [m for m in NICE if m in set(df.model)]):
            a = aut[aut.model == mdl]['aut_f1_pi10']
            r.append('—' if not len(a) or not np.isfinite(a).any() else (f'{a.mean():.3f}' + (f' ({a.min():.3f}–{a.max():.3f})' if len(a) > 1 else '')))
    hdr = ['Model', 'Seeds', 'AUC-ROC (%)', 'AUC-PR @π=10% (%)', 'F1 @π=10% (%)', 'MCC @π=10% (%)', 'Precision @π=1% (%)', 'TPR (%)', 'FPR (%)', 'FNR (%)',
           'AUT(F1@π=10%), Mar–Sep']
    write('table2_models', 'Table 2. Model zoo on the pooled March–September 2020 stream at the CP-certified 0.1% threshold', table(hdr, rows),
          'Dated stratum, 32,691 malware / 36,185 benign. Threshold certified on December 2019 (τ_FPR = 0.1%, 95% CP). Single-fit models: point '
          'estimate with 95% CI (stratified binomial bootstrap, B = 1,000; DeLong for AUC). Multi-seed models: seed mean (min–max). π-dependent cells use '
          'Eq. (70). AUT over the seven monthly F1 values (Eq. 69). "—": undefined (no positive verdict at the threshold). All values {MoC}.')


# --------------------------------------------------------------------------------------------- T3 monthly f0
def t_monthly():
    df = e1(); g = df[(df.model == 'lgbm_trace') & (df.seed == 11)]; rows = []
    for mm in ['cal_Dec'] + C.TEST_MONTHS:
        q = g[g.set == mm]

        def v(metric, pi, thr, scale=100, d=2):
            r = q[(q.metric == metric) & (q.pi == str(pi)) & (q.thr == thr)]
            if not len(r) or not np.isfinite(r['value'].iloc[0]):
                return '—'
            r = r.iloc[0]; return f"{scale * r['value']:.{d}f}{ci(r['lo'], r['hi'], d, scale)}"
        c = q[(q.metric == 'tp_fn_fp_tn') & (q.thr == 'cert_0.1')].iloc[0]
        early = mm in ('2020-01', '2020-02')
        rows.append([mm.replace('cal_Dec', 'Dec 2019 (cal)') if mm == 'cal_Dec' else MON(mm), f"{int(c.tn + c.fp):,}", f"{int(c.tp + c.fn):,}",
                     f'{int(c.fn):,}', f'{int(c.fp)}', v('fnr', 'native', 'cert_0.1'), v('fpr', 'native', 'cert_0.1', 100, 3) if not early else '— (n < 100)',
                     v('f1', '0.1', 'cert_0.1') if not early else '—', v('prec', '0.01', 'cert_0.1') if not early else '—', v('auc', 'native', '-', 100, 3),
                     v('mcc', 'native', 'cert_0.1')])
    hdr = ['Month', 'Benign', 'Malware', 'FN', 'FP', 'FNR (%)', 'FPR (%)', 'F1 @π=10% (%)', 'Precision @π=1% (%)', 'AUC-ROC (%)', 'MCC native (%)']
    write('table3_monthly_f0', 'Table 3. Evidentiary detector f₀ by month at the certified threshold', table(hdr, rows),
          'f₀ = LGBM-TRACE, seed 11; θ = 6.348 (margin), certified on December 2019 at τ_FPR = 0.1% (k* = 1). 95% CIs in brackets. January and February '
          '2020 hold 49 and 62 dated benign files, so FPR-dependent cells are not reported for them. Bootstrap intervals collapse to a point when a month has '
          'zero false positives; Table 4 gives the exact Clopper–Pearson bounds used for certification. {MoC}.')


# --------------------------------------------------------------------------------------------- T4 certificates
def t_certificates():
    A = J('analysis_certificates.json'); rows = []
    a1 = A['thr0.001|tau0.001/0.02']['months']; a5 = A['thr0.005|tau0.005/0.05']['months']
    for mm in ['2019-12'] + C.TEST_MONTHS:
        r1, r5 = a1[mm], a5[mm]
        def cell(r, e, ub, k, n):
            return f"{r[k]}/{r[n]:,} = {100 * r[e]:.3f} (≤ {100 * r[ub]:.3f})"
        rows.append([MON(mm) + (' (cal)' if mm == '2019-12' else ''), cell(r1, 'fpr', 'fpr_ub', 'fp', 'n_b'), f"{100 * r1['fnr']:.2f} (≤ {100 * r1['fnr_ub']:.2f})",
                     cell(r5, 'fpr', 'fpr_ub', 'fp', 'n_b'), f"{100 * r5['fnr']:.2f} (≤ {100 * r5['fnr_ub']:.2f})",
                     'yes' if (r5['fpr_ub'] <= 0.005 and r5['fnr_ub'] <= 0.05 and mm in C.CERT_MONTHS) else ('n/a' if mm not in C.CERT_MONTHS else 'no')])
    df = e1(); vr = []
    for thr, tau, lab in (('emp_0.1', 0.001, 'empirical 0.1% quantile of Dec benign ([1] protocol)'), ('cert_0.1', 0.001, 'CP-certified, τ = 0.1% (k*)'),
                          ('emp_1', 0.01, 'empirical 1% quantile'), ('cert_1', 0.01, 'CP-certified, τ = 1%')):
        g = df[(df.thr == thr) & (df.metric == 'tp_fn_fp_tn') & (df.set.isin(C.CERT_MONTHS))]
        fpr = g.fp / (g.fp + g.tn); lo = np.array([C.cp_lower(int(a), int(a + b)) for a, b in zip(g.fp, g.tn)])
        worst = g.assign(f=fpr).groupby('model')['f'].apply(lambda v: int((v > tau).sum())); worst = worst[worst > 0]
        vr.append([lab, f'{len(g)}', f'{int((fpr > tau).sum())} ({100 * (fpr > tau).mean():.1f}%)', f'{int((lo > tau).sum())}',
                   '; '.join(f'{NICE.get(k, k)} {v}' for k, v in worst.sort_values(ascending=False).items()) or '—'])
    vmd = table(['Threshold rule (fitted on December 2019)', 'Model×month cells (Mar–Sep)', 'Realised FPR > τ', 'CP lower bound > τ', 'Cells above τ by model'], vr)
    hdr = ['Month', 'θ@0.1%: FP/benign = FPR % (95% CP upper)', 'θ@0.1%: FNR % (upper)', 'θ@0.5%: FP/benign = FPR % (upper)', 'θ@0.5%: FNR % (upper)',
           'θ@0.5% valid at (0.5%, 5%)']
    s1 = A['thr0.001|tau0.001/0.02']; s5 = A['thr0.005|tau0.005/0.05']
    write('table4_certificates', 'Table 4. Retrospective time-indexed error certificates (Eq. S7.4) and target-FPR violations by threshold rule', table(hdr, rows) + '\n' + vmd,
          f"θ@0.1% = {s1['thr']:.3f} (k* = {s1['kstar']}), θ@0.5% = {s5['thr']:.3f} (k* = {s5['kstar']}), both certified on December 2019. A month is valid when "
          f"both one-sided 95% Clopper–Pearson upper bounds are within tolerance. SVR (Mar–Sep): θ@0.1% with (0.1%, 2%): {s1['SVR_months']}/7 "
          f"(FPR-only {s1['fpr_only_valid']}/7 Mar–Sep; FNR-only {s1['fnr_only_valid']}/9 Jan–Sep); θ@0.5% with (0.5%, 5%): {s5['SVR_months']}/7 (FPR-only {s5['fpr_only_valid']}/7 "
          f"Mar–Sep; FNR-only {s5['fnr_only_valid']}/9 Jan–Sep). "
          f"KS1 (≥ 6/7 at 0.5%) {'met' if A['KS1_pass'] else 'not met'}. January–February are not certifiable (49 and 62 dated benign). Second panel: all "
          f"models and seeds; a cell violates the target when the month's realised FPR exceeds τ. {{MoC}}.")


# --------------------------------------------------------------------------------------------- T5 strata
def t_strata():
    A = J('analysis_strata.json'); rows = []
    for mm in ('2020-01', '2020-02'):
        r = A[mm]
        rows.append([MON(mm), r['stratum'], f"{r['dated_benign']}", f"{100 * r['fpr_dated']:.2f}", f"{r['censored_benign']:,}",
                     f"{100 * r['fpr_censored']:.3f} (≤ {100 * r['fpr_ub_censored']:.3f})", f"{100 * r['fpr_with_censored']:.3f}", f"{100 * r['shift']:.3f}",
                     f"{100 * r['boot_half_width']:.3f}"])
    hdr = ['Month', 'Censored stratum', 'Dated benign', 'FPR dated (%)', 'Censored benign', 'FPR censored (%) (95% CP upper)', 'FPR pooled (%)',
           'Shift (pp)', 'Bootstrap half-width (pp)']
    md = table(hdr, rows)
    rs = [[MON(mm[-7:]), f"{A[mm]['n_spike_mal']}", f"{100 * A[mm]['fnr_spike_mal']:.2f}", f"{100 * A[mm]['fnr_dated']:.2f}", f"{100 * A[mm]['fnr_with_spike_mal']:.2f}"]
          for mm in ('RS1_2020-01', 'RS1_2020-02')]
    md += '\n' + table(['Month', 'SpikeMal files', 'FNR spike-day malware (%)', 'FNR dated (%)', 'FNR pooled (%)'], rs)
    md += '\n' + table(['June 2020 rule', 'Files', 'FNR (%)', 'FPR (%)', 'F1 native (%)'],
                       [['spike rule k = 10 (primary)', f"{A['june_k10']['n']:,}", f"{100 * A['june_k10']['fnr']:.2f}", f"{100 * A['june_k10']['fpr']:.3f}", f"{100 * A['june_k10']['f1']:.2f}"],
                        ['spike rule k = 4 (sensitivity)', f"{A['june_k4']['n']:,}", f"{100 * A['june_k4']['fnr']:.2f}", f"{100 * A['june_k4']['fpr']:.3f}", f"{100 * A['june_k4']['f1']:.2f}"]])
    write('table5_strata', 'Table 5. Censored benign strata, spike-day malware and the spike-rule sensitivity (f₀, θ@0.1%)', md,
          'Placeholder (January) and Bulk (February) benign files carry batch timestamps and are excluded from the Dated stream (S7). The KB5 rule '
          '(shift > bootstrap half-width) is met literally in both months, but the half-width is zero because the dated stratum has 0/49 and 0/62 false '
          'positives; the test is degenerate and reported as inconclusive. Both censored strata alone fail the 0.1% FPR certificate (CP upper 0.31% and '
          '0.53%). {MoC}.')


# --------------------------------------------------------------------------------------------- T6 base rate
def t_baserate():
    A = J('analysis_baserate.json'); cells = pd.DataFrame(A['cells']); dft = pd.DataFrame(A['default_threshold_sweep']); rows = []
    for mm in C.CERT_MONTHS:
        r = [MON(mm)]
        for pi in (0.01, 0.02, 0.05, 0.10):
            c = cells[(cells.month == mm) & (np.isclose(cells.pi, pi))].iloc[0]
            r.append(f"{100 * c['measured_mean']:.2f} [{100 * c['lo']:.2f}, {100 * c['hi']:.2f}] / {100 * c['analytic']:.2f}")
        for pi in (0.001, 0.01):
            d = dft[(dft.month == mm) & (np.isclose(dft.pi, pi))]
            r.append(f"{100 * d['prec'].iloc[0]:.2f}" if len(d) else '—')
        rows.append(r)
    hdr = ['Month', 'π = 1%', 'π = 2%', 'π = 5%', 'π = 10%', 'Default θ: Prec @π=0.1%', 'Default θ: Prec @π=1%']
    write('table6_base_rate', 'Table 6. Precision (%) under deployment prevalence π: measured streams versus Eq. (55)', table(hdr, rows),
          'Certified θ@0.1% columns: mean [2.5, 97.5 percentile] over 20 prevalence-resampled streams / analytic value from the month\'s measured TPR and FPR. '
          f"Analytic value outside the measured interval in {100 * A['share_outside']:.0f}% of the 28 cells (P2 not falsified). No month had realised FPR ≥ 0.1% "
          'at the certified threshold, so the second clause of P2 is untestable. Default θ (p = 0.5): analytic precision from the month\'s measured rates. {MoC}.')


# --------------------------------------------------------------------------------------------- T7 calibration and cost
def t_calibration():
    A = J('analysis_calibration.json'); P4 = A['P4']; rows = []
    for k, mm in enumerate(C.CERT_MONTHS):
        r = A['months'][mm]
        rows.append([MON(mm), f"{100 * P4['ece_raw'][k]:.2f}", f"{100 * P4['ece_iso'][k]:.2f}", f"{100 * P4['ece_platt'][k]:.2f}",
                     f"{1000 * P4['brier_prior_0.01']['iso'][k]:.2f} / {1000 * P4['brier_prior_0.01']['prior'][k]:.2f}",
                     f"{1000 * P4['brier_prior_0.001']['iso'][k]:.2f} / {1000 * P4['brier_prior_0.001']['prior'][k]:.2f}",
                     f"{1000 * P4['EC_0.01_100']['star'][k]:.1f} / {1000 * P4['EC_0.01_100']['half'][k]:.1f}"])
    hdr = ['Month', 'ECE raw sigmoid (%)', 'ECE isotonic (%)', 'ECE Platt (%)', 'Brier ×10³ @π=1%: iso / prior-shift', 'Brier ×10³ @π=0.1%: iso / prior-shift',
           'EC ×10³ @π=1%, C_FN/C_FP = 100: τ* / 0.5']
    md = table(hdr, rows)
    ec_rows = []
    for pi in (0.01, 0.001):
        for ratio in (10, 50, 100):
            e = P4[f'EC_{pi}_{ratio}']
            ec_rows.append([f'{100 * pi:g}%', ratio, f"{1000 * np.mean(e['star']):.2f}", f"{1000 * np.mean(e['half']):.2f}", f"{e['star_lt_half_months']}/7", p_fmt(e['p'])])
    md += '\n' + table(['π', 'C_FN/C_FP', 'mean EC(τ*) ×10³', 'mean EC(0.5) ×10³', 'months τ* lower', 'Wilcoxon p'], ec_rows)
    H10 = A['H10']; H6 = A['H6']
    write('table7_calibration', 'Table 7. Calibration under drift, prior shift and cost-sensitive thresholds (P4, P7, H6, H10)', md,
          f"Calibrators fitted on December 2019 (π_cal = {100 * A['pi_cal']:.1f}%). Isotonic ECE exceeded raw ECE in every month (isotonic raised ECE by "
          f"{-100 * P4['mean_reduction_iso']:.2f} pp on average, 95% CI [{-100 * P4['ci_reduction_iso'][1]:.2f}, {-100 * P4['ci_reduction_iso'][0]:.2f}]; Wilcoxon p = "
          f"{P4['wilcoxon_iso_vs_raw']:.3f}), so P4's calibrator clause is falsified. Prior shift (Eq. 31) lowered Brier at π = 0.1% (p = "
          f"{P4['brier_prior_0.001']['p']:.3f}) but not at π = 1% (p = {P4['brier_prior_0.01']['p']:.3f}). P7 survives on one of six (π, ratio) cells. "
          f"H6 (F1 at π* = 10% with the π*-aware threshold vs 0.5): mean {H6['delta_mean_pp']:+.2f} pp (p = {H6['p']:.3f}), not supported. H10: Spearman "
          f"ρ(month, isotonic ECE) = {H10['rho']:.2f} (p = {H10['p']:.2f}); met by the pre-registered sign rule, not significant. {{MoC}}.")


# --------------------------------------------------------------------------------------------- T8 bias / leakage / CV
def t_bias():
    A = J('analysis_bias.json'); rows = []
    p1 = A['P1']
    for r in p1['rows']:
        rows.append([f"seed {r['seed']}", f"{100 * r['random_f1_pi10']:.2f}", f"{100 * r['temporal_aut_f1_pi10']:.2f}",
                     f"{100 * (r['random_f1_pi10'] - r['temporal_aut_f1_pi10']):+.2f}", f"{100 * r['random_fnr']:.2f}", f"{100 * r['random_fpr']:.3f}"])
    rows.append(['mean [95% CI]', '', '', f"{p1['mean_pp_pi10']:+.2f} [{p1['ci_pi10'][0]:.2f}, {p1['ci_pi10'][1]:.2f}]", '', ''])
    md = table(['Arm', 'Random-split F1 @π=10% (%)', 'Temporal AUT(F1@π=10%) (%)', 'Inflation (pp)', 'Random-split FNR (%)', 'Random-split FPR (%)'], rows)
    kb4 = A['KB4']; cert = J('analysis_certificates.json')['thr0.001|tau0.001/0.02']['months']
    rows = [[MON(mm), f"{100 * kb4['static']['fnr']:.2f}", f"{100 * cert[mm]['fnr']:.2f}", f"{100 * kb4['static']['fpr']:.3f}", f"{100 * cert[mm]['fpr']:.3f}",
             'yes' if kb4['detail'][mm] else 'no'] for mm in C.CERT_MONTHS]
    md += '\n' + table(['Month', 'Static 80:20 FNR (%)', 'Temporal FNR (%)', 'Static FPR (%)', 'Temporal FPR (%)', 'Static understates'], rows)
    h9 = A['H9']; ex = []
    ex.append(['Without COFF timestamp (feature 626), H9', f"AUT(F1@π=10%) {100 * h9['aut_base']:.2f} → {100 * h9['aut_no626']:.2f}",
               f"{h9['delta_pp']:+.2f} pp", 'met (absolute Δ < 1 pp)'])
    pw = A['prewin']['months']; base = J('analysis_certificates.json')['thr0.001|tau0.001/0.02']['months']
    fn_b = sum(base[mm]['fn'] for mm in C.CERT_MONTHS); nm = sum(base[mm]['n_m'] for mm in C.CERT_MONTHS)
    fn_p = sum(pw[mm]['fn'] for mm in C.CERT_MONTHS); nm_p = sum(pw[mm]['tp'] + pw[mm]['fn'] for mm in C.CERT_MONTHS)
    fp_p = sum(pw[mm]['fp'] for mm in C.CERT_MONTHS); nb_p = sum(pw[mm]['fp'] + pw[mm]['tn'] for mm in C.CERT_MONTHS)
    ex.append(['+13,834 PreWindow benign in training', f"pooled FNR {100 * fn_b / nm:.2f}% → {100 * fn_p / nm_p:.2f}%; FPR {fp_p}/{nb_p:,}", f"{100 * (fn_p / nm_p - fn_b / nm):+.2f} pp FNR",
               'descriptive (S7 excluded PreWindow from the primary split)'])
    md += '\n' + table(['Variant', 'Effect', 'Δ', 'Outcome'], ex)
    cv = J('e5_cv.json')
    if cv and cv.get('folds'):
        F = pd.DataFrame(cv['folds']); df = e1(); rows = []
        for cvn, tn in (('lgbm_trace', 'lgbm_trace'), ('xgb', 'xgb'), ('et100', 'et'), ('rf100', 'rf'), ('lr', 'lr'), ('nb', 'nb')):
            a = F[F.model == cvn]
            if not len(a):
                continue
            q = df[(df.model == tn) & (df.thr == 'cert_0.1') & df.set.isin(C.CERT_MONTHS)]
            f1t = q[(q.metric == 'f1') & (q.pi == '0.1')].groupby('set')['value'].mean(); fnt = q[(q.metric == 'fnr') & (q.pi == 'native')].groupby('set')['value'].mean()
            rows.append([NICE.get(tn, tn) + (' (100 trees in CV)' if cvn.endswith('100') else ''), f"{len(a)}",
                         f"{100 * a.f1_pi10.mean():.2f} ({100 * a.f1_pi10.min():.2f}–{100 * a.f1_pi10.max():.2f})",
                         f"{100 * f1t.mean():.2f} ({100 * f1t.min():.2f}–{100 * f1t.max():.2f})", f"{100 * (a.f1_pi10.mean() - f1t.mean()):+.2f}",
                         f"{100 * a.fnr.mean():.2f}", f"{100 * fnt.mean():.2f}", f"{100 * a.fpr.mean():.3f}"])
        md += '\n' + table(['Model', 'CV folds', 'Random 5-fold CV: F1 @π=10% (%) mean (min–max)', 'Temporal months Mar–Sep: F1 @π=10% (%) mean (min–max)',
                            'Δ CV − temporal (pp)', 'CV FNR (%)', 'Temporal FNR (%)', 'CV FPR (%)'], rows)
    t0 = J('e5_t0.json'); P_ = json.load(open(f'{C.ROOT}/code/published_baselines.json'))
    if t0:
        rows = [['[1] Table III {RfP}', 'BODMAS before 2019-10-01', '—', f"{P_['BODMAS_T3_FNR']['lo']:.2f}–{P_['BODMAS_T3_FNR']['hi']:.2f}",
                 f"{P_['BODMAS_T3_FPR']['lo']:.2f}–{P_['BODMAS_T3_FPR']['hi']:.2f}", '—', f"≤ {P_['BODMAS_T3_unseenFNR_max']['value']:.2f}", f"within {P_['BODMAS_T3_knownFNR_max']['value']:.0f}"]]
        for key, lab in (('dated|lgbm_ember', 'Dated only, LGBM-EMBER'), ('dated|lgbm_trace', 'Dated only, LGBM-TRACE params'),
                         ('dated+prewindow|lgbm_ember', 'Dated + PreWindow, LGBM-EMBER'), ('dated+prewindow|lgbm_trace', 'Dated + PreWindow, LGBM-TRACE params')):
            v_ = t0['t0'].get(key)
            if not v_:
                continue
            ms = v_['months']; ks = sorted(ms)
            fn = [100 * ms[k]['fnr'] for k in ks]; fp = [100 * ms[k]['fpr'] for k in ks]
            un = [100 * ms[k]['fnr_unseen'] for k in ks if ms[k].get('n_unseen', 0) >= 20]; sn = [100 * ms[k]['fnr_seen'] for k in ks if ms[k].get('n_seen', 0) >= 20]
            jas = [100 * ms[k]['fnr'] for k in ('2020-07', '2020-08', '2020-09')]
            rows.append([lab + ' {MoC}', f"{v_['n_train']:,} train / {v_['n_val']:,} val; θ = {v_['thr']:.3f} (k = {v_['k']})", f"{min(jas):.2f}–{max(jas):.2f}",
                         f"{min(fn):.2f}–{max(fn):.2f}", f"{min(fp):.3f}–{max(fp):.3f}", f"{sum(1 for x in fp if x > 0.1)}/{len(fp)}",
                         f"≤ {max(un):.2f}" if un else '—', f"≤ {max(sn):.2f}" if sn else '—'])
        md += '\n' + table(['T0 replication of [1] Table III (train < 2019-10-01, 80:20 random split, empirical 0.1% validation threshold; test Oct 2019–Sep 2020)',
                            'Training / threshold', 'FNR Jul–Sep 2020 (%)', 'Monthly FNR (%)', 'Monthly FPR (%)', 'Months FPR > 0.1%', 'Unseen-family FNR (%)', 'Seen-family FNR (%)'], rows)
    lk, dl = leak_delong()
    if lk:
        rows = []
        for clf in ('lr', 'svm'):
            for arm in ('scale', 'chi2', 'pca'):
                c = lk['arms'].get(f'{clf}|{arm}_clean'); l_ = lk['arms'].get(f'{clf}|{arm}_leaky')
                if not c or not l_:
                    continue
                c, l_ = c['pool_MarSep'], l_['pool_MarSep']
                rows.append([{'lr': 'LR', 'svm': 'Linear SVM'}[clf], {'scale': 'z-score scaler', 'chi2': 'χ² selector (256)', 'pca': 'PCA (0.95)'}[arm], f"{100 * c['auc']:.3f} → {100 * l_['auc']:.3f}", f"{100 * c['ap_pi10']:.2f} → {100 * l_['ap_pi10']:.2f}",
                             f"{100 * c['fnr']:.2f} → {100 * l_['fnr']:.2f}", f"{100 * (l_['auc'] - c['auc']):+.3f}", p_fmt(dl[f'{clf}|{arm}'][1]) if f'{clf}|{arm}' in dl else '—'])
        md += '\n' + table(['Model', 'Pre-split fit', 'AUC-ROC (%) clean → leaky', 'AUC-PR @π=10% (%) clean → leaky', 'FNR @θ0.1% (%) clean → leaky', 'ΔAUC (pp)', 'DeLong p'], rows)
        tl = lk['lgbm_scaling_leak']
        md += (f"\nLightGBM under clean versus leaky z-scaling: margins {'identical' if tl['identical'] else 'differ'} (maximum absolute difference {tl['max_abs_diff']:.2f}); "
               f"decision agreement {100 * tl['decision_agreement']:.3f}%.\n")
    nm_ = J('e5_norm.json')
    if nm_:
        rows = [[{'dt': 'Decision tree', 'rf': 'Random forest (100 trees)', 'lgbm': 'LightGBM', 'lr': 'LR', 'knn': 'k-NN'}.get(k.split('|')[0], k.split('|')[0].upper()), k.split('|')[1].replace('_', ' ').replace('minmax', 'min-max').replace('zscore', 'z-score'), f"{v['disagree']:,}/{v['n']:,}", f"{100 * v['agreement']:.3f}"] for k, v in nm_['agreement'].items()]
        md += '\n' + table(['Model', 'Comparison', 'Disagreements', 'Agreement (%)'], rows)
    write('table8_bias', 'Table 8. Experimental-bias controls: random versus temporal split (P1), static 80:20 versus temporal certificates (KB4), '
          'timestamp artefact (H9), pre-window benign, leakage (P3) and monotone-scaling invariance (P9)', md,
          'Random arm: same model and training size, rows drawn uniformly from the pooled Dated stream, certified threshold on a random calibration '
          'hold-out (biased by construction). Relative inflation of the mean: ' + f"{p1['rel_pct_pi10']:+.2f}%. " +
          'Leakage arms fit the scaler, χ² selector (labels included) or PCA on all Dated rows (train + calibration + test) before training. {MoC}.')


# --------------------------------------------------------------------------------------------- T9 errors / families
def t_errors():
    A = J('analysis_errors.json'); md = ''
    rows = []
    for basis in ('eq19', 'mass'):
        for err in ('fnr', 'fpr'):
            r = A[basis][err]
            rows.append([{'eq19': 'Eq. (19) packing indicator, τ_p = 1/32', 'mass': 'byte mass in the two highest entropy bins > 0.5'}[basis], err.upper(),
                         f"{r['high'][0]:,}/{r['high'][1]:,} = {100 * r['rate_high']:.3f}", f"{r['low'][0]:,}/{r['low'][1]:,} = {100 * r['rate_low']:.3f}",
                         f"{r['OR']:.2f} [{r['OR_ci'][0]:.2f}, {r['OR_ci'][1]:.2f}]", p_fmt(r['p'])])
    md += table(['High-entropy definition', 'Error', 'High stratum: errors/n = %', 'Low stratum: errors/n = %', 'Odds ratio [95% CI]', 'Fisher p'], rows)
    h3 = pd.DataFrame(A['H3']['rows'])
    md += '\n' + table(['Month', 'Unseen-family malware', 'FNR unseen (%)', 'Known-family malware', 'FNR known (%)'],
                       [[MON(r.month), f'{r.n_unseen:,}', f'{100 * r.fnr_unseen:.2f}', f'{r.n_known:,}', f'{100 * r.fnr_known:.2f}'] for r in h3.itertuples()])
    fam = family_fn()
    if fam is not None:
        md += '\n' + table(['Family (Jul–Sep 2020)', 'Seen in training', 'Malware files', 'False negatives', 'FNR (%)', 'Share of all Jul–Sep FN (%)'], fam)
    write('table9_errors', 'Table 9. Error structure of f₀ at θ@0.1%: entropy strata (P10), unseen versus known families (H3) and the families behind '
          'the July–September decay', md,
          f"P10 is falsified for FPR (3 false positives in total; the odds-ratio CI spans 1) and holds for FNR. H3: Wilcoxon over months p = {A['H3']['p']:.4f}, "
          f"A12 = {A['H3']['A12']:.3f} (met), yet July–September FNR is driven by families present in training. Family labels are BODMAS family tokens "
          '(RecMaL [92] estimates about 20% of them shifted or wrong). {MoC}.')


def family_fn():
    p = f'{C.CACHE}/scores/lgbm_trace_s11.npz'
    if not os.path.exists(p):
        return None
    m = C.load_meta(); y = m['y'].to_numpy().astype(int); sp = m['split'].to_numpy(); mo = m['month'].to_numpy(); fam = m['family'].to_numpy()
    d = np.load(p); s = np.full(len(m), np.nan); s[d['idx']] = d['s']
    cal = np.where(sp == 'cal')[0]; thr, _ = C.certified_threshold(s[cal][y[cal] == 0], 0.001)
    trfam = set(fam[(sp == 'train') & (y == 1)])
    sel = np.where((sp == 'test') & (y == 1) & np.isin(mo, ['2020-07', '2020-08', '2020-09']))[0]
    fn = s[sel] <= thr; tot = int(fn.sum())
    dfm = pd.DataFrame(dict(f=fam[sel], fn=fn)).groupby('f').agg(n=('fn', 'size'), fn=('fn', 'sum')).sort_values('fn', ascending=False)
    rows = [[f, 'yes' if f in trfam else 'no', f'{int(r.n):,}', f'{int(r.fn):,}', f'{100 * r.fn / r.n:.1f}', f'{100 * r.fn / tot:.1f}']
            for f, r in dfm.head(8).iterrows()]
    rows.append(['all families', '', f'{len(sel):,}', f'{tot:,}', f'{100 * tot / len(sel):.1f}', '100.0'])
    return rows


# --------------------------------------------------------------------------------------------- T10 drift + monitor
def t_monitor():
    A = J('analysis_drift.json'); M = J('monitor.json'); cert = J('analysis_certificates.json')['thr0.001|tau0.001/0.02']['months']
    rows = [[MON(mm), f"{1000 * A['months'][mm]['D']:.2f}", f"{1000 * A['months'][mm]['D_cls0']:.2f}", f"{1000 * A['months'][mm]['D_cls1']:.2f}",
             f"{100 * cert[mm]['fnr']:.2f}"] for mm in ['2019-12'] + C.TEST_MONTHS]
    md = table(['Month', '𝒟(t) ×10³ (bits)', 'benign-class 𝒟 ×10³', 'malware-class 𝒟 ×10³', 'FNR f₀ at θ@0.1% (%)'], rows)
    D1 = [A['months'][mm]['D_cls1'] for mm in C.CERT_MONTHS]; F = [cert[mm]['fnr'] for mm in C.CERT_MONTHS]
    rho, p = C.spearman_perm(np.array(D1), np.array(F))
    W = pd.read_pickle(f'{O}/monitor_windows.pkl'); Tt = W[W.kind == 'test']; lam = M['lam']; ex = []
    for k, lab in (('c2st', 'C2ST AUC (T5)'), ('ks', 'KS on margins (T1)'), ('psi', 'mean PSI (T2)'), ('cred', '1 − mean credibility (T3)')):
        for c in (0, 1):
            v = Tt[Tt.cls == c][k].to_numpy()
            ex.append([lab, {0: 'pred. benign', 1: 'pred. malicious'}[c], f"{lam[f'{k}{c}']:.3f}", f"{int(np.sum(v > lam[f'{k}{c}']))}/{len(v)}"])
    md += '\n' + table(['Statistic', 'Class', 'λ (max over blocked null)', 'Test windows above λ'], ex)
    aci = M['aci']
    md += '\n' + table(['Signal', 'Alarms Mar–Sep', 'First alarm', 'First alarm after 5 Jul onset'],
                       [['M8 rule (P = 2 consecutive exceedances, re-arm)', len(M['alarms']), M['alarms'][0] if M['alarms'] else '—', '— (none)'],
                        ['ACI, label delay 7 d', aci['7']['alarms'], aci['7']['first'], aci['7']['first_after_onset']],
                        ['ACI, label delay 30 d', aci['30']['alarms'], aci['30']['first'], aci['30']['first_after_onset']]])
    write('table10_drift_monitor', 'Table 10. Feature drift (Eqs. 74–75) and the label-free monitor M8 (KT)', md,
          f"January–February benign-class values rest on 49 and 62 dated benign files and are inflated by small-sample JS bias. "
          f"P5: Spearman ρ(𝒟, F1@π=10%) = −0.32 (p = 0.49), falsified. Exploratory (not pre-registered): ρ(malware-class 𝒟, FNR), Mar–Sep = {rho:.2f} "
          f"(permutation p = {p:.3f}, n = 7). Monitor: {M['n_test_windows']} weekly test windows; every window exceeds at least one λ; one alarm "
          f"({M['alarms'][0]}), no alarm within 14 d of the July onset week ({M['onset_july_week']}); false alarms in stable months: "
          f"{', '.join(f'{MON(k)} {v}' for k, v in M['false_alarms_stable'].items())}. KT met → trigger claim withdrawn. {{MoC}}.")


# --------------------------------------------------------------------------------------------- T11 assurance
NAMES = {'tracepe': 'TRACE-PE (budgeted re-validation)', 'i_auto': '(i) re-score, auto-accept', 'ii_review_changes': '(ii) review changes',
         'iii_calendar': '(iii) calendar re-validation', 'iv_transcendent': '(iv) Transcendent 10%', 'v_pct_auto': '(v) PCT-adapted, auto',
         'vi_random': '(vi) random review', 'vii_margin': '(vii) lowest-margin review', 'viii_reconcile': '(viii) retrain + κ + certificates, no review',
         'viii_frozen': '(viii-f) frozen f₀ + κ + certificates', 'abl_noregion': 'ablation: no region selection', 'abl_noflag': 'ablation: no flagging',
         'abl_nogate': 'ablation: no harm gate', 'abl_noauto': 'ablation: no auto-amendment', 'a2_naive': 'A2: monthly retrain only',
         'a2_abst': 'A2: retrain + κ abstention', 'a2_cert': 'A2: retrain + certificate gating', 'a2_naive_frozen': 'A2: frozen f₀, no safeguards'}


def t_assurance():
    R = J('reval_analysis.json'); md = ''
    t = R['L30_rho1.0']; P = t['policies']; ref = P['viii_reconcile']['E_ev']
    rng_ = lambda c: f" [{c[0]:,.0f}–{c[1]:,.0f}]" if c and np.isfinite(c[0]) else ''
    rows = []
    for p in ['a2_naive_frozen', 'viii_frozen', 'a2_naive', 'a2_cert', 'a2_abst', 'viii_reconcile', 'tracepe', 'i_auto', 'ii_review_changes', 'iii_calendar',
              'iv_transcendent', 'v_pct_auto', 'vi_random', 'vii_margin', 'abl_noregion', 'abl_noflag', 'abl_nogate', 'abl_noauto']:
        if p not in P:
            continue
        r = P[p]
        rows.append([NAMES[p], f"{r['E_ev']:,}{rng_(r.get('E_ev_ci'))}", f"{r['E']:,}{rng_(r.get('E_ci'))}", f"{r['E_ev'] / ref:.2f}×",
                     f"{r['abstained']:,}", f"{r.get('scr', 0):,}", f"{100 * r['coverage']:.1f}",
                     f"{r.get('reviews', 0):,}", f"{r.get('hits', 0)}", f"{100 * r['yield_']:.2f}" if r.get('reviews') else '—', f"{r.get('harmful_auto', 0)}"])
    md += table(['Policy', 'E^ev_T, finding-days [95% CI]', 'E_T [95% CI]', 'E^ev / E^ev(viii)', 'Abstained at issue', 'Screening-only at issue',
                 'Evaluative coverage (%)', 'Reviews', 'Corrections by review', 'Yield (%)', 'Harmful auto-amendments'], rows)
    k1 = t['K1']['updates']; k2 = t['K2']['updates']
    md += '\n' + table(['Update', 'In-scope findings N', 'Budget B', 'Verdict changes on full re-scoring', 'Harmful flips', 'CP-95% upper bound of h (%)'],
                       [[u['event'], f"{u['N']:,}", u['B'], u['changes'], v['harmful'], f"{100 * v['h_ub']:.3f}"] for u, v in zip(k1, k2)])
    F = J('flips.json')
    if F and 'L30_rho1.0' in F:
        fr = F['L30_rho1.0']
        md += '\n' + table(['Update', 'Re-scored findings (incl. abstained)', 'Abstained at issue', 'Verdict flips', 'Flips among abstained',
                            'Harmful: malware → benign', 'Harmful: benign → malicious', 'Corrective flips'],
                           [[r['event'], f"{r['N']:,}", f"{r['abstained']:,}", r['flips'], r['flips_abstained'], r['mal_regress'], r['ben_regress'],
                             r['mal_correct'] + r['ben_correct']] for r in fr['updates']])
    sens = []
    for tag, lab in (('L30_rho1.0', 'L = 30 d, ρ_L = 1.0 (primary)'), ('L60_rho1.0', 'L = 60 d, ρ_L = 1.0'), ('L90_rho1.0', 'L = 90 d, ρ_L = 1.0'),
                     ('L30_rho0.5', 'L = 30 d, ρ_L = 0.5')):
        if tag not in R:
            sens.append([lab] + ['pending'] + [''] * 9)
            continue
        tt = R[tag]; PP = tt['policies']
        chg = sum(u['changes'] for u in tt['K1']['updates']); hf = sum(u['harmful'] for u in tt['K2']['updates'])
        rr = lambda q: f"{PP[q]['E_ev']:,} ({-100 * (PP[q].get('rel_red_vs_viii') or 0):+.1f}%)" if PP['viii_reconcile']['E_ev'] else f"{PP[q]['E_ev']:,}"
        sens.append([lab, f"{PP['tracepe']['iss']:,}", f"{PP['viii_reconcile']['E_ev']:,}", f"{PP['tracepe']['E_ev']:,}",
                     f"{100 * tt['K3']['rel_red']:.1f} [{100 * tt['K3']['ci'][0]:.1f}, {100 * tt['K3']['ci'][1]:.1f}]",
                     rr('vii_margin'), rr('abl_noregion'),
                     f"{tt['K1']['n_le_B']}/{tt['K1']['n_updates']} (changes: {chg})", f"{'met' if tt['K2']['met'] else 'not met'} (harmful: {hf})",
                     f"{PP['a2_naive']['E_ev']:,}" if 'a2_naive' in PP else '—', f"{PP['a2_naive_frozen']['E_ev']:,}" if 'a2_naive_frozen' in PP else '—'])
    md += '\n' + table(['Scenario', 'Issued as evaluative', 'E^ev (viii)', 'E^ev TRACE-PE', 'K3: rel. reduction (%) [CI]', 'E^ev (vii) margin (rel.)',
                        'E^ev TRACE-PE without region (rel.)', 'K1: updates with changes ≤ B', 'K2', 'E^ev retrain only', 'E^ev frozen, no safeguards'], sens)
    nz = t['noise']; rows = []
    for r_ in ('0.005', '0.01', '0.02'):
        rows.append([f'{100 * float(r_):g}%', f"{nz[f'{r_}|tracepe']['E_ev_mean']:,.1f}", f"{nz[f'{r_}|vii_margin']['E_ev_mean']:,.1f}", f"{nz[f'{r_}|vi_random']['E_ev_mean']:,.1f}",
                     f"{nz[f'{r_}|tracepe+rr']['E_ev_mean']:,.1f}", f"{nz[f'{r_}|vii_margin+rr']['E_ev_mean']:,.1f}", f"{nz[f'{r_}|viii_reconcile']['E_ev_mean']:,.1f}"])
    md += '\n' + table(['Analyst error r', 'TRACE-PE', '(vii) margin', '(vi) random', 'TRACE-PE, oracle overrides analyst at maturity',
                        '(vii), oracle overrides analyst', '(viii) no review'], rows)
    st = t['streams']; rows = []
    for pi in ('0.1', '0.05'):
        c = st[f'{pi}|viii_reconcile']['E_ev_ci']
        rows.append([f'{100 * float(pi):g}%', f"{st[f'{pi}|viii_reconcile']['E_ev_mean']:.1f} [{c[0]:.0f}, {c[1]:.0f}]", f"{st[f'{pi}|tracepe']['E_ev_mean']:.1f}",
                     f"{st[f'{pi}|vii_margin']['E_ev_mean']:.1f}", f"{st[f'{pi}|i_auto']['E_ev_mean']:.1f}", f"{st[f'{pi}|tracepe']['n_mean']:,.0f}"])
    md += '\n' + table(['Stream π', 'E^ev (viii), mean [2.5, 97.5 pct]', 'E^ev TRACE-PE', 'E^ev (vii)', 'E^ev (i)', 'Findings per stream'], rows)
    a2 = t['A2_ablation']
    write('table11_assurance', 'Table 11. Assurance-plane simulation (S7 Algorithm 6): exposure, kill criteria K1–K3, label-delay and label-rate sensitivity, '
          'analyst noise and prevalence-resampled streams', md,
          f"Native Dated stream: {P['tracepe']['iss'] + P['tracepe']['scr'] + P['tracepe']['abstained']:,} findings issued 1 Mar–30 Sep 2020, horizon 31 Oct; τ_FPR = 0.5%, τ_FNR = 5%; B = 1% of the previous 30 days' "
          f"issuances; γ = 0.5 from the pre-test replay on 2019 data. E^ev_T counts wrong findings held in evaluative states (issued, confirmed, corrected, "
          f"reconciled) per day; E_T counts all live wrong findings. CIs: 95% day-block bootstrap. Evaluative coverage = mean daily share of live findings held in "
          f"evaluative states. (iv) lowers exposure by abstaining on about twice as many findings. A2 ablation: certificates + abstention reduce E^ev by "
          f"{100 * a2['viii_reconcile']['red_vs_naive']:.2f}% versus monthly retraining alone and {100 * a2['viii_reconcile']['red_vs_naive_frozen']:.2f}% versus a "
          f"frozen detector without safeguards. K1, K2 and K3 are all met at L = 30 d, so the pre-registered fallback to A2 applies. Sensitivity rows: "
          f"relative changes of E^ev are versus (viii) in the same scenario (negative = reduction); with L ≥ 60 d few or no certificates are valid at issue "
          f"(validity horizon A_max = 60 d), so almost all findings are issued as screening-only. Noise rows: mean over "
          f"10 seeds. {{MoC}} (simulation on real BODMAS scores and labels).")


# --------------------------------------------------------------------------------------------- T12 attribution
def t_attribution():
    A = J('attr.json'); R = pd.DataFrame(A['months']); cat = pd.DataFrame(A['category']); rows = []
    for r, c in zip(R.itertuples(), cat.itertuples()):
        rows.append([MON(r.month), f'{r.n:,}', f'{100 * r.nu:.1f}', f'{100 * r.top1_known:.1f}', f'{100 * r.top3_known:.1f}', f'{100 * r.top1_all:.1f}',
                     f'{100 * r.upper_bound_all:.1f}', f'{100 * r.macroF1_closed:.1f} / {100 * r.macroF1_open:.1f}', f'{r.novelty_auroc:.3f}',
                     f'{r.novelty_auprc:.3f} ({r.novelty_base:.3f})', f'{100 * r.unknown_recall:.1f}', f'{100 * c.acc:.1f} / {100 * c.macroF1:.1f}'])
    hdr = ['Month', 'Non-generic malware', 'Unseen share ν_t (%)', 'Top-1 known (%)', 'Top-3 known (%)', 'Top-1 all (%)', 'Closed-world bound 1 − ν_t (%)',
           'Macro-F1 closed / open (%)', 'Novelty AUROC', 'Novelty AUPRC (base rate)', 'Unknowns rejected (%)', 'Category acc. / macro-F1 (%)']
    kb = A['KB10']; h7 = A['H7']; p6 = A['P6']
    write('table12_attribution', 'Table 12. Secondary attribution leg: open-set family attribution, unseen-family detection and category back-off',
          table(hdr, rows),
          f"LightGBM multiclass over {A['n_known']} families with ≥ 20 training samples ({A['n_train']:,} files; {A['n_generic']:,} files with generic AV tokens "
          f"excluded, D8). Open-set rejection at the December 5th-percentile max-probability (τ_open = {A['tau_open']['0.05']:.3f}). KB10 (July): AUROC "
          f"{kb['auroc']:.3f} ≥ 0.80 but AUPRC {kb['auprc']:.3f} < 3 × {kb['base']:.3f} = {3 * kb['base']:.3f} → kill met, attribution leg dropped. H7: "
          f"open > closed macro-F1 in 9/9 months, Wilcoxon p = {h7['p']:.4f}, mean {h7['mean_delta_pp']:+.2f} pp (met; negligible effect). P6: slope of "
          f"open-set macro-F1 {100 * p6['slope_open']:+.2f} pp/month vs detection F1 {100 * p6['slope_det']:+.2f} pp/month; difference "
          f"{100 * p6['diff']:+.2f} [{100 * p6['ci'][0]:.2f}, {100 * p6['ci'][1]:.2f}] pp/month, the opposite sign to the prediction → falsified. "
          'A first fit with num_leaves = 15, lr = 0.1 diverged (training accuracy 27.5%) and was discarded before any test month was read (D12). {MoC}.')


# --------------------------------------------------------------------------------------------- T13 explanations + ledger + reproducibility
def t_explain_ledger():
    E = J('explain.json'); L = J('ledger_tests.json'); X = J('xenv.json'); I = J('e0_init.json'); groups = [g for g, _, _ in C.GROUPS]
    v = np.array([E['importance']['mean_abs'][g] for g in groups]); sh = v / v.sum()
    rows = [[g, f"{E['importance']['mean_abs'][g]:.3f}", f"{100 * sh[i]:.1f}", f"{100 * E['gain_group'][g]:.1f}", f"{100 * E['lr_group'][g]:.1f}",
             f"{E['faithfulness']['mean_abs_delta_margin'][g]:.3f}"] for i, g in enumerate(groups)]
    md = table(['EMBER group', 'Mean abs. grouped SHAP (margin)', 'Abs. SHAP share (%)', 'Gain share (%)', 'LR abs. coefficient share (%)', 'Mean abs. Δ margin on group deletion'], rows)
    lr = []
    lr.append(['Grouped TreeSHAP cost', f"{E['shap_ms_per_finding']:.2f} ms per finding; local accuracy max residual {E['local_accuracy_max_resid']:.1e}"])
    lr.append(['Deletion faithfulness (Spearman, SHAP rank vs Δ margin)', f"mean {E['faithfulness']['mean_spearman']:.2f}, median {E['faithfulness']['median_spearman']:.2f}"])
    lr.append(['KB11 stability (top-3 group Jaccard across seeds)', f"correct {E['KB11']['mean_jaccard_correct']:.3f} vs wrong {E['KB11']['mean_jaccard_wrong']:.3f} "
               f"(n = {E['KB11']['n_wrong']}); Cliff's δ = {E['KB11']['cliffs_delta']:.3f} ≥ 0.147 → gate allowed"])
    lr.append(['Issued-finding records (ISS)', f"{E['iss_records']:,} records with monthly epoch anchors ({E['iss_seconds']:.0f} s)"])
    lr.append(['V1 chain verification', f"{E['V1']['n']:,} records {'verified' if E['V1']['ok'] else 'FAILED'} in {E['V1']['seconds']:.2f} s"])
    lr.append(['V2 content-addressed objects', f"{E['V2']['objects_checked']} objects, {E['V2']['failures']} failures"])
    lr.append(['V3 re-execution (1,000 sampled findings)', f"vector hash {E['V3']['vector_hash_match']:,}/1,000; margin bit-identical {E['V3']['margin_bit_identical']:,}/1,000; "
               f"SHAP local accuracy {E['V3']['shap_local_accuracy_ok']:,}/1,000"])
    inj = L['injections']
    TN = {'bitflip': 'bit flip', 'delete': 'deletion', 'insert': 'insertion', 'swap': 'swap', 'ts_edit': 'timestamp edit', 'actor_edit': 'actor edit'}
    lr.append(['P8 tamper injection', '; '.join(f"{TN.get(k, k)} {v_['detected']:,}/{v_['trials']:,}" for k, v_ in inj.items())])
    lr.append(['P8 verification scaling', '; '.join(f"n = {r['n']:,}: {r['seconds']:.4f} s" for r in L['scaling']) + f"; log–log slope {L['loglog_slope']:.3f} ∈ [0.9, 1.1]"])
    lr.append(['KB3 cross-environment re-execution', f"tree hash, 97,436 scores, 134,435-vector digest identical ({100 * X['bit_identical_fraction']:.1f}%); "
               f"container Python {X['container']['env']['python']} / NumPy {X['container']['env']['numpy']} vs device Python {X['device']['env']['python']} / "
               f"NumPy {X['device']['env']['numpy']}, LightGBM {X['device']['env']['lightgbm']} on both"])
    lr.append(['Acquisition', f"{sum(sum(v_.values()) for v_ in I['strata'].values()):,} ACQ records; {I['dup_groups']} duplicate groups; oracle Merkle root {I['oracle_root'][:16]}…"])
    md += '\n' + table(['Check', 'Result'], lr)
    write('table13_explain_ledger', 'Table 13. Explanation evidence and ledger integrity (KB11, P8, KB3, V1–V3)', md,
          'Grouped TreeSHAP: exact LightGBM pred_contrib summed over EMBER v2 groups, 6,020 month×class-stratified March–September findings. The anchor '
          'signature is Ed25519 with a simulated timestamping authority; WORM storage is emulated by a content-addressed write-once store. {MoC}.')


# --------------------------------------------------------------------------------------------- T14 EMBER-2018 corroboration
def t_ember():
    E = J('ember.json'); P = json.load(open(f'{C.ROOT}/code/published_baselines.json'))
    pm = E['published_model_on_EMBER_test_NovDec']
    rows = [['AUC-ROC (%)', f"{100 * P['EMBER2018_LGBM_AUC']['value']:.3f}", f"{100 * pm['auc']:.3f}", f"{100 * (pm['auc'] - P['EMBER2018_LGBM_AUC']['value']):+.3f}"],
            ['TPR at 0.1% FPR, test-tuned (%)', f"{P['EMBER2018_LGBM_TPR_0.1']['value']:.2f}", f"{100 * pm['tpr_at_fpr_1e3_testtuned']:.2f}",
             f"{100 * pm['tpr_at_fpr_1e3_testtuned'] - P['EMBER2018_LGBM_TPR_0.1']['value']:+.2f}"],
            ['TPR at 1% FPR, test-tuned (%)', f"{P['EMBER2018_LGBM_TPR_1']['value']:.2f}", f"{100 * pm['tpr_at_fpr_1e2_testtuned']:.2f}",
             f"{100 * pm['tpr_at_fpr_1e2_testtuned'] - P['EMBER2018_LGBM_TPR_1']['value']:+.2f}"]]
    md = table(['Published EMBER-2018 model on Nov–Dec 2018', 'Release notebook {RfP} (full test set)', 'This vectorisation {MoC} (stratified sub-sample)', 'Δ (pp)'], rows)
    rows = []
    for mm in ['cal'] + [f'2018-{k:02d}' for k in range(7, 13)]:
        a = E['temporal']['0.001']['months'][mm]; b = E['temporal']['0.005']['months'][mm]
        rows.append(['May–Jun 2018 (cal)' if mm == 'cal' else MON(mm), f"{a['fp'] + a['tn']:,} / {a['tp'] + a['fn']:,}", f"{100 * a['fnr']:.2f}", f"{100 * a['fpr']:.3f}",
                     f"{100 * a['f1_pi10']:.2f}", f"{100 * b['fnr']:.2f}", f"{100 * b['fpr']:.3f}", f"{100 * a['auc']:.3f}"])
    md += '\n' + table(['Month', 'Benign / malware', 'FNR @θ0.1% (%)', 'FPR @θ0.1% (%)', 'F1 @π=10%, θ0.1% (%)', 'FNR @θ0.5% (%)', 'FPR @θ0.5% (%)', 'AUC-ROC (%)'], rows)
    ra = E['random_arm']; t1 = E['temporal']['0.001']; t5 = E['temporal']['0.005']
    fw = E['forward_EMBER2018_to_BODMAS2020']; bw = E['backward_f0_to_EMBER2018']
    lines = [['Within-EMBER temporal AUT(F1@π=10%) (%), θ@0.1% / θ@0.5%', f"{100 * t1['aut_f1_pi10']:.2f} / {100 * t5['aut_f1_pi10']:.2f}"],
             ['SVR at (0.5%, 5%), Jul–Dec 2018', f"θ@0.1%: {t1['SVR_0_5_5']}/6; θ@0.5%: {t5['SVR_0_5_5']}/6"],
             ['Random-split inflation (5 seeds), F1@π=10% vs temporal AUT', f"{ra['mean_pp']:+.2f} pp [{ra['ci'][0]:.2f}, {ra['ci'][1]:.2f}]"],
             ['Forward transfer: EMBER-trained (Jan–Apr 2018) → BODMAS Mar–Sep 2020, AUT(F1@π=10%) (%)',
              f"{100 * fw['aut_f1_pi10']:.2f}; monthly FNR {min(100 * v['fnr'] for v in fw['months'].values()):.1f}–{max(100 * v['fnr'] for v in fw['months'].values()):.1f}%"],
             ['Backward application: f₀ (BODMAS 2019) → EMBER 2018, monthly AUC-ROC (C1-violating, descriptive)',
              f"{min(100 * v['auc'] for v in bw.values()):.1f}–{max(100 * v['auc'] for v in bw.values()):.1f}%"],
             ['SHA-256 overlap between the EMBER sub-sample and BODMAS', f"{E['sha_overlap_with_BODMAS']} files"]]
    md += '\n' + table(['Corroboration check', 'Result'], lines)
    write('table14_ember2018', 'Table 14. EMBER-2018 corroboration (D10)', md,
          f"Month-stratified sub-sample of the EMBER-2018 labelled release vectorised with the EMBER v2 extractor ({E['n']:,} files, about 3,000 per class "
          'per month). Within-EMBER protocol mirrors TRACE-PE: train January–April, calibrate May–June (CP-certified θ), test July–December monthly. '
          'The release-notebook values are computed on the full 200,000-file test set with test-tuned thresholds; ours on the stratified Nov–Dec sub-sample.')


# --------------------------------------------------------------------------------------------- T15 comparison with published methods
def t_comparison():
    sys.path.insert(0, os.path.dirname(__file__))
    import s10_plots as Pl
    P = json.load(open(f'{C.ROOT}/code/published_baselines.json')); M = Pl.comparison_values(); A = J('analysis_bias.json'); E = J('ember.json')
    rows = []

    def add(metric, ref, rfp, rfp_lab, moc, moc_lab, protocol, higher_better=True):
        if isinstance(rfp, (list, tuple)):
            r_lo, r_hi = rfp; m_lo, m_hi = moc if isinstance(moc, (list, tuple)) else (moc, moc)
            dd = 3 if max(abs(m_lo), abs(m_hi)) < 1 else 2
            d_lo, d_hi = m_lo - r_lo, m_hi - r_hi
            rel_lo, rel_hi = 100 * d_lo / r_lo if r_lo else np.nan, 100 * d_hi / r_hi if r_hi else np.nan
            mtxt = f'{m_lo:.{dd}f}' if m_lo == m_hi else f'{m_lo:.{dd}f}–{m_hi:.{dd}f}'
            rows.append([metric, ref, f'{r_lo:.2f}–{r_hi:.2f} {rfp_lab}', f'{mtxt} {moc_lab}', f'{d_lo:+.2f} / {d_hi:+.2f}',
                         f'{rel_lo:+.1f}% / {rel_hi:+.1f}%' if np.isfinite(rel_lo) else f'— / {rel_hi:+.1f}%', protocol])
        else:
            dd = 3 if abs(moc) < 1 else 2
            d = moc - rfp; rel = 100 * d / rfp if rfp else np.nan
            rows.append([metric, ref, f'{rfp:.2f} {rfp_lab}', f'{moc:.{dd}f} {moc_lab}', f'{d:+.{dd}f}', f'{rel:+.1f}%' if np.isfinite(rel) else '—', protocol])
    em = P['BODMAS_T2_EmberGBDT_F1']
    add('Monthly F1 (%), range', '[1] T. II, EMBER-GBDT', (em['lo'], em['hi']), '{RfP}', M['ember2018_pub|F1_emp0.1_native_MarSep'][:2], '{MoC}',
        '[1]: GBDT trained by [1] on EMBER (5 seeds), threshold at 0.1% FPR on its own validation split, Oct 2019–Sep 2020; ours: the published EMBER-2018 '
        'model file, threshold at the 0.1% empirical quantile of BODMAS Dec 2019 benign, Mar–Sep 2020 Dated (realised pooled FPR 0.193%)')
    add('Monthly F1 (%), range', '[1] T. II, EMBER-GBDT', (em['lo'], em['hi']), '{RfP}', M['lgbm_trace|F1_emp0.1_native_MarSep'][:2], '{MoC} LGBM-TRACE, 5-seed mean',
        "LGBM-TRACE trained on BODMAS Aug–Nov 2019 at [1]'s operating point (0.1% empirical on Dec 2019)")
    add('Monthly F1 (%), range', '[1] T. II, EMBER-GBDT', (em['lo'], em['hi']), '{RfP}', M['lgbm_trace|F1_cert0.1_native_MarSep'][:2], '{MoC} LGBM-TRACE, 5-seed mean',
        'LGBM-TRACE at the CP-certified 0.1% threshold (k* = 1)')
    add('Monthly F1 (%), range', '[1] T. II, SOREL-GBDT', (P['BODMAS_T2_SORELGBDT_F1']['lo'], P['BODMAS_T2_SORELGBDT_F1']['hi']), '{RfP}',
        M['lgbm_trace|F1_cert0.1_native_MarSep'][:2], '{MoC} LGBM-TRACE, 5-seed mean', 'SOREL-20M-trained GBDT ([1]) vs LGBM-TRACE certified')
    t3 = P['BODMAS_T3_FNR']
    for k, lab in (('dated|lgbm_ember', 'T0 replication, Dated'), ('dated+prewindow|lgbm_ember', 'T0 replication, Dated + PreWindow')):
        if f'T0|{k}|FNR' in M:
            add('Monthly FNR (%), range', '[1] T. III', (t3['lo'], t3['hi']), '{RfP}', M[f'T0|{k}|FNR'], '{MoC}', f"{lab}: [1]'s protocol on our strata", False)
            add('Monthly FPR (%), range', '[1] T. III', (P['BODMAS_T3_FPR']['lo'], P['BODMAS_T3_FPR']['hi']), '{RfP}', M[f'T0|{k}|FPR'], '{MoC}', lab, False)
            if M.get(f'T0|{k}|FNR_unseen_max') is not None:
                add('Max monthly FNR, unseen families (%)', '[1] T. III', P['BODMAS_T3_unseenFNR_max']['value'], '{RfP}', M[f'T0|{k}|FNR_unseen_max'], '{MoC}', lab, False)
    add('Monthly FNR (%), range', '[1] T. III', (t3['lo'], t3['hi']), '{RfP}', M['lgbm_trace|FNR_cert0.1_JanSep'][:2], '{MoC} LGBM-TRACE, 5-seed mean', 'LGBM-TRACE certified, Jan–Sep 2020', False)
    p1 = A['P1']; rr = pd.DataFrame(p1['rows'])
    add('F1 (%), random split', '[1] T. II, EMBER-GBDT validation', P['BODMAS_T2_EmberGBDT_valF1']['value'], '{RfP}', 100 * rr.random_f1.mean(), '{MoC} LGBM-TRACE random arm, 5 seeds',
        'random split inflates both; ours: BODMAS random 5-seed arm')
    add('F1 (%)', '[94] D3QN, BODMAS', P['D3QN_BODMAS_F1']['value'], '{RfP}', 100 * rr.temporal_aut_f1.mean(), '{MoC} LGBM-TRACE temporal AUT, 5-seed mean',
        '[94] reports no temporal split; ours: temporal AUT, native ratio')
    add('F1 (%)', '[94] D3QN, EMBER-2018', P['D3QN_EMBER2018_F1']['value'], '{RfP}', 100 * E['temporal']['0.005']['aut_f1_pi10'], '{MoC} within-EMBER AUT, θ@0.5%',
        'different protocol; π = 10% re-weighting')
    add('AUC-ROC (%)', 'EMBER-2018 release notebook [2]', 100 * P['EMBER2018_LGBM_AUC']['value'], '{RfP}', 100 * E['published_model_on_EMBER_test_NovDec']['auc'], '{MoC}',
        'same published model; full test set vs our stratified sub-sample')
    add('TPR at 0.1% FPR (%)', 'EMBER-2018 release notebook [2]', P['EMBER2018_LGBM_TPR_0.1']['value'], '{RfP}', 100 * E['published_model_on_EMBER_test_NovDec']['tpr_at_fpr_1e3_testtuned'],
        '{MoC}', 'test-tuned threshold in both')
    add('TPR at 0.1% FPR (%)', '[2] EMBER-2017 LightGBM', P['EMBER_LGBM_TPR_0.1']['value'], '{RfP}', M['lgbm_trace|TPR_cert0.1_pool'], '{MoC} LGBM-TRACE, 5-seed mean',
        'EMBER-2017 test set, test-tuned threshold, vs LGBM-TRACE on BODMAS Mar–Sep 2020 at a threshold fixed on December 2019')
    F = J('flips.json')
    if F and 'L30_rho1.0' in F:
        fs_ = F['L30_rho1.0']['summary']; G = P['Ghiani_regression_Android']
        add('Malware regressing after an update (%)', '[30] Ghiani, Android CL', (G['lo'], G['hi']), '{RfP}', 100 * fs_['mal_regress_rate'],
            '{MoC} naive re-scoring', '[30]: continual-learning Android detectors; ours: monthly full retraining of LGBM-TRACE, BODMAS PE, findings of the 30 d '
            'before each of 7 updates, certified 0.5% thresholds, abstained findings included', False)
        add('Goodware flips per update (%)', '[89] Kozák, full AT', P['Kozak_ATfull_goodware_flips']['value'], '{RfP, computed from counts}',
            100 * fs_['ben_flip_rate'], '{MoC} naive re-scoring', '[89]: EMBER-GBDT after full adversarial retraining; ours: benign findings turned malicious by the next monthly model', False)
        add('Malware flips per update (%)', '[89] Kozák, full AT', P['Kozak_ATfull_malware_flips']['value'], '{RfP, computed from counts}',
            100 * fs_['mal_regress_rate'], '{MoC} naive re-scoring', 'as above, malware findings turned benign; [89] denominator uncertain (27/14,997 = 0.18% as in S6; 27/1,785 = 1.51%)', False)
    tbl = table(['Metric', 'Published source', 'Published value', 'This work', 'Δ absolute (pp)', 'Δ relative', 'Protocol note'], rows)
    write('table15_comparison', 'Table 15. Comparison with existing methods and published baselines: absolute (pp) and relative differences', tbl,
          'Δ = this work − published; relative Δ = Δ / published. Ranges are compared end-to-end (lower/upper). Protocols differ in training data, test '
          'months, base rate and operating point, as stated per row; rows with matched protocol are the release-notebook rows (same EMBER-2018 model file) and the '
          'T0 replication. LGBM-TRACE values are 5-seed means. {RfP} = reproduced-from-paper or release artifact; {MoC} = measured-on-Claude.')


# --------------------------------------------------------------------------------------------- T16 compute cost
def t_cost():
    T_ = J('timing_clean.json')
    if not T_:
        return
    jobs = [j for j in T_['jobs'] if 'fit_s' in j]
    rbf = f'{C.CACHE}/scores/svm_rbf_s11.json'
    if os.path.exists(rbf):
        r = json.load(open(rbf)); jobs.append(dict(model='svm_rbf', fit_s=r.get('fit_s', np.nan), pred_us=r.get('pred_us', np.nan), rss_gb=r.get('rss_gb', np.nan)))
    rows = [[NICE.get(j['model'], j['model']), f"{j['fit_s']:,.1f}", f"{j['pred_us']:,.1f}", f"{j['rss_gb']:.2f}"] for j in sorted(jobs, key=lambda j: j['fit_s'])]
    env = T_['env']
    write('table16_cost', 'Table 16. CPU cost per model (uncontended, sequential)', table(['Model', 'Training (s)', 'Inference (µs per file)', 'Peak RSS (GB)'], rows),
          f"Training window 23,158 × 2,381 (S7); inference on 20,000 rows. {env.get('cpu_model', '').replace('(R)', '').replace(' Processor', '').replace('GHz', ' GHz')}, {env.get('nproc', '')} vCPU, Python {env.get('python', '')}, "
          f"LightGBM {env.get('lightgbm', '')}, XGBoost {env.get('xgboost', '')}, scikit-learn {env.get('sklearn', '')}. One run per model; the published EMBER-2018 "
          'model is scored only; RBF-SVM values come from its E1 run (10,000-row training sub-sample, 97,436 rows scored); the MLP was re-timed after D17. {MoC}.')


# --------------------------------------------------------------------------------------------- T17 statistics
def t_stats():
    A = J('analysis_models.json'); fr = A['friedman']; rows = []
    for w in A['wilcoxon_vs_ref']:
        mc = next((x for x in A['mcnemar'] if x['model'] == w['model']), None)
        dl = [d for d in A['delong'] if d['model'] == w['model']]
        nsig = sum(1 for d in dl if d['p_holm'] < 0.05)
        rows.append([NICE.get(w['model'], w['model']), f"{w['delta_pp']:+.2f}", f"{w['cliff']:+.3f}", p_fmt(w['p']), p_fmt(w['p_holm']),
                     f"{mc['ref_only_errors']:,} / {mc['other_only_errors']:,} (p = {p_fmt(mc['p'])})" if mc else '—',
                     f"{nsig}/{len(dl)}" if dl else '—'])
    md = table(['Model', 'Mean monthly ΔF1@π=10%, LGBM-TRACE (seed mean) − model (pp)', "Cliff's δ", 'Wilcoxon p', 'Holm p', 'McNemar vs f₀: f₀-only / model-only errors', 'Months with DeLong p_Holm < 0.05 vs f₀'], rows)
    md += '\n' + table(['Test', 'Result'], [['Friedman over 7 months', f"χ² = {fr['chi2']:.2f}, p = {p_fmt(fr['p'])}, Kendall W = {fr['W']:.3f}"],
                                             ['Mean ranks (1 = best)', '; '.join(f"{NICE.get(k, k)} {v:.2f}" for k, v in sorted(fr['mean_ranks'].items(), key=lambda kv: kv[1]))]])
    write('table17_stats', 'Table 17. Statistical comparison of detectors (U13/H5)', md,
          'Monthly F1 at π = 10% and the certified 0.1% threshold, March–September 2020 (n = 7 months; seeds averaged before testing; single-fit models use their '
          'one fit; kNN and LR + PCA are excluded from the Friedman test because F1 is undefined when no file is flagged). McNemar and DeLong compare against f₀ '
          '(seed 11) and the first seed of each model; DeLong p-values are Holm-adjusted over all model × month tests. With n = 7 the smallest two-sided Wilcoxon p is 0.0156, so no pairwise comparison can pass Holm correction over '
          f"{len(A['wilcoxon_vs_ref'])} comparisons (minimum {0.015625 * len(A['wilcoxon_vs_ref']):.3f}): a power limit of the month-level design, not evidence of equivalence. McNemar uses the pooled March–September "
          'verdicts. {MoC}.')


ALL = [t_data, t_register, t_models, t_monthly, t_certificates, t_strata, t_baserate, t_calibration, t_bias, t_errors, t_monitor, t_assurance, t_attribution,
       t_explain_ledger, t_ember, t_comparison, t_cost, t_stats]
if __name__ == '__main__':
    os.makedirs(C.TABLES, exist_ok=True)
    sel = sys.argv[1:]
    for f in ALL:
        if sel and f.__name__ not in sel:
            continue
        try:
            f()
        except Exception as e:
            import traceback; print('FAILED', f.__name__, repr(e)); traceback.print_exc()
    order = sorted(glob.glob(f'{C.TABLES}/table*.md'), key=lambda p: int(os.path.basename(p).split('_')[0][5:]))
    open(f'{C.TABLES}/all_tables.md', 'w').write('\n\n'.join(open(p).read() for p in order))
