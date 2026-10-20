"""
Danh sách ngân sách đã duyệt có sẵn (kho quét ngân sách thật) cho tab Review: chọn một dự án thay vì tải file lên.

Nguồn danh sách: kho quét (scan_budgets v2, `final_v2\\`): `dim_file.csv` (một dòng mỗi file, 87 dòng ở bản
2026-10-10), `project_map.csv` (tên dự án đọc trong file), `file_profile.csv` (năm theo nội dung, VAT, NFA, độ tin
cậy của sheet quỹ chính). Thư mục kho đặt bằng BUDGET_WEB_LIBRARY_STORE.

File được đọc khi chạy review là file sống trên SharePoint (thư mục `input\\budget_planning` qua junction; đặt bằng
BUDGET_WEB_LIBRARY_ROOT), không phải bản sao trong kho, theo quy tắc "file sống trước":
- nhóm `old8`: <root>\\<rel_path>;
- nhóm `new`: <root>\\Ngân sách thực tế dự án lập hằng năm (có số liệu báo cáo)\\<rel_path>;
- nhóm `new_converted` (bản xlsx do Excel chuyển từ xlsb / giải nén zip, không có trên SharePoint): <kho>\\<rel_path>.

Chọn được: .xlsx tồn tại trên đĩa. PDF (ảnh quét), xlsb, zip gốc hiện xám kèm lý do. Tên dự án thật chỉ nằm trong dữ
liệu đọc lúc chạy, không nằm trong repo.
"""
import csv
import os
import re
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
BUDGET_AGENT = os.path.dirname(os.path.dirname(HERE))
DEFAULT_ROOT = os.path.join(os.path.dirname(BUDGET_AGENT), 'input', 'budget_planning')
DEFAULT_STORE = os.path.join(os.path.expanduser('~'), 'Savills-local', 'budget-test', 'scan-2026-10-07', 'final_v2')
NEW_SUBFOLDER = 'Ngân sách thực tế dự án lập hằng năm (có số liệu báo cáo)'

CONFIDENCE_VI = {'high': 'Khớp tổng', 'medium': 'Lệch tổng', 'low': 'Chưa đối soát được', '': 'Không có sheet quỹ'}
UNREADABLE_VI = {'pdf': 'PDF ảnh quét: không đọc được số', 'xlsb': 'xlsb: dùng bản chuyển đổi xlsx bên dưới',
                 'zip': 'zip: dùng file đã giải nén bên dưới'}

_cache = {'key': None, 'entries': None}
_cache_lock = threading.Lock()


def root_dir():
    return os.path.abspath(os.environ.get('BUDGET_WEB_LIBRARY_ROOT') or DEFAULT_ROOT)


def store_dir():
    return os.path.abspath(os.environ.get('BUDGET_WEB_LIBRARY_STORE') or DEFAULT_STORE)


def _read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


def _resolve(row, root, store):
    group, rel = row.get('source_group', ''), row.get('rel_path') or row.get('file_name') or ''
    if group == 'old8':
        return os.path.join(root, rel)
    if group == 'new':
        return os.path.join(root, NEW_SUBFOLDER, rel)
    return os.path.join(os.path.dirname(store), rel) if not os.path.isfile(os.path.join(store, rel)) else os.path.join(store, rel)


def _float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _name_from_file(file_name):
    stem = os.path.splitext(os.path.basename(file_name))[0]
    stem = re.sub(r'__repaired$', '', stem)
    stem = re.sub(r'^(XLSB__|ZIP_[A-Za-z0-9]+__)', '', stem)
    stem = re.sub(r'^\d{6,8}\s*[-_]\s*', '', stem)
    return stem.strip() or file_name


def load(root=None, store=None):
    """Mọi dòng của kho, mỗi dòng: id (file_id), project, project_from (file | tên file), file_name, folder, year, vat,
    nfa, confidence, confidence_vi, ext, selectable, reason, path. Danh sách rỗng khi không có kho."""
    root, store = root or root_dir(), store or store_dir()
    files = _read_csv(os.path.join(store, 'dim_file.csv'))
    names = {r['file_id']: r for r in _read_csv(os.path.join(store, 'project_map.csv'))}
    profiles = {r['file_id']: r for r in _read_csv(os.path.join(store, 'file_profile.csv'))}
    out = []
    for r in files:
        fid = r['file_id']
        prof, pm = profiles.get(fid, {}), names.get(fid, {})
        ext = (r.get('ext') or os.path.splitext(r.get('file_name', ''))[1].lstrip('.')).lower()
        path = os.path.normpath(_resolve(r, root, store))
        project = (pm.get('project_name') or '').strip()
        conf = (prof.get('primary_confidence') or '').strip()
        reason = ''
        if ext != 'xlsx':
            reason = UNREADABLE_VI.get(ext, f'{ext}: không đọc được')
        elif not os.path.isfile(path):
            reason = 'Không thấy file trên SharePoint (đã đổi tên hoặc chuyển chỗ?)'
        elif not conf:
            reason = 'Không tìm thấy sheet quỹ quản lý trong file'
        year = prof.get('budget_year_v2') or pm.get('budget_year_v2') or pm.get('year_in_name') or ''
        out.append(dict(id=fid, project=project or _name_from_file(r.get('file_name', '')),
                        project_from='file' if project else 'tên file', file_name=r.get('file_name', ''),
                        folder={'old8': 'budget_planning', 'new': NEW_SUBFOLDER,
                                'new_converted': 'bản chuyển đổi trong kho quét'}.get(r.get('source_group'), ''),
                        year=int(year) if str(year).isdigit() else None, vat=prof.get('vat_basis_v2') or '',
                        nfa=_float(prof.get('nfa_total')), confidence=conf, confidence_vi=CONFIDENCE_VI.get(conf, conf),
                        ext=ext, selectable=not reason, reason=reason, path=path,
                        duplicate_of=r.get('content_dup_of') or ''))
    out.sort(key=lambda e: (not e['selectable'], e['project'].casefold(), -(e['year'] or 0)))
    return out


def entries():
    """load() có bộ nhớ đệm theo thời điểm sửa của ba file CSV của kho."""
    store = store_dir()
    key = (root_dir(), store) + tuple(
        os.path.getmtime(os.path.join(store, n)) if os.path.exists(os.path.join(store, n)) else 0
        for n in ('dim_file.csv', 'project_map.csv', 'file_profile.csv'))
    with _cache_lock:
        if _cache['key'] != key:
            _cache['entries'], _cache['key'] = load(), key
        return _cache['entries']


def find(file_id):
    return next((e for e in entries() if e['id'] == file_id), None)
