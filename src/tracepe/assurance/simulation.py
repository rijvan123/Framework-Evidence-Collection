"""Assurance-plane simulation (paper Sections 4.6, 7.6 and 8.7; S7 Algorithms 5 and 6).

The simulation replays the native Dated stream with real scores and labels. Findings are issued per UTC
day from ``assurance.start`` to ``assurance.end``; labels mature after L days (coverage rho_L); models are
retrained monthly on matured labels; a finding is ABSTAINED when its ICE credibility is below kappa,
SCREENING-ONLY when no valid prospective certificate covers its issue day, and ISSUED otherwise.
Re-validation policies act at the update events. The primary endpoint is the evaluative exposure
E^ev_T (Eq. (98)): finding-days during which an erroneous finding is held in an evaluative state
(ISSUED with a valid certificate, CONFIRMED, CORRECTED, RECONCILED).

Implementation choices the paper leaves open are listed in docs/IMPLEMENTATION_NOTES.md (section
'Assurance plane'); every one of them is a parameter in configs/default.yaml."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from ..decision.calibration import Isotonic
from ..decision.certificates import retrospective
from ..decision.conformal import ICE, kappa_for_rate, per_class_kappa
from ..decision.thresholds import certified_threshold, cp_upper
from ..evaluation.stats import block_bootstrap_sums
from ..models import lgbm as L
from ..utils import day_number, month_end_day, month_start_day

INF = 10 ** 9
ISS, SCR, ABS, FLG, AUT, CON, COR, REC, EXP = range(9)
STATE_NAMES = ['ISS', 'SCR', 'ABS', 'FLG', 'AUT', 'CON', 'COR', 'REC', 'EXP']
EVALUATIVE = np.zeros(9, bool)
EVALUATIVE[[ISS, CON, COR, REC]] = True


@dataclass
class Issuer:
    k: int
    start: int                       # first day this model issues findings
    cal_month: str
    theta: float
    k_star: int
    certified: bool
    kappa: float
    kappa_cls: dict
    z: np.ndarray                    # margins on the universe U
    p: np.ndarray                    # isotonic probabilities on U
    yhat: np.ndarray
    cred: np.ndarray
    certs: list = field(default_factory=list)
    booster: object = None
    n_train: int = 0


class Universe:
    """Dated rows used by the simulation (training history, calibration months and the issuance period)."""

    def __init__(self, run, cfg):
        a = cfg['assurance']
        m = run.meta
        dated = (m['stratum'] == 'Dated').to_numpy()
        self.rows = np.flatnonzero(dated)
        self.rows = self.rows[np.argsort(m['order'].to_numpy()[self.rows], kind='stable')]
        sub = m.iloc[self.rows]
        self.day = sub['day'].to_numpy()
        self.month = sub['month'].to_numpy()
        self.y = sub['y'].to_numpy().astype(int)
        self.order = sub['order'].to_numpy()
        self.run = run
        self.cfg = cfg
        self.test_start = day_number(cfg['screen']['test_start'])
        self.start = day_number(a['start'])
        self.end = day_number(a['end'])
        self.horizon = day_number(a['horizon'])
        self.scored = np.flatnonzero(self.day >= day_number(cfg['screen']['calibration_month'] + '-01'))

    def X(self, pos):
        return self.run.take(self.rows[pos])

    def covered(self, rho: float, seed: int) -> np.ndarray:
        """Labels that ever mature: historical labels always; deployment-period labels with probability rho."""
        if rho >= 1:
            return np.ones(len(self.rows), bool)
        rng = np.random.default_rng(seed)
        cov = rng.random(len(self.rows)) < rho
        cov[self.day < self.test_start] = True
        return cov


def _calibrate(U: Universe, booster, cal_pos, a_cfg, conf_cfg, scored_X_cache) -> dict:
    z_cal = L.margin(booster, U.X(cal_pos))
    y_cal = U.y[cal_pos]
    cert = certified_threshold(z_cal[y_cal == 0], a_cfg['tau_fpr'])
    iso = Isotonic().fit(z_cal, y_cal)
    ice = ICE().fit(iso.predict(z_cal), y_cal)
    yhat_cal = (z_cal > cert['theta']).astype(int)
    cred_cal = ice.credibility(iso.predict(z_cal), yhat_cal)
    kappa = kappa_for_rate(cred_cal, conf_cfg['max_abstention'])
    kappa_cls = per_class_kappa(cred_cal, yhat_cal, conf_cfg['transcendent_rejection'])
    z = L.margin(booster, scored_X_cache)
    p = iso.predict(z)
    yhat = (z > cert['theta']).astype(int)
    cred = ice.credibility(p, yhat)
    return dict(theta=cert['theta'], k_star=cert['k_star'], certified=cert['certified'], kappa=kappa,
                kappa_cls=kappa_cls, z=z, p=p, yhat=yhat, cred=cred)


def _certificates(U: Universe, iss: Issuer, Lday: int, covered, a_cfg, n_min: int) -> list:
    """Retrospective certificates of one issuer for every month from its calibration month on."""
    certs = []
    months = sorted(set(U.month[U.scored]))
    for mo in months:
        if mo < iss.cal_month:
            continue
        sel = (U.month[U.scored] == mo) & covered[U.scored]
        y = U.y[U.scored][sel]
        yh = iss.yhat[sel]
        fp = int(((yh == 1) & (y == 0)).sum())
        fn = int(((yh == 0) & (y == 1)).sum())
        c = retrospective(fp, int((y == 0).sum()), fn, int((y == 1).sum()), a_cfg['tau_fpr'], a_cfg['tau_fnr'], n_min)
        c['month'] = mo
        c['avail'] = iss.start if mo == iss.cal_month else month_end_day(mo) + Lday
        certs.append(c)
    return certs


def statement_valid(iss: Issuer, t: int, a_max: int) -> bool:
    """A prospective statement at day t: latest available certificate's FNR bound and the latest powered
    FPR bound within tolerance, and the newest certified month at most A_max days old."""
    av = [c for c in iss.certs if c['avail'] <= t]
    if not av:
        return False
    latest = max(av, key=lambda c: c['month'])
    fnr = [c for c in av if c['fnr_ub'] is not None]
    fpr = [c for c in av if c['fpr_powered']]
    if not fnr or not fpr:
        return False
    ok_fnr = max(fnr, key=lambda c: c['month'])['fnr_ok']
    ok_fpr = max(fpr, key=lambda c: c['month'])['fpr_ok']
    age = t - month_end_day(latest['month'])
    return bool(ok_fnr and ok_fpr and age <= a_max)


class Sequence:
    """Issuer-model sequence for one scenario: 'frozen' (f0 only), 'retrain' (monthly) or 'pct' (warm start)."""

    _cache: dict = {}

    def __init__(self, U: Universe, cfg: dict, Lday: int, rho: float, kind: str, seed: int, f0_booster=None, log=print):
        self.U, self.cfg, self.L, self.rho, self.kind = U, cfg, Lday, rho, kind
        a = cfg['assurance']
        self.covered = U.covered(rho, seed + 1000)
        n_min = int(cfg['screen']['n_min_benign'])
        threads = int(cfg['run'].get('threads', 2))
        block = cfg['models']['lgbm_trace']
        Xs = U.X(U.scored)
        cal0 = cfg['screen']['calibration_month']
        if f0_booster is None:
            tr = np.flatnonzero(U.day < day_number(cfg['screen']['train_end']))
            tr = np.sort(U.rows[tr])                        # file order, as in the paper's f0 fit
            f0_booster = L.train_lgbm(U.run.take(tr), U.run.meta['y'].to_numpy()[tr], block, seed, threads)
        issuers = []
        cal_pos = np.flatnonzero(U.month == cal0)
        c = _calibrate(U, f0_booster, cal_pos, a, cfg['conformal'], Xs)
        issuers.append(Issuer(0, U.start, cal0, booster=f0_booster, **c))
        if kind != 'frozen':
            prev = f0_booster
            for k, ev in enumerate(a['events'], start=1):
                u = day_number(ev)
                m_cal = self._cal_month(u, n_min)
                if m_cal is None:
                    issuers.append(Issuer(k, u, issuers[-1].cal_month, booster=issuers[-1].booster,
                                          **{f: getattr(issuers[-1], f) for f in
                                             ('theta', 'k_star', 'certified', 'kappa', 'kappa_cls', 'z', 'p', 'yhat', 'cred')}))
                    continue
                start_cal = month_start_day(m_cal)
                tr_pos = np.flatnonzero((U.day < start_cal) & self._matured(u))
                cal_pos = np.flatnonzero((U.month == m_cal) & self.covered)
                key = (kind, m_cal, rho, Lday if kind == 'pct' else None, seed, len(tr_pos))
                if key in Sequence._cache:
                    booster = Sequence._cache[key]
                else:
                    rows_tr = np.sort(U.rows[tr_pos])
                    Xtr = U.run.take(rows_tr)
                    ytr = U.run.meta['y'].to_numpy()[rows_tr]
                    if kind == 'pct':
                        prev_pred = (prev.predict(Xtr, raw_score=True) > issuers[-1].theta).astype(int)
                        w = np.where(prev_pred == ytr, 2.0, 1.0)
                        extra = dict(block)
                        extra['rounds'] = int(cfg['assurance'].get('pct_rounds', 100))
                        booster = L.train_lgbm(Xtr, ytr, extra, seed, threads, weight=w, init_model=prev)
                    else:
                        booster = L.train_lgbm(Xtr, ytr, block, seed, threads)
                    Sequence._cache[key] = booster
                    log(f'  [{kind} L={Lday} rho={rho}] model {k} at {ev}: train {len(tr_pos)} rows, calibrate {m_cal}')
                c = _calibrate(U, booster, cal_pos, a, cfg['conformal'], Xs)
                issuers.append(Issuer(k, u, m_cal, booster=booster, n_train=len(tr_pos), **c))
                prev = booster
        for iss in issuers:
            iss.certs = _certificates(U, iss, Lday, self.covered, a, n_min)
        self.issuers = issuers

    def _matured(self, u: int) -> np.ndarray:
        return (self.U.day + self.L <= u) & self.covered | (self.U.day < self.U.test_start)

    def _cal_month(self, u: int, n_min: int):
        months = sorted(set(self.U.month), reverse=True)
        for mo in months:
            if month_end_day(mo) + self.L > u:
                continue
            sel = (self.U.month == mo) & self.covered & (self.U.y == 0)
            if sel.sum() >= n_min:
                return mo
        return None

    def issuer_for(self, days: np.ndarray) -> np.ndarray:
        starts = np.array([i.start for i in self.issuers])
        return np.searchsorted(starts, days, side='right') - 1


POLICIES = {
    'frozen_none': dict(seq='frozen', abstain=None, gate=False, act='none', label='A2: frozen f₀, no safeguards'),
    'frozen_kappa_cert': dict(seq='frozen', abstain='ice', gate=True, act='none', label='(viii-f) frozen f₀ + κ + certificates'),
    'retrain_only': dict(seq='retrain', abstain=None, gate=False, act='none', label='A2: monthly retrain only'),
    'retrain_cert': dict(seq='retrain', abstain=None, gate=True, act='none', label='A2: retrain + certificate gating'),
    'retrain_kappa': dict(seq='retrain', abstain='ice', gate=False, act='none', label='A2: retrain + κ abstention'),
    'viii': dict(seq='retrain', abstain='ice', gate=True, act='none', label='(viii) retrain + κ + certificates, no review'),
    'trace': dict(seq='retrain', abstain='ice', gate=True, act='trace', label='TRACE-PE (budgeted re-validation)'),
    'i_autoaccept': dict(seq='retrain', abstain='ice', gate=True, act='autoaccept', label='(i) re-score, auto-accept'),
    'ii_review_changes': dict(seq='retrain', abstain='ice', gate=True, act='review_changes', label='(ii) review changes'),
    'iii_calendar': dict(seq='retrain', abstain='ice', gate=True, act='calendar', label='(iii) calendar re-validation'),
    'iv_transcendent': dict(seq='retrain', abstain='transcendent', gate=True, act='none', label='(iv) Transcendent 10%'),
    'v_pct': dict(seq='pct', abstain='ice', gate=True, act='autoaccept', label='(v) PCT-adapted, auto'),
    'vi_random': dict(seq='retrain', abstain='ice', gate=True, act='random', label='(vi) random review'),
    'vii_margin': dict(seq='retrain', abstain='ice', gate=True, act='margin', label='(vii) lowest-margin review'),
    'abl_noregion': dict(seq='retrain', abstain='ice', gate=True, act='trace', no_region=True, label='ablation: no region selection'),
    'abl_noflag': dict(seq='retrain', abstain='ice', gate=True, act='trace', no_flag=True, label='ablation: no flagging'),
    'abl_nogate': dict(seq='retrain', abstain='ice', gate=True, act='trace', no_gate=True, label='ablation: no harm gate'),
    'abl_noauto': dict(seq='retrain', abstain='ice', gate=True, act='trace', no_auto=True, label='ablation: no auto-amendment'),
}


class Findings:
    """Issued findings of one stream (native or prevalence-resampled)."""

    def __init__(self, U: Universe, sel=None):
        pos = np.flatnonzero((U.day >= U.start) & (U.day <= U.end))
        if sel is not None:
            pos = pos[sel]
        self.pos = pos                                                # positions in U
        self.spos = np.searchsorted(U.scored, pos)                    # positions in the scored arrays
        self.day = U.day[pos]
        self.y = U.y[pos]
        self.month = U.month[pos]
        self.order = U.order[pos]


def density_ratio(U: Universe, window_pos, scope_pos, cfg, seed: int = 1) -> np.ndarray:
    """Eq. (93): domain classifier (window vs reference Oct-Dec 2019) -> n_ref/n_win * p/(1-p) for the scope."""
    import lightgbm as lgb
    from sklearn.model_selection import StratifiedKFold
    mon = cfg['monitor']
    ref = np.flatnonzero((U.day >= day_number(mon['ref_start'])) & (U.day <= day_number(mon['ref_end'])))
    rng = np.random.default_rng(seed)
    cap = int(mon['c2st'].get('max_ref', 6000))
    if len(ref) > cap:
        ref = np.sort(rng.choice(ref, size=cap, replace=False))
    Xw = U.X(window_pos)
    Xr = U.X(ref)
    Z = np.vstack([Xw, Xr])
    dz = np.r_[np.ones(len(Xw)), np.zeros(len(Xr))]
    p = dict(objective='binary', num_leaves=31, learning_rate=0.1, feature_fraction=0.5, seed=7, deterministic=True,
             force_row_wise=True, num_threads=int(cfg['run'].get('threads', 2)), verbose=-1)
    rounds = int(mon['c2st'].get('rounds', 100))
    oof = np.zeros(len(dz))
    models = []
    for trn, tst in StratifiedKFold(2, shuffle=True, random_state=seed).split(Z, dz):
        clf = lgb.train(p, lgb.Dataset(Z[trn], label=dz[trn]), num_boost_round=rounds)
        oof[tst] = clf.predict(Z[tst])
        models.append(clf)
    in_win = {int(q): i for i, q in enumerate(window_pos)}
    out = np.empty(len(scope_pos))
    miss = [j for j, q in enumerate(scope_pos) if int(q) not in in_win]
    for j, q in enumerate(scope_pos):
        if int(q) in in_win:
            out[j] = oof[in_win[int(q)]]
    if miss:
        Xm = U.X(np.asarray(scope_pos)[miss])
        out[miss] = np.mean([m.predict(Xm) for m in models], axis=0)
    out = np.clip(out, 1e-6, 1 - 1e-6)
    return (len(Xr) / max(len(Xw), 1)) * out / (1 - out)


def simulate(seq: Sequence, F: Findings, policy: str, cfg: dict, noise: float = 0.0, noise_seed: int = 0,
             override: bool = False, gamma: float = 0.5, wcache: dict | None = None) -> dict:
    """Run one policy on one stream; returns exposures, daily series, review and kill-criterion statistics."""
    P = POLICIES[policy]
    a = cfg['assurance']
    U = seq.U
    Lday = seq.L
    n = len(F.pos)
    iss_idx = seq.issuer_for(F.day) if P['seq'] != 'frozen' else np.zeros(n, int)
    issuers = seq.issuers
    cur = np.empty(n, int)
    cred0 = np.empty(n)
    state = np.empty(n, int)
    for k in np.unique(iss_idx):
        m = iss_idx == k
        cur[m] = issuers[k].yhat[F.spos[m]]
        cred0[m] = issuers[k].cred[F.spos[m]]
    # issuance states (Eq. (91))
    valid_cache = {}
    for i in range(n):
        k = iss_idx[i]
        if P['abstain'] == 'ice' and cred0[i] < issuers[k].kappa:
            state[i] = ABS
            continue
        if P['abstain'] == 'transcendent' and cred0[i] < issuers[k].kappa_cls[int(cur[i])]:
            state[i] = ABS
            continue
        if P['gate']:
            key = (k, int(F.day[i]))
            if key not in valid_cache:
                valid_cache[key] = statement_valid(issuers[k], int(F.day[i]), int(a['A_max']))
            state[i] = ISS if valid_cache[key] else SCR
        else:
            state[i] = ISS
    covered = seq.covered[F.pos]
    rec_day = np.where(covered, F.day + Lday, INF)
    reviewed = np.zeros(n, bool)
    rng = np.random.default_rng(noise_seed)
    issued_state = state.copy()
    # bound expiry: certificate of the issuing model for the issue month fails when it becomes available
    exp_day = np.full(n, INF)
    if P['gate']:
        for k in np.unique(iss_idx):
            for c in issuers[k].certs:
                if not c['valid']:
                    m = (iss_idx == k) & (F.month == c['month']) & (state == ISS)
                    exp_day[m] = np.minimum(exp_day[m], c['avail'])
    events = [day_number(e) for e in a['events']] if P['act'] != 'none' else []
    budget_frac = float(a['budget_frac'])
    win_days = int(a['budget_window_days'])
    stats = dict(updates=[], reviews=0, corrections=0, harmful_auto=0, auto=0, flagged=0)
    days = np.arange(U.start, U.horizon + 1)
    U_ev = np.zeros(len(days))
    U_all = np.zeros(len(days))
    live_n = np.zeros(len(days))
    ev_n = np.zeros(len(days))
    y = F.y
    for di, t in enumerate(days):
        if t in events:
            k = int(np.searchsorted([i.start for i in issuers], t, side='right') - 1)
            r = issuers[k]
            S = np.flatnonzero((F.day < t) & np.isin(state, [ISS, SCR, FLG, AUT, EXP]) & (rec_day > t))
            if len(S):
                zp = r.z[F.spos[S]]
                yp = r.yhat[F.spos[S]]
                pp = r.p[F.spos[S]]
                credp = r.cred[F.spos[S]]
                q = np.where(cur[S] == 0, pp, 1 - pp)
                changed = yp != cur[S]
                issued_win = int(((F.day >= t - win_days) & (F.day < t)).sum())
                B = int(math.ceil(budget_frac * issued_win))
                harmful = int((changed & (cur[S] == y[S])).sum())
                stats['updates'].append(dict(day=int(t), scope=int(len(S)), budget=B, changes=int(changed.sum()),
                                             harmful=harmful, h_ub=cp_upper(harmful, len(S)), auto=0, harmful_auto=0))
                rev = np.array([], int)
                act = P['act']
                if act == 'autoaccept':
                    ch = S[changed]
                    ha = int((cur[ch] == y[ch]).sum())
                    stats['auto'] += len(ch)
                    stats['harmful_auto'] += ha
                    stats['updates'][-1].update(auto=int(len(ch)), harmful_auto=ha)
                    cur[ch] = yp[changed]
                elif act == 'review_changes':
                    ch = S[changed]
                    rev = rng.permutation(ch)[:B]
                elif act == 'calendar':
                    state[S[changed]] = FLG
                elif act == 'random':
                    rev = rng.choice(S, size=min(B, len(S)), replace=False)
                elif act == 'margin':
                    rev = S[np.argsort(np.abs(zp - r.theta), kind='stable')[:B]]
                elif act == 'trace':
                    no_region = P.get('no_region', False)
                    if no_region:
                        R = np.arange(len(S))
                    else:
                        wkey = (seq.kind, seq.L, seq.rho, int(t), len(S))
                        if wcache is not None and wkey in wcache:
                            w = wcache[wkey]
                        else:
                            win = np.flatnonzero((U.day >= t - win_days) & (U.day < t) & (U.day >= U.start))
                            w = density_ratio(U, win, F.pos[S], cfg)
                            if wcache is not None:
                                wcache[wkey] = w
                        cand = np.flatnonzero(w >= float(a['omega']))
                        cap = int(a['c_R']) * B
                        top = cand[np.argsort(-w[cand], kind='stable')[:cap]]
                        R = np.union1d(top, np.flatnonzero(changed))
                    order = np.lexsort((F.order[S][R], cred0[S][R], -q[R]))
                    Rs = R[order]
                    rev_loc = Rs[:B]
                    rest = Rs[B:]
                    if no_region:
                        rest = rest[changed[rest]]
                    gate_ok = np.ones(len(rest), bool) if P.get('no_gate') else (q[rest] >= gamma) & (credp[rest] >= r.kappa)
                    auto = rest[changed[rest] & gate_ok]
                    if P.get('no_auto'):
                        auto = auto[:0]
                    flag = np.setdiff1d(rest, auto)
                    if P.get('no_flag'):
                        flag = flag[:0]
                    ha = int((cur[S[auto]] == y[S[auto]]).sum())
                    stats['auto'] += len(auto)
                    stats['harmful_auto'] += ha
                    stats['updates'][-1].update(auto=int(len(auto)), harmful_auto=ha)
                    cur[S[auto]] = yp[auto]
                    state[S[auto]] = AUT
                    state[S[flag]] = FLG
                    stats['flagged'] += len(flag)
                    rev = S[rev_loc]
                if len(rev):
                    lab = y[rev].copy()
                    flip = rng.random(len(rev)) < noise
                    lab[flip] = 1 - lab[flip]
                    was_wrong = cur[rev] != y[rev]
                    stats['reviews'] += len(rev)
                    stats['corrections'] += int((was_wrong & (lab == y[rev])).sum())
                    stats.setdefault('wrong_reviewed', 0)
                    stats['wrong_reviewed'] += int(was_wrong.sum())
                    state[rev] = np.where(lab == cur[rev], CON, COR)
                    cur[rev] = lab
                    reviewed[rev] = True
        # expiry of statements whose certificate failed
        ex = (exp_day == t) & (state == ISS)
        state[ex] = EXP
        # reconciliation at label maturity (Algorithm 6 never reconciles reviewed findings unless overridden)
        rc = (rec_day == t) & (state != ABS) & (override | ~np.isin(state, [CON, COR]))
        cur[rc] = y[rc]
        state[rc] = REC
        issued = (F.day <= t) & (state != ABS)
        wrong = issued & (cur != y)
        U_ev[di] = (wrong & EVALUATIVE[state]).sum()
        U_all[di] = wrong.sum()
        live = issued & (rec_day > t) | (issued & np.isin(state, [CON, COR]))
        live_n[di] = live.sum()
        ev_n[di] = (live & EVALUATIVE[state]).sum()
    cov = np.divide(ev_n, live_n, out=np.zeros_like(ev_n), where=live_n > 0)
    return dict(policy=policy, label=P['label'], E_ev=float(U_ev.sum()), E=float(U_all.sum()),
                abstained=int((issued_state == ABS).sum()), screening=int((issued_state == SCR).sum()),
                issued_evaluative=int((issued_state == ISS).sum()), findings=n,
                coverage=float(cov[live_n > 0].mean()) if (live_n > 0).any() else float('nan'),
                reviews=stats['reviews'], corrections=stats['corrections'],
                yield_=(stats.get('wrong_reviewed', 0) / stats['reviews']) if stats['reviews'] else None,
                auto=stats['auto'], harmful_auto=stats['harmful_auto'], flagged=stats['flagged'],
                updates=stats['updates'], U_ev=U_ev, U=U_all)


def exposure_ci(U_ev, block: int, B: int, seed: int = 0) -> list[float]:
    s = block_bootstrap_sums([U_ev], block, B, seed)[:, 0]
    return [float(np.percentile(s, 2.5)), float(np.percentile(s, 97.5))]


def relative_reduction_ci(U_ref, U_pol, block: int, B: int, seed: int = 0) -> dict:
    s = block_bootstrap_sums([U_ref, U_pol], block, B, seed)
    ref, pol = s[:, 0], s[:, 1]
    rel = np.where(ref > 0, 1 - pol / np.maximum(ref, 1e-12), 0.0)
    point = 1 - (np.sum(U_pol) / np.sum(U_ref)) if np.sum(U_ref) > 0 else 0.0
    return dict(point=float(point), ci=[float(np.percentile(rel, 2.5)), float(np.percentile(rel, 97.5))])


def flip_decomposition(seq: Sequence, F: Findings, window_days: int = 30) -> list[dict]:
    """Deviation D15: compare each finding's actual issuer with the next model, abstained findings included."""
    out = []
    iss_idx = seq.issuer_for(F.day)
    for k in range(1, len(seq.issuers)):
        t = seq.issuers[k].start
        sel = np.flatnonzero((F.day >= t - window_days) & (F.day < t))
        if not len(sel):
            continue
        yi = np.array([seq.issuers[iss_idx[i]].yhat[F.spos[i]] for i in sel])
        ci = np.array([seq.issuers[iss_idx[i]].cred[F.spos[i]] for i in sel])
        ka = np.array([seq.issuers[iss_idx[i]].kappa for i in sel])
        yn = seq.issuers[k].yhat[F.spos[sel]]
        y = F.y[sel]
        flip = yi != yn
        abst = ci < ka
        out.append(dict(update=int(t), rescored=int(len(sel)), abstained=int(abst.sum()), flips=int(flip.sum()),
                        flips_abstained=int((flip & abst).sum()), flips_confident=int((flip & ~abst).sum()),
                        harmful_mal_to_ben=int((flip & (y == 1) & (yi == 1)).sum()),
                        harmful_ben_to_mal=int((flip & (y == 0) & (yi == 0)).sum()),
                        corrective=int((flip & (yi != y) & (yn == y)).sum()),
                        malware=int((y == 1).sum()), benign=int((y == 0).sum())))
    return out


def pretest_replay_gamma(run, cfg, seed: int, log=print) -> dict:
    """Harm gate gamma by pre-test replay on 2019 data only (deviation D11)."""
    a = cfg['assurance']
    ptr = a['ptr']
    threads = int(cfg['run'].get('threads', 2))
    block = cfg['models']['lgbm_trace']
    m = run.meta
    dated = np.flatnonzero((m['stratum'] == 'Dated').to_numpy())
    day = m['day'].to_numpy()[dated]
    d = lambda s: day_number(s)

    def fit(tr_lo, tr_hi, cal_lo, cal_hi):
        tr = dated[(day >= d(tr_lo)) & (day < d(tr_hi))]
        cal = dated[(day >= d(cal_lo)) & (day < d(cal_hi))]
        b = L.train_lgbm(run.take(np.sort(tr)), m['y'].to_numpy()[np.sort(tr)], block, seed, threads)
        zc = L.margin(b, run.take(cal))
        yc = m['y'].to_numpy()[cal]
        cert = certified_threshold(zc[yc == 0], a['tau_fpr'])
        iso = Isotonic().fit(zc, yc)
        ice = ICE().fit(iso.predict(zc), yc)
        yh = (zc > cert['theta']).astype(int)
        kappa = kappa_for_rate(ice.credibility(iso.predict(zc), yh), cfg['conformal']['max_abstention'])
        return b, cert['theta'], iso, ice, kappa

    b0, th0, iso0, ice0, k0 = fit(ptr['train'][0], ptr['train'][1], ptr['cal'][0], ptr['cal'][1])
    b1, th1, iso1, ice1, k1 = fit(ptr['train'][0], ptr['train1_end'], ptr['cal1'][0], ptr['cal1'][1])
    scope = dated[(m['month'].to_numpy()[dated] == ptr['scope_month'])]
    Xs = run.take(scope)
    ys = m['y'].to_numpy()[scope]
    z0 = L.margin(b0, Xs)
    y0 = (z0 > th0).astype(int)
    c0 = ice0.credibility(iso0.predict(z0), y0)
    keep = c0 >= k0
    z1 = L.margin(b1, Xs)
    y1 = (z1 > th1).astype(int)
    p1 = iso1.predict(z1)
    c1 = ice1.credibility(p1, y1)
    q = np.where(y0 == 0, p1, 1 - p1)
    changed = (y1 != y0) & keep
    N = int(keep.sum())
    grid = []
    chosen = None
    for g in a['gamma_grid']:
        auto = changed & (q >= g) & (c1 >= k1)
        harmful = int((auto & (y0 == ys)).sum())
        ub = cp_upper(harmful, N) if N else float('nan')
        grid.append(dict(gamma=g, auto=int(auto.sum()), harmful=harmful, ub=ub))
        if chosen is None and ub <= float(a['tau_H']):
            chosen = g
    log(f'  PTR: scope {N}, changed {int(changed.sum())}, gamma = {chosen}')
    return dict(gamma=chosen if chosen is not None else max(a['gamma_grid']), scope=N, changed=int(changed.sum()), grid=grid)
