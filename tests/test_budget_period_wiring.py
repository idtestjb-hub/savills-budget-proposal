"""Budget period wired into the readers and the month-dated rules (change apply-head-of-pm-decisions-2026-10, 1.1, 1.3).

Invented data only (the sample fixture is synthetic; the tariff table is the one test_existing_utilities.py invents).
"""
import datetime
import os
import shutil

import openpyxl
import pytest

import budget_period as bp
import existing_staffing as es
import existing_utilities as eu
import generate_project_budget as gpb
import vn_holidays as vh

import test_existing_utilities as teu
from test_existing_utilities import _both, _form, rows  # noqa: F401  (rows is a fixture)

FIXTURE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'verification', 'fixtures', 'Sample_Project_Input.xlsx')


# ---------------------------------------------------------------- 1.1 the input field
def _copy_with(tmp_path, start=None, add_field=True, roster_blank=False):
    wb = openpyxl.load_workbook(FIXTURE)
    pi = wb['Project Info']
    if add_field:
        r = pi.max_row + 2
        pi.cell(row=r, column=1, value=bp.LABEL)
        pi.cell(row=r, column=2, value=start)
    if roster_blank:
        rs = wb['Roster Setup']
        for r in range(1, 40):
            label = str(rs.cell(row=r, column=1).value or '')
            if label.startswith('Month (1-12)') or label == 'Year':
                rs.cell(row=r, column=2).value = None
    path = tmp_path / 'input.xlsx'
    wb.save(path)
    return str(path)


def test_a_form_without_the_field_reads_as_january_2027(tmp_path):
    project = gpb.read_input(_copy_with(tmp_path, add_field=False))[0]
    assert project['budget_period'].is_default


def test_a_blank_field_reads_as_january_2027(tmp_path):
    assert gpb.read_input(_copy_with(tmp_path, start=None))[0]['budget_period'].is_default


def test_a_valid_month_is_read(tmp_path):
    p = gpb.read_input(_copy_with(tmp_path, start='07/2027'))[0]['budget_period']
    assert (p.start_year, p.start_month) == (2027, 7)


def test_an_invalid_month_stops_and_names_the_field(tmp_path):
    with pytest.raises(bp.BudgetPeriodError, match="'Budget Start Month'"):
        gpb.read_input(_copy_with(tmp_path, start='next summer'))


def test_the_form_builder_carries_the_field_with_a_january_2027_default(tmp_path, monkeypatch):
    import build_project_input_form as bpf
    reports = tmp_path / 'reports'
    reports.mkdir()
    monkeypatch.setattr(bpf, 'OUT_DIR', str(reports))
    monkeypatch.setattr(bpf, 'FINAL_OUT', str(reports / 'Project_Budget_Input.xlsx'))
    monkeypatch.setattr(bpf, 'OUT', str(tmp_path / 'scratch.xlsx'))
    bpf.main(force=False)
    ws = openpyxl.load_workbook(reports / 'Project_Budget_Input.xlsx')['Project Info']
    hit = [r for r in range(1, ws.max_row + 1) if ws.cell(row=r, column=1).value == bp.LABEL]
    assert len(hit) == 1
    assert bp.from_value(ws.cell(row=hit[0], column=2).value).is_default
    assert ws.cell(row=hit[0], column=2).number_format == 'mm/yyyy'


def test_roster_month_defaults_to_the_budgets_first_month_when_both_blank(tmp_path):
    _p, _r, month, year, _h, _d = gpb.read_input(_copy_with(tmp_path, start='07/2027', roster_blank=True))
    assert (year, month) == (2027, 7)


def test_roster_month_as_entered_is_kept(tmp_path):
    _p, _r, month, year, _h, _d = gpb.read_input(_copy_with(tmp_path, start='07/2027'))
    wb = openpyxl.load_workbook(FIXTURE, data_only=True)['Roster Setup']
    entered = {str(wb.cell(row=r, column=1).value or ''): wb.cell(row=r, column=2).value for r in range(1, 40)}
    assert (year, month) == (int(entered['Year']), int(next(v for k, v in entered.items() if k.startswith('Month'))))


# ---------------------------------------------------------------- 1.3 month-dated rules
@pytest.mark.parametrize('year', [2026, 2027, 2028, 2029, 2030])
def test_a_calendar_year_period_has_the_same_holidays_as_the_year(year):
    assert vh.paid_holidays_in_period(datetime.date(year, 1, 1), datetime.date(year, 12, 31)) == vh.paid_holidays(year)


def test_a_straddling_period_joins_the_two_calendars():
    p = bp.from_value('07/2027')
    got = vh.paid_holidays_in_period(p.first_day, p.last_day)
    law_day = p.first_day
    want = sorted([(d, n) for d, n in vh.paid_holidays(2027, as_of=law_day) if d >= p.first_day] +
                  [(d, n) for d, n in vh.paid_holidays(2028, as_of=law_day) if d <= p.last_day])
    assert got == want
    assert all(p.first_day <= d <= p.last_day for d, _ in got)
    assert datetime.date(2027, 11, 24) in [d for d, _ in got]          # Culture Day, in force from 01/07/2026


def test_the_default_period_gives_the_same_holiday_allowance_as_the_budget_year():
    duty = [es.DutyRow('SG', 1, 1, 1, 8_000_000, '', 1)] if hasattr(es, 'DutyRow') else None
    if duty is None:
        pytest.skip('no DutyRow')
    assert es.a11_monthly(duty, bp.default()) == es.a11_monthly(duty, 2027)
    assert es.period_days(bp.default()) == es.year_days(2027) == 365


def test_a_july_period_counts_its_own_days_and_holidays():
    p = bp.from_value('07/2027')
    assert es.period_days(p) == 366                     # 01/07/2027 to 30/06/2028 includes 29/02/2028
    assert len(es.vh_paid(p)) == len(vh.paid_holidays_in_period(p.first_day, p.last_day))


def test_utility_prices_follow_the_period_months(rows):
    # Budget July 2026 to June 2027 on the invented table: VAT 8% to 31/12/2026, 10% from 01/01/2027.
    acts = _both(n=12, start=(2025, 3))                 # ends 02/2026, before the period starts
    wb = _form(prior=2025, actuals=acts)
    period = bp.from_value('07/2026')
    res = eu.compute(teu._read(wb), 2026, True, rows=rows, months=period.months)
    e = res.lines['EEE.C']
    six8, six10 = round(20_000 * teu.E_2026_INCL), round(20_000 * teu.E_2027_INCL)
    assert e.amounts == [six8] * 6 + [six10] * 6
    assert res.lines['EEW.C'].amounts == [round(1_000 * teu.W_2026_INCL)] * 6 + [round(1_000 * teu.W_2027_INCL)] * 6


def test_the_default_period_equals_the_calendar_year_computation(rows):
    wb = _form(actuals=_both())
    a = eu.compute(teu._read(wb), 2027, True, rows=rows)
    b = eu.compute(teu._read(wb), 2027, True, rows=rows, months=bp.default().months)
    for line in a.lines:
        assert a.lines[line].amounts == b.lines[line].amounts
        assert a.lines[line].annual == b.lines[line].annual


def test_a_month_in_or_after_the_period_stops_naming_the_period(rows):
    acts = _both(n=12, start=(2025, 3)) + [('EEE.C', '07/2026', 5, 'Yes', None)]
    wb = _form(prior=2025, actuals=acts)
    with pytest.raises(ValueError, match='the budget period starting 07/2026'):
        eu.compute(teu._read(wb), 2026, True, rows=rows, months=bp.from_value('07/2026').months)


def test_utilities_result_passes_the_projects_period(rows, monkeypatch):
    seen = {}
    monkeypatch.setattr(eu, 'compute', lambda inp, by, incl, rows=None, months=None: seen.update(by=by, months=months))
    gpb.utilities_result({'utilities': object(), 'budget_period': bp.from_value('07/2027')}, 2027, True)
    assert seen['months'] == bp.from_value('07/2027').months
