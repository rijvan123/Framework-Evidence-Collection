"""Fig. 2: Evidence flow (acquisition -> preservation -> feature extraction -> ML analysis -> reporting),
the assurance (re-validation) loop, and the timeline of one issued finding."""
import os, sys; HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from figlib import *

W, Hh = 7.16, 4.66
fig, ax = canvas(W, Hh)

# ---------------- (a) five forward stages
stages = [('1  Acquisition', 'evid', 'M1, M2',
           ['hash files at source and after\ntransfer; compare', 'schema, row alignment,\nidentifier format',
            'parse first-seen (two formats)', 'spike rule, precision regime\n→ dated / censored strata', 'ACQ, SCR records']),
          ('2  Preservation', 'evid', 'M3, M4',
           ['canonical float32-LE vector\nhash (domain-separated)', 'exact / near-duplicate audit\nbefore any split', 'content-addressed write-once\nstore; read-verify',
            'oracle snapshot → Merkle\nroot (ORC)', 'DUP, ORC, ANC records']),
          ('3  Feature extraction', 'anal', 'M5',
           ['declared extractor: EMBER v2,\nLIEF 0.9.0 (not re-executed)', 'group-invariant checks on\nall 9 groups', 'preprocessing fitted inside\nthe training window only',
            'group views for monitor and\nSHAP; COFF time excluded', 'EXT, SCR records']),
          ('4  ML analysis', 'anal', 'M6, M7',
           ['temporal split; training-\nmanifest Merkle root', 'LightGBM $f_v$; tree-section\nmodel hash', 'ICE calibration; certified\nthreshold $\\theta_v$',
            'verdict or abstain; back-off\nattribution; grouped TreeSHAP', 'MAN, MOD, CAL, ISS records']),
          ('5  Reporting', 'repo', 'M11, M12',
           ['attach valid certificate $C(t_i)$', 'PPV at $\\pi \\in$ {1, 2, 5, 10}%;\noptional capped LR', 'amendment history and\ndisclosure notices',
            'evaluative use only if receipt\nverifies, certificate valid,\nno open flag', 'CERT, report receipt'])]
x0, gap, sw = 0.16, 0.045, 1.344
ytop = 4.56
for k, (title, key, mods, items) in enumerate(stages):
    x = x0 + k * (sw + gap)
    fc, ec = PAL[key]
    # chevron header
    tip = 0.10
    pts = [(x, ytop), (x + sw - tip, ytop), (x + sw, ytop - 0.16), (x + sw - tip, ytop - 0.32), (x, ytop - 0.32)]
    if k > 0:
        pts.append((x + tip, ytop - 0.16))
    ax.add_patch(Polygon(pts, closed=True, fc=ec, ec=ec, lw=0.6, zorder=3))
    ax.text(x + sw / 2 + (0.03 if k else 0), ytop - 0.16, title, ha='center', va='center', fontsize=7.3,
            fontweight='bold', color='white', zorder=4)
    # body
    by, bh = 2.56, ytop - 0.38 - 2.56
    ax.add_patch(FancyBboxPatch((x, by), sw, bh, boxstyle='round,pad=0,rounding_size=0.04', fc=fc, ec=ec, lw=0.7, zorder=2))
    ax.text(x + sw - 0.05, by + bh - 0.05, mods, ha='right', va='top', fontsize=5.6, color=ec, style='italic', zorder=4)
    yy = by + bh - 0.22
    for it in items:
        nl = it.count('\n') + 1
        ax.text(x + 0.07, yy, '•', ha='left', va='top', fontsize=6.2, color=ec, zorder=4)
        ax.text(x + 0.16, yy, it, ha='left', va='top', fontsize=6.0, color=INK, zorder=4, linespacing=1.12)
        yy -= nl * 0.112 + 0.07
ax.text(0.04, 3.55, '(a)', fontsize=7.2, fontweight='bold', va='center', rotation=90)

# ---------------- (b) assurance loop
ax.text(0.04, 1.51, '(b)', fontsize=7.2, fontweight='bold', va='center', rotation=90)
ly, lh = 1.16, 0.70
loop = [('Monitor', 'label-free, per predicted\nclass; blocked null;\ntwo-window persistence', 0.38, 1.12),
        ('Trigger $a$', 'drift alarm, certificate\nlapse at $t+L$, schedule,\nor integrity event', 1.62, 1.12),
        ('Re-validate', 'scope: issued and unlabelled;\nregion $R_a$; rank by $q_i$; analyst\nreviews top-$B$; matured labels only', 2.86, 1.40),
        ('Amend', 'CONFIRM, CORRECT,\nAUTO-AMEND ($q \\geq \\gamma$),\nor FLAG (disclosed)', 4.38, 1.14),
        ('Re-certify', 'expire $C_v$ (EXPY);\ncertify $f_{v+1}$ (CERT)', 5.64, 1.10)]
for name, body, x, w in loop:
    box(ax, x, ly, w, lh, name, body, key='assu', tfs=7.2, bfs=6.0)
for (n1, b1, xa, wa), (n2, b2, xb, wb) in zip(loop[:-1], loop[1:]):
    arrow(ax, (xa + wa, ly + lh / 2), (xb, ly + lh / 2), color=RED if n1 == 'Monitor' else INK,
          ls=(0, (3, 1.6)) if n1 == 'Monitor' else '-')
x4 = x0 + 3 * (sw + gap); x5 = x0 + 4 * (sw + gap)
ytopl = ly + lh
def bp(pts, **kw):
    path(ax, pts, color='white', lw=3.2, head=False, z=4); path(ax, pts, z=5, **kw)
# stream: stage 4 -> monitor (level 1)
bp([(x4 + 0.30, 2.56), (x4 + 0.30, 2.42), (0.94, 2.42), (0.94, ytopl)])
label(ax, 2.55, 2.42, 'issued findings: scores, credibility, explanations', fs=5.6)
# amend -> reporting (level 2)
bp([(4.95, ytopl), (4.95, 2.24), (6.40, 2.24), (6.40, 2.56)])
label(ax, 5.95, 2.24, 'amended report, disclosure', fs=5.5)
# re-certify -> ML analysis (level 3)
bp([(6.20, ytopl), (6.20, 2.06), (5.36, 2.06), (5.36, 2.56)])
label(ax, 5.78, 2.06, '$f_{v+1}$ deployed', fs=5.5)
# ---------------- (c) timeline of one issued finding
ax.text(0.04, 0.55, '(c)', fontsize=7.2, fontweight='bold', va='center', rotation=90)
ty = 0.46
arrow(ax, (0.30, ty), (7.06, ty), lw=0.8)
ax.text(7.06, ty - 0.06, 'time', ha='right', va='top', fontsize=5.8)
ticks = [(0.50, '$t_i$', 'finding issued\nunder $C(t_i)$'), (1.55, '$t_0$', 'drift onset'), (2.75, '$t_a = t_0 + D$', 'label-free alarm;\n$C$ expires'),
         (4.00, '$t_i + \\Delta_{use}$', 'finding relied\nupon'), (6.55, '$t_i + L$', 'label matures;\nreconciliation')]
for x, s_, d_ in ticks:
    ax.add_line(Line2D([x, x], [ty - 0.04, ty + 0.04], color=INK, lw=0.8, zorder=6))
    ax.text(x, ty - 0.06, s_, ha='center', va='top', fontsize=6.2)
    ax.text(x, ty - 0.20, d_, ha='center', va='top', fontsize=5.4, color=GRAY, linespacing=1.02)
ax.add_patch(Rectangle((0.50, ty + 0.27), 6.55 - 0.50, 0.12, fc='#D9D9D9', ec='#7A7A7A', lw=0.5, zorder=5))
ax.text(0.56, ty + 0.33, 'no re-validation: an erroneous finding stays wrong and undisclosed until $t_i + L$', ha='left',
        va='center', fontsize=5.6, zorder=6)
ax.add_patch(Rectangle((0.50, ty + 0.10), 2.75 - 0.50, 0.12, fc='#8E2C2C', ec='#5A1C1C', lw=0.5, zorder=5))
ax.add_patch(Rectangle((2.75, ty + 0.10), 3.35 - 2.75, 0.12, fc='white', ec='#8E2C2C', lw=0.5, hatch='////', zorder=5))
ax.text(0.56, ty + 0.16, 'TRACE-PE: in region $R_a$, flagged at $t_a$', ha='left', va='center', fontsize=5.6, color='white', zorder=6)
ax.text(3.42, ty + 0.16, 'reviewed within budget $B$ → corrected before use', ha='left', va='center', fontsize=5.5, color=RED)
ax.text(7.06, ty + 0.50, '$U(t)$: issued findings wrong and uncorrected at $t$;  exposure $E_T=\\int_0^T U(t)\\,dt$',
        ha='right', va='center', fontsize=5.8)
save(fig, 'fig2_flow', os.path.join(HERE, 'out'))
print('ok')
