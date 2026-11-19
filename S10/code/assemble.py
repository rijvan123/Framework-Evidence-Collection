#!/usr/bin/env python3
"""Assemble S10_OUTPUT.md from the hand-written draft, the generated tables and the figure captions.
<<tableN_name>> -> tables/tableN_name.md (title line kept); ⟦CAP:figname⟧ -> caption + number label.
Reports any unresolved ⟦...⟧ marker and any cited reference missing from the reference list."""
import re, json, os, sys

R = '/home/claude/s10'
draft = open(f'{R}/report/S10_draft.md').read()
caps = json.load(open(f'{R}/figs/captions.json'))


def table_sub(m):
    p = f'{R}/tables/{m.group(1)}.md'
    return open(p).read().strip() if os.path.exists(p) else f'⟦MISSING TABLE {m.group(1)}⟧'


def cap_sub(m):
    c = caps.get(m.group(1))
    if not c:
        return f'⟦MISSING CAPTION {m.group(1)}⟧'
    lab = c.get('label', '')
    return f"{c['caption']} {{{'MoC' if lab.startswith('measured-on-Claude') and 'reproduced' not in lab else lab}}}"


out = re.sub(r'<<([A-Za-z0-9_]+)>>', table_sub, draft)
out = re.sub(r'⟦CAP:([A-Za-z0-9_]+)⟧', cap_sub, out)


def minus_signs(text):
    """Typographic minus for negative numbers in the body: a hyphen-minus that follows a space or an opening
    bracket/separator and precedes a digit. Code spans are left untouched; the reference list is not processed."""
    parts = re.split(r'(`[^`]*`)', text)
    return ''.join(p if p.startswith('`') else re.sub(r'(?<![\w.\-])-(?=\d)', '\u2212', p) for p in parts)


_body, _sep, _refs = out.partition('\n## References')
out = minus_signs(_body) + _sep + _refs
open(f'{R}/report/S10_OUTPUT.md', 'w').write(out)
left = sorted(set(re.findall(r'⟦[^⟧]*⟧', out)))
print('unresolved markers:', left)
body, _, refs = out.partition('\n## References')
cited = set(int(x) for x in re.findall(r'\[(\d{1,3})\]', body))
listed = set(int(x) for x in re.findall(r'^\[(\d{1,3})\]', refs, flags=re.M))
print('cited but not listed:', sorted(cited - listed))
print('listed but not cited:', sorted(listed - cited))
figs = sorted(set(re.findall(r'figs/(fig\d+_[a-z0-9_]+)\.png', out)))
print('figures referenced:', len(figs), [f for f in figs if not os.path.exists(f'{R}/figs/{f}.png')], 'missing files')
print('words (approx):', len(re.sub(r'\|[^\n]*\|', '', out).split()))
