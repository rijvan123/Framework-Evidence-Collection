#!/usr/bin/env python3
"""E1a - train the 17-detector zoo on the training window (Aug-Nov 2019, Dated stratum) and score every
evaluation row (December calibration month, January-September 2020, censored strata). Models are stored
in the content-addressed store and bound to the ledger by MAN and MOD records (paper Section 7.4)."""
import resource
import time


import _common  # noqa: F401
from _common import score_rows
from tracepe.config import cli, resolve
from tracepe.evidence.merkle import merkle_root
from tracepe.models.zoo import DISPLAY, fit_model, load_published, seeds_for
from tracepe.run import Run
from tracepe.utils import env_info, log


def main():
    def extra(ap):
        ap.add_argument('--models', nargs='*', default=None, help='subset of model keys')
        ap.add_argument('--force', action='store_true', help='refit models whose scores already exist')
    cfg, args = cli(__doc__, extra)
    run = Run(cfg)
    m = run.meta
    tr = run.rows(split='train')                       # file order (as in the paper's f0 fit)
    Xtr = run.take(tr)
    ytr = m['y'].to_numpy()[tr].astype(int)
    ttr = m['day'].to_numpy()[tr]
    ev = run.eval_idx
    info = run.load('e1_models') if run.has('e1_models') else {}
    L = run.ledger()
    store = run.store()
    man = dict(t='MAN', name='train', window=[cfg['screen']['window_start'], cfg['screen']['train_end']],
               label_cutoff=cfg['screen']['train_end'], n=int(len(tr)),
               root=merkle_root([s.encode() for s in sorted(m['sid'].to_numpy()[tr])]).hex())
    man_hash = None
    keys = args.models or cfg['models']['zoo']
    for key in keys:
        for seed in seeds_for(key, cfg):
            if run.has_scores(key, seed) and not args.force:
                log(f'skip {key} seed {seed} (scores exist)')
                continue
            log(f'fit {DISPLAY[key]} seed {seed}')
            mdl = fit_model(key, seed, Xtr, ytr, cfg, t_train=ttr, threads=run.threads)
            t0 = time.perf_counter()
            sc = score_rows(mdl, run, ev)
            score_s = time.perf_counter() - t0
            run.save_scores(key, seed, sc)
            h = store.put(mdl.to_bytes())
            ident = mdl.identity()
            if man_hash is None:                       # one training manifest per fitting session
                man_hash = L.append(man)
            L.append(dict(t='MOD', model=key, seed=int(seed), store=h, man=man_hash,
                          tree_sha256=ident.get('tree_sha256'), param_sha256=ident.get('param_sha256'),
                          file_sha256=ident.get('file_sha256'), threads=run.threads,
                          versions={k: str(v) for k, v in env_info().items() if k in ('lightgbm', 'xgboost', 'sklearn', 'numpy', 'python')}))
            info.setdefault(key, {})[str(seed)] = dict(store=h, identity=ident, fit_seconds=mdl.fit_seconds,
                                                       score_seconds=round(score_s, 3), n_train=int(len(tr)),
                                                       default_threshold=mdl.default_threshold, extra=mdl.extra,
                                                       peak_rss_gb=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1048576, 3))
            run.save('e1_models', info)
            L.flush()
    pub = load_published(resolve(cfg['data']['ember2018_model']))
    if pub is not None and (args.force or not run.has_scores('ember2018_pub', 0)):
        log('score published EMBER-2018 model')
        t0 = time.perf_counter()
        run.save_scores('ember2018_pub', 0, score_rows(pub, run, ev))
        h = store.put(pub.to_bytes())
        ident = pub.identity()
        L.append(dict(t='MOD', model='ember2018_pub', seed=0, store=h, tree_sha256=ident['tree_sha256'],
                      file_sha256=ident['file_sha256'], note='published model, scored only'))
        info['ember2018_pub'] = {'0': dict(store=h, identity=ident, fit_seconds=0.0,
                                            score_seconds=round(time.perf_counter() - t0, 3), default_threshold=0.0)}
        run.save('e1_models', info)
    if L.leaves:                                       # nothing new on a re-run: no empty epoch
        L.anchor('e1-zoo')
    log('E1 zoo done')


if __name__ == '__main__':
    main()
