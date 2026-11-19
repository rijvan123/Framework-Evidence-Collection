#!/usr/bin/env python3
"""E13 - statistical comparison of detectors (paper Section 8.12; H5): Friedman test with Kendall's W over
monthly F1 at pi = 10%, pairwise Wilcoxon with Holm correction and Cliff's delta against LGBM-TRACE,
exact McNemar on pooled verdicts against f0, DeLong per month with Holm correction."""
import numpy as np

import _common  # noqa: F401
from _common import certify_months, f0
from tracepe.config import cli
from tracepe.evaluation import metrics as M
from tracepe.evaluation.stats import cliffs_delta, delong, friedman, holm, mcnemar_exact, wilcoxon_p
from tracepe.models.zoo import DISPLAY
from tracepe.run import Run
from tracepe.utils import log


def main():
    cfg, args = cli(__doc__)
    run = Run(cfg)
    raw = run.load('e1_metrics_raw')
    prim = raw['rules'][0]
    cm = certify_months(cfg)
    pi = cfg['prevalence']['report']
    key0, seed0 = f0(cfg)
    monthly = {}
    for key, seeds in raw['models'].items():
        vals = []
        for mo in cm:
            v = [M.from_counts(**seeds[s][mo]['counts'][prim], pi_report=pi)['f1_pi'] for s in seeds]
            vals.append(float(np.nanmean(v)) if np.isfinite(v).any() else np.nan)
        monthly[key] = vals
    usable = [k for k, v in monthly.items() if np.all(np.isfinite(v))]
    fr = friedman(np.column_stack([monthly[k] for k in usable]))
    ranks = dict(zip(usable, fr['mean_ranks']))
    R = dict(friedman=fr, mean_ranks={k: ranks[k] for k in sorted(ranks, key=ranks.get)}, excluded=[k for k in monthly if k not in usable],
             monthly_f1=monthly, pairwise={})
    e = run.emeta
    y = e['y'].to_numpy().astype(int)
    month = e['month'].to_numpy()
    pool = (e['split'].to_numpy() == 'test') & np.isin(month, cm)
    s0 = run.load_scores(key0, seed0)
    th0 = raw['thresholds'][key0][str(seed0)][prim]['theta']
    err0 = (s0 > th0).astype(int) != y
    ref = np.array(monthly[key0])
    pw = []
    delong_p, delong_key = [], []
    for key in monthly:
        if key == key0:
            continue
        v = np.array(monthly[key])
        ok = np.isfinite(v)
        sd = sorted(raw['models'][key], key=int)[0]
        s = run.load_scores(key, int(sd))
        th = raw['thresholds'][key][sd][prim]['theta']
        err = (s > th).astype(int) != y
        b = int((err0 & ~err & pool).sum())
        c = int((~err0 & err & pool).sum())
        ent = dict(display=DISPLAY.get(key, key), mean_delta_pp=float(np.mean(ref[ok] - v[ok]) * 100) if ok.any() else None,
                   cliffs_delta=cliffs_delta(ref[ok], v[ok]) if ok.any() else None, wilcoxon_p=wilcoxon_p(ref[ok], v[ok]) if ok.sum() > 1 else None,
                   mcnemar_f0_only=b, mcnemar_model_only=c, mcnemar_p=mcnemar_exact(b, c), delong_months={})
        for mo in cm:
            mk = (e['split'].to_numpy() == 'test') & (month == mo)
            try:
                p = delong(y[mk], s0[mk], s[mk])['p']
            except Exception:
                p = np.nan
            ent['delong_months'][mo] = p
            delong_p.append(p)
            delong_key.append((key, mo))
        R['pairwise'][key] = ent
        pw.append(key)
    ps = [R['pairwise'][k]['wilcoxon_p'] if R['pairwise'][k]['wilcoxon_p'] is not None else 1.0 for k in pw]
    for k, h in zip(pw, holm(ps)):
        R['pairwise'][k]['holm_p'] = h
    finite = [i for i, p in enumerate(delong_p) if np.isfinite(p)]
    adj = holm([delong_p[i] for i in finite]) if finite else []
    for i, h in zip(finite, adj):
        k, mo = delong_key[i]
        R['pairwise'][k].setdefault('delong_holm', {})[mo] = h
    for k in pw:
        dh = R['pairwise'][k].get('delong_holm', {})
        R['pairwise'][k]['delong_months_significant'] = int(sum(v < 0.05 for v in dh.values()))
    trees = {'lgbm_trace', 'lgbm_ember', 'xgboost', 'rf', 'et', 'stack', 'ember2018_pub'}
    tree_ranks = [ranks[k] for k in usable if k in trees]
    other = [ranks[k] for k in usable if k not in trees]
    R['H5'] = dict(met=bool(fr['p'] < 0.05 and fr['kendall_w'] >= 0.5), trees_ahead=bool(tree_ranks and other and max(tree_ranks) < min(other)))
    run.save('e13_statistics', R)
    log('E13 done: Friedman', round(fr['chi2'], 2), 'p', fr['p'], 'W', round(fr['kendall_w'], 3))


if __name__ == '__main__':
    main()
