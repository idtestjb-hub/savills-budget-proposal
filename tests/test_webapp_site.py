"""Chế độ gói site của trang web (change site-standalone-package): api/site, nguồn site=1 của api/reviews, kho rỗng,
trang ngoài chế độ site không đổi; static_report.render; start_site chọn cổng. Dữ liệu và tên dự án đều bịa."""
import json
import os
import socket

import pytest

os.environ['BUDGET_WEB_AUTH'] = 'off'
pytest.importorskip('fastapi')
from fastapi.testclient import TestClient  # noqa: E402

from webapp import history, server, start_site, static_report  # noqa: E402
from tests.test_webapp_review import DELIV, INTERNAL, _review_run, fake_worker, runs_dir  # noqa: E402, F401

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


def test_static_report_renders_the_review_figures(runs_dir):
    wd = _review_run(runs_dir)
    (wd / 'review_notes.json').write_text(json.dumps(dict(
        notes=[dict(kind='để trống, PM điền', where='Site Area', text='không có trên file')],
        filled=dict(blank=['Site Area'], facts=['City / Province']))), encoding='utf-8')
    (wd / 'run.log').write_text('[1/4] x\n', encoding='utf-8')
    path = static_report.render(str(wd))
    assert os.path.basename(path) == 'ket-qua.html'
    html = open(path, encoding='utf-8').read()
    assert 'Khu Thu Nghiem' in html and 'Ngân sách đã duyệt 2026 so với ngân sách 2027' in html
    assert 'Quỹ quản lý vận hành' in html and 'Tổng thu' in html and 'Thặng dư' in html
    assert 'Duyệt NS 2026 (quy đổi)' in html and 'Công cụ NS 2027' in html
    assert 'ESS38' in html and 'Chưa có phương pháp' in html
    assert 'KHỚP' in html and 'LỆCH' in html
    assert 'Site Area' in html and DELIV in html and all(n in html for n in INTERNAL)
    assert 'href="run/' in html and str(wd) not in html


def test_static_report_shows_the_stop_line(runs_dir):
    wd = runs_dir / '20261105-100000_review-Khu-Thu-Nghiem'
    wd.mkdir()
    (wd / 'run.log').write_text('[1/4] x\nSTOPPED: no month columns\nGợi ý: ...\n', encoding='utf-8')
    html = open(static_report.render(str(wd), project=PROJECT), encoding='utf-8').read()
    assert 'STOPPED: no month columns' in html and 'Lượt chưa ra kết quả' in html


def test_start_site_skips_a_taken_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        s.listen(1)
        taken = s.getsockname()[1]
        port = start_site.free_port(start=taken, tries=5)
        assert port != taken and taken < port <= taken + 4
