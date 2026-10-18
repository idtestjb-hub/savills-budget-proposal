"""Unit tests for the client deliverable naming no other project (change apply-head-of-pm-decisions-2026-10, group 9,
tasks 9.1 and 9.3; decision D3, design D13).

Covered: the name scan inside checks.scan_internal_wording (word-bounded, case and Unicode form folded, formula text
read, this project's own name excluded), the data-built name list's filters (length, generic words), and the
client wording estimate_opex gives the pool-chemicals line.

Not covered: the full deliverable (verify.py scans every sample through check_remark_content).

Every project name here is invented.
"""
import unicodedata

import openpyxl

import estimate_opex
from verification import checks

NAMES = {checks._norm_name_text(n) for n in ('Lotus Harbour', 'Kestrel Bay', 'Zeta Heights')}


def wb_with(**cells):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '2. Budget-Management Fund'
    for coord, value in cells.items():
        ws[coord] = value
    return wb


def name_failures(wb, own='ZZ Test Tower'):
    _s, _e, failures = checks.scan_internal_wording(wb, None, NAMES, own)
    return [f for f in failures if 'project' in f[2]]


def test_a_name_in_a_remark_fails():
    fails = name_failures(wb_with(T14='Nguồn đơn giá: 2 dự án tham chiếu thực tế — Lotus Harbour, Kestrel Bay'))
    assert [(f[1], f[2]) for f in fails] == [('T14', "another project's name in client-facing text")]


def test_a_name_planted_in_a_formula_fails():
    fails = name_failures(wb_with(B30='=IF(B10>0,"cao hơn ZETA HEIGHTS","")'))
    assert [(f[1], f[2]) for f in fails] == [('B30', "another project's name in client-facing formula")]


def test_unicode_form_and_case_are_folded():
    decomposed = unicodedata.normalize('NFD', 'Theo số liệu của lotus  harbour.')
    assert name_failures(wb_with(T1=decomposed))


def test_a_name_inside_a_longer_word_does_not_fail():
    assert not name_failures(wb_with(T1='Kestrel Bayside is not on the list; neither is SuperLotus Harbour'))


def test_client_wording_passes():
    assert not name_failures(wb_with(T1='Nguồn đơn giá: 2 dự án tham chiếu thực tế.',
                                     T2='=IF(B10>0,"trong khoảng của các dự án tham chiếu","")'))


def test_the_projects_own_name_is_excluded():
    # The regression clone is itself one of the reference projects: its own name must not fail.
    assert not name_failures(wb_with(B1='Lotus Harbour (rebuilt as new prospect)'),
                             own='LOTUS HARBOUR (REBUILT AS NEW PROSPECT)')


def test_name_list_filters_short_and_generic_names(tmp_path):
    folder = tmp_path / 'master_list_verified'
    folder.mkdir()
    (folder / 'Dim_Property_Residential.csv').write_text(
        'Name,Other\nLotus Harbour,1\nParking Building,2\nABC,3\n  kestrel   BAY ,4\n', encoding='utf-8-sig')
    (folder / 'Fact_ProjectLocation.csv').write_text('# a comment line\nasset_name\nZeta Heights\n',
                                                     encoding='utf-8-sig')
    names = checks.project_names_from_data(str(tmp_path))
    assert {'lotus harbour', 'kestrel bay', 'zeta heights'} <= names
    assert 'parking building' not in names and 'abc' not in names


def test_pool_client_wording_names_no_project():
    for volume in (None, 440):
        entry = estimate_opex._pool_salt(volume, 3_000_000)
        client = entry['method_client' if volume is None else 'method'] + entry['source_client']
        assert 'A&K' not in client and 'dự án tham chiếu' in client
        assert 'A&K' in entry['source']                 # the analysis keeps the named source

# ---- task 9.2: the client Comparison sheet carries nothing past column B (D14) ----
def _comparison(**cells):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Comparison'
    ws['A4'], ws['B4'] = 'Metric', 'ZZ Test Tower'
    ws.merge_cells('A2:D2')                         # a merge or a fill past B is not a value
    for coord, value in cells.items():
        ws[coord] = value
    return ws


def test_comparison_with_this_project_column_only_passes():
    assert checks.comparison_cells_past_column_b(_comparison(B10=12_345, C11='  ')) == []


def test_comparison_with_a_peer_value_in_column_c_fails():
    ws = _comparison(C4='Lotus Harbour', D12='=1+1')
    assert checks.comparison_cells_past_column_b(ws) == ['C4', 'D12']
