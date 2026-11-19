#!/usr/bin/env python3
"""Write a synthetic BODMAS-format release (and EMBER-raw JSON lines) for the smoke test.
Numbers computed on synthetic data are meaningless; the data only exercise the code paths."""
import argparse

import _common  # noqa: F401
from tracepe.config import resolve
from tracepe.data.synthetic import make_synthetic_bodmas, make_synthetic_ember

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--out', default='data/synthetic')
ap.add_argument('--scale', type=float, default=1.0)
ap.add_argument('--seed', type=int, default=7)
ap.add_argument('--no-ember', action='store_true')
a = ap.parse_args()
out = resolve(a.out)
print(make_synthetic_bodmas(out / 'bodmas', seed=a.seed, scale=a.scale))
if not a.no_ember:
    print(make_synthetic_ember(out / 'ember2018', seed=a.seed + 1))
