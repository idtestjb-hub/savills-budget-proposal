"""Unit tests for the deliverable's helper sheets A2-A4 and B1-B5 (change apply-head-of-pm-decisions-2026-10, group 8,
tasks 8.1-8.2; design D15; spec deliverable-helper-sheets).

Covered: the A2/A3/A4 writers (fill_helper_sheets' _fill_service_post_sheet) on the standard form's own sheets, the B1
reception calendar (_reception_calendar, _fill_reception_calendar), the B2-B5 writers (_fill_b2_b5), and the tie
check's pure core (checks.helper_sheet_ties).

Not covered: the workbook end to end and Excel's recalculation (verify.py runs check_helper_sheet_ties on every
sample).

Rules (the user's choices of 2026-10-18 and 2026-10-19):
 - A2-A4 list people on an 8-hour shift (E = 8), relief for the weekly day off included (x 7/6, rounded up), at the
   line's rate x night blend in the rate cell, so each sheet's total x 12 equals ESS1 / ESS4 / ESS16;
 - a post with no standard row goes on the group's main row with a note; a supervisor goes on the sheet's unpriced
   row (A3/A4) or is named in the notes (A2); night and 24h cleaning or landscape people go in the standard-shift
   column;
 - every other standard row keeps its name and duty text with quantity 0;
 - B1 follows the roster's rest rule for the roster month, shows at most the form's five rows and notes the rest;
 - B3 garbage = ESS9 units x 100% x kg/unit/day x 30 x 1,087 VND/kg; B4 = the RA1.A/RA2 devices; B5 = RP1/RP2 prices;
   B2 and B3 consumables say "Chưa áp dụng".
The template is the standard form under input/template (read only); a test is skipped when it is not there.
Staffing rows are invented.
"""
import math
import os
import re

import openpyxl
import pytest

import generate_project_budget as g

pytestmark = pytest.mark.skipif(not os.path.exists(g.TEMPLATE_PATH), reason='standard form not available')

HELPERS = ('A2. Bảo vệ - Security', 'A3. Vệ sinh - Cleaning', 'A4. Cây xanh - Landscape', 'B1. Lịch Lễ tân',
           'B2. Mùi hương - Scent', 'B3. Vật tư vệ sinh - Consumable', 'B3. Thu gom rác - Garbage coll ',
           'B4. DT Quảng cáo - Elevator adv', 'B5. Đơn giá gửi xe - Parking pr')
SECURITY_RATE, CLEANING_RATE, LANDSCAPE_RATE = 17_500_000, 8_000_000, 11_000_000


@pytest.fixture(scope='module')
def template():
    return openpyxl.load_workbook(g.TEMPLATE_PATH)


@pytest.fixture
def wb(template):
    """A fresh workbook holding copies of the helper sheets (values, formulas and merged ranges)."""
    out = openpyxl.Workbook()
    out.remove(out.active)
    for name in HELPERS:
        src, ws = template[name], out.create_sheet(name)
        for row in src.iter_rows():
            for c in row:
                if c.value is not None:
                    ws.cell(row=c.row, column=c.column).value = c.value
        for m in src.merged_cells.ranges:
            ws.merge_cells(str(m))
    g._HELPER_FIGURES.clear()
    yield out
    g._HELPER_FIGURES.clear()


def row(position, shift, staff=1, coverage=7):
    return {'Position': position, 'ShiftCode': shift, 'StaffPerDay': staff, 'CoverageDays': coverage,
            'AvgDailyRate': 300_000}


SECURITY = [row('Security - Main Gate (Morning)', 'S', 2), row('Security - Main Gate (Afternoon)', 'C', 2),
            row('Security - Main Gate (Night)', 'D', 2), row('Security - CCTV Room (Morning)', 'S'),
            row('Security - CCTV Room (Afternoon)', 'C'), row('Security - CCTV Room (Night)', 'D'),
            row('Security - Patrol / Open Space', 'S')]
PROJECT = {'name': 'ZZ Test Tower', 'products': {'Apartment': {'nfa': 30_000, 'units': 480}}, 'car_slots': 100}


def record(cat, demand, rate, roles):
    """What contract_cost() records: matched posts, rate, roles and the 4-dp night blend."""
    from generate_project_output import SERVICE_CATEGORY_KEYWORDS, SERVICE_EXCLUDE_KEYWORDS, NIGHT_SHIFT_CODES
    kws = SERVICE_CATEGORY_KEYWORDS[cat]
    matched = [d for d in demand if any(k in d['Position'].lower() for k in kws)
               and not any(e in d['Position'].lower() for e in SERVICE_EXCLUDE_KEYWORDS)]
    qty = sum(g._post_persons(d) for d in matched)
    night = sum(g._post_persons(d) for d in matched if d['ShiftCode'] in NIGHT_SHIFT_CODES)
    blend = round(1 + (night / qty) * 0.3, 4) if qty else 1.0
    g._record_contract_posts(cat, demand, matched, rate, roles, blend, qty)
    return rate / roles * blend * qty * 12


def rate_value(ws, coord):
    a, b = re.fullmatch(r'=(\d+)\*([\d.]+)', ws[coord].value).groups()
    return float(a) * float(b)


def notes(ws, col='C'):
    """The numbered note lines the writer puts under a service sheet's table."""
    return '\n'.join(c.value for c in ws[col] if isinstance(c.value, str) and re.match(r'\d+\. ', c.value))


# ---- A2 security ----

def test_security_posts_on_their_rows_and_the_total_equals_ess1(wb):
    annual = record('Security', SECURITY, SECURITY_RATE, 3)
    g._fill_service_post_sheet(wb, PROJECT, 'Security')
    ws = wb['A2. Bảo vệ - Security']
    assert ws['G3'].value == '=17500000*1.0882'
    assert (ws['F14'].value, ws['F12'].value, ws['F16'].value) == (9, 6, 2)     # main gate, CCTV, patrol
    assert {ws.cell(row=r, column=5).value for r in (12, 14, 16)} == {8}
    rows = range(10, 31)
    total = sum(rate_value(ws, 'G3') / 24 * ws.cell(row=r, column=5).value * (ws.cell(row=r, column=6).value or 0)
                for r in rows if isinstance(ws.cell(row=r, column=5).value, (int, float)))
    assert total * 12 == pytest.approx(annual, abs=1)


def test_security_unused_rows_keep_their_duty_at_quantity_zero(wb, template):
    record('Security', SECURITY, SECURITY_RATE, 3)
    g._fill_service_post_sheet(wb, PROJECT, 'Security')
    ws, src = wb['A2. Bảo vệ - Security'], template['A2. Bảo vệ - Security']
    for r in (10, 11, 13, 15, 17, 19, 20, 21, 23, 24, 25, 27, 28, 30):
        assert ws.cell(row=r, column=6).value == 0
        assert ws.cell(row=r, column=9).value == src.cell(row=r, column=9).value      # duty description kept
        assert ws.cell(row=r, column=4).value == src.cell(row=r, column=4).value
    # The 24h-conversion block keeps its formulas and counts the 8-hour rows.
    assert ws['F33'].value.startswith('=SUMIF') and ws['E35'].value == 8
    assert (ws['M7'].value, ws['P7'].value) == (30_000, 100)


def test_security_post_with_no_standard_row_goes_on_patrol_with_a_note(wb):
    demand = SECURITY + [row('Security - Basement Ramp', 'S'), row('Security Supervisor', 'HC', coverage=6)]
    annual = record('Security', demand, SECURITY_RATE, 3)
    g._fill_service_post_sheet(wb, PROJECT, 'Security')
    ws = wb['A2. Bảo vệ - Security']
    assert ws['F16'].value == 4                                                       # patrol 2 + ramp 2
    text = notes(ws)
    assert 'Security - Basement Ramp (2 người)' in text and 'gộp vào dòng này' in text
    assert 'Không ghi trên trang này: Security Supervisor (1 người)' in text
    total = sum(rate_value(ws, 'G3') / 24 * 8 * (ws.cell(row=r, column=6).value or 0) for r in (12, 14, 16))
    assert total * 12 == pytest.approx(annual, abs=1)


# ---- A3 cleaning, A4 landscape ----

def test_cleaning_by_shift_column_with_the_supervisor_unpriced(wb):
    demand = [row('Cleaning - Common Area', 'S', 2), row('Cleaning - Common Area (Night)', 'D', 1),
              row('Cleaning - Supervisor', 'HC', coverage=6)]
    annual = record('Cleaning', demand, CLEANING_RATE, 1)
    g._fill_service_post_sheet(wb, PROJECT, 'Cleaning')
    ws = wb['A3. Vệ sinh - Cleaning']
    assert (ws['F12'].value, ws['H12'].value, ws['E12'].value) == (3, 2, 8)          # morning 3, night 2 in H
    assert ws['H10'].value == 1 and ws['J10'].value is None                           # supervisor, no price
    for coord in ('F10', 'G11', 'F13', 'G13', 'H14', 'H15', 'F18', 'G18'):            # the form's sample counts
        assert not ws[coord].value
    priced = [r for r in range(10, 23) if '$J$3' in str(ws.cell(row=r, column=10).value or '')]
    total = sum(rate_value(ws, 'J3') / 8 * ws.cell(row=r, column=5).value
                * sum(ws.cell(row=r, column=c).value or 0 for c in (6, 7, 8)) for r in priced)
    assert total * 12 == pytest.approx(annual, abs=1)
    text = notes(ws)
    assert 'không tính giá trong khoản ESS4' in text and '2 người ca đêm/24h ghi ở cột ca hành chính' in text


def test_landscape_rate_written_and_the_form_samples_cleared(wb):
    annual = record('Landscape', [row('Gardener / Landscape', 'HC', 2, 6)], LANDSCAPE_RATE, 1)
    g._fill_service_post_sheet(wb, PROJECT, 'Landscape')
    ws = wb['A4. Cây xanh - Landscape']
    assert ws['J3'].value == '=11000000*1'
    assert (ws['H8'].value, ws['H9'].value, ws['H10'].value) == (0, 0, 2)
    assert rate_value(ws, 'J3') * ws['H10'].value * 12 == pytest.approx(annual)
    assert 'gộp' not in notes(ws)


def test_a_category_with_no_posts_shows_zero(wb):
    record('Landscape', [], LANDSCAPE_RATE, 1)
    g._fill_service_post_sheet(wb, PROJECT, 'Landscape')
    ws = wb['A4. Cây xanh - Landscape']
    assert (ws['H8'].value, ws['H9'].value, ws['H10'].value) == (0, 0, 0)
    assert 'không có vị trí cây xanh' in notes(ws)


# ---- B1 reception calendar ----

ROSTER_0926 = {'roster_month': (2026, 9), 'roster_holidays': [1, 2]}


def codes(ws, r, days=31):
    return [ws.cell(row=r, column=4 + i).value for i in range(days)]


def test_reception_calendar_follows_the_roster_rest_rule(wb):
    g._fill_reception_calendar(wb, dict(PROJECT, **ROSTER_0926), [row('Reception', 'HC', 1, 7)])
    ws = wb['B1. Lịch Lễ tân']
    assert (ws['D5'].value, ws['D6'].value, ws['AG6'].value, ws['AH6'].value) == ('Thứ 3', 1, 30, None)  # 01/09/2026 Tue
    first, second = codes(ws, 7), codes(ws, 8)
    assert [d + 1 for d, c in enumerate(first) if c == 'O'] == [1, 8, 15, 22, 29]
    assert [d + 1 for d, c in enumerate(second) if c == 'O'] == [2, 9, 16, 23, 30]
    assert first[30] is None and set(first[:30]) == {'O', 'HC'}
    assert (ws['B7'].value, ws['C7'].value, ws['B8'].value) == ('Lễ tân 1', 'Hành chính', 'Lễ tân 2')
    assert ws['AP7'].value == '=30-AJ7-AK7-AM7/2' and ws['AJ8'].value == '=COUNTIF(D8:AH8,"O")'
    assert all(v is None for v in codes(ws, 9)) and ws['B9'].value is None
    assert '01/09, 02/09' in ws['B21'].value and '09/2026 (30 ngày)' in ws['B19'].value
    assert ws['B42'].value is None and ws['C42'].value is None                        # the form's #REF! cells
    assert ws['E26'].value is None and ws['B26'].value.startswith('Chưa áp dụng')


def test_reception_short_week_rests_on_the_days_past_coverage(wb):
    g._fill_reception_calendar(wb, dict(PROJECT, **ROSTER_0926), [row('Reception', 'S', 1, 5)])
    ws = wb['B1. Lịch Lễ tân']
    week = codes(ws, 7)[6:13]                                                         # 07/09 (Mon) to 13/09 (Sun)
    assert week == ['S'] * 5 + ['O', 'O'] and ws['C7'].value == 'Ca sáng'


def test_more_reception_people_than_rows_are_noted(wb):
    g._fill_reception_calendar(wb, dict(PROJECT, **ROSTER_0926), [row('Reception', 'HC', 5, 7)])
    ws = wb['B1. Lịch Lễ tân']
    assert math.ceil(5 * 7 / 6) == 6
    assert ws['B11'].value == 'Lễ tân 5' and ws['B12'].value is None
    assert ws['B22'].value.startswith('Dự án cần 6 lễ tân') and '1 người còn lại' in ws['B22'].value


def test_no_reception_clears_the_sample(wb):
    g._fill_reception_calendar(wb, dict(PROJECT, **ROSTER_0926), [row('Customer Service', 'HC')])
    ws = wb['B1. Lịch Lễ tân']
    assert ws['B7'].value == 'Dự án không có vị trí lễ tân.'
    assert all(v is None for v in codes(ws, 7)) and all(v is None for v in codes(ws, 11))


# ---- B2-B5 ----

def figures(recorded_car=None, car_slots=100):
    g._HELPER_FIGURES['waste'] = dict(apt_units=480, shop_units=12, monthly=0.0)
    g._HELPER_FIGURES['ads'] = [
        dict(item='Ad frame (tower lobby, inside elevator)', item_vi='Khung', rate=848_485, qty=4, note='giả định'),
        dict(item='LCD screen (tower lobby)', item_vi='LCD', rate=1_212_121, qty=2, note='giả định'),
        dict(item='LCD screen (basement lobby)', item_vi='LCD hầm', rate=1_060_606, qty=1, note='giả định')]
    g._HELPER_FIGURES['parking'] = {'car': dict(rate=1_100_000, slots=car_slots, recorded=recorded_car),
                                    'moto': dict(rate=110_000, slots=500, recorded=None)}


def test_garbage_sheet_prices_the_ess9_units(wb):
    figures()
    g._fill_b2_b5(wb, PROJECT)
    ws = wb['B3. Thu gom rác - Garbage coll ']
    assert (ws['C5'].value, ws['E5'].value, ws['K5'].value) == (480, 1, '=2.63*30*1087')
    assert (ws['C6'].value, ws['K6'].value) == (12, '=3.945*30*1087')                # shophouse units over the link
    assert ws['M7'].value == 'Chưa áp dụng.' and ws['J12'].value is None and ws['J49'].value is None
    assert 'Quyết định 65/2026/QĐ-UBND' in ws['M5'].value


def test_advertising_sheet_equals_the_ra_devices(wb):
    figures()
    g._fill_b2_b5(wb, PROJECT)
    ws = wb['B4. DT Quảng cáo - Elevator adv']
    assert (ws['F5'].value, ws['G5'].value, ws['I5'].value, ws['J5'].value) == (4, 848_485, 2, 1_212_121)
    assert (ws['F6'].value, ws['G6'].value, ws['I6'].value, ws['J6'].value) == (None, None, 1, 1_060_606)
    assert ws['F13'].value is None
    monthly = 4 * 848_485 + 2 * 1_212_121 + 1_060_606
    assert f'{monthly * 12:,.0f}' in ws['M7'].value


def test_parking_sheet_shows_the_rp_prices_and_no_reference_project(wb):
    figures()
    g._fill_b2_b5(wb, PROJECT)
    ws = wb['B5. Đơn giá gửi xe - Parking pr']
    assert (ws['B17'].value, ws['C17'].value, ws['E17'].value) == ('ZZ Test Tower', 1_100_000, 110_000)
    assert ws['D17'].value == ws['G17'].value == 'Chưa áp dụng.'
    assert ws['B7'].value.startswith('Chưa áp dụng') and ws['B8'].value is None


def test_recorded_parking_revenue_has_no_price_per_vehicle(wb):
    figures(recorded_car=52_000_000)
    g._fill_b2_b5(wb, PROJECT)
    ws = wb['B5. Đơn giá gửi xe - Parking pr']
    assert ws['C17'].value == 'Chưa áp dụng.' and '52,000,000 VND/tháng' in ws['I17'].value


def test_scent_and_consumables_say_not_used(wb):
    figures()
    g._fill_b2_b5(wb, PROJECT)
    b2, b3 = wb['B2. Mùi hương - Scent'], wb['B3. Vật tư vệ sinh - Consumable']
    assert all(b2.cell(row=r, column=c).value is None for r in (6, 7, 8) for c in (7, 8))
    assert b2['A11'].value.startswith('Chưa áp dụng')
    assert all(b3.cell(row=r, column=c).value is None for r in range(6, 12) for c in (3, 11, 12, 13))
    assert b3['Q13'].value is None and b3['G6'].value == 0.02                         # #REF! gone, norm kept


# ---- the tie check ----

def _tie_cells(a2_monthly, ess9_months, vat_switch='THU HỘ CHI HỘ'):
    import datetime
    fund, caf = '2. Budget-Management Fund', '2.2 Common area Fund'
    start = (datetime.datetime(2027, 1, 1) - datetime.datetime(1899, 12, 30)).days
    values = {(fund, 7, 6): vat_switch, (fund, 6, 34): start,
              ('A2. Bảo vệ - Security', 31, 8): a2_monthly, (fund, 145, 7): 1_294_958_004,
              ('A3. Vệ sinh - Cleaning', 23, 11): 24_000_000, (fund, 148, 7): 288_000_000,
              ('A4. Cây xanh - Landscape', 11, 11): 22_000_000, (fund, 160, 7): 264_000_000,
              ('B3. Thu gom rác - Garbage coll ', 11, 12): 1_000_000,
              ('B4. DT Quảng cáo - Elevator adv', 7, 12): 1_000, (caf, 20, 7): 7_000, (caf, 26, 7): 5_000}
    for i, v in enumerate(ess9_months):
        values[(fund, 153, 8 + i)] = v
    return lambda s, r, c: (values.get((s, r, c)), None)


TIE_ROWS = {('2. Budget-Management Fund', 'ESS1'): 145, ('2. Budget-Management Fund', 'ESS4'): 148,
            ('2. Budget-Management Fund', 'ESS16'): 160, ('2. Budget-Management Fund', 'ESS9'): 153,
            ('2.2 Common area Fund', 'RA1.A'): 20, ('2.2 Common area Fund', 'RA2'): 26}


def test_helper_ties_pass_with_ess9_taken_back_before_vat():
    from verification import checks
    import utility_tariffs
    vat = [utility_tariffs.vat_rate(2027, m) for m in range(1, 13)]
    ok, rows, diffs, _n = checks.helper_sheet_ties(_tie_cells(1_294_958_000 / 12,
                                                              [1_000_000 * (1 + v / 100) for v in vat]), TIE_ROWS)
    assert ok, diffs
    assert len(rows) == 5


def test_helper_ties_fail_on_a_security_gap_and_on_vat_left_in():
    from verification import checks
    ok, _rows, diffs, _n = checks.helper_sheet_ties(_tie_cells(100_000_000, [1_080_000] * 12), TIE_ROWS)
    assert not ok
    assert {str(d[0]).split('!')[0] for d in diffs} == {"'A2. Bảo vệ - Security'", "'B3. Thu gom rác - Garbage coll '"}


def test_helper_ties_compare_ess9_as_is_under_khoan():
    from verification import checks
    ok, _rows, diffs, _n = checks.helper_sheet_ties(_tie_cells(1_294_958_000 / 12, [1_000_000] * 12, 'KHOÁN'),
                                                    TIE_ROWS)
    assert ok, diffs
