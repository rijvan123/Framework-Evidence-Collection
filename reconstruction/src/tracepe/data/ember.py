"""EMBER feature version 2 vectoriser for raw-feature JSON lines (EMBER-2018 release, Anderson & Roth).

Reproduces ``PEFeatureExtractor(feature_version=2).process_raw_features`` of elastic/ember
``features.py`` group by group. Two version notes:

* EMBER hashes the entry-section name with ``FeatureHasher(50, input_type="string").transform([entry])``.
  Older scikit-learn iterates the *string*, i.e. hashes its characters; current scikit-learn rejects
  a bare string. We pass ``list(entry)``, which reproduces the original character hashing.
* Batched transforms (one FeatureHasher call per group over many samples) give exactly the same
  values as per-sample calls; ``vectorize_one`` is the per-sample transcription used in the tests.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
from sklearn.feature_extraction import FeatureHasher

DD_ORDER = ['EXPORT_TABLE', 'IMPORT_TABLE', 'RESOURCE_TABLE', 'EXCEPTION_TABLE', 'CERTIFICATE_TABLE',
            'BASE_RELOCATION_TABLE', 'DEBUG', 'ARCHITECTURE', 'GLOBAL_PTR', 'TLS_TABLE', 'LOAD_CONFIG_TABLE',
            'BOUND_IMPORT', 'IAT', 'DELAY_IMPORT_DESCRIPTOR', 'CLR_RUNTIME_HEADER']
DIM = 2381


def _fh(n, samples, kind='string'):
    return FeatureHasher(n, input_type=kind).transform(samples).toarray()


def _strings(raw):
    s = raw['strings']
    div = float(s['printables']) if s['printables'] > 0 else 1.0
    return np.hstack([s['numstrings'], s['avlength'], s['printables'], np.asarray(s['printabledist']) / div,
                      s['entropy'], s['paths'], s['urls'], s['registry'], s['MZ']])


def _general(raw):
    g = raw['general']
    return np.asarray([g['size'], g['vsize'], g['has_debug'], g['exports'], g['imports'], g['has_relocations'],
                       g['has_resources'], g['has_signature'], g['has_tls'], g['symbols']], dtype=np.float64)


def _header_scalars(raw):
    o = raw['header']['optional']
    return [o['major_image_version'], o['minor_image_version'], o['major_linker_version'], o['minor_linker_version'],
            o['major_operating_system_version'], o['minor_operating_system_version'], o['major_subsystem_version'],
            o['minor_subsystem_version'], o['sizeof_code'], o['sizeof_headers'], o['sizeof_heap_commit']]


def _section_general(raw):
    secs = raw['section']['sections']
    return [len(secs), sum(1 for s in secs if s['size'] == 0), sum(1 for s in secs if s['name'] == ''),
            sum(1 for s in secs if 'MEM_READ' in s['props'] and 'MEM_EXECUTE' in s['props']),
            sum(1 for s in secs if 'MEM_WRITE' in s['props'])]


def _entry_props(raw):
    sec = raw['section']
    return [p for s in sec['sections'] for p in s['props'] if s['name'] == sec['entry']]


def _datadirs(raw):
    dd = raw.get('datadirectories') or []
    out = np.zeros(2 * len(DD_ORDER))
    for i in range(len(DD_ORDER)):
        if i < len(dd):
            out[2 * i] = dd[i]['size']
            out[2 * i + 1] = dd[i]['virtual_address']
    return out


def vectorize_one(raw: dict) -> np.ndarray:
    """Per-sample transcription of EMBER v2 process_raw_features (reference implementation)."""
    hist = np.asarray(raw['histogram'], dtype=np.float32)
    hist = hist / hist.sum()
    beh = np.asarray(raw['byteentropy'], dtype=np.float32)
    beh = beh / beh.sum()
    secs = raw['section']['sections']
    section = np.hstack([_section_general(raw),
                         _fh(50, [[(s['name'], s['size']) for s in secs]], 'pair')[0],
                         _fh(50, [[(s['name'], s['entropy']) for s in secs]], 'pair')[0],
                         _fh(50, [[(s['name'], s['vsize']) for s in secs]], 'pair')[0],
                         _fh(50, [list(raw['section']['entry'])])[0],
                         _fh(50, [_entry_props(raw)])[0]])
    imp = raw['imports']
    libs = list(set(l.lower() for l in imp.keys()))
    funcs = [lib.lower() + ':' + e for lib, el in imp.items() for e in el]
    imports = np.hstack([_fh(256, [libs])[0], _fh(1024, [funcs])[0]])
    exports = _fh(128, [raw['exports']])[0]
    h = raw['header']
    header = np.hstack([h['coff']['timestamp'], _fh(10, [[h['coff']['machine']]])[0],
                        _fh(10, [h['coff']['characteristics']])[0], _fh(10, [[h['optional']['subsystem']]])[0],
                        _fh(10, [h['optional']['dll_characteristics']])[0], _fh(10, [[h['optional']['magic']]])[0],
                        _header_scalars(raw)])
    v = np.hstack([hist, beh, _strings(raw), _general(raw), header, section, imports, exports, _datadirs(raw)])
    return v.astype(np.float32)


def vectorize(raws: list[dict]) -> np.ndarray:
    """Batched vectorisation; identical values to vectorize_one, about 20x faster."""
    n = len(raws)
    X = np.zeros((n, DIM), np.float32)
    if n == 0:
        return X
    hist = np.asarray([r['histogram'] for r in raws], dtype=np.float32)
    X[:, 0:256] = hist / hist.sum(axis=1, keepdims=True)
    beh = np.asarray([r['byteentropy'] for r in raws], dtype=np.float32)
    X[:, 256:512] = beh / beh.sum(axis=1, keepdims=True)
    X[:, 512:616] = np.asarray([_strings(r) for r in raws], dtype=np.float32)
    X[:, 616:626] = np.asarray([_general(r) for r in raws], dtype=np.float32)
    hdr = [r['header'] for r in raws]
    X[:, 626] = np.asarray([h['coff']['timestamp'] for h in hdr], dtype=np.float32)
    X[:, 627:637] = _fh(10, [[h['coff']['machine']] for h in hdr])
    X[:, 637:647] = _fh(10, [h['coff']['characteristics'] for h in hdr])
    X[:, 647:657] = _fh(10, [[h['optional']['subsystem']] for h in hdr])
    X[:, 657:667] = _fh(10, [h['optional']['dll_characteristics'] for h in hdr])
    X[:, 667:677] = _fh(10, [[h['optional']['magic']] for h in hdr])
    X[:, 677:688] = np.asarray([_header_scalars(r) for r in raws], dtype=np.float32)
    X[:, 688:693] = np.asarray([_section_general(r) for r in raws], dtype=np.float32)
    secs = [r['section']['sections'] for r in raws]
    X[:, 693:743] = _fh(50, [[(s['name'], s['size']) for s in ss] for ss in secs], 'pair')
    X[:, 743:793] = _fh(50, [[(s['name'], s['entropy']) for s in ss] for ss in secs], 'pair')
    X[:, 793:843] = _fh(50, [[(s['name'], s['vsize']) for s in ss] for ss in secs], 'pair')
    X[:, 843:893] = _fh(50, [list(r['section']['entry']) for r in raws])
    X[:, 893:943] = _fh(50, [_entry_props(r) for r in raws])
    X[:, 943:1199] = _fh(256, [list(set(l.lower() for l in r['imports'].keys())) for r in raws])
    X[:, 1199:2223] = _fh(1024, [[lib.lower() + ':' + e for lib, el in r['imports'].items() for e in el] for r in raws])
    X[:, 2223:2351] = _fh(128, [r['exports'] for r in raws])
    X[:, 2351:2381] = np.asarray([_datadirs(r) for r in raws], dtype=np.float32)
    return X


_HEAD = re.compile(r'"appeared":\s*"(?P<appeared>[^"]*)".*?"label":\s*(?P<label>-?\d+)')
_SHA = re.compile(r'"sha256":\s*"(?P<sha>[0-9a-f]{64})"')


def scan_jsonl(paths) -> list[tuple[str, int, int, str, str]]:
    """Fast first pass: (file, line number, label, appeared, sha256) for every line, parsed from the line head."""
    rows = []
    for p in paths:
        with open(p, encoding='utf-8') as f:
            for i, line in enumerate(f):
                head = line[:400]
                m = _HEAD.search(head)
                s = _SHA.search(head)
                if m is None:
                    obj = json.loads(line)
                    rows.append((str(p), i, int(obj['label']), obj.get('appeared', ''), obj.get('sha256', '')))
                else:
                    rows.append((str(p), i, int(m.group('label')), m.group('appeared'), s.group('sha') if s else ''))
    return rows


def read_lines(selection: dict) -> list[dict]:
    """selection: {path: sorted line numbers}; returns parsed JSON objects in that order."""
    out = []
    for p, lines in selection.items():
        want = set(lines)
        with open(p, encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i in want:
                    out.append(json.loads(line))
    return out


def ember_files(ember_dir) -> list[Path]:
    d = Path(ember_dir)
    return sorted(d.glob('train_features_*.jsonl')) + sorted(d.glob('test_features.jsonl'))
