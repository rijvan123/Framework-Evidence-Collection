"""Fig. 4: Technique and modality taxonomy, with each leaf's role in TRACE-PE and the evidence-handling levels."""
import os, sys; HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from figlib import *
from matplotlib.patches import Circle, Wedge

W, Hh = 7.16, 5.58
fig, ax = canvas(W, Hh)

ROOT = 'ML-based malware evidence: techniques and modalities (locked scope: Windows PE, static EMBER v2 features)'
ax.add_patch(FancyBboxPatch((0.55, 5.24), 6.06, 0.26, boxstyle='round,pad=0,rounding_size=0.05', fc='#2B2B2B', ec='#2B2B2B', zorder=3))
ax.text(3.58, 5.37, ROOT, ha='center', va='center', fontsize=7.0, color='white', fontweight='bold', zorder=4)

U, CU, BA, CI, OU = 'used', 'core', 'base', 'cited', 'out'
cols = [
    ('I  Evidence modality', 'evid', [
        ('EMBER v2 static (2,381)', [(CU, 'byte histogram (256)'), (CU, 'byte-entropy hist. (256)'), (CU, 'strings (104)'),
                                         (CU, 'general file info (10)'), (CU, 'header (62); COFF time\nnot monitored'), (CU, 'sections (255)'),
                                         (CU, 'imports (1,280)'), (CU, 'exports (128)'), (CU, 'data directories (30)')]),
        ('Other static', [(CI, 'EMBER2024 v3 (2,568):\nincompatible'), (OU, 'raw bytes (MalConv)'), (OU, 'opcode n-grams, CFG')]),
        ('Dynamic', [(BA, 'API-call traces: separate\nexperiment, never fused')]),
        ('Other platforms', [(OU, 'memory, network/IoT,\nAndroid')]),
    ]),
    ('II  Analysis task', 'anal', [
        ('Decision', [(CU, 'detection (benign /\nmalicious)'), (BA, 'category (14 classes),\nback-off level'),
                      (BA, 'family attribution\n(n ≥ 50; generic\ntokens excluded)'), (BA, 'open-set novelty\n(unseen family)')]),
        ('Assurance', [(CU, 'label-free drift\ndetection'), (CU, 're-validation of\nissued findings'), (CU, 'time-indexed error\ncertification')]),
        ('Robustness', [(CI, 'evasion, poisoning:\nexposure statement only')]),
    ]),
    ('III  Learner family', 'anal', [
        ('Tree ensembles', [(CU, 'LightGBM (primary)'), (BA, 'XGBoost'), (BA, 'random forest,\nextra trees'), (BA, 'light stacking')]),
        ('Linear', [(BA, 'logistic regression'), (BA, 'linear SVM')]),
        ('Instance, probabilistic', [(BA, 'k-NN (sub-sample)'), (BA, 'naive Bayes')]),
        ('Neural', [(CI, 'shallow MLP, 1D-CNN:\nflagged PoC'), (CI, 'SOREL-DNN, MalConv:\nliterature only')]),
        ('Update rules', [(BA, 'calendar retraining'), (BA, 'PCT-adapted GBDT\nupdate')]),
    ]),
    ('IV  Uncertainty & drift', 'assu', [
        ('Conformal', [(CU, 'ICE credibility\n(Transcendent)'), (BA, 'Mondrian by category'), (BA, 'adaptive conformal\n(ACI)')]),
        ('Two-sample tests', [(CU, 'KS on scores'), (CU, 'PSI per group'), (CU, 'classifier two-sample\ntest (C2ST)')]),
        ('Sequential', [(CU, 'Page–Hinkley')]),
        ('Representation', [(CI, 'CADE, OWAD')]),
        ('Bounds', [(CU, 'Clopper–Pearson\n(exact, one-sided)')]),
    ]),
    ('V  Explanation, reporting', 'repo', [
        ('Attribution', [(CU, 'TreeSHAP grouped\nover 9 groups'), (BA, 'ungrouped TreeSHAP'), (CI, 'KernelSHAP, LIME'),
                         (CU, 'local-accuracy check'), (BA, 'group-deletion\nfaithfulness')]),
        ('Evidential statement', [(CU, 'PPV at $\\pi \\in$ {1, 2,\n5, 10}%'), (BA, 'score-based LR,\ncapped; Cllr'), (CI, 'C-Scale verbal\nmapping')]),
    ]),
    ('VI  Integrity & custody', 'ledg', [
        ('Primitives', [(CU, 'SHA-256 (FIPS 180-4),\ndomain-separated'), (CU, 'hash chain'), (CU, 'Merkle tree, inclusion\nproofs (RFC 9162)'),
                        (CU, 'Ed25519 anchors;\nTSA simulated')]),
        ('Storage, provenance', [(CU, 'content-addressed\nwrite-once (simulated)'), (CU, 'W3C PROV-aligned\nrecords')]),
        ('Alternatives', [(CI, 'permissioned\nblockchain custody'), (CI, 'in-toto, Sigstore'), (CI, 'proof-of-learning')]),
    ]),
]

cw, cg, x0 = 1.135, 0.04, 0.07
ytop = 5.00
LH, GH = 0.108, 0.05


def marker(x, y, kind):
    r = 0.032
    if kind == CU:
        ax.add_patch(Circle((x, y), r, fc=INK, ec=INK, lw=0.6, zorder=5))
    elif kind == BA:
        ax.add_patch(Circle((x, y), r, fc='white', ec=INK, lw=0.6, zorder=5))
        ax.add_patch(Wedge((x, y), r, 90, 270, fc=INK, ec=INK, lw=0, zorder=6))
    elif kind == CI:
        ax.add_patch(Circle((x, y), r, fc='white', ec=INK, lw=0.6, zorder=5))
    else:
        ax.add_line(Line2D([x - r, x + r], [y - r, y + r], color=INK, lw=0.8, zorder=5))
        ax.add_line(Line2D([x - r, x + r], [y + r, y - r], color=INK, lw=0.8, zorder=5))


# trunk from root
ax.add_line(Line2D([3.58, 3.58], [5.24, 5.12], color=INK, lw=0.7))
centers = [x0 + i * (cw + cg) + cw / 2 for i in range(6)]
ax.add_line(Line2D([centers[0], centers[-1]], [5.12, 5.12], color=INK, lw=0.7))
for i, (title, key, groups) in enumerate(cols):
    x = x0 + i * (cw + cg)
    fc, ec = PAL[key]
    ax.add_line(Line2D([centers[i], centers[i]], [5.12, ytop], color=INK, lw=0.7))
    ax.add_patch(FancyBboxPatch((x, ytop - 0.26), cw, 0.26, boxstyle='round,pad=0,rounding_size=0.04', fc=ec, ec=ec, zorder=3))
    ax.text(x + cw / 2, ytop - 0.13, title, ha='center', va='center', fontsize=6.1, color='white', fontweight='bold', zorder=4)
    y = ytop - 0.36
    body_top = ytop - 0.30
    for gname, leaves in groups:
        ax.text(x + 0.05, y, gname, ha='left', va='top', fontsize=5.8, fontweight='bold', color=ec, zorder=4)
        y -= 0.128
        for kind, txt in leaves:
            nl = txt.count('\n') + 1
            marker(x + 0.10, y - 0.045, kind)
            ax.text(x + 0.17, y, txt, ha='left', va='top', fontsize=5.5, color=INK, zorder=4, linespacing=1.05)
            y -= nl * LH + 0.026
        y -= GH
    ax.add_patch(FancyBboxPatch((x, y + 0.02), cw, body_top - y - 0.02, boxstyle='round,pad=0,rounding_size=0.04',
                                fc=fc, ec=ec, lw=0.6, zorder=1))

# legend
ly = 1.36
for j, (kind, txt) in enumerate([(CU, 'used in TRACE-PE'), (BA, 'baseline, comparator or sensitivity run'),
                                 (CI, 'cited, not run (estimated from literature)'), (OU, 'out of locked scope')]):
    xx = 0.20 + j * 1.72
    marker(xx, ly, kind)
    ax.text(xx + 0.08, ly, txt, va='center', fontsize=5.8)

# evidence-handling levels (S2 R2 matrix coding)
levels = [('L0', 'no evidential\nhandling', 10), ('L1', 'one evidential aspect\n(labels, analyst aid,\nrobustness or XAI)', 12),
          ('L2', 'bias-controlled\ntemporal evaluation', 21), ('L3', 'integrity-protected\ncustody of artefacts', 1),
          ('L4', 'forensic validation\nand reporting', 9)]
bx, bw, by, bh = 0.07, 1.06, 0.40, 0.62
ax.text(0.07, 1.14, 'Evidence-handling levels used to code the R2 matrix (S2; 53 rows):', fontsize=5.9, fontweight='bold', va='center')
for k, (lv, desc, n) in enumerate(levels):
    xx = bx + k * (bw + 0.05)
    shade = '#FFFFFF' if lv in ('L0', 'L1') else '#E6E6E6'
    ax.add_patch(FancyBboxPatch((xx, by), bw, bh, boxstyle='round,pad=0,rounding_size=0.04', fc=shade, ec='#555555', lw=0.6, zorder=2))
    ax.text(xx + 0.06, by + bh - 0.06, lv, ha='left', va='top', fontsize=6.4, fontweight='bold', zorder=3)
    ax.text(xx + bw - 0.06, by + bh - 0.06, f'{n} row' + ('s' if n != 1 else ''), ha='right', va='top', fontsize=5.4, color=GRAY, zorder=3)
    ax.text(xx + 0.06, by + bh - 0.20, desc, ha='left', va='top', fontsize=5.4, zorder=3, linespacing=1.05)
tx = bx + 5 * (bw + 0.05)
ax.add_patch(FancyBboxPatch((tx, by), 7.09 - tx, bh, boxstyle='round,pad=0,rounding_size=0.04', fc='#2B2B2B', ec='#2B2B2B', zorder=2))
ax.text(tx + (7.09 - tx) / 2, by + bh / 2, 'TRACE-PE target:\nL2 $\\cap$ L3 $\\cap$ L4\n(no S2 row reaches it)', ha='center', va='center',
        fontsize=5.8, color='white', fontweight='bold', zorder=3, linespacing=1.1)
# brace line over L2-L4
ax.add_line(Line2D([bx + 2 * (bw + 0.05), bx + 5 * (bw + 0.05) - 0.05], [by - 0.07, by - 0.07], color='#555555', lw=0.6))
ax.text(bx + 3.5 * (bw + 0.05) - 0.03, by - 0.13, 'shaded levels combined by TRACE-PE', ha='center', va='center', fontsize=5.3, color=GRAY)

save(fig, 'fig4_taxonomy', os.path.join(HERE, 'out'))
print('ok')
