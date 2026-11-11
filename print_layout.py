"""
Print layout of the client deliverable's '2. Budget-Management Fund' (change add-budget-print-layout).

Two layers:
- apply(wb): openpyxl only, no Excel. It sets up the sheet for printing:
  - print area X2:BB<last signature row>, A3 landscape, fit to 1 page wide;
  - rows 9:10 repeated on every page, "Page x of y" in the footer;
  - "Not Use" rows hidden by the form's column B rule; top-level section rows always shown;
  - the check row and blank spacer rows above the signatures hidden;
  - detail columns AC/AE/AF/AI folded in an outline group;
  - the 8-box signature block of the approved sample, inside X:AO.

  Row flags come from the values the tool wrote, unless the caller passes Excel's own column B read from a
  recalculated copy (not_use=...). A line whose inputs are formulas cannot be evaluated without Excel; it is kept
  visible (never hidden by mistake).
- export_pdf(deliverable, paper, out_pdf): Excel on a copy. Recalculate, apply the same rules from Excel's column B,
  set the A4 (X:AO) or A3 (X:BB) range, keep the signature block on one page, export a PDF. The deliverable itself is
  never opened for writing.
"""
import datetime
import os
import re
import shutil
import tempfile

from openpyxl.styles import Alignment, Font
from openpyxl.utils import column_index_from_string as _ci
from openpyxl.utils import get_column_letter as _cl
from openpyxl.worksheet.dimensions import ColumnDimension
from openpyxl.worksheet.properties import PageSetupProperties

SHEET = '2. Budget-Management Fund'
REPORT_SHEET = '2.1 Report-Management Fund'
FIRST_COL, A4_LAST_COL, A3_LAST_COL = 'X', 'AO', 'BB'
FIRST_PRINT_ROW = 2                      # row 1 holds helper column numbers only
TITLE_ROWS = '9:10'
FILTER_FIRST_ROW, FILTER_LAST_COL = 12, 'AW'
FOLD_COLS = ('AC', 'AE', 'AF', 'AI')     # prior-year average, actual to date, expected rest of year, report average
FOOTER = 'Page &P of &N'
PAPER_A4, PAPER_A3 = 9, 8

# Defaults of the 2027 form when a marker cannot be found.
DEFAULT_PART3_ROW, DEFAULT_SIGN_TOP, DEFAULT_SIGN_BOTTOM = 505, 514, 526

SECTION_RE = re.compile(r'^(PART\s*\d+\s*:?|[A-D]|[IVX]+)$')
_NOT_USE_RE = re.compile(r'^=\s*IF\s*\(\s*AND\s*\(\s*AC\d+\s*=\s*0', re.I)
_SUBTOTAL_RE = re.compile(r'^=\s*SUBTOTAL\s*\(\s*(?:9|109)\s*,\s*\(?\s*\$?[A-Z]+\$?(\d+)\s*:\s*\$?[A-Z]+\$?(\d+)\s*\)?\s*\)\s*$',
                          re.I)
_SUM_HI_RE = re.compile(r'^=\s*SUM\s*\(\s*H(\d+)\s*:\s*I(\d+)\s*\)\s*$', re.I)

# The approved sample's signers, in order (roles only; names are signed by hand).
SIGNERS = [('Đề xuất', 'Trưởng Ban Quản lý'),
           ('Phê duyệt', 'Trưởng Ban quản trị'),
           ('Phê duyệt', 'Phó Ban quản trị'),
           ('Phê duyệt', 'Phó Ban quản trị'),
           ('Phê duyệt', 'Ban quản trị'),
           ('Phê duyệt', 'Ban quản trị'),
           ('Phê duyệt', 'Ban quản trị'),
           ('Phê duyệt', 'Ban quản trị')]
# Contiguous column spans inside X:AO, balanced on the folded view (AC/AE/AF/AI hidden): widths of the visible
# columns are about 86, 31, 34, 30, 26, 20, 19 and 49 characters. A span may include a folded column.
SIGN_SPANS = [('X', 'Z'), ('AA', 'AB'), ('AC', 'AH'), ('AI', 'AK'), ('AL', 'AL'), ('AM', 'AM'), ('AN', 'AN'),
              ('AO', 'AO')]
INSTRUCTION = '(Ký tên, ghi rõ họ tên)'
DATE_LINE = 'Ngày: _____/_____/_____'
_SIGN_FONT = 'Arial'
_SIGN_SIZE = 12


# ---- locating rows ------------------------------------------------------------------------------------------------

def _text(v):
    return str(v).strip() if v is not None else ''


def _is_formula(v):
    return isinstance(v, str) and v.startswith('=')


def locate(ws):
    """{'part3', 'sign_top', 'sign_bottom'} of the sheet: PART 3 row, first and last row of the signature block."""
    part3 = next((r for r in range(11, ws.max_row + 1)
                  if _text(ws.cell(r, _ci('X')).value).upper().startswith('PART 3')), DEFAULT_PART3_ROW)
    cols = range(_ci('X'), _ci('BB') + 1)
    top = next((r for r in range(part3 + 1, min(ws.max_row, part3 + 40) + 1)
                if any(_text(ws.cell(r, c).value) == 'Đề xuất' for c in cols)), None)
    if top is None:
        return dict(part3=part3, sign_top=DEFAULT_SIGN_TOP, sign_bottom=DEFAULT_SIGN_BOTTOM)
    bottom = next((r for r in range(top, min(ws.max_row, top + 20) + 1)
                   if any(_text(ws.cell(r, c).value).startswith('Ngày') for c in cols)), top + 12)
    return dict(part3=part3, sign_top=top, sign_bottom=bottom)


def has_not_use_rule(ws, r):
    return bool(_NOT_USE_RE.match(_text(ws.cell(r, 2).value)))


def is_section(ws, r):
    return bool(SECTION_RE.match(_text(ws.cell(r, _ci('X')).value)))


def is_group(ws, r):
    return bool(_SUBTOTAL_RE.match(_text(ws.cell(r, _ci('AK')).value)))


def group_range(ws, r):
    m = _SUBTOTAL_RE.match(_text(ws.cell(r, _ci('AK')).value))
    return (int(m.group(1)), int(m.group(2))) if m else (r, r)


def report_row(rep, code):
    code = _text(code)
    if not code:
        return None
    for r in range(1, rep.max_row + 1):
        if _text(rep.cell(r, 5).value) == code:
            return r
    return None


# ---- the column B rule from the tool's own values -----------------------------------------------------------------

USE, NOT_USE, UNKNOWN = 'use', 'not_use', 'unknown'


def _num_state(v):
    """USE for a non-zero number, NOT_USE for 0/blank, UNKNOWN for a formula or text that is not a number."""
    if v is None or v == '':
        return NOT_USE
    if isinstance(v, bool):
        return USE if v else NOT_USE
    if isinstance(v, (int, float)):
        return USE if v != 0 else NOT_USE
    return UNKNOWN


def _any(states):
    states = list(states)
    if USE in states:
        return USE
    return UNKNOWN if UNKNOWN in states else NOT_USE


def _remark_state(ws, r):
    t = ws.cell(r, _ci('T')).value
    if isinstance(t, str):
        if _is_formula(t):
            return UNKNOWN
        return USE if t.strip() else NOT_USE
    if isinstance(t, (int, float)):
        return USE if t > 0 else NOT_USE
    ao = ws.cell(r, _ci('AO')).value
    if isinstance(ao, str) and not _is_formula(ao) and ao.strip():
        return USE
    return NOT_USE


def _report_states(ws, rep, r):
    """(prior approved, report average) states for line r, through the report sheet when sheet 2 looks them up."""
    code = ws.cell(r, _ci('Y')).value
    rr = report_row(rep, code) if rep is not None else None
    out = []
    # AB (prior approved) and AI (report monthly average)
    for col, rep_col in (('AB', 'N'), ('AI', 'L')):
        v = ws.cell(r, _ci(col)).value
        if not _is_formula(v):
            out.append(_num_state(v))
            continue
        if rr is None:
            out.append(UNKNOWN if rep is None else NOT_USE if 'VLOOKUP' not in v.upper() else UNKNOWN)
            continue
        rv = rep.cell(rr, _ci(rep_col)).value
        if rep_col == 'L' and _is_formula(rv):
            out.append(_report_total_state(rep, rr))
        else:
            out.append(_num_state(rv))
    return out


def _report_total_state(rep, rr):
    """The report row's K (= SUM(H:I) on the form): the report average is non-zero exactly when K is."""
    k = rep.cell(rr, _ci('K')).value
    if not _is_formula(k):
        return _num_state(k)
    if _SUM_HI_RE.match(k):
        h, i = rep.cell(rr, _ci('H')).value, rep.cell(rr, _ci('I')).value
        states = [_num_state(h), _num_state(i)]
        if UNKNOWN in states:
            return UNKNOWN
        total = (h or 0) + (i or 0)
        return USE if total != 0 else NOT_USE
    return UNKNOWN


def _month_starts(ws):
    start = ws.cell(6, _ci('AH')).value
    if not isinstance(start, datetime.datetime):
        return None
    out = [start]
    y, m = start.year, start.month
    for _ in range(11):
        m += 1
        if m > 12:
            y, m = y + 1, 1
        out.append(datetime.datetime(y, m, 1))
    return out


def _estimate_state(ws, r, months):
    """Is SUM(AQ:BB) non-zero? Month cells AQ:BB of the form read C (frequency), F (price) and H:S."""
    aq = [ws.cell(r, c).value for c in range(_ci('AQ'), _ci('BB') + 1)]
    if not all(_is_formula(v) and v.upper().startswith('=IF($C') for v in aq):
        if any(_is_formula(v) for v in aq):
            return UNKNOWN
        return _any(_num_state(v) for v in aq)
    freq = _text(ws.cell(r, 3).value)
    f = ws.cell(r, 6).value
    hs = [ws.cell(r, c).value for c in range(8, 20)]
    if _is_formula(f) or any(_is_formula(v) for v in hs):
        return UNKNOWN
    if freq == 'Schedule':
        return _any(_num_state(v) if not isinstance(v, str) else UNKNOWN for v in hs)
    fs = _num_state(f)
    if freq == 'Monthly' or fs != USE:
        return fs
    if not any(v not in (None, '') for v in hs):
        return NOT_USE
    if months is None:
        return UNKNOWN
    if all(isinstance(v, datetime.datetime) or v in (None, '') for v in hs):
        return USE if any(v in months for v in hs if v not in (None, '')) else NOT_USE
    return UNKNOWN


def line_state(ws, rep, r, months=None):
    """USE / NOT_USE / UNKNOWN for one leaf line, mirroring =IF(AND(AC=0,AM=" ",AO=" "),"Not Use","Use")."""
    prior, report = _report_states(ws, rep, r)
    return _any([_remark_state(ws, r), prior, report, _estimate_state(ws, r, months)])


def python_flags(wb):
    """(not_use rows, unknown rows) of the Management Fund sheet from the values in the workbook."""
    ws = wb[SHEET]
    rep = wb[REPORT_SHEET] if REPORT_SHEET in wb.sheetnames else None
    loc = locate(ws)
    months = _month_starts(ws)
    leaves, groups = {}, []
    for r in range(FILTER_FIRST_ROW, loc['part3'] + 1):
        if not has_not_use_rule(ws, r):
            continue
        if is_group(ws, r):
            groups.append(r)
        else:
            leaves[r] = line_state(ws, rep, r, months)
    states = dict(leaves)
    for g in groups:
        lo, hi = group_range(ws, g)
        # A group's prior and report figures are SUBTOTALs of its lines on the report sheet: the lines decide, and
        # only a typed-in figure on the group row itself counts on its own.
        own = [_remark_state(ws, g)] + [s for s in _report_states(ws, rep, g) if s != UNKNOWN]
        states[g] = _any(own + [s for rr, s in leaves.items() if lo <= rr <= hi])
    not_use = {r for r, s in states.items() if s == NOT_USE}
    unknown = {r for r, s in states.items() if s == UNKNOWN}
    return not_use, unknown


def excel_not_use_rows(recalc_path):
    """Rows whose column B reads "Not Use" in a workbook Excel has recalculated and saved (cached values)."""
    import openpyxl
    wb = openpyxl.load_workbook(recalc_path, data_only=True)
    try:
        ws = wb[SHEET]
        loc = locate(ws)
        return {r for r in range(FILTER_FIRST_ROW, loc['part3'] + 1)
                if _text(ws.cell(r, 2).value).lower() == 'not use'}
    finally:
        wb.close()


# ---- the openpyxl layer -------------------------------------------------------------------------------------------

def _hide_rows(ws, loc, not_use):
    for r in range(FILTER_FIRST_ROW, loc['part3'] + 1):
        ws.row_dimensions[r].hidden = (r in not_use) and not is_section(ws, r)
    for r in range(loc['part3'] + 1, loc['sign_top']):
        ws.row_dimensions[r].hidden = True
    for r in range(loc['sign_top'], loc['sign_bottom'] + 1):
        ws.row_dimensions[r].hidden = False


def _split_column_ranges(ws, letters):
    """Give each of `letters` its own <col> entry: a range entry covering it is cut into single columns."""
    wanted = {_ci(c) for c in letters}
    for key, dim in list(ws.column_dimensions.items()):
        lo, hi = dim.min or _ci(key), dim.max or _ci(key)
        if hi <= lo or not any(lo <= i <= hi for i in wanted):
            continue
        dim.min, dim.max = lo, lo
        for i in range(lo + 1, hi + 1):
            nd = ColumnDimension(ws, index=_cl(i), width=dim.width, bestFit=dim.bestFit, hidden=dim.hidden,
                                 outlineLevel=dim.outlineLevel, collapsed=dim.collapsed, customWidth=dim.customWidth)
            nd._style = dim._style
            ws.column_dimensions[_cl(i)] = nd


def _fold_columns(ws):
    _split_column_ranges(ws, FOLD_COLS)
    for c in FOLD_COLS:
        d = ws.column_dimensions[c]
        if d.width is None:
            d.width = 28
        d.outlineLevel = 2
        d.hidden = True


def _rebuild_signature(ws, loc):
    top, bottom = loc['sign_top'], loc['sign_bottom']
    first, last = _ci(FIRST_COL), _ci(A3_LAST_COL)
    for m in list(ws.merged_cells.ranges):
        if m.max_row >= top and m.min_row <= bottom and m.max_col >= first and m.min_col <= last:
            ws.unmerge_cells(str(m))
    for r in range(top, bottom + 1):
        for c in range(first, last + 1):
            ws.cell(r, c).value = None
    rows = [(top, 0, Font(name=_SIGN_FONT, size=_SIGN_SIZE, italic=True)),
            (top + 1, 1, Font(name=_SIGN_FONT, size=_SIGN_SIZE, bold=True)),
            (top + 2, 2, Font(name=_SIGN_FONT, size=_SIGN_SIZE - 1, italic=True)),
            (bottom, 3, Font(name=_SIGN_FONT, size=_SIGN_SIZE - 1))]
    wrap = Alignment(horizontal='center', vertical='center', wrap_text=True)
    shrink = Alignment(horizontal='center', vertical='center', shrink_to_fit=True)   # one line even in narrow boxes
    for (head, role), (c1, c2) in zip(SIGNERS, SIGN_SPANS):
        texts = (head, role, INSTRUCTION, DATE_LINE)
        for r, k, font in rows:
            cell = ws.cell(r, _ci(c1), texts[k])
            cell.font = font
            cell.alignment = wrap if k < 2 else shrink
            if c1 != c2:
                ws.merge_cells(f'{c1}{r}:{c2}{r}')


def _print_setup(ws, loc):
    ws.print_area = f'{FIRST_COL}{FIRST_PRINT_ROW}:{A3_LAST_COL}{loc["sign_bottom"]}'
    ws.print_title_rows = TITLE_ROWS
    ws.page_setup.paperSize = PAPER_A3
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    if ws.sheet_properties.pageSetUpPr is None:
        ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    else:
        ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.oddFooter.center.text = FOOTER
    ws.evenFooter.center.text = FOOTER


def _filter(ws, loc):
    ws.auto_filter.ref = f'A{FILTER_FIRST_ROW}:{FILTER_LAST_COL}{loc["part3"]}'
    ws.auto_filter.filterColumn = []
    ws.auto_filter.add_filter_column(1, ['Use'], blank=True)


def apply(wb, not_use=None):
    """Set up '2. Budget-Management Fund' for printing (see module docstring). `not_use`: rows Excel marks "Not Use"
    in column B; when None they are worked out from the workbook's own values (unknown lines stay visible).
    Returns the set of hidden table rows."""
    if SHEET not in wb.sheetnames:
        return set()
    ws = wb[SHEET]
    if not_use is None:
        not_use, _unknown = python_flags(wb)
    loc = locate(ws)
    _rebuild_signature(ws, loc)
    loc = locate(ws)
    _hide_rows(ws, loc, set(not_use))
    _fold_columns(ws)
    _filter(ws, loc)
    _print_setup(ws, loc)
    return {r for r in range(FILTER_FIRST_ROW, loc['part3'] + 1) if ws.row_dimensions[r].hidden}


# ---- the Excel layer: exact row flags, PDF export -----------------------------------------------------------------

def excel_flags(path):
    """Rows whose column B reads "Not Use" once Excel recalculates a copy of `path`. None when Excel is unavailable."""
    try:
        import pythoncom
        import win32com.client as w32
    except ImportError:
        return None
    work_dir = tempfile.mkdtemp(prefix='print_flags_')
    work = os.path.join(work_dir, os.path.basename(path))
    shutil.copy2(path, work)
    pythoncom.CoInitialize()
    xl = wb = None
    try:
        xl = w32.DispatchEx('Excel.Application')
        xl.Visible = False
        xl.DisplayAlerts = False
        wb = xl.Workbooks.Open(work, UpdateLinks=0, ReadOnly=True)
        xl.CalculateFullRebuild()
        ws = wb.Worksheets(SHEET)
        part3 = next((r for r in range(11, 700) if _text(ws.Range(f'X{r}').Value).upper().startswith('PART 3')),
                     DEFAULT_PART3_ROW)
        flags = ws.Range(f'B{FILTER_FIRST_ROW}:B{part3}').Value
        return {FILTER_FIRST_ROW + i for i, row in enumerate(flags) if _text(row[0]).lower() == 'not use'}
    except Exception:
        return None
    finally:
        if wb is not None:
            try:
                wb.Close(SaveChanges=False)
            except Exception:
                pass
        if xl is not None:
            try:
                xl.Quit()
            except Exception:
                pass
        pythoncom.CoUninitialize()
        shutil.rmtree(work_dir, ignore_errors=True)


def refresh_with_excel(path):
    """Re-apply the layout to the saved deliverable with Excel's own column B. Returns the number of hidden rows, or
    None when Excel is unavailable (the rows the tool could not evaluate then stay visible)."""
    not_use = excel_flags(path)
    if not_use is None:
        return None
    import openpyxl
    wb = openpyxl.load_workbook(path)
    try:
        hidden = apply(wb, not_use=not_use)
        wb.save(path)
    finally:
        wb.close()
    try:
        from generate_project_output import _strip_onedrive_zip_artifacts
        _strip_onedrive_zip_artifacts(path)
    except Exception:
        pass
    return len(hidden)

PAPERS = {'A4': (PAPER_A4, A4_LAST_COL), 'A3': (PAPER_A3, A3_LAST_COL)}


class PrintError(Exception):
    """A plain-Vietnamese reason the PDF could not be made; the deliverable is untouched."""


def pdf_name(deliverable, paper):
    stem = os.path.splitext(os.path.basename(deliverable))[0]
    return f'{stem} - In {paper}.pdf'


def _sign_page_ok(pdf_path):
    """True when the page that holds 'Đề xuất' also holds all 8 date lines; None when PyMuPDF is not installed."""
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf  # noqa: N813  (older PyMuPDF name)
        except ImportError:
            return None
    doc = pymupdf.open(pdf_path)
    try:
        for page in doc:
            text = page.get_text()
            if 'Đề xuất' in text:
                return text.count('Ngày:') >= len(SIGNERS)
        return False
    finally:
        doc.close()


def export_pdf(deliverable, paper, out_pdf):
    """Export the Management Fund sheet of `deliverable` as a PDF on `paper` ('A4' or 'A3'). Works on a copy; returns
    the page count when PyMuPDF is available, else None. Raises PrintError with a plain reason."""
    if paper not in PAPERS:
        raise PrintError(f'Khổ giấy không hợp lệ: {paper}. Chọn A4 hoặc A3.')
    folder, name = os.path.split(os.path.abspath(deliverable))
    if os.path.exists(os.path.join(folder, '~$' + name)):
        raise PrintError(f"Bản giao '{name}' đang mở trong Excel trên máy chủ. Đóng file rồi bấm lại.")
    try:
        import pythoncom
        import win32com.client as w32
    except ImportError as exc:
        raise PrintError('Xuất PDF cần Microsoft Excel trên máy chủ (thiếu pywin32).') from exc
    paper_size, last_col = PAPERS[paper]
    work_dir = tempfile.mkdtemp(prefix='print_')
    work = os.path.join(work_dir, name)
    shutil.copy2(deliverable, work)
    tmp_pdf = os.path.join(work_dir, 'out.pdf')
    pythoncom.CoInitialize()
    xl = wb = None
    try:
        try:
            xl = w32.DispatchEx('Excel.Application')
        except Exception as exc:
            raise PrintError('Xuất PDF cần Microsoft Excel trên máy chủ; không mở được Excel.') from exc
        xl.Visible = False
        xl.DisplayAlerts = False
        wb = xl.Workbooks.Open(work, UpdateLinks=0, ReadOnly=True)
        xl.CalculateFull()
        ws = wb.Worksheets(SHEET)
        part3 = next((r for r in range(11, 700) if _text(ws.Range(f'X{r}').Value).upper().startswith('PART 3')),
                     DEFAULT_PART3_ROW)
        top = next((r for r in range(part3 + 1, part3 + 40)
                    if any(_text(ws.Cells(r, c).Value) == 'Đề xuất' for c in range(_ci('X'), _ci('BB') + 1))),
                   DEFAULT_SIGN_TOP)
        bottom = next((r for r in range(top, top + 20)
                       if any(_text(ws.Cells(r, c).Value).startswith('Ngày')
                              for c in range(_ci('X'), _ci('BB') + 1))), top + 12)
        try:                                   # start from every row shown; the filter itself stays on the sheet
            if ws.FilterMode:
                ws.ShowAllData()
        except Exception:
            pass
        for r in range(FILTER_FIRST_ROW, part3 + 1):
            not_use = _text(ws.Range(f'B{r}').Text).lower() == 'not use'
            section = bool(SECTION_RE.match(_text(ws.Range(f'X{r}').Text)))
            ws.Rows(r).Hidden = not_use and not section
        for r in range(part3 + 1, top):
            ws.Rows(r).Hidden = True
        for r in range(top, bottom + 1):
            ws.Rows(r).Hidden = False
        for c in FOLD_COLS:
            ws.Columns(c).Hidden = True
        ps = ws.PageSetup
        ps.PrintArea = f'${FIRST_COL}${FIRST_PRINT_ROW}:${last_col}${bottom}'
        ps.PrintTitleRows = '$9:$10'
        ps.PaperSize = paper_size
        ps.Orientation = 2
        ps.Zoom = False
        ps.FitToPagesWide = 1
        ps.FitToPagesTall = False
        ps.CenterFooter = FOOTER
        ws.ResetAllPageBreaks()
        ws.ExportAsFixedFormat(0, tmp_pdf, 0, True, False)
        ok = _sign_page_ok(tmp_pdf)
        if ok is False or (ok is None and _break_inside(ws, top, bottom)):
            ws.HPageBreaks.Add(ws.Range(f'A{top}'))
            ws.ExportAsFixedFormat(0, tmp_pdf, 0, True, False)
        wb.Close(SaveChanges=False)
        wb = None
    except PrintError:
        raise
    except Exception as exc:
        raise PrintError(f'Excel không xuất được PDF ({type(exc).__name__}). Bản giao không bị thay đổi.') from exc
    finally:
        if wb is not None:
            try:
                wb.Close(SaveChanges=False)
            except Exception:
                pass
        if xl is not None:
            try:
                xl.Quit()
            except Exception:
                pass
        pythoncom.CoUninitialize()
    os.makedirs(os.path.dirname(os.path.abspath(out_pdf)), exist_ok=True)
    shutil.copyfile(tmp_pdf, out_pdf)
    shutil.rmtree(work_dir, ignore_errors=True)
    try:
        import pymupdf
        with pymupdf.open(out_pdf) as doc:
            return doc.page_count
    except Exception:
        return None


def _break_inside(ws, top, bottom):
    try:
        ws.DisplayPageBreaks = True
        return any(top < ws.HPageBreaks(i).Location.Row <= bottom for i in range(1, ws.HPageBreaks.Count + 1))
    except Exception:
        return False
