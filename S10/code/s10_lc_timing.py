#!/usr/bin/env python3
"""Learning curves (R5) and an uncontended timing run.
  python3 s10_lc_timing.py lc       -> out/learning_curves.json
  python3 s10_lc_timing.py timing   -> out/timing_clean.json  (one seed per model, sequential, nothing else running)"""
import sys, time, json, resource, subprocess
import numpy as np
import s10_common as C, s10_models as Mz

mode = sys.argv[1]
if mode == 'lc':
    m = C.load_meta(); X = C.load_X(); y = m['y'].to_numpy().astype(int); sp = m['split'].to_numpy(); mo = m['month'].to_numpy()
    tr = np.where(sp == 'train')[0]; cal = np.where(sp == 'cal')[0]; te = np.where((sp == 'test') & np.isin(mo, C.CERT_MONTHS))[0]
    Xc = np.asarray(X[cal]); Xt = np.asarray(X[te]); rows = []
    for name in ['lgbm_trace', 'xgb', 'rf100', 'lr', 'nb']:
        for frac in [0.05, 0.10, 0.25, 0.50, 1.00]:
            rng = np.random.default_rng(11); sub = []
            for c in (0, 1):
                ic = tr[y[tr] == c]; sub.append(rng.choice(ic, max(10, int(round(frac * len(ic)))), replace=False))
            sub = np.sort(np.concatenate(sub)); Xs = np.asarray(X[sub])
            mdl = Mz.Forest('rf', 100) if name == 'rf100' else Mz.make(name)
            t = time.perf_counter(); mdl.fit(Xs, y[sub], 11); fs = time.perf_counter() - t
            sc = mdl.score(Xc); stt = mdl.score(Xt); s_in = mdl.score(Xs)
            thr, _ = C.certified_threshold(sc[y[cal] == 0], 0.001)
            tp, fn, fp, tn = C.counts(y[te], stt, thr)
            r10 = C.rates_from_counts(tp, fn, fp, tn, C.kappa_for(0.10, tp + fn, fp + tn))
            rows.append(dict(model=name, frac=frac, n=len(sub), fit_s=fs, auc_train=C.auc_fast(y[sub], s_in), auc_cal=C.auc_fast(y[cal], sc),
                             auc_test=C.auc_fast(y[te], stt), ap_test_pi10=C.ap_score(y[te], stt, 0.10), f1_test_pi10=r10['f1'],
                             fnr_test=fn / (tp + fn), fpr_test=fp / (fp + tn)))
            print(rows[-1], flush=True)
    C.jdump(rows, f'{C.OUT}/learning_curves.json')
elif mode in ('timing', 'retime'):
    def time_job(name, seed):
        code = f"""
import time, resource, numpy as np, json, s10_common as C, s10_models as Mz, pandas as pd
m = C.load_meta(); X = C.load_X(); y = m['y'].to_numpy().astype(int)
tr = np.where(m['split'] == 'train')[0]; ev = np.where(m['split'].isin(['cal','test']))[0]
Xtr = np.asarray(X[tr]); Xev = np.asarray(X[ev[:20000]])
if '{name}' == 'ember2018_pub':
    import lightgbm as lgb
    b = lgb.Booster(model_file='/mnt/user-data/uploads/Datasets/ember2018/ember_model_2018.txt'); fs = 0.0
    t = time.perf_counter(); b.predict(Xev, raw_score=True); ps = time.perf_counter() - t
else:
    block = None
    if '{name}' == 'stack':
        ts = m['ts'].iloc[tr]; block = np.where(ts < pd.Timestamp('2019-10-01', tz='UTC'), 1, np.where(ts < pd.Timestamp('2019-11-01', tz='UTC'), 2, 3))
    mdl = Mz.make('{name}', block)
    t = time.perf_counter(); mdl.fit(Xtr, y[tr], {seed}); fs = time.perf_counter() - t
    t = time.perf_counter(); mdl.score(Xev); ps = time.perf_counter() - t
print(json.dumps(dict(model='{name}', fit_s=fs, pred_us=ps / len(Xev) * 1e6, rss_gb=C.peak_rss_gb())))
"""
        r = subprocess.run(['python3', '-c', code], capture_output=True, text=True, cwd='/home/claude/s10/code')
        try:
            return json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            return dict(model=name, error=r.stderr[-500:])
    if mode == 'timing':
        jobs = [('lgbm_trace', 11), ('lgbm_ember', 11), ('xgb', 11), ('rf', 11), ('et', 11), ('lr', 0), ('lr_chi2', 0), ('lr_ig', 0),
                ('lr_mrmr', 0), ('lr_pca', 0), ('svm_lin', 0), ('knn', 0), ('nb', 0), ('mlp', 11), ('stack', 11), ('ember2018_pub', 0)]
        out = []
        for name, seed in jobs:
            out.append(time_job(name, seed)); print(out[-1], flush=True)
            C.jdump(dict(env=C.env_info(), jobs=out), f'{C.OUT}/timing_clean.json')
    else:  # retime one job after a code change; replaces its entry and records why
        name, seed, why = sys.argv[2], int(sys.argv[3]), sys.argv[4]
        T = json.load(open(f'{C.OUT}/timing_clean.json'))
        new = time_job(name, seed); new['note'] = why; print(new, flush=True)
        T['jobs'] = [new if j.get('model') == name else j for j in T['jobs']]
        C.jdump(T, f'{C.OUT}/timing_clean.json')
