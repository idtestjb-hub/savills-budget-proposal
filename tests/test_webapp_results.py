"""Phần đọc số của trang kết quả (webapp/results.py) trên file giả dựng bằng openpyxl, và việc viewer vẫn thấy tóm tắt.

Dữ liệu là bịa; tên dự án tham chiếu trong sheet Comparison giả KHÔNG được lọt ra JSON.
"""
import json
import os

import openpyxl
import pytest

os.environ['BUDGET_WEB_AUTH'] = 'off'
pytest.importorskip('fastapi')
from fastapi.testclient import TestClient  # noqa: E402

from webapp import results, server  # noqa: E402

REF_NAMES = ['Khu Do Thi Xanh', 'Thap Sao Mai']


def _analysis(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Summary'
    ws.append(['Project Budget Output — Dự án thử'])
    sl = wb.create_sheet('Service Levels')
    sl.append(['Service Levels — ...'])
    sl.append(['Internal, display only'])
    sl.append(['Service', 'People on duty / day', 'Roster headcount', '24h-equivalent posts', 'Fee-paying NFA (m²)',
               'Measure', 'Unit', 'Level', 'Near cut-off', 'Thresholds applied',
               'Percentile among form-read real projects (%)', 'Projects compared (form-read)', 'Inferred rows'])
    sl.append(['Cleaning', 24, 28, None, 78300, 3262.5, 'm2 NFA thu phi / nguoi truc moi ngay', 'Tiêu chuẩn', None,
               '< 2,500 = Nâng cao; ...', 46.7, 30, 14])
    sl.append(['Security', 16, 23, 5.33, 78300, 0.68, 'chot 24h quy doi / 10.000 m2 NFA thu phi', 'Cơ bản', 'sát ngưỡng',
               '< 1.5 = Cơ bản; ...', 0, 32, 13])
    sl.append(['Landscape', None, None, None, 78300, None, None, 'chưa đặt ngưỡng', None])
    sl.append(['THRESHOLD TABLE — ...'])
    sl.append(['cleaning', 'm2_nfa_per_person'])
    cp = wb.create_sheet('Comparison')
    cp.append(['Comparison'])
    cp.append(['Dự án thử vs. the 2 nearest ...'])
    cp.append(['Metric', 'Dự án thử'] + REF_NAMES)
    cp.append(['SCALE'])
    cp.append(['Total NFA (m²) — matching basis', 78300, 92100.09, 75518.73])
    cp.append(['Apartment units', 600, 1251, 1048])
    cp.append(['APARTMENT MANAGEMENT FEE RATE'])
    cp.append(['Real Apartment rate per comparable (VND/m²/month)', '—', '15,000 (incl. VAT)', '16,800.0 (incl. VAT)'])
    cp.append(['MODEL-DERIVED Apartment rate (this project)', '15,900'])
    cp.append(['Management fee per apartment (VND/month)', '1,908,000', '1,104,318  (approx)', '1,210,606  (approx)'])
    wb.save(path)


@pytest.fixture
def workdir(tmp_path):
    _analysis(tmp_path / 'Project_Budget_Output.xlsx')
    (tmp_path / 'run_log').mkdir()
    (tmp_path / 'run_log' / '20261019-000000_Du-an-thu.json').write_text(json.dumps(dict(
        status='ok', budget_year=2027, vat_basis='inclusive', revenue_vnd=17_727_293_098.6,
        expense_vnd=16_519_573_044.9, fund_surplus_vnd=1_207_720_053.7, required_pct=0.59)), encoding='utf-8')
    return tmp_path


def test_financials_from_run_log(workdir):
    f = results.financials(results.read_run_log(str(workdir)))
    assert f['revenue'] == pytest.approx(17_727_293_098.6)
    assert f['expense'] == pytest.approx(16_519_573_044.9)
    assert f['surplus'] == pytest.approx(1_207_720_053.7)
    assert f['budget_year'] == 2027 and f['note'] == '' and 'run_log' in f['source']


def test_financials_without_excel_say_so():
    f = results.financials(dict(status='excel_unavailable', revenue_vnd=None, expense_vnd=None, fund_surplus_vnd=None))
    assert f['revenue'] is None and 'không có Excel' in f['note']
    assert results.financials(None)['note'].startswith('Chưa có bản ghi run_log')


def test_surplus_derived_when_missing():
    f = results.financials(dict(status='ok', revenue_vnd=10.0, expense_vnd=4.0, fund_surplus_vnd=None))
    assert f['surplus'] == 6.0


def test_service_levels(workdir):
    s = results.service_levels(str(workdir / 'Project_Budget_Output.xlsx'))
    assert [r['service'] for r in s['rows']] == ['Vệ sinh', 'Bảo vệ']
    clean, sec = s['rows']
    assert clean['level'] == 'Tiêu chuẩn' and clean['people'] == 24 and clean['percentile'] == 46.7
    assert clean['compared'] == 30 and clean['unit'].startswith('m² NFA')
    assert sec['near_cutoff'] == 'sát ngưỡng' and sec['level'] == 'Cơ bản'


def test_comparables_are_anonymous(workdir):
    c = results.comparables(str(workdir / 'Project_Budget_Output.xlsx'))
    assert c['columns'] == ['Dự án này', 'Dự án tham chiếu 1', 'Dự án tham chiếu 2']
    text = json.dumps(c, ensure_ascii=False)
    for name in REF_NAMES:
        assert name not in text
    by_label = {r['label']: r['values'] for r in c['rows']}
    assert by_label['Tổng NFA (m²), cơ sở so sánh'] == [78300, 92100.1, 75518.7]
    assert by_label['Số căn hộ'] == [600, 1251, 1048]
    assert by_label['Đơn giá phí quản lý căn hộ thực tế (VND/m²/tháng)'][1] == '15,000 (incl. VAT)'
    assert by_label['Đơn giá căn hộ đề xuất cho dự án này (VND/m²/tháng)'][0] == '15,900'


def test_summarize_survives_missing_files(tmp_path):
    s = results.summarize(str(tmp_path))
    assert s['finance']['revenue'] is None and s['finance']['note']
    assert s['service']['rows'] == [] and s['service']['note']
    assert s['compare']['rows'] == [] and s['compare']['note']


def test_viewer_gets_summary_but_not_internal_files(workdir):
    deliverable = 'Dự án thử - Sample Consulting Budget.xlsx'
    for name in (deliverable, 'Roster_Demand_Model.xlsx'):
        (workdir / name).write_bytes(b'PK')
    rid = 'summary-run'
    server._runs[rid] = dict(status='done', rc=0, started='', finished='', workdir=str(workdir), input='',
                             outputs=server._outputs(str(workdir)), log=[], summary=results.summarize(str(workdir)))
    try:
        client = TestClient(server.app)
        for headers in ({}, {'X-Hub-Role': 'viewer'}):
            body = client.get(f'/api/runs/{rid}', headers=headers).json()
            assert body['summary']['finance']['revenue'] == pytest.approx(17_727_293_098.6)
            assert len(body['summary']['service']['rows']) == 2
            assert body['summary']['compare']['count'] == 2
            for name in REF_NAMES:
                assert name not in json.dumps(body, ensure_ascii=False)
        owner = client.get(f'/api/runs/{rid}').json()
        viewer = client.get(f'/api/runs/{rid}', headers={'X-Hub-Role': 'viewer'}).json()
        assert len(owner['outputs']) == 3 and [o['name'] for o in viewer['outputs']] == [deliverable]
    finally:
        server._runs.pop(rid, None)
