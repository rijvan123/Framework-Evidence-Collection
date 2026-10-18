#!/usr/bin/env python3
"""E5 - error structure of f0 (entropy strata, P10; unseen vs known families, H3; families behind the
July-September decay) and Jensen-Shannon feature drift (Eqs. (74)-(75); P5)."""
import numpy as np

import _common  # noqa: F401
from _common import certify_months, f0, primary_tau, test_months
from tracepe.config import cli
from tracepe.drift.js import drift, histograms, quantile_edges
from tracepe.evaluation.stats import a12, fisher_or, spearman, wilcoxon_p
from tracepe.features.groups import high_entropy_mass, packing_indicator
from tracepe.run import Run
from tracepe.utils import log


def main():
    cfg, args = cli(__doc__)
    run = Run(cfg)
    e = run.emeta
    y = e['y'].to_numpy().astype(int)
    month = e['month'].to_numpy()
    split = e['split'].to_numpy()
    fam = e['fam'].to_numpy()
    key0, seed0 = f0(cfg)
    z = run.load_scores(key0, seed0)
    th = run.load('e1_metrics_raw')['thresholds'][key0][str(seed0)][f'cp{primary_tau(cfg):g}']['theta']
    pred = z > th
    cm, tms = certify_months(cfg), test_months(cfg)
    pool = (split == 'test') & np.isin(month, cm)
    ev = run.eval_idx
    R = dict(entropy={}, families={}, decay_families={}, drift={})
    # ---- P10: entropy strata (Eq. (19) indicator, tau_p = 1/32; mass definition > 0.5)
    Xp = run.take(ev[pool])
    defs = {'eq19_tau_1_32': packing_indicator(Xp, 1 / 32), 'mass_top2_bins_gt_0p5': high_entropy_mass(Xp) > 0.5}
    yp, pp = y[pool], pred[pool]
    for name, hi in defs.items():
        ent = {}
        for err, cls, wrong in (('FNR', 1, ~pp), ('FPR', 0, pp)):
            a = int((hi & (yp == cls) & wrong).sum()); n1 = int((hi & (yp == cls)).sum())
            c = int((~hi & (yp == cls) & wrong).sum()); n2 = int((~hi & (yp == cls)).sum())
            ent[err] = dict(high_errors=a, high_n=n1, low_errors=c, low_n=n2,
                            high_rate=a / n1 if n1 else None, low_rate=c / n2 if n2 else None,
                            **fisher_or(a, n1 - a, c, n2 - c))
        R['entropy'][name] = ent
    fnr_or = R['entropy']['eq19_tau_1_32']['FNR']
    fpr_or = R['entropy']['eq19_tau_1_32']['FPR']
    R['P10'] = dict(fnr_holds=bool(fnr_or['ci'][0] > 1), fpr_holds=bool(fpr_or['ci'][0] > 1))
    # ---- H3: unseen vs known families
    m = run.meta
    tr = run.rows(split='train')
    seen = set(m['fam'].to_numpy()[tr][m['y'].to_numpy()[tr] == 1])
    fu, fk = [], []
    for mo in tms:
        mk = (split == 'test') & (month == mo) & (y == 1)
        un = mk & ~np.isin(fam, list(seen))
        kn = mk & np.isin(fam, list(seen))
        r = dict(unseen=int(un.sum()), fnr_unseen=float((~pred & un).sum() / un.sum()) if un.any() else None,
                 known=int(kn.sum()), fnr_known=float((~pred & kn).sum() / kn.sum()) if kn.any() else None)
        R['families'][mo] = r
        if r['fnr_unseen'] is not None and r['fnr_known'] is not None:
            fu.append(r['fnr_unseen'])
            fk.append(r['fnr_known'])
    R['H3'] = dict(wilcoxon_p=wilcoxon_p(fu, fk), a12=a12(fu, fk), months_unseen_higher=int(sum(a > b for a, b in zip(fu, fk))))
    R['H3']['met'] = bool(R['H3']['wilcoxon_p'] < 0.05 and R['H3']['a12'] > 0.71)
    # ---- families behind the July-September errors
    late = (split == 'test') & np.isin(month, [mo for mo in tms if mo >= cfg['monitor']['onset_from'][:7]]) & (y == 1)
    fn_late = late & ~pred
    tot = int(fn_late.sum())
    rows = []
    for f in set(fam[late]):
        mk = late & (fam == f)
        rows.append(dict(family=f, seen=f in seen, files=int(mk.sum()), fn=int((mk & ~pred).sum()),
                         fnr=float((mk & ~pred).sum() / mk.sum()), share=float((mk & ~pred).sum() / tot) if tot else None))
    rows.sort(key=lambda r: -r['fn'])
    R['decay_families'] = dict(top=rows[:8], total_files=int(late.sum()), total_fn=tot,
                               fn_from_seen=int(sum(r['fn'] for r in rows if r['seen'])))
    # ---- drift relative to the training window (20 training-quantile bins)
    Xtr = run.take(tr)
    ytr = m['y'].to_numpy()[tr]
    bins = int(cfg['drift']['js_bins'])
    edges = quantile_edges(Xtr, bins)
    ref = {'pooled': histograms(Xtr, edges), 'benign': histograms(Xtr[ytr == 0], edges), 'malware': histograms(Xtr[ytr == 1], edges)}
    del Xtr
    e1 = run.load('e1_metrics')
    for mo in [cfg['screen']['calibration_month']] + tms:
        mk = ((split == 'calibration') if mo == cfg['screen']['calibration_month'] else (split == 'test')) & (month == mo)
        Xm = run.take(ev[mk])
        ym = y[mk]
        ent = {}
        for tag, sel in (('pooled', np.ones(len(ym), bool)), ('benign', ym == 0), ('malware', ym == 1)):
            if sel.sum() == 0:
                ent[tag] = None
                continue
            d = drift(ref[tag], Xm[sel], edges)
            ent[tag] = d['pooled']
            if tag == 'pooled':
                ent['groups'] = d['groups']
        ent['fnr'] = e1['f0_monthly'][mo]['metrics']['fnr']
        ent['f1_pi'] = e1['f0_monthly'][mo]['metrics']['f1_pi']
        R['drift'][mo] = ent
    dp = [R['drift'][mo]['pooled'] for mo in cm]
    f1 = [R['drift'][mo]['f1_pi'] for mo in cm]
    R['P5'] = spearman(dp, f1, seed=5)
    R['P5']['falsified'] = bool(R['P5']['rho'] >= 0 or (R['P5']['ci'][1] is not None and R['P5']['ci'][1] > -0.1))
    R['exploratory_malware_drift_vs_fnr'] = spearman([R['drift'][mo]['malware'] for mo in cm], [R['drift'][mo]['fnr'] for mo in cm], seed=6)
    run.save('e5_errors_drift', R)
    log('E5 done: P10', R['P10'], 'H3', R['H3'], 'P5 rho', round(R['P5']['rho'], 3))


if __name__ == '__main__':
    main()
