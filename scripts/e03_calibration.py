#!/usr/bin/env python3
"""E3 - calibration under drift (isotonic / Platt vs raw sigmoid; P4, H10), prior shift (Eq. (31)), Bayes-cost
thresholds (Eqs. (53)-(57); P7, H6), likelihood-ratio cost Cllr (KB12) and label-noise injection (P11, Eq. (5))."""
import numpy as np

import _common  # noqa: F401
from _common import certify_months, f0
from tracepe.config import cli
from tracepe.decision import calibration as C
from tracepe.decision.certificates import cllr
from tracepe.decision.thresholds import f1_threshold
from tracepe.evaluation import metrics as M
from tracepe.evaluation.stats import boot_mean_ci, spearman, wilcoxon_p
from tracepe.run import Run
from tracepe.utils import log


def main():
    cfg, args = cli(__doc__)
    run = Run(cfg)
    e = run.emeta
    y = e['y'].to_numpy().astype(int)
    month = e['month'].to_numpy()
    split = e['split'].to_numpy()
    key0, seed0 = f0(cfg)
    z = run.load_scores(key0, seed0)
    cal = split == 'calibration'
    cm = certify_months(cfg)
    bins = int(cfg['calibration']['ece_bins'])
    iso = C.Isotonic().fit(z[cal], y[cal])
    platt = C.Platt().fit(z[cal], y[cal])
    pi_cal = float(y[cal].mean())
    th = cfg['thresholds']
    R = dict(pi_cal=pi_cal, months={}, cost={}, cllr={})
    ece_raw, ece_iso, ece_platt = [], [], []
    for mo in [cfg['screen']['calibration_month']] + cm:
        mk = ((split == 'calibration') if mo == cfg['screen']['calibration_month'] else (split == 'test')) & (month == mo)
        zz, yy = z[mk], y[mk]
        q_iso = iso.predict(zz)
        ent = dict(ece_raw=C.ece(C.sigmoid(zz), yy, bins), ece_iso=C.ece(q_iso, yy, bins), ece_platt=C.ece(platt.predict(zz), yy, bins))
        for pi in th['cost_pis']:
            w = C.prevalence_weights(yy, pi)
            ent[f'brier_iso_{pi:g}'] = C.brier(q_iso, yy, w)
            ent[f'brier_prior_{pi:g}'] = C.brier(C.prior_shift(q_iso, pi_cal, pi), yy, w)
        lr = C.score_lr(q_iso, pi_cal)
        ent['cllr'] = cllr(lr, yy)
        R['cllr'][mo] = ent['cllr']
        R['months'][mo] = ent
        if mo != cfg['screen']['calibration_month']:
            ece_raw.append(ent['ece_raw'])
            ece_iso.append(ent['ece_iso'])
            ece_platt.append(ent['ece_platt'])
    d_iso = np.array(ece_iso) - np.array(ece_raw)
    R['P4'] = dict(iso_minus_raw_mean=float(d_iso.mean()), ci=boot_mean_ci(d_iso, seed=1), wilcoxon_p=wilcoxon_p(ece_iso, ece_raw),
                   months_iso_higher=int((d_iso > 0).sum()),
                   brier_prior_vs_iso={f'{pi:g}': dict(
                       p=wilcoxon_p([R['months'][m][f'brier_prior_{pi:g}'] for m in cm], [R['months'][m][f'brier_iso_{pi:g}'] for m in cm]),
                       months_lower=sum(R['months'][m][f'brier_prior_{pi:g}'] < R['months'][m][f'brier_iso_{pi:g}'] for m in cm))
                       for pi in th['cost_pis']})
    R['P4']['falsified'] = bool(R['P4']['ci'][0] is not None and R['P4']['ci'][0] > 0)
    R['H10'] = spearman(np.arange(len(cm)), ece_iso, n_perm=2000, seed=2, B=500)
    # expected cost of the Bayes-cost threshold tau* (on prior-shifted isotonic posteriors) vs p = 0.5
    for pi in th['cost_pis']:
        for ratio in th['cost_ratios']:
            tau_star = C.bayes_tau(ratio, 1.0)
            ec_star, ec_half = [], []
            for mo in cm:
                mk = (split == 'test') & (month == mo)
                zz, yy = z[mk], y[mk]
                q_pi = C.prior_shift(iso.predict(zz), pi_cal, pi)
                for pred, sink in (((q_pi >= tau_star).astype(int), ec_star), ((zz > 0).astype(int), ec_half)):
                    fnr = float(((pred == 0) & (yy == 1)).sum() / max((yy == 1).sum(), 1))
                    fpr = float(((pred == 1) & (yy == 0)).sum() / max((yy == 0).sum(), 1))
                    sink.append(C.expected_cost(fnr, fpr, pi, ratio, 1.0))
            ec_star, ec_half = np.array(ec_star), np.array(ec_half)
            R['cost'][f'{pi:g}_{ratio}'] = dict(pi=pi, ratio=ratio, tau_star=tau_star, ec_star=ec_star.tolist(),
                                                ec_half=ec_half.tolist(), mean_star=float(ec_star.mean()),
                                                mean_half=float(ec_half.mean()), months_star_lower=int((ec_star < ec_half).sum()),
                                                p=wilcoxon_p(ec_star, ec_half))
    R['P7'] = dict(cells_star_lower=sum(v['mean_star'] < v['mean_half'] for v in R['cost'].values()),
                   cells=len(R['cost']))
    R['P7']['falsified'] = R['P7']['cells_star_lower'] == 0
    # H6: F1 at pi* with the pi*-aware threshold (fitted on December) vs the default threshold
    t_f1 = f1_threshold(z[cal], y[cal], th['pi_star'])
    f_star, f_half = [], []
    for mo in cm:
        mk = (split == 'test') & (month == mo)
        f_star.append(M.point_metrics(z[mk], y[mk], t_f1, th['pi_star'])['f1_pi'])
        f_half.append(M.point_metrics(z[mk], y[mk], 0.0, th['pi_star'])['f1_pi'])
    R['H6'] = dict(theta=t_f1, mean_diff=float(np.nanmean(np.array(f_star) - np.array(f_half))), p=wilcoxon_p(f_star, f_half))
    # KB12: Cllr >= 1 in >= 3 months
    R['KB12'] = dict(months_ge_1=sum(v >= 1 for m, v in R['cllr'].items() if m in cm), triggered=sum(v >= 1 for m, v in R['cllr'].items() if m in cm) >= 3)
    # P11: observed rates under injected label noise follow Eq. (5)
    pool = (split == 'test') & np.isin(month, cm)
    th0 = run.load('e1_metrics_raw')['thresholds'][key0][str(seed0)][f'cp{th["certified_tau"][0]:g}']['theta']
    pred = (z[pool] > th0).astype(int)
    yt = y[pool]
    tpr = pred[yt == 1].mean()
    fpr = pred[yt == 0].mean()
    pi = yt.mean()
    R['P11'] = {}
    rng = np.random.default_rng(11)
    for eta in cfg['calibration']['label_noise']:
        noisy = yt.copy()
        flip = rng.random(len(yt)) < eta
        noisy[flip] = 1 - noisy[flip]
        o_tpr = pred[noisy == 1].mean()
        o_fpr = pred[noisy == 0].mean()
        e_tpr = (pi * (1 - eta) * tpr + (1 - pi) * eta * fpr) / (pi * (1 - eta) + (1 - pi) * eta)
        e_fpr = (pi * eta * tpr + (1 - pi) * (1 - eta) * fpr) / (pi * eta + (1 - pi) * (1 - eta))
        bt, bf = [], []
        for _ in range(int(cfg['bootstrap_B'])):
            i = rng.integers(0, len(yt), len(yt))
            nn, pp = noisy[i], pred[i]
            bt.append(pp[nn == 1].mean())
            bf.append(pp[nn == 0].mean())
        ci_t = [float(np.percentile(bt, 2.5)), float(np.percentile(bt, 97.5))]
        ci_f = [float(np.percentile(bf, 2.5)), float(np.percentile(bf, 97.5))]
        R['P11'][str(eta)] = dict(observed_tpr=float(o_tpr), predicted_tpr=float(e_tpr), ci_tpr=ci_t,
                                  observed_fpr=float(o_fpr), predicted_fpr=float(e_fpr), ci_fpr=ci_f,
                                  inside=bool(ci_t[0] <= e_tpr <= ci_t[1] and ci_f[0] <= e_fpr <= ci_f[1]))
    R['P11_falsified'] = not all(v['inside'] for v in R['P11'].values())
    run.save('e3_calibration', R)
    log('E3 done: P4 iso-raw', round(R['P4']['iso_minus_raw_mean'], 4), 'P7 cells', R['P7']['cells_star_lower'], 'KB12', R['KB12'])


if __name__ == '__main__':
    main()
