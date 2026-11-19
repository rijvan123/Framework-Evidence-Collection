#!/usr/bin/env python3
"""E2 - time-indexed error certificates of f0 (Eq. (88); paper certificates table, panel 1), statement
validity (KS1), censored benign strata (KB5), spike-day malware and the k = 4 spike-rule sensitivity."""
import numpy as np

import _common  # noqa: F401
from _common import certify_months, f0, test_months
from tracepe.config import cli
from tracepe.decision.certificates import certificate_record, retrospective
from tracepe.decision.thresholds import cp_upper
from tracepe.evaluation import metrics as M
from tracepe.run import Run
from tracepe.utils import log


def main():
    cfg, args = cli(__doc__)
    run = Run(cfg)
    e = run.emeta
    y = e['y'].to_numpy().astype(int)
    month = e['month'].to_numpy()
    split = e['split'].to_numpy()
    stratum = e['stratum'].to_numpy()
    key0, seed0 = f0(cfg)
    s0 = run.load_scores(key0, seed0)
    raw = run.load('e1_metrics_raw')
    ths = raw['thresholds'][key0][str(seed0)]
    taus = cfg['thresholds']['certified_tau'][:2]
    tols = cfg['thresholds']['joint_tolerances']
    cal_m = cfg['screen']['calibration_month']
    periods = [cal_m] + test_months(cfg)
    cm = certify_months(cfg)
    n_min = int(cfg['screen']['n_min_benign'])
    L = run.ledger()
    write = not L.has_epoch('e2-certificates')         # the ledger is append-only: record once
    if not write:
        log('CERT records already anchored (epoch e2-certificates): outputs recomputed, ledger not re-appended')
    tree = run.load('e1_models')[key0][str(seed0)]['identity'].get('tree_sha256')
    R = dict(model=[key0, seed0], tree_sha256=tree, thresholds={}, certificates={}, svr={}, censored={}, spike_malware={},
             k_sensitivity={})
    for tau, (tf, tn) in zip(taus, tols):
        r = f'cp{tau:g}'
        th = ths[r]
        R['thresholds'][r] = th
        certs = {}
        for p in periods:
            mk = (split == ('calibration' if p == cal_m else 'test')) & (month == p)
            c = M.counts(s0[mk], y[mk], th['theta'])
            cert = retrospective(c['fp'], c['fp'] + c['tn'], c['fn'], c['fn'] + c['tp'], tf, tn, n_min=0)
            cert['fpr_ub_reportable'] = (c['fp'] + c['tn']) >= n_min
            cert['in_certify_months'] = p in cm
            certs[p] = cert
            if write:
                L.append(certificate_record(f'{key0}/s{seed0}/{tree[:16] if tree else ""}', p, 'Dated', cert, th['theta'],
                                            'calibration' if p == cal_m else 'retrospective'))
        R['certificates'][r] = certs
        valid = [certs[p]['valid'] for p in cm]
        R['svr'][r] = dict(tau_fpr=tf, tau_fnr=tn, valid_months=sum(valid), months=len(cm),
                           svr=sum(valid) / len(cm) if cm else None,
                           fpr_only_valid=sum(certs[p]['fpr_ok'] for p in cm),
                           fnr_only_valid=sum(certs[p]['fnr_ok'] for p in test_months(cfg)), fnr_months=len(test_months(cfg)),
                           valid_list=[p for p in cm if certs[p]['valid']])
    # KS1: statement-validity rate at the second certified threshold
    r1 = f'cp{taus[1]:g}'
    R['KS1'] = dict(svr=R['svr'][r1]['svr'], valid=R['svr'][r1]['valid_months'], months=R['svr'][r1]['months'],
                    met=R['svr'][r1]['valid_months'] >= int(np.ceil(0.75 * len(cm))) if len(cm) == 7 else
                    R['svr'][r1]['svr'] >= 6 / 7)

    # censored benign strata (Placeholder, Bulk) against the dated benign files of the same month (KB5)
    th0 = ths[f'cp{taus[0]:g}']['theta']
    rng = np.random.default_rng(int(cfg['seeds']['bootstrap']))
    B = int(cfg['bootstrap_B'])
    kb5 = []
    for st in ('Placeholder', 'Bulk'):
        for mo in sorted(set(month[stratum == st])):
            cen = (stratum == st) & (month == mo) & (y == 0)
            dat = (split == 'test') & (month == mo) & (y == 0)
            fp_c, n_c = int((s0[cen] > th0).sum()), int(cen.sum())
            fp_d, n_d = int((s0[dat] > th0).sum()), int(dat.sum())
            fpr_d = fp_d / n_d if n_d else float('nan')
            pooled = (fp_c + fp_d) / (n_c + n_d) if (n_c + n_d) else float('nan')
            boot = rng.binomial(n_d, fpr_d, size=B) / n_d if n_d else np.zeros(B)
            half = float((np.percentile(boot, 97.5) - np.percentile(boot, 2.5)) / 2)
            shift = pooled - fpr_d
            ent = dict(stratum=st, dated_benign=n_d, fpr_dated=fpr_d, censored_benign=n_c, fp_censored=fp_c,
                       fpr_censored=fp_c / n_c if n_c else None, fpr_censored_ub=cp_upper(fp_c, n_c),
                       fpr_pooled=pooled, shift=shift, bootstrap_half_width=half, shift_exceeds=bool(shift > half),
                       degenerate=bool(half == 0))
            R['censored'][f'{st}:{mo}'] = ent
            kb5.append(ent)
    exceed = [k for k in kb5 if k['shift_exceeds']]
    # 'degenerate': every exceeding comparison has a zero bootstrap half-width (no dated false positives)
    R['KB5'] = dict(met=bool(exceed), degenerate=bool(exceed) and all(k['degenerate'] for k in exceed),
                    exceeding=[k['stratum'] for k in exceed])
    # spike-day malware (R-S1)
    for mo in sorted(set(month[stratum == 'SpikeMal'])):
        sp = (stratum == 'SpikeMal') & (month == mo)
        dat = (split == 'test') & (month == mo) & (y == 1)
        fn_s, n_s = int((s0[sp] <= th0).sum()), int(sp.sum())
        fn_d, n_d = int((s0[dat] <= th0).sum()), int(dat.sum())
        R['spike_malware'][mo] = dict(files=n_s, fnr_spike=fn_s / n_s if n_s else None, fnr_dated=fn_d / n_d if n_d else None,
                                      fnr_pooled=(fn_s + fn_d) / (n_s + n_d) if (n_s + n_d) else None)
    # k-sensitivity spike rule: rows on extra spike days removed from the dated stream
    m = run.meta
    extra = m.loc[m['spike_sens'] & ~m['censored'] & (m['split'] == 'test'), 'month'].unique()
    for mo in sorted(extra):
        base = (split == 'test') & (month == mo)
        ex = base & ~e['spike_sens'].to_numpy()
        for tag, mk in (('primary', base), ('sensitivity', ex)):
            mt = M.point_metrics(s0[mk], y[mk], th0)
            R['k_sensitivity'].setdefault(mo, {})[tag] = dict(files=int(mk.sum()), fnr=mt['fnr'], fpr=mt['fpr'], f1_native=mt['f1_native'])
    if write:
        L.anchor('e2-certificates')
    run.save('e2_certificates', R)
    log('E2 done: SVR', {k: (v['valid_months'], v['months']) for k, v in R['svr'].items()}, 'KS1', R['KS1']['met'])


if __name__ == '__main__':
    main()
