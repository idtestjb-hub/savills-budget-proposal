"""Link ngoài theo dự án (change budget-web-project-access). TEST DATA: dự án, email và file đều giả.

Cổng link (8091 trong test) đòi token Cloudflare Access ký bằng khoá RSA sinh trong test; người dùng P012 chỉ thấy lượt
và dòng kho của P012, mọi API gọi bằng mã của P020 trả 404 (hoặc 403 khi gửi lượt mới cho P020). Cổng thường không đổi.
"""
import datetime
import json
import os

import openpyxl
import pytest

os.environ['BUDGET_WEB_AUTH'] = 'off'
pytest.importorskip('fastapi')
jwt = pytest.importorskip('jwt')
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402
from fastapi.routing import APIRoute  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from webapp import auth, server  # noqa: E402

TEAM = 'https://test-team.cloudflareaccess.com'
AUD = 'aud-test-0001'
LINK = 8091
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
RUN_A = '20261117-100000_Khu-Thu-Nghiem'
RUN_B = '20261117-110000_Thap-May-Xanh'
RUN_OLD = '20261001-090000_Du-an-cu'
DELIVERABLE_A = 'Khu Thu Nghiem - Sample Consulting Budget.xlsx'
DELIVERABLE_B = 'Thap May Xanh - Sample Consulting Budget.xlsx'


def token(email='pm.a@example.com', key=KEY, aud=AUD, iss=TEAM, minutes=10):
    now = datetime.datetime.now(datetime.timezone.utc)
    claims = dict(email=email, aud=[aud], iss=iss, iat=now, nbf=now, exp=now + datetime.timedelta(minutes=minutes),
                  sub='x', type='app')
    return jwt.encode(claims, key, algorithm='RS256')


def _book(path):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet('Du an')
    ws.append(['Ma', 'Ten', 'Ten khac'])
    ws.append(['P012', 'Khu Thử Nghiệm', 'KTN'])
    ws.append(['P020', 'Tháp Mây Xanh', ''])
    ws = wb.create_sheet('Nguoi dung')
    ws.append(['Email', 'Ma du an'])
    ws.append(['pm.a@example.com', 'P012'])
    ws.append(['boss@example.com', 'ALL'])
    ws.append(['ghost@example.com', 'P999'])
    wb.save(path)


def _run(runs, rid, code, deliverable, project):
    d = runs / rid
    d.mkdir()
    for name in (deliverable, 'Project_Budget_Output.xlsx', 'Roster_Demand_Model.xlsx'):
        wb = openpyxl.Workbook()
        wb.active['A1'] = 'TEST DATA'
        wb.save(d / name)
    (d / 'Project_Budget_Input.xlsx').write_bytes(b'PK\x03\x04 test')
    meta = dict(kind='new', project=project, user='x', started='2026-11-17T10:00:00', finished='2026-11-17T10:01:00',
                status='done', rc=0)
    if code:
        meta['project_code'] = code
    (d / 'web_meta.json').write_text(json.dumps(meta), encoding='utf-8')
    (d / 'run.log').write_text('ok\n', encoding='utf-8')


@pytest.fixture
def env(tmp_path, monkeypatch):
    runs = tmp_path / 'runs'
    runs.mkdir()
    _run(runs, RUN_A, 'P012', DELIVERABLE_A, 'Khu Thử Nghiệm')
    _run(runs, RUN_B, 'P020', DELIVERABLE_B, 'Tháp Mây Xanh')
    _run(runs, RUN_OLD, '', DELIVERABLE_B, 'Dự án cũ')
    book = tmp_path / 'quyen.xlsx'
    _book(book)
    monkeypatch.setattr(server, 'RUNS_DIR', str(runs))
    monkeypatch.setattr(server, 'LINK_PORT', LINK)
    monkeypatch.setattr(server, 'ACCESS_BOOK', str(book))
    monkeypatch.setitem(server._access, 'reader', None)
    monkeypatch.setenv('BUDGET_WEB_CF_TEAM', 'test-team')
    monkeypatch.setenv('BUDGET_WEB_CF_AUD', AUD)
    monkeypatch.setattr(auth, '_cf_key', lambda tok: KEY.public_key())
    entries = [dict(file_id='f1', project='Khu Thu Nghiem', file_name='a.xlsx', path='', selectable=False, reason='x'),
               dict(file_id='f2', project='Thap May Xanh', file_name='b.xlsx', path='', selectable=False, reason='x'),
               dict(file_id='f3', project='Không khớp', file_name='c.xlsx', path='', selectable=False, reason='x')]
    monkeypatch.setattr(server.library, 'entries', lambda: entries)
    monkeypatch.setattr(server.library, 'find', lambda fid: next((e for e in entries if e['file_id'] == fid), None))
    for rid in (RUN_A, RUN_B, RUN_OLD):
        server._runs.pop(rid, None)
    yield runs
    for rid in (RUN_A, RUN_B, RUN_OLD):
        server._runs.pop(rid, None)


@pytest.fixture
def link():
    return TestClient(server.app, base_url=f'http://testserver:{LINK}')


@pytest.fixture
def hub():
    return TestClient(server.app)


def H(email='pm.a@example.com', **kw):
    return {auth.CF_TOKEN_HEADER: token(email, **kw)}


# ---- token -------------------------------------------------------------------------------------------------------

def test_link_without_token_is_401(env, link):
    assert link.get('/api/history').status_code == 401
    assert link.get('/').status_code == 401


@pytest.mark.parametrize('bad', [dict(key=OTHER_KEY), dict(aud='other-aud'), dict(iss='https://evil.cloudflareaccess.com'),
                                 dict(minutes=-5)])
def test_link_bad_token_is_401(env, link, bad):
    assert link.get('/api/history', headers=H(**bad)).status_code == 401


def test_bare_email_header_is_ignored(env, link):
    r = link.get('/api/history', headers={'Cf-Access-Authenticated-User-Email': 'boss@example.com'})
    assert r.status_code == 401


def test_hub_headers_ignored_on_link(env, link):
    r = link.get('/api/history', headers={**H(), 'X-Hub-Role': 'admin', 'X-Hub-User': 'asiavn\\boss'})
    assert {row['id'] for row in r.json()['runs']} == {RUN_A}


def test_hub_port_unchanged(env, hub):
    r = hub.get('/api/history', headers={auth.CF_TOKEN_HEADER: 'garbage'})
    assert r.status_code == 200
    assert {row['id'] for row in r.json()['runs']} == {RUN_A, RUN_B, RUN_OLD}
    files = hub.get(f'/api/runs/{RUN_B}').json()['outputs']
    assert {o['kind'] for o in files} == {'deliverable', 'analysis', 'roster'}


def test_verify_cf_token_needs_settings(monkeypatch):
    monkeypatch.delenv('BUDGET_WEB_CF_AUD', raising=False)
    with pytest.raises(auth.CfTokenError):
        auth.verify_cf_token(token(), get_key=lambda t: KEY.public_key(), team_url=TEAM)


def test_link_settings_required(monkeypatch):
    monkeypatch.setenv('BUDGET_WEB_LINK_PORT', '8091')
    monkeypatch.delenv('BUDGET_WEB_CF_TEAM', raising=False)
    monkeypatch.delenv('BUDGET_WEB_CF_AUD', raising=False)
    monkeypatch.delenv('BUDGET_WEB_ACCESS_BOOK', raising=False)
    assert set(auth.missing_link_settings()) == {'BUDGET_WEB_CF_TEAM', 'BUDGET_WEB_CF_AUD', 'BUDGET_WEB_ACCESS_BOOK'}
    assert auth.cf_team_url('team-x') == 'https://team-x.cloudflareaccess.com'


# ---- who sees what -------------------------------------------------------------------------------------------------

def test_unknown_and_codeless_people_see_nothing(env, link):
    for email in ('someone@example.com', 'ghost@example.com'):
        assert link.get('/api/history', headers=H(email)).status_code == 403
        r = link.get('/', headers=H(email))
        assert r.status_code == 403 and 'chưa được gắn dự án' in r.text


def test_no_list_means_no_access(env, link, monkeypatch, tmp_path):
    monkeypatch.setattr(server, 'ACCESS_BOOK', str(tmp_path / 'khong-co.xlsx'))
    monkeypatch.setitem(server._access, 'reader', None)
    assert link.get('/api/history', headers=H('boss@example.com')).status_code == 403


def test_all_person_sees_everything_on_link(env, link):
    r = link.get('/api/history', headers=H('boss@example.com'))
    assert {row['id'] for row in r.json()['runs']} == {RUN_A, RUN_B, RUN_OLD}


def test_history_and_files_for_project_user(env, link):
    r = link.get('/api/history', headers=H())
    rows = r.json()['runs']
    assert [row['id'] for row in rows] == [RUN_A] and r.json()['runs_dir'] == ''
    assert {o['kind'] for o in rows[0]['outputs']} == {'deliverable', 'roster'}
    run = link.get(f'/api/runs/{RUN_A}', headers=H()).json()
    assert {o['kind'] for o in run['outputs']} == {'deliverable', 'roster'} and run['workdir'] == ''
    assert link.get(f'/api/runs/{RUN_A}/files/{DELIVERABLE_A}', headers=H()).status_code == 200
    assert link.get(f'/api/runs/{RUN_A}/files/Roster_Demand_Model.xlsx', headers=H()).status_code == 200
    assert link.get(f'/api/runs/{RUN_A}/files/Project_Budget_Output.xlsx', headers=H()).status_code == 404


@pytest.mark.parametrize('rid', [RUN_B, RUN_OLD])
def test_other_project_run_is_404_on_every_route(env, link, rid):
    h = H()
    assert link.get(f'/api/runs/{rid}', headers=h).status_code == 404
    assert link.get(f'/api/runs/{rid}/input', headers=h).status_code == 404
    assert link.get(f'/api/runs/{rid}/files/{DELIVERABLE_B}', headers=h).status_code == 404
    assert link.get(f'/api/runs/{rid}/files/Project_Budget_Output.xlsx', headers=h).status_code == 404
    assert link.post(f'/api/runs/{rid}/print', headers=h, json={'paper': 'A4'}).status_code == 404
    assert link.get(f'/api/runs/{rid}/adjust', headers=h).status_code == 404
    assert link.post(f'/api/runs/{rid}/adjust', headers=h, json={'edits': [{'key': 'X', 'qty': 1}]}).status_code == 404
    n = len(os.listdir(env))
    r = link.post('/api/reviews', headers=h, data={'source_run': rid, 'facts': '{}'})
    assert r.status_code == 404 and len(os.listdir(env)) == n


def test_library_filtered(env, link, hub):
    r = link.get('/api/library', headers=H()).json()
    assert [e['file_id'] for e in r['entries']] == ['f1'] and r['root'] == '' and r['store'] == ''
    assert link.get('/api/library/f2/facts', headers=H()).status_code == 404
    assert link.get('/api/library/f3/facts', headers=H()).status_code == 404
    assert link.get('/api/library/overview', headers=H()).status_code == 404
    n = len(os.listdir(env))
    assert link.post('/api/reviews', headers=H(), data={'library_id': 'f2', 'facts': '{}'}).status_code == 404
    assert len(os.listdir(env)) == n
    assert len(hub.get('/api/library').json()['entries']) == 3


def test_new_run_for_other_project_refused_before_folder(env, link):
    n = len(os.listdir(env))
    r = link.post('/api/runs', headers=H(), json={'project_code': 'P020', 'scalars': {'project_name': 'X'}})
    assert r.status_code == 403 and len(os.listdir(env)) == n
    r = link.post('/api/reviews', headers=H(), data={'project_code': 'P020', 'facts': '{}'})
    assert r.status_code == 403 and len(os.listdir(env)) == n


def test_me(env, link, hub):
    me = link.get('/api/me', headers=H()).json()
    assert me['kind'] == 'project' and me['projects'] == [dict(code='P012', name='Khu Thử Nghiệm')]
    assert me['may_add_project'] is False and me['link'] is True
    me = hub.get('/api/me').json()
    assert me['kind'] == 'office' and me['may_add_project'] is True


def test_defaults_hide_paths_for_project_user(env, link):
    d = link.get('/api/defaults', headers=H()).json()
    assert d['runs_dir'] == '' and d['template'] == ''


# ---- every data route goes through the access check ----------------------------------------------------------------

OPEN_PATHS = {'/', '/auth/login', '/auth/callback', '/auth/logout',
              '/auth/code/request', '/auth/code/verify', '/auth/code/logout'}   # change add-link-email-code-login


def _dep_calls(dependant):
    out = {dependant.call}
    for d in dependant.dependencies:
        out |= _dep_calls(d)
    return out


def test_every_route_checks_scope():
    missing = []
    for route in server.router.routes:
        if not isinstance(route, APIRoute) or route.path in OPEN_PATHS:
            continue
        if server.require_scope not in _dep_calls(route.dependant):
            missing.append(route.path)
    assert not missing, f'routes without the project check: {missing}'


# ---- reference names held back (group 4) --------------------------------------------------------------------------

def _xlsx(path, text):
    wb = openpyxl.Workbook()
    wb.active['A1'] = text
    wb.save(path)


def test_file_with_other_project_name_is_held(env, link, monkeypatch):
    monkeypatch.setattr(server, '_leak_words', lambda scope: ['Đồi Gió Hồng'])
    _xlsx(env / RUN_A / DELIVERABLE_A, 'Ngân sách - so với Đồi Gió Hồng')
    _xlsx(env / RUN_A / 'Roster_Demand_Model.xlsx', 'Lịch trực sạch')
    assert link.get(f'/api/runs/{RUN_A}/files/{DELIVERABLE_A}', headers=H()).status_code == 409
    assert link.get(f'/api/runs/{RUN_A}/files/Roster_Demand_Model.xlsx', headers=H()).status_code == 200


def test_office_download_is_not_scanned(env, hub, monkeypatch):
    monkeypatch.setattr(server, '_leak_words', lambda scope: ['Đồi Gió Hồng'])
    _xlsx(env / RUN_A / DELIVERABLE_A, 'so với Đồi Gió Hồng')
    assert hub.get(f'/api/runs/{RUN_A}/files/{DELIVERABLE_A}').status_code == 200


def test_log_lines_with_other_names_dropped(env, link, monkeypatch):
    monkeypatch.setattr(server, '_leak_words', lambda scope: ['Đồi Gió Hồng'])
    (env / RUN_A / 'run.log').write_text('dòng một\nso sánh Đồi Gió Hồng\ndòng ba\n', encoding='utf-8')
    log = link.get(f'/api/runs/{RUN_A}', headers=H()).json()['log']
    assert log == ['dòng một', 'dòng ba']


def test_project_runs_are_scoped_office_runs_not(env, link, hub, monkeypatch):
    started = []
    def fake_start(rid, run, who, what):
        run['log_name'] = 'run.log'
        monkeypatch.setitem(server._runs, rid, run)
        started.append(run)
    monkeypatch.setattr(server, '_start', fake_start)
    monkeypatch.setattr(server.fill_input, 'write_input', lambda values, path: open(path, 'wb').close())
    r = link.post('/api/runs', headers=H(), json={'project_code': 'P012', 'scalars': {'project_name': 'Khu Thử Nghiệm'}})
    assert r.status_code == 200, r.text
    assert started[-1]['scoped'] == ('P012', ['Khu Thử Nghiệm', 'KTN']) and started[-1]['project_code'] == 'P012'
    r = hub.post('/api/runs', json={'project_code': 'P020', 'scalars': {'project_name': 'Tháp Mây Xanh'}})
    assert r.status_code == 200 and started[-1]['scoped'] is None and started[-1]['project_code'] == 'P020'
    r = hub.post('/api/runs', json={'project_code': 'P777', 'scalars': {'project_name': 'X'}})
    assert r.status_code == 400


def test_scoped_cmd_points_into_mirror(tmp_path, monkeypatch):
    import build_scoped_data
    monkeypatch.setattr(build_scoped_data, 'ensure', lambda code, names, root, log=None: str(tmp_path / 'm'))
    monkeypatch.setattr(build_scoped_data, 'prune', lambda code, root, keep: [])
    run = dict(scoped=('P012', ['Khu Thử Nghiệm']), log=[],
               cmd=['py', '-X', 'utf8', os.path.join(server.HERE, 'run_budget.py'), '--input', 'x'])
    cmd, cwd = server._scoped_cmd(run)
    src = build_scoped_data.source_dir(str(tmp_path / 'm'))
    assert cwd == src and cmd[3] == os.path.join(src, 'webapp', 'run_budget.py') and cmd[4:] == ['--input', 'x']


# ---- old runs get their code once ----------------------------------------------------------------------------------

def test_map_run_codes(env, tmp_path):
    from webapp import map_run_codes
    book = tmp_path / 'quyen.xlsx'
    (env / RUN_OLD / 'web_meta.json').write_text(json.dumps(dict(kind='new', project='KTN', status='done')),
                                                 encoding='utf-8')
    out = tmp_path / 'bang.csv'
    rows = map_run_codes.propose(str(env), str(book), str(out))
    assert [(r['run_id'], r['proposed_code']) for r in rows] == [(RUN_OLD, 'P012')]
    done, skipped = map_run_codes.apply(str(env), str(out), str(book))
    assert done == 1 and not skipped
    assert json.loads((env / RUN_OLD / 'web_meta.json').read_text(encoding='utf-8'))['project_code'] == 'P012'
    assert map_run_codes.apply(str(env), str(out), str(book))[0] == 0      # đã có mã: không ghi lại
    assert any(p.name.startswith('_backup-map-') for p in tmp_path.iterdir())


def test_summary_compare_dropped_and_leaky_summary_held(env, link, monkeypatch):
    monkeypatch.setattr(server, '_leak_words', lambda scope: ['Đồi Gió Hồng'])
    run = server._ensure_run(RUN_A)
    run['summary'] = dict(kind='new', compare=dict(columns=['Dự án này', 'Đồi Gió Hồng']), fund=dict(total=1))
    got = link.get(f'/api/runs/{RUN_A}', headers=H()).json()['summary']
    assert 'compare' not in got and got['fund'] == dict(total=1)
    run['summary'] = dict(kind='new', fund=dict(note='so với Đồi Gió Hồng'))
    got = link.get(f'/api/runs/{RUN_A}', headers=H()).json()['summary']
    assert got['note'] == server.LEAK_HOLD_MESSAGE and 'fund' not in got


def test_unreadable_file_is_held(env, link, monkeypatch):
    monkeypatch.setattr(server, '_leak_words', lambda scope: ['Đồi Gió Hồng'])
    (env / RUN_A / DELIVERABLE_A).write_bytes(b'not a workbook')
    assert link.get(f'/api/runs/{RUN_A}/files/{DELIVERABLE_A}', headers=H()).status_code == 409


def test_history_hides_other_people(env, link, hub):
    assert link.get('/api/history', headers=H()).json()['runs'][0]['user'] == ''
    assert {r['user'] for r in hub.get('/api/history').json()['runs']} == {'x'}


def test_master_spelling_is_kept(tmp_path, monkeypatch):
    import build_scoped_data
    (tmp_path / 'master_list_verified').mkdir()
    (tmp_path / 'master_list_verified' / 'Dim_Property_Residential.csv').write_text(
        'Name,District\nKHU THỬ NGHIỆM,Quận 7\nĐồi Gió Hồng,Quận 1\n', encoding='utf-8')
    monkeypatch.setattr(build_scoped_data, 'DATA_DIR', str(tmp_path))
    assert build_scoped_data.master_names(['Khu Thu Nghiem']) == ['KHU THỬ NGHIỆM']
    assert build_scoped_data.own_names_for(['Khu Thu Nghiem']) == ['KHU THỬ NGHIỆM', 'Khu Thu Nghiem']
    assert build_scoped_data.master_names(['Không có']) == []
