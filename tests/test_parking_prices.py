"""Unit tests for parking_prices.py on an invented master-list table (change price-fee-and-parking-from-portfolio,
task 3.1). Every text pattern seen in the real fee columns is reproduced with invented names and figures."""
import pytest

import parking_prices as pp
from verification.checks import _INTERNAL_WORDING_DENYLIST

PATTERNS = [
    # text, expected car price (band 300,000–5,000,000), expected status
    ('1500000', 1_500_000, pp.STATUS_PRICE),
    ('1.400.000 vnđ', 1_400_000, pp.STATUS_PRICE),
    ('2,000,000 (Managed by Investor)', 2_000_000, pp.STATUS_PRICE),
    ('1818182', 1_818_182, pp.STATUS_PRICE),
    ('1136363.6363636362', 1_136_363.6363636362, pp.STATUS_PRICE),
    ('- 1,136,363.63 VND/car/month (indoor)\n- 636,363.64 VND/car (outdoor)', 1_136_363.63, pp.STATUS_PRICE),
    ('Xe thứ 1: 1,200,000 VNĐ / Xe thứ 2 trở đi: 1,500,000 VNĐ', 1_200_000, pp.STATUS_PRICE),
    ('- G floor: /\n+ The 1st car: 800,000 vnd', 800_000, pp.STATUS_PRICE),
    ('Hầm: 1.000.000 VND / tháng; vành đai 700.000', 1_000_000, pp.STATUS_PRICE),
    ('1.300.000 ( sân)( 1500000 ( hầm)', 1_300_000, pp.STATUS_PRICE),
    ('Ô tô vành đai: 715,000đ/xe', 715_000, pp.STATUS_PRICE),
    ('', None, pp.STATUS_BLANK),
    ('0', None, pp.STATUS_ZERO),
    ('CĐT đã bán ô đậu xe nên không có phí đậu xe hơi', None, pp.STATUS_NO_PARKING),
    ('Không có', None, pp.STATUS_NO_PARKING),
    ('N/A', None, pp.STATUS_NO_PARKING),
    ('Free of charge now', None, pp.STATUS_NO_PARKING),
    ('Đơn vị khác quản lý', None, pp.STATUS_NO_PARKING),
    ('210000', None, pp.STATUS_OUT_OF_BAND),             # a motorbike-sized number in the car cell
    ('Ô xe Ô tô- SHR: 200,000 VND/ô', None, pp.STATUS_OUT_OF_BAND),
    ('VND', None, pp.STATUS_UNPARSED),
]


@pytest.mark.parametrize('text, price, status', PATTERNS)
def test_parse_car_patterns(text, price, status):
    got_price, got_status = pp.parse(text, pp.VEHICLES['car']['lo'], pp.VEHICLES['car']['hi'])
    assert got_status == status
    assert (got_price == pytest.approx(price)) if price is not None else got_price is None


def test_parse_moto_patterns():
    lo, hi = pp.VEHICLES['moto']['lo'], pp.VEHICLES['moto']['hi']
    assert pp.parse('Xe máy <175cc: 80,000 vnđ/tháng / Xe máy >175cc: 120,000', lo, hi) == (80_000, pp.STATUS_PRICE)
    assert pp.parse('from 1 to 2 motorbikes: 54.545 / 3rd motorbike: 109.091', lo, hi) == (54_545, pp.STATUS_PRICE)
    assert pp.parse('2 xe đầu: 138,889 đ/ tháng / xe thứ 3: 190,000', lo, hi) == (138_889, pp.STATUS_PRICE)
    assert pp.parse('90909.0909090909', lo, hi) == (pytest.approx(90_909.09), pp.STATUS_PRICE)
    assert pp.parse('Xe đạp: 32,400đ/chiếc', lo, hi) == (32_400, pp.STATUS_PRICE)      # inside the band: read
    assert pp.parse('2500000', lo, hi) == (None, pp.STATUS_OUT_OF_BAND)                 # a car price in the moto cell


def _rows(car_prices, moto_prices=None, names=None):
    moto_prices = moto_prices or [''] * len(car_prices)
    names = names or [f'Invented Tower {i}' for i in range(len(car_prices))]
    return [dict(name=n, district='Quan Alpha', city='TP X', car=str(c), moto=str(m))
            for n, c, m in zip(names, car_prices, moto_prices)]


def test_range_median_iqr_floor_and_self():
    prices = [1_000_000 + 50_000 * i for i in range(12)] + [9_000_000 if False else 4_900_000, 'không có', '', '0']
    rows = _rows(prices)
    pr = pp.form_range('car', rows)
    assert pr.n_rows == 16 and pr.n_price == 13
    assert pr.n_used == 12 and pr.usable                                   # 4,900,000 is the IQR outlier
    assert [w for _, _, w in pr.left_out] == [pp.OUT_HIGH]
    assert pr.median == pytest.approx(1_275_000) and pr.price == 1_275_000
    assert {s for _, _, _, s in pr.parsed} == {pp.STATUS_PRICE, pp.STATUS_NO_PARKING, pp.STATUS_BLANK, pp.STATUS_ZERO}
    # the project itself, by name (an M3-style suffix is stripped), is left out
    pr2 = pp.form_range('car', rows, self_name='Invented Tower 3 (M3 REBUILD)')
    assert ('Invented Tower 3', 1_150_000, pp.OUT_SELF) in pr2.left_out and pr2.n_used == 11
    # under the floor: not usable, no price
    pr3 = pp.form_range('car', _rows([1_000_000] * 9))
    assert pr3.n_used == 9 and not pr3.usable and pr3.price is None


def test_resolve_precedence():
    rows = _rows([1_000_000 + 50_000 * i for i in range(12)], [100_000 + 5_000 * i for i in range(12)])
    p = dict(name='ZZ New', operating={})
    out = pp.resolve(p, rows)
    assert (out['car']['source'], out['car']['price']) == (pp.SOURCE_RANGE, 1_275_000)
    assert (out['moto']['source'], out['moto']['price']) == (pp.SOURCE_RANGE, 127_500)
    # entered wins over the range for its vehicle only
    p['operating'] = dict(parking={'car': None, 'moto': None}, parking_price={'car': 1_500_000, 'moto': None})
    out = pp.resolve(p, rows)
    assert (out['car']['source'], out['car']['price']) == (pp.SOURCE_ENTERED, 1_500_000)
    assert out['moto']['source'] == pp.SOURCE_RANGE
    # recorded revenue wins over both
    p['operating'] = dict(parking={'car': 50_000_000, 'moto': None}, parking_price={'car': 1_500_000, 'moto': None})
    out = pp.resolve(p, rows)
    assert (out['car']['source'], out['car']['price'], out['car']['recorded']) == (pp.SOURCE_RECORDED, None, 50_000_000)
    # fewer than 10 prices: the former constants
    out = pp.resolve(dict(name='ZZ New'), _rows([1_000_000] * 5))
    assert (out['car']['source'], out['car']['price']) == (pp.SOURCE_DEFAULT, 1_100_000)
    assert (out['moto']['source'], out['moto']['price']) == (pp.SOURCE_DEFAULT, 110_000)
    # no master list at all
    out = pp.resolve(dict(name='ZZ New'), [])
    assert out['moto']['source'] == pp.SOURCE_DEFAULT and out['moto']['range'].n_rows == 0


def test_wording_names_no_project_and_no_internal_words():
    rows = _rows([1_000_000 + 50_000 * i for i in range(12)], [100_000 + 5_000 * i for i in range(12)])
    out = pp.resolve(dict(name='ZZ New'), rows)
    clause = pp.source_clause_vi('car', out['car'])
    assert '12 dự án' in clause and '1,137,500–1,412,500' in clause and 'đã gồm VAT' in clause
    assert 'Invented' not in clause and all(w not in clause.lower() for w in _INTERNAL_WORDING_DENYLIST)
    assert pp.source_clause_vi('moto', dict(source=pp.SOURCE_ENTERED, range=None)) == 'đơn giá giữ xe do PM nhập, đã gồm VAT'
    assert pp.source_clause_vi('moto', dict(source=pp.SOURCE_DEFAULT, range=None)) == pp.DEFAULT_CLAUSE_VI
    assert 'Median' in pp.source_label_en(out['car']) and 'Former constant' in pp.source_label_en(
        dict(source=pp.SOURCE_DEFAULT, range=pp.form_range('car', [])))


def test_verification_parking_price_agreement(tmp_path):
    """Task 6.1: the deliverable's helper B5 row 17 and the analysis's Additional Revenue table must quote the same
    price per vehicle; both blank also agrees (recorded revenue or no bays)."""
    import openpyxl
    from verification.checks import check_parking_price_agreement

    def pair(d_car, d_moto, a_car, a_moto):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'B5. Đơn giá gửi xe - Parking pr'
        ws.cell(row=17, column=3, value=d_car)
        ws.cell(row=17, column=5, value=d_moto)
        dp = tmp_path / 'd.xlsx'
        wb.save(dp)
        wa = openpyxl.Workbook()
        ws = wa.active
        ws.title = 'Additional Revenue'
        ws.cell(row=6, column=1, value='Car'); ws.cell(row=6, column=2, value=a_car)
        ws.cell(row=7, column=1, value='Motorbike'); ws.cell(row=7, column=2, value=a_moto)
        ap = tmp_path / 'a.xlsx'
        wa.save(ap)
        return dict(deliverable=str(dp), analysis=str(ap))

    ok, rows, diffs, _ = check_parking_price_agreement(pair(1_200_000, 145_000, 1_200_000, 145_000))
    assert ok and len(rows) == 2
    ok, _, diffs, _ = check_parking_price_agreement(pair('Chưa áp dụng.', 145_000, None, 145_000))
    assert ok
    ok, _, diffs, _ = check_parking_price_agreement(pair(1_200_000, 145_000, 1_100_000, 145_000))
    assert not ok and diffs[0][0].startswith('RP2')
    ok, _, diffs, _ = check_parking_price_agreement(pair('Chưa áp dụng.', 145_000, 1_200_000, 145_000))
    assert not ok
