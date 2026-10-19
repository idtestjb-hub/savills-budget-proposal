"""Unit tests for real_budget_ranges.py on invented values (tasks 1.2, 2.1, 2.2).

Covered: PERCENTILE.INC, the CPI factor (invented table, and the five years of the real public table when present),
the project left out by name and by NFA, an outlier dropped, the 10-project floor, both VAT bases, no pool, no tower,
the ESC1 / ESC2 stand-in note, cross-check codes never priced, no values file, and the remark wording scan.
"""
import os

import pytest

import real_budget_ranges as rbr
from test_build_real_budget_ranges import write_cpi
from verification.checks import _INTERNAL_WORDING_DENYLIST

VI_MARKS = 'ạảấầẩẫậắằẳẵặẹẻẽếềểễệọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹđ'


def _rows(code, values, start=1, **extra):
    out = []
    for i, v in enumerate(values, start=start):
        r = {'project_id': f'P{i:03d}', 'name_key': '', 'nfa_m2': 10000.0 * i, 'budget_year': 2027, 'code': code,
             'status': rbr.STATUS_VALUE, 'value_m2_month': v, 'cpi_factor': 1.0, 'value_m2_month_2027': v, 'flag': ''}
        r.update(extra)
        out.append(r)
    return out


def test_percentile_inc_matches_excel():
    v = [1, 2, 3, 4]
    assert rbr.percentile_inc(v, 0.25) == pytest.approx(1.75)
    assert rbr.percentile_inc(v, 0.5) == pytest.approx(2.5)
    assert rbr.percentile_inc(v, 0.75) == pytest.approx(3.25)
    assert rbr.percentile_inc([7], 0.25) == 7 and rbr.percentile_inc([], 0.5) is None


def test_cpi_factor_invented_table(tmp_path):
    cpi = rbr.load_cpi(write_cpi(tmp_path / 'cpi.csv', [(2021, 1.0, 'published'), (2022, 2.0, 'published'),
                                                         (2025, 3.0, 'published'), (2026, 4.0, 'stand-in'),
                                                         (2027, 5.0, 'stand-in'), (2028, 6.0, 'stand-in'),
                                                         (2023, 0.0, 'published'), (2024, 0.0, 'published')]))
    assert rbr.cpi_factor(2027, cpi) == 1.0
    assert rbr.cpi_factor(2026, cpi) == pytest.approx(1.05)
    assert rbr.cpi_factor(2025, cpi) == pytest.approx(1.04 * 1.05)
    assert rbr.cpi_factor(2021, cpi) == pytest.approx(1.02 * 1.0 * 1.0 * 1.03 * 1.04 * 1.05)
    assert rbr.cpi_factor(2028, cpi) == pytest.approx(1 / 1.06)
    with pytest.raises(KeyError):
        rbr.cpi_factor(2019, cpi)


def test_cpi_factor_public_table():
    """Task 1.2: the factors of the public table (read-only; skipped where the data folder is absent)."""
    if not os.path.exists(rbr.CPI_CSV):
        pytest.skip('Ref_CPI_VN.csv not present in this checkout')
    cpi = rbr.load_cpi()
    assert cpi[2025].rate == pytest.approx(0.0331) and cpi[2025].status == 'published'
    assert cpi[2026].status == cpi[2027].status == cpi[2028].status == 'stand-in'
    assert rbr.cpi_factor(2027, cpi) == 1.0
    assert rbr.cpi_factor(2026, cpi) == pytest.approx(1.0452)
    assert rbr.cpi_factor(2025, cpi) == pytest.approx(1.0452 ** 2)
    assert rbr.cpi_factor(2021, cpi) == pytest.approx(1.0315 * 1.0325 * 1.0363 * 1.0331 * 1.0452 ** 2)
    assert rbr.cpi_factor(2028, cpi) == pytest.approx(1 / 1.0452)
    assert all(c.source for c in cpi.values())


def test_leave_one_out_by_name_and_by_nfa():
    rows = _rows('ESS12', [100 + i for i in range(12)])
    rows[0]['name_key'] = rbr.name_key('Invented Park')
    res = rbr.price_line('ESS12', rows, nfa=36679, vat_rate=0.10, self_name='invented  PARK', self_nfa=1)
    assert ('P001', 100, rbr.OUT_SELF_NAME) in res.left_out and 'P001' not in [p for p, _ in res.used]
    # NFA within 0.5% of P003 (30,000 m2): 30,140 is in, 30,160 is out
    res = rbr.price_line('ESS12', rows, nfa=30140, vat_rate=0.10)
    assert ('P003', 102, rbr.OUT_SELF_NFA) in res.left_out and res.n_used == 11
    res = rbr.price_line('ESS12', rows, nfa=30160, vat_rate=0.10)
    assert res.n_used == 12 and not res.left_out


def test_outlier_dropped_once():
    rows = _rows('EMB4', [50, 52, 54, 55, 56, 57, 58, 60, 61, 62, 400])
    res = rbr.price_line('EMB4', rows, nfa=36679, vat_rate=0.10)
    assert ('P011', 400, rbr.OUT_HIGH) in res.left_out and res.n_used == 10
    assert res.usable and res.median == pytest.approx(56.5)
    assert res.p25 == pytest.approx(rbr.percentile_inc([50, 52, 54, 55, 56, 57, 58, 60, 61, 62], 0.25))


def test_floor_of_ten():
    rows = _rows('ESC5', [10 + i for i in range(10)])
    rows[0]['name_key'] = rbr.name_key('Invented Park')   # the project itself leaves 9
    res = rbr.price_line('ESC5', rows, nfa=36679, vat_rate=0.10, self_name='Invented Park')
    assert not res.usable and res.figure == 0 and res.n_used == 9
    assert res.reason == rbr.reason_too_few(9) and 'chưa đủ tối thiểu 10' in res.reason
    assert rbr.price_line('ESC5', rows, nfa=36679, vat_rate=0.10).usable


def test_figure_both_vat_bases_and_cpi_value_used():
    rows = _rows('ESS12', [100.0] * 5 + [120.0] * 6)
    rows[0].update(budget_year=2025, value_m2_month=80.0, cpi_factor=1.25, value_m2_month_2027=100.0)
    inc = rbr.price_line('ESS12', rows, nfa=36679, vat_rate=0.10, vat_inclusive=True)
    exc = rbr.price_line('ESS12', rows, nfa=36679, vat_rate=0.10, vat_inclusive=False)
    assert inc.median == 120.0
    assert exc.figure == round(120.0 * 36679 * 12) and inc.figure == round(120.0 * 36679 * 12 * 1.1)
    assert inc.figure_excl_vat == exc.figure_excl_vat


def test_pool_and_tower_gates():
    pool = _rows('ESS23', [300 + i for i in range(12)])
    assert rbr.price_line('ESS23', pool, nfa=36679, vat_rate=0.1, has_pool=False).reason == rbr.REASON_NO_POOL
    assert rbr.price_line('ESS23', pool, nfa=36679, vat_rate=0.1, has_pool=None).figure == 0
    assert rbr.price_line('ESS23', pool, nfa=36679, vat_rate=0.1, has_pool=True).usable
    tower = _rows('ESS7', [200 + i for i in range(12)])
    no = rbr.price_line('ESS7', tower, nfa=36679, vat_rate=0.1, tower_count=0)
    assert no.reason == rbr.REASON_NO_TOWER and no.figure == 0 and no.n_used == 12
    assert rbr.price_line('ESS7', tower, nfa=36679, vat_rate=0.1, tower_count=2).usable


def test_cross_check_never_priced_and_no_file():
    rows = _rows('ESI1', [500 + i for i in range(12)])
    res = rbr.price_line('ESI1', rows, nfa=36679, vat_rate=0.1)
    assert res.cross_check and not res.usable and res.figure > 0 and res.remark == ''
    res = rbr.price_line('EMB4', None, nfa=36679, vat_rate=0.1)
    assert not res.usable and res.reason == rbr.REASON_NO_DATA and res.figure == 0
    assert rbr.load_values(os.path.join('no', 'such', 'file.csv')) is None
    out = rbr.price_all(None, nfa=36679, vat_rate=0.1)
    assert set(out) == set(rbr.ALL_CODES) and all(r.figure == 0 for r in out.values())


def test_zero_rows_counted_not_used():
    rows = _rows('ESC2', [30 + i for i in range(10)])
    rows += [{**rows[0], 'project_id': 'P099', 'status': rbr.STATUS_ZERO, 'value_m2_month': None,
              'value_m2_month_2027': None}]
    res = rbr.price_line('ESC2', rows, nfa=36679, vat_rate=0.1)
    assert res.n_value == 10 and res.n_zero == 1 and res.n_used == 10


def test_remark_sentences():
    rows = _rows('ESS12', [100 + 2 * i for i in range(30)])
    res = rbr.price_line('ESS12', rows, nfa=36679, vat_rate=0.10, budget_year=2027)
    t = res.remark
    assert f'trung vị {res.median:,.1f} đ/m²/tháng' in t and '30 dự án do Savills quản lý' in t
    assert f'{res.p25:,.1f}–{res.p75:,.1f} đ/m²/tháng' in t and 'chưa VAT, theo giá năm 2027' in t
    assert '36,679 m² NFA thu phí × 12 tháng' in t and 'cộng VAT 10% năm 2027' in t
    exc = rbr.price_line('ESS12', rows, nfa=36679, vat_rate=0.10, vat_inclusive=False)
    assert exc.remark.endswith('chưa cộng VAT.')
    ev = rbr.price_line('ESC1', _rows('ESC1', [60 + i for i in range(12)]), nfa=36679, vat_rate=0.08, budget_year=2026)
    assert rbr.STAND_IN_NOTE['ESC1'] in ev.remark and 'cộng VAT 8% năm 2026' in ev.remark
    fd = rbr.price_line('ESC2', _rows('ESC2', [30 + i for i in range(12)]), nfa=36679, vat_rate=0.1)
    assert rbr.STAND_IN_NOTE['ESC2'] in fd.remark
    texts = [t, exc.remark, ev.remark, fd.remark, rbr.reason_too_few(7), rbr.REASON_NO_DATA, rbr.REASON_NO_NFA,
             rbr.REASON_NO_POOL, rbr.REASON_NO_TOWER] + list(rbr.STAND_IN_NOTE.values())
    for text in texts:
        assert not [w for w in _INTERNAL_WORDING_DENYLIST if w in text], text
        assert any(ch in text for ch in VI_MARKS), text
        assert 'Savills Budget' not in text and 'P0' not in text


def test_self_left_out_without_trailing_parenthesis():
    """User's rule, 2026-10-19: a name with a trailing "(...)" also matches the name without it."""
    rows = _rows('ESS12', [100 + i for i in range(12)])
    rows[0]['name_key'] = rbr.name_key('Invented Garden')
    res = rbr.price_line('ESS12', rows, nfa=99, vat_rate=0.1, self_name='INVENTED GARDEN (REBUILT AS NEW PROSPECT)')
    assert ('P001', 100, rbr.OUT_SELF_NAME) in res.left_out and res.n_used == 11
    assert rbr.self_keys('A (b) (c)') == {rbr.name_key('A (b) (c)'), rbr.name_key('A (b)'), rbr.name_key('A')}
    assert rbr.self_keys('') == set() and rbr.self_keys(None) == set()
    assert rbr.price_line('ESS12', rows, nfa=99, vat_rate=0.1, self_name='Invented Gardens').n_used == 12


def test_ess23_not_priced_with_inhouse_pool_staff():
    pool = _rows('ESS23', [300 + i for i in range(12)])
    res = rbr.price_line('ESS23', pool, nfa=36679, vat_rate=0.1, has_pool=True, inhouse_pool_staff=2)
    assert not res.usable and res.figure == 0 and res.reason == rbr.reason_inhouse_pool(2)
    assert rbr.price_line('ESS23', pool, nfa=36679, vat_rate=0.1, has_pool=True, inhouse_pool_staff=0).usable
    lump = rbr.price_line('ESS23', pool, nfa=36679, vat_rate=0.1, has_pool=True, staff_lump=True)
    assert not lump.usable and lump.reason == rbr.REASON_LUMP_STAFF
    assert not [w for w in _INTERNAL_WORDING_DENYLIST if w in rbr.REASON_LUMP_STAFF]
    text = rbr.reason_inhouse_pool(3)
    assert not [w for w in _INTERNAL_WORDING_DENYLIST if w in text] and any(ch in text for ch in VI_MARKS)


def test_vat_by_month_and_clause():
    rows = _rows('ESS12', [120.0] * 12)
    flat = rbr.price_line('ESS12', rows, nfa=36679, vat_rate=0.1, vat_factors=[1.1] * 12,
                          vat_clause='cộng VAT 10% theo từng tháng')
    assert flat.months == [round(120.0 * 36679 * 12 * 1.1 / 12)] * 12 and flat.figure == sum(flat.months)
    assert 'cộng VAT 10% theo từng tháng' in flat.remark and f'= {flat.figure:,.0f} VND/năm.' in flat.remark
    mixed = rbr.price_line('ESS12', rows, nfa=36679, vat_rate=0.08, vat_factors=[1.08] * 6 + [1.1] * 6)
    assert mixed.months[0] == round(120.0 * 36679 * 1.08) and mixed.months[-1] == round(120.0 * 36679 * 1.1)
    assert mixed.figure == sum(mixed.months)
    excl = rbr.price_line('ESS12', rows, nfa=36679, vat_rate=0.1, vat_inclusive=False, vat_factors=[1.1] * 12)
    assert excl.figure == round(120.0 * 36679 * 12)


def _sheet_for(code, res, name, nfa):
    """The parts of the 'Real-Budget Ranges' sheet the verification reads, built from one invented result."""
    info = {'Project': name, 'Fee-paying NFA (m²)': nfa}
    summary = [{'Code': code, 'Role': 'Priced', 'Projects used': res.n_used,
                'Written to the deliverable (VND/year)': res.figure}]
    return info, summary, {code: [p for p, _ in res.used]}


def test_verification_ties_floor_and_leave_one_out():
    """Task 3.1 on invented fixtures: a project that matches one entry, ESS12 typed 1,000 VND off."""
    from verification.checks import real_budget_ranges_problems
    rows = _rows('ESS12', [100 + i for i in range(12)])
    rows[3]['name_key'] = rbr.name_key('Invented Harbour')
    res = rbr.price_line('ESS12', rows, nfa=12345, vat_rate=0.1, self_name='Invented Harbour')
    assert 'P004' not in [p for p, _ in res.used] and res.n_used == 11
    info, summary, used = _sheet_for('ESS12', res, 'Invented Harbour', 12345)
    assert real_budget_ranges_problems(info, summary, used, {'ESS12': res.figure}, rows) == []
    off = real_budget_ranges_problems(info, summary, used, {'ESS12': res.figure + 1000}, rows)
    assert off and off[0][0] == 'ESS12' and f'{res.figure:,.0f}' in off[0][1]
    leaked = real_budget_ranges_problems(info, summary, {'ESS12': used['ESS12'][:-1] + ['P004']}, {'ESS12': res.figure},
                                         rows)
    assert any('P004 is the project itself' in m for _, m in leaked)
    few = dict(summary[0], **{'Projects used': 9})
    assert any('under the floor' in m for _, m in
               real_budget_ranges_problems(info, [few], {'ESS12': used['ESS12'][:9]}, {'ESS12': res.figure}, rows))


def test_name_scan_on_invented_names(tmp_path):
    """The values-file name scan of check_real_budget_ranges: an invented name planted in a copy is found."""
    import csv as _csv
    from verification.checks import name_leaks
    names = tmp_path / 'names.txt'
    names.write_text('Invented Riverside Towers\nZZ Imaginary Park\nAB\n', encoding='utf-8')
    clean = tmp_path / 'clean.csv'
    with open(clean, 'w', encoding='utf-8', newline='') as fh:
        w = _csv.writer(fh)
        w.writerow(rbr.VALUE_COLUMNS)
        w.writerow(['P001', 'abc', 100, 2027, 'ESS12', 'value', 1, 1, 1, ''])
    dirty = tmp_path / 'dirty.csv'
    dirty.write_text(clean.read_text(encoding='utf-8') + 'P002,zz imaginary park,1,2027,ESS12,value,1,1,1,\n',
                     encoding='utf-8')
    assert name_leaks(names, [clean]) == (2, [])
    assert name_leaks(names, [clean, dirty]) == (2, ['dirty.csv row 2'])


# ---- rate codes (change price-fee-and-parking-from-portfolio, task 2.1) ----

def _rate_rows(values):
    return _rows('RM.AP', values, basis=rbr.BASIS_APARTMENT_NFA)


def test_rate_code_gives_a_rate_not_an_amount():
    rows = _rate_rows([10000 + 500 * i for i in range(12)])          # 10,000 .. 15,500
    res = rbr.price_line('RM.AP', rows, nfa=12345, vat_rate=0.1)
    assert res.rate and res.usable and not res.cross_check and res.figure == 0 and res.remark == ''
    assert res.median == pytest.approx(12750) and res.n_used == 12
    assert rbr.applied_rate(res, 10) == 14025                         # median x 1.10, rounded to the VND
    assert rbr.applied_rate(res, 8) == 13770
    assert rbr.applied_rate(res, 10, vat_inclusive=False) == 12750
    text = rbr.rate_remark_vi(res, 14025, 10)
    assert '12 dự án' in text and '12,750' in text and '11,375–14,125' in text and '14,025' in text
    assert 'chưa VAT' in text and '2027' in text and 'cộng VAT 10%' in text
    assert all(w not in text.lower() for w in _INTERNAL_WORDING_DENYLIST)
    khoan = rbr.rate_remark_vi(res, 12750, 10, vat_inclusive=False)
    assert 'chưa cộng VAT' in khoan and '12,750' in khoan


def test_rate_code_floor_self_and_outlier():
    rows = _rate_rows([10000 + 500 * i for i in range(10)] + [90000])  # 11 values, one far outlier
    rows[2]['name_key'] = rbr.name_key('Invented Harbour')
    res = rbr.price_line('RM.AP', rows, nfa=12345, vat_rate=0.1, self_name='Invented Harbour')
    assert res.n_used == 9 and not res.usable and rbr.applied_rate(res, 10) is None
    assert 'chỉ 9 ngân sách' in res.reason
    assert {w for _, _, w in res.left_out} == {rbr.OUT_SELF_NAME, rbr.OUT_HIGH}
    res = rbr.price_line('RM.AP', rows, nfa=12345, vat_rate=0.1)      # not the project itself: 10 remain
    assert res.n_used == 10 and res.usable


def test_values_file_without_basis_column_loads(tmp_path):
    import csv as _csv
    p = tmp_path / 'old.csv'
    with open(p, 'w', encoding='utf-8-sig', newline='') as fh:
        w = _csv.writer(fh)
        w.writerow([c for c in rbr.VALUE_COLUMNS if c != 'basis'])
        w.writerow(['P001', '', 10000, 2027, 'ESS12', 'value', 1, 1, 1, ''])
    rows = rbr.load_values(str(p))
    assert rows[0]['basis'] == rbr.BASIS_FEE_NFA
    assert 'RM.AP' in rbr.ALL_CODES and rbr.CODE_NAMES['RM.AP']
