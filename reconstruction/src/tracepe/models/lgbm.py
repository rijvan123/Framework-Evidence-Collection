"""LightGBM training, scoring and model identity (paper Section 4.5).

Model identity is the SHA-256 of the *tree section* of the model file: files trained with 1 and 2
threads differ only in the line ``[num_threads: N]`` while their trees and predictions are identical
(S7 probe F1), so a whole-file hash would change without any change to the model."""
from __future__ import annotations

import hashlib

import lightgbm as lgb
import numpy as np


def lgbm_params(block: dict, seed: int, threads: int, objective: str = 'binary', **extra) -> dict:
    p = dict(objective=objective, num_leaves=block.get('num_leaves', 63), learning_rate=block.get('learning_rate', 0.05),
             feature_fraction=block.get('feature_fraction', 1.0), min_data_in_leaf=block.get('min_data_in_leaf', 20),
             seed=int(seed), deterministic=True, force_row_wise=True, num_threads=int(threads), verbose=-1)
    for k in ('bagging_fraction', 'bagging_freq', 'max_depth', 'lambda_l2'):
        if k in block:
            p[k] = block[k]
    p.update(extra)
    return p


def train_lgbm(X, y, block: dict, seed: int, threads: int, weight=None, init_model=None, **extra) -> lgb.Booster:
    ds = lgb.Dataset(np.asarray(X, dtype=np.float32), label=np.asarray(y), weight=weight,
                     params={'verbose': -1, 'max_bin': 255}, free_raw_data=True)
    return lgb.train(lgbm_params(block, seed, threads, **extra), ds, num_boost_round=int(block.get('rounds', 200)),
                     init_model=init_model)


def margin(booster: lgb.Booster, X, chunk: int = 20000) -> np.ndarray:
    """Raw scores (margins) as float64; memory-mapped inputs are read in chunks."""
    n = X.shape[0]
    out = np.empty(n, np.float64)
    for s in range(0, n, chunk):
        out[s:s + chunk] = booster.predict(np.asarray(X[s:s + chunk], dtype=np.float32), raw_score=True)
    return out


def tree_section(model_str: str) -> str:
    return model_str[model_str.find('Tree=0'):model_str.find('end of trees')]


def parameter_block(model_str: str) -> str:
    return model_str[model_str.find('parameters:'):model_str.find('end of parameters')]


def identity(booster: lgb.Booster) -> dict:
    s = booster.model_to_string(num_iteration=-1)
    return dict(tree_sha256=hashlib.sha256(tree_section(s).encode()).hexdigest(),
                param_sha256=hashlib.sha256(parameter_block(s).encode()).hexdigest(),
                file_sha256=hashlib.sha256(s.encode()).hexdigest(), n_trees=booster.num_trees(),
                model_bytes=len(s), lightgbm=lgb.__version__)


def contributions(booster: lgb.Booster, X) -> np.ndarray:
    """Exact TreeSHAP (pred_contrib): n x (d + 1), last column = expected value phi_0."""
    return booster.predict(np.asarray(X, dtype=np.float32), pred_contrib=True)
