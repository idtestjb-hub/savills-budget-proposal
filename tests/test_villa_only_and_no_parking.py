"""Projects without apartments or without parking bays (change support-villa-only-and-no-parking, rules decided
2026-10-19).

Rule source: openspec/changes/support-villa-only-and-no-parking/specs/villa-only-and-no-parking-projects/spec.md.
Invented data only (the villa fixture is built from the synthetic sample into a temporary folder).
"""
import os

import openpyxl
import pytest

import generate_project_budget as g

FIXTURES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'verification', 'fixtures')
needs_template = pytest.mark.skipif(not os.path.exists(g.TEMPLATE_PATH), reason='standard form not available')


def project(apartment=0, villas=0, car=0, moto=0, apartment_units=0, villa_units=0):
    return {'products': {'Apartment': {'gfa': 0, 'nfa': apartment, 'units': apartment_units},
                         'Villas': {'gfa': 0, 'nfa': villas, 'units': villa_units},
                         'Shophouse': {'gfa': 0, 'nfa': 0, 'units': 0}},
            'apartment_units': apartment_units, 'car_slots': car, 'moto_slots': moto}


# ---------------------------------------------------------------- the apartment column's weight
def test_apartments_keep_their_own_weight():
    assert g._apartment_column_weight(project(apartment=52000, villas=3000)) == (52000, False)


def test_villas_take_the_column_when_there_are_no_apartments():
    assert g._apartment_column_weight(project(villas=40000)) == (40000, True)


def test_neither_apartments_nor_villas():
    assert g._apartment_column_weight(project()) == (0, False)


# ---------------------------------------------------------------- BM11 / BN11
def test_no_parking_weight_gets_a_nominal_one():
    ws = openpyxl.Workbook().active
    g._parking_allocation_weights(ws, {}, 0, 0)
    assert (ws['BM11'].value, ws['BN11'].value) == (1, 0)
    assert 'Nominal' in ws['BM11'].comment.text


def test_parking_weight_is_unchanged_with_bays():
    ws = openpyxl.Workbook().active
    g._parking_allocation_weights(ws, {}, 1_000_000, 5_000_000)
    assert (ws['BM11'].value, ws['BN11'].value) == (6_000_000, 0)


def test_weights_typed_as_zero_are_still_refused():
    ws = openpyxl.Workbook().active
    ws['BM11'], ws['BN11'] = 0, 0
    with pytest.raises(ValueError, match='sum to zero'):
        g._parking_allocation_weights(ws, {}, 0, 0)


# ---------------------------------------------------------------- the standard form's cells
@needs_template
def test_villa_only_fills_the_apartment_weight_and_parking_sheet():
    wb = openpyxl.load_workbook(g.TEMPLATE_PATH)
    g._fill_product_mix_fallbacks(wb, project(villas=40000, villa_units=200))
    fund = wb['2. Budget-Management Fund']
    assert fund['BG10'].value == 40000 and 'biệt thự' in fund['BG10'].comment.text
    from common_utils_v2 import find_sheet_loose
    pk = wb[find_sheet_loose(wb, 'lấp đầy bãi xe')]
    assert pk['D6'].value == 200
    row11 = [pk.cell(row=11, column=c).value for c in range(6, pk.max_column + 1)]
    assert not any(isinstance(v, str) and '/$D$11' in v for v in row11)
    assert 'xe máy' in pk['E11'].value


@needs_template
def test_a_project_with_apartments_and_bays_is_untouched():
    wb = openpyxl.load_workbook(g.TEMPLATE_PATH)
    before = {(ws.title, c.coordinate): c.value for ws in wb for row in ws.iter_rows() for c in row}
    g._fill_product_mix_fallbacks(wb, project(apartment=52000, apartment_units=480, car=380, moto=1600))
    after = {(ws.title, c.coordinate): c.value for ws in wb for row in ws.iter_rows() for c in row}
    assert before == after


@needs_template
def test_villas_go_in_the_apartment_column_of_a2_even_with_car_bays(monkeypatch):
    wb = openpyxl.load_workbook(g.TEMPLATE_PATH)
    monkeypatch.setitem(g._HELPER_FIGURES, 'contract', {'Security': dict(
        posts=[], excluded=[], roles=1, blend=1, post_rate=10_000_000, qty=0)})
    g._fill_service_post_sheet(wb, project(villas=40000, car=50), 'Security')
    ws = wb['A2. Bảo vệ - Security']
    assert (ws['M7'].value, ws['P7'].value) == (40000, 50)
    assert 'biệt thự' in ws['M7'].comment.text


# ---------------------------------------------------------------- the run gate
def test_villa_form_is_read(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location('bvf', os.path.join(FIXTURES, 'build_villa_fixture.py'))
    bvf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bvf)
    out = bvf.build(str(tmp_path / 'villa.xlsx'))
    p = g.read_input(out)[0]
    assert p['apartment_nfa'] == 0 and p['products']['Villas']['nfa'] == 38000


def test_form_without_any_area_is_refused(tmp_path):
    wb = openpyxl.load_workbook(os.path.join(FIXTURES, 'Sample_Project_Input.xlsx'))
    pi = wb['Project Info']
    for r in range(1, pi.max_row + 1):
        if pi.cell(row=r, column=1).value in g.PRODUCT_ROWS:
            pi.cell(row=r, column=3).value = 0
    path = str(tmp_path / 'empty.xlsx')
    wb.save(path)
    with pytest.raises(ValueError, match='Product Mix'):
        g.read_input(path)
