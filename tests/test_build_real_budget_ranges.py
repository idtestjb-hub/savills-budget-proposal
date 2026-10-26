"""Unit tests for build_real_budget_ranges.py on an invented mini-store (SQLite fixture, invented names and figures).

Covered (tasks 1.1): main sheet and high confidence only, no PDF / xlsb / content duplicate, latest year per project
(tie: later file date), an unnamed file as its own project, two names with one identical NFA merged, a stale name
with a different NFA kept apart, the "I." group NFA for a summed product list, zero and blank counted not valued,
lines on other sheets ignored, name_key and nfa_m2, the CPI factor, and the refusal when a name would be written.
"""
import csv
import os
import sqlite3

import pytest

import build_real_budget_ranges as b
import real_budget_ranges as rbr

FILES = [
    # file_id, project, file_name, year, modified, nfa_total, how, types, dup, source, sheet, confidence, months
    ('f01', 'Invented Tower', 'tower 2025.xlsx', 2025, '2025-01-01 10:00', 60000, 'total_row', '', '', 'excel', 'MF', 'high', 12),
    ('f02', 'Invented Tower', 'tower 2026.xlsx', 2026, '2026-01-01 10:00', 60004, 'total_row', '', '', 'excel', 'MF', 'high', 12),
    ('f03', '', 'noname.xlsx', 2027, '2026-02-01 10:00', 100000, 'total_row', '', '', 'excel', 'MF', 'high', 12),
    ('f04', 'Phase One', 'p1.xlsx', 2026, '2026-03-01 10:00', 53826, 'total_row', '', '', 'excel', 'MF', 'high', 9),
    ('f05', 'Phase Two', 'p2.xlsx', 2026, '2026-04-01 10:00', 53826, 'total_row', '', '', 'excel', 'MF', 'high', 4),
    ('f06', 'Grouped', 'grouped.xlsx', 2024, '2024-01-01 10:00', 33566.2, 'sum_of_types',
     'I.=16783.1; Căn hộ=13936.1; Shop=1422.3; II.=1424.7', '', 'excel', 'MF', 'high', 12),
    ('f07', 'Scanned', 'scan.pdf', 2026, '2026-06-01 10:00', 50000, 'total_row', '', '', 'pdf_ocr', 'MF', 'high', 12),
    ('f08', 'Binary', 'bin.xlsb', 2026, '2026-06-01 10:00', 50000, 'total_row', '', '', 'xlsb_converted', 'MF', 'high', 12),
    ('f09', 'Copy', 'copy.xlsx', 2026, '2026-06-01 10:00', 60004, 'total_row', '', 'f02', 'excel', 'MF', 'high', 12),
    ('f10', 'Loose', 'loose.xlsx', 2026, '2026-06-01 10:00', 45000, 'total_row', '', '', 'excel', 'MF', 'medium', 12),
    ('f11', 'No Area', 'noarea.xlsx', 2026, '2026-06-01 10:00', None, 'not_found', '', '', 'excel', 'MF', 'high', 12),
    ('f12', 'Stale Name', 'stale a.xlsx', 2025, '2025-05-01 10:00', 65454, 'total_row', '', '', 'excel', 'MF', 'high', 12),
    ('f13', 'Stale Name', 'stale b.xlsx', 2025, '2025-06-01 10:00', 39833, 'total_row', '', '', 'excel', 'MF', 'high', 12),
    ('f14', 'Twin Year', 'twin v4.xlsx', 2028, '2025-11-25 10:00', 20000, 'total_row', '', '', 'excel', 'MF', 'high', 12),
    ('f15', 'Twin Year', 'twin v6.xlsx', 2028, '2026-01-28 10:00', 20000, 'total_row', '', '', 'excel', 'MF', 'high', 12),
]
LINES = [
    # file_id, sheet, row, code, amount_excl_vat_per_month
    ('f01', 'MF', 1, 'ESS12', 900000),
    ('f02', 'MF', 1, 'ESS12', 1200080),       # 1,200,080 / 60,004 -> 20 per m2 per month
    ('f02', 'MF', 2, 'ESS7', 0),              # zero -> counted, not valued
    ('f02', 'OTHER', 3, 'ESS12', 99999999),   # not the main sheet -> ignored
    ('f02', 'MF', 4, 'EMB4', None),           # blank -> counted, not valued
    ('f03', 'MF', 1, 'ESS12', 3000000),       # 30; f03 has no ESS7 line at all
    ('f04', 'MF', 1, 'ESS12', 538260),
    ('f05', 'MF', 1, 'ESS12', 1076520),       # kept over f04 (later file date): 20
    ('f06', 'MF', 1, 'ESS12', 335662),        # 335,662 / 16,783.1 = 20 (not / 33,566.2)
    ('f10', 'MF', 1, 'ESS12', 450000),
    ('f12', 'MF', 1, 'ESS12', 654540),
    ('f13', 'MF', 1, 'ESS12', 398330),
    ('f14', 'MF', 1, 'ESS12', 1),
    ('f15', 'MF', 1, 'ESS12', 418000),        # 20.9 in 2028 prices
    ('f15', 'MF', 2, 'ESS12', 0),             # a second row of the same code adds to the first
    # rate code RM.AP (change price-fee-and-parking-from-portfolio): (RM.AP + RM.0A) / apartment NFA
    ('f02', 'MF', 5, 'RM.AP', 1000000),       # (1,000,000 + 250,000) / 50,000 apartment m2 = 25 per m2 per month
    ('f02', 'MF', 6, 'RM.0A', 250000),
    ('f03', 'MF', 2, 'RM.AP', 3000000),       # above 0 but no apartment NFA -> no row, listed in the README
    ('f05', 'MF', 2, 'RM.AP', 538260),        # / 53,826 apartment m2 = 10; no RM.0A line
    ('f06', 'MF', 2, 'RM.AP', 0),             # zero -> counted, not valued
]
APARTMENT_NFA = {'f02': 50000, 'f05': 53826, 'f06': 13936.1}   # file_profile.nfa_apartment; None elsewhere
CPI_ROWS = [(2024, 3.63, 'published'), (2025, 3.31, 'published'), (2026, 4.52, 'stand-in'),
            (2027, 4.52, 'stand-in'), (2028, 4.52, 'stand-in')]


def write_cpi(path, rows=CPI_ROWS):
    with open(path, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['year', 'avg_cpi_change_pct', 'status', 'source', 'source_url', 'checked_on', 'note'])
        for y, r, s in rows:
            w.writerow([y, r, s, 'invented source', '', '2026-10-18', ''])
    return str(path)


@pytest.fixture
def mini_store(tmp_path):
    folder = tmp_path / 'final_v2'
    folder.mkdir()
    db = folder / b.STORE_FILE
    con = sqlite3.connect(db)
    con.execute('create table file_profile (file_id text, file_name text, source_type text, content_dup_of text, '
                'primary_sheet text, primary_confidence text, budget_year_v2 real, months_in_period real, '
                'nfa_total real, nfa_how text, nfa_types text, nfa_apartment real)')
    con.execute('create table dim_file (file_id text, file_name text, rel_path text, modified text, source_type text, '
                'content_dup_of text)')
    con.execute('create table project_map (file_id text, file_name text, project_name text)')
    con.execute('create table fact_line (file_id text, sheet text, source_row real, code text, '
                'amount_excl_vat_per_month real)')
    for fid, proj, fname, yr, mod, nfa, how, types, dup, st, sheet, conf, months in FILES:
        con.execute('insert into file_profile values (?,?,?,?,?,?,?,?,?,?,?,?)',
                    (fid, fname, st, dup or None, sheet, conf, yr, months, nfa, how, types, APARTMENT_NFA.get(fid)))
        con.execute('insert into dim_file values (?,?,?,?,?,?)', (fid, fname, 'sub/' + fname, mod, st, dup or None))
        con.execute('insert into project_map values (?,?,?)', (fid, fname, proj or None))
    con.executemany('insert into fact_line values (?,?,?,?,?)', LINES)
    con.commit()
    con.close()
    return str(folder), write_cpi(tmp_path / 'cpi.csv')


def _run(mini_store, tmp_path, extra=()):
    store, cpi = mini_store
    out, mp = tmp_path / 'out', tmp_path / 'map'
    b.main(['--store', store, '--out', str(out), '--map', str(mp), '--cpi', cpi, '--master', ''] + list(extra))
    rows = rbr.load_values(str(out / b.VALUES_FILE))
    with open(mp / b.MAP_FILE, encoding='utf-8-sig') as fh:
        mapping = {r['project_id']: r for r in csv.DictReader(fh)}
    return rows, mapping, out, mp


def test_store_rules(mini_store, tmp_path):
    rows, mapping, out, mp = _run(mini_store, tmp_path)
    files = {m['file_id'] for m in mapping.values()}
    # latest year (f02), unnamed own project (f03), identical NFA merged keeping the later file (f05), group NFA (f06),
    # stale name kept apart (f12, f13), same year -> later file date (f15); pdf, xlsb, duplicate, medium, no NFA out
    assert files == {'f02', 'f03', 'f05', 'f06', 'f12', 'f13', 'f15'}
    assert [m['project_id'] for m in sorted(mapping.values(), key=lambda m: m['file_id'])] == \
        [f'P{i:03d}' for i in range(1, 8)]
    readme = open(out / b.README_FILE, encoding='utf-8').read()
    for fid in ('f01', 'f04', 'f07', 'f08', 'f09', 'f10', 'f11', 'f14'):
        assert fid in readme


def test_values_zero_blank_and_absent(mini_store, tmp_path):
    rows, mapping, out, mp = _run(mini_store, tmp_path)
    by = {(mapping[r['project_id']]['file_id'], r['code']): r for r in rows}
    ess12 = by[('f02', 'ESS12')]
    assert ess12['status'] == rbr.STATUS_VALUE and ess12['value_m2_month'] == pytest.approx(20.0, abs=1e-4)
    assert ess12['budget_year'] == 2026 and ess12['cpi_factor'] == pytest.approx(1.0452)
    assert ess12['value_m2_month_2027'] == pytest.approx(20.904, abs=1e-4)
    # zero and blank: a row, no value
    for key in (('f02', 'ESS7'), ('f02', 'EMB4')):
        assert by[key]['status'] == rbr.STATUS_ZERO and by[key]['value_m2_month'] is None
    # no line on the sheet: no row
    assert ('f03', 'ESS7') not in by
    # the "I." group NFA: 335,662 / 16,783.1 = 20; 2024 -> 2027 factor
    g = by[('f06', 'ESS12')]
    assert g['value_m2_month'] == pytest.approx(20.0, abs=1e-3) and b.FLAG_NFA_GROUP_I in g['flag']
    assert g['cpi_factor'] == pytest.approx(1.0331 * 1.0452 * 1.0452, abs=1e-6)
    assert g['nfa_m2'] == 16780
    # 2028 budget divided by the 2028 rate; two rows of one code add up
    assert by[('f15', 'ESS12')]['value_m2_month'] == pytest.approx(20.9)
    assert by[('f15', 'ESS12')]['value_m2_month_2027'] == pytest.approx(20.9 / 1.0452, abs=1e-4)
    # a 2027 budget keeps factor 1; unnamed: blank name_key, flagged
    u = by[('f03', 'ESS12')]
    assert u['cpi_factor'] == 1.0 and u['name_key'] == '' and b.FLAG_UNNAMED in u['flag']
    assert by[('f02', 'ESS12')]['name_key'] == rbr.name_key('Invented Tower') and by[('f02', 'ESS12')]['nfa_m2'] == 60000
    assert b.FLAG_STALE_NAME in by[('f12', 'ESS12')]['flag'] and b.FLAG_STALE_NAME in by[('f13', 'ESS12')]['flag']
    # the stale name pair carries no name_key: running one of them by name and NFA leaves out only that one
    assert by[('f12', 'ESS12')]['name_key'] == by[('f13', 'ESS12')]['name_key'] == ''
    pid12 = by[('f12', 'ESS12')]['project_id']
    res = rbr.price_line('ESS12', rows, nfa=65454, vat_rate=0.1, self_name='Stale Name')
    assert [p for p, v, why in res.left_out if why.startswith('chính dự án')] == [pid12]
    assert 'kỳ 4 tháng' in by[('f05', 'ESS12')]['flag']
    readme = open(out / b.README_FILE, encoding='utf-8').read()
    assert '  ESS12: 7 / 0 / 0' in readme and '  ESS7: 0 / 1 / 6' in readme


def test_rate_code_per_apartment_nfa(mini_store, tmp_path):
    """Change price-fee-and-parking-from-portfolio, task 1.1: RM.AP = (RM.AP + RM.0A) / apartment NFA, basis column,
    no row without an apartment NFA, zero counted, the other codes keep basis fee_nfa."""
    rows, mapping, out, mp = _run(mini_store, tmp_path)
    by = {(mapping[r['project_id']]['file_id'], r['code']): r for r in rows}
    full = by[('f02', 'RM.AP')]
    assert full['status'] == rbr.STATUS_VALUE and full['value_m2_month'] == pytest.approx(25.0)
    assert full['basis'] == rbr.BASIS_APARTMENT_NFA and full['nfa_m2'] == 60000      # nfa_m2 stays the fee-paying NFA
    assert full['value_m2_month_2027'] == pytest.approx(25.0 * 1.0452, abs=1e-4)
    assert by[('f05', 'RM.AP')]['value_m2_month'] == pytest.approx(10.0)              # no RM.0A line: RM.AP alone
    assert by[('f06', 'RM.AP')]['status'] == rbr.STATUS_ZERO
    assert ('f03', 'RM.AP') not in by and ('f03', 'ESS12') in by                      # left out for RM.AP only
    assert by[('f02', 'ESS12')]['basis'] == rbr.BASIS_FEE_NFA
    readme = open(out / b.README_FILE, encoding='utf-8').read()
    assert '  RM.AP: 2 / 1 / 4' in readme and 'f03: RM.AP above 0 but no apartment NFA' in readme
    assert 'apartment_nfa' in readme
    with open(out / b.VALUES_FILE, encoding='utf-8-sig') as fh:
        assert csv.DictReader(fh).fieldnames == rbr.VALUE_COLUMNS


def test_output_is_anonymous(mini_store, tmp_path):
    rows, mapping, out, mp = _run(mini_store, tmp_path)
    for fname in (b.VALUES_FILE, b.README_FILE):
        text = b._norm(open(out / fname, encoding='utf-8-sig').read())
        for f in FILES:
            for name in (f[1], f[2]):
                if len(b._norm(name)) >= 4:
                    assert b._norm(name) not in text
    names = open(mp / b.NAMES_FILE, encoding='utf-8').read().splitlines()
    assert 'Invented Tower' in names and 'tower 2026.xlsx' in names


def test_refuses_to_write_a_name(tmp_path):
    rows = [{'project_id': 'P001', 'flag': 'see Invented Tower'}]
    with pytest.raises(b.NameWouldLeak):
        b.write_outputs(rows, [], {}, {'Invented Tower'}, 'ok', str(tmp_path / 'o'), str(tmp_path / 'm'))
    with pytest.raises(b.NameWouldLeak):
        b.write_outputs([], [], {}, {'Invented Tower'}, 'line\nmerged invented-tower here', str(tmp_path / 'o'),
                        str(tmp_path / 'm'))
    assert not os.path.exists(tmp_path / 'o')


def test_out_is_required_and_map_stays_outside(mini_store, tmp_path):
    store, cpi = mini_store
    with pytest.raises(SystemExit):
        b.main(['--store', store])
    with pytest.raises(ValueError):
        b.build(store, str(tmp_path / 'o'), cpi, map_dir=os.path.join(rbr.BUDGET_AGENT, 'data'))


def test_fee_nfa():
    assert b.fee_nfa(33566.2, 'sum_of_types', 'I.=16783.1; Căn hộ=13936.1; II.=1424.7') == (16783.1, b.FLAG_NFA_GROUP_I)
    assert b.fee_nfa(80000, 'sum_of_types', 'Management Fee=40000.0; Apartment=40000.0') == (40000, '')
    assert b.fee_nfa(80000, 'total_row', 'I.=100') == (80000, '')
    assert b.fee_nfa(None, 'total_row', '') == (None, '')


# ---- change widen-real-budget-store (2026-10-22): a checked NFA for a file whose profile has none -----------------

NFA_FILES = [
    # file_id, project, year, RM.* per month excl. VAT on the main sheet; every profile without an NFA
    ('n01', 'Invented Harbour', 2026, 1061800000),   # master 61,987.75 m2 at 18,500 incl. VAT -> 17,130 = reference
    ('n02', 'Invented Lake', 2026, 1912600000),      # master 54,624 m2 -> 35,014 vs 18,000 / 1.08: fails
    ('n03', 'Nowhere Name', 2026, 500000000),        # no master-list row
    ('n04', 'Invented Twin', 2026, 500000000),       # two master-list rows of the same name
    ('n05', 'Invented Lake', 2026, 0),               # no fee revenue, table row approved -> enters
    ('n06', 'Invented Harbour', 2026, 0),            # matches the master list, no fee revenue, no table row -> out
    ('n07', 'Invented Ridge', 2023, 307500000),      # table row with the file's own rate (excl. VAT)
    ('n08', 'Invented Unapproved', 2026, 0),         # table row without approved_on -> ignored -> out
]
MASTER_ROWS = [
    ('Invented Harbour', 61987.75, 18500, 'incl_VAT'),
    ('Invented Lake', 54624, 18000, 'incl_VAT'),
    ('Invented Twin', 30000, 16000, 'incl_VAT'),
    ('Invented Twin', 31000, 16000, 'incl_VAT'),
]
TABLE_ROWS = [
    # file_id, nfa_fee, nfa_apartment, ref_rate, ref_rate_vat, approved_on
    ('n05', 20944.7, 18641, '', '', '2026-10-22'),
    ('n07', 20500, '', 15500, 'excl', '2026-10-22'),     # 307,500,000 / 20,500 = 15,000 vs 15,500: -3.2%
    ('n08', 10000, '', '', '', ''),
]
VAT_CUTS = [('2022-02', '2022-12', 0.08), ('2023-07', '2023-12', 0.08), ('2024-01', '2026-12', 0.08)]


@pytest.fixture
def nfa_store(mini_store, tmp_path):
    store, cpi = mini_store
    con = sqlite3.connect(os.path.join(store, b.STORE_FILE))
    for fid, proj, yr, rm in NFA_FILES:
        con.execute('insert into file_profile values (?,?,?,?,?,?,?,?,?,?,?,?)',
                    (fid, fid + '.xlsx', 'excel', None, 'MF', 'high', yr, 12, None, 'not_found', '', None))
        con.execute('insert into dim_file values (?,?,?,?,?,?)', (fid, fid + '.xlsx', 'sub/' + fid, '2026-01-01', 'excel', None))
        con.execute('insert into project_map values (?,?,?)', (fid, fid + '.xlsx', proj))
        con.execute('insert into fact_line values (?,?,?,?,?)', (fid, 'MF', 1, 'RM.AP', rm))
        con.execute('insert into fact_line values (?,?,?,?,?)', (fid, 'MF', 2, 'ESS12', 1000000))
    con.execute('create table vat_cut_period ("from" text, "to" text, rate real, legal_basis text)')
    con.executemany('insert into vat_cut_period values (?,?,?,?)', [c + ('invented',) for c in VAT_CUTS])
    con.commit()
    con.close()
    master = tmp_path / 'master.csv'
    with open(master, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['Name', 'NFA_m2', 'MgmtFeeRate_Primary', 'MgmtFeeVAT'])
        w.writerows(MASTER_ROWS)
    table = tmp_path / 'nfa_per_file.csv'
    with open(table, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['file_id', 'nfa_fee', 'nfa_apartment', 'source_sheet', 'source_cell', 'ref_rate', 'ref_rate_vat',
                    'approved_on', 'note'])
        for fid, nfa, apt, ref, vat, ok in TABLE_ROWS:
            w.writerow([fid, nfa, apt, 'invented sheet', 'A1', ref, vat, ok, ''])
    return ['--master', str(master), '--nfa-table', str(table)]


def test_checked_nfa(mini_store, nfa_store, tmp_path):
    rows, mapping, out, mp = _run(mini_store, tmp_path, nfa_store)
    by = {(mapping[r['project_id']]['file_id'], r['code']): r for r in rows}
    files = {m['file_id'] for m in mapping.values()}
    # master list passes the fee check; table with no fee revenue; table with the file's own rate
    assert {'n01', 'n05', 'n07'} <= files and not {'n02', 'n03', 'n04', 'n06', 'n08'} & files
    assert by[('n01', 'ESS12')]['nfa_m2'] == 61990 and b.FLAG_NFA_MASTER in by[('n01', 'ESS12')]['flag']
    assert by[('n05', 'ESS12')]['value_m2_month'] == pytest.approx(1000000 / 20944.7, abs=1e-3)
    assert b.FLAG_NFA_TABLE in by[('n05', 'ESS12')]['flag']
    # the master list gives no apartment NFA: n01 left out for RM.AP; the table's apartment NFA is used for n05
    assert ('n01', 'RM.AP') not in by and by[('n05', 'RM.AP')]['status'] == rbr.STATUS_ZERO
    readme = open(out / b.README_FILE, encoding='utf-8').read()
    assert 'n01: NFA 61,987.8 from master list, implied 17,129 vs reference 17,130 (-0.0%)' in readme
    assert 'n02: NFA master lệch đơn giá' in readme and '(+110.1%)' in readme     # 35,014 vs 16,667
    assert 'n03: no fee-paying NFA, no master-list match, left out' in readme
    assert 'n04: no fee-paying NFA, trùng tên master' in readme
    assert 'n06: no fee-paying NFA, no fee revenue to check the master NFA, left out' in readme
    assert 'n07: NFA 20,500.0 from table, implied 15,000 vs reference 15,500 (-3.2%)' in readme
    assert 'n08: no fee-paying NFA, no master-list match, left out' in readme        # unapproved row ignored
    assert 'n01: RM.AP above 0 but no apartment NFA' in readme
    # the names of the master list and the store never reach the output
    for fname in (b.VALUES_FILE, b.README_FILE):
        text = b._norm(open(out / fname, encoding='utf-8-sig').read())
        for _, proj, _, _ in NFA_FILES:
            assert b._norm(proj) not in text


def test_vat_rate_of_year():
    assert b.vat_rate_of_year(2026, VAT_CUTS) == 0.08
    assert b.vat_rate_of_year(2023, VAT_CUTS) == 0.10           # 6 of 12 months cut: not most of the year
    assert b.vat_rate_of_year(2022, VAT_CUTS) == 0.08           # 11 of 12
    assert b.vat_rate_of_year(2021, VAT_CUTS) == 0.10
    assert b.vat_rate_of_year(2026, []) == 0.10


def test_nfa_table_stays_outside(mini_store, tmp_path):
    store, cpi = mini_store
    with pytest.raises(ValueError):
        b.build(store, str(tmp_path / 'o'), cpi, map_dir=str(tmp_path / 'm'),
                nfa_table=os.path.join(rbr.BUDGET_AGENT, 'data', 'nfa_per_file.csv'))


def test_table_row_wins_over_profile(mini_store, nfa_store, tmp_path):
    """An approved table row corrects a wrong profile NFA (a tower's sub-rows summed twice)."""
    store, _ = mini_store
    con = sqlite3.connect(os.path.join(store, b.STORE_FILE))
    con.execute('insert into file_profile values (?,?,?,?,?,?,?,?,?,?,?,?)',
                ('n09', 'n09.xlsx', 'excel', None, 'MF', 'high', 2026, 12, 194474.9, 'total_row', '', None))
    con.execute('insert into dim_file values (?,?,?,?,?,?)', ('n09', 'n09.xlsx', 'sub/n09', '2026-01-01', 'excel', None))
    con.execute('insert into project_map values (?,?,?)', ('n09', 'n09.xlsx', 'Invented Heights'))
    con.execute('insert into fact_line values (?,?,?,?,?)', ('n09', 'MF', 1, 'RM.AP', 1750275000))   # 18,000 x 97,237.5
    con.execute('insert into fact_line values (?,?,?,?,?)', ('n09', 'MF', 2, 'ESS12', 972375))
    con.commit()
    con.close()
    table = nfa_store[nfa_store.index('--nfa-table') + 1]
    with open(table, 'a', encoding='utf-8-sig', newline='') as fh:
        csv.writer(fh).writerow(['n09', 97237.5, 94849.2, 'INFO', 'D10', 18000, 'excl', '2026-10-22', ''])
    rows, mapping, out, mp = _run(mini_store, tmp_path, nfa_store)
    by = {(mapping[r['project_id']]['file_id'], r['code']): r for r in rows}
    assert by[('n09', 'ESS12')]['value_m2_month'] == pytest.approx(10.0) and by[('n09', 'ESS12')]['nfa_m2'] == 97240
    assert by[('n09', 'RM.AP')]['value_m2_month'] == pytest.approx(1750275000 / 94849.2, abs=1e-3)
    assert b.FLAG_NFA_TABLE in by[('n09', 'ESS12')]['flag']
    readme = open(out / b.README_FILE, encoding='utf-8').read()
    assert 'n09: NFA 97,237.5 from table, implied 18,000 vs reference 18,000 (+0.0%)' in readme


# ---- change add-library-overview-tab, tasks 1.1-1.4: Ref_RealBudgetUsage.csv ----
def _usage(out):
    with open(out / b.USAGE_FILE, encoding='utf-8-sig', newline='') as fh:
        rd = csv.DictReader(fh)
        assert rd.fieldnames == b.USAGE_COLUMNS
        return {r['file_id']: r for r in rd}


def test_usage_has_one_row_per_store_file(mini_store, tmp_path):
    rows, mapping, out, mp = _run(mini_store, tmp_path)
    usage = _usage(out)
    assert set(usage) == {f[0] for f in FILES}                    # exactly one row for each of the 15 files
    used = {fid for fid, r in usage.items() if r['usage'] == b.USAGE_USED}
    assert used == {m['file_id'] for m in mapping.values()}      # used rows = the projects of the values file
    assert len(used) == len({r['project_id'] for r in rows})


def test_usage_reasons(mini_store, tmp_path):
    rows, mapping, out, mp = _run(mini_store, tmp_path)
    u = _usage(out)
    want = {'f01': ('merged', 'merged_newer', 'f02'), 'f04': ('merged', 'merged_newer', 'f05'),
            'f14': ('merged', 'merged_newer', 'f15'), 'f02': ('used', 'used_full', ''), 'f05': ('used', 'used_full', ''),
            'f06': ('used', 'used_full', ''), 'f15': ('used', 'used_full', ''),
            'f03': ('used', 'used_without_rm_ap', ''),
            'f12': ('used', 'used_same_name_other_project', ''), 'f13': ('used', 'used_same_name_other_project', ''),
            'f07': ('left_out', 'scanned_pdf', ''), 'f08': ('left_out', 'converted_xlsb', ''),
            'f09': ('left_out', 'content_duplicate', ''), 'f10': ('left_out', 'not_tied', ''),
            'f11': ('left_out', 'no_nfa', '')}
    assert {fid: (r['usage'], r['reason_code'], r['merged_into']) for fid, r in u.items()} == want


def test_usage_agrees_with_readme(mini_store, tmp_path):
    rows, mapping, out, mp = _run(mini_store, tmp_path)
    u = _usage(out)
    readme = open(out / b.README_FILE, encoding='utf-8').read()
    section = readme.split('Files excluded or merged (store ids only):')[1]
    for line in section.splitlines():
        if not line.strip():
            continue
        ids = line.strip().split(':')[0].split(' / ')
        for fid in ids:
            assert fid in u
            if 'left out' in line and 'for RM.AP' not in line and 'two projects' not in line:
                assert u[fid]['usage'] in (b.USAGE_LEFT_OUT, b.USAGE_MERGED)
            if 'same project as' in line:
                assert u[fid]['usage'] == b.USAGE_MERGED and u[fid]['merged_into'] in line
            if 'above 0 but no apartment NFA' in line:
                assert (u[fid]['usage'], u[fid]['reason_code']) == (b.USAGE_USED, 'used_without_rm_ap')
            if 'two projects' in line:
                assert u[fid]['reason_code'] == 'used_same_name_other_project'


def test_usage_file_is_anonymous_and_checked(mini_store, tmp_path):
    rows, mapping, out, mp = _run(mini_store, tmp_path)
    u = _usage(out)
    # usage and reason_code come from a closed vocabulary; the two id columns carry store ids only
    assert {r['usage'] for r in u.values()} <= {b.USAGE_USED, b.USAGE_MERGED, b.USAGE_LEFT_OUT}
    assert {r['reason_code'] for r in u.values()} <= b.USAGE_REASONS
    text = b._norm(' '.join(r['file_id'] + ' ' + r['merged_into'] for r in u.values()))
    for f in FILES:
        for name in (f[1], f[2]):
            if len(b._norm(name)) >= 4:
                assert b._norm(name) not in text
    bad = [{'file_id': 'f01', 'usage': 'used', 'reason_code': 'see Invented Tower', 'merged_into': ''}]
    with pytest.raises(b.NameWouldLeak):
        b.write_outputs([], [], {}, {'Invented Tower'}, 'ok', str(tmp_path / 'o2'), str(tmp_path / 'm2'), bad)
    assert not os.path.exists(tmp_path / 'o2')


def test_usage_output_leaves_values_file_unchanged(mini_store, tmp_path):
    store, cpi = mini_store
    out1, out2 = tmp_path / 'o1', tmp_path / 'o2'
    for out, mp in ((out1, tmp_path / 'm1'), (out2, tmp_path / 'm2')):
        b.main(['--store', store, '--out', str(out), '--map', str(mp), '--cpi', cpi, '--master', ''])
    # a second run on the same store gives the same bytes; the usage file is deterministic too
    assert open(out1 / b.VALUES_FILE, 'rb').read() == open(out2 / b.VALUES_FILE, 'rb').read()
    assert open(out1 / b.USAGE_FILE, 'rb').read() == open(out2 / b.USAGE_FILE, 'rb').read()


def test_usage_rows_unknown_case_is_left_out_other():
    files = [{'file_id': 'a1'}, {'file_id': 'a2'}]
    rows = b.usage_rows(files, [{'file_id': 'a1'}], {})
    assert [(r['file_id'], r['usage'], r['reason_code']) for r in rows] == [('a1', 'used', 'used_full'),
                                                                            ('a2', 'left_out', 'other')]
