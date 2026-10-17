"""Unit tests for Existing-project common-area electricity and water (change carry-forward-common-utilities).

Covered: reading the 'Prior-Year Utilities' sheet by label and its stops (task 2.3), the 12-month window, blank and
zero months, consumption from the bill or derived from the amount, the implied-rate flag (3.1), fewer than 12 and
fewer than 3 months (3.2), the budget-year amounts and the bridge on both VAT bases (3.3), overrides and reasons
(3.4), and the remark sentences (4.2).

Invented data only: amounts, consumption and the tariff table below are made up. One test reads the real
Ref_UtilityTariffs.csv to check the spec's worked example (public prices, as test_utility_tariffs.py documents).
"""
import openpyxl
import pytest

import build_project_input_form as bpf
import existing_staffing as es
import existing_utilities as eu
import utility_tariffs as ut
from input_labels import LabelNotFound, SheetLabels

LT6, W = ut.CAT_E_LT6, ut.CAT_W_HCMC
TABLE = [
    f'electricity,"{LT6}",base,1000,VND/kWh,2024-01-01,2025-05-09,,Decision A,,2026-10-11,',
    f'electricity,"{LT6}",base,1100,VND/kWh,2025-05-10,,,Decision B,,2026-10-11,',
    'vat,general,vat_pct,8,%,2024-01-01,2026-12-31,,Resolution C,,2026-10-11,',
    'vat,general,vat_pct,10,%,2027-01-01,,,Law D,,2026-10-11,',
    f'water,"{W}",base,10000,VND/m3,2024-01-01,,TP.HCM,Decision E,,2026-10-11,',
    'water,,wastewater_pct,30,%,2024-01-01,,TP.HCM,Decision F,,2026-10-11,',
    'water,,vat_pct,5,%,2024-01-01,,,Law G,,2026-10-11,',
]
E_2026_INCL = 1100 * 1.08            # electricity price per kWh incl. VAT in 2026 (invented table)
E_2027_INCL = 1100 * 1.10
W_2026_INCL = 10000 * 1.05 + 3000 * 1.08
W_2027_INCL = 10000 * 1.05 + 3000 * 1.10


@pytest.fixture
def rows(tmp_path):
    path = tmp_path / 'Ref_UtilityTariffs.csv'
    path.write_text(','.join(ut.COLUMNS) + '\n' + '\n'.join(TABLE) + '\n', encoding='utf-8')
    return ut.load_rows(str(path))


def _months(start_y, start_m, n):
    out, y, m = [], start_y, start_m
    for _ in range(n):
        out.append(f'{m:02d}/{y}')
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _form(mode=es.MODE_EXISTING, prior=2026, city='TP. Hồ Chí Minh', actuals=(), lines=None):
    """An in-memory input workbook with the Existing-project fields and the utilities sheet, invented data.
    actuals: (line, month, amount, includes VAT, consumption); lines: {line: (category, bill price, source,
    approved, approved includes VAT, override, reason code, reason note)}."""
    wb = openpyxl.Workbook()
    pi = wb.active
    pi.title = 'Project Info'
    pi['A1'], pi['B1'] = 'Project Name', 'ZZ Test (TEST DATA)'
    pi['A2'], pi['B2'] = 'City / Province — leave blank if unknown', city
    bpf.add_existing_project_fields(pi, 4)
    for r in range(1, 12):
        label = str(pi.cell(row=r, column=1).value or '')
        if label == es.MODE_LABEL:
            pi.cell(row=r, column=2, value=mode)
        elif label.startswith(es.PRIOR_YEAR_LABEL):
            pi.cell(row=r, column=2, value=prior)
    ws = bpf.add_prior_year_utilities_sheet(wb)

    def first_row(title):
        return next(r for r in range(1, ws.max_row + 1)
                    if es.normalise(ws.cell(row=r, column=1).value) == es.normalise(title)) + 2
    r = first_row(eu.SEC_ACTUALS)
    for i, row in enumerate(actuals):
        for c, v in enumerate(row, 1):
            ws.cell(row=r + i, column=c, value=v)
    r = first_row(eu.SEC_LINES)
    for i in range(len(eu.LINES)):
        line = ws.cell(row=r + i, column=1).value
        for c, v in enumerate((lines or {}).get(line, ()), 2):
            ws.cell(row=r + i, column=c, value=v)
    return wb


def _read(wb):
    return eu.read_utilities(wb, SheetLabels(wb['Project Info']))


def _year(line, start=(2025, 9), n=12, amount=None, consumption=None, incl='Yes'):
    return [(line, m, amount, incl, consumption) for m in _months(*start, n)]


def _both(n=12, start=(2025, 9), e_kwh=20_000, w_m3=1_000):
    """Both lines with consumption on the bill and amounts that match the invented table exactly."""
    out = []
    for mo in _months(*start, n):
        mm, yy = (int(x) for x in mo.split('/'))
        e_price = (1000 if (yy, mm) < (2025, 6) else 1100) * 1.08
        out.append(('EEE.C', mo, round(e_kwh * e_price), 'Yes', e_kwh))
        out.append(('EEW.C', mo, round(w_m3 * W_2026_INCL), 'Yes', w_m3))
    return out


def _compute(wb, rows, budget_year=2027, incl_vat=True):
    return eu.compute(_read(wb), budget_year, incl_vat, rows=rows)


def _ties(lr):
    b = lr.bridge
    return abs(b['baseline'] + b['tariff'] + b['vat'] + b['override'] + b['rounding'] - lr.annual) < 1e-6 \
        and abs(sum(lr.amounts) - lr.annual) < 1e-6 and abs(b['rounding']) <= 12


# ---------------------------------------------------------------- reading (2.3)
def test_new_prospect_returns_none_even_with_figures():
    wb = _form(mode=es.MODE_NEW, actuals=_both())
    assert _read(wb) is None


def test_existing_without_the_sheet_stops_naming_it():
    wb = _form()
    del wb[eu.SHEET]
    with pytest.raises(LabelNotFound, match=eu.SHEET):
        _read(wb)


def test_a_renamed_block_title_stops():
    wb = _form()
    ws = wb[eu.SHEET]
    row = next(r for r in range(1, 60) if ws.cell(row=r, column=1).value == eu.SEC_LINES)
    ws.cell(row=row, column=1, value='UTILITY SETTINGS')
    with pytest.raises(LabelNotFound, match=eu.SEC_LINES):
        _read(wb)


def test_a_duplicate_month_stops_naming_both_rows():
    wb = _form(actuals=[('EEE.C', '05/2026', 1_000_000, 'Yes', None), ('EEE.C', '05/2026', 1_100_000, 'Yes', None)])
    with pytest.raises(ValueError, match=r'two rows for 05/2026.*rows 6 and 7'):
        _read(wb)


@pytest.mark.parametrize('row, message', [
    (('EEE.C', '05/2026', -5, 'Yes', None), 'negative'),
    (('EEX.C', '05/2026', 5, 'Yes', None), 'must be one of'),
    (('EEE.C', 'May 2026', 5, 'Yes', None), 'MM/YYYY'),
    (('EEE.C', '05/2026', 5, None, None), 'Includes VAT'),
])
def test_bad_rows_stop(row, message):
    with pytest.raises(ValueError, match=message):
        _read(_form(actuals=[row]))


def test_unknown_category_stops():
    with pytest.raises(ValueError, match='allowed for EEE.C'):
        _read(_form(lines={'EEE.C': ('Sinh hoạt',)}))


def test_a_month_in_the_budget_year_stops(rows):
    wb = _form(actuals=_both() + [('EEE.C', '01/2027', 5, 'Yes', None)])
    with pytest.raises(ValueError, match='in or after the budget year 2027'):
        _compute(wb, rows)


# ---------------------------------------------------------------- baseline (3.1)
def test_twelve_months_over_two_years(rows):
    res = _compute(_form(actuals=_both()), rows)
    e = res.lines['EEE.C']
    assert e.window == ((2025, 9), (2026, 8)) and len(e.months) == 12 and e.basis == 'actual'
    assert e.q_bar == pytest.approx(20_000)
    assert e.amounts == [round(20_000 * E_2027_INCL)] * 12
    assert res.lines['EEW.C'].amounts == [round(1_000 * W_2027_INCL)] * 12


def test_older_months_are_ignored_and_counted(rows):
    res = _compute(_form(actuals=_both(n=15, start=(2025, 6))), rows)   # 30 rows: the block's size
    e = res.lines['EEE.C']
    assert e.window == ((2025, 9), (2026, 8)) and e.ignored_older == 3
    assert any('3 tháng cũ hơn' in f for f in e.flags)


def test_a_blank_month_is_missing(rows):
    acts = [a for a in _both() if not (a[0] == 'EEE.C' and a[1] == '03/2026')]
    acts.append(('EEE.C', '03/2026', None, None, None))
    e = _compute(_form(actuals=acts), rows).lines['EEE.C']
    assert len(e.months) == 11 and e.missing_months == [(2026, 3)]
    assert e.flags[0].startswith('chỉ có 11/12 tháng')


def test_a_zero_month_counts_and_is_flagged(rows):
    acts = [a for a in _both() if not (a[0] == 'EEW.C' and a[1] == '02/2026')]
    acts.append(('EEW.C', '02/2026', 0, 'Yes', None))
    w = _compute(_form(actuals=acts), rows).lines['EEW.C']
    assert len(w.months) == 12 and w.q_bar == pytest.approx(1_000 * 11 / 12)
    assert any('02/2026: số tiền bằng 0' in f for f in w.flags)


def test_amount_only_is_derived_with_the_real_table():
    """The spec's worked example: 48,081,600 VND incl. 8% VAT at the default rate = 20,000 kWh."""
    acts = [('EEE.C', m, 48_081_600, 'Yes', None) for m in _months(2025, 9, 12)]
    acts += [('EEW.C', m, 1_000_000, 'Yes', None) for m in _months(2025, 9, 12)]
    e = eu.compute(_read(_form(actuals=acts)), 2027, True).lines['EEE.C']
    assert all(mu.derived for mu in e.months)
    assert e.q_bar == pytest.approx(20_000)


def test_a_bill_rate_off_by_more_than_one_percent_is_flagged(rows):
    acts = [a for a in _both() if not (a[0] == 'EEE.C' and a[1] == '04/2026')]
    acts.append(('EEE.C', '04/2026', round(20_000 * 3152 * 1.08), 'Yes', 20_000))
    e = _compute(_form(actuals=acts), rows).lines['EEE.C']
    assert any('04/2026' in f and 'loại giá' in f for f in e.flags)


# ---------------------------------------------------------------- fewer months (3.2)
def test_eight_months(rows):
    e = _compute(_form(actuals=_both(n=8, start=(2026, 1))), rows).lines['EEE.C']
    assert e.basis == 'actual' and len(e.months) == 8 and sum(e.amounts) == pytest.approx(12 * round(20_000 * E_2027_INCL))
    assert e.flags[0].startswith('chỉ có 8/12 tháng')


def test_two_months_with_an_approved_amount(rows):
    acts = _both(n=2, start=(2026, 7))
    lines = {'EEE.C': ('', None, '', 300_000_000, 'Yes'), 'EEW.C': ('', None, '', 20_000_000, 'Yes')}
    e = _compute(_form(actuals=acts, lines=lines), rows).lines['EEE.C']
    assert e.basis == 'approved'
    # 2026 at 1,100 + 8% every month, 2027 at 1,100 + 10%: only VAT moves the figure.
    assert e.annual == pytest.approx(300_000_000 * 1.10 / 1.08, abs=12)
    assert e.bridge['consumption'] == pytest.approx(0, abs=1e-6) and e.bridge['tariff'] == pytest.approx(0, abs=1e-6)
    assert any('dùng số NS 2026 đã duyệt' in f for f in e.flags)


def test_two_months_without_an_approved_amount_stops(rows):
    with pytest.raises(ValueError, match="EEE.C: .*2 month\\(s\\).*Prior-Year Approved"):
        _compute(_form(actuals=_both(n=2, start=(2026, 7))), rows)


def test_an_empty_sheet_stops(rows):
    with pytest.raises(ValueError, match='0 month'):
        _compute(_form(), rows)


# ---------------------------------------------------------------- budget year and bridge (3.3)
@pytest.mark.parametrize('incl_vat', [True, False])
def test_the_bridge_ties_on_both_vat_bases(rows, incl_vat):
    acts = _both(n=12, start=(2025, 3))          # window starts before the 10/05/2025 price step
    lines = {'EEE.C': ('', None, '', 250_000_000, 'Yes', 22_000, 'Mở dịch vụ hoặc tiện ích mới', 'clubhouse'),
             'EEW.C': ('', None, '', 15_000_000, 'No')}
    res = _compute(_form(actuals=acts, lines=lines), rows, incl_vat=incl_vat)
    for lr in res.lines.values():
        assert _ties(lr)
    e = res.lines['EEE.C']
    assert e.q_budget == 22_000
    if incl_vat:
        assert e.bridge['vat'] > 0
    else:
        assert e.bridge['vat'] == pytest.approx(0, abs=1e-6)
        assert e.amounts == [round(22_000 * 1100)] * 12


def test_exclusive_model_has_no_vat(rows):
    res = _compute(_form(actuals=_both()), rows, incl_vat=False)
    assert res.lines['EEW.C'].amounts == [round(1_000 * 13_000)] * 12


# ---------------------------------------------------------------- overrides and reasons (3.4)
@pytest.mark.parametrize('code, note, message', [
    ('', '', 'THIẾU LÝ DO'),
    (es.REASON_OTHER, '', 'THIẾU GHI CHÚ'),
    ('Theo yêu cầu của cư dân hoặc chủ sở hữu', '', 'KHÔNG CÓ TRONG DANH SÁCH'),
])
def test_an_override_without_a_valid_reason_stops(rows, code, note, message):
    lines = {'EEE.C': ('', None, '', None, None, 25_000, code, note)}
    with pytest.raises(ValueError, match=message):
        _compute(_form(actuals=_both(), lines=lines), rows)


def test_each_reason_code_is_accepted(rows):
    for code in eu.REASON_CODES:
        lines = {'EEE.C': ('', None, '', None, None, 25_000, code, 'ghi chú')}
        e = _compute(_form(actuals=_both(), lines=lines), rows).lines['EEE.C']
        assert e.reasons[-1]['source'] == es.SOURCE_PM and e.q_budget == 25_000


def test_water_outside_hcmc_without_a_bill_price_stops(rows):
    with pytest.raises(ValueError, match='City / Province'):
        _compute(_form(city='Bình Dương', actuals=_both()), rows)


# ---------------------------------------------------------------- remarks (4.2)
def test_remark_sentences(rows):
    lines = {'EEE.C': ('', None, '', 250_000_000, 'Yes', 22_000, 'Thay đổi giờ vận hành', 'mở thêm ca')}
    acts = [a for a in _both() if not (a[0] == 'EEW.C' and a[1] == '02/2026')] + [('EEW.C', '02/2026', 0, 'Yes', None)]
    res = _compute(_form(actuals=acts, lines=lines), rows)
    text = eu.narrative_vi(res, 'EEE.C') + eu.adjustment_sentence(res, 'EEE.C')
    assert 'Điều chỉnh so với NS 2026: 250,000,000 →' in text
    assert '22,000 kWh/tháng' in text and '09/2025–08/2026' in text and 'VAT 8% → 10%' in text
    assert 'Thay đổi giờ vận hành: mở thêm ca' in text
    assert 'lấp đầy' not in text and '40%' not in text
    water = eu.narrative_vi(res, 'EEW.C') + eu.adjustment_sentence(res, 'EEW.C')
    assert 'không có số NS đã duyệt để so sánh' in water and '02/2026: số tiền bằng 0' in water
    assert 'thoát nước và xử lý nước thải 30%' in water


def test_remarks_name_the_months_used_not_the_window(rows):
    # 7.2 back-test: 8 months 01-08/2026 sit in the window 09/2025-08/2026; the remark must not read as if
    # the 8 months ran from 09/2025.
    res = _compute(_form(actuals=_both(n=8, start=(2026, 1))), rows)
    text = eu.narrative_vi(res, 'EEE.C') + eu.adjustment_sentence(res, 'EEE.C')
    assert 'bình quân 8 tháng (01/2026–08/2026)' in text and 'bình quân 8 tháng 01/2026–08/2026:' in text
    assert '8 tháng (09/2025–08/2026)' not in text
    assert 'chỉ có 8/12 tháng thực chi trong kỳ 09/2025–08/2026' in text


def test_an_approved_amount_on_another_vat_basis_is_quoted_as_approved(rows):
    # 7.2 back-test: the client knows the approved amount as approved (excl. VAT); the deliverable is incl.
    # VAT, so the sentence quotes both. 2026 electricity VAT is 8% all year: 300,000,000 -> 324,000,000.
    lines = {'EEE.C': ('', None, '', 300_000_000, 'No')}
    res = _compute(_form(actuals=_both(), lines=lines), rows)
    text = eu.adjustment_sentence(res, 'EEE.C')
    assert ('Điều chỉnh so với NS 2026: NS đã duyệt 300,000,000 VND/năm (chưa gồm VAT), '
            'tương đương 324,000,000 VND/năm gồm VAT →') in text
    same = eu.adjustment_sentence(_compute(_form(actuals=_both(), lines=lines), rows, incl_vat=False), 'EEE.C')
    assert 'Điều chỉnh so với NS 2026: 300,000,000 →' in same and 'tương đương' not in same


# ------------------------------------- water groups as choices (change apply-head-of-pm-decisions-2026-10, 2.4)
@pytest.fixture
def rows_with_groups(tmp_path):
    table = TABLE + [
        f'water,"{ut.CAT_W_BUSINESS}",base,20000,VND/m3,2024-01-01,,TP.HCM,Listing Y,,2026-10-18,',
        f'water,"{ut.CAT_W_ADMIN}",base,12000,VND/m3,2024-01-01,,TP.HCM,Listing Z,,2026-10-18,',
    ]
    path = tmp_path / 'Ref_UtilityTariffs.csv'
    path.write_text(','.join(ut.COLUMNS) + '\n' + '\n'.join(table) + '\n', encoding='utf-8')
    return ut.load_rows(str(path))


def test_a_blank_water_category_keeps_the_household_default(rows_with_groups):
    res = _compute(_form(actuals=_both()), rows_with_groups)
    assert res.lines['EEW.C'].category == ut.CAT_W_HCMC
    assert res.lines['EEW.C'].budget_prices[0].base == 10000


@pytest.mark.parametrize('group, base', [(ut.CAT_W_BUSINESS, 20000), (ut.CAT_W_ADMIN, 12000)])
def test_choosing_a_water_group_prices_water_from_its_rows(rows_with_groups, group, base):
    default = _compute(_form(actuals=_both()), rows_with_groups).lines['EEW.C']
    chosen = _compute(_form(actuals=_both(), lines={'EEW.C': (group,)}), rows_with_groups).lines['EEW.C']
    assert chosen.category == group and chosen.budget_prices[0].base == base
    assert chosen.annual != default.annual
    # electricity is untouched by a water choice
    assert _compute(_form(actuals=_both(), lines={'EEW.C': (group,)}), rows_with_groups).lines['EEE.C'].annual == \
        _compute(_form(actuals=_both()), rows_with_groups).lines['EEE.C'].annual


def test_the_water_dropdown_offers_the_two_new_groups():
    assert ut.CAT_W_BUSINESS in ut.CATEGORIES[ut.WATER] and ut.CAT_W_ADMIN in ut.CATEGORIES[ut.WATER]
    assert ut.DEFAULT_CATEGORY[ut.WATER] == ut.CAT_W_HCMC
