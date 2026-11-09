"""
How often a budget line is paid in the year, and in which months (change add-line-frequency, spec line-frequency).

The 2027 form carries one frequency per fund row in column C: Monthly, Quarterly, Half a Year, Yearly, Optional or
Schedule. This module holds the rules every writer shares (generation, sheet 4, the web):

- the number of times a year of each frequency (the form's column E);
- the months of payment of a cyclic frequency: a first month inside the budget period, then every 3, 6 or 12 months,
  counted as T1..T12 of the period (T1 = the period's first month);
- the default frequency of a code in a new budget, read from data/generation_B_verified/Ref_LineFrequency.csv;
- the Vietnamese sentence the remark carries for a frequency other than Monthly.
"""
import csv
import os
import re
from collections import namedtuple

from openpyxl.utils import column_index_from_string

HERE = os.path.dirname(os.path.abspath(__file__))
TABLE_PATH = os.path.join(HERE, '..', 'data', 'generation_B_verified', 'Ref_LineFrequency.csv')

MONTHLY, QUARTERLY, HALF, YEARLY, OPTIONAL, SCHEDULE = (
    'Monthly', 'Quarterly', 'Half a Year', 'Yearly', 'Optional', 'Schedule')
FREQUENCIES = (MONTHLY, QUARTERLY, HALF, YEARLY, OPTIONAL, SCHEDULE)
CYCLIC = (QUARTERLY, HALF, YEARLY)

TIMES = {MONTHLY: 12, QUARTERLY: 4, HALF: 2, YEARLY: 1, SCHEDULE: 12}
STEP = {QUARTERLY: 3, HALF: 6, YEARLY: 12}

# Vietnamese label shown beside the form's own name on the web and on sheet 4.
LABEL_VI = {MONTHLY: 'Hàng tháng', QUARTERLY: 'Hàng quý', HALF: '6 tháng/lần', YEARLY: 'Hàng năm',
            OPTIONAL: 'Không theo chu kỳ', SCHEDULE: 'Theo lịch từng tháng'}

# Lead of the remark sentence (design D8); Optional's lead is "<n> lần/năm,".
LEAD_VI = {QUARTERLY: 'Hàng quý', HALF: '6 tháng/lần', YEARLY: 'Hàng năm', SCHEDULE: 'Chi theo lịch từng tháng'}

Default = namedtuple('Default', 'code frequency times first_month months source note')


def normalise(value):
    """The form's name of a frequency, or None for a blank. The form's own formula writes "Half a year" in lower case;
    any case and surrounding spaces are accepted. Raises ValueError for a value not on the form's list."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    for name in FREQUENCIES:
        if text.lower() == name.lower():
            return name
    raise ValueError(f'Tần suất "{text}" không có trong danh sách của mẫu')


def first_month_error(frequency, first_month):
    """The refusal message for a first month outside the frequency's range, or None when it is allowed."""
    frequency = normalise(frequency)
    if frequency not in CYCLIC:
        return None
    step = STEP[frequency]
    if isinstance(first_month, int) and 1 <= first_month <= step:
        return None
    label = LABEL_VI[frequency]
    if step == 3:
        return f'Tháng đầu của {label} phải là T1, T2 hoặc T3'
    return f'Tháng đầu của {label} phải từ T1 đến T{step}'


def months(frequency, first_month=1, optional_months=None):
    """The months of payment as T-numbers (1..12) of the budget period.

    Monthly and Schedule return all twelve months; a cyclic frequency returns the first month and every 3, 6 or 12
    months after it; Optional returns the ticked months, sorted."""
    frequency = normalise(frequency)
    if frequency in (MONTHLY, SCHEDULE):
        return list(range(1, 13))
    if frequency == OPTIONAL:
        picked = sorted({int(m) for m in (optional_months or [])})
        bad = [m for m in picked if not 1 <= m <= 12]
        if bad:
            raise ValueError(f'Tháng ngoài kỳ ngân sách: {bad}')
        if not 1 <= len(picked) <= 11:
            raise ValueError('Không theo chu kỳ phải chọn từ 1 đến 11 tháng (chọn Hàng tháng khi chi đủ 12 tháng)')
        return picked
    if frequency in CYCLIC:
        first = 1 if first_month in (None, '') else int(first_month)
        error = first_month_error(frequency, first)
        if error:
            raise ValueError(error)
        return list(range(first, 13, STEP[frequency]))
    raise ValueError('Chưa có tần suất')


def times(frequency, optional_times=None):
    """Times a year, as the form's column E computes it (Optional = column D)."""
    frequency = normalise(frequency)
    if frequency == OPTIONAL:
        n = int(optional_times or 0)
        if not 1 <= n <= 11:
            raise ValueError('Số lần của Không theo chu kỳ phải từ 1 đến 11')
        return n
    if frequency is None:
        raise ValueError('Chưa có tần suất')
    return TIMES[frequency]


def _vnd(amount):
    return f'{amount:,.0f}'


def sentence(frequency, price_per_time=None, month_list=None):
    """The remark sentence for a frequency other than Monthly; None for Monthly or a blank frequency.

    month_list is the T-numbers of the payment months (for Schedule, the months that carry an amount)."""
    frequency = normalise(frequency)
    if frequency in (None, MONTHLY):
        return None
    month_list = sorted(month_list or [])
    when = ', '.join(f'T{m}' for m in month_list)
    if frequency == SCHEDULE:
        return f'{LEAD_VI[SCHEDULE]}: {when}' if when else LEAD_VI[SCHEDULE]
    n = len(month_list)
    price = f'{_vnd(price_per_time or 0)} VND/lần'
    if frequency == OPTIONAL:
        return f'{n} lần/năm, {price}, chi vào {when}'
    return f'{LEAD_VI[frequency]}, {n} lần/năm × {price}, chi vào {when}'


def is_sentence(text):
    """True when a remark sentence is one this module writes (used to replace it rather than append a second)."""
    text = (text or '').strip()
    if not text:
        return False
    if any(text.startswith(lead) for lead in LEAD_VI.values()):
        return True
    head, _, rest = text.partition(' lần/năm, ')
    return head.isdigit() and 'VND/lần' in rest


def with_sentence(remark, text):
    """The remark with its frequency sentence replaced (design D8): a last line written by `sentence` is dropped,
    then `text` (None for Monthly) becomes the new last line. The PM's own lines are kept."""
    lines = (remark or '').rstrip().split('\n')
    if lines and is_sentence(lines[-1]):
        lines.pop()
    body = '\n'.join(lines).rstrip()
    if not text:
        return body
    return f'{body}\n{text}' if body else text


def first_in_use(frequency, first_month, original_first=1):
    """The first month a cyclic line uses, as sheet 4 computes it (column AW): the one typed, else the original first
    month while the frequency allows it, else T1."""
    if first_month not in (None, ''):
        return int(first_month)
    step = STEP.get(normalise(frequency), 1)
    return original_first if original_first and original_first <= step else 1


_HEADER_REF = re.compile(r'^=\$?([A-Z]{1,2})\$?8$')
FIRST_MONTH_COL = 8   # H; H..S = "Lần 1..12" on both fund sheets


def payment_months(ws, r):
    """The months of payment (T-numbers 1..12) of a cyclic or Optional fund row: each filled H:S cell refers to a
    row-8 month header (for example '=K8' = T4), wherever in H:S it sits. None when a filled cell is anything else."""
    paid = set()
    for c in range(FIRST_MONTH_COL, FIRST_MONTH_COL + 12):
        v = ws.cell(row=r, column=c).value
        if v in (None, ''):
            continue
        m = _HEADER_REF.match(v) if isinstance(v, str) else None
        if not m:
            return None
        col = column_index_from_string(m.group(1))
        if not FIRST_MONTH_COL <= col < FIRST_MONTH_COL + 12:
            return None
        paid.add(col - FIRST_MONTH_COL + 1)
    return paid


def load_table(path=None):
    """The default frequency of each listed code: {code: Default}. A code not listed is Monthly (or Schedule when the
    tool writes 12 month amounts). Lines starting with '#' are comments."""
    path = path or TABLE_PATH
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8-sig', newline='') as fh:
        rows = [line for line in fh if not line.startswith('#')]
    table = {}
    for r in csv.DictReader(rows):
        code = (r.get('code') or '').strip()
        if not code:
            continue
        freq = normalise(r.get('frequency'))
        if freq is None:
            raise ValueError(f'{code}: no frequency in the default table')
        first =(r.get('first_month') or '').strip()
        first = int(first) if first else 1
        n = int((r.get('times') or '').strip() or TIMES.get(str(freq), 0))
        if freq == OPTIONAL:
            raise ValueError(f'{code}: the default table does not take Optional (its months are not a rule)')
        if freq in CYCLIC and n != TIMES[freq]:
            raise ValueError(f'{code}: {freq} is {TIMES[freq]} times a year, the table says {n}')
        table[code] = Default(code, freq, n, first, months(freq, first), (r.get('source') or '').strip(),
                              (r.get('note') or '').strip())
    return table
