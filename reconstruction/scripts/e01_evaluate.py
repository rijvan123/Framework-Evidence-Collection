#!/usr/bin/env python3
"""E1b - thresholds fitted on December 2019 (certified, empirical, default, F1 at pi*), metrics per month and
pooled over the certifiable months, prevalence-resampled streams, threshold-rule violations and curve data
(paper Tables zoo / monthly / precision / certificates panel 2; Figs. metric bars, operating points, confusion, decay)."""
import numpy as np

import _common  # noqa: F401
from _common import certify_months, f0, rule_names, test_months
from tracepe.config import cli
from tracepe.decision.thresholds import certified_threshold, cp_lower, empirical_threshold, f1_threshold
from tracepe.evaluation import metrics as M
from tracepe.evaluation.stats import delong
from tracepe.evaluation.streams import prevalence_sample
from tracepe.models.zoo import DISPLAY, PROBA_SCORE
from tracepe.run import Run
from tracepe.utils import log


def thresholds_for(scores, e, cfg, key):
    th = cfg['thresholds']
    cal = e['split'].to_numpy() == 'calibration'
    yb = e['y'].to_numpy()
    ben = scores[cal & (yb == 0)]
    out = {}
    for t in th['certified_tau']:
        out[f'cp{t:g}'] = certified_threshold(ben, t, th['confidence'])
    for b in th['empirical_beta']:
        out[f'emp{b:g}'] = empirical_threshold(ben, b)
    out['default'] = dict(theta=0.5 if key in PROBA_SCORE else 0.0)
    out['f1pi'] = dict(theta=f1_threshold(scores[cal], yb[cal], th['pi_star']))
    return out


def main():
    cfg, args = cli(__doc__)
    run = Run(cfg)
    e = run.emeta
    y = e['y'].to_numpy().astype(int)
    month = e['month'].to_numpy()
    split = e['split'].to_numpy()
    dated_test = split == 'test'
    tm, cm = test_months(cfg), certify_months(cfg)
    periods = [cfg['screen']['calibration_month']] + tm
    pool = dated_test & np.isin(month, cm)
    pi_r, pi_p = cfg['prevalence']['report'], cfg['prevalence']['precision']
    B = int(cfg['bootstrap_B'])
    keys = [k for k in cfg['models']['zoo'] + ['ember2018_pub'] if run.score_seeds(k)]
    res = dict(periods=periods, pooled_months=cm, rules=rule_names(cfg), models={}, thresholds={})
    mask_p = {p: (split == ('calibration' if p == cfg['screen']['calibration_month'] else 'test')) & (month == p) for p in periods}
    mask_p['pooled'] = pool
    for key in keys:
        res['models'][key] = {}
        res['thresholds'][key] = {}
        for seed in run.score_seeds(key):
            s = run.load_scores(key, seed)
            ths = thresholds_for(s, e, cfg, key)
            res['thresholds'][key][str(seed)] = ths
            per = {}
            for p, mk in mask_p.items():
                ent = dict(auc=M.auc(s[mk], y[mk]), aucpr=M.auc_pr_at_pi(s[mk], y[mk], pi_r), counts={})
                for r, t in ths.items():
                    ent['counts'][r] = M.counts(s[mk], y[mk], t['theta'])
                per[p] = ent
            res['models'][key][str(seed)] = per
        log(f'evaluated {DISPLAY[key]} ({len(run.score_seeds(key))} seeds)')
    run.save('e1_metrics_raw', res)

    # ---------------------------------------------------------------- summaries used by tables and figures
    prim = rule_names(cfg)[0]
    key0, seed0 = f0(cfg)
    S = dict(primary_rule=prim, f0=[key0, seed0], zoo={}, f0_monthly={}, violations={}, streams={}, curves={},
             confusion={}, f0_rules={}, seed_spread={})

    def mets(c):
        return M.from_counts(c['tp'], c['fp'], c['fn'], c['tn'], pi_r, pi_p)

    for key in keys:
        seeds = sorted(res['models'][key])
        rows = []
        for sd in seeds:
            per = res['models'][key][sd]
            mt = mets(per['pooled']['counts'][prim])
            f1m = [mets(per[mo]['counts'][prim])['f1_pi'] for mo in cm]
            f1n = [mets(per[mo]['counts'][prim])['f1_native'] for mo in cm]
            rows.append(dict(seed=int(sd), auc=per['pooled']['auc'], aucpr=per['pooled']['aucpr'], f1_pi=mt['f1_pi'],
                             f1_native=mt['f1_native'], mcc_pi=mt['mcc_pi'], prec_pi=mt['precision_pi_prec'], tpr=mt['tpr'],
                             fpr=mt['fpr'], fnr=mt['fnr'], aut=M.aut(f1m), f1_monthly=f1m, aut_native=M.aut(f1n),
                             f1_native_monthly=f1n, counts=per['pooled']['counts'][prim]))
        agg = {}
        for f in ('auc', 'aucpr', 'f1_pi', 'f1_native', 'mcc_pi', 'prec_pi', 'tpr', 'fpr', 'fnr', 'aut', 'aut_native'):
            v = np.array([r[f] if r[f] is not None else np.nan for r in rows], float)
            agg[f] = dict(mean=float(np.nanmean(v)) if np.isfinite(v).any() else None,
                          min=float(np.nanmin(v)) if np.isfinite(v).any() else None,
                          max=float(np.nanmax(v)) if np.isfinite(v).any() else None)
        if len(seeds) == 1:
            c = rows[0]['counts']
            agg['ci'] = M.bootstrap_counts(c['tp'], c['fp'], c['fn'], c['tn'], B, cfg['seeds']['bootstrap'], pi_r, pi_p)
            s = run.load_scores(key, int(seeds[0]))
            try:
                agg['auc_ci'] = delong(y[pool], s[pool])['ci']
            except Exception:
                agg['auc_ci'] = None
        S['zoo'][key] = dict(display=DISPLAY[key], seeds=[int(x) for x in seeds], per_seed=rows, agg=agg)

    # f0 by month with CIs (monthly table, decay figure)
    s0 = run.load_scores(key0, seed0)
    for p in periods:
        mk = mask_p[p]
        c = res['models'][key0][str(seed0)][p]['counts'][prim]
        mt = mets(c)
        ci = M.bootstrap_counts(c['tp'], c['fp'], c['fn'], c['tn'], B, cfg['seeds']['bootstrap'], pi_r, pi_p)
        try:
            auc_ci = delong(y[mk], s0[mk])['ci']
        except Exception:
            auc_ci = None
        S['f0_monthly'][p] = dict(metrics=mt, ci=ci, auc=res['models'][key0][str(seed0)][p]['auc'], auc_ci=auc_ci,
                                  benign=int(mt['n_neg']), malware=int(mt['n_pos']),
                                  fpr_reportable=bool(mt['n_neg'] >= cfg['screen']['report_min_benign']))
    # seed spread of the f0 family (FNR per month per seed)
    for sd in sorted(res['models'][key0]):
        S['seed_spread'][sd] = {p: mets(res['models'][key0][sd][p]['counts'][prim])['fnr'] for p in periods}
    # f0 under each threshold rule (pooled)
    for r in res['thresholds'][key0][str(seed0)]:
        mt = mets(res['models'][key0][str(seed0)]['pooled']['counts'][r])
        mt['precision_pi_0.001'] = M.precision_analytic(mt['tpr'], mt['fpr'], 0.001)
        S['f0_rules'][r] = dict(theta=res['thresholds'][key0][str(seed0)][r]['theta'], metrics=mt,
                                k=res['thresholds'][key0][str(seed0)][r].get('k_star', res['thresholds'][key0][str(seed0)][r].get('k')))

    # threshold-rule violations (certificates table, panel 2)
    th = cfg['thresholds']
    for r, tau in [(f'emp{b:g}', b) for b in th['empirical_beta']] + [(f'cp{t:g}', t) for t in th['certified_tau']]:
        cells = viol = viol_lb = 0
        by_model = {}
        for key in keys:
            for sd, per in res['models'][key].items():
                for mo in cm:
                    c = per[mo]['counts'][r]
                    nb = c['fp'] + c['tn']
                    if nb == 0:
                        continue
                    cells += 1
                    if c['fp'] / nb > tau:
                        viol += 1
                        by_model[key] = by_model.get(key, 0) + 1
                        if cp_lower(c['fp'], nb) > tau:
                            viol_lb += 1
        S['violations'][r] = dict(tau=tau, cells=cells, above=viol, cp_lower_above=viol_lb, by_model=by_model)

    # prevalence-resampled streams for f0 at the primary threshold and the default threshold (precision table)
    theta0 = res['thresholds'][key0][str(seed0)][prim]['theta']
    theta_def = res['thresholds'][key0][str(seed0)]['default']['theta']
    for mo in cm:
        mk = dated_test & (month == mo)
        ben = np.flatnonzero(mk & (y == 0))
        mal = np.flatnonzero(mk & (y == 1))
        c = M.counts(s0[mk], y[mk], theta0)
        tpr = c['tp'] / max(c['tp'] + c['fn'], 1)
        fpr = c['fp'] / max(c['fp'] + c['tn'], 1)
        ent = {}
        for pi in cfg['prevalence']['streams']:
            vals = []
            for sd in cfg['seeds']['streams']:
                rng = np.random.default_rng(int(sd) * 1000 + int(round(pi * 1000)))
                idx = prevalence_sample(ben, mal, pi, rng)
                cc = M.counts(s0[idx], y[idx], theta0)
                vals.append(cc['tp'] / (cc['tp'] + cc['fp']) if (cc['tp'] + cc['fp']) else np.nan)
            vals = np.asarray(vals, float)
            ana = M.precision_analytic(tpr, fpr, pi)
            lo, hi = (np.nanpercentile(vals, 2.5), np.nanpercentile(vals, 97.5)) if np.isfinite(vals).any() else (np.nan, np.nan)
            ent[str(pi)] = dict(mean=float(np.nanmean(vals)) if np.isfinite(vals).any() else None, lo=float(lo), hi=float(hi),
                                analytic=ana, outside=bool(not (lo - 1e-12 <= ana <= hi + 1e-12)) if np.isfinite(lo) else None)
        cd = M.counts(s0[mk], y[mk], theta_def)
        tpr_d = cd['tp'] / max(cd['tp'] + cd['fn'], 1)
        fpr_d = cd['fp'] / max(cd['fp'] + cd['tn'], 1)
        ent['default'] = {str(pi): M.precision_analytic(tpr_d, fpr_d, pi) for pi in (0.001, 0.01)}
        ent['tpr'], ent['fpr'] = tpr, fpr
        S['streams'][mo] = ent

    # curves (operating points and ROC/PR) on the pooled stream, first seed of each model
    for key in keys:
        sd = sorted(res['models'][key], key=int)[0] if key != key0 else str(seed0)
        s = run.load_scores(key, int(sd))
        S['curves'][key] = dict(seed=int(sd), roc=M.roc_points(s[pool], y[pool]),
                                pr10=M.pr_points(s[pool], y[pool], 0.10), pr1=M.pr_points(s[pool], y[pool], 0.01))
    # confusion data
    S['confusion'] = {'f0_' + r: res['models'][key0][str(seed0)]['pooled']['counts'][r] for r in (prim, 'default')}
    for key in ('lr', 'ember2018_pub'):
        if key in res['models']:
            sd = sorted(res['models'][key], key=int)[0]
            S['confusion'][key + '_' + prim] = res['models'][key][sd]['pooled']['counts'][prim]
    run.save('e1_metrics', S)
    log('E1 evaluation done; f0 pooled:', {k: round(v, 5) if isinstance(v, float) else v
                                          for k, v in S['zoo'][key0]['per_seed'][[r['seed'] for r in S['zoo'][key0]['per_seed']].index(seed0)].items()
                                          if k in ('tpr', 'fpr', 'f1_pi', 'aut')})


if __name__ == '__main__':
    main()
