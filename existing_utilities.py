"""Existing-project mode for common-area electricity (EEE.C) and water (EEW.C).

Change carry-forward-common-utilities. For a project Savills already runs, both logic files say the
same thing: start from what the building actually used. This module reads the 'Prior-Year Utilities'
sheet of the input workbook (monthly amounts actually spent, optional consumption, per-line settings),
takes the average consumption over the 12 most recent months that have a figure, prices it at the
tariff and VAT in force in each month of the budget year (utility_tariffs.py), and explains every
change from the approved prior-year amount: consumption, tariff, VAT, the PM's override (design D4).

The tool adds no percentage of its own. A PM override of consumption needs a reason code. New-prospect
mode never reaches this module: read_utilities() returns None and the generators keep their
new-building estimate.

Stops (design D8) raise ValueError (LabelNotFound for a missing sheet, block or column) naming the
row or field; flags are collected in LineResult.flags and never stop the run.
"""
import datetime
import unicodedata
from dataclasses import dataclass, field

import existing_staffing as es
import utility_tariffs as ut
from input_labels import LabelNotFound, normalise

SHEET = 'Prior-Year Utilities'
SEC_ACTUALS = 'UTILITY ACTUALS'
SEC_LINES = 'UTILITY LINES'
SECTIONS = (SEC_ACTUALS, SEC_LINES)
CITY_LABEL = 'City / Province'

LINES = ('EEE.C', 'EEW.C')
LINE_UTILITY = {'EEE.C': ut.ELECTRICITY, 'EEW.C': ut.WATER}
LINE_NAME_VI = {'EEE.C': 'Điện khu công cộng', 'EEW.C': 'Nước khu công cộng'}

# Column header labels of each block (matched after input_labels.normalise, so a unit in brackets may
# change). key -> header label.
ACTUAL_COLS = {'line': 'Line', 'month': 'Month', 'amount': 'Amount', 'incl_vat': 'Includes VAT',
               'consumption': 'Consumption', 'note': 'Note'}
LINE_COLS = {'line': 'Line', 'category': 'Tariff Category', 'bill_price': 'Unit Price on Bill',
             'bill_source': 'Unit Price Source', 'approved': 'Prior-Year Approved',
             'approved_incl_vat': 'Approved Includes VAT', 'override': 'Budget-Year Consumption Override',
             'reason_code': 'Reason Code', 'reason_note': 'Reason Note'}

# The approved reason codes for a consumption override (spec existing-project-utilities). The Head of
# PM approves the final list before the change is archived (task 7.3).
REASON_OTHER = es.REASON_OTHER
REASON_CODES = (
    'Mở dịch vụ hoặc tiện ích mới',
    'Thay đổi giờ vận hành',
    'Bàn giao hoặc bổ sung khu vực quản lý',
    'Thay đổi số cư dân vào ở',
    'Tiết kiệm năng lượng',
    REASON_OTHER,
)

WINDOW_MONTHS = 12
MIN_MONTHS = 3
RATE_TOLERANCE = 0.01        # implied bill rate vs the table, same 1% as the staffing back-cast
YES = ('yes', 'y', 'có', 'co', 'x', 'true', '1')
NO = ('no', 'n', 'không', 'khong', 'false', '0')

# The internal 'Utility Bridge' sheet (generate_project_output.py) and the labels verification reads.
BRIDGE_SHEET = 'Utility Bridge'
BRIDGE_TOTAL_LABEL = 'Budget year total'


# ------------------------------------------------------------------------------------------------
# Reading
# ------------------------------------------------------------------------------------------------
@dataclass
class MonthEntry:
    line: str
    year: int
    month: int
    amount: float = None
    incl_vat: bool = None
    consumption: float = None
    note: str = ''
    row: int = 0


@dataclass
class LineSetting:
    line: str
    category: str = ''
    bill_price: float = None
    bill_source: str = ''
    approved: float = None
    approved_incl_vat: bool = None
    override: float = None
    reason_code: str = ''
    reason_note: str = ''
    row: int = 0


@dataclass
class UtilitiesInput:
    prior_year: int
    region: str
    entries: dict
    settings: dict


def _nfc(value):
    return unicodedata.normalize('NFC', es._text(value))


def _key(value):
    return normalise(_nfc(value))


def _yes_no(value, where, allow_blank=True):
    text = _key(value)
    if not text:
        if allow_blank:
            return None
        raise ValueError(f'{where} is blank; enter Yes or No.')
    if text in YES:
        return True
    if text in NO:
        return False
    raise ValueError(f'{where} is {value!r}; enter Yes or No.')


def _month(value, where):
    """(year, month) from an Excel date or a typed 'MM/YYYY' / 'M/YYYY' / 'YYYY-MM'."""
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.year, value.month
    text = es._text(value)
    try:
        if '/' in text:
            m, y = text.split('/')[-2:]
        elif '-' in text:
            y, m = text.split('-')[:2]
        else:
            raise ValueError
        y, m = int(y), int(m)
        if not (1 <= m <= 12 and 2000 <= y <= 2100):
            raise ValueError
        return y, m
    except ValueError:
        raise ValueError(f'{where} is {value!r}; enter the month as MM/YYYY (for example 09/2025).') from None


def _line(value, where):
    text = _key(value).upper()
    for line in LINES:
        if text == line.upper():
            return line
    raise ValueError(f'{where} is {value!r}; the line must be one of {", ".join(LINES)}.')


def _positive(value, where, allow_zero=True):
    n = es._num(value, where, allow_blank=True)
    if n is not None and (n < 0 or (n == 0 and not allow_zero)):
        raise ValueError(f'{where} is {n:,.0f}; a negative{"" if allow_zero else " or zero"} value is not allowed.')
    return n


def _category(value, line, where):
    text = _key(value)
    if not text:
        return ''
    for cat in ut.CATEGORIES[LINE_UTILITY[line]]:
        if _key(cat) == text:
            return cat
    raise ValueError(f'{where} is {value!r}; allowed for {line}: '
                     f'{"; ".join(ut.CATEGORIES[LINE_UTILITY[line]])}.')


def read_utilities(wb_values, pi_labels):
    """The Existing-project utility inputs, or None in New-prospect mode. Raises ValueError (or
    LabelNotFound) naming the row or field on any stop of design D8 that the input alone decides."""
    if es.read_mode(pi_labels) != es.MODE_EXISTING:
        return None
    if SHEET not in wb_values.sheetnames:
        raise LabelNotFound(f"Project mode is {es.MODE_EXISTING!r} but the workbook has no sheet {SHEET!r}, "
                            f"so common-area electricity and water have nothing to start from. Add it with "
                            f"add_existing_project_sheets.py and fill it in.")
    ws = wb_values[SHEET]
    sections = es._section_rows(ws, SECTIONS)
    missing = [t for t in SECTIONS if t not in sections]
    if missing:
        raise LabelNotFound(f"Sheet {SHEET!r} has no block titled {', '.join(repr(t) for t in missing)}. "
                            f"The form may be from an older version, or the title was renamed.")

    entries = {line: [] for line in LINES}
    seen = {}
    for r in es._read_block(ws, SEC_ACTUALS, sections, ACTUAL_COLS,
                            required=('line', 'month', 'amount', 'incl_vat', 'consumption')):
        at = f"'{SHEET}' row {r['_row']}"
        line = _line(r['line'], f'{at} Line')
        y, m = _month(r['month'], f'{at} Month')
        if (line, y, m) in seen:
            raise ValueError(f"{line} has two rows for {m:02d}/{y} ('{SHEET}' rows {seen[(line, y, m)]} and "
                             f"{r['_row']}). Keep one row per month: add several meters up before typing them in.")
        seen[(line, y, m)] = r['_row']
        amount = _positive(r['amount'], f'{at} Amount (VND)')
        incl = _yes_no(r['incl_vat'], f'{at} Includes VAT', allow_blank=amount is None)
        entries[line].append(MonthEntry(line, y, m, amount, incl,
                                        _positive(r['consumption'], f'{at} Consumption'),
                                        es._text(r['note']), r['_row']))

    settings = {}
    for r in es._read_block(ws, SEC_LINES, sections, LINE_COLS,
                            required=('line', 'category', 'bill_price', 'approved', 'approved_incl_vat',
                                      'override', 'reason_code', 'reason_note')):
        at = f"'{SHEET}' row {r['_row']}"
        line = _line(r['line'], f'{at} Line')
        if line in settings:
            raise ValueError(f"{line} has two rows in block {SEC_LINES!r} ({at} and row {settings[line].row}).")
        approved = _positive(r['approved'], f'{at} Prior-Year Approved (VND/year)')
        settings[line] = LineSetting(
            line, _category(r['category'], line, f'{at} Tariff Category'),
            _positive(r['bill_price'], f'{at} Unit Price on Bill', allow_zero=False), es._text(r['bill_source']),
            approved, _yes_no(r['approved_incl_vat'], f'{at} Approved Includes VAT', allow_blank=approved is None),
            _positive(r['override'], f'{at} Budget-Year Consumption Override'),
            es._text(r['reason_code']), es._text(r['reason_note']), r['_row'])

    prior = None
    if pi_labels.has(es.PRIOR_YEAR_LABEL) and es._text(pi_labels.value(es.PRIOR_YEAR_LABEL)):
        prior = int(es._num(pi_labels.value(es.PRIOR_YEAR_LABEL), f"Project Info '{es.PRIOR_YEAR_LABEL}'"))
    city = pi_labels.value(CITY_LABEL) if pi_labels.has(CITY_LABEL) else ''
    return UtilitiesInput(prior, ut.region_of(city), entries, settings)


# ------------------------------------------------------------------------------------------------
# Computing
# ------------------------------------------------------------------------------------------------
def _ym_add(ym, months):
    y, m = ym
    idx = y * 12 + (m - 1) + months
    return idx // 12, idx % 12 + 1


def _ym_text(ym):
    return f'{ym[1]:02d}/{ym[0]}'


def _used_range(months):
    """'01/2026–08/2026': first to last month the average actually used. The 12-month window can start
    earlier when months are missing, so remarks name the months used, not the window (7.2 back-test)."""
    return f'{_ym_text((months[0].year, months[0].month))}–{_ym_text((months[-1].year, months[-1].month))}'


@dataclass
class MonthUsed:
    year: int
    month: int
    amount: float
    incl_vat: bool
    consumption: float      # kWh or m3 used for the average
    derived: bool           # True when consumption = amount / unit price
    unit_price: float       # VND per unit on the amount's VAT basis
    flag: str = ''


@dataclass
class LineResult:
    line: str
    utility: str
    unit: str
    category: str
    bill_price: float
    bill_source: str
    basis: str                      # 'actual' or 'approved'
    months: list                    # MonthUsed, oldest first
    window: tuple                   # ((y, m), (y, m)) or None
    missing_months: list            # (y, m) inside the window with no amount
    ignored_older: int
    q_bar: float                    # baseline consumption per month
    q_budget: float                 # budget-year consumption per month (override or q_bar)
    ref_prices: list                # 12 MonthPrice the baseline is valued at
    budget_prices: list             # 12 MonthPrice of the budget year
    amounts: list                   # 12 VND amounts, rounded as written to the deliverable
    annual: float                   # sum of `amounts`
    approved: float                 # approved prior-year amount on its own VAT basis, or None
    approved_incl_vat: bool
    approved_on_basis: float        # the same, on the deliverable's VAT basis, or None
    bridge: dict                    # baseline, consumption, tariff, vat, override, rounding, budget
    reasons: list                   # reason records (es.tool_reason / es.pm_reason)
    flags: list                     # Vietnamese flag sentences, never blocking
    note: str = ''                  # 'no newer price for the year' note, or ''


@dataclass
class UtilitiesResult:
    prior_year: int
    budget_year: int
    incl_vat: bool
    region: str
    lines: dict = field(default_factory=dict)


def _first_doc(basis):
    """The first document of a legal_basis cell, without its article or appendix, for a short citation
    in a client remark: 'Quyết định 1279/QĐ-BCT Phụ lục mục 2.2.2; ...' -> 'Quyết định 1279/QĐ-BCT'."""
    doc = basis.split(';')[0].strip()
    for cut in (' Điều', ' Phụ lục', ' ('):
        if cut in doc:
            doc = doc[:doc.index(cut)]
    return doc.strip()


def _lower_first(text):
    return text[:1].lower() + text[1:]


def _vat_change(p0, pb, utility):
    """'VAT 8% → 10% (...)' for each VAT component that differs between two MonthPrice, '' if none."""
    parts = []
    pairs = [('vat_pct', 'VAT' if utility == ut.ELECTRICITY else 'VAT nước sạch')]
    if utility == ut.WATER and (p0.wastewater_pct or pb.wastewater_pct):
        pairs.append(('wastewater_vat_pct', 'VAT dịch vụ thoát nước'))
    for comp, name in pairs:
        a, b = getattr(p0, comp), getattr(pb, comp)
        if abs(a - b) > 1e-9:
            doc = _first_doc((pb.rows.get(comp) or {}).get('legal_basis', ''))
            parts.append(f'{name} {a:g}% → {b:g}%' + (f' ({doc})' if doc else ''))
    return '; '.join(parts)


def _compute_line(line, inp, budget_year, prior_year, incl_vat, rows, months_of_budget=None):
    utility = LINE_UTILITY[line]
    unit = ut.UNITS[utility]
    s = inp.settings.get(line) or LineSetting(line)
    try:
        tariff = ut.LineTariff(utility, s.category, inp.region, s.bill_price, s.bill_source, rows=rows)
    except ut.TariffError as e:
        raise ValueError(f'{line}: {e}') from None
    cat = tariff.category

    def price_of(y, m):
        try:
            return tariff.month(y, m)
        except ut.TariffError as e:
            raise ValueError(f'{line}: {e}') from None

    # The twelve (year, month) pairs priced for the budget: the budget period (change
    # apply-head-of-pm-decisions-2026-10, group 1), or calendar months 1-12 of the budget year.
    budget_months = list(months_of_budget) if months_of_budget else [(budget_year, m) for m in range(1, 13)]
    prior_months = [(y - budget_year + prior_year, m) for y, m in budget_months]
    entries = inp.entries.get(line, [])
    for e in entries:
        if (e.year, e.month) >= budget_months[0]:
            where = (f'the budget year {budget_year}' if budget_months[0] == (budget_year, 1)
                     else f'the budget period starting {_ym_text(budget_months[0])}')
            raise ValueError(f"{line}: '{SHEET}' row {e.row} is for {_ym_text((e.year, e.month))}, which is in or after "
                             f"{where}. Enter only months before the budget {'year' if budget_months[0] == (budget_year, 1) else 'period'}.")
    with_amount = [e for e in entries if e.amount is not None]
    flags, months, missing, ignored, window = [], [], [], 0, None
    if with_amount:
        latest = max((e.year, e.month) for e in with_amount)
        start = _ym_add(latest, -(WINDOW_MONTHS - 1))
        window = (start, latest)
        used = sorted((e for e in with_amount if (e.year, e.month) >= start), key=lambda e: (e.year, e.month))
        ignored = len(with_amount) - len(used)
        have = {(e.year, e.month) for e in used}
        missing = [_ym_add(start, i) for i in range(WINDOW_MONTHS) if _ym_add(start, i) not in have]
    else:
        used = []
    n = len(used)

    if n >= MIN_MONTHS:
        basis = 'actual'
        for e in used:
            p = price_of(e.year, e.month).price(e.incl_vat)
            flag = ''
            if e.consumption is not None:
                q, derived = e.consumption, False
                if e.amount > 0 and q > 0 and abs(e.amount / q / p - 1) > RATE_TOLERANCE:
                    flag = (f'tháng {_ym_text((e.year, e.month))}: đơn giá trên hóa đơn {e.amount / q:,.0f} đ/{unit} '
                            f'khác đơn giá áp dụng {p:,.0f} đ/{unit} quá 1%, cần kiểm tra loại giá')
                elif e.amount > 0 and q == 0:
                    flag = f'tháng {_ym_text((e.year, e.month))}: có số tiền nhưng lượng tiêu thụ bằng 0'
            else:
                q, derived = e.amount / p, True
            if e.amount == 0:
                flag = f'tháng {_ym_text((e.year, e.month))}: số tiền bằng 0'
            months.append(MonthUsed(e.year, e.month, e.amount, e.incl_vat, q, derived, p, flag))
            if flag:
                flags.append(flag)
        q_bar = sum(mu.consumption for mu in months) / n
        ref = [price_of(*window[1])] * 12
        if n < WINDOW_MONTHS:
            flags.insert(0, f'chỉ có {n}/12 tháng thực chi trong kỳ {_ym_text(window[0])}–{_ym_text(window[1])}')
    else:
        if s.approved is None:
            raise ValueError(
                f"{line}: '{SHEET}' has {n} month(s) of actual spend (at least {MIN_MONTHS} are needed) and no "
                f"'Prior-Year Approved' amount in block {SEC_LINES!r}. Enter the monthly amounts in block "
                f"{SEC_ACTUALS!r}, or the approved prior-year amount (VND/year) and whether it includes VAT.")
        basis = 'approved'
        ref = [price_of(y, m) for y, m in prior_months]
        q_bar = s.approved / sum(p.price(s.approved_incl_vat) for p in ref)
        flags.insert(0, f'chỉ có {n} tháng thực chi; dùng số NS {prior_year} đã duyệt làm mốc')
    if ignored:
        flags.append(f'{ignored} tháng cũ hơn kỳ 12 tháng gần nhất không được dùng')

    pm = []
    q_budget = q_bar
    if s.override is not None:
        reason = es.pm_reason(s.reason_code, s.reason_note, codes=REASON_CODES)
        if reason['status']:
            raise ValueError(f"{line}: 'Budget-Year Consumption Override' ({s.override:,.0f} {unit}/month, "
                             f"'{SHEET}' row {s.row}) needs a reason: {reason['status']}. Allowed codes: "
                             f"{'; '.join(REASON_CODES)}.")
        q_budget = s.override
        pm.append(reason)

    budget = [price_of(y, m) for y, m in budget_months]
    amounts = [round(q_budget * p.price(incl_vat)) for p in budget]
    annual = float(sum(amounts))

    def at_ref_vat(p, r):
        return p.gross(vat_pct=r.vat_pct, wastewater_vat_pct=r.wastewater_vat_pct) if incl_vat else p.net()

    base_b = q_bar * sum(r.price(incl_vat) for r in ref)
    tariff_eff = q_bar * sum(at_ref_vat(p, r) - r.price(incl_vat) for p, r in zip(budget, ref))
    vat_eff = q_bar * sum(p.price(incl_vat) - at_ref_vat(p, r) for p, r in zip(budget, ref))
    override_eff = (q_budget - q_bar) * sum(p.price(incl_vat) for p in budget)
    approved_on_basis = None
    if s.approved is not None:
        if s.approved_incl_vat == incl_vat:
            approved_on_basis = s.approved
        else:
            py = [price_of(y, m) for y, m in prior_months]
            approved_on_basis = (s.approved * sum(p.price(incl_vat) for p in py)
                                 / sum(p.price(s.approved_incl_vat) for p in py))
    bridge = {
        'approved': approved_on_basis,
        'baseline': base_b,
        'consumption': (base_b - approved_on_basis) if approved_on_basis is not None else None,
        'tariff': tariff_eff,
        'vat': vat_eff,
        'override': override_eff,
    }
    bridge['rounding'] = annual - (base_b + tariff_eff + vat_eff + override_eff)
    bridge['budget'] = annual

    # Tool-written reasons, in the order of the bridge; the PM's override reason comes last.
    p0, pb = ref[-1], budget[0]
    reasons = []
    if basis == 'actual':
        derived = sum(1 for mu in months if mu.derived)
        how = (', lượng suy ra từ số tiền trên hóa đơn' if derived == n else
               f', {derived} tháng suy ra từ số tiền' if derived else ', theo lượng trên hóa đơn')
        reasons.append(es.tool_reason(
            f'thực chi bình quân {n} tháng {_used_range(months)}: '
            f'{q_bar:,.0f} {unit}/tháng{how}'))
    else:
        reasons.append(es.tool_reason(
            f'NS {prior_year} đã duyệt {s.approved:,.0f} VND/năm '
            f'({"gồm" if s.approved_incl_vat else "chưa gồm"} VAT) tương đương {q_bar:,.0f} {unit}/tháng'))
    if abs(tariff_eff) >= 1:
        reasons.append(es.tool_reason(
            f'đơn giá đổi từ {p0.net():,.0f} {"lên" if pb.net() >= p0.net() else "xuống"} '
            f'{pb.net():,.0f} đ/{unit} chưa VAT'))
    if abs(vat_eff) >= 1 and _vat_change(p0, pb, utility):
        reasons.append(es.tool_reason(_vat_change(p0, pb, utility)))
    reasons += pm
    return LineResult(line, utility, unit, cat, s.bill_price, s.bill_source, basis, months, window, missing,
                      ignored, q_bar, q_budget, ref, budget, amounts, annual, s.approved, s.approved_incl_vat,
                      approved_on_basis, bridge, reasons, flags, tariff.year_note(budget_year))


def compute(inp, budget_year, incl_vat, rows=None, months=None):
    """UtilitiesResult for both lines. `incl_vat` is the deliverable's basis: True unless the form's VAT
    switch ('2. Budget-Management Fund'!F7) reads KHOÁN. Raises ValueError on any stop of design D8."""
    budget_year = int(budget_year)
    prior_year = inp.prior_year or budget_year - 1
    rows = ut.load_rows() if rows is None else rows
    result = UtilitiesResult(prior_year, budget_year, bool(incl_vat), inp.region)
    for line in LINES:
        result.lines[line] = _compute_line(line, inp, budget_year, prior_year, bool(incl_vat), rows, months)
    return result


# ------------------------------------------------------------------------------------------------
# Remarks (Vietnamese, client-facing: no internal wording)
# ------------------------------------------------------------------------------------------------
def _price_clause(lr):
    p = lr.budget_prices[0]
    unit = lr.unit
    if lr.bill_price is not None:
        src = f', {lr.bill_source}' if lr.bill_source else ''
        price = f'đơn giá trên hóa đơn của dự án {p.base:,.0f} đ/{unit} chưa VAT{src}'
    else:
        b = p.rows.get('base') or {}
        price = (f'đơn giá {p.base:,.0f} đ/{unit} chưa VAT ({_lower_first(lr.category)}, '
                 f'{_first_doc(b.get("legal_basis", ""))})')
    if lr.utility == ut.WATER and p.wastewater_pct:
        w = p.rows.get('wastewater_pct') or {}
        price += (f' cộng giá dịch vụ thoát nước và xử lý nước thải {p.wastewater_pct:g}% '
                  f'({_first_doc(w.get("legal_basis", ""))})')
    return price


def narrative_vi(result, line):
    """The method sentence of an Existing-project EEE.C / EEW.C remark (no curve, no floor)."""
    lr = result.lines[line]
    unit = lr.unit
    what = 'Lượng điện tiêu thụ' if lr.utility == ut.ELECTRICITY else 'Lượng nước tiêu thụ'
    text = (f'{LINE_NAME_VI[line]} = {what.lower()} {lr.q_budget:,.0f} {unit}/tháng x {_price_clause(lr)} '
            f'x 12 tháng.')
    if lr.basis == 'actual':
        text += (f' {what} lấy theo thực chi bình quân {len(lr.months)} tháng '
                 f'({_used_range(lr.months)}) của dự án.')
    else:
        text += (f' Dự án chưa đủ số liệu thực chi nên {what.lower()} suy ra từ số NS {result.prior_year} đã duyệt '
                 f'({lr.approved:,.0f} VND/năm).')
    if abs(lr.q_budget - lr.q_bar) >= 0.5:
        pm = next((r for r in lr.reasons if r['source'] == es.SOURCE_PM), {})
        text += (f' Năm {result.budget_year} {what.lower()} được điều chỉnh từ {lr.q_bar:,.0f} lên '
                 if lr.q_budget > lr.q_bar else
                 f' Năm {result.budget_year} {what.lower()} được điều chỉnh từ {lr.q_bar:,.0f} xuống ')
        text += f'{lr.q_budget:,.0f} {unit}/tháng ({pm.get("text", "")}).'
    if result.incl_vat:
        p = lr.budget_prices[0]
        v = p.rows.get('vat_pct') or {}
        vat = f'VAT {p.vat_pct:g}%'
        if lr.utility == ut.WATER and p.wastewater_pct:
            vat = f'VAT nước sạch {p.vat_pct:g}%, VAT dịch vụ thoát nước {p.wastewater_vat_pct:g}%'
        text += f' Đơn giá cộng {vat} năm {result.budget_year} ({_first_doc(v.get("legal_basis", ""))}).'
    if lr.note:
        text += ' ' + lr.note
    return text


def adjustment_sentence(result, line):
    """' Điều chỉnh so với NS <năm>: …' for EEE.C / EEW.C (spec deliverable-remarks): amounts, difference,
    causes and flags. Without an approved amount it states the basis without a difference."""
    lr = result.lines[line]
    texts = [r['text'] for r in lr.reasons if r['text']]
    flags = ('; lưu ý: ' + '; '.join(lr.flags)) if lr.flags else ''
    if lr.approved_on_basis is None:
        return (f' Điều chỉnh so với NS {result.prior_year}: không có số NS đã duyệt để so sánh; cơ sở: '
                f'{"; ".join(texts)}{flags}.')
    diff = lr.annual - lr.approved_on_basis
    approved = f'{lr.approved_on_basis:,.0f}'
    if lr.approved_incl_vat != result.incl_vat:
        # The client knows the approved amount as it was approved: quote it on its own VAT basis first, then
        # the equivalent on the deliverable's basis that the difference is measured from (7.2 back-test).
        approved = (f'NS đã duyệt {lr.approved:,.0f} VND/năm ({"gồm" if lr.approved_incl_vat else "chưa gồm"} VAT), '
                    f'tương đương {lr.approved_on_basis:,.0f} VND/năm {"gồm" if result.incl_vat else "chưa gồm"} VAT')
    return (f' Điều chỉnh so với NS {result.prior_year}: {approved} → {lr.annual:,.0f} VND/năm '
            f'({diff:+,.0f} VND); nguyên nhân: {"; ".join(texts)}{flags}.')


def summary_lines(result):
    """Plain-text lines for run.py's printed summary: each line's figure, basis and flags."""
    out = []
    for line in LINES:
        lr = result.lines[line]
        out.append(f'{line}: {lr.annual:,.0f} VND/year ({lr.basis}, {lr.q_budget:,.0f} {lr.unit}/month)')
        out.extend(f'  FLAG {f}' for f in lr.flags)
    return out
