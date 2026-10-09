"""Unit tests for estimate_opex.py (utilities and pool-salt estimate for a new project).

Covered: _tariff_year, _coerce_volume, _pool_salt, estimate_opex (usage x tariff for the three
energy lines, plain per-m2 ratio for the others, stale-tariff flag, parking reference text,
pool-salt method and fallback).
Not covered: the wording of the long Vietnamese/English source strings beyond the key figures.

Invented data only. estimate_opex looks up two project labels by name ('A&K Tower' as the usage
reference and 'Parking Building' as the reference-only building); the temporary CSV therefore uses
those two labels, with invented numbers. OPEX_CSV and AK_TOWER_NFA_M2 are patched, so the real
Fact_OPEX.csv is never read.

Rule sources: docs/05-decisions.md D9 (energy = usage x tariff, usage stored fixed, tariff a
separate dated input) and the pool-salt section (blank, 0 and non-numeric mean "unknown", 2.5 kg x
6,000 VND/kg per m3 per month); the rest is stated in code comments only.
"""
import csv

import pytest

import estimate_opex as eo

HEADER = ['Project', 'Category', 'MonthlyVND', 'Source', 'Quantity', 'Unit', 'UnitPrice', 'PriceAsOf']

# Reference building: 1,000 m2. Electricity monthly cost (900,000) is deliberately NOT quantity x
# price (400 x 2,000 = 800,000): only the stored quantity may drive the estimate.
ROWS = [
    ('A&K Tower', 'Electricity', 900000, 'usage src  TARIFF: tariff src', 400, 'kWh/month', 2000, '2026-05-09'),
    ('A&K Tower', 'Water', 5000000, 'water src', 1000, 'm3/month', 10000, '2027-01-01'),
    ('A&K Tower', 'Diesel (Generator Fuel)', 500000, 'diesel src', '', '', '', ''),
    ('A&K Tower', 'Repairs & Maintenance (materials only)', 640000, 'rm src', '', '', '', ''),
    ('A&K Tower', 'Administrative Expense (office overhead)', 320000, 'admin src', '', '', '', ''),
    ('A&K Tower', 'Pool Salt', 3000000, 'pool src', '', '', '', ''),
    ('Parking Building', 'Electricity', 100000, 'p src', 50, 'kWh/month', 2000, '2026-01-01'),
    ('Parking Building', 'Diesel (Generator Fuel)', 70000, 'p src', '', '', '', ''),
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


@pytest.fixture
def opex(tmp_path, monkeypatch):
    monkeypatch.setattr(eo, 'AK_TOWER_NFA_M2', 1000.0)

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
    moved = opex(replace_row(ROWS, 'A&K Tower', 'Electricity', UnitPrice=3000)).estimate_opex(2000)['Electricity']
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
    rows = replace_row(ROWS, 'A&K Tower', 'Electricity', PriceAsOf=as_of)
    assert opex(rows).estimate_opex(1000)['Electricity']['tariff_stale'] is stale


def test_energy_row_without_a_tariff_is_a_plain_cost_ratio(opex):
    rows = replace_row(ROWS, 'A&K Tower', 'Electricity', UnitPrice='')
    got = opex(rows).estimate_opex(2000)['Electricity']
    assert got['monthly_vnd'] == 1_800_000        # 900,000 / 1,000 m2 x 2,000 m2
    assert 'tariff' not in got


@pytest.mark.parametrize('quantity', ['', 0])
def test_energy_row_without_a_usable_quantity_is_a_plain_cost_ratio(opex, quantity):
    rows = replace_row(ROWS, 'A&K Tower', 'Electricity', Quantity=quantity)
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
    rows = replace_row(ROWS, 'A&K Tower', 'Administrative Expense (office overhead)', MonthlyVND=1000)
    # 1,000 / 1,000 m2 x 1,234 m2 = 1,234 exactly; 1,235.4 m2 -> 1,235 (round, not floor)
    assert opex(rows).estimate_opex(1235.4)['Administrative Expense (office overhead)']['monthly_vnd'] == 1235


# ---------------------------------------------------------------- estimate_opex: parking reference

def test_parking_reference_appears_only_for_categories_the_parking_building_has(opex):
    # rule source: code comment only (parking is shown for reference, never blended into the ratio)
    res = opex().estimate_opex(2000)
    elec, water, diesel = res['Electricity'], res['Water'], res['Diesel (Generator Fuel)']
    assert 'Parking Building' in elec['reference_only'] and '50 kWh/month' in elec['reference_only']
    assert diesel['reference_only'].endswith('flat.')
    assert water['reference_only'] is None


def test_parking_building_does_not_change_the_estimate(opex):
    with_parking = opex().estimate_opex(2000)
    without = opex([r for r in ROWS if r[0] != 'Parking Building']).estimate_opex(2000)
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
