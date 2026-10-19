"""Unit tests for adjustment_detail.collect(), the data behind the deliverable's '4. Điều chỉnh' sheet (docs/32, section 2).

Covered: the invariants of the interface on an invented workbook (sub-rows add up to the line, qty x unit price =
amount, every non-zero line present, zero and formula lines left out, sheet order), the real sub-rows of the contract
lines / EMH2 / ESS9 / RA1.A-RA2 / RP1-RP2 / RM.*, the lump row of every other code, the rounding row, EMH2 priced
from A1 the way the sheet computes it (one row worked by hand, the empty PM row's accident insurance, Existing mode's
carried rows below the table), and the standard sample end to end when the live input and template are present.

Invented data only: fictional posts, grosses and figures. The standard-sample test runs the budget generator with every
output redirected into a temporary folder (verification/isolation.py), as verify.py does.
"""
import os
import sys

import openpyxl
import pytest

import adjustment_detail as ad
import generate_project_budget as g

FUND, COMMON, A1 = ad.FUND_SHEET, ad.COMMON_SHEET, g.STAFF_COST_SHEET


# ------------------------------------------------------------------------------------------------
# An invented deliverable: the two fund sheets and A1 with the cells collect() reads
# ------------------------------------------------------------------------------------------------
def _fund_row(ws, row, code, name, freq=None, f=None, months=None):
    ws.cell(row=row, column=25, value=code)
    ws.cell(row=row, column=26, value=name)
    if freq:
        ws.cell(row=row, column=3, value=freq)
    if f is not None:
        ws.cell(row=row, column=6, value=f)
    if months is not None:
        for i, m in enumerate(months):
            ws.cell(row=row, column=8 + i, value=m)


def _a1_sheet(wb):
    ws = wb.create_sheet(A1)
    ws['I4'], ws['I5'] = 2_530_000, '=4960000*(1+7.2%)*0+5310000'
    for coord in ('L7', 'T7', 'V7'):
        ws[coord] = '=$I$4*20'
    for coord in ('M7', 'U7'):
        ws[coord] = '=$I$5*20'
    ws['N8'], ws['S8'], ws['T8'], ws['U8'], ws['V8'] = 12, 0.013, 0.205, 0.01, 0.02
    ws['W7'], ws['W8'], ws['AB1'] = 1_350_000, 12, 0.1
    ws['AC89'], ws['AC92'], ws['AC95'], ws['AC96'] = '=ROUND(SUM(AC15:AC88),0)', 0, 12, '=AC93*AC95'
    labels = {15: ('Trưởng Ban Quản Lý', 'PM'), 16: ('Kỹ thuật viên 1', 'TN'), 17: ('Kỹ thuật viên 2', 'TN'),
              18: ('Kế toán 1', 'ACC')}
    for r in range(15, 89):
        label, code = labels.get(r, (f'Vị trí {r}', 'XX'))
        ws.cell(row=r, column=2, value=label)
        ws.cell(row=r, column=4, value=code)
        for col, formula in g._a1_chain_formulas(r).items():
            ws.cell(row=r, column=col, value=formula)
    return ws


def _workbook(with_pm=True, emh2_formula=True):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    fund = wb.create_sheet(FUND)
    common = wb.create_sheet(COMMON)
    a1 = _a1_sheet(wb)
    if with_pm:
        a1['G15'] = 30_000_000
    a1['G16'] = a1['G17'] = 10_000_000
    # the fund sheet, in row order
    _fund_row(fund, 14, 'RM.AP', 'Management fee of Apartment\nPhí quản lý thu từ Căn hộ', 'Schedule',
              months=[1_000_000 * (i + 1) for i in range(12)])                       # 78,000,000
    _fund_row(fund, 26, 'RP1', 'Motorbike\nTiền thu từ gắn máy tháng', 'Schedule', months=[2_000_000] * 12)
    _fund_row(fund, 27, 'RP2', 'Car\nTiền thu từ xe ô tô tháng', 'Schedule', months=[5_000_000] * 12)
    emh2 = "=('A1. Staff cost 08.2026 (VN)'!AC96-'A1. Staff cost 08.2026 (VN)'!AC90*12)/12" if emh2_formula else 1_000
    _fund_row(fund, 83, 'EMH2', 'Staff cost\nPhí lương gộp', 'Monthly', f=emh2, months=[emh2] * 12)
    _fund_row(fund, 84, 'EMH3', 'Allowance\nPhụ cấp', 'Monthly', f="='A1.1 Allowance (From 08.2026)'!S13")
    _fund_row(fund, 101, 'EMA7', 'Drinking water\nChi phí nước uống', 'Monthly', f=0)      # zero: left out
    _fund_row(fund, 131, 'EM#', 'Contingency\nDự phòng', 'Schedule', months=['=ROUND(0.05*1,0)'] * 12)
    _fund_row(fund, 145, 'ESS1', 'Security\nDịch vụ bảo vệ', 'Monthly', f=7_000_007 / 12)
    _fund_row(fund, 153, 'ESS9', 'Garbage\nThu gom rác sinh hoạt', 'Monthly', f=1_000_000, months=[1_000_000] * 12)
    _fund_row(fund, 194, 'ESM2', 'Environmental report\nBáo cáo quan trắc', 'Monthly', f=2_083_333)
    _fund_row(fund, 200, 'ESM8', 'Fire dept\nPhí kết nối PCCC', 'Yearly', f=6_000_000)   # template frequency: left out
    _fund_row(common, 20, 'RA1.A', 'LCD\nQuảng cáo LCD cho khu căn hộ', 'Monthly', f=3_000_000)
    _fund_row(common, 26, 'RA2', 'Decal\nDecal quảng cáo cửa thang máy', 'Monthly', f=2_000_000)
    _fund_row(common, 44, 'EMH2', 'Staff cost\nPhí lương gộp', 'Monthly', f="=_xlfn.XLOOKUP(Y44,A:A,B:B)*$F$8")
    return wb


def _post(position, shift, staff=1, coverage=7):
    return {'Position': position, 'ShiftCode': shift, 'StaffPerDay': staff, 'CoverageDays': coverage,
            'AvgDailyRate': 224_000}


@pytest.fixture
def figures():
    g._HELPER_FIGURES.clear()
    g._HELPER_FIGURES['contract'] = {'Security': dict(
        post_rate=17_500_000, roles=3, blend=1.1, qty=7,
        posts=[(_post('Security - Main Gate (Morning)', 'S'), 5), (_post('Security - CCTV Room (Night)', 'D'), 2)],
        excluded=[])}
    g._HELPER_FIGURES['waste'] = dict(apt_units=600, shop_units=5, monthly=1_000_000)
    g._HELPER_FIGURES['ads'] = [
        dict(item='Ad frame (tower lobby, inside elevator)', item_vi='Khung quảng cáo', rate=500_000, qty=4, note=''),
        dict(item='LCD screen (tower lobby)', item_vi='Màn hình LCD (sảnh tòa nhà)', rate=1_000_000, qty=2, note=''),
        dict(item='LCD screen (basement lobby)', item_vi='Màn hình LCD (sảnh tầng hầm)', rate=1_000_000, qty=1, note='')]
    g._HELPER_FIGURES['parking'] = {'moto': dict(rate=110_000, slots=100, recorded=None),
                                    'car': dict(rate=1_100_000, slots=20, recorded=3_000_000)}
    yield
    g._HELPER_FIGURES.clear()


PROJECT = {'products': {'Apartment': {'nfa': 72_000, 'units': 600}}}


def _by_code(items):
    return {it['code']: it for it in items}


def test_every_written_non_zero_line_is_present_in_sheet_order_and_nothing_else(figures):
    items = ad.collect(_workbook(), PROJECT, [])
    assert [it['code'] for it in items] == ['RM.AP', 'RP1', 'RP2', 'EMH2', 'ESS1', 'ESS9', 'ESM2', 'RA1.A', 'RA2']
    assert [it['sheet'] for it in items[:7]] == [FUND] * 7 and [it['sheet'] for it in items[7:]] == [COMMON] * 2
    assert ad.check_invariants(items) == []


def test_parent_rows_carry_the_months_the_sheet_holds(figures):
    by = _by_code(ad.collect(_workbook(), PROJECT, []))
    assert by['RM.AP']['freq'] == 'Schedule' and by['RM.AP']['months'] == [1_000_000.0 * (i + 1) for i in range(12)]
    assert by['RM.AP']['annual'] == 78_000_000 and by['RM.AP']['row'] == 14
    assert by['ESM2']['freq'] == 'Monthly' and by['ESM2']['months'] == [2_083_333.0] * 12
    assert by['ESM2']['annual'] == 2_083_333 * 12 and by['ESM2']['name_vi'] == 'Báo cáo quan trắc'


def test_a_code_with_no_real_detail_gets_one_lump_row(figures):
    by = _by_code(ad.collect(_workbook(), PROJECT, []))
    assert by['ESM2']['subs'] == [{'desc_vi': 'Báo cáo quan trắc', 'unit_vi': 'khoản', 'qty': 1.0,
                                   'unit_price': 2_083_333 * 12.0, 'amount': 2_083_333 * 12.0, 'qty_editable': False}]


def test_contract_posts_split_the_line_by_people_with_a_rounding_row_when_needed(figures):
    subs = _by_code(ad.collect(_workbook(), PROJECT, []))['ESS1']['subs']
    annual = 7_000_007 / 12 * 12
    assert [s['desc_vi'] for s in subs[:2]] == ['Vị trí cổng chính (ca sáng)', 'Trực phòng CCTV (ca đêm)']
    assert [s['qty'] for s in subs[:2]] == [5.0, 2.0] and all(s['qty_editable'] for s in subs[:2])
    assert all(s['unit_vi'] == 'người' for s in subs[:2])
    assert abs(sum(s['amount'] for s in subs) - annual) < 1e-6
    for s in subs:
        assert abs(s['qty'] * s['unit_price'] - s['amount']) < 1e-6
    if len(subs) == 3:
        assert subs[2]['desc_vi'] == ad.ROUNDING_DESC_VI and not subs[2]['qty_editable'] and subs[2]['qty'] == 1.0


def test_waste_splits_by_units_times_kg_per_day(figures):
    subs = _by_code(ad.collect(_workbook(), PROJECT, []))['ESS9']['subs']
    annual = 12_000_000
    apt_w, shop_w = 600 * g.WASTE_APARTMENT_KG_PER_UNIT_DAY, 5 * g.WASTE_SHOPHOUSE_KG_PER_UNIT_DAY
    assert [(s['desc_vi'], s['unit_vi'], s['qty']) for s in subs[:2]] == [('Căn hộ', 'căn', 600.0), ('Shophouse', 'căn', 5.0)]
    assert subs[0]['amount'] == round(annual * apt_w / (apt_w + shop_w))
    assert sum(s['amount'] for s in subs) == annual


def test_advertising_devices_go_to_their_own_line(figures):
    by = _by_code(ad.collect(_workbook(), PROJECT, []))
    lcd, lift = by['RA1.A']['subs'], by['RA2']['subs']
    assert [s['desc_vi'] for s in lcd] == ['Màn hình LCD (sảnh tòa nhà)', 'Màn hình LCD (sảnh tầng hầm)']
    assert [s['qty'] for s in lcd] == [2.0, 1.0] and sum(s['amount'] for s in lcd) == 36_000_000
    assert lcd[0]['amount'] == 24_000_000 and lcd[1]['amount'] == 12_000_000
    assert lift == [{'desc_vi': 'Khung quảng cáo', 'unit_vi': 'thiết bị', 'qty': 4.0, 'unit_price': 6_000_000.0,
                     'amount': 24_000_000.0, 'qty_editable': True}]


def test_parking_bays_are_the_quantity_and_an_entered_actual_stays_a_lump(figures):
    by = _by_code(ad.collect(_workbook(), PROJECT, []))
    assert by['RP1']['subs'] == [{'desc_vi': 'Chỗ xe máy', 'unit_vi': 'chỗ', 'qty': 100.0, 'unit_price': 240_000.0,
                                  'amount': 24_000_000.0, 'qty_editable': True}]
    assert by['RP2']['subs'] == [{'desc_vi': 'Tiền thu từ xe ô tô tháng', 'unit_vi': 'khoản', 'qty': 1.0,
                                  'unit_price': 60_000_000.0, 'amount': 60_000_000.0, 'qty_editable': False}]


def test_management_fee_revenue_is_priced_per_square_metre(figures):
    sub, = _by_code(ad.collect(_workbook(), PROJECT, []))['RM.AP']['subs']
    assert sub['desc_vi'] == 'Diện tích căn hộ (NFA)' and sub['unit_vi'] == 'm²' and sub['qty'] == 72_000.0
    assert sub['amount'] == 78_000_000.0 and abs(sub['qty'] * sub['unit_price'] - 78_000_000) < 1e-6
    assert sub['qty_editable']
    # no area for the product: the line stays a lump row
    sub, = _by_code(ad.collect(_workbook(), {'products': {}}, []))['RM.AP']['subs']
    assert sub['unit_vi'] == 'khoản' and not sub['qty_editable']


# ---- EMH2 from A1 ----
# One Technician row on a 10,000,000 gross, worked by hand along the template's chain (column AC = AA + AB):
#   I 10,000,000; N 833,333.33; R 300,000; S 130,000; T 2,050,000 (20.5%, under the 50,600,000 cap); U 100,000;
#   V 200,000; W 112,500; X 30,000 (the floor: (297,000 + 132,000 + 446,985) x 40% / 12 = 29,199.5); Z 300,000
#   AA = ROUND(14,055,833.33) = 14,055,833; AB = ROUND(1,405,583.3) = 1,405,583; AC = 15,461,416 a month.
TN_MONTHLY = 15_461_416
# The empty PM row: X = (446,985 + 2,456,000) x 58% / 12 = 140,310.94 -> AA 140,311, AB 14,031, AC 154,342.
EMPTY_PM_MONTHLY = 154_342


def test_emh2_has_one_row_per_title_at_one_persons_annual_a1_cost(figures):
    by = _by_code(ad.collect(_workbook(), PROJECT, []))
    emh2 = by['EMH2']
    tn = [s for s in emh2['subs'] if s['desc_vi'] == 'Kỹ thuật viên']
    assert tn == [{'desc_vi': 'Kỹ thuật viên', 'unit_vi': 'người', 'qty': 2.0, 'unit_price': TN_MONTHLY * 12.0,
                   'amount': TN_MONTHLY * 24.0, 'qty_editable': True}]
    pm = [s for s in emh2['subs'] if s['desc_vi'] == 'Trưởng Ban Quản Lý']
    assert len(pm) == 1 and pm[0]['qty'] == 1.0 and pm[0]['qty_editable']
    assert ad.ROUNDING_DESC_VI not in [s['desc_vi'] for s in emh2['subs']]
    assert emh2['freq'] == 'Monthly' and emh2['annual'] == sum(s['amount'] for s in emh2['subs'])
    assert emh2['months'] == [emh2['annual'] / 12] * 12


def test_an_empty_pm_row_still_costs_its_accident_insurance_as_the_rounding_row(figures):
    emh2 = _by_code(ad.collect(_workbook(with_pm=False), PROJECT, []))['EMH2']
    rounding = [s for s in emh2['subs'] if s['desc_vi'] == ad.ROUNDING_DESC_VI]
    assert rounding == [{'desc_vi': ad.ROUNDING_DESC_VI, 'unit_vi': 'khoản', 'qty': 1.0,
                         'unit_price': EMPTY_PM_MONTHLY * 12.0, 'amount': EMPTY_PM_MONTHLY * 12.0, 'qty_editable': False}]
    assert emh2['annual'] == (2 * TN_MONTHLY + EMPTY_PM_MONTHLY) * 12


def test_existing_mode_rows_below_the_table_are_lump_rows_and_a_zeroed_pm_row_costs_nothing(figures):
    wb = _workbook(with_pm=False)
    a1 = wb[A1]
    a1['X15'] = 0                                    # Existing mode zeroes the empty PM row's accident insurance
    a1.cell(row=g._A1_UNPLACED_FIRST_ROW, column=2, value='EMH2 đã duyệt NS 2026 mang sang')
    a1.cell(row=g._A1_UNPLACED_FIRST_ROW, column=29, value=3_600_000_000 / 12)
    a1.cell(row=g._A1_UNPLACED_FIRST_ROW + 1, column=2, value='Lễ tân')     # an overflow head with A1's own chain
    a1.cell(row=g._A1_UNPLACED_FIRST_ROW + 1, column=4, value='LT')
    a1.cell(row=g._A1_UNPLACED_FIRST_ROW + 1, column=7, value=10_000_000)
    a1.cell(row=g._A1_UNPLACED_FIRST_ROW + 1, column=8, value=0)
    for col, formula in g._a1_chain_formulas(g._A1_UNPLACED_FIRST_ROW + 1).items():
        a1.cell(row=g._A1_UNPLACED_FIRST_ROW + 1, column=col, value=formula)
    emh2 = _by_code(ad.collect(wb, PROJECT, []))['EMH2']
    descs = [s['desc_vi'] for s in emh2['subs']]
    assert 'EMH2 đã duyệt NS 2026 mang sang' in descs and 'Lễ tân' in descs and ad.ROUNDING_DESC_VI not in descs
    carried = next(s for s in emh2['subs'] if s['desc_vi'].startswith('EMH2'))
    assert carried['amount'] == 3_600_000_000 and not carried['qty_editable'] and carried['unit_vi'] == 'khoản'
    assert emh2['annual'] == 2 * TN_MONTHLY * 12 + 3_600_000_000 + TN_MONTHLY * 12
    assert ad.check_invariants([emh2]) == []


def test_an_a1_reference_cell_the_tool_cannot_read_is_named():
    wb = _workbook()
    wb[A1]['T7'] = '=SOMEWHERE!A1'
    with pytest.raises(ValueError, match='T7'):
        ad.collect(wb, PROJECT, [])


def test_check_invariants_names_a_broken_item():
    item = {'code': 'X1', 'sheet': FUND, 'row': 5, 'name_vi': 'x', 'freq': 'Monthly', 'months': [1.0] * 12,
            'annual': 12.0, 'subs': [{'desc_vi': 'a', 'unit_vi': 'khoản', 'qty': 2.0, 'unit_price': 5.0,
                                      'amount': 14.0, 'qty_editable': False}]}
    problems = ad.check_invariants([item, item])
    assert any('listed twice' in p for p in problems)
    assert any('sub-rows' in p for p in problems) and any('qty x unit price' in p for p in problems)


# ------------------------------------------------------------------------------------------------
# The standard sample end to end (skipped without the live input and the standard form)
# ------------------------------------------------------------------------------------------------
@pytest.mark.skipif(not (os.path.exists(g.INPUT_PATH) and os.path.exists(g.TEMPLATE_PATH)),
                    reason='standard sample input or form not available')
def test_standard_sample_items_hold_every_invariant(tmp_path, monkeypatch):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'verification'))
    from isolation import redirected_paths
    captured = {}
    real_collect = ad.collect

    def capture(wb, project, demand):
        items = real_collect(wb, project, demand)
        captured['items'] = items
        return items
    monkeypatch.setattr(ad, 'collect', capture)
    with redirected_paths(g.INPUT_PATH, str(tmp_path)):
        project, _ratios, _month, year, _holidays, demand = g.read_input(g.INPUT_PATH)
        g.build_budget(project, demand, year)
    items = captured['items']
    assert ad.check_invariants(items) == []
    by = _by_code(items)
    assert by['EMH2']['annual'] > 0 and any(s['qty_editable'] for s in by['EMH2']['subs'])
    assert any(s['qty_editable'] for s in by['ESS1']['subs'])
    assert all(it['sheet'] == FUND for it in items[:len([i for i in items if i['sheet'] == FUND])])
    rows = [it['row'] for it in items if it['sheet'] == FUND]
    assert rows == sorted(rows)
