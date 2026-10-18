"""Unit tests for the analysis's staff cost on A1's components (change apply-head-of-pm-decisions-2026-10, group 5,
task 5.6; D6-b and D7).

Covered: every in-house position of a new prospect falls in exactly one staff category (the four the analysis left out,
and the assistant / supervisor positions split from Property Manager, Chief Engineer and Customer Service); Existing mode
keeps its old categories; A1's per-person extras (team building, training, health check, accident insurance, uniform)
on one in-house and one outsourced position; the employer caps applied per person; the 'Staff (Roster)' writer end to
end on a small invented roster.

Not covered: the recalculated workbook figures (verify.py and the measurement runs cover them).

Invented data only. Rules (docs/30 D6-b, D7; the user's choices of 2026-10-18): new prospects only; extras before the
10% markup from existing_staffing's A1 constants; outsourced Security / Cleaning / Landscape carry none.
"""
import re

import openpyxl
import pytest

import existing_staffing as es
import generate_project_output as gpo

NEW = gpo.NEW_PROSPECT_STAFF_MARKET_KEYWORDS
IN_HOUSE = ['Property Manager', 'Assistant Property Manager', 'Operations Manager', 'Customer Service',
            'Customer Service Supervisor', 'Building Executive', 'Accountant', 'Cashier', 'Chief Engineer',
            'Assistant Chief Engineer', 'Technical Secretary', 'Shift Leader (Night)', 'Technician (Morning)',
            'Reception', 'Amenities Attendant (Morning)', 'Pool Attendant (Afternoon)']
OUTSOURCED = ['Security - Main Gate (Night)', 'Cleaning - Common Area', 'Cleaning - Supervisor', 'Gardener / Landscape']


def categories_of(position, categories=NEW, first_match=True):
    return [k for k in categories if gpo.in_staff_category(position, k, categories, first_match)]


@pytest.mark.parametrize('position', IN_HOUSE)
def test_every_in_house_position_has_exactly_one_category(position):
    assert len(categories_of(position)) == 1


def test_the_split_positions_leave_their_parent_category():
    assert categories_of('Assistant Property Manager') == ['Assistant Property Manager']
    assert categories_of('Assistant Chief Engineer') == ['Assistant Chief Engineer']
    assert categories_of('Customer Service Supervisor') == ['Customer Service Supervisor']
    assert categories_of('Accountant') == ['Accountant']


@pytest.mark.parametrize('position', OUTSOURCED)
def test_outsourced_positions_have_no_staff_category(position):
    assert categories_of(position) == []


def test_existing_mode_keeps_its_old_categories():
    categories, first_match = gpo.staff_market_categories({'existing': object()})
    assert categories is gpo.STAFF_MARKET_KEYWORDS and first_match is False
    assert 'Accountant' not in categories
    # As before: the assistant still sits under Property Manager.
    assert categories_of('Assistant Property Manager', categories, False) == ['Property Manager']


def test_every_new_category_has_a_market_rate_and_a_necessity():
    for name in NEW:
        assert name in gpo.STAFF_MARKET_RATES
        assert name in gpo.STAFF_NECESSITY
    assert gpo.STAFF_NECESSITY['Accountant'][0] == 'Must-Have'
    assert gpo.STAFF_NECESSITY['Cashier'][0] == 'Optional'
    # The split assistants keep the Must-Have of the category they left; the supervisor keeps Optional.
    assert gpo.STAFF_NECESSITY['Assistant Property Manager'][0] == gpo.STAFF_NECESSITY['Property Manager'][0]
    assert gpo.STAFF_NECESSITY['Assistant Chief Engineer'][0] == gpo.STAFF_NECESSITY['Chief Engineer'][0]
    assert gpo.STAFF_NECESSITY['Customer Service Supervisor'][0] == gpo.STAFF_NECESSITY['Customer Service'][0]


def evaluate(formula, b, aa, rate, r=9):
    expr = formula.lstrip('=').replace(f'$B{r}', str(b)).replace(f'$AA{r}', str(aa)).replace(f'$R{r}', str(rate))
    return eval(expr.replace('MAX', 'max'))


def test_an_in_house_technician_carries_the_a1_extras():
    # Spec scenario: 2 Technicians at 325,000 a day over 302 working days; gross 8,179,166.7 a month each.
    team, training, check, accident, uniform = (evaluate(f, 2, 302, 325_000)
                                                for f in gpo.a1_extra_formulas(9, 'Technician (Morning)'))
    gross = 302 / 12 * 325_000
    assert team == 2 * 300_000 * 12
    assert training == pytest.approx(2 * gross * 0.013 * 12)
    assert check == 2 * 1_350_000
    # Accident insurance: base = gross x 30 x 0.00099 + gross x 3 x 0.0044 + 446,985 = 797,871; x 40% / 12 = 26,596,
    # below the 30,000 floor.
    assert accident == 2 * 30_000 * 12
    assert uniform == 2 * 300_000 * 12


def test_the_property_manager_takes_the_pm_rates():
    team, _, _, accident, _ = (evaluate(f, 1, 302, 1_628_000)
                               for f in gpo.a1_extra_formulas(9, 'Property Manager'))
    gross = 302 / 12 * 1_628_000                                        # 40,971,333
    assert team == 1_000_000 * 12
    base = gross * 30 * 0.00099 + gross * 3 * 0.0044 + 446_985
    assert accident == pytest.approx((base + 2_456_000) * 0.58 / 12 * 12)
    assert accident / 12 == pytest.approx(es.a1_accident_monthly('PM', gross))


def test_an_assistant_property_manager_takes_the_other_rates():
    team, *_ = (evaluate(f, 1, 302, 675_000) for f in gpo.a1_extra_formulas(9, 'Assistant Property Manager'))
    assert team == 300_000 * 12


def test_an_outsourced_position_carries_no_extras():
    assert gpo.a1_extra_formulas(9, 'Security - Main Gate (Night)') == [0, 0, 0, 0, 0]


def test_a1_row_cost_is_unchanged_by_the_shared_accident_helper():
    for code, gross in (('PM', 40_971_333), ('TN', 8_179_167), ('ACC', 13_564_833)):
        i = gross
        base = i * 30 * 0.00099 + i * 3 * 0.0044 + 446985
        x = (base + 2456000) * 0.58 / 12 if code == 'PM' else max(30000, base * 0.40 / 12)
        assert es.a1_accident_monthly(code, gross) == x


def roster(position, shift='HC', staff=1, coverage=6, rate=325_000):
    return {'Position': position, 'ShiftCode': shift, 'StaffPerDay': staff, 'CoverageDays': coverage,
            'AvgDailyRate': rate}


def staff_sheet(existing=None):
    demand = [roster('Property Manager', rate=1_628_000), roster('Accountant', staff=2, rate=539_000),
              roster('Customer Service', staff=10, rate=343_000), roster('Security - Main Gate (Night)', 'D', 2, 7)]
    wb = openpyxl.Workbook()
    staff = gpo.build_staff_sheet(wb, {'existing': existing, 'total_gfa': 30_000}, demand, 2027)
    return wb['Staff (Roster)'], staff


def test_the_writer_caps_each_person_and_adds_the_extras_before_the_markup():
    ws, staff = staff_sheet()
    rows = {ws.cell(r, 1).value: r for r in range(7, 12)}
    r = rows['Customer Service']
    assert re.fullmatch(rf'=\$B{r}\*MIN\(\$AA{r}/12\*\$R{r},\d+(\.\d+)?\)\*0\.205\*12', ws.cell(r, 21).value)
    assert ws.cell(r, 24).value.endswith(f'+SUM(AB{r}:AF{r})')
    assert ws.cell(5, 28).value == 'Team Building (A1)'
    assert 'Accountant' in staff['category_annual_cells']
    assert f"'Staff (Roster)'!Z{rows['Accountant']}" in staff['category_annual_cells']['Accountant']


def test_the_writer_leaves_existing_mode_as_it_was():
    ws, staff = staff_sheet(existing=object())
    r = next(r for r in range(7, 12) if ws.cell(r, 1).value == 'Customer Service')
    assert ws.cell(r, 21).value.startswith(f'=MIN(O{r}/12,')
    assert ws.cell(r, 24).value == f'=O{r}+T{r}+U{r}+V{r}+W{r}'
    assert ws.cell(5, 28).value is None
    assert 'Accountant' not in staff['category_annual_cells']
