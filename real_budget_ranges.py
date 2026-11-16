"""
Real-budget ranges (change use-real-budget-ranges, design D1-D5, D8).

Prices the budget lines the tool has no other source for from what Savills projects actually budget. The build
step (`build_real_budget_ranges.py`) turns the scan store into one anonymous per-project file; this module forms the
range when the tool runs, so that the project being budgeted can be left out of its own range.

Data files read:
  Budget_Agent/data/real_budget_ranges/Ref_RealBudgetValues.csv   one row per anonymous project and code
  Budget_Agent/data/generation_B_verified/Ref_CPI_VN.csv          annual average CPI change, with sources

Range rules (approved 2026-10-12):
  1. leave out the project itself: same name_key, or input NFA within 0.5% of the entry's nfa_m2 (D2);
  2. leave out values outside P25 - 1.5 x IQR .. P75 + 1.5 x IQR, decided once on what is left (D3);
  3. use the range only when at least 10 projects remain;
  percentiles are inclusive linear interpolation, the same as Excel's PERCENTILE.INC.
The figure = median (VND per m2 per month, 2027 prices, excluding VAT) x fee-paying NFA x 12, plus the budget-year
VAT when the deliverable is on an inclusive basis (D5).

Without the values file every code falls back to 0 with its reason, and the tool still runs (rollback, design).
"""
import csv
import os
from dataclasses import dataclass, field

from service_levels import name_key  # the same key as the service-level table (design D2)

SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
BUDGET_AGENT = os.path.abspath(os.path.join(SOURCE_DIR, '..'))
DATA_DIR = os.path.join(BUDGET_AGENT, 'data', 'real_budget_ranges')
VALUES_CSV = os.path.join(DATA_DIR, 'Ref_RealBudgetValues.csv')
CPI_CSV = os.path.join(BUDGET_AGENT, 'data', 'generation_B_verified', 'Ref_CPI_VN.csv')

TARGET_YEAR = 2027
MIN_PROJECTS = 10
SELF_NFA_TOLERANCE = 0.005
IQR_K = 1.5
MONTHS = 12

# Codes in scope (docs/05-decisions.md, 2026-10-12)
PRICED_CODES = ('EMB4', 'ESS12', 'ESC5', 'ESS7', 'ESS23', 'ESC1', 'ESC2')
STAND_IN_CODES = ('ESC1', 'ESC2')          # stand-in for the guideline's count x price per event
CROSS_CHECK_CODES = ('ESI1', 'EMH1', 'EMH3')  # shown next to the tool's own figure, never priced from the range
# Rate codes (change price-fee-and-parking-from-portfolio, design D1/D4): the value is a unit rate per m2 of
# APARTMENT NFA, not an amount per m2 of fee-paying NFA. The range gives the rate; the revenue rows multiply it by
# the product's own area. RM.AP = (RM.AP + RM.0A, the developer's share on units not yet handed over) / apartment NFA.
RATE_CODES = ('RM.AP',)
ALL_CODES = PRICED_CODES + CROSS_CHECK_CODES + RATE_CODES
CODE_NAMES = {'EMB4': 'Operation audit', 'ESS12': 'Pest control', 'ESC5': 'Lunar New Year decoration',
              'ESS7': 'Façade cleaning', 'ESS23': 'Pool staff (outsourced)', 'ESC1': 'Events', 'ESC2': 'Fire drill',
              'ESI1': 'Asset insurance', 'EMH1': "Savills' management fee", 'EMH3': 'Night and holiday allowance',
              'RM.AP': 'Apartment management-fee rate (per m² of apartment NFA)'}
SHEET_NAME = 'Real-Budget Ranges'

BASIS_FEE_NFA = 'fee_nfa'              # value per m2 of fee-paying NFA (every cost code)
BASIS_APARTMENT_NFA = 'apartment_nfa'  # value per m2 of apartment NFA (RM.AP)
VALUE_COLUMNS = ['project_id', 'name_key', 'nfa_m2', 'budget_year', 'code', 'status', 'value_m2_month',
                 'cpi_factor', 'value_m2_month_2027', 'flag', 'basis']
STATUS_VALUE = 'value'
STATUS_ZERO = 'zero_or_blank'

# Why an entry is not among the values used (internal sheet wording)
OUT_SELF_NAME = 'chính dự án (trùng tên)'
OUT_SELF_NFA = 'chính dự án (NFA lệch không quá 0,5%)'
OUT_LOW = 'ngoại lai thấp (dưới P25 - 1,5 x IQR)'
OUT_HIGH = 'ngoại lai cao (trên P75 + 1,5 x IQR)'

# Client-facing reasons for a line left at 0 (Vietnamese, design Open Questions)
REASON_NO_DATA = 'Để 0: chưa có bảng giá từ ngân sách thực tế của các dự án do Savills quản lý.'
REASON_NO_NFA = 'Để 0: chưa có NFA thu phí của dự án để nhân với đơn giá trên m².'
REASON_NO_POOL = 'Để 0: dự án không có hồ bơi, nên không có chi phí nhân sự hồ bơi thuê ngoài.'
REASON_NO_TOWER = 'Để 0: dự án không có tòa tháp, nên không có chi phí vệ sinh mặt ngoài tòa nhà.'


def reason_inhouse_pool(n):
    """ESS23 when the roster already staffs the pool in-house (user's rule, 2026-10-19): no outsourced pool staff
    on top of it."""
    return (f'Để 0: dự án đã có {n:g} nhân viên hồ bơi do Ban quản lý tự tuyển trên trang A1. Staff Cost, '
            f'nên không tính thêm nhân sự vận hành hồ bơi thuê ngoài.')


REASON_LUMP_STAFF = ('Để 0: chi phí nhân sự của dự án là một khoản cả gói đã duyệt (EMH2), có thể đã gồm nhân viên '
                     'hồ bơi, nên không tính thêm nhân sự vận hành hồ bơi thuê ngoài.')


def reason_too_few(n):
    return (f'Để 0: chỉ {n} ngân sách thực tế của dự án do Savills quản lý có dòng này, '
            f'chưa đủ tối thiểu {MIN_PROJECTS} dự án để lập khoảng giá.')


STAND_IN_NOTE = {
    'ESC1': ('Số này tạm thay cho cách tính số sự kiện dự kiến × đơn giá mỗi sự kiện, '
             'cho đến khi có số sự kiện và đơn giá thực tế.'),
    'ESC2': ('Số này tạm thay cho cách tính số đợt diễn tập phòng cháy chữa cháy × chi phí mỗi đợt, '
             'cho đến khi có số đợt và chi phí thực tế.'),
}


@dataclass
class CpiYear:
    year: int
    rate: float          # fraction, 0.0452 for +4.52%
    status: str          # 'published' / 'stand-in'
    source: str


@dataclass
class RangeResult:
    code: str
    usable: bool = False
    reason: str = ''                 # Vietnamese, when not usable
    pm_fill: bool = False            # not usable for want of data (no values file, < 10 budgets, no NFA): the line is
                                     # left for the PM (change leave-unpriced-lines-for-pm); False = genuinely 0
    stand_in: bool = False
    cross_check: bool = False
    rate: bool = False               # a RATE_CODES result: median/p25/p75 are a unit rate, figure stays 0
    used: list = field(default_factory=list)       # [(project_id, value_2027)]
    left_out: list = field(default_factory=list)   # [(project_id, value_2027, why)]
    p25: float | None = None
    median: float | None = None
    p75: float | None = None
    n_value: int = 0                 # projects in the file with a value for the code
    n_zero: int = 0                  # projects in the file showing the code at 0 or blank
    nfa: float | None = None
    vat_rate: float | None = None
    vat_inclusive: bool = True
    budget_year: int = TARGET_YEAR
    figure_excl_vat: float = 0.0
    figure: float = 0.0              # written to the deliverable (0 when not usable)
    months: list = field(default_factory=list)     # the twelve month cells, when priced by month (month_values)
    remark: str = ''

    @property
    def n_used(self):
        return len(self.used)


# ---------------------------------------------------------------- loading

def _num(v):
    if v in (None, ''):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def load_cpi(path=None):
    """{year: CpiYear}. The CSV gives the change in percent."""
    out = {}
    with open(path or CPI_CSV, encoding='utf-8-sig', newline='') as fh:
        for r in csv.DictReader(fh):
            y = int(r['year'])
            out[y] = CpiYear(y, float(r['avg_cpi_change_pct']) / 100.0, (r.get('status') or '').strip(),
                             (r.get('source') or '').strip())
    return out


def cpi_factor(year, cpi, target=TARGET_YEAR):
    """Factor that brings a value from budget year `year` to `target` prices (design D4): the product of
    (1 + rate) over the years year+1 .. target; for a later year, divided by the rates of target+1 .. year.
    Raises KeyError when a needed year has no rate."""
    year = int(year)
    f = 1.0
    if year < target:
        for y in range(year + 1, target + 1):
            f *= 1.0 + cpi[y].rate
    elif year > target:
        for y in range(target + 1, year + 1):
            f /= 1.0 + cpi[y].rate
    return f


def load_values(path=None):
    """Rows of the values file, typed; None when the file does not exist (rollback: lines stay at 0)."""
    path = path or VALUES_CSV
    if not os.path.exists(path):
        return None
    rows = []
    with open(path, encoding='utf-8-sig', newline='') as fh:
        for r in csv.DictReader(fh):
            rows.append({
                'project_id': r['project_id'], 'name_key': (r.get('name_key') or '').strip(),
                'nfa_m2': _num(r.get('nfa_m2')), 'budget_year': int(float(r['budget_year'])) if r.get('budget_year') else None,
                'code': r['code'].strip(), 'status': r['status'].strip(),
                'value_m2_month': _num(r.get('value_m2_month')), 'cpi_factor': _num(r.get('cpi_factor')),
                'value_m2_month_2027': _num(r.get('value_m2_month_2027')), 'flag': r.get('flag') or '',
                # a file written before the rate codes has no basis column: every value is per fee-paying NFA
                'basis': (r.get('basis') or BASIS_FEE_NFA).strip(),
            })
    return rows


# ---------------------------------------------------------------- statistics

def percentile_inc(values, p):
    """Excel PERCENTILE.INC: linear interpolation between closest ranks, rank = (n - 1) x p."""
    v = sorted(values)
    if not v:
        return None
    h = (len(v) - 1) * p
    lo = int(h)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (h - lo)


def self_keys(name):
    """The name keys the project being budgeted may carry in the values file: its name as entered, and its name
    without a trailing parenthesis, so that "PROJECT X (REBUILT AS NEW PROSPECT)" matches "PROJECT X"
    (user's rule, 2026-10-19)."""
    if not name:
        return set()
    text = str(name).strip()
    keys = {name_key(text)}
    while text.endswith(')') and '(' in text:
        text = text[:text.rfind('(')].strip()
        keys.add(name_key(text))
    return {k for k in keys if k}


def is_self(row, self_key, self_nfa):
    """The reason an entry is the project being budgeted, or '' (design D2). `self_key` is one key or a set of
    keys (self_keys)."""
    keys = self_key if isinstance(self_key, (set, frozenset)) else {self_key}
    if row['name_key'] and row['name_key'] in keys:
        return OUT_SELF_NAME
    if self_nfa and row['nfa_m2'] and abs(self_nfa - row['nfa_m2']) <= SELF_NFA_TOLERANCE * row['nfa_m2']:
        return OUT_SELF_NFA
    return ''


def form_range(code, rows, self_name=None, self_nfa=None):
    """Leave-one-out, then IQR outliers once. Returns (used, left_out, p25, median, p75, n_value, n_zero);
    values are VND per m2 per month at 2027 prices, excluding VAT."""
    self_key = self_keys(self_name)
    entries = [r for r in rows if r['code'] == code]
    n_value = sum(1 for r in entries if r['status'] == STATUS_VALUE)
    n_zero = sum(1 for r in entries if r['status'] == STATUS_ZERO)
    left_out, cands = [], []
    for r in entries:
        if r['status'] != STATUS_VALUE or r['value_m2_month_2027'] is None:
            continue
        why = is_self(r, self_key, self_nfa)
        if why:
            left_out.append((r['project_id'], r['value_m2_month_2027'], why))
        else:
            cands.append((r['project_id'], r['value_m2_month_2027']))
    used = cands
    if cands:
        vals = [v for _, v in cands]
        q1, q3 = percentile_inc(vals, 0.25), percentile_inc(vals, 0.75)
        lo, hi = q1 - IQR_K * (q3 - q1), q3 + IQR_K * (q3 - q1)
        used = []
        for pid, v in cands:
            if v < lo:
                left_out.append((pid, v, OUT_LOW))
            elif v > hi:
                left_out.append((pid, v, OUT_HIGH))
            else:
                used.append((pid, v))
    vals = [v for _, v in used]
    return (sorted(used), sorted(left_out), percentile_inc(vals, 0.25), percentile_inc(vals, 0.5),
            percentile_inc(vals, 0.75), n_value, n_zero)


# ---------------------------------------------------------------- figure and remark

def _pct(rate):
    return f'{rate * 100:g}%'.replace('.', ',')


def remark_priced(res, vat_clause=None, total=None):
    """Client remark for a line priced from the range (spec deliverable-remarks). `vat_clause` replaces the
    single-rate VAT wording when the caller adds VAT month by month at the dated rates; `total` is the annual
    figure written, stated at the end."""
    text = (f'Ước tính từ ngân sách thực tế của {res.n_used} dự án do Savills quản lý: trung vị '
            f'{res.median:,.1f} đ/m²/tháng (chưa VAT, theo giá năm {TARGET_YEAR}; khoảng giữa P25–P75: '
            f'{res.p25:,.1f}–{res.p75:,.1f} đ/m²/tháng) × {res.nfa:,.0f} m² NFA thu phí × {MONTHS} tháng')
    if vat_clause:
        text += f', {vat_clause}'
    elif res.vat_inclusive:
        text += f', cộng VAT {_pct(res.vat_rate)} năm {res.budget_year}'
    else:
        text += ', chưa cộng VAT'
    text += f' = {total:,.0f} VND/năm.' if total is not None else '.'
    if res.code in STAND_IN_NOTE:
        text += ' ' + STAND_IN_NOTE[res.code]
    return text


def applied_rate(res, vat_pct, vat_inclusive=True):
    """The rate the revenue rows apply (VND per m2 per month, rounded to the VND): the median brought onto the
    deliverable's VAT basis at the budget period's first month, the same conversion an excl.-VAT comparable rate
    gets (design D3, D7). None when the range is not usable."""
    if not (res.usable and res.rate and res.median is not None):
        return None
    return round(res.median * (1 + vat_pct / 100.0)) if vat_inclusive else round(res.median)


def rate_remark_vi(res, applied, vat_pct, vat_inclusive=True):
    """The source clause of the RM.AP remark when the rate comes from the range (spec deliverable-remarks): N
    projects, median, P25-P75, excl. VAT at 2027 prices, and the applied rate on the deliverable's basis. Names no
    project (decision D3)."""
    text = (f'Nguồn đơn giá: trung vị đơn giá phí quản lý căn hộ thực tế của {res.n_used} dự án do Savills quản lý, '
            f'{res.median:,.0f} đ/m²/tháng (chưa VAT, theo giá năm {TARGET_YEAR}; khoảng giữa P25–P75: '
            f'{res.p25:,.0f}–{res.p75:,.0f} đ/m²/tháng)')
    if vat_inclusive:
        text += f', cộng VAT {_pct(vat_pct / 100.0)} = {applied:,.0f} đ/m²/tháng đã gồm VAT.'
    else:
        text += f' = {applied:,.0f} đ/m²/tháng, chưa cộng VAT theo mô hình tài chính đã chọn.'
    return text


def price_line(code, rows, *, nfa, vat_rate, vat_inclusive=True, budget_year=TARGET_YEAR, self_name=None,
               self_nfa=None, has_pool=None, tower_count=None, inhouse_pool_staff=0, staff_lump=False,
               vat_factors=None, vat_clause=None):
    """One RangeResult for `code`. `rows` is load_values(); None means no values file. `self_nfa` defaults to
    `nfa` (the input's total fee-paying NFA). A cross-check code gets its range and figure but is never usable
    for pricing; the caller shows it next to the tool's own figure.
    `vat_factors`: twelve (1 + that month's VAT) factors, each month's twelfth taken at its own rate and rounded
    as the deliverable writes it (VAT by month, group 2 of apply-head-of-pm-decisions-2026-10); without them the
    single `vat_rate` applies. `vat_clause` is the remark's VAT wording for that case.
    `staff_lump`: the staff cost is one approved lump (Existing mode without a roster), so ESS23 stays at 0."""
    res = RangeResult(code=code, stand_in=code in STAND_IN_CODES, cross_check=code in CROSS_CHECK_CODES,
                      rate=code in RATE_CODES, nfa=nfa, vat_rate=vat_rate, vat_inclusive=vat_inclusive,
                      budget_year=budget_year)
    if rows is None:
        res.reason, res.pm_fill = REASON_NO_DATA, True
        return res
    (res.used, res.left_out, res.p25, res.median, res.p75,
     res.n_value, res.n_zero) = form_range(code, rows, self_name, nfa if self_nfa is None else self_nfa)
    if res.rate:
        # A unit rate (design D4): usable by the floor alone; the caller applies it to the product's own area and
        # converts the VAT basis itself, so no figure is formed here.
        if res.n_used < MIN_PROJECTS:
            res.reason, res.pm_fill = reason_too_few(res.n_used), True
        else:
            res.usable = True
        return res
    if code == 'ESS23' and has_pool is not True:
        res.reason = REASON_NO_POOL
        return res
    if code == 'ESS23' and staff_lump:
        res.reason = REASON_LUMP_STAFF
        return res
    if code == 'ESS23' and inhouse_pool_staff and inhouse_pool_staff > 0:
        res.reason = reason_inhouse_pool(inhouse_pool_staff)
        return res
    if code == 'ESS7' and not (tower_count and tower_count >= 1):
        res.reason = REASON_NO_TOWER
        return res
    if res.n_used < MIN_PROJECTS:
        res.reason, res.pm_fill = reason_too_few(res.n_used), True
        return res
    if not nfa or nfa <= 0:
        res.reason, res.pm_fill = REASON_NO_NFA, True
        return res
    res.figure_excl_vat = res.median * nfa * MONTHS
    if vat_factors is not None:
        res.months = month_values(res.figure_excl_vat, vat_factors if vat_inclusive else [1.0] * MONTHS)
        gross = sum(res.months)
    else:
        gross = res.figure_excl_vat * (1.0 + vat_rate) if vat_inclusive else res.figure_excl_vat
    if res.cross_check:
        res.figure = round(gross)      # for comparison only; never written to the deliverable
        return res
    res.usable = True
    res.figure = round(gross)
    res.remark = remark_priced(res, vat_clause, res.figure if vat_factors is not None else None)
    return res


def month_values(annual_excl, vat_factors):
    """The twelve month cells the deliverable carries for an annual amount excluding VAT: one rounded value
    repeated when every month has the same factor (an even Monthly row), else each month's own rounded value
    (a Schedule row). Their sum is the line's annual figure."""
    if len(set(vat_factors)) == 1:
        return [round(annual_excl * vat_factors[0] / MONTHS)] * MONTHS
    return [round(annual_excl / MONTHS * f) for f in vat_factors]


SF_VALUES_CSV = os.path.join(DATA_DIR, 'Ref_SinkingFundValues.csv')
BASIS_LIFT = 'lift'                    # value per lift per month (SF_LIFT_CODES)
SF_LIFT_CODES = ('ERLM1', 'ERLM2', 'ERLM3', 'ERLM4', 'ESA1')
SF_VALUE_COLUMNS = ['project_id', 'name_key', 'nfa_m2', 'budget_year', 'code', 'basis', 'value_unit_month',
                    'cpi_factor', 'value_unit_month_2027', 'flag']
# Sinking-fund lines still costed during the warranty (user, 2026-11-12; design D3): the maintenance contracts (40
# codes), the safety inspections ESA1-21, periodic cleaning ERCS1-5, outsourced sewage plant ERS1, bank fees EMB1,
# miscellaneous ERM (priced on sheet 2 today) and irrigation / plumbing ERPS4-5. A closed list, checked against the
# template's sheet 3 codes at start-up (generate_project_budget).
SF_WARRANTY_CODES = frozenset(
    ['ERE1', 'ERG1', 'ERT1', 'ERB1', 'ERLM1', 'ERLM1#', 'ERLM1##', 'ERA1', 'ERCL1', 'ERCL#1', 'ERCL##1', 'ERVR1', 'ERV1',
     'ERPS1', 'ERC1', 'ERAC1', 'ERP1', 'ERPL1', 'ERFS1', 'ERD1', 'ERL1', 'ERCC1', 'ERPA1', 'ERO1', 'ERSP1', 'ERAM1',
     'ERGS1', 'ERSM1', 'ERMF1'] + [f'ERF{i}.1' for i in range(1, 12)]
    + [f'ESA{i}' for i in range(1, 22)]
    + [f'ERCS{i}' for i in range(1, 6)]
    + ['ERS1', 'EMB1', 'ERM', 'ERPS4', 'ERPS5'])
SF_STATUS_PRICED = 'priced'
SF_STATUS_PM = 'pm_fill'
SF_STATUS_WARRANTY = 'warranty_zero'
SF_STATUS_OTHER_FUND = 'other_fund'
SF_STATUS_CARRY = 'carry_forward'
SF_OTHER_FUND_PRICED = 'đang tính ở quỹ quản lý'
SF_OTHER_FUND_PM = 'để PM điền ở quỹ quản lý'
SF_REASON_TOO_FEW = f'dưới {MIN_PROJECTS} dự án tham chiếu'
SF_REASON_NO_LIFTS = 'chưa có số thang máy'
SF_REASON_NO_NFA = 'chưa có NFA thu phí'
SF_REASON_NO_DATA = 'chưa có bảng số liệu quỹ bảo trì thực tế'
DEFAULT_WARRANTY_MONTHS = 24
MAX_WARRANTY_MONTHS = 60
WARRANTY_LABEL = 'Remaining Warranty Months'               # Project Info labels (task 3.1), read by label
TOTAL_LIFTS_LABEL = 'Total Elevators (incl. service)'


def warranty_months_of(value):
    """The input's remaining warranty months: blank -> 24; a whole number 0-60; anything else stops the run."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return DEFAULT_WARRANTY_MONTHS
    try:
        n = float(str(value).replace(',', '').strip())
    except ValueError:
        n = None
    if n is None or n != int(n) or not 0 <= n <= MAX_WARRANTY_MONTHS:
        raise ValueError(f"Project Info '{WARRANTY_LABEL}' is {value!r}: enter a whole number of months from 0 to "
                         f"{MAX_WARRANTY_MONTHS}, or leave it blank for {DEFAULT_WARRANTY_MONTHS}.")
    return int(n)


@dataclass
class SfResult:
    code: str
    status: str = SF_STATUS_PM
    basis: str = BASIS_FEE_NFA
    months: list = field(default_factory=lambda: [0] * MONTHS)   # the twelve month cells, on the deliverable's basis
    figure_excl_vat: float = 0.0
    n: int = 0
    median: float | None = None
    p25: float | None = None
    p75: float | None = None
    driver: float | None = None      # m2 NFA or lifts
    reason: str = ''                 # pm_fill: why; other_fund: which remark
    remark: str = ''
    warranty_months: int = 0         # months of the budget year inside the warranty (non-warranty codes only)
    prior: float | None = None       # carry_forward: the base, per year excluding VAT
    prior_year: int | None = None
    prior_source: str = ''

    @property
    def figure(self):
        return sum(self.months)

    @property
    def even(self):
        return len(set(self.months)) == 1


def load_sf_values(path=None):
    """Rows of the sinking-fund values file, typed; None when the file does not exist (every line left for the PM)."""
    path = path or SF_VALUES_CSV
    if not os.path.exists(path):
        return None
    rows = []
    with open(path, encoding='utf-8-sig', newline='') as fh:
        for r in csv.DictReader(fh):
            rows.append({'project_id': r['project_id'], 'name_key': (r.get('name_key') or '').strip(),
                         'nfa_m2': _num(r.get('nfa_m2')), 'budget_year': int(float(r['budget_year'])),
                         'code': r['code'].strip(), 'basis': (r.get('basis') or BASIS_FEE_NFA).strip(),
                         'value_unit_month_2027': _num(r.get('value_unit_month_2027')), 'flag': r.get('flag') or ''})
    return rows


def sf_reference(code, rows, self_name=None, self_nfa=None):
    """(values, n_left_out): the code's per-unit values at 2027 prices, plain (no IQR trim; the rule approved
    2026-11-12), leaving out the project itself by name key or NFA within 0.5% when `self_name` is given (Review)."""
    keys = self_keys(self_name) if self_name else set()
    vals, out = [], 0
    for r in rows or ():
        if r['code'] != code or r['value_unit_month_2027'] is None:
            continue
        if self_name and is_self({'name_key': r['name_key'], 'nfa_m2': r['nfa_m2']}, keys, self_nfa):
            out += 1
            continue
        vals.append(r['value_unit_month_2027'])
    return vals, out


def _sf_months(monthly_excl, n_zero, vat_factors):
    """Twelve month cells: the first `n_zero` months 0 (warranty), the rest the monthly amount on the deliverable's
    basis, each rounded."""
    return [0 if i < n_zero else round(monthly_excl * f) for i, f in enumerate(vat_factors)]


def _sf_unit(basis):
    return 'đ/thang máy/tháng' if basis == BASIS_LIFT else 'đ/m²/tháng'


def _sf_driver_text(res):
    if res.basis == BASIS_LIFT:
        return f'{res.driver:g} thang máy (gồm thang dịch vụ)'
    return f'{res.driver:,.0f} m² NFA thu phí'


def price_sf(codes, rows, *, nfa, lifts, warranty_months=DEFAULT_WARRANTY_MONTHS, vat_factors=None,
             vat_clause=None, budget_year=TARGET_YEAR, self_name=None, self_nfa=None, prior=None, cpi=None,
             excluded=None):
    """{code: SfResult} for the template's sheet 3 codes (design D2-D5).

    `rows` = load_sf_values() (None: no file). `vat_factors` = the twelve (1 + VAT) factors of the deliverable's basis
    (all 1.0 on the KHOÁN model), `vat_clause` its remark wording. `prior` (Review) = {code: (amount per year excluding
    VAT, year, source note)}; the warranty does not apply then. `excluded` = {code: SF_OTHER_FUND_PRICED or
    SF_OTHER_FUND_PM} for the codes sheet 2 holds (design D5). `self_name` / `self_nfa` leave the project out of its own
    reference (Review only)."""
    factors = list(vat_factors or [1.0] * MONTHS)
    excluded = excluded or {}
    review = prior is not None
    w = 0 if review else max(0, min(int(warranty_months or 0), MONTHS))
    out = {}
    for code in codes:
        res = SfResult(code=code, basis=BASIS_LIFT if code in SF_LIFT_CODES else BASIS_FEE_NFA)
        out[code] = res
        if code in excluded:
            res.status, res.reason = SF_STATUS_OTHER_FUND, excluded[code]
            res.remark = f'Để 0: {excluded[code]}.'
            continue
        if review and code in prior:
            amount, year, source = prior[code]
            factor = cpi_factor(year, cpi, target=budget_year) if cpi else 1.0
            res.status, res.prior, res.prior_year, res.prior_source = SF_STATUS_CARRY, amount, int(year), source
            res.figure_excl_vat = amount * factor
            res.months = _sf_months(res.figure_excl_vat / MONTHS, 0, factors)
            res.remark = (f'Theo số duyệt năm {int(year)} × CPI: {amount:,.0f} VND/năm (chưa VAT; {source}) × '
                          f'{factor:.4f} (CPI {int(year)}→{budget_year})'
                          + (f', {vat_clause}' if vat_clause else '') + f' = {res.figure:,.0f} VND/năm.')
            continue
        if rows is None:
            res.reason = SF_REASON_NO_DATA
            continue
        vals, _ = sf_reference(code, rows, self_name, self_nfa)
        res.n = len(vals)
        if vals:
            res.p25, res.median, res.p75 = (percentile_inc(vals, 0.25), percentile_inc(vals, 0.5),
                                            percentile_inc(vals, 0.75))
        res.driver = (lifts if lifts and lifts > 0 else None) if res.basis == BASIS_LIFT else (nfa if nfa and nfa > 0 else None)
        if w >= MONTHS and code not in SF_WARRANTY_CODES:
            # the whole year is inside the warranty: 0 whatever the reference holds; not a PM line (spec)
            res.status, res.warranty_months = SF_STATUS_WARRANTY, w
            res.remark = f'Để 0: trong thời gian bảo hành ({int(warranty_months)} tháng).'
            continue
        if res.n < MIN_PROJECTS:
            res.reason = SF_REASON_TOO_FEW
            continue
        if res.driver is None:
            res.reason = SF_REASON_NO_LIFTS if res.basis == BASIS_LIFT else SF_REASON_NO_NFA
            continue
        monthly = res.median * res.driver
        source = (f'Ước tính từ quỹ bảo trì thực tế của {res.n} dự án do Savills quản lý: trung vị '
                  f'{res.median:,.1f} {_sf_unit(res.basis)} (chưa VAT, theo giá năm {TARGET_YEAR}; khoảng giữa '
                  f'P25–P75: {res.p25:,.1f}–{res.p75:,.1f} {_sf_unit(res.basis)}) × {_sf_driver_text(res)}')
        if w and code not in SF_WARRANTY_CODES:
            res.warranty_months = w
            res.status = SF_STATUS_PRICED
            res.figure_excl_vat = monthly * (MONTHS - w)
            res.months = _sf_months(monthly, w, factors)
            res.remark = (f'{source} × {MONTHS - w} tháng; {w} tháng đầu nằm trong thời gian bảo hành '
                          f'({int(warranty_months)} tháng) nên để 0'
                          + (f', {vat_clause}' if vat_clause else '') + f' = {res.figure:,.0f} VND/năm.')
            continue
        res.status = SF_STATUS_PRICED
        res.figure_excl_vat = monthly * MONTHS
        res.months = _sf_months(monthly, 0, factors)
        res.remark = f'{source} × {MONTHS} tháng' + (f', {vat_clause}' if vat_clause else '') + \
            f' = {res.figure:,.0f} VND/năm.'
    return out


def price_all(rows, *, nfa, vat_rate, vat_inclusive=True, budget_year=TARGET_YEAR, self_name=None,
              has_pool=None, tower_count=None, inhouse_pool_staff=0, staff_lump=False, vat_factors=None,
              vat_clause=None, codes=ALL_CODES):
    """{code: RangeResult} for every code in scope and every cross-check code."""
    return {c: price_line(c, rows, nfa=nfa, vat_rate=vat_rate, vat_inclusive=vat_inclusive,
                          budget_year=budget_year, self_name=self_name, has_pool=has_pool,
                          tower_count=tower_count, inhouse_pool_staff=inhouse_pool_staff, staff_lump=staff_lump,
                          vat_factors=vat_factors, vat_clause=vat_clause) for c in codes}
