#!/usr/bin/env python3
"""S10 analysis of E1/E2/E5 outputs: certificates, SVR, PPV bounds, strata sensitivity, base-rate (P2), calibration
and prior shift (P4), cost thresholds (P7/H6), entropy stratum (P10), label noise (P11), unseen vs known families
(H3), ECE trend (H10), model comparison (H5), drift (P5/H4), LR/Cllr (KB12), random-split inflation (P1, KB4),
leakage (P3), invariance (P9), timestamp ablation (H9), BODMAS Table III replication.
Usage: python3 s10_analysis.py [part ...]   (default: all available parts) -> out/analysis_<part>.json"""
import sys, os, json, glob, math
import numpy as np, pandas as pd
from scipy import stats
from sklearn.isotonic import IsotonicRegression
import s10_common as C

m = C.load_meta(); y = m['y'].to_numpy().astype(int); mo = m['month'].to_numpy(); sp = m['split'].to_numpy()
st = m['stratum'].to_numpy(); fam = m['family'].to_numpy()
train_fams = set(fam[(sp == 'train') & (y == 1)])
X = None


def scores(name='lgbm_trace', seed=11):
    d = np.load(f'{C.CACHE}/scores/{name}_s{seed}.npz'); s = np.full(len(m), np.nan); s[d['idx']] = d['s']; return s


def thr_of(s, tau=0.001):
    cal = np.where(sp == 'cal')[0]; return C.certified_threshold(s[cal][y[cal] == 0], tau)


def save(part, obj):
    C.jdump(obj, f'{C.OUT}/analysis_{part}.json'); print('saved', part)


# ------------------------------------------------------------------ certificates, SVR (KS1), PPV bounds (S7.17)
def part_certificates():
    s = scores(); out = {}
    for tau_thr, (tF, tN) in [(0.001, (0.001, 0.02)), (0.005, (0.005, 0.05)), (0.001, (0.005, 0.05))]:
        thr, k = thr_of(s, tau_thr); rows = {}
        for mm in ['2019-12'] + C.TEST_MONTHS:
            sel = np.where((st == 'Dated') & (mo == mm))[0]
            tp, fn, fp, tn = C.counts(y[sel], s[sel], thr); nb, nm = fp + tn, tp + fn
            fub = C.cp_upper(fp, nb); nub = C.cp_upper(fn, nm)
            rows[mm] = dict(fp=fp, n_b=nb, fn=fn, n_m=nm, fpr=fp / nb, fnr=fn / nm, fpr_ub=fub, fnr_ub=nub,
                            fpr_cert=bool(nb >= 500 and fub <= tF), fnr_cert=bool(fnr_ok := (nub <= tN)),
                            ppv_lb={str(pi): C.ppv_bound(fp, nb, fn, nm, pi) for pi in (0.01, 0.02, 0.05, 0.10)},
                            false_alarms_per_1e4_benign=1e4 * fp / nb, fpr_ub_975=C.cp_upper(fp, nb, 0.975))
        valid = [rows[mm]['fpr_cert'] and rows[mm]['fnr_cert'] for mm in C.CERT_MONTHS]
        out[f'thr{tau_thr}|tau{tF}/{tN}'] = dict(thr=thr, kstar=k, months=rows, SVR=float(np.mean(valid)), SVR_months=int(np.sum(valid)),
                                                 fpr_only_valid=int(np.sum([rows[mm]['fpr_cert'] for mm in C.CERT_MONTHS])),
                                                 fnr_only_valid=int(np.sum([rows[mm]['fnr_cert'] for mm in C.TEST_MONTHS])))
    out['KS1_pass'] = out['thr0.005|tau0.005/0.05']['SVR_months'] >= 6
    save('certificates', out)


# ------------------------------------------------------------------ strata sensitivity: KB5, R-S1, R-S2, k=4
def part_strata():
    s = scores(); thr, _ = thr_of(s); out = {}
    for mm, cens in [('2020-01', 'Placeholder'), ('2020-02', 'Bulk')]:
        d = np.where((st == 'Dated') & (mo == mm) & (y == 0))[0]; c = np.where((st == cens) & (mo == mm))[0]
        fp_d = int(np.sum(s[d] > thr)); fp_c = int(np.sum(s[c] > thr))
        ci = C.boot_threshold_metrics(0, 1, fp_d, len(d) - fp_d, B=2000, seed=3)['fpr'] if len(d) else (np.nan, np.nan)
        half = (ci[1] - ci[0]) / 2
        fpr_d = fp_d / len(d); fpr_all = (fp_d + fp_c) / (len(d) + len(c))
        out[mm] = dict(dated_benign=len(d), censored_benign=len(c), stratum=cens, fpr_dated=fpr_d, fpr_censored=fp_c / len(c) if len(c) else None,
                       fpr_with_censored=fpr_all, shift=abs(fpr_all - fpr_d), boot_half_width=half, exceeds=bool(abs(fpr_all - fpr_d) > half),
                       fpr_ub_censored=C.cp_upper(fp_c, len(c)) if len(c) else None)
    out['KB5_pass'] = any(out[mm]['exceeds'] for mm in ('2020-01', '2020-02'))
    # R-S1: spike-day malware treated as dated (Jan/Feb FNR)
    for mm in ('2020-01', '2020-02'):
        d = np.where((st == 'Dated') & (mo == mm) & (y == 1))[0]; sm = np.where((st == 'SpikeMal') & (mo == mm))[0]
        out[f'RS1_{mm}'] = dict(fnr_dated=float(np.mean(s[d] <= thr)), fnr_with_spike_mal=float(np.mean(s[np.r_[d, sm]] <= thr)),
                                n_spike_mal=len(sm), fnr_spike_mal=float(np.mean(s[sm] <= thr)) if len(sm) else None)
    # R-S2: Bulk stratum own certificate
    b = np.where(st == 'Bulk')[0]; fpb = int(np.sum(s[b] > thr))
    out['RS2_bulk'] = dict(n=len(b), fp=fpb, fpr=fpb / len(b), fpr_ub=C.cp_upper(fpb, len(b)), cert_0_1=bool(C.cp_upper(fpb, len(b)) <= 0.001))
    pl = np.where(st == 'Placeholder')[0]; fpp = int(np.sum(s[pl] > thr))
    out['placeholder'] = dict(n=len(pl), fp=fpp, fpr=fpp / len(pl), fpr_ub=C.cp_upper(fpp, len(pl)))
    # k = 4 spike rule: June without 2020-06-08 and 2020-06-30
    jun = np.where((st == 'Dated') & (mo == '2020-06'))[0]; k4 = m['spike4'].to_numpy()
    for tag, sel in [('k10', jun), ('k4', jun[~k4[jun]])]:
        tp, fn, fp, tn = C.counts(y[sel], s[sel], thr); r = C.rates_from_counts(tp, fn, fp, tn)
        out[f'june_{tag}'] = dict(n=len(sel), fnr=r['fnr'], fpr=r['fpr'], f1=r['f1'])
    save('strata', out)


# ------------------------------------------------------------------ P2/H2: measured streams vs analytic Eq. 55/70
def part_baserate():
    st_ = pd.read_pickle(f'{C.OUT}/e1_streams.pkl'); st_ = st_[(st_.model == 'lgbm_trace') & (st_.seed == 11)]
    s = scores(); thr, _ = thr_of(s); cells = []; out = {}
    for mm in C.CERT_MONTHS:
        sel = np.where((sp == 'test') & (mo == mm))[0]; tp, fn, fp, tn = C.counts(y[sel], s[sel], thr)
        tpr = tp / (tp + fn); fpr = fp / (fp + tn)
        for pi in C.PIS_MEASURED:
            g = st_[(st_.month == mm) & (st_.pi == pi)]['prec'].to_numpy()
            ana = tpr * pi / (tpr * pi + fpr * (1 - pi))
            lo, hi = np.percentile(g, 2.5), np.percentile(g, 97.5)
            cells.append(dict(month=mm, pi=pi, analytic=ana, measured_mean=float(g.mean()), lo=float(lo), hi=float(hi), inside=bool(lo - 1e-12 <= ana <= hi + 1e-12)))
        for pi in (0.001,):
            ana = tpr * pi / (tpr * pi + fpr * (1 - pi)) if fpr > 0 else 1.0
            out[f'{mm}|prec_0.001'] = dict(analytic=ana, realised_fpr=fpr, condition=bool(fpr >= 0.001), lt_0_6=bool(ana < 0.6))
    df = pd.DataFrame(cells); out['cells'] = cells; out['share_outside'] = float(1 - df['inside'].mean())
    out['P2_part1_falsified'] = bool(out['share_outside'] > 0.20)
    cond = [v for k, v in out.items() if k.endswith('prec_0.001') and v['condition']]
    out['P2_part2'] = {'months_with_fpr_ge_0.1pct': len(cond), 'all_lt_0_6': all(c['lt_0_6'] for c in cond) if cond else None}
    # same at the default threshold (the base-rate collapse is visible there)
    thr0 = 0.0; rows = []
    for mm in C.CERT_MONTHS:
        sel = np.where((sp == 'test') & (mo == mm))[0]; tp, fn, fp, tn = C.counts(y[sel], s[sel], thr0)
        for pi in C.PIS:
            k = C.kappa_for(pi, tp + fn, fp + tn); r = C.rates_from_counts(tp, fn, fp, tn, k)
            rows.append(dict(month=mm, pi=pi, prec=r['prec'], f1=r['f1'], fpr=fp / (fp + tn)))
    out['default_threshold_sweep'] = rows
    save('baserate', out)


# ------------------------------------------------------------------ P4: calibration and prior shift; P7/H6 cost thresholds
def part_calibration():
    from sklearn.linear_model import LogisticRegression
    s = scores(); cal = np.where(sp == 'cal')[0]
    iso = IsotonicRegression(out_of_bounds='clip', y_min=0, y_max=1).fit(s[cal], y[cal])
    pl = LogisticRegression(C=1e6, max_iter=1000).fit(s[cal].reshape(-1, 1), y[cal])
    pi_tr = float(y[cal].mean()); out = dict(pi_cal=pi_tr, months={})
    e_raw, e_iso, e_pl = [], [], []
    for mm in C.CERT_MONTHS:
        sel = np.where((sp == 'test') & (mo == mm))[0]; ss = s[sel]; yy = y[sel]
        q_raw = 1 / (1 + np.exp(-ss)); q_iso = iso.predict(ss); q_pl = pl.predict_proba(ss.reshape(-1, 1))[:, 1]
        r = dict(ece_raw=C.ece_binary(yy, q_raw), ece_iso=C.ece_binary(yy, q_iso), ece_platt=C.ece_binary(yy, q_pl),
                 brier_raw=C.brier(yy, q_raw), brier_iso=C.brier(yy, q_iso))
        e_raw.append(r['ece_raw']); e_iso.append(r['ece_iso']); e_pl.append(r['ece_platt'])
        for pi in (0.01, 0.001):
            w = np.where(yy == 1, pi / yy.mean(), (1 - pi) / (1 - yy.mean()))
            qpi = (pi / pi_tr) * q_iso / ((pi / pi_tr) * q_iso + ((1 - pi) / (1 - pi_tr)) * (1 - q_iso))
            r[f'wbrier_iso_{pi}'] = float(np.sum(w * (q_iso - yy) ** 2) / np.sum(w))
            r[f'wbrier_prior_{pi}'] = float(np.sum(w * (qpi - yy) ** 2) / np.sum(w))
            for ratio in (10, 50, 100):
                tau_star = 1 / (1 + ratio)                                   # Eq. 53 with C_FP = 1, C_FN = ratio
                def ec(dec):
                    tpr = np.mean(dec[yy == 1]); fpr = np.mean(dec[yy == 0])
                    return ratio * pi * (1 - tpr) + 1 * (1 - pi) * fpr      # Eq. 57 (per file)
                r[f'EC_star_{pi}_{ratio}'] = float(ec((qpi >= tau_star).astype(int)))
                r[f'EC_half_{pi}_{ratio}'] = float(ec((q_iso >= 0.5).astype(int)))
                r[f'EC_noprior_star_{pi}_{ratio}'] = float(ec((q_iso >= tau_star).astype(int)))
        out['months'][mm] = r
    out['P4'] = dict(ece_raw=e_raw, ece_iso=e_iso, ece_platt=e_pl,
                     wilcoxon_iso_vs_raw=C.wilcoxon_p(e_iso, e_raw), wilcoxon_platt_vs_raw=C.wilcoxon_p(e_pl, e_raw),
                     mean_reduction_iso=float(np.mean(np.array(e_raw) - np.array(e_iso))),
                     ci_reduction_iso=C.boot_ci_mean(np.array(e_raw) - np.array(e_iso)))
    for pi in (0.01, 0.001):
        a = [out['months'][mm][f'wbrier_iso_{pi}'] for mm in C.CERT_MONTHS]; b = [out['months'][mm][f'wbrier_prior_{pi}'] for mm in C.CERT_MONTHS]
        out['P4'][f'brier_prior_{pi}'] = dict(iso=a, prior=b, p=C.wilcoxon_p(b, a), mean_red=float(np.mean(np.array(a) - np.array(b))),
                                               ci=C.boot_ci_mean(np.array(a) - np.array(b)))
        for ratio in (10, 50, 100):
            es = [out['months'][mm][f'EC_star_{pi}_{ratio}'] for mm in C.CERT_MONTHS]; eh = [out['months'][mm][f'EC_half_{pi}_{ratio}'] for mm in C.CERT_MONTHS]
            out['P4'][f'EC_{pi}_{ratio}'] = dict(star=es, half=eh, p=C.wilcoxon_p(es, eh), star_lt_half_months=int(np.sum(np.array(es) < np.array(eh))))
    out['P7_falsified'] = all(np.mean(out['P4'][f'EC_{pi}_{r}']['star']) >= np.mean(out['P4'][f'EC_{pi}_{r}']['half'])
                              for pi in (0.01, 0.001) for r in (10, 50, 100))
    # H10: ECE trend over Jan..Sep (isotonic)
    eces = []
    for mm in C.TEST_MONTHS:
        sel = np.where((sp == 'test') & (mo == mm))[0]; eces.append(C.ece_binary(y[sel], iso.predict(s[sel])))
    rho, p = C.spearman_perm(np.arange(len(eces)), eces, 10000, 1)
    out['H10'] = dict(ece=eces, rho=rho, p=p, pass_=bool(rho > 0))
    # H6: F1 at pi* = 10% with the pi*-aware threshold vs the default (0.5) threshold, Mar..Sep
    thrs = json.load(open(f'{C.OUT}/e1_thresholds.json'))['lgbm_trace_s11']
    f_star, f_def = [], []
    for mm in C.CERT_MONTHS:
        sel = np.where((sp == 'test') & (mo == mm))[0]
        for t_, lst in ((thrs['f1pi10'], f_star), (0.0, f_def)):
            tp, fn, fp, tn = C.counts(y[sel], s[sel], t_); lst.append(C.rates_from_counts(tp, fn, fp, tn, C.kappa_for(0.10, tp + fn, fp + tn))['f1'])
    out['H6'] = dict(f1_star=f_star, f1_default=f_def, p=C.wilcoxon_p(f_star, f_def), delta_mean_pp=100 * float(np.mean(np.array(f_star) - np.array(f_def))))
    save('calibration', out)


# ------------------------------------------------------------------ P10 entropy stratum; P11 label noise; H3 families
def part_strata_errors():
    global X
    X = C.load_X(); s = scores(); thr, _ = thr_of(s); te = np.where((sp == 'test') & np.isin(mo, C.CERT_MONTHS))[0]
    BEH = np.asarray(X[te, 256:512], dtype=np.float64).reshape(-1, 16, 16)          # (r = entropy bin, u = high nibble)
    hi_rows = BEH[:, 14:, :]
    pk_eq19 = hi_rows.sum(axis=1).max(axis=1) > (0.5 / 16)                            # Eq. 19, tau_p = 1/32
    pk_mass = hi_rows.sum(axis=(1, 2)) > 0.5                                           # total-mass variant
    out = {}
    for tag, pk in [('eq19', pk_eq19), ('mass', pk_mass)]:
        r = {}
        for cls, err_name in [(1, 'fnr'), (0, 'fpr')]:
            sel = y[te] == cls; err = (s[te] <= thr) if cls == 1 else (s[te] > thr)
            a = int(np.sum(err & sel & pk)); b = int(np.sum(~err & sel & pk)); c = int(np.sum(err & sel & ~pk)); d = int(np.sum(~err & sel & ~pk))
            OR, p = stats.fisher_exact([[a, b], [c, d]])
            se = math.sqrt(sum(1 / max(v, 0.5) for v in (a, b, c, d))); lor = math.log(max(OR, 1e-12)) if OR > 0 else float('-inf')
            r[err_name] = dict(high=[a, a + b], low=[c, c + d], rate_high=a / max(a + b, 1), rate_low=c / max(c + d, 1), OR=OR, p=p,
                               OR_ci=(math.exp(lor - 1.96 * se), math.exp(lor + 1.96 * se)) if np.isfinite(lor) else (0.0, 0.0))
        r['share_high_benign'] = float(pk[y[te] == 0].mean()); r['share_high_malware'] = float(pk[y[te] == 1].mean())
        out[tag] = r
    out['P10_falsified'] = not all((out['eq19'][k]['OR_ci'][0] > 1) for k in ('fnr', 'fpr'))
    # P11: injected class-conditional flips on test labels; Eq. 5 prediction
    yt = y[te]; dec = (s[te] > thr).astype(int); pi = yt.mean(); TPR = dec[yt == 1].mean(); FPR = dec[yt == 0].mean(); rng = np.random.default_rng(5)
    res11 = {}
    for eta in (0.01, 0.05):
        meas_t, meas_f = [], []
        for _ in range(200):
            flip = rng.random(len(yt)) < eta; yo = np.where(flip, 1 - yt, yt)
            meas_t.append(dec[yo == 1].mean()); meas_f.append(dec[yo == 0].mean())
        e0 = e1 = eta
        pt = (pi * (1 - e1) * TPR + (1 - pi) * e0 * FPR) / (pi * (1 - e1) + (1 - pi) * e0)
        pf = (pi * e1 * TPR + (1 - pi) * (1 - e0) * FPR) / (pi * e1 + (1 - pi) * (1 - e0))
        lt, ht = np.percentile(meas_t, [2.5, 97.5]); lf, hf = np.percentile(meas_f, [2.5, 97.5])
        res11[str(eta)] = dict(pred_tpr=pt, meas_tpr=float(np.mean(meas_t)), ci_tpr=(lt, ht), pred_fpr=pf, meas_fpr=float(np.mean(meas_f)), ci_fpr=(lf, hf),
                               inside=bool(lt <= pt <= ht and lf <= pf <= hf))
    out['P11'] = res11; out['P11_falsified'] = not all(v['inside'] for v in res11.values())
    # H3: unseen-family vs known-family FNR per month (Jan..Sep)
    rows = []
    for mm in C.TEST_MONTHS:
        sel = np.where((sp == 'test') & (mo == mm) & (y == 1))[0]; uns = ~np.isin(fam[sel], list(train_fams))
        fn = s[sel] <= thr
        rows.append(dict(month=mm, n_unseen=int(uns.sum()), n_known=int((~uns).sum()), fnr_unseen=float(fn[uns].mean()) if uns.any() else np.nan,
                         fnr_known=float(fn[~uns].mean())))
    df = pd.DataFrame(rows); a = df['fnr_unseen'].to_numpy(); b = df['fnr_known'].to_numpy()
    out['H3'] = dict(rows=rows, p=C.wilcoxon_p(a, b), A12=C.a12(a, b), pass_=bool(C.wilcoxon_p(a, b) < 0.05 and C.a12(a, b) > 0.71))
    save('errors', out)


# ------------------------------------------------------------------ H5: model comparison (Friedman, Kendall W, Wilcoxon+Holm, Cliff, DeLong, McNemar)
def part_models():
    df = pd.read_pickle(f'{C.OUT}/e1_metrics.pkl')
    q = df[(df.thr == 'cert_0.1') & (df.pi == '0.1') & (df.metric == 'f1') & df.set.isin(C.CERT_MONTHS)]
    piv = q.groupby(['set', 'model'])['value'].mean().unstack()           # seeds averaged first
    piv = piv.dropna(axis=1)
    chi2, p, W, ranks = C.friedman_kendall(piv.to_numpy())
    ref = 'lgbm_trace'; comps = []
    for col in piv.columns:
        if col == ref:
            continue
        comps.append(dict(model=col, p=C.wilcoxon_p(piv[ref], piv[col]), cliff=C.cliffs_delta(piv[ref], piv[col]),
                          delta_pp=100 * float((piv[ref] - piv[col]).mean())))
    adj = C.holm([c['p'] for c in comps])
    for c, a in zip(comps, adj):
        c['p_holm'] = float(a)
    # AUT per model/seed (Mar-Sep): F1@pi=10% and native; TPR over Jan-Sep
    aut = []
    for (mdl, seed), g in df[(df.thr == 'cert_0.1')].groupby(['model', 'seed']):
        f10 = [g[(g.set == mm) & (g.metric == 'f1') & (g.pi == '0.1')]['value'].iloc[0] for mm in C.CERT_MONTHS]
        fn = [g[(g.set == mm) & (g.metric == 'f1') & (g.pi == 'native')]['value'].iloc[0] for mm in C.CERT_MONTHS]
        tpr = [g[(g.set == mm) & (g.metric == 'rec') & (g.pi == 'native')]['value'].iloc[0] for mm in C.TEST_MONTHS]
        aut.append(dict(model=mdl, seed=seed, aut_f1_pi10=C.aut(f10), aut_f1_native=C.aut(fn), aut_tpr=C.aut(tpr)))
    aut = pd.DataFrame(aut)
    # DeLong (per month) and McNemar (pooled Mar-Sep) vs LGBM-TRACE seed 11
    s_ref = scores(); thr_ref, _ = thr_of(s_ref); dl = []; mc = []
    te = np.where((sp == 'test') & np.isin(mo, C.CERT_MONTHS))[0]
    for f in sorted(glob.glob(f'{C.CACHE}/scores/*_s*.npz')):
        base = os.path.basename(f)[:-4]; name, seed = base.rsplit('_s', 1)
        if name == ref or seed not in ('11', '0'):
            continue
        s2 = scores(name, int(seed)); thr2, _ = thr_of(s2)
        for mm in C.CERT_MONTHS:
            sel = np.where((sp == 'test') & (mo == mm))[0]; d_, pv = C.delong_test(y[sel], s_ref[sel], s2[sel])
            dl.append(dict(model=name, month=mm, dAUC=d_, p=pv))
        e1 = (s_ref[te] > thr_ref).astype(int) != y[te]; e2 = (s2[te] > thr2).astype(int) != y[te]
        b = int(np.sum(e1 & ~e2)); c = int(np.sum(~e1 & e2))
        mc.append(dict(model=name, ref_only_errors=b, other_only_errors=c, p=C.mcnemar_exact(b, c)))
    dl = pd.DataFrame(dl)
    if len(dl):
        dl['p_holm'] = np.concatenate([C.holm(g['p'].to_numpy()) for _, g in dl.groupby('month')]) if False else C.holm(dl['p'].to_numpy())
    out = dict(friedman=dict(chi2=chi2, p=p, W=W, models=list(piv.columns), mean_ranks=dict(zip(piv.columns, ranks.tolist())),
                             H5_pass=bool(p < 0.05 and W >= 0.5)),
               wilcoxon_vs_ref=comps, aut=aut.to_dict('records'), delong=dl.to_dict('records'), mcnemar=mc)
    save('models', out)


# ------------------------------------------------------------------ P5/H4: JS drift per EMBER group vs decay
def part_drift():
    global X
    X = C.load_X(); tr = np.where(sp == 'train')[0]
    Xtr = np.asarray(X[tr]); qs = np.linspace(0, 1, 21)[1:-1]
    edges = [np.unique(np.quantile(Xtr[:, j], qs)) for j in range(C.D)]
    def hist(Xs):
        H = np.zeros((C.D, 20))
        for j, e in enumerate(edges):
            c = np.bincount(np.searchsorted(e, Xs[:, j], side='right'), minlength=len(e) + 1); H[j, :len(c)] = c
        H = H + 1e-10; return H / H.sum(1, keepdims=True)
    def js(P, Q):
        M_ = 0.5 * (P + Q); kl = lambda A, B: np.sum(A * np.log2(A / B), axis=1); return 0.5 * kl(P, M_) + 0.5 * kl(Q, M_)
    Ptr = hist(Xtr); out = dict(months={})
    Ptr_c = {c: hist(Xtr[y[tr] == c]) for c in (0, 1)}
    for mm in ['2019-12'] + C.TEST_MONTHS:
        sel = np.where((st == 'Dated') & (mo == mm))[0]; Xm = np.asarray(X[sel])
        jf = js(Ptr, hist(Xm)); r = dict(D=float(np.mean(jf)), groups={g: float(np.mean(jf[a:b])) for g, a, b in C.GROUPS})
        for c in (0, 1):
            if np.sum(y[sel] == c) >= 30:
                jc = js(Ptr_c[c], hist(Xm[y[sel] == c])); r[f'D_cls{c}'] = float(np.mean(jc))
        out['months'][mm] = r; print('drift', mm, round(r['D'], 4), flush=True)
    df = pd.read_pickle(f'{C.OUT}/e1_metrics.pkl'); g = df[(df.model == 'lgbm_trace') & (df.seed == 11) & (df.thr == 'cert_0.1')]
    f1 = [g[(g.set == mm) & (g.metric == 'f1') & (g.pi == '0.1')]['value'].iloc[0] for mm in C.CERT_MONTHS]
    fnr = [g[(g.set == mm) & (g.metric == 'fnr') & (g.pi == 'native')]['value'].iloc[0] for mm in C.TEST_MONTHS]
    Dm = [out['months'][mm]['D'] for mm in C.CERT_MONTHS]; Dall = [out['months'][mm]['D'] for mm in C.TEST_MONTHS]
    rho, p = C.spearman_perm(Dm, f1, 10000, 2); rho2, p2 = C.spearman_perm(Dall, fnr, 10000, 3)
    rng = np.random.default_rng(4); bs = []
    for _ in range(2000):
        ii = rng.choice(len(Dm), len(Dm)); bs.append(stats.spearmanr(np.array(Dm)[ii], np.array(f1)[ii]).statistic)
    bs = np.array(bs)[np.isfinite(bs)]
    f1_dec = g[(g.set == 'cal_Dec') & (g.metric == 'f1') & (g.pi == '0.1')]['value'].iloc[0]
    out['P5'] = dict(rho_D_f1pi10=rho, p=p, ci=(float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))), rho_D_fnr=rho2, p_fnr=p2,
                     falsified=bool(rho >= 0 or np.percentile(bs, 97.5) > -0.1))
    out['H4'] = dict(decay=[f1_dec - v for v in f1], rho=-rho, p=p)
    save('drift', out)


# ------------------------------------------------------------------ KB12: score-based LR and Cllr per month
def part_lr():
    s = scores(); cal = np.where(sp == 'cal')[0]; nb = int(np.sum(y[cal] == 0)); nm = int(np.sum(y[cal] == 1))
    iso = IsotonicRegression(out_of_bounds='clip', y_min=1e-6, y_max=1 - 1e-6).fit(s[cal], y[cal])
    prior_odds = nm / nb
    def LR(ss):
        p = np.clip(iso.predict(ss), 1e-9, 1 - 1e-9); lr = (p / (1 - p)) / prior_odds
        return np.clip(lr, 1 / (nm + 1), nb + 1)                    # capped at the calibration resolution
    def cllr(ss, yy):
        lr = LR(ss); return 0.5 * (np.mean(np.log2(1 + 1 / lr[yy == 1])) + np.mean(np.log2(1 + lr[yy == 0])))
    out = {'2019-12': cllr(s[cal], y[cal])}
    for mm in C.CERT_MONTHS:
        sel = np.where((sp == 'test') & (mo == mm))[0]; out[mm] = cllr(s[sel], y[sel])
    bad = sum(1 for mm in C.CERT_MONTHS if out[mm] >= 1)
    save('lr', dict(cllr=out, months_ge_1=bad, KB12_kill=bool(bad >= 3), cap=[1 / (nm + 1), nb + 1]))


# ------------------------------------------------------------------ P1/KB4 (random split), P3, P9, H9, T0
def part_bias():
    out = {}
    if os.path.exists(f'{C.OUT}/e5_random.json'):
        R = json.load(open(f'{C.OUT}/e5_random.json'))
        df = pd.read_pickle(f'{C.OUT}/e1_metrics.pkl')
        rows = []
        for a in R['arms']:
            seed = a['seed']; g = df[(df.model == 'lgbm_trace') & (df.seed == seed) & (df.thr == 'cert_0.1')]
            f10 = [g[(g.set == mm) & (g.metric == 'f1') & (g.pi == '0.1')]['value'].iloc[0] for mm in C.CERT_MONTHS]
            fnat = [g[(g.set == mm) & (g.metric == 'f1') & (g.pi == 'native')]['value'].iloc[0] for mm in C.CERT_MONTHS]
            rows.append(dict(seed=seed, random_f1_pi10=a['cert']['pool']['f1_pi10'], random_f1=a['cert']['pool']['f1'],
                             temporal_aut_f1_pi10=C.aut(f10), temporal_aut_f1=C.aut(fnat),
                             random_fnr=a['cert']['pool']['fnr'], random_fpr=a['cert']['pool']['fpr']))
        rr = pd.DataFrame(rows)
        d10 = 100 * (rr.random_f1_pi10 - rr.temporal_aut_f1_pi10); dn = 100 * (rr.random_f1 - rr.temporal_aut_f1)
        out['P1'] = dict(rows=rows, delta_pp_pi10=d10.tolist(), delta_pp_native=dn.tolist(), mean_pp_pi10=float(d10.mean()), ci_pi10=C.boot_ci_mean(d10.to_numpy()),
                         mean_pp_native=float(dn.mean()), ci_native=C.boot_ci_mean(dn.to_numpy()),
                         rel_pct_pi10=float(np.mean(d10 / (100 * rr.temporal_aut_f1_pi10)) * 100),
                         falsified=bool(np.mean(d10) < 2 or C.boot_ci_mean(d10.to_numpy())[0] <= 0))
        # KB4: static random 80:20 vs temporal certificates (point estimates, Mar-Sep)
        cert = json.load(open(f'{C.OUT}/analysis_certificates.json'))['thr0.001|tau0.001/0.02']['months']
        stc = R['static_8020']['pool']; under = []
        for mm in C.CERT_MONTHS:
            under.append(bool(stc['fnr'] < cert[mm]['fnr'] or stc['fpr'] < cert[mm]['fpr']))
        out['KB4'] = dict(static=stc, months_understated=int(np.sum(under)), detail=dict(zip(C.CERT_MONTHS, under)), pass_=bool(np.sum(under) >= 5))
    if os.path.exists(f'{C.OUT}/e5_no626.json'):
        A = json.load(open(f'{C.OUT}/e5_no626.json'))['months']; df = pd.read_pickle(f'{C.OUT}/e1_metrics.pkl')
        g = df[(df.model == 'lgbm_trace') & (df.seed == 11) & (df.thr == 'cert_0.1')]
        base = [g[(g.set == mm) & (g.metric == 'f1') & (g.pi == '0.1')]['value'].iloc[0] for mm in C.CERT_MONTHS]
        abl = [A[mm]['f1_pi10'] for mm in C.CERT_MONTHS]
        base_t = [g[(g.set == mm) & (g.metric == 'rec') & (g.pi == 'native')]['value'].iloc[0] for mm in C.TEST_MONTHS]
        abl_t = [1 - A[mm]['fnr'] for mm in C.TEST_MONTHS]
        out['H9'] = dict(aut_base=C.aut(base), aut_no626=C.aut(abl), delta_pp=100 * (C.aut(abl) - C.aut(base)),
                         aut_tpr_base=C.aut(base_t), aut_tpr_no626=C.aut(abl_t), delta_tpr_pp=100 * (C.aut(abl_t) - C.aut(base_t)),
                         pass_=bool(abs(100 * (C.aut(abl) - C.aut(base))) < 1))
    for k in ('prewin', 'leak', 'norm', 't0', 'cv'):
        if os.path.exists(f'{C.OUT}/e5_{k}.json'):
            out[k] = json.load(open(f'{C.OUT}/e5_{k}.json'))
    save('bias', out)


PARTS = dict(certificates=part_certificates, strata=part_strata, baserate=part_baserate, calibration=part_calibration,
             errors=part_strata_errors, models=part_models, drift=part_drift, lr=part_lr, bias=part_bias)
if __name__ == '__main__':
    for p in (sys.argv[1:] or list(PARTS)):
        PARTS[p]()
