#!/usr/bin/env python3
"""Independent verifier M13: V1 (chain, epoch Merkle roots, anchor signatures), V2 (stored objects) and an
optional inclusion receipt for one record. Exit status 1 on any failure."""
import json
import sys

import _common  # noqa: F401
from tracepe.config import cli
from tracepe.evidence.ledger import receipt, verify_ledger, verify_receipt
from tracepe.evidence.store import ObjectStore
from tracepe.run import Run


def main():
    def extra(ap):
        ap.add_argument('ledger', nargs='?', default=None, help='ledger file (default: the run ledger of the config)')
        ap.add_argument('--pub', default=None, help='expected anchor public key (hex); default: trust the key of the first anchor')
        ap.add_argument('--store', default=None, help='object store directory for V2')
        ap.add_argument('--receipt', type=int, default=None, help='record index for an inclusion receipt')
    cfg, args = cli(__doc__, extra)
    run = Run(cfg)
    path = args.ledger or run.ledger_path
    out = dict(V1=verify_ledger(path, args.pub))
    store = args.store or (run.store_dir if args.ledger is None else None)
    if store:
        out['V2'] = ObjectStore(store).verify_all()
    if args.receipt is not None:
        rc = receipt(path, args.receipt)
        out['receipt'] = dict(index=rc['index'], epoch=rc.get('epoch'), proof_hashes=len(rc.get('proof') or []),
                              verified=verify_receipt(rc, args.pub), record=rc['record'])
    print(json.dumps(out, indent=1, default=str))
    ok = out['V1']['ok'] and (out.get('V2', {}).get('failures', 0) == 0) and out.get('receipt', {}).get('verified', True)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
