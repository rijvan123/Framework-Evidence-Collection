"""Temporal-evidence screen (M2; paper Section 4.3, rules R-T1..R-T6).

All rules act on metadata before any split: dual-format timestamp parsing, the common window,
the k*MAD spike rule on all-sample daily counts, the precision regime, and the strata
Dated / Placeholder / Bulk / SpikeMal / Quarantine / PreWindow. Temporal operations use UTC days;
intra-day order is lexicographic in SHA-256 so that order cannot leak the class."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..decision.thresholds import cp_upper
from ..utils import month_list

SHA256_RE = r'[0-9a-f]{64}'


def parse_timestamps(ts: pd.Series):
    """R-T1: explicit-offset and naive timestamps; naive values are read as UTC and flagged."""
    has_offset = ts.str.contains(r'[+-]\d\d:\d\d$', regex=True).to_numpy()
    fs = pd.to_datetime(ts, utc=True, format='ISO8601')
    return fs, has_offset


def spike_rule(day_counts: pd.Series, k: float) -> dict:
    """Days whose count exceeds median + k * (unscaled) MAD."""
    med = float(day_counts.median())
    mad = float((day_counts - med).abs().median())
    thr = med + k * mad
    days = {str(d): int(v) for d, v in day_counts[day_counts > thr].items()}
    return dict(days_counted=int(len(day_counts)), median=med, mad=mad, k=k, threshold=thr, spike_days=days)


def screen(meta: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, dict]:
    """meta needs columns sid, timestamp, family, y. Returns meta with screening columns and a report."""
    sc = cfg['screen']
    m = meta.copy()
    fs, has_offset = parse_timestamps(m['timestamp'])
    m['fs'] = fs
    m['has_offset'] = has_offset
    day = fs.dt.floor('D')
    m['date'] = fs.dt.strftime('%Y-%m-%d')
    m['day'] = ((day - pd.Timestamp('1970-01-01', tz='UTC')) // pd.Timedelta(days=1)).astype(np.int64)
    m['month'] = fs.dt.strftime('%Y-%m')
    m['tod'] = fs.dt.strftime('%H:%M:%S')
    m['midnight'] = (m['tod'] == '00:00:00').to_numpy()
    w0 = pd.Timestamp(sc['window_start'], tz='UTC')
    w1 = pd.Timestamp(sc['window_end'], tz='UTC')
    in_win = ((fs >= w0) & (fs < w1)).to_numpy()
    m['in_win'] = in_win
    y = m['y'].to_numpy()
    m['quarantine'] = ~m['sid'].str.fullmatch(SHA256_RE).to_numpy()

    # R-T3 spike rule on the all-sample daily series (and the benign series, recorded)
    daily_all = m.loc[in_win].groupby('date').size()
    daily_ben = m.loc[in_win & (y == 0)].groupby('date').size()
    rule = {f'all_k{sc["spike_k"]}': spike_rule(daily_all, sc['spike_k']),
            f'all_k{sc["spike_k_sensitivity"]}': spike_rule(daily_all, sc['spike_k_sensitivity']),
            f'benign_k{sc["spike_k"]}': spike_rule(daily_ben, sc['spike_k']),
            f'benign_k{sc["spike_k_sensitivity"]}': spike_rule(daily_ben, sc['spike_k_sensitivity'])}
    spike_days = set(rule[f'all_k{sc["spike_k"]}']['spike_days'])
    spike_days_sens = set(rule[f'all_k{sc["spike_k_sensitivity"]}']['spike_days'])
    on_spike = in_win & m['date'].isin(spike_days).to_numpy()
    m['censored'] = on_spike
    m['spike_sens'] = in_win & m['date'].isin(spike_days_sens).to_numpy()

    # R-T5 placeholder vs bulk: share of benign rows at exactly midnight on each spike day
    regime = {}
    for d in sorted(spike_days):
        sel = (m['date'] == d).to_numpy() & (y == 0)
        share = float(m['midnight'].to_numpy()[sel].mean()) if sel.any() else 0.0
        regime[d] = 'Placeholder' if share >= sc.get('placeholder_midnight_share', 0.99) else 'Bulk'

    stratum = np.full(len(m), 'Dated', dtype=object)
    stratum[(fs < w0).to_numpy()] = 'PreWindow'
    stratum[(fs >= w1).to_numpy()] = 'PostWindow'
    for d, kind in regime.items():
        sel = (m['date'] == d).to_numpy()
        stratum[sel & (y == 0)] = kind
        stratum[sel & (y == 1)] = 'SpikeMal'
    stratum[m['quarantine'].to_numpy()] = 'Quarantine'
    m['stratum'] = stratum

    split = np.full(len(m), '', dtype=object)
    dated = stratum == 'Dated'
    split[dated & (fs < pd.Timestamp(sc['train_end'], tz='UTC')).to_numpy()] = 'train'
    split[dated & (m['month'] == sc['calibration_month']).to_numpy()] = 'calibration'
    split[dated & (fs >= pd.Timestamp(sc['test_start'], tz='UTC')).to_numpy()] = 'test'
    m['split'] = split
    m['order'] = np.lexsort((m['sid'].to_numpy(), m['day'].to_numpy())).argsort()

    # ------------------------------------------------------------------ report
    def cls_counts(mask):
        return dict(benign=int((mask & (y == 0)).sum()), malware=int((mask & (y == 1)).sum()))

    strata = {s: cls_counts(stratum == s) for s in ['Dated', 'PreWindow', 'Placeholder', 'Bulk', 'SpikeMal',
                                                      'Quarantine', 'PostWindow']}
    splits = {s: cls_counts(split == s) for s in ['train', 'calibration', 'test']}
    months_in = sorted(set(m.loc[in_win, 'month']))
    monthly = {}
    for mo in months_in:
        sm = (m['month'] == mo).to_numpy()
        b = int((sm & dated & (y == 0)).sum())
        mw = int((sm & dated & (y == 1)).sum())
        cb = int((sm & on_spike & (y == 0)).sum())
        cm = int((sm & on_spike & (y == 1)).sum())
        monthly[mo] = dict(dated_benign=b, dated_malware=mw, censored_benign=cb, censored_malware=cm,
                           fpr_ub0=round(cp_upper(0, b) * 100, 4), fpr_ub1=round(cp_upper(1, b) * 100, 4),
                           fnr_ub0=round(cp_upper(0, mw) * 100, 4))
    normal = in_win & ~on_spike
    mid = m['midnight'].to_numpy()
    precision = {}
    for c, nm in [(0, 'benign'), (1, 'malware')]:
        sel = normal & (y == c)
        precision[nm] = dict(n=int(sel.sum()), midnight_share=round(float(mid[sel].mean()) if sel.any() else 0.0, 4),
                             by_month={mo: round(float(mid[sel & (m['month'] == mo).to_numpy()].mean()), 3)
                                       for mo in months_in if (sel & (m['month'] == mo).to_numpy()).any()})
    pre = (fs < w0).to_numpy() & (y == 0)
    precision['pre_window_benign_midnight_share'] = round(float(mid[pre].mean()), 4) if pre.any() else None
    tod = m['tod'].to_numpy()
    spikes = {}
    for d in sorted(spike_days):
        s_ = (m['date'] == d).to_numpy()
        spikes[d] = dict(rows=int(s_.sum()), benign=int((s_ & (y == 0)).sum()), malware=int((s_ & (y == 1)).sum()),
                         benign_midnight=int((s_ & (y == 0) & mid).sum()),
                         benign_distinct_times=int(len(set(tod[s_ & (y == 0)]))),
                         malware_distinct_times=int(len(set(tod[s_ & (y == 1)]))),
                         malware_midnight=int((s_ & (y == 1) & mid).sum()), regime=regime[d])
    naive = ~has_offset
    report = dict(
        timestamp_formats=dict(with_utc_offset=int(has_offset.sum()), without_offset=int(naive.sum()),
                               without_offset_range=[str(fs[naive].min()), str(fs[naive].max())] if naive.any() else None,
                               rows_sorted_by_first_seen=bool(fs.is_monotonic_increasing)),
        window=[sc['window_start'], sc['window_end']], spike_rule=rule, spike_days=spikes,
        strata=strata, splits=splits, monthly=monthly, precision_regime=precision,
        quarantine_ids=int(m['quarantine'].sum()),
        in_window_rows=int(in_win.sum()), months=months_in,
        test_months=month_list(sc['test_months'][0], sc['test_months'][-1]))
    return m, report
