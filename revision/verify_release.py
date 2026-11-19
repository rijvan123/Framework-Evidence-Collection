"""Verify the released TRACE-PE run and reproduce Tables A2 and A3 of the revised manuscript.

Usage
    python verify_release.py --ledger S10_ledger.jsonl.gz --package S10 [--out verify_out]

What it does (no model is fitted and no BODMAS data are read)
  1. Re-computes the domain-separated SHA-256 hash chain of every ledger record, the Merkle root of every epoch and the
     Ed25519 signature of every anchor (the anchor key is derived from a public seed, so a valid signature shows
     integrity of the chain, not resistance to forgery).
  2. Hashes every file bound by a REPORT or DOC record and compares size and SHA-256 with the package on disk.
  3. Rebuilds the model-update chronology of the primary assurance simulation (Table A2) from the ledger.
  4. Rebuilds the day-by-day validity of the error statement (Table A3) from the simulation's certificate table
     (out/reval_L30_rho1.0.pkl, loaded with an unpickler that admits only built-in containers), with freshness checked
     separately for the FPR bound and for the FNR bound, and lists every expiry and renewal event.
  5. Runs self-tests of the validity rule, including a 91-day-old FPR bound next to a 31-day-old FNR bound.
Requires Python >= 3.10, numpy, scipy, pandas; the 'cryptography' package for step 1's signatures (skipped if absent)."""
import argparse, collections, datetime as dt, gzip, hashlib, json, os, pickle, struct, sys
import pandas as pd
from scipy.stats import beta

DOM = b'TRACE-PE/v1/'
H = lambda b: hashlib.sha256(b).digest()
rec_hash = lambda e: H(DOM + b'rec\x00' + e)
link = lambda prev, rh: H(DOM + b'chain\x00' + prev + rh)
f32 = lambda h: struct.unpack('<f', bytes.fromhex(h))[0]          # binary32 values are stored little-endian hex
EPOCH = dt.date(1970, 1, 1)
dn = lambda s: (dt.date.fromisoformat(s) - EPOCH).days
ds = lambda d: str(EPOCH + dt.timedelta(days=int(d)))
cp_upper = lambda k, n, a=0.05: 1.0 if k >= n else float(beta.ppf(1 - a, k + 1, n - k))
month_last_day = lambda mm: dn(str(pd.Period(mm, 'M').end_time.date()))

# Parameters of the primary simulation (protocol S10_protocol.md; manuscript Section 7.6)
TAU_FPR, TAU_FNR, A_MAX, L_DAYS = 0.005, 0.05, 60, 30


def merkle_root(leaves):
    level = [H(b'\x00' + x) for x in leaves]
    if not level:
        return H(b'')
    while len(level) > 1:
        nxt = [H(b'\x01' + level[i] + level[i + 1]) for i in range(0, len(level) - 1, 2)]
        if len(level) % 2:
            nxt.append(level[-1])
        level = nxt
    return level[0]


class BuiltinsOnly(pickle.Unpickler):
    """The simulation outputs hold only dicts, lists, numbers and strings; anything else is refused."""
    def find_class(self, module, name):
        raise pickle.UnpicklingError(f'refused: {module}.{name}')


# ---------------------------------------------------------------------------------------------- validity rule
def statement_valid(t, fpr_bounds, fnr_bounds, tau_fpr=TAU_FPR, tau_fnr=TAU_FNR, a_max=A_MAX):
    """Validity of the error statement on day t (days since 1970-01-01).
    fpr_bounds / fnr_bounds: lists of (last_day_of_covered_month, upper_bound, available_from_day, source).
    Each error rate is judged on its own freshest available bound: it must be within tolerance and at most a_max days
    old, counted from the last day of the month it covers. Returns (valid, reasons, freshest_fpr, freshest_fnr)."""
    F = [b for b in fpr_bounds if b[2] <= t]
    N = [b for b in fnr_bounds if b[2] <= t]
    if not F or not N:
        return False, ['no FPR bound' if not F else 'no FNR bound'], (max(F) if F else None), (max(N) if N else None)
    f, n = max(F), max(N)                                   # freshest = latest covered month
    reasons = [w for w, bad in (('FPR bound older than %d d' % a_max, t - f[0] > a_max),
                                ('FPR bound above tolerance', f[1] > tau_fpr),
                                ('FNR bound older than %d d' % a_max, t - n[0] > a_max),
                                ('FNR bound above tolerance', n[1] > tau_fnr)) if bad]
    return not reasons, reasons, f, n


def self_tests():
    t = dn('2020-06-30')
    fpr_old = [(dn('2020-03-31'), 0.003, dn('2020-04-30'), 'Mar')]          # 91 days old on 30 June
    fnr_new = [(dn('2020-05-31'), 0.03, dn('2020-06-30'), 'May')]           # 30 days old
    ok, why, _, _ = statement_valid(t, fpr_old, fnr_new)
    assert not ok and why == ['FPR bound older than 60 d'], (ok, why)        # the reviewer's case: must be rejected
    ok, _, _, _ = statement_valid(t, fpr_old + [(dn('2020-05-31'), 0.003, dn('2020-06-30'), 'May')], fnr_new)
    assert ok                                                               # renewal by a fresh FPR bound
    ok, why, _, _ = statement_valid(t, [(dn('2020-05-31'), 0.007, dn('2020-06-30'), 'May')], fnr_new)
    assert not ok and why == ['FPR bound above tolerance']                  # expiry by tolerance
    ok, why, _, _ = statement_valid(dn('2020-07-31'), [(dn('2020-05-31'), 0.003, dn('2020-06-30'), 'May')], fnr_new)
    assert not ok and set(why) == {'FPR bound older than 60 d', 'FNR bound older than 60 d'}
    ok, why, _, _ = statement_valid(dn('2020-06-29'), fpr_old, fnr_new)    # FNR bound not yet available on 29 June
    assert not ok
    return 'all 5 validity-rule tests passed'


# ---------------------------------------------------------------------------------------------- 1. ledger
def verify_ledger(path):
    with gzip.open(path, 'rt') as f:
        lines = [json.loads(x) for x in f]
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        pub = Ed25519PrivateKey.from_private_bytes(H(b'S10-simulated-anchor-key')[:32]).public_key()
    except ImportError:
        pub = None
    head = link(H(DOM + b'genesis\x00'), rec_hash(lines[0]['e'].encode('ascii')))
    ok, first_bad, epochs, anchors, sig_ok = lines[0]['h'] == head.hex(), None, {}, 0, 0
    recs = [(lines[0]['q'], json.loads(lines[0]['e']))]
    for L in lines[1:]:
        raw = L['e'].encode('ascii'); rh = rec_hash(raw); head = link(head, rh)
        if rh.hex() != L['rh'] or head.hex() != L['h']:
            ok, first_bad = False, L['q']; break
        r = json.loads(L['e']); recs.append((L['q'], r))
        if r.get('t') == 'ANC':
            anchors += 1
            root = merkle_root(epochs.get(r['epoch'], []))
            if root.hex() != r['root']:
                ok, first_bad = False, L['q']; break
            if pub is not None:
                try:
                    pub.verify(bytes.fromhex(r['sig']), r['epoch'].encode() + root + bytes.fromhex(r['head'])); sig_ok += 1
                except Exception:
                    pass
        epochs.setdefault(r.get('ep', 'setup'), []).append(rh)
    summary = dict(records=len(lines), chain_and_merkle_ok=ok, first_bad_record=first_bad, final_head=lines[-1]['h'],
                   anchors=anchors, anchor_signatures_valid=(sig_ok if pub is not None else 'not checked (no cryptography)'),
                   record_types=dict(collections.Counter(r.get('t') for _, r in recs)))
    return summary, recs


# ---------------------------------------------------------------------------------------------- 2. bound files
def verify_files(recs, package):
    """Each bound file is looked up at its ledger path; if the package stores it elsewhere (for example logs under
    out/logs/), it is found by file name. A file matches if its size and SHA-256 equal the ledger's report record."""
    by_name = collections.defaultdict(list)
    for root, _, names in os.walk(package):
        for nm in names:
            by_name[nm].append(os.path.join(root, nm))
    rows = []
    for q, r in recs:
        if r.get('t') not in ('REPORT', 'DOC'):
            continue
        direct = os.path.join(package, r['path'])
        cands = [direct] if os.path.exists(direct) else by_name.get(os.path.basename(r['path']), [])
        if not cands:
            rows.append(dict(q=q, path=r['path'], status='missing')); continue
        status = None
        for p in cands:
            b = open(p, 'rb').read()
            if hashlib.sha256(b).hexdigest() == r['sha256'] and len(b) == r['bytes']:
                status = 'match' if p == direct else 'match at ' + os.path.relpath(p, package); break
            status = f'differs (ledger {r["bytes"]} bytes, disk {len(b)} bytes at {os.path.relpath(p, package)})'
        rows.append(dict(q=q, path=r['path'], status=status))
    return rows


# ---------------------------------------------------------------------------------------------- 3. Table A2
def chronology(recs, tag='L30_rho1.0'):
    chron = collections.OrderedDict()
    for q, e in recs:
        if e.get('ep') == 'assurance' and e.get('tag') == tag and e.get('t') in ('MAN', 'MOD', 'CAL'):
            c = chron.setdefault(e['u'], {'model_deployed': e['u']})
            if e['t'] == 'MAN':
                c.update(man_q=q, train_cutoff=e['cutoff'], cal_month=e['cal_month'], manifest_root=e['root'][:8])
            elif e['t'] == 'MOD':
                c.update(mod_q=q, model_identity=e['ident'][:8])
            else:
                c.update(cal_q=q, k_001=e['k_001'], k_005=e['k_005'], theta_001=round(f32(e['thr_001']), 3),
                         theta_005=round(f32(e['thr_005']), 3))
    for u, c in chron.items():
        c['labels_matured_up_to'] = ds(dn(u) - L_DAYS)
    return chron


# ---------------------------------------------------------------------------------------------- 4. Table A3
def validity_trace(recs, chron, reval_path):
    R = BuiltinsOnly(open(reval_path, 'rb')).load()
    arm = R['native']['primary|viii_reconcile']
    nb = {}                                                  # dated benign files per month, from the ledger's CERT records
    for _, e in recs:
        if e.get('t') == 'CERT' and 'n_b' in e:
            nb.setdefault(e['month'], e['n_b'])
    models = sorted(chron)
    fnr_b = [(v['last'], v['fnr_ub'], v['avail'], m) for m, v in arm['cert'].items() if v['fnr_ub'] is not None]
    fpr_retro = [(v['last'], v['fpr_ub'], v['avail'], m) for m, v in arm['cert'].items() if v['fpr_ub'] is not None]
    per_day = collections.Counter(e['day'] for _, e in recs if e.get('t') == 'ISS')
    trace = []
    for t in range(dn('2020-03-01'), dn('2020-09-30') + 1):
        u = max(x for x in models if dn(x) <= t); c = chron[u]; cm = c['cal_month']
        cal = (month_last_day(cm), cp_upper(c['k_005'], nb[cm]), dn(u), 'calibration ' + cm)   # model's own certificate
        ok, why, f, n = statement_valid(t, [cal] + fpr_retro, fnr_b)
        trace.append(dict(day=ds(t), model=u, valid=ok, why='; '.join(why), n_issued=per_day[ds(t)],
                          fpr=f'{f[3]}: {100 * f[1]:.3f}%, {t - f[0]} d', fnr=f'{n[3]}: {100 * n[1]:.2f}%, {t - n[0]} d'))
    events, prev = [], None
    for d in trace:
        if prev is not None and d['valid'] != prev['valid']:
            events.append(dict(day=d['day'], event='renewal' if d['valid'] else 'expiry', reason=d['why'] or 'fresh bounds'))
        prev = d
    check = dict(findings_on_invalid_days=sum(d['n_issued'] for d in trace if not d['valid']),
                 simulation_screening_only_with_gating=R['native']['primary|a2_cert']['scr_at_issue'])
    return trace, events, check


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ledger', required=True)
    ap.add_argument('--package', required=True, help='folder of the released run package (contains code/, out/, tables/)')
    ap.add_argument('--out', default='verify_out')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    print(self_tests())
    led, recs = verify_ledger(a.ledger)
    print(json.dumps(led, indent=1))
    files = verify_files(recs, a.package)
    n_match = sum(r['status'].startswith('match') for r in files)
    print(f'bound files: {n_match} of {len(files)} match the package')
    for r in files:
        if not r['status'].startswith('match'):
            print('  ', r)
    chron = chronology(recs)
    trace, events, check = validity_trace(recs, chron, os.path.join(a.package, 'out', 'reval_L30_rho1.0.pkl'))
    print('Table A2 (model updates):')
    for c in chron.values():
        print('  ', c)
    print('Table A3 events (expiry / renewal):')
    for e in events:
        print('  ', e)
    print('check:', check, '(equal)' if check['findings_on_invalid_days'] == check['simulation_screening_only_with_gating'] else '(DIFFERENT)')
    json.dump(dict(ledger=led, files=files, table_A2=list(chron.values()), table_A3_daily=trace, events=events, check=check),
              open(os.path.join(a.out, 'verify_release.json'), 'w'), indent=1)
    pd.DataFrame(trace).to_csv(os.path.join(a.out, 'table_A3_daily.csv'), index=False)
    pd.DataFrame(list(chron.values())).to_csv(os.path.join(a.out, 'table_A2.csv'), index=False)
    ok = led['chain_and_merkle_ok'] and check['findings_on_invalid_days'] == check['simulation_screening_only_with_gating']
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
