"""
Office-only: build data/generation_B_verified/Ref_LineFrequency.csv, the default frequency of each code in a new
budget (change add-line-frequency, task 1.1, design D6).

    python build_line_frequency.py [--template <xlsx>] [--out <csv>] [--dry-run]

Two sources, each row stating its own:
- the 2027 form's own column C on both fund sheets (values other than Monthly; Schedule is left out, the tool
  writes 12 month amounts there anyway);
- the counts a year the costing code already prices with (the constants named in the row's source).

First month rule (user's choice 2026-11-07): every cyclic line starts in T1, as the form's own rows do, and repeats
every 3, 6 or 12 months. The user reviews the table before it is used (task 1.2).
"""
import argparse
import csv
import os
import sys

import openpyxl
from openpyxl.utils import column_index_from_string

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import line_frequency as lf  # noqa: E402

TEMPLATE = os.path.join(HERE, '..', '..', 'input', 'template', '2027 Resi Budget Form (IT team).xlsx')
FUND_SHEETS = ('2. Budget-Management Fund', '2.2 Common area Fund')
CODE_COL, FREQ_COL, MONTH_FIRST_COL = 25, 3, 8
FIRST_MONTH = 1
FIELDS = ['code', 'frequency', 'times', 'first_month', 'source', 'note']

# Counts a year the costing code prices with (generate_project_budget.py). The constant or remark is named so a
# reader can check the row against the code.
COSTING = [
    ('ESM2', lf.HALF, 'costing: ENV_REPORT_ANNUAL, remark "6 tháng/lần theo Nghị định 40/2019/NĐ-CP Điều 47"',
     'Báo cáo quan trắc môi trường định kỳ, 2 lần/năm.'),
    ('ESM3', lf.HALF, 'costing: water_test_annual = WATER_TEST_SAMPLE_PRICE x WATER_TEST_SAMPLES_PER_ROUND x 2 đợt/năm',
     'Kiểm nghiệm nước sinh hoạt, 2 đợt/năm.'),
    ('ESM5', lf.QUARTERLY, 'costing: POOL_TEST_SAMPLES_PER_YEAR = 8 (4 đợt/năm x 2 mẫu/đợt)',
     'Kiểm nghiệm nước hồ bơi, 4 đợt/năm; chỉ ghi khi dự án có hồ bơi.'),
    ('ESC12', lf.YEARLY, 'costing: ENV_INCIDENT_PLAN_ANNUAL, remark "một lần/năm"',
     'Kế hoạch ứng phó sự cố môi trường, 1 lần/năm.'),
    ('ESM25', lf.QUARTERLY, 'costing: WASTEWATER_CROSSCHECK_PER_YEAR = 4 (hàng quý)',
     'Đối chiếu chất lượng nước sau xử lý, hàng quý.'),
]
# Template rows the table states on purpose, with the reason.
NOTES = {
    'RO2a': 'Mẫu để Half a Year nhưng chỉ ghi 1 tháng chi (T4), nên ô kiểm số lần (U) của mẫu lệch 1; bảng ghi đủ '
            '2 tháng T1, T7. Công cụ để dòng này 0 (dự án chưa có tài khoản), số tiền không đổi.',
}


def _month_of(formula, header_row=8):
    """T-number of a month cell written as a reference to the row-8 month header (for example '=K8' -> 4)."""
    if not (isinstance(formula, str) and formula.startswith('=') and formula.endswith(str(header_row))):
        return None
    col = column_index_from_string(formula[1:-len(str(header_row))].replace('$', ''))
    return col - MONTH_FIRST_COL + 1


def template_rows(path):
    wb = openpyxl.load_workbook(path, data_only=False)
    rows = {}
    for name in FUND_SHEETS:
        ws = wb[name]
        for r in range(1, ws.max_row + 1):
            code = ws.cell(r, CODE_COL).value
            if not isinstance(code, str) or not code.strip():
                continue
            try:
                freq = lf.normalise(ws.cell(r, FREQ_COL).value)
            except ValueError:
                continue
            if freq in (None, lf.MONTHLY, lf.SCHEDULE):
                continue
            filled = [_month_of(ws.cell(r, MONTH_FIRST_COL + k).value) for k in range(12)]
            filled = [m for m in filled if m]
            rows[code.strip()] = dict(frequency=freq, sheet=name, row=r, months=filled)
    return rows


def build(template_path):
    tpl = template_rows(template_path)
    out = []
    costing = {code: (freq, source, note) for code, freq, source, note in COSTING}
    for code in sorted(set(tpl) | set(costing)):
        t = tpl.get(code)
        c = costing.get(code)
        freq = c[0] if c else (t or {})['frequency']
        sources, notes = [], []
        if t:
            months_text = ', '.join(f'T{m}' for m in t['months']) or 'không ghi tháng'
            sources.append(f"template: '{t['sheet']}' row {t['row']} C = {t['frequency']} ({months_text})")
            if t['frequency'] != freq:
                notes.append(f"Mẫu để {t['frequency']}, bảng dùng {freq}.")
        if c:
            sources.append(c[1])
            notes.append(c[2])
        if code in NOTES:
            notes.append(NOTES[code])
        expected = lf.months(freq, FIRST_MONTH)
        if t and t['months'] and t['months'] != expected and code not in NOTES:
            notes.append(f"Mẫu ghi tháng {', '.join(f'T{m}' for m in t['months'])}; bảng theo quy tắc tháng đầu T1.")
        out.append(dict(code=code, frequency=freq, times=lf.TIMES[freq], first_month=FIRST_MONTH,
                        source='; '.join(sources), note=' '.join(notes)))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--template', default=TEMPLATE)
    ap.add_argument('--out', default=lf.TABLE_PATH)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args(argv)
    rows = build(args.template)
    for r in rows:
        months = ', '.join(f'T{m}' for m in lf.months(r['frequency'], r['first_month']))
        print(f"{r['code']:6} {r['frequency']:12} {r['times']:>2} lần  {months:18} | {r['source']}")
    if args.dry_run:
        return 0
    with open(args.out, 'w', encoding='utf-8-sig', newline='') as fh:
        fh.write('# Default frequency per code for a new budget (change add-line-frequency). Built by '
                 'build_line_frequency.py; reviewed by the user before use. A code not listed is Monthly.\n')
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f'{len(rows)} rows -> {os.path.abspath(args.out)}')
    lf.load_table(args.out)  # the reader accepts what was written
    return 0


if __name__ == '__main__':
    sys.exit(main())
