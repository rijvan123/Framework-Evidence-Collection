"""BODMAS release loader (Yang et al., IEEE SPW 2021): bodmas.npz, bodmas_metadata.csv, bodmas_malware_category.csv."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ..evidence.hashing import sha256_file

FILES = ('bodmas.npz', 'bodmas_metadata.csv', 'bodmas_malware_category.csv')


def file_digests(data_dir) -> dict:
    data_dir = Path(data_dir)
    return {f: sha256_file(data_dir / f) for f in FILES}


def load_release(data_dir):
    """Returns X (float32, n x 2381), y (int64), metadata (str columns sha,timestamp,family),
    categories (sha256,category) and the npz member names."""
    data_dir = Path(data_dir)
    npz = np.load(data_dir / 'bodmas.npz')
    members = list(npz.files)
    X = npz['X']
    y = npz['y'].astype(np.int64)
    meta = pd.read_csv(data_dir / 'bodmas_metadata.csv', dtype=str, keep_default_na=False)
    cat = pd.read_csv(data_dir / 'bodmas_malware_category.csv', dtype=str, keep_default_na=False)
    return X, y, meta, cat, members
