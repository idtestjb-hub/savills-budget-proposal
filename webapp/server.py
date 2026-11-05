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

from webapp import adjust, auth, facts_prefill, fill_input, history, library, results  # noqa: E402

HOST = os.environ.get('BUDGET_WEB_HOST') or '127.0.0.1'
PORT = int(os.environ.get('BUDGET_WEB_PORT') or 8090)
PREFIX = ('/' + (os.environ.get('BUDGET_WEB_PREFIX', '/budget') or '').strip('/')).rstrip('/')
RUNS_DIR = os.path.abspath(os.environ.get('BUDGET_WEB_RUNS') or os.path.join(BUDGET_AGENT, 'reports', 'web_runs'))
# Chế độ site (change site-standalone-package): BUDGET_WEB_SITE trỏ tới thư mục site\ của gói đóng cho một dự án
# (site.json + file ngân sách đã duyệt). Trang chỉ còn ba tab, nguồn Review mặc định là file trong gói, không có kho.
SITE_DIR = os.path.abspath(os.environ['BUDGET_WEB_SITE']) if os.environ.get('BUDGET_WEB_SITE') else None
SITE_FILE = 'site.json'


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
        with open(log_path, 'w', encoding='utf-8') as log_file:
            proc = subprocess.Popen(run['cmd'], cwd=SOURCE_DIR, stdout=subprocess.PIPE,
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
        complete = len(run['outputs']) == len(OUTPUT_KINDS)
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
VIEWER_KINDS = {'deliverable'}
_INTERNAL_LOG_MARKERS = ('[2/2]', 'generate_project_output', 'Internal analysis', '  analysis ', '  roster ',
                         'phân tích:', "Sheet 'Review'")


def role_of(request):
    """'viewer' khi tiêu đề X-Hub-Role (không phân biệt hoa thường) là viewer; None khi vắng hoặc giá trị khác."""
    value = (request.headers.get(ROLE_HEADER) or '').strip().lower()
    return ROLE_VIEWER if value == ROLE_VIEWER else None


def _strip(outputs):
    return [{k: v for k, v in o.items() if k != 'path'} for o in outputs]


def visible_outputs(outputs, role):
    """Danh sách file người có vai trò `role` được thấy: viewer chỉ bản giao khách; ai khác đủ 3 file."""
    if role == ROLE_VIEWER:
        return _strip(o for o in outputs if o['kind'] in VIEWER_KINDS)
    return _strip(outputs)


def may_download(run, name, role):
    """Viewer chỉ tải được file có trong danh sách của mình; ai khác tải mọi file trong thư mục chạy."""
    if role != ROLE_VIEWER:
        return True
    return any(o['name'] == name for o in visible_outputs(run['outputs'], role))


def visible_log(lines, outputs, role):
    """Log cho viewer: bỏ các dòng nêu tên hoặc đường dẫn của file bị ẩn và tiến trình của bước phân tích nội bộ."""
    if role != ROLE_VIEWER:
        return list(lines)
    hidden = [o['name'] for o in outputs if o['kind'] not in VIEWER_KINDS] + ['Project_Budget_Output.xlsx',
                                                                            'Roster_Demand_Model.xlsx']
    return [ln for ln in lines
            if not any(h in ln for h in hidden) and not any(m in ln for m in _INTERNAL_LOG_MARKERS)]


def _public(run_id, since=0, role=None):
    run = _runs[run_id]
    # `since` đếm trên log đầy đủ để trang không nhận trùng dòng; chỉ phần trả về được lọc theo vai trò.
    return dict(id=run_id, kind=run.get('kind', 'new'), project=run.get('project'), source=run.get('source', ''),
                status=run['status'], rc=run['rc'], started=run['started'], finished=run['finished'],
                workdir=run['workdir'],
                log=visible_log(run['log'][since:], run['outputs'], role), log_total=len(run['log']),
                outputs=visible_outputs(run['outputs'], role), summary=run.get('summary'))


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
    run = dict(kind=d['kind'], project=d['project'], source=d['source'], status=d['status'], rc=d['rc'],
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


def current_user(request: Request):
    """Người đang đăng nhập (dict name/email), hoặc None. Chế độ off: một người dùng cục bộ."""
    if not auth.enabled():
        return dict(name='máy cá nhân', email='')
    return request.session.get('user')


def require_user(request: Request):
    user = current_user(request)
    if not user:
        raise HTTPException(401, 'Chưa đăng nhập. Tải lại trang để đăng nhập.')
    return user


router = APIRouter()


@router.get('/', response_class=HTMLResponse)
def index(request: Request):
    """Trang nhập liệu khi đã đăng nhập; trang đăng nhập (vẫn 200, cho heartbeat) khi chưa."""
    user = current_user(request)
    if not user:
        message = request.session.pop('auth_message', '') if auth.enabled() else ''
        return _page('login.html', MESSAGE=_escape(message))
    who = '' if not auth.enabled() else (
        f'{_escape(user["name"])} · <a href="{PREFIX}/auth/logout">Đăng xuất</a>')
    return _page('index.html', USER=who, SITE='1' if SITE_DIR else '')


@router.get('/auth/login')
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


@router.get('/auth/callback')
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


@router.get('/auth/logout')
def auth_logout(request: Request):
    request.session.clear()
    if not auth.enabled():
        return RedirectResponse(PREFIX + '/', status_code=302)
    return RedirectResponse(auth.logout_url(), status_code=302)


@router.get('/api/defaults')
def defaults(user=Depends(require_user)):
    data = fill_input.read_defaults()
    data['template'] = fill_input.TEMPLATE_INPUT
    data['runs_dir'] = RUNS_DIR
    return JSONResponse(data)


def _start(run_id, run, who, what):
    """Ghi lượt vào bộ nhớ + web_meta.json và chạy tiến trình con. Gọi khi đang giữ _lock."""
    _runs[run_id] = run
    _active['id'] = run_id
    if run['kind'] != 'adjust':
        history.write_meta(run['workdir'], kind=run['kind'], project=run.get('project'), user=who,
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
def start_run(request: Request, values: dict, user=Depends(require_user)):
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
        run = dict(kind='new', project=name, source='', status='running', rc=None, log=[f'Thư mục chạy: {workdir}'],
                   started=started, finished=None, workdir=workdir, input=input_path, outputs=[], summary=None, cmd=cmd)
        _start(run_id, run, _who(request, user), f'for project {name!r}')
    return _public(run_id, role=role_of(request))


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


@router.post('/api/reviews')
async def start_review(request: Request, prior: UploadFile | None = File(None), source_run: str = Form(''),
                       library_id: str = Form(''), facts: str = Form('{}'), site: str = Form(''),
                       user=Depends(require_user)):
    """Lượt review, ngân sách năm ngoái lấy từ một trong bốn nguồn: `site=1` (file đóng trong gói site, chép một bản vào
    thư mục prior của lượt), `library_id` (dự án có sẵn trong kho, file sống trên SharePoint, chép một bản vào thư mục
    prior của lượt), `source_run` (bản giao của lượt cũ, Excel tính lại trước khi đọc), hoặc `prior` (file .xlsx tải
    lên). `facts` là JSON các ô dữ kiện của trang."""
    try:
        raw = json.loads(facts or '{}')
        if not isinstance(raw, dict):
            raise ValueError
    except ValueError:
        raise HTTPException(400, 'Dữ kiện gửi lên không đúng dạng.')
    fact_map = _facts_from_form(raw)
    source_run, library_id = (source_run or '').strip(), (library_id or '').strip()
    upload, copy_from = None, None
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
        if entry is None:
            raise HTTPException(404, 'Không có dự án này trong danh sách có sẵn.')
        if not entry['selectable']:
            raise HTTPException(400, f"Không dùng được file này: {entry['reason']}.")
        stem, recalc, copy_from = os.path.splitext(entry['file_name'])[0], False, entry['path']
        tag = 'review-' + _safe(entry['project'], 'du-an')
        source, what = f"dự án có sẵn {entry['project']} ({entry['file_name']})", f'from library {library_id}'
        project = entry['project']
        prior_src = None
    elif source_run:
        src = _ensure_run(source_run)
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
        run = dict(kind='review', project=project, source=source, status='running', rc=None,
                   log=[f'Thư mục chạy: {workdir}', f'Ngân sách năm ngoái: {source}'], started=started, finished=None,
                   workdir=workdir, input=None, outputs=[], summary=None, cmd=cmd, facts=raw)
        _start(run_id, run, _who(request, user), what)
    return _public(run_id, role=role_of(request))


@router.get('/api/runs/{run_id}')
def get_run(request: Request, run_id: str, since: int = 0, user=Depends(require_user)):
    _ensure_run(run_id)
    return _public(run_id, since, role_of(request))


@router.get('/api/runs/{run_id}/input')
def get_run_input(request: Request, run_id: str, user=Depends(require_user)):
    """Giá trị form của lượt đó (Clone, và dữ kiện cho Gen budget for new year), đọc theo nhãn như api/defaults."""
    run = _ensure_run(run_id)
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
    return JSONResponse(data)


@router.get('/api/runs/{run_id}/files/{name}')
def get_file(request: Request, run_id: str, name: str, user=Depends(require_user)):
    run = _ensure_run(run_id)
    if os.sep in name or '/' in name or '..' in name:
        raise HTTPException(400, 'Tên file không hợp lệ.')
    if not may_download(run, name, role_of(request)):
        _log(f'download refused for viewer: {run_id}/{name}')
        raise HTTPException(403, 'Tài khoản của bạn chỉ được tải bản giao khách.')
    known = next((o['path'] for o in run['outputs'] if o['name'] == name), None)
    path = known or os.path.join(run['workdir'], name)
    if not os.path.isfile(path):
        raise HTTPException(404, 'File không tồn tại.')
    return FileResponse(path, filename=name,
                        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


def _deliverable_of(run):
    found = next((o for o in run['outputs'] if o['kind'] == 'deliverable'), None)
    if not found:
        raise HTTPException(404, 'Lượt này không có bản giao để điều chỉnh.')
    return found['path']


@router.get('/api/runs/{run_id}/adjust')
def get_adjust(request: Request, run_id: str, user=Depends(require_user)):
    """Các mã trên sheet '4. Điều chỉnh' của bản giao (giá trị nhập hiện tại), số duyệt năm cũ khi là lượt review,
    và kết quả lần lưu gần nhất."""
    run = _ensure_run(run_id)
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
    return JSONResponse(dict(id=run_id, kind=run.get('kind', 'new'), project=run.get('project'),
                             deliverable=os.path.basename(path), items=items, has_approved=bool(approved), top_keys=top_keys,
                             abnormal_keys=abnormal_keys, abnormal_rule=adjust.abnormal_rule(),
                             measure_labels={k: v for k, v in (cols.get('labels') or {}).items() if measures.get(k)},
                             prior_year=years[0], budget_year=years[1],
                             last=results.adjust_result(run['workdir']) or None,
                             can_save=role_of(request) != ROLE_VIEWER, active=_active['id']))


@router.post('/api/runs/{run_id}/adjust')
def start_adjust(request: Request, run_id: str, body: dict, user=Depends(require_user)):
    """Ghi đè bản giao của lượt bằng các chỉnh sửa (backup có ngày bên cạnh), rồi Excel tính lại. Chạy như một lượt
    trong hàng đợi chung; trang theo dõi bằng api/runs/<id trả về>."""
    if role_of(request) == ROLE_VIEWER:
        raise HTTPException(403, 'Tài khoản chỉ xem không được lưu điều chỉnh.')
    base = _ensure_run(run_id)
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
        run = dict(kind='adjust', base_id=run_id, project=base.get('project'), source=f'điều chỉnh lượt {run_id}',
                   status='running', rc=None, log=[f'Điều chỉnh bản giao của lượt {run_id}: {len(edits)} mã'],
                   started=_now(), finished=None, workdir=workdir, input=None, outputs=base['outputs'], summary=None,
                   cmd=cmd, log_name='adjust.log')
        _start(job_id, run, _who(request, user), f'adjust of {run_id} ({len(edits)} codes)')
    return _public(job_id, role=role_of(request))


@router.get('/api/site')
def get_site(user=Depends(require_user)):
    """Chế độ gói site: dự án, tên file ngân sách đã duyệt, dữ kiện điền sẵn (không có đường dẫn). 404 ngoài chế độ site."""
    info = site_info()
    if info is None:
        raise HTTPException(404, 'Trang này không chạy ở chế độ gói site.')
    return JSONResponse({k: v for k, v in info.items() if k in ('project', 'prior_file', 'facts', 'store_id',
                                                                 'built_at', 'code', 'prior_exists')})


@router.get('/api/library')
def get_library(user=Depends(require_user)):
    """Ngân sách đã duyệt có sẵn (kho quét) cho tab Review; không trả đường dẫn. Chế độ gói site: danh sách rỗng, kể
    cả khi máy dựng gói có kho ở đường dẫn mặc định."""
    if SITE_DIR:
        return JSONResponse(dict(entries=[], total=0, selectable=0, root='', store=''))
    rows = [{k: v for k, v in e.items() if k != 'path'} for e in library.entries()]
    return JSONResponse(dict(entries=rows, total=len(rows), selectable=sum(e['selectable'] for e in rows),
                             root=library.root_dir(), store=library.store_dir()))


@router.get('/api/library/{file_id}/facts')
def get_library_facts(file_id: str, user=Depends(require_user)):
    """Dữ kiện điền sẵn cho mục 2 của tab Review khi chọn một dòng kho (change prefill-review-facts): lượt trước cùng
    dự án > sheet 0. Info > danh sách master, mỗi ô kèm nguồn và số khác của nguồn sau."""
    if SITE_DIR:
        raise HTTPException(404, 'Gói site không có kho.')
    entry = library.find(file_id)
    if entry is None:
        raise HTTPException(404, 'Không thấy dòng này trong kho.')
    entry = dict(entry, path=library.long_path(entry['path']) if entry.get('selectable') else '')
    return JSONResponse(facts_prefill.prefill(entry, history.scan(RUNS_DIR)))


@router.get('/api/library/overview')
def get_library_overview(user=Depends(require_user)):
    """Số tổng hợp của kho (tab Kho ngân sách): theo năm, nhóm, lý do, loại file. Chỉ có số đếm, không có tên hay đường dẫn."""
    if SITE_DIR:
        raise HTTPException(404, 'Gói site không có kho.')
    return JSONResponse(library.overview())


@router.get('/api/history')
def get_history(request: Request, user=Depends(require_user)):
    """Mọi lượt trong thư mục runs, mới nhất trước; file theo vai trò (viewer chỉ bản giao)."""
    role = role_of(request)
    rows = []
    for e in history.scan(RUNS_DIR, _active['id']):
        live = _runs.get(e['id'])
        if live:
            e['status'], e['project'] = live['status'], live.get('project') or e['project']
        rows.append(dict(id=e['id'], kind=e['kind'], project=e['project'], budget_year=e['budget_year'],
                         prior_year=e['prior_year'], started=e['started'], finished=e['finished'], user=e['user'],
                         status=e['status'], source=e['source'], outputs=visible_outputs(e['outputs'], role),
                         error=e.get('error', '') if role != ROLE_VIEWER else '',
                         can_clone=bool(e['input_form']),
                         can_gen=any(o['kind'] == 'deliverable' for o in e['outputs']),
                         gen_block=_gen_block(e['budget_year'])))
    return JSONResponse(dict(runs=rows, runs_dir=RUNS_DIR, active=_active['id']))


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
app.include_router(router)                 # sau khi proxy bỏ tiền tố: "/"
if PREFIX:
    app.include_router(router, prefix=PREFIX)   # mở trực tiếp, không qua proxy: "/budget/"
# Cookie phiên đăng nhập, ký bằng BUDGET_WEB_SESSION_SECRET; chỉ gửi qua https khi địa chỉ công khai là https.
app.add_middleware(SessionMiddleware, secret_key=auth.SESSION_SECRET, session_cookie='budget_web_session',
                   max_age=auth.SESSION_HOURS * 3600, same_site='lax',
                   https_only=auth.PUBLIC_URL.startswith('https://'))
