"""Temporal-evidence screen and intake. The intake test runs E0 on a small synthetic BODMAS-format release
and checks that the acquisition-chain head and oracle Merkle root equal those of a verbatim transcription of
the S7 probe code: on the real release this reproduces the paper's checkpoints."""
import json
import subprocess
import sys

import pandas as pd

import s7_reference as S7
from tracepe.config import ROOT
from tracepe.data.synthetic import make_synthetic_bodmas
from tracepe.evidence.hashing import sha256_file
from tracepe.evidence.screen import parse_timestamps, spike_rule


def test_dual_timestamp_formats():
    ts = pd.Series(['2019-09-01 10:00:00+00:00', '2018-01-02 03:04:05', '2020-01-01 00:00:00+02:00'])
    fs, off = parse_timestamps(ts)
    assert list(off) == [True, False, True]
    assert str(fs.iloc[1]) == '2018-01-02 03:04:05+00:00'        # naive values are read as UTC
    assert str(fs.iloc[2]) == '2019-12-31 22:00:00+00:00'


def test_spike_rule_unscaled_mad():
    counts = pd.Series([10, 12, 11, 9, 10, 300, 11, 10], index=pd.date_range('2020-01-01', periods=8))
    r = spike_rule(counts, 10)
    assert r['median'] == 10.5 and r['mad'] == 0.5 and r['threshold'] == 15.5
    assert list(r['spike_days']) == ['2020-01-06 00:00:00']


def test_intake_reproduces_s7_checkpoints(tmp_path):
    data = tmp_path / 'bodmas'
    make_synthetic_bodmas(data, seed=11, scale=0.4)
    run_dir = tmp_path / 'run'
    cmd = [sys.executable, str(ROOT / 'scripts' / 'e00_intake.py'), '--config', 'configs/smoke.yaml',
           '--set', f'run.dir={run_dir}', '--set', f'data.bodmas_dir={data}',
           '--set', f'acquisition.expected_sha256={data / "SOURCE_SHA256.json"}']
    subprocess.run(cmd, check=True, cwd=ROOT, capture_output=True)
    e0 = json.loads((run_dir / 'out' / 'e0_intake.json').read_text())
    files = ('bodmas.npz', 'bodmas_metadata.csv', 'bodmas_malware_category.csv')
    digests = {f: sha256_file(data / f) for f in files}
    claim = 'EMBER features.py v2 / LIEF 0.9.0 (declared by BODMAS dataset page; not re-executed)'
    head, root = S7.acquisition_checkpoints(data, digests, claim)
    assert e0['ledger']['acq_chain_head'] == head
    assert e0['ledger']['oracle_root'] == root
    assert all(e0['transfer_integrity_match'].values())
    st = e0['screen']['strata']
    assert st['Quarantine']['benign'] == 7 and st['Placeholder']['benign'] > 0 and st['Bulk']['benign'] > 0
    # every exact checkpoint of the screen, split, certificate arithmetic, duplicate and COFF audits
    taus = tuple(json.loads(json.dumps(e0['certified_threshold_calibration']['rule'])).keys())
    ref = S7.screen_checkpoints(data, taus=tuple(float(t) for t in taus))
    sc = e0['screen']
    assert sc['timestamp_formats']['with_utc_offset'] == ref['timestamp_formats']['with_utc_offset']
    assert sc['timestamp_formats']['without_offset'] == ref['timestamp_formats']['without_offset']
    for nm in ('all', 'benign'):
        a, b = sc['spike_rule'][f'{nm}_k10'], ref['spike'][nm]
        assert (a['days_counted'], a['median'], a['mad'], a['threshold']) == (b['days'], b['median'], b['mad'], b['threshold_k10'])
        assert a['spike_days'] == b['spike_days_k10']
        assert sc['spike_rule'][f'{nm}_k4']['spike_days'] == b['spike_days_k4']
    for s_ in ('train', 'calibration', 'test'):
        assert sc['splits'][s_] == ref['split_counts'][s_]
    assert st['PreWindow']['benign'] + st['PostWindow']['benign'] == ref['split_counts']['pre_window']['benign']
    cen = ref['split_counts']['censored']
    assert st['Placeholder']['benign'] + st['Bulk']['benign'] + st['Quarantine']['benign'] == cen['benign']
    assert st['SpikeMal']['malware'] == cen['malware']
    assert sc['monthly'] == ref['monthly']
    for t, v in ref['certified'].items():
        got = e0['certified_threshold_calibration']['rule'][t]
        assert (got['k_star'], got['ub_at_k_star']) == (v['k_star'], v['ub_at_k_star'])
    for k, v in ref['duplicates'].items():
        assert e0['duplicates'][k] == v, k
    for cls in ('benign', 'malware'):
        for k, v in ref['coff_audit'][cls].items():
            assert e0['coff_audit'][cls][k] == v, (cls, k)
    # a second intake into the same run refuses to touch the append-only ledger
    second = subprocess.run(cmd, cwd=ROOT, capture_output=True)
    assert second.returncode != 0
