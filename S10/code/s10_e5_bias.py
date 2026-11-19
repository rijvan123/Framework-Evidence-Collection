#!/usr/bin/env python3
"""Bias, leakage and sensitivity experiments that need re-training (LightGBM/LR/trees).
Usage: python3 s10_e5_bias.py <exp>   exp in {random, cv, t0, no626, prewin, leak, norm}
All thresholds are fitted on each arm's own calibration rows; nothing is fitted on test rows except where the arm is
deliberately leaky (labelled)."""
import sys, os, json, time
import numpy as np, pandas as pd
import s10_common as C, s10_models as Mz
from sklearn.preprocessing import StandardScaler, MinMaxScaler

exp = sys.argv[1]
m = C.load_meta(); X = C.load_X(); y = m['y'].to_numpy().astype(int)
mo = m['month'].to_numpy(); sp = m['split'].to_numpy()
dated = np.where(m['stratum'] == 'Dated')[0]
tr = np.where(sp == 'train')[0]; ca = np.where(sp == 'cal')[0]; te = np.where(sp == 'test')[0]
OUTJ = f'{C.OUT}/e5_{exp}.json'


def fit_score_lgbm(tr_idx, ev_idx, seed=11, params=C.LGB_TRACE, rounds=C.LGB_TRACE_ROUNDS, Xmat=None, extra_tr=None):
    Xm = X if Xmat is None else Xmat
    Xtr = np.asarray(Xm[tr_idx]); ytr = y[tr_idx]
    t = time.perf_counter(); b = Mz.fit_lgbm(Xtr, ytr, params, rounds, seed); fs = time.perf_counter() - t
    s = np.concatenate([b.predict(np.asarray(Xm[ev_idx[i:i + 20000]]), raw_score=True) for i in range(0, len(ev_idx), 20000)])
    return s, fs, b


def eval_sets(s_ev, ev_idx, thr, groups):
    out = {}
    for key, sel in groups.items():
        ys = y[ev_idx][sel]; ss = s_ev[sel]
        tp, fn, fp, tn = C.counts(ys, ss, thr)
        r = C.rates_from_counts(tp, fn, fp, tn)
        r10 = C.rates_from_counts(tp, fn, fp, tn, C.kappa_for(0.10, tp + fn, fp + tn))
        out[key] = dict(tp=tp, fn=fn, fp=fp, tn=tn, f1=r['f1'], fnr=r['fnr'], fpr=r['fpr'], prec=r['prec'],
                        f1_pi10=r10['f1'], prec_pi10=r10['prec'],
                        auc=C.auc_fast(ys, ss) if 0 < ys.sum() < len(ys) else float('nan'))
    return out


def month_groups(ev_idx, months):
    return {mm: (mo[ev_idx] == mm) for mm in months}


res = dict(exp=exp)
if exp == 'random':
    # Biased arm (Block 4, P1/H1): random stratified split of the pooled Dated stream with the temporal arm's sizes.
    pool = dated; n_tr, n_ca = len(tr), len(ca)
    arms = []
    for seed in C.MODEL_SEEDS:
        rng = np.random.default_rng(seed)
        perm = []
        for c in (0, 1):                       # stratified by label
            ic = pool[y[pool] == c]; perm.append(rng.permutation(ic))
        # allocate proportionally per class
        tr_r, ca_r, te_r = [], [], []
        for c, ic in zip((0, 1), perm):
            frac_c = len(ic) / len(pool)
            a = int(round(n_tr * frac_c)); b = int(round(n_ca * frac_c))
            tr_r.append(ic[:a]); ca_r.append(ic[a:a + b]); te_r.append(ic[a + b:])
        tr_r, ca_r, te_r = map(np.concatenate, (tr_r, ca_r, te_r))
        ev = np.r_[ca_r, te_r]
        s, fs, _ = fit_score_lgbm(tr_r, ev, seed)
        s_ca = s[:len(ca_r)]; s_te = s[len(ca_r):]
        thr, k = C.certified_threshold(s_ca[y[ca_r] == 0], 0.001)
        thr_emp, _ = C.empirical_threshold(s_ca[y[ca_r] == 0], 0.001)
        g = {'pool': np.ones(len(te_r), bool)}; g.update(month_groups(te_r, C.TEST_MONTHS + ['2019-%02d' % i for i in (8, 9, 10, 11, 12)]))
        arms.append(dict(seed=seed, fit_s=fs, k=k, thr=thr, cert=eval_sets(s_te, te_r, thr, g),
                         emp=eval_sets(s_te, te_r, thr_emp, g)))
        print('random seed', seed, arms[-1]['cert']['pool'], flush=True)
    # static random 80:20 (Block 4): 80% train (with 10% of it as calibration), 20% test
    rng = np.random.default_rng(11); perm = rng.permutation(pool)
    n80 = int(0.8 * len(pool)); trp, tep = perm[:n80], perm[n80:]
    cal_n = int(0.1 * n80); cap, trp2 = trp[:cal_n], trp[cal_n:]
    s, fs, _ = fit_score_lgbm(trp2, np.r_[cap, tep], 11)
    thr, k = C.certified_threshold(s[:cal_n][y[cap] == 0], 0.001)
    static = eval_sets(s[cal_n:], tep, thr, {'pool': np.ones(len(tep), bool)})
    res.update(arms=arms, static_8020=static)

elif exp == 'cv':
    # 5-fold random stratified CV on the pooled Dated stream (biased arm; violin plots). Threshold: certified 0.1%
    # on a 10% calibration hold-out inside each training fold.
    from sklearn.model_selection import StratifiedKFold
    pool = dated; folds = []
    skf = StratifiedKFold(5, shuffle=True, random_state=11)
    models = sys.argv[2].split(',') if len(sys.argv) > 2 else ['lgbm_trace', 'xgb', 'et100', 'rf100', 'lr', 'nb']
    for fi, (a, b) in enumerate(skf.split(pool, y[pool])):
        tr_f = pool[a]; te_f = pool[b]
        rng = np.random.default_rng(100 + fi); tr_f = rng.permutation(tr_f)
        nc = int(0.1 * len(tr_f)); ca_f, tr_f = tr_f[:nc], tr_f[nc:]
        for name in models:
            if name in ('et100', 'rf100'):
                mdl = Mz.Forest(name[:2], 100)
            else:
                mdl = Mz.make(name)
            t = time.perf_counter(); mdl.fit(np.asarray(X[np.sort(tr_f)]), y[np.sort(tr_f)], 11); fs = time.perf_counter() - t
            ev = np.r_[ca_f, te_f]
            s = np.concatenate([mdl.score(np.asarray(X[ev[i:i + 20000]])) for i in range(0, len(ev), 20000)])
            s_ca, s_te = s[:nc], s[nc:]
            thr, k = C.certified_threshold(s_ca[y[ca_f] == 0], 0.001)
            r = eval_sets(s_te, te_f, thr, {'pool': np.ones(len(te_f), bool)})['pool']
            r.update(model=name, fold=fi, fit_s=fs, ap=C.ap_score(y[te_f], s_te), ap_pi10=C.ap_score(y[te_f], s_te, 0.10))
            folds.append(r); print('cv', fi, name, {k_: r[k_] for k_ in ('auc', 'f1', 'fnr', 'fpr')}, flush=True)
            json.dump(dict(exp=exp, folds=folds), open(OUTJ, 'w'), default=float)
    res.update(folds=folds)

elif exp == 't0':
    # Replication of BODMAS Table III [1]: GBDT trained on samples before 2019-10-01, 80:20 random split, threshold at
    # 0.1% FPR on the 20% validation benign (empirical quantile, [1] protocol); monthly test Oct-2019..Sep-2020.
    out = {}
    for variant in ['dated', 'dated+prewindow']:
        pre = np.where(m['ts'] < pd.Timestamp('2019-10-01', tz='UTC'))[0]
        cand = np.intersect1d(pre, dated) if variant == 'dated' else np.r_[np.intersect1d(pre, dated), np.where(m['stratum'] == 'PreWindow')[0]]
        rng = np.random.default_rng(11); cand = rng.permutation(cand); nv = int(0.2 * len(cand))
        va, trn = cand[:nv], cand[nv:]
        months = ['2019-10', '2019-11', '2019-12'] + C.TEST_MONTHS
        ev = np.where((m['stratum'] == 'Dated') & m['month'].isin(months))[0]
        fam_tr = set(m['family'].iloc[trn][y[trn] == 1])
        for pname, params, rounds in [('lgbm_ember', C.LGB_EMBER, C.LGB_EMBER_ROUNDS), ('lgbm_trace', C.LGB_TRACE, C.LGB_TRACE_ROUNDS)]:
            s, fs, _ = fit_score_lgbm(trn, np.r_[va, ev], 11, params, rounds)
            s_va, s_ev = s[:nv], s[nv:]
            thr, k = C.empirical_threshold(s_va[y[va] == 0], 0.001)
            g = month_groups(ev, months)
            r = eval_sets(s_ev, ev, thr, g)
            unseen = ~m['family'].iloc[ev].isin(fam_tr).to_numpy()
            for mm in months:
                selm = (mo[ev] == mm) & (y[ev] == 1)
                for tag, sel in [('unseen', selm & unseen), ('seen', selm & ~unseen)]:
                    n = int(sel.sum()); fn = int(np.sum(s_ev[sel] <= thr))
                    r[mm][f'fnr_{tag}'] = fn / n if n else float('nan'); r[mm][f'n_{tag}'] = n
            out[f'{variant}|{pname}'] = dict(n_train=len(trn), n_val=nv, thr=thr, k=k, fit_s=fs, months=r)
            print('t0', variant, pname, {mm: (round(r[mm]['fpr'] * 100, 3), round(r[mm]['fnr'] * 100, 2)) for mm in months}, flush=True)
    res.update(t0=out)

elif exp in ('no626', 'prewin'):
    ev = np.r_[ca, te]
    if exp == 'no626':
        keep = np.r_[0:C.COFF_COL, C.COFF_COL + 1:C.D]
        Xr = None
        Xtr = np.asarray(X[tr])[:, keep]
        b = Mz.fit_lgbm(Xtr, y[tr], C.LGB_TRACE, C.LGB_TRACE_ROUNDS, 11)
        s = np.concatenate([b.predict(np.asarray(X[ev[i:i + 20000]])[:, keep], raw_score=True) for i in range(0, len(ev), 20000)])
    else:
        trx = np.r_[tr, np.where(m['stratum'] == 'PreWindow')[0]]
        s, fs, b = fit_score_lgbm(trx, ev, 11)
    s_ca = s[:len(ca)]; s_te = s[len(ca):]
    thr, k = C.certified_threshold(s_ca[y[ca] == 0], 0.001)
    g = month_groups(te, C.TEST_MONTHS); g['pool_MarSep'] = np.isin(mo[te], C.CERT_MONTHS)
    res.update(thr=thr, k=k, months=eval_sets(s_te, te, thr, g))
    np.savez(f'{C.CACHE}/scores_{exp}.npz', idx=ev, s=s)

elif exp == 'leak':
    # P3 (U3): leaky pipelines fit scaler / chi2 selection (labels included) / PCA on train+cal+test (all Dated) before training.
    # Memory-safe rewrite (the first version was OOM-killed): float32 views, chunked chi2 statistics, PCA by eigendecomposition of the
    # standardised covariance (same subspace as sklearn PCA(n_components=0.95, svd_solver='full') on standardised inputs).
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import LinearSVC
    allr = np.r_[tr, ca, te]; ntr = len(tr); nca = len(ca); CH = 20000
    Z_all = np.empty((len(allr), C.D), np.float32)
    for i in range(0, len(allr), CH):
        Z_all[i:i + CH] = Mz.slog(np.asarray(X[allr[i:i + CH]]))
    Ztr, Zca, Zte = Z_all[:ntr], Z_all[ntr:ntr + nca], Z_all[ntr + nca:]          # views
    yall = y[allr]; out = {}

    def moments(Z):
        mu = np.zeros(C.D); sq = np.zeros(C.D); mn = np.full(C.D, np.inf); mx = np.full(C.D, -np.inf)
        for i in range(0, len(Z), CH):
            z = Z[i:i + CH].astype(np.float64); mu += z.sum(0); sq += (z * z).sum(0); mn = np.minimum(mn, z.min(0)); mx = np.maximum(mx, z.max(0))
        n = len(Z); mu /= n; var = np.maximum(sq / n - mu * mu, 0.0); sd = np.sqrt(var); sd[sd == 0] = 1.0
        return mu, sd, mn, mx

    def apply(Z, mu, sd, cols=None, V=None):
        outm = np.empty((len(Z), C.D if cols is None and V is None else (len(cols) if V is None else V.shape[1])), np.float32)
        for i in range(0, len(Z), CH):
            z = (Z[i:i + CH].astype(np.float64) - mu) / sd
            if cols is not None:
                z = z[:, cols]
            outm[i:i + CH] = z if V is None else z @ V
        return outm

    def chi2_top(Z, yy, mn, mx, k=256):
        rng_ = np.where(mx > mn, mx - mn, 1.0); obs = np.zeros((2, C.D))
        for i in range(0, len(Z), CH):
            z = np.clip((Z[i:i + CH].astype(np.float64) - mn) / rng_, 0, None); yb = yy[i:i + CH]
            obs[1] += z[yb == 1].sum(0); obs[0] += z[yb == 0].sum(0)
        fsum = obs.sum(0); cp = np.array([(yy == 0).mean(), (yy == 1).mean()]); exp_ = np.outer(cp, fsum)
        with np.errstate(divide='ignore', invalid='ignore'):
            sc = np.nansum(np.where(exp_ > 0, (obs - exp_) ** 2 / exp_, 0.0), axis=0)
        return np.sort(np.argsort(-sc, kind='stable')[:k])

    def pca_V(Z, mu, sd, var_ratio=0.95):
        G = np.zeros((C.D, C.D))
        for i in range(0, len(Z), CH):
            z = (Z[i:i + CH].astype(np.float64) - mu) / sd; G += z.T @ z
        G /= len(Z); w, V = np.linalg.eigh(G); o = np.argsort(-w); w, V = np.clip(w[o], 0, None), V[:, o]
        k = int(np.searchsorted(np.cumsum(w) / w.sum(), var_ratio) + 1); return V[:, :k], k

    def run_arm(tag, Atr, Aca, Ate, clf):
        mdl = LogisticRegression(C=1.0, max_iter=3000, class_weight='balanced') if clf == 'lr' else \
            LinearSVC(C=0.05, class_weight='balanced', dual=False, max_iter=5000)
        mdl.fit(Atr, y[tr]); s_ca = mdl.decision_function(Aca); s_te = mdl.decision_function(Ate)
        thr, _ = C.certified_threshold(s_ca[y[ca] == 0], 0.001)
        g = month_groups(te, C.CERT_MONTHS); g['pool_MarSep'] = np.isin(mo[te], C.CERT_MONTHS)
        r = eval_sets(s_te, te, thr, g)
        for kk in r:
            sel = g[kk]; r[kk]['ap_pi10'] = C.ap_score(y[te][sel], s_te[sel], 0.10); r[kk]['ap_pi1'] = C.ap_score(y[te][sel], s_te[sel], 0.01)
        out[tag] = r; np.save(f'{C.CACHE}/leak_{tag}.npy', s_te)
        print(tag, r['pool_MarSep']['auc'], r['pool_MarSep']['ap_pi10'], flush=True)

    m_c = moments(Ztr); m_l = moments(Z_all)
    sel_c = chi2_top(Ztr, y[tr], m_c[2], m_c[3]); sel_l = chi2_top(Z_all, yall, m_l[2], m_l[3])
    res['overlap_chi2_clean_vs_leaky'] = int(len(np.intersect1d(sel_c, sel_l)))
    V_c, k_c = pca_V(Ztr, m_c[0], m_c[1]); V_l, k_l = pca_V(Z_all, m_l[0], m_l[1]); res['pca_k'] = dict(clean=k_c, leaky=k_l)
    print('chi2 overlap', res['overlap_chi2_clean_vs_leaky'], 'pca k', k_c, k_l, flush=True)
    for clf in ('lr', 'svm'):
        for tag, (mu, sd) in (('scale_clean', m_c[:2]), ('scale_leaky', m_l[:2])):
            run_arm(f'{clf}|{tag}', apply(Ztr, mu, sd), apply(Zca, mu, sd), apply(Zte, mu, sd), clf)
        for tag, cols in (('chi2_clean', sel_c), ('chi2_leaky', sel_l)):
            mu, sd = m_c[0][cols], m_c[1][cols]               # scaler fitted on training rows of the selected columns (as before)
            sub = lambda Z: apply(Z[:, :], m_c[0], m_c[1], cols=cols)
            run_arm(f'{clf}|{tag}', sub(Ztr), sub(Zca), sub(Zte), clf)
        for tag, (mu, sd, V) in (('pca_clean', (m_c[0], m_c[1], V_c)), ('pca_leaky', (m_l[0], m_l[1], V_l))):
            run_arm(f'{clf}|{tag}', apply(Ztr, mu, sd, V=V), apply(Zca, mu, sd, V=V), apply(Zte, mu, sd, V=V), clf)
        json.dump(dict(exp=exp, partial=True, arms=out), open(OUTJ + '.partial', 'w'), default=float)
    # trees under clean vs leaky scaling (P9-style check inside P3): predictions should be identical up to histogram binning
    for tag, (mu, sd) in (('clean', m_c[:2]), ('leaky', m_l[:2])):
        b = Mz.fit_lgbm(apply(Ztr, mu, sd), y[tr], C.LGB_TRACE, C.LGB_TRACE_ROUNDS, 11)
        np.save(f'{C.CACHE}/leak_lgbm_{tag}.npy', b.predict(apply(Zte, mu, sd), raw_score=True))
    a_ = np.load(f'{C.CACHE}/leak_lgbm_clean.npy'); bb = np.load(f'{C.CACHE}/leak_lgbm_leaky.npy')
    res['lgbm_scaling_leak'] = dict(max_abs_diff=float(np.max(np.abs(a_ - bb))), identical=bool(np.array_equal(a_, bb)),
                                    decision_agreement=float(np.mean((a_ > 0) == (bb > 0))))
    res['arms'] = out

elif exp == 'norm':
    # P9 (U9): invariance of trees to strictly increasing per-feature maps (Eqs. 6, 7, 11). Views processed one at a time (memory).
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.neighbors import KNeighborsClassifier
    Xtr = np.asarray(X[tr], dtype=np.float64); Xte = np.asarray(X[te], dtype=np.float64)
    mm = MinMaxScaler().fit(Xtr); zs = StandardScaler().fit(Xtr)
    sub = np.random.default_rng(11).choice(len(tr), 8000, replace=False); preds = {}

    def tf(tfm, Z):
        o = np.empty_like(Z)
        for i in range(0, len(Z), 20000):
            o[i:i + 20000] = tfm.transform(Z[i:i + 20000])
        return o

    for v in ('raw', 'minmax', 'zscore'):
        A, Bt = (Xtr, Xte) if v == 'raw' else ((tf(mm, Xtr), tf(mm, Xte)) if v == 'minmax' else (tf(zs, Xtr), tf(zs, Xte)))
        dt = DecisionTreeClassifier(max_depth=14, random_state=11).fit(A, y[tr]); p_dt = dt.predict(Bt); del dt
        rf = RandomForestClassifier(n_estimators=100, n_jobs=2, random_state=11).fit(A, y[tr]); p_rf = rf.predict(Bt); del rf
        lg = Mz.fit_lgbm(A.astype(np.float32), y[tr], C.LGB_TRACE, C.LGB_TRACE_ROUNDS, 11)
        p_lg = np.concatenate([(lg.predict(Bt[i:i + 20000].astype(np.float32), raw_score=True) > 0).astype(int) for i in range(0, len(Bt), 20000)])
        preds[v] = dict(dt=p_dt, rf=p_rf, lgbm=p_lg)
        if v in ('raw', 'zscore'):
            lr = LogisticRegression(C=1.0, max_iter=500).fit(A[sub], y[tr][sub])
            kn = KNeighborsClassifier(n_neighbors=15, n_jobs=2).fit(A[sub], y[tr][sub])
            preds[v].update(lr=lr.predict(Bt[:20000]), knn=kn.predict(Bt[:20000]))
        print('norm', v, flush=True)
        if v != 'raw':
            del A, Bt
    agree = {}
    for mdl in ('dt', 'rf', 'lgbm'):
        for v in ('minmax', 'zscore'):
            agree[f'{mdl}|raw_vs_{v}'] = dict(disagree=int(np.sum(preds['raw'][mdl] != preds[v][mdl])), n=len(te),
                                              agreement=float(np.mean(preds['raw'][mdl] == preds[v][mdl])))
    for mdl in ('lr', 'knn'):
        agree[f'{mdl}|raw_vs_zscore'] = dict(disagree=int(np.sum(preds['raw'][mdl] != preds['zscore'][mdl])), n=20000,
                                             agreement=float(np.mean(preds['raw'][mdl] == preds['zscore'][mdl])))
    res['agreement'] = agree; print(agree)

C.jdump(res, OUTJ)
print('saved', OUTJ)
