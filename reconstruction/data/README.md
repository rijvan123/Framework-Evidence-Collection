# data/

Put the datasets here (they are not part of the repository and are ignored by git):

```
data/bodmas/bodmas.npz
data/bodmas/bodmas_metadata.csv
data/bodmas/bodmas_malware_category.csv
data/ember2018/train_features_0.jsonl ... train_features_5.jsonl, test_features.jsonl   (optional)
data/ember2018/ember_model_2018.txt                                                      (optional)
```

`python scripts/make_synthetic.py` writes a synthetic stand-in to `data/synthetic/` for the smoke test.
Sources, checksums and terms: [`docs/DATA.md`](../docs/DATA.md).
