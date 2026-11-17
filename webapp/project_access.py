"""
Quyền xem theo dự án cho link ngoài (change budget-web-project-access).

File Excel phân quyền (đường dẫn đặt bằng BUDGET_WEB_ACCESS_BOOK) có hai sheet:
- `Du an`: Ma (mã dự án, ví dụ P012), Ten (tên hiển thị), Ten khac (các tên khác, cách nhau bằng dấu chấm phẩy; dùng để
  khớp tên dự án trong kho ngân sách và trong lượt cũ);
- `Nguoi dung`: Email, Ma du an (các mã cách nhau bằng dấu chấm phẩy, hoặc ALL = xem như văn phòng).

Đóng mặc định: người không có trong file, hoặc chỉ có mã không tồn tại, không thấy gì. File được đọc lại khi đổi (kiểm
tối đa mỗi CHECK_SECONDS giây); file lỗi thì giữ danh sách đọc được lần trước và ghi log; chưa từng đọc được thì mọi
người dùng link bị từ chối. Lỗi không bao giờ mở rộng quyền của ai.
"""
import os
import re
import threading
import time
import unicodedata
from dataclasses import dataclass, field

SHEET_PROJECTS = 'Du an'
SHEET_PEOPLE = 'Nguoi dung'
ALL = 'ALL'
CHECK_SECONDS = 60
CODE_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,31}$')

KIND_OFFICE, KIND_VIEWER, KIND_PROJECT, KIND_NONE = 'office', 'viewer', 'project', 'none'


class AccessBookError(ValueError):
    """File phân quyền không đọc được hoặc sai cấu trúc (cả file bị bỏ, giữ danh sách cũ)."""


def fold(text):
    """Chữ thường, bỏ dấu tiếng Việt (đ -> d), mọi ký tự không phải chữ/số thành một dấu cách."""
    s = unicodedata.normalize('NFD', str(text or '')).replace('đ', 'd').replace('Đ', 'D')
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn').lower()
    return ' '.join(re.sub(r'[^0-9a-z]+', ' ', s).split())


def _split(cell):
    return [p.strip() for p in str(cell or '').replace('\n', ';').split(';') if p.strip()]


@dataclass(frozen=True)
class Scope:
    """Người đang gọi: kind office (xem hết), viewer (vai trò viewer của Hub), project (chỉ các mã trong `codes`), none."""
    kind: str
    codes: frozenset = frozenset()
    email: str = ''

    @property
    def is_project(self):
        return self.kind == KIND_PROJECT

    def may_see(self, code):
        """Được xem một lượt / dòng kho mang mã `code` (None = chưa gắn mã: chỉ văn phòng và viewer)."""
        if self.kind in (KIND_OFFICE, KIND_VIEWER):
            return True
        if self.kind == KIND_PROJECT:
            return bool(code) and code in self.codes
        return False


@dataclass
class AccessList:
    projects: dict = field(default_factory=dict)   # code -> dict(name, aliases)
    people: dict = field(default_factory=dict)     # email (chữ thường) -> frozenset mã, hoặc frozenset({ALL})
    warnings: list = field(default_factory=list)

    def scope_for(self, email):
        email = (email or '').strip().lower()
        codes = self.people.get(email)
        if not email or not codes:
            return Scope(KIND_NONE, frozenset(), email)
        if ALL in codes:
            return Scope(KIND_OFFICE, frozenset(), email)
        return Scope(KIND_PROJECT, frozenset(codes), email)

    def names_of(self, code):
        """Tên hiển thị + các tên khác của một mã (dùng làm tên 'của chính dự án' khi ẩn danh và khi quét lộ tên)."""
        p = self.projects.get(code) or {}
        return [n for n in [p.get('name')] + list(p.get('aliases') or []) if n]

    def match(self, name):
        """Mã duy nhất có tên hoặc tên khác trùng `name` sau khi gấp chữ; None khi không khớp hoặc khớp nhiều mã."""
        key = fold(name)
        if not key:
            return None
        hits = {code for code, p in self.projects.items()
                if key in {fold(n) for n in [p['name']] + list(p['aliases'])}}
        return hits.pop() if len(hits) == 1 else None


def _header_map(row, wanted, sheet):
    """{tên cột chuẩn: chỉ số} từ dòng tiêu đề; thiếu cột nào là lỗi cả file."""
    folded = [fold(c) for c in row]
    out = {}
    for key, label in wanted.items():
        if label not in folded:
            raise AccessBookError(f"Sheet '{sheet}' thiếu cột '{label}'.")
        out[key] = folded.index(label)
    return out


def load(path):
    """Đọc file phân quyền -> AccessList. Lỗi cấu trúc (thiếu sheet, thiếu cột, trùng mã) -> AccessBookError. Dòng sai
    lẻ (email không hợp lệ, mã không tồn tại) bị bỏ và ghi vào `warnings`."""
    import openpyxl
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001 - file đang đồng bộ dở, khoá, hỏng
        raise AccessBookError(f'Không mở được file phân quyền: {type(exc).__name__}: {exc}') from exc
    try:
        for sheet in (SHEET_PROJECTS, SHEET_PEOPLE):
            if sheet not in wb.sheetnames:
                raise AccessBookError(f"File phân quyền thiếu sheet '{sheet}'.")
        acl = AccessList()
        rows = list(wb[SHEET_PROJECTS].iter_rows(values_only=True))
        if not rows:
            raise AccessBookError(f"Sheet '{SHEET_PROJECTS}' trống.")
        col = _header_map(rows[0], {'code': 'ma', 'name': 'ten', 'aliases': 'ten khac'}, SHEET_PROJECTS)
        for n, row in enumerate(rows[1:], start=2):
            cells = list(row) + [None] * 3
            code = str(cells[col['code']] or '').strip()
            name = str(cells[col['name']] or '').strip()
            if not code and not name:
                continue
            if not CODE_RE.match(code) or code.upper() == ALL:
                acl.warnings.append(f"'{SHEET_PROJECTS}' dòng {n}: mã '{code}' không hợp lệ, bỏ dòng.")
                continue
            if code in acl.projects:
                raise AccessBookError(f"Sheet '{SHEET_PROJECTS}': mã '{code}' xuất hiện hai lần (dòng {n}).")
            acl.projects[code] = dict(name=name or code, aliases=_split(cells[col['aliases']]))
        rows = list(wb[SHEET_PEOPLE].iter_rows(values_only=True))
        if not rows:
            raise AccessBookError(f"Sheet '{SHEET_PEOPLE}' trống.")
        col = _header_map(rows[0], {'email': 'email', 'codes': 'ma du an'}, SHEET_PEOPLE)
        people = {}
        for n, row in enumerate(rows[1:], start=2):
            cells = list(row) + [None] * 2
            email = str(cells[col['email']] or '').strip().lower()
            raw_codes = _split(cells[col['codes']])
            if not email and not raw_codes:
                continue
            if '@' not in email or ' ' in email:
                acl.warnings.append(f"'{SHEET_PEOPLE}' dòng {n}: email '{email}' không hợp lệ, bỏ dòng.")
                continue
            codes = set()
            for c in raw_codes:
                if c.upper() == ALL:
                    codes.add(ALL)
                elif c in acl.projects:
                    codes.add(c)
                else:
                    acl.warnings.append(f"'{SHEET_PEOPLE}' dòng {n}: mã '{c}' không có trong sheet '{SHEET_PROJECTS}', bỏ mã này.")
            people.setdefault(email, set()).update(codes)
        acl.people = {e: frozenset(c) for e, c in people.items()}
        return acl
    finally:
        wb.close()


class Reader:
    """Giữ danh sách hiện hành; đọc lại khi file đổi (mtime/size), tối đa mỗi `interval` giây. Lỗi -> giữ bản cũ."""

    def __init__(self, path, interval=CHECK_SECONDS, log=print):
        self.path = path
        self.interval = interval
        self.log = log
        self._lock = threading.Lock()
        self._acl = None
        self._stamp = None
        self._checked = 0.0
        self.last_error = ''

    def current(self):
        """AccessList đọc được gần nhất, hoặc None khi chưa từng đọc được (khi đó mọi người dùng link bị từ chối)."""
        now = time.monotonic()
        with self._lock:
            if self._acl is not None and now - self._checked < self.interval:
                return self._acl
            self._checked = now
            try:
                st = os.stat(self.path)
                stamp = (st.st_mtime_ns, st.st_size)
            except OSError as exc:
                self._fail(f'Không thấy file phân quyền {self.path!r}: {exc}')
                return self._acl
            if stamp == self._stamp and self._acl is not None:
                return self._acl
            try:
                acl = load(self.path)
            except AccessBookError as exc:
                self._fail(str(exc))
                return self._acl
            self._acl, self._stamp, self.last_error = acl, stamp, ''
            self.log(f'access book loaded: {len(acl.projects)} projects, {len(acl.people)} people'
                     + (f', {len(acl.warnings)} rows/codes skipped' if acl.warnings else ''))
            for w in acl.warnings:
                self.log(f'access book: {w}')
            return acl

    def _fail(self, message):
        if message != self.last_error:
            self.log(f'access book NOT reloaded ({"keeping previous list" if self._acl else "no list yet: link users refused"}): {message}')
        self.last_error = message
