"""Unit tests for utility_tariffs.py (the dated price table behind Existing-project EEE.C / EEW.C).

Covered: load_rows validation, month prices on both VAT bases, a VAT step on 1 January, a mid-year base change,
categories that need a bill price, the HCMC-only water default, the bill price winning, region_of.

One test reads the real Ref_UtilityTariffs.csv, as test_labor_law_params.py does for its table: it holds public
prices, not client data, and the test stops a row without its legal basis from reaching a budget. Every other test
writes an invented table to a temporary folder.
"""
import pytest

import utility_tariffs as ut

HEADER = ','.join(ut.COLUMNS) + '\n'
LT6 = ut.CAT_E_LT6
W = ut.CAT_W_HCMC
# Invented prices: electricity base 1,000 then 1,100 from 2025-05-10; general VAT 8% to 2026-12-31 then 10%
# (shared by electricity and the drainage charge); insurance VAT 10%.
# Water base 10,000 in HCMC, drainage charge 30%, clean-water VAT 5%; business water base 20,000.
# Diesel listed at 21,600 incl. 8% VAT from 2026-10-01.
BASE_ROWS = [
    f'electricity,"{LT6}",base,1000,VND/kWh,2024-01-01,2025-05-09,,Decision A,,2026-10-11,',
    f'electricity,"{LT6}",base,1100,VND/kWh,2025-05-10,,,Decision B,,2026-10-11,',
    'vat,general,vat_pct,8,%,2024-01-01,2026-12-31,,Resolution C,,2026-10-11,',
    'vat,general,vat_pct,10,%,2027-01-01,,,Law D,,2026-10-11,',
    'vat,insurance,vat_pct,10,%,2024-01-01,,,Law D art. 5,,2026-10-11,',
    'diesel,DO test,listed_price,21600,VND/l,2026-10-01,,,Listing X,,2026-10-11,',
    'diesel,DO test,listed_vat_pct,8,%,2026-10-01,,,Resolution C,,2026-10-11,',
    f'water,"{W}",base,10000,VND/m3,2024-01-01,,TP.HCM,Decision E,,2026-10-11,',
    'water,,wastewater_pct,30,%,2024-01-01,,TP.HCM,Decision F,,2026-10-11,',
    'water,,vat_pct,5,%,2024-01-01,,,Law G,,2026-10-11,',
    f'water,"{ut.CAT_W_BUSINESS}",base,20000,VND/m3,2024-01-01,,TP.HCM,Listing Y,,2026-10-11,',
]


def _rows(tmp_path, rows=BASE_ROWS):
    path = tmp_path / 'Ref_UtilityTariffs.csv'
    path.write_text(HEADER + '\n'.join(rows) + '\n', encoding='utf-8')
    return ut.load_rows(str(path))


def test_real_table_loads_and_every_row_has_its_basis():
    rows = ut.load_rows()
    assert rows, 'the real table is empty'
    assert all(r['legal_basis'] and r['effective_from'] for r in rows)
    # the defaults price a 2027 month without a bill price
    e = ut.LineTariff(ut.ELECTRICITY, rows=rows).month(2027, 1)
    assert e.base == 2226 and e.vat_pct == 10
    w = ut.LineTariff(ut.WATER, region=ut.HCMC, rows=rows).month(2027, 1)
    assert w.base == 14400 and w.wastewater_pct == 30


@pytest.mark.parametrize('broken, message', [
    (f'electricity,"{LT6}",base,1000,VND/kWh,2024-01-01,,,,,2026-10-11,', 'legal_basis is blank'),
    (f'electricity,"{LT6}",base,1000,VND/kWh,,,,Decision A,,2026-10-11,', 'effective_from is blank'),
    (f'gas,"{LT6}",base,1000,VND/kWh,2024-01-01,,,Decision A,,2026-10-11,', 'utility must be one of'),
    (f'electricity,"{LT6}",tax,1000,VND/kWh,2024-01-01,,,Decision A,,2026-10-11,', 'component must be one of'),
])
def test_a_row_without_its_basis_or_date_is_rejected(tmp_path, broken, message):
    with pytest.raises(ut.TariffError, match=message):
        _rows(tmp_path, BASE_ROWS + [broken])


def test_electricity_on_both_vat_bases(tmp_path):
    p = ut.LineTariff(ut.ELECTRICITY, rows=_rows(tmp_path)).month(2026, 3)
    assert p.price(incl_vat=False) == pytest.approx(1100)
    assert p.price(incl_vat=True) == pytest.approx(1100 * 1.08)


def test_water_on_both_vat_bases(tmp_path):
    p = ut.LineTariff(ut.WATER, region=ut.HCMC, rows=_rows(tmp_path)).month(2026, 3)
    assert p.price(incl_vat=False) == pytest.approx(10000 * 1.30)
    assert p.price(incl_vat=True) == pytest.approx(10000 * 1.05 + 3000 * 1.08)


def test_vat_steps_up_on_1_january(tmp_path):
    t = ut.LineTariff(ut.ELECTRICITY, rows=_rows(tmp_path))
    assert t.month(2026, 12).vat_pct == 8
    assert all(t.month(2027, m).vat_pct == 10 for m in range(1, 13))
    w = ut.LineTariff(ut.WATER, region=ut.HCMC, rows=_rows(tmp_path))
    assert w.month(2027, 1).wastewater_vat_pct == 10 and w.month(2027, 1).vat_pct == 5


def test_mid_year_base_change_takes_the_price_on_the_first_of_the_month(tmp_path):
    t = ut.LineTariff(ut.ELECTRICITY, rows=_rows(tmp_path))
    assert t.month(2025, 5).base == 1000      # in force on 1 May (the new price starts 10 May)
    assert t.month(2025, 6).base == 1100


def test_a_month_before_the_table_stops(tmp_path):
    with pytest.raises(ut.TariffError, match='in force on 01/12/2023'):
        ut.LineTariff(ut.ELECTRICITY, rows=_rows(tmp_path)).month(2023, 12)


def test_business_electricity_needs_a_bill_price(tmp_path):
    with pytest.raises(ut.TariffError, match='has no single table price'):
        ut.LineTariff(ut.ELECTRICITY, category=ut.CAT_E_BILL, rows=_rows(tmp_path))
    p = ut.LineTariff(ut.ELECTRICITY, category=ut.CAT_E_BILL, bill_price=3152, rows=_rows(tmp_path)).month(2027, 2)
    assert p.base == 3152 and p.vat_pct == 10 and p.bill


@pytest.mark.parametrize('region', ['', 'Bình Dương'])
def test_hcmc_water_default_outside_hcmc_stops(tmp_path, region):
    with pytest.raises(ut.TariffError, match='City / Province'):
        ut.LineTariff(ut.WATER, region=region, rows=_rows(tmp_path))


def test_bill_price_wins_and_outside_hcmc_has_no_drainage_charge(tmp_path):
    p = ut.LineTariff(ut.WATER, category=ut.CAT_W_BILL, region='Bình Dương', bill_price=12000,
                      rows=_rows(tmp_path)).month(2027, 6)
    assert p.base == 12000 and p.wastewater_pct == 0
    assert p.price(incl_vat=True) == pytest.approx(12000 * 1.05)
    h = ut.LineTariff(ut.WATER, region=ut.HCMC, bill_price=21300, rows=_rows(tmp_path)).month(2027, 6)
    assert h.base == 21300 and h.wastewater_pct == 30


def test_unknown_category_is_rejected(tmp_path):
    with pytest.raises(ut.TariffError, match='is not one of'):
        ut.LineTariff(ut.ELECTRICITY, category='Sinh hoạt', rows=_rows(tmp_path))


@pytest.mark.parametrize('typed, expected', [
    ('TP. Hồ Chí Minh', ut.HCMC), ('Ho Chi Minh City', ut.HCMC), ('HCM', ut.HCMC), ('tphcm', ut.HCMC),
    ('Sài Gòn', ut.HCMC), ('', ''), (None, ''), ('Hà Nội', 'Hà Nội'),
])
def test_region_of(typed, expected):
    assert ut.region_of(typed) == expected


def test_year_note_only_when_no_newer_price(tmp_path):
    t = ut.LineTariff(ut.ELECTRICITY, rows=_rows(tmp_path))
    assert 'năm 2027' in t.year_note(2027) and '10/05/2025' in t.year_note(2027)
    assert t.year_note(2025) == ''


# ---- group 2 of apply-head-of-pm-decisions-2026-10: the general VAT rate, insurance VAT, diesel ----

def test_general_vat_is_8_then_10_and_insurance_stays_10(tmp_path):
    rows = _rows(tmp_path)
    assert ut.vat_rate(2026, 12, rows=rows) == 8
    assert ut.vat_rate(2027, 1, rows=rows) == 10
    assert ut.vat_rate(2026, 6, ut.VAT_INSURANCE, rows=rows) == 10
    assert ut.vat_rate(2027, 6, ut.VAT_INSURANCE, rows=rows) == 10


def test_vat_rate_unknown_kind_and_uncovered_month_stop(tmp_path):
    rows = _rows(tmp_path)
    with pytest.raises(ut.TariffError, match='Unknown VAT kind'):
        ut.vat_rate(2027, 1, 'luxury', rows=rows)
    with pytest.raises(ut.TariffError, match='no general VAT rate in force on 01/12/2023'):
        ut.vat_rate(2023, 12, rows=rows)


def test_electricity_and_drainage_charge_follow_the_general_vat_row(tmp_path):
    rows = _rows(tmp_path)
    e = ut.LineTariff(ut.ELECTRICITY, rows=rows).month(2027, 1)
    assert e.vat_pct == 10 and e.rows['vat_pct']['utility'] == ut.VAT
    w = ut.LineTariff(ut.WATER, region=ut.HCMC, rows=rows).month(2026, 1)
    assert w.wastewater_vat_pct == 8 and w.rows['wastewater_vat_pct']['category'] == ut.VAT_GENERAL
    assert w.vat_pct == 5      # clean water keeps its own 5% row


def test_diesel_listed_price_is_split_and_repriced_at_the_month_vat(tmp_path):
    rows = _rows(tmp_path)
    d26 = ut.diesel_price(2026, 11, 'DO test', rows=rows)
    assert d26.net() == pytest.approx(20000) and d26.gross() == pytest.approx(21600)
    d27 = ut.diesel_price(2027, 3, 'DO test', rows=rows)
    assert d27.gross() == pytest.approx(21600 / 1.08 * 1.10)
    with pytest.raises(ut.TariffError, match='no diesel listed_price'):
        ut.diesel_price(2026, 9, 'DO test', rows=rows)


def test_a_second_water_group_has_its_own_base_but_the_same_charges(tmp_path):
    rows = _rows(tmp_path)
    p = ut.LineTariff(ut.WATER, category=ut.CAT_W_BUSINESS, region=ut.HCMC, rows=rows).month(2027, 1)
    assert p.base == 20000 and p.wastewater_pct == 30 and p.vat_pct == 5 and p.wastewater_vat_pct == 10


def test_real_table_general_vat_insurance_diesel_and_water_groups():
    rows = ut.load_rows()
    assert ut.vat_rate(2026, 12, rows=rows) == 8 and ut.vat_rate(2027, 1, rows=rows) == 10
    assert ut.vat_rate(2026, 12, ut.VAT_INSURANCE, rows=rows) == 10
    d = ut.diesel_price(2027, 1, rows=rows)
    assert d.listed == 29710 and d.listed_vat_pct == 8
    assert d.gross() == pytest.approx(29710 / 1.08 * 1.10) and round(d.gross()) == 30260
    biz = ut.LineTariff(ut.WATER, category=ut.CAT_W_BUSINESS, region=ut.HCMC, rows=rows)
    adm = ut.LineTariff(ut.WATER, category=ut.CAT_W_ADMIN, region=ut.HCMC, rows=rows)
    # all-in per m3: base x 1.05 + 30% drainage charge x (1 + month's VAT)
    assert biz.month(2026, 6).gross() == pytest.approx(29266, abs=1) and adm.month(2026, 6).gross() == pytest.approx(17862, abs=1)
    assert biz.month(2027, 1).gross() == pytest.approx(29394, abs=1) and adm.month(2027, 1).gross() == pytest.approx(17940, abs=1)
