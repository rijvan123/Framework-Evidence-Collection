#!/usr/bin/env python3
"""Naive re-scoring flips (comparison with [30] Ghiani and [89] Kozak; explains K1): for every monthly update u, the findings issued in
the L days before u are re-scored by f_u at its own certified 0.5% threshold and compared with the verdict of their actual issuer
(the latest update at issue time; for L > 30 d a window spans several issuers). Flips are split by
whether the finding was abstained at issue (ICE credibility < kappa). Uses the cached models of `s10_reval.py models L rho`.
Output: out/flips.json"""
import sys, json, pickle, math
import numpy as np
import s10_common as C
import s10_reval as R

out = {}
UPD_DAYS = [R.dnum(x) for x in R.UPDATES]
for tag in sys.argv[1:] or ['L30_rho1.0']:
    L = int(tag.split('_')[0][1:]); p = f'{C.CACHE}/reval_{tag}/models.pkl'
    if not __import__('os').path.exists(p):
        print('skip', tag, 'no models'); continue
    M = pickle.load(open(p, 'rb')); stream = M['stream']; t_i = R.DAY[stream]; yy = R.y[stream]
    rows = []
    for i, u_s in enumerate(R.EVENTS):
        u = R.dnum(u_s); Mn = M['models'][u_s]
        sc = np.where((t_i >= R.START) & (t_i > u - L) & (t_i < u))[0]          # same window as K1: (u - L, u)
        iss = np.array([max(j for j, ud in enumerate(UPD_DAYS) if ud <= t) for t in t_i[sc]], int)   # actual issuer per finding
        vo = np.zeros(len(sc), int); ab = np.zeros(len(sc), bool)
        for j in np.unique(iss):
            m = iss == j; Mi = M['models'][R.UPDATES[j]]; s_ = Mi['s'][sc[m]]
            vo[m] = (s_ > Mi['cal']['thr_0.005']).astype(int); ab[m] = R.ice_cred(s_, vo[m], Mi['cal']['ice']) < Mi['cal']['kappa_0.005']
        sn = Mn['s'][sc]; vn = (sn > Mn['cal']['thr_0.005']).astype(int)
        y_ = yy[sc]; fl = vo != vn
        r = dict(event=u_s, issuers=int(len(np.unique(iss))), N=int(len(sc)), n_mal=int((y_ == 1).sum()), n_ben=int((y_ == 0).sum()), abstained=int(ab.sum()),
                 flips=int(fl.sum()), flips_abstained=int((fl & ab).sum()), flips_confident=int((fl & ~ab).sum()),
                 mal_regress=int(((y_ == 1) & (vo == 1) & (vn == 0)).sum()), mal_correct=int(((y_ == 1) & (vo == 0) & (vn == 1)).sum()),
                 ben_regress=int(((y_ == 0) & (vo == 0) & (vn == 1)).sum()), ben_correct=int(((y_ == 0) & (vo == 1) & (vn == 0)).sum()),
                 mal_regress_conf=int(((y_ == 1) & (vo == 1) & (vn == 0) & ~ab).sum()), ben_regress_conf=int(((y_ == 0) & (vo == 0) & (vn == 1) & ~ab).sum()))
        rows.append(r)
    T = {k: sum(r[k] for r in rows) for k in rows[0] if k not in ('event', 'issuers')}
    summ = dict(mal_regress_rate=T['mal_regress'] / T['n_mal'], ben_flip_rate=T['ben_regress'] / T['n_ben'],
                mal_regress_rate_ub=C.cp_upper(T['mal_regress'], T['n_mal']), ben_flip_rate_ub=C.cp_upper(T['ben_regress'], T['n_ben']),
                share_flips_abstained=T['flips_abstained'] / T['flips'] if T['flips'] else float('nan'),
                harmful=T['mal_regress'] + T['ben_regress'], corrective=T['mal_correct'] + T['ben_correct'],
                harmful_conf=T['mal_regress_conf'] + T['ben_regress_conf'])
    out[tag] = dict(updates=rows, totals=T, summary=summ)
    print(tag, json.dumps(T), json.dumps({k: round(v, 5) if isinstance(v, float) else v for k, v in summ.items()}), flush=True)
C.jdump(out, f'{C.OUT}/flips.json')
