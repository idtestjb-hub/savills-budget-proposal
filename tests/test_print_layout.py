"""Print layout of the client deliverable's '2. Budget-Management Fund' (change add-budget-print-layout).

Runs on a copy of the standard 2027 form (skipped when the form is not on this machine). Lines are edited in the copy
to make each case; codes are the form's own, figures are invented.
"""
import os
import re
import shutil

import openpyxl
import pytest
from openpyxl.utils import column_index_from_string as ci

import print_layout as pl
from generate_project_budget import TEMPLATE_PATH

pytestmark = pytest.mark.skipif(not os.path.exists(TEMPLATE_PATH), reason='standard 2027 form not on this machine')


@pytest.fixture()
def wb(tmp_path):
    dst = tmp_path / 'form.xlsx'
    shutil.copy2(TEMPLATE_PATH, dst)
    return openpyxl.load_workbook(dst)


def _leaves(ws, n):
    """`n` leaf rows (coded, with the column B rule, not a SUBTOTAL) whose X is blank."""
    out = []
    for r in range(13, 505):
        if (pl.has_not_use_rule(ws, r) and not pl.is_group(ws, r) and not ws.cell(r, ci('X')).value
                and ws.cell(r, ci('Y')).value):
            out.append(r)
            if len(out) == n:
                return out
    raise AssertionError('not enough leaf rows')


def _blank(ws, rep, r):
    """Make a line unused: no frequency, price, months or remark, and nothing on the report sheet."""
    for c in ['C', 'E', 'F', 'T'] + [chr(ord('H') + i) for i in range(12)]:
        ws[f'{c}{r}'] = None
    code = ws.cell(r, ci('Y')).value
    rr = pl.report_row(rep, code)
    if rr:
        for c in ('H', 'I', 'N'):
            rep[f'{c}{rr}'] = None


# ---- 1.1 print setup and folded columns ------------------------------------------------------------------------

def test_print_setup(wb):
    pl.apply(wb)
    ws = wb[pl.SHEET]
    assert ws.print_area.replace("'", '').endswith('$X$2:$BB$526')
    assert ws.print_title_rows == '$9:$10'
    assert int(ws.page_setup.paperSize) == 8 and ws.page_setup.orientation == 'landscape'
    assert int(ws.page_setup.fitToWidth) == 1 and int(ws.page_setup.fitToHeight) == 0
    assert ws.sheet_properties.pageSetUpPr.fitToPage
    assert ws.oddFooter.center.text == 'Page &P of &N'


def test_detail_columns_folded_with_formulas_kept(wb):
    ws = wb[pl.SHEET]
    before = {c: ws[f'{c}14'].value for c in pl.FOLD_COLS}
    pl.apply(wb)
    for c in pl.FOLD_COLS:
        d = ws.column_dimensions[c]
        assert d.hidden and d.outlineLevel == 2, c
        assert ws[f'{c}14'].value == before[c]
    seen = {}
    for key, d in ws.column_dimensions.items():          # no two <col> ranges may cover the same column
        lo, hi = d.min or ci(key), d.max or ci(key)
        for i in range(lo, hi + 1):
            assert i not in seen, (key, seen.get(i))
            seen[i] = key


# ---- 1.2 which rows print ----------------------------------------------------------------------------------------

def test_row_rule(wb):
    ws, rep = wb[pl.SHEET], wb[pl.REPORT_SHEET]
    empty, remark, prior, report, monthly, formula, stray = _leaves(ws, 7)
    for r in (empty, remark, prior, report, monthly, formula, stray):
        _blank(ws, rep, r)
    ws[f'T{remark}'] = 'Dự trù theo hợp đồng'
    rep[f'N{pl.report_row(rep, ws.cell(prior, ci("Y")).value)}'] = 12_000_000
    rep[f'H{pl.report_row(rep, ws.cell(report, ci("Y")).value)}'] = 5_000_000
    ws[f'C{monthly}'], ws[f'F{monthly}'] = 'Monthly', 1_000_000
    ws[f'C{formula}'], ws[f'F{formula}'] = 'Monthly', '=1+1'
    ws[f'X{stray}'] = ': dự kiến'
    pl.apply(wb)
    hidden = lambda r: bool(ws.row_dimensions[r].hidden)   # noqa: E731
    assert hidden(empty) and hidden(stray)
    assert not any(hidden(r) for r in (remark, prior, report, monthly, formula))


def test_section_rows(wb):
    ws, rep = wb[pl.SHEET], wb[pl.REPORT_SHEET]
    roman = next(r for r in range(13, 505) if str(ws.cell(r, ci('X')).value or '').strip() == 'VI')
    dotted = [r for r in range(13, 505) if re.fullmatch(r'V\.\d+', str(ws.cell(r, ci('X')).value or '').strip())]
    assert dotted
    group = dotted[0]
    lo, hi = pl.group_range(ws, group)
    for r in range(lo, hi + 1):
        if pl.has_not_use_rule(ws, r) and not pl.is_group(ws, r):
            _blank(ws, rep, r)
    ws[f'T{group}'] = None
    for r in range(roman + 1, pl.group_range(ws, roman)[1] + 1):
        if pl.has_not_use_rule(ws, r) and not pl.is_group(ws, r):
            _blank(ws, rep, r)
    pl.apply(wb)
    assert not ws.row_dimensions[roman].hidden
    assert ws.row_dimensions[group].hidden
    for r in (11, 12):
        assert not ws.row_dimensions[r].hidden


def test_check_and_spacer_rows_hidden_and_filter_saved(wb):
    pl.apply(wb)
    ws = wb[pl.SHEET]
    assert all(ws.row_dimensions[r].hidden for r in range(506, 514))
    assert ws.auto_filter.ref == 'A12:AW505'
    cols = ws.auto_filter.filterColumn
    assert len(cols) == 1 and cols[0].colId == 1
    assert list(cols[0].filters.filter) == ['Use'] and cols[0].filters.blank


# ---- 1.3 signature block -----------------------------------------------------------------------------------------

def _boxes(ws, top):
    spans = sorted((m.min_col, m.max_col) for m in ws.merged_cells.ranges if m.min_row == top == m.max_row)
    singles = [c for c in range(ci('X'), ci('BB') + 1)
               if ws.cell(top, c).value and not any(lo <= c <= hi for lo, hi in spans)]
    return sorted(spans + [(c, c) for c in singles])


def test_signature_block(wb):
    pl.apply(wb)
    ws = wb[pl.SHEET]
    top, bottom = 514, 526
    boxes = _boxes(ws, top)
    assert len(boxes) == 8
    assert boxes[0][0] >= ci('X') and boxes[-1][1] <= ci('AO')
    assert all(a[1] < b[0] for a, b in zip(boxes, boxes[1:]))           # no overlap
    heads = [ws.cell(top, lo).value for lo, _ in boxes]
    roles = [ws.cell(top + 1, lo).value for lo, _ in boxes]
    assert heads == ['Đề xuất'] + ['Phê duyệt'] * 7
    assert roles == ['Trưởng Ban Quản lý', 'Trưởng Ban quản trị', 'Phó Ban quản trị', 'Phó Ban quản trị',
                     'Ban quản trị', 'Ban quản trị', 'Ban quản trị', 'Ban quản trị']
    assert all(ws.cell(top + 2, lo).value == '(Ký tên, ghi rõ họ tên)' for lo, _ in boxes)
    assert all(str(ws.cell(bottom, lo).value).startswith('Ngày:') for lo, _ in boxes)
    texts = {ws.cell(r, c).value for r in range(top, bottom + 1) for c in range(ci('X'), ci('BB') + 1)} - {None}
    assert texts == {'Đề xuất', 'Phê duyệt', 'Trưởng Ban Quản lý', 'Trưởng Ban quản trị', 'Phó Ban quản trị',
                     'Ban quản trị', '(Ký tên, ghi rõ họ tên)', pl.DATE_LINE}
    for r in range(top, bottom + 1):
        assert not any(ws.cell(r, c).value for c in range(ci('AP'), ci('BB') + 1))


def test_reapply_follows_excel_flags(wb):
    """The adjust step re-applies with Excel's column B: a line that gained an amount shows again."""
    ws = wb[pl.SHEET]
    line = _leaves(ws, 1)[0]
    pl.apply(wb, not_use={line})
    assert ws.row_dimensions[line].hidden
    pl.apply(wb, not_use=set())
    assert not ws.row_dimensions[line].hidden


def test_adjust_run_applies_the_layout():
    import inspect

    from webapp import adjust_run
    src = inspect.getsource(adjust_run.main)
    assert src.index('print_layout.apply(wb)') < src.index('wb.save(deliverable)')
    assert 'excel_not_use_rows(recalc)' in src


def test_export_pdf_a4_and_a3(wb, tmp_path):
    """Excel exports both papers from a copy; the deliverable is not touched (spec budget-web-print-pdf)."""
    pytest.importorskip('win32com.client')
    pymupdf = pytest.importorskip('pymupdf')
    pl.apply(wb)
    deliv = tmp_path / 'Demo - Sample Consulting Budget.xlsx'
    wb.save(deliv)
    before = (os.path.getmtime(deliv), deliv.read_bytes())
    for paper, width in (('A4', 842), ('A3', 1191)):
        out = tmp_path / pl.pdf_name(str(deliv), paper)
        try:
            pl.export_pdf(str(deliv), paper, str(out))
        except pl.PrintError as exc:
            pytest.skip(f'Excel not usable here: {exc}')
        with pymupdf.open(out) as doc:
            assert all(abs(p.rect.width - width) < 3 and p.rect.width > p.rect.height for p in doc), paper
            texts = [p.get_text() for p in doc]
        assert not any('TRUE' in t for t in texts), paper
        sign = [t for t in texts if 'Đề xuất' in t]
        assert len(sign) == 1 and sign[0].count('Phê duyệt') == 7 and sign[0].count('Ngày:') == 8, paper
        # The form starts in Sep/2026: the 2nd month heading (Oct/2026) exists only in the month columns AQ:BB.
        assert ('Oct/2026' in texts[0]) == (paper == 'A3'), paper
    assert (os.path.getmtime(deliv), deliv.read_bytes()) == before


def test_apply_twice_is_stable(wb, tmp_path):
    pl.apply(wb)
    pl.apply(wb)
    ws = wb[pl.SHEET]
    assert len(_boxes(ws, 514)) == 8
    out = tmp_path / 'twice.xlsx'
    wb.save(out)
    again = openpyxl.load_workbook(out)
    assert len(_boxes(again[pl.SHEET], 514)) == 8
    assert again[pl.SHEET].auto_filter.ref == 'A12:AW505'
