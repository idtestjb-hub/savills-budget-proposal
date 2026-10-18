"""Contingency lines EM#, ES#, EE# (change apply-head-of-pm-decisions-2026-10, group 6). Invented sheets only: each
mimics the standard form's codes, group totals and rows, so the approved layout check applies."""
import openpyxl
import pytest

import contingency as ct
import generate_project_budget as gpb

LEAF_G = '=IF($C{r}="Schedule",SUM(H{r}:S{r}),F{r}*E{r})'


def _sheet(sheet=ct.FUND_SHEET, extra=None):
    """A fund sheet with the approved rows: group total, one sub-group total, leaves, the contingency line."""
    ws = openpyxl.Workbook().active
    if sheet == ct.FUND_SHEET:
        groups = [('EM', 80, 'EMH', 'EMH1', 131, 'Expenses for management/ Chi phí quản lý'),
                  ('ES', 132, 'ESC', 'ESC1', 221, 'Expenses for Outsource Service/ Chi phí dịch vụ'),
                  ('EE', 227, 'EEW', 'EEW.A', 262, 'Energy Consumption/ Năng lượng')]
        codes = {239: 'EEE.A', 240: 'EEE.C'}
    else:
        groups = [('EM', 41, 'EMH', 'EMH1', 92, 'Expenses for management/ Chi phí quản lý'),
                  ('ES', 93, 'ESC', 'ESC1', 182, 'Expenses for Outsource Service/ Chi phí dịch vụ'),
                  ('EE', 188, 'EEW', 'EEW.A', 223, 'Energy Consumption/ Năng lượng')]
        codes = {200: 'EEE.A', 201: 'EEE.C'}
    codes.update(extra or {})
    for group, head, sub, first_code, cont_row, name in groups:
        ws.cell(row=head, column=25, value=group)
        ws.cell(row=head, column=26, value=name)
        ws.cell(row=head, column=7, value=f'=SUBTOTAL(9,G{head + 1}:G{cont_row})')
        ws.cell(row=head + 1, column=25, value=sub)
        ws.cell(row=head + 1, column=7, value=f'=SUBTOTAL(9,G{head + 2}:G{cont_row - 1})')
        for r in range(head + 2, cont_row + 1):
            ws.cell(row=r, column=7, value=LEAF_G.format(r=r))
            ws.cell(row=r, column=25, value=codes.get(r, f'{group}X{r}'))
        ws.cell(row=head + 2, column=25, value=first_code)
        ws.cell(row=cont_row, column=25, value=group + '#')
        ws.cell(row=cont_row, column=3, value='Monthly')
    return ws


@pytest.mark.parametrize('raw, expected', [
    (None, (0.02, True)), ('', (0.02, True)), ('  ', (0.02, True)),
    (0.015, (0.015, False)), (0, (0.0, False)), (0.1, (0.1, False)),
])
def test_rate_resolves(raw, expected):
    assert ct.resolve_rate(raw) == expected


@pytest.mark.parametrize('raw', ['abc', '2%', -0.01, 0.11, 2, True])
def test_bad_rate_stops_naming_the_field(raw):
    with pytest.raises(ct.ContingencyRateError, match=r'Contingency Rate \(EM#, ES#, EE#\)'):
        ct.resolve_rate(raw)


def test_rate_is_written_clean():
    assert ct.rate_literal(0.02) == '0.02'
    assert ct.rate_literal(0.1 + 0.2 - 0.28) == '0.02'
    assert ct.rate_vi(0.015) == '1,5%'


def test_fund_layout_and_formulas():
    lines = {l['code']: l for l in ct.layout(_sheet(), ct.FUND_SHEET, extra_exclusions={'EEW.A', 'EEE.A'})}
    assert (lines['EM#']['first'], lines['EM#']['last']) == (82, 130)
    assert lines['EM#']['excluded'] == [('EMH1', 82)]
    assert lines['ES#']['excluded'] == []
    assert lines['EE#']['excluded'] == [('EEW.A', 229), ('EEE.A', 239)]
    f = ct.month_formulas(ct.FUND_SHEET, lines['EM#'], 0.02)
    assert f[0] == '=ROUND(0.02*(SUBTOTAL(9,AQ82:AQ130)-AQ82),0)'
    assert f[11] == '=ROUND(0.02*(SUBTOTAL(9,BB82:BB130)-BB82),0)'
    assert ct.month_formulas(ct.FUND_SHEET, lines['ES#'], 0.02)[0] == '=ROUND(0.02*(SUBTOTAL(9,AQ134:AQ220)),0)'


def test_common_area_uses_its_own_rows_and_columns():
    lines = {l['code']: l for l in ct.layout(_sheet(ct.COMMON_SHEET), ct.COMMON_SHEET)}
    assert ct.month_formulas(ct.COMMON_SHEET, lines['EE#'], 0.02)[0] == \
        '=ROUND(0.02*(SUBTOTAL(9,AL190:AL222)-AL190-AL200),0)'
    assert ct.month_formulas(ct.COMMON_SHEET, lines['EE#'], 0.02)[11].startswith('=ROUND(0.02*(SUBTOTAL(9,AW190:AW222)')


def test_the_range_never_reaches_the_line_itself():
    for sheet in (ct.FUND_SHEET, ct.COMMON_SHEET):
        for line in ct.layout(_sheet(sheet), sheet):
            assert line['last'] == line['row'] - 1
            for formula in ct.month_formulas(sheet, line, 0.02):
                assert f"{line['row']})" not in formula and f"{line['row']}-" not in formula


def test_another_paired_line_is_left_out_of_its_group():
    ws = _sheet(extra={250: 'EEX.A'})
    ee = next(l for l in ct.layout(ws, ct.FUND_SHEET, extra_exclusions={'EEX.A', 'RO3.A'}) if l['code'] == 'EE#')
    assert ('EEX.A', 250) in ee['excluded']


def test_a_moved_template_stops_the_run():
    ws = _sheet()
    ws.cell(row=80, column=7, value='=SUBTOTAL(9,G81:G130)')     # group total no longer ends on EM#
    with pytest.raises(ValueError, match='EM total ends on row 130'):
        ct.layout(ws, ct.FUND_SHEET)
    ws = _sheet()
    ws.cell(row=82, column=25, value='EMH2')                       # EMH1 gone
    with pytest.raises(ValueError, match='EMH1'):
        ct.layout(ws, ct.FUND_SHEET)


def test_remark_states_rate_base_exclusions_and_recalculation():
    em = next(l for l in ct.layout(_sheet(), ct.FUND_SHEET) if l['code'] == 'EM#')
    text = ct.remark_vi(em, 0.02, True)
    for part in ('2%', 'Chi phí quản lý', 'EMH1', 'mặc định', ct.LABEL, 'Công thức tự tính lại'):
        assert part in text
    assert 'mặc định' not in ct.remark_vi(em, 0.03, False)
    assert ct.summary_item_vi(em, 0) == f"Dự phòng: để ở mức 0, {ct.ZERO_REASON_VI}"


@pytest.fixture
def no_pairs(monkeypatch):
    monkeypatch.setattr(gpb.operating_inputs, 'cob_pairing', lambda path=None: {'RO3.A': 'EEW.A', 'RO4.A': 'EEE.A'})
    gpb._ZERO_REASONS.clear()
    yield
    gpb._ZERO_REASONS.clear()


def test_writer_puts_live_schedule_formulas(no_pairs):
    ws = _sheet()
    gpb._write_contingency_lines(ws, ct.FUND_SHEET, {'contingency_rate': 0.02, 'contingency_rate_is_default': True})
    for row in (131, 221, 262):
        assert ws.cell(row=row, column=3).value == 'Schedule'
        assert ws.cell(row=row, column=6).value is None
        assert all(str(ws.cell(row=row, column=c).value).startswith('=ROUND(0.02*') for c in range(8, 20))
        assert 'Công thức tự tính lại' in ws.cell(row=row, column=gpb._REMARKS_COL).value
    assert 'EM#' not in gpb._ZERO_REASONS


def test_writer_at_zero_keeps_zero_with_the_reason(no_pairs):
    ws = _sheet()
    gpb._write_contingency_lines(ws, ct.FUND_SHEET, {'contingency_rate': 0.0, 'contingency_rate_is_default': False})
    for row, code in ((131, 'EM#'), (221, 'ES#'), (262, 'EE#')):
        assert ws.cell(row=row, column=8).value is None
        assert ws.cell(row=row, column=gpb._REMARKS_COL).value.startswith(f"Để ở mức 0: {ct.ZERO_REASON_VI}")
        assert gpb._ZERO_REASONS[code] == ct.ZERO_REASON_VI
    # '2.2' writes nothing itself at 0: its lines take the reason from _ZERO_REASONS
    common = _sheet(ct.COMMON_SHEET)
    gpb._write_contingency_lines(common, ct.COMMON_SHEET, {'contingency_rate': 0.0})
    assert common.cell(row=92, column=gpb._REMARKS_COL).value is None


def test_flagged_dicts_no_longer_hold_the_contingency_lines():
    import inspect
    src = inspect.getsource(gpb.fill_management_fund_sheet)
    for code in ('EM#', 'ES#', 'EE#'):
        assert f"('{code}'," not in src and f"'{code}':" not in src


# ---- verification.checks.contingency_ties: the verify check, on an invented evaluated grid ----
def _grid(rate=0.02, tamper=None):
    """{sheet: lines} and a cell(sheet, r, c) reader: every leaf is 100 a month, EMH1/EEW.A/EEE.A 1,000, and each
    contingency month holds the value its formula gives. `tamper(sheet, line, formulas, values)` edits a line."""
    lines_by_sheet, grid = {}, {}
    for sheet in (ct.FUND_SHEET, ct.COMMON_SHEET):
        ws = _sheet(sheet)
        lines = ct.layout(ws, sheet, extra_exclusions={'EEW.A', 'EEE.A'})
        lines_by_sheet[sheet] = lines
        for r in range(1, 300):
            g = ws.cell(row=r, column=7).value
            grid[(sheet, r, 7)] = (None, g)
        for line in lines:
            excl = {r for _c, r in line['excluded']}
            for m in range(12):
                c = ct.MONTH_BASE_COL[sheet] + m
                for r in range(line['first'], line['last'] + 1):
                    grid[(sheet, r, c)] = (1000 if r in excl else 100, None)
            formulas = ct.month_formulas(sheet, line, rate) if rate else [None] * 12
            leaves = range(line['first'], line['last'] + 1)
            leaves = [r for r in leaves if 'SUBTOTAL' not in str(ws.cell(row=r, column=7).value)]
            base = sum(grid[(sheet, r, ct.MONTH_BASE_COL[sheet])][0] for r in leaves) - 1000 * len(excl)
            values = [round(rate * base)] * 12
            if tamper:
                tamper(sheet, line, formulas, values)
            for m in range(12):
                grid[(sheet, line['row'], 8 + m)] = (values[m], formulas[m])
            grid[(sheet, line['row'], 7)] = (sum(values), None)
            grid[(sheet, line['row'], 20)] = (None if rate else f'Để ở mức 0: {ct.ZERO_REASON_VI}', None)
    return lines_by_sheet, lambda sheet, r, c: grid.get((sheet, r, c), (None, None))


def test_verify_check_passes_on_the_rule():
    from verification.checks import contingency_ties
    lines, cell = _grid()
    ok, rows, diffs, _notes = contingency_ties(lines, cell, dict(rate=0.02, bases={'Must-Have': (200, 6000, 4000)}))
    assert ok, diffs
    assert len(rows) == 6 + 1 + 2


def test_verify_check_fails_when_a_line_reaches_itself():
    from verification.checks import contingency_ties

    def reach(sheet, line, formulas, values):
        if sheet == ct.FUND_SHEET and line['code'] == 'ES#':
            formulas[3] = formulas[3].replace(f":AT{line['last']}", f":AT{line['row']}")
    lines, cell = _grid(tamper=reach)
    ok, _rows, diffs, _n = contingency_ties(lines, cell)
    assert not ok and any('reaches the line itself' in d[1] for d in diffs)


def test_verify_check_fails_on_a_wrong_month_or_a_second_rate():
    from verification.checks import contingency_ties

    def off(sheet, line, formulas, values):
        if line['code'] == 'EE#' and sheet == ct.COMMON_SHEET:
            values[5] += 7
    lines, cell = _grid(tamper=off)
    ok, _r, diffs, _n = contingency_ties(lines, cell)
    assert not ok and any('month 6' in d[1] for d in diffs)
    lines, cell = _grid()
    ok, _r, diffs, _n = contingency_ties(lines, cell, dict(rate=0.03, bases={}))
    assert not ok and diffs[0][0].startswith('the analysis uses')


def test_verify_check_at_rate_zero():
    from verification.checks import contingency_ties
    lines, cell = _grid(rate=0)
    ok, _r, diffs, notes = contingency_ties(lines, cell)
    assert ok, diffs
    assert notes[0].startswith('contingency rate 0 ')
