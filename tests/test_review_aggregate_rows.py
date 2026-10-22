"""Budget Review reads aggregate rows by formula, explains ties, prefers a visible sheet and a column with revenue
(change read-aggregate-rows-by-formula). Invented workbooks only; formula cells get the value Excel would have
cached written into the sheet XML, since openpyxl saves formulas without one."""
import os
import re
import zipfile
import xml.etree.ElementTree as ET

import openpyxl

import review
import review_import as ri
from test_review_import import CA_LAYOUT, CA_LINES, MF_LAYOUT, _fund_sheet

AK = 37                                   # value column of MF_LAYOUT, 1-based
R_LINES = [
    ('R', 'RM.AP', None, 1_000_000_000.0, None, 'Management fee of Apartment'),
    ('R', 'RO2', None, 12_000_000.0, None, 'Interest'),
    ('R', 'RO2a', None, 7_000_000.0, None, 'Interest a'),
    ('R', 'RO2b', None, 5_000_000.0, None, 'Interest b'),
    ('R', 'RO4', None, 300_000_000.0, None, 'Other income'),
    ('R', 'RO4.A', None, 100_000_000.0, None, 'Other income A'),
    ('R', 'RO4.B', None, 100_000_000.0, None, 'Other income B'),
    ('R', 'RO5', None, 100_000_000.0, None, 'Other income 5'),
]
E_LINES = [
    ('E', 'EMH', 'I.1', None, None, 'Staff'),
    ('E', 'EMH2', None, 600_000_000.0, None, 'Staff cost'),
    ('E', 'EMH3', None, 30_000_000.0, None, 'Holiday duty'),
    ('E', 'ESS1', None, 300_000_000.0, None, 'Security'),
    ('E', 'ESS4', None, 120_000_000.0, None, 'Cleaning'),
    ('E', 'ESM4', None, 24_000_000.0, None, 'Pool chemicals'),
    ('E', 'EEE.C', None, 80_000_000.0, None, 'Electricity'),
    ('E', 'EEW.C', None, 10_000_000.0, None, 'Water'),
]


def _sheet_part(z, title):
    rid = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
    rels = {el.get('Id'): el.get('Target') for el in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    for el in ET.fromstring(z.read('xl/workbook.xml')).iter():
        if el.tag.endswith('}sheet') and el.get('name') == title:
            t = rels[el.get(rid)]
            return t.lstrip('/') if t.startswith('/') else 'xl/' + t
    raise KeyError(title)


def _set_cached(path, title, values):
    """Write Excel's cached value into formula cells: {cell ref: number}."""
    with zipfile.ZipFile(path) as z:
        parts = {n: z.read(n) for n in z.namelist()}
        part = _sheet_part(z, title)
    xml = parts[part].decode('utf8')
    for ref, v in values.items():
        pat = re.compile(r'(<c r="%s"[^>]*>)(<f>.*?</f>)(<v\s*/>|<v>.*?</v>)?' % ref, re.S)
        xml, n = pat.subn(lambda m: f'{m.group(1)}{m.group(2)}<v>{v!r}</v>', xml)
        assert n == 1, ref
    parts[part] = xml.encode('utf8')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        for n, b in parts.items():
            z.writestr(n, b)


def _base(path, mf_title='2. Budget-Management Fund', extra=None):
    """Cover + MF sheet from R_LINES + E_LINES (+ CA). Returns (wb, mf sheet, rows by code, totals as written)."""
    wb = openpyxl.Workbook()
    wb.active.title = 'Cover'
    if extra:
        extra(wb)
    mf = wb.create_sheet(mf_title)
    rows, totals = _fund_sheet(mf, MF_LAYOUT, R_LINES + E_LINES)
    ca = wb.create_sheet('2.2 Common area Fund')
    _fund_sheet(ca, CA_LAYOUT, CA_LINES)
    return wb, mf, rows, totals


def _cell(row):
    return f'AK{row}'


def _subtotal_parents(mf, rows):
    """RO2 = SUBTOTAL over RO2a:RO2b; RO4 = SUBTOTAL over RO4.A .. RO5 (spans the sibling RO5)."""
    mf.cell(row=rows['RO2'], column=AK, value=f"=SUBTOTAL(9,AK{rows['RO2a']}:AK{rows['RO2b']})")
    mf.cell(row=rows['RO4'], column=AK, value=f"=SUBTOTAL(9,AK{rows['RO4.A']}:AK{rows['RO5']})")
    return {_cell(rows['RO2']): 12_000_000.0, _cell(rows['RO4']): 300_000_000.0}


LEAF_R = 1_000_000_000.0 + 7_000_000.0 + 5_000_000.0 + 300_000_000.0     # RM.AP, RO2a, RO2b, RO4.A, RO4.B, RO5
LEAF_E = 600_000_000.0 + 30_000_000.0 + 300_000_000.0 + 120_000_000.0 + 24_000_000.0 + 80_000_000.0 + 10_000_000.0


def test_subtotal_spanning_a_sibling_is_not_counted(tmp_path):
    p = os.path.join(tmp_path, 'subtotal.xlsx')
    wb, mf, rows, _ = _base(p)
    cached = _subtotal_parents(mf, rows)
    mf.cell(row=rows['R'], column=AK, value=LEAF_R)                   # the file's R: SUBTOTAL skips nested SUBTOTALs
    wb.save(p)
    _set_cached(p, '2. Budget-Management Fund', cached)
    fr = ri.read_prior_budget(p, workdir=str(tmp_path)).funds['MF']
    codes = [l.code for l in fr.lines]
    assert 'RO4' not in codes and 'RO2' not in codes
    assert codes.count('RO5') == 1 and 'RO4.A' in codes
    assert fr.value_col == AK and fr.value_how == 'reconciled'
    assert fr.tie_state == 'ok'
    assert abs(fr.section_total('R') - LEAF_R) <= 1 and abs(fr.section_total('E') - LEAF_E) <= 1


def test_the_prefix_rule_alone_counted_ro4_twice(tmp_path):
    # the same file read without its formulas (as before this change): RO4's children by prefix do not add up to it
    p = os.path.join(tmp_path, 'subtotal.xlsx')
    wb, mf, rows, _ = _base(p)
    cached = _subtotal_parents(mf, rows)
    mf.cell(row=rows['R'], column=AK, value=LEAF_R)
    wb.save(p)
    _set_cached(p, '2. Budget-Management Fund', cached)
    wbv = openpyxl.load_workbook(p, read_only=True, data_only=True)
    fr = ri.read_fund_sheet(wbv['2. Budget-Management Fund'], 'MF', '2. Budget-Management Fund')
    wbv.close()
    assert 'RO4' in [l.code for l in fr.lines]
    assert fr.tie_state == 'mismatch'


def test_a_file_saved_with_a_filter_ties_after_explanation(tmp_path):
    p = os.path.join(tmp_path, 'filter.xlsx')
    wb, mf, rows, _ = _base(p)
    cached = _subtotal_parents(mf, rows)
    for code in ('RO4.A', 'RO4.B', 'EMH3'):                            # filtered out when the file was saved
        mf.row_dimensions[rows[code]].hidden = True
    mf.auto_filter.ref = f"X11:AZ{rows['EEW.C']}"
    mf.cell(row=rows['R'], column=AK, value=LEAF_R - 200_000_000.0)    # SUBTOTAL skips the filtered rows
    mf.cell(row=rows['E'], column=AK, value=LEAF_E - 30_000_000.0)
    wb.save(p)
    _set_cached(p, '2. Budget-Management Fund', cached)
    prior = ri.read_prior_budget(p, workdir=str(tmp_path))
    fr = prior.funds['MF']
    assert fr.tie_state == 'ok_filter' and fr.value_col == AK
    assert fr.tie_notes == ['ô tổng bị bộ lọc che (3 dòng ẩn)']
    codes = {l.code: l.annual for l in fr.lines}
    assert codes['RO4.A'] == 100_000_000.0 and codes['EMH3'] == 30_000_000.0     # hidden lines keep their values
    assert abs(fr.section_total('R') - LEAF_R) <= 1
    assert (ri.NOTE_SOURCE, '2. Budget-Management Fund', 'ô tổng bị bộ lọc che (3 dòng ẩn)') in prior.notes
    assert not any(k == ri.NOTE_UNREAD and 'khác dòng' in t for k, _, t in prior.notes)


def test_a_parent_written_with_sum_ties_after_explanation(tmp_path):
    p = os.path.join(tmp_path, 'sum.xlsx')
    wb, mf, rows, _ = _base(p)
    cached = _subtotal_parents(mf, rows)
    mf.cell(row=rows['RO2'], column=AK, value=f"=SUM(AK{rows['RO2a']}:AK{rows['RO2b']})")
    mf.cell(row=rows['R'], column=AK, value=LEAF_R + 12_000_000.0)     # SUBTOTAL counts the SUM cell on top
    wb.save(p)
    _set_cached(p, '2. Budget-Management Fund', cached)
    prior = ri.read_prior_budget(p, workdir=str(tmp_path))
    fr = prior.funds['MF']
    assert fr.tie_state == 'ok_double_count' and fr.value_col == AK
    assert fr.tie_notes == ['lỗi file: RO2 dùng SUM, tổng của file cộng trùng 12,000,000 VND']
    assert abs(fr.section_total('R') - LEAF_R) <= 1
    # the Review's source-file tie holds with the note, and fails only when nothing explains the gap
    anchors = review.prior_anchors(prior)
    assert anchors['MF']['explained'] == 'ok_double_count'
    data = review.assemble([dict(fund='MF', section=s, code='X' + s, item='x', approved=fr.section_total(s),
                                 incl_vat=False, flags=[], on_form=True, remark='') for s in ('R', 'E')],
                           {'MF': anchors['MF']}, {}, dict(prior_year=2026, budget_year=2027), _ctx(),
                           template={'MF': {}})
    ties = [t for t in data['ties'] if t['kind'] == 'duyệt = file nguồn']
    assert all(t['ok'] for t in ties)
    r_tie = next(t for t in ties if t['section'] == 'R')
    assert r_tie['diff'] == -12_000_000.0 and 'RO2 dùng SUM' in r_tie['note']


def test_a_visible_sheet_is_read_before_a_hidden_scenario_sheet(tmp_path):
    p = os.path.join(tmp_path, 'two_sheets.xlsx')

    def hidden_scenario(wb):
        op3 = wb.create_sheet('2. Budget-Management Fund (OP3)')
        _fund_sheet(op3, MF_LAYOUT, [(s, c, i, (a * 2 if a else a), m, t) for s, c, i, a, m, t in R_LINES + E_LINES])
        op3.sheet_state = 'hidden'

    wb, mf, rows, _ = _base(p, mf_title='2. Budget-THCN', extra=hidden_scenario)
    wb.save(p)
    prior = ri.read_prior_budget(p, workdir=str(tmp_path))
    assert prior.funds['MF'].sheet == '2. Budget-THCN'
    assert ri.choose_fund_sheets(['2. Budget-MF (OP3)', '2. Budget-THCN'],
                                 {'2. Budget-MF (OP3)': 'hidden', '2. Budget-THCN': 'visible'})['MF'] == '2. Budget-THCN'
    assert ri.choose_fund_sheets(['2. Budget-MF (OP3)', '2. Budget-THCN'])['MF'] == '2. Budget-MF (OP3)'   # no states


def test_a_column_with_no_revenue_is_not_the_year_column(tmp_path):
    p = os.path.join(tmp_path, 'zero_r.xlsx')
    wb, mf, rows, totals = _base(p)
    AE = 31                                                            # same header, R blank, E as the year column
    mf.cell(row=10, column=AE, value='Total Budget of Year\nTổng ngân sách')
    for code, r in rows.items():
        if code not in ('R', 'E') and mf.cell(row=r, column=24).value is None:       # leaf rows (no indicator in X)
            v = mf.cell(row=r, column=AK).value
            if isinstance(v, (int, float)) and r > rows['E']:
                mf.cell(row=r, column=AE, value=v)
    mf.cell(row=rows['R'], column=AE, value=0.0)
    mf.cell(row=rows['E'], column=AE, value=totals['E'])
    # no formulas here: the prefix rule drops RO2 (RO2a + RO2b = RO2) and keeps RO4 as a typed-in line
    mf.cell(row=rows['R'], column=AK, value=totals['R'] - 12_000_000.0)
    wb.save(p)
    fr = ri.read_prior_budget(p, workdir=str(tmp_path)).funds['MF']
    assert fr.value_col == AK and fr.tie_state == 'ok'
    assert abs(fr.section_total('R') - (totals['R'] - 12_000_000.0)) <= 1


def _ctx():
    return dict(existing=True, rate_codes=set(), rate_note='', parking_codes=set(), cob_codes=set(), methods={})


def test_a_parent_typed_with_its_childs_figure_ties_after_explanation(tmp_path):
    # RO2 carries 12,000,000 typed in, as do its children RO2a + RO2b: the file's SUBTOTAL counts both
    p = os.path.join(tmp_path, 'parent.xlsx')
    wb, mf, rows, _ = _base(p)
    cached = _subtotal_parents(mf, rows)
    mf.cell(row=rows['RO2'], column=AK, value=12_000_000.0)
    del cached[_cell(rows['RO2'])]
    mf.cell(row=rows['R'], column=AK, value=LEAF_R + 12_000_000.0)
    wb.save(p)
    _set_cached(p, '2. Budget-Management Fund', cached)
    fr = ri.read_prior_budget(p, workdir=str(tmp_path)).funds['MF']
    assert fr.tie_state == 'ok_double_count' and fr.value_col == AK
    assert fr.tie_notes == ['lỗi file: RO2 trùng số với dòng con, tổng của file cộng trùng 12,000,000 VND']
    assert 'RO2' not in [l.code for l in fr.lines]
