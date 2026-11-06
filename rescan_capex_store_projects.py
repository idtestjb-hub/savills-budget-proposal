"""
Office-only: extract the capex item lists of the store projects that join the capex pool (change
widen-utility-and-capex-sources) into Fact_Capex_Rescanned.csv under their registry keys.

    python rescan_capex_store_projects.py --inspect          # print what each configured sheet yields, write nothing
    python rescan_capex_store_projects.py --write            # replace the rows of these keys in Fact_Capex_Rescanned.csv

Reuses the column detector of rescan_capex_from_source.py (Unit Price found by text; Quantity = the column to its left,
Total = the column to its right; a row counts only with a positive unit price). Sources are the real-budget store files
(index `dim_file.csv` of the scan store); a workbook openpyxl cannot open is read from the store's repaired copy. The
rows of the original eight keep their place; only the rows whose RefKey is configured here are replaced.
"""
import argparse
import csv
import os
import sys

import openpyxl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rescan_capex_from_source as rc  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BUDGET_AGENT = os.path.dirname(HERE)
PROJECT = os.path.dirname(BUDGET_AGENT)
OUT_CSV = rc.OUT_CSV
STORE = os.environ.get('BUDGET_STORE', os.path.join(os.path.expanduser('~'), 'Savills-local', 'budget-agent',
                                                    'scan-2026-10-07'))
STORE_INDEX = os.path.join(STORE, 'final_v4', 'dim_file.csv')
NEW_ROOT = os.path.join(PROJECT, 'input', 'budget_planning',
                        'Ngân sách thực tế dự án lập hằng năm (có số liệu báo cáo)')
OLD_ROOT = os.path.join(PROJECT, 'input', 'budget_planning')

# key -> store file id, label written to the Project column, and the sheets kept with their category. Sheets left out
# on purpose are listed in `skipped` with the reason, so the extraction log shows them.
SOURCES = {
    'R09': dict(file_id='254fb1cef1c3', label='Habitat Phase 3', sheets=[
        ('2.7 Chi phí Trang thiết bị MO', 'MO Equipment'),
        ('2.8 CCDC M&E', 'M&E Equipment'),
    ], skipped=[]),
    'R10': dict(file_id='67b7d566b159', label='Sycamore NS', sheets=[
        ('3. Chi phí Trang thiết bị MO', 'MO Equipment'),
        ('4. CCDC M&E', 'M&E Equipment'),
        ('6. Capex khu công cộng', 'Public Area'),
    ], skipped=[]),
    'R11': dict(file_id='86160f50e3b4', label='Masteri West Heights', sheets=[
        ('Capex detail 1. MO & COMMON', 'MO Equipment'),
        ('Capex detail 2.ME tools', 'M&E Equipment'),
        ('Capex detail 3.FF & Pool', 'Amenity Area'),
        ('Capex detail 4.Common areas', 'Public Area'),
    ], skipped=[]),
    'R12': dict(file_id='962c7429ec69', label='Sycamore B13', sheets=[
        ('3. Capex MO B13', 'MO Equipment'),
        ('4. M&E Capex', 'M&E Equipment'),
        ('6. Capex công cộng', 'Public Area'),
    ], skipped=[
        ('3. Chi phí Trang thiết bị MO', 'second copy of the item sheets in the same workbook (block sheets kept)'),
        ('4. CCDC M&E', 'second copy of the item sheets in the same workbook (block sheets kept)'),
        ('6. Capex khu công cộng', 'second copy of the item sheets in the same workbook (block sheets kept)'),
    ]),
}
FIELDS = ['Project', 'Category', 'Item', 'Unit', 'Qty', 'UnitPrice', 'Total', 'SourceSheet', 'SourceRow', 'RefKey']


def _index():
    with open(STORE_INDEX, encoding='utf-8-sig') as fh:
        return {r['file_id']: r for r in csv.DictReader(fh)}


def source_path(entry):
    root = OLD_ROOT if entry['source_group'] == 'old8' else (
        STORE if entry['source_group'] == 'new_converted' else NEW_ROOT)
    return os.path.join(root, entry['rel_path'])


def open_workbook(file_id, entry):
    live = source_path(entry)
    for path in (live, os.path.join(STORE, 'repaired', f'{file_id}.xlsx')):
        if not os.path.isfile(path):
            continue
        try:
            return openpyxl.load_workbook(path, data_only=True), path
        except Exception:  # noqa: BLE001 - try the next copy
            continue
    raise SystemExit(f'cannot open store file {file_id} (live path {live})')


def _sheet(wb, name):
    want = rc.nfc(name).strip().lower()
    for sn in wb.sheetnames:
        if rc.nfc(sn).strip().lower() == want:
            return wb[sn]
    return None


def extract(key, cfg, index):
    wb, path = open_workbook(cfg['file_id'], index[cfg['file_id']])
    rows, log = [], [f"{key} {cfg['file_id']}: {os.path.basename(path)}"]
    for sheet, category in cfg['sheets']:
        ws = _sheet(wb, sheet)
        if ws is None:
            log.append(f'  MISSING sheet {sheet!r}')
            continue
        cols = rc.find_columns(ws)
        if not cols:
            log.append(f'  NO COLUMNS in {sheet!r}')
            continue
        items = rc.extract_items(ws, cols)
        total = sum(i['total'] or 0 for i in items)
        log.append(f"  {sheet!r} -> {category}: {len(items)} items, total {total:,.0f}, header row {cols['header_row']},"
                   f" qty col {cols['qty_col']}, price col {cols['price_col']}, total col {cols['total_col']}")
        for it in items:
            rows.append(dict(Project=cfg['label'], Category=category, Item=it['item'], Unit=it['unit'], Qty=it['qty'],
                             UnitPrice=it['unit_price'], Total=it['total'], SourceSheet=ws.title,
                             SourceRow=it['source_row'], RefKey=key))
    for sheet, why in cfg['skipped']:
        log.append(f'  skipped {sheet!r}: {why}')
    return rows, log


def write(new_rows, keys):
    with open(OUT_CSV, encoding='utf-8-sig', newline='') as fh:
        old = [r for r in csv.DictReader(fh) if (r.get('RefKey') or '') not in keys]
    with open(OUT_CSV, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(old)
        w.writerows(new_rows)
    print(f'{os.path.basename(OUT_CSV)}: kept {len(old)} rows, wrote {len(new_rows)} rows for {sorted(keys)}')


def main(argv=None):
    ap = argparse.ArgumentParser(description=(__doc__ or '').split('\n\n')[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--inspect', action='store_true')
    g.add_argument('--write', action='store_true')
    a = ap.parse_args(argv)
    index = _index()
    all_rows = []
    for key, cfg in SOURCES.items():
        rows, log = extract(key, cfg, index)
        print('\n'.join(log))
        all_rows += rows
    if a.write:
        write(all_rows, set(SOURCES))
    return 0


if __name__ == '__main__':
    sys.exit(main())
