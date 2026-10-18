"""The contingency lines EM#, ES# and EE# (change apply-head-of-pm-decisions-2026-10, group 6, design D9).

Each month of a contingency line is a live formula over its group's leaf lines on the same sheet:
`=ROUND(rate*(SUBTOTAL(9,<first leaf>:<row above>)-<excluded leaves>),0)`, read from the template's month-
allocation columns (AQ:BB on '2. Budget-Management Fund', AL:AW on '2.2 Common area Fund'), not from H:S,
because a Monthly line holds its amount in F only. SUBTOTAL skips the sub-group total rows inside the
range, so every leaf counts once, and the range stops above the contingency row, so the line is never part
of its own base.

The rate is the Project Info field LABEL: blank (or a form without the field) means 2%, 0 leaves all six
lines at 0 with a reason, and text, a negative rate or a rate above 10% stop the run.
"""
import re

from openpyxl.utils import get_column_letter

LABEL = 'Contingency Rate (EM#, ES#, EE#)'
DEFAULT_RATE = 0.02
MAX_RATE = 0.10
# The reason all six lines carry at a rate of 0 (approved 2026-10-18); '2.2' copies it from '2. Fund'.
ZERO_REASON_VI = "ô 'Contingency Rate' trên Project Info là 0%."

FUND_SHEET = '2. Budget-Management Fund'
COMMON_SHEET = '2.2 Common area Fund'

# contingency code -> (its group's total-row code, the leaves always left out of the base)
GROUPS = (
    ('EM#', 'EM', ('EMH1',)),            # Savills' own fee
    ('ES#', 'ES', ()),
    ('EE#', 'EE', ('EEW.A', 'EEE.A')),   # residents' own water and electricity, collected on their behalf
)
# Why each exclusion is left out, as the remark says it.
_EXCLUDED_VI = {
    'EMH1': 'EMH1 (phí quản lý của Savills)',
    'EEW.A': 'EEW.A (nước dùng riêng của cư dân)',
    'EEE.A': 'EEE.A (điện dùng riêng của cư dân)',
}
# The month-allocation column each sheet reads month 1 from (months 2-12 follow it).
MONTH_BASE_COL = {FUND_SHEET: 43, COMMON_SHEET: 38}          # AQ, AL
# The layout the rules were approved on (2026-10-18): code -> (first leaf row, contingency row). Checked on
# every run so a reshaped template stops the run instead of pricing the wrong rows.
EXPECTED_LAYOUT = {
    FUND_SHEET: {'EM#': (82, 131), 'ES#': (134, 221), 'EE#': (229, 262)},
    COMMON_SHEET: {'EM#': (43, 92), 'ES#': (95, 182), 'EE#': (190, 223)},
}

_CODE_COL = 25     # Y
_NAME_COL = 26     # Z
_SUBTOTAL_G = re.compile(r'^=SUBTOTAL\(9,G(\d+):G(\d+)\)$')


class ContingencyRateError(ValueError):
    """The Project Info contingency rate is not a usable rate."""


def resolve_rate(raw):
    """(rate, is_default) from the Project Info cell. Blank -> (0.02, True). A percent-formatted cell reads
    back as a fraction (2% -> 0.02). Text, a negative rate or a rate above 10% raise ContingencyRateError
    naming the field."""
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return DEFAULT_RATE, True
    try:
        if isinstance(raw, bool):
            raise ValueError
        rate = float(raw)
    except (TypeError, ValueError):
        raise ContingencyRateError(
            f"Project Info '{LABEL}' is {raw!r}, which is not a rate. Enter a percentage from 0% to 10%, or clear "
            f"the cell to use 2%.") from None
    if rate < 0 or rate > MAX_RATE + 1e-12:
        raise ContingencyRateError(
            f"Project Info '{LABEL}' is {raw!r} ({rate:.2%}). It must be from 0% to 10%. Enter a valid "
            f"percentage, or clear the cell to use 2%.")
    return rate, False


def rate_literal(rate):
    """The rate as it is written into a formula: '0.02', never a float repr like '0.020000000000000004'."""
    return f'{rate:.10g}'


def rate_vi(rate):
    """'2%', '1,5%' — the Vietnamese decimal comma."""
    return f'{rate * 100:.10g}%'.replace('.', ',')


def _code_rows(ws):
    rows = {}
    for r in range(1, (ws.max_row or 1) + 1):
        c = ws.cell(row=r, column=_CODE_COL).value
        if isinstance(c, str) and c.strip():
            rows.setdefault(c.strip(), r)
    return rows


def _is_subtotal(ws, row):
    g = ws.cell(row=row, column=7).value
    return isinstance(g, str) and 'SUBTOTAL' in g.upper()


def _vi_name(text):
    """The Vietnamese half of a bilingual 'English/ Tiếng Việt' label."""
    s = str(text or '').replace('\r', '').replace('\n', ' ')
    return s.split('/')[-1].strip() if '/' in s else s.strip()


def layout(ws, sheet, extra_exclusions=()):
    """One dict per contingency line: code, row, first and last leaf rows, the excluded leaves
    ([(code, row)]), and the group's Vietnamese name. The base range comes from the group total row's own
    `=SUBTOTAL(9,G<a>:G<b>)` and must end on the contingency row; the result must match EXPECTED_LAYOUT.
    `extra_exclusions` are further codes left out of whichever group's range holds them (the expense lines
    the catalogue pairs as collect-on-behalf). Raises ValueError on any mismatch."""
    rows = _code_rows(ws)
    out = []
    for code, group, fixed in GROUPS:
        if code not in rows or group not in rows:
            raise ValueError(f"'{sheet}' has no row for {code if code not in rows else group} (column Y).")
        row, head = rows[code], rows[group]
        m = _SUBTOTAL_G.match(str(ws.cell(row=head, column=7).value or '').replace(' ', ''))
        if not m:
            raise ValueError(f"'{sheet}'!G{head} ({group}) is not the template's =SUBTOTAL(9,G..:G..) group total.")
        start, end = int(m.group(1)), int(m.group(2))
        if end != row:
            raise ValueError(f"'{sheet}' {group} total ends on row {end}, not on its contingency row {row} ({code}).")
        first = next((r for r in range(start, row) if not _is_subtotal(ws, r)), None)
        if (first, row) != EXPECTED_LAYOUT[sheet][code]:
            raise ValueError(
                f"'{sheet}' {code}: leaves start on row {first} and the line sits on row {row}, but the approved "
                f"layout is {EXPECTED_LAYOUT[sheet][code]}. Re-check the template before changing EXPECTED_LAYOUT.")
        last = row - 1
        excluded = []
        for x in fixed:
            if x not in rows or not first <= rows[x] <= last:
                raise ValueError(f"'{sheet}' {code}: excluded line {x} is not among rows {first}-{last}.")
            excluded.append((x, rows[x]))
        for x in sorted(set(extra_exclusions) - set(fixed)):
            if x in rows and first <= rows[x] <= last:
                excluded.append((x, rows[x]))
        out.append(dict(code=code, row=row, first=first, last=last, excluded=excluded,
                        group_vi=_vi_name(ws.cell(row=head, column=_NAME_COL).value)))
    return out


def month_formulas(sheet, line, rate):
    """The twelve H:S formulas of one contingency line."""
    lit = rate_literal(rate)
    formulas = []
    for i in range(12):
        col = get_column_letter(MONTH_BASE_COL[sheet] + i)
        minus = ''.join(f'-{col}{r}' for _c, r in line['excluded'])
        formulas.append(f"=ROUND({lit}*(SUBTOTAL(9,{col}{line['first']}:{col}{line['last']}){minus}),0)")
    return formulas


def _excluded_phrase(line):
    codes = [c for c, _r in line['excluded']]
    if not codes:
        return ''
    return ', không tính ' + ', '.join(_EXCLUDED_VI.get(c, c) for c in codes)


def _rate_source(rate, is_default):
    if is_default:
        return f"Tỷ lệ {rate_vi(rate)} là mức mặc định; PM sửa được tại ô '{LABEL}' trên Project Info."
    return f"Tỷ lệ {rate_vi(rate)} theo ô '{LABEL}' trên Project Info."


def remark_vi(line, rate, is_default):
    """The line's own remark: the rate, the base, the exclusions, and that the formula recalculates."""
    return (f"Dự phòng = {rate_vi(rate)} x tổng các dòng chi phí của nhóm '{line['group_vi']}' trong từng "
            f"tháng{_excluded_phrase(line)}. {_rate_source(rate, is_default)} Công thức tự tính lại khi các dòng "
            f"trong nhóm thay đổi.")


def summary_item_vi(line, rate):
    """The contingency item of a '1. Summary' narrative (K25, K35, K42)."""
    if not rate:
        return f"Dự phòng: để ở mức 0, {ZERO_REASON_VI}"
    return (f"Dự phòng: {rate_vi(rate)} x tổng chi phí nhóm '{line['group_vi']}' trong từng tháng"
            f"{_excluded_phrase(line)}; công thức tự tính lại.")
