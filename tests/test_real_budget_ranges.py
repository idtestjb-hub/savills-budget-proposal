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
    assert f'trung vị {res.median:,.0f} đ/m²/tháng' in t and '30 dự án do Savills quản lý' in t
    assert f'{res.p25:,.0f}–{res.p75:,.0f} đ/m²/tháng' in t and 'chưa VAT, theo giá năm 2027' in t
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
