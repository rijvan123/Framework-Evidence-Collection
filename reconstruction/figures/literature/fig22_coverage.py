#!/usr/bin/env python3
"""Fig. 22: coverage of evaluation discipline, evidence handling and reporting across the rows of the paper's
literature comparison table (author coding, labelled {Est} in the paper). Input: s11_rows.json in this folder.
Output: out/fig22_s11_coverage.{png,pdf}. Row labels name the works; the citations are in the paper."""
import json
import os

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = json.load(open(os.path.join(HERE, 's11_rows.json'), encoding='utf-8'))

SHORT = {'A1': 'EMBER LightGBM', 'A2': 'BODMAS GBDT', 'A3': 'SOREL-20M baselines', 'A4': 'EMBER2024', 'A5': 'EXE-Bench (preprint)',
         'B1': 'Dambra et al.', 'B2': 'Aghakhani et al.', 'B3': 'Li et al., CFG-GNN', 'B4': 'Yumlembam et al.', 'B5': 'D3QN selection',
         'B6': 'Kozák et al.', 'C1': 'Transcend', 'C2': 'Transcendent', 'C3': 'CADE', 'C4': 'Chen et al.', 'C5': 'Ghiani et al.',
         'C6': 'Chow et al.', 'D1': 'TESSERACT', 'D2': 'Arp et al.', 'E1': 'Adversarial EXEmples', 'E2': 'Severi et al.', 'F1': 'AVclass2',
         'F2': 'MOTIF', 'F3': 'RecMaL', 'G1': 'Forensic-chain', 'G2': 'in-toto', 'G3': 'Solanke', 'H1': 'Beg et al. (2025)',
         'H2': 'Beg et al. (2026)', 'T1': 'This work: A2', 'T2': 'This work: A9 (withdrawn)'}
GROUPS = {'A': 'Benchmarks', 'B': 'PE techniques', 'C': 'Drift / update', 'D': 'Method', 'E': 'Adversarial', 'F': 'Labels',
          'G': 'Integrity', 'H': "Authors' prior", 'T': 'This work'}
SUFFIX = {'Android': '  (Android)', 'Multi': '  (multi)', 'Generic': '  (generic)'}
BLOCKS = [('Evaluation discipline', ['C1', 'C2', 'C3', 'D']), ('Evidence handling', ['ID', 'PRV', 'INT', 'XAI', 'ERR', 'REP']),
          ('Reporting', ['FPR', 'Decay', 'Artifact'])]
STYLE = {'Y': ('#1F5AA6', '✓', 'white', None), 'P': ('#86B3E8', '◐', 'black', None), 'N': ('#EFEFEF', '✗', '#777777', None),
         '?': ('#FFFFFF', '?', '#555555', '////'), '-': ('#FFFFFF', '–', '#AAAAAA', None)}


def state(row, col):
    if col in ('C1', 'C2', 'C3', 'D'):
        return row['c'].get(col, '?')
    if col in row['ev']:
        return row['ev'][col]
    if col == 'FPR':
        return ('Y' if row['fpr_reported'] else 'N') if row['empirical'] else '-'
    if col == 'Decay':
        return ('Y' if 'T' in row['gen'] else 'N') if row['empirical'] else '-'
    if col == 'Artifact':
        return row['artifact'] if row['artifact'] in STYLE else '?'
    return '?'


def main():
    cols = [c for _, cs in BLOCKS for c in cs]
    cw, ch, gap_block, gap_group = 0.62, 0.36, 0.25, 0.22
    x0 = 3.6
    xs, x = [], x0
    for _, cs in BLOCKS:
        for _ in cs:
            xs.append(x)
            x += cw
        x += gap_block
    ys, y, prev = [], 0.0, None
    for r in ROWS:
        if prev is not None and r['group'] != prev:
            y += gap_group
        ys.append(y)
        y += ch
        prev = r['group']
    W, H = x + 0.2, y + 1.3
    fig = plt.figure(figsize=(W * 0.92, H * 0.92))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(H, -0.9)
    ax.axis('off')
    for i, r in enumerate(ROWS):
        yy = ys[i]
        bold = r['group'] == 'T'
        ax.text(x0 - 0.12, yy + ch / 2, SHORT.get(r['id'], r['id']) + SUFFIX.get(r['platform'], ''), ha='right', va='center',
                fontsize=7, fontweight='bold' if bold else 'normal')
        for j, c in enumerate(cols):
            st = state(r, c)
            fc, glyph, tc, hatch = STYLE.get(st, STYLE['?'])
            ax.add_patch(Rectangle((xs[j] + 0.03, yy + 0.03), cw - 0.06, ch - 0.06, fc=fc, ec='#BBBBBB' if st in '?-' else fc,
                                   lw=0.5, hatch=hatch))
            ax.text(xs[j] + cw / 2, yy + ch / 2, glyph, ha='center', va='center', fontsize=8.5, color=tc)
    # group labels and brackets
    for g, name in GROUPS.items():
        idx = [i for i, r in enumerate(ROWS) if r['group'] == g]
        if not idx:
            continue
        top, bot = ys[idx[0]], ys[idx[-1]] + ch
        ax.plot([0.08, 0.08], [top + 0.04, bot - 0.04], color='#999999', lw=0.8)
        ax.text(0.15, (top + bot) / 2, name, va='center', fontsize=7, color='#444444')
    # column headers
    k = 0
    for title, cs in BLOCKS:
        xa, xb = xs[k], xs[k + len(cs) - 1] + cw
        ax.text((xa + xb) / 2, -0.62, title, ha='center', va='center', fontsize=7.5, fontweight='bold')
        ax.plot([xa, xb], [-0.45, -0.45], color='#333333', lw=0.8)
        for c in cs:
            ax.text(xs[k] + cw / 2, -0.22, c, ha='center', va='center', fontsize=6.5)
            k += 1
    # legend
    ly = y + 0.55
    for i, (st, lab) in enumerate((('Y', 'present'), ('P', 'partial'), ('N', 'absent'), ('?', 'not verified'), ('-', 'not applicable'))):
        fc, glyph, tc, hatch = STYLE[st]
        lx = 0.1 + i * 1.75
        ax.add_patch(Rectangle((lx, ly), 0.45, 0.26, fc=fc, ec='#BBBBBB', lw=0.5, hatch=hatch))
        ax.text(lx + 0.225, ly + 0.13, glyph, ha='center', va='center', fontsize=6.5, color=tc)
        ax.text(lx + 0.55, ly + 0.13, lab, va='center', fontsize=6.5)
    out = os.path.join(HERE, 'out')
    os.makedirs(out, exist_ok=True)
    for ext in ('png', 'pdf'):
        fig.savefig(os.path.join(out, f'fig22_s11_coverage.{ext}'), dpi=200, bbox_inches='tight')
    print('ok')


if __name__ == '__main__':
    main()
