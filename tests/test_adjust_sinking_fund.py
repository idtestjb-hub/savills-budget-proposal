"""Bảng điều chỉnh với dòng quỹ bảo trì (change add-sinking-fund, task 6.1): khoá SF|<mã>, remark ở cột U của sheet 3,
dòng Nhập số nối tháng I:T, số duyệt từ review_summary.json. TEST DATA: workbook bịa, không chạy pipeline."""
import json

import openpyxl

import budget_adjustment as ba
from webapp import adjust, adjust_run

MF, SF = '2. Budget-Management Fund', '3. Budget-Sinking Fund'
ROW = 20


def _deliverable(path, remark='PM điền: chưa đủ 10 dự án có số'):
    """Sheet 3 with one PM line (ERB1) laid out like the form: code Z, item AA, frequency D, unit price G, months I:T,
    remark U, year AF = SUM(AL:AW); then its "Nhập số" row on '4. Điều chỉnh'."""
    wb = openpyxl.Workbook()
    wb.active.title = '1. Summary'
    wb.create_sheet(MF)
    ws = wb.create_sheet(SF)
    wb.create_sheet('3.1 Report-Sinking Fund')
    ws.cell(row=ROW, column=26, value='ERB1')
    ws.cell(row=ROW, column=27, value='Building repair\nSửa chữa tòa nhà (TEST)')
    ws.cell(row=ROW, column=4, value='Monthly')
    ws.cell(row=ROW, column=8, value=f'=IF($D{ROW}="Schedule",SUM(I{ROW}:T{ROW}),G{ROW}*F{ROW})')
    ws.cell(row=ROW, column=21, value=remark)
    ws.cell(row=ROW, column=32, value=f'=SUM(AL{ROW}:AW{ROW})')
    ba.build_sheet(wb, [])
    added, skipped = ba.add_pm_rows(wb, [dict(code='ERB1', name='Sửa chữa tòa nhà (TEST)', reason='chưa đủ 10 dự án có số')],
                                    SF, 'AF', 'AL')
    assert added == ['ERB1'] and not skipped
    wb.save(path)
    return path


def test_sf_line_reads_with_its_key_fund_and_remark(tmp_path):
    p = _deliverable(str(tmp_path / 'd.xlsx'))
    items = {i['key']: i for i in adjust.read_items(p)}
    it = items['SF|ERB1']
    assert it['fund'] == 'SF' and it['fund_sheet'] == SF and it['section'] == 'E'
    assert it['pm_fill'] and it['pm_empty'] and it['adj_type'] == ba.TYPE_ENTER
    assert it['remark'] == 'PM điền: chưa đủ 10 dự án có số'          # cột U, không phải T
    assert it['freq_editable'] is False                                 # dòng nối từng tháng (design D6)


def test_entered_figure_rewrites_the_sheet_3_remark(tmp_path):
    p = _deliverable(str(tmp_path / 'd.xlsx'))
    wb = openpyxl.load_workbook(p)
    written = adjust.apply_edits(wb, [dict(key='SF|ERB1', adj_type=ba.TYPE_ENTER, inflation=0,
                                           subs=[dict(idx=0, new_price=24_000_000)])])
    assert written == ['ERB1']
    ws = wb[SF]
    assert ws.cell(row=ROW, column=21).value.startswith('Số do PM nhập: 24,000,000 VND/năm. Công cụ không tính được: ')
    assert not str(ws.cell(row=ROW, column=20).value).startswith('Số do PM')   # T là tháng 12 của sheet 3, không phải remark
    assert ws.cell(row=ROW, column=4).value == 'Schedule'                # tháng I:T nối sheet 4
    assert all(str(ws.cell(row=ROW, column=9 + k).value).startswith('=') for k in range(12))
    out = str(tmp_path / 'after.xlsx')
    wb.save(out)
    it = {i['key']: i for i in adjust.read_items(out)}['SF|ERB1']
    assert not it['pm_empty'] and adjust.new_amount(it) == 24_000_000


def test_remark_sent_from_the_web_goes_to_column_u(tmp_path):
    p = _deliverable(str(tmp_path / 'd.xlsx'))
    wb = openpyxl.load_workbook(p)
    adjust.apply_edits(wb, [dict(key='SF|ERB1', adj_type='', inflation=0, subs=[], remark='Theo báo giá TEST')])
    assert wb[SF].cell(row=ROW, column=21).value == 'Theo báo giá TEST'


def test_sf_approved_from_the_review_summary(tmp_path):
    with open(tmp_path / 'review_summary.json', 'w', encoding='utf-8') as fh:
        json.dump(dict(sf_rows=[dict(code='ERB1', approved=10_000_000), dict(code='ERE2', approved=None),
                                dict(code='', approved=5)]), fh)
    assert adjust.sf_approved(str(tmp_path)) == {'SF|ERB1': 10_000_000.0}
    assert adjust.sf_approved(str(tmp_path / 'none')) == {}


def test_sf_items_order_by_the_template_row_without_groups():
    items = [dict(fund='SF', code='ERB1'), dict(fund='SF', code='EZZ9')]
    adjust.add_groups(items, codes={}, groups={}, sf_rows={'ERB1': 40})
    assert items[0]['groups'] == [] and items[0]['order'] == 40
    assert items[1]['groups'][0]['code'] == adjust.OFF_FORM_GROUP


def test_sf_template_rows_cover_the_form():
    rows = adjust.sf_template_rows()
    assert rows.get('ERM') == 15 and len(rows) >= 150


def test_new_project_page_inputs_reach_the_generator(tmp_path):
    """Task 3.2 / 6.3: the new-project tab's warranty months and total lifts go web -> fill_input.SCALARS -> form ->
    generate_project_budget.read_input; blank warranty = 24, blank lifts = None. TEST DATA."""
    import generate_project_budget as gpb
    from webapp import fill_input
    base = dict(project_name='ZZ TEST', city='Ho Chi Minh City', district='Quan 9', tower_count=1, floor_count=20)
    products = [dict(name='Apartment', gfa=20000, nfa=16000, units=200)]
    dest = str(tmp_path / 'a' / 'Project_Budget_Input.xlsx')
    fill_input.write_input(dict(scalars=dict(base, warranty_months=6, total_lifts=12), products=products), dest)
    project = gpb.read_input(dest)[0]
    assert project['warranty_months'] == 6 and project['total_lifts'] == 12
    dest2 = str(tmp_path / 'b' / 'Project_Budget_Input.xlsx')
    fill_input.write_input(dict(scalars=base, products=products), dest2)
    project2 = gpb.read_input(dest2)[0]
    assert project2['warranty_months'] == 24 and project2.get('total_lifts') is None


def test_adjust_run_reads_the_sinking_fund_total(tmp_path):
    p = str(tmp_path / 'v.xlsx')
    wb = openpyxl.Workbook()
    wb.active.title = SF
    wb[SF]['AF14'] = 123_000_000
    wb.save(p)
    assert adjust_run._sf_total(p) == 123_000_000.0
    tool = {'MF': dict(totals={'R': 10.0, 'E': 4.0})}
    assert adjust_run._totals(tool, p) == {'MF': dict(R=10.0, E=4.0, S=6.0), 'SF': dict(R=None, E=123_000_000.0, S=None)}
    assert adjust_run._totals(tool) == {'MF': dict(R=10.0, E=4.0, S=6.0)}
