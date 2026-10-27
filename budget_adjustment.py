"""Sheet '4. Điều chỉnh' of the client deliverable: the PM's budget-adjustment workspace (docs/32, section 3).

One parent (total) row per budget code that carries a figure on '2. Budget-Management Fund' or
'2.2 Common area Fund', followed by its detail sub-rows (one per post, device, product... or a single lumped row).
The PM picks an adjustment type on the parent row's dropdown (column D: quantity / unit price / both / inflation) and edits
the yellow cells of the detail rows; column M recomputes the new amount, N and O the variance. The fund sheet's own
month cells (H:S, and F for a Monthly row) are turned into formulas that scale the original month figure by the
parent's M / I ratio, so '1. Summary', the contingency, the EM#/ES#/EE# totals and '2.2 Common area Fund' follow
without any row being inserted on the fund sheets. Untouched (M = I) the workbook shows exactly the original figures.

apply(wb, items) runs inside build_budget() right before wb.save(): every note that reads the month cells back with
openpyxl has been composed by then (a formula string would read as None). `items` is the list of parent dicts that
adjustment_detail.collect() returns (docs/32, section 2):

    {'code', 'sheet', 'row', 'name_vi', 'freq', 'months' (12), 'annual', 'subs': [
        {'desc_vi', 'unit_vi', 'qty', 'unit_price', 'amount', 'qty_editable'}, ...]}

The fund row is located by its code in column Y (the key); `row` is only used when that code is not unique.
A month cell (or F) that already holds a formula, such as EMH2's link into A1, is kept and wrapped: old formula x
the same ratio, so the link stays live.
Column layout, formulas, styles and the protection rule are the ones docs/32 section 3 fixes; the table style
follows SAVILLS_BRAND_GUIDE.md section 6 (yellow header, white / warm-grey banding, grey total row, no borders).
"""
from openpyxl.styles import Alignment, Font, PatternFill, Protection
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.properties import Outline

SHEET_NAME = '4. Điều chỉnh'
AFTER_SHEET = '3.1 Report-Sinking Fund'
ADJUSTMENT_TYPES = ('Số lượng', 'Đơn giá', 'Số lượng + Đơn giá', 'Trượt giá')
TYPE_QTY, TYPE_PRICE, TYPE_QTY_PRICE, TYPE_INFLATION = ADJUSTMENT_TYPES
ROW_KIND_TOTAL, ROW_KIND_DETAIL = 'Tổng', 'Chi tiết'

TITLE_ROW, GUIDE_ROW, HEADER_ROW, FIRST_DATA_ROW = 1, 2, 4, 5
HEADERS = (
    'Mã', 'Hạng mục', 'Loại dòng', 'Loại điều chỉnh', 'Nội dung chi tiết', 'ĐVT',
    'SL gốc', 'Đơn giá gốc', 'Thành tiền gốc', 'SL mới', 'Đơn giá mới', 'Trượt giá %',
    'Thành tiền mới', 'Chênh lệch', 'Chênh lệch %',
    'Sheet quỹ', 'Dòng quỹ', 'Tần suất',
) + tuple(f'Tháng gốc {m}' for m in range(1, 13))
COL = {name: i + 1 for i, name in enumerate(
    ('code', 'name', 'kind', 'adj_type', 'desc', 'unit', 'qty', 'unit_price', 'amount',
     'new_qty', 'new_price', 'inflation', 'new_amount', 'diff', 'diff_pct', 'fund_sheet', 'fund_row', 'freq'))}
MONTH_FIRST_COL = COL['freq'] + 1          # S .. AD hold the 12 original month figures
HIDDEN_COLS = range(COL['fund_sheet'], MONTH_FIRST_COL + 12)   # P .. AD
LAST_COL = MONTH_FIRST_COL + 11            # AD

FUND_CODE_COL = 25                         # Y on both fund sheets
FUND_MONTHLY_COL = 6                       # F
FUND_MONTH_FIRST_COL = 8                   # H .. S

TITLE = 'ĐIỀU CHỈNH NGÂN SÁCH'
GUIDE = ('Cách dùng: trên dòng Tổng của một mã, chọn Loại điều chỉnh ở cột D (Số lượng / Đơn giá / Số lượng + Đơn giá '
         '/ Trượt giá). Bấm dấu + ở lề trái để mở các dòng Chi tiết rồi sửa ô vàng: SL mới (J) khi chọn Số lượng, Đơn giá '
         'mới (K) khi chọn Đơn giá, cả J và K khi chọn Số lượng + Đơn giá, Trượt giá % (L, trên dòng Tổng) khi chọn '
         'Trượt giá. Các ô khác đã khoá. '
         "Thành tiền mới (M), Chênh lệch (N, O) và các sheet 1. Summary, 2. Budget-Management Fund, "
         "2.2 Common area Fund tự cập nhật. Để trống cột D = giữ nguyên số gốc.")

# SAVILLS_BRAND_GUIDE.md: Arial; header yellow FFDF00 with black regular text; banding white / warm grey EEE8E3;
# total row E4E6E8; no borders. Input cells use the light yellow the pipeline's other editable cells already use.
FONT_NAME = 'Arial'
FILL_HEADER = PatternFill('solid', fgColor='FFDF00')
FILL_TOTAL = PatternFill('solid', fgColor='E4E6E8')
FILL_BAND = PatternFill('solid', fgColor='EEE8E3')
FILL_INPUT = PatternFill('solid', fgColor='FFF2CC')
FMT_MONEY = '#,##0'
FMT_QTY = '#,##0.00'
FMT_PCT = '0.0%'
COLUMN_WIDTHS = {'A': 9, 'B': 42, 'C': 9, 'D': 15, 'E': 44, 'F': 10, 'G': 10, 'H': 15, 'I': 17,
                 'J': 10, 'K': 15, 'L': 11, 'M': 17, 'N': 15, 'O': 11}


def _q(name):
    """A sheet name quoted for a formula: single quotes, doubled inside."""
    return "'" + name.replace("'", "''") + "'"


def _ref(col, row, absolute=False):
    letter = get_column_letter(col)
    return f'${letter}${row}' if absolute else f'{letter}{row}'


def _num(v):
    return float(v) if isinstance(v, (int, float)) else 0.0


def find_fund_row(ws, code, hint_row=None):
    """The row of `code` in column Y of a fund sheet. `hint_row` wins when the code appears more than once (or
    when it is blank there but the hint row carries it). Raises when the code is nowhere on the sheet."""
    code = str(code).strip()
    hits = [r for r in range(1, ws.max_row + 1)
            if isinstance(ws.cell(row=r, column=FUND_CODE_COL).value, str)
            and ws.cell(row=r, column=FUND_CODE_COL).value.strip() == code]
    if hint_row in hits or (hint_row and not hits):
        return hint_row
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise ValueError(f"code {code!r} not found in column Y of '{ws.title}'")
    raise ValueError(f"code {code!r} appears {len(hits)} times on '{ws.title}' (rows {hits}); pass the row")


def detail_formula(parent_row, row):
    """Column M of a detail row: the new amount under the parent's chosen adjustment type."""
    d = _ref(COL['adj_type'], parent_row, absolute=True)
    l = _ref(COL['inflation'], parent_row, absolute=True)
    g, h, i = (_ref(COL[k], row) for k in ('qty', 'unit_price', 'amount'))
    j, k = _ref(COL['new_qty'], row), _ref(COL['new_price'], row)
    return (f'=IF({d}="{TYPE_QTY}",{j}*{h},IF({d}="{TYPE_PRICE}",{g}*{k},IF({d}="{TYPE_QTY_PRICE}",{j}*{k},'
            f'IF({d}="{TYPE_INFLATION}",{i}*(1+{l}),{i}))))')


def ratio_formula(parent_row):
    """The parent's new / original ratio (1 when the original is zero, so a zero line stays zero instead of
    #DIV/0!)."""
    s = _q(SHEET_NAME)
    i, m = _ref(COL['amount'], parent_row, absolute=True), _ref(COL['new_amount'], parent_row, absolute=True)
    return f'IF({s}!{i}=0,1,{s}!{m}/{s}!{i})'


def month_formula(parent_row, month_index):
    """The fund sheet's month cell: original month figure (column S..AD of the parent row) x the ratio."""
    month = _ref(MONTH_FIRST_COL + month_index, parent_row, absolute=True)
    return f'={_q(SHEET_NAME)}!{month}*{ratio_formula(parent_row)}'


def wrapped_formula(existing, parent_row):
    """A month cell that already holds a formula (EMH2 reads A1's top-ups, for example) keeps it: the old formula
    is wrapped in brackets and multiplied by the ratio, so the link it carries stays live and the adjustment still
    scales it."""
    return f'=({existing[1:]})*{ratio_formula(parent_row)}'


def _style(cell, *, fill=None, bold=False, fmt=None, align=None, unlocked=False, indent=0, color=None):
    cell.font = Font(name=FONT_NAME, size=10, bold=bold, color=color)
    if fill is not None:
        cell.fill = fill
    if fmt:
        cell.number_format = fmt
    cell.alignment = Alignment(horizontal=None if align == 'wrap' else align, vertical='center',
                               indent=indent, wrap_text=(align == 'wrap'))
    if unlocked:
        cell.protection = Protection(locked=False)


def _place_sheet(wb, ws):
    """Right after '3.1 Report-Sinking Fund' (docs/32 section 3), else at the end."""
    wb._sheets.remove(ws)
    if AFTER_SHEET in wb.sheetnames:
        wb._sheets.insert(wb.sheetnames.index(AFTER_SHEET) + 1, ws)
    else:
        wb._sheets.append(ws)


def _write_header(ws):
    ws.cell(row=TITLE_ROW, column=1, value=TITLE).font = Font(name=FONT_NAME, size=14, bold=True)
    ws.row_dimensions[TITLE_ROW].height = 24
    c = ws.cell(row=GUIDE_ROW, column=1, value=GUIDE)
    c.font = Font(name=FONT_NAME, size=10)
    c.alignment = Alignment(wrap_text=True, vertical='top')
    ws.merge_cells(start_row=GUIDE_ROW, start_column=1, end_row=GUIDE_ROW, end_column=COL['diff_pct'])
    ws.row_dimensions[GUIDE_ROW].height = 58
    for i, name in enumerate(HEADERS, start=1):
        c = ws.cell(row=HEADER_ROW, column=i, value=name)
        _style(c, fill=FILL_HEADER, align='wrap')
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    ws.row_dimensions[HEADER_ROW].height = 30
    for letter, width in COLUMN_WIDTHS.items():
        ws.column_dimensions[letter].width = width
    for col in HIDDEN_COLS:
        ws.column_dimensions[get_column_letter(col)].hidden = True
    ws.freeze_panes = ws.cell(row=FIRST_DATA_ROW, column=COL['desc'])


def _write_parent(ws, row, item, first_sub, last_sub):
    put = lambda key, value: ws.cell(row=row, column=COL[key], value=value)
    put('code', item['code'])
    put('name', item.get('name_vi') or item['code'])
    put('kind', ROW_KIND_TOTAL)
    put('adj_type', None)
    sub_range = (f"{_ref(COL['amount'], first_sub)}:{_ref(COL['amount'], last_sub)}" if first_sub else None)
    put('amount', f'=SUM({sub_range})' if first_sub else _num(item.get('annual')))
    put('inflation', 0)
    if first_sub:
        put('new_amount', f"=SUM({_ref(COL['new_amount'], first_sub)}:{_ref(COL['new_amount'], last_sub)})")
    else:   # no detail row at all: inflation is the only adjustment that can apply
        i, d, l = (_ref(COL[k], row) for k in ('amount', 'adj_type', 'inflation'))
        put('new_amount', f'=IF({d}="{TYPE_INFLATION}",{i}*(1+{l}),{i})')
    i, m, n = (_ref(COL[k], row) for k in ('amount', 'new_amount', 'diff'))
    put('diff', f'={m}-{i}')
    put('diff_pct', f'=IF({i}=0,"N/A",{n}/{i})')
    put('fund_sheet', item['sheet'])
    put('fund_row', item['row'])
    put('freq', item.get('freq'))
    months = list(item.get('months') or [])
    months = (months + [0.0] * 12)[:12]
    for k, v in enumerate(months):
        ws.cell(row=row, column=MONTH_FIRST_COL + k, value=_num(v))

    for col in range(1, LAST_COL + 1):
        _style(ws.cell(row=row, column=col), fill=FILL_TOTAL)
    for key in ('amount', 'new_amount', 'diff'):
        _style(ws.cell(row=row, column=COL[key]), fill=FILL_TOTAL, bold=True, fmt=FMT_MONEY)
    _style(ws.cell(row=row, column=COL['diff_pct']), fill=FILL_TOTAL, bold=True, fmt=FMT_PCT)
    _style(ws.cell(row=row, column=COL['inflation']), fill=FILL_INPUT, fmt=FMT_PCT, unlocked=True)
    _style(ws.cell(row=row, column=COL['adj_type']), fill=FILL_INPUT, unlocked=True, align='center')
    _style(ws.cell(row=row, column=COL['code']), fill=FILL_TOTAL, bold=True)
    _style(ws.cell(row=row, column=COL['name']), fill=FILL_TOTAL, bold=True, align='wrap')
    for k in range(12):
        ws.cell(row=row, column=MONTH_FIRST_COL + k).number_format = FMT_MONEY


def _write_sub(ws, row, parent_row, sub, band):
    put = lambda key, value: ws.cell(row=row, column=COL[key], value=value)
    editable = bool(sub.get('qty_editable', True))
    put('kind', ROW_KIND_DETAIL)
    put('desc', sub.get('desc_vi'))
    put('unit', sub.get('unit_vi'))
    put('qty', _num(sub.get('qty')))
    put('unit_price', _num(sub.get('unit_price')))
    put('amount', _num(sub.get('amount')))
    put('new_qty', _num(sub.get('qty')) if editable else f"={_ref(COL['qty'], row)}")
    put('new_price', _num(sub.get('unit_price')))
    put('new_amount', detail_formula(parent_row, row))
    m, i, n = (_ref(COL[k], row) for k in ('new_amount', 'amount', 'diff'))
    put('diff', f'={m}-{i}')
    put('diff_pct', f'=IF({i}=0,"N/A",{n}/{i})')

    fill = FILL_BAND if band else None
    for col in range(1, LAST_COL + 1):
        _style(ws.cell(row=row, column=col), fill=fill)
    _style(ws.cell(row=row, column=COL['desc']), fill=fill, indent=2, align='wrap')
    _style(ws.cell(row=row, column=COL['qty']), fill=fill, fmt=FMT_QTY)
    for key in ('unit_price', 'amount', 'new_amount', 'diff'):
        _style(ws.cell(row=row, column=COL[key]), fill=fill, fmt=FMT_MONEY)
    _style(ws.cell(row=row, column=COL['diff_pct']), fill=fill, fmt=FMT_PCT)
    _style(ws.cell(row=row, column=COL['new_qty']), fill=FILL_INPUT if editable else fill, fmt=FMT_QTY,
           unlocked=editable)
    _style(ws.cell(row=row, column=COL['new_price']), fill=FILL_INPUT, fmt=FMT_MONEY, unlocked=True)


def _link_fund_row(wb, item, parent_row):
    """H:S (and F for a Monthly line) of the fund row become formulas into the parent row of this sheet."""
    ws = wb[item['sheet']]
    r = item['row']

    def link(col, month_index):
        cell = ws.cell(row=r, column=col)
        if isinstance(cell.value, str) and cell.value.startswith('='):
            cell.value = wrapped_formula(cell.value, parent_row)
        else:
            cell.value = month_formula(parent_row, month_index)

    for k in range(12):
        link(FUND_MONTH_FIRST_COL + k, k)
    if str(item.get('freq') or '').strip().lower() == 'monthly':
        link(FUND_MONTHLY_COL, 0)
    return r


def type_validation():
    """The list validation of column D (the adjustment types, blank allowed)."""
    return DataValidation(type='list', formula1='"' + ','.join(ADJUSTMENT_TYPES) + '"', allow_blank=True,
                          showDropDown=False, showErrorMessage=True, errorTitle='Loại điều chỉnh',
                          error='Chọn một trong: ' + ' / '.join(ADJUSTMENT_TYPES) + ', hoặc để trống.')


def build_sheet(wb, items):
    """The sheet alone (no fund-sheet links): {code: parent_row}. Rebuilt from scratch when it already exists."""
    if SHEET_NAME in wb.sheetnames:
        del wb[SHEET_NAME]
    ws = wb.create_sheet(SHEET_NAME)
    _place_sheet(wb, ws)
    _write_header(ws)
    ws.sheet_properties.outlinePr = Outline(summaryBelow=False, summaryRight=False)

    dv = type_validation()
    ws.add_data_validation(dv)

    parent_rows = {}
    row = FIRST_DATA_ROW
    for item in items:
        parent_row = row
        subs = list(item.get('subs') or [])
        first_sub = parent_row + 1 if subs else None
        last_sub = parent_row + len(subs) if subs else None
        _write_parent(ws, parent_row, item, first_sub, last_sub)
        dv.add(ws.cell(row=parent_row, column=COL['adj_type']))
        for n, sub in enumerate(subs):
            _write_sub(ws, parent_row + 1 + n, parent_row, sub, band=(n % 2 == 1))
        if subs:
            ws.row_dimensions.group(first_sub, last_sub, outline_level=1, hidden=True)
        parent_rows[item['code']] = parent_row
        row = parent_row + 1 + len(subs)

    ws.protection.sheet = True
    ws.protection.formatRows = False      # outline +/- must keep working on the protected sheet
    ws.protection.formatColumns = False
    ws.protection.selectLockedCells = False
    ws.protection.selectUnlockedCells = False
    ws.sheet_view.zoomScale = 90
    return parent_rows


def apply(wb, items):
    """Build '4. Điều chỉnh' from `items` and point every covered fund row's month cells at it.
    Returns {code: parent_row}. With no items the sheet is still built (empty) and nothing is linked."""
    items = [dict(item, row=find_fund_row(wb[item['sheet']], item['code'], item.get('row'))) for item in items]
    parent_rows = build_sheet(wb, items)
    for item in items:
        _link_fund_row(wb, item, parent_rows[item['code']])
    return parent_rows
