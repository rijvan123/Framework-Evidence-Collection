"""Additional revision statistics from released run outputs only (ledger, simulation pickles, metrics table).
No model is re-fitted and no BODMAS data are read. Outputs: revision_extra.json.
Usage: python revision_extra.py <ledger.jsonl.gz> <package>/out/reval_L30_rho1.0.pkl <package>/out/e1_metrics.pkl [out.json]"""
import gzip, json, pickle, struct, sys, datetime as dt, collections
import numpy as np, pandas as pd
from scipy.stats import beta

LEDGER, REVAL, METRICS = sys.argv[1], sys.argv[2], sys.argv[3]          # ledger .jsonl.gz, out/reval_L30_rho1.0.pkl, out/e1_metrics.pkl
OUTF = sys.argv[4] if len(sys.argv) > 4 else 'revision_extra.json'
f32 = lambda h: struct.unpack('<f', bytes.fromhex(h))[0]
cp_upper = lambda k, n, a=0.05: 1.0 if k >= n else float(beta.ppf(1 - a, k + 1, n - k))
cp_lower = lambda k, n, a=0.05: 0.0 if k <= 0 else float(beta.ppf(a, k, n - k + 1))
cp_two = lambda k, n: (cp_lower(k, n, 0.025), cp_upper(k, n, 0.025))
EPOCH = dt.date(1970, 1, 1)
dn = lambda s: (dt.date.fromisoformat(s) - EPOCH).days
ds = lambda d: str(EPOCH + dt.timedelta(days=int(d)))
OUT = {}


class Safe(pickle.Unpickler):
    def find_class(self, m, n):
        raise pickle.UnpicklingError(f'blocked {m}.{n}')


# ---------------------------------------------------------------- (a) f0 pooled counts, exact intervals, Eq. (101)
m = pd.read_pickle(METRICS)
r = m[(m.model == 'lgbm_trace') & (m.seed == 11) & (m.set == 'pool_MarSep') & (m.thr == 'cert_0.1')].iloc[0]
tp, fn, fp, tn = int(r.tp), int(r.fn), int(r.fp), int(r.tn)
nm, nb = tp + fn, fp + tn
tpr_lb = 1 - cp_upper(fn, nm, 0.025); fpr_ub = cp_upper(fp, nb, 0.025)
ppv = lambda pi: pi * tpr_lb / (pi * tpr_lb + fpr_ub * (1 - pi))
OUT['f0_pooled'] = dict(tp=tp, fn=fn, fp=fp, tn=tn, tpr=100 * tp / nm, tpr_ci=[100 * x for x in cp_two(tp, nm)],
                        fpr=100 * fp / nb, fpr_ci=[100 * x for x in cp_two(fp, nb)],
                        prec1=100 * (0.01 * tp / nm) / (0.01 * tp / nm + 0.99 * fp / nb), prec1_lb=100 * ppv(0.01))

# ---------------------------------------------------------------- (b) model-update chronology (L = 30 d, rho = 1)
recs = []
with gzip.open(LEDGER, 'rt') as f:
    for line in f:
        o = json.loads(line); e = json.loads(o['e']); recs.append((o['q'], e))
chron = collections.OrderedDict()
for q, e in recs:
    if e.get('ep') == 'assurance' and e.get('tag') == 'L30_rho1.0' and e.get('t') in ('MAN', 'MOD', 'CAL'):
        c = chron.setdefault(e['u'], {})
        if e['t'] == 'MAN':
            c.update(man_q=q, cutoff=e['cutoff'], cal_month=e['cal_month'], root=e['root'])
        elif e['t'] == 'MOD':
            c.update(mod_q=q, ident=e['ident'], fit_s=round(f32(e['fit_s']), 1))
        else:
            c.update(cal_q=q, k_001=e['k_001'], k_005=e['k_005'], thr_001=round(f32(e['thr_001']), 3),
                     thr_005=round(f32(e['thr_005']), 3), kappa=round(f32(e['kappa']), 4))
f0 = {}
for q, e in recs:
    if e.get('ep') == 'issuance-setup' and e.get('t') == 'CAL':
        f0 = dict(cal_q=q, theta=round(f32(e['theta']), 3), kstar=e['kstar'], kappa=round(f32(e['kappa']), 4), model=e['model'], cal_root=e['cal_root'])
    if e.get('ep') == 'issuance-setup' and e.get('t') == 'CERT':
        f0.update(cert_q=q, fpr_ub=round(100 * f32(e['fpr_ub']), 4), fnr_ub=round(100 * f32(e['fnr_ub']), 3))
OUT['f0_setup'] = f0
for u, c in chron.items():
    L = 30
    c['labels_matured_before'] = ds(dn(u) - L)            # rows with t_i + L <= u, i.e. first seen on or before this day
OUT['chronology_L30'] = chron

# ---------------------------------------------------------------- (c) statement-validity trace, primary arm
R = Safe(open(REVAL, 'rb')).load()
arm = R['native']['primary|viii_reconcile']
cert = arm['cert']
TAU_F, TAU_N, AMAX, NMIN = 0.005, 0.05, 60, 500
benign = {'2019-12': 6120, '2020-01': 49, '2020-02': 62, '2020-03': 3577, '2020-04': 5201, '2020-05': 6121, '2020-06': 8182,
          '2020-07': 6392, '2020-08': 2514, '2020-09': 4198}
last_day = lambda mm: dn(str((pd.Period(mm, 'M').end_time).date()))
models = sorted(chron.keys())
def model_at(t):
    return max(u for u in models if dn(u) <= t)
trace = []
for t in range(dn('2020-03-01'), dn('2020-09-30') + 1):
    u = model_at(t); c = chron[u]; cm = c['cal_month']
    srcF = [(last_day(cm), cp_upper(c['k_005'], benign[cm]), 'cal ' + cm)]
    srcN = []
    for mm, v in cert.items():
        if v['avail'] <= t:
            if v['fpr_ub'] is not None:
                srcF.append((v['last'], v['fpr_ub'], mm))
            if v['fnr_ub'] is not None:
                srcN.append((v['last'], v['fnr_ub'], mm))
    lf, uf, nf = max(srcF); ln, un, nn = max(srcN)
    ok = (uf <= TAU_F) and (t - lf <= AMAX) and (un <= TAU_N) and (t - ln <= AMAX)
    why = [] if ok else [w for w, cond in (('FPR bound stale', t - lf > AMAX), ('FPR bound above tolerance', uf > TAU_F),
                                           ('FNR bound stale', t - ln > AMAX), ('FNR bound above tolerance', un > TAU_N)) if cond]
    trace.append(dict(day=ds(t), model=u, fpr_src=nf, fpr_age=t - lf, fpr_ub=100 * uf, fnr_src=nn, fnr_age=t - ln, fnr_ub=100 * un,
                      valid=ok, why=';'.join(why)))
# per-day issued findings (all Dated test findings, from the ISS records' day field)
days = collections.Counter(e['day'] for q, e in recs if e.get('t') == 'ISS')
segs = []
for d in trace:
    key = (d['valid'], d['why'], d['fpr_src'], d['fnr_src'], d['model'])
    if segs and segs[-1]['key'] == key and dn(d['day']) == dn(segs[-1]['end']) + 1:
        s = segs[-1]; s['end'] = d['day']; s['n'] += days[d['day']]
        s['fpr_age'][1] = d['fpr_age']; s['fnr_age'][1] = d['fnr_age']
    else:
        segs.append(dict(key=key, start=d['day'], end=d['day'], n=days[d['day']], valid=d['valid'], why=d['why'], model=d['model'],
                         fpr_src=d['fpr_src'], fpr_ub=round(d['fpr_ub'], 3), fpr_age=[d['fpr_age'], d['fpr_age']],
                         fnr_src=d['fnr_src'], fnr_ub=round(d['fnr_ub'], 3), fnr_age=[d['fnr_age'], d['fnr_age']]))
for s in segs:
    s.pop('key')
OUT['validity_segments'] = segs
OUT['invalid_findings'] = int(sum(s['n'] for s in segs if not s['valid']))
OUT['valid_findings'] = int(sum(s['n'] for s in segs if s['valid']))
OUT['check_against_sim'] = dict(screening_only_no_abstention=R['native']['primary|a2_cert']['scr_at_issue'],
                                evaluative_no_abstention=R['native']['primary|a2_cert']['iss_at_issue'])

# ---------------------------------------------------------------- (d) evaluative exposure under daily re-checking (renewal semantics)
# E^ev = 90 = 3 wrong evaluative findings x 30 days (L = 30, no review in (viii)). Monthly means of U^ev locate them:
mu = arm['monthly_Uev']; days_in = {'2020-03': 31, '2020-04': 30, '2020-05': 31, '2020-06': 30, '2020-07': 31, '2020-08': 31, '2020-09': 30}
fd = {mm: round(mu[mm] * days_in[mm]) for mm in mu}
OUT['wrong_eval_finding_days_by_month'] = fd
oct_days = arm['E_ev'] - sum(fd.values())
OUT['wrong_eval_finding_days_october'] = oct_days
# exactly one wrong evaluative finding was issued in September (25 Sep days + 5 Oct days = 30); statements are invalid
# from 30 Sep (August FPR bound above tolerance) until the September certificate on 30 Oct, so under daily re-checking it
# leaves the evaluative state on 30 Sep: it keeps 24 of its 30 days. The two May findings lie wholly in valid days.
OUT['E_ev_daily_recheck'] = arm['E_ev'] - (1 + oct_days)
json.dump(OUT, open(OUTF, 'w'), indent=1, default=str)
print(json.dumps({k: v for k, v in OUT.items() if k not in ('chronology_L30',)}, indent=1, default=str)[:6000])
for u, c in chron.items():
    print(u, c)
