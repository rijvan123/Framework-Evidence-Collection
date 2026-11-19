"""Shared drawing helpers for the S7 R3 diagrams (IEEE double-column, vector output)."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Polygon, Ellipse, Rectangle
from matplotlib.lines import Line2D

FONT = 'Liberation Sans'
plt.rcParams.update({
    'font.family': 'sans-serif', 'font.sans-serif': [FONT, 'DejaVu Sans'],
    'font.size': 7, 'pdf.fonttype': 42, 'ps.fonttype': 42, 'svg.fonttype': 'none',
    'axes.linewidth': 0.6, 'lines.linewidth': 0.8, 'mathtext.fontset': 'custom',
    'mathtext.rm': FONT, 'mathtext.it': FONT + ':italic', 'mathtext.bf': FONT + ':bold',
})

# Muted, grayscale-separable palette (fill, edge) per plane
PAL = {
    'evid': ('#E9EFF5', '#2F4B66'),
    'anal': ('#EAF3EA', '#2E5E3A'),
    'assu': ('#F7F0E1', '#7A5A1E'),
    'repo': ('#F0ECF5', '#4F3F6B'),
    'ledg': ('#F3F3F3', '#1F1F1F'),
    'ext':  ('#FFFFFF', '#555555'),
}
INK = '#1F1F1F'
RED = '#8E2C2C'
GRAY = '#6B6B6B'


def canvas(w, h):
    fig = plt.figure(figsize=(w, h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w); ax.set_ylim(0, h); ax.axis('off')
    return fig, ax


def band(ax, x, y, w, h, label, key, fs=7.5):
    fc, ec = PAL[key]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=0.06',
                                fc=fc, ec=ec, lw=0.7, zorder=0))
    ax.text(x + 0.11, y + h / 2, label, rotation=90, ha='center', va='center', fontsize=fs,
            fontweight='bold', color=ec, zorder=1)


def box(ax, x, y, w, h, title, body=None, key='evid', fill='#FFFFFF', tfs=7.4, bfs=6.5,
        lw=0.8, ls='-', ledger_mark=False, title_color=None, body_ls=1.18, z=3, rounding=0.05):
    fc, ec = PAL[key]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f'round,pad=0,rounding_size={rounding}',
                                fc=fill, ec=ec, lw=lw, ls=ls, zorder=z))
    ty = y + h - 0.07
    ax.text(x + w / 2, ty, title, ha='center', va='top', fontsize=tfs, fontweight='bold',
            color=title_color or ec, zorder=z + 1, linespacing=1.05)
    if body:
        nt = title.count('\n') + 1
        by = ty - nt * tfs / 72 * 1.12 - 0.035
        ax.text(x + w / 2, by, body, ha='center', va='top', fontsize=bfs, color=INK,
                zorder=z + 1, linespacing=body_ls)
    if ledger_mark:
        s = 0.075
        ax.add_patch(Rectangle((x + w - s - 0.035, y + 0.035), s, s, fc=INK, ec=INK, lw=0, zorder=z + 2))


def arrow(ax, p1, p2, color=INK, lw=0.8, ls='-', ms=6, cs='arc3,rad=0', z=5, style='-|>'):
    a = FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=ms, color=color, lw=lw,
                        linestyle=ls, connectionstyle=cs, zorder=z, shrinkA=0, shrinkB=0)
    ax.add_patch(a)
    return a


def path(ax, pts, color=INK, lw=0.8, ls='-', ms=6, z=5, head=True):
    """Orthogonal poly-line through pts; arrowhead on the last segment."""
    for i in range(len(pts) - 2):
        ax.add_line(Line2D([pts[i][0], pts[i + 1][0]], [pts[i][1], pts[i + 1][1]], color=color,
                           lw=lw, ls=ls, zorder=z, solid_capstyle='butt', dash_capstyle='butt'))
    if head:
        arrow(ax, pts[-2], pts[-1], color=color, lw=lw, ls=ls, ms=ms, z=z)
    else:
        ax.add_line(Line2D([pts[-2][0], pts[-1][0]], [pts[-2][1], pts[-1][1]], color=color, lw=lw, ls=ls, zorder=z))


def label(ax, x, y, s, fs=6.0, color=INK, ha='center', va='center', bg=True, z=7, style='normal', weight='normal'):
    kw = dict(fontsize=fs, color=color, ha=ha, va=va, zorder=z, style=style, fontweight=weight)
    if bg:
        kw['bbox'] = dict(boxstyle='round,pad=0.08', fc='white', ec='none', alpha=0.95)
    ax.text(x, y, s, **kw)


def save(fig, stem, outdir):
    import os
    os.makedirs(outdir, exist_ok=True)
    fig.savefig(os.path.join(outdir, stem + '.pdf'))
    fig.savefig(os.path.join(outdir, stem + '.svg'))
    fig.savefig(os.path.join(outdir, stem + '.png'), dpi=300)
    plt.close(fig)
