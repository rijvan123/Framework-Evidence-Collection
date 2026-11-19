#!/usr/bin/env python3
"""Compare a run with the values reported in the paper (results/paper_reference.json).

'exact' checkpoints are deterministic functions of the released files (digests, counts, strata, split,
spike rule, oracle root, acquisition-chain head, k*, Clopper-Pearson bounds) and must match. 'model' values
depend on library versions and implementation details; their differences are reported, not judged."""
import json

import _common  # noqa: F401
from tracepe.config import ROOT, cli
from tracepe.run import Run
from tracepe.utils import load_json, log


def lookup(run, path):
    """'<output>:<key>/<key>/...' -> (value, found)."""
    name, dotted = path.split(':', 1)
    if not run.has(name):
        return None, False
    node = run.load(name)
    for p in dotted.split('/'):
        if isinstance(node, list):
            try:
                node = node[int(p)]
            except (ValueError, IndexError):
                return None, False
        elif isinstance(node, dict) and p in node:
            node = node[p]
        else:
            return None, False
    return node, True


def close(a, b, tol):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= tol
    return a == b


def main():
    cfg, args = cli(__doc__)
    run = Run(cfg)
    ref = load_json(ROOT / 'results' / 'paper_reference.json')
    rows, n_ok, n_bad, n_missing = [], 0, 0, 0
    for item in ref['exact']:
        v, found = lookup(run, item['path'])
        ok = found and close(v, item['value'], item.get('tol', 0))
        n_ok += ok
        n_bad += found and not ok
        n_missing += not found
        rows.append(dict(kind='exact', what=item['what'], path=item['path'], paper=item['value'], run=v,
                         status='match' if ok else ('MISMATCH' if found else 'missing')))
    for item in ref['model']:
        v, found = lookup(run, item['path'])
        diff = (v - item['value']) if (found and isinstance(v, (int, float)) and isinstance(item['value'], (int, float))) else None
        rows.append(dict(kind='model', what=item['what'], path=item['path'], paper=item['value'], run=v, difference=diff,
                         status='reported' if found else 'missing'))
    summary = dict(exact_match=n_ok, exact_mismatch=n_bad, exact_missing=n_missing, model_values=len(ref['model']))
    run.save('compare_to_paper', dict(summary=summary, rows=rows))
    md = ['# Run vs paper', '', f'Exact checkpoints: {n_ok} match, {n_bad} mismatch, {n_missing} missing.', '',
          '| Kind | Item | Paper | This run | Status |', '|---|---|---|---|---|']
    for r in rows:
        fmt = lambda x: json.dumps(x) if not isinstance(x, float) else f'{x:.6g}'
        md.append(f'| {r["kind"]} | {r["what"]} | {fmt(r["paper"])} | {fmt(r["run"])} | {r["status"]} |')
    (run.out / 'compare_to_paper.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    log(f'exact checkpoints: {n_ok} match, {n_bad} mismatch, {n_missing} missing -> {run.out / "compare_to_paper.md"}')


if __name__ == '__main__':
    main()
