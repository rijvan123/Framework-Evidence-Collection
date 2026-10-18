#!/usr/bin/env python3
"""Cross-environment re-execution (KB3). Run on two machines after E0:

    python scripts/xenv_fingerprint.py                       # writes xenv/<host>-py<ver>.json and scores
    python scripts/xenv_fingerprint.py --compare A.json B.json

The fingerprint retrains f0 from the cached release, records the tree-section hash, a digest of the margins
of every evaluation row and a digest of all canonical vector hashes."""
import hashlib
import json
import platform
import socket

import numpy as np

import _common  # noqa: F401
from tracepe.config import ROOT, cli
from tracepe.models import lgbm as LG
from tracepe.run import Run
from tracepe.utils import env_info, log


def main():
    def extra(ap):
        ap.add_argument('--compare', nargs=2, default=None)
        ap.add_argument('--out', default=str(ROOT / 'xenv'))
    cfg, args = cli(__doc__, extra)
    if args.compare:
        from pathlib import Path
        a, b = (json.load(open(p)) for p in args.compare)
        # the scores file travels next to its JSON (copy both from the other machine)
        sa = np.load(Path(args.compare[0]).with_name(Path(a['scores_file']).name))
        sb = np.load(Path(args.compare[1]).with_name(Path(b['scores_file']).name))
        same = float(np.mean(sa.view(np.uint64) == sb.view(np.uint64))) if sa.shape == sb.shape else 0.0
        res = dict(tree_hash_equal=a['tree_sha256'] == b['tree_sha256'], score_digest_equal=a['scores_sha256'] == b['scores_sha256'],
                   vector_digest_equal=a['vectors_sha256'] == b['vectors_sha256'], bit_identical_fraction=same,
                   KB3=dict(met=same >= 0.999), envs=[a['env'], b['env']])
        print(json.dumps(res, indent=1))
        (ROOT / 'xenv').mkdir(exist_ok=True)
        json.dump(res, open(ROOT / 'xenv' / 'xenv_compare.json', 'w'), indent=1)
        return
    run = Run(cfg)
    m = run.meta
    tr = run.rows(split='train')
    seed = int(cfg['seeds']['f0'])
    b = LG.train_lgbm(run.take(tr), m['y'].to_numpy()[tr], cfg['models']['lgbm_trace'], seed, run.threads)
    ident = LG.identity(b)
    z = LG.margin(b, run.X[run.eval_idx] if len(run.eval_idx) < 20000 else run.take(run.eval_idx))
    from pathlib import Path
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    name = f'{socket.gethostname()}-py{platform.python_version()}'
    np.save(out / f'{name}_scores.npy', z)
    rec = dict(env=env_info(), tree_sha256=ident['tree_sha256'], file_sha256=ident['file_sha256'],
               scores_sha256=hashlib.sha256(z.astype('>f8').tobytes()).hexdigest(), rows=int(len(z)),
               vectors_sha256=hashlib.sha256('\n'.join(m['vh']).encode()).hexdigest(), scores_file=f'{name}_scores.npy')
    json.dump(rec, open(out / f'{name}.json', 'w'), indent=1)
    log('fingerprint', out / f'{name}.json', rec['tree_sha256'])


if __name__ == '__main__':
    main()
