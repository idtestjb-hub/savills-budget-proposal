"""Change add-line-frequency on the workbook: the generator's default frequency pass (task 2.1), sheet 4 reading a
cyclic line (3.1), the frequency cells and the fund-row link (3.2-3.3) and the upgrade of an older sheet 4 (3.4).
Invented workbook and figures (TEST DATA); formulas checked with the small evaluator of test_budget_adjustment."""
import openpyxl
import pytest
from openpyxl.utils import get_column_letter

import adjustment_detail as ad
import budget_adjustment as ba
import generate_project_budget as g
import line_frequency as lf
from tests.test_budget_adjustment import MGMT, COMMON, RAMP, _Eval, _items, _workbook

# The form writes "Half a year"; Excel compares text without case, the small evaluator does not.
E_FORM = ('=IF(OR(C{r}="Schedule",C{r}="Monthly"),12,IF(C{r}="Yearly",1,IF(C{r}="Half a Year",2,'
          'IF(C{r}="Quarterly",4,IF(C{r}="Optional",$D{r},)))))')
HEADERS = [f'{m:02d}/2027' for m in range(1, 13)]


def _form_cells(ws, r):
    """The form's own E, G, AQ:BB (month spread on headers) and AK on a fixture fund row; row 8 = month headers."""
    ws.cell(row=r, column=5, value=E_FORM.format(r=r))
    ws.cell(row=r, column=7, value=f'=IF($C{r}="Schedule",SUM(H{r}:S{r}),F{r}*E{r})')
    for k in range(12):
        col = get_column_letter(43 + k)
        hits = ''.join(f'IF(${get_column_letter(8 + j)}{r}={col}$10,$F{r},' for j in range(12))
        ws.cell(row=r, column=43 + k, value=(f'=IF($C{r}="Schedule",VALUE({get_column_letter(8 + k)}{r}),'
                                             f'IF($C{r}="Monthly",$F{r},{hits}0' + ')' * 12 + '))'))
    ws.cell(row=r, column=37, value=f'=SUM(AQ{r}:BB{r})')


def _with_headers(wb):
    for name in (MGMT, COMMON):
        ws = wb[name]
        for k, h in enumerate(HEADERS):
            ws.cell(row=8, column=8 + k, value=h)
            ws.cell(row=10, column=43 + k, value=h)
    return wb


# ---- 2.1 generation ----------------------------------------------------------------------------------------------

def _gen_sheet():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = MGMT
    wb.create_sheet(COMMON)
    _with_headers(wb)
    for r, code in ((20, 'ESM25'), (21, 'RO2a'), (22, 'ESS1'), (23, 'ESM3'), (24, 'ESC12')):
        ws.cell(row=r, column=25, value=code)
    g._write_even_monthly_row(ws, 20, 15_400_000, remark='Đối chiếu chất lượng nước sau xử lý.')
    ws.cell(row=21, column=3, value='Half a Year')         # the template's RO2a, priced at 0 by the tool
    ws.cell(row=21, column=6, value=0)
    g._write_even_monthly_row(ws, 22, 1_200_000_000)        # unlisted: stays Monthly
    g._write_ramped_row(ws, 23, [1_000_000] * 12)           # Schedule: stays Schedule
    ws.cell(row=24, column=3, value='Monthly')              # a formula F stays as it is
    ws.cell(row=24, column=6, value="='A5'!H8/12")
    return wb, ws


TABLE = {'ESM25': lf.Default('ESM25', 'Quarterly', 4, 1, [1, 4, 7, 10], 'TEST DATA', ''),
         'RO2a': lf.Default('RO2a', 'Half a Year', 2, 1, [1, 7], 'TEST DATA', ''),
         'ESM3': lf.Default('ESM3', 'Half a Year', 2, 1, [1, 7], 'TEST DATA', ''),
         'ESC12': lf.Default('ESC12', 'Yearly', 1, 1, [1], 'TEST DATA', '')}


def test_generation_writes_the_forms_way_and_keeps_the_annual():
    wb, ws = _gen_sheet()
    changed = g._apply_line_frequencies(ws, TABLE)
    assert [c[0] for c in changed] == ['ESM25', 'RO2a']
    assert (ws['C20'].value, ws['F20'].value) == ('Quarterly', 3_850_000)
    assert [ws.cell(row=20, column=8 + k).value for k in range(12)] == [
        '=H8', None, None, '=K8', None, None, '=N8', None, None, '=Q8', None, None]
    remark = ws['T20'].value
    assert remark.endswith('\nHàng quý, 4 lần/năm × 3,850,000 VND/lần, chi vào T1, T4, T7, T10')
    assert remark.startswith('Đối chiếu chất lượng nước sau xử lý.')
    assert ws['C21'].value == 'Half a Year' and ws['F21'].value == 0
    assert ws['H21'].value == '=H8' and ws['N21'].value == '=N8' and not ws['T21'].value
    assert ws['C22'].value == 'Monthly' and ws['C23'].value == 'Schedule' and ws['F24'].value == "='A5'!H8/12"
    _form_cells(ws, 20)
    ws.cell(row=20, column=21, value=ba.times_check_formula(20))
    ev = _Eval(wb)
    assert ev.cell(MGMT, 'G20') == 15_400_000 == ev.cell(MGMT, 'AK20')
    assert ev.cell(MGMT, 'U20') == 0
    assert [ev.cell(MGMT, f'{get_column_letter(43 + k)}20') for k in range(12)] == [
        3_850_000 if k in (0, 3, 6, 9) else 0 for k in range(12)]


def test_an_unlisted_cyclic_template_row_goes_to_monthly():
    """Change default-frequency-from-real-budgets: RO2a left the table (Monthly in every real budget), so its
    template row (Half a Year, one month marked) is written Monthly; a priced row keeps its year."""
    wb, ws = _gen_sheet()
    ws['K21'] = '=K8'                                      # the template marks only T4
    ws.cell(row=26, column=25, value='ZZ1')
    ws.cell(row=26, column=3, value='Quarterly')
    ws.cell(row=26, column=6, value=3_000_000)
    for col in (8, 11, 14, 17):
        ws.cell(row=26, column=col, value=f'={get_column_letter(col)}8')
    table = {k: v for k, v in TABLE.items() if k != 'RO2a'}
    changed = g._apply_line_frequencies(ws, table)
    assert ('RO2a', 'Monthly', 0) in changed and ('ZZ1', 'Monthly', 1_000_000) in changed
    assert ws['C21'].value == 'Monthly' and ws['F21'].value == 0
    assert all(ws.cell(row=21, column=8 + k).value is None for k in range(12))
    assert ws['C26'].value == 'Monthly' and ws['F26'].value == 1_000_000      # 3,000,000 x 4 / 12
    assert all(ws.cell(row=26, column=8 + k).value is None for k in range(12))


def test_collect_written_reads_a_cyclic_line_as_price_times_count():
    wb, ws = _gen_sheet()
    g._apply_line_frequencies(ws, TABLE)
    rows = dict(g.MGMT_FUND_ROWS)
    try:
        g.MGMT_FUND_ROWS.clear()
        g.MGMT_FUND_ROWS.update({'a': 20})
        written = g._collect_written(wb)
    finally:
        g.MGMT_FUND_ROWS.clear()
        g.MGMT_FUND_ROWS.update(rows)
    assert written['ESM25']['value'] == 15_400_000


# ---- 3.1 sheet 4 lists a line of every frequency -----------------------------------------------------------------

def test_a_half_year_line_is_read_with_its_months():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.cell(row=37, column=3, value='Half a Year')
    ws.cell(row=37, column=6, value=5_000_000)
    ws.cell(row=37, column=11, value='=K8')
    ws.cell(row=37, column=17, value='=$Q$8')
    assert ad._row_figures(ws, 37) == ('Half a Year', [0, 0, 0, 5_000_000, 0, 0, 0, 0, 0, 5_000_000, 0, 0])
    ws.cell(row=37, column=12, value='=SUM(A1:A2)')
    assert ad._row_figures(ws, 37) == ('Half a Year', None)


# ---- 3.2 / 3.3 frequency cells and the fund-row link -------------------------------------------------------------

def _applied():
    wb = _with_headers(_workbook())
    for name, r in ((MGMT, 14), (MGMT, 20), (MGMT, 22), (COMMON, 20)):
        _form_cells(wb[name], r)
    items = _items()
    parents = ba.apply(wb, items)
    return wb, wb[ba.SHEET_NAME], parents


def _months(ev, sheet, r):
    return [ev.cell(sheet, f'{get_column_letter(8 + k)}{r}') for k in range(12)]


def test_blank_frequency_leaves_every_figure_and_check():
    wb, ws, _ = _applied()
    ev = _Eval(wb)
    assert ev.cell(MGMT, 'C20') == 'Monthly' and ev.cell(MGMT, 'F20') == 146_000_000
    assert ev.cell(MGMT, 'AK20') == 1_752_000_000 and ev.cell(MGMT, 'U20') == 0
    assert _months(ev, MGMT, 14) == RAMP and ev.cell(MGMT, 'AK14') == sum(RAMP) and ev.cell(MGMT, 'U14') == 0
    assert (ws['AT5'].value, ws['AU5'].value, ws['AT10'].value) == (12, 1, 12)
    assert ws['AE5'].protection.locked is False and ws['AH5'].protection.locked is False
    assert ws.column_dimensions['AT'].hidden and not ws.column_dimensions['AE'].hidden


def test_monthly_to_quarterly_keeps_the_price_per_time():
    wb, ws, _ = _applied()
    ws['AE5'], ws['AF5'] = 'Quarterly', 2
    ev = _Eval(wb)
    assert ev.cell(ba.SHEET_NAME, 'AG5') == 4
    assert ev.cell(ba.SHEET_NAME, 'M5') == 584_000_000                 # 1,752M x 4 / 12
    assert ev.cell(MGMT, 'C20') == 'Quarterly' and ev.cell(MGMT, 'F20') == 146_000_000
    assert _months(ev, MGMT, 20) == ['', '02/2027', '', '', '05/2027', '', '', '08/2027', '', '', '11/2027', '']
    assert ev.cell(MGMT, 'G20') == 584_000_000 == ev.cell(MGMT, 'AK20') and ev.cell(MGMT, 'U20') == 0


def test_optional_ticks_set_times_and_months():
    wb, ws, _ = _applied()
    ws['AE8'] = 'Optional'
    ws['AI8'], ws['AN8'], ws['AR8'] = 'x', 'x', 'x'                  # T2, T7, T11
    ev = _Eval(wb)
    assert ev.cell(ba.SHEET_NAME, 'M8') == 66_000_000                  # 264M x 3 / 12
    assert ev.cell(MGMT, 'D22') == 3 and ev.cell(MGMT, 'F22') == 22_000_000
    assert _months(ev, MGMT, 22) == ['', '02/2027', '', '', '', '', '07/2027', '', '', '', '11/2027', '']
    assert ev.cell(MGMT, 'AK22') == 66_000_000 and ev.cell(MGMT, 'U22') == 0


def test_schedule_takes_the_month_amounts():
    wb, ws, _ = _applied()
    ws['AE5'] = 'Schedule'
    ws['AH5'], ws['AS5'] = 100_000_000, 50_000_000
    ev = _Eval(wb)
    assert ev.cell(ba.SHEET_NAME, 'M5') == 150_000_000
    assert _months(ev, MGMT, 20) == [100_000_000] + [0] * 10 + [50_000_000]
    assert ev.cell(MGMT, 'F20') == '' and ev.cell(MGMT, 'AK20') == 150_000_000 and ev.cell(MGMT, 'U20') == 0


def test_schedule_original_to_half_year_and_common_area_yearly():
    wb, ws, _ = _applied()
    ws['AE10'], ws['AF10'] = 'Half a Year', 6
    ws['AE12'], ws['AF12'] = 'Yearly', 12
    ev = _Eval(wb)
    assert ev.cell(ba.SHEET_NAME, 'M10') == sum(RAMP) * 2 / 12
    assert _months(ev, MGMT, 14)[5] == '06/2027' and _months(ev, MGMT, 14)[11] == '12/2027'
    assert ev.cell(MGMT, 'AK14') == sum(RAMP) * 2 / 12 and ev.cell(MGMT, 'U14') == 0
    assert ev.cell(COMMON, 'AK20') == 4_000_000 and _months(ev, COMMON, 20)[11] == '12/2027'
    assert ev.cell(COMMON, 'U20') == 0


def test_inflation_with_a_new_frequency_multiplies():
    wb, ws, _ = _applied()
    ws['D5'], ws['L5'] = 'Trượt giá', 0.10
    ws['AE5'] = 'Half a Year'
    ev = _Eval(wb)
    assert ev.cell(ba.SHEET_NAME, 'M5') == pytest.approx(1_752_000_000 * 1.10 * 2 / 12)


def test_a_cyclic_original_line_untouched_and_changed():
    wb = _with_headers(_workbook())
    ws = wb[MGMT]
    ws.cell(row=40, column=25, value='ESM25')
    ws.cell(row=40, column=3, value='Quarterly')
    ws.cell(row=40, column=6, value=3_500_000)
    for m in (1, 4, 7, 10):
        ws.cell(row=40, column=7 + m, value=f'={get_column_letter(7 + m)}8')
    _form_cells(ws, 40)
    item = {'code': 'ESM25', 'sheet': MGMT, 'row': 40, 'name_vi': 'Đối chiếu nước thải', 'freq': 'Quarterly',
            'months': [3_500_000.0 if m in (1, 4, 7, 10) else 0.0 for m in range(1, 13)], 'annual': 14_000_000.0,
            'subs': [{'desc_vi': 'Đối chiếu nước thải', 'unit_vi': 'khoản', 'qty': 1.0, 'unit_price': 14_000_000.0,
                      'amount': 14_000_000.0, 'qty_editable': False}]}
    ba.apply(wb, [item])
    s4 = wb[ba.SHEET_NAME]
    assert (s4['AT5'].value, s4['AU5'].value) == (4, 1)
    ev = _Eval(wb)
    assert ev.cell(MGMT, 'C40') == 'Quarterly' and ev.cell(MGMT, 'F40') == 3_500_000
    assert _months(ev, MGMT, 40) == ['01/2027', '', '', '04/2027', '', '', '07/2027', '', '', '10/2027', '', '']
    assert ev.cell(MGMT, 'AK40') == 14_000_000 and ev.cell(MGMT, 'U40') == 0
    s4['AE5'] = 'Monthly'                                               # 12 times at the same price per time
    ev = _Eval(wb)
    assert ev.cell(ba.SHEET_NAME, 'M5') == 42_000_000 and ev.cell(MGMT, 'F40') == 3_500_000
    assert ev.cell(MGMT, 'AK40') == 42_000_000 and ev.cell(MGMT, 'U40') == 0


# ---- 3.4 an older sheet 4 gains the cells, figures unchanged -----------------------------------------------------

def _make_old(wb, parent_row, item):
    """Turn a total row and its fund row back into the layout before change add-line-frequency."""
    s4 = wb[ba.SHEET_NAME]
    for col in range(ba.COL['new_freq'], ba.FREQ_LAST_COL + 1):
        s4.cell(row=parent_row, column=col).value = None
        s4.cell(row=ba.HEADER_ROW, column=col).value = None
    s4.cell(row=parent_row, column=ba.COL['new_amount']).value = '=SUM(M6:M7)'
    ws = wb[item['sheet']]
    r = item['row']
    ws.cell(row=r, column=3).value = item['freq']
    ws.cell(row=r, column=4).value = None
    for k in range(12):
        ws.cell(row=r, column=8 + k).value = ba.month_formula(parent_row, k)
    ws.cell(row=r, column=6).value = ba.month_formula(parent_row, 0)
    ws.cell(row=r, column=21).value = f'=E{r}-IF(C{r}<>"Monthly",COUNTA(H{r}:S{r}),12)'


def test_upgrade_adds_the_cells_and_keeps_the_figures():
    wb, s4, _ = _applied()
    item = dict(_items()[0], row=20)
    _make_old(wb, 5, item)
    before = _Eval(wb)
    old = [before.cell(MGMT, ref) for ref in ('F20', 'H20', 'S20', 'AK20')]
    assert ba.upgrade(wb) == 1
    assert ba.upgrade(wb) == 0                                          # once only
    assert s4['AE4'].value == 'Tần suất mới' and s4['AT5'].value == 12
    assert s4['M5'].value == ba.frequency_amount('SUM(M6:M7)', 5)
    ev = _Eval(wb)
    assert [ev.cell(MGMT, ref) for ref in ('F20', 'H20', 'S20', 'AK20')] == old
    s4['AE5'], s4['AF5'] = 'Yearly', 12
    ev = _Eval(wb)
    assert ev.cell(MGMT, 'AK20') == 146_000_000 and _months(ev, MGMT, 20)[11] == '12/2027'


def test_a_schedule_original_with_a_rate_link_in_f_stays_editable_and_keeps_the_link():
    # RM.AP / RP1: F holds a rate link the form ignores under Schedule; the line can still change frequency
    wb = _with_headers(_workbook())
    ws = wb[MGMT]
    ws['F14'] = "='1. Summary'!B2"
    wb['1. Summary']['B2'] = 10_000
    _form_cells(ws, 14)
    items = [it for it in _items() if it['code'] == 'RM.AP']
    ba.apply(wb, items)
    s4 = wb[ba.SHEET_NAME]
    assert s4['AE5'].protection.locked is False
    ev = _Eval(wb)
    assert ev.cell(MGMT, 'F14') == 10_000 and _months(ev, MGMT, 14) == RAMP       # untouched: link and months kept
    s4['AE5'], s4['AF5'] = 'Quarterly', 1
    ev = _Eval(wb)
    assert ev.cell(MGMT, 'F14') == sum(RAMP) * 4 / 12 / 4 and ev.cell(MGMT, 'U14') == 0
