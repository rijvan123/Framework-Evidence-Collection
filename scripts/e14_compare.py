#!/usr/bin/env python3
"""E14 - comparison with published baselines in absolute (percentage points) and relative terms (paper
comparison table). Published values are read from results/published_baselines.json ({RfP})."""
import numpy as np

import _common  # noqa: F401
from _common import certify_months, test_months
from tracepe.config import ROOT, cli
from tracepe.evaluation import metrics as M
from tracepe.run import Run
from tracepe.utils import load_json, log


def seed_mean_monthly(raw, key, rule, months, field, pi):
    seeds = raw['models'].get(key, {})
    if not seeds:
        return None
    out = []
    for mo in months:
        v = [M.from_counts(**seeds[s][mo]['counts'][rule], pi_report=pi)[field] for s in seeds]
        out.append(float(np.nanmean(v)))
    return out


def deltas(val, pub):
    """Absolute (pp) and relative differences; ranges are compared end-to-end, a scalar against both ends."""
    vs = list(val) if isinstance(val, (list, tuple)) else [val]
    ps = list(pub) if isinstance(pub, (list, tuple)) else [pub]
    if len(vs) == 1 and len(ps) == 2:
        vs = vs * 2
    if len(ps) == 1 and len(vs) == 2:
        ps = ps * 2
    dpp = [v * 100 - p for v, p in zip(vs, ps)]
    drel = [((v * 100 - p) / p) if p else None for v, p in zip(vs, ps)]
    return (dpp if len(dpp) > 1 else dpp[0]), (drel if len(drel) > 1 else drel[0])


def rng_(v):
    v = [x for x in v if x is not None and np.isfinite(x)]
    return [min(v), max(v)] if v else None


def main():
    cfg, args = cli(__doc__)
    run = Run(cfg)
    pub = load_json(ROOT / 'results' / 'published_baselines.json')
    raw = run.load('e1_metrics_raw')
    pi = cfg['prevalence']['report']
    cm, tm = certify_months(cfg), test_months(cfg)
    emp = f'emp{cfg["thresholds"]["empirical_beta"][0]:g}'
    cp = raw['rules'][0]
    meas = {}
    if 'ember2018_pub' in raw['models']:
        meas['ember_pub_f1_native_emp'] = rng_(seed_mean_monthly(raw, 'ember2018_pub', emp, cm, 'f1_native', pi))
    meas['trace_f1_native_emp'] = rng_(seed_mean_monthly(raw, 'lgbm_trace', emp, cm, 'f1_native', pi))
    meas['trace_f1_native_cp'] = rng_(seed_mean_monthly(raw, 'lgbm_trace', cp, cm, 'f1_native', pi))
    meas['trace_fnr_cp'] = rng_(seed_mean_monthly(raw, 'lgbm_trace', cp, tm, 'fnr', pi))
    e1 = run.load('e1_metrics')
    meas['trace_tpr_cp_pooled'] = e1['zoo']['lgbm_trace']['agg']['tpr']['mean']
    meas['trace_aut_native'] = float(np.mean([r['aut_native'] for r in e1['zoo']['lgbm_trace']['per_seed']]))
    if run.has('e4_bias'):
        b = run.load('e4_bias')
        if 'random' in b:
            meas['random_f1_native'] = b['random']['f1_native_mean']
        for k, v in b.get('t0', {}).items():
            meas[f't0_{k}_fnr'] = v['fnr_range']
            meas[f't0_{k}_fpr'] = v['fpr_range']
            meas[f't0_{k}_max_unseen'] = v['max_unseen_fnr']
    if run.has('e11_ember2018'):
        e11 = run.load('e11_ember2018')
        if not e11.get('skipped'):
            pc = e11.get('published_check', {})
            meas['ember_release_auc'] = pc.get('auc')
            meas['ember_release_tpr_0p1'] = pc.get('tpr_at_0p1')
            meas['ember_release_tpr_1'] = pc.get('tpr_at_1')
            meas['within_ember_aut_cp1'] = e11['within']['aut'].get(f'cp{cfg["thresholds"]["certified_tau"][1]:g}')
    if run.has('e7_assurance'):
        ft = run.load('e7_assurance').get('flips_total', {})
        meas['malware_regress_rate'] = ft.get('malware_regress_rate')
        meas['benign_flip_rate'] = ft.get('benign_flip_rate')
    rows = []
    for row in pub['comparisons']:
        val = meas.get(row['measured'])
        p = row['published']
        if val is None:
            rows.append(dict(row, value=None, delta_pp=None, delta_rel=None))
            continue
        dpp, drel = deltas(val, p)
        rows.append(dict(row, value=val, delta_pp=dpp, delta_rel=drel))
    run.save('e14_compare', dict(rows=rows, measured=meas))
    log('E14 done:', len(rows), 'comparison rows')


if __name__ == '__main__':
    main()
