"""Fig. 1: TRACE-PE architecture (four planes, thirteen modules, ledger)."""
import os, sys; HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from figlib import *

W, Hh = 7.16, 5.30
fig, ax = canvas(W, Hh)

# ---------------- planes
XB, WB = 0.05, 6.07
band(ax, XB, 3.90, WB, 1.15, 'A  Evidence plane', 'evid')
band(ax, XB, 2.72, WB, 1.10, 'B  Analysis plane', 'anal')
band(ax, XB, 1.30, WB, 1.34, 'C  Assurance plane', 'assu')
band(ax, XB, 0.30, WB, 0.92, 'D  Reporting', 'repo')


def bridge_path(pts, **kw):
    """Draw a white underlay first so later crossings show a visible gap."""
    path(ax, pts, color='white', lw=3.2, head=False, z=4)
    path(ax, pts, z=5, **kw)


# ---------------- band A
yA, hA = 4.00, 0.95
box(ax, 0.34, yA, 0.90, hA, 'Evidence source', 'BODMAS release:\nX 134,435 × 2,381,\nmetadata, categories\n(or live intake)',
    key='ext', ls=(0, (3, 2)), title_color='#333333')
box(ax, 1.36, yA, 1.14, hA, 'M1 Intake &\nacquisition check', 'SHA-256 at source and\nafter transfer; schema;\nrow alignment; ID format', key='evid', ledger_mark=True)
box(ax, 2.62, yA, 1.14, hA, 'M2 Temporal-\nevidence screen', 'dual-format parse;\nk·MAD spike rule;\nprecision regime;\ncensored strata', key='evid', ledger_mark=True)
box(ax, 3.88, yA, 1.12, hA, 'M3 Canonical vector\n& duplicate audit', 'float32-LE vector hash;\nexact / near duplicates;\ncross-split removal', key='evid', ledger_mark=True)
box(ax, 5.12, yA, 0.94, hA, 'M4 Preservation\nstore', 'content-addressed\nwrite-once objects;\nread-verify', key='evid', ledger_mark=True)
for x1, x2 in [(1.24, 1.36), (2.50, 2.62), (3.76, 3.88), (5.00, 5.12)]:
    arrow(ax, (x1, yA + hA / 2), (x2, yA + hA / 2))

# ---------------- band B
yB, hB = 2.82, 0.92
box(ax, 0.34, yB, 1.46, hB, 'M5 Feature pipeline', 'EMBER v2 map (9 groups);\ngroup-invariant checks;\nin-split preprocessing;\nmonitor views', key='anal', ledger_mark=True)
box(ax, 1.92, yB, 1.70, hB, 'M6 Model registry\n& calibration', 'LightGBM $f_v$; manifest Merkle root;\ntree-section model hash;\nICE calibration; certified $\\theta_v$', key='anal', ledger_mark=True)
box(ax, 3.74, yB, 1.46, hB, 'M7 Finding issuance', 'verdict or abstain; back-off\nattribution; grouped TreeSHAP;\ncertificate reference', key='anal', ledger_mark=True)
box(ax, 5.30, yB, 0.76, hB, 'Finding $F_i$', 'verdict, score,\ncertificate ref,\nexplanation\nhash, receipt', key='anal', fill='#F7FBF7', ls=(0, (3, 2)), bfs=6.1)
yc = yB + hB / 2
arrow(ax, (1.80, yc), (1.92, yc)); arrow(ax, (3.62, yc), (3.74, yc)); arrow(ax, (5.20, yc), (5.30, yc))
# M4 -> M5
bridge_path([(5.59, yA), (5.59, 3.86), (1.07, 3.86), (1.07, yB + hB)])
label(ax, 3.30, 3.86, 'canonical vectors $x_i$', fs=5.8)

# ---------------- band C
yC, hC = 1.42, 1.12
box(ax, 0.34, yC, 1.28, hC, 'M8 Label-free\ndrift monitor', 'per predicted class:\nKS, group PSI,\ncredibility, C2ST;\nblocked null; persistence', key='assu', ledger_mark=True)
box(ax, 1.74, yC, 1.62, hC, 'M9 Budgeted\nre-validation', 'triggers: alarm, lapse, schedule;\nscope: issued, unlabelled;\nregion $R_a$ (density ratio);\nrank by $q_i$; review top-$B$;\nharm gate $\\gamma$', key='assu', ledger_mark=True)
box(ax, 3.48, yC, 1.18, hC, 'M10 Amendment\nwriter', 'CONFIRM / CORRECT /\nAUTO-AMEND / FLAG;\nsupersedes record $h$', key='assu', ledger_mark=True)
box(ax, 4.78, yC, 1.28, hC, 'M11 Certificate\nservice', 'CP bounds per month\nand stratum; prospective\nvalidity; expiry;\nre-certify $f_{v+1}$', key='assu', ledger_mark=True)
ym = yC + hC / 2
arrow(ax, (1.62, ym), (1.74, ym)); arrow(ax, (3.36, ym), (3.48, ym)); arrow(ax, (4.66, ym), (4.78, ym))
# M7 -> M8 stream (in the B/C gap)
bridge_path([(4.30, yB), (4.30, 2.68), (0.98, 2.68), (0.98, yC + hC)])
label(ax, 3.70, 2.68, 'score and credibility stream', fs=5.6)
# alarm => expiry (top margin of C), control style
bridge_path([(1.42, yC + hC), (1.42, 2.595), (5.46, 2.595), (5.46, yC + hC)], color=RED, ls=(0, (3, 1.6)))
label(ax, 4.22, 2.595, 'alarm → expire', fs=5.4, color=RED)
# M6 <-> M9 re-validator (crosses both gap paths)
path(ax, [(2.62, yB), (2.62, yC + hC)], color='white', lw=3.2, head=False, z=4)
arrow(ax, (2.62, yB), (2.62, yC + hC), style='<|-|>', z=6)
label(ax, 2.98, 2.735, '$f_{v+1}$', fs=5.6, bg=False)
# M11 -> M7 certificate reference
path(ax, [(4.95, yC + hC), (4.95, yB)], color='white', lw=3.2, head=False, z=4)
arrow(ax, (4.95, yC + hC), (4.95, yB), z=6)
label(ax, 5.13, 2.755, '$C(t)$', fs=5.6, bg=False)

# ---------------- band D
yD, hD = 0.40, 0.72
box(ax, 0.34, yD, 0.96, hD, 'Analyst', 'reviews ≤ $B$ cases\nper trigger;\nsigned outcome', key='ext', title_color='#333333')
box(ax, 1.42, yD, 1.20, hD, 'Label oracle', 'labels mature after\ndelay $L$; snapshot\nMerkle-committed', key='ext', title_color='#333333')
box(ax, 2.74, yD, 1.20, hD, 'M13 Independent\nverifier', 'chain, Merkle, anchors;\nre-execution check', key='repo', ledger_mark=True)
box(ax, 4.06, yD, 2.00, hD, 'M12 Evidence report', 'finding + certificate + PPV($\\pi$)\n+ optional capped LR + amendment\nhistory; "no receipt, no report"', key='repo', ledger_mark=True)
# Analyst <-> M9
path(ax, [(1.15, yD + hD), (1.15, 1.26), (1.95, 1.26), (1.95, yC)], color=GRAY, lw=0.8, head=False, z=5)
arrow(ax, (1.95, 1.30), (1.95, yC), color=GRAY, z=6)
arrow(ax, (1.15, 1.20), (1.15, yD + hD), color=GRAY, z=6)
label(ax, 1.55, 1.26, 'top-$B$ / outcome', fs=5.2, color=GRAY)
# Oracle -> M9 and -> M11 (label bus in the C/D gap)
arrow(ax, (2.30, yD + hD), (2.30, yC), color=GRAY, z=6)
bridge_path([(2.50, yD + hD), (2.50, 1.25), (5.42, 1.25), (5.42, yC)], color=GRAY)
label(ax, 3.10, 1.25, 'matured labels', fs=5.2, color=GRAY)
# M10 -> M12, M11 -> M12
path(ax, [(4.40, yC), (4.40, yD + hD)], color='white', lw=3.2, head=False, z=4)
arrow(ax, (4.40, yC), (4.40, yD + hD), z=6)
arrow(ax, (5.80, yC), (5.80, yD + hD), z=6)

# ---------------- ledger column
LX, LW, LY, LH = 6.22, 0.88, 0.30, 4.75
fc, ec = PAL['ledg']
ax.add_patch(FancyBboxPatch((LX, LY), LW, LH, boxstyle='round,pad=0,rounding_size=0.06', fc=fc, ec=ec, lw=1.1, zorder=2))
ax.text(LX + LW / 2, LY + LH - 0.08, 'Ledger $L$', ha='center', va='top', fontsize=7.4, fontweight='bold', zorder=3)
ax.text(LX + LW / 2, LY + LH - 0.25, 'append-only,\nhash-chained', ha='center', va='top', fontsize=5.8, zorder=3, linespacing=1.1)
types = ['ACQ', 'SCR', 'DUP', 'EXT', 'ORC', 'MAN', 'MOD', 'CAL', 'CERT', 'ISS', 'TRG', 'RVC', 'REV', 'AMD', 'EXPY', 'NCR', 'ANC', 'VER']
y0 = LY + LH - 0.62
for i, tname in enumerate(types):
    yy = y0 - i * 0.176
    ax.add_patch(FancyBboxPatch((LX + 0.17, yy - 0.07), LW - 0.34, 0.14, boxstyle='round,pad=0,rounding_size=0.03',
                                fc='white', ec='#444444', lw=0.5, zorder=3))
    ax.text(LX + LW / 2, yy, tname, ha='center', va='center', fontsize=5.6, zorder=4, family='DejaVu Sans Mono')
ax.text(LX + LW / 2, LY + 0.50, '$h_j = H(h_{j-1}\\,\\|\\,H(r_j))$\nMerkle epoch roots\n→ signed anchor\n(TSA simulated);\nreceipts → M12', ha='center',
        va='center', fontsize=5.3, zorder=3, linespacing=1.15)
# ledger -> M12 receipts; ledger -> M13 audit read
arrow(ax, (LX, 0.76), (6.06, 0.76), z=6)
path(ax, [(LX + 0.10, LY), (LX + 0.10, 0.355), (3.34, 0.355), (3.34, yD)], z=5)
label(ax, 4.70, 0.355, 'audit read', fs=5.2)

# ---------------- legend
lx = 0.40; ly = 0.12
ax.add_patch(Rectangle((lx, ly - 0.035), 0.07, 0.07, fc=INK, lw=0)); ax.text(lx + 0.11, ly, 'appends records to ledger $L$', va='center', fontsize=5.8)
arrow(ax, (lx + 1.45, ly), (lx + 1.80, ly)); ax.text(lx + 1.86, ly, 'data / evidence flow', va='center', fontsize=5.8)
arrow(ax, (lx + 2.95, ly), (lx + 3.30, ly), color=RED, ls=(0, (3, 1.6))); ax.text(lx + 3.36, ly, 'control (alarm, expiry)', va='center', fontsize=5.8, color=RED)
arrow(ax, (lx + 4.55, ly), (lx + 4.90, ly), color=GRAY); ax.text(lx + 4.96, ly, 'human / oracle input', va='center', fontsize=5.8, color=GRAY)

save(fig, 'fig1_architecture', os.path.join(HERE, 'out'))
print('ok')
