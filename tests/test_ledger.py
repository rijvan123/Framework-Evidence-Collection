"""Append-only ledger: chain, epochs, Ed25519 anchors, receipts, replay and tamper detection."""
import json

import pytest

from tracepe.evidence.ledger import Ledger, LedgerError, find_records, receipt, verify_ledger, verify_receipt


def build(tmp_path, n=50, epochs=3):
    L = Ledger(tmp_path / 'l.jsonl', tmp_path / 'k.pem')
    for e in range(epochs):
        for i in range(n):
            L.append(dict(t='REC', e=e, i=i, note=f'record {e}-{i}'))
        L.anchor(f'ep{e}')
    return L


def test_append_anchor_verify(tmp_path):
    L = build(tmp_path)
    v = verify_ledger(L.path, L.pub)
    assert v['ok'] and v['anchors'] == 3 and v['records'] == 153 and v['open_epoch_records'] == 0
    assert L.has_epoch('ep1') and not L.has_epoch('ep9')
    assert L.counts == {'REC': 150, 'ANC': 3}


def test_replay_continues_chain(tmp_path):
    L = build(tmp_path, n=10, epochs=1)
    head = L.head
    L2 = Ledger(tmp_path / 'l.jsonl', tmp_path / 'k.pem')
    assert L2.head == head and L2.n == L.n and L2.pub == L.pub and L2.epochs == ['ep0']
    L2.append(dict(t='REC', more=1))
    L2.anchor('ep1')
    assert verify_ledger(L2.path, L.pub)['ok']


@pytest.mark.parametrize('mutation', ['flip', 'delete', 'swap', 'insert', 'edit_field'])
def test_tamper_is_detected(tmp_path, mutation):
    L = build(tmp_path)
    lines = L.path.read_text().splitlines(keepends=True)
    j = 20
    if mutation == 'flip':
        b = bytearray(lines[j].encode())
        b[-5] ^= 0x01
        lines[j] = b.decode('latin-1')
    elif mutation == 'delete':
        del lines[j]
    elif mutation == 'swap':
        lines[j], lines[j + 1] = lines[j + 1], lines[j]
    elif mutation == 'insert':
        lines.insert(j, lines[j])
    else:
        head, js = lines[j].rstrip('\n').split(' ', 1)
        rec = json.loads(js)
        rec['note'] = 'changed'
        lines[j] = head + ' ' + json.dumps(rec, sort_keys=True, separators=(',', ':')) + '\n'
    L.path.write_text(''.join(lines), encoding='latin-1')
    assert not verify_ledger(L.path, L.pub)['ok']
    with pytest.raises(LedgerError):
        Ledger(L.path, tmp_path / 'k.pem')


def test_rewritten_chain_fails_on_signature(tmp_path):
    """An insider who recomputes every link still cannot forge the anchor signature."""
    L = build(tmp_path, n=5, epochs=1)
    other = Ledger(tmp_path / 'other.jsonl', tmp_path / 'other.pem')
    for i in range(5):
        other.append(dict(t='REC', e=0, i=i, note='forged'))
    other.anchor('ep0')
    assert verify_ledger(other.path)['ok']                       # self-consistent with its own key
    assert not verify_ledger(other.path, L.pub)['ok']            # but not under the published key


def test_receipts(tmp_path):
    L = build(tmp_path)
    hits = find_records(L.path, lambda r: r.get('t') == 'REC' and r['e'] == 1 and r['i'] == 7)
    assert len(hits) == 1
    rc = receipt(L.path, hits[0][0])
    assert rc['epoch'] == 'ep1' and verify_receipt(rc, L.pub)
    rc['record'] = dict(rc['record'], note='changed')
    assert not verify_receipt(rc, L.pub)
    L.append(dict(t='REC', open=True))
    L.flush()
    rc2 = receipt(L.path, L.n - 1)
    assert rc2.get('epoch') is None and not verify_receipt(rc2, L.pub)   # unanchored tail: no receipt


def test_floats_are_refused(tmp_path):
    L = Ledger(tmp_path / 'l.jsonl', tmp_path / 'k.pem')
    with pytest.raises(TypeError):
        L.append(dict(t='REC', x=0.1))
