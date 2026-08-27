"""
Builds the per-UNIT rate card (price for 1 staff / 1 position / 1 item -- never a portfolio
total) that feeds the Copilot Studio agent's Fabric reasoning layer.

Three domains, three different source shapes:
  - Staff:   staff_cost/2026 Staff Cost Data (Master Data) update.xlsx, sheet
             "DS Staff cost (KT - 2025)" -- ~1,800 real staff records across ~89 Savills
             projects. Averaged per position -> price for 1 staff in that role.
  - Service: service_cost/Detail form ...xlsx -- a STRUCTURE-only master file (position
             rosters, no unit price) for Security/Cleaning/Landscape, but Scent/Consumable/
             Elevator DO have real embedded prices. Security/Cleaning/Landscape fall back to
             A&K Tower's real project rate, clearly labeled as such. Garbage collection has
             no confirmed source anywhere -- left as None / "NOT FOUND", never fabricated.
  - Capex:   capex/Danh mục Capex 2026.xlsx -- a real equipment catalog (IT gear, M&E/fire
             team tools) with genuine per-item unit prices.

Outputs:
  - output/simple_reports/Master_Rate_Card.xlsx   (human-readable, 3 sheets + shift rules)
  - output/copilot_studio_package/data/Fact_MasterRateCard.csv   (flat, Fabric-ready)

Run add_shift_differentials.py afterwards to append the staff shift-differential rules
(these are flat legally-mandated percentages, not per-project data, so they're a separate
step rather than baked into this extraction).

When the 150-project pool lands: the Staff domain should scale automatically (it already
averages over however many real records exist per position). The Service domain's
Security/Cleaning/Landscape fallback should be revisited once enough real projects have
those rates filled in directly -- at that point prefer a real median over the single A&K
reference value hardcoded below.
"""
import os
import glob
import re
import csv
from collections import defaultdict

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # Budget_Agent/ — for output/ paths
# Real bug, found 2026-08-27: every input/ reference in this file used BASE (Budget_Agent/), but
# input/ actually lives one level further up, beside Budget_Agent/, not inside it — same PROJECT_ROOT
# vs BUDGET_AGENT distinction generate_project_budget.py already makes correctly. This meant
# build_staff_rates() (and therefore this whole script) has been unable to find its own source file
# and would fail before ever reaching build_capex_rates() — the glob-order bug below was unreachable.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT_DIR = os.path.join(BASE, 'output', 'simple_reports')
DATA_DIR = os.path.join(BASE, 'output', 'copilot_studio_package', 'data')


def build_staff_rates():
    staff_src = os.path.join(PROJECT_ROOT, 'input', 'staff_cost', '2026 Staff Cost Data (Master Data) update.xlsx')
    wb_staff = openpyxl.load_workbook(staff_src, data_only=True)
    ws_staff = wb_staff['DS Staff cost (KT - 2025)']
    rows = list(ws_staff.iter_rows(min_row=11, max_row=ws_staff.max_row, values_only=True))
    staff_data = [r for r in rows if r[2] is not None and r[3] is not None and isinstance(r[4], (int, float))]

    by_position = defaultdict(lambda: {'count': 0, 'gross_total': 0.0, 'admin_total': 0.0})
    for r in staff_data:
        position, gross, admin_fee = r[3], r[4], r[6]
        d = by_position[position]
        d['count'] += 1
        d['gross_total'] += gross or 0
        d['admin_total'] += admin_fee or 0

    out = []
    for pos, d in by_position.items():
        n = d['count']
        avg_gross = d['gross_total'] / n
        avg_admin = d['admin_total'] / n
        out.append({
            'Domain': 'Staff', 'Category': 'Position', 'Item': pos, 'Unit': 'VND/staff/month',
            'UnitPrice': round(avg_gross), 'AdminFeePerStaff': round(avg_admin),
            'TotalPerStaff': round(avg_gross + avg_admin), 'SampleSize': n,
            'Source': f'Average across {n} real staff records, ~89 Savills projects', 'Notes': ''
        })
    out.sort(key=lambda x: x['UnitPrice'], reverse=True)
    return out


def build_service_rates():
    # Real embedded rates confirmed present in the master service_cost file (Scent, Consumable,
    # Elevator). Security/Cleaning/Landscape/Garbage/Parking are blank in the master file --
    # Security/Cleaning/Landscape fall back to A&K Tower's real project rate; Garbage has no
    # source at all and is intentionally left unfilled.
    return [
        dict(Domain='Service', Category='Security', Item='24/24 position (all roles)', Unit='VND/position/month',
             UnitPrice=17500000, AdminFeePerStaff=None, TotalPerStaff=17500000, SampleSize=1,
             Source='A&K Tower (real project) — master file ships this cell blank',
             Notes='Structure/position list is in master file; price is not'),
        dict(Domain='Service', Category='Cleaning', Item='8/24 position (all roles)', Unit='VND/position/month',
             UnitPrice=8000000, AdminFeePerStaff=None, TotalPerStaff=8000000, SampleSize=1,
             Source='A&K Tower (real project) — master file ships this cell blank', Notes=''),
        dict(Domain='Service', Category='Landscape', Item='8/24 position (all roles)', Unit='VND/position/month',
             UnitPrice=11000000, AdminFeePerStaff=None, TotalPerStaff=11000000, SampleSize=1,
             Source='A&K Tower (real project) — master file ships this cell blank', Notes=''),
        dict(Domain='Service', Category='Scent', Item='Diffuser KD1000AC (Lobby, size L 15-18)', Unit='VND/device/month',
             UnitPrice=2045400, AdminFeePerStaff=None, TotalPerStaff=2045400, SampleSize=1,
             Source='Master rate card (real, filled)', Notes=''),
        dict(Domain='Service', Category='Scent', Item='Diffuser KD130AC (Elevator lobby, size L 5-9)', Unit='VND/device/month',
             UnitPrice=937200, AdminFeePerStaff=None, TotalPerStaff=937200, SampleSize=1,
             Source='Master rate card (real, filled)', Notes=''),
        dict(Domain='Service', Category='Scent', Item='Diffuser KDECO (Public restroom)', Unit='VND/device/month',
             UnitPrice=230400, AdminFeePerStaff=None, TotalPerStaff=230400, SampleSize=1,
             Source='Master rate card (real, filled)', Notes=''),
        dict(Domain='Service', Category='Consumable', Item='Hand sanitizer', Unit='VND/liter',
             UnitPrice=30000, AdminFeePerStaff=None, TotalPerStaff=30000, SampleSize=1,
             Source='Master rate card (real, filled)', Notes='Same rate applied to apartment/villa/staff/guest categories'),
        dict(Domain='Service', Category='Consumable', Item='Toilet paper 600gr (200m roll)', Unit='VND/roll',
             UnitPrice=30000, AdminFeePerStaff=None, TotalPerStaff=30000, SampleSize=1,
             Source='Master rate card (real, filled)', Notes=''),
        dict(Domain='Service', Category='Consumable', Item='Hand towel (100 sheets/pack)', Unit='VND/pack',
             UnitPrice=10000, AdminFeePerStaff=None, TotalPerStaff=10000, SampleSize=1,
             Source='Master rate card (real, filled)', Notes=''),
        dict(Domain='Service', Category='Garbage collection', Item='Domestic waste collection', Unit='VND/m3',
             UnitPrice=None, AdminFeePerStaff=None, TotalPerStaff=None, SampleSize=0,
             Source='NOT FOUND — master file ships this blank, no real project value extracted yet',
             Notes='Do not fabricate; leave blank until sourced'),
        dict(Domain='Service', Category='Elevator advertising', Item='Ad frame (tower lobby, inside elevator)', Unit='VND/frame/month',
             UnitPrice=848485, AdminFeePerStaff=None, TotalPerStaff=848485, SampleSize=1,
             Source='Master rate card (real, filled)', Notes=''),
        dict(Domain='Service', Category='Elevator advertising', Item='LCD screen (tower lobby)', Unit='VND/screen/month',
             UnitPrice=1212121, AdminFeePerStaff=None, TotalPerStaff=1212121, SampleSize=1,
             Source='Master rate card (real, filled)', Notes=''),
        dict(Domain='Service', Category='Elevator advertising', Item='LCD screen (basement lobby)', Unit='VND/screen/month',
             UnitPrice=1060606, AdminFeePerStaff=None, TotalPerStaff=1060606, SampleSize=1,
             Source='Master rate card (real, filled)', Notes=''),
        dict(Domain='Service', Category='Parking (market reference)', Item='Marq — car, monthly', Unit='VND/vehicle/month',
             UnitPrice=4812500, AdminFeePerStaff=None, TotalPerStaff=4812500, SampleSize=1,
             Source="A&K Tower's own market survey table", Notes='Reference/comparable market price, NOT a Savills-set rate'),
        dict(Domain='Service', Category='Parking (market reference)', Item='Marq — motorbike, monthly', Unit='VND/vehicle/month',
             UnitPrice=217000, AdminFeePerStaff=None, TotalPerStaff=217000, SampleSize=1,
             Source="A&K Tower's own market survey table", Notes='Reference/comparable market price, NOT a Savills-set rate'),
        dict(Domain='Service', Category='Parking (market reference)', Item='Estella Heights — car, monthly', Unit='VND/vehicle/month',
             UnitPrice=1620000, AdminFeePerStaff=None, TotalPerStaff=1620000, SampleSize=1,
             Source="A&K Tower's own market survey table", Notes='Reference/comparable market price, NOT a Savills-set rate'),
        dict(Domain='Service', Category='Parking (market reference)', Item='Habitat — car, monthly', Unit='VND/vehicle/month',
             UnitPrice=990000, AdminFeePerStaff=None, TotalPerStaff=990000, SampleSize=1,
             Source="A&K Tower's own market survey table", Notes='Reference/comparable market price, NOT a Savills-set rate'),
    ]


ROMAN_RE = re.compile(r'^[IVXLCDM]+$')


def _is_category_row(col_a):
    if col_a is None:
        return False
    s = str(col_a).strip()
    return bool(ROMAN_RE.match(s)) or (len(s) == 1 and s.isalpha() and s.isupper())


def build_capex_rates():
    # Real bug, found 2026-08-27 when a second file landed in this folder: glob.glob()'s order is
    # filesystem-dependent, not sorted, so [0] could silently pick either file depending on how
    # Windows happens to list the directory that run — including the STALE one, with no warning.
    # Newest-by-mtime is the correct, deterministic choice (a replacement file is always meant to
    # supersede, per how "Danh mục Capex 2026 2.xlsx" relates to "Danh mục Capex 2026.xlsx").
    candidates = sorted(glob.glob(os.path.join(PROJECT_ROOT, 'input', 'capex', '*.xlsx')), key=os.path.getmtime)
    capex_file = candidates[-1]
    wb_capex = openpyxl.load_workbook(capex_file, data_only=True)
    capex_sheets = ['1. Capex MO', '2. Capex M&E', '3. Capex khu công cộng']
    for sn in list(wb_capex.sheetnames):
        if 'tiện ích' in sn.lower():
            capex_sheets.append(sn)

    out = []
    for sn in capex_sheets:
        if sn not in wb_capex.sheetnames:
            continue
        ws = wb_capex[sn]
        current_category = None
        for row in ws.iter_rows(min_row=1, max_row=ws.max_row, values_only=True):
            col_a = row[0] if len(row) > 0 else None
            col_b = row[1] if len(row) > 1 else None
            nums = [v for v in row if isinstance(v, (int, float)) and not isinstance(v, bool)]
            unit = row[2] if len(row) > 2 and isinstance(row[2], str) and ('/' in str(row[2]) or 'iece' in str(row[2]) or 'et' in str(row[2])) else None
            if _is_category_row(col_a) and isinstance(col_b, str) and col_b.strip():
                current_category = col_b.strip().split('/')[0].strip()
            elif isinstance(col_a, (int, float)) and isinstance(col_b, str) and col_b.strip() and current_category:
                item_name = col_b.strip().split('/')[0].strip()
                if len(nums) >= 2:
                    unit_price = nums[-2]
                    out.append(dict(
                        Domain='Capex', Category=current_category, Item=item_name,
                        Unit=(unit or 'unit'), UnitPrice=round(unit_price) if isinstance(unit_price, (int, float)) else None,
                        AdminFeePerStaff=None, TotalPerStaff=None, SampleSize=1,
                        Source=f'{sn} (master capex catalog, real, filled)', Notes='',
                    ))
    out.sort(key=lambda x: x['UnitPrice'] or 0, reverse=True)
    return out


def write_flat_csv(all_rows, path):
    cols = ['Domain', 'Category', 'Item', 'Unit', 'UnitPrice', 'AdminFeePerStaff', 'TotalPerStaff', 'SampleSize', 'Source', 'Notes']
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(all_rows)


def write_readable_excel(staff_rows, service_rows, capex_rows, path):
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    title_font = Font(bold=True, size=14)
    subtitle_font = Font(italic=True, color="595959")
    missing_font = Font(italic=True, color="C00000")
    thin = Side(style='thin', color='BFBFBF')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    center = Alignment(horizontal='center', vertical='center')
    left = Alignment(horizontal='left', vertical='center', wrap_text=True)
    money_fmt = '#,##0'

    wb = openpyxl.Workbook()

    def write_sheet(ws, title, subtitle, rows, cols_shown):
        ws['A1'] = title
        ws['A1'].font = title_font
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(cols_shown))
        ws['A2'] = subtitle
        ws['A2'].font = subtitle_font
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(cols_shown))
        ws.row_dimensions[2].height = 28
        r = 4
        for c, h in enumerate(cols_shown, start=1):
            cell = ws.cell(row=r, column=c, value=h)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = center
            cell.border = border
        r += 1
        for row in rows:
            for c, key in enumerate(cols_shown, start=1):
                v = row.get(key)
                cell = ws.cell(row=r, column=c, value=v if v is not None else 'NOT FOUND')
                cell.border = border
                cell.alignment = left if key in ('Item', 'Category', 'Source', 'Notes') else center
                if key in ('UnitPrice', 'AdminFeePerStaff', 'TotalPerStaff') and isinstance(v, (int, float)):
                    cell.number_format = money_fmt
                if v is None:
                    cell.font = missing_font
            r += 1
        return r

    ws1 = wb.active
    ws1.title = 'Staff - Per Position'
    write_sheet(ws1, 'Staff Rate Card — Price for 1 Staff (per position, average across real records)',
                'PER-UNIT rate card, not a portfolio total.',
                staff_rows,
                ['Category', 'Item', 'Unit', 'UnitPrice', 'AdminFeePerStaff', 'TotalPerStaff', 'SampleSize', 'Source'])
    for col, w in {'A': 16, 'B': 40, 'C': 18, 'D': 16, 'E': 18, 'F': 16, 'G': 12, 'H': 40}.items():
        ws1.column_dimensions[col].width = w
    ws1.freeze_panes = 'A5'

    ws2 = wb.create_sheet('Service - Per Item')
    write_sheet(ws2, 'Service Cost Rate Card — Price for 1 Position/Device/Item',
                'Security/Cleaning/Landscape = A&K reference. Scent/Consumable/Elevator = real master rates. Garbage = not found.',
                service_rows,
                ['Category', 'Item', 'Unit', 'UnitPrice', 'SampleSize', 'Source', 'Notes'])
    for col, w in {'A': 24, 'B': 42, 'C': 20, 'D': 16, 'E': 12, 'F': 45, 'G': 40}.items():
        ws2.column_dimensions[col].width = w
    ws2.freeze_panes = 'A5'

    ws3 = wb.create_sheet('Capex - Per Item')
    write_sheet(ws3, 'Capex Rate Card — Price for 1 Unit of Equipment',
                'Standard-scenario unit prices per item.',
                capex_rows,
                ['Category', 'Item', 'Unit', 'UnitPrice', 'Source'])
    for col, w in {'A': 30, 'B': 45, 'C': 14, 'D': 16, 'E': 30}.items():
        ws3.column_dimensions[col].width = w
    ws3.freeze_panes = 'A5'

    wb.save(path)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)

    staff_rows = build_staff_rates()
    service_rows = build_service_rates()
    capex_rows = build_capex_rates()
    all_rows = staff_rows + service_rows + capex_rows

    csv_path = os.path.join(DATA_DIR, 'Fact_MasterRateCard.csv')
    write_flat_csv(all_rows, csv_path)
    print('Saved CSV:', csv_path, '| rows:', len(all_rows))

    xlsx_path = os.path.join(OUT_DIR, 'Master_Rate_Card.xlsx')
    write_readable_excel(staff_rows, service_rows, capex_rows, xlsx_path)
    print('Saved Excel:', xlsx_path)
    print('Staff rows:', len(staff_rows), '| Service rows:', len(service_rows), '| Capex rows:', len(capex_rows))


if __name__ == '__main__':
    main()
