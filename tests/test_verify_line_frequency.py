"""verification.checks.line_frequency_ties / frequency_edit_ties (change add-line-frequency, task 5.1) on a fake cell
reader: a three-month Quarterly line fails the form's times check; a clean workbook passes. TEST DATA, no Excel."""
import openpyxl

import budget_adjustment as ba
from verification import checks

MF, CA = checks._FUND_SHEET, checks._COMMON_AREA_SHEET


class _Fake:
    """cell(sheet, r, c) -> (value, None) from {sheet: {row: {col: value}}}."""
    def __init__(self, data):
        self.data = data

    def cell(self, sheet, r, c):
        return self.data.get(sheet, {}).get(r, {}).get(c), None

    def last_row(self, sheet):
        return max(self.data.get(sheet, {}) or [0])


def _line(code, freq, e, u, v, months=(), f=1000, d=None):
    row = {25: code, 3: freq, 5: e, 21: u, 22: v, 6: f, 4: d}
    for m in months:
        row[7 + m] = f'0{m}/2027'
    return row


def test_clean_lines_pass_and_are_counted():
    fake = _Fake({MF: {20: _line('ESS1', 'Monthly', 12, 0, True), 21: _line('ESM25', 'Quarterly', 4, 0, True, (1, 4, 7, 10)),
                       22: _line('RO2a', 'Half a Year', 2, 0, True, (1, 7), f=0), 23: _line('X1', 'Optional', 3, 0, True, (2, 7, 11), d=3)},
                  CA: {30: _line('RA1.A', 'Monthly', 12, 0, True)}})
    ok, rows, diffs, notes = checks.line_frequency_ties([MF, CA], fake.cell, fake.last_row)
    assert ok and diffs == []
    assert rows[0][1] == 4 and rows[1][1] == 1
    assert 'quarterly 1' in notes[0] and 'optional 1' in notes[0]


def test_a_three_month_quarterly_line_fails():
    fake = _Fake({MF: {21: _line('ESM25', 'Quarterly', 4, 1, True, (1, 4, 7))}, CA: {}})
    ok, _, diffs, _ = checks.line_frequency_ties([MF, CA], fake.cell, fake.last_row)
    assert not ok
    assert any('U (times check)' in d[0] for d in diffs) and any('months of payment' in d[0] for d in diffs)


def test_a_false_total_check_fails():
    fake = _Fake({MF: {21: _line('ESM25', 'Quarterly', 4, 0, False, (1, 4, 7, 10))}, CA: {}})
    ok, _, diffs, _ = checks.line_frequency_ties([MF, CA], fake.cell, fake.last_row)
    assert not ok and diffs[0][0].endswith('V (total check)')


def _sheet4():
    wb = openpyxl.Workbook()
    wb.active.title = '1. Summary'
    for name in (MF, CA, '3.1 Report-Sinking Fund'):
        wb.create_sheet(name)
    items = []
    for n, code in enumerate(('A1', 'A2', 'A3', 'A4', 'A5', 'A6')):
        items.append(dict(code=code, sheet=MF, row=20 + n, name_vi=code, freq='Monthly', months=[100.0] * 12,
                          annual=1200.0, subs=[dict(desc_vi=code, unit_vi='khoản', qty=1, unit_price=1200.0,
                                                    amount=1200.0, qty_editable=False)]))
    items.append(dict(code='Z0', sheet=MF, row=30, name_vi='Z0', freq='Monthly', months=[0.0] * 12, annual=0.0, subs=[]))
    ba.build_sheet(wb, items)
    return wb


def test_edit_plan_takes_five_editable_monthly_lines_and_expected_amounts():
    wb = _sheet4()
    plan = checks.frequency_edit_plan(wb)
    assert [(p[0], p[4], p[5], p[6]) for p in plan] == [
        ('A1', 'Quarterly', 3, None), ('A2', 'Half a Year', 6, None), ('A3', 'Yearly', 12, None),
        ('A4', 'Optional', None, (2, 7, 11)), ('A5', 'Schedule', None, None)]
    expected = checks.apply_frequency_edits(wb, plan)
    assert expected == {'A1': 400.0, 'A2': 200.0, 'A3': 100.0, 'A4': 300.0, 'A5': 600}
    ws = wb[ba.SHEET_NAME]
    r = plan[3][2]
    assert [ws.cell(row=r, column=ba.MONTH_IN_FIRST_COL + k).value for k in range(12)] == [
        'x' if k + 1 in (2, 7, 11) else None for k in range(12)]


def test_edit_ties_pass_on_matching_figures_and_fail_on_a_moved_one():
    wb = _sheet4()
    plan = checks.frequency_edit_plan(wb)
    expected = checks.apply_frequency_edits(wb, plan)
    data = {checks.ADJUSTMENT_SHEET: {}, MF: {}}
    for code, sheet, r, _a, name, first, ticks in plan:
        data[checks.ADJUSTMENT_SHEET][r] = {13: expected[code], 17: 20 + int(code[1]) - 1}
        fr = 20 + int(code[1]) - 1
        months = (list(ticks) if name == 'Optional' else list(range(1, 13)) if name == 'Schedule'
                  else list(range(first, 13, {'Quarterly': 3, 'Half a Year': 6, 'Yearly': 12}[name])))
        times = 12 if name == 'Schedule' else len(months)
        data[MF][fr] = _line(code, name, times, 0, True, months, f=expected[code] / times)
        data[MF][fr][37] = expected[code]
    fake = _Fake(data)
    ok, rows, diffs, notes = checks.frequency_edit_ties(plan, expected, [MF, CA], fake.cell, fake.last_row)
    assert ok and diffs == [] and len(rows) == 5 and 'A1 -> Quarterly' in notes[0]
    data[MF][20][37] = 999
    ok, _, diffs, _ = checks.frequency_edit_ties(plan, expected, [MF, CA], fake.cell, fake.last_row)
    assert not ok and 'year total' in diffs[0][0]
