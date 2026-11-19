#!/usr/bin/env python3
"""Seal the S10 write-up: append a DOC record holding the SHA-256 of S10_OUTPUT.md (which cannot contain its own hash), anchor the
'doc' epoch and re-verify the chain. Output: out/ledger_doc.json"""
import os, json
import s10_common as C

doc = f'{C.ROOT}/report/S10_OUTPUT.md'
rec = dict(t='DOC', path='S10_OUTPUT.md', sha256=C.sha256_file(doc), bytes=os.path.getsize(doc))
C.ledger_append([rec], epoch='doc'); C.ledger_anchor('doc')
v1 = C.verify_main_ledger(); last = C._last_line(C.MAIN_LEDGER)
out = dict(doc=rec, V1=v1, head=last['h'])
C.jdump(out, f'{C.OUT}/ledger_doc.json'); print(json.dumps(out, indent=1))
