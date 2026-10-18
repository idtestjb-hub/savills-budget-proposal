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
ALL_CODES = PRICED_CODES + CROSS_CHECK_CODES

VALUE_COLUMNS = ['project_id', 'name_key', 'nfa_m2', 'budget_year', 'code', 'status', 'value_m2_month',
                 'cpi_factor', 'value_m2_month_2027', 'flag']
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
    stand_in: bool = False
    cross_check: bool = False
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


def is_self(row, self_key, self_nfa):
    """The reason an entry is the project being budgeted, or '' (design D2)."""
    if self_key and row['name_key'] and row['name_key'] == self_key:
        return OUT_SELF_NAME
    if self_nfa and row['nfa_m2'] and abs(self_nfa - row['nfa_m2']) <= SELF_NFA_TOLERANCE * row['nfa_m2']:
        return OUT_SELF_NFA
    return ''


def form_range(code, rows, self_name=None, self_nfa=None):
    """Leave-one-out, then IQR outliers once. Returns (used, left_out, p25, median, p75, n_value, n_zero);
    values are VND per m2 per month at 2027 prices, excluding VAT."""
    self_key = name_key(self_name) if self_name else ''
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


def remark_priced(res):
    """Client remark for a line priced from the range (spec deliverable-remarks)."""
    text = (f'Ước tính từ ngân sách thực tế của {res.n_used} dự án do Savills quản lý: trung vị '
            f'{res.median:,.0f} đ/m²/tháng (chưa VAT, theo giá năm {TARGET_YEAR}; khoảng giữa P25–P75: '
            f'{res.p25:,.0f}–{res.p75:,.0f} đ/m²/tháng) × {res.nfa:,.0f} m² NFA thu phí × {MONTHS} tháng')
    if res.vat_inclusive:
        text += f', cộng VAT {_pct(res.vat_rate)} năm {res.budget_year}.'
    else:
        text += ', chưa cộng VAT.'
    if res.code in STAND_IN_NOTE:
        text += ' ' + STAND_IN_NOTE[res.code]
    return text


def price_line(code, rows, *, nfa, vat_rate, vat_inclusive=True, budget_year=TARGET_YEAR, self_name=None,
               self_nfa=None, has_pool=None, tower_count=None):
    """One RangeResult for `code`. `rows` is load_values(); None means no values file. `self_nfa` defaults to
    `nfa` (the input's total fee-paying NFA). A cross-check code gets its range and figure but is never usable
    for pricing; the caller shows it next to the tool's own figure."""
    res = RangeResult(code=code, stand_in=code in STAND_IN_CODES, cross_check=code in CROSS_CHECK_CODES,
                      nfa=nfa, vat_rate=vat_rate, vat_inclusive=vat_inclusive, budget_year=budget_year)
    if rows is None:
        res.reason = REASON_NO_DATA
        return res
    (res.used, res.left_out, res.p25, res.median, res.p75,
     res.n_value, res.n_zero) = form_range(code, rows, self_name, nfa if self_nfa is None else self_nfa)
    if code == 'ESS23' and has_pool is not True:
        res.reason = REASON_NO_POOL
        return res
    if code == 'ESS7' and not (tower_count and tower_count >= 1):
        res.reason = REASON_NO_TOWER
        return res
    if res.n_used < MIN_PROJECTS:
        res.reason = reason_too_few(res.n_used)
        return res
    if not nfa or nfa <= 0:
        res.reason = REASON_NO_NFA
        return res
    res.figure_excl_vat = res.median * nfa * MONTHS
    gross = res.figure_excl_vat * (1.0 + vat_rate) if vat_inclusive else res.figure_excl_vat
    if res.cross_check:
        res.figure = round(gross)      # for comparison only; never written to the deliverable
        return res
    res.usable = True
    res.figure = round(gross)
    res.remark = remark_priced(res)
    return res


def price_all(rows, *, nfa, vat_rate, vat_inclusive=True, budget_year=TARGET_YEAR, self_name=None,
              has_pool=None, tower_count=None, codes=ALL_CODES):
    """{code: RangeResult} for every code in scope and every cross-check code."""
    return {c: price_line(c, rows, nfa=nfa, vat_rate=vat_rate, vat_inclusive=vat_inclusive,
                          budget_year=budget_year, self_name=self_name, has_pool=has_pool,
                          tower_count=tower_count) for c in codes}
