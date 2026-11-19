"""Run context: the directory layout of one run and cached access to the screened release."""
from __future__ import annotations

from functools import cached_property
from pathlib import Path

import numpy as np
import pandas as pd

from .config import resolve
from .utils import save_json, load_json


class Run:
    """runs/<name>/{cache,out,out/scores,tables,figures,ledger,store}."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.dir = resolve(cfg['run']['dir'])
        self.cache = self.dir / 'cache'
        self.out = self.dir / 'out'
        self.scores_dir = self.out / 'scores'
        self.tables = self.dir / 'tables'
        self.figs = self.dir / 'figures'
        self.ledger_dir = self.dir / 'ledger'
        self.store_dir = self.dir / 'store'
        for p in (self.cache, self.out, self.scores_dir, self.tables, self.figs, self.ledger_dir, self.store_dir):
            p.mkdir(parents=True, exist_ok=True)
        self.ledger_path = self.ledger_dir / 'trace_pe_ledger.jsonl'
        self.key_path = self.ledger_dir / 'anchor_key.pem'
        self.threads = int(cfg['run'].get('threads', 2))

    # ------------------------------------------------------------------ cached release
    @cached_property
    def meta(self) -> pd.DataFrame:
        p = self.cache / 'meta.pkl'
        if not p.exists():
            raise FileNotFoundError(f'{p} missing: run scripts/e00_intake.py first')
        return pd.read_pickle(p)

    @cached_property
    def X(self) -> np.ndarray:
        return np.load(self.cache / 'X.npy', mmap_mode='r')

    @cached_property
    def eval_idx(self) -> np.ndarray:
        return np.load(self.cache / 'eval_idx.npy')

    @cached_property
    def emeta(self) -> pd.DataFrame:
        return self.meta.iloc[self.eval_idx].reset_index(drop=True)

    def rows(self, split=None, stratum=None, months=None, y=None, by_order=False) -> np.ndarray:
        m = self.meta
        mask = np.ones(len(m), bool)
        if split is not None:
            mask &= m['split'].isin([split] if isinstance(split, str) else split).to_numpy()
        if stratum is not None:
            mask &= m['stratum'].isin([stratum] if isinstance(stratum, str) else stratum).to_numpy()
        if months is not None:
            mask &= m['month'].isin(list(months)).to_numpy()
        if y is not None:
            mask &= (m['y'].to_numpy() == y)
        idx = np.flatnonzero(mask)
        if by_order:
            idx = idx[np.argsort(m['order'].to_numpy()[idx], kind='stable')]
        return idx

    def emask(self, split=None, months=None, stratum=None, y=None) -> np.ndarray:
        e = self.emeta
        mask = np.ones(len(e), bool)
        if split is not None:
            mask &= e['split'].isin([split] if isinstance(split, str) else split).to_numpy()
        if months is not None:
            mask &= e['month'].isin(list(months)).to_numpy()
        if stratum is not None:
            mask &= e['stratum'].isin([stratum] if isinstance(stratum, str) else stratum).to_numpy()
        if y is not None:
            mask &= (e['y'].to_numpy() == y)
        return mask

    def take(self, idx: np.ndarray, chunk: int = 20000) -> np.ndarray:
        """Copy rows of the memory-mapped matrix (sorted access in chunks)."""
        idx = np.asarray(idx)
        out = np.empty((len(idx), self.X.shape[1]), np.float32)
        for s in range(0, len(idx), chunk):
            out[s:s + chunk] = self.X[idx[s:s + chunk]]
        return out

    # ------------------------------------------------------------------ outputs
    def save(self, name: str, obj) -> Path:
        return save_json(obj, self.out / (name if name.endswith('.json') else name + '.json'))

    def load(self, name: str):
        return load_json(self.out / (name if name.endswith('.json') else name + '.json'))

    def has(self, name: str) -> bool:
        return (self.out / (name if name.endswith('.json') else name + '.json')).exists()

    def save_scores(self, key: str, seed: int, arr: np.ndarray) -> Path:
        p = self.scores_dir / f'{key}__s{seed}.npy'
        np.save(p, np.asarray(arr, dtype=np.float64))
        return p

    def load_scores(self, key: str, seed: int) -> np.ndarray:
        return np.load(self.scores_dir / f'{key}__s{seed}.npy')

    def has_scores(self, key: str, seed: int) -> bool:
        return (self.scores_dir / f'{key}__s{seed}.npy').exists()

    def score_seeds(self, key: str) -> list[int]:
        return sorted(int(p.stem.split('__s')[1]) for p in self.scores_dir.glob(f'{key}__s*.npy'))

    # ------------------------------------------------------------------ evidence layer
    def ledger(self):
        from .evidence.ledger import Ledger
        return Ledger(self.ledger_path, key_path=self.key_path)

    def store(self):
        from .evidence.store import ObjectStore
        return ObjectStore(self.store_dir)
