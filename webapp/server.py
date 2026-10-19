"""
Trang nhập liệu + nút "Tạo ngân sách" cho Budget Agent (FastAPI).

    cd source_code
    python -m webapp              # xem webapp/__main__.py cho biến môi trường

Mỗi lần bấm nút:
  1. chép mẫu ..\\reports\\Project_Budget_Input.xlsx sang <runs>\\<timestamp>\\Project_Budget_Input.xlsx và ghi
     giá trị form vào đúng ô theo nhãn (fill_input.py; file mẫu chỉ được đọc);
  2. chạy run.py trong tiến trình con (sys.executable, cwd = source_code) với mọi đường dẫn vào/ra đổi hướng
     về thư mục của lần chạy (run_budget.py);
  3. phát log theo thời gian thực và cho tải 3 file kết quả.

Chỉ một lượt chạy tại một thời điểm: cả hai generator dùng một file tạm cố định cho lịch trực. Thư mục
runs mặc định là ..\\reports\\web_runs (bên trong bản đóng băng trên Hub; BUDGET_WEB_RUNS để đổi).

Tiền tố (BUDGET_WEB_PREFIX, mặc định /budget): reverse proxy chuyển /budget/* về app và BỎ tiền tố, nên app
nhận "/" ; mọi link và fetch trên trang mang tiền tố. Các route được đăng ký hai lần, ở gốc và ở tiền tố, để
mở trực tiếp http://host:port/budget/ (không qua proxy) cũng chạy. GET / trả 200 cho heartbeat.
"""
import datetime
import glob
import os
import re
import subprocess
import sys
import threading

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.dirname(HERE)
BUDGET_AGENT = os.path.dirname(SOURCE_DIR)
if SOURCE_DIR not in sys.path:
    sys.path.insert(0, SOURCE_DIR)

from webapp import fill_input  # noqa: E402

HOST = os.environ.get('BUDGET_WEB_HOST') or '127.0.0.1'
PORT = int(os.environ.get('BUDGET_WEB_PORT') or 8090)
PREFIX = ('/' + (os.environ.get('BUDGET_WEB_PREFIX', '/budget') or '').strip('/')).rstrip('/')
RUNS_DIR = os.path.abspath(os.environ.get('BUDGET_WEB_RUNS') or os.path.join(BUDGET_AGENT, 'reports', 'web_runs'))

_lock = threading.Lock()
_runs = {}          # run_id -> dict(status, log, rc, started, finished, workdir, outputs)
_active = {'id': None}

OUTPUT_KINDS = (
    ('deliverable', '* - Sample Consulting Budget.xlsx', 'Bản giao khách (form chuẩn 25 sheet)'),
    ('analysis', 'Project_Budget_Output.xlsx', 'Bản phân tích nội bộ'),
    ('roster', 'Roster_Demand_Model.xlsx', 'Lịch trực'),
)


def _log(message):
    print(f'{datetime.datetime.now():%Y-%m-%d %H:%M:%S} budget-web: {message}', flush=True)


def _outputs(workdir):
    found = []
    for kind, pattern, title in OUTPUT_KINDS:
        matches = glob.glob(os.path.join(workdir, pattern))
        if matches:
            path = max(matches, key=os.path.getmtime)
            found.append(dict(kind=kind, title=title, name=os.path.basename(path),
                              size=os.path.getsize(path)))
    return found


def _worker(run_id):
    run = _runs[run_id]
    cmd = [sys.executable, '-X', 'utf8', os.path.join(HERE, 'run_budget.py'),
           '--input', run['input'], '--workdir', run['workdir']]
    log_path = os.path.join(run['workdir'], 'run.log')
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUNBUFFERED='1')
    try:
        with open(log_path, 'w', encoding='utf-8') as log_file:
            proc = subprocess.Popen(cmd, cwd=SOURCE_DIR, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, env=env)
            assert proc.stdout is not None
            for raw in proc.stdout:
                line = raw.decode('utf-8', errors='replace').rstrip('\r\n')
                run['log'].append(line)
                log_file.write(line + '\n')
            rc = proc.wait()
        run['rc'] = rc
        run['outputs'] = _outputs(run['workdir'])
        complete = len(run['outputs']) == len(OUTPUT_KINDS)
        run['status'] = 'done' if (rc == 0 and complete) else 'failed'
        if rc == 0 and not complete:
            run['log'].append('Thiếu file kết quả trong thư mục chạy.')
    except Exception as exc:  # the page must always learn why a run stopped
        run['log'].append(f'Lỗi khi chạy: {type(exc).__name__}: {exc}')
        run['rc'] = -1
        run['status'] = 'failed'
    finally:
        run['finished'] = datetime.datetime.now().isoformat(timespec='seconds')
        _log(f'run {run_id} {run["status"]} rc={run["rc"]} outputs={len(run["outputs"])}')
        with _lock:
            _active['id'] = None


def _public(run_id, since=0):
    run = _runs[run_id]
    return dict(id=run_id, status=run['status'], rc=run['rc'], started=run['started'],
                finished=run['finished'], workdir=run['workdir'],
                log=run['log'][since:], log_total=len(run['log']), outputs=run['outputs'])


router = APIRouter()


@router.get('/', response_class=HTMLResponse)
def index():
    with open(os.path.join(HERE, 'static', 'index.html'), encoding='utf-8') as fh:
        return fh.read().replace('__PREFIX__', PREFIX)


@router.get('/api/defaults')
def defaults():
    data = fill_input.read_defaults()
    data['template'] = fill_input.TEMPLATE_INPUT
    data['runs_dir'] = RUNS_DIR
    return JSONResponse(data)


@router.post('/api/runs')
def start_run(values: dict):
    with _lock:
        if _active['id']:
            raise HTTPException(409, 'Đang có một lượt tạo ngân sách chạy. Chờ xong rồi bấm lại.')
        name = str(values.get('scalars', {}).get('project_name') or '').strip()
        if not name:
            raise HTTPException(400, 'Tên dự án không được để trống.')
        safe = re.sub(r'[^A-Za-z0-9]+', '-', name).strip('-') or 'project'
        run_id = datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '_' + safe[:40]
        workdir = os.path.join(RUNS_DIR, run_id)
        os.makedirs(workdir, exist_ok=True)
        input_path = os.path.join(workdir, 'Project_Budget_Input.xlsx')
        try:
            fill_input.write_input(values, input_path)
        except Exception as exc:
            raise HTTPException(400, f'Không ghi được file nhập liệu: {exc}')
        _runs[run_id] = dict(status='running', rc=None, log=[f'Thư mục chạy: {workdir}'],
                             started=datetime.datetime.now().isoformat(timespec='seconds'),
                             finished=None, workdir=workdir, input=input_path, outputs=[])
        _active['id'] = run_id
    _log(f'run {run_id} started for project {name!r}')
    threading.Thread(target=_worker, args=(run_id,), daemon=True).start()
    return _public(run_id)


@router.get('/api/runs/{run_id}')
def get_run(run_id: str, since: int = 0):
    if run_id not in _runs:
        raise HTTPException(404, 'Không có lượt chạy này.')
    return _public(run_id, since)


@router.get('/api/runs/{run_id}/files/{name}')
def get_file(run_id: str, name: str):
    if run_id not in _runs:
        raise HTTPException(404, 'Không có lượt chạy này.')
    if os.sep in name or '/' in name or '..' in name:
        raise HTTPException(400, 'Tên file không hợp lệ.')
    path = os.path.join(_runs[run_id]['workdir'], name)
    if not os.path.isfile(path):
        raise HTTPException(404, 'File không tồn tại.')
    return FileResponse(path, filename=name,
                        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


app = FastAPI(title='Budget Agent - nhập liệu', docs_url=None, redoc_url=None)
app.include_router(router)                 # sau khi proxy bỏ tiền tố: "/"
if PREFIX:
    app.include_router(router, prefix=PREFIX)   # mở trực tiếp, không qua proxy: "/budget/"
