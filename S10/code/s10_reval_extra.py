#!/usr/bin/env python3
"""Adds the A2-component ablations and the reviewed-finding reconciliation variant to an existing reval_<tag>.pkl
(used for L = 30, which ran before these policies were added). Same code path as s10_reval.simulate."""
import sys, pickle, json, numpy as np
import s10_common as C, s10_reval as RV
L = int(sys.argv[1]); rho = float(sys.argv[2]); tag = f'L{L}_rho{rho}'
R = pickle.load(open(f'{C.CACHE}/reval_{tag}/models.pkl', 'rb')); res = pickle.load(open(f'{C.OUT}/reval_{tag}.pkl', 'rb'))
ptr = json.load(open(f'{C.OUT}/reval_ptr.json')); gamma = ptr['0.005']['gamma']
e1 = np.load(f'{C.CACHE}/scores/lgbm_trace_s11.npz'); sall = np.full(len(RV.m), np.nan); sall[e1['idx']] = e1['s']
cal_idx = np.where(RV.m['split'] == 'cal')[0]
f0 = dict(s=sall[R['stream']], s_all=sall, cal=RV.calibrate(sall[cal_idx], RV.y[cal_idx]), cal_month='2019-12')
native = R['stream'][RV.DAY[R['stream']] >= RV.START]
for pol in ('a2_naive', 'a2_abst', 'a2_cert', 'a2_naive_frozen'):
    r = RV.simulate(pol, R, L, 'primary', gamma, native, f0, record=True)
    np.save(f'{C.CACHE}/reval_{tag}/Uev_{pol}.npy', np.array(r['Uev_series'])); np.save(f'{C.CACHE}/reval_{tag}/U_{pol}.npy', np.array(r['U_series']))
    for k_ in ('U_series', 'Uev_series', 'final_state', 'rows', 'cur', 'ver'):
        r.pop(k_, None)
    res['native'][f'primary|{pol}'] = r; print(pol, r['E_ev'], r['E'], flush=True)
for noise in (0.005, 0.01, 0.02):
    for pol in ('tracepe', 'vii_margin'):
        vr = [RV.simulate(pol, R, L, 'primary', gamma, native, f0, noise=noise, noise_seed=s_, recon_reviewed=True) for s_ in range(10)]
        res['noise'][f'{noise}|{pol}+rr'] = dict(E_ev=[v['E_ev'] for v in vr]); print(noise, pol, np.mean([v['E_ev'] for v in vr]), flush=True)
pickle.dump(res, open(f'{C.OUT}/reval_{tag}.pkl', 'wb')); print('updated', tag)
