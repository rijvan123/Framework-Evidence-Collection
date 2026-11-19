"""Small shared helpers: logging, timing, JSON with NumPy types, environment description."""
from __future__ import annotations

import json
import math
import os
import platform
import resource
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np

_T0 = time.perf_counter()


def log(*msg):
    print(f'[{time.perf_counter() - _T0:8.1f}s]', *msg, flush=True)


@contextmanager
def timer(label: str = '', sink: dict | None = None, key: str | None = None):
    t = time.perf_counter()
    yield
    dt = time.perf_counter() - t
    if sink is not None:
        sink[key or label] = round(dt, 4)
    if label:
        log(f'{label}: {dt:.2f} s')


def peak_rss_gb() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round((r / 1024 / 1024) if sys.platform != 'darwin' else r / 1e9, 3)


def to_jsonable(o):
    if isinstance(o, dict):
        return {str(k): to_jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        return to_jsonable(o.tolist())
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        v = float(o)
        return None if (math.isnan(v) or math.isinf(v)) else v
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, Path):
        return str(o)
    return o


def save_json(obj, path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(to_jsonable(obj), f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)
    return path


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def env_info() -> dict:
    import pandas, scipy, sklearn
    info = dict(python=sys.version.split()[0], numpy=np.__version__, pandas=pandas.__version__,
                scipy=scipy.__version__, sklearn=sklearn.__version__, platform=platform.platform(),
                nproc=os.cpu_count())
    for mod in ('lightgbm', 'xgboost', 'matplotlib', 'cryptography'):
        try:
            info[mod] = __import__(mod).__version__
        except Exception:  # pragma: no cover
            info[mod] = None
    try:
        info['cpu_model'] = [l.split(':', 1)[1].strip() for l in open('/proc/cpuinfo') if l.startswith('model name')][0]
    except Exception:
        info['cpu_model'] = platform.processor() or 'unavailable'
    try:
        info['mem_total_gb'] = round(os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') / 1e9, 2)
    except Exception:
        info['mem_total_gb'] = None
    return info


def month_list(start: str, end: str) -> list[str]:
    """Inclusive list of 'YYYY-MM' months."""
    y, m = map(int, start.split('-'))
    ye, me = map(int, end.split('-'))
    out = []
    while (y, m) <= (ye, me):
        out.append(f'{y:04d}-{m:02d}')
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def day_number(date_str: str) -> int:
    """Days since 1970-01-01 for 'YYYY-MM-DD'."""
    return int(np.datetime64(date_str, 'D').astype(np.int64))


def day_string(day: int) -> str:
    return str(np.datetime64(int(day), 'D'))


def month_end_day(month: str) -> int:
    """Day number of the last day of month 'YYYY-MM'."""
    y, m = map(int, month.split('-'))
    nxt = f'{y + (m == 12):04d}-{(m % 12) + 1:02d}-01'
    return day_number(nxt) - 1


def month_start_day(month: str) -> int:
    return day_number(month + '-01')


def rng_for(*keys) -> np.random.Generator:
    """Deterministic generator derived from integer/string keys."""
    import hashlib
    h = hashlib.sha256('|'.join(map(str, keys)).encode()).digest()
    return np.random.default_rng(int.from_bytes(h[:8], 'little'))
