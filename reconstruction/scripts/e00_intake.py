#!/usr/bin/env python3
"""E0 - acquisition check, temporal-evidence screen, canonical vectors, duplicate audit, oracle snapshot and
ledger genesis (paper Section 4.3, strata table; S7 Algorithm 1, modules M1-M5).

The MAN0 manifest and the ACQ records are written byte-for-byte as in the paper's S7 probe, so the chain
head after the last ACQ record and the oracle Merkle root are exact checkpoints (results/paper_reference.json)."""
import json
import sys

import numpy as np
import pandas as pd

import _common  # noqa: F401
from tracepe.config import cli, resolve
from tracepe.data import bodmas
from tracepe.decision.thresholds import cp_upper, k_star
from tracepe.evidence import hashing as hh
from tracepe.evidence.merkle import merkle_root
from tracepe.evidence.screen import screen
from tracepe.features.groups import GROUPS, check_invariants
from tracepe.run import Run
from tracepe.utils import env_info, log, timer


def main():
    cfg, args = cli(__doc__)
    run = Run(cfg)
    if run.ledger_path.exists() and run.ledger_path.stat().st_size > 0:
        sys.exit(f'{run.ledger_path} already holds records: the ledger is append-only. '
                 f'Start a new run directory (run.dir) to repeat the intake.')
    T = {}
    R = dict(env=env_info(), config_sources=cfg['_sources'])
    data_dir = resolve(cfg['data']['bodmas_dir'])

    # ---- M1: digests at source vs after transfer (F1)
    with timer('file digests', T, 'digests'):
        dig = bodmas.file_digests(data_dir)
    exp = cfg['acquisition']['expected_sha256']
    if isinstance(exp, str):
        exp = json.loads(resolve(exp).read_text())
    R['file_sha256'] = dig
    R['file_bytes'] = {f: (data_dir / f).stat().st_size for f in dig}
    R['transfer_integrity_match'] = {f: exp.get(f) == dig[f] for f in dig}
    if not all(R['transfer_integrity_match'].values()) and cfg['acquisition'].get('halt_on_mismatch', True):
        run.save('e0_intake', R)
        sys.exit(f'F1: digest mismatch {R["transfer_integrity_match"]} - intake halted, nothing issued')

    # ---- load and schema / row alignment (F2)
    with timer('load release', T, 'load'):
        X, y, meta, cat, members = bodmas.load_release(data_dir)
    n, d = X.shape
    R['npz_members'] = members
    R['X'] = dict(dtype=str(X.dtype), shape=[n, d], nbytes=int(X.nbytes), c_contiguous=bool(X.flags['C_CONTIGUOUS']))
    R['y_counts'] = {str(k): int(v) for k, v in zip(*np.unique(y, return_counts=True))}
    fam_present = (meta['family'] != '').to_numpy()
    R['row_alignment'] = dict(rows_equal=len(meta) == n, y1_with_family=int(((y == 1) & fam_present).sum()),
                              y0_without_family=int(((y == 0) & ~fam_present).sum()),
                              mismatches=int(((y == 1) != fam_present).sum()))
    if X.dtype != np.float32 or d != 2381 or len(meta) != n or R['row_alignment']['mismatches']:
        run.save('e0_intake', R)
        sys.exit('F2: schema or row-alignment violation - intake halted')
    R['sha_unique'] = bool(meta['sha'].is_unique)
    cat_map = dict(zip(cat['sha256'], cat['category']))
    category = meta['sha'].map(cat_map).fillna('').to_numpy()
    R['category_join'] = dict(malware_with_category=int(((y == 1) & (category != '')).sum()),
                              benign_with_category=int(((y == 0) & (category != '')).sum()),
                              category_rows_not_in_metadata=int((~cat['sha256'].isin(set(meta['sha']))).sum()),
                              category_sha_unique=bool(cat['sha256'].is_unique))
    R['category_counts'] = {k: int(v) for k, v in pd.Series(category[y == 1]).value_counts().items()}
    fam_raw = meta['family'].to_numpy()
    R['family_strings_raw'] = int(len(set(fam_raw[fam_present])))
    R['family_strings_casefold'] = int(len(set(s.lower() for s in fam_raw[fam_present])))

    # ---- M2: temporal-evidence screen
    m0 = pd.DataFrame({'sid': meta['sha'].to_numpy(), 'timestamp': meta['timestamp'].to_numpy(), 'family': fam_raw,
                       'y': y.astype(np.int8), 'category': category})
    with timer('screen', T, 'screen'):
        m, scr = screen(m0, cfg)
    R['screen'] = scr

    # ---- M3/M5: invariants, non-finite values, canonical vector hashes
    with timer('invariants', T, 'invariants'):
        nonfinite = negzero = 0
        for s in range(0, n, 20000):
            blk = X[s:s + 20000]
            nonfinite += int((~np.isfinite(blk)).sum())
            negzero += int(((blk == 0) & np.signbit(blk)).sum())
        inv, row_ok = check_invariants(X)
    R['nonfinite_values'] = nonfinite
    R['negative_zero_values'] = negzero
    R['invariants'] = inv
    with timer('vector hashes', T, 'vector_hashes'):
        vh = hh.vector_hashes(X)
    R['vector_hash_MBps'] = round(n * d * 4 / 1e6 / max(T['vector_hashes'], 1e-9), 1)
    m['vh'] = vh
    m.loc[~row_ok, 'stratum'] = 'Quarantine'
    m.loc[~row_ok, 'split'] = ''
    m['quarantine_reason'] = np.where(m['quarantine'], 'identifier', np.where(~row_ok, 'invariant', ''))

    # ---- duplicate audit and cross-split policy (Eq. (23))
    vs = pd.Series(vh)
    sizes = vs.value_counts()
    dup_keys = set(sizes[sizes > 1].index)
    split = m['split'].to_numpy()
    # split labels of the S7 duplicate audit (outside the window -> pre_window, spike day -> censored)
    split7 = np.where(~m['in_win'].to_numpy(), 'pre_window', np.where(m['censored'].to_numpy(), 'censored', split))
    rank = {'train': 0, 'calibration': 1, 'test': 2}
    dup_drop = np.zeros(n, bool)
    groups = []
    for key in sorted(dup_keys):
        rows = np.flatnonzero(vh == key)
        rows = rows[np.argsort(m['order'].to_numpy()[rows])]
        lab = set(y[rows].tolist())
        fams = set(fam_raw[r] for r in rows if y[r] == 1)
        sp = [split[r] for r in rows]
        sp7 = [split7[r] for r in rows]
        for r in rows:
            if split[r] in rank:
                for r2 in rows:
                    if split[r2] in rank and rank[split[r2]] < rank[split[r]]:
                        dup_drop[r] = True
        groups.append(dict(members=[m['sid'].iat[r] for r in rows], strata=[m['stratum'].iat[r] for r in rows],
                           splits=sp, labels=sorted(lab), label_conflict=len(lab) > 1, family_conflict=len(fams) > 1,
                           first_seen=[m['timestamp'].iat[r] for r in rows],
                           gap_days=int(m['day'].iat[rows[-1]] - m['day'].iat[rows[0]]),
                           drop=[m['sid'].iat[r] for r in rows if dup_drop[r]], splits_s7=sp7))
    m['dup_drop'] = dup_drop
    tr_v = set(vh[split == 'train'])
    cal_v = set(vh[split == 'calibration'])
    R['duplicates'] = dict(unique_vectors=int(len(sizes)), rows=int(n), duplicate_groups=len(dup_keys),
                           rows_in_duplicate_groups=int(sizes[sizes > 1].sum()) if len(dup_keys) else 0,
                           largest_group=int(sizes.max()), groups_label_conflict=sum(g['label_conflict'] for g in groups),
                           malware_groups_family_conflict=sum(g['family_conflict'] for g in groups),
                           groups_spanning_splits=sum(len(set(g['splits_s7'])) > 1 for g in groups),
                           test_rows_vector_in_train=int(((split == 'test') & np.isin(vh, list(tr_v))).sum()),
                           calibration_rows_vector_in_train=int(((split == 'calibration') & np.isin(vh, list(tr_v))).sum()),
                           test_rows_vector_in_train_or_cal=int(((split == 'test') & np.isin(vh, list(tr_v | cal_v))).sum()),
                           dropped_rows=int(dup_drop.sum()), groups=groups)

    # ---- near duplicates (cosine >= 1 - delta), candidates blocked on the GeneralFileInfo signature (impl.)
    with timer('near duplicates', T, 'near_dups'):
        sig = {}
        tr_rows = np.flatnonzero(split == 'train')
        G = np.asarray(X[:, 616:626])
        for r in tr_rows:
            sig.setdefault(G[r].tobytes(), []).append(r)
        near = {str(dl): 0 for dl in cfg['screen']['near_dup_deltas']}
        for r in np.flatnonzero(np.isin(split, ['calibration', 'test'])):
            cand = sig.get(G[r].tobytes())
            if not cand:
                continue
            A = np.asarray(X[cand], dtype=np.float64)
            v = np.asarray(X[r], dtype=np.float64)
            cos = (A @ v) / (np.linalg.norm(A, axis=1) * np.linalg.norm(v) + 1e-300)
            for dl in cfg['screen']['near_dup_deltas']:
                near[str(dl)] += int((cos >= 1 - dl).any())
        R['near_duplicates'] = dict(blocking='GeneralFileInfo signature (impl.)', eval_rows_with_near_dup_in_train=near)

    # ---- R-T6: COFF TimeDateStamp vs first-seen (timeline-quality flags only)
    coff = np.asarray(X[:, 626], dtype=np.float64)
    fs_epoch = (m['fs'] - pd.Timestamp('1970-01-01', tz='UTC')).dt.total_seconds().to_numpy()
    aud = {}
    for c, nm in [(0, 'benign'), (1, 'malware')]:
        sel = m['in_win'].to_numpy() & (y == c)
        c_, f_ = coff[sel], fs_epoch[sel]
        aud[nm] = dict(n=int(sel.sum()), coff_zero=round(float(np.mean(c_ == 0)), 6) if sel.any() else None,
                       coff_after_first_seen_plus1d=round(float(np.mean((c_ > f_ + 86400) & (c_ > 0))), 6) if sel.any() else None,
                       coff_before_1992=round(float(np.mean((c_ > 0) & (c_ < 694224000))), 6) if sel.any() else None,
                       coff_float32_quantum_s=int(np.spacing(np.float32(1.6e9))))
    R['coff_audit'] = aud

    # ---- family tokens (D8) and the evaluation index
    m['fam'] = m['family'].str.lower()
    m['generic'] = m['fam'].str.fullmatch(cfg['screen']['generic_family_regex']).fillna(False).to_numpy() & (m['y'] == 1).to_numpy()
    ev = (np.isin(split, ['calibration', 'test']) | m['stratum'].isin(['Placeholder', 'Bulk', 'SpikeMal']).to_numpy()) & ~dup_drop
    eval_idx = np.flatnonzero(ev)
    eval_idx = eval_idx[np.argsort(m['order'].to_numpy()[eval_idx], kind='stable')]
    R['eval_rows'] = int(len(eval_idx))
    s = cfg['screen']
    cal = m[(m['split'] == 'calibration')]
    nb_dec = int((cal['y'] == 0).sum())
    R['certified_threshold_calibration'] = dict(
        n_benign=nb_dec, n_malware=int((cal['y'] == 1).sum()),
        rule={str(t): dict(k_star=k_star(nb_dec, t),
                           ub_at_k_star=(round(cp_upper(k_star(nb_dec, t), nb_dec) * 100, 4) if k_star(nb_dec, t) >= 0 else None))
              for t in cfg['thresholds']['certified_tau']},
        empirical={str(b): dict(k=int(np.floor(b * nb_dec)), ub=round(cp_upper(int(np.floor(b * nb_dec)), nb_dec) * 100, 4))
                   for b in cfg['thresholds']['empirical_beta']})

    # ---- cache for the later steps
    with timer('cache', T, 'cache'):
        np.save(run.cache / 'X.npy', np.ascontiguousarray(X, dtype='<f4'))
        np.save(run.cache / 'eval_idx.npy', eval_idx)
        m.to_pickle(run.cache / 'meta.pkl')
    del X

    # ---- ledger: MAN0 genesis and ACQ records exactly as in the S7 probe, then PREREG, EXT, SCR, NCR, DUP, ORC
    with timer('ledger', T, 'ledger'):
        L = run.ledger()
        L.append(dict(t='MAN0', files=dig, feature_version=2, dims=d, extractor_claim=cfg['acquisition']['extractor_claim']))
        has25 = (m['timestamp'].str.len() == 25).to_numpy()
        win = m['in_win'].to_numpy()
        cen = m['censored'].to_numpy()
        sid = m['sid'].to_numpy()
        ts = m['timestamp'].to_numpy()
        ds = dig['bodmas.npz'][:16]
        for i in range(n):
            L.append(dict(t='ACQ', q=i + 1, sid=sid[i], vh=vh[i], fs=ts[i], off=bool(has25[i]), win=bool(win[i]),
                          cen=bool(cen[i]), ds=ds))
        acq_head = L.head.hex()
        prereg = resolve(cfg['prereg_file'])
        if prereg.exists():
            R['prereg'] = dict(file=str(cfg['prereg_file']), sha256=hh.sha256_file(prereg))
            L.append(dict(t='PREREG', file=str(cfg['prereg_file']), sha256=R['prereg']['sha256']))
        else:
            R['prereg'] = None
        L.append(dict(t='EXT', feature_version=2, lief='0.9.0', status='declared, not executed',
                      group_map_sha256=hh.sha256_hex(hh.enc([[g, a, b] for g, a, b in GROUPS])), invariant_set='v1'))
        L.append(dict(t='SCR', window=[s['window_start'], s['window_end']], spike_k=s['spike_k'],
                      spike_median=str(scr['spike_rule'][f'all_k{s["spike_k"]}']['median']),
                      spike_mad=str(scr['spike_rule'][f'all_k{s["spike_k"]}']['mad']),
                      spike_days=sorted(scr['spike_rule'][f'all_k{s["spike_k"]}']['spike_days']),
                      strata={k: v for k, v in scr['strata'].items()}, splits=scr['splits'],
                      strata_sha256=hh.sha256_hex('\n'.join(m['stratum'].astype(str)).encode())))
        for i in np.flatnonzero(m['quarantine_reason'].to_numpy() != ''):
            L.append(dict(t='NCR', code=m['quarantine_reason'].iat[i], sid=sid[i], action='Quarantine stratum'))
        for k, g in enumerate(groups):
            L.append(dict(t='DUP', group=k, members=g['members'], keep=g['members'][0], drop=g['drop'],
                          reason='earliest first-seen row kept; later splits dropped'))
        with timer('oracle root', T, 'oracle_root'):
            leaves = [hh.enc(dict(sid=sid[i], y=int(y[i]), fam=fam_raw[i], cat=category[i])) for i in range(n)]
            orc_root = merkle_root(leaves).hex()
        L.append(dict(t='ORC', root=orc_root, leaves=n, oracle='BODMAS release labels', dataset=ds))
        anc = L.anchor('e0-intake')
        L.flush()
    R['ledger'] = dict(acq_chain_head=acq_head, oracle_root=orc_root, records=L.n, anchor_root=anc['root'],
                       anchor_public_key=L.pub)
    R['timings_s'] = T
    run.save('e0_intake', R)
    log('E0 done:', {k: v for k, v in scr['strata'].items()}, 'eval rows', len(eval_idx))
    log('acquisition-chain head', acq_head, '| oracle root', orc_root)


if __name__ == '__main__':
    main()
