"""Bộ dữ liệu tham chiếu rút gọn, ẩn danh cho một dự án (change site-data-isolation).

Gói site của một dự án (và sau này một vai trò chỉ xem một dự án trên server) chỉ được mang dữ liệu của chính dự án đó cộng
với phần tham chiếu mà công cụ cần để lập ngân sách. Đo bằng một lượt Review có ghi vết mở file (05/11/2026, City Garden):
pipeline đọc đúng 14 file trong `data\\` (KEEP). Những file đó được chép sang gói qua `build()`:
- tên dự án khác đổi thành "Dự án tham chiếu NN" (cùng một mã cho cùng một tên ở mọi file, để các phép nối theo tên vẫn
  đúng); địa chỉ, tên file nguồn và các cột ghi chú thô bị xoá; số (diện tích, đơn giá, toạ độ) giữ nguyên để công cụ ra
  cùng số như trên Hub;
- tên của chính dự án (tên site, tên trong file đã duyệt) giữ nguyên, để quy tắc "bỏ chính dự án ra khỏi so sánh" vẫn chạy;
- tên các dự án nằm sẵn trong code (`master_comparables.HAND_VERIFIED_COMPARABLES`, `estimate_opex` dùng 'A&K Tower' và
  'Parking Building') giữ nguyên vì code tra theo đúng tên đó: đây là bộ tham chiếu của phương pháp, có trên Hub và trên
  sheet Comparison của mọi bản giao.
`find_leaks()` quét gói đã dựng: mọi tên toà nhà trong danh sách master (căn hộ + thương mại) và tên file của kho quét,
trừ tên của chính dự án và tên trong code, không được xuất hiện trong bất kỳ file văn bản hay ô chữ Excel nào của gói.
"""
import csv
import os
import re
import shutil
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
BUDGET_AGENT = os.path.dirname(HERE)
DATA_DIR = os.path.join(BUDGET_AGENT, 'data')

# Đúng các file một lượt Review mở (đo 05/11/2026, vết mở file đã chuẩn hoá đường dẫn). Thêm file vào đây khi pipeline đọc thêm; test_site_data kiểm sự tồn tại.
KEEP = (
    'generation_A_star_schema/Fact_CapexReserve.csv',
    'generation_A_star_schema/Fact_Capex_Rescanned.csv',
    'generation_A_star_schema/Fact_OPEX.csv',
    'generation_B_verified/Ref_CPI_VN.csv',
    'generation_B_verified/Ref_LaborLawParams.csv',
    'generation_B_verified/Ref_UtilityTariffs.csv',
    'master_list_verified/Costing_Method_Catalogue.csv',
    'master_list_verified/Dim_Property_Residential.csv',
    'master_list_verified/Fact_ProjectLocation.csv',
    'master_list_verified/Fact_StaffingRatio_ByPosition.csv',
    'master_list_verified/Ref_ComparableVATBasis.csv',
    'real_budget_ranges/README.txt',
    'real_budget_ranges/Ref_RealBudgetValues.csv',
    'service_levels/Ref_ServiceLevelProjects.csv',
    'service_levels/Ref_ServiceLevelThresholds.csv',
)
# File có tên dự án: cột tên để ẩn danh, cột văn bản để xoá trắng. Cột kết thúc bằng "_raw" (ghi chép thô) luôn xoá.
MASK = {
    'master_list_verified/Dim_Property_Residential.csv': dict(
        name='Name', blank=('SourceRow', 'No', 'Address_Raw', 'Street', 'Ward', 'District_Raw', 'AddressParseStatus')),
    'master_list_verified/Fact_ProjectLocation.csv': dict(name='asset_name', blank=()),
    'generation_A_star_schema/Fact_CapexReserve.csv': dict(name='Project', blank=('SourceFile', 'Year1Sheet', 'LaterSheet')),
    'generation_A_star_schema/Fact_OPEX.csv': dict(name='Project', blank=('Source',)),
    'generation_A_star_schema/Fact_Capex_Rescanned.csv': dict(name='Project', blank=()),
    'master_list_verified/Ref_ComparableVATBasis.csv': dict(name='project_key', blank=()),
}
PSEUDONYM = 'Dự án tham chiếu {n:02d}'
# estimate_opex / estimate_capex_qty tra theo đúng tên này ('11D Thi Sach' không dấu là khoá của Fact_Capex_Rescanned).
CODE_NAMES_EXTRA = ('A&K Tower', 'Parking Building', '11D Thi Sach')
MIN_WORD = 4
TEXT_EXT = {'.py', '.txt', '.md', '.json', '.html', '.cmd', '.csv', '.pth', '._pth', '.yaml', '.yml'}
XLSX_EXT = {'.xlsx', '.xlsm'}
COMMERCIAL_CSV = os.path.join(DATA_DIR, 'master_list_verified', 'Dim_Property_Commercial.csv')
STORE_FILES_CSV = 'dim_file.csv'


def norm(name):
    """Khoá so tên: NFC, bỏ hoa thường và khoảng trắng hai đầu."""
    return unicodedata.normalize('NFC', str(name or '')).strip().casefold()


def code_names():
    """Tên dự án nằm trong code (giữ nguyên trong gói)."""
    try:
        from master_comparables import HAND_VERIFIED_COMPARABLES
        names = [c['name'] for c in HAND_VERIFIED_COMPARABLES]
    except Exception:  # noqa: BLE001
        names = []
    return set(names) | set(CODE_NAMES_EXTRA)


def _read_csv(path):
    """(dòng chú thích đầu file, header, rows) của một CSV có thể mở đầu bằng các dòng '#'."""
    with open(path, encoding='utf-8-sig', newline='') as fh:
        lines = fh.read().splitlines(keepends=True)
    i = 0
    while i < len(lines) and lines[i].startswith('#'):
        i += 1
    comments, body = lines[:i], lines[i:]
    rows = list(csv.reader(body))
    header, data = (rows[0], rows[1:]) if rows else ([], [])
    return comments, header, data


def _write_csv(path, comments, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8-sig', newline='') as fh:
        fh.writelines(comments)
        w = csv.writer(fh, lineterminator='\n')
        if header:
            w.writerow(header)
        w.writerows(rows)


class Pseudonyms:
    """Một mã cho một tên, cấp theo thứ tự gặp; tên được giữ (chính dự án, tên trong code) trả về nguyên văn."""

    def __init__(self, keep):
        self.keep = {norm(k) for k in keep if norm(k)}
        self.map = {}

    def __call__(self, name):
        key = norm(name)
        if not key or key in self.keep:
            return name
        if key not in self.map:
            self.map[key] = PSEUDONYM.format(n=len(self.map) + 1)
        return self.map[key]


def _mask_file(src, dst, rule, pseud):
    comments, header, rows = _read_csv(src)
    if not header:
        shutil.copy2(src, dst)
        return 0
    idx = {h: i for i, h in enumerate(header)}
    name_i = idx.get(rule['name'])
    blank_i = {idx[h] for h in rule['blank'] if h in idx} | {i for i, h in enumerate(header) if h.lower().endswith('_raw')}
    changed = 0
    for r in rows:
        if name_i is not None and name_i < len(r):
            new = pseud(r[name_i])
            if new != r[name_i]:
                r[name_i] = new
                changed += 1
        for i in blank_i:
            if i < len(r):
                r[i] = ''
    # Dòng chú thích đầu file có thể nhắc tên file nguồn của máy văn phòng: thay bằng một dòng ghi nguồn chung.
    if comments:
        comments = ['# Bản rút gọn cho gói site: tên dự án khác đã ẩn danh, cột văn bản thô đã xoá.\n']
    _write_csv(dst, comments, header, rows)
    return changed


def build(src_data, dst_data, own_names=(), keep_names=None):
    """Chép đúng các file KEEP từ `src_data` sang `dst_data`, ẩn danh theo MASK. Trả về dict(copied, masked, pseudonyms).
    `own_names`: tên của chính dự án (giữ nguyên). `keep_names`: tên trong code (mặc định code_names())."""
    keep = set(own_names) | (code_names() if keep_names is None else set(keep_names))
    pseud = Pseudonyms(keep)
    copied, masked = [], {}
    for rel in KEEP:
        src = os.path.join(src_data, *rel.split('/'))
        dst = os.path.join(dst_data, *rel.split('/'))
        if not os.path.isfile(src):
            raise FileNotFoundError(f'Thiếu file dữ liệu {rel} trong {src_data}')
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if rel in MASK:
            masked[rel] = _mask_file(src, dst, MASK[rel], pseud)
        else:
            shutil.copy2(src, dst)
        copied.append(rel)
    return dict(copied=copied, masked=masked, pseudonyms=dict(pseud.map))


GENERIC_TOKENS = {'budget', 'ngan', 'ngân', 'sach', 'sách', 'nam', 'năm', 'du', 'dự', 'toan', 'toán', 'ke', 'kế', 'hoach',
                  'hoạch', 'rv', 'rev', 'ver', 'version', 'final', 'phase', 'giai', 'đoạn', 'doan', 'ban', 'bản', 'nhap', 'nháp',
                  'operation', 'pre', 'opening', 'mf', 'ca', 'copy', 'noi', 'nội', 'bo', 'bộ', 'repaired', 'file', 'form', 'fund'}


def _names_something(stem):
    """Một tên file kho có nhắc tên dự án không: bỏ các từ chung (ngân sách, năm, rv, final...) và số; còn từ 3 chữ cái
    thì coi là có tên. 'NGÂN SÁCH NĂM 2026' -> không; 'Budget 2026 Sao Mai_rv1' -> có."""
    toks = [t for t in re.split(r'[^0-9A-Za-zÀ-ỹ]+', unicodedata.normalize('NFC', stem)) if t]
    rest = [t for t in toks if t.casefold() not in GENERIC_TOKENS and not t.isdigit()]
    return sum(ch.isalpha() for t in rest for ch in t) >= 3


def leak_words(src_data, own_names=(), store_dir=None, keep_names=None):
    """Những tên không được xuất hiện trong gói: tên toà nhà trong hai danh sách master và tên file của kho quét (nếu có
    `store_dir`), trừ tên của chính dự án và tên trong code; bỏ tên ngắn dưới MIN_WORD ký tự."""
    own = {norm(n) for n in own_names if norm(n)}
    keep = own | {norm(n) for n in (code_names() if keep_names is None else set(keep_names))}
    words = set()
    for rel in ('master_list_verified/Dim_Property_Residential.csv', 'master_list_verified/Dim_Property_Commercial.csv'):
        p = os.path.join(src_data, *rel.split('/'))
        if os.path.isfile(p):
            _, header, rows = _read_csv(p)
            if 'Name' in header:
                i = header.index('Name')
                words |= {r[i].strip() for r in rows if i < len(r) and r[i].strip()}
    if store_dir and os.path.isfile(os.path.join(store_dir, STORE_FILES_CSV)):
        _, header, rows = _read_csv(os.path.join(store_dir, STORE_FILES_CSV))
        if 'file_name' in header:
            i = header.index('file_name')
            stems = {os.path.splitext(r[i])[0].strip() for r in rows if i < len(r) and r[i].strip()}
            words |= {w for w in stems if _names_something(w)}
    out = set()
    for w in words:
        k = norm(w)
        letters = sum(ch.isalpha() for ch in k)
        # Bỏ: tên đã giữ, tên nằm trong một tên đã giữ, và tên chứa tên của chính dự án (ví dụ tên file duyệt của nó).
        if (len(k) >= MIN_WORD and letters >= 3 and k not in keep and not any(k in o for o in keep)
                and not any(o in k for o in own)):
            out.add(w)
    return sorted(out, key=norm)


def _xlsx_text(path):
    """Mọi chuỗi trong một workbook (ô chữ, tên sheet), đọc bằng openpyxl read-only; '' khi không mở được."""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=False)
    except Exception:  # noqa: BLE001
        return ''
    parts = []
    try:
        for ws in wb.worksheets:
            parts.append(ws.title)
            for row in ws.iter_rows(values_only=True):
                parts.extend(v for v in row if isinstance(v, str))
    except Exception:  # noqa: BLE001
        pass
    finally:
        wb.close()
    return chr(10).join(parts)


def find_leaks(pkg, words, skip_dirs=('python',)):
    """[(đường dẫn tương đối, [tên])] của mọi file văn bản hoặc Excel trong gói chứa một tên trong `words`
    (so không phân biệt hoa thường, NFC). Thư mục `skip_dirs` ở gốc gói không quét (runtime Python)."""
    keys = [(w, norm(w)) for w in words]
    hits = []
    for d, dirs, files in os.walk(pkg):
        if os.path.relpath(d, pkg).split(os.sep)[0] in skip_dirs:
            dirs[:] = []
            continue
        for f in files:
            p = os.path.join(d, f)
            ext = os.path.splitext(f)[1].lower()
            if ext in TEXT_EXT:
                try:
                    with open(p, encoding='utf-8', errors='ignore') as fh:
                        text = fh.read()
                except OSError:
                    continue
            elif ext in XLSX_EXT:
                text = _xlsx_text(p)
            else:
                continue
            low = norm(text)
            found = [w for w, k in keys if k in low]
            if found:
                hits.append((os.path.relpath(p, pkg), found[:5]))
    return hits
