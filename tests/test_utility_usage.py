"""Unit tests for utility_usage.py and the energy lines of estimate_opex.py that use it (change
widen-utility-and-capex-sources).

Covered: accepted rows only, one accepted row per project and utility, the IQR fence and median (the spec's seven-value
example), the minimum of five projects and the fallback to the utilities base, the remark fields, electricity priced
month by month from the dated EVN rate before VAT (a rate change on 10 May counts from June), and a price change moving
the cost in proportion.
Not covered: the office-side table builder (build_utility_usage.py), which reads the store.

Invented data only: an invented usage table, registry, Fact_OPEX and tariff table in tmp_path; no real file is read.
Rule sources: outer docs/05-decisions.md "Utility and capex sources: four rules for the next change" (2026-11-06) and
the change's specs utility-usage-benchmark and dated-tax-and-tariff-rates.
"""
import csv

import pytest

import estimate_opex as eo
import reference_projects as rp
import utility_tariffs as ut
import utility_usage as uu

from tests.test_estimate_opex import ROWS, write_csv, write_registry


def write_usage(path, rows):
    with open(path, 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.DictWriter(fh, fieldnames=uu.COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, '') for c in uu.COLUMNS})
    return str(path)


def usage_row(pid, utility, per_m2, check='accepted', nfa=10000):
    unit = uu.UNITS[utility]
    return dict(file_id=f'f{pid}', project_id=pid, utility=utility, quantity_month=per_m2 * nfa, unit=unit,
                nfa_m2=nfa, usage_per_m2_month=per_m2, check=check, reason='test', checked_by='test',
                checked_on='2026-11-06')


SEVEN = [2.1, 2.4, 2.5, 2.6, 2.8, 3.0, 9.5]


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(rp, 'REGISTRY_CSV', write_registry(tmp_path / 'reg.csv'))
    rp.clear_cache()
    monkeypatch.setattr(eo, 'OPEX_CSV', write_csv(tmp_path / 'opex.csv', ROWS))

    def with_usage(rows):
        monkeypatch.setattr(uu, 'USAGE_CSV', write_usage(tmp_path / 'usage.csv', rows))
        uu.clear_cache()
        return eo

    return with_usage


def test_fence_drops_the_outlier_and_takes_the_median_of_the_rest(setup):
    setup([usage_row(f'P{i:03d}', 'electricity', v) for i, v in enumerate(SEVEN)])
    b = uu.benchmark('Electricity')
    assert [p for p, _ in b['dropped']] == ['P006'] and b['n'] == 6
    assert b['median'] == pytest.approx(2.55) and b['enough']


def test_rejected_and_duplicate_rows_do_not_count(setup):
    rows = [usage_row(f'P{i:03d}', 'water', v) for i, v in enumerate(SEVEN[:5])]
    rows.append(usage_row('P900', 'water', 50.0, check='rejected'))
    rows.append(usage_row('P901', 'water', 50.0, check='duplicate'))
    setup(rows)
    b = uu.benchmark('Water')
    assert b['n'] == 5 and 'P900' not in [p for p, _ in b['kept'] + b['dropped']]


def test_two_accepted_rows_for_one_project_stop_the_run(setup):
    setup([usage_row('P001', 'diesel', 0.01), usage_row('P001', 'diesel', 0.02)])
    with pytest.raises(uu.UtilityUsageError, match='two accepted'):
        uu.benchmark('Diesel (Generator Fuel)')


def test_a_missing_table_stops_the_run_naming_the_file(tmp_path, monkeypatch):
    monkeypatch.setattr(uu, 'USAGE_CSV', str(tmp_path / 'absent.csv'))
    uu.clear_cache()
    with pytest.raises(uu.UtilityUsageError, match='absent.csv'):
        uu.benchmark('Water')


def test_estimate_uses_the_median_times_the_project_nfa(setup):
    mod = setup([usage_row(f'P{i:03d}', 'electricity', v) for i, v in enumerate(SEVEN)])
    e = mod.estimate_opex(2000.0)['Electricity']
    assert e['usage_basis'] == 'benchmark' and e['n'] == 6
    assert e['usage_per_m2'] == pytest.approx(2.55)
    assert e['monthly_vnd'] == round(2.55 * 2000 * 2000)          # Fact_OPEX tariff 2,000 without a period
    assert 'P006' not in [p for p, _ in e['usage_projects']] and 'P006' in e['source']


def test_fewer_than_five_projects_fall_back_to_the_base_and_say_why(setup):
    mod = setup([usage_row(f'P{i:03d}', 'diesel', v) for i, v in enumerate([0.01, 0.02, 0.03])])
    rows = [r for r in ROWS]
    e = mod.estimate_opex(2000.0)['Electricity']                  # no electricity rows at all
    assert e['usage_basis'] == 'fallback' and e['n'] == 1
    assert e['usage_per_m2'] == pytest.approx(400 / 1000)          # the base: 400 kWh on 1,000 m²
    assert 'cần tối thiểu 5' in e['usage_fallback_reason'] and rows


TARIFF_HEADER = ','.join(ut.COLUMNS) + '\n'
TARIFFS = [
    f'electricity,"{ut.CAT_E_LT6}",base,2000,VND/kWh,2025-05-10,2027-05-09,,Decision E,,2026-10-18,',
    f'electricity,"{ut.CAT_E_LT6}",base,2200,VND/kWh,2027-05-10,,,Decision F,,2026-10-18,',
    'vat,general,vat_pct,10,%,2024-01-01,,,Law D,,2026-10-18,',
    f'water,"{ut.CAT_W_BUSINESS}",base,20000,VND/m3,2025-07-01,,TP.HCM,Listing Y,,2026-10-18,',
    'water,,wastewater_pct,30,%,2025-01-01,,TP.HCM,Decision F,,2026-10-18,',
    'water,,vat_pct,5,%,2024-01-01,,,Law G,,2026-10-18,',
]


def _tariff_rows(tmp_path, lines):
    path = tmp_path / 'tariffs.csv'
    path.write_text(TARIFF_HEADER + '\n'.join(lines) + '\n', encoding='utf-8')
    return ut.load_rows(str(path))


def _months_2027():
    return [(2027, m) for m in range(1, 13)]


def test_electricity_is_the_evn_rate_before_vat_month_by_month(setup, tmp_path):
    mod = setup([usage_row(f'P{i:03d}', 'electricity', v) for i, v in enumerate(SEVEN)])
    rows = _tariff_rows(tmp_path, TARIFFS)
    e = mod.estimate_opex(1000.0, period_months=_months_2027(), tariff_rows=rows)['Electricity']
    by_month = e['tariff_by_month']
    assert by_month[4] == 2000 and by_month[5] == 2200          # 10 May counts from June
    assert e['tariff'] == 2000 and e['dated']['provenance'] == 'Decision E'
    assert e['monthly_vnd_by_month'][0] == round(2.55 * 1000 * 2000)
    assert e['monthly_vnd'] == round(2.55 * 1000 * sum(by_month) / 12)


def test_an_electricity_price_rise_moves_the_cost_in_proportion(setup, tmp_path):
    mod = setup([usage_row(f'P{i:03d}', 'electricity', v) for i, v in enumerate(SEVEN)])
    low = mod.estimate_opex(1000.0, period_months=_months_2027(),
                            tariff_rows=_tariff_rows(tmp_path, [TARIFFS[0].replace('2027-05-09', '')] + TARIFFS[2:]))
    high = mod.estimate_opex(1000.0, period_months=_months_2027(),
                             tariff_rows=_tariff_rows(tmp_path, [TARIFFS[0].replace('2027-05-09', '')
                                                                 .replace(',2000,', ',2350,')] + TARIFFS[2:]))
    ratio = high['Electricity']['monthly_vnd'] / low['Electricity']['monthly_vnd']
    assert ratio == pytest.approx(2350 / 2000, rel=1e-6)
    assert high['Electricity']['usage_per_m2'] == low['Electricity']['usage_per_m2']
