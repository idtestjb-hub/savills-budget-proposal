"""review.py: the VAT conversion, the labels, the assembled rows, the ties and the Review sheet, on dictionaries of
invented figures (no Excel); and one end-to-end run on an invented approved budget, skipped without Excel."""
import os

import openpyxl
import pytest

import review
import review_import as ri
from tests.test_review_import import build_prior_workbook

MONTHS_2026 = [(2026, m) for m in range(1, 13)]
MONTHS_2027 = [(2027, m) for m in range(1, 13)]


def test_vat_factor_rules():
    assert review.vat_factor('EEE.C', MONTHS_2026, False, True) == pytest.approx(1.08)
    assert review.vat_factor('EEE.C', MONTHS_2027, False, True) == pytest.approx(1.10)
    assert review.vat_factor('EEE.C', MONTHS_2026, True, False) == pytest.approx(1 / 1.08)
    assert review.vat_factor('EEE.C', MONTHS_2026, True, True) == 1.0
    assert review.vat_factor('EMH2', MONTHS_2026, False, True) == 1.0        # salary: no VAT
    assert review.vat_factor('CIT1', MONTHS_2026, False, True) == 1.0
    assert review.vat_factor('RO2a', MONTHS_2026, False, True) == 1.0
    half = [(2026, 12), (2027, 1)]
    assert review.vat_factor('ESS1', half, False, True) == pytest.approx(1.09)
    assert review.vat_rate(2021, 5) == 10.0 and review.vat_rate(2022, 6) == 8.0   # before the table: dated periods


def _ctx():
    return dict(existing=True, rate_codes={'RM.AP'}, parking_codes={'RP1', 'RP2'},
                methods={'RM.AP': ('area-x-rate', 'Phí quản lý thu từ Căn hộ'),
                         'ESS1': ('contract-posts-x-24h-rate', 'Dịch vụ bảo vệ'),
                         'ESS38': ('not-estimated', 'Chia sẻ doanh thu bãi xe'),
                         'ESM4': ('pool-volume-x-dose-x-price', 'Hóa chất hồ bơi'),
                         'EEE.C': ('consumption-x-tariff', 'Điện khu công cộng')})


def test_labels_of_design_d6():
    ctx = _ctx()
    assert review.label_of('EMH2', 'MF', 100.0, 90.0, ctx)[0] == review.LABEL_LAW
    assert review.label_of('EEE.C', 'MF', 100.0, 90.0, ctx)[0] == review.LABEL_TARIFF
    assert review.label_of('RM.AP', 'MF', 100.0, 90.0, ctx)[0] == review.LABEL_PM
    assert review.label_of('RP1', 'MF', 100.0, 90.0, ctx)[0] == review.LABEL_PM
    assert review.label_of('ESS1', 'MF', 100.0, 90.0, ctx)[0] == 'Ước lượng: hợp đồng: vị trí × giá 24h'
    assert review.label_of('ESS38', 'MF', 100.0, 0.0, ctx)[0] == review.LABEL_NO_METHOD
    assert review.label_of('EXX9', 'MF', 100.0, None, ctx)[0] == review.LABEL_NO_METHOD      # not catalogued
    assert review.label_of('ESM4', 'MF', 100.0, 0.0, ctx)[0] == review.LABEL_ZERO
    assert review.label_of('ESM4', 'MF', 0.0, 50.0, ctx)[0] == review.LABEL_TOOL_ONLY
    assert review.label_of('ESA1', 'MF', 100.0, None, dict(ctx, on_form=False))[0] == review.LABEL_NOT_ON_FORM
    assert review.label_of('EMH2', 'MF', 100.0, 90.0, dict(ctx, existing=False))[0].startswith(review.LABEL_ESTIMATE)


def _data():
    prior_lines = [
        dict(fund='MF', section='R', code='RM.AP', item='Management fee of Apartment', approved=2_400_000_000.0, incl_vat=False, flags=[], on_form=True, remark=''),
        dict(fund='MF', section='R', code='RP1', item='Motorbike parking', approved=120_000_000.0, incl_vat=False, flags=[], on_form=True, remark=''),
        dict(fund='MF', section='R', code='RO2a', item='Bank interest', approved=12_000_000.0, incl_vat=False, flags=[ri.FLAG_NOT_ON_FORM], on_form=False, remark=''),
        dict(fund='MF', section='E', code='EMH2', item='Staff cost', approved=1_200_000_000.0, incl_vat=False, flags=[], on_form=True, remark=''),
        dict(fund='MF', section='E', code='EEE.C', item='Electricity', approved=480_000_000.0, incl_vat=False, flags=[], on_form=True, remark='Dự phòng tăng giá'),
        dict(fund='MF', section='E', code='ESS38', item='Sharing revenue', approved=100_000_000.0, incl_vat=False, flags=[], on_form=True, remark=''),
        dict(fund='MF', section='E', code='ESS1', item='Security', approved=900_000_000.0, incl_vat=False, flags=[ri.FLAG_MONTHS], on_form=True, remark=''),
        dict(fund='MF', section='E', code='ESS1', item='Security (second row)', approved=100_000_000.0, incl_vat=False, flags=[], on_form=True, remark=''),
    ]
    anchors = {'MF': {'R': 2_532_000_000.0, 'E': 2_780_000_000.0}}
    tool = {'MF': dict(lines={
        'RM.AP': dict(sec='R', name='Management fee of Apartment', amount=2_400_000_000.0),
        'RP1': dict(sec='R', name='Motorbike parking', amount=130_000_000.0),
        'RP2': dict(sec='R', name='Car parking', amount=50_000_000.0),
        'EMH2': dict(sec='E', name='Staff cost', amount=1_260_000_000.0),
        'EEE.C': dict(sec='E', name='Electricity', amount=500_000_000.0),
        'ESS1': dict(sec='E', name='Security', amount=1_100_000_000.0),
        'ESM4': dict(sec='E', name='Pool chemicals', amount=20_000_000.0),
    }, totals={'R': 2_580_000_000.0, 'E': 2_880_000_000.0}, incl_vat=True)}
    meta = dict(prior_year=2026, budget_year=2027, deliverable_incl=True, file_incl=False, file_name='approved_2026.xlsx',
                sheets={'MF': '2. Budget-Management Fund'}, period=MONTHS_2026, period_text='01/2026–12/2026')
    return prior_lines, anchors, tool, meta


def test_assemble_rows_totals_and_ties():
    prior_lines, anchors, tool, meta = _data()
    data = review.assemble(prior_lines, anchors, tool, meta, _ctx(), template={'MF': {'RM.AP': 14, 'RP1': 26, 'RP2': 27, 'EMH2': 81, 'EEE.C': 242, 'ESS1': 100, 'ESS38': 140, 'ESM4': 160}})
    r = {x['code']: x for x in data['rows_by'][('MF', 'R')]['rows']}
    e = {x['code']: x for x in data['rows_by'][('MF', 'E')]['rows']}
    assert r['RM.AP']['factor'] == pytest.approx(1.08) and r['RM.AP']['converted'] == pytest.approx(2_592_000_000.0)
    assert r['RM.AP']['label'] == review.LABEL_PM and r['RM.AP']['item'] == 'Phí quản lý thu từ Căn hộ'
    assert e['EMH2']['factor'] == 1.0 and e['EMH2']['converted'] == 1_200_000_000.0 and e['EMH2']['label'] == review.LABEL_LAW
    assert e['EEE.C']['converted'] == pytest.approx(518_400_000.0) and e['EEE.C']['label'] == review.LABEL_TARIFF
    assert e['ESS1']['approved'] == 1_000_000_000.0                       # a code repeated on one side is summed
    assert ri.FLAG_MONTHS in e['ESS1']['remark']
    assert e['ESS38']['tool'] == 0.0 and e['ESS38']['label'] == review.LABEL_NO_METHOD   # never copied
    assert e['ESM4']['label'] == review.LABEL_TOOL_ONLY and e['ESM4']['approved'] == 0.0
    assert r['RO2a']['on_form'] is False and r['RO2a']['tool'] is None and r['RO2a']['label'] == review.LABEL_NOT_ON_FORM
    assert [x['code'] for x in data['rows_by'][('MF', 'R')]['rows']] == ['RM.AP', 'RP1', 'RP2', 'RO2a']   # template order, off-form last
    tot_r = data['rows_by'][('MF', 'R')]['total']
    assert tot_r['approved'] == 2_532_000_000.0 and tot_r['tool'] == 2_580_000_000.0
    ties = {(t['kind'], t['section']): t for t in data['ties']}
    assert all(t['ok'] for t in data['ties']), data['ties']
    assert ties[('duyệt = file nguồn', 'E')]['left'] == 2_780_000_000.0
    s = data['summary']['MF']['S']
    assert s['tool'] == pytest.approx(2_580_000_000.0 - 2_880_000_000.0)
    c = data['counts']
    assert c['not_on_form'] == 1 and c['no_method'] == 1 and c['only_tool'] == 2
    assert data['top'][0]['code'] == 'RM.AP' or abs(data['top'][0]['diff']) >= abs(data['top'][1]['diff'])


def test_tie_failure_is_reported_not_hidden():
    prior_lines, anchors, tool, meta = _data()
    tool['MF']['totals']['E'] = 2_880_000_001.5
    data = review.assemble(prior_lines, anchors, tool, meta, _ctx(), template={'MF': {}})
    bad = [t for t in data['ties'] if not t['ok']]
    assert len(bad) == 1 and bad[0]['section'] == 'E' and bad[0]['kind'] == 'công cụ = bản giao'


def test_review_sheet_is_written_last_with_summary_and_rows(tmp_path):
    prior_lines, anchors, tool, meta = _data()
    data = review.assemble(prior_lines, anchors, tool, meta, _ctx(), template={'MF': {}})
    wb = openpyxl.Workbook()
    wb.active.title = 'Summary'
    wb.create_sheet('Service Levels')
    review.build_review_sheet(wb, data, meta)
    assert wb.sheetnames[-1] == review.REVIEW_SHEET
    ws = wb[review.REVIEW_SHEET]
    texts = [str(c.value) for row in ws.iter_rows() for c in row if c.value is not None]
    assert any(t.startswith('Review — ngân sách đã duyệt 2026') for t in texts)
    assert 'Tổng thu' in texts and 'Tổng chi' in texts and 'Thặng dư' in texts
    assert 'Duyệt NS 2026 (quy đổi)' in texts and 'Công cụ NS 2027' in texts
    assert 'RM.AP' in texts and 'ESS38' in texts and review.LABEL_NO_METHOD in texts
    assert any('KHỚP' in t for t in texts)
    p = os.path.join(tmp_path, 'out.xlsx')
    wb.save(p)
    md = review.summary_md(data, meta)
    assert '| Tổng thu |' in md and 'Top 10' in md


def _excel_available():
    try:
        import pythoncom  # noqa: F401
        import win32com.client as w
        pythoncom.CoInitialize()
        xl = w.DispatchEx('Excel.Application')
        xl.Quit()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _excel_available(), reason='Excel is needed for the Review sheet')
def test_end_to_end_on_an_invented_budget(tmp_path):
    from verification.run_workflow import PRODUCTION_FILES, snapshot
    p = os.path.join(tmp_path, 'approved_2026.xlsx')
    build_prior_workbook(p)
    facts = os.path.join(tmp_path, 'facts.json')
    open(facts, 'w', encoding='utf-8').write('{"Tower Count": 2, "Floor Count": 20, "Gate / Entrance Count": 2, '
                                             '"Has Swimming Pool?": "Yes", "Pool Volume": 300, "Car Parking Slots": 150, '
                                             '"City / Province": "Ho Chi Minh City"}')   # the water tariff needs the city
    before = snapshot(PRODUCTION_FILES)
    code, result = review.run(p, facts_path=facts, workdir=os.path.join(tmp_path, 'work'), quiet=True)
    assert snapshot(PRODUCTION_FILES) == before
    assert code == 0, [t for t in result['data']['ties'] if not t['ok']]
    assert len(result['data']['ties']) == 8
    wb = openpyxl.load_workbook(result['analysis'])
    assert wb.sheetnames[-1] == review.REVIEW_SHEET
    assert os.path.exists(os.path.join(tmp_path, 'work', 'review_summary.md'))
    e = {x['code']: x for x in result['data']['rows_by'][('MF', 'E')]['rows']}
    assert e['EMH2']['label'] == review.LABEL_LAW and e['EEE.C']['label'] == review.LABEL_TARIFF
    assert e['EMH2']['tool'] > 0
