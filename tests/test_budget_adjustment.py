"""Unit tests for budget_adjustment: sheet '4. Điều chỉnh' and the month-cell links into the fund sheets
(docs/32 sections 2 and 3).

Covered on an invented workbook (fund sheets with the standard form's column letters only, no template needed):
 - sheet position, header rows, parent / detail row layout, hidden columns, outline groups collapsed;
 - the dropdown on every parent row's column D, the protection flags, which cells are unlocked;
 - the formulas of M / N / O, the parent SUMs, the fund row's H:S (and F for Monthly) links;
 - evaluated by hand with a small evaluator for this formula grammar: untouched, M = I and every month formula
   gives the original month figure; each adjustment type gives the expected new amount;
 - the leading "= " text fixer leaves the formulas alone;
 - with Excel installed (pywin32), the saved workbook recalculates with no error cell, equals the original
   untouched, and moves as expected after an edit of each type.
Codes, names and figures are invented.
"""
import os
import re

import openpyxl
import pytest
from openpyxl.utils import get_column_letter

import budget_adjustment as ba

MGMT, COMMON, SINKING_REPORT = '2. Budget-Management Fund', '2.2 Common area Fund', '3.1 Report-Sinking Fund'
SHEETS_BEFORE = ['Cover', '1. Summary', MGMT, COMMON, '3. Budget-Sinking Fund', SINKING_REPORT, 'A1. Staff cost']

RAMP = [10_000_000 * m for m in range(1, 13)]   # a Schedule line that grows month by month


def _items():
    """Three parent lines on '2.' (real sub-rows, one lumped row, one Schedule line) and one on '2.2'."""
    return [
        {'code': 'ESS1', 'sheet': MGMT, 'row': 20, 'name_vi': 'Dịch vụ bảo vệ', 'freq': 'Monthly',
         'months': [146_000_000.0] * 12, 'annual': 1_752_000_000.0,
         'subs': [
             {'desc_vi': 'Vị trí cổng chính', 'unit_vi': 'vị trí', 'qty': 4.0, 'unit_price': 300_000_000.0,
              'amount': 1_200_000_000.0, 'qty_editable': True},
             {'desc_vi': 'Vị trí CCTV', 'unit_vi': 'vị trí', 'qty': 2.0, 'unit_price': 276_000_000.0,
              'amount': 552_000_000.0, 'qty_editable': True},
         ]},
        {'code': 'ESS16', 'sheet': MGMT, 'row': 22, 'name_vi': 'Chăm sóc cây xanh', 'freq': 'Monthly',
         'months': [22_000_000.0] * 12, 'annual': 264_000_000.0,
         'subs': [{'desc_vi': 'Chăm sóc cây xanh', 'unit_vi': 'khoản', 'qty': 1.0, 'unit_price': 264_000_000.0,
                   'amount': 264_000_000.0, 'qty_editable': False}]},
        {'code': 'RM.AP', 'sheet': MGMT, 'row': 14, 'name_vi': 'Phí quản lý căn hộ', 'freq': 'Schedule',
         'months': [float(m) for m in RAMP], 'annual': float(sum(RAMP)),
         'subs': [{'desc_vi': 'Căn hộ', 'unit_vi': 'm²', 'qty': 78_000.0, 'unit_price': 10_000.0,
                   'amount': 780_000_000.0, 'qty_editable': True}]},
        {'code': 'RA1.A', 'sheet': COMMON, 'row': 20, 'name_vi': 'Quảng cáo LCD', 'freq': 'Monthly',
         'months': [4_000_000.0] * 12, 'annual': 48_000_000.0,
         'subs': [{'desc_vi': 'Màn hình LCD sảnh', 'unit_vi': 'thiết bị', 'qty': 3.0, 'unit_price': 16_000_000.0,
                   'amount': 48_000_000.0, 'qty_editable': True}]},
    ]


def _fund_row(ws, r, code, freq, months):
    """A fund row the way the standard form lays it out: C freq, F monthly figure, H:S months, G and AK formulas,
    AQ:BB the form's own month chain (Monthly reads F, Schedule reads H:S)."""
    ws.cell(row=r, column=25, value=code)
    ws.cell(row=r, column=3, value=freq)
    ws.cell(row=r, column=5, value=12)
    if freq == 'Monthly':
        ws.cell(row=r, column=6, value=months[0])
    for k, v in enumerate(months):
        ws.cell(row=r, column=8 + k, value=v)
        ws.cell(row=r, column=43 + k, value=(f'=IF($C{r}="Schedule",VALUE({get_column_letter(8 + k)}{r}),'
                                             f'IF($C{r}="Monthly",$F{r},0))'))
    ws.cell(row=r, column=7, value=f'=IF($C{r}="Schedule",SUM(H{r}:S{r}),F{r}*E{r})')
    ws.cell(row=r, column=37, value=f'=SUM(AQ{r}:BB{r})')


def _workbook():
    wb = openpyxl.Workbook()
    wb.remove(wb.worksheets[0])
    for name in SHEETS_BEFORE:
        wb.create_sheet(name)
    ws = wb[MGMT]
    _fund_row(ws, 14, 'RM.AP', 'Schedule', RAMP)
    _fund_row(ws, 20, 'ESS1', 'Monthly', [146_000_000] * 12)
    _fund_row(ws, 21, 'ESS4', 'Monthly', [24_000_000] * 12)      # not covered: must stay literal
    _fund_row(ws, 22, 'ESS16', 'Monthly', [22_000_000] * 12)
    ws.cell(row=22, column=20, value='= text that starts with an equals sign and a space')
    _fund_row(wb[COMMON], 20, 'RA1.A', 'Monthly', [4_000_000] * 12)
    s = wb['1. Summary']
    s['H29'] = f"='{MGMT}'!AK20"
    s['H30'] = f"='{MGMT}'!AK14+'{COMMON}'!AK20"
    return wb


@pytest.fixture
def applied():
    wb = _workbook()
    parents = ba.apply(wb, _items())
    return wb, wb[ba.SHEET_NAME], parents


# ---- a small evaluator for the formulas this module writes (IF, SUM, + - * /, = <>, refs, quoted strings) ----

def _lazy_if(expr):
    """IF(c,a,b) -> (a if c else b), nested, so an untaken branch (a division by zero) is never evaluated."""
    i = expr.find('IF(')
    if i < 0:
        return expr
    depth, parts, start = 0, [], i + 3
    for j in range(i + 3, len(expr)):
        ch = expr[j]
        if ch == '(':
            depth += 1
        elif ch == ')':
            if depth == 0:
                parts.append(expr[start:j])
                c, a, b = (_lazy_if(x) for x in parts)
                return expr[:i] + f'(({a}) if ({c}) else ({b}))' + _lazy_if(expr[j + 1:])
            depth -= 1
        elif ch == ',' and depth == 0:
            parts.append(expr[start:j])
            start = j + 1
    raise ValueError(expr)


class _Eval:
    def __init__(self, wb):
        self.wb = wb

    def cell(self, sheet, ref):
        v = self.wb[sheet][ref.replace('$', '')].value
        if isinstance(v, str) and v.startswith('='):
            return self.formula(sheet, v)
        return v if v is not None else 0

    def formula(self, sheet, text):
        expr = text[1:]
        strings = []

        def keep(m):
            strings.append(m.group(0)[1:-1])
            return f'__s{len(strings) - 1}__'
        expr = re.sub(r'"[^"]*"', keep, expr)
        expr = re.sub(r"SUM\('([^']+)'!(\$?[A-Z]+\$?\d+):(\$?[A-Z]+\$?\d+)\)",
                      lambda m: f'R("{m.group(1)}","{m.group(2)}","{m.group(3)}")', expr)
        expr = re.sub(r"'([^']+)'!(\$?[A-Z]+\$?\d+)", lambda m: f'C("{m.group(1)}","{m.group(2)}")', expr)
        expr = re.sub(r'SUM\((\$?[A-Z]+\$?\d+):(\$?[A-Z]+\$?\d+)\)',
                      lambda m: f'R("{sheet}","{m.group(1)}","{m.group(2)}")', expr)
        expr = re.sub(r'(?<![A-Za-z"])(\$?[A-Z]{1,3}\$?\d+)(?![\w"])', lambda m: f'C("{sheet}","{m.group(1)}")', expr)
        expr = expr.replace('<>', '!=').replace('=', '==').replace('!==', '!=')
        expr = re.sub(r'__s(\d+)__', lambda m: repr(strings[int(m.group(1))]), expr)
        expr = _lazy_if(expr)

        def R(sh, a, b):
            ws = self.wb[sh]
            a, b = a.replace('$', ''), b.replace('$', '')
            return sum((self.cell(sh, c.coordinate) or 0) for row in ws[a:b] for c in row)
        return eval(expr, {'C': self.cell, 'R': R, 'VALUE': float})


# ---- layout ----

def test_sheet_sits_right_after_the_sinking_fund_report(applied):
    wb, ws, _ = applied
    names = wb.sheetnames
    assert names.index(ba.SHEET_NAME) == names.index(SINKING_REPORT) + 1
    assert names.index(ba.SHEET_NAME) < names.index('A1. Staff cost')


def test_header_rows_and_hidden_columns(applied):
    _, ws, _ = applied
    assert ws['A1'].value == ba.TITLE
    assert 'cột D' in ws['A2'].value and 'ô vàng' in ws['A2'].value
    assert [ws.cell(row=4, column=c).value for c in range(1, 16)] == list(ba.HEADERS[:15])
    assert ws['P4'].value == 'Sheet quỹ' and ws['S4'].value == 'Tháng gốc 1' and ws['AD4'].value == 'Tháng gốc 12'
    assert all(ws.column_dimensions[get_column_letter(c)].hidden for c in range(16, 31))
    assert not ws.column_dimensions['O'].hidden
    assert ws['A4'].fill.fgColor.rgb.endswith('FFDF00') and not ws['A4'].font.bold
    assert ws['A4'].font.name == 'Arial'


def test_parent_and_detail_rows(applied):
    _, ws, parents = applied
    assert parents == {'ESS1': 5, 'ESS16': 8, 'RM.AP': 10, 'RA1.A': 12}
    assert [ws.cell(row=r, column=3).value for r in range(5, 14)] == [
        'Tổng', 'Chi tiết', 'Chi tiết', 'Tổng', 'Chi tiết', 'Tổng', 'Chi tiết', 'Tổng', 'Chi tiết']
    assert (ws['A5'].value, ws['B5'].value) == ('ESS1', 'Dịch vụ bảo vệ')
    assert ws['A6'].value is None and ws['B6'].value is None and ws['E5'].value is None
    assert (ws['E6'].value, ws['F6'].value, ws['G6'].value, ws['H6'].value, ws['I6'].value) == (
        'Vị trí cổng chính', 'vị trí', 4.0, 300_000_000.0, 1_200_000_000.0)
    assert ws['E6'].alignment.indent >= 1
    assert (ws['P5'].value, ws['Q5'].value, ws['R5'].value) == (MGMT, 20, 'Monthly')
    assert [ws.cell(row=10, column=c).value for c in range(19, 31)] == [float(m) for m in RAMP]
    assert ws['J6'].value == 4.0 and ws['K6'].value == 300_000_000.0
    assert ws['J9'].value == '=G9'                           # lumped row: quantity follows the original
    assert ws['L5'].value == 0 and ws['D5'].value is None
    assert ws['I5'].value == '=SUM(I6:I7)' and ws['M5'].value == '=SUM(M6:M7)'
    assert ws['N5'].value == '=M5-I5' and ws['O5'].value == '=IF(I5=0,"N/A",N5/I5)'
    assert ws['M6'].value == ('=IF($D$5="Số lượng",J6*H6,IF($D$5="Đơn giá",G6*K6,IF($D$5="Số lượng + Đơn giá",J6*K6,'
                              'IF($D$5="Trượt giá",I6*(1+$L$5),IF($D$5="Nhập số",K6,I6)))))')
    assert ws['N6'].value == '=M6-I6' and ws['O6'].value == '=IF(I6=0,"N/A",N6/I6)'
    assert ws['A5'].fill.fgColor.rgb.endswith('E4E6E8')
    assert ws['A7'].fill.fgColor.rgb.endswith('EEE8E3') and ws['A6'].fill.fill_type is None


def test_outline_groups_collapsed_with_the_button_on_the_parent_row(applied):
    _, ws, _ = applied
    for r in (6, 7, 9, 11, 13):
        assert ws.row_dimensions[r].outline_level == 1 and ws.row_dimensions[r].hidden
    for r in (5, 8, 10, 12):
        assert not ws.row_dimensions[r].outline_level and not ws.row_dimensions[r].hidden
    assert ws.sheet_properties.outlinePr.summaryBelow is False


def test_dropdown_on_every_parent_row(applied):
    _, ws, _ = applied
    dvs = ws.data_validations.dataValidation
    assert len(dvs) == 1 and dvs[0].type == 'list'
    assert dvs[0].formula1 == '"Số lượng,Đơn giá,Số lượng + Đơn giá,Trượt giá,Nhập số"'
    covered = {str(rng) for rng in dvs[0].sqref.ranges}
    assert covered == {'D5', 'D8', 'D10', 'D12'}


def test_protection_and_unlocked_cells(applied):
    _, ws, _ = applied
    assert ws.protection.sheet is True and ws.protection.password is None
    assert ws.protection.formatRows is False and ws.protection.formatColumns is False
    unlocked = {c.coordinate for row in ws.iter_rows(min_row=5, max_row=13, max_col=30)
                for c in row if c.protection.locked is False}
    assert unlocked == {'D5', 'L5', 'J6', 'K6', 'J7', 'K7',
                        'D8', 'L8', 'K9',                       # lumped row: quantity stays locked
                        'D10', 'L10', 'J11', 'K11',
                        'D12', 'L12', 'J13', 'K13'}
    for ref in sorted(unlocked):
        assert ws[ref].fill.fgColor.rgb.endswith('FFF2CC'), ref


# ---- links into the fund sheets ----

def test_fund_month_cells_point_at_the_parent_row(applied):
    wb, _, _ = applied
    ws = wb[MGMT]
    expected = ("=IF('4. Điều chỉnh'!$I$5=0,'4. Điều chỉnh'!$M$5/12,'4. Điều chỉnh'!$S$5*IF('4. Điều chỉnh'!$I$5=0,1,"
                "'4. Điều chỉnh'!$M$5/'4. Điều chỉnh'!$I$5))")
    assert ws['H20'].value == expected and ws['F20'].value == expected
    assert ws['S20'].value == expected.replace('$S$5', '$AD$5')
    assert ws['F14'].value is None                             # Schedule: F untouched
    assert "'4. Điều chỉnh'!$S$10*" in ws['H14'].value and ws['H14'].value.startswith("=IF(")
    assert ws['H21'].value == 24_000_000 and ws['F21'].value == 24_000_000   # ESS4 not covered
    assert "'4. Điều chỉnh'!$S$12*" in wb[COMMON]['H20'].value
    assert ws['G20'].value.startswith('=IF($C20=') and ws['AK20'].value == '=SUM(AQ20:BB20)'


def test_untouched_everything_equals_the_original(applied):
    wb, _, _ = applied
    ev = _Eval(wb)
    assert ev.cell(ba.SHEET_NAME, 'M5') == 1_752_000_000 == ev.cell(ba.SHEET_NAME, 'I5')
    assert ev.cell(ba.SHEET_NAME, 'N5') == 0 and ev.cell(ba.SHEET_NAME, 'O5') == 0
    assert ev.cell(ba.SHEET_NAME, 'M10') == 780_000_000
    assert ev.cell(MGMT, 'F20') == 146_000_000 and ev.cell(MGMT, 'S20') == 146_000_000
    assert [ev.cell(MGMT, f'{get_column_letter(8 + k)}14') for k in range(12)] == RAMP
    assert ev.cell(MGMT, 'AK20') == 1_752_000_000 and ev.cell(MGMT, 'G20') == 1_752_000_000
    assert ev.cell(MGMT, 'AK14') == sum(RAMP)
    assert ev.cell(COMMON, 'AK20') == 48_000_000
    assert ev.cell('1. Summary', 'H30') == sum(RAMP) + 48_000_000


def test_each_adjustment_type_moves_the_fund_row(applied):
    wb, ws, _ = applied
    ev = _Eval(wb)
    ws['D5'], ws['J6'] = 'Số lượng', 5                          # +1 post at the main gate
    assert ev.cell(ba.SHEET_NAME, 'M6') == 1_500_000_000
    assert ev.cell(ba.SHEET_NAME, 'M5') == 2_052_000_000 and ev.cell(ba.SHEET_NAME, 'N5') == 300_000_000
    assert ev.cell(MGMT, 'F20') == pytest.approx(146_000_000 * 2_052 / 1_752)
    assert ev.cell(MGMT, 'AK20') == pytest.approx(2_052_000_000)
    assert ev.cell('1. Summary', 'H29') == pytest.approx(2_052_000_000)
    ws['D8'], ws['K9'] = 'Đơn giá', 290_400_000                 # lumped line, price +10%
    assert ev.cell(ba.SHEET_NAME, 'M8') == pytest.approx(290_400_000)
    assert ev.cell(MGMT, 'H22') == pytest.approx(24_200_000)
    ws['D10'], ws['L10'] = 'Trượt giá', 0.05                    # Schedule line, 5% inflation on every month
    assert ev.cell(ba.SHEET_NAME, 'M10') == pytest.approx(819_000_000)
    assert ev.cell(MGMT, 'H14') == pytest.approx(10_500_000) and ev.cell(MGMT, 'S14') == pytest.approx(126_000_000)
    ws['D5'] = 'Trượt giá'                                      # the quantity edit no longer counts
    assert ev.cell(ba.SHEET_NAME, 'M5') == 1_752_000_000
    ws['D5'], ws['K6'] = 'Số lượng + Đơn giá', 330_000_000      # 5 posts at the new price, CCTV unchanged
    assert ev.cell(ba.SHEET_NAME, 'M6') == 1_650_000_000
    assert ev.cell(ba.SHEET_NAME, 'M5') == 2_202_000_000 and ev.cell(MGMT, 'AK20') == pytest.approx(2_202_000_000)
    ws['D8'] = 'Số lượng + Đơn giá'                             # lumped row: quantity stays the original
    assert ev.cell(ba.SHEET_NAME, 'M8') == pytest.approx(290_400_000)


def test_a_month_cell_that_is_already_a_formula_is_wrapped_not_replaced():
    wb = _workbook()
    ws = wb[MGMT]
    _fund_row(ws, 83, 'EMH2', 'Monthly', [0] * 12)
    old = "=('A1. Staff cost'!AC96-'A1. Staff cost'!AC90*'A1. Staff cost'!AC95+SUM('A1. Staff cost'!AC98:AC100)*12)/12"
    ws['F83'] = old
    for c in range(8, 20):
        ws.cell(row=83, column=c, value=old)
    a1 = wb['A1. Staff cost']
    a1['AC96'], a1['AC90'], a1['AC95'], a1['AC98'], a1['AC99'], a1['AC100'] = 1_200_000_000, 0, 0, 0, 0, 0
    item = {'code': 'EMH2', 'sheet': MGMT, 'row': 83, 'name_vi': 'Nhân sự Savills', 'freq': 'Monthly',
            'months': [100_000_000.0] * 12, 'annual': 1_200_000_000.0,
            'subs': [{'desc_vi': 'Trưởng BQL', 'unit_vi': 'người', 'qty': 1.0, 'unit_price': 1_200_000_000.0,
                      'amount': 1_200_000_000.0, 'qty_editable': True}]}
    ba.apply(wb, [item])
    ratio = "IF('4. Điều chỉnh'!$I$5=0,1,'4. Điều chỉnh'!$M$5/'4. Điều chỉnh'!$I$5)"
    assert ws['F83'].value == '=(' + old[1:] + ')*' + ratio
    assert ws['H83'].value == ws['F83'].value and ws['S83'].value == ws['F83'].value
    assert "'A1. Staff cost'!AC96" in ws['F83'].value          # the link into A1 is still there
    ev = _Eval(wb)
    assert ev.cell(MGMT, 'F83') == 100_000_000 and ev.cell(MGMT, 'AK83') == 1_200_000_000
    a1['AC96'] = 1_320_000_000                                  # A1 still drives EMH2 ...
    assert ev.cell(MGMT, 'F83') == 110_000_000
    wb[ba.SHEET_NAME]['D5'], wb[ba.SHEET_NAME]['J6'] = 'Số lượng', 2   # ... and the adjustment still scales it
    assert ev.cell(MGMT, 'F83') == 220_000_000


def test_zero_original_row_stays_zero_without_a_division_error():
    wb = _workbook()
    _fund_row(wb[MGMT], 30, 'ESS99', 'Monthly', [0] * 12)
    item = {'code': 'ESS99', 'sheet': MGMT, 'row': 30, 'name_vi': 'Dòng trống', 'freq': 'Monthly',
            'months': [0.0] * 12, 'annual': 0.0, 'subs': []}
    ba.apply(wb, [item])
    ev = _Eval(wb)
    ws = wb[ba.SHEET_NAME]
    assert ws['I5'].value == 0.0 and ev.cell(ba.SHEET_NAME, 'O5') == 'N/A'
    assert ev.cell(MGMT, 'H30') == 0
    assert ws.data_validations.dataValidation[0].sqref


def test_row_is_found_by_code_not_by_the_row_number():
    wb = _workbook()
    items = _items()[:1]
    items[0]['row'] = 99                                        # stale row number: the code wins
    ba.apply(wb, items)
    assert "'4. Điều chỉnh'!$S$5*" in wb[MGMT]['H20'].value
    assert wb[MGMT]['H99'].value is None
    assert wb[ba.SHEET_NAME]['Q5'].value == 20                 # the resolved row is what the sheet records
    with pytest.raises(ValueError):
        ba.apply(wb, [dict(items[0], code='NOPE', row=None)])


def test_apply_twice_rebuilds_one_sheet(applied):
    wb, _, _ = applied
    ba.apply(wb, _items())
    assert wb.sheetnames.count(ba.SHEET_NAME) == 1
    assert wb[ba.SHEET_NAME]['A5'].value == 'ESS1' and wb[ba.SHEET_NAME].max_row == 13


def test_text_fixer_leaves_the_formulas_alone(applied):
    from generate_project_output import _fix_fake_formula_strings
    wb, ws, _ = applied  # noqa
    before = {c.coordinate: c.value for row in ws.iter_rows() for c in row if isinstance(c.value, str)}
    fund_before = wb[MGMT]['H20'].value
    _fix_fake_formula_strings(wb)
    assert {c.coordinate: c.value for row in ws.iter_rows() for c in row if isinstance(c.value, str)} == before
    assert wb[MGMT]['H20'].value == fund_before
    assert wb[MGMT]['T22'].value.startswith('text that starts')


# ---- Excel itself ----

def _excel_available():
    try:
        import win32com.client  # noqa: F401
    except ImportError:
        return False
    return os.name == 'nt'


@pytest.mark.skipif(not _excel_available(), reason='Excel COM (pywin32 on Windows) not available')
def test_excel_recalculates_without_errors_and_moves_as_expected(tmp_path):
    import pythoncom
    import win32com.client
    from generate_project_output import _fix_fake_formula_strings
    wb = _workbook()
    _fix_fake_formula_strings(wb)          # the pipeline's order: fixer first, then apply
    ba.apply(wb, _items())
    path = tmp_path / 'adjust_fixture.xlsx'
    wb.save(path)
    pythoncom.CoInitialize()
    xl = win32com.client.DispatchEx('Excel.Application')
    xl.Visible, xl.DisplayAlerts = False, False
    try:
        book = xl.Workbooks.Open(str(path))
        xl.CalculateFull()
        adj, fund, common = book.Worksheets(ba.SHEET_NAME), book.Worksheets(MGMT), book.Worksheets(COMMON)
        errors = [(ws.Name, c.Address) for ws in book.Worksheets
                  for c in (ws.UsedRange.SpecialCells(-4123, 16) if _has_error(ws) else [])]
        assert errors == []
        assert adj.Range('M5').Value == 1_752_000_000 and adj.Range('N5').Value == 0
        assert fund.Range('AK20').Value == 1_752_000_000 and fund.Range('F20').Value == 146_000_000
        assert fund.Range('AK14').Value == sum(RAMP) and common.Range('AK20').Value == 48_000_000
        assert adj.ProtectContents and not adj.Range('J6').Locked and adj.Range('I6').Locked
        assert adj.Range('D5').Validation.Formula1.strip('"') == 'Số lượng,Đơn giá,Số lượng + Đơn giá,Trượt giá,Nhập số'
        assert adj.Rows(6).OutlineLevel == 2 and adj.Rows(6).Hidden
        adj.Range('D5').Value, adj.Range('J6').Value = 'Số lượng', 5
        adj.Range('D10').Value, adj.Range('L10').Value = 'Trượt giá', 0.05
        xl.CalculateFull()
        assert adj.Range('M5').Value == 2_052_000_000
        assert abs(fund.Range('AK20').Value - 2_052_000_000) < 1
        assert abs(fund.Range('S14').Value - 126_000_000) < 1
        assert abs(book.Worksheets('1. Summary').Range('H29').Value - 2_052_000_000) < 1
        # both quantity and price: 5 posts at 330,000,000 + 2 at 276,000,000; lumped row: original quantity x new price
        adj.Range('D5').Value, adj.Range('K6').Value = 'Số lượng + Đơn giá', 330_000_000
        adj.Range('D8').Value, adj.Range('K9').Value = 'Số lượng + Đơn giá', 290_400_000
        xl.CalculateFull()
        assert adj.Range('M6').Value == 1_650_000_000 and adj.Range('M5').Value == 2_202_000_000
        assert abs(fund.Range('AK20').Value - 2_202_000_000) < 1
        assert abs(adj.Range('M8').Value - 290_400_000) < 1 and abs(fund.Range('H22').Value - 24_200_000) < 1
        book.Close(SaveChanges=False)
    finally:
        xl.Quit()
        pythoncom.CoUninitialize()


def _has_error(ws):
    try:
        ws.UsedRange.SpecialCells(-4123, 16)   # xlCellTypeFormulas, xlErrors
        return True
    except Exception:
        return False


# ---- type "Nhập số" and append_items (change adjust-rows-for-zero-tool-codes) ----

def _zero_item(code='ESS99', row=30, sheet=MGMT, name='Dòng công cụ ra 0'):
    return {'code': code, 'sheet': sheet, 'row': row, 'name_vi': name, 'freq': 'Monthly', 'months': [0.0] * 12,
            'annual': 0.0, 'subs': [{'desc_vi': name, 'unit_vi': 'khoản', 'qty': 1.0, 'unit_price': 0.0,
                                     'amount': 0.0, 'qty_editable': False}]}


def test_enter_type_is_the_fifth_item_of_the_dropdown(applied):
    _, ws, _ = applied
    assert ba.ADJUSTMENT_TYPES[-1] == ba.TYPE_ENTER == 'Nhập số' and len(ba.ADJUSTMENT_TYPES) == 5
    assert ws.data_validations.dataValidation[0].formula1.endswith(',Nhập số"')


def test_enter_type_takes_the_typed_figure_per_row(applied):
    wb, ws, _ = applied
    ws['D5'] = 'Nhập số'
    ws['K6'], ws['K7'] = 100.0, 50.0
    ev = _Eval(wb)
    assert ev.cell(ba.SHEET_NAME, 'M6') == 100.0 and ev.cell(ba.SHEET_NAME, 'M5') == 150.0
    assert ev.cell(MGMT, 'H20') == pytest.approx(146_000_000 * 150.0 / 1_752_000_000)


def _zero_workbook():
    wb = _workbook()
    _fund_row(wb[MGMT], 30, 'ESS99', 'Monthly', [None] * 12)
    wb[MGMT].cell(row=30, column=6).value = None
    return wb


def test_zero_original_month_is_the_new_amount_over_twelve():
    wb = _zero_workbook()
    ba.apply(wb, _items())
    parents = ba.append_items(wb, [_zero_item()])
    ws = wb[ba.SHEET_NAME]
    assert parents == {'ESS99': 14}
    p = parents['ESS99']
    ws.cell(row=p, column=4).value = 'Nhập số'
    ws.cell(row=p + 1, column=11).value = 1_200_000.0
    ev = _Eval(wb)
    assert ev.cell(ba.SHEET_NAME, f'M{p}') == 1_200_000.0
    assert ev.cell(MGMT, 'F30') == 100_000.0 and ev.cell(MGMT, 'S30') == 100_000.0
    assert ev.cell(MGMT, 'AK30') == 1_200_000.0


def test_zero_original_untouched_stays_zero():
    wb = _zero_workbook()
    ba.apply(wb, _items())
    ba.append_items(wb, [_zero_item()])
    ev = _Eval(wb)
    assert ev.cell(MGMT, 'AK30') == 0 and ev.cell(MGMT, 'H30') == 0


def test_append_items_keeps_the_earlier_rows_and_extends_the_dropdown():
    wb = _zero_workbook()
    ba.apply(wb, _items())
    ws = wb[ba.SHEET_NAME]
    before = [[c.value for c in row] for row in ws.iter_rows(min_row=1, max_row=13)]
    ba.append_items(wb, [_zero_item()])
    assert [[c.value for c in row] for row in ws.iter_rows(min_row=1, max_row=13)] == before
    assert [ws.cell(row=r, column=3).value for r in (14, 15)] == ['Tổng', 'Chi tiết']
    assert (ws['A14'].value, ws['P14'].value, ws['Q14'].value) == ('ESS99', MGMT, 30)
    assert ws['J15'].value == '=G15'                      # locked quantity
    assert ws.protection.sheet and ws['K15'].protection.locked is False and ws['A14'].protection.locked
    assert 'D14' in str(ws.data_validations.dataValidation[0].sqref)
    assert ws.row_dimensions[15].outlineLevel == 1 and ws.row_dimensions[15].hidden
    assert "'4. Điều chỉnh'!$M$14/12" in wb[MGMT]['F30'].value


def test_append_items_skips_a_code_already_on_the_sheet():
    wb = _zero_workbook()
    ba.apply(wb, _items())
    assert ba.append_items(wb, [_zero_item()]) == {'ESS99': 14}
    assert ba.append_items(wb, [_zero_item()]) == {}
    assert ba.append_items(wb, [_zero_item('ESS1', 20)]) == {}


def test_append_items_reports_a_code_missing_from_the_fund_sheet():
    wb = _zero_workbook()
    ba.apply(wb, _items())
    with pytest.raises(ValueError, match='not found'):
        ba.append_items(wb, [_zero_item('NOPE', None)])


def test_new_project_apply_is_unchanged_by_the_fifth_type():
    wb = _workbook()
    ba.apply(wb, _items())
    ws = wb[ba.SHEET_NAME]
    assert ws.max_row == 13 and [ws.cell(row=r, column=1).value for r in (5, 8, 10, 12)] == ['ESS1', 'ESS16', 'RM.AP', 'RA1.A']
