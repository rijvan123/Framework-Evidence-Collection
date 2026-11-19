#!/usr/bin/env python3
"""S10 figures (R5). Static IEEE figures: 7.16 in (double column) or 3.5 in (single column), Liberation Sans/DejaVu,
validated categorical palette (dataviz reference palette, light mode, fixed slot order), hairline solid grids,
2 px lines, legend for >= 2 series, no dual axes, sequential single-hue blue, diverging blue<->red with grey midpoint.
Every figure is written as PDF + PNG and registered in figs/captions.json with its number label."""
import os, sys, json, glob, math
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import s10_common as C

SLOT = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948']
INK = '#0b0b0b'; INK2 = '#52514e'; MUTED = '#898781'; GRID = '#e1e0d9'; AXIS = '#c3c2b7'; SURF = '#fcfcfb'; GREY = '#c3c2b7'
BLUES = ['#cde2fb', '#b7d3f6', '#9ec5f4', '#86b6ef', '#6da7ec', '#5598e7', '#3987e5', '#2a78d6', '#256abf', '#1c5cab', '#184f95', '#104281', '#0d366b']
SEQ = LinearSegmentedColormap.from_list('seqblue', ['#fcfcfb'] + BLUES)
DIV = LinearSegmentedColormap.from_list('div', ['#1c5cab', '#86b6ef', '#f0efec', '#ec8a89', '#c63a39'])
MARK = ['o', 's', '^', 'D', 'v', 'P', 'X', '*']
MODEL_COLOR = {'lgbm_trace': SLOT[0], 'lgbm_ember': SLOT[1], 'xgb': SLOT[2], 'rf': SLOT[3], 'et': SLOT[4], 'lr': SLOT[5],
               'ember2018_pub': SLOT[6], 'nb': SLOT[7]}
MODEL_MARK = {'lgbm_trace': 'o', 'lgbm_ember': 's', 'xgb': '^', 'rf': 'D', 'et': 'v', 'lr': 'P', 'ember2018_pub': 'X', 'nb': '*'}
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 7.5, 'axes.titlesize': 8, 'axes.labelsize': 7.5,
                     'xtick.labelsize': 6.8, 'ytick.labelsize': 6.8, 'legend.fontsize': 6.6, 'axes.edgecolor': AXIS,
                     'axes.linewidth': 0.6, 'axes.labelcolor': INK, 'xtick.color': INK2, 'ytick.color': INK2, 'text.color': INK,
                     'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.5, 'grid.linestyle': '-', 'axes.axisbelow': True,
                     'lines.linewidth': 1.4, 'lines.markersize': 3.5, 'figure.facecolor': 'white', 'axes.facecolor': 'white',
                     'savefig.dpi': 300, 'pdf.fonttype': 42, 'ps.fonttype': 42, 'legend.frameon': False,
                     'axes.spines.top': False, 'axes.spines.right': False})
CAPS = {}
CAP_PATH = f'{C.FIGS}/captions.json'
if os.path.exists(CAP_PATH):
    CAPS = json.load(open(CAP_PATH))
NICE = {'lgbm_trace': 'LGBM-TRACE (f₀ family)', 'lgbm_ember': 'LGBM-EMBER', 'xgb': 'XGBoost', 'rf': 'Random forest', 'et': 'Extra trees',
        'lr': 'LR', 'lr_chi2': 'LR + χ²(256)', 'lr_ig': 'LR + IG(256)', 'lr_mrmr': 'LR + mRMR(128)', 'lr_pca': 'LR + PCA(0.95)',
        'svm_lin': 'Linear SVM', 'svm_rbf': 'RBF-SVM (PoC, 10k)', 'knn': 'k-NN (PCA-50)', 'nb': 'Gaussian NB', 'mlp': 'MLP (PoC, 20k)',
        'stack': 'Temporal stacking', 'vote': 'Soft vote', 'ember2018_pub': 'EMBER-2018 GBDT (published model)'}


def save(fig, name, caption, label, data_note=''):
    fig.savefig(f'{C.FIGS}/{name}.pdf', bbox_inches='tight'); fig.savefig(f'{C.FIGS}/{name}.png', bbox_inches='tight', dpi=200)
    plt.close(fig); CAPS[name] = dict(caption=caption, label=label, note=data_note)
    json.dump(CAPS, open(CAP_PATH, 'w'), indent=1, ensure_ascii=False); print('fig', name)


def e1():
    return pd.read_pickle(f'{C.OUT}/e1_metrics.pkl')


def val(df, model, set_, metric, pi='native', thr='cert_0.1', seed=None):
    q = df[(df.model == model) & (df.set == set_) & (df.metric == metric) & (df.pi == str(pi)) & (df.thr == thr)]
    if seed is not None:
        q = q[q.seed == seed]
    return q


def fig_metric_bars():
    df = e1(); models = [mm for mm in NICE if mm in set(df.model)]
    mets = [('f1', '0.1', 'F1 (π = 10%)'), ('ap', '0.1', 'AUC-PR (π = 10%)'), ('mcc', '0.1', 'MCC (π = 10%)'),
            ('fnr', 'native', 'FNR'), ('fpr', 'native', 'FPR (log)'), ('auc', 'native', 'AUC-ROC')]
    fig, axes = plt.subplots(2, 3, figsize=(7.16, 5.0), sharey=True)
    axes = axes.ravel()
    order = sorted(models, key=lambda mm: -val(df, mm, 'pool_MarSep', 'f1', '0.1')['value'].mean())
    yy = np.arange(len(order))
    for ax, (met, pi, title) in zip(axes, mets):
        thr = '-' if met in ('ap', 'auc') else 'cert_0.1'
        for k, mm in enumerate(order):
            q = val(df, mm, 'pool_MarSep', met, pi, thr)
            v = q['value'].to_numpy(); mu = np.nanmean(v)
            col = SLOT[1] if mm == 'lgbm_trace' else SLOT[0]
            dots = met in ('ap', 'auc', 'fpr')             # non-zero baseline or log axis: dot plot, never truncated bars
            if dots:
                if met == 'fpr' and not (mu > 0):
                    ax.text(1.2e-5, k, '0', va='center', fontsize=6, color=INK2); continue
                ax.plot(mu, k, 'o', color=col, ms=4, zorder=3)
            else:
                ax.barh(k, mu, height=0.62, color=col, edgecolor='none')
            if len(v) > 1:
                ax.plot([np.nanmin(v), np.nanmax(v)], [k, k], color=INK, lw=0.8, zorder=2)
            elif q['lo'].notna().any():
                lo_, hi_ = q['lo'].iloc[0], q['hi'].iloc[0]
                if met == 'fpr':
                    lo_ = max(lo_, 1e-5)
                ax.plot([lo_, hi_], [k, k], color=INK, lw=0.8, zorder=2)
        ax.set_title(title); ax.grid(axis='y', visible=False)
        if met == 'fpr':
            ax.set_xscale('log'); ax.set_xlim(1e-5, 3e-3)
        if met in ('f1', 'mcc'):
            ax.set_xlim(0, 1.0)
        if met in ('ap', 'auc'):
            lo = min(np.nanmean(val(df, mm, 'pool_MarSep', met, pi, thr)['value']) for mm in order)
            ax.set_xlim(lo - 0.01, 1.002)
    for a in (axes[0], axes[3]):
        a.set_yticks(yy); a.set_yticklabels([NICE[mm] for mm in order])
    axes[0].invert_yaxis()
    fig.tight_layout(w_pad=0.6, h_pad=1.0)
    save(fig, 'fig5_metric_bars', 'Per-model detection metrics on the pooled March–September 2020 test stream (Dated stratum), '
         'threshold certified at τ_FPR = 0.1% on December 2019 (k* = 1). π-dependent metrics use the Eq. (70) re-weighting to '
         'π = 10%. Bars or dots: mean over model seeds (dots where the axis cannot start at zero: AUC-PR, AUC-ROC, log FPR; "0" = no false positive); '
         'whiskers: min–max over the seeds (multi-seed models) or the 95% stratified bootstrap CI (single fits; DeLong for AUC). Orange: LGBM-TRACE, the f₀ family.', 'measured-on-Claude')


def roc_points(y, s, n=400):
    from sklearn.metrics import roc_curve
    f, t, _ = roc_curve(y, s); return f, t


def fig_roc_pr():
    m = C.load_meta(); y = m['y'].to_numpy(); sp = m['split'].to_numpy(); mo = m['month'].to_numpy()
    te = np.where((sp == 'test') & np.isin(mo, C.CERT_MONTHS))[0]
    hi = ['lgbm_trace', 'lgbm_ember', 'xgb', 'rf', 'et', 'lr', 'ember2018_pub', 'nb']
    rest = [os.path.basename(f)[:-4].rsplit('_s', 1)[0] for f in glob.glob(f'{C.CACHE}/scores/*_s*.npz')]
    rest = sorted(set(rest) - set(hi))
    def sc(name):
        f = sorted(glob.glob(f'{C.CACHE}/scores/{name}_s*.npz'))[0]; d = np.load(f); s = np.full(len(m), np.nan); s[d['idx']] = d['s']; return s[te]
    from sklearn.metrics import roc_curve, precision_recall_curve
    fig, axes = plt.subplots(1, 3, figsize=(7.16, 2.85))
    for name in rest:
        s = sc(name); f, t, _ = roc_curve(y[te], s); axes[0].plot(np.maximum(f, 1e-5), t, color=GREY, lw=0.7, zorder=1)
    for k, name in enumerate(hi):
        if not glob.glob(f'{C.CACHE}/scores/{name}_s*.npz'):
            continue
        s = sc(name); f, t, _ = roc_curve(y[te], s)
        axes[0].plot(np.maximum(f, 1e-5), t, color=MODEL_COLOR[name], lw=1.2, label=NICE[name], zorder=3)
        for ax, pi in ((axes[1], 0.10), (axes[2], 0.01)):
            w = np.where(y[te] == 1, 1.0, C.kappa_for(pi, int(y[te].sum()), int((1 - y[te]).sum())))
            p, r, _ = precision_recall_curve(y[te], s, sample_weight=w); ax.plot(r, p, color=MODEL_COLOR[name], lw=1.2, label=NICE[name])
    axes[0].set_xscale('log'); axes[0].set_xlim(1e-5, 1); axes[0].set_ylim(0.5, 1.001)
    for v in (1e-3, 1e-2):
        axes[0].axvline(v, color=AXIS, lw=0.6)
    axes[0].set_xlabel('False-positive rate (log)'); axes[0].set_ylabel('True-positive rate'); axes[0].set_title('ROC, pooled Mar–Sep 2020')
    for ax, pi, ylo in ((axes[1], '10%', 0.6), (axes[2], '1%', 0.0)):
        ax.set_xlabel('Recall'); ax.set_ylabel('Precision'); ax.set_title(f'Precision–recall at π = {pi}'); ax.set_xlim(0.6, 1.0); ax.set_ylim(ylo, 1.005)
    h, l = axes[1].get_legend_handles_labels()
    fig.legend(h, l, loc='lower center', ncol=4, bbox_to_anchor=(0.5, -0.02), handlelength=1.6, columnspacing=1.2)
    fig.tight_layout(w_pad=1.0, rect=(0, 0.1, 1, 1))
    save(fig, 'fig6_roc_pr', 'Multi-model ROC (log FPR axis; grey: remaining models, incl. k-NN, LR variants, linear SVM) and precision–recall curves on the pooled March–September 2020 '
         'test stream. PR curves are computed with benign weights κ (Eq. 70) so that the effective prevalence is π = 10% (centre) and π = 1% (right). '
         'Vertical rules mark FPR = 0.1% and 1%. Seed 11 (stochastic) or the single fit (deterministic).', 'measured-on-Claude')


def fig_confusion():
    df = e1()
    def counts_of(model, thr='cert_0.1', seed=None):
        q = df[(df.model == model) & (df.metric == 'tp_fn_fp_tn') & (df.thr == thr) & (df.set == 'pool_MarSep')]
        q = q[q.seed == (seed if seed is not None else sorted(q.seed.unique())[0])]
        r = q.iloc[0]; return r.tp, r.fn, r.fp, r.tn
    fig, axes = plt.subplots(2, 4, figsize=(7.16, 3.9))
    def draw(ax, M, title, fmt):
        ax.imshow(M / M.sum(1, keepdims=True), cmap=SEQ, vmin=0, vmax=1); ax.grid(False)
        for i in range(2):
            for j in range(2):
                frac = M[i, j] / M[i].sum(); ax.text(j, i, fmt(M[i, j]) + f'\n({100 * frac:.2f}%)', ha='center', va='center',
                                                      color='white' if frac > 0.6 else INK, fontsize=6.2)
        ax.set_xticks([0, 1]); ax.set_xticklabels(['benign', 'malware'], fontsize=6); ax.set_yticks([0, 1]); ax.set_yticklabels(['benign', 'malware'], fontsize=6)
        ax.set_title(title, fontsize=6.8)
    tp, fn, fp, tn = counts_of('lgbm_trace', seed=11)
    draw(axes[0, 0], np.array([[tn, fp], [fn, tp]], float), 'f₀, certified θ: counts', lambda v: f'{int(v):,}')
    for ax, pi in ((axes[0, 1], 0.10), (axes[0, 2], 0.01)):
        Nf = 10000; P = pi * Nf; Ng = (1 - pi) * Nf; tpr = tp / (tp + fn); fpr = fp / (fp + tn)
        draw(ax, np.array([[Ng * (1 - fpr), Ng * fpr], [P * (1 - tpr), P * tpr]]), f'f₀, per 10,000 files, π = {int(pi * 100)}%', lambda v: f'{v:,.1f}')
    tp2, fn2, fp2, tn2 = counts_of('lgbm_trace', 'default', 11)
    draw(axes[0, 3], np.array([[tn2, fp2], [fn2, tp2]], float), 'f₀, default θ (p = 0.5): counts', lambda v: f'{int(v):,}')
    for ax, (mdl, sd) in zip(axes[1], (('ember2018_pub', None), ('xgb', 11), ('et', 11), ('lr', None))):
        if mdl not in set(df.model):
            ax.axis('off'); continue
        t_, f_, p_, n_ = counts_of(mdl, seed=sd)
        draw(ax, np.array([[n_, p_], [f_, t_]], float), f"{NICE[mdl].split(' (')[0]}, certified θ", lambda v: f'{int(v):,}')
    for ax in axes[:, 0]:
        ax.set_ylabel('Oracle label', fontsize=6.5)
    for ax in axes[1]:
        ax.set_xlabel('Predicted', fontsize=6.5)
    fig.tight_layout(w_pad=0.6, h_pad=1.2)
    save(fig, 'fig7_confusion', 'Confusion matrices on the pooled March–September 2020 stream (36,185 benign, 32,691 malware). Top: the evidentiary detector f₀ '
         '(LGBM-TRACE, seed 11) at the CP-certified threshold (τ_FPR = 0.1%, k* = 1) as measured counts, as expected counts per 10,000 files at deployment '
         'prevalence π = 10% and 1% (analytic from the measured TPR and FPR), and at the default threshold p = 0.5. Bottom: comparators at their own certified '
         'thresholds (seed 11 or single fit). Cell shading = row-normalised rate.', 'measured-on-Claude (counts); derived from measured rates (per-10,000 panels)')


# ====================================================================================== additional figures
def _months_label(ms):
    return [pd.Timestamp(mm + '-01').strftime('%b') for mm in ms]


def fig_decay():
    df = e1(); fig, axes = plt.subplots(1, 2, figsize=(7.16, 2.9))
    sel = [('lgbm_trace', 0), ('lgbm_ember', 1), ('xgb', 2), ('rf', 3), ('et', 4), ('ember2018_pub', 6)]
    xs_all = np.arange(len(C.TEST_MONTHS)); xs_c = np.arange(2, len(C.TEST_MONTHS))
    for name, k in sel:
        if name not in set(df.model):
            continue
        g = df[(df.model == name) & (df.thr == 'cert_0.1')]
        fnr = np.array([g[(g.set == mm) & (g.metric == 'fnr') & (g.pi == 'native')]['value'].mean() for mm in C.TEST_MONTHS])
        f1 = np.array([g[(g.set == mm) & (g.metric == 'f1') & (g.pi == '0.1')]['value'].mean() for mm in C.CERT_MONTHS])
        lab = f"{NICE[name]} (AUT={C.aut(f1):.3f})"
        axes[0].plot(xs_all, 100 * fnr, color=MODEL_COLOR[name], marker=MODEL_MARK[name], ms=3, lw=1.3, label=NICE[name])
        axes[1].plot(xs_c, f1, color=MODEL_COLOR[name], marker=MODEL_MARK[name], ms=3, lw=1.3, label=lab)
        if g.seed.nunique() > 1:                 # band = min-max over model seeds
            lo = [g[(g.set == mm) & (g.metric == 'fnr') & (g.pi == 'native')]['value'].min() for mm in C.TEST_MONTHS]
            hi = [g[(g.set == mm) & (g.metric == 'fnr') & (g.pi == 'native')]['value'].max() for mm in C.TEST_MONTHS]
            axes[0].fill_between(xs_all, 100 * np.array(lo), 100 * np.array(hi), color=MODEL_COLOR[name], alpha=0.10, lw=0)
            lo = [g[(g.set == mm) & (g.metric == 'f1') & (g.pi == '0.1')]['value'].min() for mm in C.CERT_MONTHS]
            hi = [g[(g.set == mm) & (g.metric == 'f1') & (g.pi == '0.1')]['value'].max() for mm in C.CERT_MONTHS]
            axes[1].fill_between(xs_c, lo, hi, color=MODEL_COLOR[name], alpha=0.10, lw=0)
    axes[0].axvspan(-0.4, 1.4, color='#f0efec', zorder=0); axes[0].text(0.5, axes[0].get_ylim()[1] * 0.92 if axes[0].get_ylim()[1] > 0 else 1, 'benign-\ndeficient', ha='center', va='top', fontsize=6, color=INK2)
    axes[0].set_xticks(xs_all); axes[0].set_xticklabels(_months_label(C.TEST_MONTHS)); axes[0].set_ylabel('FNR (%)'); axes[0].set_title('Monthly FNR, Jan–Sep 2020')
    axes[1].set_xticks(xs_c); axes[1].set_xticklabels(_months_label(C.CERT_MONTHS)); axes[1].set_ylabel('F1 at π = 10%'); axes[1].set_title('Monthly F1 at π = 10%, Mar–Sep 2020')
    h, l = axes[1].get_legend_handles_labels()
    fig.legend(h, l, loc='lower center', ncol=3, bbox_to_anchor=(0.5, -0.01), fontsize=6.2)
    fig.tight_layout(w_pad=1.5, rect=(0, 0.13, 1, 1))
    save(fig, 'fig8_temporal_decay', 'Temporal decay under the TESSERACT protocol (train Aug–Nov 2019, calibrate Dec 2019, test monthly). Threshold certified at '
         'τ_FPR = 0.1% on December. Lines: seed mean; shaded band: min–max over the model seeds (multi-seed models). Left: FNR for every test month (Jan–Feb carry '
         'only 49 and 62 dated benign samples, so F1 is not reported there). Right: F1 at π = 10% (Eq. 70) with AUT (Eq. 69) over the seven months in the legend.',
         'measured-on-Claude')


def fig_certificates():
    A = json.load(open(f'{C.OUT}/analysis_certificates.json'))
    fig, axes = plt.subplots(1, 2, figsize=(7.16, 2.4))
    for k, (key, lab) in enumerate([('thr0.001|tau0.001/0.02', 'θ certified at 0.1%'), ('thr0.005|tau0.005/0.05', 'θ certified at 0.5%')]):
        r = A[key]['months']; ms = C.CERT_MONTHS; xs = np.arange(len(ms)) + (k - 0.5) * 0.18
        for ax, met, ub in ((axes[0], 'fpr', 'fpr_ub'), (axes[1], 'fnr', 'fnr_ub')):
            v = np.array([r[mm][met] for mm in ms]) * 100; u = np.array([r[mm][ub] for mm in ms]) * 100
            ax.vlines(xs, v, u, color=SLOT[k], lw=1.2); ax.plot(xs, v, 'o', color=SLOT[k], ms=3.5, label=f'{lab}: estimate')
            ax.plot(xs, u, '_', color=SLOT[k], ms=7, mew=1.5, label=f'{lab}: 95% CP upper bound')
    from matplotlib.transforms import blended_transform_factory as _btf
    for ax, taus, t in ((axes[0], (0.1, 0.5), 'FPR (%)'), (axes[1], (2, 5), 'FNR (%)')):
        for tv in taus:
            ax.axhline(tv, color=INK2, lw=0.7)
            ax.text(1.01, tv, f'τ = {tv}%', fontsize=6, color=INK2, va='center', ha='left', transform=_btf(ax.transAxes, ax.transData), clip_on=False)
        ax.set_xticks(range(len(C.CERT_MONTHS))); ax.set_xticklabels(_months_label(C.CERT_MONTHS)); ax.set_ylabel(t)
    axes[0].set_title('Retrospective FPR certificates (Mar–Sep 2020)'); axes[1].set_title('Retrospective FNR certificates (Mar–Sep 2020)')
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc='lower center', ncol=4, fontsize=6, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(w_pad=3.0, rect=(0, 0.08, 1, 1))
    save(fig, 'fig9_certificates', 'Time-indexed error certificates of f₀ (Eq. S7.4): monthly point estimates and one-sided 95% Clopper–Pearson upper bounds for FPR '
         '(left) and FNR (right), with the threshold certified on December 2019 at τ_FPR = 0.1% (k* = 1) and 0.5% (k* = 21). Horizontal rules: tolerances τ.', 'measured-on-Claude')


def fig_baserate():
    A = json.load(open(f'{C.OUT}/analysis_baserate.json'))
    fig, axes = plt.subplots(1, 2, figsize=(7.16, 2.5), sharey=True)
    cells = pd.DataFrame(A['cells']); dft = pd.DataFrame(A['default_threshold_sweep'])
    pis = np.logspace(-3, np.log10(0.5), 60)
    m = C.load_meta(); y = m['y'].to_numpy(); sp = m['split'].to_numpy(); mo = m['month'].to_numpy()
    d = np.load(f'{C.CACHE}/scores/lgbm_trace_s11.npz'); s = np.full(len(m), np.nan); s[d['idx']] = d['s']
    cal = np.where(sp == 'cal')[0]; thr, _ = C.certified_threshold(s[cal][y[cal] == 0], 0.001)
    for ax, t_, title in ((axes[0], thr, 'CP-certified θ (τ_FPR = 0.1%)'), (axes[1], 0.0, 'Default θ (p = 0.5)')):
        for k, mm in enumerate(C.CERT_MONTHS):
            sel = np.where((sp == 'test') & (mo == mm))[0]; tp, fn, fp, tn = C.counts(y[sel], s[sel], t_)
            tpr = tp / (tp + fn); fpr = max(fp / (fp + tn), 1e-12)
            ax.plot(pis, tpr * pis / (tpr * pis + fpr * (1 - pis)), color=SLOT[k % 8], lw=1.1, label=pd.Timestamp(mm + '-01').strftime('%b'))
        ax.set_xscale('log'); ax.set_xlabel('Deployment prevalence π (log)'); ax.set_title(title)
        ax.axvline(0.01, color=AXIS, lw=0.6); ax.axvline(0.10, color=AXIS, lw=0.6)
    g = cells.groupby('pi')
    for k, mm in enumerate(C.CERT_MONTHS):
        c = cells[cells.month == mm]
        axes[0].errorbar(c['pi'], c['measured_mean'], yerr=[c['measured_mean'] - c['lo'], c['hi'] - c['measured_mean']], fmt='o', ms=2.5,
                         color=SLOT[k % 8], elinewidth=0.7, capsize=0)
    axes[0].set_ylabel('Precision (PPV)'); axes[1].legend(title='Month', fontsize=6, title_fontsize=6, loc='lower right')
    fig.tight_layout(w_pad=1.0)
    save(fig, 'fig10_base_rate', 'Base-rate sensitivity of f₀: precision versus deployment prevalence π. Curves: Eq. (55) evaluated with each month\'s measured TPR and FPR; '
         'points (left): mean and 2.5–97.5 percentiles over 20 prevalence-resampled streams at π ∈ {1, 2, 5, 10}%. The certified threshold keeps PPV high at low '
         'π because realised FPR is 0–3 per 10⁴ benign files; the default threshold collapses PPV in March–April.', 'measured-on-Claude (points); analytic from measured rates (curves)')


def fig_drift():
    A = json.load(open(f'{C.OUT}/analysis_drift.json')); ms = ['2019-12'] + C.TEST_MONTHS
    M = np.array([[A['months'][mm]['groups'][g] for mm in ms] for g, _, _ in C.GROUPS])
    fig, axes = plt.subplots(1, 2, figsize=(7.16, 2.5), gridspec_kw=dict(width_ratios=[1.6, 1]))
    im = axes[0].imshow(M, cmap=SEQ, aspect='auto'); axes[0].grid(False)
    axes[0].set_yticks(range(9)); axes[0].set_yticklabels([g for g, _, _ in C.GROUPS]); axes[0].set_xticks(range(len(ms)))
    axes[0].set_xticklabels([pd.Timestamp(mm + '-01').strftime('%b\n%y') for mm in ms], fontsize=6)
    cb = fig.colorbar(im, ax=axes[0], fraction=0.04, pad=0.02); cb.set_label('mean per-feature JS (bits)', fontsize=6); cb.ax.tick_params(labelsize=5.5)
    axes[0].set_title('Drift vs training window by EMBER group (Eq. 75)')
    df = e1(); g = df[(df.model == 'lgbm_trace') & (df.seed == 11) & (df.thr == 'cert_0.1')]
    f1 = [g[(g.set == mm) & (g.metric == 'f1') & (g.pi == '0.1')]['value'].iloc[0] for mm in C.CERT_MONTHS]
    Dm = [A['months'][mm]['D'] for mm in C.CERT_MONTHS]
    axes[1].plot(Dm, f1, 'o', color=SLOT[0], ms=4)
    for x_, y_, mm in zip(Dm, f1, C.CERT_MONTHS):
        axes[1].annotate(pd.Timestamp(mm + '-01').strftime('%b'), (x_, y_), textcoords='offset points', xytext=(3, 2), fontsize=6, color=INK2)
    axes[1].set_xlabel(r'Global drift $\mathcal{D}(t)$ (bits)'); axes[1].set_ylabel('F1 at π = 10% (f₀)')
    axes[1].set_title(f"Spearman ρ = {A['P5']['rho_D_f1pi10']:.2f} (p = {A['P5']['p']:.3f})")
    fig.tight_layout(w_pad=1.2)
    save(fig, 'fig11_drift', 'Feature drift relative to the training window (Aug–Nov 2019): per-group Jensen–Shannon divergence on 20 training-quantile bins '
         '(Eqs. 74–75) for December 2019 and each 2020 month (left; January–February values are inflated by the 49 and 62 dated benign files), and global drift '
         '𝒟(t) against f₀\'s monthly F1 at π = 10% over March–September (right; P5).', 'measured-on-Claude')


def fig_monitor():
    W = pd.read_pickle(f'{C.OUT}/monitor_windows.pkl'); D_ = json.load(open(f'{C.OUT}/monitor.json')); T = W[W.kind == 'test']
    fig, axes = plt.subplots(2, 3, figsize=(7.16, 3.6), sharex=True)
    stats_ = [('c2st', 'C2ST AUC (T5)'), ('ks', 'KS on margins (T1)'), ('psi', 'Mean PSI (T2)'), ('cred', '1 − mean credibility (T3)')]
    xs = np.arange(T['w'].nunique()); starts = sorted(T['start'].unique())
    for j, (k, title) in enumerate(stats_):
        ax = axes.flat[j]
        for c, col, lab in ((0, SLOT[0], 'predicted benign'), (1, SLOT[1], 'predicted malicious')):
            v = T[T.cls == c].sort_values('w')[k].to_numpy(); ax.plot(xs[:len(v)], v, color=col, lw=1.1, marker='o', ms=2, label=lab)
            ax.axhline(D_['lam'][f'{k}{c}'], color=col, lw=0.8, ls=(0, (1, 0)), alpha=0.6)
        ax.set_title(title)
    ax = axes.flat[4]
    for c, col in ((0, SLOT[0]), (1, SLOT[1])):
        ph = np.array(D_['ph'][str(c)]['series']); ax.plot(np.arange(len(ph)) / 7.0, ph, color=col, lw=1.0)
        ax.axhline(D_['ph_lam'][str(c)], color=col, lw=0.8, alpha=0.6)
    ax.set_title('Page–Hinkley on credibility (T4)')
    ax = axes.flat[5]
    us = T[T.cls == 1].sort_values('w')['unseen_share'].to_numpy()
    ax.bar(xs[:len(us)], 100 * us, width=0.7, color=SLOT[2]); ax.axhline(5, color=INK2, lw=0.7)
    ax.set_title('Unseen-family share of malware (%)')
    for a in axes.flat:
        a.axvline(starts.index(D_['onset_july_week']) if D_['onset_july_week'] in starts else 18, color=SLOT[7], lw=0.8)
    mfirst = [i for i in xs if i == 0 or pd.Timestamp(starts[i]).month != pd.Timestamp(starts[i - 1]).month]
    for a in axes[1]:
        a.set_xticks(mfirst); a.set_xticklabels([pd.Timestamp(starts[i]).strftime('%b') for i in mfirst], rotation=0, fontsize=6)
    h, l = axes.flat[0].get_legend_handles_labels()
    h += [plt.Line2D([], [], color=INK2, lw=0.8), plt.Line2D([], [], color=SLOT[7], lw=0.8)]; l += ['alarm threshold λ (colour = class)', 'July onset week']
    fig.legend(h, l, loc='lower center', ncol=4, fontsize=6, bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(h_pad=0.8, w_pad=0.8, rect=(0, 0.05, 1, 1))
    save(fig, 'fig12_monitor', 'Label-free monitor M8 on weekly windows from 1 March 2020 (f₀, predicted-class conditioning, COFF column excluded). Thin horizontal '
         'lines: alarm thresholds λ = maximum over the blocked null (86 Oct–Dec windows for C2ST/PSI; 25 December windows for KS/credibility; December '
         'daily series for Page–Hinkley). Red rule: July onset week (unseen-family share > 5%). Every test window exceeds at least one λ, so the '
         'monitor cannot separate the July event from ordinary non-stationarity (trigger kill KT met).', 'measured-on-Claude')


def fig_importance():
    A = json.load(open(f'{C.OUT}/explain.json')); groups = [g for g, _, _ in C.GROUPS]
    fig, axes = plt.subplots(1, 3, figsize=(7.16, 2.6), gridspec_kw=dict(width_ratios=[1, 1.1, 1.2]))
    v = np.array([A['importance']['mean_abs'][g] for g in groups]); o = np.argsort(v)
    axes[0].barh(np.arange(9), v[o], height=0.6, color=SLOT[0]); axes[0].set_yticks(range(9)); axes[0].set_yticklabels([groups[i] for i in o])
    axes[0].set_xlabel('mean |grouped TreeSHAP| (margin)'); axes[0].set_title('f₀ attribution by EMBER group'); axes[0].grid(axis='y', visible=False)
    shap_share = v / v.sum(); gain = np.array([A['gain_group'][g] for g in groups]); lr = np.array([A['lr_group'][g] for g in groups])
    for k, (arr, lab) in enumerate(((shap_share, '|SHAP| share (f₀)'), (gain, 'gain share (f₀)'), (lr, '|coef| share (LR)'))):
        axes[1].plot(arr[o], np.arange(9), MARK[k], color=SLOT[k], ms=4, label=lab, lw=0)
    axes[1].set_yticks(range(9)); axes[1].set_yticklabels([groups[i] for i in o]); axes[1].set_xlabel('share of total')
    axes[1].legend(fontsize=5.8, loc='upper center', bbox_to_anchor=(0.45, -0.2), ncol=2, handletextpad=0.2, columnspacing=0.8)
    axes[1].set_title('Importance share by group'); axes[1].grid(axis='y', visible=False)
    tf = A['top_features'][:15][::-1]
    axes[2].barh(np.arange(len(tf)), [t['gain_share'] for t in tf], height=0.6, color=SLOT[0])
    axes[2].set_yticks(range(len(tf))); axes[2].set_yticklabels([f"{t['group']}[{t['offset']}] (#{t['index']})" for t in tf], fontsize=5.8)
    axes[2].set_xlabel('gain share'); axes[2].set_title('Top-15 features (f₀ gain)'); axes[2].grid(axis='y', visible=False)
    fig.tight_layout(w_pad=0.8)
    save(fig, 'fig13_importance', 'Feature importance of f₀. Left: mean absolute grouped TreeSHAP (exact, LightGBM pred_contrib) per EMBER v2 group on 6,020 '
         'month×class-stratified March–September findings. Centre: share of importance per group under three measures (|SHAP|, LightGBM gain, LR |coefficient| '
         'on signed-log standardised inputs). Right: top-15 features by gain; index = EMBER v2 column, offset = position inside its group.', 'measured-on-Claude')


def fig_timing():
    T = json.load(open(f'{C.OUT}/timing_clean.json'))['jobs']; T = [t for t in T if 'fit_s' in t]
    rbf = glob.glob(f'{C.CACHE}/scores/svm_rbf_s11.json')
    if rbf:
        r = json.load(open(rbf[0])); T.append(dict(model='svm_rbf', fit_s=r['fit_s'], pred_us=r['pred_us'], rss_gb=r['rss_gb']))
    T = sorted(T, key=lambda t: (t['model'] != 'ember2018_pub', t['fit_s']))
    fig, axes = plt.subplots(1, 3, figsize=(7.16, 2.7), sharey=True)
    ys = np.arange(len(T))
    for ax, key, lab, logx in ((axes[0], 'fit_s', 'training time (s, log)', True), (axes[1], 'pred_us', 'inference (µs per file, log)', True),
                               (axes[2], 'rss_gb', 'peak RSS (GB)', False)):
        vals = [np.nan if (key == 'fit_s' and t['model'] == 'ember2018_pub') else max(t[key], 1e-3) for t in T]
        ax.barh(ys, vals, height=0.6, color=[SLOT[1] if t['model'] == 'lgbm_trace' else SLOT[0] for t in T])
        if key == 'fit_s':
            for yy_, t in zip(ys, T):
                if t['model'] == 'ember2018_pub':
                    ax.text(0.02, yy_, 'scored only (not trained)', transform=matplotlib.transforms.blended_transform_factory(ax.transAxes, ax.transData),
                            va='center', fontsize=5.8, color=INK2)
        if logx:
            ax.set_xscale('log')
        ax.set_xlabel(lab); ax.grid(axis='y', visible=False)
    axes[0].set_yticks(ys); axes[0].set_yticklabels([NICE.get(t['model'], t['model']) for t in T])
    fig.tight_layout(w_pad=0.8)
    save(fig, 'fig14_cost', 'CPU cost per model on the S7 training window (23,158 × 2,381; 2 vCPU Intel Xeon 2.1 GHz): wall-clock training time, inference time per '
         'file (20,000 evaluation rows) and process peak RSS, from an uncontended sequential timing run (one seed per model). The published EMBER-2018 model is '
         'scored only. RBF-SVM: E1 run on its 10,000-row sub-sample.', 'measured-on-Claude')


def fig_learning():
    L = pd.DataFrame(json.load(open(f'{C.OUT}/learning_curves.json')))
    fig, axes = plt.subplots(1, 3, figsize=(7.16, 2.4))
    for k, name in enumerate(['lgbm_trace', 'xgb', 'rf100', 'lr', 'nb']):
        g = L[L.model == name].sort_values('n'); lab = NICE.get(name, 'Random forest (100 trees)' if name == 'rf100' else name)
        key = 'rf' if name == 'rf100' else name; col = MODEL_COLOR[key]; mk = MODEL_MARK[key]
        axes[0].plot(g['n'], g['ap_test_pi10'], marker=mk, color=col, label=lab)
        axes[0].plot(g['n'], g['auc_train'], color=col, lw=0.7, alpha=0.5)
        axes[1].plot(g['n'], 100 * g['fnr_test'], marker=mk, color=col, label=lab)
        axes[2].plot(g['n'], g['fit_s'], marker=mk, color=col, label=lab)
    for ax in axes:
        ax.set_xscale('log'); ax.set_xlabel('training rows (log)')
    axes[0].set_ylabel('AUC-PR at π = 10% (test)'); axes[0].set_title('Learning curve (thin: train AUC)')
    axes[1].set_ylabel('FNR at certified θ (%)'); axes[1].set_title('Recall cost of the 0.1% certificate')
    axes[2].set_yscale('log'); axes[2].set_ylabel('fit time (s, log)'); axes[2].set_title('Training time vs size')
    h, l = axes[2].get_legend_handles_labels(); fig.legend(h, l, loc='lower center', ncol=5, fontsize=6.2, bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(w_pad=1.0, rect=(0, 0.08, 1, 1))
    save(fig, 'fig15_learning', 'Learning curves on stratified sub-samples (5–100%) of the training window, evaluated on the pooled March–September 2020 stream: '
         'AUC-PR at π = 10% (thick) with in-sample training AUC (thin), FNR at the CP-certified 0.1% threshold fitted on December, and wall-clock fit time.',
         'measured-on-Claude')


def fig_cv():
    cv = pd.DataFrame(json.load(open(f'{C.OUT}/e5_cv.json'))['folds']); df = e1()
    pairs = [('lgbm_trace', 'lgbm_trace'), ('xgb', 'xgb'), ('et100', 'et'), ('rf100', 'rf'), ('lr', 'lr'), ('nb', 'nb')]
    fig, axes = plt.subplots(1, 2, figsize=(7.16, 2.5))
    for ax, met_cv, met_t, pi, lab in ((axes[0], 'f1_pi10', 'f1', '0.1', 'F1 at π = 10%'), (axes[1], 'fnr', 'fnr', 'native', 'FNR')):
        data, pos, cols = [], [], []
        for k, (cvn, tn) in enumerate(pairs):
            a = cv[cv.model == cvn][met_cv].to_numpy()
            b = df[(df.model == tn) & (df.thr == 'cert_0.1') & (df.metric == met_t) & (df.pi == pi) & df.set.isin(C.CERT_MONTHS)].groupby('set')['value'].mean().to_numpy()
            if met_t == 'fnr':
                a, b = 100 * a, 100 * b
            data += [a, b]; pos += [3 * k, 3 * k + 1]; cols += [SLOT[0], SLOT[1]]
        bp = ax.boxplot(data, positions=pos, widths=0.75, patch_artist=True, showfliers=False, medianprops=dict(color=INK, lw=1))
        for patch, c in zip(bp['boxes'], cols):
            patch.set_facecolor(c); patch.set_alpha(0.25); patch.set_edgecolor(c)
        for d_, p_, c in zip(data, pos, cols):
            ax.plot(np.full(len(d_), p_) + np.linspace(-0.15, 0.15, len(d_)), d_, 'o', color=c, ms=2.5)
        ax.set_xticks([3 * k + 0.5 for k in range(len(pairs))]); ax.set_xticklabels([NICE.get(t, t).split(' (')[0] for _, t in pairs], rotation=20, fontsize=6)
        ax.set_ylabel(lab + (' (%)' if met_t == 'fnr' else ''))
    axes[0].plot([], [], 's', color=SLOT[0], label='random 5-fold CV (folds)'); axes[0].plot([], [], 's', color=SLOT[1], label='temporal (months Mar–Sep)')
    axes[0].legend(fontsize=6, loc='lower left'); axes[0].set_title('Random CV vs temporal evaluation'); axes[1].set_title('FNR: random CV vs temporal')
    fig.tight_layout(w_pad=1.2)
    save(fig, 'fig16_cv_vs_temporal', 'Distribution of F1 at π = 10% and FNR under random stratified 5-fold cross-validation of the pooled Dated stream (biased arm; '
         'certified threshold on a 10% calibration hold-out per fold) versus the temporal protocol (monthly values, March–September 2020; seed mean). '
         'Box: inter-quartile range; points: folds or months. ET and RF use 100 trees in the CV arm.', 'measured-on-Claude')


def fig_reval():
    A = json.load(open(f'{C.OUT}/reval_analysis.json')); tag = 'L30_rho1.0'; P = A[tag]['policies']; d = f'{C.CACHE}/reval_{tag}'
    fig, axes = plt.subplots(1, 3, figsize=(7.16, 2.6), gridspec_kw=dict(width_ratios=[1.35, 1.1, 1.0]))
    days = pd.date_range('2020-03-01', '2020-10-31')
    show = [('a2_naive', 'retrain only (no abstention, no certificates)', 7), ('a2_cert', '+ certificate gating', 3), ('a2_abst', '+ abstention (κ)', 2),
            ('viii_reconcile', '+ both = (viii) reconciliation only', 0), ('tracepe', '+ budgeted re-validation (TRACE-PE)', 1)]
    for p, lab, k in show:
        v = np.load(f'{d}/Uev_{p}.npy'); axes[0].plot(days[:len(v)], np.maximum(v, 0.5), color=SLOT[k], lw=1.2 if p != 'tracepe' else 1.0,
                                                     ls='-' if p != 'tracepe' else (0, (3, 2)), label=lab)
    axes[0].set_yscale('log'); axes[0].set_ylabel(r'$U^{\mathrm{ev}}(t)$ (erroneous evaluative findings)'); axes[0].set_title('Evaluative error count (L = 30 d)')
    axes[0].set_xticks([pd.Timestamp(f'2020-{m_:02d}-01') for m_ in (3, 5, 7, 9, 11)])
    axes[0].xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%b'))
    h0, l0 = axes[0].get_legend_handles_labels()
    fig.legend(h0, l0, loc='lower left', ncol=3, fontsize=5.8, bbox_to_anchor=(0.01, -0.02), title='Left panel: cumulative safeguards', title_fontsize=6)
    order = ['a2_naive_frozen', 'viii_frozen', 'a2_naive', 'a2_cert', 'a2_abst', 'viii_reconcile', 'iv_transcendent', 'tracepe', 'vii_margin', 'vi_random', 'i_auto', 'v_pct_auto']
    names = {'a2_naive_frozen': 'frozen f₀, no safeguards', 'viii_frozen': 'frozen f₀ + κ + certificates', 'a2_naive': 'monthly retrain only',
             'a2_cert': 'retrain + certificates', 'a2_abst': 'retrain + κ', 'viii_reconcile': '(viii) retrain + κ + cert.', 'iv_transcendent': '(iv) Transcendent 10%',
             'tracepe': 'TRACE-PE re-validation', 'vii_margin': '(vii) lowest-margin review', 'vi_random': '(vi) random review', 'i_auto': '(i) re-score, auto-accept',
             'v_pct_auto': '(v) PCT-adapted, auto'}
    ys = np.arange(len(order))
    for k, p in enumerate(order):
        r = P[p]; col = SLOT[1] if p == 'tracepe' else (SLOT[0] if not p.startswith('a2') and 'frozen' not in p else GREY)
        axes[1].barh(k, max(r['E_ev'], 1), height=0.6, color=col)
        if r['E_ev_ci']:
            axes[1].plot([max(r['E_ev_ci'][0], 1), max(r['E_ev_ci'][1], 1)], [k, k], color=INK, lw=0.8)
    axes[1].set_xscale('log'); axes[1].set_yticks(ys); axes[1].set_yticklabels([names[p] for p in order], fontsize=5.8); axes[1].invert_yaxis()
    axes[1].set_xlabel(r'$E^{\mathrm{ev}}_T$ (finding-days, log)'); axes[1].set_title('Evaluative exposure, Mar–Oct 2020'); axes[1].grid(axis='y', visible=False)
    R = A[tag].get('noise', {})
    rs = [0.0, 0.005, 0.01, 0.02]
    for k, (p, lab) in enumerate((('tracepe', 'TRACE-PE'), ('vii_margin', '(vii) margin'), ('tracepe+rr', 'TRACE-PE, oracle overrides analyst'))):
        vals = [P['tracepe']['E_ev'] if p.startswith('tracepe') else P['vii_margin']['E_ev']] + [R.get(f'{r_}|{p}', {}).get('E_ev_mean', np.nan) for r_ in rs[1:]]
        axes[2].plot([100 * r_ for r_ in rs], vals, marker=MARK[k], color=SLOT[k], label=lab)
    axes[2].axhline(P['viii_reconcile']['E_ev'], color=INK2, lw=0.7)
    axes[2].text(2.0, P['viii_reconcile']['E_ev'] * 1.12, 'no review (viii)', fontsize=6, color=INK2, ha='right')
    axes[2].set_yscale('log'); axes[2].set_xlabel('analyst error rate r (%)'); axes[2].set_ylabel(r'$E^{\mathrm{ev}}_T$ (finding-days, log)')
    axes[2].set_title('Analyst noise (10 seeds)')
    axes[2].legend(fontsize=5.8, loc='upper left')
    fig.tight_layout(w_pad=0.8, rect=(0, 0.1, 1, 1))
    save(fig, 'fig17_assurance', 'Assurance-plane simulation on the native Dated stream (issuance 1 Mar–30 Sep 2020, horizon 31 Oct; label delay L = 30 d; τ_FPR = 0.5%, '
         'τ_FNR = 5%; budget B = 1% of the previous 30 days\' issuances; calendar events 1 Apr–1 Oct). Left: daily count of erroneous findings in evaluative states '
         'for cumulative safeguards. Centre: total evaluative exposure with 95% day-block bootstrap CIs (log scale). Right: exposure under analyst label noise; '
         'reviewed findings are never reconciled under S7 Algorithm 6, so analyst errors persist unless the oracle overrides the analyst at maturity.',
         'measured-on-Claude (simulation on real BODMAS scores and labels)')


def fig_attribution():
    A = json.load(open(f'{C.OUT}/attr.json')); R = pd.DataFrame(A['months']); xs = np.arange(len(R))
    fig, axes = plt.subplots(1, 3, figsize=(7.16, 2.4))
    for k, (c, lab) in enumerate((('top1_known', 'top-1, known families'), ('top3_known', 'top-3, known families'), ('top1_all', 'top-1, all families'),
                                  ('upper_bound_all', 'closed-world bound 1 − ν_t (Eq. 72)'))):
        axes[0].plot(xs, 100 * R[c], marker=MARK[k], color=SLOT[k], label=lab, ls='-' if k < 3 else (0, (2, 2)))
    axes[0].set_ylabel('accuracy (%)'); axes[0].set_title(f"Family attribution ({A['n_known']} known families)")
    axes[0].legend(fontsize=5.6, loc='upper center', bbox_to_anchor=(0.5, -0.14), ncol=2)
    for k, (c, lab) in enumerate((('macroF1_closed', 'closed-set'), ('macroF1_open', 'open-set (τ_open, 5%)'))):
        axes[1].plot(xs, R[c], marker=MARK[k], color=SLOT[k], label=lab)
    axes[1].set_ylabel('macro-F1'); axes[1].set_title('Closed vs open-set macro-F1'); axes[1].legend(fontsize=5.6, loc='upper center', bbox_to_anchor=(0.5, -0.14), ncol=2)
    axes[2].plot(xs, R['novelty_auroc'], marker='o', color=SLOT[0], label='AUROC (1 − max p)')
    axes[2].plot(xs, R['novelty_auprc'], marker='s', color=SLOT[1], label='AUPRC')
    axes[2].plot(xs, R['novelty_base'], color=GREY, lw=1, label='base rate ν_t')
    axes[2].axhline(0.80, color=INK2, lw=0.6); axes[2].set_title('Unseen-family detection')
    axes[2].legend(fontsize=5.6, loc='upper center', bbox_to_anchor=(0.5, -0.14), ncol=2)
    for ax in axes:
        ax.set_xticks(xs); ax.set_xticklabels(_months_label(list(R['month'])), fontsize=5.8, rotation=90)
    fig.tight_layout(w_pad=1.0)
    fig.subplots_adjust(bottom=0.34)
    save(fig, 'fig18_attribution', 'Attribution leg (secondary). LightGBM multiclass on families with ≥ 20 training samples (generic AV tokens excluded, D8); '
         'monthly top-k accuracy on known families and on all non-generic malware with the closed-world bound (left), macro-F1 with and without open-set '
         'rejection at the December 5th-percentile max-probability threshold (centre), and detection of unseen families by 1 − max p (right). Family labels '
         'carry a ±20 pp oracle-uncertainty band (RecMaL [92]).', 'measured-on-Claude')


def fig_ledger():
    A = json.load(open(f'{C.OUT}/ledger_tests.json')); S = pd.DataFrame(A['scaling'])
    fig, axes = plt.subplots(1, 2, figsize=(7.16, 2.2), gridspec_kw=dict(width_ratios=[1, 1.2]))
    axes[0].loglog(S['n'], S['seconds'], 'o-', color=SLOT[0], ms=4)
    axes[0].set_xlabel('records n (log)'); axes[0].set_ylabel('full verification time (s, log)')
    axes[0].set_title(f"V1 chain verification, slope = {A['loglog_slope']:.3f}")
    inj = A['injections']; ks = list(inj)
    axes[1].barh(np.arange(len(ks)), [100 * inj[k]['rate'] for k in ks], height=0.55, color=SLOT[2])
    for i, k in enumerate(ks):
        axes[1].text(101, i, f"{inj[k]['detected']:,}/{inj[k]['trials']:,}", va='center', fontsize=6, color=INK2)
    axes[1].set_yticks(range(len(ks))); axes[1].set_yticklabels(ks); axes[1].set_xlim(0, 125); axes[1].set_xlabel('detected (%)')
    axes[1].set_title('Tamper injection (10⁴ trials per type)'); axes[1].grid(axis='y', visible=False)
    fig.tight_layout(w_pad=1.2)
    save(fig, 'fig19_ledger', 'Evidence-ledger integrity (P8): wall-clock time of a full hash-chain verification for n ∈ {10³, …, 10⁶} records (left; log–log slope) '
         'and detection of injected modifications in a 2,000-record chain (right).', 'measured-on-Claude')


def comparison_values():
    """Measured counterparts of the published baselines (all measured-on-Claude)."""
    df = e1(); out = {}
    def rng_(model, thr, met, pi, months, scale=100):
        v = [df[(df.model == model) & (df.thr == thr) & (df.metric == met) & (df.pi == pi) & (df.set == mm)]['value'].mean() for mm in months]
        return float(np.nanmin(v)) * scale, float(np.nanmax(v)) * scale, [float(x) * scale for x in v]
    for name in ('lgbm_trace', 'ember2018_pub', 'xgb', 'lgbm_ember'):
        if name in set(df.model):
            out[f'{name}|F1_emp0.1_native_MarSep'] = rng_(name, 'emp_0.1', 'f1', 'native', C.CERT_MONTHS)
            out[f'{name}|F1_emp0.1_native_JanSep'] = rng_(name, 'emp_0.1', 'f1', 'native', C.TEST_MONTHS)
            out[f'{name}|F1_cert0.1_native_MarSep'] = rng_(name, 'cert_0.1', 'f1', 'native', C.CERT_MONTHS)
            out[f'{name}|F1_cert0.1_pi10_MarSep'] = rng_(name, 'cert_0.1', 'f1', '0.1', C.CERT_MONTHS)
            out[f'{name}|FNR_emp0.1_JanSep'] = rng_(name, 'emp_0.1', 'fnr', 'native', C.TEST_MONTHS)
            out[f'{name}|FPR_emp0.1_MarSep'] = rng_(name, 'emp_0.1', 'fpr', 'native', C.CERT_MONTHS)
            out[f'{name}|FNR_cert0.1_JanSep'] = rng_(name, 'cert_0.1', 'fnr', 'native', C.TEST_MONTHS)
            out[f'{name}|AUC_pool'] = float(df[(df.model == name) & (df.metric == 'auc') & (df.set == 'pool_MarSep')]['value'].mean())
            out[f'{name}|TPR_cert0.1_pool'] = float(df[(df.model == name) & (df.thr == 'cert_0.1') & (df.metric == 'rec') & (df.pi == 'native') & (df.set == 'pool_MarSep')]['value'].mean()) * 100
            out[f'{name}|FPR_cert0.1_pool'] = float(df[(df.model == name) & (df.thr == 'cert_0.1') & (df.metric == 'fpr') & (df.pi == 'native') & (df.set == 'pool_MarSep')]['value'].mean()) * 100
            out[f'{name}|TPR_emp1_pool'] = float(df[(df.model == name) & (df.thr == 'emp_1') & (df.metric == 'rec') & (df.pi == 'native') & (df.set == 'pool_MarSep')]['value'].mean()) * 100
            out[f'{name}|FPR_emp1_pool'] = float(df[(df.model == name) & (df.thr == 'emp_1') & (df.metric == 'fpr') & (df.pi == 'native') & (df.set == 'pool_MarSep')]['value'].mean()) * 100
    if os.path.exists(f'{C.OUT}/e5_t0.json'):
        T0 = json.load(open(f'{C.OUT}/e5_t0.json'))['t0']
        for k, v in T0.items():
            ms = v['months']; keys = sorted(ms)
            out[f'T0|{k}|FPR'] = (100 * min(ms[mm]['fpr'] for mm in keys), 100 * max(ms[mm]['fpr'] for mm in keys))
            out[f'T0|{k}|FNR'] = (100 * min(ms[mm]['fnr'] for mm in keys), 100 * max(ms[mm]['fnr'] for mm in keys))
            un = [ms[mm].get('fnr_unseen') for mm in keys if ms[mm].get('n_unseen', 0) >= 20]
            kn = [ms[mm].get('fnr_seen') for mm in keys if ms[mm].get('n_seen', 0) >= 20]
            out[f'T0|{k}|FNR_unseen_max'] = 100 * float(np.nanmax(un)) if un else None
            out[f'T0|{k}|FNR_known_max'] = 100 * float(np.nanmax(kn)) if kn else None
    return out


def fig_comparison():
    P = json.load(open(f'{C.ROOT}/code/published_baselines.json')); M = comparison_values(); A = json.load(open(f'{C.OUT}/analysis_bias.json'))
    F = json.load(open(f'{C.OUT}/flips.json')) if os.path.exists(f'{C.OUT}/flips.json') else None
    fig, axes = plt.subplots(1, 3, figsize=(7.16, 3.0), gridspec_kw=dict(width_ratios=[1.2, 1.05, 1.05]))
    rows = [('[1] UCSB-GBDT (RfP)', P['BODMAS_T2_UCSBGBDT_F1']['lo'], P['BODMAS_T2_UCSBGBDT_F1']['hi'], 'r'),
            ('[1] SOREL-DNN (RfP)', P['BODMAS_T2_SORELDNN_F1']['lo'], P['BODMAS_T2_SORELDNN_F1']['hi'], 'r'),
            ('[1] EMBER-GBDT (RfP)', P['BODMAS_T2_EmberGBDT_F1']['lo'], P['BODMAS_T2_EmberGBDT_F1']['hi'], 'r'),
            ('[1] SOREL-GBDT (RfP)', P['BODMAS_T2_SORELGBDT_F1']['lo'], P['BODMAS_T2_SORELGBDT_F1']['hi'], 'r')]
    if 'ember2018_pub|F1_emp0.1_native_MarSep' in M:
        a_, b_, _ = M['ember2018_pub|F1_emp0.1_native_MarSep']; rows.append(('EMBER-2018 GBDT, [1] op. point (MoC)', a_, b_, 'm'))
    a_, b_, _ = M['lgbm_trace|F1_emp0.1_native_MarSep']; rows.append(('LGBM-TRACE, [1] op. point (MoC)', a_, b_, 'm'))
    a_, b_, _ = M['lgbm_trace|F1_cert0.1_native_MarSep']; rows.append(('LGBM-TRACE, CP-certified (MoC)', a_, b_, 'm'))
    a_, b_, _ = M['lgbm_trace|F1_cert0.1_pi10_MarSep']; rows.append(('LGBM-TRACE, certified, π = 10% (MoC)', a_, b_, 'm'))
    for i, (lab, lo, hi, kind) in enumerate(rows):
        col = SLOT[0] if kind == 'r' else SLOT[1]
        axes[0].plot([lo, hi], [i, i], color=col, lw=2.2, solid_capstyle='round'); axes[0].plot([lo, hi], [i, i], 'o', color=col, ms=3.5)
    axes[0].set_yticks(range(len(rows))); axes[0].set_yticklabels([r[0] for r in rows], fontsize=5.8); axes[0].set_xlabel('monthly F1 (%), range over test months')
    axes[0].set_title('Temporal F1 on BODMAS'); axes[0].grid(axis='y', visible=False)
    rows2 = [('[1] Table III (RfP)', P['BODMAS_T3_FNR']['lo'], P['BODMAS_T3_FNR']['hi'], 'r')]
    for k in ('dated|lgbm_ember', 'dated+prewindow|lgbm_ember'):
        if f'T0|{k}|FNR' in M:
            lo, hi = M[f'T0|{k}|FNR']; rows2.append((f"T0 replication, {k.split('|')[0].replace('+prewindow', ' + PreWindow')} (MoC)", lo, hi, 'm'))
    lo, hi, _ = M['lgbm_trace|FNR_emp0.1_JanSep']; rows2.append(('LGBM-TRACE, [1] op. point (MoC)', lo, hi, 'm'))
    lo, hi, _ = M['lgbm_trace|FNR_cert0.1_JanSep']; rows2.append(('LGBM-TRACE, CP-certified (MoC)', lo, hi, 'm'))
    for i, (lab, lo, hi, kind) in enumerate(rows2):
        col = SLOT[0] if kind == 'r' else SLOT[1]
        axes[1].plot([lo, hi], [i, i], color=col, lw=2.2, solid_capstyle='round'); axes[1].plot([lo, hi], [i, i], 'o', color=col, ms=3.5)
    axes[1].set_yticks(range(len(rows2))); axes[1].set_yticklabels([r[0] for r in rows2], fontsize=5.8); axes[1].set_xlabel('monthly FNR (%), range')
    axes[1].set_xlim(0, None); axes[1].set_title('Recall decay (Jan–Sep 2020)'); axes[1].grid(axis='y', visible=False)
    p1 = A.get('P1', {}); rows3 = [('[1] EMBER-GBDT, random val. (RfP)', P['BODMAS_T2_EmberGBDT_valF1']['value'], 'r'),
                                   ('[94] D3QN, no temporal split (RfP)', P['D3QN_BODMAS_F1']['value'], 'r')]
    if p1:
        rr = pd.DataFrame(p1['rows'])
        rows3 += [('LGBM-TRACE, random split (MoC)', 100 * rr.random_f1.mean(), 'm'), ('LGBM-TRACE, temporal AUT (MoC)', 100 * rr.temporal_aut_f1.mean(), 'm')]
    for i, (lab, v, kind) in enumerate(rows3):
        axes[2].plot(v, i, 'o' if kind == 'r' else 'D', color=SLOT[0] if kind == 'r' else SLOT[1], ms=5)
        axes[2].text(v - 0.35, i + 0.22, f'{v:.2f}', ha='right', fontsize=6, color=INK2)
    axes[2].set_xlim(88, 100); axes[2].set_ylim(-0.6, len(rows3) - 0.4); axes[2].set_yticks(range(len(rows3)))
    axes[2].set_yticklabels([r[0] for r in rows3], fontsize=5.8); axes[2].set_xlabel('F1, native ratio (%)'); axes[2].set_title('Split-induced inflation')
    axes[2].grid(axis='y', visible=False)
    fig.tight_layout(w_pad=0.6)
    save(fig, 'fig20_comparison', 'Comparison with published results. Blue: reproduced-from-paper (RfP) values as reported (BODMAS [1] Tables II–III; D3QN [94]); '
         'orange: measured-on-Claude (MoC) under this paper\'s protocol (Dated stratum; thresholds fitted on December 2019; months March–September 2020 for F1, '
         'January–September for FNR; LGBM-TRACE values are 5-seed means). Protocols differ (training data, months, operating point), so the comparison shows '
         'magnitudes, not a like-for-like ranking; the T0 rows replicate [1]\'s Table III protocol on our strata. Right: dot plot (axis does not start at zero).',
         'reproduced-from-paper (blue); measured-on-Claude (orange)')


def fig_ember():
    E = json.load(open(f'{C.OUT}/ember.json')); P = json.load(open(f'{C.ROOT}/code/published_baselines.json'))
    cert = json.load(open(f'{C.OUT}/analysis_certificates.json'))['thr0.001|tau0.001/0.02']['months']
    B = json.load(open(f'{C.OUT}/analysis_bias.json'))['P1']
    fig, axes = plt.subplots(1, 3, figsize=(7.16, 2.5), gridspec_kw=dict(width_ratios=[1.3, 0.9, 1.1]))
    ax = axes[0]
    em = [f'2018-{k:02d}' for k in range(7, 13)]
    series = [('BODMAS f₀ (train Aug–Nov 2019; Mar–Sep 2020)', [100 * cert[mm]['fnr'] for mm in C.CERT_MONTHS], 0, 'o'),
              ('EMBER-2018, within-dataset (train Jan–Apr; Jul–Dec)', [100 * E['temporal']['0.001']['months'][mm]['fnr'] for mm in em], 1, 's'),
              ('EMBER-2018-trained → BODMAS Mar–Sep 2020', [100 * E['forward_EMBER2018_to_BODMAS2020']['months'][mm]['fnr'] for mm in C.CERT_MONTHS], 2, '^')]
    for lab, v, k, mk in series:
        ax.plot(np.arange(1, len(v) + 1), v, marker=mk, color=SLOT[k], label=lab)
    ax.set_xlabel('test month index (1 = first test month)'); ax.set_ylabel('FNR at CP-certified θ@0.1% (%)'); ax.set_ylim(0, 112)
    ax.set_title('FNR at a certified 0.1% FPR threshold'); ax.legend(fontsize=5.6, loc='upper left', handlelength=1.6)
    ax = axes[1]
    vals = [('BODMAS', B['mean_pp_pi10'], B['ci_pi10']), ('EMBER-2018', E['random_arm']['mean_pp'], E['random_arm']['ci'])]
    for i, (lab, v, c) in enumerate(vals):
        ax.bar(i, v, width=0.55, color=SLOT[i]); ax.plot([i, i], c, color=INK, lw=0.9)
        ax.text(i, c[1] + 0.6, f'{v:+.2f} pp', ha='center', fontsize=6.2, color=INK2)
    ax.set_xticks([0, 1]); ax.set_xticklabels([v[0] for v in vals]); ax.set_ylabel('ΔF1 at π = 10%, random − temporal (pp)', fontsize=6.5)
    ax.set_title('Random-split inflation (5 seeds)'); ax.grid(axis='x', visible=False); ax.set_ylim(0, max(v[2][1] for v in vals) + 4)
    ax = axes[2]
    pm = E['published_model_on_EMBER_test_NovDec']
    rows = [('AUC-ROC', 100 * P['EMBER2018_LGBM_AUC']['value'], 100 * pm['auc']), ('TPR @ 1% FPR', P['EMBER2018_LGBM_TPR_1']['value'], 100 * pm['tpr_at_fpr_1e2_testtuned']),
            ('TPR @ 0.1% FPR', P['EMBER2018_LGBM_TPR_0.1']['value'], 100 * pm['tpr_at_fpr_1e3_testtuned'])]
    for i, (lab, r, mv) in enumerate(rows):
        ax.plot([r, mv], [i, i], color=GREY, lw=1.0, zorder=1)
        ax.plot(r, i, 'o', color=SLOT[0], ms=5, zorder=2, label='release notebook [2] (RfP)' if i == 0 else None)
        ax.plot(mv, i, 'D', color=SLOT[1], ms=4.5, zorder=3, label='this vectorisation (MoC)' if i == 0 else None)
        ax.text(101.2, i, f'Δ = {mv - r:+.2f} pp', va='center', fontsize=6, color=INK2)
    ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows]); ax.set_xlim(84, 109); ax.set_ylim(-0.6, 2.6); ax.set_xlabel('%')
    ax.set_xticks([85, 90, 95, 100])
    ax.set_title('Published EMBER-2018 model'); ax.grid(axis='y', visible=False)
    ax.legend(fontsize=5.6, loc='upper center', bbox_to_anchor=(0.45, -0.22), ncol=1)
    fig.tight_layout(w_pad=1.0)
    save(fig, 'fig21_ember2018', 'EMBER-2018 corroboration (D10). Left: FNR at a CP-certified 0.1% FPR threshold by test month for f₀ on BODMAS, for the same '
         'pipeline trained and tested inside EMBER-2018 (month-stratified sub-sample), and for the EMBER-trained detector applied forward to BODMAS 2020. '
         'Centre: random-split inflation of F1 at π = 10% over the temporal AUT (5 seeds; 95% CI). Right: pipeline check with the published EMBER-2018 '
         'model, release-notebook values (full test set) versus this vectorisation (stratified sub-sample).',
         'measured-on-Claude (orange/centre/left); reproduced from the EMBER release notebook (blue dots, right)')


ALL = ['fig_metric_bars', 'fig_roc_pr', 'fig_confusion', 'fig_decay', 'fig_certificates', 'fig_baserate', 'fig_drift', 'fig_monitor',
       'fig_importance', 'fig_timing', 'fig_learning', 'fig_cv', 'fig_reval', 'fig_attribution', 'fig_ledger', 'fig_comparison', 'fig_ember']
if __name__ == '__main__':
    for f in (sys.argv[1:] or ALL):
        try:
            globals()[f]()
        except Exception as e:
            print('FAILED', f, repr(e))
