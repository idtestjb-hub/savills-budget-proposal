"""Nút PDF A4 / A3 của bản giao trên trang web (change add-budget-print-layout, spec budget-web-print-pdf).

Không chạy Excel: tiến trình xuất PDF được thay bằng một hàm giả ghi file PDF hoặc trả lời "STOPPED: ...".
Lượt chạy dựng sẵn trong bộ nhớ với ba file giả như tests/test_webapp_roles.py.
"""
import os
import subprocess

import pytest

os.environ['BUDGET_WEB_AUTH'] = 'off'
pytest.importorskip('fastapi')
from fastapi.testclient import TestClient  # noqa: E402

from webapp import history, server  # noqa: E402

DELIVERABLE = 'Demo Tower - Sample Consulting Budget.xlsx'
INTERNAL = ['Project_Budget_Output.xlsx', 'Roster_Demand_Model.xlsx']
VIEWER = {'X-Hub-Role': 'viewer'}


@pytest.fixture
def run_id(tmp_path):
    for name in [DELIVERABLE] + INTERNAL:
        (tmp_path / name).write_bytes(b'PK\x03\x04 test')
    rid = 'print-run'
    server._runs[rid] = dict(status='done', rc=0, started='2026-11-11T10:00:00', finished='2026-11-11T10:01:00',
                             workdir=str(tmp_path), input=None, outputs=server._outputs(str(tmp_path)), log=[])
    server._active['id'] = None
    yield rid
    server._runs.pop(rid, None)


@pytest.fixture
def client():
    return TestClient(server.app)


def _fake_export(stdout, write=True):
    def run(cmd, **_kw):
        out = cmd[cmd.index('--out') + 1]
        if write:
            with open(out, 'wb') as fh:
                fh.write(b'%PDF-1.4 test')
        return subprocess.CompletedProcess(cmd, 0 if write else 2, stdout=stdout.encode('utf-8'), stderr=b'')
    return run


def test_viewer_exports_and_downloads_a4(client, run_id, monkeypatch):
    monkeypatch.setattr(server.subprocess, 'run', _fake_export('PDF A4: x.pdf (11 trang)'))
    r = client.post(f'/api/runs/{run_id}/print', json={'paper': 'A4'}, headers=VIEWER)
    assert r.status_code == 200, r.text
    pdf = r.json()['pdf']
    assert pdf == 'Demo Tower - Sample Consulting Budget - In A4.pdf'
    assert sorted(o['name'] for o in r.json()['outputs']) == sorted([DELIVERABLE, pdf])
    got = client.get(f'/api/runs/{run_id}/files/{pdf}', headers=VIEWER)
    assert got.status_code == 200 and got.headers['content-type'] == 'application/pdf'
    assert server._active['id'] is None


def test_bad_paper_and_plain_error(client, run_id, monkeypatch):
    assert client.post(f'/api/runs/{run_id}/print', json={'paper': 'A5'}).status_code == 400
    msg = "Bản giao 'x.xlsx' đang mở trong Excel trên máy chủ. Đóng file rồi bấm lại."
    monkeypatch.setattr(server.subprocess, 'run', _fake_export(f'STOPPED: {msg}', write=False))
    r = client.post(f'/api/runs/{run_id}/print', json={'paper': 'A3'})
    assert r.status_code == 400 and r.json()['detail'] == msg
    assert server._active['id'] is None


def test_busy_server_refuses(client, run_id):
    server._active['id'] = 'other'
    try:
        assert client.post(f'/api/runs/{run_id}/print', json={'paper': 'A4'}).status_code == 409
    finally:
        server._active['id'] = None


def test_pdfs_do_not_change_completeness_and_show_in_site_mode(tmp_path):
    for name in [DELIVERABLE] + INTERNAL + ['Demo Tower - Sample Consulting Budget - In A3.pdf']:
        (tmp_path / name).write_bytes(b'x')
    outs = history.outputs_of(str(tmp_path))
    assert history.is_complete(outs) and len(outs) == 4
    assert 'deliverable_pdf_a3' in {o['kind'] for o in server.visible_outputs(outs, None, site=True)}
    assert {o['kind'] for o in server.visible_outputs(outs, 'viewer')} == {'deliverable', 'deliverable_pdf_a3'}
    assert not history.is_complete([o for o in outs if o['kind'] != 'roster'])
