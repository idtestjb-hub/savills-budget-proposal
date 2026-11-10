"""
Office-only: build data/generation_B_verified/Ref_LineFrequency.csv, the default frequency of each code in a new
budget (change default-frequency-from-real-budgets, spec line-frequency; earlier change add-line-frequency).

    python build_line_frequency.py --workdir <folder outside SharePoint> [--store <scan store final_v4>] [--dry-run]
    python build_line_frequency.py --from-votes <freq_raw_lines.csv> [--names <names.txt>] [--dry-run]

Source: the frequency column ("Frequency" / "Tần suất", in C, D or E) of the fund sheets of the real budgets mapped in
the store's real_budget_ranges_map.csv. The raw read (one row per budget line) is written only to --workdir; it holds
store file ids and stays on the office machine. --from-votes rebuilds from a saved raw read.

Rules (user, 2026-11-09, docs/05-decisions.md "Default frequency from the 55 real budgets"):
- one vote per file and code, Management Fund budget sheets only, lines with a non-zero amount; Schedule is not
  counted; a file whose MF sheets give two frequencies equally often votes for nothing (the Common Area Fund is
  counted and printed for reference only);
- a code is listed when at least MIN_FILES files carry it and one frequency other than Monthly has more than half of
  the votes; otherwise it is Monthly and not listed;
- COSTING_KEEPS: four codes keep the frequency their costing counts (user, 2026-11-09);
- USER_FREQUENCIES: four near-threshold codes the user set to Yearly (2026-11-09, change
  near-threshold-and-unpriced-frequency); a code in both lists stops the build;
- a code not on the 2027 form's Management Fund sheet is not listed.
Every cyclic line starts in T1 (user's choice 2026-11-07). The template's own column C is read only for the notes.
Sources are stated as counts; the written table is checked against the store's project names and refused on a match.
"""
import argparse
import collections
import csv
import os
import shutil
import sys

import openpyxl
from openpyxl.utils import column_index_from_string, get_column_letter

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import line_frequency as lf  # noqa: E402

PROJECT = os.path.dirname(os.path.dirname(HERE))
TEMPLATE = os.path.join(HERE, '..', '..', 'input', 'template', '2027 Resi Budget Form (IT team).xlsx')
STORE_ROOT = os.environ.get('BUDGET_STORE', os.path.join(os.path.expanduser('~'), 'Savills-local', 'budget-agent',
                                                         'scan-2026-10-07'))
STORE = os.path.join(STORE_ROOT, 'final_v4')
NEW_ROOT = os.path.join(PROJECT, 'input', 'budget_planning', 'Ngân sách thực tế dự án lập hằng năm (có số liệu báo cáo)')
OLD_ROOT = os.path.join(PROJECT, 'input', 'budget_planning')
NAMES_FILE = 'real_budget_ranges_names.txt'

FUND_SHEETS = ('2. Budget-Management Fund', '2.2 Common area Fund')
CODE_COL, FREQ_COL, MONTH_FIRST_COL = 25, 3, 8
FIRST_MONTH = 1
MIN_FILES = 5
FIELDS = ['code', 'frequency', 'times', 'first_month', 'source', 'note']
RAW_FIELDS = ['file_id', 'budget_year', 'fund', 'sheet', 'sheet_kind', 'row', 'code', 'amount_year', 'is_blank',
              'freq_col', 'freq_header', 'freq_raw', 'colC_raw']
HEADER_KEYS = ('frequen', 'tần suất', 'tan suat')
TIE = '(tie)'

# Codes that keep the frequency their costing counts, over the real-budget rule (user, 2026-11-09). The constant or
# remark is named so a reader can check the row against generate_project_budget.py.
COSTING_KEEPS = [
    ('ESC12', lf.YEARLY, 'costing: ENV_INCIDENT_PLAN_ANNUAL, remark "một lần/năm"',
     'Kế hoạch ứng phó sự cố môi trường, 1 lần/năm.'),
    ('ESM2', lf.HALF, 'costing: ENV_REPORT_ANNUAL, remark "6 tháng/lần theo Nghị định 40/2019/NĐ-CP Điều 47"',
     'Báo cáo quan trắc môi trường định kỳ, 2 lần/năm.'),
    ('ESM5', lf.QUARTERLY, 'costing: POOL_TEST_SAMPLES_PER_YEAR = 8 (4 đợt/năm x 2 mẫu/đợt)',
     'Kiểm nghiệm nước hồ bơi, 4 đợt/năm; chỉ ghi khi dự án có hồ bơi.'),
    ('ESM25', lf.QUARTERLY, 'costing: WASTEWATER_CROSSCHECK_PER_YEAR = 4 (hàng quý)',
     'Đối chiếu chất lượng nước sau xử lý, hàng quý.'),
]
KEEP_NOTE = 'Giữ tần suất theo cách tính (người dùng chốt 09/11/2026), không theo đa số ngân sách thật.'

# Codes near the threshold (Yearly in 40-50 % of the MF files that carry them) that the user set to Yearly on
# 2026-11-09 (change near-threshold-and-unpriced-frequency, design D1). The rule itself is unchanged.
USER_FREQUENCIES = [
    ('ESC2', lf.YEARLY, 'Diễn tập PCCC.'),
    ('ESC3', lf.YEARLY, 'Đại hội cư dân.'),
    ('ESS7', lf.YEARLY, 'Vệ sinh mặt ngoài.'),
    ('EMA18', lf.YEARLY, 'Thuế môn bài.'),
]
USER_NOTE = 'Gần ngưỡng: người dùng chốt Hàng năm 09/11/2026, không theo quy tắc trên một nửa.'


# ---- reading the real budgets (office machine) ----

def _store_rows(store, name):
    with open(os.path.join(store, name), encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


def _text(v):
    return '' if v is None else str(v).replace('\n', ' ').strip()


def _long(path):
    path = os.path.abspath(path)
    return '\\\\?\\' + path if os.name == 'nt' and not path.startswith('\\\\?\\') else path


def _source_path(entry, store):
    group, rel = entry['source_group'], entry['rel_path']
    if group == 'old8':
        return os.path.join(OLD_ROOT, rel)
    if group == 'new':
        return os.path.join(NEW_ROOT, rel)
    for root in (store, os.path.dirname(store)):
        if os.path.isfile(_long(os.path.join(root, rel))):
            return os.path.join(root, rel)
    return os.path.join(os.path.dirname(store), rel)


def read_store(store, workdir):
    """The raw read: [dict(RAW_FIELDS)] for every budget line of the MF and CA sheets of the mapped files, with the
    value of the sheet's frequency column. Each source is copied into `workdir` before it is opened (a file open in
    Excel stays untouched), through review_import.open_workbook (repair of the #N/A defined-name trap). Returns
    (lines, problems)."""
    import review_import as ri
    mapped = {r['file_id']: r for r in _store_rows(store, 'real_budget_ranges_map.csv')}
    dim = {r['file_id']: r for r in _store_rows(store, 'dim_file.csv') if r['file_id'] in mapped}
    catalog = collections.defaultdict(list)
    for r in _store_rows(store, 'sheet_catalog.csv'):
        if r['file_id'] in mapped and r['fund'] in ('MF', 'CA'):
            catalog[r['file_id']].append(r)
    store_lines = collections.defaultdict(list)
    for r in _store_rows(store, 'fact_line.csv'):
        if r['file_id'] in mapped:
            store_lines[(r['file_id'], r['sheet'])].append(r)
    src_dir = os.path.join(workdir, 'src')
    os.makedirs(src_dir, exist_ok=True)
    out, problems = [], []
    for n, (fid, entry) in enumerate(sorted(mapped.items()), 1):
        local = os.path.join(src_dir, fid + '.xlsx')
        try:
            if not os.path.exists(local):
                shutil.copy2(_long(_source_path(dim[fid], store)), local)
            wb, _path = ri.open_workbook(local, workdir=os.path.join(workdir, 'repaired'))
        except Exception as exc:  # noqa: BLE001 - listed, the other files go on
            problems.append((fid, 'open', repr(exc)[:200]))
            continue
        for sc in catalog[fid]:
            if sc['sheet'] not in wb.sheetnames:
                problems.append((fid, sc['sheet'], 'sheet missing'))
                continue
            grid = [list(r) for r in wb[sc['sheet']].iter_rows(values_only=True)]
            fcol, fhead = None, ''
            for r in grid[:25]:
                for ci, v in enumerate(r):
                    t = _text(v).lower()
                    if t and any(k in t for k in HEADER_KEYS):
                        fcol, fhead = ci, _text(v)
                        break
                if fcol is not None:
                    break
            for ln in store_lines[(fid, sc['sheet'])]:
                i = int(ln['source_row']) - 1
                row = grid[i] if 0 <= i < len(grid) else []
                out.append(dict(file_id=fid, budget_year=entry['budget_year'], fund=sc['fund'], sheet=sc['sheet'],
                                sheet_kind=sc['sheet_kind'], row=ln['source_row'], code=ln['code'],
                                amount_year=ln['amount_year'], is_blank=ln['is_blank'],
                                freq_col=get_column_letter(fcol + 1) if fcol is not None else '', freq_header=fhead,
                                freq_raw=_text(row[fcol]) if fcol is not None and fcol < len(row) else '',
                                colC_raw=_text(row[2]) if len(row) > 2 else ''))
        wb.close()
        print(f'  {n:>2} {fid} read', flush=True)
    return out, problems


def write_raw(lines, path):
    with open(path, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=RAW_FIELDS)
        w.writeheader()
        w.writerows(lines)


def read_raw(path):
    with open(path, encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


# ---- votes ----

def _amount(x):
    try:
        return float(x or 0)
    except ValueError:
        return 0.0


def votes(lines, fund='MF'):
    """{code: Counter(frequency or TIE: files)}: one vote per file, the frequency most of the file's lines carry on the
    fund's budget sheets (non-zero amount, Schedule and unknown values left out); a file with a tie votes TIE."""
    per_file = collections.defaultdict(collections.Counter)
    for r in lines:
        if r['fund'] != fund or r['sheet_kind'] != 'budget' or not (r.get('code') or '').strip():
            continue
        if abs(_amount(r['amount_year'])) < 1:
            continue
        try:
            freq = lf.normalise(r['freq_raw'])
        except ValueError:
            continue
        if freq in (None, lf.SCHEDULE):
            continue
        per_file[(r['code'].strip(), r['file_id'])][freq] += 1
    out = collections.defaultdict(collections.Counter)
    for (code, _fid), c in per_file.items():
        top = c.most_common()
        out[code][TIE if len(top) > 1 and top[0][1] == top[1][1] else top[0][0]] += 1
    return out


def winner(counter):
    """The non-Monthly frequency that passes the rule (>= MIN_FILES files, more than half of them), or None."""
    n = sum(counter.values())
    if n < MIN_FILES:
        return None
    for freq, k in counter.most_common():
        if freq not in (lf.MONTHLY, TIE) and k * 2 > n:
            return freq
    return None


def count_text(counter, fund='MF'):
    """'Yearly 22 of 40 MF files (16 Monthly, 2 tie)' (no file id, no name)."""
    n = sum(counter.values())
    if not n:
        return f'no {fund} file carries the code'
    top, k = next(((f, k) for f, k in counter.most_common() if f != TIE), (TIE, counter[TIE]))
    rest = ', '.join(f'{v} {"tie" if f == TIE else f}' for f, v in counter.most_common() if f != top)
    return f'{top} {k} of {n} {fund} files' + (f' ({rest})' if rest else '')


# ---- the 2027 template ----

def _month_of(formula, header_row=8):
    """T-number of a month cell written as a reference to the row-8 month header (for example '=K8' -> 4)."""
    if not (isinstance(formula, str) and formula.startswith('=') and formula.endswith(str(header_row))):
        return None
    col = column_index_from_string(formula[1:-len(str(header_row))].replace('$', ''))
    return col - MONTH_FIRST_COL + 1


def template_rows(path):
    """{code: dict(frequency, sheet, row, months)} of the template's fund rows other than Monthly or Schedule, and the
    set of codes on its Management Fund sheet."""
    wb = openpyxl.load_workbook(path, data_only=False)
    rows, mf_codes = {}, set()
    for name in FUND_SHEETS:
        ws = wb[name]
        for r in range(1, ws.max_row + 1):
            code = ws.cell(r, CODE_COL).value
            if not isinstance(code, str) or not code.strip():
                continue
            if name == FUND_SHEETS[0]:
                mf_codes.add(code.strip())
            try:
                freq = lf.normalise(ws.cell(r, FREQ_COL).value)
            except ValueError:
                continue
            if freq in (None, lf.MONTHLY, lf.SCHEDULE):
                continue
            filled = [_month_of(ws.cell(r, MONTH_FIRST_COL + k).value) for k in range(12)]
            rows[code.strip()] = dict(frequency=freq, sheet=name, row=r, months=[m for m in filled if m])
    wb.close()
    return rows, mf_codes


# ---- the table ----

def build(lines, template_path):
    """(rows of the table, report lines). `lines` = the raw read."""
    tpl, mf_codes = template_rows(template_path)
    mf = votes(lines, 'MF')
    keeps = {code: (freq, source, note) for code, freq, source, note in COSTING_KEEPS}
    users = {code: (freq, note) for code, freq, note in USER_FREQUENCIES}
    both = sorted(set(keeps) & set(users))
    if both:
        raise ValueError(f'codes in both COSTING_KEEPS and USER_FREQUENCIES: {", ".join(both)}')
    report, chosen = [], {}
    for code in sorted(mf):
        freq = winner(mf[code])
        if freq is None:
            continue
        if code not in mf_codes:
            report.append(f'left out, not on the 2027 form: {code} {count_text(mf[code])}')
            continue
        chosen[code] = freq
    out = []
    for code in sorted(set(chosen) | set(keeps) | set(users)):
        counts = count_text(mf.get(code, collections.Counter()))
        notes = []
        if code in keeps:
            freq, costing, note = keeps[code]
            source = f'{costing}; real budgets: {counts}'
            notes += [note, KEEP_NOTE]
        elif code in users:
            freq, note = users[code]
            source = f'real budgets: {counts}'
            notes += [note, USER_NOTE]
        else:
            freq = chosen[code]
            source = f'real budgets: {counts}'
        t = tpl.get(code)
        if t and t['frequency'] != freq:
            notes.append(f"Mẫu để {t['frequency']}, bảng dùng {freq}.")
        out.append(dict(code=code, frequency=freq, times=lf.TIMES[freq], first_month=FIRST_MONTH, source=source,
                        note=' '.join(notes)))
    listed = {r['code'] for r in out}
    for code, t in sorted(tpl.items()):
        if code not in listed:
            report.append(f"template {t['frequency']} not used (real budgets: {count_text(mf.get(code, {}))}): {code}")
    ca = votes(lines, 'CA')
    ca_pass = [f'{c} {count_text(v, "CA")}' for c, v in sorted(ca.items()) if winner(v)]
    report.append('Common Area Fund above the threshold (reference only): ' + ('; '.join(ca_pass) or 'none'))
    return out, report


def leak_check(rows, names_path):
    """Names of the store's projects (one per line, the part after a leading '(n) ') found in the written table."""
    if not names_path or not os.path.exists(names_path):
        return None
    text = ' '.join(f"{r['source']} {r['note']}" for r in rows).lower()
    found = []
    with open(names_path, encoding='utf-8-sig') as fh:
        for line in fh:
            name = line.strip()
            if name.startswith('(') and ') ' in name:
                name = name.split(') ', 1)[1]
            for part in (name, name.split(' - ')[0]):
                part = part.strip().lower()
                if len(part) >= 6 and part in text:
                    found.append(part)
    return found


def write_table(rows, path):
    with open(path, 'w', encoding='utf-8-sig', newline='') as fh:
        fh.write('# Default frequency per code for a new budget (change default-frequency-from-real-budgets). Built by '
                 'build_line_frequency.py from the frequency column of the mapped real budgets; reviewed by the user '
                 'before use. A code not listed is Monthly.\n')
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=(__doc__ or '').split('\n\n')[1].strip())
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument('--workdir', help='read the store and write the raw read here (outside SharePoint)')
    src.add_argument('--from-votes', help='a saved raw read (freq_raw_lines.csv)')
    ap.add_argument('--store', default=STORE)
    ap.add_argument('--names', default=None, help=f'project names for the leak check (default: <store>/{NAMES_FILE})')
    ap.add_argument('--template', default=TEMPLATE)
    ap.add_argument('--out', default=lf.TABLE_PATH)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args(argv)
    if args.from_votes:
        lines = read_raw(args.from_votes)
    else:
        os.makedirs(args.workdir, exist_ok=True)
        lines, problems = read_store(args.store, args.workdir)
        write_raw(lines, os.path.join(args.workdir, 'freq_raw_lines.csv'))
        print(f'raw read: {len(lines)} lines, {len(problems)} problems -> {args.workdir}')
        for p in problems:
            print('  problem:', *p)
    rows, report = build(lines, args.template)
    for r in rows:
        months = ', '.join(f'T{m}' for m in lf.months(r['frequency'], r['first_month']))
        print(f"{r['code']:6} {r['frequency']:12} {r['times']:>2} lần  {months:18} | {r['source']}")
    for line in report:
        print('  ' + line)
    found = leak_check(rows, args.names or os.path.join(args.store, NAMES_FILE))
    if found:
        print('REFUSED: project names in the table:', ', '.join(sorted(set(found))))
        return 2
    if found is None:
        print('  (no names file: leak check skipped)')
    if args.dry_run:
        return 0
    write_table(rows, args.out)
    print(f'{len(rows)} rows -> {os.path.abspath(args.out)}')
    lf.load_table(args.out)  # the reader accepts what was written
    return 0


if __name__ == '__main__':
    sys.exit(main())
