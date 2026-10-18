#!/usr/bin/env python3
"""E4 - experimental-bias controls (paper bias table): random vs temporal split (P1), static 80:20 vs temporal
certificates (KB4), random 5-fold CV, BODMAS Table III replication (T0), COFF-timestamp ablation (H9),
pre-window benign files, pre-split leakage (P3, memory-safe: D18) and monotone-scaling invariance (P9)."""
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import LinearSVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier

import _common  # noqa: F401
from _common import certify_months, f0, margin_rows, primary_tau, test_months
from tracepe.config import cli
from tracepe.decision.thresholds import certified_threshold, empirical_threshold
from tracepe.evaluation import metrics as M
from tracepe.evaluation.stats import boot_mean_ci, delong
from tracepe.models import lgbm as LG
from tracepe.models.zoo import fit_model
from tracepe.run import Run
from tracepe.utils import log, month_list


def tm(cfg):
    return test_months(cfg)


def certify(scores_cal, y_cal, tau):
    return certified_threshold(scores_cal[y_cal == 0], tau)['theta']


def f1pi(scores, y, theta, pi):
    return M.point_metrics(scores, y, theta, pi)


def random_arm(run, cfg, R, e1):
    m = run.meta
    pooled = run.rows(split=['train', 'calibration', 'test'])
    n_tr, n_cal = len(run.rows(split='train')), len(run.rows(split='calibration'))
    y_all = m['y'].to_numpy()
    tau, pi = primary_tau(cfg), cfg['prevalence']['report']
    rows = []
    per_seed_aut = {r['seed']: r for r in e1['zoo']['lgbm_trace']['per_seed']}
    for seed in cfg['bias']['random_seeds']:
        rng = np.random.default_rng(seed)
        perm = rng.permutation(pooled)
        tr, cal, te = np.sort(perm[:n_tr]), np.sort(perm[n_tr:n_tr + n_cal]), np.sort(perm[n_tr + n_cal:])
        b = LG.train_lgbm(run.take(tr), y_all[tr], cfg['models']['lgbm_trace'], seed, run.threads)
        th = certify(LG.margin(b, run.take(cal)), y_all[cal], tau)
        z = margin_rows(b, run, te)
        mt = f1pi(z, y_all[te], th, pi)
        temporal = per_seed_aut.get(seed, {})
        rows.append(dict(seed=seed, f1_pi=mt['f1_pi'], f1_native=mt['f1_native'], fnr=mt['fnr'], fpr=mt['fpr'],
                         temporal_aut=temporal.get('aut'), temporal_aut_native=temporal.get('aut_native'),
                         inflation=(mt['f1_pi'] - temporal['aut']) if temporal.get('aut') is not None else None))
        log(f'  random arm seed {seed}: F1@pi {mt["f1_pi"]:.4f} vs temporal AUT {temporal.get("aut")}')
    infl = [r['inflation'] for r in rows if r['inflation'] is not None]
    aut = [r['temporal_aut'] for r in rows if r['temporal_aut'] is not None]
    R['random'] = dict(seeds=rows, inflation_mean=float(np.mean(infl)) if infl else None, inflation_ci=boot_mean_ci(infl, seed=3),
                       relative=float(np.mean(infl) / np.mean(aut)) if infl else None,
                       f1_native_mean=float(np.mean([r['f1_native'] for r in rows])))
    R['P1'] = dict(falsified=bool(not infl or np.mean(infl) < 0.02 or R['random']['inflation_ci'][0] <= 0))


def static_arm(run, cfg, R, e1):
    """KB4: 5 x 80:20 rotations of the training window (out-of-fold), December-certified threshold per fold model."""
    m = run.meta
    tr = run.rows(split='train')
    cal = run.rows(split='calibration')
    y = m['y'].to_numpy()
    seed = int(cfg['seeds']['f0'])
    tau = primary_tau(cfg)
    Xc = run.take(cal)
    oof_pred = np.zeros(len(tr), int)
    for k, (a, b) in enumerate(StratifiedKFold(5, shuffle=True, random_state=seed).split(tr, y[tr])):
        bst = LG.train_lgbm(run.take(tr[a]), y[tr[a]], cfg['models']['lgbm_trace'], seed, run.threads)
        th = certify(LG.margin(bst, Xc), y[cal], tau)
        oof_pred[b] = (LG.margin(bst, run.take(tr[b])) > th).astype(int)
    yt = y[tr]
    fnr = float(((oof_pred == 0) & (yt == 1)).sum() / (yt == 1).sum())
    fpr = float(((oof_pred == 1) & (yt == 0)).sum() / (yt == 0).sum())
    months = {}
    for mo in certify_months(cfg):
        t = e1['f0_monthly'][mo]['metrics']
        months[mo] = dict(static_fnr=fnr, temporal_fnr=t['fnr'], static_fpr=fpr, temporal_fpr=t['fpr'],
                          understates=bool(fnr < t['fnr'] or fpr < t['fpr']))
    n_under = sum(v['understates'] for v in months.values())
    R['static'] = dict(fnr=fnr, fpr=fpr, months=months, understated_months=n_under)
    R['KB4'] = dict(met=n_under >= 5 if len(months) == 7 else n_under >= int(np.ceil(5 / 7 * len(months))), months=n_under)


def cv_arm(run, cfg, R, raw):
    m = run.meta
    pooled = run.rows(split=['train', 'calibration', 'test'])
    y = m['y'].to_numpy()
    seed = int(cfg['seeds']['f0'])
    tau, pi = primary_tau(cfg), cfg['prevalence']['report']
    cm = certify_months(cfg)
    out = {}
    c2 = dict(cfg)
    c2['models'] = dict(cfg['models'])
    for k in ('rf', 'et'):
        c2['models'][k] = dict(cfg['models'][k], n_estimators=int(cfg['bias']['cv_trees']))
    for key in cfg['bias']['cv_models']:
        folds = []
        for a, b in StratifiedKFold(int(cfg['bias']['cv_folds']), shuffle=True, random_state=seed).split(pooled, y[pooled]):
            rng = np.random.default_rng(seed + len(folds))
            a = rng.permutation(a)
            ncal = int(round(cfg['bias']['cv_cal_frac'] * len(a)))
            cal_i, tr_i = np.sort(pooled[a[:ncal]]), np.sort(pooled[a[ncal:]])
            te_i = np.sort(pooled[b])
            mdl = fit_model(key, seed, run.take(tr_i), y[tr_i], c2, t_train=m['day'].to_numpy()[tr_i], threads=run.threads)
            th = certify(mdl.score(run.take(cal_i)), y[cal_i], tau)
            mt = f1pi(mdl.score(run.take(te_i)), y[te_i], th, pi)
            folds.append(dict(f1_pi=mt['f1_pi'], fnr=mt['fnr'], fpr=mt['fpr']))
        temporal = []
        tfnr = []
        rules = raw['models'].get(key, {})
        for mo in cm:
            vals = [M.from_counts(**rules[s][mo]['counts'][f'cp{tau:g}'], pi_report=pi)['f1_pi'] for s in rules]
            fn = [M.from_counts(**rules[s][mo]['counts'][f'cp{tau:g}'], pi_report=pi)['fnr'] for s in rules]
            temporal.append(float(np.nanmean(vals)) if vals else None)
            tfnr.append(float(np.nanmean(fn)) if fn else None)
        f1s = [f['f1_pi'] for f in folds]
        out[key] = dict(folds=folds, cv_mean=float(np.nanmean(f1s)), cv_min=float(np.nanmin(f1s)), cv_max=float(np.nanmax(f1s)),
                        temporal_months=temporal, temporal_mean=float(np.nanmean([t for t in temporal if t is not None])) if temporal else None,
                        temporal_min=float(np.nanmin([t for t in temporal if t is not None])) if temporal else None,
                        temporal_max=float(np.nanmax([t for t in temporal if t is not None])) if temporal else None,
                        cv_fnr=float(np.mean([f['fnr'] for f in folds])), temporal_fnr=float(np.nanmean([t for t in tfnr if t is not None])) if tfnr else None,
                        cv_fpr=float(np.mean([f['fpr'] for f in folds])))
        out[key]['delta'] = (out[key]['cv_mean'] - out[key]['temporal_mean']) if out[key]['temporal_mean'] is not None else None
        log(f'  CV {key}: {out[key]["cv_mean"]:.4f} vs temporal {out[key]["temporal_mean"]}')
    R['cv'] = out


def t0_arm(run, cfg, R):
    """Replication of BODMAS Table III: train before 2019-10-01, 80:20 random split, empirical 0.1% threshold."""
    m = run.meta
    y = m['y'].to_numpy()
    fs_day = m['day'].to_numpy()
    from tracepe.utils import day_number
    cut = day_number(cfg['bias']['t0_cutoff'])
    stratum = m['stratum'].to_numpy()
    seed = int(cfg['seeds']['f0'])
    months = month_list(*cfg['bias']['t0_test'])
    test = np.flatnonzero((stratum == 'Dated') & (fs_day >= cut) & np.isin(m['month'].to_numpy(), months))
    fam = m['fam'].to_numpy()
    month = m['month'].to_numpy()
    out = {}
    for variant, strata in (('dated', ['Dated']), ('dated_prewindow', ['Dated', 'PreWindow'])):
        pool = np.flatnonzero(np.isin(stratum, strata) & (fs_day < cut))
        rng = np.random.default_rng(seed)
        perm = rng.permutation(pool)
        nv = int(round(0.2 * len(pool)))
        val, tr = np.sort(perm[:nv]), np.sort(perm[nv:])
        seen = set(fam[tr][y[tr] == 1])
        Xte = run.take(test)
        for key in cfg['bias']['t0_models']:
            block = cfg['models'][key]
            b = LG.train_lgbm(run.take(tr), y[tr], block, seed, run.threads)
            zv = LG.margin(b, run.take(val))
            th = empirical_threshold(zv[y[val] == 0], cfg['thresholds']['empirical_beta'][0])
            z = LG.margin(b, Xte)
            pred = z > th['theta']
            mon = {}
            for mo in months:
                mk = month[test] == mo
                yy, pp = y[test][mk], pred[mk]
                ff = fam[test][mk]
                unseen = (yy == 1) & ~np.isin(ff, list(seen))
                seen_m = (yy == 1) & np.isin(ff, list(seen))
                mon[mo] = dict(fnr=float((~pp & (yy == 1)).sum() / max((yy == 1).sum(), 1)),
                               fpr=float((pp & (yy == 0)).sum() / max((yy == 0).sum(), 1)) if (yy == 0).any() else None,
                               fnr_unseen=float((~pp & unseen).sum() / unseen.sum()) if unseen.any() else None,
                               fnr_seen=float((~pp & seen_m).sum() / seen_m.sum()) if seen_m.any() else None,
                               benign=int((yy == 0).sum()))
            fnrs = [v['fnr'] for v in mon.values()]
            fprs = [v['fpr'] for v in mon.values() if v['fpr'] is not None]
            late = [mon[mo]['fnr'] for mo in months if mo >= '2020-07']
            out[f'{variant}:{key}'] = dict(train=int(len(tr)), val=int(len(val)), theta=th['theta'], k=th['k'], months=mon,
                                           fnr_range=[min(fnrs), max(fnrs)], fpr_range=[min(fprs), max(fprs)] if fprs else None,
                                           months_fpr_above=sum(f > cfg['thresholds']['empirical_beta'][0] for f in fprs),
                                           fnr_jul_sep=[min(late), max(late)] if late else None,
                                           max_unseen_fnr=max([v['fnr_unseen'] for v in mon.values() if v['fnr_unseen'] is not None], default=None),
                                           max_seen_fnr=max([v['fnr_seen'] for v in mon.values() if v['fnr_seen'] is not None], default=None))
            log(f'  T0 {variant} {key}: FNR {out[f"{variant}:{key}"]["fnr_range"]}')
    R['t0'] = out


def coff_and_prewindow(run, cfg, R, e1):
    m = run.meta
    y = m['y'].to_numpy()
    tr = run.rows(split='train')
    seed = int(cfg['seeds']['f0'])
    tau, pi = primary_tau(cfg), cfg['prevalence']['report']
    cm = certify_months(cfg)
    e = run.emeta
    ye = e['y'].to_numpy()
    te_mask = (e['split'].to_numpy() == 'test')
    month = e['month'].to_numpy()
    ev = run.eval_idx
    # H9: without the COFF TimeDateStamp (column 626 set to a constant)
    Xtr = run.take(tr)
    Xtr[:, 626] = 0
    b = LG.train_lgbm(Xtr, y[tr], cfg['models']['lgbm_trace'], seed, run.threads)
    z = np.empty(len(ev))
    for s in range(0, len(ev), 20000):
        blk = np.asarray(run.X[ev[s:s + 20000]], dtype=np.float32).copy()
        blk[:, 626] = 0
        z[s:s + 20000] = b.predict(blk, raw_score=True)
    calm = e['split'].to_numpy() == 'calibration'
    th = certified_threshold(z[calm & (ye == 0)], tau)['theta']
    f1m, tprm = [], []
    for mo in cm:
        mk = te_mask & (month == mo)
        mt = M.point_metrics(z[mk], ye[mk], th, pi)
        f1m.append(mt['f1_pi'])
        tprm.append(mt['tpr'])
    k0, s0 = f0(cfg)
    base = next(r for r in e1['zoo'][k0]['per_seed'] if r['seed'] == s0)
    base_tpr = [e1['f0_monthly'][mo]['metrics']['tpr'] for mo in cm]
    R['coff'] = dict(aut_f1=M.aut(f1m), aut_f1_f0=base['aut'], delta_aut_f1=M.aut(f1m) - base['aut'],
                     aut_tpr=M.aut(tprm), aut_tpr_f0=M.aut(base_tpr), delta_aut_tpr=M.aut(tprm) - M.aut(base_tpr))
    R['H9'] = dict(met=abs(R['coff']['delta_aut_f1']) < 0.01)
    # pre-window benign files added to training only (TESSERACT-legal)
    pre = run.rows(stratum='PreWindow')
    pre = pre[~m['dup_drop'].to_numpy()[pre]]
    rows = np.sort(np.concatenate([tr, pre]))
    b2 = LG.train_lgbm(run.take(rows), y[rows], cfg['models']['lgbm_trace'], seed, run.threads)
    z2 = np.empty(len(ev))
    for s in range(0, len(ev), 20000):
        z2[s:s + 20000] = b2.predict(np.asarray(run.X[ev[s:s + 20000]], dtype=np.float32), raw_score=True)
    th2 = certified_threshold(z2[calm & (ye == 0)], tau)['theta']
    pool = te_mask & np.isin(month, cm)
    mt = M.point_metrics(z2[pool], ye[pool], th2, pi)
    R['prewindow'] = dict(added_benign=int(len(pre)), fnr=mt['fnr'], fp=mt['fp'], n_benign=mt['n_neg'], fpr=mt['fpr'],
                          fnr_f0=e1['zoo'][k0]['per_seed'][[r['seed'] for r in e1['zoo'][k0]['per_seed']].index(s0)]['fnr'])


# ---------------------------------------------------------------- leakage (D18: chunked statistics, float32)
def chunked_stats(run, rows, chunk=20000):
    """Mean, std, min, max of signed-log1p features over rows."""
    d = run.X.shape[1]
    s = np.zeros(d)
    ss = np.zeros(d)
    mn = np.full(d, np.inf)
    mx = np.full(d, -np.inf)
    for a in range(0, len(rows), chunk):
        Z = np.asarray(run.X[rows[a:a + chunk]], dtype=np.float32)
        Z = np.sign(Z) * np.log1p(np.abs(Z))
        s += Z.sum(axis=0, dtype=np.float64)
        ss += (Z.astype(np.float64) ** 2).sum(axis=0)
        mn = np.minimum(mn, Z.min(axis=0))
        mx = np.maximum(mx, Z.max(axis=0))
    n = len(rows)
    mu = s / n
    sd = np.sqrt(np.maximum(ss / n - mu ** 2, 0))
    return mu, sd, mn, mx


def chi2_scores(run, rows, y, mn, mx, chunk=20000):
    d = run.X.shape[1]
    obs = np.zeros((2, d))
    for a in range(0, len(rows), chunk):
        Z = np.asarray(run.X[rows[a:a + chunk]], dtype=np.float32)
        Z = np.sign(Z) * np.log1p(np.abs(Z))
        Z = np.clip((Z - mn) / np.where(mx > mn, mx - mn, 1), 0, None)
        yy = y[rows[a:a + chunk]]
        obs[1] += Z[yy == 1].sum(axis=0)
        obs[0] += Z[yy == 0].sum(axis=0)
    py = np.array([(y[rows] == 0).mean(), (y[rows] == 1).mean()])
    tot = obs.sum(axis=0)
    exp = py[:, None] * tot[None, :]
    with np.errstate(divide='ignore', invalid='ignore'):
        return np.nan_to_num(((obs - exp) ** 2 / exp).sum(axis=0))


def pca_basis(run, rows, mu, sd, var=0.95, chunk=20000):
    d = run.X.shape[1]
    cov = np.zeros((d, d))
    sdz = np.where(sd > 0, sd, 1)
    for a in range(0, len(rows), chunk):
        Z = np.asarray(run.X[rows[a:a + chunk]], dtype=np.float32)
        Z = ((np.sign(Z) * np.log1p(np.abs(Z)) - mu) / sdz).astype(np.float64)
        cov += Z.T @ Z
    cov /= max(len(rows) - 1, 1)
    w, V = np.linalg.eigh(cov)
    order = np.argsort(w)[::-1]
    w, V = w[order], V[:, order]
    k = int(np.searchsorted(np.cumsum(w) / w.sum(), var) + 1)
    return V[:, :k].astype(np.float32)


def transform(run, rows, mu, sd, sel=None, basis=None, chunk=20000):
    out = []
    sdz = np.where(sd > 0, sd, 1)
    for a in range(0, len(rows), chunk):
        Z = np.asarray(run.X[rows[a:a + chunk]], dtype=np.float32)
        Z = ((np.sign(Z) * np.log1p(np.abs(Z)) - mu) / sdz).astype(np.float32)
        if sel is not None:
            Z = Z[:, sel]
        if basis is not None:
            Z = Z @ basis
        out.append(Z)
    return np.vstack(out)


def leakage_arm(run, cfg, R):
    m = run.meta
    y = m['y'].to_numpy()
    tr = run.rows(split='train')
    alld = run.rows(split=['train', 'calibration', 'test'])
    ev = run.eval_idx
    e = run.emeta
    ye = e['y'].to_numpy()
    calm = e['split'].to_numpy() == 'calibration'
    pool = (e['split'].to_numpy() == 'test') & np.isin(e['month'].to_numpy(), certify_months(cfg))
    tau, pi = primary_tau(cfg), cfg['prevalence']['report']
    seed = int(cfg['seeds']['f0'])
    k = int(cfg['models']['select']['chi2_k'])
    stats = {'clean': chunked_stats(run, tr), 'leaky': chunked_stats(run, alld)}
    sels = {}
    for tag, rows in (('clean', tr), ('leaky', alld)):
        mu, sd, mn, mx = stats[tag]
        sels[tag] = np.sort(np.argsort(-chi2_scores(run, rows, y, mn, mx))[:k])
    bases = {tag: pca_basis(run, rows, stats[tag][0], stats[tag][1], cfg['models']['select']['pca_var'])
             for tag, rows in (('clean', tr), ('leaky', alld))}
    out = dict(shared_chi2_features=int(len(np.intersect1d(sels['clean'], sels['leaky']))),
               pca_components=dict(clean=int(bases['clean'].shape[1]), leaky=int(bases['leaky'].shape[1])), arms={})
    for model in cfg['bias']['leak_models']:
        for fit_kind in ('zscore', 'chi2', 'pca'):
            res = {}
            for tag in ('clean', 'leaky'):
                mu, sd = stats[tag][0], stats[tag][1]
                sel = sels[tag] if fit_kind == 'chi2' else None
                basis = bases[tag] if fit_kind == 'pca' else None
                Ztr = transform(run, tr, mu, sd, sel, basis)
                est = (LogisticRegression(C=cfg['models']['lr']['C'], max_iter=cfg['models']['lr']['max_iter'], class_weight='balanced')
                       if model == 'lr' else LinearSVC(C=cfg['models']['linsvm']['C'], max_iter=cfg['models']['linsvm']['max_iter'],
                                                       class_weight='balanced'))
                est.fit(Ztr, y[tr])
                z = est.decision_function(transform(run, ev, mu, sd, sel, basis))
                th = certified_threshold(z[calm & (ye == 0)], tau)['theta']
                mt = M.point_metrics(z[pool], ye[pool], th, pi)
                res[tag] = dict(z=z, auc=M.auc(z[pool], ye[pool]), aucpr=M.auc_pr_at_pi(z[pool], ye[pool], pi), fnr=mt['fnr'], f1_pi=mt['f1_pi'])
            dl = delong(ye[pool], res['leaky']['z'][pool], res['clean']['z'][pool])
            out['arms'][f'{model}:{fit_kind}'] = dict(
                auc_clean=res['clean']['auc'], auc_leaky=res['leaky']['auc'], delta_auc=res['leaky']['auc'] - res['clean']['auc'],
                delong_p=dl['p'], aucpr_clean=res['clean']['aucpr'], aucpr_leaky=res['leaky']['aucpr'],
                fnr_clean=res['clean']['fnr'], fnr_leaky=res['leaky']['fnr'], f1_clean=res['clean']['f1_pi'], f1_leaky=res['leaky']['f1_pi'])
            log(f'  leakage {model}/{fit_kind}: dAUC {out["arms"][f"{model}:{fit_kind}"]["delta_auc"]:+.5f}')
    # LightGBM under clean vs leaky z-scaling
    zs = {}
    for tag in ('clean', 'leaky'):
        mu, sd = stats[tag][0], stats[tag][1]
        b = LG.train_lgbm(transform(run, tr, mu, sd), y[tr], cfg['models']['lgbm_trace'], seed, run.threads)
        z = b.predict(transform(run, ev, mu, sd), raw_score=True)
        zs[tag] = (z, certified_threshold(z[calm & (ye == 0)], tau)['theta'])
    te = e['split'].to_numpy() == 'test'
    agree = np.mean((zs['clean'][0][te] > zs['clean'][1]) == (zs['leaky'][0][te] > zs['leaky'][1]))
    out['lgbm_zscore'] = dict(max_abs_margin_diff=float(np.max(np.abs(zs['clean'][0] - zs['leaky'][0]))), decision_agreement=float(agree))
    sel_arms = [v for kk, v in out['arms'].items() if kk.endswith(':chi2')]
    out['P3'] = dict(selection_leak_significant=any(v['delong_p'] < 0.05 and v['delta_auc'] > 0 for v in sel_arms),
                     pca_leak_inflates=any(v['delta_auc'] > 0 and v['delong_p'] < 0.05 for kk, v in out['arms'].items() if kk.endswith(':pca')))
    R['leakage'] = out


def scaling_arm(run, cfg, R):
    """P9: verdict agreement between raw and monotone-rescaled inputs (scalers fitted on the training window)."""
    m = run.meta
    y = m['y'].to_numpy()
    tr = run.rows(split='train')
    te = run.rows(split='test')
    Xtr = run.take(tr)
    seed = int(cfg['seeds']['f0'])
    mn, mx = Xtr.min(axis=0), Xtr.max(axis=0)
    mu, sd = Xtr.mean(axis=0, dtype=np.float64), Xtr.std(axis=0, dtype=np.float64)
    rng_mm = np.where(mx > mn, mx - mn, 1)
    sd_z = np.where(sd > 0, sd, 1)

    def chunked(f):
        # float32 output filled in row chunks: bounded temporary memory on the full test window (D18)
        def g(Z):
            out = np.empty(Z.shape, np.float32)
            for a in range(0, len(Z), 10000):
                out[a:a + 10000] = f(Z[a:a + 10000])
            return out
        return g
    scal = {'raw': lambda Z: Z,
            'minmax': chunked(lambda Z: (Z - mn) / rng_mm),
            'zscore': chunked(lambda Z: (Z - mu) / sd_z)}
    rng = np.random.default_rng(seed)
    sub = np.sort(rng.choice(te, size=min(int(cfg['bias']['scale_sub']), len(te)), replace=False))
    out = {}
    for key in cfg['bias']['scale_models']:
        rows = sub if key in ('lr', 'knn') else te
        Xte = run.take(rows)
        preds = {}
        for tag in (('raw', 'zscore') if key in ('lr', 'knn') else ('raw', 'minmax', 'zscore')):
            A, Bm = scal[tag](Xtr), scal[tag](Xte)
            if key == 'dt':
                p = DecisionTreeClassifier(max_depth=int(cfg['bias']['dt_depth']), random_state=seed).fit(A, y[tr]).predict(Bm)
            elif key == 'rf':
                p = RandomForestClassifier(n_estimators=int(cfg['bias']['cv_trees']), n_jobs=run.threads, random_state=seed).fit(A, y[tr]).predict(Bm)
            elif key == 'lgbm_trace':
                p = (LG.train_lgbm(A, y[tr], cfg['models']['lgbm_trace'], seed, run.threads).predict(Bm, raw_score=True) > 0).astype(int)
            elif key == 'lr':
                p = LogisticRegression(max_iter=cfg['models']['lr']['max_iter'], class_weight='balanced').fit(A, y[tr]).predict(Bm)
            else:
                p = KNeighborsClassifier(n_neighbors=int(cfg['models']['knn']['k']), n_jobs=run.threads).fit(A, y[tr]).predict(Bm)
            preds[tag] = p
        for tag in preds:
            if tag == 'raw':
                continue
            dis = int((preds[tag] != preds['raw']).sum())
            out[f'{key}:raw_vs_{tag}'] = dict(disagreements=dis, n=int(len(rows)), agreement=1 - dis / len(rows))
        log(f'  scaling {key}: ' + ', '.join(f'{k} {v["disagreements"]}' for k, v in out.items() if k.startswith(key)))
    R['scaling'] = out
    exact = [v for k, v in out.items() if k.split(':')[0] in ('dt', 'rf')]
    R['P9'] = dict(falsified=any(v['disagreements'] > 0 for v in exact))


ARMS = ['random', 'static', 'cv', 't0', 'coff', 'leakage', 'scaling']


def main():
    def extra(ap):
        ap.add_argument('--arms', nargs='*', default=ARMS, choices=ARMS)
    cfg, args = cli(__doc__, extra)
    run = Run(cfg)
    e1 = run.load('e1_metrics')
    raw = run.load('e1_metrics_raw')
    R = run.load('e4_bias') if run.has('e4_bias') else {}
    for arm in args.arms:
        log(f'arm {arm}')
        if arm == 'random':
            random_arm(run, cfg, R, e1)
        elif arm == 'static':
            static_arm(run, cfg, R, e1)
        elif arm == 'cv':
            cv_arm(run, cfg, R, raw)
        elif arm == 't0':
            t0_arm(run, cfg, R)
        elif arm == 'coff':
            coff_and_prewindow(run, cfg, R, e1)
        elif arm == 'leakage':
            leakage_arm(run, cfg, R)
        elif arm == 'scaling':
            scaling_arm(run, cfg, R)
        run.save('e4_bias', R)
    log('E4 done')


if __name__ == '__main__':
    main()
