#!/usr/bin/env python3
"""Seal a run: bind every output file (out/, tables/, figures/) to the ledger with a REPORT record, anchor the
final epoch and write out/ledger_final.json (head, record counts, anchor public key, V1 result)."""
import time

import _common  # noqa: F401
from tracepe.config import cli
from tracepe.evidence.hashing import sha256_file
from tracepe.evidence.ledger import verify_ledger
from tracepe.run import Run
from tracepe.utils import log


def main():
    cfg, args = cli(__doc__)
    run = Run(cfg)
    L = run.ledger()
    if L.leaves:
        L.anchor('open-epoch')
    n = 0
    for sub in (run.out, run.tables, run.figs):
        for p in sorted(sub.rglob('*')):
            if p.is_file() and p.name != 'ledger_final.json' and not p.name.endswith('.npy'):
                L.append(dict(t='REPORT', path=str(p.relative_to(run.dir)), sha256=sha256_file(p), bytes=p.stat().st_size))
                n += 1
    for p in sorted(run.scores_dir.glob('*.npy')):
        L.append(dict(t='REPORT', path=str(p.relative_to(run.dir)), sha256=sha256_file(p), bytes=p.stat().st_size))
        n += 1
    L.anchor('report')
    t0 = time.perf_counter()
    v = verify_ledger(run.ledger_path)
    run.save('ledger_final', dict(head=L.head.hex(), records=L.n, counts=L.counts, report_records=n, anchor_public_key=L.pub,
                                  V1=dict(ok=v['ok'], records=v['records'], anchors=v['anchors'], seconds=round(time.perf_counter() - t0, 3))))
    log(f'sealed: {n} REPORT records; head {L.head.hex()}; V1 ok {v["ok"]}')


if __name__ == '__main__':
    main()
