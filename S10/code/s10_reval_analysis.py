#!/usr/bin/env python3
"""Assurance-plane analysis: E^ev_T and E_T with day-block bootstrap CIs, relative reduction vs (viii) (K3), K1/K2 per
update, KB1 (yield, monthly U), KB7 (noise), KS2 (r_H bound), A2-component ablations, L / rho / pi sensitivity.
Output: out/reval_analysis.json"""
import os, glob, json, pickle
import numpy as np
import s10_common as C

out = {}
for f in sorted(glob.glob(f'{C.OUT}/reval_L*_rho*.pkl')):
    R = pickle.load(open(f, 'rb')); tag = R['tag']; d = f'{C.CACHE}/reval_{tag}'; nat = R['native']; res = dict(L=R['L'], rho=R['rho'])
    pols = sorted({k.split('|')[1] for k in nat if k.startswith('primary|')})
    series = {p: np.load(f'{d}/Uev_{p}.npy') for p in pols if os.path.exists(f'{d}/Uev_{p}.npy')}
    seriesU = {p: np.load(f'{d}/U_{p}.npy') for p in pols if os.path.exists(f'{d}/U_{p}.npy')}
    ndays = len(next(iter(series.values()))); blocks = np.arange(0, ndays, 7); rng = np.random.default_rng(13); B = 2000
    idx_b = [rng.choice(len(blocks), len(blocks)) for _ in range(B)]
    def boot_sum(v):
        return np.array([sum(v[blocks[b]:blocks[b] + 7].sum() for b in ib) for ib in idx_b])
    bs = {p: boot_sum(series[p]) for p in series}; bsU = {p: boot_sum(seriesU[p]) for p in seriesU}
    tab = {}
    for p in pols:
        r = nat[f'primary|{p}']
        ev = r['events']; reviews = sum(e.get('reviews', 0) or 0 for e in ev); hits = sum(e.get('review_hits', 0) or 0 for e in ev)
        auto = sum(e.get('auto', 0) or 0 for e in ev); harm = sum(e.get('harmful_auto', 0) or 0 for e in ev); flagged = sum(e.get('flagged', 0) or 0 for e in ev)
        row = dict(E_ev=r['E_ev'], E=r['E'], E_ev_ci=(float(np.percentile(bs[p], 2.5)), float(np.percentile(bs[p], 97.5))) if p in bs else None,
                   E_ci=(float(np.percentile(bsU[p], 2.5)), float(np.percentile(bsU[p], 97.5))) if p in bsU else None,
                   reviews=reviews, hits=hits, yield_=hits / reviews if reviews else None, auto=auto, harmful_auto=harm, flagged=flagged,
                   abstained=r['abstained'], scr=r['scr_at_issue'], iss=r['iss_at_issue'], coverage=r['coverage'], eps=r['eps'],
                   monthly_Uev=r['monthly_Uev'], monthly_U=r['monthly_U'])
        if 'viii_reconcile' in bs and p in bs:
            base = bs['viii_reconcile']; rr = np.where(base > 0, 1 - bs[p] / np.maximum(base, 1e-9), 0.0)
            row['rel_red_vs_viii'] = (1 - r['E_ev'] / nat['primary|viii_reconcile']['E_ev']) if nat['primary|viii_reconcile']['E_ev'] else 0.0
            row['rel_red_vs_viii_ci'] = (float(np.percentile(rr, 2.5)), float(np.percentile(rr, 97.5)))
            baseU = bsU['viii_reconcile']; rrU = np.where(baseU > 0, 1 - bsU[p] / np.maximum(baseU, 1e-9), 0.0)
            row['relE_red_vs_viii'] = 1 - r['E'] / nat['primary|viii_reconcile']['E'] if nat['primary|viii_reconcile']['E'] else 0.0
            row['relE_red_vs_viii_ci'] = (float(np.percentile(rrU, 2.5)), float(np.percentile(rrU, 97.5)))
        tab[p] = row
    res['policies'] = tab
    # K1 / K2 from full re-scoring (policy i) per update; KS2 r_H bound from TRACE-PE auto-amendments
    ev_i = nat['primary|i_auto']['events']; ev_t = nat['primary|tracepe']['events']
    k1 = [dict(event=e['event'], N=e['N'], B=e['B'], changes=e['changes'], r=e['changes'] / e['N'] if e['N'] else 0,
               le_B=bool(e['changes'] <= e['B'])) for e in ev_i]
    k2 = [dict(event=e['event'], N=e['N'], harmful=e.get('harmful_auto', 0) or 0,
               h_ub=C.cp_upper(e.get('harmful_auto', 0) or 0, e['N'])) for e in ev_i]
    ks2 = [dict(event=e['event'], harmful_auto=e.get('harmful_auto', 0) or 0, N=e['N'], rH_ub=C.cp_upper(e.get('harmful_auto', 0) or 0, e['N'])) for e in ev_t]
    res['K1'] = dict(updates=k1, n_le_B=int(sum(x['le_B'] for x in k1)), n_updates=len(k1), met=bool(sum(x['le_B'] for x in k1) >= int(np.ceil(0.75 * len(k1)))))
    res['K2'] = dict(updates=k2, met=bool(all(x['h_ub'] < 0.001 for x in k2)))
    res['KS2'] = dict(updates=ks2, pass_=bool(all(x['rH_ub'] <= 0.005 for x in ks2)))
    t3 = tab['tracepe']
    res['K3'] = dict(rel_red=t3.get('rel_red_vs_viii'), ci=t3.get('rel_red_vs_viii_ci'), met=bool(t3.get('rel_red_vs_viii_ci') is not None and t3['rel_red_vs_viii_ci'][1] < 0.10))
    y_t = t3['yield_'] or 0.0; y_v = tab['vii_margin']['yield_'] or 0.0
    lower_months = sum(1 for mm in C.CERT_MONTHS if t3['monthly_U'][mm] < tab['viii_reconcile']['monthly_U'][mm])
    res['KB1'] = dict(yield_tracepe=y_t, yield_margin=y_v, ratio=(y_t / y_v) if y_v else None, months_lower_U=lower_months,
                      pass_=bool(y_v and y_t >= 1.5 * y_v and lower_months >= 6))
    if R.get('noise'):
        nz = {k: dict(E_ev_mean=float(np.mean(v['E_ev'])), yield_mean=float(np.mean(v['yield_'])) if 'yield_' in v else None) for k, v in R['noise'].items()}
        adv = {}
        for r_ in ('0.005', '0.01', '0.02'):
            a = nz.get(f'{r_}|tracepe', {}).get('yield_mean'); b = nz.get(f'{r_}|vii_margin', {}).get('yield_mean')
            adv[r_] = (a - b) if (a is not None and b is not None) else None
        res['noise'] = nz; res['KB7'] = dict(yield_adv_tracepe_minus_margin=adv, adv_r0=(y_t - y_v),
                                             sign_holds=bool(adv.get('0.02') is not None and np.sign(adv['0.02']) == np.sign(y_t - y_v) and (y_t - y_v) > 0))
    if R.get('streams'):
        st = {}
        for k, v in R['streams'].items():
            E = np.array([x['E_ev'] for x in v]); st[k] = dict(E_ev_mean=float(E.mean()), E_ev_ci=(float(np.percentile(E, 2.5)), float(np.percentile(E, 97.5))),
                                                              E_mean=float(np.mean([x['E'] for x in v])), n_mean=float(np.mean([x['n'] for x in v])))
        for pi in ('0.1', '0.05'):
            a = np.array([x['E_ev'] for x in R['streams'][f'{pi}|tracepe']]); b = np.array([x['E_ev'] for x in R['streams'][f'{pi}|viii_reconcile']])
            st[f'{pi}|rel_red_tracepe_vs_viii'] = float(1 - a.sum() / b.sum()) if b.sum() else 0.0
        res['streams'] = st
    # A2 component ablation (calendar retraining, abstention, certificate gating)
    if 'a2_naive' in tab:
        base = tab['a2_naive']['E_ev']; fz = tab.get('a2_naive_frozen', {}).get('E_ev')
        res['A2_ablation'] = {p: dict(E_ev=tab[p]['E_ev'], red_vs_naive=1 - tab[p]['E_ev'] / base if base else None,
                                      red_vs_naive_frozen=(1 - tab[p]['E_ev'] / fz) if fz else None)
                              for p in ('a2_naive_frozen', 'viii_frozen', 'a2_naive', 'a2_cert', 'a2_abst', 'viii_reconcile', 'tracepe') if p in tab}
    out[tag] = res
    print(tag, 'K1', res['K1']['met'], 'K2', res['K2']['met'], 'K3', res['K3'], 'KB1', res['KB1']['pass_'])
C.jdump(out, f'{C.OUT}/reval_analysis.json')
