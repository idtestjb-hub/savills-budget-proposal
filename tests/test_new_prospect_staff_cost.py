"""Unit tests for a new prospect's staff cost (change apply-head-of-pm-decisions-2026-10, group 5).

Covered so far (tasks 5.1-5.2, D6): the calendar working-day count turning a daily rate into a monthly gross on A1
(_new_prospect_monthly_gross, period_workdays), Existing mode keeping 25 days a month (_monthly_gross_of), the
analysis using the same function, A1.1's daily-wage divisor and the input form's default daily rates.

Not covered here: the workbook writers end to end (verify.py runs them on the samples).

Invented data only: fictional positions and rates. Expected values are worked by hand from docs/30 D4 (302 working
days in 2027, paid evenly at 302/12 a month; 252 for a 5-day position) and the template's 25 days (A1.1!E7).
"""
import openpyxl
import pytest

import budget_period
import generate_project_budget as g

P2027 = budget_period.default()


def row(position='Technician (Morning)', staff=1, coverage=6, rate=300_000):
    return {'Position': position, 'StaffPerDay': staff, 'CoverageDays': coverage, 'AvgDailyRate': rate}


def test_a_six_day_position_is_paid_302_twelfths_of_its_daily_rate():
    # 300,000 x 302 / 12 = 7,550,000
    assert g._new_prospect_monthly_gross([row()], P2027) == 7_550_000


def test_a_seven_day_position_counts_six_days_per_person():
    # 7-day coverage: headcount ceil(1 x 7/6) = 2, each still on 302 days.
    assert g._new_prospect_monthly_gross([row(coverage=7)], P2027) == 7_550_000


def test_a_five_day_position_counts_mondays_to_fridays():
    # 300,000 x 252 / 12 = 6,300,000
    assert g._new_prospect_monthly_gross([row(coverage=5)], P2027) == 6_300_000


def test_rows_of_one_position_are_weighted_by_headcount():
    # (1 x 300,000 x 302 + 1 x 360,000 x 252) / 2 / 12 = (90,600,000 + 90,720,000) / 24 = 7,555,000
    rows = [row(rate=300_000, coverage=6), row(rate=360_000, coverage=5)]
    assert g._new_prospect_monthly_gross(rows, P2027) == 7_555_000


def test_an_unstaffed_row_weighs_nothing_even_with_no_coverage_day():
    assert g._new_prospect_monthly_gross([row(staff=0, coverage=0)], P2027) == 0
    assert g._new_prospect_monthly_gross([row(), row(staff=0, coverage=0)], P2027) == 7_550_000


def test_a_staffed_row_with_no_coverage_day_stops_and_names_the_position():
    with pytest.raises(ValueError, match='Accountant'):
        g._new_prospect_monthly_gross([row(position='Accountant', coverage=0)], P2027)


def test_the_count_follows_the_budget_period():
    # A 2026 budget has 303 working days (24/11 not yet in force on 1 January 2026): 300,000 x 303 / 12 = 7,575,000.
    assert g._new_prospect_monthly_gross([row()], budget_period.BudgetPeriod(2026, 1)) == 7_575_000


def test_existing_mode_keeps_25_days_a_month():
    # G2-a: Existing mode's new positions still use the template's 25 days: 300,000 x 25 = 7,500,000.
    assert g._monthly_gross_of([row()]) == 7_500_000


def test_unplaced_positions_use_the_period_count():
    demand = [row(position='Reception', staff=1, coverage=6, rate=340_000)]
    # 340,000 x 302 / 12 = 8,556,666.7 -> 8,556,667
    assert g._unplaced_positions(demand, P2027) == [('Reception', 1, 8_556_667)]


def test_the_analysis_uses_the_same_working_day_function():
    gpo = pytest.importorskip('generate_project_output')
    assert gpo.period_workdays is g.period_workdays


def test_a11_daily_wage_divisor_is_the_count_over_twelve():
    wb = openpyxl.Workbook()
    wb.active.title = g.STAFF_COST_SHEET
    a11 = wb.create_sheet(g.A11_SHEET)
    for r in range(7, 12):
        a11.cell(row=r, column=5, value=25)
    g.fill_staff_cost_sheet(wb, {'budget_period': P2027}, [], 2027)
    assert [a11.cell(row=r, column=5).value for r in range(7, 12)] == ['=302/12'] * 5


def test_input_form_default_daily_rates_use_302_twelfths():
    form = pytest.importorskip('build_project_input_form')
    assert form._WORKDAYS_PER_YEAR == 302
    # Technician: 8,459,141 / (302 / 12) = 336,124 -> 336,000; Accountant: 13,574,175 / 25.1667 = 539,371 -> 539,000.
    rates = {r[0]: r[4] for r in form.EXAMPLE_DEMAND}
    assert rates['Technician (Morning)'] == 336_000
    assert rates['Accountant'] == 539_000
    notes = ' '.join(str(r[5]) for r in form.EXAMPLE_DEMAND if r[5])
    assert '÷ 26' not in notes and '302/12' in notes


# --- task 5.5 (D7 / docs/30 D6): every head reaches A1; extra heads go below the table with the unplaced rows ---
# Template rows per group (read from the 2027 form): PM 1, ACC 1, TN 19. Expected values from the rule, not the code.
ROWS = {'PM': [15], 'ACC': [43], 'TN': list(range(57, 76))}


def test_two_accountants_put_the_second_below_the_table():
    demand = [row(position='Accountant', staff=2, coverage=6, rate=539_000)]
    below = g._new_prospect_below_rows(demand, P2027, ROWS)
    # 539,000 x 302 / 12 = 13,564,833.3 -> 13,564,833
    assert [(code, gross) for _label, code, gross in below] == [('ACC', 13_564_833)]


def test_a_second_property_manager_goes_below_too():
    demand = [row(position='Property Manager', staff=2, coverage=6, rate=1_682_000)]
    below = g._new_prospect_below_rows(demand, P2027, ROWS)
    assert [code for _label, code, _g in below] == ['PM']


def test_unplaced_rows_come_first_then_the_overflow():
    demand = [row(position='Accountant', staff=2, coverage=6, rate=539_000),
              row(position='Reception', staff=1, coverage=6, rate=340_000)]
    below = g._new_prospect_below_rows(demand, P2027, ROWS)
    assert [code for _label, code, _g in below] == ['LT', 'ACC']


def test_heads_within_the_template_rows_stay_in_the_table():
    demand = [row(position='Technician (Morning)', staff=3, coverage=6)]
    assert g._new_prospect_below_rows(demand, P2027, ROWS) == []


def test_a_zero_pay_position_is_flagged_by_name():
    demand = [row(position='Accountant', staff=1, coverage=6, rate=0), row()]
    assert g._zero_pay_positions(demand, P2027) == ['Accountant']
