"""Result figures of the paper (Figs. 5-21) rebuilt from the run outputs in ``out/``.

Each figure is written as PNG (200 dpi) and PDF to ``<run>/figures``. A figure whose inputs are missing is
skipped. Every figure carries the run label (``run.label`` in the configuration) in its lower-right corner, so
that figures from the synthetic smoke run cannot be mistaken for results.
"""
from __future__ import annotations

import math

import matplotlib

matplotlib.use('Agg')
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter  # noqa: E402
import numpy as np  # noqa: E402

from ..evaluation import metrics as M  # noqa: E402
from ..features.groups import GROUP_NAMES  # noqa: E402
from ..models.zoo import DISPLAY  # noqa: E402
from ..utils import load_json, log, month_list  # noqa: E402

plt.rcParams.update({'font.size': 7, 'axes.titlesize': 7.5, 'axes.labelsize': 7, 'legend.fontsize': 6, 'xtick.labelsize': 6,
                     'ytick.labelsize': 6, 'axes.linewidth': 0.6, 'lines.linewidth': 1.0, 'pdf.fonttype': 42, 'ps.fonttype': 42,
                     'axes.spines.top': False, 'axes.spines.right': False})

F0C = '#D55E00'              # f0 family / measured on this run
RFP = '#2B6CB0'              # reproduced from paper
GREY = '#9A9A9A'
COLORS = {'lgbm_trace': F0C, 'lgbm_ember': '#0072B2', 'xgboost': '#009E73', 'rf': '#CC79A7', 'et': '#56B4E9', 'stack': '#E69F00',
          'ember2018_pub': '#222222'}
TREES = list(COLORS)


def color(key):
    return COLORS.get(key, GREY)


def disp(key):
    return DISPLAY.get(key, key)


def _ok(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v is not None and math.isfinite(v)


def _mlabel(mo):
    y, m = mo.split('-')
    return ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][int(m) - 1] + f' {y[2:]}'


def _stamp(fig, cfg):
    lab = cfg['run'].get('label', 'measured on this run')
    fig.text(0.995, 0.003, lab, ha='right', va='bottom', fontsize=5.5, color='#B00020' if 'SYNTHETIC' in lab.upper() else '#555555')


def _save(fig, run, cfg, name):
    _stamp(fig, cfg)
    run.figs.mkdir(parents=True, exist_ok=True)
    paths = []
    for ext in ('png', 'pdf'):
        p = run.figs / f'{name}.{ext}'
        fig.savefig(p, dpi=200, bbox_inches='tight')
        paths.append(p)
    plt.close(fig)
    return paths


def _logx(ax, axis='x'):
    """Log axis with ticks at 1-2-5 steps and compact labels (no overlapping minor labels)."""
    ax_ = ax.xaxis if axis == 'x' else ax.yaxis
    (ax.set_xscale if axis == 'x' else ax.set_yscale)('log')
    ax_.set_major_locator(LogLocator(base=10, subs=(1.0, 2.0, 5.0)))
    ax_.set_major_formatter(FuncFormatter(lambda v, _: f'{v:g}'))
    ax_.set_minor_formatter(NullFormatter())


def _mets(c, cfg):
    return M.from_counts(c['tp'], c['fp'], c['fn'], c['tn'], cfg['prevalence']['report'], cfg['prevalence']['precision'])


def _seed_series(raw, key, rule, months, field, cfg):
    """(mean, min, max) per month over the seeds of one model."""
    seeds = raw['models'].get(key, {})
    vals = np.array([[_mets(seeds[s][mo]['counts'][rule], cfg)[field] for mo in months] for s in seeds], float)
    if vals.size == 0:
        return None
    with np.errstate(all='ignore'):
        return np.nanmean(vals, 0), np.nanmin(vals, 0), np.nanmax(vals, 0)


# ------------------------------------------------------------------ Fig. 5
def fig05(O, cfg, run):
    zoo = O['e1_metrics']['zoo']
    keys = list(zoo)
    pi = cfg['prevalence']['report']
    panels = [('tpr', 'TPR (%)', 'bar'), ('fnr', 'FNR (%)', 'bar'), ('f1_pi', f'F1 @π={pi:.0%} (%)', 'bar'), ('mcc_pi', f'MCC @π={pi:.0%} (%)', 'bar'),
              ('prec_pi', f'Precision @π={cfg["prevalence"]["precision"]:.0%} (%)', 'bar'), ('aucpr', f'AUC-PR @π={pi:.0%} (%)', 'dot'),
              ('auc', 'AUC-ROC (%)', 'dot'), ('fpr', 'FPR (%), log scale', 'log')]
    fig, axes = plt.subplots(2, 4, figsize=(7.2, 0.17 * len(keys) * 2 + 1.2), sharey=True)
    y = np.arange(len(keys))
    for ax, (f, title, kind) in zip(axes.flat, panels):
        for i, k in enumerate(keys):
            a = zoo[k]['agg']
            v = a.get(f, {}).get('mean')
            if not _ok(v):
                ax.text(0.02, i, '—', va='center', fontsize=5.5, transform=ax.get_yaxis_transform())
                continue
            if len(zoo[k]['seeds']) > 1:
                lo, hi = a[f]['min'], a[f]['max']
            else:
                ci = a.get('auc_ci') if f == 'auc' else a.get('ci', {}).get({'prec_pi': 'precision_pi_prec'}.get(f, f))
                lo, hi = (ci if ci else [v, v])
            lo = v if not _ok(lo) else lo
            hi = v if not _ok(hi) else hi
            err = [[max(0.0, (v - lo) * 100)], [max(0.0, (hi - v) * 100)]]
            if kind == 'bar':
                ax.barh(i, v * 100, color=color(k), height=0.7)
                ax.errorbar(v * 100, i, xerr=err, fmt='none', ecolor='k', lw=0.6, capsize=1.2)
            elif kind == 'dot':
                ax.errorbar(v * 100, i, xerr=err, fmt='o', color=color(k), ms=2.8, ecolor='k', elinewidth=0.6, capsize=1.2)
            else:
                floor = 1e-4
                ax.errorbar(max(v * 100, floor), i, xerr=None, fmt='o' if v > 0 else 'x', color=color(k), ms=2.8)
                if v == 0:
                    ax.text(floor * 1.4, i, '0', va='center', fontsize=5)
        ax.set_title(title)
        if kind == 'log':
            _logx(ax)
        ax.grid(axis='x', lw=0.3, alpha=0.5)
    axes[0, 0].set_yticks(y)
    axes[0, 0].set_yticklabels([disp(k) for k in keys])
    axes[0, 0].invert_yaxis()
    fig.tight_layout()
    return _save(fig, run, cfg, 'fig5_metric_bars')


# ------------------------------------------------------------------ Fig. 6
def fig06(O, cfg, run):
    curves = O['e1_metrics']['curves']
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.6))
    order = [k for k in curves if k not in TREES] + [k for k in curves if k in TREES and k != 'lgbm_trace'] + (['lgbm_trace'] if 'lgbm_trace' in curves else [])
    for k in order:
        c = curves[k]
        main = k in TREES
        kw = dict(color=color(k), lw=1.3 if k == 'lgbm_trace' else (0.9 if main else 0.5), alpha=1 if main else 0.7,
                  label=disp(k) if main else None, zorder=3 if main else 1)
        fpr = np.asarray(c['roc']['fpr'], float) * 100
        axes[0].plot(np.maximum(fpr, 1e-3), np.asarray(c['roc']['tpr']) * 100, **kw)
        axes[1].plot(np.asarray(c['pr10']['recall']) * 100, np.asarray(c['pr10']['precision']) * 100, **kw)
        axes[2].plot(np.asarray(c['pr1']['recall']) * 100, np.asarray(c['pr1']['precision']) * 100, **kw)
    _logx(axes[0])
    axes[0].set_xlim(1e-3, 100)
    for x in (0.1, 1):
        axes[0].axvline(x, color='k', lw=0.4, ls=':')
    axes[0].set_xlabel('FPR (%), log scale')
    axes[0].set_ylabel('TPR (%)')
    axes[0].set_title('ROC (grey: remaining models)')
    for ax, pi in ((axes[1], cfg['prevalence']['report']), (axes[2], cfg['prevalence']['precision'])):
        ax.set_xlabel('Recall (%)')
        ax.set_ylabel('Precision (%)')
        ax.set_title(f'Precision–recall at π = {pi:.0%} (Eq. 70 weights)')
    axes[0].legend(loc='lower right', frameon=False)
    fig.tight_layout()
    return _save(fig, run, cfg, 'fig6_roc_pr')


# ------------------------------------------------------------------ Fig. 7
def _cm(ax, cm, title, fmt='{:,.0f}'):
    m = np.array([[cm['tn'], cm['fp']], [cm['fn'], cm['tp']]], float)
    rate = m / np.maximum(m.sum(1, keepdims=True), 1e-12)
    ax.imshow(rate, cmap='Blues', vmin=0, vmax=1)
    for i in range(2):
        for j in range(2):
            ax.text(j, i, fmt.format(m[i, j]), ha='center', va='center', fontsize=6, color='white' if rate[i, j] > 0.6 else 'black')
    ax.set_xticks([0, 1])
    ax.set_xticklabels(['pred. benign', 'pred. malicious'], fontsize=5.5)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(['benign', 'malware'], fontsize=5.5)
    ax.set_title(title, fontsize=6.2)


def fig07(O, cfg, run):
    e1 = O['e1_metrics']
    conf = e1['confusion']
    prim = e1['primary_rule']
    f0 = conf.get('f0_' + prim)
    if f0 is None:
        return []
    mt = _mets(f0, cfg)
    exp = {}
    for pi in (cfg['prevalence']['report'], cfg['prevalence']['precision']):
        n = 10000
        exp[pi] = dict(tp=pi * n * mt['tpr'], fn=pi * n * (1 - mt['tpr']), fp=(1 - pi) * n * mt['fpr'], tn=(1 - pi) * n * (1 - mt['fpr']))
    others = [k for k in conf if not k.startswith('f0_')][:4]
    ncol = 4
    fig, axes = plt.subplots(2 if others else 1, ncol, figsize=(7.2, 3.6 if others else 1.9), squeeze=False)
    _cm(axes[0, 0], f0, f'f₀ at θ@{prim[2:]}: measured')
    for j, pi in enumerate(exp, start=1):
        _cm(axes[0, j], exp[pi], f'f₀ expected per 10,000 at π = {pi:.0%}', '{:,.1f}')
    if 'f0_default' in conf:
        _cm(axes[0, 3], conf['f0_default'], 'f₀ at default threshold')
    else:
        axes[0, 3].axis('off')
    for j in range(ncol):
        if others and j < len(others):
            k = others[j]
            key = k.rsplit('_', 1)[0]
            _cm(axes[1, j], conf[k], f'{disp(key)} at θ@{prim[2:]}')
        elif others:
            axes[1, j].axis('off')
    fig.tight_layout()
    return _save(fig, run, cfg, 'fig7_confusion')


# ------------------------------------------------------------------ Fig. 8
def fig08(O, cfg, run):
    raw = O['e1_metrics_raw']
    prim = raw['rules'][0]
    a, b = cfg['screen']['test_months']
    tm = month_list(a, b)
    a, b = cfg['screen']['certify_months']
    cm = month_list(a, b)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.7))
    keys = [k for k in raw['models'] if k not in TREES] + [k for k in TREES if k in raw['models']]
    for k in keys:
        main = k in TREES
        lw = 1.4 if k == 'lgbm_trace' else (0.9 if main else 0.4)
        s = _seed_series(raw, k, prim, tm, 'fnr', cfg)
        if s is not None:
            axes[0].plot(range(len(tm)), s[0] * 100, color=color(k), lw=lw, alpha=1 if main else 0.6, label=disp(k) if main else None)
            if main and len(raw['models'][k]) > 1:
                axes[0].fill_between(range(len(tm)), s[1] * 100, s[2] * 100, color=color(k), alpha=0.15, lw=0)
        s = _seed_series(raw, k, prim, cm, 'f1_pi', cfg)
        if s is not None and main:
            aut = M.aut(list(s[0]))
            axes[1].plot(range(len(cm)), s[0] * 100, color=color(k), lw=lw, label=f'{disp(k)} (AUT {aut:.3f})' if _ok(aut) else disp(k))
            if len(raw['models'][k]) > 1:
                axes[1].fill_between(range(len(cm)), s[1] * 100, s[2] * 100, color=color(k), alpha=0.15, lw=0)
    axes[0].set_xticks(range(len(tm)))
    axes[0].set_xticklabels([_mlabel(m) for m in tm], rotation=45)
    axes[0].set_ylabel('FNR (%)')
    axes[0].set_title(f'FNR at the certified threshold ({prim})')
    axes[1].set_xticks(range(len(cm)))
    axes[1].set_xticklabels([_mlabel(m) for m in cm], rotation=45)
    axes[1].set_ylabel(f'F1 @π={cfg["prevalence"]["report"]:.0%} (%)')
    axes[1].set_title('F1 at the deployment prevalence (AUT in legend)')
    axes[0].legend(frameon=False, fontsize=5.5)
    axes[1].legend(frameon=False, fontsize=5.2)
    fig.tight_layout()
    return _save(fig, run, cfg, 'fig8_temporal_decay')


# ------------------------------------------------------------------ Fig. 9
def fig09(O, cfg, run):
    e2 = O['e2_certificates']
    rules = list(e2['certificates'])
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6))
    for j, r in enumerate(rules[:2]):
        certs = e2['certificates'][r]
        months = list(certs)
        x = np.arange(len(months)) + (j - 0.5) * 0.18
        col = [F0C, '#0072B2'][j]
        for ax, f in ((axes[0], 'fpr'), (axes[1], 'fnr')):
            v = np.array([certs[m][f] if _ok(certs[m][f]) else np.nan for m in months]) * 100
            ub = np.array([certs[m][f + '_ub'] if _ok(certs[m][f + '_ub']) else np.nan for m in months]) * 100
            ax.errorbar(x, v, yerr=[np.zeros_like(v), np.where(np.isfinite(ub), ub - v, 0)], fmt='o', ms=2.8, color=col, capsize=1.5,
                        elinewidth=0.7, label=f'θ@{r[2:]} (k* = {e2["thresholds"][r]["k_star"]})')
            tol = certs[months[-1]]['tau_' + f]
            ax.axhline(tol * 100, color=col, lw=0.6, ls='--')
    for ax, t in ((axes[0], 'FPR (%): point and one-sided 95% CP upper bound'), (axes[1], 'FNR (%): point and upper bound')):
        ax.set_xticks(range(len(months)))
        ax.set_xticklabels([_mlabel(m) for m in months], rotation=45)
        ax.set_title(t)
        ax.legend(frameon=False)
    axes[0].set_yscale('symlog', linthresh=0.1)
    fig.tight_layout()
    return _save(fig, run, cfg, 'fig9_certificates')


# ------------------------------------------------------------------ Fig. 10
def fig10(O, cfg, run):
    st = O['e1_metrics']['streams']
    pis = np.logspace(-3, math.log10(0.5), 80)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6), gridspec_kw=dict(width_ratios=[1.6, 1]))
    cmap = plt.get_cmap('viridis')
    months = list(st)
    for i, mo in enumerate(months):
        v = st[mo]
        tpr, fpr = v['tpr'], v['fpr']
        prec = [M.precision_analytic(tpr, fpr, float(q)) for q in pis]
        c = cmap(i / max(1, len(months) - 1))
        axes[0].plot(pis * 100, np.asarray(prec) * 100, color=c, lw=0.9, label=_mlabel(mo))
        for p in cfg['prevalence']['streams']:
            s = v.get(str(p))
            if s:
                axes[0].errorbar(p * 100, s['mean'] * 100, yerr=[[max(0, (s['mean'] - s['lo']) * 100)], [max(0, (s['hi'] - s['mean']) * 100)]],
                                 fmt='o', ms=2.5, color=c, capsize=1)
    _logx(axes[0])
    axes[0].set_xlabel('Deployment prevalence π (%)')
    axes[0].set_ylabel('Precision (%)')
    axes[0].set_title('Certified threshold: Eq. (55) curves, resampled streams (points)')
    axes[0].legend(frameon=False, ncol=2)
    x = np.arange(len(months))
    for j, (p, lab) in enumerate(((0.001, 'π = 0.1%'), (0.01, 'π = 1%'))):
        cert = [M.precision_analytic(st[m]['tpr'], st[m]['fpr'], p) * 100 for m in months]
        dflt = [(st[m].get('default') or {}).get(str(p), np.nan) * 100 for m in months]
        axes[1].plot(x, cert, marker='o', ms=2.5, color=F0C, ls='-' if j else '--', label=f'certified θ, {lab}')
        axes[1].plot(x, dflt, marker='s', ms=2.5, color=GREY, ls='-' if j else '--', label=f'default θ, {lab}')
    axes[1].set_xticks(x)
    axes[1].set_xticklabels([_mlabel(m) for m in months], rotation=45)
    axes[1].set_ylabel('Precision (%)')
    axes[1].set_title('Certified versus default threshold')
    axes[1].legend(frameon=False)
    fig.tight_layout()
    return _save(fig, run, cfg, 'fig10_base_rate')


# ------------------------------------------------------------------ Fig. 11
def fig11(O, cfg, run):
    e5 = O['e5_errors_drift']
    dr = e5['drift']
    months = list(dr)
    H = np.array([[dr[m]['groups'][g] for m in months] for g in GROUP_NAMES]) * 1e3
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.7), gridspec_kw=dict(width_ratios=[1.7, 1]))
    im = axes[0].imshow(H, aspect='auto', cmap='magma_r')
    axes[0].set_yticks(range(len(GROUP_NAMES)))
    axes[0].set_yticklabels(GROUP_NAMES)
    axes[0].set_xticks(range(len(months)))
    axes[0].set_xticklabels([_mlabel(m) for m in months], rotation=45)
    axes[0].set_title('Jensen–Shannon divergence per EMBER group (×10³ bits)')
    fig.colorbar(im, ax=axes[0], fraction=0.04)
    a, b = cfg['screen']['certify_months']
    cm = [m for m in month_list(a, b) if m in dr]
    xs = [dr[m]['pooled'] * 1e3 for m in cm]
    ys = [dr[m]['f1_pi'] * 100 if _ok(dr[m]['f1_pi']) else np.nan for m in cm]
    axes[1].scatter(xs, ys, color=F0C, s=12)
    for m, xx, yy in zip(cm, xs, ys):
        axes[1].annotate(_mlabel(m), (xx, yy), fontsize=5, xytext=(2, 2), textcoords='offset points')
    p5 = e5['P5']
    axes[1].set_title(f'Global drift vs F1 (P5: ρ = {p5["rho"]:.2f}, p = {p5["p"]:.2g})')
    axes[1].set_xlabel('D(t) ×10³ (bits)')
    axes[1].set_ylabel(f'F1 @π={cfg["prevalence"]["report"]:.0%} (%)')
    fig.tight_layout()
    return _save(fig, run, cfg, 'fig11_drift')


# ------------------------------------------------------------------ Fig. 12
def fig12(O, cfg, run):
    e6 = O['e6_monitor']
    W = e6['windows']
    if not W:
        return []
    import datetime as _dt
    dates = [_dt.date.fromisoformat(w['start']) for w in W]
    stats = [('c2st', 'C2ST AUC (T5)'), ('ks', 'KS on margins (T1)'), ('psi', 'mean PSI (T2)'), ('cred', '1 − mean credibility (T3)')]
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 4.0), sharex=True)
    onset = e6['KT'].get('onset')
    for ax, (s, t) in zip(axes.flat, stats):
        for cls, col, lab in (('0', '#0072B2', 'pred. benign'), ('1', F0C, 'pred. malicious')):
            vals = [w['stats'][cls][s] if _ok(w['stats'][cls].get(s)) else np.nan for w in W]
            ax.plot(dates, vals, color=col, lw=0.9, marker='o', ms=1.8, label=lab)
            lam = e6['lambda_'][cls][s]
            if _ok(lam):
                ax.axhline(lam, color=col, lw=0.6, ls='--')
        if onset:
            ax.axvline(_dt.date.fromisoformat(onset), color='#B00020', lw=0.8)
        for d in e6['KT'].get('alarm_days', []):
            ax.axvline(_dt.date.fromisoformat(d), color='k', lw=0.5, ls=':')
        ax.set_title(t)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    axes[0, 0].legend(frameon=False)
    fig.suptitle('Label-free monitor: weekly windows; dashed = λ (max over blocked null); red = onset week; dotted = alarms', fontsize=7)
    fig.tight_layout()
    return _save(fig, run, cfg, 'fig12_monitor')


# ------------------------------------------------------------------ Fig. 13
def fig13(O, cfg, run):
    e9 = O['e9_explain_issue']
    G = e9['groups']
    names = [g['group'] for g in G]
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.7), gridspec_kw=dict(width_ratios=[1, 1.3, 1.2]))
    y = np.arange(len(G))
    axes[0].barh(y, [g['mean_abs_shap'] for g in G], color=F0C)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(names)
    axes[0].invert_yaxis()
    axes[0].set_title('Mean |grouped TreeSHAP| (margin)')
    w = 0.27
    for j, (f, lab, col) in enumerate((('shap_share', '|SHAP|', F0C), ('gain_share', 'LightGBM gain', '#0072B2'), ('lr_share', 'LR |coef.|', GREY))):
        axes[1].barh(y + (j - 1) * w, [g[f] * 100 for g in G], height=w, color=col, label=lab)
    axes[1].set_yticks(y)
    axes[1].set_yticklabels([])
    axes[1].invert_yaxis()
    axes[1].set_title('Share of importance per group (%)')
    axes[1].legend(frameon=False)
    T = e9['top_gain_features'][:15]
    axes[2].barh(range(len(T)), [t['gain_share'] * 100 for t in T], color='#0072B2')
    axes[2].set_yticks(range(len(T)))
    axes[2].set_yticklabels([f'#{t["column"]} {t["group"]}+{t["offset"]}' for t in T], fontsize=5.3)
    axes[2].invert_yaxis()
    axes[2].set_title('Top features by gain (%)')
    fig.tight_layout()
    return _save(fig, run, cfg, 'fig13_importance')


# ------------------------------------------------------------------ Fig. 14
def fig14(O, cfg, run):
    T = O['e12_cost_learning'].get('timing', [])
    if not T:
        return []
    T = sorted(T, key=lambda t: t['train_seconds'])
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 0.16 * len(T) + 1.0), sharey=True)
    y = np.arange(len(T))
    cols = [color(t['model']) for t in T]
    for ax, f, t, lg in ((axes[0], 'train_seconds', 'Training (s)', True), (axes[1], 'inference_us_per_file', 'Inference (µs per file)', True),
                         (axes[2], 'peak_rss_gb', 'Peak RSS (GB)', False)):
        ax.barh(y, [max(x[f], 1e-3) for x in T], color=cols)
        if lg:
            _logx(ax)
        ax.set_title(t)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels([disp(t['model']) for t in T])
    fig.tight_layout()
    return _save(fig, run, cfg, 'fig14_cost')


# ------------------------------------------------------------------ Fig. 15
def fig15(O, cfg, run):
    L = O['e12_cost_learning'].get('learning', {})
    if not L:
        return []
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.4))
    for k, pts in L.items():
        n = [p['rows'] for p in pts]
        axes[0].plot(n, [p['aucpr_pi'] * 100 for p in pts], color=color(k), lw=1.4, marker='o', ms=2.5, label=disp(k))
        axes[0].plot(n, [p['train_auc'] * 100 for p in pts], color=color(k), lw=0.6, ls=':')
        axes[1].plot(n, [p['fnr'] * 100 for p in pts], color=color(k), marker='o', ms=2.5)
        axes[2].plot(n, [p['fit_seconds'] for p in pts], color=color(k), marker='o', ms=2.5)
    for ax, t in zip(axes, ('AUC-PR @π (thick) and train AUC (thin), %', 'FNR at the certified threshold (%)', 'Fit time (s)')):
        _logx(ax)
        ax.set_xlabel('Training rows')
        ax.set_title(t)
    axes[0].legend(frameon=False)
    fig.tight_layout()
    return _save(fig, run, cfg, 'fig15_learning')


# ------------------------------------------------------------------ Fig. 16
def fig16(O, cfg, run):
    cv = O['e4_bias'].get('cv')
    raw = O.get('e1_metrics_raw')
    if not cv:
        return []
    a, b = cfg['screen']['certify_months']
    cm = month_list(a, b)
    prim = f'cp{cfg["thresholds"]["certified_tau"][0]:g}'
    keys = list(cv)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6))
    for j, (f, title) in enumerate((('f1_pi', f'F1 @π={cfg["prevalence"]["report"]:.0%} (%)'), ('fnr', 'FNR (%)'))):
        data, pos, cols = [], [], []
        for i, k in enumerate(keys):
            data.append([fo[f] * 100 for fo in cv[k]['folds'] if _ok(fo[f])])
            if f == 'f1_pi':
                tmp = [t * 100 for t in cv[k]['temporal_months'] if _ok(t)]
            else:
                s = _seed_series(raw, k, prim, cm, 'fnr', cfg) if raw else None
                tmp = [] if s is None else [v * 100 for v in s[0] if _ok(v)]
            data.append(tmp)
            pos += [3 * i, 3 * i + 1]
            cols += [GREY, color(k) if k in COLORS else '#444444']
        bp = axes[j].boxplot(data, positions=pos, widths=0.8, patch_artist=True, showfliers=False)
        for patch, c in zip(bp['boxes'], cols):
            patch.set_facecolor(c)
            patch.set_alpha(0.6)
        for p, d in zip(pos, data):
            axes[j].scatter([p] * len(d), d, s=4, color='k', zorder=3)
        axes[j].set_xticks([3 * i + 0.5 for i in range(len(keys))])
        axes[j].set_xticklabels([disp(k) for k in keys], rotation=30, ha='right')
        axes[j].set_title(f'{title}: random k-fold CV (grey) vs temporal months')
    fig.tight_layout()
    return _save(fig, run, cfg, 'fig16_cv_vs_temporal')


# ------------------------------------------------------------------ Fig. 17
def fig17(O, cfg, run):
    e7 = O['e7_assurance']
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.7), gridspec_kw=dict(width_ratios=[1.3, 1.2, 1]))
    ser = e7.get('series')
    labels = {p: v['label'] for p, v in e7['primary'].items()}
    if ser:
        import datetime as _dt
        d0 = _dt.date.fromisoformat(ser['start'])
        for p, col in (('frozen_none', '#222222'), ('retrain_only', '#0072B2'), ('retrain_cert', '#56B4E9'), ('retrain_kappa', '#009E73'), ('viii', F0C)):
            if p in ser['U_ev']:
                u = ser['U_ev'][p]
                axes[0].plot([d0 + _dt.timedelta(days=i) for i in range(len(u))], u, color=col, lw=0.9, label=labels.get(p, p))
        axes[0].xaxis.set_major_formatter(mdates.DateFormatter('%b'))
        axes[0].set_yscale('symlog', linthresh=1)
        axes[0].set_title('Wrong findings in evaluative states per day')
        axes[0].legend(frameon=False, fontsize=4.8)
    P = e7['primary']
    ks = list(P)
    y = np.arange(len(ks))
    for i, k in enumerate(ks):
        v = P[k]
        ci = v.get('E_ev_ci') or [v['E_ev'], v['E_ev']]
        col = F0C if k == 'trace' else ('#0072B2' if k == 'viii' else GREY)
        axes[1].errorbar(max(v['E_ev'], 0.5), i, xerr=[[max(0, v['E_ev'] - ci[0])], [max(0, ci[1] - v['E_ev'])]], fmt='o', ms=2.5, color=col,
                         ecolor=col, elinewidth=0.6, capsize=1)
    axes[1].set_yticks(y)
    axes[1].set_yticklabels([P[k]['label'] for k in ks], fontsize=4.8)
    axes[1].invert_yaxis()
    _logx(axes[1])
    axes[1].set_title('E^ev_T (finding-days), 95% block bootstrap')
    N = e7.get('noise', {})
    if N:
        rs = sorted(N, key=float)
        x = [float(r) * 100 for r in rs]
        for p, col, ls in (('trace', F0C, '-'), ('vii_margin', '#0072B2', '-'), ('vi_random', GREY, '-'), ('trace_override', F0C, '--'),
                           ('vii_margin_override', '#0072B2', '--'), ('viii', '#222222', ':')):
            axes[2].plot(x, [N[r][p] for r in rs], color=col, ls=ls, marker='o', ms=2.2, label=p.replace('_', ' '))
        axes[2].set_xlabel('Analyst error rate r (%)')
        axes[2].set_title('E^ev under analyst noise')
        axes[2].legend(frameon=False, fontsize=4.8)
    fig.tight_layout()
    return _save(fig, run, cfg, 'fig17_assurance')


# ------------------------------------------------------------------ Fig. 18
def fig18(O, cfg, run):
    e8 = O['e8_attribution']
    months = list(e8['months'])
    V = e8['months']
    x = np.arange(len(months))
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.4))
    for f, lab, col in (('top1_known', 'top-1, known families', F0C), ('top3_known', 'top-3, known families', '#E69F00'),
                        ('top1_all', 'top-1, all non-generic', '#0072B2'), ('closed_bound', 'closed-world bound 1 − ν', '#222222')):
        axes[0].plot(x, [V[m][f] * 100 if _ok(V[m][f]) else np.nan for m in months], marker='o', ms=2, color=col, label=lab,
                     ls='--' if f == 'closed_bound' else '-')
    axes[0].set_title('Attribution accuracy (%)')
    axes[0].legend(frameon=False, fontsize=5)
    for f, lab, col in (('macro_f1_closed', 'closed set', GREY), ('macro_f1_open', 'open set (rejection)', F0C)):
        axes[1].plot(x, [V[m][f] * 100 if _ok(V[m][f]) else np.nan for m in months], marker='o', ms=2, color=col, label=lab)
    axes[1].set_title('Macro-F1 (%)')
    axes[1].legend(frameon=False)
    axes[2].plot(x, [V[m]['novelty_auroc'] if _ok(V[m]['novelty_auroc']) else np.nan for m in months], marker='o', ms=2, color=F0C, label='AUROC')
    axes[2].plot(x, [V[m]['novelty_auprc'] if _ok(V[m]['novelty_auprc']) else np.nan for m in months], marker='s', ms=2, color='#0072B2', label='AUPRC')
    axes[2].plot(x, [V[m]['base_rate'] if _ok(V[m]['base_rate']) else np.nan for m in months], ls=':', color='#0072B2', label='base rate')
    axes[2].set_title('Unseen-family detection by 1 − max p')
    axes[2].legend(frameon=False)
    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels([_mlabel(m) for m in months], rotation=45)
    fig.tight_layout()
    return _save(fig, run, cfg, 'fig18_attribution')


# ------------------------------------------------------------------ Fig. 19
def fig19(O, cfg, run):
    e10 = O['e10_ledger_tests']
    S = e10['scaling']
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.3))
    n = [s['n'] for s in S]
    t = [max(s['seconds'], 1e-6) for s in S]
    axes[0].loglog(n, t, marker='o', ms=3, color=F0C)
    axes[0].set_xlabel('Records')
    axes[0].set_ylabel('Full verification (s)')
    axes[0].set_title(f'Verification time (log–log slope {e10["loglog_slope"]:.3f})')
    T = e10['tamper']
    names = list(T)
    axes[1].bar(range(len(names)), [T[k]['injected'] for k in names], color='#DDDDDD', label='injected')
    axes[1].bar(range(len(names)), [T[k]['detected'] for k in names], color=F0C, width=0.5, label='detected')
    axes[1].set_xticks(range(len(names)))
    axes[1].set_xticklabels([k.replace('_', ' ') for k in names], rotation=30, ha='right')
    axes[1].set_title(f'Tamper injection ({e10["chain_len"]:,}-record chain)')
    axes[1].legend(frameon=False)
    fig.tight_layout()
    return _save(fig, run, cfg, 'fig19_ledger')


# ------------------------------------------------------------------ Fig. 20
def fig20(O, cfg, run):
    rows = [r for r in O['e14_compare']['rows']]
    if not rows:
        return []
    big = [r for r in rows if any(s in r['metric'] for s in ('F1', 'AUC', 'TPR'))]
    small = [r for r in rows if r not in big]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 0.2 * max(len(big), len(small)) + 1.2))

    def draw(ax, R, title):
        for i, r in enumerate(R):
            p = r['published']
            pv = p if isinstance(p, list) else [p, p]
            ax.plot(pv, [i + 0.15] * 2, color=RFP, lw=2.2, solid_capstyle='butt')
            ax.plot(pv, [i + 0.15] * 2, 'o', color=RFP, ms=2.6)
            v = r.get('value')
            if v is not None:
                vv = [x * 100 for x in (v if isinstance(v, list) else [v, v])]
                ax.plot(vv, [i - 0.15] * 2, color=F0C, lw=2.2, solid_capstyle='butt')
                ax.plot(vv, [i - 0.15] * 2, 'o', color=F0C, ms=2.6)
        ax.set_yticks(range(len(R)))
        ax.set_yticklabels([f'{r["id"]}: {r["metric"]} — {r["source"]}' for r in R], fontsize=4.8)
        ax.invert_yaxis()
        ax.set_title(title)
        ax.grid(axis='x', lw=0.3, alpha=0.5)
    draw(axes[0], big, 'F1, AUC, TPR (%)')
    draw(axes[1], small, 'FNR, FPR, regression rates (%)')
    axes[1].plot([], [], color=RFP, lw=2.2, label='published (reproduced from paper)')
    axes[1].plot([], [], color=F0C, lw=2.2, label='this run')
    axes[1].legend(frameon=False, loc='lower right', bbox_to_anchor=(1.0, 1.04), ncol=2)
    fig.tight_layout()
    return _save(fig, run, cfg, 'fig20_comparison')


# ------------------------------------------------------------------ Fig. 21
def fig21(O, cfg, run):
    e11 = O['e11_ember2018']
    if e11.get('skipped'):
        return []
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.4))
    prim = f'cp{cfg["thresholds"]["certified_tau"][0]:g}'
    e1 = O.get('e1_metrics', {})
    a, b = cfg['screen']['certify_months']
    cm = month_list(a, b)
    f0 = [e1['f0_monthly'][m]['metrics']['fnr'] * 100 for m in cm if m in e1.get('f0_monthly', {})]
    within = [v[prim]['fnr'] * 100 for k, v in e11['within']['months'].items() if k != 'cal' and prim in v]
    fwd = [v * 100 if _ok(v) else np.nan for v in e11['forward_transfer'].get('monthly_fnr', [])]
    for vals, lab, col in ((f0, 'f₀ on BODMAS', F0C), (within, 'within EMBER-2018', '#0072B2'), (fwd, 'EMBER-trained → BODMAS', '#222222')):
        if vals:
            axes[0].plot(range(1, len(vals) + 1), vals, marker='o', ms=2.2, color=col, label=lab)
    axes[0].set_xlabel('Test month index')
    axes[0].set_ylabel(f'FNR at θ@{prim[2:]} (%)')
    axes[0].legend(frameon=False)
    axes[0].set_title('FNR by test month')
    b4 = O.get('e4_bias', {}).get('random')
    ri = e11['random_inflation']
    for i, (lab, m, ci) in enumerate((('BODMAS', b4 and b4.get('inflation_mean'), b4 and b4.get('inflation_ci')),
                                      ('EMBER-2018', ri.get('mean'), ri.get('ci')))):
        if _ok(m):
            lo, hi = (ci if ci and _ok(ci[0]) else [m, m])
            axes[1].errorbar(i, m * 100, yerr=[[max(0, (m - lo) * 100)], [max(0, (hi - m) * 100)]], fmt='o', color=F0C, capsize=2)
    axes[1].set_xticks([0, 1])
    axes[1].set_xticklabels(['BODMAS', 'EMBER-2018'])
    axes[1].axhline(0, color='k', lw=0.4)
    axes[1].set_title('Random-split inflation of F1 @π (pp)')
    rel = O.get('_published', {}).get('ember2018_release', {})
    pc = e11['published_check']
    labs = [('auc', 'AUC-ROC'), ('tpr_at_0p1', 'TPR @0.1% FPR'), ('tpr_at_1', 'TPR @1% FPR')]
    for i, (k, lab) in enumerate(labs):
        if _ok(rel.get(k)):
            axes[2].plot(i - 0.1, rel[k], 'o', color=RFP, ms=3.5, label='release notebook (RfP)' if i == 0 else None)
        if _ok(pc.get(k)):
            axes[2].plot(i + 0.1, pc[k] * 100, 's', color=F0C, ms=3.5, label='this run' if i == 0 else None)
    axes[2].set_xticks(range(len(labs)))
    axes[2].set_xticklabels([l for _, l in labs])
    axes[2].set_title('Published EMBER-2018 model: pipeline check (%)')
    axes[2].legend(frameon=False)
    fig.tight_layout()
    return _save(fig, run, cfg, 'fig21_ember2018')


FIGS = [(fig05, ['e1_metrics']), (fig06, ['e1_metrics']), (fig07, ['e1_metrics']), (fig08, ['e1_metrics_raw']), (fig09, ['e2_certificates']),
        (fig10, ['e1_metrics']), (fig11, ['e5_errors_drift']), (fig12, ['e6_monitor']), (fig13, ['e9_explain_issue']), (fig14, ['e12_cost_learning']),
        (fig15, ['e12_cost_learning']), (fig16, ['e4_bias']), (fig17, ['e7_assurance']), (fig18, ['e8_attribution']), (fig19, ['e10_ledger_tests']),
        (fig20, ['e14_compare']), (fig21, ['e11_ember2018'])]


def build_all(run, cfg) -> list:
    from ..config import ROOT
    names = {n for _, need in FIGS for n in need} | {'e4_bias', 'e1_metrics'}
    O = {n: run.load(n) for n in names if run.has(n)}
    pb = ROOT / 'results' / 'published_baselines.json'
    O['_published'] = load_json(pb) if pb.exists() else {}
    written = []
    for fn, need in FIGS:
        missing = [n for n in need if n not in O]
        if missing:
            log(f'  skip {fn.__name__}: missing {", ".join(missing)}')
            continue
        try:
            written += fn(O, cfg, run)
        except Exception as exc:                      # one failing figure must not stop the others
            plt.close('all')
            log(f'  {fn.__name__} failed: {type(exc).__name__}: {exc}')
    return written
