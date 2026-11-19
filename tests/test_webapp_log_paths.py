"""Khung log trên trang không hiện đường dẫn máy chủ (C:\\...): chỉ còn tên file hoặc tên thư mục cuối.

run.log trên đĩa vẫn giữ đường dẫn đầy đủ. Lượt chạy được dựng sẵn trong bộ nhớ, không chạy pipeline (TEST DATA).
"""
import os

import pytest

os.environ['BUDGET_WEB_AUTH'] = 'off'
pytest.importorskip('fastapi')
from fastapi.testclient import TestClient  # noqa: E402

from webapp import server  # noqa: E402

DELIVERABLE = 'Demo Tower (TEST DATA) - Sample Consulting Budget.xlsx'


@pytest.mark.parametrize('line, shown', [
    (r'Saved locally: C:\ZWork\tmp\Demo Tower (TEST DATA) - Sample Consulting Budget.xlsx',
     'Saved locally: Demo Tower (TEST DATA) - Sample Consulting Budget.xlsx'),
    (r'Thư mục chạy: C:\Users\SVN\Savills Asia Pacific\VN, IT Collab - Data\web_runs\20261119-121521_Demo',
     'Thư mục chạy: 20261119-121521_Demo'),
    (r'copy C:\a\b.xlsx -> D:\c d\e.xlsx', 'copy b.xlsx -> e.xlsx'),
    ('Roster: C:/ZWork/run/Roster_Demand_Model.xlsx', 'Roster: Roster_Demand_Model.xlsx'),
    (r'Mở \\fileserver\share\Budget\Input.xlsx', 'Mở Input.xlsx'),
    (r'  File "C:\Python312\Lib\site-packages\openpyxl\reader.py", line 12, in load',
     '  File "reader.py", line 12, in load'),
    (r'Ngân sách năm ngoái: C:\in\Sunrise 2025.xlsx', 'Ngân sách năm ngoái: Sunrise 2025.xlsx'),
])
def test_hide_paths_keeps_only_the_name(line, shown):
    assert server.hide_paths([line]) == [shown]


@pytest.mark.parametrize('line', [
    'Budget web: http://127.0.0.1:8090/ (https://example.test/a/b)',
    'Apartment rate: 18,671 VND/m²/month',
    '[1/2] Client deliverable + roster  (generate_project_budget.py)',
    'Giờ chạy 16:00:05, tỷ lệ 3:1',
    '',
])
def test_hide_paths_leaves_other_text_alone(line):
    assert server.hide_paths([line]) == [line]


@pytest.fixture
def run_id(tmp_path):
    (tmp_path / DELIVERABLE).write_bytes(b'PK\x03\x04 test')
    rid = 'test-run-paths'
    server._runs[rid] = dict(
        status='done', rc=0, started='2026-11-19T16:00:00', finished='2026-11-19T16:01:00',
        workdir=str(tmp_path), input=str(tmp_path / 'in.xlsx'), outputs=server._outputs(str(tmp_path)),
        log=[f'Thư mục chạy: {tmp_path}', f'Copied into place: {tmp_path / DELIVERABLE}', 'Done.'])
    yield rid
    server._runs.pop(rid, None)


@pytest.mark.parametrize('headers', [{}, {'X-Hub-Role': 'viewer'}])
def test_page_log_has_no_folder_paths(run_id, tmp_path, headers):
    body = TestClient(server.app).get(f'/api/runs/{run_id}', headers=headers).json()
    text = '\n'.join(body['log'])
    assert str(tmp_path.parent) not in text and ':\\' not in text
    assert f'Copied into place: {DELIVERABLE}' in body['log']
    assert body['log'][0] == f'Thư mục chạy: {tmp_path.name}'
    assert body['log_total'] == 3
    assert server._runs[run_id]['log'][1] == f'Copied into place: {tmp_path / DELIVERABLE}'   # bản trong bộ nhớ/đĩa giữ nguyên
