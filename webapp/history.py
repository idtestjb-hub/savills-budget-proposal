"""
Các lượt chạy trên đĩa (thư mục runs) cho tab Dự án đã tạo, và dựng lại một lượt vào bộ nhớ sau khi server
khởi động lại. Chỉ đọc file đã có; không chạy gì.

Mỗi lượt là một thư mục <runs>\\<yyyymmdd-hhmmss>_<tên>\\ gồm:
- lượt "new" (Tạo ngân sách): Project_Budget_Input.xlsx, 3 file kết quả, run.log, run_log\\*.json;
- lượt "review" (Review ngân sách dự án đang vận hành): prior\\<file duyệt> hoặc prior_recalc.xlsx, input\\<form>,
  run\\<3 file kết quả>, review_summary.json, review_notes.json, run.log.
Server ghi web_meta.json (kind, project, user, started, status...) khi bắt đầu và khi xong; lượt của phiên
server trước khi có file này được suy từ run_log json / review_summary.json và tên thư mục.
"""
import datetime
import glob
import json
import os
import re

META_FILE = 'web_meta.json'
RUN_ID_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]*$')

OUTPUT_KINDS = (
    ('deliverable', '* - Sample Consulting Budget.xlsx', 'Bản giao khách (form chuẩn 25 sheet)'),
    ('analysis', 'Project_Budget_Output.xlsx', 'Bản phân tích nội bộ'),
    ('roster', 'Roster_Demand_Model.xlsx', 'Lịch trực'),
)
OUTPUT_DIRS = ('', 'run')      # lượt new ghi thẳng vào thư mục lượt; lượt review ghi vào <lượt>\run


def outputs_of(workdir):
    """[{kind, title, name, size, path}] của các file kết quả có trong thư mục lượt (hoặc thư mục con run\\)."""
    found = []
    for kind, pattern, title in OUTPUT_KINDS:
        matches = []
        for sub in OUTPUT_DIRS:
            matches += glob.glob(os.path.join(workdir, sub, pattern) if sub else os.path.join(workdir, pattern))
        if matches:
            path = max(matches, key=os.path.getmtime)
            found.append(dict(kind=kind, title=title, name=os.path.basename(path),
                              size=os.path.getsize(path), path=path))
    return found


def read_meta(workdir):
    path = os.path.join(workdir, META_FILE)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh) or {}
    except Exception:
        return {}


def write_meta(workdir, **fields):
    """Gộp `fields` vào web_meta.json của lượt (tạo mới nếu chưa có)."""
    meta = read_meta(workdir)
    meta.update(fields)
    with open(os.path.join(workdir, META_FILE), 'w', encoding='utf-8') as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1, default=str)
    return meta


def _run_log_record(workdir):
    files = glob.glob(os.path.join(workdir, 'run_log', '*.json'))
    if not files:
        return {}
    try:
        with open(max(files, key=os.path.getmtime), encoding='utf-8') as fh:
            return json.load(fh) or {}
    except Exception:
        return {}


def _review_meta(workdir):
    path = os.path.join(workdir, 'review_summary.json')
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding='utf-8') as fh:
            return (json.load(fh) or {}).get('meta') or {}
    except Exception:
        return {}


def _started_from_name(run_id):
    m = re.match(r'^(\d{8})-(\d{6})', run_id)
    if not m:
        return None
    try:
        return datetime.datetime.strptime(m.group(1) + m.group(2), '%Y%m%d%H%M%S').isoformat(timespec='seconds')
    except ValueError:
        return None


def input_form_of(workdir, kind):
    """Đường dẫn form nhập liệu của lượt (để Clone), hoặc None."""
    candidates = ([os.path.join(workdir, 'input', 'Project_Budget_Input.xlsx')] + glob.glob(os.path.join(workdir, 'input', '*.xlsx'))
                  if kind == 'review' else [os.path.join(workdir, 'Project_Budget_Input.xlsx')])
    return next((p for p in candidates if os.path.isfile(p)), None)


def describe(workdir, run_id=None):
    """Một dict mô tả lượt trong thư mục `workdir`: kind, project, budget_year, prior_year, started, finished, user,
    status, rc, outputs, input_form, source. Lượt chưa có web_meta.json được suy từ các file của pipeline."""
    run_id = run_id or os.path.basename(workdir)
    meta = read_meta(workdir)
    kind = meta.get('kind') or ('review' if (os.path.isdir(os.path.join(workdir, 'input'))
                                             or os.path.exists(os.path.join(workdir, 'review_summary.json'))) else 'new')
    outputs = outputs_of(workdir)
    record = _run_log_record(workdir) if kind == 'new' else {}
    rmeta = _review_meta(workdir) if kind == 'review' else {}
    project = meta.get('project') or record.get('project_name') or rmeta.get('project') or ''
    if not project:
        tail = run_id.split('_', 1)[1] if '_' in run_id else run_id
        project = tail.replace('-', ' ')
    budget_year = meta.get('budget_year') or record.get('budget_year') or rmeta.get('budget_year')
    prior_year = meta.get('prior_year') or rmeta.get('prior_year')
    status = meta.get('status')
    if status in (None, 'running'):
        # web_meta chưa có, hoặc server dừng giữa chừng: suy từ file kết quả.
        status = 'done' if len(outputs) == len(OUTPUT_KINDS) else 'failed'
        if kind == 'review' and status == 'done' and not os.path.exists(os.path.join(workdir, 'review_summary.json')):
            status = 'failed'
    return dict(id=run_id, kind=kind, project=project, budget_year=budget_year, prior_year=prior_year,
                started=meta.get('started') or _started_from_name(run_id), finished=meta.get('finished'),
                user=meta.get('user') or '', status=status, rc=meta.get('rc'), outputs=outputs,
                input_form=input_form_of(workdir, kind), source=meta.get('source') or '', workdir=workdir)


def scan(runs_dir, active_id=None):
    """Mọi lượt trong `runs_dir`, mới nhất trước. Lượt đang chạy (`active_id`) có status 'running'."""
    if not os.path.isdir(runs_dir):
        return []
    entries = []
    for name in sorted(os.listdir(runs_dir), reverse=True):
        workdir = os.path.join(runs_dir, name)
        if not os.path.isdir(workdir) or not RUN_ID_RE.match(name):
            continue
        entry = describe(workdir, name)
        if name == active_id:
            entry['status'] = 'running'
        entries.append(entry)
    return entries


def read_log(workdir):
    path = os.path.join(workdir, 'run.log')
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8', errors='replace') as fh:
        return [ln.rstrip('\r\n') for ln in fh]
