#!/usr/bin/env python3
"""Compact machine-readable summary of the S10 headline results for S11/S12 (all values measured-on-Claude unless a key says rfp).
Output: out/S10_results.json"""
import json, os
import numpy as np, pandas as pd
import s10_common as C

J = lambda n: json.load(open(f'{C.OUT}/{n}')) if os.path.exists(f'{C.OUT}/{n}') else None
df = pd.read_pickle(f'{C.OUT}/e1_metrics.pkl')


def v(model, set_, metric, pi, thr, seed=None):
    q = df[(df.model == model) & (df.set == set_) & (df.metric == metric) & (df.pi == str(pi)) & (df.thr == thr)]
    if seed is not None:
        q = q[q.seed == seed]
    return None if not len(q) else dict(value=float(q['value'].mean()), lo=float(q['lo'].iloc[0]) if len(q) == 1 else None,
                                        hi=float(q['hi'].iloc[0]) if len(q) == 1 else None, n_seeds=int(q.seed.nunique()))


f0 = {k: v('lgbm_trace', 'pool_MarSep', *a, seed=11) for k, a in {
    'tpr': ('rec', 'native', 'cert_0.1'), 'fpr': ('fpr', 'native', 'cert_0.1'), 'fnr': ('fnr', 'native', 'cert_0.1'), 'f1_pi10': ('f1', '0.1', 'cert_0.1'),
    'prec_pi1': ('prec', '0.01', 'cert_0.1'), 'mcc_native': ('mcc', 'native', 'cert_0.1'), 'auc': ('auc', 'native', '-'), 'ap_pi10': ('ap', '0.1', '-')}.items()}
f0['monthly_fnr'] = {mm: v('lgbm_trace', mm, 'fnr', 'native', 'cert_0.1', 11)['value'] for mm in C.TEST_MONTHS}
A = J('analysis_models.json'); aut = pd.DataFrame(A['aut'])
zoo = {m: dict(aut_f1_pi10_mean=float(g.aut_f1_pi10.mean()), aut_min=float(g.aut_f1_pi10.min()), aut_max=float(g.aut_f1_pi10.max()), n_seeds=int(len(g)),
               tpr_cert01_pool=v(m, 'pool_MarSep', 'rec', 'native', 'cert_0.1')['value'], auc_pool=v(m, 'pool_MarSep', 'auc', 'native', '-')['value'])
       for m, g in aut.groupby('model')}
R = J('reval_analysis.json'); t = R['L30_rho1.0']
out = dict(
    label='measured-on-Claude unless key contains rfp', data=J('e0_init.json')['strata'], f0=f0, zoo=zoo,
    friedman=A['friedman'], certificates={k: dict(SVR_months=v_['SVR_months'], fpr_only=v_['fpr_only_valid'], fnr_only=v_['fnr_only_valid'], thr=v_['thr'], kstar=v_['kstar'])
                                         for k, v_ in J('analysis_certificates.json').items() if k.startswith('thr')},
    KS1=J('analysis_certificates.json')['KS1_pass'], P1=J('analysis_bias.json')['P1'], KB4=J('analysis_bias.json')['KB4']['months_understated'],
    H9=J('analysis_bias.json')['H9'], monitor=dict(alarms=J('monitor.json')['alarms'], KT_pass=J('monitor.json')['KT_pass']),
    assurance={tag: dict(E_ev={p: r['E_ev'] for p, r in tt['policies'].items()}, K1=tt['K1']['met'], K2=tt['K2']['met'], K3=tt['K3'], KB1=tt['KB1'])
               for tag, tt in R.items()},
    flips=J('flips.json'), attribution=dict(KB10=J('attr.json')['KB10'], H7=J('attr.json')['H7'], P6=J('attr.json')['P6']),
    explain=dict(KB11=J('explain.json')['KB11'], faithfulness=J('explain.json')['faithfulness']['mean_spearman']),
    ledger=J('ledger_tests.json'), xenv=J('xenv.json')['match'], ember2018={k: v_ for k, v_ in J('ember.json').items() if k not in ('counts', 'backward_f0_to_EMBER2018')},
    timing=J('timing_clean.json'))
C.jdump(out, f'{C.OUT}/S10_results.json'); print('ok', os.path.getsize(f'{C.OUT}/S10_results.json'))
