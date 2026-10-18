"""Fig. 3: Conceptual model. (a) PROV-aligned evidence model (entities, activities, agents);
(b) lifecycle of an issued finding, with the states in which evaluative use is permitted."""
import os, sys; HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from figlib import *
import numpy as np

W, Hh = 7.16, 5.05
fig, ax = canvas(W, Hh)

ENT = ('#FFF4CC', '#8A6D00')     # PROV entity (oval)
ACT = ('#DCE9F6', '#2F4B66')     # PROV activity (rectangle)
AGT = ('#FBE2CF', '#8A4A12')     # PROV agent (pentagon)

X = [0.66, 1.66, 2.66, 3.66, 4.66, 5.66, 6.62]
Y1, Y2, Y3, Y4 = 4.62, 3.92, 3.27, 2.62
EW, EH = 0.82, 0.38
AW, AH = 0.66, 0.30
GW, GH = 0.94, 0.38
nodes = {}


def ent(k, x, y, txt):
    ax.add_patch(Ellipse((x, y), EW, EH, fc=ENT[0], ec=ENT[1], lw=0.8, zorder=4))
    ax.text(x, y, txt, ha='center', va='center', fontsize=6.0, zorder=5, linespacing=1.05)
    nodes[k] = ('e', x, y)


def act(k, x, y, txt):
    ax.add_patch(Rectangle((x - AW / 2, y - AH / 2), AW, AH, fc=ACT[0], ec=ACT[1], lw=0.8, zorder=4))
    ax.text(x, y, txt, ha='center', va='center', fontsize=6.0, zorder=5, linespacing=1.05, fontweight='bold', color=ACT[1])
    nodes[k] = ('a', x, y)


def agt(k, x, y, txt):
    w, h = GW, GH
    pts = [(x - w / 2, y - h / 2), (x + w / 2, y - h / 2), (x + w / 2, y + h / 2 - 0.10), (x, y + h / 2 + 0.02), (x - w / 2, y + h / 2 - 0.10)]
    ax.add_patch(Polygon(pts, closed=True, fc=AGT[0], ec=AGT[1], lw=0.8, zorder=4))
    ax.text(x, y - 0.02, txt, ha='center', va='center', fontsize=6.0, zorder=5, linespacing=1.05, color='#5A2E0A')
    nodes[k] = ('g', x, y)


def anchor(k, toward):
    """Boundary point of node k in the direction of point `toward`."""
    t, x, y = nodes[k]
    dx, dy = toward[0] - x, toward[1] - y
    if t == 'e':
        a, b = EW / 2, EH / 2
        s = 1 / np.sqrt((dx / a) ** 2 + (dy / b) ** 2)
        return (x + dx * s, y + dy * s)
    hw, hh = (AW / 2, AH / 2) if t == 'a' else (GW / 2, GH / 2)
    s = min(hw / abs(dx) if dx else 1e9, hh / abs(dy) if dy else 1e9)
    return (x + dx * s, y + dy * s)


def rel(k1, k2, lab, rad=0.0, lpos=0.5, dx=0.0, dy=None, color=INK, ls='-', t1=None, t2=None):
    p1 = nodes[k1][1:]; p2 = nodes[k2][1:]
    a1 = anchor(k1, t1 if t1 else p2); a2 = anchor(k2, t2 if t2 else p1)
    if dy is None:
        dy = 0.075 if abs(a1[1] - a2[1]) < 0.02 else 0.0
    arrow(ax, a1, a2, color=color, lw=0.75, ms=5.5, cs=f'arc3,rad={rad}', z=3, ls=ls)
    mx = a1[0] + (a2[0] - a1[0]) * lpos + dx; my = a1[1] + (a2[1] - a1[1]) * lpos + dy
    if lab:
        ax.text(mx, my, lab, ha='center', va='center', fontsize=5.2, style='italic', color=color, zorder=6,
                bbox=dict(boxstyle='round,pad=0.03', fc='white', ec='none', alpha=0.0 if dy else 0.9))


ax.text(0.04, 3.55, '(a)', fontsize=7.2, fontweight='bold', va='center', rotation=90)
# agents
agt('P', X[1], Y1, 'Pipeline service\n(versioned)')
agt('A', X[5], Y1, 'Analyst')
agt('S', X[0], Y4, 'Label source\n(AV consensus)')
# main flow
ent('s', X[0], Y2, 'Sample $i$\n(SHA-256 id)')
act('acq', X[1], Y2, 'Acquire')
ent('x', X[2], Y2, 'Vector $x$\n(vector hash)')
act('iss', X[3], Y2, 'Issue')
ent('F', X[4], Y2, 'Finding $F_i$')
act('amd', X[5], Y2, 'Re-validate\n& amend')
ent('F2', X[6], Y2, "Finding $F_i'$\n(revision)")
ent('E', X[3], Y1, 'Explanation $E_i$\n(grouped SHAP)')
# models, certificates, monitoring
ent('M', X[0], Y3, 'Manifest $M_v$\n(Merkle root)')
act('trn', X[1], Y3, 'Train')
ent('f', X[2], Y3, 'Model $f_v$\n(tree hash)')
ent('C', X[3], Y3, 'Certificate\n$C_{v,m}$')
act('mon', X[4], Y3, 'Monitor')
ent('a', X[5], Y3, 'Trigger $a$')
ent('R', X[6], Y3, 'Report')
ent('O', X[1], Y4, 'Oracle $O_u$\n(Merkle root)')
act('cer', X[3], Y4, 'Certify')

rel('acq', 's', 'used'); rel('x', 'acq', 'genBy'); rel('iss', 'x', 'used'); rel('F', 'iss', 'genBy')
rel('amd', 'F', 'used'); rel('F2', 'amd', 'genBy')
rel('F2', 'F', '', rad=0.30, color=RED, t1=(X[6] - 0.25, Y2 + 1), t2=(X[4] + 0.25, Y2 + 1))
ax.text(X[5] + 0.42, Y2 + 0.40, 'revOf', fontsize=5.2, style='italic', color=RED, ha='center', va='center', zorder=6)
rel('x', 's', '', rad=-0.30, t1=(X[2] - 0.25, Y2 - 1), t2=(X[0] + 0.25, Y2 - 1))
ax.text(X[1], Y2 - 0.38, 'derFrom (declared extractor)', fontsize=5.2, style='italic', ha='center', va='center', zorder=6)
rel('E', 'iss', 'genBy', lpos=0.45); rel('iss', 'f', 'used', lpos=0.42); rel('iss', 'C', 'used', lpos=0.55)
rel('f', 'trn', 'genBy'); rel('trn', 'M', 'used'); rel('trn', 'O', 'used', lpos=0.5)
rel('C', 'cer', 'genBy', lpos=0.5); rel('cer', 'f', 'used', lpos=0.5); rel('cer', 'O', 'used')
rel('mon', 'F', 'used', lpos=0.5); rel('a', 'mon', 'genBy'); rel('C', 'mon', 'invBy', color=RED)
rel('amd', 'a', 'used', lpos=0.5); rel('R', 'F2', 'derFrom', lpos=0.5)
rel('acq', 'P', 'assoc', lpos=0.5); rel('iss', 'P', 'assoc', lpos=0.55); rel('amd', 'A', 'assoc', lpos=0.5)
rel('O', 'S', '')
ax.text((X[0] + X[1]) / 2 + 0.02, Y4 + 0.19, 'attrTo', fontsize=5.2, style='italic', ha='center', va='center', zorder=6)

# legend for panel (a)
lx, ly = 4.60, 2.62
ax.add_patch(Ellipse((lx + 0.14, ly + 0.10), 0.26, 0.13, fc=ENT[0], ec=ENT[1], lw=0.7)); ax.text(lx + 0.32, ly + 0.10, 'entity', va='center', fontsize=5.6)
ax.add_patch(Rectangle((lx + 0.78, ly + 0.045), 0.22, 0.11, fc=ACT[0], ec=ACT[1], lw=0.7)); ax.text(lx + 1.05, ly + 0.10, 'activity', va='center', fontsize=5.6)
ax.add_patch(Polygon([(lx + 1.56, ly + 0.045), (lx + 1.78, ly + 0.045), (lx + 1.78, ly + 0.13), (lx + 1.67, ly + 0.17), (lx + 1.56, ly + 0.13)], closed=True,
                     fc=AGT[0], ec=AGT[1], lw=0.7)); ax.text(lx + 1.83, ly + 0.10, 'agent', va='center', fontsize=5.6)
ax.text(lx, ly - 0.10, 'used, genBy = wasGeneratedBy, derFrom = wasDerivedFrom,\nrevOf = wasRevisionOf (PROV-O), invBy = wasInvalidatedBy,\nassoc = wasAssociatedWith, attrTo = wasAttributedTo',
        va='top', fontsize=5.3, color=GRAY, linespacing=1.12)

# ---------------- (b) lifecycle of an issued finding
ax.add_line(Line2D([0.10, 7.06], [2.16, 2.16], color='#BBBBBB', lw=0.5))
ax.text(0.04, 1.08, '(b)', fontsize=7.2, fontweight='bold', va='center', rotation=90)
SW, SH = 1.22, 0.34
states = {
    'ISS': (1.05, 1.62, 'ISSUED\n(valid certificate)', True),
    'SCR': (1.05, 1.02, 'SCREENING ONLY\n(no valid certificate)', False),
    'ABS': (1.05, 0.42, 'ABSTAINED\n(referred, no verdict)', False),
    'UND': (2.85, 1.32, 'UNDER\nRE-VALIDATION', False),
    'CON': (4.72, 1.80, 'CONFIRMED\n(reviewed, unchanged)', True),
    'COR': (4.72, 1.34, 'CORRECTED\n(reviewed, amended)', True),
    'AUT': (4.72, 0.88, 'AUTO-AMENDED\n(beyond $B$, $q_i \\geq \\gamma$)', False),
    'FLG': (4.72, 0.42, 'FLAGGED-PENDING\n(beyond $B$, $q_i < \\gamma$)', False),
    'REC': (6.45, 1.10, 'RECONCILED\n(label matured)', True),
}
for k, (x, y, txt, ev) in states.items():
    ax.add_patch(FancyBboxPatch((x - SW / 2, y - SH / 2), SW, SH, boxstyle='round,pad=0,rounding_size=0.08',
                                fc='#FFFFFF' if not ev else '#EEF5EE', ec='#2E5E3A' if ev else '#7A5A1E', lw=1.5 if ev else 0.8, zorder=4))
    ax.text(x, y, txt, ha='center', va='center', fontsize=6.0, zorder=5, linespacing=1.05, fontweight='bold' if ev else 'normal')
st = states
L_ = lambda k: (st[k][0] - SW / 2, st[k][1]); R_ = lambda k: (st[k][0] + SW / 2, st[k][1])
T_ = lambda k: (st[k][0], st[k][1] + SH / 2); B_ = lambda k: (st[k][0], st[k][1] - SH / 2)


def sedge(p1, p2, color=INK, ls='-', rad=0.0, z=3):
    arrow(ax, p1, p2, color=color, lw=0.75, ms=5.5, cs=f'arc3,rad={rad}', z=z, ls=ls)


def slab(x, y, txt, color=INK, ha='center'):
    ax.text(x, y, txt, ha=ha, va='center', fontsize=5.3, style='italic', color=color, zorder=6, linespacing=1.05,
            bbox=dict(boxstyle='round,pad=0.04', fc='white', ec='none', alpha=0.95))


# entry
ax.add_patch(plt.Circle((0.22, 1.02), 0.05, color=INK, zorder=5))
ax.text(0.22, 0.92, 'issue', ha='center', va='top', fontsize=5.3, style='italic')
sedge((0.26, 1.06), (L_('ISS')[0], 1.56), rad=-0.2); sedge((0.27, 1.02), L_('SCR')); sedge((0.26, 0.98), (L_('ABS')[0], 0.48), rad=0.2)
# into re-validation
sedge(R_('ISS'), (L_('UND')[0], 1.40), color=RED); slab(1.98, 1.64, 'trigger $a$, $i \\in R_a$', color=RED)
sedge(R_('SCR'), (L_('UND')[0], 1.24), color=RED); slab(1.98, 1.06, '$i \\in R_a$', color=RED)
# fan-out
ux = R_('UND')[0]
for k, dy_, lab, ly_ in [('CON', 0.12, 'reviewed, unchanged', 1.86), ('COR', 0.04, 'reviewed, changed', 1.44),
                         ('AUT', -0.04, 'beyond $B$, $q_i \\geq \\gamma$', 1.04), ('FLG', -0.12, 'beyond $B$, $q_i < \\gamma$', 0.62)]:
    sedge((ux, st['UND'][1] + dy_), L_(k))
# next trigger loop (below everything)
path(ax, [(L_('FLG')[0], 0.34), (3.05, 0.34), (3.05, B_('UND')[1])], color=RED, lw=0.75, ms=5.5, z=3)
slab(3.55, 0.34, 'next trigger', color=RED)
# reconciliation at label maturity (dashed)
path(ax, [T_('ISS'), (st['ISS'][0], 2.06), (6.45, 2.06), T_('REC')], color=GRAY, lw=0.75, ls=(0, (2, 1.4)), ms=5.5, z=3)
slab(5.60, 2.06, 'label matures at $t_i + L$ (no trigger)', color=GRAY)
sedge(R_('AUT'), (L_('REC')[0], 1.04), color=GRAY, ls=(0, (2, 1.4)))
sedge(R_('FLG'), (L_('REC')[0] + 0.12, B_('REC')[1]), color=GRAY, ls=(0, (2, 1.4)))
slab(6.42, 0.66, 'label matures\nat $t_i + L$', color=GRAY)
# legend (b)
ax.add_patch(FancyBboxPatch((1.80, 0.52), 0.22, 0.11, boxstyle='round,pad=0,rounding_size=0.03', fc='#EEF5EE', ec='#2E5E3A', lw=1.5))
ax.text(2.08, 0.575, 'evaluative use permitted', va='center', fontsize=5.4)
ax.add_patch(FancyBboxPatch((1.80, 0.33), 0.22, 0.11, boxstyle='round,pad=0,rounding_size=0.03', fc='white', ec='#7A5A1E', lw=0.8))
ax.text(2.08, 0.385, 'investigative lead only', va='center', fontsize=5.4)
ax.text(1.80, 0.17, 'each transition appends a TRG, RVC,\nREV, AMD or EXPY ledger record', va='center', fontsize=5.1, color=GRAY, linespacing=1.05)
save(fig, 'fig3_conceptual', os.path.join(HERE, 'out'))
print('ok')
