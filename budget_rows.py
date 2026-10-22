"""Leaf lines and aggregate rows of a real budget workbook, and the tie of a sheet's leaf sum to its own R / E rows
(change read-aggregate-rows-by-formula, spec budget-workbook-aggregate-rows).

Shared by Budget Review (`review_import.py`) and the real-budget scan store (`scan_budgets_v2.py` in Savills-local),
so both read a workbook the same way. Pure functions: the caller reads the sheet (cached values and, from a second
read, the formulas) and passes accessors. Rows and columns are 0-based; formulas carry Excel's 1-based addresses.

- `aggregate_refs(value, col)`: a `SUBTOTAL(9|109, ...)` or `SUM(...)` formula over cells of column `col` -> its rows.
- `find_aggregates(...)`: the coded rows whose formula covers at least one other coded row, with their children.
- `prefix_kids(codes)` / `dropped(...)`: rows not counted: aggregates by formula first, then the store's prefix rule
  for any other parent its same-prefix children add up to exactly.
- `double_counted(...)`: the rows not counted here that the file's own SUBTOTAL counts (a SUM aggregate, a parent
  dropped by the prefix rule).
- `explain_tie(...)`: direct tie, tie after a filter, tie after a double count, or a gap; Vietnamese notes.
"""
import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET

from openpyxl.utils import column_index_from_string

TOL = 1.0
SUFFIX_RE = re.compile(r'^(\.[A-Za-z0-9#]+|[a-z]|\d+)$')
_CALL = re.compile(r'^=\s*(SUBTOTAL|SUM)\s*\((.*)\)\s*$', re.I | re.S)
_REF = re.compile(r'^\$?([A-Z]{1,3})\$?(\d+)(?::\$?([A-Z]{1,3})\$?(\d+))?$')

NOTE_FILTER = 'ô tổng bị bộ lọc che ({n} dòng ẩn)'
NOTE_SUM = 'lỗi file: {code} dùng SUM, tổng của file cộng trùng {amount} VND'
NOTE_PARENT = 'lỗi file: {code} trùng số với dòng con, tổng của file cộng trùng {amount} VND'
NOTE_GAP = '{section} lệch {amount} VND'


def _vnd(x):
    return f'{x:,.0f}'


def formula_text(v):
    """The formula of a cell read without data_only: a '=...' string or an array formula's text; else None."""
    if isinstance(v, str):
        return v if v.startswith('=') else None
    text = getattr(v, 'text', None)
    if isinstance(text, str) and text:
        return text if text.startswith('=') else '=' + text
    return None


def aggregate_refs(v, col):
    """('SUBTOTAL' | 'SUM', sorted 0-based rows) when the whole formula is one SUBTOTAL(9 or 109, refs) or SUM(refs)
    whose refs are cells or ranges of column `col` (0-based) on the same sheet; else None."""
    text = formula_text(v)
    if not text:
        return None
    m = _CALL.match(text.strip())
    if not m:
        return None
    kind, inner = m.group(1).upper(), m.group(2)
    if '(' in inner or ')' in inner or '!' in inner:
        return None
    args = [a.strip() for a in inner.split(',')]
    if kind == 'SUBTOTAL':
        if len(args) < 2 or args[0] not in ('9', '109'):
            return None
        args = args[1:]
    rows = set()
    for a in args:
        r = _REF.match(a.upper())
        if not r:
            return None
        c1, r1, c2, r2 = r.group(1), int(r.group(2)), r.group(3) or r.group(1), int(r.group(4) or r.group(2))
        if column_index_from_string(c1) - 1 != col or column_index_from_string(c2) - 1 != col:
            return None
        lo, hi = min(r1, r2), max(r1, r2)
        rows.update(range(lo - 1, hi))
    return (kind, sorted(rows)) if rows else None


def find_aggregates(fget, candidates, coded_rows, col):
    """{row: {'kind', 'children'}} for each candidate row whose formula in column `col` covers at least one other
    coded row. `fget(r, c)`: the formula read's cell value; `candidates`: the rows that may be aggregates (coded rows
    without an indicator); `coded_rows`: every coded row of the sheet."""
    coded = set(coded_rows)
    out = {}
    for r in sorted(candidates):
        ref = aggregate_refs(fget(r, col), col)
        if not ref:
            continue
        children = [x for x in ref[1] if x != r and x in coded]
        if children:
            out[r] = {'kind': ref[0], 'children': children}
    return out


def prefix_kids(codes):
    """{i: [j, ...]}: the codes that extend code i by a suffix (`.x`, a lower-case letter, or digits after a code
    with no digit), as the scan store's rule of 2026-10-07."""
    kids = {}
    for i, lc in enumerate(codes):
        kids[i] = [j for j, k in enumerate(codes)
                   if k != lc and k.startswith(lc) and SUFFIX_RE.match(k[len(lc):])
                   and not (k[len(lc):].isdigit() and any(ch.isdigit() for ch in lc))]
    return kids


def dropped(vals, leaves, kids, aggregates):
    """Indexes of `leaves` not counted in one column: every aggregate by formula, whatever its cached value; then
    any other row whose same-prefix children add up to its value within 1 VND."""
    gone = {i for i, lf in enumerate(leaves) if lf['row'] in aggregates}
    for i, v in enumerate(vals):
        if i in gone or not kids.get(i) or v is None or abs(v) <= TOL:
            continue
        if abs(sum((vals[j] or 0.0) for j in kids[i]) - v) <= TOL:
            gone.add(i)
    return gone


_REL_ID = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'


def sheet_layout(path, names):
    """{sheet name: (hidden 0-based rows, auto-filter range or None)} for the named sheets, read from the
    workbook's XML (openpyxl's read-only mode does not keep row heights or filters)."""
    out = {}
    with zipfile.ZipFile(path) as z:
        targets = {}
        for el in ET.fromstring(z.read('xl/_rels/workbook.xml.rels')):
            t = el.get('Target', '')
            targets[el.get('Id')] = t.lstrip('/') if t.startswith('/') else posixpath.normpath(posixpath.join('xl', t))
        for el in ET.fromstring(z.read('xl/workbook.xml')).iter():
            if not el.tag.endswith('}sheet') or el.get('name') not in names:
                continue
            part = targets.get(el.get(_REL_ID))
            hidden, ref = set(), None
            if part and part in z.namelist():
                with z.open(part) as fh:
                    for _, node in ET.iterparse(fh):
                        tag = node.tag.rsplit('}', 1)[-1]
                        if tag == 'row':
                            rnum = node.get('r')
                            if node.get('hidden') in ('1', 'true') and rnum:
                                hidden.add(int(rnum) - 1)
                            node.clear()
                        elif tag == 'autoFilter':
                            ref = node.get('ref')
            out[el.get('name')] = (hidden, ref)
    return out


def double_counted(leaves, vals, gone, aggregates, fget, col):
    """(row, section, code, value, kind) of the rows dropped in column `col` that a SUBTOTAL over the section still
    counts: an aggregate written with SUM (kind 'SUM'), or a parent dropped by the prefix rule whose cell is not a
    SUBTOTAL (kind 'parent': a figure typed or month-summed in both the parent and its child)."""
    out = []
    for i in sorted(gone):
        lf = leaves[i]
        r = lf['row']
        if r in aggregates:
            if aggregates[r]['kind'] != 'SUM':
                continue
            kind = 'SUM'
        else:
            text = formula_text(fget(r, col)) or ''
            if re.match(r'^=\s*SUBTOTAL\s*\(', text, re.I):
                continue
            kind = 'parent'
        out.append((r, lf['section'], lf['code'], vals[i] or 0.0, kind))
    return out


def filter_on(auto_filter_ref, n_hidden, n_rows):
    """A sheet counts as filtered when it has an auto-filter, or more than half its rows between R and PL1 are
    hidden (design D4)."""
    return bool(auto_filter_ref) or (n_rows > 0 and n_hidden * 2 > n_rows)


def explain_tie(sections, items, doubles, anchors, hidden, filter_on, n_hidden=0):
    """Tie of the leaf sums to the sheet's own section rows.
    items: (row, section, value) of the counted leaves; doubles: double_counted() of the same column, the rows
    the file's SUBTOTAL counts on top of their children; anchors: {section: cached figure or None}.
    -> {'state': ok | ok_double_count | ok_filter | mismatch | no_anchor, 'notes': [...],
        'diffs': {section: leaf - anchor}}"""
    leaf = {s: 0.0 for s in sections}
    for _, s, v in items:
        if s in leaf:
            leaf[s] += v
    if any(anchors.get(s) is None for s in sections):
        return {'state': 'no_anchor', 'notes': [], 'diffs': {s: None for s in sections}}
    diffs = {s: leaf[s] - anchors[s] for s in sections}

    def ties(sums):
        return all(abs(sums[s] - anchors[s]) <= TOL for s in sections)

    def plus_sum(base, skip_hidden):
        out = dict(base)
        for r, s, _, v, _ in doubles:
            if s in out and not (skip_hidden and r in hidden):
                out[s] += v
        return out

    def sum_notes(skip_hidden):
        return [(NOTE_SUM if kind == 'SUM' else NOTE_PARENT).format(code=code, amount=_vnd(v))
                for r, s, code, v, kind in doubles
                if s in leaf and abs(v) > TOL and not (skip_hidden and r in hidden)]

    if ties(leaf):
        return {'state': 'ok', 'notes': [], 'diffs': diffs}
    if doubles and ties(plus_sum(leaf, False)):
        return {'state': 'ok_double_count', 'notes': sum_notes(False), 'diffs': diffs}
    if filter_on and hidden:
        visible = {s: 0.0 for s in sections}
        for r, s, v in items:
            if s in visible and r not in hidden:
                visible[s] += v
        note = NOTE_FILTER.format(n=n_hidden)
        if ties(visible):
            return {'state': 'ok_filter', 'notes': [note], 'diffs': diffs}
        if doubles and ties(plus_sum(visible, True)):
            return {'state': 'ok_filter', 'notes': [note] + sum_notes(True), 'diffs': diffs}
    return {'state': 'mismatch', 'diffs': diffs,
            'notes': [NOTE_GAP.format(section=s, amount=_vnd(diffs[s])) for s in sections if abs(diffs[s]) > TOL]}
