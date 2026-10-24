"""
Danh sách ngân sách đã duyệt có sẵn (kho quét ngân sách thật) cho tab Review: chọn một dự án thay vì tải file lên.

Nguồn danh sách: kho quét (scan_budgets v4, `final_v4\\`): `dim_file.csv` (một dòng mỗi file, 87 dòng ở bản
2026-10-10), `project_map.csv` (tên dự án đọc trong file), `file_profile.csv` (năm theo nội dung, VAT, NFA, độ tin
cậy của sheet quỹ chính). Thư mục kho đặt bằng BUDGET_WEB_LIBRARY_STORE.

File được đọc khi chạy review là file sống trên SharePoint (thư mục `input\\budget_planning` qua junction; đặt bằng
BUDGET_WEB_LIBRARY_ROOT), không phải bản sao trong kho, theo quy tắc "file sống trước":
- nhóm `old8`: <root>\\<rel_path>;
- nhóm `new`: <root>\\Ngân sách thực tế dự án lập hằng năm (có số liệu báo cáo)\\<rel_path>;
- nhóm `new_converted` (bản xlsx do Excel chuyển từ xlsb / giải nén zip, không có trên SharePoint): <kho>\\<rel_path>.

Chọn được: .xlsx tồn tại trên đĩa và có năm ngân sách trước năm của mẫu (mẫu hiện là 2027 nên chỉ nhận ngân sách của
năm 2026 trở về trước). PDF (ảnh quét), xlsb, zip gốc, file không có sheet quỹ, file từ năm của mẫu trở lên hiện xám
kèm lý do. Tên dự án thật chỉ nằm trong dữ liệu đọc lúc chạy, không nằm trong repo.

Đường dẫn dài: tên file trong thư viện có thể dài, nên đường dẫn đầy đủ vượt 260 ký tự (283 ở THE HORIZON trên server).
Windows chỉ nhận đường dẫn đó khi bật LongPathsEnabled (client có, server không), nên mọi chỗ đọc hay chép file thư
viện đi qua `long_path()` (tiền tố `\\\\?\\`), không phụ thuộc cài đặt hệ thống.
"""
import csv
import os
import re
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
BUDGET_AGENT = os.path.dirname(os.path.dirname(HERE))
DEFAULT_ROOT = os.path.join(os.path.dirname(BUDGET_AGENT), 'input', 'budget_planning')
DEFAULT_STORE = os.path.join(os.path.expanduser('~'), 'Savills-local', 'budget-test', 'scan-2026-10-07', 'final_v4')
NEW_SUBFOLDER = 'Ngân sách thực tế dự án lập hằng năm (có số liệu báo cáo)'

CONFIDENCE_VI = {'high': 'Khớp tổng', 'medium': 'Tổng không khớp', 'low': 'Form cũ, chưa đối soát',
                 '': 'Không có sheet quỹ'}
# Khớp sau giải thích (bộ lọc che ô tổng, hoặc file cộng trùng một dòng): kho xếp 'high', nhãn riêng kèm ghi chú của kho.
EXPLAINED_VI = 'Khớp tổng (đã giải thích)'
# Trạng thái đối soát của kho quét (reconcile.csv, sheet quỹ chính) -> câu giải thích hiện cạnh tên dự án.
SECTION_VI = {'R': 'thu', 'E': 'chi', 'D': 'mục D'}
MISMATCH_TAIL = ('; có thể do công thức trong file gốc hoặc do kho quét đọc trùng dòng gộp. Vẫn chạy được: Review tự '
                 'đối soát lại, xem kỹ sheet Review')
NO_ANCHOR_NOTE = ('sheet quỹ không có đủ các dòng mốc R, E, PL1, PL2 của form mới nên kho quét không đối soát tổng; '
                  'khi chạy, Review vẫn tự đối soát số duyệt với dòng tổng của file')
# File đọc qua bảng ghép mã (scan_other_forms.py: form của chủ đầu tư, file không có cột mã): kho khớp tổng, nhưng Review
# chưa đọc được form này nên không cho chọn (như trước khi kho đọc được chúng).
OTHER_FORM_NOTE = 'form khác, đọc qua bảng ghép'
OTHER_FORM_REASON = ('Form riêng của chủ đầu tư, kho quét đọc qua bảng ghép mã để làm khoảng ngân sách thật; '
                     'Review chưa đọc được form này')
NO_VALUE_COL_NOTE ='kho quét không xác định được cột số cả năm; khi chạy, Review đọc lại và tự đối soát'
UNREADABLE_VI = {'pdf': 'PDF ảnh quét: không đọc được số', 'xlsb': 'xlsb: dùng bản chuyển đổi xlsx bên dưới',
                 'zip': 'zip: dùng file đã giải nén bên dưới'}

_cache = {'key': None, 'entries': None}
_cache_lock = threading.Lock()

LONG_PATH_MIN = 240   # dưới mức này Windows nhận đường dẫn thường; trên đó dùng tiền tố \\?\
FALLBACK_TEMPLATE_YEAR = 2027
_template_year = {'value': None}


def long_path(path):
    """Đường dẫn dùng được cho open / isfile / shutil trên Windows kể cả khi dài hơn 260 ký tự và hệ thống chưa bật
    LongPathsEnabled: đường dẫn tuyệt đối có tiền tố \\\\?\\ (UNC: \\\\?\\UNC\\). Hệ điều hành khác hoặc đường dẫn ngắn: giữ nguyên."""
    if os.name != 'nt' or not path:
        return path
    p = os.path.abspath(path)
    if p.startswith('\\\\?\\') or len(p) < LONG_PATH_MIN:
        return p
    if p.startswith('\\\\'):
        return '\\\\?\\UNC\\' + p[2:]
    return '\\\\?\\' + p


def template_year():
    """Năm ngân sách của mẫu mà công cụ lập (ô AL5 của mẫu, hiện 2027). Đọc một lần khi cần; không đọc được thì 2027.
    File ngân sách đã duyệt phải thuộc năm TRƯỚC năm này (existing_staffing.compute dừng nếu Prior Budget Year >= năm mẫu)."""
    if _template_year['value'] is None:
        try:
            import generate_project_budget
            _template_year['value'] = int(generate_project_budget.template_budget_year())
        except Exception:      # noqa: BLE001 - mọi lỗi đọc mẫu đều quay về giá trị cố định, trang vẫn chạy
            _template_year['value'] = FALLBACK_TEMPLATE_YEAR
    return _template_year['value']


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


def _mtr(v):
    return f'{abs(v) / 1e6:,.2f}'.replace(',', ' ').replace('.', ',').replace(' ', '.') + ' tr'


def confidence_note(rec):
    """Câu giải thích cho một dòng reconcile.csv (sheet quỹ chính); '' khi khớp hoặc không có dòng."""
    if not rec:
        return ''
    status = rec.get('status', '')
    if status == 'mismatch':
        parts = []
        for s in 'RED':
            d = _float(rec.get(f'{s}_diff'))
            if d and abs(d) > 1:
                more = 'cao hơn' if d > 0 else 'thấp hơn'   # diff = cộng các dòng - dòng tổng của file
                parts.append(f'cộng các dòng {SECTION_VI[s]} {more} dòng tổng của file {_mtr(d)}')
        return ('; '.join(parts) + MISMATCH_TAIL) if parts else ''
    if status == 'no_anchor':
        return NO_ANCHOR_NOTE
    if status == 'no_value_col':
        return NO_VALUE_COL_NOTE
    if status.startswith('ok_'):
        return rec.get('note', '') or ''
    return ''


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
    recon = {(r['file_id'], r['sheet']): r for r in _read_csv(os.path.join(store, 'reconcile.csv'))}
    out = []
    for r in files:
        fid = r['file_id']
        prof, pm = profiles.get(fid, {}), names.get(fid, {})
        ext = (r.get('ext') or os.path.splitext(r.get('file_name', ''))[1].lstrip('.')).lower()
        path = os.path.normpath(_resolve(r, root, store))
        project = (pm.get('project_name') or '').strip()
        conf = (prof.get('primary_confidence') or '').strip()
        year = prof.get('budget_year_v2') or pm.get('budget_year_v2') or pm.get('year_in_name') or ''
        rec = recon.get((fid, prof.get('primary_sheet', '')))
        reason = ''
        if ext != 'xlsx':
            reason = UNREADABLE_VI.get(ext, f'{ext}: không đọc được')
        elif not os.path.isfile(long_path(path)):
            reason = 'Không thấy file trên SharePoint (đã đổi tên hoặc chuyển chỗ?)'
        elif not conf:
            reason = 'Không tìm thấy sheet quỹ quản lý trong file'
        elif (rec or {}).get('note', '').startswith(OTHER_FORM_NOTE):
            reason = OTHER_FORM_REASON
        elif str(year).isdigit() and int(year) >= template_year():
            reason = (f'Ngân sách năm {int(year)}: công cụ lập ngân sách năm {template_year()}, nên chỉ review được '
                      f'ngân sách đã duyệt của năm {template_year() - 1} trở về trước')
        explained = conf == 'high' and (rec or {}).get('status', '').startswith('ok_')
        note = confidence_note(rec) if (conf != 'high' or explained) else ''
        out.append(dict(id=fid, project=project or _name_from_file(r.get('file_name', '')),
                        project_from='file' if project else 'tên file', file_name=r.get('file_name', ''),
                        folder={'old8': 'budget_planning', 'new': NEW_SUBFOLDER,
                                'new_converted': 'bản chuyển đổi trong kho quét'}.get(r.get('source_group'), ''),
                        year=int(year) if str(year).isdigit() else None, vat=prof.get('vat_basis_v2') or '',
                        nfa=_float(prof.get('nfa_total')), confidence=conf,
                        confidence_vi=EXPLAINED_VI if explained else CONFIDENCE_VI.get(conf, conf),
                        confidence_note=note, ext=ext, selectable=not reason, reason=reason, path=path,
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
