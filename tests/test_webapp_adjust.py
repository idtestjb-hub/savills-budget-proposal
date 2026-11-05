"""Điều chỉnh ngân sách trên web (webapp/adjust.py, api/runs/<id>/adjust): đọc sheet '4. Điều chỉnh', công thức xem trước,
ghi ô nhập theo khoá mã + sheet quỹ, kiểm tra giá trị, số duyệt từ sheet Review, API và quyền viewer.

Sheet 4 được dựng bằng chính budget_adjustment.build_sheet trên dữ liệu bịa; không chạy pipeline, không cần Excel.
"""
import json
import os

import openpyxl
import pytest

os.environ['BUDGET_WEB_AUTH'] = 'off'
pytest.importorskip('fastapi')
from fastapi.testclient import TestClient  # noqa: E402

import budget_adjustment as ba  # noqa: E402
import review  # noqa: E402
from webapp import adjust, history, server  # noqa: E402
from tests.test_review_sheet import _ctx, _data  # noqa: E402

MF, CA = '2. Budget-Management Fund', '2.2 Common area Fund'
DELIV = 'Khu Thu Nghiem - Sample Consulting Budget.xlsx'

ITEMS = [
    dict(code='ESS1', sheet=MF, row=20, name_vi='Dịch vụ bảo vệ', freq='Yearly', months=[100.0] * 12, annual=1200.0, subs=[
        dict(desc_vi='Cổng chính (ca sáng)', unit_vi='người', qty=3, unit_price=200.0, amount=600.0, qty_editable=True),
        dict(desc_vi='CCTV', unit_vi='người', qty=2, unit_price=300.0, amount=600.0, qty_editable=True)]),
    dict(code='EMA7', sheet=MF, row=21, name_vi='Nước uống', freq='Yearly', months=[10.0] * 12, annual=120.0, subs=[
        dict(desc_vi='Nước uống', unit_vi='khoản', qty=1, unit_price=120.0, amount=120.0, qty_editable=False)]),
    dict(code='RM.AP', sheet=MF, row=10, name_vi='Phí quản lý căn hộ', freq='Monthly', months=[50.0] * 12, annual=600.0, subs=[
        dict(desc_vi='NFA căn hộ', unit_vi='m²', qty=100, unit_price=6.0, amount=600.0, qty_editable=True)]),
    dict(code='ESS4', sheet=CA, row=30, name_vi='Vệ sinh', freq='Yearly', months=[5.0] * 12, annual=60.0, subs=[]),
]


def _deliverable(path):
    wb = openpyxl.Workbook()
    wb.active.title = '1. Summary'
    for name in (MF, CA):
        wb.create_sheet(name)
    wb.create_sheet('3.1 Report-Sinking Fund')
    ba.build_sheet(wb, ITEMS)
    wb.save(path)
    return path


@pytest.fixture
def deliv(tmp_path):
    return _deliverable(str(tmp_path / DELIV))


def test_read_items_keys_and_subs(deliv):
    items = {i['key']: i for i in adjust.read_items(deliv)}
    assert list(items) == ['MF|ESS1', 'MF|EMA7', 'MF|RM.AP', 'CA|ESS4']
    e = items['MF|ESS1']
    assert e['section'] == 'E' and e['amount'] == 1200.0 and e['adj_type'] == '' and e['has_subs']
    assert [s['qty'] for s in e['subs']] == [3, 2] and e['subs'][0]['qty_editable']
    assert items['MF|EMA7']['subs'][0]['qty_editable'] is False          # dòng gộp: SL khoá (cột J là công thức)
    assert items['MF|RM.AP']['section'] == 'R'
    assert items['CA|ESS4']['has_subs'] is False and items['CA|ESS4']['amount'] == 60.0
    assert all(abs(adjust.new_amount(i) - i['amount']) < 1e-9 for i in items.values())   # chưa chỉnh = số gốc


def test_read_items_carries_the_new_year_remark(deliv):
    wb = openpyxl.load_workbook(deliv)
    fund_row = {i['key']: i for i in adjust.read_items(deliv)}      # fund_row của mỗi mã nằm ở sheet điều chỉnh
    ws = wb[adjust.SHEET]
    rows = {(ws.cell(r, ba.COL['code']).value, ws.cell(r, ba.COL['fund_sheet']).value): ws.cell(r, ba.COL['fund_row']).value
            for r in range(ba.FIRST_DATA_ROW, ws.max_row + 1) if ws.cell(r, ba.COL['kind']).value == ba.ROW_KIND_TOTAL}
    wb[MF].cell(row=rows[('ESS1', MF)], column=adjust.REMARK_COL, value='  Bảo vệ 24/24, 5 vị trí  ')
    wb[MF].cell(row=rows[('EMA7', MF)], column=adjust.REMARK_COL, value='=Z1')      # công thức: không đọc được, để trống
    wb[CA].cell(row=rows[('ESS4', CA)], column=adjust.REMARK_COL, value='Vệ sinh khu chung')
    wb.save(deliv)
    items = {i['key']: i for i in adjust.read_items(deliv)}
    assert items['MF|ESS1']['remark'] == 'Bảo vệ 24/24, 5 vị trí'
    assert items['MF|EMA7']['remark'] == ''
    assert items['CA|ESS4']['remark'] == 'Vệ sinh khu chung'
    assert items['MF|RM.AP']['remark'] == '' and set(fund_row) == set(items)


def test_apply_edits_writes_the_remark_only_when_sent(deliv, tmp_path):
    wb = openpyxl.load_workbook(deliv)
    wb[MF].cell(row=21, column=adjust.REMARK_COL, value='Remark cũ của EMA7')
    written = adjust.apply_edits(wb, [
        dict(key='MF|ESS1', adj_type='', inflation=0, subs=[], remark='  Bảo vệ 24/24, 6 vị trí  '),
        dict(key='MF|EMA7', adj_type='Trượt giá', inflation=0.05, subs=[]),                     # không gửi remark
        dict(key='CA|ESS4', adj_type='', inflation=0, subs=[], remark='')])                      # xoá remark
    assert written == ['ESS1', 'EMA7', 'ESS4']
    out = str(tmp_path / 'remark.xlsx')
    wb.save(out)
    items = {i['key']: i for i in adjust.read_items(out)}
    assert items['MF|ESS1']['remark'] == 'Bảo vệ 24/24, 6 vị trí'
    assert items['MF|EMA7']['remark'] == 'Remark cũ của EMA7'                                   # giữ nguyên
    assert items['CA|ESS4']['remark'] == ''


@pytest.mark.parametrize('bad', ['=SUM(A1:A2)', 'x' * (adjust.MAX_REMARK + 1), 5])
def test_apply_edits_rejects_a_bad_remark_and_writes_nothing(deliv, bad):
    wb = openpyxl.load_workbook(deliv)
    with pytest.raises(adjust.AdjustError):
        adjust.apply_edits(wb, [dict(key='MF|ESS1', adj_type='Trượt giá', inflation=0.1, subs=[], remark='ghi được'),
                                dict(key='MF|EMA7', adj_type='', inflation=0, subs=[], remark=bad)])
    assert wb[MF].cell(row=20, column=adjust.REMARK_COL).value is None                       # không ghi nửa chừng
    assert {i['key']: i for i in adjust.read_items(deliv)}['MF|ESS1']['adj_type'] == ''


def test_new_amount_follows_the_spec_formulas(deliv):
    e = {i['key']: i for i in adjust.read_items(deliv)}['MF|ESS1']
    e['subs'][0]['new_qty'] = 4                                   # 4.1: SL mới × đơn giá gốc
    assert adjust.new_amount(e, adj_type='Số lượng') == 4 * 200 + 2 * 300
    e['subs'][1]['new_price'] = 330                                # 4.2: SL gốc × đơn giá mới
    assert adjust.new_amount(e, adj_type='Đơn giá') == 3 * 200 + 2 * 330
    assert adjust.new_amount(e, adj_type='Trượt giá', inflation=0.05) == pytest.approx(1260.0)   # 4.3
    assert adjust.new_amount(e, adj_type='') == 1200.0             # để trống: số gốc
    lump = {i['key']: i for i in adjust.read_items(deliv)}['MF|EMA7']
    lump['subs'][0]['new_qty'] = 9                                  # SL khoá: bỏ qua
    assert adjust.new_amount(lump, adj_type='Số lượng') == 120.0
    # Số lượng + Đơn giá: SL mới × đơn giá mới; dòng SL khoá giữ SL gốc (change add-qty-and-price-adjustment)
    assert adjust.new_amount(e, adj_type='Số lượng + Đơn giá') == 4 * 200 + 2 * 330
    e['subs'][0]['new_price'] = 220
    assert adjust.new_amount(e, adj_type='Số lượng + Đơn giá') == 4 * 220 + 2 * 330
    lump['subs'][0]['new_price'] = 132
    assert adjust.new_amount(lump, adj_type='Số lượng + Đơn giá') == 132.0


def test_apply_edits_writes_input_cells_by_key(deliv, tmp_path):
    wb = openpyxl.load_workbook(deliv)
    written = adjust.apply_edits(wb, [
        dict(key='MF|ESS1', adj_type='Số lượng', inflation=0, subs=[dict(idx=0, new_qty=4, new_price=200)]),
        dict(key='MF|EMA7', adj_type='Số lượng', inflation=0, subs=[dict(idx=0, new_qty=9, new_price=120)]),
        dict(key='CA|ESS4', adj_type='Trượt giá', inflation=0.03, subs=[])])
    assert written == ['ESS1', 'EMA7', 'ESS4']
    out = str(tmp_path / 'out.xlsx')
    wb.save(out)
    items = {i['key']: i for i in adjust.read_items(out)}
    assert items['MF|ESS1']['adj_type'] == 'Số lượng' and items['MF|ESS1']['subs'][0]['new_qty'] == 4
    assert items['MF|ESS1']['subs'][1]['new_qty'] == 2                 # dòng không gửi giữ nguyên
    assert items['MF|EMA7']['subs'][0]['qty_editable'] is False        # công thức =G không bị ghi đè
    assert items['CA|ESS4']['adj_type'] == 'Trượt giá' and items['CA|ESS4']['inflation'] == 0.03
    assert items['MF|RM.AP']['adj_type'] == ''                          # mã không gửi giữ nguyên
    ws = openpyxl.load_workbook(out)[ba.SHEET_NAME]
    assert str(ws.cell(row=5, column=ba.COL['new_amount']).value).startswith('=SUM(')   # công thức template còn nguyên
    wb2 = openpyxl.load_workbook(out)                                   # để trống = bỏ điều chỉnh
    adjust.apply_edits(wb2, [dict(key='MF|ESS1', adj_type='', inflation=0, subs=[])])
    assert wb2[ba.SHEET_NAME].cell(row=5, column=ba.COL['adj_type']).value is None


def _old_form(path):
    """The deliverable as an earlier release wrote it: column M without the combined type, dropdown of three types."""
    from openpyxl.worksheet.datavalidation import DataValidation
    wb = openpyxl.load_workbook(path)
    ws = wb[ba.SHEET_NAME]
    for r in range(ba.FIRST_DATA_ROW, ws.max_row + 1):
        if ws.cell(row=r, column=ba.COL['kind']).value == ba.ROW_KIND_TOTAL:
            parent = r
        elif ws.cell(row=r, column=ba.COL['kind']).value == ba.ROW_KIND_DETAIL:
            ws.cell(row=r, column=ba.COL['new_amount']).value = (
                f'=IF($D${parent}="Số lượng",J{r}*H{r},IF($D${parent}="Đơn giá",G{r}*K{r},'
                f'IF($D${parent}="Trượt giá",I{r}*(1+$L${parent}),I{r})))')
    ws.data_validations.dataValidation = []
    dv = DataValidation(type='list', formula1='"Số lượng,Đơn giá,Trượt giá"', allow_blank=True)
    ws.add_data_validation(dv)
    for r in (5, 8, 10, 12):
        dv.add(ws.cell(row=r, column=ba.COL['adj_type']))
    wb.save(path)
    return path


def test_apply_edits_upgrades_an_older_sheet_with_the_same_figures(deliv, tmp_path):
    from tests.test_budget_adjustment import _Eval
    old = _old_form(deliv)
    edits = [dict(key='MF|ESS1', adj_type='Số lượng', inflation=0, subs=[dict(idx=0, new_qty=4)]),
             dict(key='MF|EMA7', adj_type='Đơn giá', inflation=0, subs=[dict(idx=0, new_price=132)]),
             dict(key='MF|RM.AP', adj_type='Trượt giá', inflation=0.05, subs=[])]
    before = openpyxl.load_workbook(old)                        # the old formulas, written by hand as the web did
    bws = before[ba.SHEET_NAME]
    bws['D5'], bws['J6'], bws['D8'], bws['K9'], bws['D10'], bws['L10'] = 'Số lượng', 4, 'Đơn giá', 132, 'Trượt giá', 0.05
    after = openpyxl.load_workbook(old)
    adjust.apply_edits(after, edits)
    aws = after[ba.SHEET_NAME]
    assert 'Số lượng + Đơn giá' in aws['M6'].value and aws['M6'].value == ba.detail_formula(5, 6)
    dvs = [dv for dv in aws.data_validations.dataValidation if dv.type == 'list']
    assert len(dvs) == 1 and dvs[0].formula1 == '"Số lượng,Đơn giá,Số lượng + Đơn giá,Trượt giá,Nhập số"'
    assert {str(r) for r in dvs[0].sqref.ranges} == {'D5', 'D8', 'D10', 'D12'}
    eb, ea = _Eval(before), _Eval(after)
    for ref in ('M5', 'M6', 'M7', 'M8', 'M9', 'M10', 'M11', 'M12'):
        assert ea.cell(ba.SHEET_NAME, ref) == pytest.approx(eb.cell(ba.SHEET_NAME, ref)), ref
    assert ea.cell(ba.SHEET_NAME, 'M5') == 4 * 200 + 2 * 300 and ea.cell(ba.SHEET_NAME, 'M8') == 132
    adjust.apply_edits(after, [dict(key='MF|ESS1', adj_type='Số lượng + Đơn giá', inflation=0,
                                    subs=[dict(idx=0, new_qty=4, new_price=220)])])
    assert ea.cell(ba.SHEET_NAME, 'M5') == 4 * 220 + 2 * 300
    assert len([dv for dv in aws.data_validations.dataValidation if dv.type == 'list']) == 1   # upgrade twice = once
    out = str(tmp_path / 'upgraded.xlsx')
    after.save(out)
    assert {i['key']: i for i in adjust.read_items(out)}['MF|ESS1']['adj_type'] == 'Số lượng + Đơn giá'


@pytest.mark.parametrize('edit, message', [
    (dict(key='MF|KHONGCO', adj_type='Số lượng'), 'Không có mã'),
    (dict(key='MF|ESS1', adj_type='Tăng'), 'không hợp lệ'),
    (dict(key='CA|ESS4', adj_type='Đơn giá'), 'chỉ điều chỉnh được bằng trượt giá'),
    (dict(key='CA|ESS4', adj_type='Số lượng + Đơn giá'), 'chỉ điều chỉnh được bằng trượt giá'),
    (dict(key='MF|ESS1', adj_type='Số lượng + Đơn giá', subs=[dict(idx=0, new_price=-5)]), 'không được âm'),
    (dict(key='MF|ESS1', adj_type='Số lượng', subs=[dict(idx=0, new_qty=-1)]), 'không được âm'),
    (dict(key='MF|ESS1', adj_type='Số lượng', subs=[dict(idx=5, new_qty=1)]), 'không có dòng chi tiết thứ 6'),
    (dict(key='MF|ESS1', adj_type='Trượt giá', inflation=-1.2), 'lớn hơn -100%'),
])
def test_apply_edits_rejects_bad_input_and_writes_nothing(deliv, edit, message):
    wb = openpyxl.load_workbook(deliv)
    good = dict(key='MF|EMA7', adj_type='Trượt giá', inflation=0.1, subs=[])
    with pytest.raises(adjust.AdjustError, match=message):
        adjust.apply_edits(wb, [good, edit])
    assert wb[ba.SHEET_NAME].cell(row=7, column=ba.COL['adj_type']).value is None    # mã hợp lệ cũng chưa được ghi


def test_approved_by_key_from_review_sheet(tmp_path):
    prior_lines, anchors, tool, meta = _data()
    data = review.assemble(prior_lines, anchors, tool, meta, _ctx(), template={'MF': {}})
    wb = openpyxl.Workbook()
    review.build_review_sheet(wb, data, meta)
    p = str(tmp_path / 'analysis.xlsx')
    wb.save(p)
    ap = adjust.approved_by_key(p)
    assert ap['MF|RM.AP'] == pytest.approx(2_592_000_000.0)            # đã quy đổi (×1.08)
    assert ap['MF|EMH2'] == 1_200_000_000.0                         # lương: không VAT
    assert ap['MF|ESS1'] == pytest.approx(1_080_000_000.0)            # hai dòng cộng lại, ×1.08
    assert adjust.review_years(p) == (2026, 2027)
    assert adjust.approved_by_key(str(tmp_path / 'khong-co.xlsx')) == {}


# ---- API ---------------------------------------------------------------------------------------

@pytest.fixture
def run_id(tmp_path, monkeypatch):
    runs = tmp_path / 'web_runs'
    wd = runs / '20261020-110000_Khu-Thu-Nghiem'
    wd.mkdir(parents=True)
    _deliverable(str(wd / DELIV))
    for name in ('Project_Budget_Output.xlsx', 'Roster_Demand_Model.xlsx'):
        (wd / name).write_bytes(b'PK')
    history.write_meta(str(wd), kind='new', project='Khu Thu Nghiem', status='done', rc=0, user='pm.test')
    monkeypatch.setattr(server, 'RUNS_DIR', str(runs))
    server._runs.clear()
    server._active['id'] = None
    yield wd.name
    server._runs.clear()
    server._active['id'] = None


@pytest.fixture
def client():
    return TestClient(server.app)


def test_get_adjust(client, run_id):
    body = client.get(f'/api/runs/{run_id}/adjust').json()
    assert body['deliverable'] == DELIV and len(body['items']) == 4 and body['can_save']
    assert body['has_approved'] is False and body['last'] is None
    assert client.get(f'/api/runs/{run_id}/adjust', headers={'X-Hub-Role': 'viewer'}).json()['can_save'] is False


def test_post_adjust_queues_a_job_without_touching_run_meta(client, run_id, monkeypatch):
    seen = {}

    def worker(job_id):
        seen['job'] = server._runs[job_id]
        server._runs[job_id]['status'] = 'done'
        server._active['id'] = None

    monkeypatch.setattr(server, '_worker', worker)
    edits = [dict(key='MF|ESS1', adj_type='Số lượng', inflation=0, subs=[dict(idx=0, new_qty=4, new_price=200)])]
    r = client.post(f'/api/runs/{run_id}/adjust', json=dict(edits=edits))
    assert r.status_code == 200, r.text
    job = seen['job']
    assert r.json()['kind'] == 'adjust' and r.json()['id'].startswith(run_id + '__adjust-')
    cmd = job['cmd']
    assert cmd[3].endswith('adjust_run.py') and cmd[cmd.index('--deliverable') + 1].endswith(DELIV)
    assert job['log_name'] == 'adjust.log'
    saved = json.load(open(cmd[cmd.index('--edits') + 1], encoding='utf-8'))
    assert saved == edits
    meta = history.read_meta(os.path.join(server.RUNS_DIR, run_id))
    assert meta['kind'] == 'new' and meta['status'] == 'done' and meta['user'] == 'pm.test'   # lượt gốc không đổi


def test_post_adjust_refusals(client, run_id, monkeypatch):
    monkeypatch.setattr(server, '_worker', lambda job_id: None)
    ok = dict(edits=[dict(key='MF|ESS1', adj_type='Trượt giá', inflation=0.05, subs=[])])
    assert client.post(f'/api/runs/{run_id}/adjust', json=ok, headers={'X-Hub-Role': 'viewer'}).status_code == 403
    assert client.post(f'/api/runs/{run_id}/adjust', json=dict(edits=[])).status_code == 400
    r = client.post(f'/api/runs/{run_id}/adjust', json=dict(edits=[dict(key='MF|ESS1', adj_type='Số lượng',
                                                                          subs=[dict(idx=0, new_qty=-3)])]))
    assert r.status_code == 400 and 'không được âm' in r.json()['detail']
    assert client.post(f'/api/runs/{run_id}/adjust', json=ok).status_code == 200
    assert client.post(f'/api/runs/{run_id}/adjust', json=ok).status_code == 409    # một lượt tại một thời điểm


def test_review_columns_old_and_new_layout(tmp_path):
    """The adjust table reads the Review sheet by header: a sheet written before change
    add-review-prior-and-actual-columns (Duyệt at column 5) and one with the N-1 columns in front."""
    from tests.test_review_prior_columns import _measures, _meta_with
    old = openpyxl.Workbook()
    ws = old.active
    ws.title = 'Review'
    ws['A1'] = 'Review — ngân sách đã duyệt 2026 so với ngân sách 2027 do công cụ sinh'
    ws.append([])
    ws.append([adjust.FUND_VI['MF'] + ' (2. Budget-Management Fund)'])
    ws.append(['Mã', 'Hạng mục', 'Duyệt NS 2026 (như file)', 'Hệ số VAT', 'Duyệt NS 2026 (quy đổi)', 'Công cụ NS 2027'])
    ws.append(['EMH2', 'Lương', 1_000.0, 1.0, 1_000.0, 1_100.0])
    p_old = str(tmp_path / 'old.xlsx')
    old.save(p_old)
    cols = adjust.review_columns(p_old)
    assert cols['approved'] == {'MF|EMH2': 1_000.0} and cols['n1'] == {} and cols['labels'] == {}

    prior_lines, anchors, tool, meta = _data()
    meta2 = _meta_with(meta)
    data = review.assemble(prior_lines, anchors, tool, meta2, _ctx(), template={'MF': {}}, measures=_measures())
    wb = openpyxl.Workbook()
    review.build_review_sheet(wb, data, meta2)
    p = str(tmp_path / 'new.xlsx')
    wb.save(p)
    cols = adjust.review_columns(p)
    assert cols['approved']['MF|EMH2'] == 1_200_000_000.0               # Duyệt N, now at column 8
    assert cols['n1']['MF|EMH2'] == 1_000_000_000.0
    assert cols['actual']['MF|EMH2'] == 700_000_000.0
    assert cols['expected']['MF|EMH2'] == 1_100_000_000.0
    assert cols['labels']['n1'] == 'Duyệt NS 2025 (năm trước, quy đổi)'
    assert cols['labels']['actual'] == 'Thực tế 01–09/2025 (9 tháng, quy đổi)'
    assert adjust.review_years(p) == (2026, 2027)

    plain = review.assemble(prior_lines, anchors, tool, meta, _ctx(), template={'MF': {}})
    wb = openpyxl.Workbook()
    review.build_review_sheet(wb, plain, meta)                           # no N-1 columns: 'File không có số'
    p3 = str(tmp_path / 'plain.xlsx')
    wb.save(p3)
    cols = adjust.review_columns(p3)
    assert cols['n1'] == {} and cols['labels'] == {} and cols['approved']['MF|EMH2'] == 1_200_000_000.0


# ---- nhóm của form 2027 cho bảng điều chỉnh trên web (như sheet Review) ----
def test_add_groups_follows_the_form_chain():
    codes = {'MF': {'EM': 40, 'EMH': 41, 'EMH2': 43, 'EMA': 50, 'EMA7': 57, 'RM': 13, 'RM.AP': 14}}
    groups = {'MF': {'groups': {'EM': dict(row=40, name='Chi phí quản lý', parent=None),
                                'EMH': dict(row=41, name='Nhân sự', parent='EM'),
                                'EMA': dict(row=50, name='Hành chính', parent='EM'),
                                'RM': dict(row=13, name='Phí quản lý', parent=None)},
                     'parent_of_row': {43: 'EMH', 57: 'EMA', 14: 'RM', 41: 'EM', 50: 'EM'}}}
    items = [dict(fund='MF', code='EMH2'), dict(fund='MF', code='EMA7'), dict(fund='MF', code='RM.AP'),
             dict(fund='MF', code='EMH'), dict(fund='CA', code='ZZ9')]
    adjust.add_groups(items, codes=codes, groups=groups)
    chain = {it['code']: [g['code'] for g in it['groups']] for it in items}
    assert chain == {'EMH2': ['EM', 'EMH'], 'EMA7': ['EM', 'EMA'], 'RM.AP': ['RM'], 'EMH': ['EM'],
                     'ZZ9': [adjust.OFF_FORM_GROUP]}
    assert items[0]['groups'][1]['name'] == 'Nhân sự'
    assert [it['order'] for it in items] == [43, 57, 14, 41, 10 ** 6]


def test_add_groups_on_the_real_template():
    items = adjust.add_groups([dict(fund='MF', code='ESS1'), dict(fund='MF', code='RM.AP')])
    assert items[0]['groups'] and items[0]['groups'][0]['code'] == 'ES'
    assert items[1]['groups'][0]['code'] == 'RM'


# ---- type "Nhập số" and the zero rows the Review adds (change adjust-rows-for-zero-tool-codes) ----

ZERO = dict(code='ESS38', sheet=MF, row=40, name_vi='Chia sẻ doanh thu', freq='Monthly', months=[0.0] * 12, annual=0.0,
            subs=[dict(desc_vi='Chia sẻ doanh thu', unit_vi='khoản', qty=1.0, unit_price=0.0, amount=0.0, qty_editable=False)])


@pytest.fixture
def deliv_zero(tmp_path):
    p = _deliverable(str(tmp_path / DELIV))
    wb = openpyxl.load_workbook(p)
    ws = wb[MF]
    ws.cell(row=40, column=25, value='ESS38')
    ws.cell(row=40, column=3, value='Monthly')
    ba.append_items(wb, [ZERO])
    wb.save(p)
    return p


def test_read_items_flags_the_zero_row(deliv_zero):
    items = {i['key']: i for i in adjust.read_items(deliv_zero)}
    z = items['MF|ESS38']
    assert z['zero_row'] and z['has_subs'] and z['amount'] == 0.0 and z['section'] == 'E'
    assert not items['MF|ESS1']['zero_row'] and not items['CA|ESS4']['zero_row']     # no sub-rows: not a zero row


def test_enter_type_preview_validation_and_save(deliv_zero, tmp_path):
    items = {i['key']: i for i in adjust.read_items(deliv_zero)}
    z = items['MF|ESS38']
    z['subs'][0]['new_price'] = 240_000_000.0
    assert adjust.new_amount(z, adj_type='Nhập số') == 240_000_000.0
    assert adjust.new_amount(z, adj_type='') == 0.0
    wb = openpyxl.load_workbook(deliv_zero)
    with pytest.raises(adjust.AdjustError, match='không được âm'):
        adjust.apply_edits(wb, [dict(key='MF|ESS38', adj_type='Nhập số', subs=[dict(idx=0, new_price=-1)])])
    assert wb[ba.SHEET_NAME].cell(row=ba.FIRST_DATA_ROW + 11, column=ba.COL['adj_type']).value is None
    assert adjust.apply_edits(wb, [dict(key='MF|ESS38', adj_type='Nhập số', inflation=0,
                                        subs=[dict(idx=0, new_qty=7, new_price=240_000_000)])]) == ['ESS38']
    out = str(tmp_path / 'out.xlsx')
    wb.save(out)
    saved = {i['key']: i for i in adjust.read_items(out)}['MF|ESS38']
    assert saved['adj_type'] == 'Nhập số' and saved['subs'][0]['new_price'] == 240_000_000
    assert saved['subs'][0]['new_qty'] == 1.0 and saved['subs'][0]['qty_editable'] is False   # J untouched (formula)
    ws = openpyxl.load_workbook(out)[ba.SHEET_NAME]
    prow = [r for r in range(5, ws.max_row + 1) if ws.cell(r, 1).value == 'ESS38'][0]
    assert 'Nhập số' in ws.cell(row=prow + 1, column=ba.COL['new_amount']).value


def test_enter_type_needs_detail_rows(deliv):
    wb = openpyxl.load_workbook(deliv)
    with pytest.raises(adjust.AdjustError, match='chỉ điều chỉnh được bằng trượt giá'):
        adjust.apply_edits(wb, [dict(key='CA|ESS4', adj_type='Nhập số')])


def test_top_keys_from_the_review_summary(tmp_path):
    (tmp_path / 'review_summary.json').write_text(json.dumps({'top': [
        {'fund': 'MF', 'code': 'ESS1', 'diff': -3.4}, {'fund': 'CA', 'code': 'RA2', 'diff': 1.0}, {'code': 'X'}]}),
        encoding='utf-8')
    assert adjust.top_keys(str(tmp_path)) == ['MF|ESS1', 'CA|RA2']
    assert adjust.top_keys(str(tmp_path / 'none')) == []
    (tmp_path / 'review_summary.json').write_text('{broken', encoding='utf-8')
    assert adjust.top_keys(str(tmp_path)) == []
