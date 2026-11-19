#!/usr/bin/env python3
"""E12 - CPU cost per detector (uncontended, one process per model: training time, inference time per file,
peak resident memory) and learning curves on stratified sub-samples of the training window (paper Section 8.11)."""
import multiprocessing as mp
import resource
import time

import numpy as np

import _common  # noqa: F401
from _common import certify_months, primary_tau
from tracepe.config import cli
from tracepe.decision.thresholds import certified_threshold
from tracepe.evaluation import metrics as M
from tracepe.models.zoo import DISPLAY, fit_model, load_published
from tracepe.run import Run
from tracepe.utils import log


def _time_one(key, cfg, q):
    run = Run(cfg)
    m = run.meta
    tr = run.rows(split='train')
    Xtr = run.take(tr)
    ytr = m['y'].to_numpy()[tr]
    seed = int(cfg['seeds']['f0'])
    if key == 'ember2018_pub':
        from tracepe.config import resolve
        mdl = load_published(resolve(cfg['data']['ember2018_model']))
        fit_s = 0.0
    else:
        t0 = time.perf_counter()
        mdl = fit_model(key, seed, Xtr, ytr, cfg, t_train=m['day'].to_numpy()[tr], threads=run.threads)
        fit_s = time.perf_counter() - t0
    ev = run.eval_idx[:int(cfg['cost']['inference_rows'])]
    Xe = run.take(ev)
    t0 = time.perf_counter()
    mdl.score(Xe)
    inf_s = time.perf_counter() - t0
    q.put(dict(model=key, train_seconds=round(fit_s, 2), inference_us_per_file=round(inf_s / len(ev) * 1e6, 2),
               peak_rss_gb=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1048576, 3), rows=int(len(tr))))


def main():
    def extra(ap):
        ap.add_argument('--skip-timing', action='store_true')
    cfg, args = cli(__doc__, extra)
    run = Run(cfg)
    R = dict(timing=[], learning={})
    if not args.skip_timing:
        ctx = mp.get_context('spawn')
        keys = list(cfg['models']['zoo']) + (['ember2018_pub'] if run.has_scores('ember2018_pub', 0) else [])
        for key in keys:
            q = ctx.Queue()
            p = ctx.Process(target=_time_one, args=(key, cfg, q))
            p.start()
            res = q.get()
            p.join()
            R['timing'].append(res)
            log(f'  {DISPLAY[key]:34s} train {res["train_seconds"]:8.2f} s  inference {res["inference_us_per_file"]:9.2f} us  RSS {res["peak_rss_gb"]} GB')
            run.save('e12_cost_learning', R)
    # learning curves
    m = run.meta
    tr = run.rows(split='train')
    y = m['y'].to_numpy()
    e = run.emeta
    ye = e['y'].to_numpy()
    calm = e['split'].to_numpy() == 'calibration'
    pool = (e['split'].to_numpy() == 'test') & np.isin(e['month'].to_numpy(), certify_months(cfg))
    ev = run.eval_idx
    Xev = None
    seed = int(cfg['seeds']['f0'])
    cfg2 = dict(cfg)
    cfg2['models'] = dict(cfg['models'])
    cfg2['models']['rf'] = dict(cfg['models']['rf'], n_estimators=int(cfg['cost']['learning_rf_trees']))
    rng = np.random.default_rng(seed)
    for key in cfg['cost']['learning_models']:
        pts = []
        for frac in cfg['cost']['learning_fracs']:
            sub = []
            for c in (0, 1):
                ci = tr[y[tr] == c]
                sub.append(rng.choice(ci, size=max(2, int(round(frac * len(ci)))), replace=False))
            sub = np.sort(np.concatenate(sub))
            Xs = run.take(sub)
            t0 = time.perf_counter()
            mdl = fit_model(key, seed, Xs, y[sub], cfg2, t_train=m['day'].to_numpy()[sub], threads=run.threads)
            fit_s = time.perf_counter() - t0
            if Xev is None:
                Xev = run.take(ev)
            s = mdl.score(Xev)
            th = certified_threshold(s[calm & (ye == 0)], primary_tau(cfg))['theta']
            mt = M.point_metrics(s[pool], ye[pool], th, cfg['prevalence']['report'])
            pts.append(dict(fraction=frac, rows=int(len(sub)), aucpr_pi=M.auc_pr_at_pi(s[pool], ye[pool], cfg['prevalence']['report']),
                            train_auc=M.auc(mdl.score(Xs), y[sub]), fnr=mt['fnr'], fit_seconds=round(fit_s, 2)))
            log(f'  learning {key} {frac:.2f}: FNR {mt["fnr"]:.4f}')
        R['learning'][key] = pts
    run.save('e12_cost_learning', R)
    log('E12 done')


if __name__ == '__main__':
    main()
