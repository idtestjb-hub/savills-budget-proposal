"""Danh sách ngân sách đã duyệt có sẵn (webapp/library.py, api/library, api/reviews với library_id).

Kho quét giả (ba CSV) và thư mục SharePoint giả dựng trong thư mục tạm; tên dự án và tên file đều bịa.
"""
import csv
import json
import os

import pytest

os.environ['BUDGET_WEB_AUTH'] = 'off'
pytest.importorskip('fastapi')
from fastapi.testclient import TestClient  # noqa: E402

from webapp import library, server  # noqa: E402
from tests.test_review_import import build_prior_workbook  # noqa: E402

FILES = [  # file_id, file_name, rel_path, source_group, ext
    ('aaa111', 'NS 2026 Khu A.xlsx', 'Budget 2026/NS 2026 Khu A.xlsx', 'new', 'xlsx'),
    ('bbb222', 'NS 2025 Khu B.xlsx', 'NS 2025 Khu B.xlsx', 'old8', 'xlsx'),
    ('ccc333', 'NS 2026 Khu C.pdf', 'Budget 2026/NS 2026 Khu C.pdf', 'new', 'pdf'),
    ('ddd444', 'XLSB__NS Khu D.xlsx', 'extra_in/XLSB__NS Khu D.xlsx', 'new_converted', 'xlsx'),
    ('eee555', '20260101 - NS Khu E.xlsx', 'Budget 2026/20260101 - NS Khu E.xlsx', 'new', 'xlsx'),   # thiếu trên đĩa
    ('fff666', 'NS Khu F.xlsx', 'Budget 2026/NS Khu F.xlsx', 'new', 'xlsx'),                       # không có sheet quỹ
]
NAMES = {'aaa111': 'KHU A', 'bbb222': 'KHU B', 'ddd444': ''}
PROFILE = {'aaa111': ('high', '2026', 'excl', '50000'), 'bbb222': ('medium', '2025', 'incl', ''),
           'ddd444': ('low', '2023', 'incl', ''), 'eee555': ('high', '2026', 'incl', ''), 'fff666': ('', '2026', '', '')}


def _write(path, header, rows):
    with open(path, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


@pytest.fixture
def store(tmp_path, monkeypatch):
    root = tmp_path / 'budget_planning'
    sub = root / library.NEW_SUBFOLDER / 'Budget 2026'
    sub.mkdir(parents=True)
    st = tmp_path / 'scan' / 'final_v2'
    st.mkdir(parents=True)
    (tmp_path / 'scan' / 'extra_in').mkdir()
    build_prior_workbook(str(sub / 'NS 2026 Khu A.xlsx'))
    build_prior_workbook(str(root / 'NS 2025 Khu B.xlsx'))
    (sub / 'NS 2026 Khu C.pdf').write_bytes(b'%PDF')
    build_prior_workbook(str(tmp_path / 'scan' / 'extra_in' / 'XLSB__NS Khu D.xlsx'))
    build_prior_workbook(str(sub / 'NS Khu F.xlsx'))
    _write(st / 'dim_file.csv', ['file_id', 'file_name', 'rel_path', 'source_group', 'ext', 'content_dup_of'],
           [(f, n, r, g, e, '') for f, n, r, g, e in FILES])
    _write(st / 'project_map.csv', ['file_id', 'file_name', 'project_name', 'year_in_name'],
           [(f, n, NAMES.get(f, ''), '') for f, n, *_ in FILES])
    _write(st / 'file_profile.csv', ['file_id', 'primary_confidence', 'budget_year_v2', 'vat_basis_v2', 'nfa_total'],
           [(f,) + PROFILE[f] for f in PROFILE])
    monkeypatch.setenv('BUDGET_WEB_LIBRARY_ROOT', str(root))
    monkeypatch.setenv('BUDGET_WEB_LIBRARY_STORE', str(st))
    library._cache['key'] = None
    return root


def test_load_resolves_live_paths_and_marks_unusable(store):
    by = {e['id']: e for e in library.entries()}
    assert len(by) == 6
    a = by['aaa111']
    assert a['selectable'] and a['project'] == 'KHU A' and a['project_from'] == 'file'
    assert a['year'] == 2026 and a['vat'] == 'excl' and a['nfa'] == 50000 and a['confidence_vi'] == 'Khớp tổng'
    assert a['path'] == os.path.join(str(store), library.NEW_SUBFOLDER, 'Budget 2026', 'NS 2026 Khu A.xlsx')
    assert by['bbb222']['path'] == os.path.join(str(store), 'NS 2025 Khu B.xlsx') and by['bbb222']['selectable']
    assert by['ddd444']['selectable'] and by['ddd444']['project'] == 'NS Khu D' and by['ddd444']['project_from'] == 'tên file'
    assert not by['ccc333']['selectable'] and 'PDF' in by['ccc333']['reason']
    assert not by['eee555']['selectable'] and 'SharePoint' in by['eee555']['reason']
    assert by['eee555']['project'] == 'NS Khu E'                             # tiền tố ngày bị bỏ khỏi tên
    assert not by['fff666']['selectable'] and 'sheet quỹ' in by['fff666']['reason']
    order = [e['id'] for e in library.entries()]
    assert order.index('ccc333') > order.index('ddd444')                      # file chọn được đứng trước


def test_no_store_gives_empty_list(tmp_path, monkeypatch):
    monkeypatch.setenv('BUDGET_WEB_LIBRARY_STORE', str(tmp_path / 'khong-co'))
    library._cache['key'] = None
    assert library.entries() == []


@pytest.fixture
def client(store, tmp_path, monkeypatch):
    monkeypatch.setattr(server, 'RUNS_DIR', str(tmp_path / 'web_runs'))
    server._runs.clear()
    server._active['id'] = None
    yield TestClient(server.app)
    server._runs.clear()
    server._active['id'] = None


def test_api_library_hides_paths(client):
    body = client.get('/api/library').json()
    assert body['total'] == 6 and body['selectable'] == 3
    assert all('path' not in e for e in body['entries'])


def test_review_from_library_copies_a_snapshot(client, monkeypatch):
    seen = {}

    def worker(run_id):
        seen['run'] = server._runs[run_id]
        server._runs[run_id]['status'] = 'done'
        server._active['id'] = None

    monkeypatch.setattr(server, '_worker', worker)
    r = client.post('/api/reviews', data={'library_id': 'aaa111', 'facts': json.dumps(dict(city='Ho Chi Minh City'))})
    assert r.status_code == 200, r.text
    run = seen['run']
    prior = run['cmd'][run['cmd'].index('--prior') + 1]
    assert prior.startswith(os.path.join(run['workdir'], 'prior')) and os.path.getsize(prior) > 0
    assert '--recalc' not in run['cmd'] and run['project'] == 'KHU A' and 'KHU A' in run['source']
    assert r.json()['id'].endswith('_review-KHU-A')


def test_review_from_library_refusals(client, monkeypatch):
    monkeypatch.setattr(server, '_worker', lambda run_id: None)
    facts = json.dumps(dict(city='Ho Chi Minh City'))
    assert client.post('/api/reviews', data={'library_id': 'zzz', 'facts': facts}).status_code == 404
    r = client.post('/api/reviews', data={'library_id': 'ccc333', 'facts': facts})
    assert r.status_code == 400 and 'PDF' in r.json()['detail']
