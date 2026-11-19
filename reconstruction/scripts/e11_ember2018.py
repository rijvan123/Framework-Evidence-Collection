#!/usr/bin/env python3
"""E11 - EMBER-2018 corroboration (deviation D10; paper Section 8.10): month-stratified sub-sample vectorised
with the EMBER v2 extractor, pipeline check of the published model, within-EMBER temporal certificates,
random-split inflation, forward transfer to BODMAS and backward application of f0. Skipped when the data are absent."""
import numpy as np

import _common  # noqa: F401
from _common import certify_months, f0
from tracepe.config import cli, resolve
from tracepe.data.ember import ember_files, read_lines, scan_jsonl, vectorize
from tracepe.decision.certificates import retrospective
from tracepe.decision.thresholds import certified_threshold
from tracepe.evaluation import metrics as M
from tracepe.evaluation.stats import boot_mean_ci
from tracepe.models import lgbm as LG
from tracepe.models.zoo import load_published, model_from_bytes
from tracepe.run import Run
from tracepe.utils import log, month_list


def tpr_at_test_fpr(s, y, fpr):
    ben = np.sort(s[y == 0])[::-1]
    k = int(np.floor(fpr * len(ben)))
    th = ben[min(k, len(ben) - 1)]
    return float((s[y == 1] > th).mean())


def main():
    cfg, args = cli(__doc__)
    run = Run(cfg)
    E = cfg['ember2018']
    d = resolve(cfg['data']['ember2018_dir'])
    files = ember_files(d) if d.exists() else []
    if not files:
        run.save('e11_ember2018', dict(skipped=True, reason=f'no EMBER-2018 JSON lines in {d}'))
        log('E11 skipped: EMBER-2018 data not found')
        return
    tau0, tau1 = cfg['thresholds']['certified_tau'][:2]
    pi = cfg['prevalence']['report']
    seed = int(E['seed'])
    log('scan', [f.name for f in files])
    rows = scan_jsonl(files)
    rng = np.random.default_rng(seed)
    months = month_list(E['train_months'][0], E['test_months'][1])
    sel = {}
    for mo in months:
        for lab in (0, 1):
            cand = [r for r in rows if r[3] == mo and r[2] == lab]
            k = min(int(E['per_class_month']), len(cand))
            for i in rng.choice(len(cand), size=k, replace=False):
                p, ln = cand[i][0], cand[i][1]
                sel.setdefault(p, []).append(ln)
    for p in sel:
        sel[p] = sorted(sel[p])
    raws = read_lines(sel)
    log(f'vectorise {len(raws)} files')
    Xe = vectorize(raws)
    ye = np.array([r['label'] for r in raws])
    me = np.array([r['appeared'] for r in raws])
    she = np.array([r['sha256'] for r in raws])
    R = dict(files=int(len(raws)), per_month={mo: dict(benign=int(((me == mo) & (ye == 0)).sum()), malware=int(((me == mo) & (ye == 1)).sum()))
                                              for mo in months})
    # pipeline check with the published model on the check months (test-tuned thresholds, as in the release notebook)
    pub = load_published(resolve(cfg['data']['ember2018_model']))
    chk = np.isin(me, month_list(*E['check_months']))
    if pub is not None and chk.any():
        s = pub.score(Xe[chk])
        R['published_check'] = dict(auc=M.auc(s, ye[chk]), tpr_at_0p1=tpr_at_test_fpr(s, ye[chk], 0.001), tpr_at_1=tpr_at_test_fpr(s, ye[chk], 0.01))
    # within-EMBER temporal protocol
    trm = np.isin(me, month_list(*E['train_months']))
    calm = np.isin(me, month_list(*E['cal_months']))
    test_ms = month_list(*E['test_months'])
    b = LG.train_lgbm(Xe[trm], ye[trm], cfg['models']['lgbm_trace'], seed, run.threads)
    z = LG.margin(b, Xe)
    th = {t: certified_threshold(z[calm & (ye == 0)], t)['theta'] for t in (tau0, tau1)}
    mon = {}
    for mo in month_list(*E['cal_months'])[:1] + test_ms:
        mk = (me == mo) if mo in test_ms else calm
        ent = dict(benign=int((ye[mk] == 0).sum()), malware=int((ye[mk] == 1).sum()), auc=M.auc(z[mk], ye[mk]))
        for t in (tau0, tau1):
            mt = M.point_metrics(z[mk], ye[mk], th[t], pi)
            ent[f'cp{t:g}'] = dict(fnr=mt['fnr'], fpr=mt['fpr'], f1_pi=mt['f1_pi'])
        mon['cal' if mo not in test_ms else mo] = ent
    R['within'] = dict(months=mon, aut={f'cp{t:g}': M.aut([mon[mo][f'cp{t:g}']['f1_pi'] for mo in test_ms]) for t in (tau0, tau1)})
    tols = cfg['thresholds']['joint_tolerances']
    R['within']['svr'] = {}
    for t, (tf, tn) in zip((tau0, tau1), tols):
        valid = 0
        for mo in test_ms:
            mk = me == mo
            yy, pp = ye[mk], z[mk] > th[t]
            c = retrospective(int((pp & (yy == 0)).sum()), int((yy == 0).sum()), int((~pp & (yy == 1)).sum()), int((yy == 1).sum()), tf, tn, 0)
            valid += c['valid']
        R['within']['svr'][f'cp{t:g}'] = dict(valid=int(valid), months=len(test_ms))
    # random-split inflation (same sizes as the temporal training and calibration sets)
    pooled = np.flatnonzero(trm | calm | np.isin(me, test_ms))
    infl = []
    for sd in cfg['bias']['random_seeds']:
        r = np.random.default_rng(sd)
        perm = r.permutation(pooled)
        ntr, ncal = int(trm.sum()), int(calm.sum())
        tr_i, cal_i, te_i = perm[:ntr], perm[ntr:ntr + ncal], perm[ntr + ncal:]
        bb = LG.train_lgbm(Xe[np.sort(tr_i)], ye[np.sort(tr_i)], cfg['models']['lgbm_trace'], sd, run.threads)
        thr = certified_threshold(LG.margin(bb, Xe[cal_i])[ye[cal_i] == 0], tau0)['theta']
        f1r = M.point_metrics(LG.margin(bb, Xe[te_i]), ye[te_i], thr, pi)['f1_pi']
        infl.append(f1r - R['within']['aut'][f'cp{tau0:g}'])
    R['random_inflation'] = dict(values=infl, mean=float(np.mean(infl)), ci=boot_mean_ci(infl, seed=4))
    # forward transfer: EMBER-trained model certified on BODMAS December, tested on BODMAS certifiable months
    e = run.emeta
    yb = e['y'].to_numpy()
    sb = np.empty(len(run.eval_idx))
    for s_ in range(0, len(run.eval_idx), 20000):
        sb[s_:s_ + 20000] = b.predict(np.asarray(run.X[run.eval_idx[s_:s_ + 20000]], dtype=np.float32), raw_score=True)
    calb = e['split'].to_numpy() == 'calibration'
    thb = certified_threshold(sb[calb & (yb == 0)], tau0)['theta']
    f1s, fnrs = [], []
    for mo in certify_months(cfg):
        mk = (e['split'].to_numpy() == 'test') & (e['month'].to_numpy() == mo)
        mt = M.point_metrics(sb[mk], yb[mk], thb, pi)
        f1s.append(mt['f1_pi'])
        fnrs.append(mt['fnr'])
    R['forward_transfer'] = dict(aut=M.aut(f1s), fnr_range=[min(fnrs), max(fnrs)], monthly_fnr=fnrs)
    # backward application of f0 (violates C1; descriptive) and SHA-256 overlap
    key0, seed0 = f0(cfg)
    f = model_from_bytes(key0, seed0, run.store().get(run.load('e1_models')[key0][str(seed0)]['store'])).obj
    zf = LG.margin(f, Xe)
    R['backward_f0_auc'] = {mo: M.auc(zf[me == mo], ye[me == mo]) for mo in months if (me == mo).any()}
    R['sha_overlap_with_bodmas'] = int(len(set(she) & set(run.meta['sid'])))
    run.save('e11_ember2018', R)
    log('E11 done: published check', R.get('published_check'), 'within AUT', R['within']['aut'])


if __name__ == '__main__':
    main()
