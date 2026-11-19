#!/usr/bin/env python3
"""E8 - secondary attribution leg (paper Section 8.8): open-set family attribution, unseen-family detection
(KB10), category back-off, H7 (open-set rejection) and P6 (decline of open-set macro-F1 vs detection F1)."""
import numpy as np
from sklearn.metrics import average_precision_score, f1_score, roc_auc_score

import _common  # noqa: F401
from _common import test_months
from tracepe.config import cli
from tracepe.evaluation.stats import wilcoxon_p
from tracepe.run import Run
from tracepe.utils import log


def main():
    cfg, args = cli(__doc__)
    run = Run(cfg)
    A = cfg['attribution']
    m = run.meta
    y = m['y'].to_numpy()
    fam = m['fam'].to_numpy()
    generic = m['generic'].to_numpy()
    cat = m['category'].to_numpy()
    split = m['split'].to_numpy()
    month = m['month'].to_numpy()
    seed = int(cfg['seeds']['f0'])
    tr = np.flatnonzero((split == 'train') & (y == 1) & ~generic)
    counts = {}
    for f in fam[tr]:
        counts[f] = counts.get(f, 0) + 1
    known = sorted(f for f, c in counts.items() if c >= int(A['min_train']))
    kidx = {f: i for i, f in enumerate(known)}
    trk = tr[np.isin(fam[tr], known)]
    yk = np.array([kidx[f] for f in fam[trk]])
    p = dict(objective='multiclass', num_class=len(known), num_leaves=A['lgbm']['num_leaves'], learning_rate=A['lgbm']['learning_rate'],
             min_data_in_leaf=A['lgbm']['min_data_in_leaf'], feature_fraction=A['lgbm'].get('feature_fraction', 0.5), seed=seed,
             deterministic=True, force_row_wise=True, num_threads=run.threads, verbose=-1)
    import lightgbm as lgb
    clf = lgb.train(p, lgb.Dataset(run.take(trk), label=yk), num_boost_round=int(A['lgbm']['rounds']))
    train_acc = float((clf.predict(run.take(trk)).argmax(axis=1) == yk).mean())
    classes = list(A['category_classes'])
    ycat_tr = np.array([classes.index(c) if c in classes else len(classes) for c in cat[tr]])
    pc = dict(p, num_class=len(classes) + 1)
    clf_cat = lgb.train(pc, lgb.Dataset(run.take(tr), label=ycat_tr), num_boost_round=int(A['lgbm']['rounds']))
    cal = np.flatnonzero((split == 'calibration') & (y == 1) & ~generic & np.isin(fam, known))
    tau_open = float(np.percentile(clf.predict(run.take(cal)).max(axis=1), float(A['open_percentile']))) if len(cal) else 0.0
    R = dict(known_families=len(known), train_files=int(len(trk)), generic_excluded=int(((split == 'train') & (y == 1) & generic).sum()),
             train_accuracy=train_acc, tau_open=tau_open, months={})
    e1 = run.load('e1_metrics')
    o_f1, c_f1, det_f1 = [], [], []
    for mo in test_months(cfg):
        rows = np.flatnonzero((split == 'test') & (month == mo) & (y == 1) & ~generic)
        if not len(rows):
            continue
        P = clf.predict(run.take(rows))
        f = fam[rows]
        is_known = np.isin(f, known)
        top = np.argsort(-P, axis=1)
        truth = np.array([kidx.get(x, -1) for x in f])
        top1 = top[:, 0] == truth
        top3 = (top[:, :3] == truth[:, None]).any(axis=1)
        maxp = P.max(axis=1)
        pred_closed = top[:, 0]
        pred_open = np.where(maxp >= tau_open, top[:, 0], -1)
        truth_open = np.where(is_known, truth, -1)
        labels = sorted(set(truth_open) | {-1})
        mf_closed = f1_score(truth_open, pred_closed, labels=labels, average='macro', zero_division=0)
        mf_open = f1_score(truth_open, pred_open, labels=labels, average='macro', zero_division=0)
        nov = (~is_known).astype(int)
        nov_auc = roc_auc_score(nov, 1 - maxp) if 0 < nov.sum() < len(nov) else None
        nov_ap = average_precision_score(nov, 1 - maxp) if nov.sum() > 0 else None
        Pc = clf_cat.predict(run.take(rows))
        yc = np.array([classes.index(c) if c in classes else len(classes) for c in cat[rows]])
        pcat = Pc.argmax(axis=1)
        R['months'][mo] = dict(non_generic=int(len(rows)), unseen_share=float(1 - is_known.mean()),
                               top1_known=float(top1[is_known].mean()) if is_known.any() else None,
                               top3_known=float(top3[is_known].mean()) if is_known.any() else None,
                               top1_all=float(top1.mean()), closed_bound=float(is_known.mean()),
                               macro_f1_closed=float(mf_closed), macro_f1_open=float(mf_open),
                               novelty_auroc=nov_auc, novelty_auprc=nov_ap, base_rate=float(nov.mean()),
                               unknowns_rejected=float((maxp[~is_known] < tau_open).mean()) if (~is_known).any() else None,
                               category_accuracy=float((pcat == yc).mean()),
                               category_macro_f1=float(f1_score(yc, pcat, average='macro', zero_division=0)))
        o_f1.append(mf_open)
        c_f1.append(mf_closed)
        det_f1.append(e1['f0_monthly'][mo]['metrics']['f1_pi'] if mo in e1['f0_monthly'] else np.nan)
    kb = R['months'].get(A['kb10_month'], {})
    R['KB10'] = dict(month=A['kb10_month'], auroc=kb.get('novelty_auroc'), auprc=kb.get('novelty_auprc'), base_rate=kb.get('base_rate'),
                     met_criteria=bool(kb and kb['novelty_auroc'] is not None and kb['novelty_auroc'] >= 0.80
                                       and kb['novelty_auprc'] >= 3 * kb['base_rate']))
    R['KB10']['kill_met'] = not R['KB10']['met_criteria']
    R['H7'] = dict(months_open_higher=int(sum(o > c for o, c in zip(o_f1, c_f1))), months=len(o_f1), p=wilcoxon_p(o_f1, c_f1),
                   mean_diff=float(np.mean(np.array(o_f1) - np.array(c_f1))) if o_f1 else None)
    t = np.arange(len(o_f1))
    ok = np.isfinite(det_f1)
    if ok.sum() >= 3:
        s_open = float(np.polyfit(t[ok], np.array(o_f1)[ok], 1)[0])
        s_det = float(np.polyfit(t[ok], np.array(det_f1)[ok], 1)[0])
        rng = np.random.default_rng(seed)
        diffs = []
        for _ in range(2000):
            i = np.sort(rng.choice(np.flatnonzero(ok), size=ok.sum(), replace=True))
            if len(set(i)) < 3:
                continue
            diffs.append(np.polyfit(t[i], np.array(o_f1)[i], 1)[0] - np.polyfit(t[i], np.array(det_f1)[i], 1)[0])
        R['P6'] = dict(slope_open=s_open, slope_detection=s_det, diff=s_open - s_det,
                       ci=[float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))] if diffs else None)
        R['P6']['falsified'] = bool(R['P6']['ci'] is None or R['P6']['ci'][0] <= 0 <= R['P6']['ci'][1] or R['P6']['diff'] > 0)
    run.save('e8_attribution', R)
    log('E8 done: known families', len(known), 'KB10', R['KB10'])


if __name__ == '__main__':
    main()
