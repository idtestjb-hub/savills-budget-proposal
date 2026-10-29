"""Dated rates wired into the readers and the two generators (change apply-head-of-pm-decisions-2026-10, group 2).

Uses the synthetic sample input and the real public tariff table (public prices, not client data).
"""
import os

import openpyxl
import pytest

import budget_period as bp
import estimate_opex as eo
import generate_project_budget as gpb
import generate_project_output as gpo
import utility_tariffs as ut

FIXTURE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'verification', 'fixtures', 'Sample_Project_Input.xlsx')


def _project(tmp_path, group=None, start=None, city=None):
    wb = openpyxl.load_workbook(FIXTURE)
    pi = wb['Project Info']
    r = pi.max_row + 2
    for label, value in ((ut.WATER_GROUP_LABEL, group), (bp.LABEL, start)):
        pi.cell(row=r, column=1, value=label)
        pi.cell(row=r, column=2, value=value)
        r += 1
    path = tmp_path / 'input.xlsx'
    wb.save(path)
    project = gpb.read_input(str(path))[0]
    if city is not None:
        project['city'] = city
    return project


def test_a_form_without_the_water_group_reads_blank(tmp_path):
    wb = openpyxl.load_workbook(FIXTURE)
    path = tmp_path / 'input.xlsx'
    wb.save(path)
    assert gpb.read_input(str(path))[0]['water_group'] is None


def test_the_water_group_is_read_and_changes_the_price(tmp_path):
    biz = eo.estimate_opex(50_000, **gpb._opex_kwargs(_project(tmp_path)))['Water']
    adm = eo.estimate_opex(50_000, **gpb._opex_kwargs(_project(tmp_path, group='Hành chính sự nghiệp')))['Water']
    assert biz['dated']['group'] == ut.CAT_W_BUSINESS and adm['dated']['group'] == ut.CAT_W_ADMIN
    assert adm['monthly_vnd'] / biz['monthly_vnd'] == pytest.approx(17940 / 29394, rel=1e-4)


def test_an_invalid_water_group_stops_the_run(tmp_path):
    with pytest.raises(ut.TariffError, match='Water Customer Group'):
        eo.estimate_opex(50_000, **gpb._opex_kwargs(_project(tmp_path, group='Sinh hoạt')))


@pytest.mark.parametrize('start, expected', [((2027, 1), [10.0] * 12), ((2026, 10), [8.0] * 3 + [10.0] * 9)])
def test_general_vat_months_follow_the_budget_period(tmp_path, start, expected):
    project = _project(tmp_path, start=f'{start[1]:02d}/{start[0]}')
    assert gpb._general_vat_months(project) == expected


def test_vat_factors_are_one_when_the_model_excludes_vat(tmp_path, monkeypatch):
    project = _project(tmp_path)
    monkeypatch.setattr(gpb, '_ACTIVE_VAT_SENTENCE', '')
    assert gpb._vat_factors(project) == [1.0] * 12
    monkeypatch.setattr(gpb, '_ACTIVE_VAT_SENTENCE', 'Chi phí hạng mục này đã bao gồm VAT.')
    assert gpb._vat_factors(project) == pytest.approx([1.10] * 12)


def test_rate_phrase_names_each_step():
    months = [(2026, 10), (2026, 11), (2026, 12), (2027, 1)]
    assert gpb._rate_phrase(months, [8.0, 8.0, 8.0, 10.0]) == '8% đến hết tháng 12/2026 và 10% từ tháng 01/2027'
    assert gpb._rate_phrase(months, [10.0] * 4) == '10%'


def test_water_remark_names_the_group_and_the_default(tmp_path):
    project = _project(tmp_path)
    text = gpb._energy_narrative_vi('Water', project, '2027')
    assert 'kinh doanh dịch vụ' in text and 'mặc định' in text and 'SAWACO' in text
    assert 'built-up' not in text and 'cùng quy mô' not in text
    chosen = gpb._energy_narrative_vi('Water', _project(tmp_path, group='Hành chính sự nghiệp'), '2027')
    assert 'hành chính sự nghiệp' in chosen and 'mặc định' not in chosen and 'theo nhóm PM đã chọn' in chosen


def test_water_remark_flags_a_project_outside_hcmc(tmp_path):
    assert 'ngoài TP.HCM' in gpb._energy_narrative_vi('Water', _project(tmp_path, city='Hà Nội'), '2027')


def test_diesel_remark_cites_the_listing_date_and_the_re_taxed_price(tmp_path):
    text = gpb._energy_narrative_vi('Diesel (Generator Fuel)', _project(tmp_path), '2027')
    assert '01/10/2026' in text and '29,710' in text and '32,681' in text and 'DO 0,05S-II' in text
    assert 'chưa gồm VAT' in text and 'VAT 0%' not in text      # the 01/10/2026 price carries no VAT


def test_electricity_remark_states_the_price_before_vat_and_the_month_vat(tmp_path, monkeypatch):
    monkeypatch.setattr(gpb, '_ACTIVE_VAT_SENTENCE', 'Chi phí hạng mục này đã bao gồm VAT.')
    text = gpb._energy_narrative_vi('Electricity', _project(tmp_path), '2027')
    assert 'trước VAT, cộng VAT 10% theo từng tháng' in text and 'chưa gồm VAT' not in text


def test_household_waste_price_is_the_qd_65_2026_price():
    assert (gpb.WASTE_COLLECTION_PRICE, gpb.WASTE_TRANSPORT_PRICE, gpb.WASTE_TREATMENT_PRICE) == (486, 180, 421)
    assert gpb.WASTE_UNIT_PRICE == 1087
    assert gpb.WASTE_UNIT_PRICE / 1086.49 == pytest.approx(1.000469, rel=1e-5)


def test_analysis_electricity_is_the_monthly_amount_before_vat_times_12_times_1_10(tmp_path, monkeypatch):
    project = _project(tmp_path)
    excl = eo.estimate_opex(project['total_nfa'], **gpb._opex_kwargs(project))['Electricity']['monthly_vnd']
    monkeypatch.setattr(gpo, 'template_vat_inclusive', lambda: True)
    wb = openpyxl.Workbook()
    gpo.build_opex_sheet(wb, project)
    ws = wb['OPEX']
    row = next(r for r in range(1, 30) if ws.cell(r, 1).value == 'Electricity')
    assert ws.cell(row, 2).value == round(excl * 1.10)
    assert ws.cell(row, 2).value * 12 == pytest.approx(excl * 12 * 1.10, abs=12)


def test_analysis_electricity_is_unchanged_when_the_model_excludes_vat(tmp_path, monkeypatch):
    project = _project(tmp_path)
    excl = eo.estimate_opex(project['total_nfa'], **gpb._opex_kwargs(project))['Electricity']['monthly_vnd']
    monkeypatch.setattr(gpo, 'template_vat_inclusive', lambda: False)
    wb = openpyxl.Workbook()
    gpo.build_opex_sheet(wb, project)
    ws = wb['OPEX']
    row = next(r for r in range(1, 30) if ws.cell(r, 1).value == 'Electricity')
    assert ws.cell(row, 2).value == excl


# ---------------------------------------------------- group 3: ESI2, USD premium x rate x insurance VAT
def test_esi2_defaults_when_both_inputs_are_blank():
    r = gpb._resolve_esi2(None, '')
    assert (r['premium_usd'], r['rate'], r['premium_is_default'], r['rate_is_default']) == (1000, 26190, True, True)
    assert 1000 * 26190 * 1.10 == pytest.approx(28_809_000)


def test_esi2_takes_the_pms_quote_and_rate():
    r = gpb._resolve_esi2(1500, 26300)
    assert (r['premium_usd'], r['rate'], r['premium_is_default'], r['rate_is_default']) == (1500, 26300, False, False)
    assert r['premium_usd'] * r['rate'] * 1.10 == pytest.approx(1500 * 26300 * 1.10)


def test_esi2_zero_premium_is_an_entered_zero_not_a_blank():
    r = gpb._resolve_esi2(0, None)
    assert r['premium_usd'] == 0 and not r['premium_is_default']


@pytest.mark.parametrize('premium, rate, label', [
    ('abc', None, gpb.ESI2_PREMIUM_LABEL), (-5, None, gpb.ESI2_PREMIUM_LABEL),
    (None, 0, gpb.USD_RATE_LABEL), (None, 'x', gpb.USD_RATE_LABEL), (None, -1, gpb.USD_RATE_LABEL),
])
def test_esi2_invalid_inputs_stop_and_name_the_field(premium, rate, label):
    with pytest.raises(ValueError, match=label.replace('(', r'\(').replace(')', r'\)')):
        gpb._resolve_esi2(premium, rate)


def test_a_form_without_the_esi2_fields_reads_the_defaults(tmp_path):
    wb = openpyxl.load_workbook(FIXTURE)
    path = tmp_path / 'input.xlsx'
    wb.save(path)
    project = gpb.read_input(str(path))[0]
    assert project['esi2']['premium_is_default'] and project['esi2']['rate'] == 26190


def test_the_esi2_fields_are_read_by_label(tmp_path):
    wb = openpyxl.load_workbook(FIXTURE)
    pi = wb['Project Info']
    r = pi.max_row + 2
    for label, value in ((gpb.ESI2_PREMIUM_LABEL, 1500), (gpb.USD_RATE_LABEL, 26300)):
        pi.cell(row=r, column=1, value=label)
        pi.cell(row=r, column=2, value=value)
        r += 1
    path = tmp_path / 'input.xlsx'
    wb.save(path)
    assert gpb.read_input(str(path))[0]['esi2']['premium_usd'] == 1500


def test_insurance_vat_is_10_percent_in_every_month_including_2026(tmp_path):
    project = _project(tmp_path, start='10/2026')
    assert gpb._general_vat_months(project, ut.VAT_INSURANCE) == [10.0] * 12
    assert gpb._general_vat_months(project)[:3] == [8.0, 8.0, 8.0]
