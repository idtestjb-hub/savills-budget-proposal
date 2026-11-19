"""
Trang nhập liệu + nút "Tạo ngân sách" cho Budget Agent (FastAPI).

    cd source_code
    python -m webapp              # xem webapp/__main__.py cho biến môi trường

Hai luồng, cùng một hàng đợi (một lượt tại một thời điểm, vì hai pipeline dùng chung file tạm của lịch trực):
1. Tạo ngân sách (dự án mới), POST api/runs: chép mẫu ..\\reports\\Project_Budget_Input.xlsx sang
   <runs>\\<timestamp>_<tên>\\Project_Budget_Input.xlsx, ghi giá trị form theo nhãn (fill_input.py; file mẫu chỉ
   được đọc), rồi chạy run.py trong tiến trình con với mọi đường dẫn đổi hướng về thư mục lượt (run_budget.py).
2. Review ngân sách dự án đang vận hành, POST api/reviews (multipart): file ngân sách đã duyệt năm ngoái tải lên
   (hoặc bản giao của một lượt cũ, "Gen budget for new year" trên tab Dự án đã tạo) + dữ kiện file không có
   (facts.json) → review.py trong tiến trình con (review_run.py): đổ form Existing project, hai generator cô lập,
   Excel tính lại, sheet Review cuối bản phân tích, review_summary.json.

Cả hai phát log theo thời gian thực (api/runs/<id>) và cho tải 3 file kết quả. Tab Dự án đã tạo (api/history)
liệt kê mọi lượt trong thư mục runs kể cả của phiên server trước (history.py), với Clone (api/runs/<id>/input:
giá trị form của lượt đó) và Gen budget for new year. Thư mục runs mặc định là ..\\reports\\web_runs (bên trong
bản đóng băng trên Hub; BUDGET_WEB_RUNS để đổi).

Tiền tố (BUDGET_WEB_PREFIX, mặc định /budget): reverse proxy chuyển /budget/* về app và BỎ tiền tố, nên app
nhận "/" ; mọi link và fetch trên trang mang tiền tố. Các route được đăng ký hai lần, ở gốc và ở tiền tố, để
mở trực tiếp http://host:port/budget/ (không qua proxy) cũng chạy. GET / trả 200 cho heartbeat.
"""
import contextlib
import datetime
import hmac
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time

from fastapi import APIRouter, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.dirname(HERE)
BUDGET_AGENT = os.path.dirname(SOURCE_DIR)
if SOURCE_DIR not in sys.path:
    sys.path.insert(0, SOURCE_DIR)

from webapp import adjust, auth, facts_prefill, fill_input, history, library, link_login, project_access, results  # noqa: E402,E501
from webapp.project_access import KIND_NONE, KIND_OFFICE, KIND_PROJECT, KIND_VIEWER, Scope  # noqa: E402

HOST = os.environ.get('BUDGET_WEB_HOST') or '127.0.0.1'
PORT = int(os.environ.get('BUDGET_WEB_PORT') or 8090)
PREFIX = ('/' + (os.environ.get('BUDGET_WEB_PREFIX', '/budget') or '').strip('/')).rstrip('/')
RUNS_DIR = os.path.abspath(os.environ.get('BUDGET_WEB_RUNS') or os.path.join(BUDGET_AGENT, 'reports', 'web_runs'))
# Chế độ site (change site-standalone-package): BUDGET_WEB_SITE trỏ tới thư mục site\ của gói đóng cho một dự án
# (site.json + file ngân sách đã duyệt). Trang chỉ còn ba tab, nguồn Review mặc định là file trong gói, không có kho.
SITE_DIR = os.path.abspath(os.environ['BUDGET_WEB_SITE']) if os.environ.get('BUDGET_WEB_SITE') else None
SITE_FILE = 'site.json'
# Link ngoài (change budget-web-project-access): cổng riêng cho tunnel Cloudflare; mọi yêu cầu trên cổng này phải có
# token Cloudflare Access hợp lệ, và người dùng chỉ thấy dự án của mình theo file phân quyền BUDGET_WEB_ACCESS_BOOK.
# Cổng thường (đường Hub, đăng nhập Windows) giữ nguyên như trước.
LINK_PORT = int(os.environ.get('BUDGET_WEB_LINK_PORT') or 0)
ACCESS_BOOK = (os.environ.get('BUDGET_WEB_ACCESS_BOOK') or '').strip()
# Bản chạy ẩn danh theo mã dự án (build_scoped_data.py) cho lượt của người dùng dự án; mặc định cạnh thư mục runs.
SCOPED_ROOT = os.path.abspath(os.environ.get('BUDGET_WEB_SCOPED_ROOT')
                              or os.path.join(os.path.dirname(RUNS_DIR), 'scoped'))


def site_info():
    """Nội dung site.json của gói (project, prior_file, facts, store_id, built_at, code) kèm `prior_exists`; None khi
    không ở chế độ site hoặc file thiếu / hỏng."""
    if not SITE_DIR:
        return None
    try:
        with open(os.path.join(SITE_DIR, SITE_FILE), encoding='utf-8') as fh:
            info = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(info, dict):
        return None
    prior = os.path.join(SITE_DIR, str(info.get('prior_file') or ''))
    info['prior_exists'] = bool(info.get('prior_file')) and os.path.isfile(prior)
    return info


def site_prior_path():
    info = site_info()
    return os.path.join(SITE_DIR, info['prior_file']) if info and info['prior_exists'] else None

_access = {'reader': None}


def access_list():
    """Danh sách phân quyền hiện hành (project_access.AccessList) hoặc None khi chưa đặt file / chưa từng đọc được."""
    if not ACCESS_BOOK:
        return None
    if _access['reader'] is None:
        _access['reader'] = project_access.Reader(ACCESS_BOOK, log=_log)
    return _access['reader'].current()


_lock = threading.Lock()
_runs = {}          # run_id -> dict(kind, status, log, rc, started, finished, workdir, outputs, summary, ...)
_active = {'id': None}

OUTPUT_KINDS = history.OUTPUT_KINDS
_outputs = history.outputs_of          # [{kind, title, name, size, path}]; `path` không ra khỏi server

# Ô dữ kiện của chế độ Review (file ngân sách không có) -> nhãn trên Project Info (review_import.write_form đọc
# facts theo nhãn). Tỉnh / thành phố bắt buộc: biểu giá nước lấy theo đó.
FACT_LABELS = {
    'city': ('City / Province', 'text'),
    'district': ('District', 'text'),
    'tower_count': ('Tower Count', 'number'),
    'floor_count': ('Floor Count', 'number'),
    'gate_count': ('Gate / Entrance Count', 'number'),
    'has_pool': ('Has Swimming Pool?', 'yesno'),
    'pool_area': ('Pool Area', 'number'),
    'pool_volume': ('Pool Volume', 'number'),
    'car_slots': ('Car Parking Slots', 'number'),
    'moto_slots': ('Moto Parking Slots', 'number'),
    'site_area': ('Site Area', 'number'),
    'garden_area': ('Garden / Landscape Area', 'number'),
    'open_space': ('Circulation / Hardscape Area', 'number'),
    # change project-info-everywhere
    'elevators': ('Passenger Elevators per Tower', 'number'),
    'basements': ('Number of Basements', 'number'),
    'pool_count': ('Number of Pools', 'number'),
    'street': ('Street Address', 'text'),
    # change add-sinking-fund: every lift of the project, for the sinking-fund lift lines
    'total_lifts': ('Total Elevators (incl. service)', 'number'),
}
MAX_UPLOAD = 60 * 1024 * 1024


def _log(message):
    print(f'{datetime.datetime.now():%Y-%m-%d %H:%M:%S} budget-web: {message}', flush=True)


def _now():
    return datetime.datetime.now().isoformat(timespec='seconds')


def _worker(run_id):
    run = _runs[run_id]
    log_path = os.path.join(run['workdir'], run.get('log_name') or 'run.log')
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUNBUFFERED='1')
    try:
        cmd, cwd = run['cmd'], SOURCE_DIR
        if run.get('scoped'):
            cmd, cwd = _scoped_cmd(run)
        with open(log_path, 'w', encoding='utf-8') as log_file:
            proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, env=env)
            assert proc.stdout is not None
            for raw in proc.stdout:
                line = raw.decode('utf-8', errors='replace').rstrip('\r\n')
                run['log'].append(line)
                log_file.write(line + '\n')
            rc = proc.wait()
        run['rc'] = rc
        run['outputs'] = _outputs(run['workdir'])
        # Tóm tắt kết quả cho mọi vai trò, kể cả viewer; lỗi chỉ thành note.
        run['summary'] = results.summarize_run(run['workdir'], run['kind'])
        complete = history.is_complete(run['outputs'])
        if run['kind'] == 'adjust':
            ok = rc == 0 and not run['summary'].get('note')
            base = _runs.get(run.get('base_id'))
            if base is not None:
                base['outputs'] = run['outputs']       # bản giao đã ghi đè: cỡ file mới
        elif run['kind'] == 'review':
            # rc 1 = một phép đối chiếu lệch: vẫn có đủ file và sheet Review, trang nói rõ LỆCH.
            ok = rc in (0, 1) and complete and bool(run['summary'].get('summary'))
            meta = run['summary'].get('meta') or {}
            run['project'] = meta.get('project') or run['project']
            run['budget_year'], run['prior_year'] = meta.get('budget_year'), meta.get('prior_year')
        else:
            ok = rc == 0 and complete
        run['status'] = 'done' if ok else 'failed'
        if rc == 0 and not complete:
            run['log'].append('Thiếu file kết quả trong thư mục chạy.')
    except Exception as exc:  # the page must always learn why a run stopped
        run['log'].append(f'Lỗi khi chạy: {type(exc).__name__}: {exc}')
        run['rc'] = -1
        run['status'] = 'failed'
    finally:
        run['finished'] = _now()
        if run['kind'] != 'adjust':        # lượt điều chỉnh nằm trong thư mục của lượt gốc: không đụng web_meta của nó
            history.write_meta(run['workdir'], status=run['status'], rc=run['rc'], finished=run['finished'],
                               project=run.get('project'), budget_year=run.get('budget_year'),
                               prior_year=run.get('prior_year'))
        _log(f'run {run_id} {run["status"]} rc={run["rc"]} outputs={len(run["outputs"])}')
        with _lock:
            _active['id'] = None


# Vai trò do reverse proxy gắn vào yêu cầu (tiêu đề X-Hub-Role). Proxy xoá tiêu đề trình duyệt tự gửi và gắn
# `viewer` cho tài khoản chỉ được xem; owner và yêu cầu từ loopback không có tiêu đề. Viewer chỉ thấy và tải được
# bản giao khách; hai file nội bộ vẫn được sinh đủ trong thư mục chạy, chỉ bị ẩn khỏi danh sách và chặn tải.
ROLE_HEADER = 'X-Hub-Role'
ROLE_VIEWER = 'viewer'
VIEWER_KINDS = {'deliverable', 'deliverable_pdf_a4', 'deliverable_pdf_a3'}   # bản in PDF cũng là bản giao khách
# Người dùng dự án qua link ngoài: bản giao khách (Excel + PDF) và lịch trực; không bao giờ có bản phân tích nội bộ.
ROLE_PROJECT = 'project'
PROJECT_KINDS = VIEWER_KINDS | {'roster'}
ROLE_KINDS = {ROLE_VIEWER: VIEWER_KINDS, ROLE_PROJECT: PROJECT_KINDS}
_INTERNAL_LOG_MARKERS = ('[2/2]', 'generate_project_output', 'Internal analysis', '  analysis ', '  roster ',
                         'phân tích:', "Sheet 'Review'")


def role_of(request):
    """'viewer' khi tiêu đề X-Hub-Role (không phân biệt hoa thường) là viewer; None khi vắng hoặc giá trị khác."""
    value = (request.headers.get(ROLE_HEADER) or '').strip().lower()
    return ROLE_VIEWER if value == ROLE_VIEWER else None


def _strip(outputs):
    return [{k: v for k, v in o.items() if k != 'path'} for o in outputs]


# Gói site (người dùng 09/11/2026): PM ở site không cần bản phân tích nội bộ. File vẫn được sinh trong thư mục lượt
# (sheet Review và bảng điều chỉnh đọc từ đó), chỉ bị ẩn khỏi danh sách và chặn tải; bản giao và lịch trực vẫn tải được.
SITE_HIDDEN_KINDS = {'analysis'}


def visible_outputs(outputs, role, site=None):
    """Danh sách file người có vai trò `role` được thấy: viewer chỉ bản giao khách; trong gói site bỏ bản phân tích
    nội bộ; còn lại đủ 3 file. `site` mặc định theo chế độ của server (SITE_DIR)."""
    if role in ROLE_KINDS:
        return _strip(o for o in outputs if o['kind'] in ROLE_KINDS[role])
    if SITE_DIR if site is None else site:
        return _strip(o for o in outputs if o['kind'] not in SITE_HIDDEN_KINDS)
    return _strip(outputs)


def may_download(run, name, role, site=None):
    """Viewer chỉ tải được file có trong danh sách của mình; trong gói site không tải được bản phân tích nội bộ; ai khác
    tải mọi file trong thư mục chạy."""
    if role in ROLE_KINDS:
        return any(o['name'] == name for o in visible_outputs(run['outputs'], role))
    if SITE_DIR if site is None else site:
        return not any(o['name'] == name and o['kind'] in SITE_HIDDEN_KINDS for o in run['outputs'])
    return True


def visible_log(lines, outputs, role):
    """Log cho viewer: bỏ các dòng nêu tên hoặc đường dẫn của file bị ẩn và tiến trình của bước phân tích nội bộ."""
    if role not in ROLE_KINDS:
        return list(lines)
    hidden = [o['name'] for o in outputs if o['kind'] not in VIEWER_KINDS] + ['Project_Budget_Output.xlsx',
                                                                            'Roster_Demand_Model.xlsx']
    return [ln for ln in lines
            if not any(h in ln for h in hidden) and not any(m in ln for m in _INTERNAL_LOG_MARKERS)]


# Đường dẫn Windows (ổ đĩa hoặc \\máy\chia sẻ) tới hết dấu \ hoặc / cuối cùng. Tên thư mục có thể có dấu cách nhưng không
# có dấu ':', nên hai đường dẫn trên cùng một dòng được bắt riêng; chữ trước ổ đĩa (http:, https:) không bị bắt.
_PATH_DIRS_RE = re.compile(r'(?:(?<![A-Za-z])[A-Za-z]:[\\/]|\\\\[^\\/:*?"<>|\r\n]+[\\/])(?:[^\\/:*?"<>|\r\n]*[\\/])*')


def hide_paths(lines):
    """Log hiện trên trang: bỏ phần thư mục của mọi đường dẫn, chỉ giữ tên file hoặc tên thư mục cuối. run.log trên
    đĩa vẫn giữ đường dẫn đầy đủ để tra lỗi."""
    return [_PATH_DIRS_RE.sub('', ln) for ln in lines]


def _scan_log(lines, role, scope):
    """Người dùng dự án: bỏ dòng log có tên dự án khác (ghi log server); vai trò khác: giữ nguyên."""
    if role != ROLE_PROJECT or scope is None:
        return lines
    words = _leak_words(scope)
    out = []
    for ln in lines:
        hits = _text_hits(ln, words)
        if hits:
            _log(f'log line held back from {scope.email!r}: {len(hits)} name(s)')
            continue
        out.append(ln)
    return out


def _project_summary(summary, scope):
    """Tóm tắt kết quả cho người dùng dự án: bỏ phần so sánh với dự án tham chiếu (lấy từ bản phân tích nội bộ); phần
    còn lại có tên dự án khác thì thay bằng lời nhắn."""
    if not isinstance(summary, dict):
        return summary
    out = {k: v for k, v in summary.items() if k != 'compare'}
    if _text_hits(json.dumps(out, ensure_ascii=False, default=str), _leak_words(scope)):
        _log(f'run summary held back from {scope.email!r}')
        return dict(kind=summary.get('kind'), note=LEAK_HOLD_MESSAGE)
    return out


def _public(run_id, since=0, role=None, scope=None):
    run = _runs[run_id]
    # `since` đếm trên log đầy đủ để trang không nhận trùng dòng; chỉ phần trả về được lọc theo vai trò.
    return dict(id=run_id, kind=run.get('kind', 'new'), project=run.get('project'), source=run.get('source', ''),
                project_code=run.get('project_code') or '',
                status=run['status'], rc=run['rc'], started=run['started'], finished=run['finished'],
                workdir='' if role == ROLE_PROJECT else run['workdir'],
                log=hide_paths(_scan_log(visible_log(run['log'][since:], run['outputs'], role), role, scope)),
                log_total=len(run['log']),
                outputs=visible_outputs(run['outputs'], role),
                summary=_project_summary(run.get('summary'), scope) if role == ROLE_PROJECT and scope else run.get('summary'))


def _ensure_run(run_id):
    """Lượt trong bộ nhớ; lượt của phiên server trước được dựng lại từ thư mục của nó (history.describe)."""
    if run_id in _runs:
        return _runs[run_id]
    if not history.RUN_ID_RE.match(run_id or ''):
        raise HTTPException(404, 'Không có lượt chạy này.')
    workdir = os.path.join(RUNS_DIR, run_id)
    if not os.path.isdir(workdir):
        raise HTTPException(404, 'Không có lượt chạy này.')
    d = history.describe(workdir, run_id)
    run = dict(kind=d['kind'], project=d['project'], project_code=d.get('project_code') or '', source=d['source'],
               status=d['status'], rc=d['rc'],
               started=d['started'], finished=d['finished'], workdir=workdir, input=d['input_form'],
               outputs=d['outputs'], log=history.read_log(workdir),
               summary=results.summarize_run(workdir, d['kind']), budget_year=d['budget_year'],
               prior_year=d['prior_year'], cmd=None)
    _runs[run_id] = run
    return run


def _page(name, **fields):
    with open(os.path.join(HERE, 'static', name), encoding='utf-8') as fh:
        html = fh.read().replace('__PREFIX__', PREFIX)
    for key, value in fields.items():
        html = html.replace(f'__{key}__', value)
    return html


def _escape(text):
    return (str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;'))


def _safe(name, fallback='project'):
    return (re.sub(r'[^A-Za-z0-9]+', '-', str(name)).strip('-') or fallback)[:40]


def _new_run_id(tag):
    return datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '_' + tag


def _who(request, user):
    # X-Hub-User: tên đăng nhập Windows do cổng đăng nhập của Hub chép sang qua Caddy; chỉ để ghi log, không phân quyền.
    return (request.headers.get('X-Hub-User') or '').strip() or user.get('email') or user.get('name') or ''


def on_link(request):
    """Yêu cầu đến qua cổng link ngoài (BUDGET_WEB_LINK_PORT)."""
    server = request.scope.get('server') or (None, None)
    return bool(LINK_PORT) and server[1] == LINK_PORT


_link = {'store': None, 'key': None}


def link_store():
    """Kho mã / phiên của đăng nhập bằng mã (link_login.Store), tạo một lần theo biến môi trường."""
    key = (os.environ.get('BUDGET_WEB_LINK_DB') or os.path.join(os.path.dirname(RUNS_DIR), 'link_login.sqlite'),
           os.environ.get('BUDGET_WEB_LINK_SECRET', '').strip(), os.environ.get('BUDGET_WEB_OTP_OUTBOX', '').strip())
    if _link['store'] is None or _link['key'] != key:
        _link['store'], _link['key'] = link_login.Store(key[0], key[1], key[2], log=_log), key
    return _link['store']


def client_ip(request):
    """IP người dùng theo khả năng (CF-Connecting-IP > X-Forwarded-For > socket). Chỉ dùng cho giới hạn phụ và log;
    trên cổng link mọi yêu cầu đến từ 127.0.0.1 nên không bao giờ dùng để phân quyền."""
    ip = (request.headers.get('CF-Connecting-IP') or '').strip()
    if not ip:
        ip = (request.headers.get('X-Forwarded-For') or '').split(',')[0].strip()
    if not ip and request.client:
        ip = request.client.host or ''
    return ip[:64]


def link_identity(request):
    """(email, 'cf' | 'otp', csrf) của người gọi trên cổng link, hoặc None. Thứ tự (design D1): token Cloudflare hợp lệ
    (khi chế độ có cf), rồi cookie phiên mã (khi chế độ có otp). Tiêu đề X-Hub-* và email trần không bao giờ được tin."""
    if getattr(request.state, 'link_checked', False):
        return request.state.link_identity
    mode, ident = auth.link_mode(), None
    token = request.headers.get(auth.CF_TOKEN_HEADER)
    if auth.link_uses_cf(mode) and (token or not auth.link_uses_otp(mode)):
        try:
            email = auth.verify_cf_token(token)
            ident = (email, 'cf', link_store().cf_csrf(email) if auth.link_uses_otp(mode) else '')
        except auth.CfTokenError as exc:
            _log(f'link token refused ({request.url.path}): {exc}')
    if ident is None and auth.link_uses_otp(mode):
        sess = link_store().session(request.cookies.get(link_login.COOKIE_NAME))
        if sess:
            ident = (sess['email'], 'otp', sess['csrf'])
    request.state.link_checked, request.state.link_identity = True, ident
    return ident


def link_email(request):
    """Email của người gọi trên cổng link; 401 khi chưa đăng nhập. Tiêu đề X-Hub-* bị bỏ qua trên cổng này."""
    ident = link_identity(request)
    if ident is None:
        if auth.link_uses_otp():
            raise HTTPException(401, 'Chưa đăng nhập hoặc phiên đã hết. Tải lại trang để đăng nhập.')
        raise HTTPException(401, 'Chưa đăng nhập qua link của Savills. Mở lại link để đăng nhập.')
    return ident[0]


def scope_of(request):
    """Phạm vi xem của người gọi. Cổng link: theo file phân quyền (không có danh sách = không thấy gì). Cổng Hub:
    viewer khi Hub gắn vai trò viewer, còn lại văn phòng (như trước change này)."""
    if on_link(request):
        email = link_email(request)
        acl = access_list()
        return acl.scope_for(email) if acl is not None else Scope(KIND_NONE, frozenset(), email)
    return Scope(KIND_VIEWER) if role_of(request) == ROLE_VIEWER else Scope(KIND_OFFICE)


def out_role(scope):
    """Vai trò dùng để lọc file và log: 'viewer', 'project' hoặc None (văn phòng)."""
    return {KIND_VIEWER: ROLE_VIEWER, KIND_PROJECT: ROLE_PROJECT}.get(scope.kind)


def current_user(request: Request):
    """Người đang đăng nhập (dict name/email), hoặc None. Chế độ off: một người dùng cục bộ. Cổng link: email trong
    token Cloudflare (401 khi thiếu hoặc sai)."""
    if on_link(request):
        email = link_email(request)
        return dict(name=email, email=email)
    if not auth.enabled():
        return dict(name='máy cá nhân', email='')
    return request.session.get('user')


def require_user(request: Request):
    user = current_user(request)
    if not user:
        raise HTTPException(401, 'Chưa đăng nhập. Tải lại trang để đăng nhập.')
    return user


NO_PROJECT_MESSAGE = ('Email của bạn chưa được gắn dự án nào trên trang Budget. Liên hệ văn phòng (Project Management) '
                      'để được cấp quyền.')


def require_scope(request: Request, user=Depends(require_user)):
    """Phụ thuộc chung của mọi API dữ liệu: người đã đăng nhập và phạm vi xem; không có dự án nào -> 403."""
    scope = scope_of(request)
    if scope.kind == KIND_NONE:
        _log(f'no project for {scope.email!r} ({request.url.path})')
        raise HTTPException(403, NO_PROJECT_MESSAGE)
    return scope


def _run_for(scope, run_id):
    """Lượt `run_id` nếu người gọi được xem; lượt của dự án khác trả 404 như lượt không tồn tại."""
    run = _ensure_run(run_id)
    if not scope.may_see(run.get('project_code') or None):
        _log(f'run {run_id} hidden from {scope.email!r} (code {run.get("project_code")!r})')
        raise HTTPException(404, 'Không có lượt chạy này.')
    return run


def _scoped_cmd(run):
    """Lệnh và thư mục chạy của một lượt người dùng dự án: cùng script, nhưng trong bản mã nguồn có data\\ ẩn danh
    (build_scoped_data.ensure; mọi tên dự án khác thành "Dự án tham chiếu NN", số liệu không đổi)."""
    import build_scoped_data
    code, names = run['scoped']
    run['log'].append('Chuẩn bị dữ liệu tham chiếu ẩn danh cho dự án...')
    if not build_scoped_data.master_names(names):
        run['log'].append('Chú ý: tên dự án trong file phân quyền không khớp tên nào trong danh sách master, nên dữ kiện '
                          'master của dự án không được dùng. Báo văn phòng thêm đúng tên vào cột Ten khac.')
        _log(f'scoped run {code}: no master-list name matches {names!r}')
    mirror = build_scoped_data.ensure(code, names, SCOPED_ROOT, log=_log)
    build_scoped_data.prune(code, SCOPED_ROOT, mirror)
    src = build_scoped_data.source_dir(mirror)
    cmd = list(run['cmd'])
    for i, part in enumerate(cmd):
        if isinstance(part, str) and os.path.normcase(part).startswith(os.path.normcase(HERE + os.sep)):
            cmd[i] = os.path.join(src, 'webapp', os.path.relpath(part, HERE))
    return cmd, src


def _scoped_for(scope, code):
    """(mã, tên của dự án) khi lượt phải chạy trên dữ liệu ẩn danh (người dùng dự án), None khi không."""
    if not scope.is_project:
        return None
    acl = access_list()
    names = acl.names_of(code) if acl is not None else []
    if not names:
        raise HTTPException(403, 'Dự án này chưa có tên trong danh sách phân quyền; liên hệ văn phòng.')
    return (code, names)


# ---- quét lộ tên trước khi trả cho người dùng dự án ----------------------------------------------------------------
_leak_cache = {}            # (path, mtime_ns, size, words key) -> [tên]
_leak_words_cache = {}      # (mã..., dấu) -> (danh sách từ, từ đã có sẵn trong form chuẩn)


def _leak_words(scope):
    """Từ cần quét cho người dùng `scope`: như kiểm tra gói site (site_data.leak_words), trừ tên các dự án của họ.
    Tên đã có sẵn trong form chuẩn 2027 (ghi chú của biểu mẫu, mọi PM đều có) được tách riêng, không chặn."""
    import build_scoped_data
    import site_data
    acl = access_list()
    own = build_scoped_data.own_names_for({n for c in scope.codes for n in (acl.names_of(c) if acl is not None else [])})
    key = (tuple(sorted(scope.codes)), build_scoped_data.stamp(own))
    if key not in _leak_words_cache:
        store = library.store_dir()
        words = site_data.leak_words(build_scoped_data.DATA_DIR, own_names=own,
                                     store_dir=store if store and os.path.isdir(store) else None)
        tpl = _template_text()
        in_tpl = {w for w in words if site_data.norm(w) and site_data.norm(w) in tpl}
        if len(_leak_words_cache) > 64:
            _leak_words_cache.clear()
        _leak_words_cache[key] = ([w for w in words if w not in in_tpl], in_tpl)
    return _leak_words_cache[key][0]


_template_cache = {}


def _template_text():
    """Chữ của form chuẩn 2027 (gấp hoa thường), nhớ theo mtime."""
    import build_scoped_data
    import site_data
    path = build_scoped_data.TEMPLATE
    try:
        mt = os.stat(path).st_mtime_ns
    except OSError:
        return ''
    if _template_cache.get('mt') != mt:
        _template_cache.update(mt=mt, text=site_data.norm(site_data._xlsx_text(path)))
    return _template_cache['text']


def _text_hits(text, words):
    import site_data
    low = site_data.norm(text)
    return [w for w in words if site_data.norm(w) and site_data.norm(w) in low]


def _xlsx_text_strict(path):
    """Mọi chuỗi của một workbook; ném lỗi khi không đọc được (quét cho người dùng dự án không được 'mở khi lỗi')."""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=False)
    try:
        parts = []
        for ws in wb.worksheets:
            parts.append(ws.title)
            for row in ws.iter_rows(values_only=True):
                parts.extend(v for v in row if isinstance(v, str))
        return chr(10).join(parts)
    finally:
        wb.close()


def _file_hits(path, words, run=None):
    """Tên dự án khác trong file `path`. PDF được xét theo bản giao mà nó được in ra (cùng lượt). File không đọc được
    trả về ['(không đọc được để kiểm tra)'] để bị giữ lại."""
    if path.lower().endswith('.pdf'):
        deliverable = next((o['path'] for o in (run or {}).get('outputs', []) if o['kind'] == 'deliverable'), None)
        if not deliverable:
            return ['(không có bản giao để kiểm tra bản in)']
        path = deliverable
    st = os.stat(path)
    key = (os.path.normcase(path), st.st_mtime_ns, st.st_size, len(words))
    if key not in _leak_cache:
        try:
            text = _xlsx_text_strict(path) if path.lower().endswith('.xlsx') else None
        except Exception as exc:  # noqa: BLE001
            _log(f'leak scan could not read {os.path.basename(path)}: {type(exc).__name__}: {exc}')
            text = None
        _leak_cache[key] = ['(không đọc được để kiểm tra)'] if text is None else _text_hits(text, words)
    return _leak_cache[key]


def _guard_json(scope, payload, what):
    """Người dùng dự án: 409 khi dữ liệu trả về (JSON) có tên dự án khác; ghi log server."""
    if not scope.is_project:
        return payload
    hits = _text_hits(json.dumps(payload, ensure_ascii=False, default=str), _leak_words(scope))
    if hits:
        _log(f'{what} held back from {scope.email!r}: {len(hits)} other project name(s)')
        raise HTTPException(409, LEAK_HOLD_MESSAGE)
    return payload


LEAK_HOLD_MESSAGE = 'File này cần văn phòng kiểm tra trước khi tải. Liên hệ văn phòng (Project Management).'


def _project_code_for(scope, code, required):
    """Mã dự án gửi từ form, đã kiểm: người dùng dự án chỉ được mã của mình (403); văn phòng được mã có trong file
    phân quyền hoặc để trống (dự án mới) khi `required` là False."""
    code = (code or '').strip()
    if scope.is_project:
        if not code and len(scope.codes) == 1:
            code = next(iter(scope.codes))
        if code not in scope.codes:
            raise HTTPException(403, 'Bạn không được lập ngân sách cho dự án này.')
        return code
    if not code:
        if required:
            raise HTTPException(400, 'Chưa chọn dự án.')
        return ''
    acl = access_list()
    if acl is not None and code not in acl.projects:
        raise HTTPException(400, f'Mã dự án {code!r} không có trong danh sách dự án.')
    return code


router = APIRouter()


@router.get('/', response_class=HTMLResponse)
def index(request: Request):
    """Trang nhập liệu khi đã đăng nhập; trang đăng nhập (vẫn 200, cho heartbeat) khi chưa. Cổng link: token sai -> 401,
    email chưa có dự án -> trang báo, không có dữ liệu."""
    if on_link(request):
        try:
            scope = scope_of(request)
        except HTTPException as exc:
            if exc.status_code == 401 and auth.link_uses_otp():
                return HTMLResponse(_page('login_code.html', MINUTES=str(link_login.CODE_MINUTES)))
            return HTMLResponse(_page('login.html', MESSAGE=_escape(exc.detail)), status_code=exc.status_code)
        if scope.kind == KIND_NONE:
            return HTMLResponse(_page('login.html', MESSAGE=_escape(NO_PROJECT_MESSAGE)), status_code=403)
        ident = link_identity(request)
        who = _escape(scope.email)
        if ident and auth.link_uses_otp():
            who += ' · <a href="#" id="link-logout">Đăng xuất</a>'
        return _page('index.html', USER=who, SITE='', CSRF=_escape(ident[2] if ident else ''))
    user = current_user(request)
    if not user:
        message = request.session.pop('auth_message', '') if auth.enabled() else ''
        return _page('login.html', MESSAGE=_escape(message))
    who = '' if not auth.enabled() else (
        f'{_escape(user["name"])} · <a href="{PREFIX}/auth/logout">Đăng xuất</a>')
    return _page('index.html', USER=who, SITE='1' if SITE_DIR else '', CSRF='')


def _not_on_link(request: Request):
    """Các route đăng nhập Entra không tồn tại trên cổng link."""
    if on_link(request):
        raise HTTPException(404, 'Not Found')


CODE_SENT_MESSAGE = ('Nếu email này có quyền dùng trang Budget, mã đăng nhập sẽ tới hộp thư trong vài phút '
                     f'(thường 1 đến 5 phút). Mã dùng được {link_login.CODE_MINUTES} phút và chỉ một lần.')


def _otp_route(request):
    if not (on_link(request) and auth.link_uses_otp()):
        raise HTTPException(404, 'Not Found')


async def _fields(request):
    """Trường của form hoặc JSON gửi lên (trang đăng nhập gửi JSON)."""
    if (request.headers.get('content-type') or '').startswith('application/json'):
        try:
            data = await request.json()
        except ValueError:
            data = {}
        return data if isinstance(data, dict) else {}
    return dict(await request.form())


def _is_listed(email):
    acl = access_list()
    return acl is not None and email in acl.people


@router.post('/auth/code/request')
async def code_request(request: Request):
    """Bước 1: xin mã. Mọi kết quả (gửi, email lạ, quá giới hạn, lỗi ghi file) trả cùng một câu, cùng mã 200."""
    _otp_route(request)
    data = await _fields(request)
    link_store().request_code(data.get('email'), client_ip(request), _is_listed)
    return JSONResponse(dict(ok=True, message=CODE_SENT_MESSAGE, minutes=link_login.CODE_MINUTES))


@router.post('/auth/code/verify')
async def code_verify(request: Request):
    """Bước 2: nhập mã. Đúng -> tạo phiên phía server và đặt cookie HttpOnly, Secure, SameSite=Lax."""
    _otp_route(request)
    data = await _fields(request)
    store = link_store()
    email = link_login.normal_email(data.get('email'))
    result = store.verify_code(email, data.get('code'), client_ip(request))
    if result == link_login.CHECK_LIMITED:
        raise HTTPException(429, 'Bạn đã thử quá nhiều lần. Đợi một giờ rồi thử lại.')
    if result == link_login.EXPIRED:
        raise HTTPException(400, 'Mã đã hết hạn, đã dùng hoặc chưa được gửi. Bấm "Gửi lại mã" để nhận mã mới.')
    if result != link_login.OK:
        raise HTTPException(400, f'Mã không đúng. Sai {link_login.MAX_WRONG} lần thì mã bị huỷ, phải xin mã mới.')
    if not _is_listed(email):          # bị gỡ khỏi file phân quyền giữa lúc xin mã và lúc nhập
        raise HTTPException(403, NO_PROJECT_MESSAGE)
    token, _, max_age = store.create_session(email)
    response = JSONResponse(dict(ok=True))
    response.set_cookie(link_login.COOKIE_NAME, token, max_age=max_age, path=PREFIX or '/', secure=True,
                        httponly=True, samesite='lax')
    return response


@router.post('/auth/code/logout')
def code_logout(request: Request):
    """Đăng xuất: xoá phiên phía server (cookie cũ không còn dùng được) và xoá cookie. Người vào bằng Cloudflare được
    chuyển tới trang đăng xuất của Cloudflare Access."""
    _otp_route(request)
    ident = link_identity(request)
    token = request.cookies.get(link_login.COOKIE_NAME)
    link_store().logout(token)
    if ident:
        _log(f'link-login logout email={ident[0]} ip={client_ip(request) or "-"}')
    redirect = '/cdn-cgi/access/logout' if ident and ident[1] == 'cf' else (PREFIX or '') + '/'
    response = JSONResponse(dict(ok=True, redirect=redirect))
    response.delete_cookie(link_login.COOKIE_NAME, path=PREFIX or '/', secure=True, httponly=True, samesite='lax')
    return response


@router.get('/auth/login', dependencies=[Depends(_not_on_link)])
def auth_login(request: Request):
    if not auth.enabled():
        return RedirectResponse(PREFIX + '/', status_code=302)
    try:
        flow = auth.begin_login()
    except Exception as exc:  # tenant sai, mất mạng tới Microsoft...: nói trên trang thay vì lỗi 500
        _log(f'login could not start: {type(exc).__name__}: {exc}')
        request.session['auth_message'] = f'Không kết nối được dịch vụ đăng nhập Microsoft: {exc}'
        return RedirectResponse(PREFIX + '/', status_code=302)
    request.session['auth_flow'] = flow
    return RedirectResponse(flow['auth_uri'], status_code=302)


@router.get('/auth/callback', dependencies=[Depends(_not_on_link)])
def auth_callback(request: Request):
    if not auth.enabled():
        return RedirectResponse(PREFIX + '/', status_code=302)
    flow = request.session.pop('auth_flow', None)
    if not flow:
        request.session['auth_message'] = 'Phiên đăng nhập không hợp lệ hoặc đã hết hạn. Bấm đăng nhập lại.'
        return RedirectResponse(PREFIX + '/', status_code=302)
    try:
        claims = auth.finish_login(flow, request.query_params)
    except ValueError as exc:
        _log(f'login failed: {exc}')
        request.session['auth_message'] = f'Đăng nhập không thành công: {exc}'
        return RedirectResponse(PREFIX + '/', status_code=302)
    email, name, _ = auth.identity_of(claims)
    if not auth.is_allowed(claims):
        _log(f'login refused: {email!r} is not in BUDGET_WEB_ALLOWED_USERS')
        request.session['auth_message'] = (
            f'Tài khoản {email or "(không rõ)"} chưa được cấp quyền dùng trang này. '
            'Liên hệ người quản trị Budget Agent để được thêm vào danh sách.')
        return RedirectResponse(PREFIX + '/', status_code=302)
    request.session['user'] = dict(name=name, email=email)
    _log(f'login ok: {email}')
    return RedirectResponse(PREFIX + '/', status_code=302)


@router.get('/auth/logout', dependencies=[Depends(_not_on_link)])
def auth_logout(request: Request):
    request.session.clear()
    if not auth.enabled():
        return RedirectResponse(PREFIX + '/', status_code=302)
    return RedirectResponse(auth.logout_url(), status_code=302)


@router.get('/api/defaults')
def defaults(scope=Depends(require_scope)):
    data = fill_input.read_defaults()
    data['template'] = '' if scope.is_project else fill_input.TEMPLATE_INPUT
    data['runs_dir'] = '' if scope.is_project else RUNS_DIR
    return JSONResponse(data)


@router.get('/api/me')
def get_me(request: Request, scope=Depends(require_scope)):
    """Người đang xem: kind (office / viewer / project), các dự án được chọn trên form (mã + tên), email."""
    acl = access_list()
    projects = []
    if acl is not None:
        codes = sorted(scope.codes) if scope.is_project else sorted(acl.projects)
        projects = [dict(code=c, name=(acl.projects.get(c) or {}).get('name') or c) for c in codes]
    ident = link_identity(request) if on_link(request) else None
    return JSONResponse(dict(kind=scope.kind, email=scope.email, projects=projects, link=on_link(request),
                             may_add_project=not scope.is_project, login=ident[1] if ident else '',
                             csrf=ident[2] if ident else ''))


def _start(run_id, run, who, what):
    """Ghi lượt vào bộ nhớ + web_meta.json và chạy tiến trình con. Gọi khi đang giữ _lock."""
    _runs[run_id] = run
    _active['id'] = run_id
    if run['kind'] != 'adjust':
        history.write_meta(run['workdir'], kind=run['kind'], project=run.get('project'), user=who,
                           project_code=run.get('project_code') or '',
                           started=run['started'], status='running', source=run.get('source', ''),
                           facts=run.get('facts'))
    _log(f'run {run_id} started {what} by {who}')
    threading.Thread(target=_worker, args=(run_id,), daemon=True).start()


def _failed_before_start(workdir, kind, project, who, started, exc):
    """A run whose folder exists but whose subprocess never started: web_meta.json says failed and why, so History shows
    the reason (change log-review-runs). Returns the HTTPException for the page: the same one, or a 500 with a message."""
    detail = exc.detail if isinstance(exc, HTTPException) else f'Không chuẩn bị được lượt chạy: {type(exc).__name__}: {exc}'
    try:
        history.write_meta(workdir, kind=kind, project=project, user=who, started=started, finished=_now(),
                           status='failed', rc=None, error=str(detail))
    except OSError:
        pass
    _log(f'run {os.path.basename(workdir)} failed before start: {detail}')
    return exc if isinstance(exc, HTTPException) else HTTPException(500, detail)


@router.post('/api/runs')
def start_run(request: Request, values: dict, user=Depends(require_user), scope=Depends(require_scope)):
    # Gói site có kèm ngân sách đã duyệt chỉ chạy Review; gói không kèm (dựng không có --prior) lập được dự án mới
    # (change site-package-new-project-entry).
    if SITE_DIR and (site_info() or {}).get('prior_file'):
        raise HTTPException(403, 'Gói này lập ngân sách từ ngân sách đã duyệt của dự án: dùng tab Review.')
    code = _project_code_for(scope, str(values.get('project_code') or ''), required=False)
    scoped = _scoped_for(scope, code)
    with _lock:
        if _active['id']:
            raise HTTPException(409, 'Đang có một lượt chạy. Chờ xong rồi bấm lại.')
        name = str(values.get('scalars', {}).get('project_name') or '').strip()
        if not name:
            raise HTTPException(400, 'Tên dự án không được để trống.')
        run_id = _new_run_id(_safe(name))
        workdir = os.path.join(RUNS_DIR, run_id)
        os.makedirs(workdir, exist_ok=True)
        input_path = os.path.join(workdir, 'Project_Budget_Input.xlsx')
        started = _now()
        try:
            fill_input.write_input(values, input_path)
        except Exception as exc:
            raise _failed_before_start(workdir, 'new', name, _who(request, user), started,
                                       HTTPException(400, f'Không ghi được file nhập liệu: {exc}'))
        cmd = [sys.executable, '-X', 'utf8', os.path.join(HERE, 'run_budget.py'),
               '--input', input_path, '--workdir', workdir]
        run = dict(kind='new', project=name, project_code=code, source='', status='running', rc=None,
                   log=[f'Thư mục chạy: {workdir}'], scoped=scoped,
                   started=started, finished=None, workdir=workdir, input=input_path, outputs=[], summary=None, cmd=cmd)
        _start(run_id, run, _who(request, user), f'for project {name!r}')
    return _public(run_id, role=out_role(scope), scope=scope)


def _facts_from_form(raw):
    """{'city': ..., 'tower_count': ...} từ trang -> {nhãn Project Info: giá trị, '_sources': {...}}. Ô trống bị bỏ
    (review_import ghi 0 và liệt kê 'để trống, PM điền'). Tỉnh / thành phố bắt buộc."""
    facts, sources = {}, {}
    for key, (label, kind) in FACT_LABELS.items():
        value = raw.get(key)
        if value is None or not str(value).strip():
            continue
        if kind == 'number':
            try:
                value = fill_input._to_number(value)
            except ValueError:
                raise HTTPException(400, f'Ô {label} phải là số.')
        elif kind == 'yesno':
            value = 'Yes' if str(value).strip().lower() in ('yes', 'có', 'co', 'true', '1') else 'No'
        else:
            value = str(value).strip()
        facts[label] = value
        sources[label] = 'nhập trên trang web'
    if not facts.get('City / Province'):
        raise HTTPException(400, 'Tỉnh / thành phố không được để trống: biểu giá nước lấy theo đó.')
    facts['_sources'] = sources
    return facts


def _mark_package_facts(fact_map, raw):
    """Trong gói site: ô trang giữ nguyên giá trị đóng trong gói thì nguồn là 'dữ kiện đóng trong gói' (change
    project-info-everywhere); ô PM đã sửa vẫn là 'nhập trên trang web'."""
    info = site_info()
    if not info:
        return
    packed = info.get('facts') or {}
    for key, (label, _kind) in FACT_LABELS.items():
        if key in packed and label in fact_map and str(raw.get(key, '')).strip() == str(packed[key]).strip():
            fact_map['_sources'][label] = 'dữ kiện đóng trong gói'
    # Ô văn phòng cố ý để trống khi đóng gói (site.json blank_facts, build_site_package --blank-fact): PM không nhập thì
    # Review cũng không lấy số master (facts_prefill.master_fallback).
    blank = [FACT_LABELS[k][0] for k in info.get('blank_facts') or () if k in FACT_LABELS]
    blank = [label for label in blank if label not in fact_map]
    if blank:
        fact_map['_no_master'] = blank


@router.post('/api/reviews')
async def start_review(request: Request, prior: UploadFile | None = File(None), source_run: str = Form(''),
                       library_id: str = Form(''), facts: str = Form('{}'), site: str = Form(''),
                       project_code: str = Form(''), user=Depends(require_user), scope=Depends(require_scope)):
    """Lượt review, ngân sách năm ngoái lấy từ một trong bốn nguồn: `site=1` (file đóng trong gói site, chép một bản vào
    thư mục prior của lượt), `library_id` (dự án có sẵn trong kho, file sống trên SharePoint, chép một bản vào thư mục
    prior của lượt), `source_run` (bản giao của lượt cũ, Excel tính lại trước khi đọc), hoặc `prior` (file .xlsx tải
    lên). `facts` là JSON các ô dữ kiện của trang."""
    # Quyền trước mọi kiểm tra khác (change budget-web-project-access): nguồn của dự án khác -> 404, mã dự án không
    # phải của mình -> 403, kể cả khi phần dữ kiện gửi lên còn thiếu.
    # Văn phòng giữ đúng thứ tự kiểm tra cũ.
    if scope.is_project and (library_id or '').strip():
        _entry = library.find(library_id.strip())
        if _entry is None or not scope.may_see(_library_code(_entry)):
            raise HTTPException(404, 'Không có dự án này trong danh sách có sẵn.')
    elif scope.is_project and (source_run or '').strip():
        _run_for(scope, source_run.strip())
    elif scope.is_project:
        _project_code_for(scope, project_code, required=False)
    try:
        raw = json.loads(facts or '{}')
        if not isinstance(raw, dict):
            raise ValueError
    except ValueError:
        raise HTTPException(400, 'Dữ kiện gửi lên không đúng dạng.')
    fact_map = _facts_from_form(raw)
    _mark_package_facts(fact_map, raw)
    source_run, library_id = (source_run or '').strip(), (library_id or '').strip()
    upload, copy_from = None, None
    code = None                     # mã dự án của lượt; nguồn kho / lượt cũ quyết định mã khi có
    if (site or '').strip() in ('1', 'true', 'yes'):
        info = site_info()
        if not SITE_DIR or info is None:
            raise HTTPException(400, 'Trang này không chạy ở chế độ gói site.')
        if not info['prior_exists']:
            raise HTTPException(400, f"Gói không có file ngân sách đã duyệt {info.get('prior_file') or ''!r} trong thư mục site.")
        copy_from, recalc = site_prior_path(), False
        stem = os.path.splitext(info['prior_file'])[0]
        project = str(info.get('project') or stem)
        tag = 'review-' + _safe(project, 'du-an')
        source, what = f"ngân sách đã duyệt của dự án {project} ({info['prior_file']})", 'from site package'
        prior_src = None
    elif library_id:
        entry = library.find(library_id)
        if entry is None or not scope.may_see(_library_code(entry)):
            raise HTTPException(404, 'Không có dự án này trong danh sách có sẵn.')
        code = _library_code(entry) or None
        if not entry['selectable']:
            raise HTTPException(400, f"Không dùng được file này: {entry['reason']}.")
        stem, recalc, copy_from = os.path.splitext(entry['file_name'])[0], False, entry['path']
        tag = 'review-' + _safe(entry['project'], 'du-an')
        source, what = f"dự án có sẵn {entry['project']} ({entry['file_name']})", f'from library {library_id}'
        project = entry['project']
        prior_src = None
    elif source_run:
        src = _run_for(scope, source_run)
        code = src.get('project_code') or None
        deliverable = next((o for o in src['outputs'] if o['kind'] == 'deliverable'), None)
        if not deliverable:
            raise HTTPException(400, f'Lượt {source_run} không có bản giao để lấy làm ngân sách năm ngoái.')
        prior_src, recalc, stem = deliverable['path'], True, ''
        tag, source, what = 'review-' + _safe(src.get('project') or source_run), f'lượt {source_run}', f'from run {source_run}'
        project = src.get('project') or ''
    else:
        if prior is None or not prior.filename:
            raise HTTPException(400, 'Chưa chọn file ngân sách đã duyệt (.xlsx).')
        if not prior.filename.lower().endswith('.xlsx'):
            raise HTTPException(400, 'File ngân sách đã duyệt phải là .xlsx trên form Savills (PDF, xlsb không đọc được).')
        upload = await prior.read()
        if len(upload) > MAX_UPLOAD:
            raise HTTPException(400, 'File lớn hơn 60 MB.')
        stem = os.path.splitext(os.path.basename(prior.filename))[0]
        prior_src, recalc = None, False
        tag, source, what = 'review-' + _safe(stem, 'file'), f'file {os.path.basename(prior.filename)}', f'from file {prior.filename!r}'
        project = ''
    if code is None:
        code = _project_code_for(scope, project_code, required=False)
    elif (project_code or '').strip() and project_code.strip() != code and scope.is_project:
        raise HTTPException(403, 'Bạn không được lập ngân sách cho dự án này.')
    scoped = _scoped_for(scope, code)
    with _lock:
        if _active['id']:
            raise HTTPException(409, 'Đang có một lượt chạy. Chờ xong rồi bấm lại.')
        run_id = _new_run_id(tag)
        workdir = os.path.join(RUNS_DIR, run_id)
        os.makedirs(os.path.join(workdir, 'prior'), exist_ok=True)
        started = _now()
        facts_path = os.path.join(workdir, 'facts.json')
        try:
            if copy_from is not None:      # bản chụp của file sống (kho) hoặc file trong gói: lượt chạy lại sau vẫn ra cùng số
                prior_src = os.path.join(workdir, 'prior', _safe(stem, 'approved') + '.xlsx')
                shutil.copy2(library.long_path(copy_from), prior_src)
            if upload is not None:
                prior_src = os.path.join(workdir, 'prior', _safe(stem, 'approved') + '.xlsx')
                with open(prior_src, 'wb') as fh:
                    fh.write(upload)
            with open(facts_path, 'w', encoding='utf-8') as fh:
                json.dump(fact_map, fh, ensure_ascii=False, indent=1)
        except Exception as exc:
            raise _failed_before_start(workdir, 'review', project, _who(request, user), started, exc)
        cmd = [sys.executable, '-X', 'utf8', os.path.join(HERE, 'review_run.py'),
               '--prior', prior_src, '--facts', facts_path, '--workdir', workdir] + (['--recalc'] if recalc else [])
        run = dict(kind='review', project=project, project_code=code, source=source, status='running', rc=None,
                   scoped=scoped,
                   log=[f'Thư mục chạy: {workdir}', f'Ngân sách năm ngoái: {source}'], started=started, finished=None,
                   workdir=workdir, input=None, outputs=[], summary=None, cmd=cmd, facts=raw)
        _start(run_id, run, _who(request, user), what)
    return _public(run_id, role=out_role(scope), scope=scope)


@router.get('/api/runs/{run_id}')
def get_run(request: Request, run_id: str, since: int = 0, scope=Depends(require_scope)):
    _run_for(scope, run_id)
    return _public(run_id, since, out_role(scope), scope)


@router.get('/api/runs/{run_id}/input')
def get_run_input(request: Request, run_id: str, scope=Depends(require_scope)):
    """Giá trị form của lượt đó (Clone, và dữ kiện cho Gen budget for new year), đọc theo nhãn như api/defaults."""
    run = _run_for(scope, run_id)
    path = run.get('input') or history.input_form_of(run['workdir'], run.get('kind', 'new'))
    if not path or not os.path.isfile(path):
        raise HTTPException(404, 'Lượt này không còn file nhập liệu.')
    try:
        data = fill_input.read_defaults(path)
    except Exception as exc:
        raise HTTPException(400, f'Không đọc được form của lượt: {exc}')
    data['id'] = run_id
    data['kind'] = run.get('kind', 'new')
    data['project'] = run.get('project')
    data['project_code'] = run.get('project_code') or ''
    return JSONResponse(_guard_json(scope, data, f'input of {run_id}'))


@router.get('/api/runs/{run_id}/files/{name}')
def get_file(request: Request, run_id: str, name: str, scope=Depends(require_scope)):
    run = _run_for(scope, run_id)
    if os.sep in name or '/' in name or '..' in name:
        raise HTTPException(400, 'Tên file không hợp lệ.')
    role = out_role(scope)
    if not may_download(run, name, role):
        _log(f'download refused for {role}: {run_id}/{name}')
        if role == ROLE_PROJECT:
            raise HTTPException(404, 'File không tồn tại.')
        raise HTTPException(403, 'Tài khoản của bạn chỉ được tải bản giao khách.')
    known = next((o['path'] for o in run['outputs'] if o['name'] == name), None)
    path = known or os.path.join(run['workdir'], name)
    if not os.path.isfile(path):
        raise HTTPException(404, 'File không tồn tại.')
    if role == ROLE_PROJECT:
        hits = _file_hits(path, _leak_words(scope), run)
        if hits:
            _log(f'download held back: {run_id}/{name} for {scope.email!r}: {len(hits)} other project name(s): {hits[:5]}')
            raise HTTPException(409, LEAK_HOLD_MESSAGE)
    media = ('application/pdf' if name.lower().endswith('.pdf')
             else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    return FileResponse(path, filename=name, media_type=media)


PRINT_TIMEOUT_S = 300


@router.post('/api/runs/{run_id}/print')
def print_pdf(request: Request, run_id: str, body: dict, user=Depends(require_user), scope=Depends(require_scope)):
    """Xuất PDF A4 (X:AO) hoặc A3 (X:BB) sheet '2. Budget-Management Fund' của bản giao hiện tại, kể cả điều chỉnh đã
    lưu (change add-budget-print-layout). Excel làm trên bản sao trong một tiến trình riêng; bản giao không đổi.
    Mọi vai trò tải được bản giao đều xuất được."""
    paper = str((body or {}).get('paper') or '').strip().upper()
    if paper not in ('A4', 'A3'):
        raise HTTPException(400, 'Chọn khổ giấy A4 hoặc A3.')
    run = _run_for(scope, run_id)
    if run.get('status') == 'running':
        raise HTTPException(409, 'Lượt này đang chạy.')
    path = next((o['path'] for o in run['outputs'] if o['kind'] == 'deliverable'), None)
    if not path:
        raise HTTPException(404, 'Lượt này không có bản giao để in.')
    import print_layout
    out = os.path.join(os.path.dirname(path), print_layout.pdf_name(path, paper))
    with _lock:
        if _active['id']:
            raise HTTPException(409, 'Đang có một lượt chạy. Chờ xong rồi bấm lại.')
        _active['id'] = f'{run_id}__print-{paper}'
    try:
        cmd = [sys.executable, '-X', 'utf8', os.path.join(HERE, 'print_run.py'), '--deliverable', path,
               '--paper', paper, '--out', out]
        env = dict(os.environ, PYTHONIOENCODING='utf-8')
        try:
            proc = subprocess.run(cmd, cwd=SOURCE_DIR, capture_output=True, timeout=PRINT_TIMEOUT_S, env=env)
        except subprocess.TimeoutExpired:
            raise HTTPException(504, 'Excel xuất PDF quá lâu. Thử lại sau; bản giao không bị thay đổi.')
        lines = proc.stdout.decode('utf-8', errors='replace').splitlines()
        if proc.returncode != 0 or not os.path.isfile(out):
            stopped = next((ln[len('STOPPED: '):] for ln in reversed(lines) if ln.startswith('STOPPED: ')), None)
            _log(f'print {run_id} {paper} failed rc={proc.returncode}')
            raise HTTPException(400, stopped or 'Không xuất được PDF. Bản giao không bị thay đổi.')
        run['outputs'] = _outputs(run['workdir'])
        _log(f'print {run_id} {paper} -> {os.path.basename(out)} by {_who(request, user)}')
        return JSONResponse(dict(pdf=os.path.basename(out), message=lines[-1] if lines else '',
                                 outputs=visible_outputs(run['outputs'], out_role(scope))))
    finally:
        with _lock:
            _active['id'] = None


def _deliverable_of(run):
    found = next((o for o in run['outputs'] if o['kind'] == 'deliverable'), None)
    if not found:
        raise HTTPException(404, 'Lượt này không có bản giao để điều chỉnh.')
    return found['path']


@router.get('/api/runs/{run_id}/adjust')
def get_adjust(request: Request, run_id: str, scope=Depends(require_scope)):
    """Các mã trên sheet '4. Điều chỉnh' của bản giao (giá trị nhập hiện tại), số duyệt năm cũ khi là lượt review,
    và kết quả lần lưu gần nhất."""
    run = _run_for(scope, run_id)
    path = _deliverable_of(run)
    try:
        items = adjust.read_items(path)
    except adjust.AdjustError as exc:
        raise HTTPException(400, str(exc))
    try:
        adjust.add_groups(items)                     # nhóm của form 2027 như sheet Review; thiếu template thì bảng không chia nhóm
    except Exception:  # noqa: BLE001
        pass
    analysis = next((o['path'] for o in run['outputs'] if o['kind'] == 'analysis'), None)
    cols, years = {}, (None, None)
    if run.get('kind') == 'review' and analysis:
        cols = adjust.review_columns(analysis)
        years = adjust.review_years(analysis)
    approved = cols.get('approved') or {}
    if run.get('kind') == 'review':                                           # quỹ bảo trì: số duyệt từ review_summary.json
        approved = {**approved, **adjust.sf_approved(run['workdir'])}
    top_keys = adjust.top_keys(run['workdir']) if approved else []            # 10 dòng lệch lớn nhất của lượt review
    measures = {k: cols.get(k) or {} for k in ('n1', 'actual', 'expected')}   # cột năm trước có trong file (nếu có)
    for it in items:
        it['approved'] = approved.get(it['key'])
        for k, by_key in measures.items():
            if by_key:
                it[k] = by_key.get(it['key'])
    abnormal_keys = []                                                        # dòng bất thường (change flag-abnormal-review-diffs)
    if approved:
        abnormal_keys = adjust.abnormal_keys(run['workdir'])
        if abnormal_keys is None:                                             # lượt cũ, file tóm tắt chưa có danh sách
            abnormal_keys = adjust.flag_abnormal(items)
    return JSONResponse(_guard_json(scope, dict(id=run_id, kind=run.get('kind', 'new'), project=run.get('project'),
                             deliverable=os.path.basename(path), items=items, has_approved=bool(approved), top_keys=top_keys,
                             abnormal_keys=abnormal_keys, abnormal_rule=adjust.abnormal_rule(),
                             measure_labels={k: v for k, v in (cols.get('labels') or {}).items() if measures.get(k)},
                             prior_year=years[0], budget_year=years[1],
                             period=adjust.period_labels(path, run['workdir']),   # 'MM/YYYY' x 12, danh sách Tháng đầu
                             last=results.adjust_result(run['workdir']) or None,
                             can_save=scope.kind != KIND_VIEWER, active=_active['id']), f'adjust table of {run_id}'))


@router.post('/api/runs/{run_id}/adjust')
def start_adjust(request: Request, run_id: str, body: dict, user=Depends(require_user), scope=Depends(require_scope)):
    """Ghi đè bản giao của lượt bằng các chỉnh sửa (backup có ngày bên cạnh), rồi Excel tính lại. Chạy như một lượt
    trong hàng đợi chung; trang theo dõi bằng api/runs/<id trả về>."""
    base = _run_for(scope, run_id)
    if scope.kind == KIND_VIEWER:
        raise HTTPException(403, 'Tài khoản chỉ xem không được lưu điều chỉnh.')
    if base.get('status') == 'running':
        raise HTTPException(409, 'Lượt này đang chạy.')
    edits = body.get('edits')
    if not isinstance(edits, list) or not edits:
        raise HTTPException(400, 'Chưa có mã nào được điều chỉnh.')
    path = _deliverable_of(base)
    try:                                   # kiểm tra trước, để lỗi nhập hiện ngay thay vì trong log
        import openpyxl
        wb = openpyxl.load_workbook(path)
        try:
            adjust.apply_edits(wb, edits)
        finally:
            wb.close()
    except adjust.AdjustError as exc:
        raise HTTPException(400, str(exc))
    with _lock:
        if _active['id']:
            raise HTTPException(409, 'Đang có một lượt chạy. Chờ xong rồi bấm lại.')
        workdir = base['workdir']
        job_id = f'{run_id}__adjust-{datetime.datetime.now():%H%M%S}'
        edits_path = os.path.join(workdir, 'adjust_edits.json')
        with open(edits_path, 'w', encoding='utf-8') as fh:
            json.dump(edits, fh, ensure_ascii=False, indent=1)
        cmd = [sys.executable, '-X', 'utf8', os.path.join(HERE, 'adjust_run.py'), '--deliverable', path,
               '--edits', edits_path, '--workdir', workdir]
        baseline = os.path.join(workdir, 'deliverable_recalc.xlsx')
        if os.path.exists(baseline):
            cmd += ['--baseline-recalc', baseline]
        run = dict(kind='adjust', base_id=run_id, project=base.get('project'), project_code=base.get('project_code') or '',
                   source=f'điều chỉnh lượt {run_id}',
                   status='running', rc=None, log=[f'Điều chỉnh bản giao của lượt {run_id}: {len(edits)} mã'],
                   started=_now(), finished=None, workdir=workdir, input=None, outputs=base['outputs'], summary=None,
                   cmd=cmd, log_name='adjust.log')
        _start(job_id, run, _who(request, user), f'adjust of {run_id} ({len(edits)} codes)')
    return _public(job_id, role=out_role(scope), scope=scope)


@router.get('/api/site')
def get_site(scope=Depends(require_scope)):
    """Chế độ gói site: dự án, tên file ngân sách đã duyệt, dữ kiện điền sẵn (không có đường dẫn). 404 ngoài chế độ site."""
    info = site_info()
    if info is None:
        raise HTTPException(404, 'Trang này không chạy ở chế độ gói site.')
    return JSONResponse({k: v for k, v in info.items() if k in ('project', 'prior_file', 'facts', 'fact_notes',
                                                                 'store_id', 'built_at', 'code', 'prior_exists')})


def _library_code(entry):
    """Mã dự án của một dòng kho: khớp tên dự án đọc trong file với tên / tên khác trong file phân quyền; '' khi không
    khớp hoặc chưa có danh sách (khi đó người dùng dự án không thấy dòng đó)."""
    acl = access_list()
    return (acl.match(entry.get('project')) if acl is not None else None) or ''


@router.get('/api/library')
def get_library(scope=Depends(require_scope)):
    """Ngân sách đã duyệt có sẵn (kho quét) cho tab Review; không trả đường dẫn. Chế độ gói site: danh sách rỗng, kể
    cả khi máy dựng gói có kho ở đường dẫn mặc định."""
    if SITE_DIR:
        return JSONResponse(dict(entries=[], total=0, selectable=0, root='', store=''))
    rows = [{k: v for k, v in e.items() if k != 'path'} for e in library.entries()
            if not scope.is_project or scope.may_see(_library_code(e))]
    hide = scope.is_project
    return JSONResponse(dict(entries=rows, total=len(rows), selectable=sum(e['selectable'] for e in rows),
                             root='' if hide else library.root_dir(), store='' if hide else library.store_dir()))


@router.get('/api/library/{file_id}/facts')
def get_library_facts(file_id: str, scope=Depends(require_scope)):
    """Dữ kiện điền sẵn cho mục 2 của tab Review khi chọn một dòng kho (change prefill-review-facts): lượt trước cùng
    dự án > sheet 0. Info > danh sách master, mỗi ô kèm nguồn và số khác của nguồn sau."""
    if SITE_DIR:
        raise HTTPException(404, 'Gói site không có kho.')
    entry = library.find(file_id)
    if entry is None or not scope.may_see(_library_code(entry)):
        raise HTTPException(404, 'Không thấy dòng này trong kho.')
    entry = dict(entry, path=library.long_path(entry['path']) if entry.get('selectable') else '')
    runs = [e for e in history.scan(RUNS_DIR) if scope.may_see(e.get('project_code') or None)]
    return JSONResponse(facts_prefill.prefill(entry, runs))


@router.get('/api/library/overview')
def get_library_overview(scope=Depends(require_scope)):
    """Số tổng hợp của kho (tab Kho ngân sách): theo năm, nhóm, lý do, loại file. Chỉ có số đếm, không có tên hay đường dẫn.
    Người dùng dự án không có tab này."""
    if SITE_DIR or scope.is_project:
        raise HTTPException(404, 'Gói site không có kho.')
    return JSONResponse(library.overview())


@router.get('/api/history')
def get_history(request: Request, scope=Depends(require_scope)):
    """Mọi lượt trong thư mục runs mà người gọi được xem, mới nhất trước; file theo vai trò (viewer chỉ bản giao, người
    dùng dự án bản giao + lịch trực)."""
    role = out_role(scope)
    rows = []
    for e in history.scan(RUNS_DIR, _active['id']):
        if not scope.may_see(e.get('project_code') or None):
            continue
        live = _runs.get(e['id'])
        if live:
            e['status'], e['project'] = live['status'], live.get('project') or e['project']
        rows.append(dict(id=e['id'], kind=e['kind'], project=e['project'], project_code=e.get('project_code') or '',
                         budget_year=e['budget_year'],
                         prior_year=e['prior_year'], started=e['started'], finished=e['finished'],
                         user='' if role == ROLE_PROJECT else e['user'],
                         status=e['status'],
                         source=('' if role == ROLE_PROJECT and _text_hits(e['source'] or '', _leak_words(scope))
                                 else e['source']),
                         outputs=visible_outputs(e['outputs'], role),
                         error=e.get('error', '') if role is None else '',
                         can_clone=bool(e['input_form']),
                         can_gen=any(o['kind'] == 'deliverable' for o in e['outputs']),
                         gen_block=_gen_block(e['budget_year'])))
    return JSONResponse(dict(runs=rows, runs_dir='' if scope.is_project else RUNS_DIR,
                             active=_active['id'] if not scope.is_project or any(r['id'] == _active['id'] for r in rows)
                             else ('busy' if _active['id'] else None)))


def _gen_block(budget_year):
    """Lý do không Gen budget for new year được: bản giao thuộc năm >= năm của mẫu, nên lượt review từ nó sẽ dừng ở
    Prior Budget Year (cùng quy tắc năm với danh sách có sẵn). '' nếu được."""
    tool_year = library.template_year()
    year = int(budget_year) if str(budget_year or '').isdigit() else None
    if year and year >= tool_year:
        return (f'Bản giao này là ngân sách năm {year}; công cụ lập ngân sách năm {tool_year}, chưa lập tiếp được năm '
                f'{year + 1}.')
    return ''


# Dọn lượt lỗi cũ (change log-review-runs): lượt failed quá số ngày này bị xoá lúc server khởi động và mỗi 24 giờ;
# lượt done không bao giờ bị xoá tự động. 0 = tắt.
PRUNE_FAILED_DAYS = int(os.environ.get('BUDGET_WEB_PRUNE_FAILED_DAYS') or 30)


def _prune_loop():
    while True:
        try:
            with _lock:
                active = _active['id']
            history.prune_failed(RUNS_DIR, active, max_age_days=PRUNE_FAILED_DAYS, log=_log)
        except Exception as exc:  # noqa: BLE001 - dọn lỗi không được làm dừng server
            _log(f'prune: error {type(exc).__name__}: {exc}')
        time.sleep(24 * 3600)


@contextlib.asynccontextmanager
async def _lifespan(app):
    if PRUNE_FAILED_DAYS > 0:
        threading.Thread(target=_prune_loop, daemon=True, name='prune-failed-runs').start()
    yield


app = FastAPI(title='Budget Agent - nhập liệu', docs_url=None, redoc_url=None, lifespan=_lifespan)


LOGIN_STEPS = ('/auth/code/request', '/auth/code/verify')


@app.middleware('http')
async def _link_post_guard(request: Request, call_next):
    """Chống CSRF trên cổng link khi bật đăng nhập bằng mã (design D8): mọi POST/PUT/PATCH/DELETE phải có Origin đúng
    địa chỉ link công khai; ngoài hai bước đăng nhập, còn phải có X-CSRF-Token khớp với người gọi. Sai -> 403, không
    route nào chạy."""
    if request.method in ('GET', 'HEAD', 'OPTIONS') or not on_link(request) or not auth.link_uses_otp():
        return await call_next(request)
    origin = (request.headers.get('Origin') or '').strip().lower().rstrip('/')
    if not origin or origin != auth.link_public_origin():
        _log(f'link post refused ({request.url.path}): origin {origin or "-"}')
        return JSONResponse(dict(detail='Yêu cầu không đến từ trang Budget. Tải lại trang rồi thử lại.'), status_code=403)
    path = request.url.path
    if PREFIX and path.startswith(PREFIX + '/'):
        path = path[len(PREFIX):]
    if path not in LOGIN_STEPS:
        ident = link_identity(request)
        sent = request.headers.get('X-CSRF-Token') or ''
        if ident is None:
            return JSONResponse(dict(detail='Chưa đăng nhập hoặc phiên đã hết. Tải lại trang để đăng nhập.'),
                                status_code=401)
        if not ident[2] or not hmac.compare_digest(sent.encode('utf-8'), ident[2].encode('utf-8')):
            _log(f'link post refused ({request.url.path}): csrf token missing or wrong for {ident[0]}')
            return JSONResponse(dict(detail='Phiên trang đã cũ. Tải lại trang rồi thử lại.'), status_code=403)
    return await call_next(request)


app.include_router(router)                 # sau khi proxy bỏ tiền tố: "/"
if PREFIX:
    app.include_router(router, prefix=PREFIX)   # mở trực tiếp, không qua proxy: "/budget/"
# Cookie phiên đăng nhập, ký bằng BUDGET_WEB_SESSION_SECRET; chỉ gửi qua https khi địa chỉ công khai là https.
app.add_middleware(SessionMiddleware, secret_key=auth.SESSION_SECRET, session_cookie='budget_web_session',
                   max_age=auth.SESSION_HOURS * 3600, same_site='lax',
                   https_only=auth.PUBLIC_URL.startswith('https://'))
