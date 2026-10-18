#!/usr/bin/env python3
"""E9 - explanations and issuance (paper Section 8.9): exact grouped TreeSHAP, deletion faithfulness, seed
stability (KB11), gain and linear-coefficient shares; issuance of every test finding as an ISS record with
monthly epoch anchors (M7); verifier levels V1 (chain), V2 (stored objects) and V3 (re-execution)."""
import time

import numpy as np
from scipy.stats import spearmanr

import _common  # noqa: F401
from _common import certify_months, f0, primary_tau, test_months
from tracepe.assurance.simulation import Issuer, statement_valid
from tracepe.config import cli
from tracepe.decision.calibration import Isotonic
from tracepe.decision.certificates import retrospective
from tracepe.decision.conformal import ICE, kappa_for_rate
from tracepe.evaluation.stats import cliffs_delta_large
from tracepe.evidence import hashing as hh
from tracepe.evidence.ledger import verify_ledger
from tracepe.features.groups import GROUPS, GROUP_NAMES, group_of_column, group_sum
from tracepe.models.zoo import model_from_bytes
from tracepe.run import Run
from tracepe.utils import log, month_end_day


def main():
    cfg, args = cli(__doc__)
    run = Run(cfg)
    X = cfg['explain']
    e = run.emeta
    y = e['y'].to_numpy().astype(int)
    month = e['month'].to_numpy()
    split = e['split'].to_numpy()
    ev = run.eval_idx
    key0, seed0 = f0(cfg)
    store = run.store()
    models = run.load('e1_models')
    f = model_from_bytes(key0, seed0, store.get(models[key0][str(seed0)]['store'])).obj
    z0 = run.load_scores(key0, seed0)
    th = run.load('e1_metrics_raw')['thresholds'][key0][str(seed0)][f'cp{primary_tau(cfg):g}']['theta']
    R = {}
    # ---- explanation sample: month x class stratified over the certifiable months
    rng = np.random.default_rng(seed0)
    sample = []
    for mo in certify_months(cfg):
        for c in (0, 1):
            pos = np.flatnonzero((split == 'test') & (month == mo) & (y == c))
            sample.append(rng.choice(pos, size=min(int(X['per_month_class']), len(pos)), replace=False))
    sample = np.sort(np.concatenate(sample))
    Xs = run.take(ev[sample])
    t0 = time.perf_counter()
    contrib = f.predict(Xs, pred_contrib=True)
    shap_s = (time.perf_counter() - t0) / len(sample)
    G = group_sum(contrib[:, :-1])
    resid = np.abs(G.sum(axis=1) + contrib[:, -1] - z0[sample])
    gain = f.feature_importance('gain')
    gcol = group_of_column()
    gain_g = np.array([gain[gcol == g].sum() for g in range(9)])
    # linear model coefficients on signed-log standardised inputs
    lr_share = None
    if 'lr' in models:
        lr = model_from_bytes('lr', int(next(iter(models['lr']))), store.get(next(iter(models['lr'].values()))['store'])).obj
        coef = np.abs(lr.named_steps['clf'].coef_.ravel())
        lr_share = [float(coef[gcol == g].sum() / coef.sum()) for g in range(9)]
    # deletion faithfulness: replace a group by its benign training median
    tr = run.rows(split='train')
    Xtr = run.take(tr)
    med = np.median(Xtr[run.meta['y'].to_numpy()[tr] == 0], axis=0).astype(np.float32)
    del Xtr
    dmarg = np.zeros((len(sample), 9))
    for g, (_, a, b) in enumerate(GROUPS):
        Xd = Xs.copy()
        Xd[:, a:b] = med[a:b]
        dmarg[:, g] = np.abs(z0[sample] - f.predict(Xd, raw_score=True))
    rhos = []
    for i in range(len(sample)):
        r = spearmanr(np.abs(G[i]), dmarg[i])[0]
        if np.isfinite(r):
            rhos.append(r)
    absG = np.abs(G).mean(axis=0)
    R['groups'] = [dict(group=GROUP_NAMES[g], mean_abs_shap=float(absG[g]), shap_share=float(absG[g] / absG.sum()),
                        gain_share=float(gain_g[g] / gain_g.sum()), lr_share=lr_share[g] if lr_share else None,
                        mean_abs_delta_on_deletion=float(dmarg[:, g].mean())) for g in range(9)]
    top = np.argsort(-gain)[:15]
    R['top_gain_features'] = [dict(column=int(j), group=GROUP_NAMES[gcol[j]], offset=int(j - GROUPS[gcol[j]][1]),
                                   gain_share=float(gain[j] / gain.sum())) for j in top]
    R['shap'] = dict(findings=int(len(sample)), ms_per_finding=round(shap_s * 1000, 3), max_local_accuracy_residual=float(resid.max()),
                     faithfulness_spearman_mean=float(np.mean(rhos)) if rhos else None,
                     faithfulness_spearman_median=float(np.median(rhos)) if rhos else None)
    # ---- KB11: stability of the top-3 groups across the LGBM-TRACE seeds, correct vs wrong findings
    k3 = int(X['stability_top'])
    sets0 = [set(np.argsort(-np.abs(G[i]))[:k3]) for i in range(len(sample))]
    jac = np.zeros(len(sample))
    others = [s for s in models[key0] if int(s) != seed0]
    for s in others:
        fs = model_from_bytes(key0, int(s), store.get(models[key0][s]['store'])).obj
        Gs = group_sum(fs.predict(Xs, pred_contrib=True)[:, :-1])
        for i in range(len(sample)):
            si = set(np.argsort(-np.abs(Gs[i]))[:k3])
            jac[i] += len(si & sets0[i]) / len(si | sets0[i])
    if others:
        jac /= len(others)
        wrong = (z0[sample] > th).astype(int) != y[sample]
        delta = cliffs_delta_large(jac[~wrong], jac[wrong]) if wrong.any() and (~wrong).any() else None
        R['KB11'] = dict(jaccard_correct=float(jac[~wrong].mean()) if (~wrong).any() else None,
                         jaccard_wrong=float(jac[wrong].mean()) if wrong.any() else None, n_wrong=int(wrong.sum()),
                         cliffs_delta=delta, met=bool(delta is not None and delta >= 0.147))
    else:
        R['KB11'] = dict(met=None, note='needs more than one LGBM-TRACE seed')
    # ---- issuance (M7): every test finding, ICE credibility vs December, certificate state, top-5 grouped SHAP
    cal = split == 'calibration'
    iso = Isotonic().fit(z0[cal], y[cal])
    ice = ICE().fit(iso.predict(z0[cal]), y[cal])
    yh_cal = (z0[cal] > th).astype(int)
    kappa = kappa_for_rate(ice.credibility(iso.predict(z0[cal]), yh_cal), cfg['conformal']['max_abstention'])
    tf, tn = cfg['thresholds']['joint_tolerances'][0]
    Lday = int(cfg['assurance']['primary_L'])
    certs = []
    for mo in [cfg['screen']['calibration_month']] + test_months(cfg):
        mk = (split == ('calibration' if mo == cfg['screen']['calibration_month'] else 'test')) & (month == mo)
        yy, pp = y[mk], (z0[mk] > th).astype(int)
        c = retrospective(int(((pp == 1) & (yy == 0)).sum()), int((yy == 0).sum()), int(((pp == 0) & (yy == 1)).sum()),
                          int((yy == 1).sum()), tf, tn, int(cfg['screen']['n_min_benign']))
        c['month'] = mo
        c['avail'] = -10 ** 9 if mo == cfg['screen']['calibration_month'] else month_end_day(mo) + Lday
        certs.append(c)
    iss_obj = Issuer(0, 0, cfg['screen']['calibration_month'], th, 0, True, kappa, {}, None, None, None, None, certs=certs)
    tree = models[key0][str(seed0)]['identity']['tree_sha256']
    test = np.flatnonzero(split == 'test')
    L = run.ledger()
    write = not any(ep.startswith('iss-') for ep in L.epochs)   # append-only: issue once
    if not write:
        log('ISS records already anchored: states recomputed, ledger not re-appended')
    t0 = time.perf_counter()
    states = {}
    meta = run.meta
    vh = meta['vh'].to_numpy()
    sid = meta['sid'].to_numpy()
    day = e['day'].to_numpy()
    for mo in test_months(cfg):
        pos = test[month[test] == mo]
        if not len(pos):
            continue
        C = f.predict(run.take(ev[pos]), pred_contrib=True)
        Gm = group_sum(C[:, :-1])
        zz = z0[pos]
        p1 = iso.predict(zz)
        yh = (zz > th).astype(int)
        cr = ice.credibility(p1, yh)
        for j, i in enumerate(pos):
            if cr[j] < kappa:
                st = 'ABS'
            elif statement_valid(iss_obj, int(day[i]), int(cfg['assurance']['A_max'])):
                st = 'ISS'
            else:
                st = 'SCR'
            states[st] = states.get(st, 0) + 1
            order = np.argsort(-np.abs(Gm[j]))[:int(X['top_k'])]
            r = ev[i]
            if not write:
                continue
            L.append(dict(t='ISS', sid=sid[r], vh=vh[r], model=tree, theta=hh.f64hex(th), z=hh.f64hex(zz[j]), s=hh.f32hex(zz[j]),
                          yhat=int(yh[j]), cred=hh.f32hex(cr[j]), state=st, month=mo,
                          xg=[[int(g), hh.f32hex(Gm[j, g])] for g in order], b0=hh.f64hex(C[j, -1]),
                          res=hh.f64hex(abs(Gm[j].sum() + C[j, -1] - zz[j]))))
        if write:
            L.anchor(f'iss-{mo}')
    R['issuance'] = dict(records=int(len(test)), seconds=round(time.perf_counter() - t0, 2), states=states, kappa=kappa,
                         appended=write)
    # ---- V1 / V2 / V3
    t0 = time.perf_counter()
    v1 = verify_ledger(run.ledger_path)
    R['V1'] = dict(ok=v1['ok'], records=v1['records'], anchors=v1['anchors'], seconds=round(time.perf_counter() - t0, 3))
    R['V2'] = store.verify_all()
    from tracepe.evidence.ledger import find_records
    iss = find_records(run.ledger_path, lambda r: r.get('t') == 'ISS')
    pick = rng.choice(len(iss), size=min(int(X['reexec_sample']), len(iss)), replace=False)
    rowmap = {s: i for i, s in enumerate(sid)}
    ok_vh = ok_z = ok_shap = 0
    for k in pick:
        rec = iss[k][1]
        r = rowmap[rec['sid']]
        x = np.asarray(run.X[r], dtype=np.float32)
        ok_vh += hh.vector_hash(x) == rec['vh']
        zz = f.predict(x[None, :], raw_score=True)[0]
        ok_z += hh.f64hex(zz) == rec['z']
        c = f.predict(x[None, :], pred_contrib=True)[0]
        ok_shap += abs(c.sum() - zz) <= float(X['eps_num'])
    R['V3'] = dict(sampled=int(len(pick)), vector_hash=int(ok_vh), margin_bit_identical=int(ok_z), shap_local_accuracy=int(ok_shap))
    run.save('e9_explain_issue', R)
    log('E9 done: V1', R['V1'], 'V3', R['V3'], 'KB11', R['KB11'].get('met'))


if __name__ == '__main__':
    main()
