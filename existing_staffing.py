"""Existing-project mode: carry last year's approved staffing forward and explain every change.

Change carry-forward-staffing (openspec/changes/carry-forward-staffing, design D1-D14). For a project
Savills already manages, the Head of PM's instruction is: start from last year's approved staff
cost, recalculate it under state law only, and give a reason for every line that moves. This module
is the one place that does that, for both generators:

- reading: the project mode, minimum-wage region and prior budget year on `Project Info`, and the
  four blocks of the `Prior-Year Roster` sheet, all found by their labels (a renamed label stops the
  run and names itself, as everywhere else in this pipeline);
- computing: the budget-year staff lines (EMH2, EMH3, EMH4), the reason record of every change, and
  the Staff bridge from the baseline to the budget year;
- a Python replica of the template's own `A1. Staff cost` and `A1.1 Allowance` row formulas, so the
  internal Staff bridge can state the same figures the client deliverable's formulas produce.
  Verification compares the two after Excel recalculates the deliverable (design D13).

New-prospect mode (blank or "New prospect") never reaches anything below `read_existing()`; its
figures do not move.

A baseline is either a Prior-Year Roster (position, heads, monthly gross per head) or, for a project
whose approved budget carried staff cost as one figure, the approved line amounts (design D8). The
tool applies no percentage of its own: the law table (labor_law_params.py) and the paid-holiday
calendar (vn_holidays.paid_holidays) are the only things that move a figure without a PM reason.
"""
import calendar
import math
from dataclasses import dataclass, field

import labor_law_params
import vn_holidays
from input_labels import LabelNotFound, normalise

MODE_LABEL = 'Project Mode'
REGION_LABEL = 'Minimum Wage Region'
PRIOR_YEAR_LABEL = 'Prior Budget Year'
MODE_NEW = 'New prospect'
MODE_EXISTING = 'Existing project'
MODES = (MODE_NEW, MODE_EXISTING)

ROSTER_SHEET = 'Prior-Year Roster'
SEC_ROSTER = 'PRIOR-YEAR ROSTER'
SEC_DUTY = 'HOLIDAY AND NIGHT DUTY'
SEC_LINES = 'STAFF LINES'
SEC_ACTUAL = 'ACTUAL HEADCOUNT'
SECTIONS = (SEC_ROSTER, SEC_DUTY, SEC_LINES, SEC_ACTUAL)

# Column header labels of each block (matched after input_labels.normalise, so a unit in brackets
# may change). key -> header label.
ROSTER_COLS = {'position': 'Position', 'shift': 'Shift Code', 'heads': 'Headcount',
               'gross': 'Monthly Gross per Head', 'year': 'Budget Year', 'new_heads': 'New Headcount',
               'new_gross': 'New Monthly Gross', 'reason_code': 'Reason Code',
               'reason_note': 'Reason Note', 'note': 'Note'}
DUTY_COLS = {'code': 'Code', 'night_normal': 'Night Staff per Normal Night',
             'night_holiday': 'Night Staff per Holiday Night', 'day_holiday': 'Day Staff per Holiday',
             'gross': 'Monthly Gross for Allowance', 'note': 'Note'}
LINES_COLS = {'line': 'Line', 'approved': 'Prior-Year Approved', 'override': 'Budget-Year Override',
              'reason_code': 'Reason Code', 'reason_note': 'Reason Note'}
ACTUAL_COLS = {'position': 'Position', 'heads': 'Actual Headcount', 'source': 'Source', 'note': 'Note'}
DUTY_CODES = ('CS', 'BE', 'TDS', 'TN', 'AA')     # the five rows of the template's A1.1 (rows 7-11)
STAFF_LINES = ('EMH2', 'EMH3', 'EMH4')

# The approved reason codes (spec existing-project-staffing). The Head of PM approves the final list
# before the change is archived (task 8.4).
REASON_OTHER = 'Khác (bắt buộc ghi chú)'
REASON_CODES = (
    'Mở dịch vụ hoặc tiện ích mới',
    'Thay đổi mô hình ca hoặc giờ làm việc',
    'Thay đổi quy định pháp luật',
    'Bàn giao hoặc bổ sung khu vực quản lý',
    'Chuyển đổi giữa nhân sự trực tiếp và thuê ngoài',
    'Theo yêu cầu của cư dân hoặc chủ sở hữu',
    'Vị trí trống, không tuyển bổ sung',
    REASON_OTHER,
)
REASON_MIN_WAGE = 'điều chỉnh theo lương tối thiểu vùng'
REASON_LAW = 'điều chỉnh theo lương tối thiểu vùng và mức đóng bảo hiểm'
SOURCE_TOOL = 'tool'
SOURCE_PM = 'PM'
MISSING = 'THIẾU LÝ DO'
MISSING_NOTE = 'THIẾU GHI CHÚ (mã "Khác")'
UNKNOWN_CODE = 'MÃ LÝ DO KHÔNG CÓ TRONG DANH SÁCH'

BACKCAST_TOLERANCE = 0.01   # design: a recomputed prior year >1% off the approved EMH2 is flagged

# The internal analysis workbook's Staff Bridge sheet (generate_project_output.py) and the labels
# verification/checks.py reads back from it.
BRIDGE_SHEET = 'Staff Bridge'
BRIDGE_BASELINE_LABEL = 'Baseline (prior year)'
BRIDGE_TOTAL_LABEL = 'Budget year total'
REASONS_TITLE = 'CHANGED LINES AND REASONS'
REASON_HEADERS = ('Line', 'Item', 'Baseline', 'Budget year', 'Difference (VND/year)', 'Reason code',
                  'Reason note', 'Reason', 'Source', 'Status')

# --- The template's own A1 policy constants (2027 Resi form, 'A1. Staff cost 08.2026 (VN)') --------
# Not law: Savills' payroll policy as the template carries it. The replica below uses them exactly as
# the template's row formulas do (rows 15-88 are uniform; read 2026-10-10). If the template changes
# them, the deliverable and this replica disagree and verification's bridge-ties check fails.
A1_TRAINING_RATE = 0.013          # S8
A1_CHECKUP_ANNUAL = 1_350_000     # W7, spread over W8 = 12 months
A1_TEAM_BUILDING_PM = 1_000_000   # R: PM row
A1_TEAM_BUILDING = 300_000        # R: every other row
A1_UNIFORM = 300_000              # Z
A1_CONTRACT_MONTHS = 12           # AC95
# A1.1 (allowance) constants: E7:E11 working days per month, and the legal rates I6/M6/Q6
# (Labour Code 2019 Article 98: night +30%, night on a holiday 390%, day on a holiday 300%).
A11_WORKDAYS = 25
A11_NIGHT_RATE = 0.3
A11_HOLIDAY_NIGHT_RATE = 3.9
A11_HOLIDAY_DAY_RATE = 3


def excel_round(x, digits=0):
    """Excel's ROUND: half away from zero (Python's round() is half-to-even)."""
    q = 10 ** digits
    return math.floor(abs(x) * q + 0.5) / q * (1 if x >= 0 else -1)


def _num(value, where, allow_blank=True):
    if value is None or (isinstance(value, str) and not value.strip()):
        if allow_blank:
            return None
        raise ValueError(f'{where} is blank.')
    try:
        return float(str(value).replace(',', '')) if isinstance(value, str) else float(value)
    except ValueError:
        raise ValueError(f'{where} is {value!r}, which is not a number.') from None


def _text(value):
    return '' if value is None else str(value).strip()


# ------------------------------------------------------------------------------------------------
# Reading
# ------------------------------------------------------------------------------------------------
def read_mode(pi_labels):
    """'New prospect' or 'Existing project'. A form without the field, or a blank field, is New prospect."""
    if not pi_labels.has(MODE_LABEL):
        return MODE_NEW
    raw = _text(pi_labels.value(MODE_LABEL))
    if not raw:
        return MODE_NEW
    for mode in MODES:
        if normalise(raw) == normalise(mode):
            return mode
    raise ValueError(f"Project Info '{MODE_LABEL}' is {raw!r}. Allowed values: "
                     f"{', '.join(repr(m) for m in MODES)} (blank means {MODE_NEW!r}).")


@dataclass
class RosterRow:
    position: str
    shift: str
    heads: int
    gross: float
    year: int
    new_heads: int = None
    new_gross: float = None
    reason_code: str = ''
    reason_note: str = ''
    note: str = ''
    row: int = 0


@dataclass
class DutyRow:
    code: str
    night_normal: int
    night_holiday: int
    day_holiday: int
    gross: float
    note: str = ''
    row: int = 0


@dataclass
class LineRow:
    line: str
    approved: float = None
    override: float = None
    reason_code: str = ''
    reason_note: str = ''
    row: int = 0


@dataclass
class ExistingInput:
    region: str
    prior_year: int
    roster: list
    duty: list
    lines: dict
    actual: list


def _section_rows(ws, titles=SECTIONS):
    """Row of each block title in column A. Data rows may repeat any text, so this does not use
    SheetLabels (which refuses duplicate labels); it only looks for the block titles (`titles`:
    this sheet's four by default; existing_utilities passes its own two)."""
    found = {}
    for row in range(1, min(ws.max_row or 1, 400) + 1):
        key = normalise(ws.cell(row=row, column=1).value)
        for title in titles:
            if key == normalise(title):
                if title in found:
                    raise ValueError(f"Sheet {ws.title!r} has the block title {title!r} twice "
                                     f"(rows {found[title]} and {row}).")
                found[title] = row
    return found


def _read_block(ws, title, sections, columns, required=()):
    """Rows of one block as dicts keyed like `columns`. The row after the title holds the column
    headers; data runs until the next block title (or the end of the sheet). Blank rows are
    skipped, so a gap in the table does not hide the rows below it."""
    if title not in sections:
        raise LabelNotFound(f"Sheet {ws.title!r} has no block titled {title!r}. The form may be from "
                            f"an older version, or the title was renamed.")
    header_row = sections[title] + 1
    by_header = {}
    for col in range(1, (ws.max_column or 1) + 1):
        key = normalise(ws.cell(row=header_row, column=col).value)
        if key:
            by_header[key] = col
    cols = {}
    for key, label in columns.items():
        col = by_header.get(normalise(label))
        if col is None and key in required:
            raise LabelNotFound(f"Sheet {ws.title!r}, block {title!r}: no column headed {label!r} "
                                f"(row {header_row}).")
        cols[key] = col
    later = [r for r in sections.values() if r > sections[title]]
    last = (min(later) - 1) if later else min(ws.max_row or 0, 400)
    out = []
    for row in range(header_row + 1, last + 1):
        values = {k: (ws.cell(row=row, column=c).value if c else None) for k, c in cols.items()}
        if not all(v is None or (isinstance(v, str) and not v.strip()) for v in values.values()):
            values['_row'] = row
            out.append(values)
    return out


def read_existing(wb_values, pi_labels):
    """The Existing-project inputs, or None in New-prospect mode. Raises ValueError naming the field
    when the mode is Existing and the inputs cannot price the staff lines."""
    if read_mode(pi_labels) != MODE_EXISTING:
        return None
    region = _text(pi_labels.value(REGION_LABEL)) if pi_labels.has(REGION_LABEL) else ''
    region = (region or labor_law_params.DEFAULT_REGION).upper()
    if region not in labor_law_params.REGIONS:
        raise ValueError(f"Project Info '{REGION_LABEL}' is {region!r}; allowed: "
                         f"{', '.join(labor_law_params.REGIONS)} (blank means Region I).")
    prior = _num(pi_labels.value(PRIOR_YEAR_LABEL), f"Project Info '{PRIOR_YEAR_LABEL}'",
                 allow_blank=False)
    if ROSTER_SHEET not in wb_values.sheetnames:
        raise LabelNotFound(f"Project mode is {MODE_EXISTING!r} but the workbook has no sheet "
                            f"{ROSTER_SHEET!r}. Add it with add_existing_project_sheets.py.")
    ws = wb_values[ROSTER_SHEET]
    sections = _section_rows(ws)
    where = f"'{ROSTER_SHEET}'"
    # All four titles first: a renamed title would otherwise let the block above it run on into
    # the renamed block's rows.
    missing = [t for t in SECTIONS if t not in sections]
    if missing:
        raise LabelNotFound(f"Sheet {where} has no block titled {', '.join(repr(t) for t in missing)}. "
                            f"The form may be from an older version, or the title was renamed.")

    roster = []
    for r in _read_block(ws, SEC_ROSTER, sections, ROSTER_COLS,
                         required=('position', 'shift', 'heads', 'gross', 'new_heads', 'new_gross',
                                   'reason_code', 'reason_note')):
        at = f"{where} row {r['_row']}"
        pos = _text(r['position'])
        if not pos:
            raise ValueError(f'{at}: Position is blank.')
        heads = _num(r['heads'], f'{at} Headcount', allow_blank=False)
        gross = _num(r['gross'], f'{at} Monthly Gross per Head', allow_blank=heads == 0) or 0
        if heads < 0 or heads != int(heads):
            raise ValueError(f'{at}: Headcount {heads:g} is not a whole number of people.')
        new_heads = _num(r['new_heads'], f'{at} New Headcount')
        if new_heads is not None and (new_heads < 0 or new_heads != int(new_heads)):
            raise ValueError(f'{at}: New Headcount {new_heads:g} is not a whole number of people.')
        year = _num(r.get('year'), f'{at} Budget Year')
        roster.append(RosterRow(
            position=pos, shift=_text(r['shift']), heads=int(heads), gross=gross,
            year=int(year) if year else int(prior),
            new_heads=None if new_heads is None else int(new_heads),
            new_gross=_num(r['new_gross'], f'{at} New Monthly Gross'),
            reason_code=_text(r['reason_code']), reason_note=_text(r['reason_note']),
            note=_text(r.get('note')), row=r['_row']))

    duty = []
    for r in _read_block(ws, SEC_DUTY, sections, DUTY_COLS,
                         required=('code', 'night_normal', 'night_holiday', 'day_holiday', 'gross')):
        at = f"{where} row {r['_row']}"
        code = _text(r['code']).upper()
        if code not in DUTY_CODES:
            raise ValueError(f"{at}: Code {code!r} is not one of the A1.1 codes {', '.join(DUTY_CODES)}.")
        counts = [int(_num(r[k], f'{at} {DUTY_COLS[k]}') or 0)
                  for k in ('night_normal', 'night_holiday', 'day_holiday')]
        gross = _num(r['gross'], f'{at} Monthly Gross for Allowance', allow_blank=not any(counts))
        if any(counts) or gross:
            duty.append(DutyRow(code, *counts, gross=gross or 0, note=_text(r.get('note')), row=r['_row']))
    if len({d.code for d in duty}) != len(duty):
        raise ValueError(f"{where} block {SEC_DUTY!r}: a code appears twice.")

    lines = {}
    for r in _read_block(ws, SEC_LINES, sections, LINES_COLS,
                         required=('line', 'approved', 'override', 'reason_code', 'reason_note')):
        at = f"{where} row {r['_row']}"
        line = _text(r['line']).upper()
        if line not in STAFF_LINES:
            raise ValueError(f"{at}: Line {line!r} is not one of {', '.join(STAFF_LINES)}.")
        lines[line] = LineRow(line, approved=_num(r['approved'], f'{at} Prior-Year Approved'),
                              override=_num(r['override'], f'{at} Budget-Year Override'),
                              reason_code=_text(r['reason_code']), reason_note=_text(r['reason_note']),
                              row=r['_row'])

    actual = []
    for r in _read_block(ws, SEC_ACTUAL, sections, ACTUAL_COLS, required=('position', 'heads')):
        pos = _text(r['position'])
        heads = _num(r['heads'], f"{where} row {r['_row']} Actual Headcount")
        if pos and heads is not None:
            actual.append({'position': pos, 'heads': heads, 'source': _text(r.get('source')),
                           'note': _text(r.get('note'))})

    emh2 = lines.get('EMH2')
    if not roster and (emh2 is None or emh2.approved is None):
        raise ValueError(
            f"Project mode is {MODE_EXISTING!r} but there is no baseline: the {SEC_ROSTER!r} block on "
            f"{where} has no rows and {SEC_LINES!r} has no 'Prior-Year Approved' amount for EMH2. "
            f"Fill one of the two (design D8).")
    return ExistingInput(region=region, prior_year=int(prior), roster=roster, duty=duty,
                         lines=lines, actual=actual)


# ------------------------------------------------------------------------------------------------
# Reasons
# ------------------------------------------------------------------------------------------------
def pm_reason(code, note, codes=None):
    """A PM reason record. status is '' when complete, otherwise what is missing. `codes` is the
    approved list to check against (staffing's by default; existing_utilities passes its own, which
    ends with the same "Khác" code)."""
    code, note = _text(code), _text(note)
    if not code:
        return {'code': '', 'note': note, 'text': '', 'source': SOURCE_PM, 'status': MISSING}
    match = next((c for c in (codes or REASON_CODES) if normalise(c) == normalise(code)), None)
    if match is None:
        return {'code': code, 'note': note, 'text': code, 'source': SOURCE_PM, 'status': UNKNOWN_CODE}
    if match == REASON_OTHER and not note:
        return {'code': match, 'note': '', 'text': 'Khác', 'source': SOURCE_PM, 'status': MISSING_NOTE}
    text = (note if match == REASON_OTHER else f'{match}: {note}' if note else match)
    return {'code': match, 'note': note, 'text': text, 'source': SOURCE_PM, 'status': ''}


def tool_reason(text):
    return {'code': '', 'note': '', 'text': text, 'source': SOURCE_TOOL, 'status': ''}


# ------------------------------------------------------------------------------------------------
# Replica of the template's A1 / A1.1 row formulas
# ------------------------------------------------------------------------------------------------
def a1_params(month_values):
    """A1's hidden reference cells for one month of law values (I4, I5, caps, employer rates)."""
    base = month_values['insurance_base']
    ui_base = month_values['min_wage_region']
    return {
        'I4': base, 'I5': ui_base,
        'cap_si_hi': base * month_values['si_hi_ceiling_multiple'],
        'cap_ui': ui_base * month_values['ui_ceiling_multiple'],
        'T8': round(month_values['employer_si_rate'] + month_values['employer_hi_rate'], 6),
        'U8': month_values['employer_ui_rate'],
        'V8': month_values['union_rate'],
        'AB1': month_values['admin_markup'],
    }


def a1_row_cost(code, gross, p):
    """One A1 row's monthly cost to Savills incl. admin markup (column AC), as the template computes
    it from column G (gross) with H (increase rate) blank."""
    i = excel_round(gross)
    if i <= 0:
        return 0
    n = i / 12
    r = A1_TEAM_BUILDING_PM if code == 'PM' else A1_TEAM_BUILDING
    s = i * A1_TRAINING_RATE
    t = p['cap_si_hi'] * p['T8'] if i > p['cap_si_hi'] else i * p['T8']
    u = p['cap_ui'] * p['U8'] if i > p['cap_ui'] else i * p['U8']
    v = p['cap_si_hi'] * p['V8'] if i > p['cap_si_hi'] else i * p['V8']
    w = A1_CHECKUP_ANNUAL / 12
    base = i * 30 * 0.00099 + i * 3 * 0.0044 + 446985
    if code == 'PM':
        x = (base + 2456000) * 0.58 / 12
    else:
        x = max(30000, base * 0.40 / 12)
    z = A1_UNIFORM
    aa = excel_round(i + n + r + s + t + u + v + w + x + 0 + z)
    ab = excel_round(aa * p['AB1'])
    return aa + ab


def a1_monthly_total(persons, p):
    """Sum of AC over the persons (each person is one A1 row: (code, gross))."""
    return sum(a1_row_cost(code, gross, p) for code, gross in persons)


def year_days(year):
    return 366 if calendar.isleap(year) else 365


def a11_monthly(duty, year, gross_of=lambda d: d.gross):
    """A1.1!S13 — the monthly night/holiday allowance for the duty rows in `year`'s calendar."""
    n = len(vh_paid(year))
    h6, l6, p6 = year_days(year) - n, n, n
    j = nn = rr = 0.0
    for d in duty:
        f = gross_of(d) / A11_WORKDAYS
        h = h6 * d.night_normal if d.night_normal > 0 else 0
        l_ = l6 * d.night_holiday if d.night_holiday > 0 else 0
        pp = p6 * d.day_holiday if d.day_holiday > 0 else 0
        j += A11_NIGHT_RATE * h * f
        nn += A11_HOLIDAY_NIGHT_RATE * l_ * f
        rr += A11_HOLIDAY_DAY_RATE * pp * f
    s12 = rr + nn + j
    return excel_round(s12 / A1_CONTRACT_MONTHS)


def vh_paid(year):
    return vn_holidays.paid_holidays(year)


def holiday_change(prior_year, budget_year):
    """(added names, removed names) of paid holidays between the two years' calendars, by name."""
    def names(y):
        out = []
        for _d, name in vh_paid(y):
            base = name.split(' (')[0] if name.startswith('Tet Am lich') else name
            out.append(base)
        return out
    a, b = names(prior_year), names(budget_year)
    added, removed = list(b), list(a)
    for x in a:
        if x in added:
            added.remove(x)
    for x in b:
        if x in removed:
            removed.remove(x)
    return added, removed


_HOLIDAY_VN = {vn_holidays.CULTURE_DAY_NAME: vn_holidays.CULTURE_DAY_NAME_VN}


def holiday_reason(prior_year, budget_year):
    added, removed = holiday_change(prior_year, budget_year)
    parts = []
    if added:
        parts.append('thêm ' + ', '.join(_HOLIDAY_VN.get(a, a) for a in added))
    if removed:
        parts.append('bớt ' + ', '.join(_HOLIDAY_VN.get(r, r) for r in removed))
    n0, n1 = len(vh_paid(prior_year)), len(vh_paid(budget_year))
    return f'thay đổi số ngày lễ hưởng nguyên lương ({n0} → {n1} ngày): ' + '; '.join(parts)


# ------------------------------------------------------------------------------------------------
# Computing the budget year
# ------------------------------------------------------------------------------------------------
@dataclass
class Person:
    code: str            # A1 code written in column D ('PM', 'TN', 'AA', ...); '' for unplaced w/o code
    group: str           # placement group ('PM', 'TN', 'AA_POOL', ...) or None for an unplaced position
    label: str           # position name as given
    shift: str
    gross: float
    origin: str          # 'roster' | 'new-typed' | 'new-ratio'
    note: str = ''       # Vietnamese label for A1's remarks column


@dataclass
class LineResult:
    line: str
    baseline: float               # VND/year
    budget: float                 # VND/year, after any override
    computed: float               # VND/year before override
    law: float = 0.0
    headcount: float = 0.0
    allowance: float = 0.0
    override: float = 0.0
    reasons: list = field(default_factory=list)
    kind: str = ''                # 'roster' | 'lump' | 'duty' | 'carried' | 'ratio' | 'template'
    approved: float = None


@dataclass
class Result:
    region: str
    prior_year: int
    budget_year: int
    kind: str                     # 'roster' or 'lump'
    persons: list                 # budget-year A1 rows
    lines: dict                   # 'EMH2'/'EMH3'/'EMH4' -> LineResult
    reason_rows: list             # one per changed item (bridge + verification)
    a1_cells: dict                # hidden reference cells for A1 (budget year)
    duty: list                    # DutyRow with budget-year gross (floored)
    a11_days: tuple               # (H6, L6, P6) for the budget year
    notes: list
    backcast: dict
    actual_rows: list
    emh4_from_a5: bool


def _avg_params(params):
    """A1 parameters for a year: the annual average of each month's (constant years: the value)."""
    months = [a1_params(params.months[m]) for m in range(1, 13)]
    # round(): the mean of twelve equal floats is not always that float (0.1 -> 0.10000000000000002)
    return ({k: round(sum(m[k] for m in months) / 12, 9) for k in months[0]},
            all(m == months[0] for m in months))


def a5_template_annual():
    """EMH4 as the template's A5 sheet computes it today (H8): (1+2+17) people x wage x 1.078 / 26
    x 30% x 2 days x 4 trainings. Used for the bridge when the approved EMH4 is blank."""
    c = 5310000 * (1 + 0.078)
    return sum(c / 26 * 0.3 * 2 * 4 * g for g in (1, 2, 17))


def compute(ex, demand, budget_year, code_of, is_outsourced, unplaced_code_of,
            eff_headcount, monthly_gross_of):
    """Everything Existing-project mode writes. Pure: no workbook is opened.

    code_of(position) -> placement group ('PM', 'TN', 'AA_POOL', ...) or None;
    is_outsourced(position) -> True for the Security/Cleaning/Landscape contract roles;
    unplaced_code_of(position) -> the column-D code for a position with no A1 group;
    eff_headcount(demand_row) and monthly_gross_of(rows) are the New-prospect conversions, reused
    unchanged for new positions priced from Staffing Demand.
    """
    if ex.prior_year >= budget_year:
        raise ValueError(f"Project Info '{PRIOR_YEAR_LABEL}' is {ex.prior_year}, which is not before "
                         f"the budget year {budget_year} of the template.")
    prior_p = labor_law_params.params_for_year(ex.prior_year, ex.region)
    budget_p = labor_law_params.params_for_year(budget_year, ex.region)
    if budget_p.value('thirteenth_month') != 1:
        raise ValueError('The law table changes the 13th-month rule; A1 carries exactly one month.')
    a1_budget, constant = _avg_params(budget_p)
    floor = max(budget_p.value('min_wage_region', m) for m in range(1, 13))
    notes = []
    if budget_p.note:
        notes.append(budget_p.note)
    if not constant:
        notes.append(f'Tham số luật thay đổi trong năm {budget_year}: A1 dùng mức bình quân 12 tháng.')

    def display_code(group):
        return 'AA' if group and group.startswith('AA_') else (group or '')

    reason_rows = []

    def add_reason(line, item, baseline, budget, diff, reason):
        reason_rows.append({'line': line, 'item': item, 'baseline': baseline, 'budget': budget,
                            'diff': diff, **reason})

    # ---------------- EMH2 ----------------
    persons, base_persons, floored_base_persons = [], [], []
    emh2_line = ex.lines.get('EMH2') or LineRow('EMH2')
    kind = 'roster' if ex.roster else 'lump'
    if ex.roster:
        covered = set()
        for rr in ex.roster:
            group = code_of(rr.position)
            covered.add(group if group else rr.position.casefold())
            code = display_code(group) if group else unplaced_code_of(rr.position)
            heads1 = rr.heads if rr.new_heads is None else rr.new_heads
            gross1_raw = rr.gross if rr.new_gross is None else rr.new_gross
            gross1 = max(gross1_raw, floor) if heads1 else gross1_raw
            base_persons += [(code, rr.gross)] * rr.heads
            floored_base_persons += [(code, max(rr.gross, floor))] * rr.heads
            label = f'Theo NS {rr.year} đã duyệt'
            changed_pm = (rr.new_heads is not None and rr.new_heads != rr.heads) or \
                         (rr.new_gross is not None and rr.new_gross != rr.gross)
            if changed_pm:
                label += f'; điều chỉnh {rr.heads} → {heads1} người, ' \
                         f'{rr.gross:,.0f} → {gross1:,.0f} VND/tháng'
            persons += [Person(code, group, rr.position, rr.shift, gross1, 'roster', label)] * heads1
            item = f'A1: {rr.position}'
            base_txt = f'{rr.heads} × {rr.gross:,.0f}'
            budget_txt = f'{heads1} × {gross1:,.0f}'
            diff = 12 * (a1_monthly_total([(code, gross1)] * heads1, a1_budget)
                         - a1_monthly_total([(code, rr.gross)] * rr.heads, a1_budget))
            if changed_pm:
                add_reason('EMH2', item, base_txt, budget_txt, diff, pm_reason(rr.reason_code, rr.reason_note))
            if heads1 and gross1 > gross1_raw:
                add_reason('EMH2', item + ' (lương tối thiểu)', f'{gross1_raw:,.0f}', f'{gross1:,.0f}',
                           12 * heads1 * (a1_row_cost(code, gross1, a1_budget)
                                          - a1_row_cost(code, gross1_raw, a1_budget)),
                           tool_reason(f'{REASON_MIN_WAGE} ({floor:,.0f} VND/tháng, vùng {ex.region})'))
        # New positions: in-house Staffing Demand rows whose group the roster does not cover.
        groups = {}
        for d in demand:
            pos = d['Position']
            if is_outsourced(pos):
                continue
            group = code_of(pos)
            key = group if group else pos.casefold()
            if key in covered:
                continue
            groups.setdefault(key, []).append(d)
        for key, rows in groups.items():
            heads = sum(eff_headcount(d) for d in rows)
            if not heads:
                continue
            gross = max(monthly_gross_of(rows), floor)
            group = code_of(rows[0]['Position'])
            code = display_code(group) if group else unplaced_code_of(rows[0]['Position'])
            ratio = any('rounded up' in (d.get('Basis') or '') for d in rows)
            origin = 'new-ratio' if ratio else 'new-typed'
            label = (f'ước tính (vị trí mới so với NS {ex.prior_year})' if ratio
                     else f'vị trí mới so với NS {ex.prior_year} (PM nhập)')
            persons += [Person(code, group, rows[0]['Position'], rows[0].get('ShiftCode', ''), gross,
                               origin, label)] * heads
            reason = next((pm_reason(d.get('ReasonCode'), d.get('ReasonNote')) for d in rows
                           if _text(d.get('ReasonCode'))), pm_reason('', ''))
            add_reason('EMH2', f'A1: {rows[0]["Position"]} (vị trí mới)', '0', f'{heads} × {gross:,.0f}',
                       12 * a1_monthly_total([(code, gross)] * heads, a1_budget), reason)

        base_backcast = sum(a1_monthly_total(base_persons, a1_params(prior_p.months[m]))
                            for m in range(1, 13))
        law_level = 12 * a1_monthly_total(floored_base_persons, a1_budget)
        computed = 12 * a1_monthly_total([(p.code, p.gross) for p in persons], a1_budget)
        emh2 = LineResult('EMH2', baseline=base_backcast, budget=computed, computed=computed,
                          law=law_level - base_backcast, headcount=computed - law_level,
                          kind='roster', approved=emh2_line.approved)
        if abs(emh2.law) >= 1:
            emh2.reasons.append(tool_reason(REASON_LAW))
        if abs(emh2.headcount) >= 1:
            emh2.reasons.append(tool_reason('thay đổi nhân sự theo các dòng A1 có lý do riêng'))
    else:
        emh2 = LineResult('EMH2', baseline=emh2_line.approved, budget=emh2_line.approved,
                          computed=emh2_line.approved, kind='lump', approved=emh2_line.approved)
        notes.append('Không có bảng nhân sự theo vị trí: EMH2 giữ theo số đã duyệt, không tính được '
                     'tác động của luật lên lương từng người.')
    backcast = {}
    if kind == 'roster' and emh2_line.approved:
        gap = emh2.baseline - emh2_line.approved
        backcast = {'recomputed': emh2.baseline, 'approved': emh2_line.approved, 'gap': gap,
                    'flag': abs(gap) > BACKCAST_TOLERANCE * emh2_line.approved}

    # ---------------- EMH3 ----------------
    emh3_line = ex.lines.get('EMH3') or LineRow('EMH3')
    duty_budget = [DutyRow(d.code, d.night_normal, d.night_holiday, d.day_holiday,
                           gross=max(d.gross, floor), note=d.note, row=d.row) for d in ex.duty]
    n1 = len(vh_paid(budget_year))
    a11_days = (year_days(budget_year) - n1, n1, n1)
    if ex.duty:
        b3 = 12 * a11_monthly(ex.duty, ex.prior_year)
        h3 = 12 * a11_monthly(ex.duty, budget_year)
        c3 = 12 * a11_monthly(duty_budget, budget_year)
        emh3 = LineResult('EMH3', baseline=b3, budget=c3, computed=c3, allowance=c3 - b3, kind='duty',
                          approved=emh3_line.approved)
        if abs(h3 - b3) >= 1:
            reason = tool_reason(holiday_reason(ex.prior_year, budget_year))
            emh3.reasons.append(reason)
            add_reason('EMH3', 'Số ngày lễ', str(len(vh_paid(ex.prior_year))), str(n1), h3 - b3, reason)
        if abs(c3 - h3) >= 1:
            reason = tool_reason(f'{REASON_MIN_WAGE} ({floor:,.0f} VND/tháng, vùng {ex.region})')
            emh3.reasons.append(reason)
            add_reason('EMH3', 'Lương tính phụ cấp', '', '', c3 - h3, reason)
        if emh3_line.approved:
            gap = b3 - emh3_line.approved
            if abs(gap) > BACKCAST_TOLERANCE * emh3_line.approved:
                notes.append(f'EMH3 tính lại cho NS {ex.prior_year} là {b3:,.0f} VND, khác số đã duyệt '
                             f'{emh3_line.approved:,.0f} VND ({gap:+,.0f}).')
    elif emh3_line.approved is not None:
        emh3 = LineResult('EMH3', baseline=emh3_line.approved, budget=emh3_line.approved,
                          computed=emh3_line.approved, kind='carried', approved=emh3_line.approved)
    else:
        emh3 = LineResult('EMH3', baseline=0, budget=0, computed=0, kind='none')

    # ---------------- EMH4 ----------------
    emh4_line = ex.lines.get('EMH4') or LineRow('EMH4')
    emh4_from_a5 = emh4_line.approved is None
    if emh4_from_a5:
        a5 = a5_template_annual()
        emh4 = LineResult('EMH4', baseline=a5, budget=a5, computed=a5, kind='template')
    else:
        avg0 = prior_p.annual_average('min_wage_region')
        avg1 = budget_p.annual_average('min_wage_region')
        new = excel_round(emh4_line.approved * avg1 / avg0) if emh4_line.approved else 0
        emh4 = LineResult('EMH4', baseline=emh4_line.approved, budget=new, computed=new,
                          allowance=new - emh4_line.approved, kind='carried', approved=emh4_line.approved)
        if abs(new - emh4_line.approved) >= 1:
            reason = tool_reason(f'{REASON_MIN_WAGE} ({avg0:,.0f} → {avg1:,.0f} VND/tháng bình quân, '
                                 f'vùng {ex.region})')
            emh4.reasons.append(reason)
            add_reason('EMH4', 'Lương tối thiểu vùng', f'{avg0:,.0f}', f'{avg1:,.0f}',
                       new - emh4_line.approved, reason)

    # ---------------- PM line overrides ----------------
    for result, line in ((emh2, emh2_line), (emh3, emh3_line), (emh4, emh4_line)):
        if line.override is not None and abs(line.override - result.computed) >= 1:
            reason = pm_reason(line.reason_code, line.reason_note)
            result.override = line.override - result.computed
            result.budget = line.override
            result.reasons.append(reason)
            add_reason(result.line, 'Ghi đè của PM', f'{result.computed:,.0f}', f'{line.override:,.0f}',
                       result.override, reason)

    # Any line that moved without a reason of its own is itself a missing reason.
    for result in (emh2, emh3, emh4):
        if result.baseline is not None and abs(result.budget - result.baseline) >= 1 and not result.reasons:
            r = pm_reason('', '')
            result.reasons.append(r)
            add_reason(result.line, 'Cả dòng', f'{result.baseline:,.0f}', f'{result.budget:,.0f}',
                       result.budget - result.baseline, r)

    a1_cells = {'I4': a1_budget['I4'], 'I5': a1_budget['I5'], 'T8': a1_budget['T8'],
                'U8': a1_budget['U8'], 'V8': a1_budget['V8'], 'AB1': a1_budget['AB1'],
                'si_hi_multiple': budget_p.value('si_hi_ceiling_multiple'),
                'ui_multiple': budget_p.value('ui_ceiling_multiple')}

    actual_rows = []
    if ex.actual:
        base_heads = {}
        for rr in ex.roster:
            base_heads[rr.position.casefold()] = base_heads.get(rr.position.casefold(), 0) + rr.heads
        for a in ex.actual:
            b = base_heads.get(a['position'].casefold())
            actual_rows.append({**a, 'baseline': b, 'differs': b is None or b != a['heads']})

    return Result(region=ex.region, prior_year=ex.prior_year, budget_year=budget_year, kind=kind,
                  persons=persons, lines={'EMH2': emh2, 'EMH3': emh3, 'EMH4': emh4},
                  reason_rows=reason_rows, a1_cells=a1_cells, duty=duty_budget, a11_days=a11_days,
                  notes=notes, backcast=backcast, actual_rows=actual_rows, emh4_from_a5=emh4_from_a5)


def adjustment_sentence(result, line):
    """'Điều chỉnh so với NS <năm>: …' for a changed line, '' for an unchanged one (spec
    deliverable-remarks)."""
    lr = result.lines[line]
    if lr.baseline is None or abs(lr.budget - lr.baseline) < 1:
        return ''
    texts = [r['text'] or 'chưa ghi lý do' for r in lr.reasons] or ['chưa ghi lý do']
    return (f' Điều chỉnh so với NS {result.prior_year}: {lr.baseline:,.0f} → {lr.budget:,.0f} VND/năm '
            f'({lr.budget - lr.baseline:+,.0f} VND); lý do: {"; ".join(texts)}.')


LABEL_PM_ADJUST = 'Điều chỉnh của PM'


def detail_rows(result):
    """The rows Existing-project mode adds below A1, A1.1 and A5 so that EMH2, EMH3 and EMH4 each
    equal their detail sheet (design D15): {'EMH2': [...], 'EMH3': [...], 'EMH4': [...]}, each row
    {'label', 'annual' (VND/year), 'note'}. A carried-forward line gets a "mang sang" row, EMH4 a
    minimum-wage row when the ratio moved it, and a PM override a row equal to the override minus
    the computed figure. A line computed on its sheet without an override gets no row."""
    rows = {'EMH2': [], 'EMH3': [], 'EMH4': []}
    py = result.prior_year
    e2, e3, e4 = (result.lines[k] for k in ('EMH2', 'EMH3', 'EMH4'))
    if e2.kind == 'lump':
        rows['EMH2'].append({'label': f'EMH2 đã duyệt NS {py} mang sang', 'annual': e2.computed,
                             'note': f'Số EMH2 đã duyệt NS {py}; dự án không có bảng nhân sự theo vị trí.'})
    if e3.kind == 'carried':
        rows['EMH3'].append({'label': f'EMH3 đã duyệt NS {py} mang sang', 'annual': e3.computed,
                             'note': f'Số EMH3 đã duyệt NS {py}; không có số nhân sự trực ca đêm/ngày lễ.'})
    if e4.kind == 'carried':
        rows['EMH4'].append({'label': f'EMH4 đã duyệt NS {py} mang sang', 'annual': e4.baseline,
                             'note': f'Số EMH4 đã duyệt NS {py}.'})
        if abs(e4.allowance) >= 1:
            rows['EMH4'].append({'label': 'Điều chỉnh theo lương tối thiểu vùng', 'annual': e4.allowance,
                                 'note': next((r['text'] for r in e4.reasons if r['source'] == SOURCE_TOOL),
                                              REASON_MIN_WAGE)})
    for key, lr in (('EMH2', e2), ('EMH3', e3), ('EMH4', e4)):
        if abs(lr.override) >= 1:
            reason = next((r for r in reversed(lr.reasons) if r['source'] == SOURCE_PM), None)
            rows[key].append({'label': LABEL_PM_ADJUST, 'annual': lr.override,
                              'note': (reason or {}).get('text') or 'chưa ghi lý do'})
    return rows


def missing_reasons(reason_rows):
    """Reason rows that fail the rule: no reason, unknown code, or 'Khác' without a note."""
    return [r for r in reason_rows if r.get('status')]
