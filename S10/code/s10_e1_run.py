#!/usr/bin/env python3
"""E1 driver: python3 s10_e1_run.py <model> <seed> -- trains on the S7 training window, scores evaluation rows,
saves scores + timings, and writes MAN/MOD records to the S10 ledger. One process per (model, seed) so that
peak RSS is per model."""
import sys, os, time, pickle, hashlib, json
import numpy as np, pandas as pd
import s10_common as C, s10_models as Mz

name = sys.argv[1]; seed = int(sys.argv[2])
os.makedirs(f'{C.CACHE}/scores', exist_ok=True)
outp = f'{C.CACHE}/scores/{name}_s{seed}.npz'
if os.path.exists(outp):
    print('exists', outp); sys.exit(0)
m = C.load_meta(); X = C.load_X()
tr = np.where(m['split'] == 'train')[0]
ev = np.where(m['split'].isin(['cal', 'test']) | m['stratum'].isin(['Placeholder', 'Bulk', 'SpikeMal']))[0]
y = m['y'].to_numpy().astype(int)
Xtr = np.asarray(X[tr]); ytr = y[tr]
store = C.Store()
man_root = C.merkle_root([bytes.fromhex(s) for s in sorted(m['sha'].iloc[tr])]).hex()

if name == 'ember2018_pub':
    import lightgbm as lgb
    mp = '/mnt/user-data/uploads/Datasets/ember2018/ember_model_2018.txt'
    t = time.perf_counter(); b = lgb.Booster(model_file=mp); load_s = time.perf_counter() - t
    t = time.perf_counter(); s = np.concatenate([b.predict(np.asarray(X[ev[i:i + 20000]]), raw_score=True)
                                                 for i in range(0, len(ev), 20000)]); pred_s = time.perf_counter() - t
    ident = C.tree_section_hash(b.model_to_string()); fit_s = 0.0
    extra = dict(model_file_sha256=C.sha256_file(mp), trees=b.num_trees(), load_s=load_s)
else:
    block = None
    if name == 'stack':
        ts = m['ts'].iloc[tr]
        block = np.where(ts < pd.Timestamp('2019-10-01', tz='UTC'), 1, np.where(ts < pd.Timestamp('2019-11-01', tz='UTC'), 2, 3))
    mdl = Mz.make(name, block)
    t = time.perf_counter(); mdl.fit(Xtr, ytr, seed); fit_s = time.perf_counter() - t
    t = time.perf_counter(); s = np.concatenate([mdl.score(np.asarray(X[ev[i:i + 20000]])) for i in range(0, len(ev), 20000)])
    pred_s = time.perf_counter() - t
    extra = {}
    if isinstance(mdl, Mz.LGBM):
        ms = mdl.b.model_to_string(); ident = C.tree_section_hash(ms); extra['model_obj'] = store.put(ms.encode())
        extra['trees'] = mdl.b.num_trees()
    else:
        blob = pickle.dumps(mdl, protocol=5); ident = hashlib.sha256(blob).hexdigest(); extra['model_obj'] = store.put(blob)
    if name == 'svm_rbf':
        extra['n_sv'] = mdl.n_sv
    if name == 'lr_pca':
        extra['pca_components'] = int(mdl.p.n_components_)
    if name in ('lr_ig', 'lr_mrmr', 'lr_chi2'):
        extra['selected'] = [int(v) for v in (mdl.s.sel if name != 'lr_chi2' else np.where(mdl.s.get_support())[0])]
s = np.asarray(s, dtype=np.float64)
rss = C.peak_rss_gb()
np.savez(outp, idx=ev, s=s, fit_s=fit_s, pred_s=pred_s, rss=rss)
meta_rec = dict(model=name, seed=seed, fit_s=round(fit_s, 3), pred_us=round(pred_s / len(ev) * 1e6, 3), rss_gb=rss,
                n_train=len(tr), n_scored=len(ev), ident=ident, **{k: v for k, v in extra.items() if k not in ('selected',)})
json.dump(dict(meta_rec, selected=extra.get('selected')), open(outp.replace('.npz', '.json'), 'w'))
C.ledger_append([dict(t='MAN', model=name, seed=seed, root=man_root, window=['2019-08-29', '2019-12-01'], cutoff='2019-12-01'),
                 dict(t='MOD', model=name, seed=seed, ident=ident, obj=extra.get('model_obj', ''),
                      fit_s=C.f32hex(fit_s), pred_us=C.f32hex(pred_s / len(ev) * 1e6), rss_gb=C.f32hex(rss),
                      libs=C.env_info())], epoch='models')
print(json.dumps(meta_rec))
