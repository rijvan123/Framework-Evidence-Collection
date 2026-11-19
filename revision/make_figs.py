"""Re-drawn Figs. 6, 11, 12 and 17 of the revised manuscript (label collisions removed; Fig. 17a series corrected).
Every plotted value is copied from the original run's result tables / output files (S10 package); nothing is re-computed
from data. Colours follow the other figures of the paper (Okabe-Ito)."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

OR, BL, PK, GR, SKY, GY = '#D55E00', '#0072B2', '#CC79A7', '#009E73', '#56B4E9', '#7f7f7f'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 7.5, 'axes.titlesize': 7.8, 'axes.labelsize': 7.5,
                     'xtick.labelsize': 7, 'ytick.labelsize': 7, 'legend.fontsize': 6.8, 'axes.spines.top': False,
                     'axes.spines.right': False, 'axes.grid': True, 'grid.color': '#e3e3e3', 'grid.linewidth': 0.6,
                     'axes.axisbelow': True, 'savefig.dpi': 330, 'axes.titlelocation': 'left', 'axes.titlepad': 6})
W = 6.2


def save(fig, name):
    fig.savefig(f'{name}.png', bbox_inches='tight', pad_inches=0.04, facecolor='white')
    plt.close(fig)


# ------------------------------------------------------------------------------------------------ Fig. 6
# Table 12: pooled March-September stream, certified 0.1% threshold. (TPR %, FPR %); seed means for multi-seed models.
zoo = [('Temporal stacking', 89.44, 0.009), ('LGBM-EMBER', 87.71, 0.007), ('LGBM-TRACE (f₀ family)', 84.12, 0.008),
       ('EMBER-2018 GBDT (pub.)', 90.11, 0.030), ('Extra trees', 81.60, 0.002), ('Random forest', 75.95, 0.005),
       ('XGBoost', 75.64, 0.003), ('RBF-SVM (PoC)', 38.53, 0.000), ('LR + χ²(256)', 36.13, 0.011),
       ('LR + mRMR(128)', 32.83, 0.036), ('MLP (PoC)', 22.62, 0.011), ('LR', 17.09, 0.022), ('Gaussian NB', 10.52, 0.144),
       ('Linear SVM', 5.73, 0.022), ('LR + IG(256)', 1.01, 0.019), ('LR + PCA(0.95)', 0.01, 0.003), ('k-NN (PCA-50)', 0.00, 0.000)]
# label positions (x in % FPR, y in % TPR) chosen to avoid collisions; leader lines join label and point
lab = {'Temporal stacking': (0.013, 101.5), 'LGBM-EMBER': (0.00105, 97.0), 'LGBM-TRACE (f₀ family)': (0.0135, 78.5),
       'EMBER-2018 GBDT (pub.)': (0.045, 92.0), 'Extra trees': (0.00034, 88.0), 'Random forest': (0.0095, 66.5),
       'XGBoost': (0.00034, 69.0), 'RBF-SVM (PoC)': (0.00034, 47.5), 'LR + χ²(256)': (0.0165, 45.0),
       'LR + mRMR(128)': (0.06, 36.0), 'MLP (PoC)': (0.0034, 29.0), 'LR': (0.042, 21.5), 'Gaussian NB': (0.075, 14.5),
       'Linear SVM': (0.045, 5.0), 'LR + IG(256)': (0.0052, 9.0), 'LR + PCA(0.95)': (0.00075, 3.6), 'k-NN (PCA-50)': (0.00034, 15.0)}
ZERO = 0.0003                     # plotting position for zero false positives (marked x)
fig, (a, b) = plt.subplots(1, 2, figsize=(W, 3.25), gridspec_kw=dict(width_ratios=[1.25, 1]), constrained_layout=True)
for name, tpr, fpr in zoo:
    x = fpr if fpr > 0 else ZERO
    c = OR if name.startswith('LGBM-TRACE') else (BL if name.startswith('EMBER-2018') else GY)
    mk = 'X' if fpr == 0 else 'o'
    a.scatter(x, tpr, s=26 if c != GY else 18, marker=mk, color=c, zorder=3, edgecolor='white', linewidth=0.6)
    lx, ly = lab[name]
    a.annotate(name, (x, tpr), xytext=(lx, ly), textcoords='data', fontsize=6.2, color='#222222', va='center',
               ha='left', arrowprops=dict(arrowstyle='-', color='#9a9a9a', lw=0.5, shrinkA=0, shrinkB=2.5))
a.axvline(0.1, color=BL, lw=0.8, ls='--', zorder=1)
a.text(0.115, 62.0, '0.1% FPR\ntarget', fontsize=5.8, color=BL, va='center')
a.set_xscale('log'); a.set_xlim(0.0002, 1.0); a.set_ylim(-3, 106)
a.set_xticks([0.0003, 0.001, 0.01, 0.1, 1.0]); a.set_xticklabels(['0 FP', '0.001', '0.01', '0.1', '1'])
a.minorticks_off()
a.set_xlabel('realised FPR (%), log scale'); a.set_ylabel('TPR (%)')
a.set_title('(a) operating points at the certified 0.1% threshold')
# (b) precision at prevalence pi from Eq. (55) using the same TPR and FPR
for name, tpr, fpr in zoo:
    if tpr == 0:
        continue
    t, f = tpr / 100, fpr / 100
    c = OR if name.startswith('LGBM-TRACE') else (BL if name.startswith('EMBER-2018') else GY)
    for pi, mk, fill in ((0.10, 'o', True), (0.01, 's', False)):
        p = 100 * pi * t / (pi * t + (1 - pi) * f) if f > 0 else 100.0
        b.scatter(tpr, p, s=20, marker=mk, facecolor=c if fill else 'white', edgecolor=c, linewidth=0.9, zorder=3)
b.set_xlim(-3, 100); b.set_ylim(-3, 104)
b.set_xlabel('recall = TPR (%)'); b.set_ylabel('precision at deployment prevalence π (%)')
b.set_title('(b) precision at π = 10% and 1%, Eq. (55)')
hb = [Line2D([], [], marker='o', ls='', color=GY, label='π = 10%', markersize=4.5),
      Line2D([], [], marker='s', ls='', markerfacecolor='white', markeredgecolor=GY, color=GY, label='π = 1%', markersize=4.5),
      Line2D([], [], marker='o', ls='', color=OR, label='LGBM-TRACE (f₀ family)', markersize=4.5),
      Line2D([], [], marker='o', ls='', color=BL, label='EMBER-2018 GBDT (pub.)', markersize=4.5)]
b.legend(handles=hb, loc='lower right', frameon=True, framealpha=0.95, edgecolor='#dddddd', borderpad=0.5)
save(fig, 'fig6_operating_points')

# ------------------------------------------------------------------------------------------------ Fig. 11
seeds = [11, 23, 37, 41, 53]
rnd = [96.04, 98.76, 98.81, 97.99, 97.80]           # Table 14: random-split F1 at pi = 10%
tmp = [93.35, 89.52, 91.36, 89.03, 91.51]           # Table 14: temporal AUT(F1 at pi = 10%)
cv = [('LGBM-TRACE (f₀)', 99.30, 99.23, 99.46, 90.72, 82.83, 96.82, 1.10, 16.25),
      ('XGBoost', 99.39, 99.29, 99.49, 85.17, 75.51, 92.93, 0.79, 24.81),
      ('Extra trees', 99.20, 99.04, 99.33, 89.38, 77.86, 95.47, 1.17, 18.59),
      ('Random forest', 99.06, 98.91, 99.26, 85.50, 71.26, 93.72, 1.39, 24.37),
      ('LR', 25.39, 0.35, 60.45, 27.66, 16.18, 48.28, 83.48, 83.47),
      ('Gaussian NB', 22.74, 0.02, 41.54, 18.90, 4.76, 31.16, 85.86, 89.13)]
fig = plt.figure(figsize=(W, 3.0), constrained_layout=True)
gs = fig.add_gridspec(1, 3, width_ratios=[0.8, 1.45, 1.0])
a, b, c = fig.add_subplot(gs[0]), fig.add_subplot(gs[1]), fig.add_subplot(gs[2])
for s_, r_, t_ in zip(seeds, rnd, tmp):
    a.plot([0, 1], [r_, t_], color='#b0b0b0', lw=0.9, zorder=1)
    a.scatter([0], [r_], color=PK, s=18, zorder=3, edgecolor='white', linewidth=0.5)
    a.scatter([1], [t_], color=OR, s=18, marker='s', zorder=3, edgecolor='white', linewidth=0.5)
a.set_xticks([0, 1]); a.set_xticklabels(['random\nsplit', 'temporal\nAUT']); a.set_xlim(-0.35, 1.35)
a.set_ylabel('F1 at π = 10% (%)'); a.set_ylim(88.3, 99.6)
a.set_title('(a) per seed (5 seeds)')
a.text(-0.3, 88.6, 'mean +6.93 pp\n95% CI [4.59, 8.72]', ha='left', va='bottom', fontsize=6.0, color='#333333')
y = np.arange(len(cv))[::-1]
for yi, (nm, cm, clo, chi, tm, tlo, thi, cfnr, tfnr) in zip(y, cv):
    b.errorbar(cm, yi + 0.17, xerr=[[cm - clo], [chi - cm]], fmt='o', color=PK, ms=3.6, lw=0.9, capsize=2)
    b.errorbar(tm, yi - 0.17, xerr=[[tm - tlo], [thi - tm]], fmt='s', color=OR, ms=3.4, lw=0.9, capsize=2)
b.set_yticks(y); b.set_yticklabels([r[0] for r in cv]); b.set_xlim(-2, 102); b.set_ylim(-0.7, len(cv) - 0.3)
b.set_xlabel('F1 at π = 10% (%)')
b.set_title('(b) 5-fold CV versus temporal months')
for yi, (nm, *_rest) in zip(y, cv):
    cfnr, tfnr = _rest[-2], _rest[-1]
    c.barh(yi + 0.19, cfnr, height=0.36, color=PK, edgecolor='white', linewidth=0.6)
    c.barh(yi - 0.19, tfnr, height=0.36, color=OR, edgecolor='white', linewidth=0.6)
    c.text(cfnr + 1.5, yi + 0.19, f'{cfnr:.1f}', va='center', fontsize=5.8, color='#333333')
    c.text(tfnr + 1.5, yi - 0.19, f'{tfnr:.1f}', va='center', fontsize=5.8, color='#333333')
c.set_yticks(y); c.set_yticklabels([]); c.set_xlim(0, 104); c.set_ylim(-0.7, len(cv) - 0.3)
c.set_xlabel('mean FNR (%)')
c.set_title('(c) FNR at the certified \u03b8')
leg = [Line2D([], [], marker='o', color=PK, ls='-', lw=0.9, ms=3.6, label='random split / random 5-fold CV (biased arm)'),
       Line2D([], [], marker='s', color=OR, ls='-', lw=0.9, ms=3.4, label='temporal protocol (months March–September)')]
fig.legend(handles=leg, loc='lower center', ncol=2, bbox_to_anchor=(0.5, -0.075), frameon=False)
save(fig, 'fig11_random_vs_temporal')

# ------------------------------------------------------------------------------------------------ Fig. 12
months = ['Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep']
pooled = [3.03, 15.76, 19.26, 5.34, 4.11, 8.00, 11.44, 8.65, 10.12, 4.79]     # Table S12 / S10 Table 10
benign = [2.74, 35.53, 52.04, 2.05, 4.98, 6.58, 6.03, 4.03, 4.92, 4.82]
malw = [7.72, 5.45, 10.65, 11.99, 8.45, 17.24, 32.84, 24.40, 28.84, 20.13]
f1 = {'Mar': 96.51, 'Apr': 97.45, 'May': 97.33, 'Jun': 97.11, 'Jul': 90.86, 'Aug': 85.95, 'Sep': 86.31}   # Table 13
stats = ['C2ST\nAUC', 'KS on\nmargins', 'mean\nPSI', '1 − mean\ncredibility']
exc_b = [22, 5, 5, 2]; exc_m = [28, 24, 9, 21]                                # windows of 31 above lambda
fig = plt.figure(figsize=(W, 2.95), constrained_layout=True)
gs = fig.add_gridspec(1, 3, width_ratios=[1.25, 0.95, 1.05])
a, b, c = fig.add_subplot(gs[0]), fig.add_subplot(gs[1]), fig.add_subplot(gs[2])
x = np.arange(len(months))
a.axvspan(6.5, 9.5, color='#f4e4c9', alpha=0.6, lw=0, zorder=0)
a.plot(x, pooled, color='#222222', marker='o', ms=3.2, lw=1.4, label='pooled D(t)')
a.plot(x, benign, color=GR, marker='s', ms=3.0, lw=1.0, ls='--', label='benign class')
a.plot(x, malw, color=PK, marker='^', ms=3.4, lw=1.0, ls='--', label='malware class')
a.set_xticks(x); a.set_xticklabels(months, fontsize=6.4); a.set_ylabel('JS drift ×10³ (bits)')
a.set_title('(a) drift relative to Aug–Nov 2019')
a.legend(loc='upper right', frameon=True, framealpha=0.95, edgecolor='#dddddd')
a.text(8.0, -6.5, 'Jul–Sep', ha='center', fontsize=5.8, color='#8a6a2a')
a.set_ylim(-9, 56)
d_ = dict(zip(months, pooled))
off = {'Mar': (4, -10), 'Apr': (-3, 6), 'May': (-4, 6), 'Jun': (-15, -11), 'Jul': (5, 2), 'Aug': (-6, 6), 'Sep': (5, 2)}
for mm, v in f1.items():
    b.scatter(d_[mm], v, color=OR, s=20, zorder=3, edgecolor='white', linewidth=0.5)
    b.annotate(mm, (d_[mm], v), xytext=off[mm], textcoords='offset points', fontsize=6.2)
b.set_xlabel('pooled D(t) ×10³, March–September'); b.set_ylabel('f₀ F1 at π = 10% (%)')
b.set_xlim(3.3, 12.4); b.set_ylim(84.5, 98.8)
b.set_title('(b) drift vs F1 (ρ = −0.32)')
xs = np.arange(len(stats))
c.bar(xs - 0.2, exc_b, width=0.38, color=GR, edgecolor='white', linewidth=0.6, label='predicted benign')
c.bar(xs + 0.2, exc_m, width=0.38, color=PK, edgecolor='white', linewidth=0.6, hatch='////', label='predicted malicious')
for xi, vb, vm in zip(xs, exc_b, exc_m):
    c.text(xi - 0.2, vb + 0.6, str(vb), ha='center', fontsize=5.8); c.text(xi + 0.2, vm + 0.6, str(vm), ha='center', fontsize=5.8)
c.axhline(31, color='#888888', lw=0.8, ls=':')
c.text(3.62, 31.6, '31 = all windows', fontsize=5.6, color='#666666', ha='right', va='bottom')
c.set_xticks(xs); c.set_xticklabels(stats, fontsize=6.0); c.set_ylim(0, 48); c.set_yticks([0, 10, 20, 30])
c.set_ylabel('windows above λ (of 31)')
c.set_title('(c) monitor M8 exceedances')
c.legend(loc='upper left', frameon=False, ncol=1, bbox_to_anchor=(0.0, 1.02), handlelength=1.6)
save(fig, 'fig12_drift_monitor')

# ------------------------------------------------------------------------------------------------ Fig. 17
bod = [4.07, 5.86, 6.51, 4.98, 5.07, 5.62, 16.76, 24.64, 23.92]        # f0 on BODMAS, Jan-Sep 2020, theta@0.1% (Table 13)
e01 = [52.48, 59.50, 72.48, 61.48, 58.13, 66.68]                        # within EMBER-2018, Jul-Dec 2018, theta@0.1% (FNR)
e05 = [27.89, 33.23, 42.70, 36.03, 31.01, 38.97]                        # within EMBER-2018, theta@0.5% (FNR) -- corrected series
fig = plt.figure(figsize=(W, 3.05), constrained_layout=True)
gs = fig.add_gridspec(1, 3, width_ratios=[1.35, 0.8, 1.0])
a, b, c = fig.add_subplot(gs[0]), fig.add_subplot(gs[1]), fig.add_subplot(gs[2])
a.plot(range(1, 10), bod, color=OR, marker='o', ms=3.4, lw=1.4, label='f₀ on BODMAS (Jan–Sep 2020), θ@0.1%')
a.plot(range(1, 7), e01, color=BL, marker='s', ms=3.4, lw=1.4, label='within EMBER-2018 (Jul–Dec 2018), θ@0.1%')
a.plot(range(1, 7), e05, color=SKY, marker='D', ms=3.2, lw=1.2, ls='--', label='within EMBER-2018, θ@0.5%')
a.set_xticks(range(1, 10)); a.set_xlabel('month after the calibration window'); a.set_ylabel('FNR (%)')
a.set_ylim(0, 100); a.set_xlim(0.6, 9.4)
a.set_title('(a) FNR at the certified threshold')
a.legend(loc='upper left', frameon=True, framealpha=0.95, edgecolor='#dddddd', fontsize=6.2)
vals, lo, hi = [6.93, 19.86], [4.59, 18.17], [8.72, 21.81]
b.bar([0, 1], vals, width=0.6, color=[OR, BL], edgecolor='white', linewidth=0.6)
b.errorbar([0, 1], vals, yerr=[np.subtract(vals, lo), np.subtract(hi, vals)], fmt='none', color='#333333', lw=0.9, capsize=3)
for xi, v in enumerate(vals):
    b.text(xi, hi[xi] + 0.8, f'+{v:.2f}', ha='center', fontsize=6.4)
b.set_xticks([0, 1]); b.set_xticklabels(['BODMAS', 'EMBER-\n2018']); b.set_ylim(0, 26)
b.set_ylabel('F1 inflation (pp), 95% CI'); b.grid(axis='x', visible=False)
b.set_title('(b) random-split inflation')
items = ['AUC-ROC', 'TPR at\n0.1% FPR', 'TPR at\n1% FPR']
rel = [99.643, 86.81, 96.50]; ours = [99.659, 85.49, 96.23]; dl = ['+0.02', '−1.32', '−0.26']
yy = np.arange(3)[::-1]
for yi, r_, o_, d in zip(yy, rel, ours, dl):
    c.scatter(r_, yi + 0.14, color=BL, s=24, zorder=3, edgecolor='white', linewidth=0.5)
    c.scatter(o_, yi - 0.14, color=OR, s=24, marker='s', zorder=3, edgecolor='white', linewidth=0.5)
    c.text(102.9, yi, f'{d} pp', ha='right', va='center', fontsize=6.2, color='#333333')
c.text(102.9, 2.55, '\u0394', ha='right', va='center', fontsize=6.4, color='#333333')
c.set_yticks(yy); c.set_yticklabels(items, fontsize=6.4); c.set_xlim(84.0, 103.2); c.set_ylim(-0.75, 2.8)
c.set_xticks([85, 90, 95, 100])
c.set_xlabel('value (%)')
c.set_title('(c) same published model file')
lc = [Line2D([], [], marker='o', ls='', color=BL, label='release notebook {RfP}', markersize=4.5),
      Line2D([], [], marker='s', ls='', color=OR, label='this vectorisation {MoC}', markersize=4.5)]
c.legend(handles=lc, loc='lower left', frameon=True, framealpha=0.95, edgecolor='#dddddd', fontsize=5.9, bbox_to_anchor=(0.0, 0.0))
save(fig, 'fig17_ember2018')
print('ok')
