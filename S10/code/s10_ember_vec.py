#!/usr/bin/env python3
"""EMBER-2018 raw-feature CSV -> EMBER v2 vectors (2,381-d), re-implementing PEFeatureExtractor.process_raw_features of
the project copy of features.py (feature_version=2) without LIEF (raw features are already extracted). Batch
FeatureHasher calls; the entry-name quirk (string hashed per character) is preserved as in the original code.
Usage: python3 s10_ember_vec.py <subsample.csv[.gz]> <out.npz>"""
import sys, csv, gzip, json, ast, time
import numpy as np
from sklearn.feature_extraction import FeatureHasher

csv.field_size_limit(10 ** 9)


def parse(v):
    try:
        return json.loads(v)
    except Exception:
        return ast.literal_eval(v)


def FH(n, kind, batch):
    return FeatureHasher(n, input_type=kind).transform(batch).toarray().astype(np.float32)


def vectorize(rows):
    n = len(rows); out = []
    h = np.array([r['histogram'] for r in rows], np.float32); out.append(h / h.sum(1, keepdims=True))
    be = np.array([r['byteentropy'] for r in rows], np.float32); out.append(be / be.sum(1, keepdims=True))
    S = []
    for r in rows:
        s = r['strings']; div = float(s['printables']) if s['printables'] > 0 else 1.0
        S.append(np.hstack([s['numstrings'], s['avlength'], s['printables'], np.asarray(s['printabledist']) / div, s['entropy'],
                            s['paths'], s['urls'], s['registry'], s['MZ']]))
    out.append(np.array(S, np.float32))
    out.append(np.array([[g['size'], g['vsize'], g['has_debug'], g['exports'], g['imports'], g['has_relocations'], g['has_resources'],
                          g['has_signature'], g['has_tls'], g['symbols']] for g in (r['general'] for r in rows)], np.float32))
    hd = [r['header'] for r in rows]
    out.append(np.hstack([np.array([[x['coff']['timestamp']] for x in hd], np.float32),
                          FH(10, 'string', [[x['coff']['machine']] for x in hd]), FH(10, 'string', [x['coff']['characteristics'] for x in hd]),
                          FH(10, 'string', [[x['optional']['subsystem']] for x in hd]), FH(10, 'string', [x['optional']['dll_characteristics'] for x in hd]),
                          FH(10, 'string', [[x['optional']['magic']] for x in hd]),
                          np.array([[x['optional'][k] for k in ('major_image_version', 'minor_image_version', 'major_linker_version', 'minor_linker_version',
                                                                 'major_operating_system_version', 'minor_operating_system_version', 'major_subsystem_version',
                                                                 'minor_subsystem_version', 'sizeof_code', 'sizeof_headers', 'sizeof_heap_commit')] for x in hd], np.float32)]))
    sec = [r['section'] for r in rows]
    gen = np.array([[len(s['sections']), sum(1 for z in s['sections'] if z['size'] == 0), sum(1 for z in s['sections'] if z['name'] == ''),
                     sum(1 for z in s['sections'] if 'MEM_READ' in z['props'] and 'MEM_EXECUTE' in z['props']),
                     sum(1 for z in s['sections'] if 'MEM_WRITE' in z['props'])] for s in sec], np.float32)
    out.append(np.hstack([gen,
                          FH(50, 'pair', [[(z['name'], z['size']) for z in s['sections']] for s in sec]),
                          FH(50, 'pair', [[(z['name'], z['entropy']) for z in s['sections']] for s in sec]),
                          FH(50, 'pair', [[(z['name'], z['vsize']) for z in s['sections']] for s in sec]),
                          FH(50, 'string', [list(s['entry']) for s in sec]),                 # quirk preserved: legacy sklearn hashed the entry string per character
                          FH(50, 'string', [[p for z in s['sections'] for p in z['props'] if z['name'] == s['entry']] for s in sec])]))
    imp = [r['imports'] for r in rows]
    out.append(np.hstack([FH(256, 'string', [list(set(l.lower() for l in d.keys())) for d in imp]),
                          FH(1024, 'string', [[l.lower() + ':' + e for l, el in d.items() for e in el] for d in imp])]))
    out.append(FH(128, 'string', [r['exports'] for r in rows]))
    names = ['EXPORT_TABLE', 'IMPORT_TABLE', 'RESOURCE_TABLE', 'EXCEPTION_TABLE', 'CERTIFICATE_TABLE', 'BASE_RELOCATION_TABLE', 'DEBUG',
             'ARCHITECTURE', 'GLOBAL_PTR', 'TLS_TABLE', 'LOAD_CONFIG_TABLE', 'BOUND_IMPORT', 'IAT', 'DELAY_IMPORT_DESCRIPTOR', 'CLR_RUNTIME_HEADER']
    DD = np.zeros((n, 30), np.float32)
    for i, r in enumerate(rows):
        dd = r['datadirectories']
        for k in range(15):
            if k < len(dd):
                DD[i, 2 * k] = dd[k]['size']; DD[i, 2 * k + 1] = dd[k]['virtual_address']
    out.append(DD)
    V = np.hstack(out).astype(np.float32)
    assert V.shape[1] == 2381, V.shape
    return V


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]; t = time.perf_counter()
    op = gzip.open if src.endswith('.gz') else open
    Vs = []; meta = []; buf = []
    with op(src, 'rt', encoding='utf-8', newline='') as f:
        r = csv.reader(f); hdr = next(r)
        for row in r:
            if row and row[0] == 'sha256':
                continue                      # header repeated in appended gzip members is not expected, but skip if present
            d = dict(zip(hdr, row))
            buf.append({k: parse(d[k]) for k in ('histogram', 'byteentropy', 'strings', 'general', 'header', 'section', 'imports', 'exports', 'datadirectories')})
            meta.append((d['sha256'], d['appeared'], int(d['label'])))
            if len(buf) == 2000:
                Vs.append(vectorize(buf)); buf = []
                print(len(meta), round(time.perf_counter() - t, 1), flush=True)
    if buf:
        Vs.append(vectorize(buf))
    V = np.vstack(Vs)
    np.savez(dst, X=V, sha=np.array([m_[0] for m_ in meta]), appeared=np.array([m_[1] for m_ in meta]), y=np.array([m_[2] for m_ in meta]))
    print('vectorised', V.shape, round(time.perf_counter() - t, 1), 's')
