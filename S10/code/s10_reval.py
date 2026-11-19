#!/usr/bin/env python3
"""Assurance-plane simulation (S7 Parts 6.4-6.8; Algorithms 2, 3, 5, 6): budgeted re-validation of issued findings,
amendment semantics, retrospective/prospective certificates, exposure E^ev_T, kills K1/K2/K3, KB1, KB7, KS1, KS2.

Stages:
  python3 s10_reval.py ptr                      -> harm gate gamma by pre-test replay on 2019 data only (D11)
  python3 s10_reval.py models <L> <rho>         -> issuer/re-validator models f_u at u in U, PCT variants, region scores
  python3 s10_reval.py sim <L> <rho>            -> all policies, native stream + resampled streams + noise scenarios
"""
import sys, os, json, time, math, pickle
import numpy as np, pandas as pd, lightgbm as lgb
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import StratifiedKFold
import s10_common as C, s10_models as Mz

m = C.load_meta(); y = m['y'].to_numpy().astype(int)
DAY = ((m['day'].dt.tz_convert(None) - pd.Timestamp('1970-01-01')).dt.days).to_numpy()
month = m['month'].to_numpy(); sha = m['sha'].to_numpy()
dated = (m['stratum'] == 'Dated').to_numpy()


def dnum(s):
    return int((pd.Timestamp(s) - pd.Timestamp('1970-01-01')).days)


START = dnum('2020-03-01'); HORIZON = dnum('2020-10-31')
UPDATES = ['2020-03-01'] + ['2020-%02d-01' % k for k in range(4, 11)]          # issuer updates; events = Apr..Oct
EVENTS = UPDATES[1:]
TAU_PAIRS = {'primary': (0.005, 0.05), 'strict': (0.001, 0.02)}
A_MAX = 60; N_MIN = 500; C_R = 10; OMEGA = 1.0; TAU_H = 0.005


def month_last_day(mm):
    p = pd.Period(mm, 'M'); return dnum(str(p.end_time.date()))


def month_counts(mm):
    sel = dated & (month == mm); return int(((y == 0) & sel).sum()), int(((y == 1) & sel).sum())


def cal_month(u, L, labelled=None):
    """Latest fully matured month with >= N_MIN dated benign and malware (searching back from u)."""
    cands = pd.period_range('2019-09', '2020-09', freq='M').astype(str)[::-1]
    for mm in cands:
        if month_last_day(mm) + L <= u:
            nb, nm = month_counts(mm)
            if nb >= N_MIN and nm >= N_MIN:
                return mm
    raise RuntimeError('no calibration month')


def ice_sets(s, yy):
    p1 = 1 / (1 + np.exp(-s))
    return {c: np.sort(np.where(c == 1, 1 - p1, p1)[yy == c]) for c in (0, 1)}


def ice_cred(s, yhat, sets):
    p1 = 1 / (1 + np.exp(-s)); out = np.empty(len(s))
    for c in (0, 1):
        sel = yhat == c; a = np.where(c == 1, 1 - p1[sel], p1[sel]); ac = sets[c]
        out[sel] = (1 + (len(ac) - np.searchsorted(ac, a, side='left'))) / (1 + len(ac))
    return out


def calibrate(s_cal, y_cal):
    """Algorithm 2 lines 5-8: certified thresholds, isotonic map, ICE sets, kappa (<= 5% Dec abstention), Transcendent
    per-class thresholds (10% rejection, baseline iv)."""
    b = s_cal[y_cal == 0]; out = {}
    for tau in (0.001, 0.005):
        thr, k = C.certified_threshold(b, tau); out[f'thr_{tau}'] = thr; out[f'k_{tau}'] = k
    out['iso'] = IsotonicRegression(out_of_bounds='clip', y_min=0, y_max=1).fit(s_cal, y_cal)
    out['ice'] = ice_sets(s_cal, y_cal)
    for tau in (0.001, 0.005):
        yh = (s_cal > out[f'thr_{tau}']).astype(int); cr = ice_cred(s_cal, yh, out['ice'])
        cs = np.sort(cr); out[f'kappa_{tau}'] = float(cs[int(np.floor(0.05 * len(cs)))])
        out[f'kT_{tau}'] = {c: float(np.quantile(cr[yh == c], 0.10)) if (yh == c).any() else 0.0 for c in (0, 1)}
        tp, fn, fp, tn = C.counts(y_cal, s_cal, out[f'thr_{tau}'])
        out[f'calcert_{tau}'] = dict(fp=fp, n_b=fp + tn, fn=fn, n_m=tp + fn, fpr_ub=C.cp_upper(fp, fp + tn), fnr_ub=C.cp_upper(fn, tp + fn))
    return out


X = None


def getX():
    global X
    if X is None:
        X = C.load_X()
    return X


def train_at(u, L, rho_mask=None, init_model=None, weight_fn=None, rounds=C.LGB_TRACE_ROUNDS, seed=11):
    """Algorithm 2: train on Dated rows with t_i + L <= u, excluding the calibration month; labels limited by rho."""
    cm = cal_month(u, L)
    tr = dated & (DAY + L <= u) & (month != cm)
    if rho_mask is not None:
        tr &= rho_mask
    tr = np.where(tr)[0]
    Xa = getX(); Xtr = np.asarray(Xa[tr]); w = None if weight_fn is None else weight_fn(tr)
    t = time.perf_counter()
    b = Mz.fit_lgbm(Xtr, y[tr], C.LGB_TRACE, rounds, seed, weight=w, init_model=init_model)
    fs = time.perf_counter() - t
    ci = np.where(dated & (month == cm) & (rho_mask if rho_mask is not None else True))[0]
    s_cal = b.predict(np.asarray(Xa[ci]), raw_score=True)
    return b, tr, cm, ci, s_cal, fs


# ======================================================================================== PTR (D11)
def run_ptr():
    Xa = getX(); L = 30
    d_ = lambda s: dnum(s)
    tr0 = np.where(dated & (DAY < d_('2019-10-01')))[0]
    ca0 = np.where(dated & (DAY >= d_('2019-10-01')) & (DAY < d_('2019-10-16')))[0]
    iss = np.where(dated & (DAY >= d_('2019-10-16')) & (DAY < d_('2019-12-01')))[0]
    b0 = Mz.fit_lgbm(np.asarray(Xa[tr0]), y[tr0], C.LGB_TRACE, C.LGB_TRACE_ROUNDS, 11)
    s0c = b0.predict(np.asarray(Xa[ca0]), raw_score=True); cal0 = calibrate(s0c, y[ca0])
    s0 = b0.predict(np.asarray(Xa[iss]), raw_score=True)
    tr1 = np.where(dated & (DAY < d_('2019-10-16')))[0]
    ca1 = np.where(dated & (DAY >= d_('2019-10-16')) & (DAY < d_('2019-11-01')))[0]
    b1 = Mz.fit_lgbm(np.asarray(Xa[tr1]), y[tr1], C.LGB_TRACE, C.LGB_TRACE_ROUNDS, 11)
    s1c = b1.predict(np.asarray(Xa[ca1]), raw_score=True); cal1 = calibrate(s1c, y[ca1])
    s1 = b1.predict(np.asarray(Xa[iss]), raw_score=True)
    scope = DAY[iss] + L > d_('2019-11-30')                          # November findings, labels not matured
    out = {}
    for tau in (0.005, 0.001):
        yh0 = (s0 > cal0[f'thr_{tau}']).astype(int); yh1 = (s1 > cal1[f'thr_{tau}']).astype(int)
        p1 = cal1['iso'].predict(s1); q = np.where(yh0 == 0, p1, 1 - p1)
        cr1 = ice_cred(s1, yh1, cal1['ice']); kap = cal1[f'kappa_{tau}']
        ch = scope & (yh1 != yh0); yt = y[iss]
        grid = np.round(np.arange(0.50, 1.0001, 0.01), 2); rows = []
        for g in grid:
            auto = ch & (q >= g) & (cr1 >= kap)
            harm = int(np.sum(auto & (yh0 == yt))); n_auto = int(auto.sum()); N = int(scope.sum())
            rows.append(dict(gamma=float(g), n_auto=n_auto, harmful=harm, corrections=int(np.sum(auto & (yh0 != yt))),
                             rH=harm / N, rH_ub=C.cp_upper(harm, N), share_harmful=harm / n_auto if n_auto else 0.0))
        ok = [r['gamma'] for r in rows if r['rH_ub'] <= TAU_H]
        out[str(tau)] = dict(gamma=min(ok) if ok else float('inf'), N_scope=int(scope.sum()), changes=int(ch.sum()), grid=rows,
                             kappa=kap, thr0=cal0[f'thr_{tau}'], thr1=cal1[f'thr_{tau}'])
        print('PTR tau', tau, 'gamma', out[str(tau)]['gamma'], 'scope', int(scope.sum()), 'changes', int(ch.sum()), flush=True)
    C.jdump(out, f'{C.OUT}/reval_ptr.json')
    C.ledger_append([dict(t='CAL', kind='PTR', gamma={k: (C.f32hex(v['gamma']) if v['gamma'] != float('inf') else 'inf') for k, v in out.items()},
                          tau_H=C.f32hex(TAU_H), data='2019-08-29..2019-11-30 only')], epoch='assurance')
    return out


# ======================================================================================== models stage
def run_models(L, rho):
    Xa = getX(); tag = f'L{L}_rho{rho}'; d = f'{C.CACHE}/reval_{tag}'; os.makedirs(d, exist_ok=True)
    stream = np.where(dated & (DAY >= dnum('2020-01-01')) & (DAY <= dnum('2020-09-30')))[0]
    rng = np.random.default_rng(777)
    rho_mask = None
    if rho < 1.0:      # labels of 2020 findings mature only with probability rho (pre-2020 labels all available)
        lab = np.ones(len(m), bool); is20 = DAY >= dnum('2020-01-01'); lab[is20] = rng.random(int(is20.sum())) < rho
        rho_mask = lab; np.save(f'{d}/rho_mask.npy', lab)
    Xs = np.asarray(Xa[stream])
    res = dict(stream=stream, models={})
    prev_b = None
    for u_s in UPDATES:
        u = dnum(u_s)
        b, tr, cm, ci, s_cal, fs = train_at(u, L, rho_mask)
        cal = calibrate(s_cal, y[ci]); s_stream = b.predict(Xs, raw_score=True)
        entry = dict(u=u_s, cal_month=cm, n_train=len(tr), fit_s=fs, cal=cal, s=s_stream, ident=C.tree_section_hash(b.model_to_string()))
        # PCT-adapted re-scorer (baseline v): warm start from the previous issuer + 2x weight on samples it got right
        if prev_b is not None:
            thr_prev = res['models'][prev_u]['cal']['thr_0.005']
            def wfn(tr_idx, pb=prev_b, th=thr_prev):
                sp = pb.predict(np.asarray(Xa[tr_idx]), raw_score=True); return np.where((sp > th).astype(int) == y[tr_idx], 2.0, 1.0)
            bp, trp, cmp_, cip, s_calp, fsp = train_at(u, L, rho_mask, init_model=prev_b, weight_fn=wfn, rounds=100)
            entry['pct'] = dict(cal=calibrate(s_calp, y[cip]), s=bp.predict(Xs, raw_score=True), fit_s=fsp)
        res['models'][u_s] = entry; prev_b = b; prev_u = u_s
        C.ledger_append([dict(t='MAN', kind='revalidator', tag=tag, u=u_s, root=C.merkle_root([bytes.fromhex(sha[i]) for i in sorted(tr, key=lambda i: sha[i])]).hex(),
                              cutoff=u_s, L=L, cal_month=cm),
                         dict(t='MOD', kind='revalidator', tag=tag, u=u_s, ident=entry['ident'], fit_s=C.f32hex(fs)),
                         dict(t='CAL', tag=tag, u=u_s, thr_005=C.f32hex(cal['thr_0.005']), k_005=cal['k_0.005'],
                              thr_001=C.f32hex(cal['thr_0.001']), k_001=cal['k_0.001'], kappa=C.f32hex(cal['kappa_0.005']))], epoch='assurance')
        print(tag, u_s, 'cal', cm, 'n_train', len(tr), 'fit', round(fs, 1), flush=True)
    # Region scores: domain classifier window (findings issued in (u-L, u)) vs the issuer's calibration month (S7.9)
    reg = {}
    for i, u_s in enumerate(EVENTS):
        u = dnum(u_s); prev = UPDATES[i]
        win = stream[(DAY[stream] >= START) & (DAY[stream] < u) & (DAY[stream] + L > u)]
        ref = np.where(dated & (month == res['models'][prev]['cal_month']))[0]
        Z = np.vstack([np.asarray(Xa[win]), np.asarray(Xa[ref])]); dz = np.r_[np.ones(len(win)), np.zeros(len(ref))]
        oof = np.zeros(len(dz))
        for a, bb in StratifiedKFold(2, shuffle=True, random_state=11).split(Z, dz):
            clf = lgb.train(dict(objective='binary', num_leaves=31, learning_rate=0.1, feature_fraction=0.5, seed=7, deterministic=True,
                                 force_row_wise=True, num_threads=2, verbose=-1), lgb.Dataset(Z[a], label=dz[a]), num_boost_round=100)
            oof[bb] = clf.predict(Z[bb])
        p = np.clip(oof[:len(win)], 1e-6, 1 - 1e-6)
        reg[u_s] = dict(rows=win, w=(len(ref) / len(win)) * p / (1 - p), auc=C.auc_fast(dz, oof))
        print(tag, 'region', u_s, 'win', len(win), 'auc', round(reg[u_s]['auc'], 3), flush=True)
    res['region'] = reg
    pickle.dump(res, open(f'{d}/models.pkl', 'wb'))


# ======================================================================================== simulation stage
POLICIES = ['tracepe', 'i_auto', 'ii_review_changes', 'iii_calendar', 'iv_transcendent', 'v_pct_auto', 'vi_random', 'vii_margin',
            'viii_reconcile', 'viii_frozen', 'abl_noregion', 'abl_noflag', 'abl_nogate', 'abl_noauto',
            'a2_naive', 'a2_abst', 'a2_cert', 'a2_naive_frozen']
NO_REOPEN = ('iii_calendar', 'iv_transcendent', 'viii_reconcile', 'viii_frozen', 'a2_naive', 'a2_abst', 'a2_cert', 'a2_naive_frozen')
ST = dict(ISS=0, SCR=1, ABS=2, CON=3, COR=4, AUT=5, FLG=6, REC=7)
EVAL = np.array([1, 0, 0, 1, 1, 0, 0, 1], bool)          # evaluative states: ISS, CON, COR, REC


def simulate(policy, R, L, tau_pair, gamma, stream_rows, f0, noise=0.0, noise_seed=0, rho_mask=None, record=False, recon_reviewed=False):
    """Day-stepped simulation over findings `stream_rows` (subset of R['stream'], Mar 1 - Sep 30)."""
    tauF, tauN = TAU_PAIRS[tau_pair]; tkey = 'thr_0.005' if tau_pair == 'primary' else 'thr_0.001'
    kkey = 'kappa_0.005' if tau_pair == 'primary' else 'kappa_0.001'; ktkey = 'kT_0.005' if tau_pair == 'primary' else 'kT_0.001'
    ckey = 'calcert_0.005' if tau_pair == 'primary' else 'calcert_0.001'
    pos = {r: k for k, r in enumerate(R['stream'])}
    rows = np.array(sorted(stream_rows, key=lambda r: (DAY[r], sha[r])))
    n = len(rows); sidx = np.array([pos[r] for r in rows]); t_i = DAY[rows]; yy = y[rows]
    labelled = np.ones(n, bool) if rho_mask is None else rho_mask[rows]
    upd_days = [dnum(u) for u in UPDATES]
    frozen = policy in ('viii_frozen', 'a2_naive_frozen')

    def model_at(t):
        k = max(j for j, ud in enumerate(upd_days) if ud <= t); return UPDATES[k]

    # issuance (Algorithm 3): verdict, credibility, state
    ver = np.zeros(n, int); cred = np.zeros(n); issuer = np.empty(n, object); state = np.zeros(n, int)
    for u_s in UPDATES:
        sel = np.array([model_at(t) == u_s for t in t_i]) if not frozen else np.ones(n, bool) & (u_s == UPDATES[0])
        if not sel.any():
            continue
        if frozen:
            s = f0['s'][sidx[sel]]; cal = f0['cal']
        else:
            s = R['models'][u_s]['s'][sidx[sel]]; cal = R['models'][u_s]['cal']
        v = (s > cal[tkey]).astype(int); ver[sel] = v; cred[sel] = ice_cred(s, v, cal['ice']); issuer[sel] = 'f0' if frozen else u_s
    # retrospective certificates per (issuer, month) from issuance verdicts; Jan-Feb findings were issued by f0
    cert = {}
    for mm in ['2020-%02d' % k for k in range(1, 10)]:
        if mm in ('2020-01', '2020-02'):
            sel0 = np.where(dated & (month == mm))[0]; s0 = f0['s_all'][sel0]; v0 = (s0 > f0['cal'][tkey]).astype(int); yt = y[sel0]
        else:
            selm = np.array([month[r] == mm for r in rows]); v0 = ver[selm]; yt = yy[selm]
        fp = int(np.sum((v0 == 1) & (yt == 0))); nb = int(np.sum(yt == 0)); fn = int(np.sum((v0 == 0) & (yt == 1))); nm = int(np.sum(yt == 1))
        cert[mm] = dict(avail=month_last_day(mm) + L, last=month_last_day(mm), fp=fp, n_b=nb, fn=fn, n_m=nm,
                        fpr_ub=C.cp_upper(fp, nb) if nb >= N_MIN else None, fnr_ub=C.cp_upper(fn, nm) if nm >= N_MIN else None)

    def valid(t, u_s):
        cal = f0['cal'] if frozen else R['models'][u_s]['cal']; cm = f0['cal_month'] if frozen else R['models'][u_s]['cal_month']
        srcF = [(month_last_day(cm), cal[ckey]['fpr_ub'])]; srcN = [(month_last_day(cm), cal[ckey]['fnr_ub'])]
        for mm, c in cert.items():
            if c['avail'] <= t:
                if c['fpr_ub'] is not None:
                    srcF.append((c['last'], c['fpr_ub']))
                if c['fnr_ub'] is not None:
                    srcN.append((c['last'], c['fnr_ub']))
        lf, uf = max(srcF); ln, un = max(srcN)
        return (uf <= tauF) and (t - lf <= A_MAX) and (un <= tauN) and (t - ln <= A_MAX)

    vcache = {}
    for k in range(n):
        u_s = issuer[k]
        key = (t_i[k], u_s)
        if key not in vcache:
            vcache[key] = valid(t_i[k], UPDATES[0] if frozen else u_s)
        cal = f0['cal'] if frozen else R['models'][u_s]['cal']
        if policy == 'iv_transcendent':
            abst = cred[k] < cal[ktkey][ver[k]]
        elif policy in ('a2_naive', 'a2_cert', 'a2_naive_frozen'):
            abst = False                                   # A2 ablation: no abstention
        else:
            abst = cred[k] < cal[kkey]
        gate = True if policy in ('a2_naive', 'a2_abst', 'a2_naive_frozen') else vcache[key]   # A2 ablation: no certificate gating
        state[k] = ST['ABS'] if abst else (ST['ISS'] if gate else ST['SCR'])
    cur = ver.copy(); issued = np.zeros(n, bool); reconciled = np.zeros(n, bool)
    rng = np.random.default_rng(noise_seed)
    ev_log = []; U = []; Uev = []; cov = []; days = list(range(START, HORIZON + 1))
    iss_state0 = state.copy()
    ev_days = {dnum(e): e for e in EVENTS}
    use_err = {7: np.zeros(n, bool), 14: np.zeros(n, bool), 30: np.zeros(n, bool)}
    first_issue = {}
    for t in days:
        # --- event (Algorithm 5) before the day's issuance
        if t in ev_days and policy not in NO_REOPEN:
            u_s = ev_days[t]; Mv = R['models'][u_s]
            scope = np.where(issued & (t_i < t) & (t_i + L > t) & np.isin(state, [ST['ISS'], ST['SCR'], ST['FLG'], ST['AUT']]))[0]
            N = len(scope); recent = np.sum(issued & (t_i >= t - 30) & (t_i < t)); B = int(math.ceil(0.01 * recent))
            if policy == 'v_pct_auto':
                s2 = Mv['pct']['s'][sidx[scope]]; cal2 = Mv['pct']['cal']
            else:
                s2 = Mv['s'][sidx[scope]]; cal2 = Mv['cal']
            v2 = (s2 > cal2[tkey]).astype(int); ch = v2 != cur[scope]
            p2 = cal2['iso'].predict(s2); q = np.where(cur[scope] == 0, p2, 1 - p2); cr2 = ice_cred(s2, v2, cal2['ice'])
            wrong_before = cur[scope] != yy[scope]
            log = dict(event=u_s, N=N, B=B, changes=int(ch.sum()), wrong_before=int(wrong_before.sum()),
                       changes_correcting=int(np.sum(ch & wrong_before)), changes_harmful=int(np.sum(ch & ~wrong_before)))
            reviewed = np.zeros(N, bool); auto = np.zeros(N, bool); flag = np.zeros(N, bool)
            if policy in ('i_auto', 'v_pct_auto'):
                auto_acc = ch
            elif policy == 'ii_review_changes':
                cidx = np.where(ch)[0]; pick = rng.choice(cidx, min(B, len(cidx)), replace=False) if len(cidx) else []
                reviewed[pick] = True
            elif policy == 'vi_random':
                reviewed[rng.choice(N, min(B, N), replace=False)] = True
            elif policy == 'vii_margin':
                reviewed[np.argsort(np.abs(s2 - cal2[tkey]), kind='stable')[:min(B, N)]] = True
            else:   # tracepe and ablations
                g = gamma if policy not in ('abl_nogate', 'abl_noauto') else (0.0 if policy == 'abl_nogate' else float('inf'))
                if policy == 'abl_noregion':
                    region = np.ones(N, bool)          # review ranks the whole scope; beyond budget only changes are acted on
                else:
                    reg = R['region'][u_s]; wmap = dict(zip(reg['rows'], reg['w'])); wv = np.array([wmap.get(rows[k], 0.0) for k in scope])
                    cand = np.where(wv >= OMEGA)[0]; top = cand[np.argsort(-wv[cand], kind='stable')[:C_R * B]]
                    region = np.zeros(N, bool); region[top] = True; region |= ch
                ridx = np.where(region)[0]
                order = sorted(ridx, key=lambda k: (-q[k], cred[scope[k]], sha[rows[scope[k]]]))
                reviewed[order[:B]] = True
                rest = region & ~reviewed
                if policy == 'abl_noregion':
                    rest = rest & ch
                auto = rest & ch & (q >= g) & (cr2 >= cal2[kkey])
                flag = rest & ~auto if policy != 'abl_noflag' else np.zeros(N, bool)
            # apply
            if policy in ('i_auto', 'v_pct_auto'):
                k_ = scope[auto_acc]; log['harmful_auto'] = int(np.sum(cur[k_] == yy[k_])); log['correct_auto'] = int(np.sum(cur[k_] != yy[k_]))
                cur[k_] = v2[auto_acc]
            rv = scope[reviewed]
            if len(rv):
                ystar = np.where(rng.random(len(rv)) < noise, 1 - yy[rv], yy[rv])
                log['reviews'] = len(rv); log['review_hits'] = int(np.sum(cur[rv] != yy[rv]))
                state[rv] = np.where(ystar == cur[rv], ST['CON'], ST['COR']); cur[rv] = ystar
            ak = scope[auto]
            if len(ak):
                log['auto'] = len(ak); log['harmful_auto'] = int(np.sum(cur[ak] == yy[ak])); log['correct_auto'] = int(np.sum(cur[ak] != yy[ak]))
                cur[ak] = v2[auto]; state[ak] = ST['AUT']
            fk = scope[flag]; log['flagged'] = len(fk); state[fk] = ST['FLG']
            ev_log.append(log)
        # --- reconciliation (Algorithm 6) for matured labels
        excl = [ST['ABS']] if recon_reviewed else [ST['CON'], ST['COR'], ST['ABS']]       # S10 variant: oracle overrides analyst at maturity
        mat = issued & ~reconciled & (t_i + L <= t) & labelled & ~np.isin(state, excl)
        cur[mat] = yy[mat]; state[mat] = ST['REC']; reconciled |= mat
        # --- issuance
        new = (t_i == t); issued |= new
        # --- accounting
        live = issued & (state != ST['ABS']); wrong = live & (cur != yy)
        U.append(int(wrong.sum())); Uev.append(int(np.sum(wrong & EVAL[state])))
        nl = int(live.sum()); cov.append(np.sum(live & EVAL[state]) / nl if nl else np.nan)
        for dlt in use_err:
            at = issued & (t_i + dlt == t)
            use_err[dlt][at] = (wrong & EVAL[state])[at]
    days_arr = np.array(days)
    out = dict(policy=policy, L=L, tau=tau_pair, noise=noise, n=n, E_ev=int(np.sum(Uev)), E=int(np.sum(U)), events=ev_log,
               abstained=int(np.sum(iss_state0 == ST['ABS'])), scr_at_issue=int(np.sum(iss_state0 == ST['SCR'])),
               iss_at_issue=int(np.sum(iss_state0 == ST['ISS'])), coverage=float(np.nanmean(cov)),
               final_states={k: int(np.sum(state == v)) for k, v in ST.items()},
               eps={d_: float(use_err[d_][(t_i + d_ <= HORIZON) & (state != ST['ABS'])].mean()) for d_ in use_err},
               monthly_Uev={mm: float(np.mean([Uev[i] for i, d_ in enumerate(days) if str(pd.Timestamp('1970-01-01') + pd.Timedelta(days=d_))[:7] == mm]))
                            for mm in C.CERT_MONTHS},
               monthly_U={mm: float(np.mean([U[i] for i, d_ in enumerate(days) if str(pd.Timestamp('1970-01-01') + pd.Timedelta(days=d_))[:7] == mm]))
                          for mm in C.CERT_MONTHS},
               cert={k: dict(v) for k, v in cert.items()})
    if record:
        out['U_series'] = U; out['Uev_series'] = Uev; out['final_state'] = state; out['rows'] = rows; out['cur'] = cur; out['ver'] = ver
    return out


def finding_exposure(policy, R, L, tau_pair, gamma, stream_rows, f0):
    """Per-day exposure series, used for the day-block bootstrap of the E^ev ratio."""
    r = simulate(policy, R, L, tau_pair, gamma, stream_rows, f0, record=True)
    return np.array(r['Uev_series']), r


def run_sim(L, rho):
    tag = f'L{L}_rho{rho}'; d = f'{C.CACHE}/reval_{tag}'
    R = pickle.load(open(f'{d}/models.pkl', 'rb'))
    rho_mask = np.load(f'{d}/rho_mask.npy') if rho < 1.0 else None
    ptr = json.load(open(f'{C.OUT}/reval_ptr.json'))
    # frozen f0 (S7 detector): scores of stream rows and Jan-Feb rows from E1
    e1 = np.load(f'{C.CACHE}/scores/lgbm_trace_s11.npz'); sall = np.full(len(m), np.nan); sall[e1['idx']] = e1['s']
    cal_idx = np.where(m['split'] == 'cal')[0]
    f0 = dict(s=sall[R['stream']], s_all=sall, cal=calibrate(sall[cal_idx], y[cal_idx]), cal_month='2019-12')
    native = R['stream'][DAY[R['stream']] >= START]
    results = dict(tag=tag, L=L, rho=rho, gamma=ptr, native={}, streams={}, noise={})
    for tau_pair in ('primary', 'strict'):
        gamma = ptr['0.005' if tau_pair == 'primary' else '0.001']['gamma']
        for pol in POLICIES:
            if tau_pair == 'strict' and (pol.startswith('abl_') or pol.startswith('a2_')):
                continue
            r = simulate(pol, R, L, tau_pair, gamma, native, f0, rho_mask=rho_mask, record=(tau_pair == 'primary'))
            if tau_pair == 'primary':
                np.save(f'{d}/Uev_{pol}.npy', np.array(r['Uev_series'])); np.save(f'{d}/U_{pol}.npy', np.array(r['U_series']))
                for k_ in ('U_series', 'Uev_series', 'final_state', 'rows', 'cur', 'ver'):
                    r.pop(k_, None)
            results['native'][f'{tau_pair}|{pol}'] = r
            print(tag, tau_pair, pol, 'E_ev', r['E_ev'], 'E', r['E'], flush=True)
    # analyst-noise scenarios (KB7) for the review policies, 10 noise seeds
    if rho == 1.0:
        gamma = ptr['0.005']['gamma']
        for noise in (0.005, 0.01, 0.02):
            for pol in ('tracepe', 'vii_margin', 'vi_random', 'ii_review_changes', 'viii_reconcile'):
                vals = [simulate(pol, R, L, 'primary', gamma, native, f0, noise=noise, noise_seed=s_) for s_ in range(10)]
                results['noise'][f'{noise}|{pol}'] = dict(E_ev=[v['E_ev'] for v in vals],
                                                          yield_=[sum(e.get('review_hits', 0) for e in v['events']) / max(1, sum(e.get('reviews', 0) for e in v['events'])) for v in vals])
                if pol in ('tracepe', 'vii_margin'):
                    vr = [simulate(pol, R, L, 'primary', gamma, native, f0, noise=noise, noise_seed=s_, recon_reviewed=True) for s_ in range(10)]
                    results['noise'][f'{noise}|{pol}+rr'] = dict(E_ev=[v['E_ev'] for v in vr])
            print(tag, 'noise', noise, flush=True)
        # prevalence-resampled streams (D6): pi in {10, 5}% x 20 seeds
        for pi in (0.10, 0.05):
            for ss in C.STREAM_SEEDS:
                rng = np.random.default_rng(ss); keep = []
                for mm in C.CERT_MONTHS:
                    sel = native[month[native] == mm]; ib = sel[y[sel] == 0]; im = sel[y[sel] == 1]
                    k = int(round(pi * len(ib) / (1 - pi))); keep.append(np.r_[ib, rng.choice(im, min(k, len(im)), replace=False)])
                keep = np.concatenate(keep)
                for pol in ('tracepe', 'viii_reconcile', 'i_auto', 'vii_margin', 'vi_random', 'ii_review_changes'):
                    r = simulate(pol, R, L, 'primary', gamma, keep, f0)
                    results['streams'].setdefault(f'{pi}|{pol}', []).append(dict(E_ev=r['E_ev'], E=r['E'], n=r['n'],
                        reviews=sum(e.get('reviews', 0) for e in r['events']), hits=sum(e.get('review_hits', 0) for e in r['events'])))
            print(tag, 'pi', pi, flush=True)
    pickle.dump(results, open(f'{C.OUT}/reval_{tag}.pkl', 'wb'))
    print('saved', tag)


if __name__ == '__main__':
    if sys.argv[1] == 'ptr':
        run_ptr()
    elif sys.argv[1] == 'models':
        run_models(int(sys.argv[2]), float(sys.argv[3]))
    elif sys.argv[1] == 'sim':
        run_sim(int(sys.argv[2]), float(sys.argv[3]))
