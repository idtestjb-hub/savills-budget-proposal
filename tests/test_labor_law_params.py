"""Unit tests for labor_law_params.py (the dated labour-law table behind the staff cost).

Covered: load_rows validation, params_for_year month by month, the note for a year after the latest rule.

One test reads the real Ref_LaborLawParams.csv. That is the one exception to the rule that tests never read a
reference CSV: the table holds public law (decree values and dates), not client data, and the test exists to stop
a row without its legal basis or effective date from reaching a budget. Every other test writes an invented table
to a temporary folder.
"""
import datetime

import pytest

import labor_law_params as llp

HEADER = 'parameter,region,value,unit,effective_from,effective_to,legal_basis,source_url,checked_on\n'
# A complete invented table: one regional wage step on 2026-01-01 and an insurance-base step on 2026-07-01.
BASE_ROWS = [
    'min_wage_region,I,4000000,VND/month,2024-01-01,2025-12-31,Decree A,,2026-10-10',
    'min_wage_region,II,3500000,VND/month,2024-01-01,2025-12-31,Decree A,,2026-10-10',
    'min_wage_region,III,3000000,VND/month,2024-01-01,,Decree A,,2026-10-10',
    'min_wage_region,IV,2500000,VND/month,2024-01-01,,Decree A,,2026-10-10',
    'min_wage_region,I,4500000,VND/month,2026-01-01,,Decree B,,2026-10-10',
    'min_wage_region,II,3900000,VND/month,2026-01-01,,Decree B,,2026-10-10',
    'insurance_base,,2000000,VND/month,2024-01-01,2026-06-30,Decree C,,2026-10-10',
    'insurance_base,,2200000,VND/month,2026-07-01,,Decree D,,2026-10-10',
    'si_hi_ceiling_multiple,,20,x,2024-01-01,,Law E,,2026-10-10',
    'ui_ceiling_multiple,,20,x,2024-01-01,,Law F,,2026-10-10',
    'employer_si_rate,,0.175,share,2024-01-01,,Law E,,2026-10-10',
    'employer_hi_rate,,0.03,share,2024-01-01,,Law G,,2026-10-10',
    'employer_ui_rate,,0.01,share,2024-01-01,,Law F,,2026-10-10',
    'union_rate,,0.02,share,2024-01-01,,Law H,,2026-10-10',
    'thirteenth_month,,1,months,2000-01-01,,template,,2026-10-10',
    'admin_markup,,0.10,share,2000-01-01,,template,,2026-10-10',
]


def _table(tmp_path, rows):
    path = tmp_path / 'Ref_LaborLawParams.csv'
    path.write_text(HEADER + '\n'.join(rows) + '\n', encoding='utf-8')
    return str(path)


def test_real_table_loads_and_every_legal_row_is_sourced():
    rows = llp.load_rows()
    assert rows, 'the table is empty'
    for r in rows:
        assert r['legal_basis'], r
        assert r['effective_from'], r
        assert r['checked_on'], r
    # The values the spec names are present.
    by = {(r['parameter'], r['region'], r['effective_from']): r['value'] for r in rows}
    assert by[('min_wage_region', 'I', datetime.date(2026, 1, 1))] == 5310000
    assert by[('min_wage_region', 'IV', datetime.date(2026, 1, 1))] == 3700000
    assert by[('min_wage_region', 'I', datetime.date(2024, 7, 1))] == 4960000
    assert by[('insurance_base', '', datetime.date(2024, 7, 1))] == 2340000
    assert by[('insurance_base', '', datetime.date(2026, 7, 1))] == 2530000


def test_real_table_2026_constants_match_the_template():
    p = llp.params_for_year(2026)
    assert p.value('min_wage_region', 12) == 5310000          # template A1!I5
    assert p.value('insurance_base', 12) == 2530000           # template A1!I4
    assert p.value('employer_si_rate') + p.value('employer_hi_rate') == pytest.approx(0.205)


@pytest.mark.parametrize('bad_row, message', [
    ('union_rate,,0.02,share,2024-01-01,,,,2026-10-10', 'legal_basis is blank'),
    ('union_rate,,0.02,share,,,Law H,,2026-10-10', 'effective_from is blank'),
    ('union_rate,,0.02,share,2024-01-01,,Law H,,', 'checked_on is blank'),
    ('min_wage_region,V,1,VND/month,2024-01-01,,Decree A,,2026-10-10', 'region "V"'),
    ('union_rate,,abc,share,2024-01-01,,Law H,,2026-10-10', 'not a number'),
])
def test_a_bad_row_is_refused_and_named(tmp_path, bad_row, message):
    path = _table(tmp_path, BASE_ROWS + [bad_row])
    with pytest.raises(ValueError, match=message) as err:
        llp.load_rows(path)
    assert f'row {len(BASE_ROWS) + 2}' in str(err.value)


def test_a_year_inside_one_rule(tmp_path):
    p = llp.params_for_year(2025, 'II', path=_table(tmp_path, BASE_ROWS))
    assert all(p.value('min_wage_region', m) == 3500000 for m in range(1, 13))
    assert p.is_constant('insurance_base') and p.value('insurance_base') == 2000000
    assert p.note == ''


def test_a_year_spanning_the_mid_year_insurance_step(tmp_path):
    p = llp.params_for_year(2026, path=_table(tmp_path, BASE_ROWS))
    assert [p.value('insurance_base', m) for m in range(1, 13)] == [2000000] * 6 + [2200000] * 6
    assert p.annual_average('insurance_base') == 2100000
    assert p.value('min_wage_region', 1) == 4500000          # blank region = Region I
    assert p.rows[7]['insurance_base']['legal_basis'] == 'Decree D'
    assert p.note == ''


def test_a_year_after_the_latest_rule_uses_it_and_says_so(tmp_path):
    p = llp.params_for_year(2027, 'I', path=_table(tmp_path, BASE_ROWS))
    assert p.value('insurance_base', 1) == 2200000
    assert p.value('min_wage_region', 12) == 4500000
    assert 'Chưa có quy định mới cho năm 2027' in p.note
    assert '01/07/2026' in p.note


def test_a_new_row_moves_only_the_months_after_it(tmp_path):
    rows = BASE_ROWS + ['min_wage_region,I,4800000,VND/month,2027-07-01,,Decree Z,,2026-10-10']
    p = llp.params_for_year(2027, path=_table(tmp_path, rows))
    assert [p.value('min_wage_region', m) for m in range(1, 13)] == [4500000] * 6 + [4800000] * 6
    assert p.note == ''


def test_a_region_without_a_row_in_force_is_named(tmp_path):
    rows = [r for r in BASE_ROWS if not r.startswith('min_wage_region,II,3900000')]
    with pytest.raises(ValueError, match='region II'):
        llp.params_for_year(2026, 'II', path=_table(tmp_path, rows))


def test_an_unknown_region_is_refused(tmp_path):
    with pytest.raises(ValueError, match='Minimum Wage Region "V"'):
        llp.params_for_year(2026, 'V', path=_table(tmp_path, BASE_ROWS))
