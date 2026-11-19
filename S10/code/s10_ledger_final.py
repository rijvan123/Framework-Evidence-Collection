#!/usr/bin/env python3
"""Close the S10 ledger: TRG (monitor), CERT (retrospective certificates of f0), RVC per re-validation event (L = 30, TRACE-PE),
REPORT records binding every S10 result file and figure by SHA-256, anchors for all open epochs, then V1 + V2 verification.
Output: out/ledger_final.json"""
import os, json, glob, pickle, hashlib
import numpy as np
import s10_common as C

recs = []
mon = json.load(open(f'{C.OUT}/monitor.json'))
recs.append(dict(t='TRG', kind='drift', model='f0', alarms=mon['alarms'], exceed_share=C.f32hex(mon['exceed_any_share']), KT_pass=int(mon['KT_pass']),
                 lam={k: C.f32hex(v) for k, v in mon['lam'].items()}, window_days=7, persistence=2, note='every test window exceeded >= 1 null maximum'))
cert = json.load(open(f'{C.OUT}/analysis_certificates.json'))
for key in ('thr0.001|tau0.001/0.02', 'thr0.005|tau0.005/0.05'):
    for mm, r in cert[key]['months'].items():
        recs.append(dict(t='CERT', kind='retrospective', model='f0', key=key, month=mm, fp=r['fp'], n_b=r['n_b'], fn=r['fn'], n_m=r['n_m'],
                         fpr_ub=C.f32hex(r['fpr_ub']), fnr_ub=C.f32hex(r['fnr_ub']), fpr_cert=int(r['fpr_cert']), fnr_cert=int(r['fnr_cert'])))
R = pickle.load(open(f'{C.OUT}/reval_L30_rho1.0.pkl', 'rb'))
for e in R['native']['primary|tracepe']['events']:
    recs.append(dict(t='RVC', policy='tracepe', L=30, event=e['event'], N=e['N'], B=e['B'], changes=e['changes'], reviews=int(e.get('reviews') or 0),
                     review_hits=int(e.get('review_hits') or 0), auto=int(e.get('auto') or 0), flagged=int(e.get('flagged') or 0),
                     note='simulation summary; per-finding AMD records demonstrated in S7 prototype'))
C.ledger_append(recs, epoch='assurance')
files = sorted(glob.glob(f'{C.OUT}/*.json') + glob.glob(f'{C.OUT}/*.pkl') + glob.glob(f'{C.OUT}/*.log') + glob.glob(f'{C.OUT}/log_*.txt') +
               glob.glob(f'{C.FIGS}/*.pdf') + glob.glob(f'{C.FIGS}/*.png') + glob.glob(f'{C.FIGS}/*.json') + glob.glob(f'{C.TABLES}/*') +
               glob.glob(f'{C.ROOT}/code/*.py') + glob.glob(f'{C.ROOT}/code/*.sh') + glob.glob(f'{C.ROOT}/code/*.json') +
               [f'{C.ROOT}/report/assemble.py', f'{C.ROOT}/report/verify_numbers.py', f'{C.ROOT}/S10_protocol.md'])
files = [f for f in files if not f.endswith('ledger_final.json')]
rep = [dict(t='REPORT', path=os.path.relpath(f, C.ROOT), sha256=C.sha256_file(f), bytes=os.path.getsize(f)) for f in files]
C.ledger_append(rep, epoch='report')
eps = set()
with open(C.MAIN_LEDGER) as f:
    for L in f:
        r = json.loads(json.loads(L)['e'])
        if r.get('t') == 'ANC':
            eps.discard(r['epoch'])
        elif 'ep' in r and r['ep'] != 'anchors':
            eps.add(r['ep'])
for ep in sorted(eps):
    C.ledger_anchor(ep)
v1 = C.verify_main_ledger()
store = C.Store(); n_obj = 0; bad = 0
for p in glob.glob(f'{C.LEDGER_DIR}/objects/*/*'):
    n_obj += 1
    try:
        store.get(os.path.basename(p))
    except Exception:
        bad += 1
counts = {}
with open(C.MAIN_LEDGER) as f:
    for L in f:
        t = json.loads(json.loads(L)['e']).get('t'); counts[t] = counts.get(t, 0) + 1
last = C._last_line(C.MAIN_LEDGER)
out = dict(V1=v1, V2=dict(objects=n_obj, failures=bad), record_counts=counts, head=last['h'], report_files=len(rep),
           ledger_bytes=os.path.getsize(C.MAIN_LEDGER), anchored_epochs=sorted(eps))
C.jdump(out, f'{C.OUT}/ledger_final.json'); print(json.dumps(out, indent=1))
