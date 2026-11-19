"""Markdown renderings of the paper's result tables (Tables 1-17) from the run outputs in ``out/``.

Every table is rebuilt from the JSON files written by the experiment scripts; nothing is typed in by hand.
A table whose inputs are missing is skipped with a message. Values are those of the run that produced the
outputs (measured on that machine); published values in Table 15 come from ``results/published_baselines.json``.
"""
from __future__ import annotations

import math

from ..models.zoo import DISPLAY
from ..utils import load_json, log

MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


# ------------------------------------------------------------------ formatting helpers
def _isnum(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v is not None and math.isfinite(v)


def pct(v, nd: int = 2) -> str:
    return f'{100 * v:.{nd}f}' if _isnum(v) else '—'


def num(v, nd: int = 3) -> str:
    if isinstance(v, bool):
        return 'yes' if v else 'no'
    if isinstance(v, int):
        return f'{v:,}'
    return f'{v:.{nd}f}' if _isnum(v) else '—'


def ci_pct(ci, nd: int = 2) -> str:
    if not ci or ci[0] is None or ci[1] is None:
        return ''
    return f' [{pct(ci[0], nd)}, {pct(ci[1], nd)}]'


def mm_pct(agg: dict, nd: int = 2) -> str:
    """seed mean (min-max) in percent."""
    if not agg or agg.get('mean') is None:
        return '—'
    return f'{pct(agg["mean"], nd)} ({pct(agg["min"], nd)}–{pct(agg["max"], nd)})'


def month_label(mo: str) -> str:
    y, m = mo.split('-')
    return f'{MONTH_NAMES[int(m) - 1]} {y}'


def compact(v, depth: int = 0) -> str:
    """Short rendering of a measured value of the register."""
    if v is None:
        return '—'
    if isinstance(v, bool):
        return 'yes' if v else 'no'
    if isinstance(v, int):
        return f'{v:,}'
    if isinstance(v, float):
        return f'{v:.4g}' if math.isfinite(v) else '—'
    if isinstance(v, str):
        return v
    if isinstance(v, (list, tuple)):
        return '[' + ', '.join(compact(x, depth + 1) for x in v[:6]) + (', …' if len(v) > 6 else '') + ']'
    if isinstance(v, dict):
        if depth > 1:
            return '{…}'
        items = [(k, x) for k, x in v.items() if not isinstance(x, (list, dict)) or depth == 0]
        return '; '.join(f'{k} {compact(x, depth + 1)}' for k, x in items[:8])
    return str(v)


def md_table(header: list[str], rows: list[list]) -> str:
    out = ['| ' + ' | '.join(header) + ' |', '|' + '---|' * len(header)]
    for r in rows:
        out.append('| ' + ' | '.join('' if c is None else str(c) for c in r) + ' |')
    return '\n'.join(out)


def disp(key: str) -> str:
    return DISPLAY.get(key, key)


# ------------------------------------------------------------------ table builders
def t01(O, cfg):
    e0 = O['e0_intake']
    st, sp = e0['screen']['strata'], e0['screen']['splits']
    role = {'Dated': 'primary stream (train / calibrate / test)', 'PreWindow': 'benign first seen before the window; PreWindow arm only',
            'Placeholder': 'benign with placeholder timestamp on a spike day; censored (KB5)',
            'Bulk': 'benign with batch timestamp on a spike day; censored (KB5)', 'SpikeMal': 'malware on spike days; spike-day analysis only',
            'Quarantine': 'unparseable identifier or failed invariant; excluded', 'PostWindow': 'first seen after the window'}
    rows = [[k, num(v['benign']), num(v['malware']), role.get(k, '')] for k, v in st.items() if v['benign'] or v['malware']]
    tb = sum(v['benign'] for v in st.values())
    tm = sum(v['malware'] for v in st.values())
    rows.append(['Total', num(tb), num(tm), f'{tb + tm:,} files; {e0["duplicates"]["duplicate_groups"]} identical-vector groups logged (DUP)'])
    s = cfg['screen']
    rows2 = [[f'Train: Dated, {s["window_start"]} to {s["train_end"]} (excl.)', num(sp['train']['benign']), num(sp['train']['malware']),
              num(sp['train']['benign'] + sp['train']['malware'])],
             [f'Calibrate: Dated, {s["calibration_month"]}', num(sp['calibration']['benign']), num(sp['calibration']['malware']),
              num(sp['calibration']['benign'] + sp['calibration']['malware'])],
             [f'Test: Dated, {s["test_months"][0]} to {s["test_months"][1]}', num(sp['test']['benign']), num(sp['test']['malware']),
              num(sp['test']['benign'] + sp['test']['malware'])]]
    body = (md_table(['Stratum', 'Benign', 'Malware', 'Role'], rows) + '\n\n' +
            md_table(['Split', 'Benign', 'Malware', 'Files'], rows2))
    note = (f'Spike rule: all-sample daily counts, median + {s["spike_k"]}·MAD; certificates and FPR-dependent metrics use '
            f'{s["certify_months"][0]} to {s["certify_months"][1]} (months with ≥ {s["n_min_benign"]} dated benign files).')
    return 'table01_strata', 'Table 1. Strata and the temporal split', body, note, ['e0_intake']


def t01b(O, cfg):
    R = O['e15_register']
    rows = [[r['id'], r['statement'], compact(r['measured']), r['outcome'] or 'not run'] for r in R['register']]
    note = f'Decision: {R.get("decision")} — {R.get("decision_text") or ""}'
    return 'table01b_register', 'Table 1b. Pre-registered register: measured outcomes', md_table(['ID', 'Statement', 'Measured', 'Outcome'], rows), note, ['e15_register']


def t02(O, cfg):
    e1 = O['e1_metrics']
    rows = []
    for key, z in e1['zoo'].items():
        a = z['agg']
        if len(z['seeds']) > 1:
            cell = lambda f, nd=2: mm_pct(a.get(f), nd)
            aut = (f'{a["aut"]["mean"]:.3f} ({a["aut"]["min"]:.3f}–{a["aut"]["max"]:.3f})' if a['aut']['mean'] is not None else '—')
        else:
            ci = a.get('ci', {})
            cimap = {'prec_pi': 'precision_pi_prec'}

            def cell(f, nd=2, ci=ci, a=a):
                v = a.get(f, {}).get('mean')
                if f == 'auc':
                    return pct(v, 3) + ci_pct(a.get('auc_ci'), 3)
                return pct(v, nd) + ci_pct(ci.get(cimap.get(f, f)), nd)
            aut = f'{a["aut"]["mean"]:.3f}' if a['aut']['mean'] is not None else '—'
        rows.append([z['display'], len(z['seeds']), cell('auc', 3) if len(z['seeds']) > 1 else cell('auc'), cell('aucpr'), cell('f1_pi'),
                     cell('mcc_pi'), cell('prec_pi'), cell('tpr'), cell('fpr', 3), cell('fnr'), aut])
    pi_r, pi_p = cfg['prevalence']['report'], cfg['prevalence']['precision']
    hdr = ['Model', 'Seeds', 'AUC-ROC (%)', f'AUC-PR @π={pi_r:.0%} (%)', f'F1 @π={pi_r:.0%} (%)', f'MCC @π={pi_r:.0%} (%)',
           f'Precision @π={pi_p:.0%} (%)', 'TPR (%)', 'FPR (%)', 'FNR (%)', 'AUT(F1@π)']
    tau = cfg['thresholds']['certified_tau'][0]
    note = (f'Pooled {cfg["screen"]["certify_months"][0]} to {cfg["screen"]["certify_months"][1]}, Dated stratum; threshold certified on '
            f'{cfg["screen"]["calibration_month"]} at τ_FPR = {tau:g} (one-sided 95% Clopper–Pearson). Multi-seed models: seed mean '
            '(min–max); single fits: point estimate [95% stratified bootstrap CI; DeLong for AUC]. π-dependent cells use Eq. (70).')
    return 'table02_models', 'Table 2. Model zoo on the pooled test stream at the CP-certified threshold', md_table(hdr, rows), note, ['e1_metrics']


def t03(O, cfg):
    e1 = O['e1_metrics']
    rows = []
    cal = cfg['screen']['calibration_month']
    for p, v in e1['f0_monthly'].items():
        if p == 'pooled':
            continue
        m, ci = v['metrics'], v['ci']
        rep = v.get('fpr_reportable', True)
        rows.append([month_label(p) + (' (cal)' if p == cal else ''), num(v['benign']), num(v['malware']), num(m['fn']), num(m['fp']),
                     pct(m['fnr']) + ci_pct(ci.get('fnr')),
                     (pct(m['fpr'], 3) + ci_pct(ci.get('fpr'), 3)) if rep else f'— (n < {cfg["screen"]["report_min_benign"]})',
                     (pct(m['f1_pi']) + ci_pct(ci.get('f1_pi'))) if rep else '—',
                     (pct(m['precision_pi_prec']) + ci_pct(ci.get('precision_pi_prec'))) if rep else '—',
                     pct(v.get('auc'), 3) + ci_pct(v.get('auc_ci'), 3), pct(m['mcc_native']) + ci_pct(ci.get('mcc_native'))])
    pi_r, pi_p = cfg['prevalence']['report'], cfg['prevalence']['precision']
    hdr = ['Month', 'Benign', 'Malware', 'FN', 'FP', 'FNR (%)', 'FPR (%)', f'F1 @π={pi_r:.0%} (%)', f'Precision @π={pi_p:.0%} (%)',
           'AUC-ROC (%)', 'MCC native (%)']
    th = O['e1_metrics_raw']['thresholds'][e1['f0'][0]][str(e1['f0'][1])][e1['primary_rule']]
    note = f'f₀ = {disp(e1["f0"][0])}, seed {e1["f0"][1]}; θ = {th["theta"]:.3f} (margin, k* = {th.get("k_star")}). 95% bootstrap CIs in brackets.'
    return 'table03_f0_monthly', 'Table 3. Evidentiary detector f₀ by month at the certified threshold', md_table(hdr, rows), note, ['e1_metrics', 'e1_metrics_raw']


def t04(O, cfg):
    e2 = O['e2_certificates']
    rules = list(e2['certificates'])
    r0, r1 = rules[0], rules[1] if len(rules) > 1 else rules[0]
    s1 = e2['svr'][r1]
    rows = []
    for p in e2['certificates'][r0]:
        c0, c1 = e2['certificates'][r0][p], e2['certificates'][r1][p]
        f = lambda c: f'{c["fp"]}/{c["n_b"]:,} = {pct(c["fpr"], 3)} (≤ {pct(c["fpr_ub"], 3)})'
        g = lambda c: f'{pct(c["fnr"])} (≤ {pct(c["fnr_ub"])})'
        valid = ('yes' if c1['valid'] else 'no') if c1.get('in_certify_months') else 'n/a'
        rows.append([month_label(p), f(c0), g(c0), f(c1), g(c1), valid])
    t0, t1 = e2['thresholds'][r0], e2['thresholds'][r1]
    hdr = ['Month', f'θ@{r0[2:]}: FP/benign = FPR % (95% CP upper)', f'θ@{r0[2:]}: FNR % (upper)', f'θ@{r1[2:]}: FP/benign = FPR % (upper)',
           f'θ@{r1[2:]}: FNR % (upper)', f'θ@{r1[2:]} valid at ({s1["tau_fpr"]:g}, {s1["tau_fnr"]:g})']
    body = md_table(hdr, rows)
    viol = O['e1_metrics'].get('violations', {})
    if viol:
        vr = []
        for r, v in viol.items():
            kind = 'empirical quantile' if r.startswith('emp') else 'CP-certified'
            bym = '; '.join(f'{disp(k)} {n}' for k, n in sorted(v['by_model'].items(), key=lambda kv: -kv[1]) if n)
            vr.append([f'{kind}, τ = {v["tau"]:g}', num(v['cells']), f'{v["above"]} ({pct(v["above"] / v["cells"], 1) if v["cells"] else "—"}%)',
                       num(v['cp_lower_above']), bym or '—'])
        body += '\n\n' + md_table(['Threshold rule (fitted on the calibration month)', 'Model×month cells', 'Realised FPR > τ',
                                   'CP lower bound > τ', 'Cells above τ by model'], vr)
    note = (f'θ@{r0[2:]} = {t0["theta"]:.3f} (k* = {t0["k_star"]}), θ@{r1[2:]} = {t1["theta"]:.3f} (k* = {t1["k_star"]}). SVR at θ@{r1[2:]}: '
            f'{s1["valid_months"]}/{s1["months"]} (FPR-only {s1["fpr_only_valid"]}/{s1["months"]}; FNR-only {s1["fnr_only_valid"]}/{s1["fnr_months"]}). '
            f'KS1 met: {e2["KS1"]["met"]}.')
    return 'table04_certificates', 'Table 4. Retrospective time-indexed error certificates and target-FPR violations by threshold rule', body, note, ['e2_certificates', 'e1_metrics']


def t05(O, cfg):
    e2 = O['e2_certificates']
    r1 = [[month_label(k.split(':')[1]), v['stratum'], num(v['dated_benign']), pct(v['fpr_dated']), num(v['censored_benign']),
           f'{pct(v["fpr_censored"], 3)} (≤ {pct(v["fpr_censored_ub"], 3)})', pct(v['fpr_pooled'], 3), pct(v['shift'], 3),
           pct(v['bootstrap_half_width'], 3)] for k, v in e2['censored'].items()]
    r2 = [[month_label(k), num(v['files']), pct(v['fnr_spike']), pct(v['fnr_dated']), pct(v['fnr_pooled'])] for k, v in e2['spike_malware'].items()]
    r3 = []
    for mo, v in e2['k_sensitivity'].items():
        for lab, key in (('spike rule, primary k', 'primary'), ('spike rule, sensitivity k', 'sensitivity')):
            x = v[key]
            r3.append([f'{month_label(mo)}: {lab}', num(x['files']), pct(x['fnr']), pct(x['fpr'], 3), pct(x['f1_native'])])
    body = (md_table(['Month', 'Censored stratum', 'Dated benign', 'FPR dated (%)', 'Censored benign', 'FPR censored (%) (95% CP upper)',
                      'FPR pooled (%)', 'Shift (pp)', 'Bootstrap half-width (pp)'], r1) + '\n\n' +
            md_table(['Month', 'SpikeMal files', 'FNR spike-day malware (%)', 'FNR dated (%)', 'FNR pooled (%)'], r2) + '\n\n' +
            md_table(['Rule', 'Files', 'FNR (%)', 'FPR (%)', 'F1 native (%)'], r3))
    kb5 = e2['KB5']
    note = f'KB5 met: {kb5["met"]}' + ('; degenerate (zero bootstrap half-width), reported as inconclusive.' if kb5.get('degenerate') else '.')
    return 'table05_censored', 'Table 5. Censored benign strata, spike-day malware and the spike-rule sensitivity (f₀)', body, note, ['e2_certificates']


def t06(O, cfg):
    st = O['e1_metrics']['streams']
    pis = [str(p) for p in cfg['prevalence']['streams']]
    rows = []
    for mo, v in st.items():
        r = [month_label(mo)]
        for p in pis:
            c = v.get(p)
            r.append(f'{pct(c["mean"])} [{pct(c["lo"])}, {pct(c["hi"])}] / {pct(c["analytic"])}' if c else '—')
        d = v.get('default', {})
        r += [pct(d.get('0.001')), pct(d.get('0.01'))]
        rows.append(r)
    hdr = ['Month'] + [f'π = {float(p):.0%}' for p in pis] + ['Default θ: Prec @π=0.1%', 'Default θ: Prec @π=1%']
    cells = [c for v in st.values() for p in pis if isinstance(v.get(p), dict) for c in [v[p]]]
    out = sum(bool(c.get('outside')) for c in cells)
    note = (f'Certified-threshold columns: mean [2.5, 97.5 percentile] over {len(cfg["seeds"]["streams"])} prevalence-resampled streams / '
            f'analytic Eq. (55) from the month\'s TPR and FPR. Analytic value outside the interval in {out} of {len(cells)} cells.')
    return 'table06_precision', 'Table 6. Precision (%) under deployment prevalence π: measured streams versus Eq. (55)', md_table(hdr, rows), note, ['e1_metrics']


def t07(O, cfg):
    e3 = O['e3_calibration']
    cost = e3['cost']
    key100 = next((k for k in cost if k.endswith('_100') and k.startswith(str(cfg['thresholds']['cost_pis'][0]))), None)
    months = [m for m in e3['months'] if m != cfg['screen']['calibration_month']]
    rows = []
    for i, mo in enumerate(months):
        v = e3['months'][mo]
        ec = (f'{cost[key100]["ec_star"][i] * 1e3:.1f} / {cost[key100]["ec_half"][i] * 1e3:.1f}' if key100 else '—')
        rows.append([month_label(mo), pct(v['ece_raw']), pct(v['ece_iso']), pct(v['ece_platt']),
                     f'{v["brier_iso_0.01"] * 1e3:.2f} / {v["brier_prior_0.01"] * 1e3:.2f}',
                     f'{v["brier_iso_0.001"] * 1e3:.2f} / {v["brier_prior_0.001"] * 1e3:.2f}', ec, f'{v["cllr"]:.3f}'])
    r2 = [[f'{c["pi"]:.1%}', c['ratio'], f'{c["mean_star"] * 1e3:.2f}', f'{c["mean_half"] * 1e3:.2f}',
           f'{c["months_star_lower"]}/{len(c["ec_star"])}', num(c['p'])] for c in cost.values()]
    body = (md_table(['Month', 'ECE raw sigmoid (%)', 'ECE isotonic (%)', 'ECE Platt (%)', 'Brier ×10³ @π=1%: iso / prior-shift',
                      'Brier ×10³ @π=0.1%: iso / prior-shift', 'EC ×10³ @π=1%, C_FN/C_FP = 100: τ* / 0.5', 'Cllr'], rows) + '\n\n' +
            md_table(['π', 'C_FN/C_FP', 'mean EC(τ*) ×10³', 'mean EC(0.5) ×10³', 'months τ* lower', 'Wilcoxon p'], r2))
    p4 = e3['P4']
    note = (f'Calibrators fitted on {cfg["screen"]["calibration_month"]} (π_cal = {e3["pi_cal"]:.3f}). Isotonic − raw ECE: '
            f'{pct(p4["iso_minus_raw_mean"])} pp{ci_pct(p4["ci"])} (P4 falsified: {p4["falsified"]}). H10: ρ(month, ECE) = '
            f'{e3["H10"]["rho"]:.2f} (p = {e3["H10"]["p"]:.2g}). KB12 triggered: {e3["KB12"]["triggered"]}.')
    return 'table07_calibration', 'Table 7. Calibration under drift, prior shift and cost-sensitive thresholds', body, note, ['e3_calibration']


def t08(O, cfg):
    b = O['e4_bias']
    parts = []
    if 'random' in b:
        r = b['random']
        rows = [[f'seed {x["seed"]}', pct(x['f1_pi']), pct(x['temporal_aut']), f'{(x["inflation"] or 0) * 100:+.2f}', pct(x['fnr']), pct(x['fpr'], 3)]
                for x in r['seeds']]
        rows.append(['mean [95% CI]', '', '', f'{r["inflation_mean"] * 100:+.2f}{ci_pct(r["inflation_ci"])}', '', ''])
        parts.append(md_table(['Arm', 'Random-split F1 @π (%)', 'Temporal AUT(F1@π) (%)', 'Inflation (pp)', 'Random-split FNR (%)',
                               'Random-split FPR (%)'], rows))
    if 'static' in b:
        s = b['static']
        rows = [[month_label(mo), pct(v['static_fnr']), pct(v['temporal_fnr']), pct(v['static_fpr'], 3), pct(v['temporal_fpr'], 3),
                 'yes' if v['understates'] else 'no'] for mo, v in s['months'].items()]
        parts.append(md_table(['Month', 'Static 80:20 FNR (%)', 'Temporal FNR (%)', 'Static FPR (%)', 'Temporal FPR (%)', 'Static understates'], rows))
    rows = []
    if 'coff' in b:
        c = b['coff']
        rows.append(['Without COFF timestamp (feature 626), H9', f'AUT(F1@π) {pct(c["aut_f1_f0"])} → {pct(c["aut_f1"])}',
                     f'{c["delta_aut_f1"] * 100:+.2f} pp', 'met' if b.get('H9', {}).get('met') else 'not met'])
    if 'prewindow' in b:
        pw = b['prewindow']
        rows.append([f'+{pw["added_benign"]:,} PreWindow benign in training', f'pooled FNR {pct(pw["fnr_f0"])}% → {pct(pw["fnr"])}%; FPR {pw["fp"]}/{pw["n_benign"]:,}',
                     f'{(pw["fnr"] - pw["fnr_f0"]) * 100:+.2f} pp FNR', 'descriptive'])
    if rows:
        parts.append(md_table(['Variant', 'Effect', 'Δ', 'Outcome'], rows))
    if 'cv' in b:
        rows = [[disp(k), len(v['folds']), f'{pct(v["cv_mean"])} ({pct(v["cv_min"])}–{pct(v["cv_max"])})',
                 f'{pct(v["temporal_mean"])} ({pct(v["temporal_min"])}–{pct(v["temporal_max"])})',
                 f'{(v["cv_mean"] - v["temporal_mean"]) * 100:+.2f}' if _isnum(v['cv_mean']) and _isnum(v['temporal_mean']) else '—',
                 pct(v['cv_fnr']), pct(v['temporal_fnr']), pct(v['cv_fpr'], 3)] for k, v in b['cv'].items()]
        parts.append(md_table(['Model', 'CV folds', 'Random k-fold CV: F1 @π (%) mean (min–max)', 'Temporal months: F1 @π (%) mean (min–max)',
                               'Δ CV − temporal (pp)', 'CV FNR (%)', 'Temporal FNR (%)', 'CV FPR (%)'], rows))
    if 't0' in b:
        rows = []
        for k, v in b['t0'].items():
            var, key = k.split(':')
            rows.append([f'{var.replace("_", " + ")}, {disp(key)}', f'{v["train"]:,} train / {v["val"]:,} val; θ = {v["theta"]:.3f} (k = {v["k"]})',
                         f'{pct(v["fnr_jul_sep"][0])}–{pct(v["fnr_jul_sep"][1])}' if v.get('fnr_jul_sep') else '—',
                         f'{pct(v["fnr_range"][0])}–{pct(v["fnr_range"][1])}',
                         f'{pct(v["fpr_range"][0], 3)}–{pct(v["fpr_range"][1], 3)}' if v.get('fpr_range') else '—',
                         f'{v["months_fpr_above"]}/{len(v["months"])}', f'≤ {pct(v["max_unseen_fnr"])}', f'≤ {pct(v["max_seen_fnr"])}'])
        parts.append(md_table(['T0 replication (train < cut-off, 80:20 random split, empirical validation threshold)', 'Training / threshold',
                               'FNR Jul–Sep (%)', 'Monthly FNR (%)', 'Monthly FPR (%)', 'Months FPR > τ', 'Unseen-family FNR (%)',
                               'Seen-family FNR (%)'], rows))
    if 'leakage' in b:
        lk = b['leakage']
        names = {'zscore': 'z-score scaler', 'chi2': f'χ² selector ({cfg["models"]["select"]["chi2_k"]})', 'pca': f'PCA ({cfg["models"]["select"]["pca_var"]})'}
        rows = []
        for k, v in lk['arms'].items():
            m, f = k.split(':')
            rows.append([disp(m), names.get(f, f), f'{pct(v["auc_clean"], 3)} → {pct(v["auc_leaky"], 3)}', f'{pct(v["aucpr_clean"])} → {pct(v["aucpr_leaky"])}',
                         f'{pct(v["fnr_clean"])} → {pct(v["fnr_leaky"])}', f'{v["delta_auc"] * 100:+.3f}', f'{v["delong_p"]:.2g}'])
        parts.append(md_table(['Model', 'Pre-split fit', 'AUC-ROC (%) clean → leaky', 'AUC-PR @π (%) clean → leaky', 'FNR (%) clean → leaky',
                               'ΔAUC (pp)', 'DeLong p'], rows))
        lz = lk.get('lgbm_zscore')
        if lz:
            parts.append(f'LightGBM under clean versus leaky z-scaling: maximum absolute margin difference {lz["max_abs_margin_diff"]:.3g}; '
                         f'decision agreement {pct(lz["decision_agreement"], 3)}%.')
    if 'scaling' in b:
        rows = [[disp(k.split(':')[0]) if k.split(':')[0] != 'dt' else 'Decision tree', k.split(':')[1].replace('_', ' '),
                 f'{v["disagreements"]:,}/{v["n"]:,}', pct(v['agreement'], 3)] for k, v in b['scaling'].items()]
        parts.append(md_table(['Model', 'Comparison', 'Disagreements', 'Agreement (%)'], rows))
    crit = '; '.join(f'{k}: {compact(b[k])}' for k in ('P1', 'KB4', 'H9', 'P9') if k in b)
    return 'table08_bias', 'Table 8. Experimental-bias controls', '\n\n'.join(parts), crit, ['e4_bias']


def t09(O, cfg):
    e5 = O['e5_errors_drift']
    names = {'eq19_tau_1_32': 'Eq. (19) packing indicator, τ_p = 1/32', 'mass_top2_bins_gt_0p5': 'byte mass in the two highest entropy bins > 0.5'}
    rows = []
    for d, v in e5['entropy'].items():
        for err in ('FNR', 'FPR'):
            x = v[err]
            rows.append([names.get(d, d), err, f'{x["high_errors"]:,}/{x["high_n"]:,} = {pct(x["high_rate"], 3)}',
                         f'{x["low_errors"]:,}/{x["low_n"]:,} = {pct(x["low_rate"], 3)}',
                         f'{x["odds_ratio"]:.2f} [{x["ci"][0]:.2f}, {x["ci"][1]:.2f}]' if _isnum(x.get('odds_ratio')) else '—', f'{x["p"]:.2g}'])
    r2 = [[month_label(mo), num(v['unseen']), pct(v['fnr_unseen']), num(v['known']), pct(v['fnr_known'])] for mo, v in e5['families'].items()]
    df = e5['decay_families']
    r3 = [[x['family'], 'yes' if x['seen'] else 'no', num(x['files']), num(x['fn']), pct(x['fnr'], 1), pct(x['share'], 1)] for x in df['top']]
    if 'all' in df:
        a = df['all']
        r3.append(['all families', '', num(a['files']), num(a['fn']), pct(a['fnr'], 1), '100.0'])
    body = (md_table(['High-entropy definition', 'Error', 'High stratum: errors/n = %', 'Low stratum: errors/n = %', 'Odds ratio [95% CI]', 'Fisher p'], rows)
            + '\n\n' + md_table(['Month', 'Unseen-family malware', 'FNR unseen (%)', 'Known-family malware', 'FNR known (%)'], r2)
            + '\n\n' + md_table(['Family (decay months)', 'Seen in training', 'Malware files', 'False negatives', 'FNR (%)', 'Share of FN (%)'], r3))
    note = f'P10: {compact(e5["P10"])}. H3: {compact(e5["H3"])}.'
    return 'table09_errors', 'Table 9. Error structure of f₀: entropy strata, unseen versus known families, families behind the decay', body, note, ['e5_errors_drift']


def t10(O, cfg):
    e5, e6 = O['e5_errors_drift'], O.get('e6_monitor')
    rows = [[month_label(mo), f'{v["pooled"] * 1e3:.2f}', f'{v["benign"] * 1e3:.2f}' if _isnum(v.get('benign')) else '—',
             f'{v["malware"] * 1e3:.2f}' if _isnum(v.get('malware')) else '—', pct(v['fnr'])] for mo, v in e5['drift'].items()]
    parts = [md_table(['Month', '𝒟(t) ×10³ (bits)', 'benign-class 𝒟 ×10³', 'malware-class 𝒟 ×10³', 'FNR f₀ (%)'], rows)]
    note = f'P5: ρ = {e5["P5"]["rho"]:.2f} (p = {e5["P5"]["p"]:.2g}); falsified: {e5["P5"]["falsified"]}.'
    if e6:
        lab = {'c2st': 'C2ST AUC (T5)', 'ks': 'KS on margins (T1)', 'psi': 'mean PSI (T2)', 'cred': '1 − mean credibility (T3)'}
        rows = []
        for stat in ('c2st', 'ks', 'psi', 'cred'):
            for cls in ('0', '1'):
                lam = e6['lambda_'][cls][stat]
                rows.append([lab[stat], 'pred. benign' if cls == '0' else 'pred. malicious', f'{lam:.3f}',
                             f'{e6["exceed_counts"].get(f"{stat}_{cls}", 0)}/{e6["n_windows"]}'])
        parts.append(md_table(['Statistic', 'Class', 'λ (max over blocked null)', 'Test windows above λ'], rows))
        kt = e6['KT']
        rows = [['M8 rule (persistence, re-arm)', kt['alarms'], kt['alarm_days'][0] if kt['alarm_days'] else '—',
                 next((d for d in kt['alarm_days'] if d >= (kt['onset'] or '9999')), '— (none)')]]
        for dl, v in e6.get('aci', {}).items():
            rows.append([f'ACI, label delay {dl} d', v['alarms'], v['first'] or '—', v['first_after_onset'] or '—'])
        parts.append(md_table(['Signal', 'Alarms', 'First alarm', 'First alarm after onset'], rows))
        note += (f' Monitor: {e6["n_windows"]} weekly windows, {e6["windows_with_any"]} with an exceedance; onset {kt["onset"]}; '
                 f'false alarms in stable months: {compact(kt["false_alarms_stable"])}; KT kill met: {kt["kill_met"]}.')
    return 'table10_drift_monitor', 'Table 10. Feature drift and the label-free monitor', '\n\n'.join(parts), note, ['e5_errors_drift', 'e6_monitor']


def t11(O, cfg):
    e7 = O['e7_assurance']
    P = e7['primary']
    rows = []
    for k, v in P.items():
        ci = v.get('E_ev_ci') or [None, None]
        ce = v.get('E_ci') or [None, None]
        rows.append([v['label'], f'{v["E_ev"]:,.0f} [{ci[0]:,.0f}–{ci[1]:,.0f}]', f'{v["E"]:,.0f} [{ce[0]:,.0f}–{ce[1]:,.0f}]',
                     f'{v["ratio_to_viii"]:.2f}×' if _isnum(v.get('ratio_to_viii')) else '—', num(v['abstained']), num(v['screening']),
                     pct(v['coverage'], 1), num(v['reviews']), num(v['corrections']), pct(v['yield_']) if v['yield_'] is not None else '—',
                     num(v['harmful_auto'])])
    parts = [md_table(['Policy', 'E^ev_T, finding-days [95% CI]', 'E_T [95% CI]', 'E^ev / E^ev(viii)', 'Abstained at issue',
                       'Screening-only at issue', 'Evaluative coverage (%)', 'Reviews', 'Corrections by review', 'Yield (%)',
                       'Harmful auto-amendments'], rows)]
    from ..utils import day_string
    rows = [[day_string(u['day']), num(u['scope']), num(u['budget']), num(u['changes']), num(u['harmful']), pct(u['h_ub'], 3)]
            for u in e7['K1']['updates']]
    parts.append(md_table(['Update', 'In-scope findings N', 'Budget B', 'Verdict changes on full re-scoring', 'Harmful flips',
                           'CP-95% upper bound of h (%)'], rows))
    rows = [[day_string(f['update']), num(f['rescored']), num(f['abstained']), num(f['flips']), num(f['flips_abstained']),
             num(f['harmful_mal_to_ben']), num(f['harmful_ben_to_mal']), num(f['corrective'])] for f in e7.get('flips', [])]
    parts.append(md_table(['Update', 'Re-scored findings (incl. abstained)', 'Abstained at issue', 'Verdict flips', 'Flips among abstained',
                           'Harmful: malware → benign', 'Harmful: benign → malicious', 'Corrective flips'], rows))
    if e7.get('scenarios'):
        rows = []
        for k, v in e7['scenarios'].items():
            rel = lambda p: v[p].get('rel_vs_viii', {})
            rr = rel('trace')
            rows.append([k, num(v['trace']['issued_evaluative']), f'{v["viii"]["E_ev"]:,.0f}', f'{v["trace"]["E_ev"]:,.0f}',
                         f'{pct(rr.get("point"), 1)}{ci_pct(rr.get("ci"), 1)}', f'{v["vii_margin"]["E_ev"]:,.0f}',
                         f'{v["abl_noregion"]["E_ev"]:,.0f}', f'{v["K1"]["ok"]}/{v["K1"]["n"]} (changes: {v["K1"]["changes"]})',
                         f'harmful: {v["K2"]["harmful"]}', f'{v["retrain_only"]["E_ev"]:,.0f}', f'{v["frozen_none"]["E_ev"]:,.0f}'])
        parts.append(md_table(['Scenario', 'Issued as evaluative', 'E^ev (viii)', 'E^ev TRACE-PE', 'Rel. reduction vs (viii) (%) [CI]',
                               'E^ev (vii) margin', 'E^ev without region', 'K1', 'K2', 'E^ev retrain only', 'E^ev frozen'], rows))
    if e7.get('noise'):
        rows = [[f'{float(r):.1%}', f'{v["trace"]:,.1f}', f'{v["vii_margin"]:,.1f}', f'{v["vi_random"]:,.1f}', f'{v["trace_override"]:,.1f}',
                 f'{v["vii_margin_override"]:,.1f}', f'{v["viii"]:,.1f}'] for r, v in e7['noise'].items()]
        parts.append(md_table(['Analyst error r', 'TRACE-PE', '(vii) margin', '(vi) random', 'TRACE-PE, oracle overrides', '(vii), oracle overrides',
                               '(viii) no review'], rows))
    if e7.get('streams'):
        rows = [[f'{float(p):.0%}', f'{v["viii"]["mean"]:.1f} [{v["viii"]["lo"]:.0f}, {v["viii"]["hi"]:.0f}]', f'{v["trace"]["mean"]:.1f}',
                 f'{v["vii_margin"]["mean"]:.1f}', f'{v["i_autoaccept"]["mean"]:.1f}', f'{v["findings_per_stream"]:,.0f}']
                for p, v in e7['streams'].items()]
        parts.append(md_table(['Stream π', 'E^ev (viii), mean [2.5, 97.5 pct]', 'E^ev TRACE-PE', 'E^ev (vii)', 'E^ev (i)', 'Findings per stream'], rows))
    a = cfg['assurance']
    note = (f'Issuance {a["start"]} to {a["end"]}, horizon {a["horizon"]}; L = {a["primary_L"]} d; τ_FPR = {a["tau_fpr"]:g}, τ_FNR = {a["tau_fnr"]:g}; '
            f'B = {a["budget_frac"]:.0%} of the previous {a["budget_window_days"]} days; γ = {e7.get("ptr", {}).get("gamma")}. '
            f'K1 met: {e7["K1"]["met"]}; K2 met: {e7["K2"]["met"]} (max {pct(e7["K2"]["max_h_ub"], 3)}%); K3 met: {e7["K3"]["met"]} '
            f'({pct(e7["K3"]["relative_reduction"], 1)}%{ci_pct(e7["K3"]["ci"], 1)}). Decision: {e7["decision"]}.')
    return 'table11_assurance', 'Table 11. Assurance-plane simulation: exposure, kill criteria, sensitivity, analyst noise and streams', '\n\n'.join(parts), note, ['e7_assurance']


def t12(O, cfg):
    e8 = O['e8_attribution']
    rows = []
    for mo, v in e8['months'].items():
        nov = (f'{v["novelty_auprc"]:.3f} ({v["base_rate"]:.3f})' if _isnum(v.get('novelty_auprc')) else '—')
        rows.append([month_label(mo), num(v['non_generic']), pct(v['unseen_share'], 1), pct(v['top1_known'], 1), pct(v['top3_known'], 1),
                     pct(v['top1_all'], 1), pct(v['closed_bound'], 1), f'{pct(v["macro_f1_closed"], 1)} / {pct(v["macro_f1_open"], 1)}',
                     f'{v["novelty_auroc"]:.3f}' if _isnum(v.get('novelty_auroc')) else '—', nov, pct(v.get('unknowns_rejected'), 1),
                     f'{pct(v["category_accuracy"], 1)} / {pct(v["category_macro_f1"], 1)}'])
    hdr = ['Month', 'Non-generic malware', 'Unseen share (%)', 'Top-1 known (%)', 'Top-3 known (%)', 'Top-1 all (%)', 'Closed-world bound (%)',
           'Macro-F1 closed / open (%)', 'Novelty AUROC', 'Novelty AUPRC (base rate)', 'Unknowns rejected (%)', 'Category acc. / macro-F1 (%)']
    note = (f'{e8["known_families"]} families with ≥ {cfg["attribution"]["min_train"]} training files ({e8["train_files"]:,} files; '
            f'{e8["generic_excluded"]:,} with generic tokens excluded); τ_open = {e8["tau_open"]:.3f}. KB10: {compact(e8["KB10"])}. '
            f'H7: {compact(e8["H7"])}. P6: {compact(e8["P6"])}.')
    return 'table12_attribution', 'Table 12. Secondary attribution leg', md_table(hdr, rows), note, ['e8_attribution']


def t13(O, cfg):
    e9, e10 = O['e9_explain_issue'], O.get('e10_ledger_tests')
    rows = [[g['group'], f'{g["mean_abs_shap"]:.3f}', pct(g['shap_share'], 1), pct(g['gain_share'], 1), pct(g['lr_share'], 1),
             f'{g["mean_abs_delta_on_deletion"]:.3f}'] for g in e9['groups']]
    parts = [md_table(['EMBER group', 'Mean abs. grouped SHAP (margin)', 'Abs. SHAP share (%)', 'Gain share (%)', 'LR abs. coefficient share (%)',
                       'Mean abs. Δ margin on group deletion'], rows)]
    sh, kb, iss = e9['shap'], e9['KB11'], e9['issuance']
    checks = [['Grouped TreeSHAP cost', f'{sh["ms_per_finding"]} ms per finding; local accuracy max residual {sh["max_local_accuracy_residual"]:.1e}'],
              ['Deletion faithfulness (Spearman)', f'mean {sh["faithfulness_spearman_mean"]:.2f}, median {sh["faithfulness_spearman_median"]:.2f}'],
              ['KB11 stability (top-group Jaccard across seeds)', f'correct {kb["jaccard_correct"]:.3f} vs wrong {kb["jaccard_wrong"]:.3f} '
               f'(n = {kb["n_wrong"]}); Cliff\'s δ = {kb["cliffs_delta"]:.3f}; met: {kb["met"]}'],
              ['Issued-finding records (ISS)', f'{iss["records"]:,} records; states {compact(iss["states"])}; {iss["seconds"]} s'],
              ['V1 chain verification', f'{e9["V1"]["records"]:,} records, {e9["V1"]["anchors"]} anchors, ok {e9["V1"]["ok"]}, {e9["V1"]["seconds"]} s'],
              ['V2 content-addressed objects', f'{e9["V2"]["objects"]} objects, {e9["V2"]["failures"]} failures'],
              ['V3 re-execution', f'{e9["V3"]["sampled"]} sampled: vector hash {e9["V3"]["vector_hash"]}, margin bit-identical '
               f'{e9["V3"]["margin_bit_identical"]}, SHAP local accuracy {e9["V3"]["shap_local_accuracy"]}']]
    if e10:
        checks.append(['P8 tamper injection', '; '.join(f'{k.replace("_", " ")} {v["detected"]:,}/{v["injected"]:,}' for k, v in e10['tamper'].items())])
        checks.append(['P8 verification scaling', '; '.join(f'n = {s["n"]:,}: {s["seconds"]} s' for s in e10['scaling']) +
                       f'; log–log slope {e10["loglog_slope"]:.3f}'])
        checks.append(['Merkle inclusion receipts', f'verified: {e10["receipts_verified"]}; leaf modification detected: {e10["merkle_leaf_modification_detected"]}'])
    xc = O.get('_xenv')
    if xc:
        checks.append(['KB3 cross-environment re-execution', f'bit-identical fraction {xc["bit_identical_fraction"]:.4f}; tree hash equal '
                       f'{xc["tree_hash_equal"]}; vector digest equal {xc["vector_digest_equal"]}'])
    parts.append(md_table(['Check', 'Result'], checks))
    return 'table13_explain_ledger', 'Table 13. Explanation evidence and ledger integrity', '\n\n'.join(parts), \
        'Anchors: Ed25519 with a simulated time-stamping authority; write-once storage emulated by a content-addressed store.', ['e9_explain_issue', 'e10_ledger_tests']


def t14(O, cfg):
    e11 = O['e11_ember2018']
    if e11.get('skipped'):
        return 'table14_ember2018', 'Table 14. EMBER-2018 corroboration', 'Skipped: ' + str(e11.get('reason', 'no EMBER-2018 data')), '', ['e11_ember2018']
    rel = O.get('_published', {}).get('ember2018_release', {})
    pc = e11['published_check']
    rows = [['AUC-ROC (%)', num(rel.get('auc'), 3), pct(pc['auc'], 3)], ['TPR at 0.1% FPR, test-tuned (%)', num(rel.get('tpr_at_0p1'), 2), pct(pc['tpr_at_0p1'])],
            ['TPR at 1% FPR, test-tuned (%)', num(rel.get('tpr_at_1'), 2), pct(pc['tpr_at_1'])]]
    parts = [md_table(['Published EMBER-2018 model on the check months', 'Release notebook (RfP)', 'This vectorisation (this run)'], rows)]
    rules = [r for r in next(iter(e11['within']['months'].values())) if r.startswith('cp')]
    rows = []
    for mo, v in e11['within']['months'].items():
        r = [mo if mo == 'cal' else month_label(mo), f'{v["benign"]:,} / {v["malware"]:,}']
        for rl in rules:
            r += [pct(v[rl]['fnr']), pct(v[rl]['fpr'], 3), pct(v[rl]['f1_pi'])]
        r.append(pct(v.get('auc'), 3))
        rows.append(r)
    hdr = ['Month', 'Benign / malware'] + [f'{h} @θ{rl[2:]}' for rl in rules for h in ('FNR (%)', 'FPR (%)', 'F1 @π (%)')] + ['AUC-ROC (%)']
    parts.append(md_table(hdr, rows))
    ri, ft = e11['random_inflation'], e11['forward_transfer']
    checks = [['Within-EMBER temporal AUT(F1@π)', '; '.join(f'{k}: {pct(v)}' for k, v in e11['within']['aut'].items())],
              ['SVR, test months', compact(e11['within'].get('svr'))],
              ['Random-split inflation, F1@π vs temporal AUT', f'{ri["mean"] * 100:+.2f} pp{ci_pct(ri["ci"])}' if _isnum(ri.get('mean')) else '—'],
              ['Forward transfer to BODMAS: AUT(F1@π); monthly FNR', f'{pct(ft.get("aut"))}; {pct(ft["fnr_range"][0])}–{pct(ft["fnr_range"][1])}%'],
              ['Backward application of f₀ to EMBER-2018, monthly AUC-ROC (descriptive)',
               f'{pct(min(e11["backward_f0_auc"].values()), 1)}–{pct(max(e11["backward_f0_auc"].values()), 1)}%'],
              ['SHA-256 overlap with BODMAS', num(e11['sha_overlap_with_bodmas'])]]
    parts.append(md_table(['Corroboration check', 'Result'], checks))
    return 'table14_ember2018', 'Table 14. EMBER-2018 corroboration', '\n\n'.join(parts), f'{e11["files"]:,} vectorised files.', ['e11_ember2018']


def t15(O, cfg):
    e14 = O['e14_compare']
    refs = O.get('_published', {}).get('references', {})

    def val(v, published=False):
        if v is None:
            return 'not measured'
        if isinstance(v, list):
            return f'{v[0]:.2f}–{v[1]:.2f}' if published else f'{pct(v[0])}–{pct(v[1])}'
        return f'{v:.2f}' if published else pct(v, 3 if abs(v) < 0.01 else 2)

    def d(v, rel=False):
        if v is None:
            return '—'
        f = (lambda x: f'{x * 100:+.1f}%' if _isnum(x) else '—') if rel else (lambda x: f'{x:+.2f}' if _isnum(x) else '—')
        return ' / '.join(f(x) for x in v) if isinstance(v, list) else f(v)
    rows = [[r['metric'], r['source'], f'{val(r["published"], True)} ({r["label"]})', f'{val(r.get("value"))} ({r["this_work"]})',
             d(r['delta_pp']), d(r['delta_rel'], True), r['protocol']] for r in e14['rows']]
    body = md_table(['Metric', 'Published source', 'Published value', 'This work', 'Δ absolute (pp)', 'Δ relative', 'Protocol note'], rows)
    body += '\n\nReferences: ' + ' '.join(f'[{k}] {v}' for k, v in refs.items())
    note = 'Δ = this work − published (percentage points); relative Δ = Δ / published. Ranges are compared end-to-end. Protocols differ as stated per row.'
    return 'table15_comparison', 'Table 15. Comparison with published baselines: absolute (pp) and relative differences', body, note, ['e14_compare']


def t16(O, cfg):
    e12 = O['e12_cost_learning']
    rows = [[disp(t['model']), f'{t["train_seconds"]:.1f}', f'{t["inference_us_per_file"]:,.1f}', f'{t["peak_rss_gb"]:.2f}']
            for t in sorted(e12.get('timing', []), key=lambda t: t['train_seconds'])]
    parts = [md_table(['Model', 'Training (s)', 'Inference (µs per file)', 'Peak RSS (GB)'], rows)] if rows else []
    lr = []
    for k, pts in e12.get('learning', {}).items():
        for p in pts:
            lr.append([disp(k), f'{p["fraction"]:.0%}', num(p['rows']), pct(p['aucpr_pi']), pct(p['train_auc'], 3), pct(p['fnr']), p['fit_seconds']])
    if lr:
        parts.append(md_table(['Model', 'Fraction of training window', 'Rows', 'AUC-PR @π (%)', 'Train AUC (%)', 'FNR @certified θ (%)', 'Fit (s)'], lr))
    env = O.get('e0_intake', {}).get('env', {})
    note = (f'One process per model (uncontended); inference on {cfg["cost"]["inference_rows"]:,} rows. Machine: {env.get("cpu_model", "?")}, '
            f'{env.get("nproc", "?")} CPUs, Python {env.get("python", "?")}, LightGBM {env.get("lightgbm", "?")}.')
    return 'table16_cost', 'Table 16. CPU cost per model and learning curves', '\n\n'.join(parts), note, ['e12_cost_learning']


def t17(O, cfg):
    e13 = O['e13_statistics']
    rows = []
    for k, v in sorted(e13['pairwise'].items(), key=lambda kv: kv[1]['display']):
        rows.append([v['display'], f'{v["mean_delta_pp"]:+.2f}' if _isnum(v.get('mean_delta_pp')) else '—',
                     f'{v["cliffs_delta"]:+.3f}' if _isnum(v.get('cliffs_delta')) else '—', num(v.get('wilcoxon_p')), num(v.get('holm_p')),
                     f'{v["mcnemar_f0_only"]:,} / {v["mcnemar_model_only"]:,} (p = {v["mcnemar_p"]:.2g})',
                     f'{v.get("delong_months_significant", 0)}/{len(v.get("delong_months", {}))}'])
    fr = e13['friedman']
    parts = [md_table(['Model', 'Mean monthly ΔF1@π, f₀ family − model (pp)', "Cliff's δ", 'Wilcoxon p', 'Holm p',
                       'McNemar vs f₀: f₀-only / model-only errors', 'Months with DeLong p_Holm < 0.05'], rows),
             md_table(['Test', 'Result'], [['Friedman over months', f'χ² = {fr["chi2"]:.2f}, p = {fr["p"]:.2g}, Kendall W = {fr["kendall_w"]:.3f}'],
                                           ['Mean ranks (1 = best)', '; '.join(f'{disp(k)} {v:.2f}' for k, v in e13['mean_ranks'].items())]])]
    note = (f'H5: {compact(e13["H5"])}. Excluded from Friedman (F1 undefined in some month): '
            f'{", ".join(disp(k) for k in e13.get("excluded", [])) or "none"}.')
    return 'table17_statistics', 'Table 17. Statistical comparison of detectors', '\n\n'.join(parts), note, ['e13_statistics']


BUILDERS = [t01, t01b, t02, t03, t04, t05, t06, t07, t08, t09, t10, t11, t12, t13, t14, t15, t16, t17]
NEEDS = {t01: ['e0_intake'], t01b: ['e15_register'], t02: ['e1_metrics'], t03: ['e1_metrics', 'e1_metrics_raw'], t04: ['e2_certificates', 'e1_metrics'],
         t05: ['e2_certificates'], t06: ['e1_metrics'], t07: ['e3_calibration'], t08: ['e4_bias'], t09: ['e5_errors_drift'],
         t10: ['e5_errors_drift'], t11: ['e7_assurance'], t12: ['e8_attribution'], t13: ['e9_explain_issue'], t14: ['e11_ember2018'],
         t15: ['e14_compare'], t16: ['e12_cost_learning'], t17: ['e13_statistics']}


def build_all(run, cfg) -> list:
    from ..config import ROOT
    names = {n for f in NEEDS.values() for n in f} | {'e6_monitor', 'e10_ledger_tests'}
    O = {n: run.load(n) for n in names if run.has(n)}
    pb = ROOT / 'results' / 'published_baselines.json'
    O['_published'] = load_json(pb) if pb.exists() else {}
    xc = ROOT / 'xenv' / 'xenv_compare.json'
    if xc.exists():
        O['_xenv'] = load_json(xc)
    label = cfg['run'].get('label', 'measured on this run')
    written, chunks = [], []
    for fn in BUILDERS:
        missing = [n for n in NEEDS[fn] if n not in O]
        if missing:
            log(f'  skip {fn.__name__}: missing {", ".join(missing)}')
            continue
        try:
            name, title, body, note, src = fn(O, cfg)
        except Exception as exc:                      # a malformed output must not hide the other tables
            log(f'  {fn.__name__} failed: {type(exc).__name__}: {exc}')
            continue
        text = (f'**{title}**\n\n{body}\n\n{note}\n\nSource: ' + ', '.join(f'out/{s}.json' for s in src) + f'. Values: {label}.\n')
        path = run.tables / f'{name}.md'
        path.write_text(text, encoding='utf-8')
        written.append(path)
        chunks.append(text)
    (run.tables / 'all_tables.md').write_text('\n\n'.join(chunks), encoding='utf-8')
    return written
