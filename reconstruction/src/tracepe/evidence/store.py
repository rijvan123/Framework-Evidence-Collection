"""Content-addressed write-once object store (M4): objects/<h[:2]>/<h>, h = SHA-256 of the content.

Objects are created exclusively and set read-only; every read re-hashes the content. Write-once is
enforced by policy and made detectable through the ledger, not physically guaranteed (paper, N1-N5)."""
from __future__ import annotations

import io
import os
from pathlib import Path

import numpy as np

from .hashing import enc, sha256_hex


class IntegrityError(Exception):
    pass


class ObjectStore:
    def __init__(self, root):
        self.root = Path(root)
        (self.root / 'objects').mkdir(parents=True, exist_ok=True)

    def path(self, h: str) -> Path:
        return self.root / 'objects' / h[:2] / h

    def put(self, data: bytes) -> str:
        h = sha256_hex(data)
        p = self.path(h)
        if p.exists():
            if sha256_hex(p.read_bytes()) != h:
                raise IntegrityError(f'stored object {h} does not match its name')
            return h
        p.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(p, 0o444)
        return h

    def put_file(self, path) -> str:
        return self.put(Path(path).read_bytes())

    def put_json(self, obj) -> str:
        return self.put(enc(obj, check=False))

    def put_array(self, arr: np.ndarray) -> str:
        buf = io.BytesIO()
        np.save(buf, np.ascontiguousarray(arr), allow_pickle=False)
        return self.put(buf.getvalue())

    def get(self, h: str) -> bytes:
        p = self.path(h)
        data = p.read_bytes()
        if sha256_hex(data) != h:
            raise IntegrityError(f'object {h} failed read-verify')
        return data

    def get_array(self, h: str) -> np.ndarray:
        return np.load(io.BytesIO(self.get(h)), allow_pickle=False)

    def has(self, h: str) -> bool:
        return self.path(h).exists()

    def verify_all(self) -> dict:
        """Verifier level V2: every stored object re-hashes to its name."""
        n, bad = 0, []
        for p in sorted((self.root / 'objects').glob('*/*')):
            n += 1
            if sha256_hex(p.read_bytes()) != p.name:
                bad.append(p.name)
        return dict(objects=n, failures=len(bad), failed=bad[:20])
