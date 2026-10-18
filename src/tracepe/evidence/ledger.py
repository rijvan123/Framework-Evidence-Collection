"""Append-only, hash-chained evidence ledger with Merkle epochs and Ed25519-signed anchors (paper Section 4.3).

File format: one record per line, ``<chain head hex> <canonical JSON record>``. The chain starts from
h_0 = H(DOM||"genesis"||0x00); the first record is the dataset manifest MAN0. An ANC record closes an
epoch: it carries the Merkle root over the record hashes of the epoch, the chain head before the
anchor and an Ed25519 signature over (epoch, root, head). The RFC 3161 time-stamping authority is
*simulated* (local key, wall-clock time) and labelled as such in every ANC record.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

from .hashing import DOM, GENESIS_SEED, enc, link, rec_hash
from .merkle import inclusion_proof, merkle_levels, merkle_root, verify_inclusion


class LedgerError(Exception):
    pass


def anchor_message(epoch: str, root: bytes, head: bytes) -> bytes:
    return DOM + b'anchor\x00' + epoch.encode('utf-8') + b'\x00' + root + head


def load_or_create_key(path) -> Ed25519PrivateKey:
    path = Path(path)
    if path.exists():
        return serialization.load_pem_private_key(path.read_bytes(), password=None)
    sk = Ed25519PrivateKey.generate()
    path.parent.mkdir(parents=True, exist_ok=True)
    pem = sk.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(pem)
    return sk


def public_hex(sk: Ed25519PrivateKey) -> str:
    return sk.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()


def verify_signature(pub_hex: str, sig_hex: str, msg: bytes) -> bool:
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex)).verify(bytes.fromhex(sig_hex), msg)
        return True
    except (InvalidSignature, ValueError):
        return False


class Ledger:
    """Append records with :meth:`append`; close an epoch with :meth:`anchor`."""

    def __init__(self, path, key_path=None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.head = GENESIS_SEED
        self.n = 0
        self.leaves: list[bytes] = []          # record hashes of the open epoch
        self.counts: dict[str, int] = {}
        self.epochs: list[str] = []            # names of the anchored epochs, in order
        self._buf: list[str] = []
        if self.path.exists() and self.path.stat().st_size > 0:
            self._replay()
        self._sk = load_or_create_key(key_path) if key_path else None
        self.pub = public_hex(self._sk) if self._sk else None

    def _replay(self):
        with open(self.path, encoding='ascii') as f:
            for i, line in enumerate(f):
                head_hex, js = line.rstrip('\n').split(' ', 1)
                rh = rec_hash(js.encode('ascii'))
                self.head = link(self.head, rh)
                if self.head.hex() != head_hex:
                    raise LedgerError(f'chain break at record {i} while opening {self.path}')
                r = json.loads(js)
                t = r.get('t', '?')
                self.counts[t] = self.counts.get(t, 0) + 1
                if t == 'ANC':
                    self.leaves = []
                    self.epochs.append(r.get('epoch', ''))
                else:
                    self.leaves.append(rh)
                self.n += 1

    # -------------------------------------------------------------- writing
    def append(self, rec: dict) -> str:
        e = enc(rec)
        rh = rec_hash(e)
        self.head = link(self.head, rh)
        self._buf.append(f'{self.head.hex()} {e.decode("ascii")}\n')
        self.leaves.append(rh)
        t = rec.get('t', '?')
        self.counts[t] = self.counts.get(t, 0) + 1
        self.n += 1
        if len(self._buf) >= 20000:
            self.flush()
        return rh.hex()

    def flush(self):
        if self._buf:
            with open(self.path, 'a', encoding='ascii') as f:
                f.writelines(self._buf)
                f.flush()
                os.fsync(f.fileno())
            self._buf.clear()

    def anchor(self, epoch: str) -> dict:
        if self._sk is None:
            raise LedgerError('no signing key configured')
        root = merkle_root(self.leaves)
        head_before = self.head
        sig = self._sk.sign(anchor_message(epoch, root, head_before))
        rec = dict(t='ANC', epoch=epoch, n=len(self.leaves), root=root.hex(), head=head_before.hex(),
                   sig=sig.hex(), pub=self.pub, tsa='simulated',
                   tsa_time=_dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
        e = enc(rec)
        self.head = link(self.head, rec_hash(e))
        self._buf.append(f'{self.head.hex()} {e.decode("ascii")}\n')
        self.counts['ANC'] = self.counts.get('ANC', 0) + 1
        self.n += 1
        self.leaves = []
        self.epochs.append(epoch)
        self.flush()
        return rec

    def has_epoch(self, name: str) -> bool:
        """True if an epoch of this name was anchored (used by the stages to avoid re-appending on a re-run)."""
        return name in self.epochs

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.flush()


# ------------------------------------------------------------------ verification (M13, level V1)
def verify_ledger(path, pub_hex: str | None = None, stop_at_first: bool = True) -> dict:
    """Recompute every chain link, every epoch Merkle root and every anchor signature."""
    head, leaves, n, anchors, errors = GENESIS_SEED, [], 0, 0, []
    counts: dict[str, int] = {}
    first_pub = pub_hex
    with open(path, encoding='ascii') as f:
        for i, line in enumerate(f):
            try:
                head_hex, js = line.rstrip('\n').split(' ', 1)
                rec = json.loads(js)
            except ValueError:
                errors.append(dict(index=i, error='malformed line'))
                break
            e = js.encode('ascii')
            if enc(rec, check=False) != e:
                errors.append(dict(index=i, error='non-canonical encoding'))
            rh = rec_hash(e)
            prev = head
            head = link(head, rh)
            if head.hex() != head_hex:
                errors.append(dict(index=i, error='chain link mismatch'))
                if stop_at_first:
                    break
            t = rec.get('t', '?')
            counts[t] = counts.get(t, 0) + 1
            if t == 'ANC':
                anchors += 1
                root = merkle_root(leaves)
                ok_root = rec.get('root') == root.hex() and rec.get('n') == len(leaves)
                ok_head = rec.get('head') == prev.hex()
                pub = first_pub or rec.get('pub')
                first_pub = first_pub or pub
                ok_sig = bool(pub) and rec.get('pub') == pub and verify_signature(
                    pub, rec.get('sig', ''), anchor_message(rec.get('epoch', ''), root, prev))
                if not (ok_root and ok_head and ok_sig):
                    errors.append(dict(index=i, error='anchor', root=ok_root, head=ok_head, signature=ok_sig))
                    if stop_at_first:
                        break
                leaves = []
            else:
                leaves.append(rh)
            n += 1
    return dict(ok=not errors, records=n, anchors=anchors, open_epoch_records=len(leaves),
                head=head.hex(), errors=errors[:20], counts=counts, pub=first_pub)


# ------------------------------------------------------------------ receipts (per-finding inclusion proofs)
def receipt(path, index: int) -> dict:
    """Inclusion proof of record ``index`` in its epoch and the anchor that closes the epoch."""
    leaves = []
    target = None
    with open(path, encoding='ascii') as f:
        for i, line in enumerate(f):
            head_hex, js = line.rstrip('\n').split(' ', 1)
            rh = rec_hash(js.encode('ascii'))
            rec = json.loads(js)
            if i == index:
                if rec.get('t') == 'ANC':
                    raise LedgerError('receipts are issued for records, not anchors')
                target = dict(index=i, record=rec, record_hash=rh.hex(), position=len(leaves))
            if rec.get('t') == 'ANC':
                if target is not None:
                    levels = merkle_levels(leaves)
                    proof = inclusion_proof(levels, target['position'])
                    target.update(epoch=rec['epoch'], root=rec['root'], anchor_index=i, anchor=rec,
                                  proof=[[s, h.hex()] for s, h in proof], epoch_size=len(leaves))
                    return target
                leaves = []
            else:
                leaves.append(rh)
    if target is None:
        raise LedgerError(f'record {index} not found')
    target.update(epoch=None, anchor=None, unanchored=True)   # non-guarantee N1
    return target


def verify_receipt(rc: dict, pub_hex: str | None = None) -> bool:
    if not rc.get('anchor'):
        return False
    e = enc(rc['record'], check=False)
    if rec_hash(e).hex() != rc['record_hash']:
        return False
    proof = [(s, bytes.fromhex(h)) for s, h in rc['proof']]
    root = bytes.fromhex(rc['root'])
    if not verify_inclusion(bytes.fromhex(rc['record_hash']), proof, root):
        return False
    anc = rc['anchor']
    pub = pub_hex or anc.get('pub')
    return anc.get('root') == rc['root'] and verify_signature(
        pub, anc['sig'], anchor_message(anc['epoch'], root, bytes.fromhex(anc['head'])))


def find_records(path, predicate, limit: int | None = None) -> list[tuple[int, dict]]:
    out = []
    with open(path, encoding='ascii') as f:
        for i, line in enumerate(f):
            rec = json.loads(line.split(' ', 1)[1])
            if predicate(rec):
                out.append((i, rec))
                if limit and len(out) >= limit:
                    break
    return out
