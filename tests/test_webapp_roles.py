"""Phân quyền tải file của trang nhập liệu theo tiêu đề X-Hub-Role do reverse proxy gắn.

Viewer chỉ thấy và tải được bản giao khách; hai file nội bộ bị ẩn khỏi danh sách và bị chặn (403) dù đoán đúng tên.
Không có tiêu đề, hoặc giá trị khác `viewer`, thì đủ 3 file như trước. Lượt chạy được dựng sẵn trong bộ nhớ với ba
file giả, không chạy pipeline. Đăng nhập tắt (BUDGET_WEB_AUTH=off) vì phần SSO không phải đối tượng ở đây.
"""
import os

import pytest

os.environ['BUDGET_WEB_AUTH'] = 'off'
pytest.importorskip('fastapi')
from fastapi.testclient import TestClient  # noqa: E402

from webapp import server  # noqa: E402

DELIVERABLE = 'Demo Tower - Sample Consulting Budget.xlsx'
INTERNAL = ['Project_Budget_Output.xlsx', 'Roster_Demand_Model.xlsx']


@pytest.fixture
def run_id(tmp_path):
    for name in [DELIVERABLE] + INTERNAL:
        (tmp_path / name).write_bytes(b'PK\x03\x04 test')
    rid = 'test-run'
    server._runs[rid] = dict(
        status='done', rc=0, started='2026-10-19T16:00:00', finished='2026-10-19T16:01:00',
        workdir=str(tmp_path), input=str(tmp_path / 'in.xlsx'), outputs=server._outputs(str(tmp_path)),
        log=['[1/2] Client deliverable + roster  (generate_project_budget.py)',
             f'Copied into place: {tmp_path / DELIVERABLE}',
             '[2/2] Internal analysis  (generate_project_output.py)',
             f'Copied into place: {tmp_path / INTERNAL[0]}',
             '  deliverable   1,327,967 bytes', f'               {tmp_path / DELIVERABLE}',
             '  analysis        118,384 bytes', f'               {tmp_path / INTERNAL[0]}',
             '  roster           33,637 bytes', f'               {tmp_path / INTERNAL[1]}',
             '  -> both outputs describe the same project.'])
    yield rid
    server._runs.pop(rid, None)


@pytest.fixture
def client():
    return TestClient(server.app)


def _names(payload):
    return sorted(o['name'] for o in payload['outputs'])


def test_without_header_all_three_files(client, run_id):
    r = client.get(f'/api/runs/{run_id}')
    assert r.status_code == 200
    assert _names(r.json()) == sorted([DELIVERABLE] + INTERNAL)
    assert len(r.json()['log']) == 11
    for name in [DELIVERABLE] + INTERNAL:
        assert client.get(f'/api/runs/{run_id}/files/{name}').status_code == 200


def test_other_role_value_is_not_viewer(client, run_id):
    r = client.get(f'/api/runs/{run_id}', headers={'X-Hub-Role': 'owner'})
    assert _names(r.json()) == sorted([DELIVERABLE] + INTERNAL)


@pytest.mark.parametrize('header', ['viewer', 'Viewer', ' VIEWER '])
def test_viewer_sees_only_deliverable(client, run_id, header):
    r = client.get(f'/api/runs/{run_id}', headers={'x-hub-role': header})
    assert r.status_code == 200
    body = r.json()
    assert _names(body) == [DELIVERABLE]
    assert body['outputs'][0]['kind'] == 'deliverable'
    assert body['log_total'] == 11          # bộ đếm `since` của trang vẫn theo log đầy đủ
    text = '\n'.join(body['log'])
    for hidden in INTERNAL:
        assert hidden not in text
    assert '[2/2]' not in text
    assert not [ln for ln in body['log'] if ln.startswith(('  analysis', '  roster'))]
    assert DELIVERABLE in text and '[1/2]' in text


def test_viewer_download_blocked_for_internal_files(client, run_id):
    assert client.get(f'/api/runs/{run_id}/files/{DELIVERABLE}',
                      headers={'X-Hub-Role': 'viewer'}).status_code == 200
    for name in INTERNAL:
        r = client.get(f'/api/runs/{run_id}/files/{name}', headers={'X-Hub-Role': 'viewer'})
        assert r.status_code == 403, name
        assert 'bản giao khách' in r.json()['detail']


def test_viewer_also_filtered_under_prefix(client, run_id):
    r = client.get(f'{server.PREFIX}/api/runs/{run_id}', headers={'X-Hub-Role': 'viewer'})
    assert _names(r.json()) == [DELIVERABLE]
    assert client.get(f'{server.PREFIX}/api/runs/{run_id}/files/{INTERNAL[0]}',
                      headers={'X-Hub-Role': 'viewer'}).status_code == 403


def test_helpers_pure():
    outs = [dict(kind='deliverable', name='a.xlsx'), dict(kind='analysis', name='b.xlsx'),
            dict(kind='roster', name='c.xlsx')]
    assert [o['name'] for o in server.visible_outputs(outs, 'viewer')] == ['a.xlsx']
    assert len(server.visible_outputs(outs, None)) == 3
    run = dict(outputs=outs)
    assert server.may_download(run, 'a.xlsx', 'viewer') and not server.may_download(run, 'b.xlsx', 'viewer')
    assert server.may_download(run, 'b.xlsx', None)


def test_site_package_hides_internal_analysis():
    """Gói site: bản phân tích nội bộ ẩn và bị chặn tải; bản giao, lịch trực và file khác của lượt vẫn tải được."""
    outs = [dict(kind='deliverable', name='a.xlsx'), dict(kind='analysis', name='b.xlsx'),
            dict(kind='roster', name='c.xlsx')]
    assert [o['name'] for o in server.visible_outputs(outs, None, site=True)] == ['a.xlsx', 'c.xlsx']
    assert len(server.visible_outputs(outs, None, site=False)) == 3
    run = dict(outputs=outs)
    assert not server.may_download(run, 'b.xlsx', None, site=True)
    assert server.may_download(run, 'a.xlsx', None, site=True) and server.may_download(run, 'c.xlsx', None, site=True)
    assert server.may_download(run, 'in.xlsx', None, site=True)
    assert [o['name'] for o in server.visible_outputs(outs, 'viewer', site=True)] == ['a.xlsx']
