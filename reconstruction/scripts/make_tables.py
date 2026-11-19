#!/usr/bin/env python3
"""Render the result tables of the paper as Markdown (tables/) from the run outputs (out/)."""
import _common  # noqa: F401
from tracepe.config import cli
from tracepe.reporting.tables import build_all
from tracepe.run import Run
from tracepe.utils import log


def main():
    cfg, args = cli(__doc__)
    run = Run(cfg)
    written = build_all(run, cfg)
    log(f'{len(written)} tables written to {run.tables}')


if __name__ == '__main__':
    main()
