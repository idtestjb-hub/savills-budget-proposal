"""Unit tests for service_levels.py (change add-service-level-table, spec service-level-tiers).

Invented thresholds, projects and demand rows only; the live data files are not read (every test passes its own).
"""
import csv

import pytest

import service_levels as sl

THRESHOLD_ROWS = [
    {'service': 'cleaning', 'measure': 'm2', 'unit': 'm2/nguoi', 'cutoff_1': '2500', 'cutoff_2': '4000',
     'direction': 'lower_is_higher_level', 'level_below_cutoff_1': 'Nâng cao', 'level_between': 'Tiêu chuẩn',
     'level_from_cutoff_2': 'Cơ bản', 'bound_low': '1000', 'bound_high': '8000', 'approved_on': '2026-10-16',
     'bounds_approved_on': '2026-10-18', 'source': 'test'},
    {'service': 'security', 'measure': 'posts', 'unit': 'chot/10k', 'cutoff_1': '1.5', 'cutoff_2': '3.0',
     'direction': 'higher_is_higher_level', 'level_below_cutoff_1': 'Cơ bản', 'level_between': 'Tiêu chuẩn',
     'level_from_cutoff_2': 'Nâng cao', 'bound_low': '0.5', 'bound_high': '8', 'approved_on': '2026-10-18',
     'bounds_approved_on': '2026-10-18', 'source': 'test'},
    {'service': 'landscape', 'measure': '', 'unit': '', 'cutoff_1': '', 'cutoff_2': '', 'direction': 'not_set',
     'level_below_cutoff_1': '', 'level_between': '', 'level_from_cutoff_2': '', 'bound_low': '', 'bound_high': '',
     'approved_on': '2026-10-16', 'bounds_approved_on': '', 'source': ''},
]


def _write_thresholds(path, rows=THRESHOLD_ROWS):
    with open(path, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return str(path)


@pytest.fixture
def thresholds(tmp_path):
    return sl.load_thresholds(_write_thresholds(tmp_path / 't.csv'))


def test_thresholds_load_and_read_back(thresholds):
    assert thresholds['cleaning'].cutoff_1 == 2500 and thresholds['cleaning'].cutoff_2 == 4000
    assert thresholds['security'].cutoff_1 == 1.5 and thresholds['security'].cutoff_2 == 3.0
    assert thresholds['cleaning'].bound_low == 1000 and thresholds['cleaning'].bound_high == 8000
    assert thresholds['security'].bound_low == 0.5 and thresholds['security'].bound_high == 8
    assert not thresholds['landscape'].is_set and thresholds['landscape'].levels is None


def test_thresholds_edit_changes_classification_without_code(tmp_path):
    rows = [dict(r) for r in THRESHOLD_ROWS]
    rows[0]['cutoff_1'] = '3100'
    t = sl.load_thresholds(_write_thresholds(tmp_path / 't2.csv', rows))
    assert sl.classify('cleaning', 3000, t).level == 'Nâng cao'


def test_missing_service_raises(tmp_path):
    with pytest.raises(ValueError):
        sl.load_thresholds(_write_thresholds(tmp_path / 't3.csv', THRESHOLD_ROWS[1:]))


@pytest.mark.parametrize('value, level', [(2499.99, 'Nâng cao'), (2500, 'Tiêu chuẩn'), (3999.99, 'Tiêu chuẩn'),
                                          (4000, 'Cơ bản'), (3000, 'Tiêu chuẩn')])
def test_cleaning_edges(thresholds, value, level):
    assert sl.classify('cleaning', value, thresholds).level == level


@pytest.mark.parametrize('value, level', [(1.49, 'Cơ bản'), (1.5, 'Tiêu chuẩn'), (2.9, 'Tiêu chuẩn'),
                                          (3.0, 'Nâng cao'), (6.0, 'Nâng cao')])
def test_security_edges(thresholds, value, level):
    assert sl.classify('security', value, thresholds).level == level


def test_near_mark(thresholds):
    assert sl.classify('cleaning', 2400, thresholds).near is True          # inside cut-off x 0.9 .. x 1.1
    assert sl.classify('cleaning', 2400, thresholds).level == 'Nâng cao'   # the mark changes no level
    assert sl.classify('cleaning', 3000, thresholds).near is False
    assert sl.classify('cleaning', 2250, thresholds).near is True          # lower edge inclusive
    assert sl.classify('cleaning', 2750, thresholds).near is False         # upper edge exclusive
    assert sl.classify('security', 1.5, thresholds).near is True
    assert sl.classify('security', 2.0, thresholds).near is False


def test_out_of_bounds_kept_not_classified(thresholds):
    c = sl.classify('security', 0.08, thresholds)
    assert c.level is None and c.reason == sl.REASON_OUT_OF_BOUNDS and c.value == 0.08
    assert c.label == 'chưa phân loại: ngoài cận, nghi đọc sai'
    assert sl.classify('cleaning', 9000, thresholds).level is None
    assert sl.classify('cleaning', 8000, thresholds).level == 'Cơ bản'     # on the bound: classified


def test_missing_inputs(thresholds):
    assert sl.classify('cleaning', None, thresholds, reason_if_missing=sl.REASON_NO_NFA).label == 'chưa phân loại: thiếu NFA'
    assert sl.classify('cleaning', 0, thresholds).reason == sl.REASON_NO_HEADCOUNT
    assert sl.measure_cleaning(0, 10) is None and sl.measure_cleaning(60000, 0) is None
    assert sl.measure_security(None, 5) is None


def test_measures_from_spec_scenarios():
    assert sl.measure_cleaning(60_000, 20) == 3_000
    # 10 people on 24H + 15 people on 8-hour shifts = 10 + 5 = 15 posts on 100,000 m² -> 1.5 per 10,000 m²
    demand = [{'Position': 'Security - Gate', 'ShiftCode': '24H', 'StaffPerDay': 10, 'CoverageDays': 7},
              {'Position': 'Security - Patrol (Morning)', 'ShiftCode': 'S', 'StaffPerDay': 5, 'CoverageDays': 7},
              {'Position': 'Security - Patrol (Afternoon)', 'ShiftCode': 'C', 'StaffPerDay': 5, 'CoverageDays': 7},
              {'Position': 'Security - Patrol (Night)', 'ShiftCode': 'D', 'StaffPerDay': 5, 'CoverageDays': 7},
              {'Position': 'Cleaning - Common Area', 'ShiftCode': 'S', 'StaffPerDay': 18, 'CoverageDays': 7},
              {'Position': 'Cleaning - Supervisor', 'ShiftCode': 'HC', 'StaffPerDay': 2, 'CoverageDays': 6},
              {'Position': 'Reception', 'ShiftCode': 'HC', 'StaffPerDay': 1, 'CoverageDays': 7}]
    c = sl.tool_headcount(demand)
    assert c['security']['posts24'] == 15 and c['security']['on_duty'] == 25
    assert c['cleaning']['on_duty'] == 20                       # supervisors included
    assert c['cleaning']['roster'] == 21 + 2                   # ceil(18*7/6)=21 for 7-day cover, 2 for 6-day
    assert sl.measure_security(100_000, c['security']['posts24']) == 1.5


def test_percentile_leaves_the_project_out_and_ignores_inferred():
    projects = [
        {'name_key': sl.name_key('Alpha'), 'nfa_m2': 50_000, 'cln_source': 'form', 'cln_level': 'Tiêu chuẩn', 'cln_m2_per_person': 3000},
        {'name_key': sl.name_key('Beta'), 'nfa_m2': 70_000, 'cln_source': 'form', 'cln_level': 'Cơ bản', 'cln_m2_per_person': 5000},
        {'name_key': sl.name_key('Gamma'), 'nfa_m2': 90_000, 'cln_source': 'chi phí', 'cln_level': 'Nâng cao', 'cln_m2_per_person': 2000},
        {'name_key': sl.name_key('Delta'), 'nfa_m2': 30_000, 'cln_source': 'form', 'cln_level': 'chưa phân loại', 'cln_m2_per_person': 9000},
        {'name_key': sl.name_key('Self'), 'nfa_m2': 60_000, 'cln_source': 'form', 'cln_level': 'Nâng cao', 'cln_m2_per_person': 1500},
    ]
    values, n_inf = sl.comparison_set('cleaning', projects, self_name_key=sl.name_key('Self'))
    assert sorted(values) == [3000, 5000] and n_inf == 1          # Self out, inferred counted apart, unclassified out
    values2, _ = sl.comparison_set('cleaning', projects, self_nfa=60_100)   # within 0.5% of Self's NFA
    assert sorted(values2) == [3000, 5000]
    assert sl.percentile(3000, [3000, 5000]) == 50.0
    assert sl.percentile(3000, []) is None


def test_name_key_is_stable_and_blank_for_no_name():
    assert sl.name_key('Dự án  A1') == sl.name_key('dự án a1') != ''
    assert sl.name_key('') == '' and sl.name_key(None) == ''


def test_evaluate_without_nfa(thresholds):
    out = sl.evaluate({'name': 'X', 'total_nfa': 0}, [], thresholds=thresholds, projects=[])
    for s in sl.SERVICES:
        assert out['services'][s]['classification'].label == 'chưa phân loại: thiếu NFA'
        assert out['services'][s]['percentile'] is None
    assert 'thiếu diện tích cây xanh' in out['landscape']
