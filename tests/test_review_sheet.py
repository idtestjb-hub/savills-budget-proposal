"""review.py: the VAT conversion, the labels, the assembled rows, the ties and the Review sheet, on dictionaries of
invented figures (no Excel); and one end-to-end run on an invented approved budget, skipped without Excel."""
import os

import openpyxl
from openpyxl.utils import get_column_letter
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


def test_group_chain_follows_the_form_subtotal_ranges():
    rows = ri.template_codes()
    assert ri.group_chain('MF', 'EMH2', rows['MF']['EMH2']) == ['EM', 'EMH']
    assert ri.group_chain('MF', 'EM#', rows['MF']['EM#']) == ['EM']                 # after the EMO lines, but in EM
    assert ri.group_chain('MF', 'ERF1.1', rows['MF']['ERF1.1']) == ['ER', 'ERF', 'ERF1']
    assert ri.group_chain('MF', 'RO2', rows['MF']['RO2']) == ['RO', 'RO2']          # an older file's single RO2 row
    assert ri.group_chain('CA', 'EMH1', rows['CA']['EMH1']) == ['EM', 'EMH']
    assert ri.group_chain('MF', 'XYZ9', 10 ** 6) == []
    assert ri.template_groups()['MF']['groups']['EMH']['name'].startswith('Human Resource')


def _subtotal_of(ws, row, col):
    """The value Excel gives the SUBTOTAL(9, …) of a summary row: the lines in its range, nested summary rows left out."""
    f = ws.cell(row=row, column=col).value
    a, b = (int(x) for x in f.split(',')[1].rstrip(')').replace(f'{get_column_letter(col)}', '').split(':'))
    return sum(ws.cell(row=i, column=col).value or 0.0 for i in range(a, b + 1)
               if not str(ws.cell(row=i, column=1).value or '').startswith(review.GROUP_PREFIX))


def test_review_sheet_groups_lines_by_the_form_with_subtotals(tmp_path):
    prior_lines, anchors, tool, meta = _data()
    data = review.assemble(prior_lines, anchors, tool, meta, _ctx())          # the real 2027 template's rows
    wb = openpyxl.Workbook()
    ws = review.build_review_sheet(wb, data, meta)
    col_a = {str(ws.cell(row=i, column=1).value or ''): i for i in range(1, ws.max_row + 1)}
    # form order, the summary row above its lines, nested groups inside their parent
    assert col_a['Cộng RM'] < col_a['RM.AP'] < col_a['Cộng RPa'] < col_a['RP1'] < col_a['RP2'] < col_a['Cộng ngoài form'] < col_a['RO2a']
    assert col_a['Cộng EM'] < col_a['Cộng EMH'] < col_a['EMH2'] < col_a['Cộng ES'] < col_a['Cộng ESS'] < col_a['ESS1']
    assert ws.cell(row=col_a['Cộng EMH'], column=2).value.startswith('Human Resource')
    lvl = {k: ws.row_dimensions[i].outline_level for k, i in col_a.items()}
    assert lvl['Cộng EM'] == 0 and lvl['Cộng EMH'] == 1 and lvl['EMH2'] == 2 and lvl['RM.AP'] == 1 and lvl['RO2a'] == 1
    assert ws.sheet_properties.outlinePr.summaryBelow is False
    # every subtotal equals its lines, in each money column; a group never takes a line of another
    by_code = {x['code']: x for b in data['rows_by'].values() for x in b['rows']}
    for g, members in (('EM', ['EMH2']), ('EMH', ['EMH2']), ('ES', ['ESS1', 'ESS38', 'ESM4']), ('ESS', ['ESS1', 'ESS38']),
                       ('EE', ['EEE.C']), ('RPa', ['RP1', 'RP2'])):
        for col, key in ((6, 'approved'), (8, 'converted'), (9, 'tool_num'), (10, 'diff')):
            assert _subtotal_of(ws, col_a[f'Cộng {g}'], col) == pytest.approx(sum(by_code[c][key] for c in members)), (g, key)
    assert _subtotal_of(ws, col_a['Cộng ngoài form'], 6) == pytest.approx(12_000_000.0)
    r = col_a['Cộng ESS']
    assert ws.cell(row=r, column=11).value == f'=IF(ABS(H{r})<0.5,"",J{r}/H{r})'
    assert ws.cell(row=r, column=3).value is None and ws.cell(row=r, column=12).value is None   # no N-1 column in the file
    # the section total still adds the lines once
    tot_e = col_a['Tổng E']
    assert ws.cell(row=tot_e, column=6).value == pytest.approx(sum(x['approved'] for x in data['rows_by'][('MF', 'E')]['rows']))
    # the web's code reader takes the lines only, never a summary row
    p = os.path.join(tmp_path, 'groups.xlsx')
    wb.save(p)
    from webapp import adjust
    keys = set(adjust.review_columns(p)['approved'])
    assert keys == {f'MF|{c}' for c in by_code}


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


# ---- abnormal differences (change flag-abnormal-review-diffs) -----------------------------------

def test_abnormal_rule_cases():
    assert review.is_abnormal(300_000_000.0, 0.30)                    # both thresholds reached
    assert not review.is_abnormal(30_000_000.0, 3.0)                  # large %, small amount
    assert not review.is_abnormal(-192_000_000.0, -0.074)             # large amount, small %
    assert review.is_abnormal(50_000_000.0, None)                     # no approved figure: the amount alone
    assert review.is_abnormal(-100_000_000.0, -1.0)                   # zero-tool code
    assert not review.is_abnormal(None, None) and not review.is_abnormal(49_999_999.0, None)
    assert not review.is_abnormal(60_000_000.0, 0.1999) and review.is_abnormal(-60_000_000.0, -0.2)
    assert review.ABNORMAL_RULE_VI == '≥20% và ≥50 triệu/năm'


def test_assemble_flags_abnormal_lines_and_counts_them():
    prior_lines, anchors, tool, meta = _data()
    data = review.assemble(prior_lines, anchors, tool, meta, _ctx(), template={'MF': {}})
    rows = {x['code']: x for b in data['rows_by'].values() for x in b['rows']}
    assert rows['ESS38']['abnormal'] and rows['RP2']['abnormal']          # −100% of 108M; 50M with no approved figure
    assert not any(rows[c]['abnormal'] for c in ('RM.AP', 'RP1', 'EMH2', 'EEE.C', 'ESS1', 'ESM4', 'RO2a'))
    assert data['counts']['abnormal'] == 2
    assert sorted((x['fund'], x['code']) for x in data['abnormal']) == [('MF', 'ESS38'), ('MF', 'RP2')]
    js = review.summary_json(data, meta)
    assert js['abnormal_rule'] == {'pct': 0.2, 'vnd': 50_000_000.0} and len(js['abnormal']) == 2
    assert any(x['code'] == 'ESS38' and x['abnormal'] for x in js['top'])
    assert any(x['code'] == 'RM.AP' and not x['abnormal'] for x in js['top'])
    md = review.summary_md(data, meta)
    assert 'bất thường (≥20% và ≥50 triệu/năm): 2' in md and '| Bất thường |' in md


def test_review_sheet_marks_abnormal_lines(tmp_path):
    prior_lines, anchors, tool, meta = _data()
    data = review.assemble(prior_lines, anchors, tool, meta, _ctx(), template={'MF': {}})
    wb = openpyxl.Workbook()
    review.build_review_sheet(wb, data, meta)
    ws = wb[review.REVIEW_SHEET]
    by_code = {ws.cell(row=r, column=1).value: r for r in range(1, ws.max_row + 1)}
    r_ab, r_ok = by_code['ESS38'], by_code['RM.AP']
    for col in review.ABNORMAL_COLS:
        assert str(ws.cell(row=r_ab, column=col).fill.start_color.rgb).endswith('FCE4D6')
        assert ws.cell(row=r_ok, column=col).fill.fill_type is None
    assert ws.cell(row=r_ab, column=16).value.startswith(review.LABEL_ABNORMAL)
    assert ws.cell(row=by_code['ESS1'], column=16).value == ri.FLAG_MONTHS      # not flagged: remark unchanged
    assert 'bất thường (≥20% và ≥50 triệu/năm): 2' in ws['A3'].value and review.LABEL_ABNORMAL in ws['A2'].value
    wb.save(os.path.join(tmp_path, 'out.xlsx'))
