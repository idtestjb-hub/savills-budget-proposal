"""Unit tests for Existing-project mode (change carry-forward-staffing).

Covered: reading the mode and the Prior-Year Roster by label (task 2.3), source priority and A1 overflow (3.1),
the A1 replica and the minimum-wage floor (3.2), the holiday allowance (3.3), EMH4 (3.4), reason records (5.1),
the adjustment sentence (5.2), the two verification checks and run.py's report (7.1), and an invented
multi-region case with a headcount change (8.3).

Invented data only: positions, salaries and amounts are made up. The labour-law values come from the public law
table (Ref_LaborLawParams.csv), the same exception test_labor_law_params.py documents. Two A1 row costs below were
read from a deliverable that Excel recalculated (2026-10-10, invented fixture): they pin the Python replica to the
template's own formulas.
"""
import openpyxl
import pytest

import build_project_input_form as bpf
import existing_staffing as es
import generate_project_budget as g
from input_labels import LabelNotFound, SheetLabels


# ---------------------------------------------------------------- helpers
def _form(mode=es.MODE_EXISTING, region='II', prior=2026, roster=(), duty=(), lines=None):
    """An in-memory input workbook carrying the Existing-project fields, filled with invented data."""
    wb = openpyxl.Workbook()
    pi = wb.active
    pi.title = 'Project Info'
    pi['A1'] = 'Project Name'
    pi['B1'] = 'ZZ Test (TEST DATA)'
    bpf.add_existing_project_fields(pi, 3)
    labels = {pi.cell(row=r, column=1).value: r for r in range(1, 10) if pi.cell(row=r, column=1).value}
    for label, value in labels.items():
        if label == es.MODE_LABEL:
            pi.cell(row=value, column=2, value=mode)
        elif str(label).startswith(es.REGION_LABEL):
            pi.cell(row=value, column=2, value=region)
        elif str(label).startswith(es.PRIOR_YEAR_LABEL):
            pi.cell(row=value, column=2, value=prior)
    ws = bpf.add_prior_year_roster_sheet(wb)

    def first_row(title):
        return next(r for r in range(1, ws.max_row + 1)
                    if es.normalise(ws.cell(row=r, column=1).value) == es.normalise(title)) + 2
    r = first_row(es.SEC_ROSTER)
    for i, row in enumerate(roster):
        for c, v in enumerate(row, 1):
            ws.cell(row=r + i, column=c, value=v)
    r = first_row(es.SEC_DUTY)
    for i in range(len(es.DUTY_CODES)):
        code = ws.cell(row=r + i, column=1).value
        for c, v in enumerate(dict(duty).get(code, ()), 2):
            ws.cell(row=r + i, column=c, value=v)
    r = first_row(es.SEC_LINES)
    for i in range(len(es.STAFF_LINES)):
        line = ws.cell(row=r + i, column=1).value
        for c, v in enumerate((lines or {}).get(line, ()), 2):
            ws.cell(row=r + i, column=c, value=v)
    return wb


def _read(wb):
    return es.read_existing(wb, SheetLabels(wb['Project Info']))


def _demand(position, code='HC', staff=1, days=6, rate=400_000, basis='PM-entered value', reason=None):
    return dict(Position=position, ShiftCode=code, StaffPerDay=staff, CoverageDays=days, AvgDailyRate=rate,
                SourceRow=5, Basis=basis, ReasonCode=reason, ReasonNote=None)


def _compute(ex, demand=(), budget_year=2027):
    return es.compute(ex, list(demand), budget_year, g._a1_group_of, g._is_outsourced, g._unplaced_code_of,
                      g._eff_headcount, g._monthly_gross_of)


# ---------------------------------------------------------------- 2.3 reading
def test_a_workbook_without_the_fields_is_a_new_prospect():
    wb = openpyxl.Workbook()
    wb.active.title = 'Project Info'
    wb.active['A1'] = 'Project Name'
    assert es.read_existing(wb, SheetLabels(wb.active)) is None


def test_blank_mode_and_new_prospect_read_as_new_prospect():
    assert _read(_form(mode=None)) is None
    assert _read(_form(mode=es.MODE_NEW)) is None


def test_an_unknown_mode_stops_and_names_the_field():
    with pytest.raises(ValueError, match="'Project Mode'.*'New prospect', 'Existing project'"):
        _read(_form(mode='Renewal'))


def test_roster_only_is_read():
    ex = _read(_form(roster=[('Technician', 'S', 2, 9_000_000)]))
    assert ex.region == 'II' and ex.prior_year == 2026
    assert [(r.position, r.heads, r.gross, r.year) for r in ex.roster] == [('Technician', 2, 9_000_000, 2026)]


def test_lump_sum_only_is_read():
    ex = _read(_form(lines={'EMH2': (1_200_000_000,)}))
    assert ex.roster == [] and ex.lines['EMH2'].approved == 1_200_000_000


def test_neither_roster_nor_approved_amount_stops_naming_both():
    with pytest.raises(ValueError, match="PRIOR-YEAR ROSTER.*STAFF LINES"):
        _read(_form())


def test_a_renamed_block_title_stops_and_names_it():
    wb = _form(roster=[('Technician', 'S', 2, 9_000_000)])
    ws = wb[es.ROSTER_SHEET]
    row = next(r for r in range(1, ws.max_row + 1) if ws.cell(row=r, column=1).value == es.SEC_DUTY)
    ws.cell(row=row, column=1, value='NIGHT DUTY')
    with pytest.raises(LabelNotFound, match=es.SEC_DUTY):
        _read(wb)


def test_a_gap_in_the_roster_does_not_hide_the_rows_below_it():
    wb = _form(roster=[('Technician', 'S', 2, 9_000_000), (None,), (None,), ('Accountant', 'HC', 1, 15_000_000)])
    assert [r.position for r in _read(wb).roster] == ['Technician', 'Accountant']


# ---------------------------------------------------------------- 3.1 source priority, 3.2 replica and floor
def test_rostered_code_ignores_staffing_demand_and_new_positions_are_labelled():
    ex = _read(_form(roster=[('Technician', 'S', 3, 9_000_000)]))
    demand = [_demand('Technician (Morning)', staff=5, days=7),           # covered: ignored
              _demand('Reception', staff=1, days=6, rate=340_000, reason='Theo yêu cầu của cư dân hoặc chủ sở hữu'),
              _demand('Pool Attendant (Morning)', staff=1, days=6, rate=276_000, basis='ratio = 1.20, rounded up'),
              _demand('Security - Main Gate (Morning)', staff=4, days=7)]  # outsourced: never on A1
    res = _compute(ex, demand)
    by_origin = {}
    for p in res.persons:
        by_origin.setdefault((p.label, p.origin), 0)
        by_origin[(p.label, p.origin)] += 1
    assert by_origin == {('Technician', 'roster'): 3, ('Reception', 'new-typed'): 1,
                         ('Pool Attendant (Morning)', 'new-ratio'): 1}
    ratio = next(p for p in res.persons if p.origin == 'new-ratio')
    assert ratio.note.startswith('ước tính')
    missing = es.missing_reasons(res.reason_rows)
    assert [r['item'] for r in missing] == ['A1: Pool Attendant (Morning) (vị trí mới)']


def test_more_heads_than_template_rows_go_below_the_table():
    ex = _read(_form(roster=[('Building Executive', 'HC', 8, 12_000_000)]))
    res = _compute(ex)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = g.STAFF_COST_SHEET
    for r in range(18, 24):                       # the template's six BE rows
        ws.cell(row=r, column=4, value='BE')
    placed, below = g._existing_a1_layout(wb, res)
    assert sorted(placed) == list(range(18, 24))
    assert len(below) == 2 and all(p.code == 'BE' for p in below)


def test_a1_replica_matches_excel_on_two_rows():
    p = {'I4': 2_530_000, 'I5': 4_730_000, 'cap_si_hi': 2_530_000 * 20, 'cap_ui': 4_730_000 * 20,
         'T8': 0.205, 'U8': 0.01, 'V8': 0.02, 'AB1': 0.1}
    assert es.a1_row_cost('BE', 12_000_000, p) == 18_392_616     # read from Excel, invented fixture
    assert es.a1_row_cost('LT', 8_500_000, p) == 13_264_716


def test_salary_below_the_floor_is_raised_with_an_automatic_reason():
    ex = _read(_form(region='II', roster=[('Customer Service', 'HC', 2, 4_500_000)]))
    res = _compute(ex)
    assert {p.gross for p in res.persons} == {4_730_000}          # Region II, 2027
    floor = [r for r in res.reason_rows if 'lương tối thiểu' in r['item']]
    assert floor and floor[0]['source'] == es.SOURCE_TOOL and es.REASON_MIN_WAGE in floor[0]['text']
    assert res.lines['EMH2'].law > 0 and not es.missing_reasons(res.reason_rows)


def test_a_salary_above_the_floor_is_not_changed_by_law():
    ex = _read(_form(region='I', roster=[('Chief Engineer', 'HC', 1, 30_000_000)]))
    res = _compute(ex)
    assert res.persons[0].gross == 30_000_000
    assert res.reason_rows == []          # 2026 and 2027 law values are the same below the ceiling


# ---------------------------------------------------------------- 3.3 holiday allowance
def test_one_more_paid_holiday_raises_emh3_by_that_day_and_names_it():
    ex = _read(_form(region='I', lines={'EMH2': (1_000_000_000,)}, duty=[('TN', (0, 0, 2, 9_000_000))]))
    res = _compute(ex)
    emh3 = res.lines['EMH3']
    assert emh3.baseline == 12 * 1_980_000                      # 11 days x 2 staff x 9,000,000/25 x 300%
    assert emh3.budget - emh3.baseline == 2 * 9_000_000 / 25 * 3  # one more day
    assert 'Ngày Văn hóa Việt Nam (24/11)' in emh3.reasons[0]['text']
    assert res.a11_days == (353, 12, 12)


def test_empty_duty_block_carries_the_approved_emh3():
    ex = _read(_form(lines={'EMH2': (1_000_000_000,), 'EMH3': (24_000_000,)}))
    res = _compute(ex)
    assert res.lines['EMH3'].budget == 24_000_000 and res.lines['EMH3'].reasons == []
    # Task 5.7 (change apply-head-of-pm-decisions-2026-10): the empty table is flagged, not filled.
    assert res.duty == []
    assert any(n.startswith(es.BLANK_DUTY_TEXT) and 'giữ số đã duyệt NS 2026' in n for n in res.notes)


def test_empty_duty_block_without_an_approved_emh3_is_flagged_and_left_at_zero():
    ex = _read(_form(lines={'EMH2': (1_000_000_000,)}))
    # A night shift in Staffing Demand must not be turned into duty counts.
    res = _compute(ex, [_demand('Technician (Night)', code='D', staff=2, days=7)])
    assert res.lines['EMH3'].kind == 'none' and res.lines['EMH3'].budget == 0
    assert res.duty == []
    assert any(n.startswith(es.BLANK_DUTY_TEXT) and 'không có số trực' in n for n in res.notes)


# ---------------------------------------------------------------- 3.4 EMH4
def test_emh4_follows_the_regional_minimum_wage():
    ex = _read(_form(region='I', prior=2025, lines={'EMH2': (1_000_000_000,), 'EMH4': (10_000_000,)}))
    res = _compute(ex, budget_year=2026)
    assert res.lines['EMH4'].budget == round(10_000_000 * 5_310_000 / 4_960_000)
    assert es.REASON_MIN_WAGE in res.lines['EMH4'].reasons[0]['text']


def test_emh4_zero_stays_zero_and_blank_uses_the_template():
    zero = _compute(_read(_form(lines={'EMH2': (1_000_000_000,), 'EMH4': (0,)})))
    assert zero.lines['EMH4'].budget == 0 and zero.lines['EMH4'].reasons == []
    blank = _compute(_read(_form(lines={'EMH2': (1_000_000_000,)})))
    assert blank.emh4_from_a5 and blank.lines['EMH4'].budget == pytest.approx(es.a5_template_annual())


# ---------------------------------------------------------------- lump sum and overrides
def test_lump_sum_is_carried_and_an_override_needs_its_reason():
    ex = _read(_form(lines={'EMH2': (1_200_000_000, 1_260_000_000, 'Thay đổi quy định pháp luật')}))
    res = _compute(ex)
    emh2 = res.lines['EMH2']
    assert res.kind == 'lump' and emh2.baseline == 1_200_000_000 and emh2.budget == 1_260_000_000
    assert emh2.override == 60_000_000 and not es.missing_reasons(res.reason_rows)
    sentence = es.adjustment_sentence(res, 'EMH2')
    assert 'Điều chỉnh so với NS 2026: 1,200,000,000 → 1,260,000,000' in sentence
    assert 'Thay đổi quy định pháp luật' in sentence


def test_an_override_without_a_reason_is_missing():
    res = _compute(_read(_form(lines={'EMH2': (1_200_000_000, 1_260_000_000)})))
    assert [r['status'] for r in es.missing_reasons(res.reason_rows)] == [es.MISSING]


# ---------------------------------------------------------------- 5.1 reason records, 5.2 sentence
@pytest.mark.parametrize('code', [c for c in es.REASON_CODES if c != es.REASON_OTHER])
def test_each_approved_code_is_a_complete_reason(code):
    assert es.pm_reason(code, '')['status'] == ''


def test_other_needs_a_note_and_unknown_codes_are_refused():
    assert es.pm_reason(es.REASON_OTHER, '')['status'] == es.MISSING_NOTE
    assert es.pm_reason(es.REASON_OTHER, 'Lên bậc lương')['status'] == ''
    assert es.pm_reason('Tăng lương', '')['status'] == es.UNKNOWN_CODE
    assert es.pm_reason('', '')['status'] == es.MISSING


def test_an_unchanged_line_gets_no_sentence():
    res = _compute(_read(_form(lines={'EMH2': (1_200_000_000,)})))
    assert es.adjustment_sentence(res, 'EMH2') == ''


# ---------------------------------------------------------------- 9.2 detail rows (design D15)
def _on_sheet(lr):
    """What the detail sheet computes itself, before the added rows."""
    return 0 if lr.kind in ('lump', 'carried') else lr.computed


def _ties(res):
    rows = es.detail_rows(res)
    for line, lr in res.lines.items():
        assert _on_sheet(lr) + sum(r['annual'] for r in rows[line]) == pytest.approx(lr.budget, abs=1e-6), line
    return rows


def test_lump_sum_with_override_gets_a_carried_and_an_adjustment_row():
    res = _compute(_read(_form(lines={'EMH2': (1_200_000_000, 1_260_000_000, 'Thay đổi quy định pháp luật')})))
    rows = _ties(res)['EMH2']
    assert [(r['label'], r['annual']) for r in rows] == [('EMH2 đã duyệt NS 2026 mang sang', 1_200_000_000),
                                                         (es.LABEL_PM_ADJUST, 60_000_000)]
    assert rows[1]['note'] == 'Thay đổi quy định pháp luật'


def test_carried_emh3_with_override_and_zero_emh4():
    res = _compute(_read(_form(lines={'EMH2': (1_000_000_000,),
                                      'EMH3': (24_000_000, 25_200_000, es.REASON_OTHER, 'Thêm ca trực Tết'),
                                      'EMH4': (0,)})))
    rows = _ties(res)
    assert [r['annual'] for r in rows['EMH3']] == [24_000_000, 1_200_000]
    assert rows['EMH3'][1]['note'] == 'Thêm ca trực Tết'
    assert [(r['label'], r['annual']) for r in rows['EMH4']] == [('EMH4 đã duyệt NS 2026 mang sang', 0)]


def test_carried_emh4_gets_a_minimum_wage_row_when_the_ratio_moves_it():
    res = _compute(_read(_form(region='I', prior=2025, lines={'EMH2': (1_000_000_000,), 'EMH4': (10_000_000,)})),
                   budget_year=2026)
    rows = _ties(res)['EMH4']
    assert [r['label'] for r in rows] == ['EMH4 đã duyệt NS 2025 mang sang', 'Điều chỉnh theo lương tối thiểu vùng']
    assert es.REASON_MIN_WAGE in rows[1]['note']


def test_lines_computed_on_their_sheet_get_no_row():
    res = _compute(_read(_form(roster=[('Technician', 'S', 2, 9_000_000)],
                               duty=[('TN', (0, 0, 2, 9_000_000))])))
    assert _ties(res) == {'EMH2': [], 'EMH3': [], 'EMH4': []}


def test_a1_rows_follow_the_overflow_rows():
    res = _compute(_read(_form(lines={'EMH2': (1_200_000_000, 1_260_000_000, 'Thay đổi quy định pháp luật')})))
    at = g._existing_detail_layout(res, ({}, ['overflow 1', 'overflow 2']))
    assert [r for r, _ in at['EMH2']] == [100, 101] and at['a1_last'] == 101
    assert at['a11_total'] is None and at['a5_total'] is None


# ---------------------------------------------------------------- 8.3 invented multi-region case
def test_region_iii_floor_and_a_headcount_change_with_reason():
    ex = _read(_form(region='III', roster=[
        ('Technician', 'S', 4, 4_000_000, 2026, 5, None, 'Bàn giao hoặc bổ sung khu vực quản lý', 'Khu C'),
        ('Accountant', 'HC', 1, 15_000_000)]))
    res = _compute(ex)
    techs = [p for p in res.persons if p.label == 'Technician']
    assert len(techs) == 5 and {p.gross for p in techs} == {4_140_000}     # Region III, 2027
    emh2 = res.lines['EMH2']
    assert emh2.law > 0 and emh2.headcount > 0
    assert abs(emh2.baseline + emh2.law + emh2.headcount - emh2.budget) < 1e-6
    assert not es.missing_reasons(res.reason_rows)


# ---------------------------------------------------------------- 7.1 the checks and run.py
def _analysis_with_reasons(tmp_path, records, name='analysis.xlsx'):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = es.BRIDGE_SHEET
    ws['A10'] = 'Step'
    for c, h in enumerate(['Step', 'EMH2', 'EMH3', 'EMH4'], 1):
        ws.cell(row=10, column=c, value=h)
    for c, v in enumerate([es.BRIDGE_TOTAL_LABEL, 100.0, 20.0, 5.0], 1):
        ws.cell(row=11, column=c, value=v)
    ws['A20'] = es.REASONS_TITLE
    for c, h in enumerate(es.REASON_HEADERS, 1):
        ws.cell(row=21, column=c, value=h)
    for i, rec in enumerate(records):
        for c, v in enumerate(rec, 1):
            ws.cell(row=22 + i, column=c, value=v)
    path = tmp_path / name
    wb.save(path)
    return str(path)


GOOD = ('EMH2', 'A1: Technician', '4 × 9,000,000', '5 × 9,000,000', 100.0,
        'Bàn giao hoặc bổ sung khu vực quản lý', '', 'Bàn giao hoặc bổ sung khu vực quản lý', 'PM', 'OK')


def test_reason_check_passes_on_good_records(tmp_path):
    from verification.checks import check_staffing_reasons
    ok, rows, problems, _ = check_staffing_reasons(_analysis_with_reasons(tmp_path, [GOOD]))
    assert ok and len(rows) == 1 and not problems


@pytest.mark.parametrize('broken, message', [
    (GOOD[:5] + ('', '', '', 'PM', 'OK'), 'no reason'),
    (GOOD[:5] + (es.REASON_OTHER, '', 'Khác', 'PM', 'OK'), 'Khác'),
    (GOOD[:5] + ('Tăng lương', '', 'Tăng lương', 'PM', 'OK'), 'not on the approved list'),
])
def test_reason_check_fails_and_names_the_line(tmp_path, broken, message):
    from verification.checks import check_staffing_reasons
    ok, _rows, problems, _ = check_staffing_reasons(_analysis_with_reasons(tmp_path, [GOOD, broken]))
    assert not ok and len(problems) == 1
    assert 'A1: Technician' in problems[0][0] and message in problems[0][1]


def test_bridge_check_ties_and_fails_on_a_gap(tmp_path):
    from verification.checks import check_staff_bridge
    analysis = _analysis_with_reasons(tmp_path, [GOOD])
    deliverable = tmp_path / 'deliverable.xlsx'
    openpyxl.Workbook().save(deliverable)
    paths = {'analysis': analysis, 'deliverable': str(deliverable)}
    ok, *_ = check_staff_bridge(paths, True, deliverable_values={'EMH2': 100.0, 'EMH3': 20.0, 'EMH4': 5.0})
    assert ok
    ok, _rows, diffs, _ = check_staff_bridge(paths, True, deliverable_values={'EMH2': 90.0, 'EMH3': 20.0, 'EMH4': 5.0})
    assert not ok and diffs[0][0] == 'Staff Bridge EMH2 = deliverable EMH2'
    ok, _rows, diffs, _ = check_staff_bridge(paths, False)
    assert not ok and diffs[0][0] == 'New-prospect run produces no Staff Bridge'


def _detail_cells(emh2_f="=('A1. Staff cost 08.2026 (VN)'!AC96-'A1. Staff cost 08.2026 (VN)'!AC90"
                         "*'A1. Staff cost 08.2026 (VN)'!AC95+SUM('A1. Staff cost 08.2026 (VN)'!AC98:AC99)*12)/12"):
    """A lump-sum deliverable as Excel would read it back: invented figures, VND."""
    a1, a11, a5, fund = ('A1. Staff cost 08.2026 (VN)', 'A1.1 Allowance (From 08.2026)', 'A5. Trợ cấp PCCC',
                         '2. Budget-Management Fund')
    cells = {
        (a1, 96, 29): (24_000, '=AC93*AC95'), (a1, 90, 29): (2_000, "='A1.1'!S13"), (a1, 95, 29): (12, None),
        (a1, 98, 29): (100_000, None), (a1, 99, 29): (5_000, None),
        (a11, 13, 19): (2_000, '=ROUND(S12/$F$13,0)'), (a11, 15, 19): (1_200, None), (a11, 15, 20): (100, '=S15/$T$2'),
        (a11, 16, 20): (2_100, '=S13+SUM(T15:T15)'),
        (a5, 8, 8): (0, '=SUM(H5:H7)'), (a5, 10, 8): (0, None), (a5, 11, 8): (0, '=H8+SUM(H10:H10)'),
        (fund, 83, 6): (105_000, emh2_f), (fund, 83, 7): (1_260_000, '=F83*E83'),
        (fund, 84, 6): (2_100, "='A1.1 Allowance (From 08.2026)'!T16"), (fund, 84, 7): (25_200, '=F84*E84'),
        (fund, 85, 6): (0, "='A5. Trợ cấp PCCC'!H11/12"), (fund, 85, 7): (0, '=F85*E85'),
    }
    if not emh2_f.startswith('='):
        cells[(fund, 83, 6)] = (105_000, None)
    return lambda sheet, r, c: cells.get((sheet, r, c), (None, None))


def test_detail_tie_check_passes_and_fails_on_a_typed_line():
    from verification.checks import existing_detail_ties
    rows = {'EMH2': 83, 'EMH3': 84, 'EMH4': 85}
    ok, checked, diffs, _ = existing_detail_ties(_detail_cells(), rows)
    assert ok and len(checked) == 3, diffs
    ok, _checked, diffs, _ = existing_detail_ties(_detail_cells(emh2_f='105000'), rows)
    assert not ok and 'EMH2' in diffs[0][0] and 'typed amount' in diffs[0][1]


def test_run_reports_a_missing_reason(tmp_path, capsys):
    import run
    bad = _analysis_with_reasons(tmp_path, [GOOD[:5] + ('', '', '', 'PM', 'OK')])
    assert run._report_staffing_reasons(bad) == 1
    assert 'A1: Technician' in capsys.readouterr().out
    assert run._report_staffing_reasons(_analysis_with_reasons(tmp_path, [GOOD], 'good.xlsx')) == 0
