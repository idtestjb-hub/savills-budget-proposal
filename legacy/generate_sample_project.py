# RETIRED 2026-10-04 (backlog A7): paths point at a folder that does not exist; do not run. See legacy/README.md.
"""
Generates a fictional sample consulting budget from template 2026.xlsx, seeded from a real
project's rates +/-15%, plus a Comparison sheet against 2 other real projects.

This is the manual, one-off version of what the Copilot Studio agent's "Generate Budget File"
tool should eventually do automatically (see output/copilot_studio_package/02_FillBudgetTemplate.osts
for the Office Script version of the same cell-fill logic, and 03_Copilot_Studio_Topic_Spec.md
for how it's meant to be wired into Power Automate).

Produces: output/<PROJECT_NAME> - Sample Consulting Budget 2026.xlsx
  - template 2026.xlsx copied, with ~25 designated input cells filled (project name, GFA/NFA/
    units, security/cleaning/landscape unit prices, consumable/garbage/elevator/parking inputs)
  - a new "Comparison" sheet added (20 sheets total -- the template's original 19 + this one,
    deliberately NOT expanded to a bloated A&K-style 78-sheet structure)

Never touches a formula cell -- only ever writes to the same ~25 coordinates documented in
05_Project_Intake_Template.md / the Office Script. If template 2026.xlsx's layout changes,
update PROJECT_NAME cell / SECTION comments below to match.
"""
import os
import random

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from common_utils_v2 import repair_workbook

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# ---- Editable per run ----
PROJECT_NAME = 'SOLIS BAY RESIDENCE'
OUT_FILENAME = f'{PROJECT_NAME.title()} - Sample Consulting Budget 2026.xlsx'
SEED = 2026

# Reference rates this sample is seeded from (A&K Tower, the real project) -- swap these for a
# different reference project's verified numbers (see
# output/copilot_studio_package/data/Dim_Property_v2_verified.csv) to reseed from elsewhere.
AK_APT_GFA, AK_APT_NFA, AK_APT_UNITS = 40863.4, 59285.7, 1155
AK_SECURITY_UNIT = 17500000
AK_CLEANING_UNIT = 8000000
AK_LANDSCAPE_UNIT = 11000000
AK_MGMT_STAFF, AK_SUBCON_STAFF, AK_RESIDENT_GUEST, AK_OTHER_VISITOR = 19, 13, 50, 100

# Comparable projects for the Comparison sheet (real, from Budget_PowerBI_Model.xlsx fact tables)
COMPARABLE_A = {
    'name': 'A&K Tower (Real)', 'duty_entries': 565, 'positions': 35, 'staff_cost': 439296000,
    'avg_salary': 11625000, 'headcount': 416, 'sheet_count': 77, 'formula_ratio': 0.421,
    'categories': {'Reception': 11, 'Security': 14, 'Technical': 2, 'Management': 1, 'Cleaning': 1, 'Other': 6},
}
COMPARABLE_B = {
    'name': '11D Thi Sách (Real)', 'duty_entries': 150, 'positions': 32, 'staff_cost': 220536000,
    'avg_salary': 9375000, 'headcount': None, 'sheet_count': 19, 'formula_ratio': 0.437,
    'categories': {'Reception': 7, 'Security': 9, 'Technical': 2, 'Management': 2, 'Cleaning': 1, 'Other': 11},
}


def j(x, lo=0.85, hi=1.15):
    return round(x * random.uniform(lo, hi))


def build():
    random.seed(SEED)
    template_path = os.path.join(BASE, 'input', 'template', 'template 2026.xlsx')
    out_dir = os.path.join(BASE, 'output')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, OUT_FILENAME)

    repaired = repair_workbook(template_path)
    wb = openpyxl.load_workbook(repaired, data_only=False)

    # ---- Master project name (drives Cover + 0.Info titles) ----
    wb['2. Budget-Management Fund']['AH5'] = PROJECT_NAME
    for sheet, coord in [
        ('A2. Bảo vệ - Security', 'C1'), ('A3. Vệ sinh - Cleaning', 'C1'), ('A4. Cây xanh - Landscape', 'C1'),
        ('A5. Trợ cấp PCCC', 'B1'), ('B1. Lịch Lễ tân', 'B1'), ('B2. Mùi hương - Scent', 'B2'),
        ('B3. Vật tư vệ sinh - Consumable', 'B1'), ('B3. Thu gom rác - Garbage coll ', 'B1'),
        ('B4. DT Quảng cáo - Elevator adv', 'B1'), ('B5. Đơn giá gửi xe - Parking pr', 'B1'),
    ]:
        wb[sheet][coord] = PROJECT_NAME

    # ---- 0. Info: property scale ----
    info = wb['0. Info']
    apt_gfa, apt_nfa, apt_units = j(AK_APT_GFA), j(AK_APT_NFA), j(AK_APT_UNITS)
    info['C8'], info['D8'], info['E8'] = apt_gfa, apt_nfa, apt_units
    info['I8'] = j(16500)
    parking_slots = j(150)
    info['F12'], info['I12'] = parking_slots, j(800000)

    # ---- A2/A3/A4: service unit prices ----
    wb['A2. Bảo vệ - Security']['G3'] = j(AK_SECURITY_UNIT)
    wb['A3. Vệ sinh - Cleaning']['K3'] = j(AK_CLEANING_UNIT)
    wb['A4. Cây xanh - Landscape']['K3'] = j(AK_LANDSCAPE_UNIT)

    # ---- A5: PCCC adjustment rate ----
    wb['A5. Trợ cấp PCCC']['C2'] = round(0.06 * random.uniform(0.85, 1.15), 4)

    # ---- B2: Scent device quantities ----
    scent = wb['B2. Mùi hương - Scent']
    scent['G6'], scent['G7'], scent['G8'] = max(1, j(2, 0.8, 1.2)), max(1, j(4, 0.8, 1.2)), max(1, j(3, 0.8, 1.2))

    # ---- B3 Consumable: unit counts & headcounts ----
    consumable = wb['B3. Vật tư vệ sinh - Consumable']
    consumable['C6'], consumable['C7'] = apt_units, 0
    mgmt_staff, subcon_staff = j(AK_MGMT_STAFF), j(AK_SUBCON_STAFF)
    consumable['D8'], consumable['D9'] = mgmt_staff, subcon_staff
    consumable['D10'], consumable['D11'] = j(AK_RESIDENT_GUEST), j(AK_OTHER_VISITOR)

    # ---- B3 Garbage: unit price (no real reference found -- market estimate, documented) ----
    garbage = wb['B3. Thu gom rác - Garbage coll ']
    garbage_price = j(180000)
    for coord in ['K5', 'K7', 'K8', 'K9', 'K10']:
        garbage[coord] = garbage_price
    garbage['C9'], garbage['C10'] = 0, 0

    # ---- B4 Elevator advertising: install counts ----
    elev = wb['B4. DT Quảng cáo - Elevator adv']
    elev['E5'], elev['F5'], elev['I5'] = j(9, 0.8, 1.2), j(9, 0.8, 1.2), j(6, 0.8, 1.2)
    elev['E6'], elev['I6'] = j(3, 0.8, 1.2), j(3, 0.8, 1.2)

    # ---- B5 Parking: reference market survey (from A&K's own comparable-project table) ----
    parking = wb['B5. Đơn giá gửi xe - Parking pr']
    ak_refs = [
        ('Marq', 4812500, 40000, 217000, 5000, 40000, 2000),
        ('Estella Heights', 1620000, 35000, 162000, 4000, None, None),
        ('Habitat', 990000, 30000, 110000, 5000, None, None),
        ('Sky Bridge', 1100000, 30000, 110000, 5000, 40000, 2000),
    ]
    for i, (name, car_m, car_t, moto_m, moto_t, bike_m, bike_t) in enumerate(ak_refs):
        r = 7 + i
        parking[f'B{r}'] = name
        parking[f'C{r}'] = j(car_m) if car_m else None
        parking[f'D{r}'] = car_t
        parking[f'E{r}'] = j(moto_m) if moto_m else None
        parking[f'F{r}'] = moto_t
        if bike_m:
            parking[f'G{r}'] = j(bike_m)
            parking[f'H{r}'] = bike_t

    wb.save(out_path)
    print('SAVED:', out_path)
    print(f'APT_GFA={apt_gfa} APT_NFA={apt_nfa} APT_UNITS={apt_units} PARKING_SLOTS={parking_slots}')

    add_comparison_sheet(out_path)
    return out_path


def add_comparison_sheet(path):
    """Adds the 20th sheet: Sample Project vs. 2 real comparables, from Budget_PowerBI_Model.xlsx facts."""
    wb = openpyxl.load_workbook(path, data_only=False)

    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    section_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    section_font = Font(bold=True)
    thin = Side(style='thin', color='BFBFBF')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    center = Alignment(horizontal='center', vertical='center')
    left = Alignment(horizontal='left', vertical='center', wrap_text=True)

    if 'Comparison' in wb.sheetnames:
        del wb['Comparison']
    ws = wb.create_sheet('Comparison')

    ws['A1'] = f'CROSS-PROJECT COMPARISON — {PROJECT_NAME} (SAMPLE, NOT REAL) vs. 2 REAL SAVILLS PROJECTS'
    ws['A1'].font = Font(bold=True, size=13)
    ws['A2'] = (f'{PROJECT_NAME.title()} is a fictional prospect budget generated from template 2026.xlsx for '
                'new-client consulting pitches. It is NOT a real project and NOT real client data.')
    ws['A2'].font = Font(italic=True, color='C00000')
    ws.merge_cells('A2:D2')
    ws.row_dimensions[2].height = 30

    headers = ['Metric', f'{PROJECT_NAME.title()} (Sample)', COMPARABLE_A['name'], COMPARABLE_B['name']]
    r = 4
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center
        cell.border = border
    r += 1

    def section(row, label):
        ws.cell(row=row, column=1, value=label).font = section_font
        for c in range(1, 5):
            ws.cell(row=row, column=c).fill = section_fill
            ws.cell(row=row, column=c).border = border
        return row + 1

    def data_row(row, label, sample, a, b):
        for col, v in enumerate([label, sample, a, b], start=1):
            cell = ws.cell(row=row, column=col, value=v)
            cell.border = border
            cell.alignment = left if col == 1 else center
        return row + 1

    r = section(r, 'STRUCTURE')
    r = data_row(r, 'Total duty-roster entries', 'n/a (template-based)', COMPARABLE_A['duty_entries'], COMPARABLE_B['duty_entries'])
    r = data_row(r, 'Distinct staff positions', 'n/a', COMPARABLE_A['positions'], COMPARABLE_B['positions'])
    r = data_row(r, 'Total staff cost (VND)', 'n/a (see A2-B5 sheets)', COMPARABLE_A['staff_cost'], COMPARABLE_B['staff_cost'])
    r = data_row(r, 'Avg gross salary (VND)', 'n/a', COMPARABLE_A['avg_salary'], COMPARABLE_B['avg_salary'])
    r = data_row(r, 'Workbook sheet count', 20, COMPARABLE_A['sheet_count'], COMPARABLE_B['sheet_count'])
    r = data_row(r, 'Avg formula ratio', '~0.45', COMPARABLE_A['formula_ratio'], COMPARABLE_B['formula_ratio'])

    r += 1
    ws.cell(row=r, column=1, value='HEADCOUNT BY CATEGORY').font = section_font
    r += 1
    for c, h in enumerate(['Category', f'{PROJECT_NAME.title()} (Sample)', COMPARABLE_A['name'], COMPARABLE_B['name']], start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center
        cell.border = border
    r += 1
    for cat in ['Reception', 'Security', 'Cleaning', 'Technical', 'Management', 'Other']:
        r = data_row(r, cat, 'n/a', COMPARABLE_A['categories'].get(cat, 'n/a'), COMPARABLE_B['categories'].get(cat, 'n/a'))

    widths = {'A': 42, 'B': 30, 'C': 24, 'D': 22}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w

    wb.save(path)
    print('Comparison sheet added. Sheets now:', len(wb.sheetnames))


if __name__ == '__main__':
    build()
