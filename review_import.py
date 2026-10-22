"""Budget Review, step 1 (change add-budget-renewal-mode, design D1-D8): read last year's approved budget workbook
and fill the Existing-project input form from it.

For a building Savills already runs, the PM's starting point is the budget approved for the year that is ending.
This module reads that workbook (the Savills form, 2026 or 2027 layout) the way the real-budget scan store does,
by content and headers rather than fixed addresses:

- `read_prior_budget(path, workdir)`: both fund sheets (Management Fund, Common area Fund), every leaf line of
  sections R and E with its code, item text, the approved annual figure from the year column, the twelve months,
  the remark, the source row and flags; the sheet's own R and E figures; the VAT basis; the period.
- `read_info(wb)`: the project's scale from `0. Info`: fee-paying area, units and applied rate per product, the
  parking bay counts, the project name.
- `write_form(...)`: a filled input form in Existing-project mode (a fresh form from the builder, or a dated copy
  of a form the user names; never the original), with the new sheet `Prior-Year Budget` (every line read, plus an
  `IMPORT NOTES` block listing what could not be read, what is not on the 2027 form, and which scale fields were
  left blank for the PM).
- `read_prior_budget_sheet(wb)`: the sheet read back, for review.py and the tests.

Nothing here is read by the generators: New-prospect mode does not change. Facts the file does not carry are never
invented: they stay blank and are listed, or come from a facts file the user gives (label -> value).
"""
import csv
import datetime
import io
import json
import os
import re
import shutil
import unicodedata
import zipfile
from dataclasses import dataclass, field

import openpyxl
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

import budget_rows as br
import existing_staffing as es
import existing_utilities as eu
import operating_inputs as oi
from input_labels import LabelNotFound, normalise

_HERE = os.path.dirname(os.path.abspath(__file__))
_BUDGET_AGENT = os.path.dirname(_HERE)
TEMPLATE_PATH = os.path.join(os.path.dirname(_BUDGET_AGENT), 'input', 'template', '2027 Resi Budget Form (IT team).xlsx')
CATALOGUE_PATH = os.path.join(_BUDGET_AGENT, 'data', 'master_list_verified', 'Costing_Method_Catalogue.csv')

# The two fund sheets of the form, by the template's names; a file on the 2026 layout uses the same names.
FUNDS = ('MF', 'CA')
FUND_SHEETS = {'MF': '2. Budget-Management Fund', 'CA': '2.2 Common area Fund'}
FUND_VI = {'MF': 'Quỹ quản lý vận hành', 'CA': 'Quỹ khai thác khu vực chung'}
SECTIONS_COMPARED = ('R', 'E')

# ---- the scan store's rules (scan_budgets.py, 2026-10-07), ported --------------------------------------------
CODE_RE = re.compile(r'^(E[A-Z]{0,3}|R[A-Z]{0,2}|D[A-Z]{0,2}|PL|VAT|CIT)[0-9#]*(\.[A-Za-z0-9#]+)*[a-z]?$')
SUFFIX_RE = re.compile(r'^(\.[A-Za-z0-9#]+|[a-z]|\d+)$')
LEAF_DESPITE_INDICATOR = {'EM#', 'ES#', 'EE#', 'ESR'}
DERIVED = {'PL1', 'PL2'}
TOL = 1.0
MAX_ROWS, MAX_COLS = 1500, 90
HDR_PRI = [(re.compile(r'total budget of year'), 1), (re.compile(r'estimate budget of year|estimate budget'), 2),
           (re.compile(r'total budget|ngân sách năm|cả năm'), 3)]
HDR_BAD = re.compile(r'approved|actual|average|allocated|%|expected|trung bình|thực tế|dự kiến')

# Lines that carry no VAT on either basis (the scan store's v2 rule, as compare_m3.py): salaries, taxes and
# fees, bank fees, bank interest.
NO_VAT_CODES = {'EMH2', 'EMH3', 'EMH4', 'EMH6', 'EMH8', 'EMH11', 'EMH12', 'EMO1', 'EMH10', 'EMA17', 'EMB1'}
NO_VAT_PREFIXES = ('CIT', 'VAT', 'RO2')

# Old-form codes mapped to 2027 codes. Empty on purpose: a mapping goes here only once the Head of PM confirms it
# (design D4). Until then a code the 2027 form does not carry is listed, not mapped.
CODE_ALIASES = {}

# Flags (Vietnamese, shown on the Prior-Year Budget sheet and the Review sheet).
FLAG_MONTHS = '12 tháng không khớp cột năm'
FLAG_NOT_ON_FORM = 'mã không có trên form 2027'
FLAG_DUP = 'mã lặp trên sheet, đã cộng'
FLAG_NO_CODE = 'dòng có số nhưng không có mã'

# The catalogue's method keys in short Vietnamese (design D6). A key not here falls back to the English text.
METHOD_VI = {
    'area-x-rate': 'diện tích × đơn giá',
    'bays-x-fill-x-rate': 'chỗ xe × lấp đầy × giá',
    'visitor-parking-estimate': 'ước lượng xe vãng lai',
    'benchmark-by-comparable': 'so sánh dự án tương đương',
    'benchmark-or-package': 'so sánh hoặc gói dịch vụ',
    'estimate-or-benchmark': 'ước lượng hoặc so sánh',
    'frequency-x-unit-cost': 'số lần × đơn giá',
    'consumption-x-tariff': 'tiêu thụ × biểu giá',
    'official-tariff-table': 'biểu giá nhà nước',
    'headcount-x-consumption': 'số người × định mức',
    'headcount-from-staffing-sheet': 'theo bảng nhân sự',
    'contract-headcount-x-12': 'hợp đồng: số người × 12',
    'contract-posts-x-24h-rate': 'hợp đồng: vị trí × giá 24h',
    'contract-posts-x-rate': 'hợp đồng: vị trí × giá',
    'contract-fixed-or-percent-of-fee': 'hợp đồng: cố định hoặc % phí',
    'a1-live-formula-plus-unplaced-rows': 'bảng lương A1',
    'labour-law-driver': 'theo luật lao động',
    'regulation-count-x-cost': 'quy định: số lượng × chi phí',
    'regulation-fixed-estimate': 'quy định: mức cố định',
    'regulation-fixed-fee': 'quy định: phí cố định',
    'regulation-driven': 'theo quy định',
    'asset-list-sum-depreciated-24mo': 'danh mục tài sản, khấu hao 24 tháng',
    'asset-value-x-premium-rate': 'giá trị tài sản × tỷ lệ phí',
    'mirror-of-ESI1': 'theo ESI1',
    'itemised-list': 'danh mục chi tiết',
    'programme-itemised': 'chương trình chi tiết',
    'annual-quotation': 'báo giá năm',
    'pool-volume-x-dose-x-price': 'thể tích hồ × liều × giá',
    'fund-allocation-rule': 'phân bổ theo quỹ',
    'percent-of-section': '% của nhóm',
    'section-catch-all': 'dòng gom của nhóm',
    'section-total': 'tổng nhóm',
    'linked-from-common-area-fund': 'nối từ quỹ khu vực chung',
    'collect-on-behalf-pair': 'thu hộ chi hộ',
    'developer-covers-unlet': 'CĐT trả phần chưa bàn giao',
    'rate-on-extra-revenue': 'tỷ lệ trên doanh thu khác',
    'reserve-schedule': 'lịch trích quỹ',
    'formula-from-year-2': 'công thức từ năm 2',
    'conditional-luxury-only': 'chỉ dự án cao cấp',
    'not-estimated': 'không ước lượng',
    'unclear': 'chưa rõ phương pháp',
    'manual-per-project': 'PM nhập theo dự án',
}
NO_METHOD_KEYS = {'not-estimated', 'unclear', 'manual-per-project'}

# `0. Info` product rows: the form's product label -> the names the Info sheet may use (matched after NFC and
# casefold, on the whole text or its start).
PRODUCT_ALIASES = {
    'Apartment': ('apartment', 'căn hộ'),
    'Officetel': ('officetel',),
    'Office': ('office', 'văn phòng'),
    'Shopping Mall': ('shopping mall', 'thương mại', 'trung tâm thương mại', 'mall'),
    'Retail': ('retail', 'bán lẻ'),
    'Shop Apartment': ('shop apartment', 'shop-apartment'),
    'Shophouse': ('shophouse', 'shop house', 'nhà phố'),
    'Villas': ('villas', 'villa', 'biệt thự'),
    'Nursery / Nhà trẻ': ('nursery', 'kindergarten', 'nhà trẻ'),
}
PRODUCT_CODES = {'Apartment': 'RM.AP', 'Officetel': 'RM.OT', 'Office': 'RM.OF', 'Shopping Mall': 'RM.SM',
                 'Retail': 'RM.RE', 'Shop Apartment': 'RM.SA', 'Shophouse': 'RM.SH', 'Villas': 'RM.VI',
                 'Nursery / Nhà trẻ': 'RM.KG'}
INFO_SHEET_PREFIXES = ('0. info', 'info', 'thông tin')

# Project Info fields the file does not carry: blanked on a fresh form (its placeholders would otherwise pass as
# facts) and listed for the PM, unless the facts file gives them (design D7).
PM_SCALE_LABELS = ('Site Area', 'Garden / Landscape Area', 'Circulation / Hardscape Area', 'Floor Count',
                   'Tower Count', 'Gate / Entrance Count', 'District', 'City / Province', 'Street Address',
                   'Latitude', 'Longitude', 'Passenger Elevators per Tower', 'Number of Basements',
                   'Has Swimming Pool?', 'Number of Pools', 'Pool Area', 'Pool Volume')

NUMERIC_SCALE_LABELS = ('Site Area', 'Garden / Landscape Area', 'Circulation / Hardscape Area', 'Floor Count',
                        'Tower Count', 'Gate / Entrance Count', 'Latitude', 'Longitude', 'Passenger Elevators per Tower',
                        'Number of Basements', 'Number of Pools', 'Pool Area', 'Pool Volume')

# The new input sheet (design D8).
SHEET = 'Prior-Year Budget'
SEC_LINES = 'PRIOR-YEAR BUDGET'
SEC_NOTES = 'IMPORT NOTES'
MONTH_KEYS = [f'm{i}' for i in range(1, 13)]
LINE_COLS = {'fund': 'Fund Sheet', 'section': 'Section', 'code': 'Code', 'item': 'Item',
             'approved': 'Approved (VND/year)', 'incl_vat': 'Includes VAT (Yes/No)',
             **{k: f'Month {i}' for i, k in enumerate(MONTH_KEYS, start=1)},
             'src_sheet': 'Source Sheet', 'src_row': 'Source Row', 'remark': 'Remark', 'flags': 'Flags'}
NOTE_COLS = {'kind': 'Kind', 'where': 'Code or Field', 'text': 'Note'}
NOTE_UNREAD = 'không đọc được'
NOTE_NOT_ON_FORM = 'không có trên form 2027'
NOTE_BLANK = 'để trống, PM điền'
NOTE_FACT = 'từ file dữ kiện'
NOTE_INFO = 'đọc từ 0. Info'
NOTE_CHECK = 'cần PM xác nhận'
NOTE_SOURCE = 'nguồn'


class PriorBudgetError(ValueError):
    """The approved budget workbook cannot be read; the message names the file and the reason."""


@dataclass
class PriorLine:
    fund: str
    sheet: str
    row: int
    section: str
    code: str
    item: str
    annual: float
    months: list
    remark: str = ''
    flags: list = field(default_factory=list)
    on_form: bool = True


@dataclass
class FundRead:
    fund: str
    sheet: str
    lines: list
    anchors: dict                 # {'R': float|None, 'E': float|None}
    value_col: int                # 1-based
    value_how: str                # 'reconciled' | 'header_only'
    month_cols: list              # 1-based columns, in order
    period: list                  # [(y, m), ...] one per month column
    vat_basis: str                # 'excl' | 'incl' | 'unknown'
    flags: list = field(default_factory=list)
    tie_state: str = ''           # budget_rows.explain_tie: ok | ok_filter | ok_double_count | mismatch | no_anchor
    tie_notes: list = field(default_factory=list)

    @property
    def ties(self):
        """The leaf sums tie to the sheet's own R and E rows, directly or after explanation."""
        return self.tie_state.startswith('ok')

    def section_total(self, section):
        return sum(l.annual for l in self.lines if l.section == section)


@dataclass
class PriorBudget:
    path: str
    project_name: str
    funds: dict                   # fund -> FundRead
    notes: list                   # (kind, where, text)
    budget_year: int
    period: list                  # [(y, m), ...] of the Management Fund sheet

    def lines(self):
        for fund in FUNDS:
            fr = self.funds.get(fund)
            if fr:
                yield from fr.lines


@dataclass
class ProjectInfo:
    name: str = ''
    products: dict = field(default_factory=dict)   # form label -> dict(gfa, nfa, units, rate)
    car_bays: 'float | None' = None
    moto_bays: 'float | None' = None
    notes: list = field(default_factory=list)
    sheet: str = ''


# ------------------------------------------------------------------------------------------------
# Small helpers
# ------------------------------------------------------------------------------------------------
def _nfc(s):
    return unicodedata.normalize('NFC', s) if isinstance(s, str) else s


def _key(s):
    return ' '.join(_nfc(str(s or '')).split()).casefold()


def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def no_vat(code):
    code = (code or '').strip()
    return code in NO_VAT_CODES or code.startswith(NO_VAT_PREFIXES)


def method_vi(method):
    method = (method or '').strip()
    return METHOD_VI.get(method, method)


def fund_of(name):
    """The scan store's sheet-name rule: which fund a sheet belongs to."""
    n = _key(name)
    if 'sinking' in n:
        return 'SF'
    if 'common area' in n:
        return 'CA'
    if re.match(r'ngân sách 20\d\d', n):
        return 'MF'
    if re.search(r'chi tiết (dự toán )?ngân sách', n) and not re.search(r'pre|năm 2', n):
        return 'MF'
    if 'management' in n or re.search(r'budget-m\b|budget-mf|\bmf\b|\bqvh\b|vận hành', n) or n.startswith('2'):
        return 'MF'
    return 'OTHER'


def kind_of(name):
    n = _key(name)
    if re.search(r'report|so sánh|kh - th|tổng hợp|chi phí qvh|chi phí qbt|rate to allocate|mapping|mr\s*14|p\s*&\s*l', n):
        return 'report'
    if re.search(r'\bpre\b|tkt|pre-|25%|50%|75%|95%|100%|\bn2\b|năm 2|year 2|op2|y2|2nd year', n):
        return 'other'
    return 'budget'


def vat_of(text):
    t = _key(text)
    if 'vat' not in t and 'gtgt' not in t:
        return None
    if re.search(r'excl|chưa|không bao|xcl', t):
        return 'excl'
    if re.search(r'incl|bao gồm|đã gồm|ncl', t):
        return 'incl'
    return None


def _as_month(v):
    if isinstance(v, (datetime.datetime, datetime.date)) and 2010 <= v.year <= 2040:
        return (v.year, v.month)
    if isinstance(v, str):
        m = re.search(r'(?<!\d)(\d{1,2})\s*[/.]\s*(20[1-4]\d)(?!\d)', v)
        if m and 1 <= int(m.group(1)) <= 12:
            return (int(m.group(2)), int(m.group(1)))
    return None


# ------------------------------------------------------------------------------------------------
# Opening the workbook
# ------------------------------------------------------------------------------------------------
def open_workbook(path, workdir=None):
    """Read-only, values only. A workbook openpyxl refuses (broken defined names, OneDrive artefacts) is read
    from a stripped copy written into `workdir` (never beside the source). PDF and xlsb stop with a message."""
    if not os.path.exists(path):
        raise PriorBudgetError(f'{path}: file not found.')
    ext = os.path.splitext(path)[1].lower()
    if ext != '.xlsx':
        raise PriorBudgetError(f'{os.path.basename(path)}: a {ext or "file without extension"} cannot be read; the '
                               f'approved budget must be an .xlsx workbook on the Savills form (PDF and xlsb are not read).')
    try:
        return openpyxl.load_workbook(path, read_only=True, data_only=True), path
    except Exception as first:
        if not workdir:
            raise PriorBudgetError(f'{os.path.basename(path)}: openpyxl cannot open it ({type(first).__name__}: {first}) '
                                   f'and no work folder was given for a repaired copy.') from None
        os.makedirs(workdir, exist_ok=True)
        dst = os.path.join(workdir, os.path.splitext(os.path.basename(path))[0] + '__repaired.xlsx')
        try:
            with zipfile.ZipFile(path) as zin, zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zout:
                for it in zin.infolist():
                    if 'trash' in it.filename.lower():
                        continue
                    b = zin.read(it.filename)
                    if it.filename == 'xl/workbook.xml':
                        b = re.sub(r'<definedNames>.*?</definedNames>', '', b.decode('utf8'), flags=re.S).encode('utf8')
                    zout.writestr(it, b)
            return openpyxl.load_workbook(dst, read_only=True, data_only=True), dst
        except Exception as second:
            raise PriorBudgetError(f'{os.path.basename(path)}: cannot be read even after stripping its defined names '
                                   f'({type(second).__name__}: {second}).') from None


def choose_fund_sheets(sheetnames, states=None):
    """{'MF': sheet, 'CA': sheet or None}. The template's own names win; otherwise the first budget sheet of the
    fund by the scan store's name rules, a visible one before a hidden one. `states`: {sheet: 'visible' | 'hidden'
    | 'veryHidden'}; without it every sheet counts as visible."""
    states = states or {}
    chosen = {}
    for fund in FUNDS:
        exact = next((n for n in sheetnames if _key(n) == _key(FUND_SHEETS[fund])), None)
        if exact:
            chosen[fund] = exact
            continue
        cands = [n for n in sheetnames if fund_of(n) == fund and kind_of(n) == 'budget']
        cands.sort(key=lambda n: states.get(n, 'visible') != 'visible')          # stable: file order within each
        chosen[fund] = cands[0] if cands else None
    if chosen['MF'] is None:
        raise PriorBudgetError('no Management Fund budget sheet found (looked for a sheet named like '
                               f"'{FUND_SHEETS['MF']}'). Sheets: {', '.join(sheetnames)}")
    return chosen


# ------------------------------------------------------------------------------------------------
# Reading one fund sheet
# ------------------------------------------------------------------------------------------------
def _rows_of(ws):
    rows = []
    for row in ws.iter_rows(min_row=1, max_row=MAX_ROWS, max_col=MAX_COLS, values_only=True):
        rows.append(tuple(row))
    while rows and all(v is None for v in rows[-1]):
        rows.pop()
    return rows


def read_fund_sheet(ws, fund, sheet_name, ws_formulas=None, layout=None):
    """One fund sheet -> FundRead, by the scan store's rules (design D1, D2) and the aggregate-row and tie rules
    of budget_rows (change read-aggregate-rows-by-formula). `ws_formulas`: the same sheet read without data_only;
    `layout`: (hidden rows, auto-filter range) from budget_rows.sheet_layout. Without them only the prefix rule
    finds aggregate rows and no tie is explained by a filter."""
    rows = _rows_of(ws)
    nrows = len(rows)
    frows = _rows_of(ws_formulas) if ws_formulas is not None else []
    hidden, af_ref = layout if layout else (set(), None)

    def get(r, c):
        return rows[r][c] if 0 <= r < nrows and 0 <= c < len(rows[r]) else None

    def fget(r, c):
        return frows[r][c] if 0 <= r < len(frows) and 0 <= c < len(frows[r]) else None

    # code column: the one with the most code-like strings
    cnt = {}
    for row in rows:
        for i in range(min(60, len(row))):
            v = row[i]
            if isinstance(v, str):
                s = v.strip()
                if CODE_RE.match(s) and 1 <= len(s) <= 12 and re.search(r'\d|^[RED]$', s):
                    cnt[i] = cnt.get(i, 0) + 1
    if not cnt or max(cnt.values()) < 10:
        raise PriorBudgetError(f"sheet '{sheet_name}': no column of budget codes found.")
    cc = max(cnt, key=lambda c: cnt[c])
    ic = cc - 1
    code_at = {r: _nfc(get(r, cc).strip()) for r in range(nrows) if isinstance(get(r, cc), str) and get(r, cc).strip()}
    ind_at = {r: str(get(r, ic)).strip() for r in range(nrows) if get(r, ic) not in (None, '')}

    r_row = next((r for r, c in code_at.items() if c == 'R' and r in ind_at), None)
    e_row = next((r for r, c in code_at.items() if c == 'E' and r in ind_at and r_row is not None and r > r_row), None)
    pl1 = next((r for r, c in code_at.items() if c == 'PL1'), None)
    pl2 = next((r for r, c in code_at.items() if c.startswith('PL2')), None)
    if None in (r_row, e_row, pl1):
        raise PriorBudgetError(f"sheet '{sheet_name}': the R, E and PL1 rows were not all found (R row "
                               f"{r_row}, E row {e_row}, PL1 row {pl1}).")
    end_row = pl2 if pl2 is not None else pl1

    def header(c):
        return ' '.join(str(get(r, c)) for r in range(0, 14) if isinstance(get(r, c), str)).lower()

    # leaves: coded rows between R and PL1 without an indicator (plus the store's exceptions and a parent whose
    # children are all empty)
    coded = [(r, code_at.get(r), ind_at.get(r)) for r in sorted(set(code_at) | set(ind_at))]
    childless, child_rows = set(), {}
    for n, (r, c, i) in enumerate(coded):
        if not (c and i) or not c.startswith('E'):
            continue
        under, next_ind = [], None
        for r2, c2, i2 in coded[n + 1:]:
            if i2:
                next_ind = c2
                break
            if c2:
                under.append(r2)
        child_rows[c] = under
        if not under and not (next_ind and next_ind.startswith(c)):
            childless.add(c)
    leaves = []
    for r, code in code_at.items():
        if code in DERIVED or code.startswith('PL') or not CODE_RE.match(code) or len(code) > 12:
            continue
        if r <= r_row or r >= pl1:
            continue
        sec = 'R' if r < e_row else 'E'
        ind = ind_at.get(r)
        if ind and code not in LEAF_DESPITE_INDICATOR and code not in childless:
            if child_rows.get(code):
                leaves.append({'row': r, 'code': code, 'section': sec, 'cond_rows': child_rows[code]})
            continue
        leaves.append({'row': r, 'code': code, 'section': sec})

    kids = br.prefix_kids([lf['code'] for lf in leaves])
    candidates = {lf['row'] for lf in leaves if not ind_at.get(lf['row'])}   # rows with an indicator keep their rules
    coded_rows = set(code_at)

    def col_sums(c):
        vals = [_num(get(lf['row'], c)) for lf in leaves]
        for i, lf in enumerate(leaves):
            if lf.get('cond_rows') is not None:
                own = vals[i]
                if not (own is not None and abs(own) > TOL and all((_num(get(rr, c)) or 0.0) == 0.0 for rr in lf['cond_rows'])):
                    vals[i] = None
        aggs = br.find_aggregates(fget, candidates, coded_rows, c) if frows else {}
        gone = br.dropped(vals, leaves, kids, aggs)
        sums = {'R': 0.0, 'E': 0.0}
        seen = False
        for i, v in enumerate(vals):
            if v is not None:
                seen = True
                if i not in gone:
                    sums[leaves[i]['section']] += v
        return sums, seen, vals, gone, aggs

    ncols = max(len(r) for r in rows)
    anchor_rows = {'R': r_row, 'E': e_row}
    n_hidden = sum(1 for h in hidden if r_row < h < pl1)
    filtered = br.filter_on(af_ref, n_hidden, pl1 - r_row - 1)

    def tie(c, vals, gone, aggs):
        items = [(lf['row'], lf['section'], vals[i]) for i, lf in enumerate(leaves)
                 if vals[i] is not None and i not in gone]
        doubles = br.double_counted(leaves, vals, gone, aggs, fget, c)
        anchors_c = {s: _num(get(anchor_rows[s], c)) for s in SECTIONS_COMPARED}
        return br.explain_tie(SECTIONS_COMPARED, items, doubles, anchors_c, hidden, filtered, n_hidden)

    passing = []
    for c in range(cc + 2, ncols):
        sums, seen, vals, gone, aggs = col_sums(c)
        if not seen:
            continue
        t = tie(c, vals, gone, aggs)
        if t['state'].startswith('ok') and abs(sums['R']) + abs(sums['E']) > 0:
            passing.append((c, t['state'], sums['R']))
    if any(abs(r_sum) > TOL for _, _, r_sum in passing):            # a column with no revenue does not tie
        passing = [p for p in passing if abs(p[2]) > TOL]
    direct = {c for c, state, _ in passing if state == 'ok'}
    passing = [c for c, _, _ in passing]

    def pri(c):
        h = header(c)
        if HDR_BAD.search(h) and not re.search(r'total budget of year', h):
            return 9
        for rx, p in HDR_PRI:
            if rx.search(h):
                return p
        return 5

    hdr_cols = [c for c in range(cc + 2, ncols) if pri(c) <= 3]
    flags = []
    if passing:
        value_col, value_how = min(passing, key=lambda c: (c not in direct, pri(c), c)), 'reconciled'
    elif hdr_cols:
        value_col, value_how = min(hdr_cols, key=lambda c: (pri(c), c)), 'header_only'
        flags.append(f"cột giá trị '{get_column_letter(value_col + 1)}' chọn theo tiêu đề, tổng dòng lá không khớp dòng R/E của sheet")
    else:
        raise PriorBudgetError(f"sheet '{sheet_name}': no year column found (none ties to the R and E rows and none is "
                               f"headed 'Total budget of year').")

    # the twelve months: the run of columns to the right of the value column whose header (the form's rows
    # 8-14) is the first day of a month or a 'mm/yyyy' text; the Starting / Ending Month cells of rows 5-6 are
    # not headers
    month_cols, period = [], []

    def month_header(c):
        for r in range(7, 14):
            v = get(r, c)
            if isinstance(v, (datetime.datetime, datetime.date)) and v.day != 1:
                continue
            ym = _as_month(v)
            if ym:
                return ym
        return None

    for c in range(value_col + 1, min(ncols, value_col + 40)):
        ym = month_header(c)
        if ym:
            month_cols.append(c)
            period.append(ym)
        elif month_cols:
            break
        if len(month_cols) == 12:
            break
    if len(month_cols) != 12:
        flags.append(f'tìm thấy {len(month_cols)} cột tháng thay vì 12')

    # remarks column
    rem_col = None
    for c in range(cc + 2, ncols):
        h = header(c)
        if re.search(r'remarks\s*\n?\s*ghi chú', h) or h.strip().startswith('remarks'):
            rem_col = c
    # VAT basis: the sheet's title rows and the F7 switch
    basis = None
    for r in range(0, 8):
        for c in range(0, min(40, ncols)):
            v = get(r, c)
            if isinstance(v, str) and vat_of(v):
                basis = vat_of(v)
                break
        if basis:
            break
    if basis is None:
        switch = ' '.join(str(get(6, 5) or '').split()).upper()
        basis = 'excl' if switch == 'KHOÁN' else ('incl' if switch else 'unknown')
    if basis == 'unknown':
        flags.append('không đọc được cơ sở VAT của sheet')

    # lines
    sums, _, vals, gone, aggs = col_sums(value_col)
    value_tie = tie(value_col, vals, gone, aggs)
    seen = {}
    lines = []
    for i, lf in enumerate(leaves):
        if lf.get('cond_rows') is not None and vals[i] is None:
            continue
        if i in gone:
            continue
        r, code = lf['row'], lf['code']
        annual = vals[i] if vals[i] is not None else 0.0
        months = [_num(get(r, c)) or 0.0 for c in month_cols]
        lflags = []
        if month_cols and len(month_cols) == 12 and abs(sum(months) - annual) > TOL:
            lflags.append(FLAG_MONTHS)
        item = ' '.join(str(get(r, cc + 1) or '').split())
        remark = ' '.join(str(get(r, rem_col) or '').split()) if rem_col is not None else ''
        lines.append(PriorLine(fund, sheet_name, r + 1, lf['section'], code, item, annual, months, remark, lflags))
        seen[code] = seen.get(code, 0) + 1
    for l in lines:
        if seen[l.code] > 1:
            l.flags.append(FLAG_DUP)
    anchors = {s: _num(get(anchor_rows[s], value_col)) for s in SECTIONS_COMPARED}
    return FundRead(fund, sheet_name, lines, anchors, value_col + 1, value_how, [c + 1 for c in month_cols], period,
                    basis, flags, value_tie['state'], value_tie['notes'])


def _project_name(ws_rows, info_name):
    for r in range(0, 8):
        for c, v in enumerate(ws_rows[r] if r < len(ws_rows) else ()):
            if isinstance(v, str) and re.search(r'project name|tên dự án', v, re.I):
                nxt = next((str(x).strip() for x in ws_rows[r][c + 1:c + 12] if isinstance(x, (str, int, float)) and str(x).strip()), '')
                if nxt and nxt.upper() != 'AAA':
                    return _nfc(nxt)
    return info_name


def template_codes(path=TEMPLATE_PATH):
    """{fund: {code: template row}} of the 2027 template's two fund sheets (code column Y). Cached."""
    cache = template_codes.__dict__.setdefault('_cache', {})
    if path in cache:
        return cache[path]
    wb = openpyxl.load_workbook(path, read_only=True)
    out = {}
    for fund, sheet in FUND_SHEETS.items():
        ws = wb[sheet]
        codes = {}
        for i, row in enumerate(ws.iter_rows(min_row=1, max_row=700, min_col=25, max_col=25, values_only=True), start=1):
            v = row[0]
            if isinstance(v, str) and v.strip():
                codes.setdefault(v.strip(), i)
        out[fund] = codes
    wb.close()
    cache[path] = out
    return out


def catalogue_methods(path=CATALOGUE_PATH):
    """{code: (method, item_vi)} from the costing catalogue."""
    with open(path, encoding='utf-8-sig') as f:
        body = ''.join(l for l in f if not l.startswith('#'))
    return {r['code'].strip(): (r.get('method', '').strip(), r.get('item_vi', '').strip())
            for r in csv.DictReader(io.StringIO(body)) if r.get('code', '').strip()}


def read_prior_budget(path, workdir=None, template=TEMPLATE_PATH):
    """The approved budget workbook -> PriorBudget (design D1, D2, D4). Raises PriorBudgetError."""
    wb, opened = open_workbook(path, workdir)
    wbf = None
    try:
        chosen = choose_fund_sheets(wb.sheetnames, {ws.title: ws.sheet_state for ws in wb.worksheets})
        notes = []
        if opened != path:
            notes.append((NOTE_SOURCE, os.path.basename(path), f'đọc qua bản sao đã bỏ defined names: {os.path.basename(opened)}'))
        # formulas and hidden rows of the same file (the stripped copy when that is what opened)
        try:
            wbf = openpyxl.load_workbook(opened, read_only=True)
            layouts = br.sheet_layout(opened, {n for n in chosen.values() if n})
        except Exception as exc:
            wbf, layouts = None, {}
            notes.append((NOTE_SOURCE, os.path.basename(path), f'không đọc được công thức ({type(exc).__name__}): '
                                                                f'dòng gộp chỉ nhận theo tiền tố mã'))
        funds = {}
        tcodes = template_codes(template)
        for fund in FUNDS:
            name = chosen.get(fund)
            if not name:
                notes.append((NOTE_UNREAD, FUND_SHEETS[fund], 'file không có sheet này'))
                continue
            try:
                fr = read_fund_sheet(wb[name], fund, name, wbf[name] if wbf is not None else None, layouts.get(name))
            except PriorBudgetError as exc:
                if fund == 'MF':
                    raise PriorBudgetError(f'{os.path.basename(path)}: {exc}') from None
                notes.append((NOTE_UNREAD, name, str(exc)))
                continue
            for fl in fr.flags:
                notes.append((NOTE_UNREAD, name, fl))
            for l in fr.lines:
                code = CODE_ALIASES.get(l.code, l.code)
                if code != l.code:
                    l.flags.append(f'mã {l.code} ánh xạ sang {code}')
                    l.code = code
                if l.code not in tcodes[fund]:
                    l.on_form = False
                    l.flags.append(FLAG_NOT_ON_FORM)
                    notes.append((NOTE_NOT_ON_FORM, l.code, f"{name} dòng {l.row}: {l.item[:60]} = {l.annual:,.0f}"))
            if fr.ties:
                for n in fr.tie_notes:                                   # a tie after explanation says why
                    notes.append((NOTE_SOURCE, name, n))
            else:
                for s in SECTIONS_COMPARED:
                    a = fr.anchors.get(s)
                    if a is None or abs(fr.section_total(s) - a) > TOL:
                        notes.append((NOTE_UNREAD, f'{name} {s}',
                                      f'tổng dòng lá {fr.section_total(s):,.0f} khác dòng {s} của sheet {a if a is None else format(a, ",.0f")}'))
            funds[fund] = fr
        mf = funds['MF']
        info_name = ''
        try:
            info_name = read_info(wb).name
        except Exception:
            pass
        project_name = _project_name(_rows_of(wb[chosen['MF']])[:8], info_name)
        years = [y for y, _ in mf.period]
        budget_year = max(set(years), key=lambda y: (years.count(y), y)) if years else None
        if budget_year is None:
            raise PriorBudgetError(f"{os.path.basename(path)}: no month columns on '{mf.sheet}', so the budget year is unknown.")
        return PriorBudget(path, project_name, funds, notes, budget_year, list(mf.period))
    finally:
        wb.close()
        if wbf is not None:
            wbf.close()


# ------------------------------------------------------------------------------------------------
# The project's scale from '0. Info'
# ------------------------------------------------------------------------------------------------
def _info_sheet(wb):
    for n in wb.sheetnames:
        k = _key(n)
        if any(k.startswith(p) for p in INFO_SHEET_PREFIXES):
            return n
    return None


def _product_of(text):
    k = _key(text)
    if not k:
        return None
    for product, aliases in PRODUCT_ALIASES.items():
        if k in aliases:
            return product
    for product, aliases in PRODUCT_ALIASES.items():
        for a in aliases:
            if k.startswith(a) and (len(k) == len(a) or not k[len(a)].isalpha()):
                return product
    return None


def read_info(wb):
    """The scale facts the Info sheet carries (design D7). Everything not found is a note, never a guess."""
    out = ProjectInfo()
    name = _info_sheet(wb)
    if not name:
        out.notes.append((NOTE_UNREAD, '0. Info', 'file không có sheet Info'))
        return out
    out.sheet = name
    rows = _rows_of(wb[name])
    for r in range(0, min(4, len(rows))):
        for v in rows[r]:
            if isinstance(v, str) and re.search(r'information of|thông tin dự án', v, re.I):
                nm = re.sub(r'(?i)^.*?(information of|thông tin dự án)\s*', '', _nfc(v)).strip()
                if nm and not out.name:
                    out.name = nm
    hdr = next((r for r in range(0, min(20, len(rows)))
                if any(isinstance(v, str) and re.search(r'\bNFA\b|NSA|diện tích thu phí', v, re.I) for v in rows[r])), None)
    if hdr is None:
        out.notes.append((NOTE_UNREAD, name, 'không thấy dòng tiêu đề có NFA'))
        return out
    cols = {}
    for c, v in enumerate(rows[hdr]):
        if not isinstance(v, str):
            continue
        k = _key(v)
        if 'nfa' in k or 'nsa' in k or 'thu phí' in k:
            cols.setdefault('nfa', c)
        elif 'gfa' in k or 'sàn xây dựng' in k:
            cols.setdefault('gfa', c)
        elif 'số sản phẩm' in k or 'units' in k or 'số căn' in k:
            cols.setdefault('units', c)
        elif 'số ô' in k or 'slot' in k or 'số chỗ' in k or 'bays' in k:
            cols.setdefault('bays', c)
        elif 'đơn giá' in k or 'rate' in k:
            cols.setdefault('rate', c)
    for r in range(hdr + 1, min(hdr + 60, len(rows))):
        first = next((v for v in rows[r][:3] if isinstance(v, str) and v.strip()), None)
        if first is None:
            continue
        k = _key(first)
        if k.startswith(('tổng cộng', 'total')):
            break
        cell = lambda key: _num(rows[r][cols[key]]) if key in cols and cols[key] < len(rows[r]) else None
        if re.search(r'gắn máy|xe máy|motor', k):
            if out.moto_bays is None and cell('bays') is not None:
                out.moto_bays = cell('bays')
            continue
        if re.search(r'ô tô|\bcar\b', k):
            if out.car_bays is None and cell('bays') is not None:
                out.car_bays = cell('bays')
            continue
        product = _product_of(first)
        if product and product not in out.products and (cell('nfa') or cell('units')):
            out.products[product] = dict(gfa=cell('gfa'), nfa=cell('nfa'), units=cell('units'), rate=cell('rate'), row=r + 1)
    if out.car_bays is not None:
        out.notes.append((NOTE_CHECK, 'Car Parking Slots', f"'Số ô' của dòng bãi xe ô tô trên {name} = {out.car_bays:g}; "
                          f'có thể là số bãi chứ không phải số chỗ'))
    if out.moto_bays is not None:
        out.notes.append((NOTE_CHECK, 'Moto Parking Slots', f"'Số ô' của dòng xe gắn máy trên {name} = {out.moto_bays:g}"))
    return out


# ------------------------------------------------------------------------------------------------
# Writing the form
# ------------------------------------------------------------------------------------------------
def _label_row(ws, label, required=True):
    want = normalise(label)
    for r in range(1, (ws.max_row or 1) + 1):
        if normalise(ws.cell(row=r, column=1).value) == want:
            return r
    if required:
        raise LabelNotFound(f"Project Info has no label {label!r}.")
    return None


def _put(ws, label, value, required=True):
    r = _label_row(ws, label, required)
    if r is not None:
        ws.cell(row=r, column=2).value = value
    return r


def fresh_form(out_path):
    """A blank form from the builder, written at `out_path` (the builder's live path is not touched)."""
    import build_project_input_form as bpf
    saved = (bpf.OUT, bpf.FINAL_OUT)
    try:
        bpf.OUT = os.path.join(os.path.dirname(out_path), '_tmp_' + os.path.basename(out_path))
        bpf.FINAL_OUT = out_path
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            bpf.main()
        if os.path.exists(bpf.OUT):
            os.remove(bpf.OUT)
    finally:
        bpf.OUT, bpf.FINAL_OUT = saved
    return out_path


def _dated_copy(src, out_dir, now=None):
    stamp = (now or datetime.datetime.now()).strftime('%Y%m%d_%H%M')
    stem, ext = os.path.splitext(os.path.basename(src))
    dst = os.path.join(out_dir, f'{stem}_REVIEW_{stamp}{ext}')
    shutil.copyfile(src, dst)
    return dst


def _ensure_existing_sheets(wb):
    import build_project_input_form as bpf
    if es.ROSTER_SHEET not in wb.sheetnames:
        pi = wb['Project Info']
        last = max((r for r in range(1, (pi.max_row or 1) + 1) if pi.cell(row=r, column=1).value not in (None, '')), default=1)
        bpf.add_existing_project_fields(pi, last + 2)
        bpf.add_prior_year_roster_sheet(wb)
    if eu.SHEET not in wb.sheetnames:
        bpf.add_prior_year_utilities_sheet(wb)


def _block_first_row(ws, title):
    for r in range(1, (ws.max_row or 1) + 1):
        if normalise(ws.cell(row=r, column=1).value) == normalise(title):
            return r + 2
    raise LabelNotFound(f"sheet {ws.title!r} has no block {title!r}")


def _header_cols(ws, header_row):
    return {normalise(ws.cell(row=header_row, column=c).value): c
            for c in range(1, (ws.max_column or 1) + 1) if ws.cell(row=header_row, column=c).value}


def add_prior_budget_sheet(wb, prior, notes):
    """The 'Prior-Year Budget' sheet (design D8), replacing an older one of the same name."""
    if SHEET in wb.sheetnames:
        del wb[SHEET]
    ws = wb.create_sheet(SHEET)
    ws['A1'] = (f"Last year's approved budget, read line by line from {os.path.basename(prior.path)} "
                f"(budget year {prior.budget_year}) — written by the automation, read by review.py only")
    ws['A1'].font = Font(bold=True, size=12)
    ws['A2'] = ('One row per leaf line of sections R and E of the two fund sheets, as read: the year column is the '
                'approved figure, the twelve months are shown beside it. The generators do not read this sheet.')
    ws['A2'].font = Font(italic=True, size=9, color='7F7F7F')
    r = 4
    ws.cell(row=r, column=1, value=SEC_LINES).font = Font(bold=True)
    headers = list(LINE_COLS.values())
    for i, (ym) in enumerate(prior.period[:12]):
        headers[list(LINE_COLS).index(MONTH_KEYS[i])] = f'Month {i + 1} ({ym[1]:02d}/{ym[0]})'
    for c, h in enumerate(headers, start=1):
        ws.cell(row=r + 1, column=c, value=h).font = Font(bold=True)
    r += 2
    for l in prior.lines():
        fr = prior.funds[l.fund]
        values = [l.sheet, l.section, l.code, l.item, l.annual, 'Yes' if fr.vat_basis == 'incl' else ('No' if fr.vat_basis == 'excl' else '')]
        values += [l.months[i] if i < len(l.months) else None for i in range(12)]
        values += [l.sheet, l.row, l.remark, '; '.join(l.flags)]
        for c, v in enumerate(values, start=1):
            cell = ws.cell(row=r, column=c, value=v)
            if isinstance(v, float):
                cell.number_format = '#,##0'
        r += 1
    r += 1
    ws.cell(row=r, column=1, value=SEC_NOTES).font = Font(bold=True)
    for c, h in enumerate(NOTE_COLS.values(), start=1):
        ws.cell(row=r + 1, column=c, value=h).font = Font(bold=True)
    r += 2
    for kind, where, text in notes:
        for c, v in enumerate((kind, where, text), start=1):
            ws.cell(row=r, column=c, value=v)
        r += 1
    ws.column_dimensions['D'].width = 48
    ws.column_dimensions['C'].width = 12
    ws.column_dimensions['E'].width = 18
    return ws


def write_form(prior, info, facts, out_dir, base_form=None, now=None, stamp=None):
    """A filled Existing-project form in `out_dir` (design D7, D8). Returns (path, notes, filled) where
    `filled` records what went onto the form: products with a rate, parking revenue entered, blanks."""
    os.makedirs(out_dir, exist_ok=True)
    facts = dict(facts or {})
    sources = facts.pop('_sources', {}) or {}
    if base_form:
        path = _dated_copy(base_form, out_dir, now)
    else:
        path = fresh_form(os.path.join(out_dir, 'Project_Budget_Input.xlsx'))
    wb = openpyxl.load_workbook(path)
    _ensure_existing_sheets(wb)
    pi = wb['Project Info']
    notes = list(prior.notes) + list(info.notes)
    filled = dict(rates={}, parking={}, blank=[], facts=[], mode_fields=[])
    mf = prior.funds['MF']
    budget_year = prior.budget_year + 1
    start_ym = (prior.period[0][0] + 1, prior.period[0][1]) if prior.period else (budget_year, 1)

    # Scale from the Info sheet
    if prior.project_name:
        _put(pi, 'Project Name', prior.project_name)
    for product, p in info.products.items():
        row = _label_row(pi, product, required=False)
        if row is None:
            notes.append((NOTE_UNREAD, product, 'form không có dòng sản phẩm này'))
            continue
        pi.cell(row=row, column=2).value = p.get('gfa') or 0
        pi.cell(row=row, column=3).value = p.get('nfa') or 0
        pi.cell(row=row, column=4).value = p.get('units') or 0
        notes.append((NOTE_INFO, product, f"NFA {p.get('nfa') or 0:,.2f} m², {p.get('units') or 0:g} căn ({info.sheet} dòng {p['row']})"))
    for label in ('Car Parking Slots', 'Moto Parking Slots'):
        v = info.car_bays if label.startswith('Car') else info.moto_bays
        _put(pi, label, v, required=False)

    # Fee rates and parking revenue from the file (user's choice 2026-10-20): the operating-project inputs
    rate_basis = oi.VAT_EXCL if mf.vat_basis == 'excl' else oi.VAT_INCL
    hdr_row = _label_row(pi, oi.PRODUCT_HEADER, required=False)
    if hdr_row:
        cols = _header_cols(pi, hdr_row)
        rc, vc = cols.get(normalise(oi.RATE_HEADER)), cols.get(normalise(oi.VAT_HEADER))
        for product, p in info.products.items():
            if rc and vc and p.get('rate') and p.get('nfa'):
                row = _label_row(pi, product, required=False)
                if row:
                    pi.cell(row=row, column=rc).value = p['rate']
                    pi.cell(row=row, column=vc).value = rate_basis
                    filled['rates'][product] = (p['rate'], rate_basis)
                    notes.append((NOTE_INFO, PRODUCT_CODES[product], f"đơn giá {p['rate']:,.0f} VND/m²/tháng ({rate_basis}, theo cơ sở của sheet quỹ)"))
    else:
        notes.append((NOTE_UNREAD, oi.RATE_HEADER, 'form không có cột đơn giá thật; phí quản lý sẽ được ước lượng'))
    _put(pi, oi.STABLE_LABEL, 'Yes', required=False)
    by_code = {}
    for l in mf.lines:
        by_code[l.code] = by_code.get(l.code, 0.0) + l.annual
    for code, label, key in (('RP2', oi.PARKING_CAR_LABEL, 'car'), ('RP1', oi.PARKING_MOTO_LABEL, 'moto')):
        if code in by_code and _label_row(pi, label, required=False):
            monthly = round(by_code[code] / 12.0)
            _put(pi, label, monthly)
            filled['parking'][key] = monthly
            notes.append((NOTE_INFO, code, f'doanh thu xe {monthly:,.0f} VND/tháng = số duyệt {by_code[code]:,.0f} ÷ 12'))

    # Collect-on-behalf water and electricity from the approved RO3.<x> / RO4.<x> lines (same user choice: known
    # revenue comes from the file). Row 'Thu hộ chi hộ: <product>', water in column 2, electricity in column 3.
    filled['cob'] = {}
    suffix_product = {v: k for k, v in oi.COB_SUFFIX.items()}
    for prefix, col, utility in ((oi.COB_REVENUE_PREFIX['water'], 2, 'water'), (oi.COB_REVENUE_PREFIX['electricity'], 3, 'electricity')):
        for code, annual in by_code.items():
            if not code.startswith(prefix + '.') or abs(annual) < 0.5:
                continue
            product = suffix_product.get(code[len(prefix) + 1:])
            row = _label_row(pi, oi.COB_ROW_PREFIX + product, required=False) if product else None
            if row is None:
                notes.append((NOTE_UNREAD, code, f'thu hộ chi hộ {annual:,.0f} VND/năm: form không có dòng cho mã này'))
                continue
            monthly = round(annual / 12.0)
            pi.cell(row=row, column=col).value = monthly
            filled['cob'][code] = monthly
            notes.append((NOTE_INFO, code, f'thu hộ chi hộ {utility} {product}: {monthly:,.0f} VND/tháng = số duyệt {annual:,.0f} ÷ 12'))

    # Existing-project mode
    _put(pi, es.MODE_LABEL, es.MODE_EXISTING)
    _put(pi, es.PRIOR_YEAR_LABEL, prior.budget_year)
    _put(pi, 'Budget Start Month', datetime.datetime(start_ym[0], start_ym[1], 1), required=False)
    _put(pi, 'Operating Years to Budget', 1, required=False)
    filled['mode_fields'] = [es.MODE_EXISTING, prior.budget_year, f'{start_ym[1]:02d}/{start_ym[0]}']

    # Fields the file does not carry: blank unless a fact is given
    for label in PM_SCALE_LABELS + (es.REGION_LABEL,):
        row = _label_row(pi, label, required=False)
        if row is None:
            continue
        if label in facts:
            pi.cell(row=row, column=2).value = facts[label]
            filled['facts'].append(label)
            notes.append((NOTE_FACT, label, f'{facts[label]!r}: {sources.get(label, "file dữ kiện")}'))
        else:
            # A numeric field gets 0, which the tool reads as "not given" (the M3 runs entered 0 for the same facts);
            # a blank would stop the generator with a bare TypeError. Text fields stay blank.
            numeric = label in NUMERIC_SCALE_LABELS
            pi.cell(row=row, column=2).value = 0 if numeric else None
            filled['blank'].append(label)
            notes.append((NOTE_BLANK, label, 'file ngân sách không có dữ kiện này' + (' (ghi 0)' if numeric else '')))
    for label, value in facts.items():
        if label in PM_SCALE_LABELS or label == es.REGION_LABEL:
            continue
        row = _label_row(pi, label, required=False)
        if row is None:
            notes.append((NOTE_UNREAD, label, 'nhãn trong file dữ kiện không có trên form'))
            continue
        pi.cell(row=row, column=2).value = value
        filled['facts'].append(label)
        notes.append((NOTE_FACT, label, f'{value!r}: {sources.get(label, "file dữ kiện")}'))

    rs = wb['Roster Setup']
    for label, value in (('Month (1-12)', start_ym[1]), ('Year', start_ym[0])):
        for r in range(1, (rs.max_row or 1) + 1):
            if normalise(rs.cell(row=r, column=1).value) == normalise(label):
                rs.cell(row=r, column=2).value = value
                break

    # Staff lines and utility lines (the approved amounts of the Management Fund sheet)
    ws = wb[es.ROSTER_SHEET]
    first = _block_first_row(ws, es.SEC_LINES)
    for i, line in enumerate(es.STAFF_LINES):
        if ws.cell(row=first + i, column=1).value != line:
            raise LabelNotFound(f"'{es.ROSTER_SHEET}' block {es.SEC_LINES!r}: row {first + i} is not {line}")
        ws.cell(row=first + i, column=2).value = by_code.get(line, 0.0)
        notes.append((NOTE_INFO, line, f"số duyệt {by_code.get(line, 0.0):,.0f} VND/năm vào '{es.SEC_LINES}'"))
    uw = wb[eu.SHEET]
    first = _block_first_row(uw, eu.SEC_LINES)
    cols = _header_cols(uw, first - 1)
    ac, vc = cols[normalise(eu.LINE_COLS['approved'])], cols[normalise(eu.LINE_COLS['approved_incl_vat'])]
    for i, line in enumerate(eu.LINES):
        if uw.cell(row=first + i, column=1).value != line:
            raise LabelNotFound(f"'{eu.SHEET}' block {eu.SEC_LINES!r}: row {first + i} is not {line}")
        uw.cell(row=first + i, column=ac).value = by_code.get(line, 0.0)
        uw.cell(row=first + i, column=vc).value = 'Yes' if mf.vat_basis == 'incl' else 'No'
        notes.append((NOTE_INFO, line, f"số duyệt {by_code.get(line, 0.0):,.0f} VND/năm vào '{eu.SEC_LINES}' "
                      f"(gồm VAT: {'Yes' if mf.vat_basis == 'incl' else 'No'}); không có 12 tháng hoá đơn"))

    add_prior_budget_sheet(wb, prior, notes)
    wb.save(path)
    return path, notes, filled


# ------------------------------------------------------------------------------------------------
# Reading the sheet back
# ------------------------------------------------------------------------------------------------
def read_prior_budget_sheet(wb_values):
    """(lines, notes) from the 'Prior-Year Budget' sheet: lines as dicts keyed like LINE_COLS plus 'months'."""
    if SHEET not in wb_values.sheetnames:
        raise LabelNotFound(f"the workbook has no sheet {SHEET!r}.")
    ws = wb_values[SHEET]
    sections = es._section_rows(ws, (SEC_LINES, SEC_NOTES))
    cols = dict(LINE_COLS)
    lines = []
    for r in es._read_block(ws, SEC_LINES, sections, cols, required=('fund', 'section', 'code', 'approved')):
        months = [float(r[k]) if isinstance(r[k], (int, float)) else 0.0 for k in MONTH_KEYS]
        lines.append(dict(fund=r['fund'], section=str(r['section']).strip(), code=str(r['code']).strip(),
                          item=r['item'] or '', approved=float(r['approved'] or 0.0),
                          incl_vat=str(r['incl_vat'] or '').strip().casefold() == 'yes', months=months,
                          src_sheet=r['src_sheet'], src_row=r['src_row'], remark=r['remark'] or '',
                          flags=[f for f in str(r['flags'] or '').split('; ') if f], row=r['_row']))
    notes = [(r['kind'], r['where'], r['text']) for r in es._read_block(ws, SEC_NOTES, sections, NOTE_COLS)]
    return lines, notes


def load_facts(path):
    """A facts file: JSON {label: value, ..., "_sources": {label: text}}."""
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f'{path}: the facts file must be a JSON object of label -> value.')
    return data
