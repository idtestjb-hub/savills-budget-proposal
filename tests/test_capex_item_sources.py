"""Unit tests for the capex item pool of estimate_capex_qty.py (change widen-utility-and-capex-sources).

Covered: the nearest admitted project by capex NFA supplies the list (the spec's 18,000 / 36,500 / 61,000 m² example),
quantities scale by the NFA ratio with the source unit price kept, a store row (Comparable = 0) is not a comparable,
Study 1 ratios are medians over the pool with n, and a second file of the same building counts once.
Not covered: the office-side extraction (rescan_capex_store_projects.py), which reads the store.

Invented data only: an invented registry and item table in tmp_path; no real file is read.
Rule sources: the change's spec capex-item-sources and outer docs/05-decisions.md (2026-11-06).
"""
import csv

import pytest

import estimate_capex_qty as ecq
import reference_projects as rp


def reg_row(key, nfa, district, comparable='0'):
    return dict(RefKey=key, DisplayName=f'Dự án thử {key}', Aliases='', TotalNFA_m2='', CapexNFA_m2=str(nfa),
                ApartmentUnits='', TotalUnits='', MgmtRate_VND_m2_month='', MgmtRateVAT='', District=district,
                City='Hồ Chí Minh', Comparable=comparable, ExcludedFromRanking='store row', Roles='capex_items',
                Source='test', LocationSource='', VerifiedOn='2026-11-06')


REGISTRY = [reg_row('R01', 18000, 'Quận 1', comparable='1'), reg_row('R06', 36500, 'Quận 2', comparable='1'),
            reg_row('R07', 36500, 'Quận 2', comparable='1'),          # second file of the same building
            reg_row('R09', 61000, 'Quận 9')]
ITEMS = [  # (key, category, item, qty, unit price)
    ('R01', 'MO Equipment', 'Bàn', 18, 1000), ('R01', 'Public Area', 'Ghế đá', 9, 500),
    ('R01', 'Amenity Area', 'Phao bơi', 2, 300),           # the only amenity list in the pool
    ('R06', 'MO Equipment', 'Bàn', 73, 1000), ('R06', 'Public Area', 'Ghế đá', 36.5, 500),
    ('R07', 'MO Equipment', 'Bàn', 365, 1000),
    ('R09', 'MO Equipment', 'Bàn', 183, 1200), ('R09', 'Public Area', 'Ghế đá', 610, 500),
]


@pytest.fixture
def pool(tmp_path, monkeypatch):
    reg = tmp_path / 'reg.csv'
    with open(reg, 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.DictWriter(fh, fieldnames=rp.COLUMNS)
        w.writeheader()
        w.writerows(REGISTRY)
    items = tmp_path / 'items.csv'
    with open(items, 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.writer(fh)
        w.writerow(['Project', 'Category', 'Item', 'Unit', 'Qty', 'UnitPrice', 'Total', 'SourceSheet', 'SourceRow',
                    'RefKey'])
        for key, cat, item, qty, price in ITEMS:
            w.writerow([key, cat, item, 'cái', qty, price, qty * price, 'S', 1, key])
    monkeypatch.setattr(rp, 'REGISTRY_CSV', str(reg))
    monkeypatch.setattr(ecq, 'RESCANNED_CSV', str(items))
    rp.clear_cache()
    ecq._STUDY1_CACHE.clear()
    return ecq


def test_the_nearest_project_by_capex_nfa_supplies_the_list(pool):
    items, info = pool.estimate_capex_items(40000)
    assert info['source_key'] in ('R06', 'R07') and info['source_nfa'] == 36500
    assert info['scale_factor'] == pytest.approx(40000 / 36500, rel=1e-4)


def test_quantities_scale_and_unit_prices_are_kept(pool):
    items, info = pool.estimate_capex_items(61000 * 2)
    assert info['source_key'] == 'R09'
    desk = next(i for i in items if i['item'] == 'Bàn')
    assert desk['qty'] == 366 and desk['unit_price'] == 1200


def test_a_store_row_is_not_a_comparable(pool):
    keys = [c['key'] for c in rp.hand_verified_comparables()]
    assert 'R09' not in keys and 'R01' in keys


def test_study1_is_the_median_per_1000_m2_with_n_and_one_building_counts_once(pool):
    s1 = pool.study1_ratios()
    # MO per 1,000 m²: R01 1.0, R06 2.0 (R07 skipped: same NFA and district), R09 3.0 -> median 2.0, n 3
    assert s1['MO Equipment']['n'] == 3 and s1['MO Equipment']['median'] == pytest.approx(2.0)
    assert 'R07' not in s1['MO Equipment']['keys']
    assert s1['Public Area']['range'] == (pytest.approx(0.5), pytest.approx(10.0))
    est = pool.estimate_capex_qty(10000)['MO Equipment']
    assert est['study1_qty'] == pytest.approx(20.0) and est['study1_n'] == 3


def test_a_category_the_nearest_lacks_comes_from_the_nearest_that_lists_it(pool):
    items, info = pool.estimate_capex_items(40000)
    assert info['borrowed']['Amenity Area']['source_key'] == 'R01'
    floats = [i for i in items if i['category'] == 'Amenity Area']
    assert len(floats) == 1 and floats[0]['qty'] == round(2 * 40000 / 18000) and floats[0]['unit_price'] == 300
    assert 'MO Equipment' not in info['borrowed']
