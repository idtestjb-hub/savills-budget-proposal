"""Đăng nhập bằng mã qua email trên link ngoài (change add-link-email-code-login). TEST DATA: email, dự án, file đều giả.

Kiểm: mã hết hạn sau 15 phút, dùng một lần, sai 5 lần bị huỷ, mã mới thay mã cũ; giới hạn theo email, IP, toàn site;
email lạ nhận cùng câu trả lời; cờ cookie; CSRF + Origin trên POST; đăng xuất; người bị gỡ khỏi file phân quyền;
token Cloudflare vẫn dùng được ở chế độ cf+otp; cổng Hub không đổi; kho và log không có mã hay token rõ.
"""
import datetime
import json
import os
import sqlite3

import openpyxl
import pytest

os.environ['BUDGET_WEB_AUTH'] = 'off'
pytest.importorskip('fastapi')
jwt = pytest.importorskip('jwt')
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from webapp import auth, link_login, server  # noqa: E402

LINK = 8091
SECRET = 'test-secret-0123456789-abcdefghijklmnop'
ORIGIN = 'https://power.example.test'
TEAM = 'https://test-team.cloudflareaccess.com'
AUD = 'aud-test-0001'
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
RUN_A = '20261119-100000_Khu-Thu-Nghiem'
RUN_B = '20261119-110000_Thap-May-Xanh'
PM = 'pm.a@example.com'


class Clock:
    def __init__(self):
        self.t = 1_800_000_000.0

    def __call__(self):
        return self.t


# ---- kho (không qua web) ----------------------------------------------------------------------------------------

@pytest.fixture
def store(tmp_path):
    lines = []
    s = link_login.Store(str(tmp_path / 'db' / 'l.sqlite'), SECRET, str(tmp_path / 'outbox'), clock=Clock(),
                         log=lines.append)
    s.lines = lines
    return s


def listed(email):
    return email in {PM, 'boss@example.com'}


def outbox_files(s):
    return sorted(os.listdir(s.outbox)) if os.path.isdir(s.outbox) else []


def last_code(s):
    """Nội dung file yêu cầu duy nhất trong outbox, rồi xoá nó (như flow): mỗi lần xin mã để lại đúng một file."""
    names = outbox_files(s)
    assert len(names) == 1, names
    path = os.path.join(s.outbox, names[0])
    with open(path, encoding='utf-8') as fh:
        body = json.load(fh)
    os.remove(path)
    return body


def other_than(code):
    return '000000' if code != '000000' else '111111'


def test_code_is_six_digits_and_file_has_no_email_in_name(store):
    assert store.request_code(' PM.A@Example.com ', '1.1.1.1', listed) == link_login.SENT
    names = outbox_files(store)
    assert len(names) == 1 and names[0].startswith('otp-') and names[0].endswith('.json')
    assert 'example' not in names[0] and 'pm.a' not in names[0]
    body = last_code(store)
    assert body['to'] == PM and len(body['code']) == 6 and body['code'].isdigit() and body['minutes'] == 15
    assert not any(n.endswith('.tmp') for n in names)


def test_code_works_once(store):
    store.request_code(PM, '', listed)
    code = last_code(store)['code']
    assert store.verify_code(PM, code, '') == link_login.OK
    assert store.verify_code(PM, code, '') == link_login.EXPIRED


def test_code_expires_after_15_minutes(store):
    store.request_code(PM, '', listed)
    code = last_code(store)['code']
    store.clock.t += 15 * 60 - 1
    assert store.verify_code(PM, other_than(code), '') == link_login.WRONG     # còn hạn: mã sai bị đếm
    store.clock.t += 2
    assert store.verify_code(PM, code, '') == link_login.EXPIRED


def test_fifth_wrong_attempt_voids_code(store):
    store.request_code(PM, '', listed)
    code = last_code(store)['code']
    for _ in range(4):
        assert store.verify_code(PM, other_than(code), '') == link_login.WRONG
    assert store.verify_code(PM, code, '') == link_login.OK      # 4 lần sai vẫn còn dùng được
    store.request_code(PM, '', listed)
    code = last_code(store)['code']
    for _ in range(5):
        store.verify_code(PM, other_than(code), '')
    assert store.verify_code(PM, code, '') == link_login.EXPIRED


def test_new_code_replaces_old(store):
    store.request_code(PM, '', listed)
    first = last_code(store)['code']
    store.clock.t += 1
    store.request_code(PM, '', listed)
    second = last_code(store)['code']
    if first != second:
        assert store.verify_code(PM, first, '') == link_login.WRONG
    assert store.verify_code(PM, second, '') == link_login.OK


def test_unknown_email_gets_nothing(store):
    assert store.request_code('stranger@example.com', '1.1.1.1', listed) == link_login.UNKNOWN
    assert store.request_code('not-an-email', '1.1.1.1', listed) == link_login.INVALID
    assert outbox_files(store) == []


def test_email_limits(store):
    for _ in range(3):
        assert store.request_code(PM, '', listed) == link_login.SENT
        store.clock.t += 60
    assert store.request_code(PM, '', listed) == link_login.LIMITED       # 4 mã trong 15 phút
    assert len(outbox_files(store)) == 3
    store.clock.t += 15 * 60
    for _ in range(3):
        assert store.request_code(PM, '', listed) == link_login.SENT
        store.clock.t += 60
    store.clock.t += 9 * 60
    assert store.request_code(PM, '', listed) == link_login.LIMITED       # 7 mã trong 1 giờ
    store.clock.t += 3600
    assert store.request_code(PM, '', listed) == link_login.SENT


def test_ip_limits(store):
    for i in range(20):
        store.request_code(f'nobody{i}@example.com', '9.9.9.9', listed)
    assert store.request_code(PM, '9.9.9.9', listed) == link_login.LIMITED
    assert store.request_code(PM, '8.8.8.8', listed) == link_login.SENT
    for _ in range(30):
        store.verify_code(PM, '000001', '7.7.7.7')
    assert store.verify_code(PM, '000001', '7.7.7.7') == link_login.CHECK_LIMITED


def test_site_limit(store):
    people = [f'p{i}@example.com' for i in range(101)]
    for p in people[:100]:
        assert store.request_code(p, '', lambda e: True) == link_login.SENT
    assert store.request_code(people[100], '', lambda e: True) == link_login.LIMITED
    store.clock.t += 3601
    assert store.request_code(people[100], '', lambda e: True) == link_login.SENT


def test_store_and_log_hold_no_code_or_token(store):
    store.request_code(PM, '1.1.1.1', listed)
    code = last_code(store)['code']
    token, csrf, _ = store.create_session(PM)
    store.verify_code(PM, code, '1.1.1.1')
    db = sqlite3.connect(store.path)
    cells = [str(v) for t in ('codes', 'events', 'sessions') for row in db.execute(f'SELECT * FROM {t}') for v in row]
    db.close()
    assert code not in cells and token not in cells
    assert not any(code in line or token in line for line in store.lines)
    assert any('link-login sent email=pm.a@example.com' in line for line in store.lines)


def test_session_expires_after_12_hours_and_logout(store):
    token, csrf, max_age = store.create_session(PM)
    assert max_age == 12 * 3600 and store.session(token)['email'] == PM
    store.clock.t += 12 * 3600 - 1
    assert store.session(token) is not None
    store.clock.t += 2
    assert store.session(token) is None
    token, _, _ = store.create_session(PM)
    store.logout(token)
    assert store.session(token) is None


def test_short_secret_refused(tmp_path):
    with pytest.raises(ValueError):
        link_login.Store(str(tmp_path / 'x.sqlite'), 'short', str(tmp_path / 'o'))


# ---- web (cổng link, chế độ cf+otp) -----------------------------------------------------------------------------

def _book(path, people=((PM, 'P012'), ('boss@example.com', 'ALL'))):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet('Du an')
    ws.append(['Ma', 'Ten', 'Ten khac'])
    ws.append(['P012', 'Khu Thử Nghiệm', 'KTN'])
    ws.append(['P020', 'Tháp Mây Xanh', ''])
    ws = wb.create_sheet('Nguoi dung')
    ws.append(['Email', 'Ma du an'])
    for row in people:
        ws.append(list(row))
    wb.save(path)


def _run(runs, rid, code, project):
    d = runs / rid
    d.mkdir()
    meta = dict(kind='new', project=project, user='x', started='2026-11-19T10:00:00', finished='2026-11-19T10:01:00',
                status='done', rc=0, project_code=code)
    (d / 'web_meta.json').write_text(json.dumps(meta), encoding='utf-8')
    (d / 'run.log').write_text('ok\n', encoding='utf-8')


@pytest.fixture
def env(tmp_path, monkeypatch):
    runs = tmp_path / 'runs'
    runs.mkdir()
    _run(runs, RUN_A, 'P012', 'Khu Thử Nghiệm')
    _run(runs, RUN_B, 'P020', 'Tháp Mây Xanh')
    book = tmp_path / 'quyen.xlsx'
    _book(book)
    monkeypatch.setattr(server, 'RUNS_DIR', str(runs))
    monkeypatch.setattr(server, 'LINK_PORT', LINK)
    monkeypatch.setattr(server, 'ACCESS_BOOK', str(book))
    monkeypatch.setitem(server._access, 'reader', None)
    monkeypatch.setitem(server._link, 'store', None)
    monkeypatch.setenv('BUDGET_WEB_LINK_AUTH', 'cf+otp')
    monkeypatch.setenv('BUDGET_WEB_LINK_SECRET', SECRET)
    monkeypatch.setenv('BUDGET_WEB_OTP_OUTBOX', str(tmp_path / 'outbox'))
    monkeypatch.setenv('BUDGET_WEB_LINK_DB', str(tmp_path / 'link.sqlite'))
    monkeypatch.setenv('BUDGET_WEB_LINK_PUBLIC_URL', ORIGIN + '/budget/')
    monkeypatch.setenv('BUDGET_WEB_CF_TEAM', 'test-team')
    monkeypatch.setenv('BUDGET_WEB_CF_AUD', AUD)
    monkeypatch.setattr(auth, '_cf_key', lambda tok: KEY.public_key())
    for rid in (RUN_A, RUN_B):
        server._runs.pop(rid, None)
    yield dict(runs=runs, book=book, outbox=tmp_path / 'outbox')
    for rid in (RUN_A, RUN_B):
        server._runs.pop(rid, None)


@pytest.fixture
def link():
    return TestClient(server.app, base_url=f'https://testserver:{LINK}')


@pytest.fixture
def hub():
    return TestClient(server.app)


P = server.PREFIX
O = {'Origin': ORIGIN}


def cf_token(email=PM):
    now = datetime.datetime.now(datetime.timezone.utc)
    claims = dict(email=email, aud=[AUD], iss=TEAM, iat=now, nbf=now, exp=now + datetime.timedelta(minutes=10))
    return jwt.encode(claims, KEY, algorithm='RS256')


def mailed_code(env):
    """Mã trong file yêu cầu duy nhất của outbox, rồi xoá file (như flow)."""
    names = os.listdir(env['outbox'])
    assert len(names) == 1, names
    path = env['outbox'] / names[0]
    code = json.loads(path.read_text(encoding='utf-8'))['code']
    path.unlink()
    return code


def login(link, env, email=PM):
    assert link.post(f'{P}/auth/code/request', json=dict(email=email), headers=O).status_code == 200
    r = link.post(f'{P}/auth/code/verify', json=dict(email=email, code=mailed_code(env)), headers=O)
    assert r.status_code == 200, r.text
    return r


def test_no_login_shows_code_page_and_apis_401(env, link):
    r = link.get(f'{P}/')
    assert r.status_code == 200 and 'Gửi mã' in r.text and '__' not in r.text.replace('__PREFIX', '')
    assert link.get(f'{P}/api/history').status_code == 401


def test_unknown_email_same_answer(env, link):
    a = link.post(f'{P}/auth/code/request', json=dict(email=PM), headers=O)
    b = link.post(f'{P}/auth/code/request', json=dict(email='stranger@example.com'), headers=O)
    assert (a.status_code, a.json()) == (b.status_code, b.json())
    names = os.listdir(env['outbox'])
    assert len(names) == 1
    assert json.loads((env['outbox'] / names[0]).read_text(encoding='utf-8'))['to'] == PM


def test_limited_email_same_answer(env, link):
    answers = {link.post(f'{P}/auth/code/request', json=dict(email=PM), headers=O).text for _ in range(4)}
    assert len(answers) == 1 and len(os.listdir(env['outbox'])) == 3


def test_login_sets_protected_cookie_and_scopes_data(env, link):
    r = login(link, env)
    cookie = r.headers['set-cookie']
    assert cookie.startswith(link_login.COOKIE_NAME + '=')
    low = cookie.lower()
    assert 'httponly' in low and 'secure' in low and 'samesite=lax' in low and 'max-age=43200' in low
    assert f'path={P or "/"}'.lower() in low
    r = link.get(f'{P}/api/history')
    assert r.status_code == 200 and {row['id'] for row in r.json()['runs']} == {RUN_A}
    me = link.get(f'{P}/api/me').json()
    assert me['login'] == 'otp' and me['csrf']
    page = link.get(f'{P}/').text
    assert me['csrf'] in page and 'link-logout' in page


def test_code_reuse_refused_on_web(env, link):
    link.post(f'{P}/auth/code/request', json=dict(email=PM), headers=O)
    code = mailed_code(env)
    assert link.post(f'{P}/auth/code/verify', json=dict(email=PM, code=code), headers=O).status_code == 200
    other = TestClient(server.app, base_url=f'https://testserver:{LINK}')
    assert other.post(f'{P}/auth/code/verify', json=dict(email=PM, code=code), headers=O).status_code == 400


def test_expired_code_refused_on_web(env, link, monkeypatch):
    clock = Clock()
    server.link_store().clock = clock
    link.post(f'{P}/auth/code/request', json=dict(email=PM), headers=O)
    clock.t += 16 * 60
    r = link.post(f'{P}/auth/code/verify', json=dict(email=PM, code=mailed_code(env)), headers=O)
    assert r.status_code == 400 and 'hết hạn' in r.json()['detail']


def test_post_without_csrf_or_wrong_origin_refused(env, link):
    login(link, env)
    csrf = link.get(f'{P}/api/me').json()['csrf']
    before = set(os.listdir(env['runs']))
    body = dict(project_name='Khu Thử Nghiệm', project_code='P012')
    assert link.post(f'{P}/api/runs', json=body, headers=O).status_code == 403
    assert link.post(f'{P}/api/runs', json=body, headers={'Origin': 'https://evil.example',
                                                           'X-CSRF-Token': csrf}).status_code == 403
    assert link.post(f'{P}/api/runs', json=body, headers={'X-CSRF-Token': csrf}).status_code == 403
    assert link.post(f'{P}/api/runs', json=body, headers={**O, 'X-CSRF-Token': 'wrong'}).status_code == 403
    assert set(os.listdir(env['runs'])) == before
    # đúng Origin + đúng token thì qua lớp chặn (route tự kiểm tiếp)
    r = link.post(f'{P}/api/runs/{RUN_B}/print', json=dict(paper='A4'), headers={**O, 'X-CSRF-Token': csrf})
    assert r.status_code == 404      # lượt của dự án khác: 404 từ route, không phải 403 từ lớp chặn


def test_login_steps_need_origin(env, link):
    r = link.post(f'{P}/auth/code/request', json=dict(email=PM))
    assert r.status_code == 403 and not os.path.isdir(env['outbox'])


def test_logout_kills_old_cookie(env, link):
    login(link, env)
    token = link.cookies.get(link_login.COOKIE_NAME)
    csrf = link.get(f'{P}/api/me').json()['csrf']
    r = link.post(f'{P}/auth/code/logout', headers={**O, 'X-CSRF-Token': csrf})
    assert r.status_code == 200 and r.json()['redirect'] == f'{P}/'
    replay = TestClient(server.app, base_url=f'https://testserver:{LINK}')
    replay.cookies.set(link_login.COOKIE_NAME, token)
    assert replay.get(f'{P}/api/history').status_code == 401


def test_person_removed_from_book_is_refused(env, link):
    login(link, env)
    assert link.get(f'{P}/api/history').status_code == 200
    _book(env['book'], people=(('boss@example.com', 'ALL'),))
    server._access['reader'] = None
    assert link.get(f'{P}/api/history').status_code == 403


def test_cloudflare_token_still_works(env, link):
    r = link.get(f'{P}/api/history', headers={auth.CF_TOKEN_HEADER: cf_token()})
    assert r.status_code == 200 and {row['id'] for row in r.json()['runs']} == {RUN_A}
    me = link.get(f'{P}/api/me', headers={auth.CF_TOKEN_HEADER: cf_token()}).json()
    assert me['login'] == 'cf' and me['csrf'] == server.link_store().cf_csrf(PM)
    r = link.post(f'{P}/api/runs/{RUN_B}/print', json=dict(paper='A4'),
                  headers={auth.CF_TOKEN_HEADER: cf_token(), **O, 'X-CSRF-Token': me['csrf']})
    assert r.status_code == 404


def test_bad_cloudflare_token_falls_back_to_code_page(env, link):
    assert link.get(f'{P}/api/history', headers={auth.CF_TOKEN_HEADER: 'garbage'}).status_code == 401
    assert 'Gửi mã' in link.get(f'{P}/', headers={auth.CF_TOKEN_HEADER: 'garbage'}).text


def test_entra_routes_404_on_link(env, link, hub):
    for path in ('/auth/login', '/auth/callback', '/auth/logout'):
        assert link.get(f'{P}{path}', follow_redirects=False).status_code == 404
    assert hub.get(f'{P}/auth/login', follow_redirects=False).status_code in (302, 307)


def test_hub_port_unchanged(env, hub):
    assert hub.post(f'{P}/auth/code/request', json=dict(email=PM)).status_code == 404
    r = hub.get(f'{P}/api/history')
    assert r.status_code == 200 and {row['id'] for row in r.json()['runs']} == {RUN_A, RUN_B}
    assert "const CSRF = ''" in hub.get(f'{P}/').text


def test_cf_mode_has_no_code_login(env, link, monkeypatch):
    monkeypatch.setenv('BUDGET_WEB_LINK_AUTH', 'cf')
    assert link.get(f'{P}/').status_code == 401
    assert link.post(f'{P}/auth/code/request', json=dict(email=PM), headers=O).status_code == 404


def test_link_settings_per_mode(monkeypatch):
    for k in ('BUDGET_WEB_CF_TEAM', 'BUDGET_WEB_CF_AUD', 'BUDGET_WEB_LINK_SECRET', 'BUDGET_WEB_OTP_OUTBOX',
              'BUDGET_WEB_LINK_PUBLIC_URL'):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv('BUDGET_WEB_LINK_PORT', '8091')
    monkeypatch.setenv('BUDGET_WEB_ACCESS_BOOK', 'x.xlsx')
    monkeypatch.setenv('BUDGET_WEB_LINK_AUTH', 'otp')
    missing = ' '.join(auth.missing_link_settings())
    assert 'OTP_OUTBOX' in missing and 'LINK_SECRET' in missing and 'CF_TEAM' not in missing
    monkeypatch.setenv('BUDGET_WEB_LINK_AUTH', 'cf+otp')
    assert 'CF_TEAM' in ' '.join(auth.missing_link_settings())
    monkeypatch.setenv('BUDGET_WEB_LINK_AUTH', 'sms')
    assert 'BUDGET_WEB_LINK_AUTH' in ' '.join(auth.missing_link_settings())
    monkeypatch.setenv('BUDGET_WEB_LINK_AUTH', 'otp')
    monkeypatch.setenv('BUDGET_WEB_LINK_SECRET', SECRET)
    monkeypatch.setenv('BUDGET_WEB_OTP_OUTBOX', 'C:/x')
    monkeypatch.setenv('BUDGET_WEB_LINK_PUBLIC_URL', ORIGIN + '/budget/')
    assert auth.missing_link_settings() == []
    assert auth.link_public_origin() == ORIGIN
