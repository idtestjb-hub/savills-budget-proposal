"""Unit tests for estimate_opex.py (utilities and pool-salt estimate for a new project).

Covered: _tariff_year, _coerce_volume, _pool_salt, estimate_opex (usage x tariff for the three
energy lines, plain per-m2 ratio for the others, stale-tariff flag, parking reference text,
pool-salt method and fallback).
Not covered: the wording of the long Vietnamese/English source strings beyond the key figures.

Invented data only. estimate_opex finds the usage reference and the reference-only parking building through the
reference-project registry (roles utilities_base and parking_base) and selects Fact_OPEX rows by RefKey; the fixture
writes an invented registry (two rows, R02 = 'Tháp Thử Nghiệm' with 1,000 m², R08 = 'Bãi Xe Thử') and an invented
Fact_OPEX with those keys. OPEX_CSV and the registry path are patched, so no real data file is read.

Rule sources: docs/05-decisions.md D9 (energy = usage x tariff, usage stored fixed, tariff a
separate dated input) and the pool-salt section (blank, 0 and non-numeric mean "unknown", 2.5 kg x
6,000 VND/kg per m3 per month); the rest is stated in code comments only.
"""
import csv

import pytest

import estimate_opex as eo
import reference_projects as rp

HEADER = ['Project', 'Category', 'MonthlyVND', 'Source', 'Quantity', 'Unit', 'UnitPrice', 'PriceAsOf', 'RefKey']
BASE, PARKING = 'Tháp Thử Nghiệm', 'Bãi Xe Thử'

# Reference building: 1,000 m2. Electricity monthly cost (900,000) is deliberately NOT quantity x
# price (400 x 2,000 = 800,000): only the stored quantity may drive the estimate.
ROWS = [
    (BASE, 'Electricity', 900000, 'usage src  TARIFF: tariff src', 400, 'kWh/month', 2000, '2026-05-09', 'R02'),
    (BASE, 'Water', 5000000, 'water src', 1000, 'm3/month', 10000, '2027-01-01', 'R02'),
    (BASE, 'Diesel (Generator Fuel)', 500000, 'diesel src', '', '', '', '', 'R02'),
    (BASE, 'Repairs & Maintenance (materials only)', 640000, 'rm src', '', '', '', '', 'R02'),
    (BASE, 'Administrative Expense (office overhead)', 320000, 'admin src', '', '', '', '', 'R02'),
    (BASE, 'Pool Salt', 3000000, 'pool src', '', '', '', '', 'R02'),
    (PARKING, 'Electricity', 100000, 'p src', 50, 'kWh/month', 2000, '2026-01-01', 'R08'),
    (PARKING, 'Diesel (Generator Fuel)', 70000, 'p src', '', '', '', '', 'R08'),
]


def write_csv(path, rows):
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows)
    return str(path)


def replace_row(rows, project, category, **changes):
    out = []
    for r in rows:
        if (r[0], r[1]) == (project, category):
            d = dict(zip(HEADER, r))
            d.update(changes)
            r = tuple(d[h] for h in HEADER)
        out.append(r)
    return out


REGISTRY_ROWS = [
    dict(RefKey='R02', DisplayName=BASE, Aliases='', TotalNFA_m2='1000', CapexNFA_m2='1000', ApartmentUnits='10',
         TotalUnits='10', MgmtRate_VND_m2_month='', MgmtRateVAT='', District='Quận 1', City='Hồ Chí Minh', Comparable='1',
         ExcludedFromRanking='', Roles='utilities_base|capex_items', Source='test', LocationSource='test', VerifiedOn='2026-11-06'),
    dict(RefKey='R08', DisplayName=PARKING, Aliases='', TotalNFA_m2='', CapexNFA_m2='', ApartmentUnits='0', TotalUnits='0',
         MgmtRate_VND_m2_month='', MgmtRateVAT='', District='', City='', Comparable='0', ExcludedFromRanking='no apartments',
         Roles='parking_base', Source='test', LocationSource='', VerifiedOn='2026-11-06'),
]


def write_registry(path, rows=REGISTRY_ROWS):
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=rp.COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return str(path)


@pytest.fixture
def opex(tmp_path, monkeypatch):
    # The utilities base has 1,000 m² in the invented registry; the real registry is never read.
    monkeypatch.setattr(rp, 'REGISTRY_CSV', write_registry(tmp_path / 'Dim_ReferenceProject_invented.csv'))
    rp.clear_cache()

    def load(rows=ROWS):
        monkeypatch.setattr(eo, 'OPEX_CSV', write_csv(tmp_path / 'Fact_OPEX_invented.csv', rows))
        return eo

    return load


# ---------------------------------------------------------------- _tariff_year

@pytest.mark.parametrize('text, year', [
    ('2025-05-09', 2025),
    ('~2020 (old figure)', 2020),
    ('2027', 2027),
    ('12-2025', 2025),        # a 2-digit run is not a year
    ('May 9, 2024', 2024),
    ('2025-2030', 2025),      # first run wins
    ('202', None),
    ('no date', None),
    ('', None),
    (None, None),
])
def test_tariff_year_takes_first_four_digit_run(text, year):
    # rule source: docstring ("First 4-digit run in a PriceAsOf string, or None")
    assert eo._tariff_year(text) == year


# ---------------------------------------------------------------- _coerce_volume

@pytest.mark.parametrize('value, expected', [
    (440, 440.0), (440.5, 440.5), ('440', 440.0), (' 440 ', 440.0), ('0.5', 0.5),
])
def test_coerce_volume_accepts_positive_numbers(value, expected):
    assert eo._coerce_volume(value) == expected


@pytest.mark.parametrize('value', [0, 0.0, -1, -440, '', '   ', None, 'abc', '12,5', float('nan'), [], {}])
def test_coerce_volume_blank_zero_negative_and_non_numeric_mean_unknown(value):
    # rule source: docs/05-decisions.md pool section ("Blank, 0 and non-numeric all mean unknown")
    # '12,5' (decimal comma) is not parsed: it falls back to unknown. Not settled for Vietnamese input.
    assert eo._coerce_volume(value) is None


# ---------------------------------------------------------------- _pool_salt

def test_pool_salt_with_volume_is_volume_x_2_5kg_x_6000(opex):
    # docs/05-decisions.md worked example: 440 m3 x 2.5 kg x 6,000 VND/kg x 12 = 79,200,000 a year
    got = eo._pool_salt(440, 123456)
    assert got['monthly_vnd'] * 12 == 79_200_000
    assert got['monthly_vnd'] == 6_600_000
    assert got['pool_volume_m3'] == 440.0
    assert got['ratio_per_m2'] is None
    assert '79,200,000' in got['method']


def test_pool_salt_range_is_reported_with_the_figure(opex):
    # docs/05-decisions.md: 440 m3 reads "31,680,000 to 126,720,000" a year (1 kg to 4 kg)
    got = eo._pool_salt(440, 123456)
    assert '31,680,000' in got['source'] and '126,720,000' in got['source']


def test_pool_salt_scales_linearly_with_volume():
    assert eo._pool_salt(220, 1)['monthly_vnd'] * 2 == eo._pool_salt(440, 1)['monthly_vnd']


def test_pool_salt_string_volume_is_used(opex):
    assert eo._pool_salt('440', 1)['monthly_vnd'] == 6_600_000


@pytest.mark.parametrize('volume', [None, '', 0, -5, 'abc'])
def test_pool_salt_unknown_volume_falls_back_to_flat_figure_and_says_so(volume):
    got = eo._pool_salt(volume, 3_000_000)
    assert got['monthly_vnd'] == 3_000_000
    assert got['pool_volume_m3'] is None
    assert got['method'].startswith('DỰ PHÒNG')
    assert '200 m³' in got['method']          # 3,000,000 / (2.5 x 6,000) = 200 m3 implied by the flat figure


def test_pool_salt_fallback_is_not_a_zero_volume_pool():
    assert eo._pool_salt(0, 3_000_000)['monthly_vnd'] != 0


# ---------------------------------------------------------------- estimate_opex: energy lines

def test_energy_line_is_stored_quantity_times_project_nfa_times_tariff(opex):
    got = opex().estimate_opex(2000)['Electricity']
    # usage 400 kWh / 1,000 m2 = 0.4 per m2; x 2,000 m2 = 800 kWh; x 2,000 VND = 1,600,000
    assert got['monthly_vnd'] == 1_600_000
    assert got['usage_per_m2'] == 0.4
    assert got['project_quantity_month'] == 800.0
    assert got['ratio_per_m2'] == 800.0           # 0.4 kWh/m2 x 2,000 VND
    assert got['tariff'] == 2000 and got['tariff_unit'] == 'VND/kWh'
    assert got['usage_unit'] == 'kWh/month'
    assert got['tariff_as_of'] == '2026-05-09'


def test_energy_estimate_does_not_use_the_stored_monthly_cost(opex):
    # stored cost 900,000 would imply 450 kWh; the stored quantity 400 must win
    mod = opex()
    low = mod.estimate_opex(1000)['Electricity']['monthly_vnd']
    assert low == 800_000


def test_changing_the_tariff_moves_the_figure_in_proportion(opex):
    base = opex().estimate_opex(2000)['Electricity']['monthly_vnd']
    moved = opex(replace_row(ROWS, BASE, 'Electricity', UnitPrice=3000)).estimate_opex(2000)['Electricity']
    assert base == 1_600_000
    assert moved['monthly_vnd'] == 2_400_000      # same stored quantity, 50% higher tariff
    assert moved['tariff'] == 3000


def test_energy_figure_scales_with_nfa_and_is_zero_for_zero_nfa(opex):
    mod = opex()
    assert mod.estimate_opex(0)['Electricity']['monthly_vnd'] == 0
    assert mod.estimate_opex(4000)['Electricity']['monthly_vnd'] == 2 * mod.estimate_opex(2000)['Electricity']['monthly_vnd']


def test_water_uses_its_own_unit_and_tariff(opex):
    got = opex().estimate_opex(500)['Water']
    assert got['monthly_vnd'] == 5_000_000        # 1.0 m3/m2 x 500 m2 x 10,000
    assert got['tariff_unit'] == 'VND/m3'


@pytest.mark.parametrize('as_of, stale', [
    ('2026-12-31', True),     # before 2027: stale
    ('~2020 (old)', True),
    ('2027-01-01', False),    # the 2027 budget year itself is not stale
    ('2028-03-01', False),
    ('', False),              # not settled: an undated tariff is silently not flagged stale
])
def test_tariff_stale_flag_is_before_2027(opex, as_of, stale):
    # rule source: code comment only (_TARIFF_STALE_BEFORE_YEAR = 2027)
    rows = replace_row(ROWS, BASE, 'Electricity', PriceAsOf=as_of)
    assert opex(rows).estimate_opex(1000)['Electricity']['tariff_stale'] is stale


def test_energy_row_without_a_tariff_is_a_plain_cost_ratio(opex):
    rows = replace_row(ROWS, BASE, 'Electricity', UnitPrice='')
    got = opex(rows).estimate_opex(2000)['Electricity']
    assert got['monthly_vnd'] == 1_800_000        # 900,000 / 1,000 m2 x 2,000 m2
    assert 'tariff' not in got


@pytest.mark.parametrize('quantity', ['', 0])
def test_energy_row_without_a_usable_quantity_is_a_plain_cost_ratio(opex, quantity):
    rows = replace_row(ROWS, BASE, 'Electricity', Quantity=quantity)
    got = opex(rows).estimate_opex(2000)['Electricity']
    assert got['monthly_vnd'] == 1_800_000 and 'tariff' not in got


# ---------------------------------------------------------------- estimate_opex: ratio lines

def test_non_energy_lines_are_per_m2_cost_ratios_of_the_reference(opex):
    res = opex().estimate_opex(2500)
    assert res['Diesel (Generator Fuel)']['monthly_vnd'] == 1_250_000        # 500 VND/m2
    assert res['Repairs & Maintenance (materials only)']['monthly_vnd'] == 1_600_000   # 640 VND/m2
    assert res['Administrative Expense (office overhead)']['monthly_vnd'] == 800_000    # 320 VND/m2
    assert res['Repairs & Maintenance (materials only)']['ratio_per_m2'] == 640.0
    assert all(res[c]['n'] == 1 for c in eo.RATIO_CATEGORIES)


def test_every_ratio_category_is_returned(opex):
    assert list(opex().estimate_opex(1000)) == eo.RATIO_CATEGORIES


def test_ratio_line_rounds_to_whole_vnd(opex):
    rows = replace_row(ROWS, BASE, 'Administrative Expense (office overhead)', MonthlyVND=1000)
    # 1,000 / 1,000 m2 x 1,234 m2 = 1,234 exactly; 1,235.4 m2 -> 1,235 (round, not floor)
    assert opex(rows).estimate_opex(1235.4)['Administrative Expense (office overhead)']['monthly_vnd'] == 1235


# ---------------------------------------------------------------- estimate_opex: parking reference

def test_parking_reference_appears_only_for_categories_the_parking_building_has(opex):
    # rule source: code comment only (parking is shown for reference, never blended into the ratio)
    res = opex().estimate_opex(2000)
    elec, water, diesel = res['Electricity'], res['Water'], res['Diesel (Generator Fuel)']
    assert PARKING in elec['reference_only'] and '50 kWh/month' in elec['reference_only']
    assert diesel['reference_only'].endswith('flat.')
    assert water['reference_only'] is None


def test_parking_building_does_not_change_the_estimate(opex):
    with_parking = opex().estimate_opex(2000)
    without = opex([r for r in ROWS if r[0] != PARKING]).estimate_opex(2000)
    for cat in eo.RATIO_CATEGORIES:
        assert with_parking[cat]['monthly_vnd'] == without[cat]['monthly_vnd']
        assert without[cat]['reference_only'] is None


# ---------------------------------------------------------------- estimate_opex: pool salt

def test_pool_salt_absent_unless_asked_for(opex):
    assert 'Pool Salt' not in opex().estimate_opex(2000)
    assert 'Pool Salt' not in opex().estimate_opex(2000, has_pool=False, pool_volume_m3=440)


def test_pool_salt_with_known_volume(opex):
    got = opex().estimate_opex(2000, has_pool=True, pool_volume_m3=440)['Pool Salt']
    assert got['monthly_vnd'] == 6_600_000 and got['pool_volume_m3'] == 440.0


@pytest.mark.parametrize('volume', [None, 0, '', 'abc', -10])
def test_pool_salt_with_unknown_volume_uses_the_reference_flat_figure(opex, volume):
    got = opex().estimate_opex(2000, has_pool=True, pool_volume_m3=volume)['Pool Salt']
    assert got['monthly_vnd'] == 3_000_000          # not scaled by NFA
    assert got['pool_volume_m3'] is None


def test_pool_salt_flat_figure_does_not_scale_with_nfa(opex):
    mod = opex()
    assert mod.estimate_opex(500, has_pool=True)['Pool Salt']['monthly_vnd'] == \
        mod.estimate_opex(5000, has_pool=True)['Pool Salt']['monthly_vnd']


def test_pool_requested_but_reference_has_no_pool_salt_row(opex):
    rows = [r for r in ROWS if r[1] != 'Pool Salt']
    assert 'Pool Salt' not in opex(rows).estimate_opex(2000, has_pool=True, pool_volume_m3=440)


# ---------------------------------------- dated water and diesel (change apply-head-of-pm-decisions-2026-10, group 2)

import utility_tariffs as ut

_TARIFF_HEADER = ','.join(ut.COLUMNS) + '\n'
# Invented dated table: business water 20,000 (admin 10,000) in HCMC, drainage 30%, clean-water VAT 5%,
# general VAT 8% to 2026-12-31 then 10%; diesel listed at 10,800 incl. 8% VAT from 2026-10-01.
_TARIFF_ROWS = [
    f'water,"{ut.CAT_W_BUSINESS}",base,20000,VND/m3,2025-07-01,,TP.HCM,Listing Y,,2026-10-18,',
    f'water,"{ut.CAT_W_ADMIN}",base,10000,VND/m3,2025-07-01,,TP.HCM,Listing Z,,2026-10-18,',
    'water,,wastewater_pct,30,%,2025-01-01,,TP.HCM,Decision F,,2026-10-18,',
    'water,,vat_pct,5,%,2024-01-01,,,Law G,,2026-10-18,',
    'vat,general,vat_pct,8,%,2024-01-01,2026-12-31,,Resolution C,,2026-10-18,',
    'vat,general,vat_pct,10,%,2027-01-01,,,Law D,,2026-10-18,',
    'diesel,DO test,listed_price,10800,VND/l,2026-10-01,,,Listing X,,2026-10-18,',
    'diesel,DO test,listed_vat_pct,8,%,2026-10-01,,,Resolution C,,2026-10-18,',
]
_DIESEL_ROWS = replace_row(ROWS, BASE, 'Diesel (Generator Fuel)',
                           Quantity=100, Unit='litre/month', UnitPrice=5000, PriceAsOf='2020')


@pytest.fixture
def dated(tmp_path, opex):
    path = tmp_path / 'Ref_UtilityTariffs_invented.csv'
    path.write_text(_TARIFF_HEADER + '\n'.join(_TARIFF_ROWS) + '\n', encoding='utf-8')
    rows = ut.load_rows(str(path))
    mod = opex(_DIESEL_ROWS)
    # the diesel category label the module asks for is the real one; point it at the invented row
    for r in rows:
        if r['utility'] == ut.DIESEL:
            r['category'] = ut.CAT_DIESEL
    return mod, rows


def _months(start_year, start_month):
    return [((start_year * 12 + start_month - 1 + i) // 12, (start_month - 1 + i) % 12 + 1) for i in range(12)]


def test_water_defaults_to_business_and_is_priced_from_the_dated_file(dated):
    mod, rows = dated
    e = mod.estimate_opex(1000.0, period_months=_months(2027, 1), tariff_rows=rows)['Water']
    gross_2027 = 20000 * 1.05 + 6000 * 1.10
    assert e['tariff'] == pytest.approx(gross_2027)
    assert e['monthly_vnd'] == round(1000 * gross_2027)       # A&K usage 1,000 m3 on a 1,000 m2 building
    assert e['dated']['group'] == ut.CAT_W_BUSINESS and e['dated']['group_is_default']


def test_administrative_water_group_uses_its_own_base(dated):
    mod, rows = dated
    e = mod.estimate_opex(1000.0, period_months=_months(2027, 1), water_group='Hành chính sự nghiệp',
                          tariff_rows=rows)['Water']
    assert e['tariff'] == pytest.approx(10000 * 1.05 + 3000 * 1.10)
    assert not e['dated']['group_is_default']


def test_a_period_across_the_vat_step_prices_each_month(dated):
    mod, rows = dated
    e = mod.estimate_opex(1000.0, period_months=_months(2026, 10), tariff_rows=rows)
    w = e['Water']['monthly_vnd_by_month']
    assert w[0] == round(1000 * (20000 * 1.05 + 6000 * 1.08)) and w[-1] == round(1000 * (20000 * 1.05 + 6000 * 1.10))
    assert e['Water']['monthly_vnd'] == round(sum(w) / 12)
    d = e['Diesel (Generator Fuel)']['monthly_vnd_by_month']
    assert d[0] == round(100 * 10800) and d[-1] == round(100 * 10800 / 1.08 * 1.10)


def test_diesel_2027_is_the_listed_price_re_taxed(dated):
    mod, rows = dated
    e = mod.estimate_opex(1000.0, period_months=_months(2027, 1), tariff_rows=rows)['Diesel (Generator Fuel)']
    assert e['tariff'] == pytest.approx(10800 / 1.08 * 1.10)
    assert e['dated']['listed'] == 10800 and e['dated']['listed_vat'] == 8


def test_an_unknown_water_group_stops():
    with pytest.raises(ut.TariffError, match='Water Customer Group'):
        ut.water_group_category('Sinh hoạt')


@pytest.mark.parametrize('typed, category, is_default', [
    (None, ut.CAT_W_BUSINESS, True), ('', ut.CAT_W_BUSINESS, True), ('Kinh doanh dịch vụ', ut.CAT_W_BUSINESS, False),
    ('hanh chinh su nghiep', ut.CAT_W_ADMIN, False), ('Administrative', ut.CAT_W_ADMIN, False),
])
def test_water_group_category(typed, category, is_default):
    assert ut.water_group_category(typed) == (category, is_default)


def test_without_a_period_the_old_fact_opex_tariff_is_used(opex):
    e = opex().estimate_opex(1000.0)['Water']
    assert e['tariff'] == 10000 and 'dated' not in e
