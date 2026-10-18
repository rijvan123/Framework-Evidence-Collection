#!/usr/bin/env python3
"""E6 - label-free drift monitor M8 (KS on margins, mean PSI, credibility, Page-Hinkley, C2ST; per predicted
class; temporally blocked nulls; persistence P = 2) and adaptive conformal inference (KT; paper Section 8.6)."""
import numpy as np

import _common  # noqa: F401
from _common import f0, primary_tau
from tracepe.config import cli
from tracepe.decision.calibration import Isotonic
from tracepe.decision.conformal import ICE
from tracepe.drift.aci import aci_alarms
from tracepe.drift.monitor import alarm_rule, c2st_auc, ks, page_hinkley, psi_mean
from tracepe.features.groups import COFF_COL, D
from tracepe.run import Run
from tracepe.utils import day_number, day_string, log


def main():
    cfg, args = cli(__doc__)
    run = Run(cfg)
    mc = cfg['monitor']
    m = run.meta
    key0, seed0 = f0(cfg)
    b = run.store()
    info = run.load('e1_models')[key0][str(seed0)]
    from tracepe.models.zoo import model_from_bytes
    f = model_from_bytes(key0, seed0, b.get(info['store']))
    th = run.load('e1_metrics_raw')['thresholds'][key0][str(seed0)][f'cp{primary_tau(cfg):g}']['theta']
    dated = np.flatnonzero((m['stratum'] == 'Dated').to_numpy())
    day = m['day'].to_numpy()[dated]
    r0, r1 = day_number(mc['ref_start']), day_number(mc['ref_end'])
    t0, t1 = day_number(mc['start']), day_number(mc['end'])
    sel = dated[((day >= r0) & (day <= r1)) | ((day >= t0) & (day <= t1))]
    sday = m['day'].to_numpy()[sel]
    y = m['y'].to_numpy()[sel]
    X = run.take(sel)
    z = f.score(X)
    yhat = (z > th).astype(int)
    cal = m['month'].to_numpy()[sel] == mc['model_ref_month']
    iso = Isotonic().fit(z[cal], y[cal])
    p1 = iso.predict(z)
    ice = ICE().fit(p1[cal], y[cal])
    cred = ice.credibility(p1, yhat)
    keep = np.ones(D, bool)
    keep[COFF_COL] = False
    Xm = X[:, keep]
    W = int(mc['window_days'])
    c2 = dict(mc['c2st'], threads=run.threads)
    rng = np.random.default_rng(int(cfg['seeds']['f0']))
    ref_free = (sday >= r0) & (sday <= r1)
    dec0 = day_number(mc['model_ref_month'] + '-01')
    ref_model = (sday >= dec0) & (sday <= r1)

    def stats_for(win, ref_f, ref_m):
        out = {}
        for c in (0, 1):
            w = win & (yhat == c)
            rf = ref_f & (yhat == c)
            rm = ref_m & (yhat == c)
            if w.sum() < 4 or rf.sum() < 4 or rm.sum() < 4:
                out[c] = dict(ks=np.nan, psi=np.nan, cred=np.nan, c2st=np.nan)
                continue
            ridx = np.flatnonzero(rf)
            if len(ridx) > int(c2['max_ref']):
                ridx = np.sort(rng.choice(ridx, size=int(c2['max_ref']), replace=False))
            out[c] = dict(ks=ks(z[w], z[rm]), psi=psi_mean(Xm[ridx], Xm[w], int(mc['psi_bins'])),
                          cred=float(1 - cred[w].mean()), c2st=c2st_auc(Xm[w], Xm[ridx], c2))
        return out

    # ---- blocked nulls: model-free statistics on Oct-Dec (86 windows), model-dependent on December (25 windows)
    null = {c: {s: [] for s in ('ks', 'psi', 'cred', 'c2st')} for c in (0, 1)}
    for st in range(r0, r1 - W + 2):
        win = (sday >= st) & (sday < st + W)
        free_rest = ref_free & ~win
        st_ = stats_for(win, free_rest, ref_model & ~win) if st >= dec0 else None
        for c in (0, 1):
            if st >= dec0 and st_ is not None:
                null[c]['ks'].append(st_[c]['ks'])
                null[c]['cred'].append(st_[c]['cred'])
                null[c]['psi'].append(st_[c]['psi'])
                null[c]['c2st'].append(st_[c]['c2st'])
            else:
                w = win & (yhat == c)
                rf = free_rest & (yhat == c)
                if w.sum() >= 4 and rf.sum() >= 4:
                    ridx = np.flatnonzero(rf)
                    if len(ridx) > int(c2['max_ref']):
                        ridx = np.sort(rng.choice(ridx, size=int(c2['max_ref']), replace=False))
                    null[c]['psi'].append(psi_mean(Xm[ridx], Xm[w], int(mc['psi_bins'])))
                    null[c]['c2st'].append(c2st_auc(Xm[w], Xm[ridx], c2))
    lam = {c: {s: float(np.nanmax(v)) if len(v) and np.isfinite(v).any() else np.inf for s, v in null[c].items()} for c in (0, 1)}
    # Page-Hinkley thresholds from the December daily series of 1 - mean credibility
    def daily(mask_days, c):
        ds = sorted(set(sday[mask_days]))
        return ds, np.array([1 - cred[(sday == d_) & (yhat == c)].mean() if ((sday == d_) & (yhat == c)).any() else np.nan for d_ in ds])
    ph_lam = {}
    for c in (0, 1):
        _, sdec = daily(ref_model, c)
        sdec = sdec[~np.isnan(sdec)]
        ph_lam[c] = float(page_hinkley(sdec, float(mc['ph_delta'])).max()) if len(sdec) else np.inf
    # ---- weekly test windows
    test = (sday >= t0) & (sday <= t1)
    starts = list(range(t0, t1 + 1, W))
    ph_series = {}
    for c in (0, 1):
        ds, sv = daily(test, c)
        sv = np.nan_to_num(sv, nan=np.nanmean(sv) if np.isfinite(sv).any() else 0)
        ph_series[c] = dict(zip(ds, page_hinkley(sv, float(mc['ph_delta']))))
    windows = []
    for st in starts:
        win = (sday >= st) & (sday < st + W) & test
        s_ = stats_for(win, ref_free, ref_model)
        ex = {}
        for c in (0, 1):
            for s in ('ks', 'psi', 'cred', 'c2st'):
                v = s_[c][s]
                ex[f'{s}_{c}'] = bool(np.isfinite(v) and v > lam[c][s])
            ph = max([v for d_, v in ph_series[c].items() if st <= d_ < st + W], default=0.0)
            ex[f'ph_{c}'] = bool(ph > ph_lam[c])
        windows.append(dict(start=day_string(st), stats={str(c): s_[c] for c in (0, 1)}, exceed=ex, any=any(ex.values())))
    alarms = alarm_rule(np.array([w['any'] for w in windows]), int(mc['persistence']))
    # ---- onset of the July shift (first week from onset_from with unseen-family share above the bar)
    tr = run.rows(split='train')
    seen = set(m['fam'].to_numpy()[tr][m['y'].to_numpy()[tr] == 1])
    fam = m['fam'].to_numpy()[sel]
    onset = None
    for st in starts:
        if st < day_number(mc['onset_from']):
            continue
        wm = (sday >= st) & (sday < st + W) & (y == 1)
        if wm.any() and np.mean(~np.isin(fam[wm], list(seen))) > float(mc['onset_unseen_share']):
            onset = st
            break
    alarm_days = [starts[a] + W - 1 for a in alarms]
    stable = mc['stable_months']
    false_by_month = {mo: sum(day_string(d_)[:7] == mo for d_ in alarm_days) for mo in stable}
    within = [d_ for d_ in alarm_days if onset is not None and onset <= d_ <= onset + int(mc['kt_days'])]
    KT = dict(alarms=len(alarm_days), alarm_days=[day_string(d_) for d_ in alarm_days], onset=day_string(onset) if onset else None,
              alarm_within_14d=bool(within), false_alarms_stable=false_by_month,
              passes=bool(within) and all(v <= 1 for v in false_by_month.values()))
    KT['kill_met'] = not KT['passes']
    exceed_counts = {k: sum(w['exceed'][k] for w in windows) for k in windows[0]['exceed']} if windows else {}
    # ---- ACI with delayed labels
    pv = np.column_stack([ice.credibility(p1, np.zeros(len(p1), int)), ice.credibility(p1, np.ones(len(p1), int))])
    order = np.argsort(sday[test], kind='stable')
    tidx = np.flatnonzero(test)[order]
    aci = {}
    for dl in mc['aci']['delays']:
        a = aci_alarms(sday[tidx], pv[tidx], y[tidx], float(mc['aci']['alpha']), float(mc['aci']['gamma']), int(dl))
        ad = a['alarms']
        aci[str(dl)] = dict(alarms=len(ad), first=day_string(ad[0]) if ad else None,
                            first_after_onset=day_string(next((d_ for d_ in ad if onset and d_ >= onset), 0)) if (onset and any(d_ >= onset for d_ in ad)) else None,
                            per_month={mo: sum(day_string(d_)[:7] == mo for d_ in ad) for mo in sorted(set(day_string(d_)[:7] for d_ in ad))})
    R = dict(lambda_=lam, ph_lambda=ph_lam, null_windows={c: {s: len(v) for s, v in null[c].items()} for c in (0, 1)},
             windows=windows, exceed_counts=exceed_counts, n_windows=len(windows),
             windows_with_any=int(sum(w['any'] for w in windows)), KT=KT, aci=aci)
    run.save('e6_monitor', R)
    log('E6 done: alarms', KT['alarm_days'], 'onset', KT['onset'], 'KT kill met', KT['kill_met'])


if __name__ == '__main__':
    main()
