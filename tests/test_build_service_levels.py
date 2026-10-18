"""Unit tests for build_service_levels.py on an invented mini-store (SQLite fixture + levels CSV, invented names).

Covered: latest year per project, an unnamed file as its own project, two names with one identical NFA merged into
one row, form-read and inferred headcount, missing NFA, zero or blank measure, a value outside the bounds kept but not
classified, the near mark, the Management Fee and group-row double-count fixes, and the refusal to write when a name would be written.
"""
import csv
import os
import sqlite3

import pytest

import build_service_levels as b
import service_levels as sl
from test_service_levels import _write_thresholds

FILES = [
    # file_id, project, file_name, year, modified, nfa_total, nfa_how, nfa_types, dup, source_type
    ('f1', 'Invented Tower', 'tower 2025.xlsx', 2025, '2025-01-01 10:00', 60000, 'total_row', '', '', 'excel'),
    ('f2', 'Invented Tower', 'tower 2026.xlsx', 2026, '2026-01-01 10:00', 60000, 'total_row', '', '', 'excel'),
    ('f3', '', 'noname.xlsx', 2026, '2026-02-01 10:00', 100000, 'total_row', '', '', 'excel'),
    ('f4', 'Phase One', 'p1.xlsx', 2026, '2026-03-01 10:00', 53826, 'total_row', '', '', 'excel'),
    ('f5', 'Phase Two', 'p2.xlsx', 2026, '2026-04-01 10:00', 53826, 'total_row', '', '', 'excel'),
    ('f6', 'No Area', 'noarea.xlsx', 2026, '2026-05-01 10:00', None, '', '', '', 'excel'),
    ('f7', 'Doubled', 'doubled.xlsx', 2026, '2026-06-01 10:00', 80000, 'sum_of_types', 'Management Fee=40000.0; Apartment=40000.0', '', 'excel'),
    ('f8', 'Scanned', 'scan.pdf', 2026, '2026-06-01 10:00', 50000, 'total_row', '', '', 'pdf_ocr'),
    ('f9', 'Copy', 'copy.xlsx', 2026, '2026-06-01 10:00', 50000, 'total_row', '', 'f2', 'excel'),
    # the store summed group rows (I., II., B) and their children: total 72,000 = twice I. + II.
    ('f10', 'Grouped', 'grouped.xlsx', 2026, '2026-07-01 10:00', 72000, 'sum_of_types',
     'I.=30000.0; Căn hộ=25000.0; Shophouse=5000.0; II.=6000.0; A=2000.0; B=4000.0; B1=3000.0; B2=1000.0', '', 'excel'),
]
LEVELS = [
    # file_id, sec_equiv_posts, sec_src, cln_equiv_posts, cln_src
    ('f1', 9, 'form', 20, 'form'),
    ('f2', 9, 'form', 24, 'cost'),       # 60000/24 = 2500 -> Tiêu chuẩn, near; 1.5 -> Tiêu chuẩn, near
    ('f3', 0.5, 'form', 25, 'form'),     # 0.05 per 10k -> out of bounds; 4000 -> Cơ bản
    ('f4', 8, 'form', 8, 'form'),
    ('f5', 7, 'form', 8, 'form'),
    ('f6', 5, 'form', 5, 'form'),        # no NFA
    ('f7', 8, 'cost', 20, 'cost'),       # fee NFA 40000 -> 2000 Nâng cao; 2.0 Tiêu chuẩn
    ('f8', 5, 'form', 5, 'form'),
    ('f9', 5, 'form', 5, 'form'),
    ('f10', 6, 'form', 10, 'form'),      # fee NFA 30000 (group I) -> 3000 Tiêu chuẩn; 2.0 Tiêu chuẩn
]


@pytest.fixture
def mini_store(tmp_path):
    db = tmp_path / 'store.sqlite'
    con = sqlite3.connect(db)
    con.execute('create table file_profile (file_id text, file_name text, budget_year_v2 real, nfa_total real, '
                'nfa_how text, nfa_types text, content_dup_of text, source_type text)')
    con.execute('create table dim_file (file_id text, file_name text, modified text)')
    con.execute('create table project_map (file_id text, project_name text)')
    for fid, proj, fname, yr, mod, nfa, how, types, dup, st in FILES:
        con.execute('insert into file_profile values (?,?,?,?,?,?,?,?)', (fid, fname, yr, nfa, how, types, dup or None, st))
        con.execute('insert into dim_file values (?,?,?)', (fid, fname, mod))
        con.execute('insert into project_map values (?,?)', (fid, proj))
    con.commit()
    con.close()
    levels = tmp_path / 'levels.csv'
    with open(levels, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['file_id', 'project', 'file', 'nfa', 'sec_equiv_posts', 'sec_src', 'cln_equiv_posts', 'cln_src'])
        for fid, sp, ss, cp, cs in LEVELS:
            w.writerow([fid, '', '', '', sp, ss, cp, cs])
    thresholds = _write_thresholds(tmp_path / 'thresholds.csv')
    return str(db), str(levels), thresholds


def _run(mini_store, tmp_path):
    db, levels, thresholds = mini_store
    out, mp = tmp_path / 'out', tmp_path / 'map'
    b.main(['--store', db, '--levels', levels, '--out', str(out), '--map', str(mp), '--thresholds', thresholds])
    rows = sl.load_projects(str(out / 'Ref_ServiceLevelProjects.csv'))
    with open(mp / b.MAP_FILE, encoding='utf-8-sig') as fh:
        mapping = {r['project_id']: r for r in csv.DictReader(fh)}
    return rows, mapping, out, mp


def test_rules_and_classification(mini_store, tmp_path):
    rows, mapping, out, mp = _run(mini_store, tmp_path)
    by_file = {mapping[r['project_id']]['file_id']: r for r in rows}
    # latest year wins; pdf and content duplicate left out; two names with one NFA -> one row (later file date)
    assert set(by_file) == {'f2', 'f3', 'f5', 'f6', 'f7', 'f10'}
    # f2: inferred cleaning 2500 exactly -> Tiêu chuẩn (edge) with near mark; security 1.5 -> Tiêu chuẩn near
    assert by_file['f2']['cln_level'] == 'Tiêu chuẩn' and by_file['f2']['cln_near'] is True
    assert by_file['f2']['cln_source'] == sl.SOURCE_COST and by_file['f2']['sec_source'] == sl.SOURCE_FORM
    assert by_file['f2']['sec_level'] == 'Tiêu chuẩn' and by_file['f2']['sec_near'] is True
    # f3: unnamed file is its own project; security 0.05 out of bounds -> kept, not classified, flagged
    assert by_file['f3']['sec_level'] == sl.NOT_CLASSIFIED and by_file['f3']['sec_reason'] == sl.REASON_OUT_OF_BOUNDS
    assert by_file['f3']['sec_per_10k'] == 0.05 and 'bảo vệ ngoài cận' in by_file['f3']['flag']
    assert 'không có tên' in by_file['f3']['flag'] and by_file['f3']['name_key'] == ''
    assert by_file['f3']['cln_level'] == 'Cơ bản'
    # f6: no NFA -> both not classified with the reason, no guess
    assert by_file['f6']['cln_level'] == sl.NOT_CLASSIFIED and by_file['f6']['cln_reason'] == sl.REASON_NO_NFA
    assert by_file['f6']['cln_m2_per_person'] is None
    # f7: Management Fee pseudo-product removed -> fee NFA 40,000
    assert by_file['f7']['nfa_fee_m2'] == 40000 and by_file['f7']['cln_level'] == 'Nâng cao'
    # f10: group and child rows both summed -> fee NFA is the group I row (group II is parking)
    assert by_file['f10']['nfa_fee_m2'] == 30000 and by_file['f10']['nfa_m2'] == 30000
    assert by_file['f10']['cln_m2_per_person'] == 3000 and by_file['f10']['cln_level'] == 'Tiêu chuẩn'
    assert by_file['f10']['sec_per_10k'] == 2.0 and by_file['f10']['sec_level'] == 'Tiêu chuẩn'
    assert 'f10: fee NFA from the group I row' in (out / b.BUILD_INFO).read_text(encoding='utf-8')
    # ids are sequential and anonymous; the map holds the names, outside the table
    assert [r['project_id'] for r in rows] == ['S001', 'S002', 'S003', 'S004', 'S005', 'S006']
    assert all(mapping[r['project_id']]['project_name'] == next(p for p in FILES if p[0] == mapping[r['project_id']]['file_id'])[1]
               for r in rows)
    assert (mp / b.NAMES_FILE).exists() and (out / b.BUILD_INFO).exists()


def test_table_is_anonymous(mini_store, tmp_path):
    rows, mapping, out, mp = _run(mini_store, tmp_path)
    text = open(out / 'Ref_ServiceLevelProjects.csv', encoding='utf-8-sig').read().casefold()
    for name in ('invented tower', 'phase one', 'phase two', 'doubled', 'tower 2026', 'noname', 'grouped'):
        assert name not in text


def test_refuses_to_write_a_name(tmp_path):
    rows = [{'project_id': 'S001', 'flag': 'see Invented Tower', 'name_key': '', 'snapshot': ''}]
    with pytest.raises(b.NameWouldLeak):
        b.write_outputs(rows, {'Invented Tower'}, str(tmp_path / 'o'), str(tmp_path / 'm'), [], '')
    assert not os.path.exists(tmp_path / 'o' / 'Ref_ServiceLevelProjects.csv')


def test_fee_nfa_fix():
    assert b.fee_nfa(80000, 'sum_of_types', 'Management Fee=40000.0; Apartment=40000.0') == 40000
    assert b.fee_nfa(80000, 'total_row', 'Management Fee=40000.0') == 80000
    assert b.fee_nfa(None, 'total_row', '') is None


def test_fee_nfa_group_i_row():
    groups = 'I.=16000.0; Căn hộ=13000.0; Shop=1500.0; II.=1500.0'
    assert b.fee_nfa(32000, 'sum_of_types', groups) == 16000
    # group I need not come first in the list
    assert b.fee_nfa(32000, 'sum_of_types', 'II.=1500.0; I.=16000.0; Căn hộ=16000.0') == 16000
    # a zero group I row falls back to the Management Fee rule, then to the total
    assert b.fee_nfa(80000, 'sum_of_types', 'I.=0; Management Fee=40000.0; Apartment=40000.0') == 40000
    assert b.fee_nfa(30000, 'sum_of_types', 'I.=0; Apartment=30000.0') == 30000
    # a product whose label merely starts with I is not the group row; total_row files keep their total
    assert b.fee_nfa(30000, 'sum_of_types', 'Industrial=10000.0; Apartment=20000.0') == 30000
    assert b.fee_nfa(30000, 'total_row', 'I.=15000.0') == 30000
