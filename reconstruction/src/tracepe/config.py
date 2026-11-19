"""Configuration: configs/default.yaml plus overlays (--config), dotted overrides (--set) and TRACEPE_CONFIG."""
from __future__ import annotations

import argparse
import copy
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]          # repository root (src/tracepe/config.py -> repo)
DEFAULT = ROOT / 'configs' / 'default.yaml'


def deep_merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def set_dotted(cfg: dict, expr: str) -> None:
    """Apply one override 'a.b.c=value'; the value is parsed as YAML (numbers, lists, booleans)."""
    if '=' not in expr:
        raise ValueError(f'override must look like key.sub=value, got {expr!r}')
    key, raw = expr.split('=', 1)
    node = cfg
    parts = key.strip().split('.')
    for p in parts[:-1]:
        node = node.setdefault(p, {})
    node[parts[-1]] = yaml.safe_load(raw)


def load_config(paths=None, overrides=None) -> dict:
    with open(DEFAULT, encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    files = []
    env = os.environ.get('TRACEPE_CONFIG')
    if env:
        files += [p for p in env.split(os.pathsep) if p]
    files += list(paths or [])
    for p in files:
        p = resolve(p)
        if p == DEFAULT:
            continue
        with open(p, encoding='utf-8') as f:
            cfg = deep_merge(cfg, yaml.safe_load(f) or {})
    for o in overrides or []:
        set_dotted(cfg, o)
    cfg['_sources'] = [str(DEFAULT)] + [str(resolve(p)) for p in files]
    return cfg


def resolve(p) -> Path:
    """Relative paths are resolved against the repository root, so scripts can run from anywhere."""
    p = Path(p)
    return p if p.is_absolute() else (ROOT / p)


def get(cfg: dict, dotted: str, default=None):
    node = cfg
    for k in dotted.split('.'):
        if not isinstance(node, dict) or k not in node:
            return default
        node = node[k]
    return node


def cli(description: str, extra=None):
    """Standard command line: --config (repeatable overlay) and --set key=value (repeatable)."""
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument('--config', action='append', default=[], help='YAML overlay (repeatable)')
    ap.add_argument('--set', action='append', default=[], dest='overrides', help='override key.sub=value (repeatable)')
    if extra:
        extra(ap)
    args = ap.parse_args()
    cfg = load_config(args.config, args.overrides)
    return cfg, args
