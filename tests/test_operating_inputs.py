"""Unit tests for operating_inputs.py and the stable-operation path of fill_curve.py (change
use-operating-project-actuals: P3 switch, P1 entered rates, P2 recorded parking, P4 collect-on-behalf).

Covered: reading and validating each optional field from a small invented 'Project Info' sheet; the
stop rules (unrecognised switch value, rate without VAT basis, text or negative amounts, parking or
collect-on-behalf without the switch, an unmapped product); the printout; fill_curve with `stable`;
a freshly built intake form (temp folder) carrying every new label and reading back as blank.
Not covered: how the generators write the figures (verification section 9 does that end to end).

Invented data only. The form build redirects OUT_DIR / FINAL_OUT / OUT into pytest's tmp folder.

Rule sources: the change's specs (occupancy-ramp, product-revenue-pricing, parking-revenue-actuals,
pass-through-collections, input-workbook-reading) and design.md D2-D6 and "Answers recorded".
"""
import openpyxl
import pytest

import fill_curve as fc
import operating_inputs as oi
from input_labels import SheetLabels

PRODUCTS = ['Apartment', 'Officetel', 'Office', 'Shopping Mall', 'Retail', 'Shop Apartment',
            'Shophouse', 'Villas', 'Nursery / Nhà trẻ']


def sheet(stable=None, rates=None, rate_cols=True, parking=None, cob=None, cob_block=True,
          with_stable_label=True):
    """An invented 'Project Info' with the Product Mix block and, optionally, the new fields."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Project Info'
    ws['A1'] = 'Project Name'
    ws['B1'] = 'ZZ Invented Tower'
    ws['A3'] = 'PRODUCT MIX'
    for c, h in enumerate(['Product', 'GFA (m²)', 'NFA (m²)', 'Units'], start=1):
        ws.cell(row=4, column=c, value=h)
    if rate_cols:
        ws.cell(row=4, column=5, value=oi.RATE_HEADER)
        ws.cell(row=4, column=6, value=oi.VAT_HEADER)
    for i, p in enumerate(PRODUCTS, start=5):
        ws.cell(row=i, column=1, value=p)
        ws.cell(row=i, column=3, value=1000 if p in ('Apartment', 'Officetel', 'Shophouse') else 0)
        for col, v in zip((5, 6), (rates or {}).get(p, (None, None))):
            ws.cell(row=i, column=col, value=v)
    r = 20
    if with_stable_label:
        ws.cell(row=r, column=1, value=oi.STABLE_LABEL)
        ws.cell(row=r, column=2, value=stable)
    if parking is not None:
        ws.cell(row=r + 1, column=1, value=oi.PARKING_CAR_LABEL)
        ws.cell(row=r + 1, column=2, value=parking.get('car'))
        ws.cell(row=r + 2, column=1, value=oi.PARKING_MOTO_LABEL)
        ws.cell(row=r + 2, column=2, value=parking.get('moto'))
    if cob_block:
        ws.cell(row=30, column=1, value=oi.COB_SECTION)
        for c, h in enumerate((oi.COB_HEADER, oi.COB_WATER_HEADER, oi.COB_ELEC_HEADER), start=1):
            ws.cell(row=31, column=c, value=h)
        for i, p in enumerate(PRODUCTS, start=32):
            ws.cell(row=i, column=1, value=oi.COB_ROW_PREFIX + p)
            water, elec = (cob or {}).get(p, (None, None))
            ws.cell(row=i, column=2, value=water)
            ws.cell(row=i, column=3, value=elec)
    products = {p: dict(nfa=ws.cell(row=i, column=3).value or 0) for i, p in enumerate(PRODUCTS, start=5)}
    return ws, SheetLabels(ws), products


def read(**kw):
    ws, L, products = sheet(**kw)
    return oi.read_operating_inputs(ws, L, products)


# ---------------------------------------------------------------- P3 switch

@pytest.mark.parametrize('value, expected, status', [
    ('Yes', True, 'filled'), ('yes', True, 'filled'), ('No', False, 'filled'),
    (None, False, 'blank'), ('  ', False, 'blank'),
])
def test_stable_switch_values(value, expected, status):
    ops = read(stable=value)
    assert ops['stable'] is expected
    assert ops['status']['stable'] == status


def test_stable_switch_absent_reads_as_not_on_the_form():
    ops = read(with_stable_label=False, rate_cols=False, cob_block=False)
    assert ops['stable'] is False
    assert ops['status'] == dict(stable='not on the form', rates='not on the form', car='not on the form',
                                 moto='not on the form', cob='not on the form')


def test_unrecognised_switch_value_stops_and_names_the_field():
    with pytest.raises(oi.OperatingInputError, match=r"Stable Operation\?.*'Maybe'"):
        read(stable='Maybe')


@pytest.mark.parametrize('fn', [fc.year1_fills, fc.year1_electricity_fills])
def test_curve_without_stable_is_unchanged(fn):
    assert fn(False) == fn()
    assert fn(stable=False) != [1.0] * 12


def test_parking_and_monthly_path_without_stable_are_unchanged():
    assert fc.parking_fills(100, 500, False) == fc.parking_fills(100, 500)
    assert fc.monthly_fill_path(False) == fc.monthly_fill_path()


def test_stable_curve_is_full_every_month():
    assert fc.year1_fills(True) == [1.0] * 12
    assert fc.year1_electricity_fills(True) == [1.0] * 12
    assert fc.parking_fills(100, 500, True) == [1.0] * 12
    path = fc.monthly_fill_path(True)
    assert len(path) == 48 and all(f == 1.0 for _m, _l, f in path)


# ---------------------------------------------------------------- P1 entered rates

def test_entered_rate_is_read_by_header_with_its_vat_basis():
    ops = read(rates={'Apartment': (15000, 'excl. VAT'), 'Officetel': (0, None)})
    assert ops['rates'] == {'Apartment': dict(rate=15000.0, vat='excl. VAT')}
    assert ops['status']['rates'] == 'filled'


def test_moving_the_rate_columns_does_not_change_what_is_read():
    ws, L, products = sheet(rates={'Apartment': (15000, 'incl. VAT')})
    ws.insert_cols(5)          # rate and VAT now sit in F and G
    assert oi.read_entered_rates(ws, L, products)[0] == {'Apartment': dict(rate=15000.0, vat='incl. VAT')}


def test_form_without_the_rate_columns_reads_every_rate_as_blank():
    ops = read(rate_cols=False)
    assert ops['rates'] == {} and ops['status']['rates'] == 'not on the form'


def test_rate_without_vat_basis_stops_and_names_the_product():
    with pytest.raises(oi.OperatingInputError, match='Officetel'):
        read(rates={'Officetel': (20000, None)})


@pytest.mark.parametrize('value', ['15,000', -5])
def test_text_or_negative_rate_stops_and_names_product_and_value(value):
    with pytest.raises(oi.OperatingInputError, match=r'Apartment.*' + repr(value).replace('-', r'\-')):
        read(rates={'Apartment': (value, 'incl. VAT')})


def test_unknown_vat_basis_stops():
    with pytest.raises(oi.OperatingInputError, match='Rate VAT Basis'):
        read(rates={'Apartment': (15000, 'gross')})


def test_rate_on_a_product_without_area_is_named_in_the_printout():
    ops = read(rates={'Villas': (30000, 'incl. VAT')})
    assert any('Villas' in n and 'no chargeable area' in n for n in ops['rate_notes'])
    assert any('Villas' in line for line in oi.report_lines(ops))


def test_vat_mismatch_sentence_only_when_bases_differ():
    assert oi.vat_mismatch_vi(oi.DELIVERABLE_VAT_BASIS) == ''
    assert oi.vat_mismatch_vi(oi.VAT_EXCL) == ('Lưu ý: đơn giá nhập chưa gồm VAT, số liệu ngân sách này '
                                               'trình bày đã gồm VAT; chưa quy đổi.')


# ---------------------------------------------------------------- P2 recorded parking

def test_parking_blank_entered_and_zero():
    ops = read(stable='Yes', parking={'car': 45_000_000, 'moto': 0})
    assert ops['parking'] == {'car': 45_000_000.0, 'moto': 0.0}
    lines = oi.report_lines(ops)
    assert any('Motorbike' in line and 'ZERO' in line for line in lines)
    assert read(stable='Yes', parking={})['parking'] == {'car': None, 'moto': None}


def test_parking_without_the_switch_stops_and_names_both_fields():
    with pytest.raises(oi.OperatingInputError) as exc:
        read(stable='No', parking={'car': 45_000_000})
    assert oi.PARKING_CAR_LABEL in str(exc.value) and oi.STABLE_LABEL in str(exc.value)


def test_parking_text_stops():
    with pytest.raises(oi.OperatingInputError, match='Car Parking'):
        read(stable='Yes', parking={'car': 'about 45m'})


# ---------------------------------------------------------------- P4 collect-on-behalf

def test_cob_amounts_are_read_and_zeros_listed():
    ops = read(stable='Yes', cob={'Apartment': (120_000_000, None), 'Shophouse': (0, 8_000_000)})
    assert ops['cob'] == {'Apartment': {'water': 120_000_000.0, 'electricity': None},
                          'Shophouse': {'water': 0.0, 'electricity': 8_000_000.0}}
    assert any('Shophouse water' in line and 'entered at 0' in line for line in oi.report_lines(ops))


def test_cob_for_an_unmapped_product_stops_and_names_product_and_utility():
    with pytest.raises(oi.OperatingInputError, match=r'Villas \(water\)'):
        read(stable='Yes', cob={'Villas': (5_000_000, None)})


def test_cob_zero_for_an_unmapped_product_does_not_stop():
    assert read(stable='Yes', cob={'Villas': (0, None)})['cob'] == {'Villas': {'water': 0.0, 'electricity': None}}


def test_cob_without_the_switch_stops():
    with pytest.raises(oi.OperatingInputError, match='Thu hộ chi hộ: Apartment'):
        read(stable=None, cob={'Apartment': (1_000_000, None)})


def test_cob_lines_pair_each_amount_through_the_catalogue_pairing():
    ops = read(stable='Yes', cob={'Apartment': (100, 200), 'Shophouse': (0, 50)})
    pairing = {'RO3.A': 'EEW.A', 'RO4.A': 'EEE.A', 'RO4.S': 'EEE.A'}
    lines = oi.cob_lines(ops, pairing)
    assert [(l['revenue_code'], l['expense_code'], l['monthly']) for l in lines] == [
        ('RO3.A', 'EEW.A', 100.0), ('RO4.A', 'EEE.A', 200.0), ('RO4.S', 'EEE.A', 50.0)]


def test_cob_line_without_a_catalogue_pairing_stops():
    ops = read(stable='Yes', cob={'Office': (100, None)})
    with pytest.raises(oi.OperatingInputError, match='RO3.O'):
        oi.cob_lines(ops, {'RO3.A': 'EEW.A'})


def test_parse_departure_record():
    rec = oi.parse_departure('departs_from_guideline=yes | paired_with=EEW.A | approved_on=2026-10-11')
    assert rec == {'departs_from_guideline': 'yes', 'paired_with': 'EEW.A', 'approved_on': '2026-10-11'}


# ---------------------------------------------------------------- the built form

def test_fresh_form_carries_every_new_label_and_reads_back_blank(tmp_path, monkeypatch):
    import build_project_input_form as bpf
    from generate_project_budget import read_input
    monkeypatch.setattr(bpf, 'OUT_DIR', str(tmp_path / 'reports'))
    monkeypatch.setattr(bpf, 'FINAL_OUT', str(tmp_path / 'reports' / 'Project_Budget_Input.xlsx'))
    monkeypatch.setattr(bpf, 'OUT', str(tmp_path / 'built.xlsx'))
    bpf.main()
    wb = openpyxl.load_workbook(tmp_path / 'built.xlsx')
    L = SheetLabels(wb['Project Info'])          # raises AmbiguousLabel if a new label collides
    for label in (oi.STABLE_LABEL, oi.PARKING_CAR_LABEL, oi.PARKING_MOTO_LABEL, oi.COB_SECTION,
                  oi.COB_HEADER, oi.COB_ROW_PREFIX + 'Apartment'):
        assert L.has(label), label
    header_row = L.row_of('Product')
    headers = [wb['Project Info'].cell(row=header_row, column=c).value for c in range(1, 8)]
    assert oi.RATE_HEADER in headers and oi.VAT_HEADER in headers
    # The VAT basis cell of every product row offers exactly the two bases as a list (task 4.1).
    pi = wb['Project Info']
    vat_col = headers.index(oi.VAT_HEADER) + 1
    vat_list = '"' + ','.join(oi.VAT_BASES) + '"'
    lists = [dv for dv in pi.data_validations.dataValidation if dv.type == 'list' and dv.formula1 == vat_list]
    assert len(lists) == 1
    from generate_project_budget import PRODUCT_ROWS
    for product in PRODUCT_ROWS:
        coord = pi.cell(row=L.row_of(product), column=vat_col).coordinate
        assert coord in lists[0].sqref, (product, coord)
    project = read_input(str(tmp_path / 'built.xlsx'))[0]
    assert project['stable_operation'] is False
    assert project['operating']['status'] == dict(stable='blank', rates='blank', car='blank', moto='blank',
                                                  cob='blank')


# ---------------------------------------------------------------- task 6.2: approved departures

_CAT_HEADER = ('code,item_en,item_vi,section,method,method_detail,inputs,occupancy_scaled,remark_components,'
               'legal_citation,guideline_sheet,exensive_logic,precedence_note,summary_recipe,fixed_sentence')
_APPROVED = 'approved_by=Invented approver | approved_on=2026-01-01 | decision_record=invented record'


def _catalogue(tmp_path, ro3a_note):
    """A small invented catalogue: two approved collect-on-behalf revenue lines, one expense line, and
    one ordinary entry."""
    rows = [
        '# invented catalogue for tests',
        _CAT_HEADER,
        f'RO3.A,w,w,revenue,collect-on-behalf-pair,d,,,,,s,n,"{ro3a_note}",,',
        f'RO4.S,e,e,revenue,collect-on-behalf-pair,d,,,,,s,n,"departs_from_guideline=yes | paired_with=EEE.A | {_APPROVED}",,',
        f'EEW.A,x,x,energy,collect-on-behalf-pair,d,,,,,s,n,"departs_from_guideline=yes | paired_with=RO3.* | {_APPROVED}",,',
        'ESS1,y,y,expense,headcount-x-rate,d,,,,,s,n,,,',
    ]
    path = tmp_path / 'catalogue.csv'
    path.write_text(chr(10).join(rows) + chr(10), encoding='utf-8')
    return str(path)


def test_pairing_is_read_from_revenue_entries_only(tmp_path):
    path = _catalogue(tmp_path, f'departs_from_guideline=yes | paired_with=EEW.A | {_APPROVED}')
    assert oi.cob_pairing(path) == {'RO3.A': 'EEW.A', 'RO4.S': 'EEE.A'}


def test_approved_departures_are_expected_and_an_unapproved_one_is_a_mismatch(tmp_path):
    from verification import method_coverage as mc
    ok = _catalogue(tmp_path, f'departs_from_guideline=yes | paired_with=EEW.A | {_APPROVED}')
    verdicts = mc.departure_verdicts(ok)
    assert set(verdicts) == {'RO3.A', 'RO4.S', 'EEW.A'} and all(v['verdict'] == 'matches' for v in verdicts.values())
    broken = _catalogue(tmp_path, 'departs_from_guideline=yes | paired_with=EEW.A')      # approval removed
    verdicts = mc.departure_verdicts(broken)
    assert verdicts['RO3.A']['verdict'] == 'mismatch' and verdicts['RO4.S']['verdict'] == 'matches'
    report = mc.compute_fidelity({'RO3.A': 1_200.0, 'EEW.A': 1_200.0}, catalogue_path=broken)
    assert report['mismatch']['codes'] == ['RO3.A'] and report['matches']['codes'] == ['EEW.A']
