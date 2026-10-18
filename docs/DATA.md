# Data

No dataset is redistributed in this repository. Obtain the files from their publishers and place them as
below; the intake step (`scripts/e00_intake.py`) checks every file against the SHA-256 digests recorded in
the paper before anything else runs.

## BODMAS (primary dataset)

L. Yang, A. Ciptadi, I. Laziuk, A. Ahmadzadeh and G. Wang, "BODMAS: An open dataset for learning based
temporal analysis of PE malware," IEEE Security and Privacy Workshops (DLS), 2021,
doi:10.1109/SPW53761.2021.00020. Dataset page: <https://whyisyoung.github.io/BODMAS/>.

According to the dataset page, the feature vectors and metadata are open to everyone and hosted on Google
Drive; the malware category file was added in a later update (December 2021) in the same place; malware
binaries are available on request only and benign binaries are not released. Features are EMBER v2
vectors (2,381 dimensions) extracted with LIEF 0.9.0. The page states no licence for the data; cite the
paper and do not redistribute the files.

| File | Bytes | SHA-256 (as used in the paper) |
|---|---|---|
| `data/bodmas/bodmas.npz` | 261,557,445 | `0a833e46c22c096920c8068d4fb54b868067777c277c0a6eecf527c98d7e5a9e` |
| `data/bodmas/bodmas_metadata.csv` | 12,705,748 | `5f1dc793cac4a540ef9e0c40fd7897142095621790d3c6f2d6637971806f4c50` |
| `data/bodmas/bodmas_malware_category.csv` | 4,119,807 | `617fda69347ec907a79f198add431c8bb39102781de41cc03b7cd1718cff2198` |

`bodmas.npz` holds `X` (134,435 × 2,381, float32) and `y` (77,142 benign, 57,293 malware). The metadata file
has columns `sha`, `timestamp`, `family`; the category file `sha256`, `category`.

If your copies differ (a re-release, a different download), intake stops with failure mode F1. To run on
different files anyway, point `acquisition.expected_sha256` to a JSON file `{file: digest}` with your own
digests (computed at the source, before transfer). The deterministic checkpoints of
`results/paper_reference.json` then no longer apply.

### What the screen does with the release

The screen (paper Section 4.3; `tracepe.evidence.screen`) is run on the metadata before any split:

* two timestamp formats: 130,723 values carry a UTC offset, 3,712 (benign files first seen 2016–2018) do not and are read as UTC;
* a common window 2019-08-29 to 2020-09-30; benign files first seen earlier form the **PreWindow** stratum (13,834);
* a spike rule on all-sample daily counts (median 297.5 + 10 × MAD 74.5 = 1,042.5) flags 2020-01-01, 2020-02-19 and 2020-02-26:
  benign files on the first day carry a placeholder midnight timestamp (**Placeholder**, 5,870), those on the
  February days a batch timestamp (**Bulk**, 3,641); malware on spike days forms **SpikeMal** (349);
* 7 benign identifiers are VirusShare names rather than SHA-256 digests (**Quarantine**);
* everything else is **Dated** (53,790 benign / 56,944 malware) and is split in time: train 29 Aug–30 Nov 2019,
  calibrate December 2019, test January–September 2020.

## EMBER-2018, feature version 2 (optional corroboration)

H. S. Anderson and P. Roth, "EMBER: An open dataset for training static PE malware machine learning
models," arXiv:1804.04637, 2018. Repository: <https://github.com/elastic/ember>.

Download `https://ember.elastic.co/ember_dataset_2018_2.tar.bz2` (SHA-256
`b6052eb8d350a49a8d5a5396fbe7d16cf42848b86ff969b77464434cf2997812`, as listed in the EMBER repository) and
place the raw-feature JSON-lines files in `data/ember2018/`:

```
data/ember2018/train_features_0.jsonl ... train_features_5.jsonl
data/ember2018/test_features.jsonl
data/ember2018/ember_model_2018.txt      # the published EMBER-2018 LightGBM model, if you have it
```

The EMBER README states that feature version 2 is computed with LIEF 0.9.0. `tracepe.data.ember` re-implements
the vectorisation of EMBER's `features.py` (`process_raw_features`) from the raw JSON, so neither LIEF nor the
`ember` package is needed. Without EMBER-2018, `e11_ember2018.py` records `skipped` and the published-model
rows of the comparison table are left empty.

## Synthetic data (smoke test)

`scripts/make_synthetic.py` writes a small BODMAS-format release and EMBER-format JSON lines to
`data/synthetic/`. The generator reproduces the structural anomalies the screen must handle (offset-free
timestamps, a placeholder day, two bulk days, a k = 4-only spike, VirusShare identifiers, duplicate vectors,
pre-window benign files, unseen families and a drifting family from July). The class signal is artificial;
**results on synthetic data are meaningless** and are labelled as such on every table and figure.
