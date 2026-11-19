#!/usr/bin/env python3
"""Render the result figures of the paper (PNG and PDF, figures/) from the run outputs (out/), plus the
literature-coverage figure from figures/literature/s11_rows.json."""
import _common  # noqa: F401
from tracepe.config import cli
from tracepe.plotting.figures import build_all
from tracepe.run import Run
from tracepe.utils import log


def main():
    cfg, args = cli(__doc__)
    run = Run(cfg)
    written = build_all(run, cfg)
    log(f'{len(written)} figures written to {run.figs}')


if __name__ == '__main__':
    main()
