#!/usr/bin/env python3
"""Evidence report M12 for one finding ("no receipt, no report"; paper Section 4.7). The report is refused
unless the ISS record's inclusion receipt verifies against a signed anchor."""
import sys

import _common  # noqa: F401
from tracepe.config import cli
from tracepe.decision.certificates import ppv_lower
from tracepe.evidence.hashing import hex2f32, hex2f64
from tracepe.evidence.ledger import find_records, receipt, verify_receipt
from tracepe.features.groups import GROUP_NAMES
from tracepe.run import Run


def main():
    def extra(ap):
        ap.add_argument('--sid', required=True, help='SHA-256 of the sample')
        ap.add_argument('--out', default=None, help='write Markdown here instead of stdout')
    cfg, args = cli(__doc__, extra)
    run = Run(cfg)
    hits = find_records(run.ledger_path, lambda r: r.get('t') == 'ISS' and r.get('sid') == args.sid)
    if not hits:
        sys.exit('no ISS record for this sample: no receipt, no report')
    idx, rec = hits[-1]
    rc = receipt(run.ledger_path, idx)
    if not verify_receipt(rc):
        sys.exit('receipt does not verify: no report (failure mode F7)')
    amd = find_records(run.ledger_path, lambda r: r.get('t') == 'AMD' and r.get('supersedes_sid') == args.sid)
    certs = run.load('e2_certificates') if run.has('e2_certificates') else {}
    prim = f'cp{cfg["thresholds"]["certified_tau"][0]:g}'
    cert = certs.get('certificates', {}).get(prim, {}).get(rec['month'])
    lines = [f'# Evidence report: {args.sid}', '',
             '## 1. Identity',
             f'- Sample SHA-256: `{rec["sid"]}`; canonical vector hash: `{rec["vh"]}`',
             f'- Ledger record {idx}, epoch `{rc["epoch"]}`, Merkle inclusion proof of {len(rc["proof"])} hashes, anchor record {rc["anchor_index"]} '
             f'(Ed25519, time-stamping authority **simulated**)',
             '- Feature vector supplied by the dataset publisher (EMBER v2, LIEF 0.9.0 declared, not re-executed): derivation gap N5.', '',
             '## 2. Finding',
             f'- State at issue: **{rec["state"]}**; verdict: {"malicious" if rec["yhat"] else "benign"}',
             f'- Margin {hex2f64(rec["z"]):.6f}; certified threshold {hex2f64(rec["theta"]):.6f}; ICE credibility {hex2f32(rec["cred"]):.4f}',
             f'- Model identity (tree-section SHA-256): `{rec["model"]}`', '',
             '## 3. Error statement']
    if rec['state'] == 'ISS' and cert:
        lines.append('- At issue, a valid prospective statement existed (certificate gating, S7.7).')
        lines.append(f'- Retrospective certificate for the issue month {rec["month"]} (computed after its labels matured): FPR {cert["fp"]}/{cert["n_b"]} (one-sided 95% CP upper '
                     f'{(cert["fpr_ub"] or float("nan")) * 100:.3f}%), FNR {cert["fn"]}/{cert["n_m"]} (upper {(cert["fnr_ub"] or float("nan")) * 100:.3f}%).')
        lines.append('')
        lines.append('## 4. Prevalence table (lower bound on PPV, S7.17)')
        lines.append('| Deployment prevalence | PPV lower bound |')
        lines.append('|---|---|')
        for pi in (0.01, 0.02, 0.05, 0.10):
            lines.append(f'| {pi * 100:g}% | {ppv_lower(cert["fn"], cert["n_m"], cert["fp"], cert["n_b"], pi) * 100:.2f}% |')
    else:
        lines.append('- No error-rate statement: **investigative lead only**.')
    lines += ['', '## 5. Explanation (top grouped TreeSHAP attributions, margin units)']
    for g, v in rec['xg']:
        lines.append(f'- {GROUP_NAMES[g]}: {hex2f32(v):+.4f}')
    lines += [f'- Base value {hex2f64(rec["b0"]):.6f}; local-accuracy residual {hex2f64(rec["res"]):.2e}', '',
              '## 6. History', f'- Amendments: {len(amd)}', '',
              '## 7. Limitations',
              '- Correctness is relative to the BODMAS release labels (multi-vendor verdicts, about 1% manual); family labels about 20% shifted or wrong.',
              '- No robustness claim: functionality-preserving evasion and poisoning are possible; packing is a confound.',
              '- Non-guarantees N1-N5: unanchored tail, insider before anchor, truth of content, equivocation without witness, derivation gap.', '',
              '## 8. Wording', '- Error-rate statements relevant to reliability inquiries. This report makes no claim of admissibility.']
    text = '\n'.join(lines) + '\n'
    if args.out:
        open(args.out, 'w', encoding='utf-8').write(text)
    else:
        print(text)


if __name__ == '__main__':
    main()
