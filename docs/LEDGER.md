# Evidence ledger

`tracepe.evidence.ledger` implements the append-only evidence ledger of the paper (Section 4.3; S7
definitions S7.1–S7.3). This page specifies the format so that a third party can verify a ledger without
this code.

## File format

One record per line, ASCII:

```
<chain head after this record, 64 hex> <canonical JSON of the record>
```

Canonical JSON (`enc`): keys sorted, separators `,` and `:` without spaces, ASCII escapes, **no floats**.
Real numbers are carried as integers (e.g. bounds in parts per billion) or as IEEE-754 hex strings:
`f64hex` = binary64 big-endian (margins, thresholds; bit-exact), `f32hex` = binary32 big-endian (display
values, attributions).

## Hash constructions

All hashes are SHA-256 with the domain prefix `DOM = "TRACE-PE/v1/"`:

| Object | Construction |
|---|---|
| canonical vector (S7.1) | `vh = SHA256(DOM ‖ "vec" ‖ 0x00 ‖ LE32(d) ‖ float32-LE(x + 0.0))` — `-0.0` is mapped to `+0.0`; NaN/inf are rejected at intake |
| record hash (S7.2) | `ρ_j = SHA256(DOM ‖ "rec" ‖ 0x00 ‖ enc(r_j))` |
| chain (S7.2) | `h_0 = SHA256(DOM ‖ "genesis" ‖ 0x00)`, `h_j = SHA256(DOM ‖ "chain" ‖ 0x00 ‖ h_{j−1} ‖ ρ_j)` |
| Merkle tree (S7.3) | leaf `SHA256(0x00 ‖ ρ)`, node `SHA256(0x01 ‖ left ‖ right)`, odd last node promoted; equals the RFC 9162 Merkle tree hash (tested); empty tree `SHA256("")` |
| anchor (S7.3) | `σ_e = Ed25519_sign(DOM ‖ "anchor" ‖ 0x00 ‖ epoch ‖ 0x00 ‖ M_e ‖ h_before)` over the epoch's Merkle root `M_e` of record hashes and the chain head before the anchor |

The first record is the dataset manifest `MAN0`, so `h_1 = SHA256(DOM ‖ "chain" ‖ 0x00 ‖ h_0 ‖ ρ_MAN0)`, exactly as
in the S7 probe code (`tests/s7_reference.py`).

## Record types

| Type | Written by | Content |
|---|---|---|
| `MAN0` | E0 | file digests, feature version, dimension, extractor claim (declared, not executed) |
| `ACQ` | E0 | one per sample: running number, SHA-256 identifier, canonical vector hash, raw first-seen string, offset flag, window and spike-day flags, dataset id |
| `PREREG` | E0 | path and SHA-256 of `docs/PREREGISTRATION.md` |
| `EXT`, `SCR` | E0 | extractor declaration and group map hash; screen parameters, spike days, strata, split counts |
| `NCR` | E0 | non-conformity (identifier not a SHA-256 digest, failed invariant) and the action taken |
| `DUP` | E0 | identical-vector groups, kept and dropped members |
| `ORC` | E0 | Merkle root over `enc({sid, y, fam, cat})` of every row: the oracle snapshot |
| `MAN`, `MOD` | E1 | training manifest (Merkle root of training identifiers); model identity (tree-section SHA-256, parameter hash, file hash, store object, library versions) |
| `CERT` | E2 | retrospective certificate: counts, CP bounds (ppb), tolerances, validity, θ (f64 hex) |
| `TRG`, `RVC` | E7 | scheduled re-validation events and their scope, budget, changes and harmful flips (simulation) |
| `ISS` | E9 | one per issued test finding: sample, vector hash, model, θ, margin, verdict, credibility, state (ISS / SCR / ABS), month, top grouped attributions, base value, local-accuracy residual |
| `REPORT` | seal | path, size and SHA-256 of every output file of the run |
| `ANC` | all | epoch name, number of records, Merkle root, head before, signature, public key, `tsa: "simulated"`, wall-clock time |

Stages that write records refuse to append twice: re-running a stage recomputes its outputs but leaves the
ledger untouched when its epoch is already anchored.

## Verification

```bash
python scripts/verify_ledger.py --config configs/default.yaml                   # V1 + V2 of the run
python scripts/verify_ledger.py runs/paper/ledger/trace_pe_ledger.jsonl --pub <hex> --receipt 12345
```

* **V1** recomputes every link, every epoch Merkle root and every anchor signature. With `--pub` the key is
  pinned; without it the key of the first anchor is trusted (and must then be compared out of band with the
  key published in `out/ledger_final.json`).
* **V2** re-hashes every object of the content-addressed store (models, arrays).
* **V3** (in `e09_explain_issue.py`) re-executes sampled findings: vector hash, bit-identical margin from the
  stored model, SHAP local accuracy.
* A **receipt** is the Merkle inclusion proof of one record in its epoch plus the signed anchor that closes
  the epoch. `scripts/report_finding.py` refuses to produce an evidence report for a finding whose receipt
  does not verify ("no receipt, no report").

## Trust model and non-guarantees

The chain detects any change to recorded content after the head it is checked against; the signed anchors
fix that head. It does not provide:

* **N1** protection of the unanchored tail (records after the last anchor);
* **N2** protection against an insider who rewrites records before they are anchored;
* **N3** truth of content: a record can be faithfully preserved and still be wrong (labels, verdicts);
* **N4** detection of equivocation (two different ledgers shown to two parties) without an external witness;
* **N5** the derivation gap: feature vectors come from the dataset provider and are not re-derived from binaries.

The time-stamping authority is **simulated** (local Ed25519 key, wall-clock time; marked `tsa: "simulated"`
in every anchor) and write-once storage is emulated by a content-addressed store with read-only files. A
production deployment would replace both with an RFC 3161 TSA and hardware object locks. Nothing here is a
claim of legal admissibility.
