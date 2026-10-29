"""
Measure columns of an approved budget workbook of year N (change add-review-prior-and-actual-columns): the columns the
form carries beside the year column, of year N-1 because a budget of year N is written during N-1:
- 'n1'       Duyệt N-1          "Approved budget of Year …", "Ngân sách phê duyệt"
- 'actual'   Thực tế lũy kế N-1 "Total Actual From … to …", "Thực tế", "Lũy kế"
- 'expected' Dự kiến cả năm N-1 "Expected Report Year …", "Báo cáo dự kiến"

The header, period and flag rules are those of the real-budget scan store (scan_budgets_v2.classify / parse_period,
build_final_v2 flags and primary column), copied here because the scan lives outside the repository. Plain functions
on text and numbers; review_import reads the sheets and calls them.
"""
import re
import unicodedata

# ---------------------------------------------------------------- header classification (scan_budgets_v2)
HEAD_LABELS = re.compile(r'(budget year:?\s*(/\s*)?dự toán của năm:?|starting month:?\s*(/\s*)?tháng bắt đầu:?|ending month:?\s*(/\s*)?'
                         r'tháng kết thúc:?|report year:?\s*(/\s*)?báo cáo của năm:?|project name:?\s*(/\s*)?tên dự án:?)', re.I)
ACT_NOT = re.compile(r'dự kiến thực hiện|số lần thực hiện|thực hiện từng tháng|thực hiện hoặc giá trị phát sinh|check số|đánh tháng|đánh số', re.I)

MEASURES = ('actual', 'expected_rest', 'expected_year', 'approved_prior')
KIND_OF_MEASURE = {'approved_prior': 'n1', 'actual': 'actual', 'expected_year': 'expected'}
KINDS = ('n1', 'actual', 'expected')
KIND_VI = {'n1': 'Duyệt', 'actual': 'Thực tế', 'expected': 'Dự kiến'}


def nfc(s):
    return unicodedata.normalize('NFC', s) if isinstance(s, str) else s


def clean_header(h):
    """The header with the form's head labels removed and spaces collapsed (as the store records it)."""
    return re.sub(r'\s+', ' ', HEAD_LABELS.sub(' ', nfc(h or ''))).strip()


def classify(h):
    """Class of a column from its own header text (head labels removed)."""
    t = HEAD_LABELS.sub(' ', nfc(h or '').lower())
    t = re.sub(r'\s+', ' ', t).strip()
    if not t:
        return 'empty'
    if re.search(r'chênh lệch|variance|%\s*increase|tăng\s*/\s*giảm|so với', t):
        return 'variance'
    if re.search(r'tham khảo|reference', t):
        return 'reference'
    if re.search(r'approved budget|ngân sách phê duyệt|ngân sách được duyệt', t):
        return 'approved_prior'
    if re.search(r'estimate budget|total budget|budget of year|ngân sách năm|dự toán', t):
        return 'budget'
    if re.search(r'total expected from|dự ước (doanh thu|từ|t\s*\d)', t):
        return 'expected_rest'
    if re.search(r'expected report year|báo cáo dự kiến|dự ước', t):
        return 'expected_year'
    if re.search(r'total actual|\bactual\b|thực tế|lũy kế|luỹ kế|\bytd\b|thực chi|thực hiện', t) and not ACT_NOT.search(t):
        return 'actual'
    if re.search(r'average month|trung bình', t):
        return 'average'
    return 'other'


# ---------------------------------------------------------------- periods (scan_budgets_v2)
def ym(t):
    return t[0] * 12 + t[1] - 1


def months_between(a, b):
    return ym(b) - ym(a) + 1


def add_months(t, k):
    n = ym(t) + k
    return (n // 12, n % 12 + 1)


def month_list(a, b):
    return [add_months(a, k) for k in range(months_between(a, b))]


def year_most_months(a, b):
    cnt = {}
    for y, _ in month_list(a, b):
        cnt[y] = cnt.get(y, 0) + 1
    best = max(cnt.values())
    return max(y for y, n in cnt.items() if n == best)            # tie -> later year


RANGE_RX = re.compile(r'(?:from|từ)?\s*(?:t|tháng)?\s*(\d{1,2})\s*(?:[/.]\s*(20[1-4]\d))?\s*(?:to|đến|-|–)\s*(?:t|tháng)?\s*(\d{1,2})\s*[/.]\s*(20[1-4]\d)', re.I)
FROM_RX = re.compile(r'(?:from|từ)\s*(?:t|tháng)?\s*(\d{1,2})\s*[/.]\s*(20[1-4]\d)', re.I)
MONTH_RX = re.compile(r'(?:tháng|month|t)\s*(\d{1,2})\s*[/.]\s*(20[1-4]\d)', re.I)
MONTH_ONLY_RX = re.compile(r'(?:tháng|month)\s*(\d{1,2})(?!\s*[/.\d])', re.I)
ACTUAL_N_RX = re.compile(r'\bactual\s+(\d{1,2})\b(?!\s*[/.\d])', re.I)
BARE_MONTH_RX = re.compile(r'(?<![\d/.])(\d{1,2})\s*[./]\s*(20[1-4]\d)(?!\d)')
YEAR_RX = re.compile(r'(?<!\d)(20[1-4]\d)(?!\d)')


def parse_period(text, group, sheet_year, measure=None):
    """((y, m) first, (y, m) last, how) of a measure column from its own header, its month-group label and the
    sheet's year; (None, None, 'unknown') when nothing gives a period. `measure` (the column's class) lets an
    approved / expected column keep its header year over a month written in another style, and an actual column its
    header month over the group label. The scan store imports this function (scan_budgets_v2)."""
    t = nfc(text or '')
    m = RANGE_RX.search(t)
    if m:
        m1, y1, m2, y2 = int(m.group(1)), m.group(2), int(m.group(3)), int(m.group(4))
        y1 = int(y1) if y1 else y2
        if 1 <= m1 <= 12 and 1 <= m2 <= 12 and (y2, m2) >= (y1, m1):
            # "Year 2025 (From 01.2023 to 12.2023)": a whole-year range of another year is the older template's
            # text; the year the PM wrote wins (approved / expected only; change fix-review-reading-gaps)
            stated = {int(y) for y in YEAR_RX.findall(t[:m.start()] + ' ' + t[m.end():])}
            if (measure in ('approved_prior', 'expected_year') and (m1, m2) == (1, 12) and y1 == y2
                    and len(stated) == 1 and y2 not in stated):
                y = stated.pop()
                return (y, 1), (y, 12), 'header_year_over_range'
            return (y1, m1), (y2, m2), 'header_range'
    m = FROM_RX.search(t)
    if m and 1 <= int(m.group(1)) <= 12:
        a = (int(m.group(2)), int(m.group(1)))
        return a, (a[0], 12), 'header_from_to_year_end'
    m = MONTH_RX.search(t)
    if m and 1 <= int(m.group(1)) <= 12:
        a = (int(m.group(2)), int(m.group(1)))
        return a, a, 'header_month'
    # a year in the column's own header wins over the month-group label: the label can pick up the sheet's Starting
    # Month cell ("Expected Report Year 2025" under a 01/2026 head cell). An approved / expected column is a whole year
    # even when its header also writes months the range pattern misses ("From 01,2024 to 12.2024"). Two years: the last.
    ys = YEAR_RX.findall(t)
    month_in_header = MONTH_ONLY_RX.search(t) or ACTUAL_N_RX.search(t) or BARE_MONTH_RX.search(t)
    if ys and (measure in ('approved_prior', 'expected_year') or not month_in_header):
        y = int(ys[-1])
        return (y, 1), (y, 12), 'header_year'
    # an actual column's own month ("01/2025 Actual") before the group label
    m = BARE_MONTH_RX.search(t) if measure == 'actual' else None
    if m and 1 <= int(m.group(1)) <= 12:
        a = (int(m.group(2)), int(m.group(1)))
        return a, a, 'header_month_bare'
    m = MONTH_RX.search(group or '')
    if m and 1 <= int(m.group(1)) <= 12:
        a = (int(m.group(2)), int(m.group(1)))
        return a, a, 'group_month'
    m = MONTH_ONLY_RX.search(t) or ACTUAL_N_RX.search(t)
    if m and sheet_year and 1 <= int(m.group(1)) <= 12:
        a = (sheet_year, int(m.group(1)))
        return a, a, 'header_month_sheet_year'
    m = BARE_MONTH_RX.search(t)
    if m and 1 <= int(m.group(1)) <= 12:
        a = (int(m.group(2)), int(m.group(1)))
        return a, a, 'header_month_bare'
    ys = YEAR_RX.findall(t)
    if ys:
        y = int(ys[-1])
        return (y, 1), (y, 12), 'header_year'
    return None, None, 'unknown'


def infer_cumulative(cols):
    """A cumulative actual without a period ("lũy kế") ends the month before the same sheet's "expected from" column
    starts (scan_budgets_v2). `cols`: the candidate dicts of one sheet; changed in place."""
    exp_from = [c for c in cols if c['measure'] == 'expected_rest' and c['start']]
    for c in cols:
        if c['measure'] == 'actual' and c['how'] == 'unknown' and exp_from:
            y, mo = exp_from[0]['start']
            if mo > 1:
                c.update(start=(y, 1), end=(y, mo - 1), how='inferred_from_expected')


# ---------------------------------------------------------------- flags and choice (build_final_v2)
FLAG_VI = {'chua_dien': 'cột trống', 'mau_AAA': 'cột mẫu AAA', 'du_an_khac': 'cột của dự án khác hoặc tham khảo',
           'mau_ky_sau_ngay_luu_file': 'kỳ thực tế kết thúc sau ngày lưu file', 'khong_ro_ky': 'không rõ kỳ'}


def flags_of(col, own_name='', other_names=(), saved_month=None):
    """The store's flags of one candidate column (empty list = usable). `col`: dict with measure, header, start, end,
    n_nonzero. `other_names`: upper-case project names of the store, when known."""
    h = nfc(col['header'] or '').upper()
    flags = []
    if not col['n_nonzero']:
        flags.append('chua_dien')
    if re.search(r'\bAAA\b', h):
        flags.append('mau_AAA')
    own = nfc(own_name or '').strip().upper()
    # a store "name" without a letter (e.g. "2023" from a file named 2023.pdf) would match every header of that year
    other = [n for n in other_names if n and re.search(r'[^\W\d_]', n) and n != own and n in h
             and not (own and (n in own or own in n))]
    if other or re.search(r'tham khảo', col['header'] or '', re.I):
        flags.append('du_an_khac')
    if col['measure'] == 'actual' and col['start'] and saved_month and col['end'] > saved_month:
        flags.append('mau_ky_sau_ngay_luu_file')
    if not col['start']:
        flags.append('khong_ro_ky')
    return flags


def year_ok(col, budget_year):
    """All three kinds are of year N-1: the approved and the expected column by the year with most of their months,
    the actual by the year its period ends."""
    target = budget_year - 1
    if col['measure'] == 'actual':
        return col['end'][0] == target
    return year_most_months(col['start'], col['end']) == target


def choose(cands):
    """The column of one kind: one that ties, then the longest period (a cumulative actual before a one-month
    column), then one on a report sheet, a visible one, the one with more figures."""
    return max(cands, key=lambda c: (c['tie_ok'], months_between(c['start'], c['end']),
                                     c['sheet_kind'] == 'report', c['sheet_state'] == 'visible', c['n_nonzero']))


def period_text(col):
    a, b = col['start'], col['end']
    if col['measure'] == 'actual':
        return f'{a[1]:02d}–{b[1]:02d}/{b[0]}' if a[0] == b[0] else f'{a[1]:02d}/{a[0]}–{b[1]:02d}/{b[0]}'
    return str(year_most_months(a, b))
