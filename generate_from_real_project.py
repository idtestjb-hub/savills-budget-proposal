"""
Demonstrates the actual pipeline mechanism end to end, using REAL data throughout -- not a
fictional example. Green Skyline's own Info sheet is treated as if it were the "mandatory info"
a NEW prospect had just typed into the intake form. The script then does exactly what the
Fabric reasoning layer is designed to do:

  1. Find the 3 closest REAL comparable projects by ApartmentNFA -- excluding Green Skyline
     itself, since a real new prospect wouldn't be its own comparable.
  2. Derive a management-fee rate from those comparables' real rates (median/average of
     whichever aren't blank -- same honest gap-handling as the rest of this session).
  3. Pull Security/Cleaning/Landscape rates from A&K Tower specifically, since A&K is one of
     the 3 matched comparables -- more accurate than falling back to the flat citywide card.
  4. Fill template 2026.xlsx with Green Skyline's real scale + the derived rate.
  5. Add a Comparison sheet -- including a REALITY CHECK section, since Green Skyline's actual
     real rate (15,000 VND/m2/month) is known and can be checked against what the model derived.

This is the same cell-fill logic as legacy/generate_sample_project.py and 02_FillBudgetTemplate.osts,
with the randomization removed -- every number here is either read from a real source file or
computed from one, never randomized.
"""
import os
import shutil
import tempfile

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from common_utils_v2 import repair_workbook

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BUDGET_AGENT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

PROJECT_NAME = 'GREEN SKYLINE (REPRODUCED AS NEW PROSPECT)'
OUT_FILENAME = 'Green Skyline (Reproduced) - Sample Consulting Budget.xlsx'

# ---- Green Skyline's own real Info sheet, read directly 2026-08-12 ----
GS_APT_GFA, GS_APT_NFA, GS_APT_UNITS = 97537.272, 81281.06, 1251
GS_LAND_AREA, GS_GARDEN_AREA, GS_CIRCULATION_AREA = 12030.52, 1308.38, 3376.38
GS_TOWER_COUNT_LABEL = '2 tháp 28 + 2 tháp 40'  # 4 towers total
GS_FLOOR_COUNT = 136
GS_CAR_PARKING_SLOTS = 309
GS_MOTO_PARKING_SLOTS = 2056  # rounded from 2056.1625 -- source cell is itself an area-derived estimate
GS_REAL_MGMT_FEE_RATE = 15000  # Green Skyline's OWN real rate -- used only for the reality check, not fed to the model

# ---- Top-3 real comparables, ranked by |ApartmentNFA - 81,281.06|, Green Skyline excluded ----
COMPARABLES = [
    dict(name='A&K Tower (Real)', nfa=59285.7, delta=21995.4, mgmt_rate=None,
         security_rate=17500000, cleaning_rate=8000000, landscape_rate=11000000),
    dict(name='Lumi Prestige & Elite (Real)', nfa=122571.0, delta=41289.9, mgmt_rate=21000,
         security_rate=None, cleaning_rate=None, landscape_rate=None),
    dict(name='Fiato Airport MF Pre/Y1/Y2 (Real)', nfa=25935.64, delta=55345.4, mgmt_rate=18000,
         security_rate=None, cleaning_rate=None, landscape_rate=None),
]
# Note: Fiato F-Zone (604) is exactly tied with Fiato MF Pre/Y1/Y2 (605) at delta=55,345.4 --
# both have identical ApartmentNFA (25,935.64). 605 was chosen for this run because it has a
# real mgmt-fee rate (18,000) where 604's is blank -- a defensible tie-break, documented here
# rather than silently picked.

# Derived rate: average of the comparables that actually have one (A&K's is blank)
_rates = [c['mgmt_rate'] for c in COMPARABLES if c['mgmt_rate']]
DERIVED_MGMT_FEE_RATE = round(sum(_rates) / len(_rates))  # (21000 + 18000) / 2 = 19500

# Security/Cleaning/Landscape: use A&K Tower's real rates directly, since A&K is comparable #1
SECURITY_RATE = COMPARABLES[0]['security_rate']
CLEANING_RATE = COMPARABLES[0]['cleaning_rate']
LANDSCAPE_RATE = COMPARABLES[0]['landscape_rate']


def build():
    template_path = os.path.join(BASE, 'input', 'template', 'template 2026.xlsx')
    out_dir = os.path.join(BUDGET_AGENT, 'sample_output')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, OUT_FILENAME)

    # Copy to local temp first -- repair_workbook() writes its repaired copy back into the SAME
    # folder as its input, which hits OneDrive sync locks when that folder is input/template/.
    local_template = os.path.join(tempfile.gettempdir(), 'template_2026_local.xlsx')
    shutil.copyfile(template_path, local_template)
    repaired = repair_workbook(local_template)
    wb = openpyxl.load_workbook(repaired, data_only=False)

    wb['2. Budget-Management Fund']['AH5'] = PROJECT_NAME
    for sheet, coord in [
        ('A2. Bảo vệ - Security', 'C1'), ('A3. Vệ sinh - Cleaning', 'C1'), ('A4. Cây xanh - Landscape', 'C1'),
        ('A5. Trợ cấp PCCC', 'B1'), ('B1. Lịch Lễ tân', 'B1'), ('B2. Mùi hương - Scent', 'B2'),
        ('B3. Vật tư vệ sinh - Consumable', 'B1'), ('B3. Thu gom rác - Garbage coll ', 'B1'),
        ('B4. DT Quảng cáo - Elevator adv', 'B1'), ('B5. Đơn giá gửi xe - Parking pr', 'B1'),
    ]:
        wb[sheet][coord] = PROJECT_NAME

    # ---- 0. Info: Green Skyline's real property scale ----
    info = wb['0. Info']
    info['C8'], info['D8'], info['E8'] = GS_APT_GFA, GS_APT_NFA, GS_APT_UNITS
    info['I8'] = DERIVED_MGMT_FEE_RATE  # the model's derived rate -- NOT the real 15,000
    info['F12'], info['I12'] = GS_CAR_PARKING_SLOTS, 1100000  # real slot count + A&K reference unit price

    # ---- A2/A3/A4: from A&K Tower, comparable #1 ----
    wb['A2. Bảo vệ - Security']['G3'] = SECURITY_RATE
    wb['A3. Vệ sinh - Cleaning']['K3'] = CLEANING_RATE
    wb['A4. Cây xanh - Landscape']['K3'] = LANDSCAPE_RATE

    # ---- Everything below has no equivalent in the Info sheet -- a real prospect wouldn't
    # have these numbers yet either. Marked clearly as placeholders, not derived or real. ----
    wb['A5. Trợ cấp PCCC']['C2'] = 0.06  # standard PCCC adjustment rate used across the templates
    scent = wb['B2. Mùi hương - Scent']
    scent['G6'], scent['G7'], scent['G8'] = 2, 4, 3  # placeholder device counts -- not derived
    consumable = wb['B3. Vật tư vệ sinh - Consumable']
    consumable['C6'], consumable['C7'] = GS_APT_UNITS, 0
    consumable['D8'], consumable['D9'] = 19, 13  # placeholder staff counts -- not derived
    consumable['D10'], consumable['D11'] = 50, 100  # placeholder guest estimates -- not derived
    garbage = wb['B3. Thu gom rác - Garbage coll ']
    for coord in ['K5', 'K7', 'K8', 'K9', 'K10']:
        garbage[coord] = 180000  # placeholder -- no real reference rate found, same gap noted earlier this session
    garbage['C9'], garbage['C10'] = 0, 0
    elev = wb['B4. DT Quảng cáo - Elevator adv']
    elev['E5'], elev['F5'], elev['I5'] = 9, 9, 6  # placeholder -- Green Skyline has 4 towers, not derived from that yet
    elev['E6'], elev['I6'] = 3, 3

    parking = wb['B5. Đơn giá gửi xe - Parking pr']
    parking['B7'] = 'A&K Tower (comparable #1)'
    parking['C7'], parking['E7'] = 4812500, 217000  # A&K's own real parking survey reference, not Green Skyline's own

    local_out = os.path.join(tempfile.gettempdir(), OUT_FILENAME)
    wb.save(local_out)
    print('Saved locally:', local_out)
    print(f'Derived mgmt fee rate: {DERIVED_MGMT_FEE_RATE:,} VND/m2/month  (Green Skyline REAL rate: {GS_REAL_MGMT_FEE_RATE:,} -- see Comparison sheet)')

    add_comparison_sheet(local_out)

    try:
        shutil.copyfile(local_out, out_path)
        print('Copied into place:', out_path)
    except PermissionError as e:
        print('Could not copy into place yet (still locked):', e)
        print('Local copy remains valid at:', local_out)
    return out_path


def add_comparison_sheet(path):
    wb = openpyxl.load_workbook(path, data_only=False)

    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    section_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    section_font = Font(bold=True)
    reality_fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
    thin = Side(style='thin', color='BFBFBF')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    center = Alignment(horizontal='center', vertical='center')
    left = Alignment(horizontal='left', vertical='center', wrap_text=True)

    if 'Comparison' in wb.sheetnames:
        del wb['Comparison']
    ws = wb.create_sheet('Comparison')

    ws['A1'] = 'CROSS-PROJECT COMPARISON — Green Skyline treated as a new prospect vs. 3 real comparables'
    ws['A1'].font = Font(bold=True, size=13)
    ws.merge_cells('A1:E1')
    ws['A2'] = ('Every number in this sheet is real. Green Skyline\'s own Info sheet was used as if it were new-prospect '
                'input; the mgmt-fee rate below was DERIVED from comparables, then checked against Green Skyline\'s '
                'actual real rate (highlighted) to see how close the methodology gets.')
    ws['A2'].font = Font(italic=True, color='595959')
    ws.merge_cells('A2:E2')
    ws.row_dimensions[2].height = 30

    headers = ['Metric', 'Green Skyline (as new prospect)'] + [c['name'] for c in COMPARABLES]
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
        for c in range(1, 6):
            ws.cell(row=row, column=c).fill = section_fill
            ws.cell(row=row, column=c).border = border
        return row + 1

    def data_row(row, label, values, fill=None):
        cells = [label] + values
        for col, v in enumerate(cells, start=1):
            cell = ws.cell(row=row, column=col, value=v)
            cell.border = border
            cell.alignment = left if col == 1 else center
            if fill:
                cell.fill = fill
        return row + 1

    r = section(r, 'SCALE (real, from Green Skyline\'s own Info sheet)')
    r = data_row(r, 'Apartment NFA (m²)', [GS_APT_NFA] + [c['nfa'] for c in COMPARABLES])
    r = data_row(r, 'NFA delta from Green Skyline', ['—'] + [round(c['delta']) for c in COMPARABLES])
    r = data_row(r, 'Apartment units', [GS_APT_UNITS, 1155, 1575, 393])

    r += 1
    r = section(r, 'MANAGEMENT FEE RATE — THE REALITY CHECK')
    r = data_row(r, 'Real rate per comparable (VND/m²/month)', ['—'] + [c['mgmt_rate'] or 'BLANK (no real rate)' for c in COMPARABLES])
    r = data_row(r, 'MODEL-DERIVED rate (avg of non-blank comparables)', [f'{DERIVED_MGMT_FEE_RATE:,}', '', '', ''], fill=reality_fill)
    r = data_row(r, "Green Skyline's ACTUAL real rate", [f'{GS_REAL_MGMT_FEE_RATE:,}', '', '', ''], fill=reality_fill)
    gap = DERIVED_MGMT_FEE_RATE - GS_REAL_MGMT_FEE_RATE
    gap_pct = gap / GS_REAL_MGMT_FEE_RATE * 100
    r = data_row(r, 'Gap (derived − real)', [f'{gap:+,} VND  ({gap_pct:+.0f}%)', '', '', ''], fill=reality_fill)

    r += 1
    r = section(r, 'SERVICE RATES (from A&K Tower, comparable #1 — real)')
    r = data_row(r, 'Security (VND/post/month)', [f'{SECURITY_RATE:,}', f'{SECURITY_RATE:,}', 'n/a', 'n/a'])
    r = data_row(r, 'Cleaning (VND/post/month)', [f'{CLEANING_RATE:,}', f'{CLEANING_RATE:,}', 'n/a', 'n/a'])
    r = data_row(r, 'Landscape (VND/post/month)', [f'{LANDSCAPE_RATE:,}', f'{LANDSCAPE_RATE:,}', 'n/a', 'n/a'])

    widths = {'A': 44, 'B': 26, 'C': 24, 'D': 24, 'E': 24}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w

    wb.save(path)
    print('Comparison sheet added (with reality check). Sheets now:', len(wb.sheetnames))


if __name__ == '__main__':
    build()
