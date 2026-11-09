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

import line_frequency

SHEET_NAME = '4. Điều chỉnh'
AFTER_SHEET = '3.1 Report-Sinking Fund'
MF_SHEET = '2. Budget-Management Fund'          # the default frequency table is for this fund only
ADJUSTMENT_TYPES = ('Số lượng', 'Đơn giá', 'Số lượng + Đơn giá', 'Trượt giá', 'Nhập số')
TYPE_QTY, TYPE_PRICE, TYPE_QTY_PRICE, TYPE_INFLATION, TYPE_ENTER = ADJUSTMENT_TYPES
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
FUND_FREQ_COL = 3                          # C: Monthly / Schedule / ...
FUND_TIMES_COL = 4                         # D: number of times for Optional
FUND_MONTHLY_COL = 6                       # F
FUND_MONTH_FIRST_COL = 8                   # H .. S
FUND_CHECK_TIMES_COL = 21                  # U: the form's times check

# Frequency cells (change add-line-frequency, design D2): appended after AD so no earlier column moves.
# AE new frequency, AF first month, AG new times (formula), AH..AS the 12 month inputs (a tick "x" for Optional, VND
# for Schedule); hidden helpers AT original times, AU original first month, AV frequency in use, AW first month in
# use, AX month step.
FREQ_HEADERS = (('new_freq', 'Tần suất mới'), ('first_month', 'Tháng đầu'), ('new_times', 'Số lần mới')) + tuple(
    (f'month_in_{m}', f'Tháng {m} (x / VND)') for m in range(1, 13)) + (
    ('orig_times', 'Số lần gốc'), ('orig_first', 'Tháng đầu gốc'), ('eff_freq', 'Tần suất dùng'),
    ('eff_first', 'Tháng đầu dùng'), ('step', 'Bước tháng'))
COL.update({key: LAST_COL + 1 + i for i, (key, _) in enumerate(FREQ_HEADERS)})
MONTH_IN_FIRST_COL = COL['month_in_1']     # AH
FREQ_HIDDEN_COLS = range(COL['orig_times'], COL['step'] + 1)   # AT .. AX
FREQ_LAST_COL = COL['step']                # AX
# Lines left for the PM (change leave-unpriced-lines-for-pm, design D4): hidden AY "PM điền" mark and AZ reason on the
# total row, read back by the web; the fund row's F and H:S show nothing while the PM's cell is empty.
PM_HEADERS = (('pm_mark', 'PM điền'), ('pm_reason', 'Lý do PM điền'))
COL.update({key: FREQ_LAST_COL + 1 + i for i, (key, _) in enumerate(PM_HEADERS)})
PM_MARK = 'PM điền'
FMT_BLANK_ZERO = '#,##0;-#,##0;;@'         # a 0 shows nothing, so a fund cell the PM has not filled reads blank
FREQUENCIES = ('Monthly', 'Quarterly', 'Half a Year', 'Yearly', 'Optional', 'Schedule')
SCHEDULE_NOTE = 'Tần suất Schedule: loại điều chỉnh không có tác dụng, số mới = tổng 12 tháng nhập'

TITLE = 'ĐIỀU CHỈNH NGÂN SÁCH'
GUIDE = ('Cách dùng: trên dòng Tổng của một mã, chọn Loại điều chỉnh ở cột D (Số lượng / Đơn giá / Số lượng + Đơn giá '
         '/ Trượt giá / Nhập số). Bấm dấu + ở lề trái để mở các dòng Chi tiết rồi sửa ô vàng: SL mới (J) khi chọn Số lượng, Đơn giá '
         'mới (K) khi chọn Đơn giá, cả J và K khi chọn Số lượng + Đơn giá, Trượt giá % (L, trên dòng Tổng) khi chọn '
         'Trượt giá, hoặc Đơn giá mới (K) = số cả năm của dòng khi chọn Nhập số (dùng cho mã công cụ ra 0). Các ô khác đã khoá. '
         "Thành tiền mới (M), Chênh lệch (N, O) và các sheet 1. Summary, 2. Budget-Management Fund, "
         "2.2 Common area Fund tự cập nhật. Để trống cột D = giữ nguyên số gốc. Tần suất: chọn Tần suất mới (cột AE) "
         "trên dòng Tổng; Tháng đầu (AF) cho Quarterly (T1-T3), Half a Year (T1-T6), Yearly (T1-T12); đánh dấu x ở "
         "các ô tháng AH:AS cho Optional, hoặc nhập số tiền từng tháng cho Schedule. Đổi tần suất giữ đơn giá mỗi lần: "
         "số mới = số theo loại điều chỉnh × số lần mới / số lần gốc. Để trống AE = giữ tần suất gốc. Không gõ đè các "
         "ô C, D, F, H:S của sheet quỹ.")

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
            f'IF({d}="{TYPE_INFLATION}",{i}*(1+{l}),IF({d}="{TYPE_ENTER}",{k},{i})))))')


def ratio_formula(parent_row):
    """The parent's new / original ratio (1 when the original is zero, so a zero line stays zero instead of
    #DIV/0!)."""
    s = _q(SHEET_NAME)
    i, m = _ref(COL['amount'], parent_row, absolute=True), _ref(COL['new_amount'], parent_row, absolute=True)
    return f'IF({s}!{i}=0,1,{s}!{m}/{s}!{i})'


def month_formula(parent_row, month_index):
    """The fund sheet's month cell: original month figure (column S..AD of the parent row) x the ratio. When the
    original annual is zero the ratio is undefined, so the cell takes the new annual amount / 12 (type "Nhập số"
    on a line the tool priced at 0)."""
    s = _q(SHEET_NAME)
    month = _ref(MONTH_FIRST_COL + month_index, parent_row, absolute=True)
    i, m = _ref(COL['amount'], parent_row, absolute=True), _ref(COL['new_amount'], parent_row, absolute=True)
    return f'=IF({s}!{i}=0,{s}!{m}/12,{s}!{month}*{ratio_formula(parent_row)})'


def wrapped_formula(existing, parent_row):
    """A month cell that already holds a formula (EMH2 reads A1's top-ups, for example) keeps it: the old formula
    is wrapped in brackets and multiplied by the ratio, so the link it carries stays live and the adjustment still
    scales it."""
    return f'=({existing[1:]})*{ratio_formula(parent_row)}'


# ------------------------------------------------------------------------------------------------
# Frequency (change add-line-frequency, spec budget-adjustment-sheet, design D2-D4)
# ------------------------------------------------------------------------------------------------
def original_frequency(item):
    """(frequency, times, first month) of a line as written: Monthly / Schedule count 12 times; a cyclic line its
    form count, first month = its first month of payment; Optional = the months carrying an amount."""
    try:
        freq = line_frequency.normalise(item.get('freq')) or line_frequency.MONTHLY
    except ValueError:
        freq = line_frequency.MONTHLY
    months = (list(item.get('months') or []) + [0.0] * 12)[:12]
    paid = [k + 1 for k, v in enumerate(months) if abs(_num(v)) >= 1e-9]
    if freq == line_frequency.OPTIONAL:
        return freq, max(len(paid), 1), (paid[0] if paid else 1)
    if freq in line_frequency.CYCLIC:
        first = item.get('first_month') or (paid[0] if paid else 1)
        return freq, line_frequency.TIMES[freq], int(first)
    return freq, 12, 1


def _month_inputs(row):
    return f"{_ref(MONTH_IN_FIRST_COL, row)}:{_ref(MONTH_IN_FIRST_COL + 11, row)}"


def frequency_amount(base, row):
    """Total-row M with the frequency applied: Schedule = the sum of the 12 month inputs; any other new frequency =
    the amount of the adjustment type x new times / original times; a blank AE leaves `base` unchanged."""
    ae, ag, at = (_ref(COL[k], row) for k in ('new_freq', 'new_times', 'orig_times'))
    return f'=IF({ae}="Schedule",SUM({_month_inputs(row)}),({base})*IF({ae}="",1,IF({at}=0,1,{ag}/{at})))'


def new_times_formula(row):
    ae, at = _ref(COL['new_freq'], row), _ref(COL['orig_times'], row)
    return (f'=IF({ae}="",{at},IF({ae}="Optional",COUNTA({_month_inputs(row)}),IF(OR({ae}="Monthly",{ae}="Schedule"),'
            f'12,IF({ae}="Quarterly",4,IF({ae}="Half a Year",2,IF({ae}="Yearly",1,{at}))))))')


def _sheet4(key, row, col=None):
    """An absolute reference into '4. Điều chỉnh' for a fund-sheet formula."""
    return f"{_q(SHEET_NAME)}!{_ref(col or COL[key], row, absolute=True)}"


def fund_month_formula(parent_row, month_index, fund_col):
    """The fund sheet's month cell H..S of a linked line (design D4, one test per month instead of a running count):
    Schedule = the original month x ratio, or the month input when AE is Schedule; Monthly = the original month x
    ratio, or blank when AE is Monthly; Optional = the month header when that month is ticked; a cyclic frequency =
    the month header when (month - first month) is a multiple of the step."""
    m = month_index + 1
    today = month_formula(parent_row, month_index)[1:]
    eff, ae = _sheet4('eff_freq', parent_row), _sheet4('new_freq', parent_row)
    first, step = _sheet4('eff_first', parent_row), _sheet4('step', parent_row)
    month_in = _sheet4(None, parent_row, MONTH_IN_FIRST_COL + month_index)
    header = f'${get_column_letter(fund_col)}$8'
    return (f'=IF({eff}="Schedule",IF({ae}="",{today},N({month_in})),IF({eff}="Monthly",IF({ae}="",{today},""),'
            f'IF({eff}="Optional",IF({month_in}<>"",{header},""),'
            f'IF(AND({m}>={first},MOD({m}-{first},{step})=0),{header},""))))')


def fund_price_formula(parent_row, keep=None):
    """F of a linked line: blank under Schedule (or `keep`, the formula the cell held, such as a Schedule line's rate
    link into '0. Info', which the form ignores under Schedule), else the new amount / the times in use."""
    eff, ag, m = (_sheet4(k, parent_row) for k in ('eff_freq', 'new_times', 'new_amount'))
    under_schedule = f'({keep[1:]})' if isinstance(keep, str) and keep.startswith('=') else '""'
    return f'=IF({eff}="Schedule",{under_schedule},IF({ag}=0,0,{m}/{ag}))'


def times_check_formula(r):
    """The form's U on a linked line: COUNTA would count a formula that returns "" as filled, so the filled month
    cells are counted with SUMPRODUCT (design D4, the trap)."""
    return f'=E{r}-IF(C{r}<>"Monthly",SUMPRODUCT(--(H{r}:S{r}<>"")),12)'


def frequency_validations():
    """List validation of AE (the form's six frequencies, blank allowed) and whole-number 1..12 of AF."""
    freq = DataValidation(type='list', formula1='"' + ','.join(FREQUENCIES) + '"', allow_blank=True,
                          showDropDown=False, showErrorMessage=True, errorTitle='Tần suất',
                          error='Chọn một trong: ' + ' / '.join(FREQUENCIES) + ', hoặc để trống.')
    first = DataValidation(type='whole', operator='between', formula1='1', formula2='12', allow_blank=True,
                           showErrorMessage=True, errorTitle='Tháng đầu',
                           error='Tháng đầu là số từ 1 đến 12 (Quarterly T1-T3, Half a Year T1-T6, Yearly T1-T12).')
    return freq, first


def _freq_validations_of(ws):
    """The two frequency validations of the sheet, added when missing."""
    freq = next((d for d in ws.data_validations.dataValidation
                 if d.type == 'list' and 'Half a Year' in str(d.formula1 or '')), None)
    first = next((d for d in ws.data_validations.dataValidation if d.type == 'whole'), None)
    if freq is None or first is None:
        new_freq, new_first = frequency_validations()
        if freq is None:
            freq = new_freq
            ws.add_data_validation(freq)
        if first is None:
            first = new_first
            ws.add_data_validation(first)
    return freq, first


def _write_freq_header(ws):
    for key, name in FREQ_HEADERS:
        c = ws.cell(row=HEADER_ROW, column=COL[key], value=name)
        _style(c, fill=FILL_HEADER, align='wrap')
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    ws.column_dimensions[get_column_letter(COL['new_freq'])].width = 13
    for key in ('first_month', 'new_times'):
        ws.column_dimensions[get_column_letter(COL[key])].width = 9
    for k in range(12):
        ws.column_dimensions[get_column_letter(MONTH_IN_FIRST_COL + k)].width = 11
    for col in FREQ_HIDDEN_COLS:
        ws.column_dimensions[get_column_letter(col)].hidden = True


def _write_freq_cells(ws, row, item, validations, editable=True):
    """The frequency block of one total row. A line whose fund cells are formulas of their own (EMH2) is not
    editable: its inputs stay locked and grey, and the block only reports the original frequency."""
    freq, times, first = original_frequency(item)
    put = lambda key, value: ws.cell(row=row, column=COL[key], value=value)
    put('orig_times', times)
    put('orig_first', first)
    ae, af, au, r = (_ref(COL[k], row) for k in ('new_freq', 'first_month', 'orig_first', 'freq'))
    put('new_times', new_times_formula(row))
    put('eff_freq', f'=IF({ae}="",{r},{ae})')
    eff, step = _ref(COL['eff_freq'], row), _ref(COL['step'], row)
    put('step', f'=IF({eff}="Quarterly",3,IF({eff}="Half a Year",6,IF({eff}="Yearly",12,1)))')
    # a blank AF keeps the original first month while it is allowed for the frequency in use, else T1
    put('eff_first', f'=IF({af}="",IF({au}<={step},{au},1),{af})')
    if editable:   # spec budget-adjustment-sheet: under Schedule the adjustment type has no effect; the row says so
        d = _ref(COL['adj_type'], row)
        note = ws.cell(row=row, column=COL['desc'],
                       value=f'=IF(AND({ae}="Schedule",{d}<>""),"{SCHEDULE_NOTE}","")')
        _style(note, fill=FILL_TOTAL, align='wrap', color='C00000')
    inputs = [COL['new_freq'], COL['first_month']] + [MONTH_IN_FIRST_COL + k for k in range(12)]
    for col in range(COL['new_freq'], FREQ_LAST_COL + 1):
        _style(ws.cell(row=row, column=col), fill=FILL_TOTAL)
    for col in inputs:
        _style(ws.cell(row=row, column=col), fill=FILL_INPUT if editable else FILL_TOTAL, unlocked=editable,
               align='center', fmt=FMT_MONEY if col >= MONTH_IN_FIRST_COL else None)
    _style(ws.cell(row=row, column=COL['new_times']), fill=FILL_TOTAL, align='center')
    if editable:
        validations[0].add(ws.cell(row=row, column=COL['new_freq']))
        validations[1].add(ws.cell(row=row, column=COL['first_month']))


def _own_formula(value):
    """True for a fund cell formula that is not the tool's own month-header reference ('=K8')."""
    return (isinstance(value, str) and value.startswith('=')
            and not (len(value) <= 6 and value.endswith('8') and value[1:-1].replace('$', '').isalpha()))


def freq_editable(wb, item):
    """A line can change frequency unless its F or H:S cells are formulas of their own (EMH2's link into A1). Under
    Schedule the form ignores F, so a Schedule line's F link (a rate into '0. Info') does not lock it."""
    ws = wb[item['sheet']]
    r = item['row']
    cols = [FUND_MONTH_FIRST_COL + k for k in range(12)]
    if original_frequency(item)[0] != line_frequency.SCHEDULE:
        cols.append(FUND_MONTHLY_COL)
    return not any(_own_formula(ws.cell(row=r, column=c).value) for c in cols)


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
    ws.row_dimensions[GUIDE_ROW].height = 70
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
    _write_freq_header(ws)
    ws.row_dimensions[GUIDE_ROW].height = 100


def _write_parent(ws, row, item, first_sub, last_sub, validations=None, editable=False):
    put = lambda key, value: ws.cell(row=row, column=COL[key], value=value)
    put('code', item['code'])
    put('name', item.get('name_vi') or item['code'])
    put('kind', ROW_KIND_TOTAL)
    put('adj_type', None)
    sub_range = (f"{_ref(COL['amount'], first_sub)}:{_ref(COL['amount'], last_sub)}" if first_sub else None)
    put('amount', f'=SUM({sub_range})' if first_sub else _num(item.get('annual')))
    put('inflation', 0)
    if first_sub:
        base = f"SUM({_ref(COL['new_amount'], first_sub)}:{_ref(COL['new_amount'], last_sub)})"
    else:   # no detail row at all: inflation is the only adjustment that can apply
        i, d, l = (_ref(COL[k], row) for k in ('amount', 'adj_type', 'inflation'))
        base = f'IF({d}="{TYPE_INFLATION}",{i}*(1+{l}),{i})'
    put('new_amount', frequency_amount(base, row) if editable else f'={base}')
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
    if validations is not None:
        _write_freq_cells(ws, row, item, validations, editable)


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


def _link_fund_row(wb, item, parent_row, editable=None):
    """The fund row becomes formulas into the parent row of this sheet. A line that can change frequency gets C, D,
    F, H:S and U (design D4); with AE blank every figure equals the earlier link (original month x ratio). A line
    with formulas of its own (EMH2) keeps the earlier link: H:S (and F for a Monthly line) wrapped x the ratio."""
    ws = wb[item['sheet']]
    r = item['row']
    if editable is None:
        editable = freq_editable(wb, item)
    if editable:
        ws.cell(row=r, column=FUND_FREQ_COL, value=f'={_sheet4("eff_freq", parent_row)}')
        ws.cell(row=r, column=FUND_TIMES_COL,
                value=f'=IF({_sheet4("eff_freq", parent_row)}="Optional",{_sheet4("new_times", parent_row)},"")')
        f_cell = ws.cell(row=r, column=FUND_MONTHLY_COL)
        keep = f_cell.value if _own_formula(f_cell.value) else None      # a Schedule line's rate link, kept
        f_cell.value = fund_price_formula(parent_row, keep)
        for k in range(12):
            col = FUND_MONTH_FIRST_COL + k
            ws.cell(row=r, column=col, value=fund_month_formula(parent_row, k, col))
        ws.cell(row=r, column=FUND_CHECK_TIMES_COL, value=times_check_formula(r))
        return r

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


def _write_item(ws, dv, parent_row, item, validations=None):
    """One code's total row and its detail rows from `parent_row`; the next free row."""
    subs = list(item.get('subs') or [])
    first_sub = parent_row + 1 if subs else None
    last_sub = parent_row + len(subs) if subs else None
    _write_parent(ws, parent_row, item, first_sub, last_sub, validations, item.get('freq_editable', True))
    dv.add(ws.cell(row=parent_row, column=COL['adj_type']))
    for n, sub in enumerate(subs):
        _write_sub(ws, parent_row + 1 + n, parent_row, sub, band=(n % 2 == 1))
    if subs:
        ws.row_dimensions.group(first_sub, last_sub, outline_level=1, hidden=True)
    return parent_row + 1 + len(subs)


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
    validations = _freq_validations_of(ws)

    parent_rows = {}
    row = FIRST_DATA_ROW
    for item in items:
        parent_rows[item['code']] = row
        row = _write_item(ws, dv, row, item, validations)

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
    items = [dict(item, freq_editable=freq_editable(wb, item)) for item in items]
    parent_rows = build_sheet(wb, items)
    for item in items:
        _link_fund_row(wb, item, parent_rows[item['code']], item['freq_editable'])
    return parent_rows


def upgrade(wb):
    """An older '4. Điều chỉnh' (built before change add-line-frequency) gains the frequency cells; no figure moves.
    Each total row without the original-times cell gets the block, its M the frequency factor (1 while AE is blank)
    and its fund row the new link. A fund row whose cells were wrapped (a formula of its own x the ratio, EMH2) keeps
    its link and gets a locked block. Returns the number of rows upgraded; 0 when there is no sheet."""
    if SHEET_NAME not in wb.sheetnames:
        return 0
    ws = wb[SHEET_NAME]
    validations = None
    if ws.cell(row=HEADER_ROW, column=COL['new_freq']).value in (None, ''):
        _write_freq_header(ws)
        ws.cell(row=GUIDE_ROW, column=1, value=GUIDE)
        ws.row_dimensions[GUIDE_ROW].height = 100
    upgraded = 0
    for r in range(FIRST_DATA_ROW, ws.max_row + 1):
        if ws.cell(row=r, column=COL['kind']).value != ROW_KIND_TOTAL:
            continue
        if ws.cell(row=r, column=COL['orig_times']).value not in (None, ''):
            continue
        sheet = str(ws.cell(row=r, column=COL['fund_sheet']).value or '').strip()
        fund_row = ws.cell(row=r, column=COL['fund_row']).value
        if sheet not in wb.sheetnames or not isinstance(fund_row, (int, float)):
            continue
        item = {'code': ws.cell(row=r, column=COL['code']).value, 'sheet': sheet, 'row': int(fund_row),
                'freq': ws.cell(row=r, column=COL['freq']).value,
                'months': [_num(ws.cell(row=r, column=MONTH_FIRST_COL + k).value) for k in range(12)]}
        fws = wb[sheet]
        cols = [FUND_MONTHLY_COL] + [FUND_MONTH_FIRST_COL + k for k in range(12)]
        editable = not any(isinstance(fws.cell(row=item['row'], column=c).value, str)
                           and fws.cell(row=item['row'], column=c).value.startswith('=(') for c in cols)
        validations = validations or _freq_validations_of(ws)
        _write_freq_cells(ws, r, item, validations, editable)
        if editable:
            m = ws.cell(row=r, column=COL['new_amount']).value
            if isinstance(m, str) and m.startswith('='):
                ws.cell(row=r, column=COL['new_amount'], value=frequency_amount(m[1:], r))
            _link_fund_row(wb, item, r, True)
        upgraded += 1
    return upgraded


def listed_codes(ws):
    """{(code, fund sheet)} of the total rows already on '4. Điều chỉnh'."""
    return {(str(ws.cell(row=r, column=COL['code']).value or '').strip(),
             str(ws.cell(row=r, column=COL['fund_sheet']).value or '').strip())
            for r in range(FIRST_DATA_ROW, ws.max_row + 1)
            if ws.cell(row=r, column=COL['kind']).value == ROW_KIND_TOTAL}


def append_items(wb, items):
    """Add `items` (the same dicts as apply()) after the last row of the existing '4. Điều chỉnh' and link their fund
    rows: the Review adds a line for every code the approved budget carries and the tool priced at 0. The earlier
    rows, the protection and the outline settings are untouched. Returns {code: parent_row}; a code already on the
    sheet for the same fund sheet is skipped."""
    ws = wb[SHEET_NAME]
    existing = listed_codes(ws)
    todo = [dict(item, row=find_fund_row(wb[item['sheet']], item['code'], item.get('row')))
            for item in items if (item['code'], item['sheet']) not in existing]
    todo = [dict(item, freq_editable=freq_editable(wb, item)) for item in todo]
    upgrade(wb)
    validations = _freq_validations_of(ws)
    dv = next((d for d in ws.data_validations.dataValidation if d.type == 'list' and TYPE_INFLATION in str(d.formula1 or '')),
              None)
    if dv is None:
        dv = type_validation()
        ws.add_data_validation(dv)
    parent_rows, row = {}, ws.max_row + 1
    for item in todo:
        parent_rows[item['code']] = row
        row = _write_item(ws, dv, row, item, validations)
        _link_fund_row(wb, item, parent_rows[item['code']], item['freq_editable'])
    return parent_rows


# ------------------------------------------------------------------------------------------------
# Lumped "Nhập số" lines: zero-tool codes on a Review, lines left for the PM on every run
# ------------------------------------------------------------------------------------------------
def lumped_item(wb, sheet, code, name, value_col, first_month_col, defaults=None, pm_line=False):
    """(item, None) for a one-detail "Nhập số" line of `code` on `sheet` for append_items(), or (None, reason) when the
    code is not a plain leaf line of its fund sheet (no unique row, or no =SUM(first month) annual in `value_col`).
    A frequency the fund row carries is kept; a blank one (or Optional) takes the code's default from
    Ref_LineFrequency.csv, else Monthly (change add-line-frequency). A line left for the PM (`pm_line`) on a Monthly
    row also takes a non-Monthly default (change default-frequency-from-real-budgets, design D3): its price is blank,
    so the template's Monthly carries no choice of the tool. Moved from review.add_zero_rows."""
    if sheet not in wb.sheetnames:
        return None, 'không có sheet quỹ'
    ws = wb[sheet]
    try:
        row = find_fund_row(ws, code)
    except ValueError as exc:
        return None, str(exc)
    annual = str(ws[f'{value_col}{row}'].value or '').replace(' ', '').upper()
    if not annual.startswith(f'=SUM({first_month_col}'):
        return None, 'không phải dòng chi tiết của form (không có công thức năm =SUM tháng)'
    lf = line_frequency
    defaults = lf.load_table() if defaults is None else defaults
    try:
        freq = lf.normalise(ws.cell(row=row, column=FUND_FREQ_COL).value)
    except ValueError:
        freq = None
    default = defaults.get(code)
    first = None
    if pm_line and freq == lf.MONTHLY and default and default.frequency != lf.MONTHLY:
        freq = None                                  # the default below applies
    if freq in (None, lf.OPTIONAL):
        freq = default.frequency if default else lf.MONTHLY
        first = default.first_month if default else None
    elif freq in lf.CYCLIC:
        paid = lf.payment_months(ws, row)
        first = (min(paid) if paid else
                 default.first_month if default and default.frequency == freq else 1)
    ws.cell(row=row, column=FUND_FREQ_COL).value = freq
    name = name or code
    return dict(code=code, sheet=sheet, row=row, name_vi=name, freq=freq, first_month=first,
                months=[0.0] * 12, annual=0.0,
                subs=[dict(desc_vi=name, unit_vi='khoản', qty=1.0, unit_price=0.0, amount=0.0,
                           qty_editable=False)]), None


def _write_pm_header(ws):
    for key, name in PM_HEADERS:
        c = ws.cell(row=HEADER_ROW, column=COL[key], value=name)
        _style(c, fill=FILL_HEADER, align='wrap')
        ws.column_dimensions[get_column_letter(COL[key])].hidden = True


def shade_pm_fund_row(ws, row, cyclic=False):
    """A line left for the PM on its fund sheet: F and H:S light yellow, a 0 shown as nothing (design D3). A cyclic
    line (change default-frequency-from-real-budgets, D4): H:S show the months of payment as on any cyclic row of the
    form, so they keep the row-8 month format and no fill; only F is shaded."""
    for col in [FUND_MONTHLY_COL] + [FUND_MONTH_FIRST_COL + k for k in range(12)]:
        cell = ws.cell(row=row, column=col)
        if cyclic and col != FUND_MONTHLY_COL:
            cell.fill = PatternFill(fill_type=None)
            cell.number_format = ws.cell(row=8, column=col).number_format
            continue
        cell.fill = PatternFill('solid', fgColor=FILL_INPUT.fgColor.rgb)
        cell.number_format = FMT_BLANK_ZERO


def add_pm_rows(wb, lines, sheet, value_col, first_month_col):
    """Rows on '4. Điều chỉnh' for the lines left for the PM (change leave-unpriced-lines-for-pm, spec
    budget-adjustment-sheet): `lines` = [dict(code, name, reason)] of `sheet`. Each gets a lumped detail row whose
    yellow cell is empty, the type "Nhập số" already chosen, the hidden mark and reason, and its fund row linked; every
    line's F and H:S on the fund sheet are shaded, linked or not. Returns (added codes, [(code, reason skipped)])."""
    added, skipped, items, reasons = [], [], [], {}
    if SHEET_NAME not in wb.sheetnames:
        return added, [(ln['code'], "không có sheet '4. Điều chỉnh'") for ln in lines]
    defaults = line_frequency.load_table()
    for ln in lines:
        item, why = lumped_item(wb, sheet, ln['code'], ln.get('name'), value_col, first_month_col, defaults,
                                pm_line=sheet == MF_SHEET)   # common-area shares stay Monthly
        if item is None:
            skipped.append((ln['code'], why))
        else:
            items.append(item)
            reasons[ln['code']] = ln.get('reason') or ''
    ws = wb[SHEET_NAME]
    if items:
        parent_rows = append_items(wb, items)
        _write_pm_header(ws)
        for code, prow in parent_rows.items():
            ws.cell(row=prow, column=COL['adj_type'], value=TYPE_ENTER)
            ws.cell(row=prow, column=COL['pm_mark'], value=PM_MARK)
            ws.cell(row=prow, column=COL['pm_reason'], value=reasons.get(code, ''))
            ws.cell(row=prow + 1, column=COL['new_price']).value = None    # the PM's cell starts empty
            added.append(code)
    fund = wb[sheet]
    cyclic = {it['code'] for it in items if it['freq'] in line_frequency.CYCLIC}
    for ln in lines:
        try:
            shade_pm_fund_row(fund, find_fund_row(fund, ln['code']), cyclic=ln['code'] in cyclic)
        except ValueError:
            pass
    return added, skipped


def pm_rows(ws):
    """{(code, fund sheet): (total row, reason)} of the total rows marked "PM điền" on '4. Điều chỉnh'."""
    out = {}
    for r in range(FIRST_DATA_ROW, ws.max_row + 1):
        if (ws.cell(row=r, column=COL['kind']).value == ROW_KIND_TOTAL
                and ws.cell(row=r, column=COL['pm_mark']).value == PM_MARK):
            out[(str(ws.cell(row=r, column=COL['code']).value or '').strip(),
                 str(ws.cell(row=r, column=COL['fund_sheet']).value or '').strip())] = (
                r, ws.cell(row=r, column=COL['pm_reason']).value or '')
    return out

