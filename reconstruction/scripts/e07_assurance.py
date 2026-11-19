#!/usr/bin/env python3
"""E7 - assurance-plane simulation (paper Section 8.7; S7 Algorithms 5-6): cumulative safeguards, re-validation
policies (i)-(viii) and TRACE-PE with ablations, kill criteria K1-K3, flip decomposition (D15), label-delay
and label-coverage sensitivity, analyst noise, prevalence-resampled streams and the harm gate by pre-test replay."""
import numpy as np

import _common  # noqa: F401
from tracepe.assurance import simulation as S
from tracepe.config import cli
from tracepe.decision.thresholds import cp_upper
from tracepe.models.zoo import model_from_bytes
from tracepe.run import Run
from tracepe.utils import day_number, day_string, log, month_list

PRIMARY = ['frozen_none', 'frozen_kappa_cert', 'retrain_only', 'retrain_cert', 'retrain_kappa', 'viii', 'trace',
           'i_autoaccept', 'ii_review_changes', 'iii_calendar', 'iv_transcendent', 'v_pct', 'vi_random', 'vii_margin',
           'abl_noregion', 'abl_noflag', 'abl_nogate', 'abl_noauto']
SENS = ['frozen_none', 'retrain_only', 'viii', 'trace', 'vii_margin', 'abl_noregion']


def summarize(res, a, seed):
    out = {k: v for k, v in res.items() if k not in ('U_ev', 'U')}
    out['E_ev_ci'] = S.exposure_ci(res['U_ev'], int(a['block_days']), 1000, seed)
    out['E_ci'] = S.exposure_ci(res['U'], int(a['block_days']), 1000, seed)
    return out


def main():
    def extra(ap):
        ap.add_argument('--skip', nargs='*', default=[], choices=['sensitivity', 'noise', 'streams', 'ptr'])
    cfg, args = cli(__doc__, extra)
    run = Run(cfg)
    a = cfg['assurance']
    seed = int(cfg['seeds']['f0'])
    U = S.Universe(run, cfg)
    info = run.load('e1_models')['lgbm_trace'][str(seed)]
    f0 = model_from_bytes('lgbm_trace', seed, run.store().get(info['store'])).obj
    R = dict(primary={}, scenarios={}, noise={}, streams={})
    # harm gate by pre-test replay on 2019 data only
    if 'ptr' not in args.skip:
        R['ptr'] = S.pretest_replay_gamma(run, cfg, seed, log)
        gamma = R['ptr']['gamma']
    else:
        gamma = float(a['gamma_grid'][0])
    Lp = int(a['primary_L'])
    seqs = {}

    def seq(kind, Lday, rho):
        k = (kind, Lday, rho)
        if k not in seqs:
            seqs[k] = S.Sequence(U, cfg, Lday, rho, kind, seed, f0_booster=f0, log=log)
        return seqs[k]

    F = S.Findings(U)
    wcache = {}
    base = {}
    for pol in PRIMARY:
        kind = S.POLICIES[pol]['seq']
        res = S.simulate(seq(kind, Lp, 1.0), F, pol, cfg, gamma=gamma, wcache=wcache)
        base[pol] = res
        R['primary'][pol] = summarize(res, a, seed)
        log(f'  {S.POLICIES[pol]["label"]:45s} E_ev {res["E_ev"]:9.0f}  E {res["E"]:9.0f}  reviews {res["reviews"]}')
    ref = base['viii']['U_ev']
    # daily series of wrong findings in evaluative states for the cumulative safeguards (figure)
    R['series'] = dict(start=a['start'], horizon=a['horizon'],
                       U_ev={p: [int(v) for v in base[p]['U_ev']] for p in
                             ('frozen_none', 'retrain_only', 'retrain_cert', 'retrain_kappa', 'viii', 'frozen_kappa_cert', 'trace')})
    for pol in PRIMARY:
        R['primary'][pol]['ratio_to_viii'] = (base[pol]['E_ev'] / base['viii']['E_ev']) if base['viii']['E_ev'] else None
    # kill criteria at the primary label delay
    upd = base['trace']['updates']
    k1_ok = sum(u['changes'] <= u['budget'] for u in upd)
    R['K1'] = dict(updates=upd, updates_with_changes_le_B=k1_ok, n_updates=len(upd), met=k1_ok >= int(np.ceil(0.75 * len(upd))))
    R['K2'] = dict(max_h_ub=max((u['h_ub'] for u in upd), default=None), met=all(u['h_ub'] < 0.001 for u in upd))
    rr = S.relative_reduction_ci(ref, base['trace']['U_ev'], int(a['block_days']), 1000, seed)
    R['K3'] = dict(relative_reduction=rr['point'], ci=rr['ci'], met=rr['ci'][1] < 0.10)
    R['decision'] = 'A2' if ((R['K1']['met'] and R['K2']['met']) or R['K3']['met']) else 'A9'
    y_tr, y_m = base['trace'], base['vii_margin']
    # KB1: yield >= 1.5 x lowest-margin review AND lower live exposure U(t) (all live wrong findings) in >= 6/7 months
    days = np.arange(day_number(a['start']), day_number(a['horizon']) + 1)
    mon = np.array([day_string(int(d))[:7] for d in days])
    months_iss = month_list(a['start'][:7], a['end'][:7])
    lower = sum(float(y_tr['U'][mon == mo].sum()) < float(y_m['U'][mon == mo].sum()) for mo in months_iss)
    yield_ok = bool(y_tr['yield_'] is not None and y_m['yield_'] and y_tr['yield_'] >= 1.5 * y_m['yield_'])
    R['KB1'] = dict(yield_trace=y_tr['yield_'], yield_margin=y_m['yield_'],
                    ratio=(y_tr['yield_'] / y_m['yield_']) if (y_tr['yield_'] is not None and y_m['yield_']) else None,
                    months_lower_U=int(lower), months=len(months_iss),
                    met=bool(yield_ok and lower >= int(np.ceil(6 / 7 * len(months_iss)))))
    # KS2: one-sided CP-95% upper bound of the harmful auto-amendment rate r_H per update (denominator: in-scope findings)
    rh = [cp_upper(u['harmful_auto'], u['scope']) for u in upd if u['scope']]
    R['KS2'] = dict(max_rH_ub=max(rh, default=None), harmful_auto=y_tr['harmful_auto'], auto=y_tr['auto'],
                    met=bool(all(v <= float(a['tau_H']) for v in rh)))
    R['ablation_safeguards'] = {p: base[p]['E_ev'] for p in ('frozen_none', 'retrain_only', 'retrain_cert', 'retrain_kappa', 'viii', 'frozen_kappa_cert')}
    ro = base['retrain_only']['E_ev']
    R['ablation_safeguards']['viii_vs_retrain_only'] = (1 - base['viii']['E_ev'] / ro) if ro else None
    R['ablation_safeguards']['viii_vs_frozen'] = (1 - base['viii']['E_ev'] / base['frozen_none']['E_ev']) if base['frozen_none']['E_ev'] else None
    R['flips'] = S.flip_decomposition(seq('retrain', Lp, 1.0), F, int(a['budget_window_days']))
    tot = {k: sum(f[k] for f in R['flips']) for k in ('rescored', 'flips', 'flips_abstained', 'flips_confident', 'harmful_mal_to_ben',
                                                       'harmful_ben_to_mal', 'corrective', 'malware', 'benign')}
    tot['malware_regress_rate'] = tot['harmful_mal_to_ben'] / tot['malware'] if tot['malware'] else None
    tot['benign_flip_rate'] = tot['harmful_ben_to_mal'] / tot['benign'] if tot['benign'] else None
    R['flips_total'] = tot
    run.save('e7_assurance', R)
    L = run.ledger()
    if not L.has_epoch('e7-assurance'):                 # append-only: record the review cycles once
        for u in upd:
            L.append(dict(t='TRG', kind='schedule', day=int(u['day'])))
            L.append(dict(t='RVC', day=int(u['day']), scope=u['scope'], budget=u['budget'], changes=u['changes'], harmful=u['harmful']))
        L.anchor('e7-assurance')
    # label delay and coverage sensitivity
    if 'sensitivity' not in args.skip:
        for Lday in a['L']:
            for rho in a['rho']:
                if (Lday, rho) == (Lp, 1.0) or (rho < 1 and Lday != Lp):
                    continue
                key = f'L{Lday}_rho{rho:g}'
                ent = {}
                for pol in SENS:
                    res = S.simulate(seq(S.POLICIES[pol]['seq'], Lday, rho), F, pol, cfg, gamma=gamma, wcache=wcache)
                    ent[pol] = dict(E_ev=res['E_ev'], E=res['E'], issued_evaluative=res['issued_evaluative'],
                                    updates=res['updates'], U_ev=res['U_ev'].tolist())
                for pol in ('trace', 'vii_margin', 'abl_noregion'):
                    rr = S.relative_reduction_ci(np.array(ent['viii']['U_ev']), np.array(ent[pol]['U_ev']), int(a['block_days']), 1000, seed)
                    ent[pol]['rel_vs_viii'] = rr
                upd_s = ent['trace']['updates']
                ent['K1'] = dict(ok=sum(u['changes'] <= u['budget'] for u in upd_s), n=len(upd_s), changes=sum(u['changes'] for u in upd_s))
                ent['K2'] = dict(harmful=sum(u['harmful'] for u in upd_s), max_h_ub=max((u['h_ub'] for u in upd_s), default=None))
                ent['flips'] = S.flip_decomposition(seq('retrain', Lday, rho), F, int(a['budget_window_days']))
                for pol in ent:
                    if isinstance(ent[pol], dict):
                        ent[pol].pop('U_ev', None)
                R['scenarios'][key] = ent
                log(f'  scenario {key}: E_ev viii {ent["viii"]["E_ev"]:.0f}, TRACE {ent["trace"]["E_ev"]:.0f}, margin {ent["vii_margin"]["E_ev"]:.0f}')
                run.save('e7_assurance', R)
    # analyst noise (Algorithm 6 never lets the oracle override a reviewed finding unless override=True)
    if 'noise' not in args.skip:
        sq = seq('retrain', Lp, 1.0)
        for r in a['noise']:
            ent, yields = {}, {}
            for pol, ov in (('trace', False), ('vii_margin', False), ('vi_random', False), ('trace', True), ('vii_margin', True)):
                runs_ = [S.simulate(sq, F, pol, cfg, noise=r, noise_seed=s, override=ov, gamma=gamma, wcache=wcache)
                         for s in range(int(a['noise_seeds']))]
                ent[f'{pol}{"_override" if ov else ""}'] = float(np.mean([x['E_ev'] for x in runs_]))
                if not ov:
                    yv = [x['yield_'] for x in runs_ if x['yield_'] is not None]
                    yields[pol] = float(np.mean(yv)) if yv else None
            ent['viii'] = base['viii']['E_ev']
            ent['yield'] = yields
            R['noise'][str(r)] = ent
            log(f'  noise {r}: {ent}')
        # KB7: the yield advantage of TRACE-PE over lowest-margin review keeps its sign at the largest analyst error rate
        adv0 = (y_tr['yield_'] - y_m['yield_']) if (y_tr['yield_'] is not None and y_m['yield_'] is not None) else None
        yr = R['noise'][str(max(a['noise']))]['yield']
        advr = (yr['trace'] - yr['vii_margin']) if (yr.get('trace') is not None and yr.get('vii_margin') is not None) else None
        R['KB7'] = dict(advantage_r0=adv0, advantage_rmax=advr, r_max=max(a['noise']),
                        met=bool(adv0 is not None and advr is not None and adv0 > 0 and advr > 0))
        run.save('e7_assurance', R)
    # prevalence-resampled streams (D6: re-validators trained on the native matured stream)
    if 'streams' not in args.skip:
        sq = seq('retrain', Lp, 1.0)
        for pi in a['stream_pis']:
            vals = {p: [] for p in ('viii', 'trace', 'vii_margin', 'i_autoaccept')}
            sizes = []
            for sd in cfg['seeds']['streams']:
                rng = np.random.default_rng(int(sd))
                keep = np.zeros(len(F.pos), bool)
                for mo in sorted(set(F.month)):
                    mk = F.month == mo
                    b_ = np.flatnonzero(mk & (F.y == 0))
                    m_ = np.flatnonzero(mk & (F.y == 1))
                    k = int(round(pi * len(b_) / (1 - pi)))
                    keep[b_] = True
                    keep[rng.choice(m_, size=min(k, len(m_)), replace=False)] = True
                Fs = S.Findings(U, sel=np.flatnonzero(keep))
                sizes.append(len(Fs.pos))
                for p in vals:
                    vals[p].append(S.simulate(sq, Fs, p, cfg, gamma=gamma, wcache=None)['E_ev'])
            R['streams'][str(pi)] = {p: dict(mean=float(np.mean(v)), lo=float(np.percentile(v, 2.5)), hi=float(np.percentile(v, 97.5)))
                                     for p, v in vals.items()}
            R['streams'][str(pi)]['findings_per_stream'] = float(np.mean(sizes))
            log(f'  stream pi={pi}: ' + ', '.join(f'{p} {np.mean(v):.1f}' for p, v in vals.items()))
    run.save('e7_assurance', R)
    log('E7 done: decision', R['decision'], '| K1', R['K1']['met'], 'K2', R['K2']['met'], 'K3', R['K3']['met'])


if __name__ == '__main__':
    main()
