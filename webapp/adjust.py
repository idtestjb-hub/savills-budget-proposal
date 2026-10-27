"""
Điều chỉnh ngân sách trên web: đọc và ghi sheet '4. Điều chỉnh' của bản giao (budget_adjustment.py dựng sheet này).

Sheet đã có đủ cơ chế của chức năng "Budget Adjustment – Dynamic Detail Sub-Rows": mỗi mã ngân sách một dòng Tổng
(loại điều chỉnh ở cột D, trượt giá % ở L), các dòng Chi tiết ngay bên dưới (SL gốc G, đơn giá gốc H, thành tiền gốc I,
SL mới J, đơn giá mới K); công thức thành tiền mới M, chênh lệch N, % O ("N/A" khi gốc 0) và các ô tháng của sheet quỹ
chạy theo tỉ lệ M / I. Trang web chỉ đọc sheet và ghi lại các ô nhập D, L, J, K; mọi con số khác do công thức của
template tính khi Excel mở file.

Khoá liên kết là mã (cột A) + sheet quỹ (cột P) của dòng Tổng, và thứ tự dòng Chi tiết trong mã đó; không dùng số dòng
Excel làm khoá (dòng chỉ được tìm lại khi đọc file).

Quy tắc (người dùng duyệt 20/10/2026):
- Mỗi mã một loại điều chỉnh: '' (giữ số gốc), 'Số lượng', 'Đơn giá', 'Số lượng + Đơn giá' (thêm 27/10/2026, change
  add-qty-and-price-adjustment), 'Trượt giá'.
- Số lượng: chỉ SL mới sửa được; dòng có SL khoá (cột J là công thức, dòng gộp "khoản") giữ nguyên.
  Đơn giá: chỉ đơn giá mới. Số lượng + Đơn giá: SL mới × đơn giá mới (dòng SL khoá giữ SL gốc). Trượt giá: chỉ % trên
  dòng Tổng (cho phép âm). Mã không có dòng Chi tiết: chỉ trượt giá.
- Sheet của bản giao cũ (trước loại Số lượng + Đơn giá) được nâng cấp khi lưu: công thức M của dòng Chi tiết và danh
  sách chọn cột D viết lại theo bản hiện tại; ba loại cũ cho đúng số như trước.
- SL mới và đơn giá mới không được âm.
- Các ô không thuộc loại đã chọn vẫn được ghi đúng giá trị gửi lên, nhưng công thức của template bỏ qua chúng.
"""
import re

import openpyxl

import budget_adjustment as ba

SHEET = ba.SHEET_NAME
TYPES = ('',) + tuple(ba.ADJUSTMENT_TYPES)
TYPE_QTY, TYPE_PRICE, TYPE_QTY_PRICE, TYPE_INFLATION = ba.TYPE_QTY, ba.TYPE_PRICE, ba.TYPE_QTY_PRICE, ba.TYPE_INFLATION
DETAIL_TYPES = (TYPE_QTY, TYPE_PRICE, TYPE_QTY_PRICE)          # cần dòng Chi tiết
C = ba.COL
FUND_SHORT = {'2. Budget-Management Fund': 'MF', '2.2 Common area Fund': 'CA'}
FUND_VI = {'MF': 'Quỹ quản lý vận hành', 'CA': 'Quỹ khai thác khu vực chung'}
CODE_RE = re.compile(r'^[A-Z][A-Z0-9#.]*[a-z]?$')


class AdjustError(ValueError):
    pass


def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _text(v):
    return str(v).strip() if v is not None else ''


def key_of(code, fund_sheet):
    return f'{FUND_SHORT.get(fund_sheet, fund_sheet)}|{code}'


def _section(code):
    return 'R' if code.startswith('R') else ('E' if code.startswith('E') else '')


def _scan(ws):
    """[(parent_row, [sub_rows])] theo thứ tự trên sheet."""
    blocks, current = [], None
    for r in range(ba.FIRST_DATA_ROW, ws.max_row + 1):
        kind = _text(ws.cell(row=r, column=C['kind']).value)
        if kind == ba.ROW_KIND_TOTAL:
            current = (r, [])
            blocks.append(current)
        elif kind == ba.ROW_KIND_DETAIL and current is not None:
            current[1].append(r)
    return blocks


REMARK_COL = 20     # T của sheet quỹ: Remarks / Ghi chú của năm mới (generate_project_budget._REMARKS_COL)


def _fund_remark(wb, fund_sheet, fund_row):
    """Remark của năm mới của một mã: ô T tại dòng của mã trên sheet quỹ (cột fund_row của sheet điều chỉnh).
    Chuỗi rỗng khi không tìm được dòng, hoặc ô là công thức (không đọc được giá trị khi chưa tính)."""
    if fund_sheet not in wb.sheetnames or not isinstance(fund_row, (int, float)) or isinstance(fund_row, bool):
        return ''
    text = _text(wb[fund_sheet].cell(row=int(fund_row), column=REMARK_COL).value)
    return '' if text.startswith('=') else text


def read_items(path):
    """Các mã trên sheet '4. Điều chỉnh' của bản giao `path`, cùng giá trị nhập hiện tại (D, L, J, K).

    Trả về list dict: key, code, name, fund, fund_sheet, section, adj_type, inflation, amount (thành tiền gốc),
    has_subs, subs [{idx, desc, unit, qty, unit_price, amount, new_qty, new_price, qty_editable}], remark (năm mới)."""
    wb = openpyxl.load_workbook(path)
    try:
        if SHEET not in wb.sheetnames:
            raise AdjustError(f"Bản giao không có sheet '{SHEET}' (bản giao cũ hơn chức năng điều chỉnh).")
        ws = wb[SHEET]
        items = []
        for prow, srows in _scan(ws):
            g = lambda col, r=prow: ws.cell(row=r, column=C[col]).value
            code, fund_sheet = _text(g('code')), _text(g('fund_sheet'))
            subs = []
            for i, r in enumerate(srows):
                qty_cell = ws.cell(row=r, column=C['new_qty']).value
                editable = not (isinstance(qty_cell, str) and qty_cell.startswith('='))
                qty, price, amount = (_num(ws.cell(row=r, column=C[k]).value) or 0.0 for k in ('qty', 'unit_price', 'amount'))
                new_price = _num(ws.cell(row=r, column=C['new_price']).value)
                subs.append(dict(idx=i, desc=_text(ws.cell(row=r, column=C['desc']).value),
                                 unit=_text(ws.cell(row=r, column=C['unit']).value), qty=qty, unit_price=price,
                                 amount=amount, new_qty=(_num(qty_cell) if editable else qty),
                                 new_price=price if new_price is None else new_price, qty_editable=editable))
            amount = sum(s['amount'] for s in subs) if subs else (_num(g('amount')) or 0.0)
            adj_type = _text(g('adj_type'))
            items.append(dict(key=key_of(code, fund_sheet), code=code, name=_text(g('name')),
                              fund=FUND_SHORT.get(fund_sheet, fund_sheet), fund_sheet=fund_sheet, section=_section(code),
                              adj_type=adj_type if adj_type in TYPES else '', inflation=_num(g('inflation')) or 0.0,
                              amount=amount, has_subs=bool(subs), subs=subs,
                              remark=_fund_remark(wb, fund_sheet, g('fund_row'))))
        return items
    finally:
        wb.close()


def new_amount(item, adj_type=None, inflation=None, subs=None):
    """Thành tiền mới của một mã theo đúng công thức của template (để xem trước và để kiểm tra)."""
    adj_type = item['adj_type'] if adj_type is None else adj_type
    inflation = item['inflation'] if inflation is None else inflation
    subs = item['subs'] if subs is None else subs
    if not item['has_subs']:
        return item['amount'] * (1 + inflation) if adj_type == TYPE_INFLATION else item['amount']
    total = 0.0
    for s in subs:
        if adj_type == TYPE_QTY:
            total += (s['new_qty'] if s['qty_editable'] else s['qty']) * s['unit_price']
        elif adj_type == TYPE_PRICE:
            total += s['qty'] * s['new_price']
        elif adj_type == TYPE_QTY_PRICE:
            total += (s['new_qty'] if s['qty_editable'] else s['qty']) * s['new_price']
        elif adj_type == TYPE_INFLATION:
            total += s['amount'] * (1 + inflation)
        else:
            total += s['amount']
    return total


def _validate(edit, item):
    adj_type = _text(edit.get('adj_type'))
    if adj_type not in TYPES:
        raise AdjustError(f"{item['code']}: loại điều chỉnh '{adj_type}' không hợp lệ.")
    if adj_type in DETAIL_TYPES and not item['has_subs']:
        raise AdjustError(f"{item['code']}: mã không có dòng chi tiết, chỉ điều chỉnh được bằng trượt giá.")
    try:
        inflation = float(edit.get('inflation') or 0)
    except (TypeError, ValueError):
        raise AdjustError(f"{item['code']}: trượt giá % không phải số.")
    if inflation <= -1:
        raise AdjustError(f"{item['code']}: trượt giá phải lớn hơn -100%.")
    subs = {}
    for s in edit.get('subs') or []:
        try:
            idx = int(s['idx'])
        except (KeyError, TypeError, ValueError):
            raise AdjustError(f"{item['code']}: dòng chi tiết không có số thứ tự.")
        if not 0 <= idx < len(item['subs']):
            raise AdjustError(f"{item['code']}: không có dòng chi tiết thứ {idx + 1}.")
        vals = {}
        for k in ('new_qty', 'new_price'):
            if s.get(k) in (None, ''):
                continue
            try:
                v = float(s[k])
            except (TypeError, ValueError):
                raise AdjustError(f"{item['code']}, dòng chi tiết {idx + 1}: {k} không phải số.")
            if v < 0:
                raise AdjustError(f"{item['code']}, dòng chi tiết {idx + 1}: số lượng và đơn giá không được âm.")
            vals[k] = v
        subs[idx] = vals
    return adj_type, inflation, subs


MAX_REMARK = 5000


def _validate_remark(wb, code, remark, fund_sheet, fund_row):
    """(sheet quỹ, dòng, nội dung) để ghi vào ô Remarks (T) của mã. Dòng của mã trên sheet quỹ lấy từ sheet điều chỉnh."""
    if not isinstance(remark, str):
        raise AdjustError(f'{code}: remark phải là chữ.')
    text = remark.strip()
    if len(text) > MAX_REMARK:
        raise AdjustError(f'{code}: remark dài quá {MAX_REMARK} ký tự.')
    if text.startswith('='):
        raise AdjustError(f'{code}: remark không được bắt đầu bằng dấu "=" (Excel sẽ coi là công thức).')
    if fund_sheet not in wb.sheetnames or not isinstance(fund_row, (int, float)) or isinstance(fund_row, bool):
        raise AdjustError(f'{code}: không tìm được dòng của mã trên sheet quỹ để ghi remark.')
    return fund_sheet, int(fund_row), text


def upgrade_sheet(ws, blocks):
    """Viết lại công thức M của mọi dòng Chi tiết và danh sách chọn cột D theo bản hiện tại của budget_adjustment, để
    sheet của bản giao cũ dùng được loại Số lượng + Đơn giá. Công thức chỉ phụ thuộc số dòng nên viết lại nhiều lần
    vẫn như nhau; ba loại cũ cho đúng số như trước. `blocks`: (dòng Tổng, [dòng Chi tiết], ...) như index của apply_edits."""
    for block in blocks:
        prow, srows = block[0], block[1]
        for r in srows:
            ws.cell(row=r, column=C['new_amount']).value = ba.detail_formula(prow, r)
    keep = [dv for dv in ws.data_validations.dataValidation
            if not (dv.type == 'list' and TYPE_INFLATION in str(dv.formula1 or ''))]
    ws.data_validations.dataValidation = keep
    dv = ba.type_validation()
    ws.add_data_validation(dv)
    for block in blocks:
        dv.add(ws.cell(row=block[0], column=C['adj_type']))


def apply_edits(wb, edits):
    """Ghi các chỉnh sửa vào sheet '4. Điều chỉnh' của workbook `wb` (đã mở, không phải data_only).

    `edits`: [{key, adj_type, inflation, subs: [{idx, new_qty, new_price}], remark?}]. Mã không có trong `edits` giữ nguyên.
    `remark` (tuỳ chọn): remark năm mới, ghi vào ô T của dòng mã trên sheet quỹ; bỏ trống khóa này thì ô T giữ nguyên.
    Trả về danh sách mã đã ghi. Lỗi bất kỳ (khoá không có, giá trị sai) thì không ghi gì và ném AdjustError."""
    if SHEET not in wb.sheetnames:
        raise AdjustError(f"Bản giao không có sheet '{SHEET}'.")
    ws = wb[SHEET]
    index = {}
    for prow, srows in _scan(ws):
        code = _text(ws.cell(row=prow, column=C['code']).value)
        fund_sheet = _text(ws.cell(row=prow, column=C['fund_sheet']).value)
        editable = []
        for r in srows:
            v = ws.cell(row=r, column=C['new_qty']).value
            editable.append(not (isinstance(v, str) and v.startswith('=')))
        index[key_of(code, fund_sheet)] = (prow, srows, editable, code, fund_sheet,
                                           ws.cell(row=prow, column=C['fund_row']).value)
    plan, remarks = [], []
    for edit in edits:
        key = _text(edit.get('key'))
        if key not in index:
            raise AdjustError(f"Không có mã {key} trên sheet '{SHEET}'.")
        prow, srows, editable, code, fund_sheet, fund_row = index[key]
        item = dict(code=code, has_subs=bool(srows), subs=[None] * len(srows))
        plan.append((prow, srows, editable, code) + _validate(edit, item))
        if edit.get('remark') is not None:          # chỉ khi gửi lên: mã không sửa remark giữ nguyên ô T
            remarks.append(_validate_remark(wb, code, edit['remark'], fund_sheet, fund_row))
    upgrade_sheet(ws, index.values())
    written = []
    for sheet, row, text in remarks:
        wb[sheet].cell(row=row, column=REMARK_COL).value = text or None
    for prow, srows, editable, code, adj_type, inflation, subs in plan:
        ws.cell(row=prow, column=C['adj_type']).value = adj_type or None
        ws.cell(row=prow, column=C['inflation']).value = inflation
        for idx, vals in subs.items():
            r = srows[idx]
            if 'new_qty' in vals and editable[idx]:
                ws.cell(row=r, column=C['new_qty']).value = vals['new_qty']
            if 'new_price' in vals:
                ws.cell(row=r, column=C['new_price']).value = vals['new_price']
        written.append(code)
    return written


N_CONVERTED_RE = re.compile(r'^Duyệt NS \d{4} \(quy đổi\)$')    # cột số duyệt năm N đã quy đổi (bố cục cũ và mới)
MEASURE_HEADS = (('n1', 'Duyệt NS'), ('actual', 'Thực tế'), ('expected', 'Dự kiến cả năm'))
N1_MARK, NO_COLUMN = 'năm trước', 'File không có số'


def _measure_of(header):
    """'n1' | 'actual' | 'expected' cho tiêu đề một cột năm trước của sheet Review, None với cột khác hoặc cột 'File
    không có số' (change add-review-prior-and-actual-columns)."""
    h = _text(header)
    if not h or NO_COLUMN in h:
        return None
    for kind, head in MEASURE_HEADS:
        if h.startswith(head) and (kind != 'n1' or N1_MARK in h):
            return kind
    return None


def review_columns(analysis_path):
    """Số theo key từ sheet 'Review': {'approved': {key: duyệt năm N quy đổi}, 'n1' | 'actual' | 'expected': {key: số},
    'labels': {kind: tiêu đề dòng đầu}}. Cột tìm theo tiêu đề ở dòng 'Mã' của từng quỹ, nên đọc được cả sheet trước change
    add-review-prior-and-actual-columns (cột duyệt ở vị trí 5) và sau (cột năm trước đứng trước). {} khi không có sheet."""
    out = {}
    try:
        wb = openpyxl.load_workbook(analysis_path, read_only=True, data_only=True)
    except Exception:
        return out
    try:
        if 'Review' not in wb.sheetnames:
            return out
        out = dict(approved={}, n1={}, actual={}, expected={}, labels={})
        fund, cols = None, {'approved': 4}
        for row in wb['Review'].iter_rows(values_only=True):
            a = _text(row[0]) if row else ''
            for short, vi in FUND_VI.items():
                if a.startswith(vi):
                    fund = short
            if a == 'Mã':
                cols = {}
                for i, h in enumerate(row):
                    if N_CONVERTED_RE.match(_text(h)):
                        cols['approved'] = i
                    kind = _measure_of(h)
                    if kind:
                        cols[kind] = i
                        out['labels'].setdefault(kind, _text(h).split(chr(10))[0])
                cols.setdefault('approved', 4)
                continue
            if fund and CODE_RE.match(a):
                key = f'{fund}|{a}'
                for kind, i in cols.items():
                    v = _num(row[i]) if i < len(row) else None
                    if v is not None:
                        out[kind][key] = out[kind].get(key, 0.0) + v
        return out
    finally:
        wb.close()


def approved_by_key(analysis_path):
    """{key: số duyệt năm cũ đã quy đổi} từ sheet 'Review' của bản phân tích (lượt review); {} khi không có sheet."""
    return review_columns(analysis_path).get('approved', {})


def review_years(analysis_path):
    """(năm duyệt, năm công cụ) từ tiêu đề sheet Review, hoặc (None, None)."""
    try:
        wb = openpyxl.load_workbook(analysis_path, read_only=True, data_only=True)
    except Exception:
        return None, None
    try:
        if 'Review' not in wb.sheetnames:
            return None, None
        title = _text(wb['Review']['A1'].value)
        years = re.findall(r'(20\d\d)', title)
        return (int(years[0]), int(years[1])) if len(years) >= 2 else (None, None)
    finally:
        wb.close()
