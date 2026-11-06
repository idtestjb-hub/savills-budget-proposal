"""
Rescans all 8 real project files directly for Capex line items — replaces reliance on
data/generation_A_star_schema/Fact_Capex.csv, which turned out to have real, confirmed bugs:

  1. WRONG QUANTITY COLUMN. 7 of the 8 real files lay out their Capex sheets with THREE
     sub-quantity columns (Required / Standard / Optional equipment) followed by a TRUE total
     Quantity column, then Unit Price, then Total — e.g. "8. Capex MO" in Lumi Prestige & Elite:
     D=Required, E=Standard, F=Optional, G=Quantity (the real total), H=Unit Price, I=Total.
     Fact_Capex.csv used column D (Required only) as "Quantity" — for an item priced only under
     "Optional" (Required=0), that reads as Qty=0 and the item silently vanishes; for the "IT
     Equipment" section-header row, D=56 when the real total (G) is 59.
  2. UnitPrice reads as 0.0 for nearly every one of those same rows, because the same 3-column
     shift pushes the real "Unit Price" header off wherever the ETL expected it.
  3. Section/category HEADER rows ("IT Equipment", "Public restroom area", ...) got extracted as
     if they were individual purchasable items — double-counting against the real line items
     listed underneath them.
  4. An entire 4th Capex sheet per project — "Capex khu tiện ích" (Amenity Area) — was never
     extracted at all; Dim_Equipment.csv only has 3 categories (M&E/MO/Public Area), not 4.

Only 11D Thi Sách's sheets use a simpler single-Quantity-column layout (no Required/Standard/
Optional split), which is why ITS numbers came out right in Fact_Capex.csv while every other
project's didn't.

FIX: a generic column-detector that doesn't assume a fixed layout. It finds the "Unit Price"
header wherever it actually sits (by text, not position), then takes Quantity = the column
immediately to its LEFT and Total = the column immediately to its RIGHT — true in every layout
seen across all 8 files, because Quantity/Price/Total are always adjacent in that order even
when the number of columns before them (Required/Standard/Optional, or just Stt) varies. A row
only counts as a real line item if it has a real positive Unit Price — that's what separates an
actual purchasable item from a section-header/subtotal row, which is deliberately excluded here
rather than double-counted.
"""
import os
import re
import glob
import sys
import zipfile
import tempfile
import unicodedata

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reference_projects  # noqa: E402

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BUDGET_AGENT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT_CSV = os.path.join(BUDGET_AGENT, 'data', 'generation_A_star_schema', 'Fact_Capex_Rescanned.csv')
DETAIL_LIST_PATH = os.path.join(BUDGET_AGENT, 'reports', 'Project_Detail_Lists.xlsx')


def nfc(s):
    """Some of these workbooks store Vietnamese sheet names in decomposed Unicode (NFD -- base
    character + separate combining diacritic marks) rather than composed (NFC). A keyword match
    against a plain NFC string silently fails on those sheets otherwise -- this bit the very
    first version of this script on EVERY 'Capex khu tiện ích' sheet in all 8 files."""
    return unicodedata.normalize('NFC', s)


CAPEX_SHEET_CATEGORIES = [
    (['capex mo', 'trang thiết bị mo'], 'MO Equipment'),
    (['capex m&e', 'ccdc m&e'], 'M&E Equipment'),
    (['capex khu công cộng', 'capex khu cong cong'], 'Public Area'),
    (['capex khu tiện ích', 'capex khu tien ich'], 'Amenity Area'),  # the missing 4th category
]

FRIENDLY_NAMES = {
    '20232710': '11D Thi Sach', '20251006': 'A&K Tower',
    'Lumi Prestige': 'Lumi Prestige & Elite', 'Lumi Signature': 'Lumi Signature',
    'Parking Building': 'Parking Building', 'Green Skyline': 'Green Skyline',
    '202604': 'Fiato Airport - F Zone G2', '202605': 'Fiato Airport - F Zone MF Pre/Y1/Y2',
}


def friendly_name(filename):
    for key, name in FRIENDLY_NAMES.items():
        if key in filename:
            return name
    return filename


def repair_workbook(filepath):
    """Local-temp repair (same fix as legacy/list_positions_by_project.py) -- avoids the OneDrive-sync
    lock hazard of writing a repaired copy back into the same synced input folder."""
    try:
        openpyxl.load_workbook(filepath, read_only=True)
        return filepath
    except Exception:
        pass
    repaired_path = os.path.join(tempfile.gettempdir(), os.path.basename(filepath).replace('.xlsx', '__local_repaired.xlsx'))
    with zipfile.ZipFile(filepath, 'r') as zin:
        wbxml = zin.read('xl/workbook.xml').decode('utf-8')
        cleaned = re.sub(r'<definedNames>.*?</definedNames>', '', wbxml, flags=re.DOTALL)
        with zipfile.ZipFile(repaired_path, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.namelist():
                data = zin.read(item)
                if item == 'xl/workbook.xml':
                    data = cleaned.encode('utf-8')
                zout.writestr(item, data)
    return repaired_path


PRICE_RE = re.compile(r'đơn giá|unit price', re.IGNORECASE)
TOTAL_RE = re.compile(r'tổng cộng|total', re.IGNORECASE)
ITEM_RE = re.compile(r'thiết bị|equip', re.IGNORECASE)
UNIT_RE = re.compile(r'đơn vị|unit', re.IGNORECASE)
CONTINGENCY_RE = re.compile(r'dự phòng|contingency', re.IGNORECASE)


def find_columns(ws, max_scan_row=12, max_scan_col=20):
    """Locates the header row and the Item/Unit/Quantity/UnitPrice/Total columns by TEXT, not
    fixed position -- see module docstring for why fixed positions don't work here."""
    for r in range(1, max_scan_row + 1):
        price_col = None
        for c in range(1, max_scan_col + 1):
            v = ws.cell(row=r, column=c).value
            if isinstance(v, str) and len(v) < 80 and PRICE_RE.search(v):
                price_col = c
                break
        if not price_col:
            continue
        qty_col = price_col - 1
        total_col = price_col + 1
        total_val = ws.cell(row=r, column=total_col).value
        if not (isinstance(total_val, str) and TOTAL_RE.search(total_val)):
            for c2 in range(price_col + 1, price_col + 4):
                v2 = ws.cell(row=r, column=c2).value
                if isinstance(v2, str) and TOTAL_RE.search(v2):
                    total_col = c2
                    break
        item_col = None
        for c in range(1, price_col):
            v = ws.cell(row=r, column=c).value
            if isinstance(v, str) and ITEM_RE.search(v):
                item_col = c
                break
        if item_col is None:
            nonempty = [c for c in range(1, price_col) if ws.cell(row=r, column=c).value]
            item_col = nonempty[1] if len(nonempty) > 1 else (nonempty[0] if nonempty else 2)
        unit_col = None
        for c in range(item_col + 1, qty_col + 1):
            v = ws.cell(row=r, column=c).value
            if isinstance(v, str) and UNIT_RE.search(v) and not PRICE_RE.search(v):
                unit_col = c
                break
        return dict(header_row=r, item_col=item_col, unit_col=unit_col, qty_col=qty_col,
                    price_col=price_col, total_col=total_col)
    return None


def clean_name(s):
    return nfc(re.sub(r'\s*\n\s*', ' ', s.strip()))


def extract_items(ws, cols):
    """A row is a real line item only if it has a real, positive Unit Price -- that's what
    separates a purchasable item from a section-header/subtotal row (which has a Total but no
    per-unit price, since it's summing the rows below it)."""
    items = []
    r = cols['header_row'] + 1
    max_r = min(ws.max_row, cols['header_row'] + 250)
    while r <= max_r:
        item = ws.cell(row=r, column=cols['item_col']).value
        price = ws.cell(row=r, column=cols['price_col']).value
        if isinstance(item, str) and item.strip() and isinstance(price, (int, float)) and price > 0:
            name = clean_name(item)
            if not CONTINGENCY_RE.search(name):
                qty = ws.cell(row=r, column=cols['qty_col']).value
                unit = ws.cell(row=r, column=cols['unit_col']).value if cols['unit_col'] else None
                total = ws.cell(row=r, column=cols['total_col']).value
                items.append(dict(
                    item=name, unit=clean_name(unit) if isinstance(unit, str) else unit,
                    qty=qty if isinstance(qty, (int, float)) else None,
                    unit_price=price, total=total if isinstance(total, (int, float)) else None,
                    source_row=r,
                ))
        r += 1
    return items


def scan_all():
    files = sorted(glob.glob(os.path.join(BASE, 'input', 'budget_planning', '*.xlsx')))
    files = [f for f in files if '__' not in os.path.basename(f) and not any(
        x in os.path.basename(f) for x in ['MasterData', 'Budget_Workbook', 'Sheet_Index', 'PowerBI', 'SAMPLE', 'GENERATED'])]

    all_rows = []
    for f in files:
        repaired = repair_workbook(f)
        wb = openpyxl.load_workbook(repaired, data_only=True)
        proj_name = friendly_name(os.path.basename(f))
        ref_key = reference_projects.key_for_name(proj_name) or ''
        for keywords, category in CAPEX_SHEET_CATEGORIES:
            sheet_name = next((sn for sn in wb.sheetnames if any(k in nfc(sn).lower() for k in keywords)), None)
            if not sheet_name:
                all_rows.append(dict(Project=proj_name, Category=category, Item='(sheet not found)',
                                      Unit=None, Qty=None, UnitPrice=None, Total=None,
                                      SourceSheet=None, SourceRow=None, RefKey=ref_key))
                continue
            ws = wb[sheet_name]
            cols = find_columns(ws)
            if not cols:
                all_rows.append(dict(Project=proj_name, Category=category, Item='(columns not detected)',
                                      Unit=None, Qty=None, UnitPrice=None, Total=None,
                                      SourceSheet=sheet_name, SourceRow=None, RefKey=ref_key))
                continue
            for it in extract_items(ws, cols):
                all_rows.append(dict(Project=proj_name, Category=category, Item=it['item'],
                                      Unit=it['unit'], Qty=it['qty'], UnitPrice=it['unit_price'],
                                      Total=it['total'], SourceSheet=sheet_name, SourceRow=it['source_row'],
                                      RefKey=ref_key))
    return all_rows


HEADER_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)
TITLE_FONT = Font(bold=True, size=14)
SUBTITLE_FONT = Font(italic=True, color="595959")
SECTION_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
SECTION_FONT = Font(bold=True)
THIN = Side(style='thin', color='BFBFBF')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal='center', vertical='center')
LEFT = Alignment(horizontal='left', vertical='center', wrap_text=True)
MONEY_FMT = '#,##0'


def write_csv(rows):
    import csv
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=['Project', 'Category', 'Item', 'Unit', 'Qty', 'UnitPrice',
                                           'Total', 'SourceSheet', 'SourceRow', 'RefKey'])
        w.writeheader()
        w.writerows(rows)


def append_to_detail_lists(rows):
    """Adds a 'Capex Items by Project' sheet to reports/Project_Detail_Lists.xlsx, matching the
    Security/Cleaning/Landscape Positions by Project sheets already there — same file, one more
    real category, built the same way (legacy/list_positions_by_project.py's pattern)."""
    if os.path.exists(DETAIL_LIST_PATH):
        try:
            wb = openpyxl.load_workbook(DETAIL_LIST_PATH)
        except PermissionError:
            local = os.path.join(tempfile.gettempdir(), 'Project_Detail_Lists.xlsx')
            import shutil
            shutil.copyfile(DETAIL_LIST_PATH, local)
            wb = openpyxl.load_workbook(local)
    else:
        wb = openpyxl.Workbook()

    if 'Capex Items by Project' in wb.sheetnames:
        del wb['Capex Items by Project']
    ws = wb.create_sheet('Capex Items by Project')
    ws['A1'] = 'Capex — real line items listed per project, rescanned directly from source (see rescan_capex_from_source.py)'
    ws['A1'].font = TITLE_FONT
    ws.merge_cells('A1:G1')
    ws['A2'] = ('Replaces Fact_Capex.csv, which used the wrong quantity column and zero unit prices for 7 of the 8 projects '
                '(their sheets have 3 sub-quantity columns before the real total — see script docstring). Includes the '
                '"Capex khu tiện ích" (Amenity Area) category, never extracted before now.')
    ws['A2'].font = SUBTITLE_FONT
    ws['A2'].alignment = LEFT
    ws.merge_cells('A2:G2')
    ws.row_dimensions[2].height = 28

    headers = ['Project', 'Category', 'Item', 'Unit', 'Qty', 'Unit Price (VND)', 'Total (VND)']
    r = 4
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    r += 1

    current_proj = None
    for row in rows:
        if row['Item'] in ('(sheet not found)', '(columns not detected)'):
            continue  # only the real project-level rows go into this human-facing sheet
        if row['Project'] != current_proj:
            current_proj = row['Project']
            ws.cell(row=r, column=1, value=current_proj).font = SECTION_FONT
            for c in range(1, 8):
                ws.cell(row=r, column=c).fill = SECTION_FILL
                ws.cell(row=r, column=c).border = BORDER
            r += 1
        ws.cell(row=r, column=2, value=row['Category']).border = BORDER
        ic = ws.cell(row=r, column=3, value=row['Item'])
        ic.border = BORDER
        ic.alignment = LEFT
        ws.cell(row=r, column=4, value=row['Unit']).border = BORDER
        ws.cell(row=r, column=5, value=row['Qty']).border = BORDER
        c6 = ws.cell(row=r, column=6, value=row['UnitPrice'])
        c6.number_format = MONEY_FMT
        c6.border = BORDER
        c7 = ws.cell(row=r, column=7, value=row['Total'])
        c7.number_format = MONEY_FMT
        c7.border = BORDER
        r += 1

    for col, w in {'A': 22, 'B': 14, 'C': 46, 'D': 12, 'E': 8, 'F': 16, 'G': 16}.items():
        ws.column_dimensions[col].width = w
    ws.freeze_panes = 'A5'

    import shutil
    local_out = os.path.join(tempfile.gettempdir(), 'Project_Detail_Lists.xlsx')
    wb.save(local_out)
    print('Saved locally:', local_out)
    try:
        shutil.copyfile(local_out, DETAIL_LIST_PATH)
        print('Copied into place:', DETAIL_LIST_PATH)
    except PermissionError as e:
        print('Could not copy into place yet (still locked):', e)
        print('Local copy remains valid at:', local_out)


def main():
    rows = scan_all()
    real_rows = [r for r in rows if r['Item'] not in ('(sheet not found)', '(columns not detected)')]
    missing = [r for r in rows if r['Item'] in ('(sheet not found)', '(columns not detected)')]
    print(f'Real Capex line items found: {len(real_rows)}')
    if missing:
        print(f'{len(missing)} project/category combos had no sheet found or columns not detected:')
        for m in missing:
            print(f"   {m['Project']} / {m['Category']}")

    by_project_cat = {}
    for row in real_rows:
        key = (row['Project'], row['Category'])
        by_project_cat.setdefault(key, []).append(row)
    print('\nQty totals by project/category:')
    for (proj, cat), items in sorted(by_project_cat.items()):
        total_qty = sum(it['Qty'] for it in items if it['Qty'])
        print(f'  {proj} / {cat}: {len(items)} items, total Qty={total_qty:.0f}')

    write_csv(rows)
    print('\nSaved CSV:', OUT_CSV)
    append_to_detail_lists(rows)


if __name__ == '__main__':
    main()
