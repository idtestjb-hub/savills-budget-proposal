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
  add-qty-and-price-adjustment), 'Trượt giá', 'Nhập số' (thêm 05/11/2026, change adjust-rows-for-zero-tool-codes).
- Số lượng: chỉ SL mới sửa được; dòng có SL khoá (cột J là công thức, dòng gộp "khoản") giữ nguyên.
  Đơn giá: chỉ đơn giá mới. Số lượng + Đơn giá: SL mới × đơn giá mới (dòng SL khoá giữ SL gốc). Trượt giá: chỉ % trên
  dòng Tổng (cho phép âm). Nhập số: số cả năm của từng dòng Chi tiết gõ ở ô đơn giá mới (K), không âm; dùng cho mã công
  cụ ra 0 (dòng do lượt Review thêm vào) nhưng chọn được ở mọi mã có dòng Chi tiết. Mã không có dòng Chi tiết: chỉ trượt giá.
- Sheet của bản giao cũ (trước loại Số lượng + Đơn giá) được nâng cấp khi lưu: công thức M của dòng Chi tiết và danh
  sách chọn cột D viết lại theo bản hiện tại; ba loại cũ cho đúng số như trước.
- SL mới và đơn giá mới không được âm.
- Các ô không thuộc loại đã chọn vẫn được ghi đúng giá trị gửi lên, nhưng công thức của template bỏ qua chúng.
"""
import os
import re

import openpyxl

import budget_adjustment as ba
import line_frequency as lf

SHEET = ba.SHEET_NAME
TYPES = ('',) + tuple(ba.ADJUSTMENT_TYPES)
TYPE_QTY, TYPE_PRICE, TYPE_QTY_PRICE, TYPE_INFLATION, TYPE_ENTER = (ba.TYPE_QTY, ba.TYPE_PRICE, ba.TYPE_QTY_PRICE,
                                                                    ba.TYPE_INFLATION, ba.TYPE_ENTER)
DETAIL_TYPES = (TYPE_QTY, TYPE_PRICE, TYPE_QTY_PRICE, TYPE_ENTER)          # cần dòng Chi tiết
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
    has_subs, zero_row (có dòng Chi tiết mà thành tiền gốc bằng 0: dòng công cụ ra 0), subs [{idx, desc, unit, qty, unit_price, amount, new_qty, new_price, qty_editable}], remark (năm mới)."""
    wb = openpyxl.load_workbook(path)
    try:
        return _read_wb(wb)
    finally:
        wb.close()


def _freq_of(wb, ws, prow, fund_sheet, fund_row):
    """Tần suất của một mã (change add-line-frequency): tần suất gốc, số lần gốc, tháng đầu gốc, 12 số tháng gốc; tần
    suất mới (AE), tháng đầu (AF), 12 ô tháng (AH:AS: dấu x của Optional hoặc số tiền của Schedule) và mã có đổi được
    tần suất không. Sheet của bản giao cũ (chưa có các ô này) đọc ra tần suất gốc, ô mới để trống."""
    g = lambda col: ws.cell(row=prow, column=col).value
    months = [_num(g(ba.MONTH_FIRST_COL + k)) or 0.0 for k in range(12)]
    freq, times, first = ba.original_frequency({'freq': g(C['freq']), 'months': months})
    if _num(g(C['orig_times'])):
        times, first = int(_num(g(C['orig_times']))), int(_num(g(C['orig_first'])) or 1)
        editable = ws.cell(row=prow, column=C['new_freq']).protection.locked is False
    else:                        # sheet cũ: mã có công thức riêng (EMH2, ô đã bọc '=(') không đổi được tần suất
        editable = True
        if fund_sheet in wb.sheetnames and isinstance(fund_row, (int, float)) and not isinstance(fund_row, bool):
            fws = wb[fund_sheet]
            cols = [ba.FUND_MONTH_FIRST_COL + k for k in range(12)] + ([] if freq == lf.SCHEDULE else [ba.FUND_MONTHLY_COL])
            editable = not any(_text(fws.cell(row=int(fund_row), column=c).value).startswith('=(') for c in cols)
    try:
        new_freq = lf.normalise(g(C['new_freq'])) or ''
    except ValueError:
        new_freq = ''
    first_month = _num(g(C['first_month']))
    inputs = [g(ba.MONTH_IN_FIRST_COL + k) for k in range(12)]
    return dict(freq=freq, freq_label=freq_label(freq), orig_times=times, orig_first=first, orig_months=months,
                new_freq=new_freq, first_month=int(first_month) if first_month else None,
                ticks=[_text(v) != '' and _num(v) is None for v in inputs],
                month_amounts=[_num(v) for v in inputs], freq_editable=editable)


def period_labels(path, workdir=None):
    """'MM/YYYY' của 12 tháng trong kỳ ngân sách: giá trị Excel đã tính của H8:S8 trên sheet quỹ (tiêu đề tháng của
    form), đọc từ bản Excel đã tính lại trong thư mục lượt (deliverable_recalc.xlsx) nếu có, không thì từ bản giao.
    [] khi không có giá trị đã tính hoặc ô không phải ngày (danh sách Tháng đầu khi đó chỉ ghi T1..T12)."""
    recalc = os.path.join(workdir, 'deliverable_recalc.xlsx') if workdir else None
    if recalc and os.path.exists(recalc):
        got = period_labels(recalc)
        if got:
            return got
    try:
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    except Exception:  # noqa: BLE001
        return []
    try:
        if '2. Budget-Management Fund' not in wb.sheetnames:
            return []
        row = next(wb['2. Budget-Management Fund'].iter_rows(min_row=8, max_row=8, min_col=8, max_col=19,
                                                            values_only=True), ())
        if len(row) != 12 or not all(hasattr(v, 'month') and hasattr(v, 'year') for v in row):
            return []
        return [f'{v.month:02d}/{v.year}' for v in row]
    finally:
        wb.close()


def freq_label(freq):
    """'Hàng quý (Quarterly)' ... như cột Tần suất của bảng điều chỉnh."""
    return f'{lf.LABEL_VI[freq]} ({freq})' if freq in lf.LABEL_VI else ''


def _read_wb(wb):
    """Như read_items, trên workbook đã mở."""
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
        # Dòng để PM điền (change leave-unpriced-lines-for-pm): dấu ở cột ẩn AY, lý do ở AZ; "chưa điền" khi ô nhập
        # của dòng Chi tiết còn trống hoặc 0.
        pm_fill = _text(g('pm_mark')) == ba.PM_MARK
        pm_empty = pm_fill and not any(_num(ws.cell(row=r, column=C['new_price']).value) for r in srows)
        items.append(dict(key=key_of(code, fund_sheet), code=code, name=_text(g('name')),
                          pm_fill=pm_fill, pm_reason=_text(g('pm_reason')) if pm_fill else '', pm_empty=pm_empty,
                          fund=FUND_SHORT.get(fund_sheet, fund_sheet), fund_sheet=fund_sheet, section=_section(code),
                          adj_type=adj_type if adj_type in TYPES else '', inflation=_num(g('inflation')) or 0.0,
                          amount=amount, has_subs=bool(subs), zero_row=bool(subs) and abs(amount) < 0.5, subs=subs,
                          remark=_fund_remark(wb, fund_sheet, g('fund_row')),
                          **_freq_of(wb, ws, prow, fund_sheet, g('fund_row'))))
    for it in items:
        it['remark_stale'] = remark_stale(it)
    return items


OFF_FORM_GROUP = '__off_form__'
OFF_FORM_NAME = 'Mã ngoài form 2027'


def add_groups(items, codes=None, groups=None):
    """Gắn nhóm của form 2027 cho từng mã, như sheet Review (review_import.group_chain): it['groups'] = [{code, name}]
    từ cấp trên xuống, không gồm chính mã đó; it['order'] = dòng của mã trên template (mã ngoài form: sau cùng, trong
    nhóm OFF_FORM_GROUP). Bảng điều chỉnh trên web dùng để xếp và cộng theo nhóm."""
    import review_import as ri
    codes = ri.template_codes() if codes is None else codes
    groups = ri.template_groups() if groups is None else groups
    for it in items:
        fund, code = it.get('fund'), it.get('code')
        row = (codes.get(fund) or {}).get(code)
        if row is None:
            it['groups'], it['order'] = [dict(code=OFF_FORM_GROUP, name=OFF_FORM_NAME)], 10 ** 6
            continue
        gs = (groups.get(fund) or {}).get('groups', {})
        it['groups'] = [dict(code=g, name=gs.get(g, {}).get('name', '')) for g in ri.group_chain(fund, code, row, groups)
                        if g != code]
        it['order'] = row
    return items


def new_amount(item, adj_type=None, inflation=None, subs=None, freq=None):
    """Thành tiền mới của một mã theo đúng công thức của sheet (để xem trước và để kiểm tra). `freq` (tuỳ chọn):
    {new_freq, ticks, month_amounts} thay cho giá trị đang lưu. Tần suất mới (change add-line-frequency, cột M của
    dòng Tổng): Schedule = tổng 12 tháng nhập; tần suất khác = số theo loại điều chỉnh × số lần mới / số lần gốc."""
    base = _type_amount(item, adj_type, inflation, subs)
    f = dict(item, **(freq or {}))
    new_freq = f.get('new_freq') or ''
    if not new_freq:
        return base
    if new_freq == lf.SCHEDULE:
        return sum(v or 0.0 for v in f.get('month_amounts') or [])
    times = new_times(f)
    return base * times / (item.get('orig_times') or 1)


def new_times(f):
    """Số lần mới như cột AG: trống = số lần gốc; Optional = số tháng đánh dấu; tần suất khác = số lần của mẫu."""
    new_freq = f.get('new_freq') or ''
    if not new_freq:
        return f.get('orig_times') or 12
    if new_freq == lf.OPTIONAL:
        return sum(1 for t in f.get('ticks') or [] if t)
    return lf.TIMES[new_freq]


def freq_months(f):
    """(tần suất đang dùng, các tháng chi T1..T12) của một mã theo các ô đang có."""
    eff = f.get('new_freq') or f.get('freq') or lf.MONTHLY
    if eff == lf.OPTIONAL:
        if f.get('new_freq'):
            return eff, [k + 1 for k, t in enumerate(f.get('ticks') or []) if t]
        return eff, [k + 1 for k, v in enumerate(f.get('orig_months') or []) if abs(v or 0) >= 1e-9]
    if eff == lf.SCHEDULE:
        source = f.get('month_amounts') if f.get('new_freq') else f.get('orig_months')
        return eff, [k + 1 for k, v in enumerate(source or []) if abs(v or 0) >= 0.5]
    if eff in lf.CYCLIC:
        first = lf.first_in_use(eff, f.get('first_month'), f.get('orig_first') or 1)
        return eff, list(range(first, 13, lf.STEP[eff]))
    return eff, list(range(1, 13))


def freq_sentence(item, amount=None, freq=None):
    """Câu tần suất của remark cho các ô đang có (None khi Hàng tháng)."""
    f = dict(item, **(freq or {}))
    eff, months = freq_months(f)
    if eff == lf.MONTHLY:
        return None
    amount = new_amount(item, freq=freq) if amount is None else amount
    times = len(months) if eff in (lf.OPTIONAL, lf.SCHEDULE) else lf.TIMES[eff]
    return lf.sentence(eff, round(amount / times) if times else 0, months)


def remark_stale(item):
    """True khi câu tần suất ở cuối remark không khớp tần suất đang có (sửa offline trong Excel: web báo
    "Remark chưa theo tần suất mới"). Dòng 0 đồng không xét."""
    if abs(new_amount(item)) < 0.5:
        return False
    if not item.get('new_freq') and item.get('freq') in (lf.MONTHLY, lf.SCHEDULE):
        return False                 # a line the tool wrote Monthly or Schedule (ramped) carries no sentence
    want = freq_sentence(item)
    lines = (item.get('remark') or '').rstrip().split('\n')
    last = lines[-1] if lines else ''
    if want is None:
        return lf.is_sentence(last)
    return last.strip() != want


def fixed_remark(item, current):
    """Remark của một dòng bị cờ "Remark chưa theo tần suất mới" sau khi cập nhật (change fix-stale-frequency-remarks,
    design D2): chỉ câu tần suất ở cuối được thay theo tần suất và thành tiền đang có trên sheet 4, như một lần lưu
    trên web; phần PM viết giữ nguyên; Hàng tháng thì bỏ câu; remark chưa có câu thì thêm vào cuối."""
    return lf.with_sentence(current or '', freq_sentence(item))


FORMULA_REMARK = 'remark là công thức Excel'


def _type_amount(item, adj_type=None, inflation=None, subs=None):
    """Thành tiền theo loại điều chỉnh, chưa tính tần suất."""
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
        elif adj_type == TYPE_ENTER:
            total += s['new_price']
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
    return adj_type, inflation, subs, _validate_freq(edit, item)


def _validate_freq(edit, item):
    """Ô tần suất của một mã (change add-line-frequency); None khi lần lưu không gửi khoá new_freq (giữ nguyên ô)."""
    if 'new_freq' not in edit:
        return None
    code = item['code']
    raw = _text(edit.get('new_freq'))
    try:
        new_freq = lf.normalise(raw) or ''
    except ValueError:
        raise AdjustError(f"{code}: tần suất '{raw}' không hợp lệ.")
    if new_freq and not item.get('freq_editable', True):
        raise AdjustError(f'{code}: dòng quỹ của mã này là công thức riêng, không đổi được tần suất.')
    first = edit.get('first_month')
    try:
        first = None if first in (None, '') else int(first)
    except (TypeError, ValueError):
        raise AdjustError(f'{code}: tháng đầu không phải số.')
    if new_freq in lf.CYCLIC:
        error = lf.first_month_error(new_freq, lf.first_in_use(new_freq, first, item.get('orig_first') or 1))
        if error:
            raise AdjustError(f'{code}: {error}.')
    ticks = [bool(t) for t in (list(edit.get('ticks') or []) + [False] * 12)[:12]]
    amounts = []
    for k, v in enumerate((list(edit.get('month_amounts') or []) + [None] * 12)[:12]):
        if v in (None, ''):
            amounts.append(None)
            continue
        try:
            v = float(v)
        except (TypeError, ValueError):
            raise AdjustError(f'{code}: số tiền tháng T{k + 1} không phải số.')
        if v < 0 and new_freq == lf.SCHEDULE:
            raise AdjustError(f'{code}: số tiền tháng T{k + 1} không được âm.')
        amounts.append(v)
    if new_freq == lf.OPTIONAL and not 1 <= sum(ticks) <= 11:
        raise AdjustError(f'{code}: Không theo chu kỳ phải chọn từ 1 đến 11 tháng (chọn Hàng tháng khi chi đủ 12 tháng).')
    return dict(new_freq=new_freq, first_month=first if new_freq in lf.CYCLIC else None,
                ticks=ticks if new_freq == lf.OPTIONAL else [False] * 12,
                month_amounts=amounts if new_freq == lf.SCHEDULE else [None] * 12)


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


def _write_freq(wb, ws, prow, item, adj_type, inflation, subs, freq):
    """Ghi các ô tần suất (AE, AF, AH:AS) của một dòng Tổng và thay câu tần suất ở cuối remark của mã (design D8):
    phần remark của PM giữ nguyên, câu cuối do công cụ viết được thay (bỏ khi Hàng tháng). Remark là công thức Excel
    thì giữ nguyên ô và trả về lý do bỏ qua (change fix-stale-frequency-remarks, D3); ngược lại trả về None."""
    ws.cell(row=prow, column=C['new_freq']).value = freq['new_freq'] or None
    ws.cell(row=prow, column=C['first_month']).value = freq['first_month']
    for k in range(12):
        cell = ws.cell(row=prow, column=ba.MONTH_IN_FIRST_COL + k)
        if freq['new_freq'] == lf.OPTIONAL:
            cell.value = 'x' if freq['ticks'][k] else None
        elif freq['new_freq'] == lf.SCHEDULE:
            cell.value = freq['month_amounts'][k]
        else:
            cell.value = None
    new_subs = [dict(s, **subs.get(i, {})) for i, s in enumerate(item['subs'])]
    amount = new_amount(item, adj_type, inflation, new_subs, freq)
    sheet, row = item['fund_sheet'], ws.cell(row=prow, column=C['fund_row']).value
    if sheet in wb.sheetnames and isinstance(row, (int, float)):
        cell = wb[sheet].cell(row=int(row), column=REMARK_COL)
        if isinstance(cell.value, str) and cell.value.startswith('='):
            return FORMULA_REMARK
        current = cell.value if isinstance(cell.value, str) else ''
        cell.value = lf.with_sentence(current, freq_sentence(item, amount, freq)) or None
    return None


def apply_edits(wb, edits, report=None):
    """Ghi các chỉnh sửa vào sheet '4. Điều chỉnh' của workbook `wb` (đã mở, không phải data_only).

    `edits`: [{key, adj_type, inflation, subs: [{idx, new_qty, new_price}], remark?}]. Mã không có trong `edits` giữ nguyên.
    `remark` (tuỳ chọn): remark năm mới, ghi vào ô T của dòng mã trên sheet quỹ; bỏ trống khóa này thì ô T giữ nguyên.
    `{key, fix_remark: true}` (không kèm khoá nào khác; change fix-stale-frequency-remarks): chỉ cập nhật câu tần suất ở
    cuối remark của một dòng đang bị cờ "Remark chưa theo tần suất mới", không ghi ô nào của sheet 4.
    Trả về danh sách mã đã ghi trên sheet 4. `report` (dict, tuỳ chọn) nhận remarks_fixed [mã] và remarks_skipped
    [(mã, lý do)]. Lỗi bất kỳ (khoá không có, giá trị sai) thì không ghi gì và ném AdjustError."""
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
    items = {it['key']: it for it in _read_wb(wb)}
    plan, remarks, fixes, seen = [], [], [], set()
    for edit in edits:
        key = _text(edit.get('key'))
        if key not in index:
            raise AdjustError(f"Không có mã {key} trên sheet '{SHEET}'.")
        if key in seen:
            raise AdjustError(f'{key}: mã được gửi hai lần trong một lần lưu.')
        seen.add(key)
        prow, srows, editable, code, fund_sheet, fund_row = index[key]
        if edit.get('fix_remark'):
            if set(edit) - {'key', 'fix_remark'}:
                raise AdjustError(f'{code}: lần cập nhật remark không được kèm thay đổi khác.')
            fixes.append(key)
            continue
        plan.append((prow, srows, editable, code) + _validate(edit, items[key]))
        if edit.get('remark') is not None:          # chỉ khi gửi lên: mã không sửa remark giữ nguyên ô T
            remarks.append(_validate_remark(wb, code, edit['remark'], fund_sheet, fund_row))
    fixed, skipped = [], []
    if report is not None:
        report['remarks_fixed'], report['remarks_skipped'] = fixed, skipped
    if plan:                                        # chỉ cập nhật remark: không đụng sheet 4, kể cả nâng cấp sheet cũ
        ba.upgrade(wb)                              # sheet cũ: thêm các ô tần suất, số không đổi
        upgrade_sheet(ws, index.values())
    written = []
    for sheet, row, text in remarks:
        wb[sheet].cell(row=row, column=REMARK_COL).value = text or None
    sent_remark = {(s, r) for s, r, _t in remarks}
    for prow, srows, editable, code, adj_type, inflation, subs, freq in plan:
        if freq is not None:
            why = _write_freq(wb, ws, prow, items[key_of(code, _text(ws.cell(row=prow, column=C['fund_sheet']).value))],
                              adj_type, inflation, subs, freq)
            if why:
                skipped.append((code, why))
        ws.cell(row=prow, column=C['adj_type']).value = adj_type or None
        ws.cell(row=prow, column=C['inflation']).value = inflation
        for idx, vals in subs.items():
            r = srows[idx]
            if 'new_qty' in vals and editable[idx]:
                ws.cell(row=r, column=C['new_qty']).value = vals['new_qty']
            if 'new_price' in vals:
                ws.cell(row=r, column=C['new_price']).value = vals['new_price']
        it = items[key_of(code, _text(ws.cell(row=prow, column=C['fund_sheet']).value))]
        _pm_remark(wb, ws, prow, srows, sent_remark, it, adj_type, inflation, subs, freq)
        written.append(code)
    for key in fixes:
        _fix_remark(wb, items[key], index[key], fixed, skipped)
    return written


def _fix_remark(wb, item, entry, fixed, skipped):
    """Cập nhật câu tần suất ở cuối remark của một dòng (design D1-D3): dòng không còn bị cờ thì bỏ qua (không đếm);
    remark là công thức thì giữ nguyên và ghi vào `skipped`."""
    _prow, _srows, _editable, code, fund_sheet, fund_row = entry
    if not item.get('remark_stale'):
        return
    if fund_sheet not in wb.sheetnames or not isinstance(fund_row, (int, float)) or isinstance(fund_row, bool):
        skipped.append((code, 'không tìm được dòng của mã trên sheet quỹ'))
        return
    cell = wb[fund_sheet].cell(row=int(fund_row), column=REMARK_COL)
    if isinstance(cell.value, str) and cell.value.startswith('='):
        skipped.append((code, FORMULA_REMARK))
        return
    cell.value = fixed_remark(item, cell.value if isinstance(cell.value, str) else '') or None
    fixed.append(code)


PM_LEAD = 'PM điền: '
PM_FILLED_LEAD = 'Số do PM nhập: {figure} VND/năm. Công cụ không tính được: '


def pm_remark_text(remark, figure):
    """Remark của dòng để PM điền theo số PM nhập (spec budget-web-adjust-table): có số thì "Số do PM nhập: <số>
    VND/năm. Công cụ không tính được: <lý do>", không có số thì "PM điền: <lý do>"; phần sau lý do (câu VAT, câu tần
    suất) giữ nguyên. Remark không mở đầu bằng một trong hai câu đó (PM đã tự viết) thì trả về nguyên như cũ."""
    text = remark or ''
    m = re.match(r'^Số do PM nhập: [\d,.]+ VND/năm\. Công cụ không tính được: ', text)
    if text.startswith(PM_LEAD):
        body = text[len(PM_LEAD):]
    elif m:
        body = text[m.end():]
    else:
        return text
    if figure:
        return PM_FILLED_LEAD.format(figure=f'{figure:,.0f}') + body
    return PM_LEAD + body


def _pm_remark(wb, ws, prow, srows, sent, item=None, adj_type=None, inflation=None, subs=None, freq=None):
    """Sau khi ghi một dòng để PM điền: viết lại câu đầu remark trên sheet quỹ theo số PM nhập (trừ khi lần lưu
    này gửi remark riêng của mã). Dòng không phải Hàng tháng (change default-frequency-from-real-budgets, D6): có số
    thì remark kết thúc bằng câu tần suất theo số đó, chưa có số thì không có câu."""
    if _text(ws.cell(row=prow, column=C['pm_mark']).value) != ba.PM_MARK:
        return
    fund_sheet = _text(ws.cell(row=prow, column=C['fund_sheet']).value)
    fund_row = ws.cell(row=prow, column=C['fund_row']).value
    if fund_sheet not in wb.sheetnames or not isinstance(fund_row, (int, float)) or (fund_sheet, int(fund_row)) in sent:
        return
    figure = sum(_num(ws.cell(row=r, column=C['new_price']).value) or 0.0 for r in srows)
    cell = wb[fund_sheet].cell(row=int(fund_row), column=REMARK_COL)
    new = pm_remark_text(_text(cell.value), figure)
    if item is not None and (new.startswith(PM_LEAD) or new.startswith(PM_FILLED_LEAD.split('{')[0])):
        sentence = None
        if figure:
            new_subs = [dict(s, **(subs or {}).get(i, {})) for i, s in enumerate(item['subs'])]
            sentence = freq_sentence(item, new_amount(item, adj_type, inflation, new_subs, freq), freq)
        new = lf.with_sentence(new, sentence)
    if new != _text(cell.value):
        cell.value = new


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


def _summary_json(workdir):
    import json
    import os
    try:
        with open(os.path.join(workdir, 'review_summary.json'), encoding='utf-8') as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _keys_of(rows):
    return [f"{x['fund']}|{x['code']}" for x in rows if isinstance(x, dict) and x.get('code') and x.get('fund')]


def top_keys(workdir):
    """['MF|ESS1', ...]: khoá của 10 dòng lệch lớn nhất trong review_summary.json của lượt review (bảng điều chỉnh đánh dấu
    "Top 10"); [] khi không có file hoặc file hỏng."""
    return _keys_of(_summary_json(workdir).get('top') or [])


def abnormal_keys(workdir):
    """Khoá các dòng Review gắn cờ bất thường (change flag-abnormal-review-diffs) trong review_summary.json của lượt;
    None khi file không có danh sách (lượt chạy trước quy tắc, hoặc không có file): server tính lại bằng flag_abnormal."""
    data = _summary_json(workdir)
    if 'abnormal' not in data:
        return None
    return _keys_of(data.get('abnormal') or [])


def flag_abnormal(items):
    """Khoá các mã bất thường tính từ chính bảng (thành tiền gốc trừ số duyệt, cùng quy tắc review.is_abnormal), cho lượt
    cũ không có danh sách trong file tóm tắt. Chỉ xét mã có số duyệt trên sheet Review (it['approved'] không None)."""
    import review
    out = []
    for it in items:
        ap = it.get('approved')
        if ap is None:
            continue
        diff = (it.get('amount') or 0.0) - ap
        if review.is_abnormal(diff, (diff / ap) if abs(ap) >= 0.5 else None):
            out.append(it['key'])
    return out


def abnormal_rule():
    """{'pct': 0.2, 'vnd': 50000000.0}: ngưỡng hiện hành, để trang in ra."""
    import review
    return dict(pct=review.ABNORMAL_PCT, vnd=review.ABNORMAL_VND)
