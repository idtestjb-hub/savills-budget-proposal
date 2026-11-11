"""Chế độ gói site của trang web (change site-standalone-package): api/site, nguồn site=1 của api/reviews, kho rỗng,
trang ngoài chế độ site không đổi; start_site chọn cổng. Dữ liệu và tên dự án đều bịa."""
import json
import os
import socket

import pytest

os.environ['BUDGET_WEB_AUTH'] = 'off'
pytest.importorskip('fastapi')
from fastapi.testclient import TestClient  # noqa: E402

from webapp import history, server, start_site  # noqa: E402
from tests.test_webapp_review import fake_worker, runs_dir  # noqa: E402, F401

PROJECT = 'Khu Thu Nghiem'
PRIOR = 'NS duyet 2026 (ban cuoi).xlsx'


@pytest.fixture
def site_dir(tmp_path, monkeypatch):
    d = tmp_path / 'site'
    d.mkdir()
    (d / PRIOR).write_bytes(b'PK\x03\x04 prior')
    (d / 'site.json').write_text(json.dumps(dict(
        project=PROJECT, prior_file=PRIOR, facts=dict(city='Hồ Chí Minh', gate_count=2, has_pool='Yes'),
        store_id='abc', built_at='2026-11-05 10:00', code='0123abc')), encoding='utf-8')
    monkeypatch.setattr(server, 'SITE_DIR', str(d))
    return d


@pytest.fixture
def client():
    return TestClient(server.app)


def test_api_site_returns_package_info_without_paths(client, site_dir):
    r = client.get('/api/site')
    assert r.status_code == 200
    d = r.json()
    assert d['project'] == PROJECT and d['prior_file'] == PRIOR and d['prior_exists'] is True
    assert d['facts']['gate_count'] == 2 and d['code'] == '0123abc'
    assert 'path' not in d and str(site_dir) not in r.text


def test_api_site_is_404_outside_site_mode(client, monkeypatch):
    monkeypatch.setattr(server, 'SITE_DIR', None)
    assert client.get('/api/site').status_code == 404


def test_page_flag_and_library_empty_in_site_mode(client, site_dir, monkeypatch):
    html = client.get('/').text
    assert "const SITE = '1' === '1';" in html
    lib = client.get('/api/library').json()
    assert lib['entries'] == [] and lib['total'] == 0
    assert client.get('/api/library/abc/facts').status_code == 404
    assert client.get('/api/library/overview').status_code == 404


def test_page_unchanged_outside_site_mode(client, monkeypatch):
    monkeypatch.setattr(server, 'SITE_DIR', None)
    html = client.get('/').text
    assert "const SITE = '' === '1';" in html
    assert html.count('data-tab="') == 6
    assert 'id="src-site-btn"' in html and 'class="hidden" id="src-site-btn"' in html


def test_review_from_site_snapshots_the_packaged_file(client, site_dir, runs_dir, fake_worker):
    r = client.post('/api/reviews', data=dict(site='1', facts=json.dumps(dict(city='Hồ Chí Minh'))))
    assert r.status_code == 200, r.text
    run = r.json()
    assert run['kind'] == 'review' and run['project'] == PROJECT
    assert fake_worker.done.wait(5)
    wd = os.path.join(str(runs_dir), run['id'])
    priors = os.listdir(os.path.join(wd, 'prior'))
    assert len(priors) == 1 and priors[0].endswith('.xlsx')
    assert open(os.path.join(wd, 'prior', priors[0]), 'rb').read() == b'PK\x03\x04 prior'
    facts = json.load(open(os.path.join(wd, 'facts.json'), encoding='utf-8'))
    assert facts['City / Province'] == 'Hồ Chí Minh'
    assert run['id'].endswith('_review-Khu-Thu-Nghiem')
    meta = history.read_meta(wd)
    assert meta['project'] == PROJECT and PRIOR in meta['source']
    assert any(h['id'] == run['id'] and h['project'] == PROJECT for h in client.get('/api/history').json()['runs'])


def test_review_from_site_refused_when_file_missing(client, site_dir, runs_dir):
    (site_dir / PRIOR).unlink()
    r = client.post('/api/reviews', data=dict(site='1', facts=json.dumps(dict(city='Hồ Chí Minh'))))
    assert r.status_code == 400 and 'không có file ngân sách đã duyệt' in r.text


def test_review_from_site_refused_outside_site_mode(client, runs_dir, monkeypatch):
    monkeypatch.setattr(server, 'SITE_DIR', None)
    r = client.post('/api/reviews', data=dict(site='1', facts=json.dumps(dict(city='Hồ Chí Minh'))))
    assert r.status_code == 400


def test_start_site_skips_a_taken_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        s.listen(1)
        taken = s.getsockname()[1]
        port = start_site.free_port(start=taken, tries=5)
        assert port != taken and taken < port <= taken + 4


# ---- Gói không kèm ngân sách đã duyệt (change site-package-new-project-entry) ----

@pytest.fixture
def site_dir_no_prior(site_dir):
    info = json.loads((site_dir / 'site.json').read_text(encoding='utf-8'))
    info['prior_file'] = ''
    (site_dir / 'site.json').write_text(json.dumps(info), encoding='utf-8')
    (site_dir / PRIOR).unlink()
    return site_dir


def test_new_project_run_refused_when_the_package_has_an_approved_budget(client, site_dir, runs_dir):
    r = client.post('/api/runs', json=dict(scalars=dict(project_name=PROJECT)))
    assert r.status_code == 403
    assert not list(runs_dir.iterdir())


def test_new_project_run_reaches_the_runner_without_an_approved_budget(client, site_dir_no_prior, runs_dir):
    # Tên trống: qua được bước chặn của gói, dừng ở kiểm tra tên như trên Hub (không chạy pipeline thật).
    r = client.post('/api/runs', json=dict(scalars=dict(project_name='')))
    assert r.status_code == 400 and 'Tên dự án' in r.json()['detail']
    d = client.get('/api/site').json()
    assert d['prior_file'] == '' and d['prior_exists'] is False


def test_new_project_run_unchanged_outside_site_mode(client, runs_dir, monkeypatch):
    monkeypatch.setattr(server, 'SITE_DIR', None)
    r = client.post('/api/runs', json=dict(scalars=dict(project_name='')))
    assert r.status_code == 400


def test_page_marks_only_the_new_project_parts_for_a_package_without_budget(client, site_dir_no_prior):
    html = client.get('/').text
    assert 'body.site.site-new .site-hide.site-new-ok { display: revert; }' in html
    assert 'class="on site-hide site-new-ok" data-tab="nhap"' in html
    assert 'class="site-hide site-new-ok" data-tab="ketqua"' in html
    assert '<section id="hd-new" class="site-hide site-new-ok">' in html
    assert 'data-act="clone"' in html and 'sm site-hide site-new-ok' in html
    # Kho, kiến trúc và nguồn "Dự án có sẵn" vẫn ẩn trong mọi gói.
    assert 'class="site-hide" data-tab="kho"' in html
    assert '<section id="hd-arch" class="site-hide">' in html
    assert "document.body.classList.add('site-new')" in html and 'if (!siteInfo.prior_file)' in html
    assert "getElementById('src-site-btn').classList.add('hidden')" in html
