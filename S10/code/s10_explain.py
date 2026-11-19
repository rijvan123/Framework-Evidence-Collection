#!/usr/bin/env python3
"""Explanations (S7 Part 7; S6 Block 11) and issuance records (Algorithm 3) for the evidentiary model f0:
grouped TreeSHAP importance, local-accuracy check, seed stability (KB11), group-deletion faithfulness, gain importance,
LR coefficient mass per group; ISS records for every Dated 2020 finding + monthly anchors; V2/V3 verifier.
Output: out/explain.json, cache/iss_expected.npz"""
import json, time, pickle, hashlib
import numpy as np, pandas as pd, lightgbm as lgb
import s10_common as C

t0 = time.perf_counter()
m = C.load_meta(); X = C.load_X(); y = m['y'].to_numpy().astype(int); sp = m['split'].to_numpy(); mo = m['month'].to_numpy()
store = C.Store()
boosters = {}
for s in C.MODEL_SEEDS:
    meta = json.load(open(f'{C.CACHE}/scores/lgbm_trace_s{s}.json'))
    boosters[s] = lgb.Booster(model_str=store.get(meta['model_obj']).decode())
f0 = boosters[11]
cal = np.where(sp == 'cal')[0]
s_cal = f0.predict(np.asarray(X[cal]), raw_score=True)
theta0, kst = C.certified_threshold(s_cal[y[cal] == 0], 0.001)
GI = [(a, b) for _, a, b in C.GROUPS]


def grouped(contrib):
    return np.stack([contrib[:, a:b].sum(1) for a, b in GI], axis=1), contrib[:, -1]


# ---------------------------------------------------------------- sample for importance / stability (Mar..Sep, stratified)
rng = np.random.default_rng(11); samp = []
for mm in C.CERT_MONTHS:
    for c in (0, 1):
        pool = np.where((sp == 'test') & (mo == mm) & (y == c))[0]; samp.append(rng.choice(pool, min(430, len(pool)), replace=False))
samp = np.sort(np.concatenate(samp)); Xs = np.asarray(X[samp])
G = {}; base = {}
t = time.perf_counter()
for s, b in boosters.items():
    G[s], base[s] = grouped(b.predict(Xs, pred_contrib=True))
shap_s = time.perf_counter() - t
z0 = f0.predict(Xs, raw_score=True)
resid = np.abs(G[11].sum(1) + base[11] - z0)
imp = dict(mean_abs={g: float(np.mean(np.abs(G[11][:, j]))) for j, (g, _, _) in enumerate(C.GROUPS)},
           mean_signed_mal={g: float(np.mean(G[11][y[samp] == 1, j])) for j, (g, _, _) in enumerate(C.GROUPS)},
           mean_signed_ben={g: float(np.mean(G[11][y[samp] == 0, j])) for j, (g, _, _) in enumerate(C.GROUPS)},
           by_month={mm: {g: float(np.mean(np.abs(G[11][mo[samp] == mm, j]))) for j, (g, _, _) in enumerate(C.GROUPS)} for mm in C.CERT_MONTHS})
# seed stability of the top-3 groups (mean pairwise Jaccard over the 5 seeds) vs correctness (KB11)
top3 = {s: np.argsort(-np.abs(G[s]), axis=1)[:, :3] for s in G}
pairs = [(a, b) for i, a in enumerate(C.MODEL_SEEDS) for b in C.MODEL_SEEDS[i + 1:]]
jac = np.zeros(len(samp))
for a, b in pairs:
    for k in range(len(samp)):
        A = set(top3[a][k]); B = set(top3[b][k]); jac[k] += len(A & B) / len(A | B)
jac /= len(pairs)
correct = (z0 > theta0).astype(int) == y[samp]
delta = C.cliffs_delta(jac[correct], jac[~correct])
KB11 = dict(mean_jaccard_correct=float(jac[correct].mean()), mean_jaccard_wrong=float(jac[~correct].mean()), n_wrong=int((~correct).sum()),
            cliffs_delta=delta, gate=bool(abs(delta) >= 0.147))
# group-deletion faithfulness: replace a group with its training-window median, measure |delta margin|
med = np.median(np.asarray(X[np.where(sp == 'train')[0]]), axis=0)
sub = np.arange(0, len(samp), max(1, len(samp) // 1000))[:1000]; dm = np.zeros((len(sub), 9))
for j, (a, b) in enumerate(GI):
    Xd = Xs[sub].copy(); Xd[:, a:b] = med[a:b]; dm[:, j] = np.abs(f0.predict(Xd, raw_score=True) - z0[sub])
from scipy.stats import spearmanr
rhos = [spearmanr(np.abs(G[11][sub][k]), dm[k]).statistic for k in range(len(sub))]
faith = dict(mean_spearman=float(np.nanmean(rhos)), median_spearman=float(np.nanmedian(rhos)),
             mean_abs_delta_margin={g: float(dm[:, j].mean()) for j, (g, _, _) in enumerate(C.GROUPS)})
# gain importance (f0) and top features
gain = f0.feature_importance('gain'); gsum = {g: float(gain[a:b].sum() / gain.sum()) for g, a, b in C.GROUPS}
names = []
for j in np.argsort(-gain)[:25]:
    g = next(g for g, a, b in C.GROUPS if a <= j < b); names.append(dict(index=int(j), group=g, offset=int(j - dict((g_, a) for g_, a, _ in C.GROUPS)[g]),
                                                                         gain_share=float(gain[j] / gain.sum())))
# LR coefficient mass per group (signed log1p + standardised inputs)
lr_meta = json.load(open(f'{C.CACHE}/scores/lr_s0.json')); lr = pickle.loads(store.get(lr_meta['model_obj']))
coef = np.abs(lr.m.coef_[0]); lr_group = {g: float(coef[a:b].sum() / coef.sum()) for g, a, b in C.GROUPS}
# ---------------------------------------------------------------- ISS records for every Dated 2020 finding (f0, theta0)
te = C.stream_order(m, (sp == 'test'))
p1c = 1 / (1 + np.exp(-s_cal)); acal = {c: np.sort(np.where(c == 1, 1 - p1c, p1c)[y[cal] == c]) for c in (0, 1)}
yh_cal = (s_cal > theta0).astype(int)
def credf(sv, yh):
    p1 = 1 / (1 + np.exp(-sv)); out = np.empty(len(sv))
    for c in (0, 1):
        sel = yh == c; a = np.where(c == 1, 1 - p1[sel], p1[sel]); ac = acal[c]
        out[sel] = (1 + (len(ac) - np.searchsorted(ac, a, side='left'))) / (1 + len(ac))
    return out
cr_cal = np.sort(credf(s_cal, yh_cal)); kappa = float(cr_cal[int(np.floor(0.05 * len(cr_cal)))])
meta0 = json.load(open(f'{C.CACHE}/scores/lgbm_trace_s11.json')); model_id = meta0['ident']; model_obj = meta0['model_obj']
vh_all = np.load(f'{C.CACHE}/vh.npy', allow_pickle=True)
cert_rec = dict(t='CERT', kind='calibration', model=model_id, month='2019-12', n_b=int(np.sum(y[cal] == 0)), fp=int(np.sum((s_cal > theta0) & (y[cal] == 0))),
                n_m=int(np.sum(y[cal] == 1)), fn=int(np.sum((s_cal <= theta0) & (y[cal] == 1))), tau=C.f32hex(0.001), conf='0.95 one-sided CP')
cert_rec['fpr_ub'] = C.f32hex(C.cp_upper(cert_rec['fp'], cert_rec['n_b'])); cert_rec['fnr_ub'] = C.f32hex(C.cp_upper(cert_rec['fn'], cert_rec['n_m']))
q_c, _, cert_head = C.ledger_append([cert_rec, dict(t='CAL', model=model_id, theta=C.f32hex(theta0), kstar=kst, kappa=C.f32hex(kappa),
                                                    cal_root=C.merkle_root([bytes.fromhex(m['sha'].iat[i]) for i in sorted(cal, key=lambda i: m['sha'].iat[i])]).hex())],
                                    epoch='issuance-setup')[0]
cert_id = hashlib.sha256(C.enc(cert_rec)).hexdigest()
t = time.perf_counter(); iss_n = 0; exp_scores = {}; sh_t = 0.0
for mm in C.TEST_MONTHS:
    rows = te[mo[te] == mm]; recs = []
    for s0 in range(0, len(rows), 5000):
        blk = rows[s0:s0 + 5000]; Xb = np.asarray(X[blk]); zb = f0.predict(Xb, raw_score=True)
        tt = time.perf_counter(); cb = f0.predict(Xb, pred_contrib=True); sh_t += time.perf_counter() - tt
        Gb, b0 = grouped(cb); rb = np.abs(Gb.sum(1) + b0 - zb); yhb = (zb > theta0).astype(int); crb = credf(zb, yhb)
        for k, i in enumerate(blk):
            order = np.argsort(-np.abs(Gb[k]))[:5]
            st_ = 'ABS' if crb[k] < kappa else 'ISS'
            recs.append(dict(t='ISS', sid=m['sha'].iat[i], vh=str(vh_all[i]), model=model_id, obj=model_obj, thr=C.f32hex(theta0), s=C.f32hex(zb[k]),
                             s64=np.float64(zb[k]).astype('>f8').tobytes().hex(), yhat=int(yhb[k]), cred=C.f32hex(crb[k]), cert=cert_id,
                             xg=[[int(g), C.f32hex(Gb[k, g])] for g in order], b0=C.f32hex(b0[k]), res=C.f32hex(rb[k]), st=st_, day=str(m['day'].iat[i].date())))
            exp_scores[int(i)] = float(zb[k])
    C.ledger_append(recs, epoch=f'iss-{mm}'); C.ledger_anchor(f'iss-{mm}'); iss_n += len(recs)
    print('ISS', mm, len(recs), flush=True)
iss_s = time.perf_counter() - t
np.savez(f'{C.CACHE}/iss_expected.npz', idx=np.array(list(exp_scores.keys())), s=np.array(list(exp_scores.values())))
# ---------------------------------------------------------------- V1, V2, V3 on the main ledger
v1 = C.verify_main_ledger()
t = time.perf_counter(); refs = 0; bad = 0
with open(C.MAIN_LEDGER) as f:
    for L in f:
        r = json.loads(json.loads(L)['e'])
        o = r.get('obj') or r.get('model_obj')
        if r.get('t') == 'MOD' and o:
            refs += 1
            try:
                store.get(o)
            except Exception:
                bad += 1
v2 = dict(objects_checked=refs, failures=bad, seconds=round(time.perf_counter() - t, 2))
# V3: re-execute 1,000 random ISS records from the ledger (vector hash, margin bit-identity, SHAP local accuracy)
iss_lines = []
with open(C.MAIN_LEDGER) as f:
    for L in f:
        d = json.loads(L)
        if '"t":"ISS"' in d['e']:
            iss_lines.append(d['e'])
pick = np.random.default_rng(5).choice(len(iss_lines), 1000, replace=False)
sha2row = dict(zip(m['sha'].to_numpy(), range(len(m)))); models = {}
ok_vh = ok_s = ok_res = 0; t = time.perf_counter()
for k in pick:
    r = json.loads(iss_lines[k]); i = sha2row[r['sid']]
    ok_vh += C.vec_hash(X[i]) == r['vh']
    if r['obj'] not in models:
        models[r['obj']] = lgb.Booster(model_str=store.get(r['obj']).decode())
    b = models[r['obj']]; xi = np.asarray(X[i:i + 1])
    z = b.predict(xi, raw_score=True)[0]
    ok_s += np.float64(z).astype('>f8').tobytes().hex() == r['s64']
    cb = b.predict(xi, pred_contrib=True)[0]; ok_res += abs(cb.sum() - z) <= 1e-9
v3 = dict(n=1000, vector_hash_match=int(ok_vh), margin_bit_identical=int(ok_s), shap_local_accuracy_ok=int(ok_res), seconds=round(time.perf_counter() - t, 2))
out = dict(theta0=theta0, kstar=kst, kappa=kappa, sample=len(samp), shap_seconds_5models=shap_s, shap_ms_per_finding=1000 * sh_t / iss_n,
           local_accuracy_max_resid=float(resid.max()), importance=imp, KB11=KB11, faithfulness=faith, gain_group=gsum, top_features=names,
           lr_group=lr_group, iss_records=iss_n, iss_seconds=iss_s, abstained=None, V1=v1, V2=v2, V3=v3, seconds=round(time.perf_counter() - t0, 1))
C.jdump(out, f'{C.OUT}/explain.json'); print(json.dumps({k: out[k] for k in ('KB11', 'V1', 'V2', 'V3', 'local_accuracy_max_resid', 'gain_group')}, indent=1, default=str))
