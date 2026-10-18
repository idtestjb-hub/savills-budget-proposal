"""Unit tests for a new prospect's holiday and night allowance on A1.1 (change apply-head-of-pm-decisions-2026-10,
group 5, task 5.3; D5).

Covered: which positions get A1.1 counts (_new_prospect_duty), the A1.1 monthly total on the calendar day count
(existing_staffing.a11_monthly with a working-day divisor), and the detail-sheet tie that catches a double count
(checks.existing_detail_ties).

Not covered: the workbook writer end to end (verify.py runs it on the standard sample).

Invented data only. Rules (docs/30 B2 + D5, the user's choices of 2026-10-18):
 - holiday work at 300% only for a position on 7-day coverage that has a night shift (D or 24H); its holiday day staff
   = the staff per day of every shift that is not a night shift (morning + afternoon), 24H staff included;
 - night work at 30% (non-holiday nights) and 390% (holiday nights): the staff per day on D and 24H shifts, for any
   position with a night shift;
 - outsourced Security / Cleaning / Landscape are not on A1.1.
Expected amounts are worked by hand from A1.1's own formulas (F = D / E, J = 30% x H x F, N = 390% x L x F,
R = 300% x P x F, S13 = ROUND(S12 / 12)) with 2027's 353 non-holiday days and 12 holidays.
"""
import pytest

import budget_period
import existing_staffing as es
import generate_project_budget as g

P2027 = budget_period.default()


def row(position, shift, staff=1, coverage=7, rate=325_000):
    return {'Position': position, 'ShiftCode': shift, 'StaffPerDay': staff, 'CoverageDays': coverage,
            'AvgDailyRate': rate}


TECH = [row('Technician (Morning)', 'S'), row('Technician (Afternoon)', 'C'), row('Technician (Night)', 'D')]


def duty_by_code(demand):
    return {d.code: d for d in g._new_prospect_duty(demand, P2027)}


def test_a_technician_on_a_24_hour_rotation():
    # Spec scenario: 7 coverage days, day shifts 1 + 1 staff, night shift 1 staff.
    d = duty_by_code(TECH)['TN']
    assert (d.day_holiday, d.night_normal, d.night_holiday) == (2, 1, 1)
    # A1's per-person gross: 325,000 x 302 / 12 = 8,179,166.7 -> 8,179,167
    assert d.gross == 8_179_167


def test_a_day_only_seven_day_position_is_not_counted():
    assert 'CS' not in duty_by_code([row('Customer Service', 'HC')])


def test_a_night_position_below_seven_days_gets_night_work_only():
    d = duty_by_code([row('Technician (Morning)', 'S', coverage=6), row('Technician (Night)', 'D', coverage=6)])['TN']
    assert (d.day_holiday, d.night_normal, d.night_holiday) == (0, 1, 1)


def test_a_24h_post_counts_for_both_day_and_night():
    d = duty_by_code([row('Shift Leader (24h)', '24H', staff=1)])['TDS']
    assert (d.day_holiday, d.night_normal, d.night_holiday) == (1, 1, 1)


def test_outsourced_and_unstaffed_rows_are_left_out():
    demand = [row('Security - Main Gate (Night)', 'D', staff=2), row('Shift Leader (Night)', 'D', staff=0)]
    assert duty_by_code(demand) == {}


def test_a_qualifying_position_with_no_a11_row_keeps_its_own_code():
    # Chief Engineer (A1 code CE) has no row on A1.1 (CS, BE, TDS, TN, AA): it is returned under CE, and the writer
    # gives it its own row below the table.
    d = duty_by_code([row('Chief Engineer', 'HC'), row('Chief Engineer (Night)', 'D')])
    assert set(d) == {'CE'} and d['CE'].day_holiday == 1 and d['CE'].night_normal == 1


def test_a11_monthly_on_the_calendar_divisor():
    # F = 8,179,167 / (302/12) = 325,000.01; S12 = F x (0.3 x 353 x 1 + 3.9 x 12 x 1 + 3 x 12 x 2) = F x 224.7
    # = 73,027,503; S13 = ROUND(S12 / 12) = 6,085,625.
    duty = [es.DutyRow('TN', 1, 1, 2, gross=8_179_167)]
    assert es.a11_monthly(duty, P2027, workdays=302 / 12) == 6_085_625


def test_a11_monthly_keeps_25_days_for_existing_mode():
    # Default divisor is still the template's 25 (Existing mode unchanged): F = 8,125,000 / 25 = 325,000.
    duty = [es.DutyRow('TN', 1, 1, 2, gross=8_125_000)]
    assert es.a11_monthly(duty, P2027) == round(325_000 * 224.7 / 12)


# --- existing_detail_ties on a new prospect (the double count it must catch) ---
ROWS = {'EMH2': 83, 'EMH3': 84, 'EMH4': 85}

def _cells(emh2_formula, emh2_value, a11_rows=None):
    """A fake recalculated workbook: A1 total 120,000,000/year incl. an allowance of 1,000,000/month (AC90),
    A1.1!S13 = 1,000,000; EMH2, EMH3 and EMH4 on fund rows 83, 84 and 85 (A5 empty)."""
    a1, a11, fund = (g.STAFF_COST_SHEET, g.A11_SHEET, '2. Budget-Management Fund')
    values = {(a1, 96, 29): (120_000_000, '=AC93*AC95'), (a1, 90, 29): (1_000_000, "='A1.1'!S13"),
              (a1, 95, 29): (12, None), (a11, 13, 19): (1_000_000, '=ROUND(S12/$F$13,0)'),
              (fund, 83, 6): (None, emh2_formula), (fund, 83, 7): (emh2_value, None),
              (fund, 84, 6): (None, f"='{a11}'!S13"), (fund, 84, 7): (12_000_000, None),
              (fund, 85, 6): (None, f"='{g.A5_SHEET}'!H8/12"), (fund, 85, 7): (0, None)}
    values.update(a11_rows or {})

    def cell(sheet, r, c):
        return values.get((sheet, r, c), (None, None))
    return cell


def test_detail_ties_pass_when_emh2_leaves_the_allowance_out():
    from verification import checks
    cell = _cells(f"=('{g.STAFF_COST_SHEET}'!AC96-'{g.STAFF_COST_SHEET}'!AC90*'{g.STAFF_COST_SHEET}'!AC95)/12",
                  108_000_000)
    ok, _rows, diffs, _n = checks.existing_detail_ties(cell, ROWS)
    assert ok, diffs


def test_detail_ties_fail_on_a_double_counted_allowance():
    from verification import checks
    cell = _cells(f"='{g.STAFF_COST_SHEET}'!AC96/12", 120_000_000)       # EMH2 still carries AC90
    ok, _rows, diffs, _n = checks.existing_detail_ties(cell, ROWS)
    assert not ok and any('EMH2' in str(d[0]) for d in diffs)


def test_detail_ties_count_extra_allowance_rows_with_formulas():
    # A qualifying position with no A1.1 row is written below the table with A1.1's own formula chain (S a formula).
    from verification import checks
    a11 = g.A11_SHEET
    cell = _cells(f"=('{g.STAFF_COST_SHEET}'!AC96-'{g.STAFF_COST_SHEET}'!AC90*'{g.STAFF_COST_SHEET}'!AC95)/12",
                  108_000_000,
                  {(a11, 15, 19): (2_400_000, '=R15+N15+J15'),
                   ('2. Budget-Management Fund', 84, 7): (14_400_000, None),
                   ('2. Budget-Management Fund', 84, 6): (None, f"='{a11}'!T16")})
    ok, _rows, diffs, _n = checks.existing_detail_ties(cell, ROWS)
    assert ok, diffs
