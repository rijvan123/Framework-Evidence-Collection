**Table 13. Explanation evidence and ledger integrity (KB11, P8, KB3, V1–V3)**

| EMBER group | Mean abs. grouped SHAP (margin) | Abs. SHAP share (%) | Gain share (%) | LR abs. coefficient share (%) | Mean abs. Δ margin on group deletion |
|---|---|---|---|---|---|
| ByteHistogram | 1.079 | 11.4 | 8.6 | 10.8 | 1.024 |
| ByteEntropyHistogram | 0.272 | 2.9 | 3.2 | 10.0 | 0.307 |
| StringExtractor | 1.142 | 12.0 | 13.7 | 6.5 | 1.087 |
| GeneralFileInfo | 0.385 | 4.0 | 3.6 | 1.1 | 0.272 |
| HeaderFileInfo | 2.674 | 28.1 | 36.6 | 4.3 | 1.700 |
| SectionInfo | 0.749 | 7.9 | 3.1 | 9.3 | 0.668 |
| ImportsInfo | 0.796 | 8.4 | 9.7 | 52.8 | 0.605 |
| ExportsInfo | 0.002 | 0.0 | 0.0 | 2.6 | 0.000 |
| DataDirectories | 2.403 | 25.3 | 21.6 | 2.7 | 1.134 |

| Check | Result |
|---|---|
| Grouped TreeSHAP cost | 4.09 ms per finding; local accuracy max residual 4.3e-14 |
| Deletion faithfulness (Spearman, SHAP rank vs Δ margin) | mean 0.62, median 0.70 |
| KB11 stability (top-3 group Jaccard across seeds) | correct 0.906 vs wrong 0.856 (n = 373); Cliff's δ = 0.168 ≥ 0.147 → gate allowed |
| Issued-finding records (ISS) | 77,417 records with monthly epoch anchors (341 s) |
| V1 chain verification | 211,960 records verified in 2.13 s |
| V2 content-addressed objects | 28 objects, 0 failures |
| V3 re-execution (1,000 sampled findings) | vector hash 1,000/1,000; margin bit-identical 1,000/1,000; SHAP local accuracy 1,000/1,000 |
| P8 tamper injection | bit flip 10,000/10,000; deletion 10,000/10,000; insertion 10,000/10,000; swap 10,000/10,000; timestamp edit 10,000/10,000; actor edit 10,000/10,000 |
| P8 verification scaling | n = 1,000: 0.0015 s; n = 10,000: 0.0218 s; n = 100,000: 0.1356 s; n = 1,000,000: 1.4649 s; log–log slope 0.973 ∈ [0.9, 1.1] |
| KB3 cross-environment re-execution | tree hash, 97,436 scores, 134,435-vector digest identical (100.0%); container Python 3.13.16 / NumPy 2.5.3 vs device Python 3.10.12 / NumPy 2.2.6, LightGBM 4.7.0 on both |
| Acquisition | 134,435 ACQ records; 7 duplicate groups; oracle Merkle root 7dcfe2a8d1c034ff… |

Grouped TreeSHAP: exact LightGBM pred_contrib summed over EMBER v2 groups, 6,020 month×class-stratified March–September findings. The anchor signature is Ed25519 with a simulated timestamping authority; WORM storage is emulated by a content-addressed write-once store. {MoC}.
