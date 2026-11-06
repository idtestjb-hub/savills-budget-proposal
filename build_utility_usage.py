"""
Office-only: build data/generation_B_verified/Ref_UtilityUsage.csv from the hand-checked worksheet of usage candidates
(change widen-utility-and-capex-sources, task 2.4).

    python build_utility_usage.py --checked <checked_usage.csv> [--checked-by <role>] [--out <csv>] [--dry-run]

The worksheet has one row per candidate the store scan flagged (accepted / rejected / duplicate, with the reason).
Every row is carried into the table so the rejections stay visible; only `accepted` rows count at run time
(utility_usage.py). Rows of projects outside real_budget_ranges_map.csv are refused. Prints, per utility, the accepted
and rejected counts, the usage values and what the IQR fence would drop.
"""
import argparse
import csv
import datetime
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import utility_usage as uu  # noqa: E402

STORE = os.environ.get('BUDGET_STORE', os.path.join(os.path.expanduser('~'), 'Savills-local', 'budget-agent',
                                                    'scan-2026-10-07'))
MAP_CSV = os.path.join(STORE, 'final_v4', 'real_budget_ranges_map.csv')
UNIT_ALIASES = {'kwh': 'kWh', 'm3': 'm3', 'm³': 'm3', 'litre': 'litre', 'liter': 'litre', 'lít': 'litre', 'lit': 'litre'}


def _mapped():
    with open(MAP_CSV, encoding='utf-8-sig') as fh:
        return {r['file_id']: r['project_id'] for r in csv.DictReader(fh)}


def convert(checked_path, checked_by, today):
    mapped = _mapped()
    out, problems = [], []
    with open(checked_path, encoding='utf-8-sig', newline='') as fh:
        for row_no, r in enumerate(csv.DictReader(fh), start=2):
            fid = (r.get('file_id') or '').strip()
            if fid not in mapped:
                problems.append(f'row {row_no}: file {fid} is not one of the mapped projects')
                continue
            check = (r.get('check') or '').strip().lower()
            unit = UNIT_ALIASES.get((r.get('unit') or '').strip().lower(), (r.get('unit') or '').strip())
            utility = (r.get('utility') or '').strip().lower()
            if check == 'accepted' and unit != uu.UNITS.get(utility):
                problems.append(f'row {row_no}: {utility} accepted with unit {unit!r}')
            cell = (r.get('source_cell') or '').strip()
            out.append(dict(
                file_id=fid, project_id=mapped[fid], utility=utility,
                quantity_month=(r.get('quantity_month') or '').strip(), unit=unit,
                period_basis=(r.get('period_basis') or '').strip(), conversion=(r.get('conversion') or '').strip(),
                nfa_m2=(r.get('nfa_m2') or '').strip(), nfa_source=(r.get('nfa_source') or '').strip(),
                usage_per_m2_month=(r.get('usage_per_m2_month') or '').strip(),
                source_sheet=(r.get('source_sheet') or r.get('candidate_sheet') or '').strip(),
                source_cell=cell or f"row {(r.get('candidate_row') or '').strip()}",
                check=check, reason=(r.get('reason') or '').strip(), checked_by=checked_by, checked_on=today))
    return out, problems


def report(path):
    uu.clear_cache()
    for category in uu.CATEGORY_UTILITY:
        b = uu.benchmark(category, path)
        kept = ', '.join(f'{p} {v:.4f}' for p, v in b['kept'])
        dropped = ', '.join(f'{p} {v:.4f}' for p, v in b['dropped']) or 'none'
        median = f"{b['median']:.4f}" if b['median'] is not None else '-'
        print(f"{category}: n={b['n']} median={median} {b['unit']}/m2/month; enough={b['enough']}\n"
              f"  kept: {kept}\n  dropped by the fence: {dropped}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=(__doc__ or '').split('\n\n')[0])
    ap.add_argument('--checked', required=True)
    ap.add_argument('--checked-by', default='công cụ tự động; người kiểm xác nhận mẫu')
    ap.add_argument('--out', default=uu.USAGE_CSV)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding='utf-8')
    rows, problems = convert(a.checked, a.checked_by, datetime.date.today().isoformat())
    for p in problems:
        print('PROBLEM', p)
    counts = {}
    for r in rows:
        counts.setdefault(r['utility'], {}).setdefault(r['check'], 0)
        counts[r['utility']][r['check']] += 1
    print('rows by utility and check:', counts)
    if problems:
        return 1
    out = a.out if not a.dry_run else os.path.join(os.environ.get('TEMP', '.'), 'Ref_UtilityUsage.dry-run.csv')
    with open(out, 'w', encoding='utf-8-sig', newline='') as fh:
        fh.write('# Hand-checked common-area usage per project (change widen-utility-and-capex-sources). Only rows '
                 'with check = accepted count; see utility_usage.py.\n')
        w = csv.DictWriter(fh, fieldnames=uu.COLUMNS, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    print(f'wrote {len(rows)} rows -> {out}')
    report(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
