"""Statistics added in the revision, computed from the counts recorded by the original run (S10 package and ledger).
No model is re-fitted and no new data are used. Every number written here is derived from released counts.
Usage: python revision_stats.py <package>/out/e1_metrics.pkl revision_stats.json"""
import json, math, sys
import numpy as np, pandas as pd
from scipy.stats import beta, wilcoxon

OUT = {}


def cp_upper(k, n, a=0.05):            # one-sided upper bound, level 1-a; real-valued k allowed (design-effect scaling)
    return 1.0 if k >= n else float(beta.ppf(1 - a, k + 1, n - k))


def cp_lower(k, n, a=0.05):
    return 0.0 if k <= 0 else float(beta.ppf(a, k, n - k + 1))


def cp_two(k, n):                      # exact two-sided 95% Clopper-Pearson
    return cp_lower(k, n, 0.025), cp_upper(k, n, 0.025)


def ppv_lb(fp, nb, fn, nm, pi):       # Eq. (101): Bonferroni-split one-sided bounds, simultaneous 95%
    tpr_lb = 1 - cp_upper(fn, nm, 0.025)
    fpr_ub = cp_upper(fp, nb, 0.025)
    return pi * tpr_lb / (pi * tpr_lb + fpr_ub * (1 - pi))


# ------------------------------------------------------------------ Table 13 (f0, theta@0.1%, months)
t13 = {  # month: (benign, malware, FN, FP)  -- Table 13 / ledger CERT records
    'Dec 2019 (cal)': (6120, 4039, 97, 1), 'Jan 2020': (49, 4400, 179, 0), 'Feb 2020': (62, 4030, 236, 0),
    'Mar 2020': (3577, 4990, 325, 1), 'Apr 2020': (5201, 4640, 231, 0), 'May 2020': (6121, 5449, 276, 1),
    'Jun 2020': (8182, 4217, 237, 0), 'Jul 2020': (6392, 4995, 837, 0), 'Aug 2020': (2514, 3823, 942, 0),
    'Sep 2020': (4198, 4577, 1095, 1)}
rows = {}
for mth, (nb, nm, fn, fp) in t13.items():
    fnr = fn / nm; flo, fhi = cp_two(fn, nm)
    r = dict(fnr=100 * fnr, fnr_lo=100 * flo, fnr_hi=100 * fhi)
    if nb >= 100:
        plo, phi = cp_two(fp, nb)
        prec1 = 0.01 * (1 - fnr) / (0.01 * (1 - fnr) + 0.99 * fp / nb) if (fp / nb) > 0 else 1.0
        r.update(fpr=100 * fp / nb, fpr_lo=100 * plo, fpr_hi=100 * phi, fpr_ub1=100 * cp_upper(fp, nb),
                 prec1=100 * prec1, prec1_lb=100 * ppv_lb(fp, nb, fn, nm, 0.01))
    rows[mth] = r
OUT['table13'] = rows

# ------------------------------------------------------------------ Table 16 (precision under pi, Eq. (101) bounds)
t16 = {}
for mth in ['Mar 2020', 'Apr 2020', 'May 2020', 'Jun 2020', 'Jul 2020', 'Aug 2020', 'Sep 2020']:
    nb, nm, fn, fp = t13[mth]
    t16[mth] = {str(p): 100 * ppv_lb(fp, nb, fn, nm, p) for p in (0.01, 0.02, 0.05, 0.10)}
OUT['table16_lb'] = t16

# ------------------------------------------------------------------ Table 12 (single fits, pooled Mar-Sep, certified 0.1%)
df = pd.read_pickle(sys.argv[1] if len(sys.argv) > 1 else 'out/e1_metrics.pkl')   # metrics table of the run
single = ['lr', 'lr_chi2', 'lr_ig', 'lr_mrmr', 'lr_pca', 'svm_lin', 'svm_rbf', 'knn', 'nb', 'ember2018_pub']
t12 = {}
for mdl in single:
    sub = df[(df.model == mdl) & (df.set == 'pool_MarSep') & (df.thr == 'cert_0.1') & (df.metric == 'tp_fn_fp_tn')]
    if not len(sub):
        continue
    s = sub.iloc[0]; tp, fn, fp, tn = int(s.tp), int(s.fn), int(s.fp), int(s.tn)
    nm, nb = tp + fn, fp + tn
    tlo, thi = cp_two(tp, nm); flo, fhi = cp_two(fp, nb); nlo, nhi = cp_two(fn, nm)
    prec1 = (0.01 * tp / nm / (0.01 * tp / nm + 0.99 * fp / nb)) if (tp + fp) > 0 and tp > 0 else float('nan')
    t12[mdl] = dict(seed=int(s.seed), tp=tp, fn=fn, fp=fp, tn=tn, tpr=100 * tp / nm, tpr_lo=100 * tlo, tpr_hi=100 * thi,
                    fpr=100 * fp / nb, fpr_lo=100 * flo, fpr_hi=100 * fhi, fnr=100 * fn / nm, fnr_lo=100 * nlo, fnr_hi=100 * nhi,
                    prec1=100 * prec1 if prec1 == prec1 else None, prec1_lb=100 * ppv_lb(fp, nb, fn, nm, 0.01) if tp > 0 else None)
OUT['table12_single'] = t12

# ------------------------------------------------------------------ dependence sensitivity and simultaneous coverage (theta@0.5%)
c05 = {  # month: (FP, benign, FN, malware) at theta@0.5% for f0 -- ledger CERT records (key thr0.005)
    'Mar': (3, 3577, 105, 4990), 'Apr': (3, 5201, 81, 4640), 'May': (3, 6121, 93, 5449), 'Jun': (7, 8182, 108, 4217),
    'Jul': (6, 6392, 388, 4995), 'Aug': (1, 2514, 497, 3823), 'Sep': (5, 4198, 585, 4577)}
# empirical extra-binomial dispersion of FNR across the four stable months (Pearson chi2 / df)
fnk = np.array([c05[m][2] for m in ('Mar', 'Apr', 'May', 'Jun')], float); fnn = np.array([c05[m][3] for m in ('Mar', 'Apr', 'May', 'Jun')], float)
p_ = fnk.sum() / fnn.sum(); chi2 = float(np.sum((fnk - fnn * p_) ** 2 / (fnn * p_ * (1 - p_)))); phi_fnr = chi2 / 3
fpk = np.array([c05[m][0] for m in ('Mar', 'Apr', 'May', 'Jun')], float); fpn = np.array([c05[m][1] for m in ('Mar', 'Apr', 'May', 'Jun')], float)
q_ = fpk.sum() / fpn.sum(); chi2f = float(np.sum((fpk - fpn * q_) ** 2 / (fpn * q_ * (1 - q_)))); phi_fpr = chi2f / 3
OUT['dispersion'] = dict(fnr_pooled=100 * p_, chi2_fnr=chi2, phi_fnr=phi_fnr, fpr_pooled=100 * q_, chi2_fpr=chi2f, phi_fpr=phi_fpr)
a_sim = 0.05 / 14
dep = {}
for m, (fp, nb, fn, nm) in c05.items():
    d = dict(fpr=100 * fp / nb, fpr_ub=100 * cp_upper(fp, nb), fnr=100 * fn / nm, fnr_ub=100 * cp_upper(fn, nm),
             fpr_ub_sim=100 * cp_upper(fp, nb, a_sim), fnr_ub_sim=100 * cp_upper(fn, nm, a_sim))
    for deff in (2.0, 4.0):
        d[f'fpr_ub_deff{deff:g}'] = 100 * cp_upper(fp / deff, nb / deff)
        d[f'fnr_ub_deff{deff:g}'] = 100 * cp_upper(fn / deff, nm / deff)
    d['valid'] = d['fpr_ub'] <= 0.5 and d['fnr_ub'] <= 5
    d['valid_sim'] = d['fpr_ub_sim'] <= 0.5 and d['fnr_ub_sim'] <= 5
    for deff in (2.0, 4.0):
        d[f'valid_deff{deff:g}'] = d[f'fpr_ub_deff{deff:g}'] <= 0.5 and d[f'fnr_ub_deff{deff:g}'] <= 5
    dep[m] = d
OUT['dependence_theta05'] = dep
for key in ('valid', 'valid_sim', 'valid_deff2', 'valid_deff4'):
    OUT[f'svr_{key}'] = sum(dep[m][key] for m in dep)
# calibration-month certificate of the 0.1% threshold (k*=1 of 6,120) under dependence
OUT['cal_0p1'] = {f'deff{d:g}': 100 * cp_upper(1 / d, 6120 / d) for d in (1.0, 1.5, 2.0, 4.0)}
OUT['cal_0p5'] = {f'deff{d:g}': 100 * cp_upper(21 / d, 6120 / d) for d in (1.0, 1.5, 2.0, 4.0)}

# ------------------------------------------------------------------ U12 with the Holm rule
unseen = np.array([36.51, 37.18, 45.07, 15.49, 28.57, 26.09, 8.72, 32.06, 59.76])
known = np.array([3.60, 5.24, 5.96, 4.82, 4.35, 5.28, 18.14, 24.38, 21.89])
p_u12 = float(wilcoxon(unseen, known, alternative='two-sided').pvalue)
fam = {'U12 (H3)': p_u12, 'U14 (H7)': 0.0039, 'H6 (part of U7)': 0.297}
order = sorted(fam, key=fam.get); adj = {}; run = 0.0
for i, k in enumerate(order):
    run = max(run, min(1.0, (len(order) - i) * fam[k])); adj[k] = run
OUT['holm'] = dict(raw=fam, adjusted=adj, u12_recomputed=p_u12)

# ------------------------------------------------------------------ assurance simulation: errors among issued findings
# E_T and E^ev_T of policies without re-validation events are 30 x (number of wrong findings), because every finding issued
# between 1 March and 30 September is live for exactly L = 30 days before its label matures (horizon 31 October).
sim = {  # policy: (n, abstained, screening-only at issue, E_ev, E)
    'frozen f0, no safeguards': (68876, 0, 0, 56550, 56550),
    'frozen f0 + abstention + certificate gating (viii-f)': (68876, 7234, 24094, 600, 1140),
    'monthly retraining only': (68876, 0, 0, 8730, 8730),
    'retraining + certificate gating': (68876, 0, 18279, 4740, 8730),
    'retraining + abstention': (68876, 5466, 0, 510, 510),
    'retraining + abstention + certificate gating (viii)': (68876, 5466, 16814, 90, 510)}
base_wrong = {'frozen': 56550 // 30, 'retrain': 8730 // 30}
tab = {}
for pol, (n, ab, sc, eev, e) in sim.items():
    assert eev % 30 == 0 and e % 30 == 0
    ev = n - ab - sc; w_ev = eev // 30; w_live = e // 30
    tot = base_wrong['frozen'] if pol.startswith('frozen') else base_wrong['retrain']
    lo, hi = cp_two(w_ev, ev)
    tab[pol] = dict(n=n, abstained=ab, screening=sc, evaluative=ev, evaluative_share=100 * ev / n, wrong_evaluative=w_ev,
                    err_evaluative=100 * w_ev / ev, err_lo=100 * lo, err_hi=100 * hi, wrong_nonabstained=w_live,
                    nonabstained=n - ab, err_nonabstained=100 * w_live / (n - ab), wrong_abstained=tot - w_live,
                    err_abstained=100 * (tot - w_live) / ab if ab else None, E_ev=eev,
                    random_matched_expected=tot * ev / n)
OUT['simulation_errors'] = tab
json.dump(OUT, open(sys.argv[2] if len(sys.argv) > 2 else 'revision_stats.json', 'w'), indent=1)
print(json.dumps(OUT, indent=1)[:12000])
