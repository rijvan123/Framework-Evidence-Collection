#!/usr/bin/env python3
"""E15 - the unified pre-registered register (U1-U16, K1-K3, KT, KB*, KS*) with measured outcomes, and the
mechanical A9 -> A2 decision (docs/PREREGISTRATION.md)."""
import _common  # noqa: F401
from tracepe.config import ROOT, cli
from tracepe.run import Run
from tracepe.utils import load_json, log


def g(d, *path, default=None):
    for p in path:
        if not isinstance(d, dict) or p not in d:
            return default
        d = d[p]
    return d


def main():
    cfg, args = cli(__doc__)
    run = Run(cfg)
    o = {n: (run.load(n) if run.has(n) else {}) for n in
         ('e1_metrics', 'e2_certificates', 'e3_calibration', 'e4_bias', 'e5_errors_drift', 'e6_monitor', 'e7_assurance',
          'e8_attribution', 'e9_explain_issue', 'e10_ledger_tests', 'e13_statistics')}
    reg = []

    def add(id_, statement, measured, outcome):
        reg.append(dict(id=id_, statement=statement, measured=measured, outcome=outcome))

    b = o['e4_bias']
    add('U1', 'Random split inflates GBDT F1 vs temporal AUT', g(b, 'random', 'inflation_mean'),
        None if 'P1' not in b else ('falsified' if b['P1']['falsified'] else 'not falsified'))
    st = o['e1_metrics'].get('streams', {})
    cells = [c for mo in st.values() for k, c in mo.items() if isinstance(c, dict) and 'outside' in c]
    out = sum(bool(c['outside']) for c in cells)
    add('U2', 'Precision at pi follows Eq. (55)', f'{out}/{len(cells)} cells outside', 'falsified' if cells and out / len(cells) > 0.2 else 'not falsified')
    lk = g(b, 'leakage', 'P3', default={})
    add('U3', 'Pre-split selection/PCA inflates LR/SVM; scaling leaves trees unchanged', lk,
        None if not lk else ('selection clause not falsified' if lk.get('selection_leak_significant') else 'falsified'))
    c3 = o['e3_calibration']
    add('U4', 'Isotonic/Platt lower ECE; prior shift lowers Brier/EC at pi <= 1%', g(c3, 'P4'),
        None if not c3 else ('falsified' if g(c3, 'P4', 'falsified') else 'not falsified'))
    e5 = o['e5_errors_drift']
    add('U5', 'Spearman rho(JS drift, F1) <= -0.5', g(e5, 'P5', 'rho'), None if not e5 else ('falsified' if g(e5, 'P5', 'falsified') else 'not falsified'))
    e8 = o['e8_attribution']
    add('U6', 'Open-set macro-F1 declines faster than detection F1', g(e8, 'P6', 'diff'),
        None if 'P6' not in e8 else ('falsified' if e8['P6']['falsified'] else 'not falsified'))
    add('U7', 'tau* beats 0.5 on expected cost at pi <= 1%', g(c3, 'P7'), None if not c3 else ('falsified' if g(c3, 'P7', 'falsified') else 'not falsified'))
    e10 = o['e10_ledger_tests']
    add('U8', 'Chain detects all injected edits; verification linear', g(e10, 'loglog_slope'),
        None if not e10 else ('not falsified' if g(e10, 'P8', 'met') else 'falsified'))
    add('U9', 'Trees invariant to monotone scaling; LR/kNN not', g(b, 'P9'), None if 'P9' not in b else ('falsified as stated' if b['P9']['falsified'] else 'not falsified'))
    add('U10', 'FNR and FPR higher in the high-entropy stratum', g(e5, 'P10'),
        None if not e5 else ('holds' if (e5['P10']['fnr_holds'] and e5['P10']['fpr_holds']) else ('falsified for FPR' if e5['P10']['fnr_holds'] else 'falsified')))
    add('U11', 'Observed TPR/FPR follow Eq. (5) under injected label noise', g(c3, 'P11_falsified'),
        None if not c3 else ('falsified' if c3['P11_falsified'] else 'not falsified'))
    add('U12', 'Unseen-family FNR > known-family FNR', g(e5, 'H3'), None if not e5 else ('met' if e5['H3']['met'] else 'not met'))
    s13 = o['e13_statistics']
    add('U13', 'GBDT leads on AUT', g(s13, 'friedman'), None if not s13 else ('met' if s13['H5']['met'] else 'not met'))
    add('U14', 'Open-set rejection raises open-set macro-F1', g(e8, 'H7'), None if not e8 else ('met' if g(e8, 'H7', 'p', default=1) < 0.05 else 'not met'))
    add('U15', 'No COFF-timestamp artefact (|dAUT| < 1 pp)', g(b, 'coff', 'delta_aut_f1'), None if 'H9' not in b else ('met' if b['H9']['met'] else 'not met'))
    add('U16', 'Calibration degrades over time', g(c3, 'H10', 'rho'), None if not c3 else ('met' if g(c3, 'H10', 'rho', default=0) > 0 else 'not met'))
    e7 = o['e7_assurance']
    for k, s in (('K1', 'Full re-scoring changes <= B in >= 6 of 7 updates'), ('K2', 'CP-95% upper bound of h < 0.1% in every update'),
                 ('K3', 'Upper CI of relative E^ev reduction vs (viii) < 10% (L = 30 d)')):
        add(k, s, {kk: vv for kk, vv in g(e7, k, default={}).items() if kk != 'updates'}, None if k not in e7 else ('kill met' if e7[k]['met'] else 'not met'))
    e6 = o['e6_monitor']
    add('KT', 'Alarm within 14 d of the July onset and <= 1 false alarm per stable month', g(e6, 'KT'),
        None if not e6 else ('kill met -> scheduled re-validation' if e6['KT']['kill_met'] else 'passes'))
    add('KB1', 'Yield >= 1.5x lowest-margin review and lower U(t) in >= 6/7 months', g(e7, 'KB1'),
        None if 'KB1' not in e7 else ('met' if e7['KB1']['met'] else 'not met'))
    xc = ROOT / 'xenv' / 'xenv_compare.json'
    kb3 = load_json(xc) if xc.exists() else None
    add('KB3', '>= 99.9% bit-identical re-execution across environments', None if kb3 is None else
        dict(bit_identical_fraction=kb3['bit_identical_fraction'], tree_hash_equal=kb3['tree_hash_equal'],
             vector_digest_equal=kb3['vector_digest_equal']),
        None if kb3 is None else ('met' if kb3['KB3']['met'] else 'not met'))
    add('KB4', 'Static 80:20 understates FPR or FNR in >= 5/7 months', g(b, 'KB4'), None if 'KB4' not in b else ('met' if b['KB4']['met'] else 'not met'))
    e2 = o['e2_certificates']
    add('KB5', 'Censored stratum shifts FPR > bootstrap half-width', g(e2, 'KB5'),
        None if not e2 else (('met literally; inconclusive (degenerate)' if e2['KB5'].get('degenerate') else 'met') if e2['KB5']['met'] else 'not met'))
    add('KB7', 'Yield advantage keeps its sign at the largest analyst error rate', g(e7, 'KB7'),
        None if 'KB7' not in e7 else ('met' if e7['KB7']['met'] else ('not met (moot)' if (g(e7, 'KB7', 'advantage_r0') or 0) <= 0 else 'not met')))
    add('KB9', 'Ambiguity beats margin by >= 0.05 AUPRC', 'not executed (D13)', 'moot after A2' if g(e7, 'decision') == 'A2' else 'not executed')
    add('KB10', 'Novel-family AUROC >= 0.80 and AUPRC >= 3x base rate (July)', g(e8, 'KB10'),
        None if not e8 else ('kill met -> attribution leg dropped' if e8['KB10']['kill_met'] else 'passes'))
    e9 = o['e9_explain_issue']
    add('KB11', "Cliff's delta (stability: correct vs wrong) >= 0.147", g(e9, 'KB11', 'cliffs_delta'),
        None if not e9 else ('met' if g(e9, 'KB11', 'met') else 'not met'))
    add('KB12', 'Cllr >= 1 in >= 3 months', g(c3, 'KB12'), None if not c3 else ('kill triggered' if c3['KB12']['triggered'] else 'kill not triggered'))
    add('KS1', 'SVR >= 6 of 7 months at the second certified threshold', g(e2, 'KS1'), None if not e2 else ('met' if e2['KS1']['met'] else 'not met'))
    add('KS2', 'CP upper bound of r_H <= tau_H per update', g(e7, 'KS2', 'max_rH_ub'),
        None if 'KS2' not in e7 else ('met' if e7['KS2']['met'] else 'not met'))
    decision = g(e7, 'decision')
    R = dict(register=reg, decision=decision,
             decision_text=None if decision is None else ('K1 and K2, or K3 met: re-validation (A9) withdrawn; the manuscript proceeds as A2 '
                                                        '(time-indexed certificates + evidence ledger)' if decision == 'A2' else 'A9 retained'))
    run.save('e15_register', R)
    log('E15 done: decision', decision)


if __name__ == '__main__':
    main()
