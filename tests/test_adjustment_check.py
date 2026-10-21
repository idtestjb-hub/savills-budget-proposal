"""The adjustment-sheet check (docs/32 section 4) on small workbooks built to the layout of docs/32 section 3.

Every workbook here is invented: two fund sheets with a handful of leaf rows, the sheet '4. Điều chỉnh' with one parent
row per written line and its detail rows, and the fund months linked back to the sheet. The formulas are evaluated by
Excel (one instance for the whole module), as the real check does; without Excel the module is skipped.
"""
import openpyxl
import pytest
from openpyxl.utils import get_column_letter

from verification import checks

ADJ = checks.ADJUSTMENT_SHEET
FUND = '2. Budget-Management Fund'
CAF = '2.2 Common area Fund'
A1 = 'A1. Staff cost 08.2026 (VN)'
SHEET_ORDER = ['Cover', '1. Summary', FUND, CAF, '3. Budget-Sinking Fund', '3.1 Report-Sinking Fund', ADJ, A1]
VARIANTS = ('good', 'parent_mismatch', 'm_differs', 'months_constant', 'missing_code', 'misplaced', 'wrapped')


def _link(parent_row, month_index):
    """The fund month cell of docs/32 section 3: the original month scaled by the parent's M / I."""
    q = f"'{ADJ}'"
    col = get_column_letter(19 + month_index)
    return (f"={q}!{col}{parent_row}*IF({q}!I{parent_row}=0,1,{q}!M{parent_row}/{q}!I{parent_row})")


def _wrap(old_formula, parent_row):
    """A fund cell that was already a formula keeps it inside the wrap: =(<old>)*IF(I=0,1,M/I)."""
    q = f"'{ADJ}'"
    return f"=({old_formula[1:]})*IF({q}!$I${parent_row}=0,1,{q}!$M${parent_row}/{q}!$I${parent_row})"


def _detail_m(parent_row, r):
    p = f'$D${parent_row}'
    return (f'=IF({p}="Số lượng",J{r}*H{r},IF({p}="Đơn giá",G{r}*K{r},'
            f'IF({p}="Trượt giá",I{r}*(1+$L${parent_row}),I{r})))')


def _fund_leaf(ws, r, code, freq, parent_row=None, constant=None):
    """One fund leaf row: C freq, E 12, F and H:S the month cells, G the form's own total, Y the code, AK the sum."""
    ws.cell(r, 3, freq)
    ws.cell(r, 5, 12)
    ws.cell(r, 25, code)
    ws.cell(r, 7, f'=IF($C{r}="Schedule",SUM(H{r}:S{r}),F{r}*E{r})')
    ws.cell(r, 37, f'=SUM(H{r}:S{r})')
    for i in range(12):
        ws.cell(r, 8 + i, _link(parent_row, i) if parent_row else constant)
    ws.cell(r, 6, (_link(parent_row, 0) if parent_row else constant) if freq == 'Monthly' else None)


def _parent(ws, r, code, name, fund_sheet, fund_row, freq, months, details):
    """A parent row and its detail rows; returns the next free row."""
    last = r + len(details)
    ws.cell(r, 1, code)
    ws.cell(r, 2, name)
    ws.cell(r, 3, 'Tổng')
    ws.cell(r, 9, f'=SUM(I{r + 1}:I{last})')
    ws.cell(r, 12, 0)
    ws.cell(r, 13, f'=SUM(M{r + 1}:M{last})')
    ws.cell(r, 14, f'=M{r}-I{r}')
    ws.cell(r, 15, f'=IF(I{r}=0,"N/A",N{r}/I{r})')
    ws.cell(r, 16, fund_sheet)
    ws.cell(r, 17, fund_row)
    ws.cell(r, 18, freq)
    for i, m in enumerate(months):
        ws.cell(r, 19 + i, m)
    for k, (desc, unit, qty, price, editable) in enumerate(details, start=1):
        d = r + k
        ws.cell(d, 3, 'Chi tiết')
        ws.cell(d, 5, desc)
        ws.cell(d, 6, unit)
        ws.cell(d, 7, qty)
        ws.cell(d, 8, price)
        ws.cell(d, 9, qty * price)
        ws.cell(d, 10, qty if editable else f'=G{d}')
        ws.cell(d, 11, price)
        ws.cell(d, 13, _detail_m(r, d))
        ws.cell(d, 14, f'=M{d}-I{d}')
        ws.cell(d, 15, f'=IF(I{d}=0,"N/A",N{d}/I{d})')
    return last + 1


def build_workbook(path, variant='good'):
    """The invented deliverable: ESS1 (two editable posts), ESS4 (one post) and EMB3 (one lumped sub-row) on the
    management fund, RA1.A on the common-area fund; ESS9 at zero and EMH2 a staff-sheet formula (derived, off the
    sheet). `variant` breaks exactly one thing."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    order = list(SHEET_ORDER)
    if variant == 'misplaced':
        order.remove(ADJ)
        order.insert(order.index('1. Summary'), ADJ)
    for name in order:
        wb.create_sheet(name)
    wb[A1]['B2'] = 25_000_000                               # EMH2's month on the staff sheet (300,000,000 a year)

    adj = wb[ADJ]
    adj['A1'] = 'Điều chỉnh ngân sách'
    adj['A2'] = 'Chọn loại điều chỉnh ở cột D của dòng tổng, sửa ô vàng ở dòng chi tiết.'
    for c, h in enumerate(['Mã', 'Hạng mục', 'Loại dòng', 'Loại điều chỉnh', 'Nội dung chi tiết', 'ĐVT', 'SL gốc',
                           'Đơn giá gốc', 'Thành tiền gốc', 'SL mới', 'Đơn giá mới', 'Trượt giá %', 'Thành tiền mới',
                           'Chênh lệch', 'Chênh lệch %', 'Sheet quỹ', 'Dòng quỹ', 'Tần suất'], start=1):
        adj.cell(4, c, h)
    r = 5
    ess1_row = r
    r = _parent(adj, r, 'ESS1', 'Dịch vụ bảo vệ', FUND, 13, 'Monthly', [50_000_000] * 12,
                [('Vị trí cổng chính', 'vị trí', 4, 120_000_000, True), ('Vị trí CCTV', 'vị trí', 2, 60_000_000, True)])
    ess4_row = r
    r = _parent(adj, r, 'ESS4', 'Dịch vụ vệ sinh', FUND, 14, 'Monthly', [20_000_000] * 12,
                [('Nhân viên vệ sinh', 'vị trí', 2, 120_000_000, True)])
    emb3_row = r
    r = _parent(adj, r, 'EMB3', 'Văn phòng phẩm', FUND, 15, 'Schedule', [10_000_000] * 12,
                [('Văn phòng phẩm', 'khoản', 1, 120_000_000, False)])
    ra1a_row = r
    r = _parent(adj, r, 'RA1.A', 'Quảng cáo LCD', CAF, 13, 'Monthly', [1_000_000] * 12,
                [('Màn hình LCD sảnh', 'thiết bị', 1, 12_000_000, True)])
    emh2_row = r
    if variant == 'wrapped':
        r = _parent(adj, r, 'EMH2', 'Nhân sự Savills', FUND, 17, 'Monthly', [25_000_000] * 12,
                    [('Trưởng ban quản lý', 'người', 1, 300_000_000, True)])
    if variant == 'parent_mismatch':
        adj.cell(ess1_row, 9, 481_000_000)                 # a value instead of the SUM of its details
    if variant == 'm_differs':
        adj.cell(ess1_row, 4, 'Số lượng')                  # an edit left on the delivered sheet
        adj.cell(ess1_row + 1, 10, 5)

    fund = wb[FUND]
    fund.cell(12, 25, 'ESS')
    fund.cell(12, 7, '=SUBTOTAL(9,G13:G18)')
    if variant == 'months_constant':
        _fund_leaf(fund, 13, 'ESS1', 'Monthly', constant=50_000_000)
    else:
        _fund_leaf(fund, 13, 'ESS1', 'Monthly', parent_row=ess1_row)
    _fund_leaf(fund, 14, 'ESS4', 'Monthly', parent_row=ess4_row)
    _fund_leaf(fund, 15, 'EMB3', 'Schedule', parent_row=emb3_row)
    _fund_leaf(fund, 16, 'ESS9', 'Monthly', constant=0)
    _fund_leaf(fund, 17, 'EMH2', 'Monthly', constant='=$F17')
    fund.cell(17, 6, f"='{A1}'!B2")
    if variant == 'wrapped':                                 # EMH2 on the sheet, its A1 formula kept inside the wrap
        fund.cell(17, 6, _wrap(f"='{A1}'!B2", emh2_row))
        for i in range(12):
            fund.cell(17, 8 + i, _wrap('=$F17', emh2_row))
    if variant == 'missing_code':
        _fund_leaf(fund, 18, 'ESS12', 'Monthly', constant=5_000_000)
    fund.cell(20, 25, 'PL1')                                 # PART 2 starts here: values, never lines
    fund.cell(20, 7, '=ROUND(G12-G13,0)')
    fund.cell(20, 37, 999_999_999)
    fund.cell(21, 25, 'VAT1')
    fund.cell(21, 7, 123_456)
    fund.cell(21, 37, 123_456)

    caf = wb[CAF]
    caf.cell(12, 25, 'RA')
    caf.cell(12, 7, '=SUBTOTAL(9,G13:G14)')
    _fund_leaf(caf, 13, 'RA1.A', 'Monthly', parent_row=ra1a_row)
    _fund_leaf(caf, 14, 'ESS1', 'Monthly', constant='=$F14')       # the form's own pass-through share
    caf.cell(14, 6, f"='{FUND}'!F13*0.1")
    wb.save(path)
    return path


@pytest.fixture(scope='module')
def evaluated(tmp_path_factory):
    """{variant: (sheet_names, cell, last_row)} after one Excel recalculation each."""
    pytest.importorskip('win32com.client')
    import pythoncom
    import win32com.client
    folder = tmp_path_factory.mktemp('adjust_check')
    out = {}
    pythoncom.CoInitialize()
    xl = None
    try:
        xl = win32com.client.DispatchEx('Excel.Application')
        xl.Visible = False
        xl.DisplayAlerts = False
        for variant in VARIANTS:
            path = build_workbook(str(folder / f'{variant}.xlsx'), variant)
            wb = xl.Workbooks.Open(path, UpdateLinks=0, ReadOnly=True)
            try:
                xl.CalculateFullRebuild()
                out[variant] = checks.adjustment_cells_from_workbook(wb)
            finally:
                wb.Close(SaveChanges=False)
    finally:
        if xl is not None:
            xl.Quit()
        pythoncom.CoUninitialize()
    return out


def _labels(diffs):
    return [str(d[0]) for d in diffs]


def test_expected_sheets_carry_the_sheet_right_after_the_sinking_fund_report():
    sheets = checks.EXPECTED_SHEETS['deliverable']
    assert sheets.index(ADJ) == sheets.index('3.1 Report-Sinking Fund') + 1


def test_good_workbook_passes_and_names_the_derived_lines(evaluated):
    ok, rows, diffs, notes = checks.adjustment_sheet_ties(*evaluated['good'])
    assert ok, diffs
    assert any('4 parent row(s), 5 detail row(s), 4 fund line(s) linked' in n for n in notes)
    assert any("EMH2 (row 17)" in n and "'2.2 Common area Fund': 1 pass-through" in n for n in notes), notes
    assert sum(1 for lbl, _g, _e in rows if "'!AK" in str(lbl)) == 3        # the management-fund lines
    assert sum(1 for lbl, _g, _e in rows if "'2.2 Common area Fund'!G" in str(lbl)) == 1


def test_parent_not_equal_to_its_details_is_caught(evaluated):
    ok, _rows, diffs, _n = checks.adjustment_sheet_ties(*evaluated['parent_mismatch'])
    assert not ok
    hit = [d for d in diffs if 'parent I vs sum of detail I' in str(d[0])]
    assert hit and hit[0][1] == 481_000_000 and hit[0][2] == 600_000_000


def test_a_sheet_left_edited_is_caught_as_m_not_equal_i(evaluated):
    ok, _rows, diffs, _n = checks.adjustment_sheet_ties(*evaluated['m_differs'])
    assert not ok
    labels = _labels(diffs)
    assert any('M (new amount) vs I' in lbl and lbl.startswith('ESS1') for lbl in labels), labels
    assert any('N (difference)' in lbl for lbl in labels)
    assert not any(lbl.startswith('ESS4') for lbl in labels)


def test_fund_months_written_as_values_are_caught(evaluated):
    ok, _rows, diffs, _n = checks.adjustment_sheet_ties(*evaluated['months_constant'])
    assert not ok
    assert len(diffs) == 1, diffs
    assert 'month cell(s) not a formula' in str(diffs[0][0]) and diffs[0][1] == 'H, I, J, K, L, M, N, O, P, Q, R, S, F'


def test_a_written_line_missing_from_the_sheet_is_caught(evaluated):
    ok, _rows, diffs, _n = checks.adjustment_sheet_ties(*evaluated['missing_code'])
    assert not ok
    assert len(diffs) == 1 and 'code ESS12' in str(diffs[0][0]) and diffs[0][1] == 60_000_000


def test_the_sheet_in_the_wrong_place_is_caught(evaluated):
    ok, _rows, diffs, _n = checks.adjustment_sheet_ties(*evaluated['misplaced'])
    assert not ok
    assert len(diffs) == 1 and 'position' in str(diffs[0][0])


def test_wrapped_fund_formulas_count_as_linked(evaluated):
    ok, rows, diffs, notes = checks.adjustment_sheet_ties(*evaluated['wrapped'])
    assert ok, diffs
    assert any('5 parent row(s)' in n and '5 fund line(s) linked' in n for n in notes), notes
    assert not any('EMH2' in n for n in notes)                           # linked now, no longer "derived"
    assert any("EMH2" in str(lbl) and "'!AK17" in str(lbl) and got == exp == 300_000_000 for lbl, got, exp in rows)


def test_unwrap_gives_back_the_old_formula():
    old = "=('A1. Staff cost 08.2026 (VN)'!AC96+SUM('A1. Staff cost 08.2026 (VN)'!AC98:AC99)*12)/12"
    wrapped = f"=({old[1:]})*IF('4. Điều chỉnh'!$I$41=0,1,'4. Điều chỉnh'!$M$41/'4. Điều chỉnh'!$I$41)"
    assert checks.unwrap_adjustment_formula(wrapped) == old
    assert checks.unwrap_adjustment_formula(old) == old
    assert checks.unwrap_adjustment_formula("='4. Điều chỉnh'!S41*IF('4. Điều chỉnh'!I41=0,1,1)") ==         "='4. Điều chỉnh'!S41*IF('4. Điều chỉnh'!I41=0,1,1)"
    assert checks.unwrap_adjustment_formula(123) == 123


def test_check_adjustment_sheet_runs_end_to_end(tmp_path):
    pytest.importorskip('win32com.client')
    path = build_workbook(str(tmp_path / 'good.xlsx'))
    ok, rows, diffs, notes = checks.check_adjustment_sheet({'deliverable': path})
    assert ok, diffs
    assert rows and notes


def test_original_months_come_from_the_sheet_when_the_fund_cells_are_formulas(tmp_path):
    wb = openpyxl.load_workbook(build_workbook(str(tmp_path / 'good.xlsx')))
    assert checks.adjustment_original_months(wb, 'ESS1') == [50_000_000.0] * 12
    assert checks.adjustment_original_months(wb, 'EMB3', FUND) == [10_000_000.0] * 12
    assert checks.adjustment_original_months(wb, 'RA1.A', CAF) == [1_000_000.0] * 12
    assert checks.adjustment_original_months(wb, 'RA1.A', FUND) is None
    assert checks.adjustment_original_months(wb, 'ESS9') is None
    assert checks.fund_months_as_written(wb, FUND, 13) == [50_000_000.0] * 12     # linked: the originals
    assert checks.fund_months_as_written(wb, CAF, 13) == [1_000_000.0] * 12
    assert checks.fund_months_as_written(wb, FUND, 16) == [0.0] * 12               # plain values stay
    wb_values = openpyxl.load_workbook(build_workbook(str(tmp_path / 'constant.xlsx'), 'months_constant'))
    assert checks.fund_months_as_written(wb_values, FUND, 13) == [50_000_000.0] * 12
    wb_values[FUND].cell(13, 8, "='4. Điều chỉnh'!S99")                          # linked, nobody on the sheet
    wb_values[FUND].cell(13, 25, 'ESS99')
    with pytest.raises(ValueError):
        checks.fund_months_as_written(wb_values, FUND, 13)
    wb_no_sheet = openpyxl.Workbook()
    assert checks.adjustment_original_months(wb_no_sheet, 'ESS1') is None


def test_missing_sheet_is_the_only_difference():
    ok, _rows, diffs, _n = checks.adjustment_sheet_ties(['Cover', FUND, CAF], lambda s, r, c: (None, None),
                                                        lambda s: 0)
    assert not ok and len(diffs) == 1 and 'sheet missing' in str(diffs[0][1])
