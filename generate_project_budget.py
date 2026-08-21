"""
Unified generator — reads the ONE merged input file (Project_Budget_Input.xlsx, built by
build_project_input_form.py) and produces:

  1. A filled budget workbook (from template 2026.xlsx) with a Comparison sheet showing the
     2 nearest real comparable projects by ApartmentNFA, and the derived management-fee rate.
  2. A full calendar-month roster (same formula-driven engine as generate_roster.py), reading
     staffing ratios and demand from the same input file.

Replaces the earlier split (build_roster_input_form.py + generate_roster.py for the roster,
generate_from_real_project.py for the budget) with a single input -> two outputs pipeline, and
replaces that script's HARDCODED per-run comparable list with a dynamic lookup against
master_comparables.py (built from real, directly-verified project data — see that module).

Comparable matching is real, not fictional: nearest 2 by |ApartmentNFA delta|, excluding the
input project itself by name if it happens to match one already in the master table (so
re-running this against a real project's own numbers, e.g. Green Skyline, doesn't compare it
to itself). The "reality check" row on the Comparison sheet only appears when the input
project's OWN real rate is independently known from the master table — for a genuinely new,
unlisted prospect, it correctly reports "not applicable — new prospect."
"""
import os
import math
import shutil
import tempfile
import calendar as cal

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import FormulaRule

from common_utils_v2 import repair_workbook
from master_comparables import (
    MASTER_COMPARABLES, SECURITY_RATE_CITYWIDE, CLEANING_RATE_CITYWIDE, LANDSCAPE_RATE_CITYWIDE,
    RATE_CARD_SOURCE, nearest_comparables, derive_mgmt_rate,
)

SOURCE_DIR = os.path.dirname(__file__)
BUDGET_AGENT = os.path.abspath(os.path.join(SOURCE_DIR, '..'))
BASE = os.path.abspath(os.path.join(SOURCE_DIR, '..', '..'))

INPUT_PATH = os.path.join(BUDGET_AGENT, 'reports', 'Project_Budget_Input.xlsx')
TEMPLATE_PATH = os.path.join(BASE, 'input', 'template', 'template 2026.xlsx')
BUDGET_OUT_DIR = os.path.join(BUDGET_AGENT, 'sample_output')
ROSTER_OUT_DIR = os.path.join(BUDGET_AGENT, 'reports')
ROSTER_FINAL_OUT = os.path.join(ROSTER_OUT_DIR, 'Roster_Demand_Model.xlsx')
ROSTER_OUT = os.path.join(tempfile.gettempdir(), 'Roster_Demand_Model.xlsx')

MAX_DAYS = 31
DAY_COL_START = 3
DAY_COL_END = DAY_COL_START + MAX_DAYS - 1
COL_DAYOFF = DAY_COL_END + 1
COL_SHIFTCODE = DAY_COL_END + 2

PRODUCT_ROWS = ['Apartment', 'Officetel', 'Shophouse', 'Shopping Mall', 'Nursery / Nhà trẻ']

# Ratio-driven Staffing Demand rows — matches the ROUNDUP(...) formulas build_project_input_form.py
# bakes into the Staffing Demand sheet's "Staff On Duty / Day" cells for these exact position
# names. Recomputed HERE in Python (not read from the cell's cached formula value) so a PM who
# edits Project Info or Roster Setup without reopening the file in Excel to force a recalc still
# gets a fresh, correct number — openpyxl reads cached formula results, which go stale silently
# otherwise. Any OTHER position in the sheet (CCTV/Reception — fixed, not ratio-driven — or any
# custom row a PM adds) is left exactly as typed; only these 5 known ratio-driven rows are touched.
RATIO_DRIVEN_STAFFING = {
    'Security - Main Gate (Morning)': lambda p, r: (
        p['gate_count'] * r['staff_per_gate'], f"Gate Count ({p['gate_count']:g}) × Staff per Gate ({r['staff_per_gate']:g})"),
    'Security - Main Gate (Afternoon)': lambda p, r: (
        p['gate_count'] * r['staff_per_gate'], f"Gate Count ({p['gate_count']:g}) × Staff per Gate ({r['staff_per_gate']:g})"),
    'Security - Main Gate (Night)': lambda p, r: (
        p['gate_count'] * r['staff_per_gate'], f"Gate Count ({p['gate_count']:g}) × Staff per Gate ({r['staff_per_gate']:g})"),
    'Security - Patrol / Open Space': lambda p, r: (
        p['open_space'] / r['sqm_per_patrol'], f"Open Space ({p['open_space']:,.0f} m²) ÷ m² per Patrol Staff ({r['sqm_per_patrol']:g})"),
    'Cleaning - Common Area': lambda p, r: (
        p['open_space'] / r['sqm_per_cleaner'], f"Open Space ({p['open_space']:,.0f} m²) ÷ m² per Cleaner ({r['sqm_per_cleaner']:g})"),
    'Cleaning - Supervisor': lambda p, r: (
        p['towers'] / r['towers_per_supervisor'], f"Tower Count ({p['towers']:g}) ÷ Towers per Supervisor ({r['towers_per_supervisor']:g})"),
    'Gardener / Landscape': lambda p, r: (
        p['garden_area'] / r['sqm_per_gardener'], f"Garden Area ({p['garden_area']:,.0f} m²) ÷ m² per Gardener ({r['sqm_per_gardener']:g})"),
}


def read_input(path):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found. Run build_project_input_form.py first, fill it in, then re-run this script."
        )
    wb = openpyxl.load_workbook(path, data_only=True)

    pi = wb['Project Info']
    segment = str(pi['B3'].value or 'Residential').strip()
    if segment.lower() != 'residential':
        raise ValueError(
            f"Project Info!B3 (Property Segment) = '{segment}' — this pipeline only supports Residential today. "
            "Its cost logic (management-fee rate, staffing pattern, Capex/OPEX scaling) is Residential "
            "apartment-building math, comparable-matched on Apartment NFA; none of it applies to a Commercial "
            "property, and running it anyway would silently produce wrong numbers rather than a useful budget. "
            "Real Commercial comparable data exists (Dim_Property_Commercial.csv) but nothing in this generator "
            "reads it yet — that's a real scoping/build task, not a quick fix. Set Project Info!B3 back to "
            "'Residential' to continue."
        )
    project = dict(
        name=pi['B5'].value, segment=segment, site_area=pi['B6'].value, garden_area=pi['B7'].value,
        open_space=pi['B8'].value, floor_count=pi['B9'].value, towers=pi['B10'].value,
        car_slots=pi['B21'].value, moto_slots=pi['B22'].value,
        has_pool=str(pi['B25'].value).strip().lower() == 'yes',
        pool_area=pi['B26'].value, gate_count=pi['B27'].value,
    )
    products = {}
    for i, name in enumerate(PRODUCT_ROWS, start=14):
        gfa = pi.cell(row=i, column=2).value or 0
        nfa = pi.cell(row=i, column=3).value or 0
        units = pi.cell(row=i, column=4).value or 0
        products[name] = dict(gfa=gfa, nfa=nfa, units=units)
    project['products'] = products
    project['apartment_gfa'] = products['Apartment']['gfa']
    project['apartment_nfa'] = products['Apartment']['nfa']
    project['apartment_units'] = products['Apartment']['units']
    # Whole-building NFA (sum across all product rows) — this is the driver comparable matching
    # uses now (master_comparables.py switched from ApartmentNFA to TotalNFA so the ~75 Master
    # List comparables, which only have whole-building NFA, can be ranked on the same basis as
    # the 7 hand-verified ones). Apartment NFA above is still what management-fee REVENUE uses.
    project['total_nfa'] = sum(p['nfa'] for p in products.values())
    project['total_gfa'] = sum(p['gfa'] for p in products.values())
    if not project['apartment_nfa']:
        raise ValueError("Project Info!C14:D14 (Apartment GFA/NFA) must be filled in — comparable "
                          "matching is by Apartment NFA.")

    rs = wb['Roster Setup']
    ratios = dict(
        staff_per_gate=rs['B4'].value, sqm_per_patrol=rs['B5'].value,
        sqm_per_cleaner=rs['B6'].value, towers_per_supervisor=rs['B7'].value,
        sqm_per_gardener=rs['B8'].value,
    )
    month, year = rs['B12'].value, rs['B13'].value
    if not month or not year:
        raise ValueError("Roster Setup!B12 (Month) and B13 (Year) must both be filled in.")
    month, year = int(month), int(year)

    holiday_days = set()
    for r in range(20, 30):
        d = rs.cell(row=r, column=1).value
        if d is None or str(d).strip() == '':
            continue
        holiday_days.add(int(d))

    ws_demand = wb['Staffing Demand']
    demand = []
    for r in range(5, ws_demand.max_row + 1):
        pos = ws_demand.cell(row=r, column=1).value
        code = ws_demand.cell(row=r, column=2).value
        staff = ws_demand.cell(row=r, column=3).value
        days = ws_demand.cell(row=r, column=4).value
        rate = ws_demand.cell(row=r, column=5).value
        if not pos or not code:
            continue
        ratio_fn = RATIO_DRIVEN_STAFFING.get(str(pos))
        if ratio_fn:
            raw, basis = ratio_fn(project, ratios)
            staff = math.ceil(raw)
            basis = f'{basis} = {raw:.2f}, rounded up'
        elif staff is None:
            raise ValueError(
                f"Staffing Demand row {r} ('{pos}'): Staff On Duty / Day is blank and this position isn't one of "
                "the ratio-driven rows this script knows how to compute — enter a value directly."
            )
        else:
            basis = 'PM-entered value (Staffing Demand sheet, not ratio-driven)'
        demand.append(dict(
            Position=str(pos), ShiftCode=str(code),
            StaffPerDay=int(round(staff)), CoverageDays=int(days), AvgDailyRate=float(rate),
            SourceRow=r, Basis=basis,
        ))
    if not demand:
        raise ValueError("Staffing Demand sheet has no complete rows.")

    return project, ratios, month, year, holiday_days, demand


# ============================================================================================
# Budget workbook
# ============================================================================================

def build_budget(project):
    top2 = nearest_comparables(project['apartment_nfa'], exclude_name=project['name'], n=2)
    all_ranked = nearest_comparables(project['apartment_nfa'], exclude_name=project['name'], n=len(MASTER_COMPARABLES))
    derived_rate, rate_note = derive_mgmt_rate(top2, all_ranked=all_ranked)
    if derived_rate is None:
        raise ValueError("Could not derive a management-fee rate — no comparable in the master table has one.")

    own_real = next((c for c in MASTER_COMPARABLES
                      if c['name'].strip().lower() in project['name'].strip().lower() and c['mgmt_rate']), None)

    print(f"Comparables for {project['name']} (ApartmentNFA={project['apartment_nfa']:,.0f} m²):")
    for c in top2:
        rate_str = f"{c['mgmt_rate']:,} ({c['mgmt_rate_vat']})" if c['mgmt_rate'] else 'no real rate'
        print(f"  - {c['name']}: NFA={c['nfa']:,.0f}, delta={abs(c['nfa']-project['apartment_nfa']):,.0f}, rate={rate_str}")
    print(f"Derived mgmt fee rate: {derived_rate:,} VND/m²/month" + (f"  [{rate_note}]" if rate_note else ''))
    if own_real:
        gap = derived_rate - own_real['mgmt_rate']
        print(f"Reality check: {project['name']}'s own real rate is {own_real['mgmt_rate']:,} "
              f"({own_real['mgmt_rate_vat']}) — gap {gap:+,} ({gap/own_real['mgmt_rate']*100:+.0f}%)")

    local_template = os.path.join(tempfile.gettempdir(), 'template_2026_local.xlsx')
    shutil.copyfile(TEMPLATE_PATH, local_template)
    repaired = repair_workbook(local_template)
    wb = openpyxl.load_workbook(repaired, data_only=False)

    wb['2. Budget-Management Fund']['AH5'] = project['name']
    for sheet, coord in [
        ('A2. Bảo vệ - Security', 'C1'), ('A3. Vệ sinh - Cleaning', 'C1'), ('A4. Cây xanh - Landscape', 'C1'),
        ('A5. Trợ cấp PCCC', 'B1'), ('B1. Lịch Lễ tân', 'B1'), ('B2. Mùi hương - Scent', 'B2'),
        ('B3. Vật tư vệ sinh - Consumable', 'B1'), ('B3. Thu gom rác - Garbage coll ', 'B1'),
        ('B4. DT Quảng cáo - Elevator adv', 'B1'), ('B5. Đơn giá gửi xe - Parking pr', 'B1'),
    ]:
        wb[sheet][coord] = project['name']

    # ---- 0. Info: user-input scale + derived rate. Template's fee table only has rows for
    # Apartment(8)/Officetel(9)/Office(10)/Shopping Mall(11) — Shophouse and Nursery entered on
    # the input form have no equivalent row in this template version, so they're not written here.
    info = wb['0. Info']
    info['C8'], info['D8'], info['E8'] = project['apartment_gfa'], project['apartment_nfa'], project['apartment_units']
    info['I8'] = derived_rate
    if project['products']['Officetel']['nfa']:
        p = project['products']['Officetel']
        info['C9'], info['D9'], info['E9'] = p['gfa'], p['nfa'], p['units']
    if project['products']['Shopping Mall']['nfa']:
        p = project['products']['Shopping Mall']
        info['C11'], info['D11'], info['E11'] = p['gfa'], p['nfa'], p['units']
    info['F12'] = project['car_slots']
    # I12 (parking mgmt fee/m²) left blank -- no consistent real per-project reference was found
    # across comparables (each real file's own parking fee differs and isn't NFA-comparable the
    # way the apartment fee is); PM to confirm before this line item is trusted.

    # ---- A2/A3/A4: flat citywide real rates (Fact_MasterRateCard.csv — same for every project) ----
    wb['A2. Bảo vệ - Security']['G3'] = SECURITY_RATE_CITYWIDE
    wb['A3. Vệ sinh - Cleaning']['K3'] = CLEANING_RATE_CITYWIDE
    wb['A4. Cây xanh - Landscape']['K3'] = LANDSCAPE_RATE_CITYWIDE

    # ---- Everything below has no equivalent on the input form -- a real prospect wouldn't have
    # these numbers yet either. Marked clearly as placeholders, not derived or real. ----
    wb['A5. Trợ cấp PCCC']['C2'] = 0.06
    scent = wb['B2. Mùi hương - Scent']
    scent['G6'], scent['G7'], scent['G8'] = 2, 4, 3
    consumable = wb['B3. Vật tư vệ sinh - Consumable']
    consumable['C6'], consumable['C7'] = project['apartment_units'], 0
    consumable['D8'], consumable['D9'] = 19, 13
    consumable['D10'], consumable['D11'] = 50, 100
    garbage = wb['B3. Thu gom rác - Garbage coll ']
    for coord in ['K5', 'K7', 'K8', 'K9', 'K10']:
        garbage[coord] = 180000
    garbage['C9'], garbage['C10'] = 0, 0
    elev = wb['B4. DT Quảng cáo - Elevator adv']
    elev['E5'], elev['F5'], elev['I5'] = 9, 9, 6
    elev['E6'], elev['I6'] = 3, 3
    parking = wb['B5. Đơn giá gửi xe - Parking pr']
    parking['B7'] = 'Placeholder — no per-project parking-fee reference in master data yet'
    parking['C7'], parking['E7'] = 4812500, 217000  # Fact_MasterRateCard.csv market reference (Marq), for context only

    out_filename = f"{project['name']} - Sample Consulting Budget.xlsx"
    local_out = os.path.join(tempfile.gettempdir(), out_filename)
    wb.save(local_out)
    print('Saved locally:', local_out)

    add_comparison_sheet(local_out, project, top2, derived_rate, rate_note, own_real)

    os.makedirs(BUDGET_OUT_DIR, exist_ok=True)
    out_path = os.path.join(BUDGET_OUT_DIR, out_filename)
    try:
        shutil.copyfile(local_out, out_path)
        print('Copied into place:', out_path)
    except PermissionError as e:
        print('Could not copy into place yet (still locked):', e)
        print('Local copy remains valid at:', local_out)
        out_path = local_out
    return out_path


def add_comparison_sheet(path, project, comparables, derived_rate, rate_note, own_real):
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

    ws['A1'] = f"CROSS-PROJECT COMPARISON — {project['name']} vs. the 2 nearest real comparables by scale"
    ws['A1'].font = Font(bold=True, size=13)
    ws.merge_cells('A1:D1')
    ws['A2'] = ('Comparables are the 2 real projects in master_comparables.py with the closest Apartment NFA. '
                'The management-fee rate below is DERIVED from whichever of those 2 have a verified real rate.')
    ws['A2'].font = Font(italic=True, color='595959')
    ws.merge_cells('A2:D2')
    ws.row_dimensions[2].height = 28

    headers = ['Metric', project['name']] + [c['name'] for c in comparables]
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

    def data_row(row, label, values, fill=None):
        cells = [label] + values
        for col, v in enumerate(cells, start=1):
            cell = ws.cell(row=row, column=col, value=v)
            cell.border = border
            cell.alignment = left if col == 1 else center
            if fill:
                cell.fill = fill
        return row + 1

    r = section(r, 'SCALE')
    r = data_row(r, 'Apartment NFA (m²)', [project['apartment_nfa']] + [c['nfa'] for c in comparables])
    r = data_row(r, 'NFA delta from this project', ['—'] + [round(abs(c['nfa'] - project['apartment_nfa'])) for c in comparables])
    r = data_row(r, 'Apartment units', [project['apartment_units']] + [c['units'] for c in comparables])

    r += 1
    r = section(r, 'MANAGEMENT FEE RATE')
    r = data_row(r, 'Real rate per comparable (VND/m²/month)',
                 ['—'] + [f"{c['mgmt_rate']:,} ({c['mgmt_rate_vat']})" if c['mgmt_rate'] else 'BLANK (no real rate)' for c in comparables])
    r = data_row(r, 'MODEL-DERIVED rate (this project)', [f'{derived_rate:,}', '', ''], fill=reality_fill)
    if rate_note:
        r = data_row(r, 'Derivation note', [rate_note, '', ''])
    if own_real:
        gap = derived_rate - own_real['mgmt_rate']
        gap_pct = gap / own_real['mgmt_rate'] * 100
        r = data_row(r, f"{project['name']}'s ACTUAL real rate (reality check)",
                     [f"{own_real['mgmt_rate']:,} ({own_real['mgmt_rate_vat']})", '', ''], fill=reality_fill)
        r = data_row(r, 'Gap (derived − real)', [f'{gap:+,} VND  ({gap_pct:+.0f}%)', '', ''], fill=reality_fill)
    else:
        r = data_row(r, 'Reality check', ['Not applicable — new prospect, no independently known real rate', '', ''])

    r += 1
    r = section(r, f'SERVICE RATES ({RATE_CARD_SOURCE})')
    r = data_row(r, 'Security (VND/post/month)', [f'{SECURITY_RATE_CITYWIDE:,}'] * 3)
    r = data_row(r, 'Cleaning (VND/post/month)', [f'{CLEANING_RATE_CITYWIDE:,}'] * 3)
    r = data_row(r, 'Landscape (VND/post/month)', [f'{LANDSCAPE_RATE_CITYWIDE:,}'] * 3)

    widths = {'A': 46, 'B': 26, 'C': 24, 'D': 24}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w

    wb.save(path)
    print('Comparison sheet added. Sheets now:', len(wb.sheetnames))


# ============================================================================================
# Roster workbook (same engine as generate_roster.py, reading the merged input file)
# ============================================================================================
HEADER_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)
TITLE_FONT = Font(bold=True, size=14)
SUBTITLE_FONT = Font(italic=True, color="595959")
INFO_FONT = Font(size=10, color="1F4E78")
OFF_FILL = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
ON_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
HOLIDAY_FILL = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
SECTION_FONT = Font(bold=True)
THIN = Side(style='thin', color='BFBFBF')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal='center', vertical='center')
LEFT = Alignment(horizontal='left', vertical='center', wrap_text=True)
MONEY_FMT = '#,##0'


def build_roster(project, ratios, month, year, holiday_days, demand):
    days_in_month = cal.monthrange(year, month)[1]
    month_name = cal.month_name[month]
    print(f"Generating formula-driven roster for {project['name']} — {month_name} {year} "
          f"({days_in_month} days), holidays flagged: {sorted(holiday_days) or 'none'}")

    os.makedirs(ROSTER_OUT_DIR, exist_ok=True)
    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = 'Shift Types'
    ws1['A1'] = 'Shift Type Reference'
    ws1['A1'].font = TITLE_FONT
    ws1.merge_cells('A1:E1')
    headers = ['Code', 'Name', 'Hours', 'Duration (hrs)', 'Night Shift?']
    for c, h in enumerate(headers, start=1):
        cell = ws1.cell(row=3, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    SHIFT_REF = [
        ('HC', 'Hành chính / Admin hours', '08:00-17:00', 8, 'No'),
        ('S', 'Ca sáng / Morning shift', '06:00-15:00', 9, 'No'),
        ('C', 'Ca chiều / Afternoon shift', '13:00-22:00', 9, 'No'),
        ('D', 'Ca đêm / Night shift (24h post overnight portion)', '22:00-06:00', 8, 'Yes'),
        ('24H', '24/24 continuous post', '00:00-24:00', 24, 'Yes'),
    ]
    for i, row_vals in enumerate(SHIFT_REF, start=4):
        for c, v in enumerate(row_vals, start=1):
            cell = ws1.cell(row=i, column=c, value=v)
            cell.border = BORDER
            cell.alignment = LEFT if c == 2 else CENTER
    for col, w in {'A': 8, 'B': 42, 'C': 16, 'D': 14, 'E': 12}.items():
        ws1.column_dimensions[col].width = w

    ws2 = wb.create_sheet('Staffing Demand')
    ws2['A1'] = f'Staffing Demand — copied from Project_Budget_Input.xlsx for {project["name"]}'
    ws2['A1'].font = TITLE_FONT
    ws2.merge_cells('A1:E1')
    ws2['A2'] = 'To change these numbers: edit Project_Budget_Input.xlsx and re-run generate_project_budget.py.'
    ws2['A2'].font = SUBTITLE_FONT
    ws2.merge_cells('A2:E2')
    headers2 = ['Position', 'Shift Code', 'Staff On Duty / Day', 'Coverage Days / Week', 'Avg Daily Rate (VND)']
    for c, h in enumerate(headers2, start=1):
        cell = ws2.cell(row=4, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    for i, d in enumerate(demand, start=5):
        ws2.cell(row=i, column=1, value=d['Position']).border = BORDER
        ws2.cell(row=i, column=1).alignment = LEFT
        ws2.cell(row=i, column=2, value=d['ShiftCode']).border = BORDER
        ws2.cell(row=i, column=2).alignment = CENTER
        ws2.cell(row=i, column=3, value=d['StaffPerDay']).border = BORDER
        ws2.cell(row=i, column=3).alignment = CENTER
        ws2.cell(row=i, column=4, value=d['CoverageDays']).border = BORDER
        ws2.cell(row=i, column=4).alignment = CENTER
        c5 = ws2.cell(row=i, column=5, value=d['AvgDailyRate'])
        c5.number_format = MONEY_FMT
        c5.border = BORDER
        d['DemandRow'] = i
    for col, w in {'A': 30, 'B': 12, 'C': 18, 'D': 18, 'E': 20}.items():
        ws2.column_dimensions[col].width = w

    ws0 = wb.create_sheet('Setup')
    ws0['A1'] = 'Project Info + Schedule Setup (copied from Project_Budget_Input.xlsx)'
    ws0['A1'].font = TITLE_FONT
    ws0.merge_cells('A1:B1')
    info_rows = [
        ('Project Name', project['name']), ('Tower Count', project['towers']),
        ('Site Area (m²)', project['site_area']), ('Apartment GFA (m²)', project['apartment_gfa']),
        ('Apartment Units', project['apartment_units']),
        ('Has Swimming Pool?', 'Yes' if project['has_pool'] else 'No'),
        ('Pool Area (m²)', project['pool_area']),
        ('Garden Area (m²)', project['garden_area']),
        ('Gate / Entrance Count', project['gate_count']),
        ('Open Space / Common Outdoor Area (m²)', project['open_space']),
        ('Ratio — Security: Staff per Gate', ratios['staff_per_gate']),
        ('Ratio — Security: m² Open Space per Patrol Staff', ratios['sqm_per_patrol']),
        ('Ratio — Cleaning: m² Open Space per Cleaner', ratios['sqm_per_cleaner']),
        ('Ratio — Cleaning: Towers per Supervisor', ratios['towers_per_supervisor']),
        ('Ratio — Landscape: m² Garden per Gardener', ratios['sqm_per_gardener']),
        ('Month', month), ('Year', year),
    ]
    for i, (label, val) in enumerate(info_rows, start=3):
        ws0.cell(row=i, column=1, value=label).font = Font(bold=True)
        ws0.cell(row=i, column=2, value=val)
    # info_rows has 17 entries starting at row 3, so Month lands on row 19, Year on row 20.
    ws0['A21'] = 'Days in month'
    ws0['A21'].font = Font(bold=True)
    ws0['B21'] = '=DAY(EOMONTH(DATE(B20,B19,1),0))'
    ws0['A23'] = 'Holiday dates this month'
    ws0['A23'].font = Font(bold=True)
    for i, d in enumerate(sorted(holiday_days), start=24):
        ws0.cell(row=i, column=1, value=d)
    holiday_last_row = max(24 + len(holiday_days) - 1, 24)
    ws0.column_dimensions['A'].width = 40
    ws0.column_dimensions['B'].width = 20
    MONTH_CELL = 'Setup!$B$19'
    YEAR_CELL = 'Setup!$B$20'
    DAYS_IN_MONTH_CELL = 'Setup!$B$21'
    HOLIDAY_RANGE = f'Setup!$A$24:$A${holiday_last_row}'

    ws3 = wb.create_sheet('Generated Roster')
    header_bits = [f"{project['towers']} tower(s)", f"{project['apartment_gfa']:,.0f} m² apartment GFA" if project['apartment_gfa'] else None,
                   f"{project['apartment_units']:,.0f} units" if project['apartment_units'] else None,
                   f"{project['gate_count']} gate(s)" if project['gate_count'] else None,
                   f"{project['open_space']:,.0f} m² open space" if project['open_space'] else None,
                   'pool' if project['has_pool'] else None, 'garden' if project['garden_area'] else None]
    header_bits = [b for b in header_bits if b]
    ws3['A1'] = f"Generated Roster — {project['name']} — {month_name} {year}"
    ws3['A1'].font = TITLE_FONT
    ws3.merge_cells('A1:F1')
    ws3['A2'] = ' · '.join(header_bits)
    ws3['A2'].font = INFO_FONT
    ws3.merge_cells('A2:F2')
    ws3['A3'] = 'Every schedule cell and header below is a live formula, not a fixed value — see the row-3 helper and column AH/AI.'
    ws3['A3'].font = SUBTITLE_FONT
    ws3.merge_cells('A3:L3')

    HOLIDAY_FLAG_ROW = 5
    DAY_NUM_ROW = 6
    WEEKDAY_ROW = 7
    FIRST_STAFF_ROW = 8

    ws3.cell(row=DAY_NUM_ROW, column=1, value='Position').fill = HEADER_FILL
    ws3.cell(row=DAY_NUM_ROW, column=1).font = HEADER_FONT
    ws3.cell(row=DAY_NUM_ROW, column=1).border = BORDER
    ws3.cell(row=DAY_NUM_ROW, column=2, value='Staff Slot').fill = HEADER_FILL
    ws3.cell(row=DAY_NUM_ROW, column=2).font = HEADER_FONT
    ws3.cell(row=DAY_NUM_ROW, column=2).border = BORDER
    for c in range(DAY_COL_START, DAY_COL_END + 1):
        col_letter = get_column_letter(c)
        f_flag = ws3.cell(row=HOLIDAY_FLAG_ROW, column=c,
                           value=f'=IF({col_letter}{DAY_NUM_ROW}="",FALSE,COUNTIF({HOLIDAY_RANGE},{col_letter}{DAY_NUM_ROW})>0)')
        f_day = ws3.cell(row=DAY_NUM_ROW, column=c,
                          value=f'=IF(COLUMN()-{DAY_COL_START - 1}<={DAYS_IN_MONTH_CELL},COLUMN()-{DAY_COL_START - 1},"")')
        f_day.fill = HEADER_FILL
        f_day.font = HEADER_FONT
        f_day.alignment = CENTER
        f_day.border = BORDER
        f_wd = ws3.cell(row=WEEKDAY_ROW, column=c,
                         value=f'=IF({col_letter}{DAY_NUM_ROW}="","",TEXT(DATE({YEAR_CELL},{MONTH_CELL},{col_letter}{DAY_NUM_ROW}),"ddd"))')
        f_wd.alignment = CENTER
        f_wd.font = Font(italic=True, size=8, color='7F7F7F')
    ws3.row_dimensions[HOLIDAY_FLAG_ROW].hidden = True

    r = FIRST_STAFF_ROW
    priced = []
    for d in demand:
        staff_count = math.ceil(d['StaffPerDay'] * 7 / 6) if d['CoverageDays'] >= 7 else d['StaffPerDay']
        first_row = r
        for s in range(1, staff_count + 1):
            ws3.cell(row=r, column=1, value=d['Position'] if s == 1 else '').border = BORDER
            ws3.cell(row=r, column=1).alignment = LEFT
            ws3.cell(row=r, column=2, value=f'Staff {s}').border = BORDER
            ws3.cell(row=r, column=2).alignment = CENTER

            demand_ref = f"'Staffing Demand'!$B${d['DemandRow']}"
            for c in range(DAY_COL_START, DAY_COL_END + 1):
                col_letter = get_column_letter(c)
                if d['CoverageDays'] >= 7:
                    formula = (f'=IF({col_letter}${DAY_NUM_ROW}="","",'
                               f'IF(MOD({col_letter}${DAY_NUM_ROW}-1,7)=${get_column_letter(COL_DAYOFF)}{r},"O",${get_column_letter(COL_SHIFTCODE)}{r}))')
                else:
                    formula = (f'=IF({col_letter}${DAY_NUM_ROW}="","",'
                               f"IF(WEEKDAY(DATE({YEAR_CELL},{MONTH_CELL},{col_letter}${DAY_NUM_ROW}),2)<='Staffing Demand'!$D${d['DemandRow']},"
                               f'${get_column_letter(COL_SHIFTCODE)}{r},"O"))')
                cell = ws3.cell(row=r, column=c, value=formula)
                cell.alignment = CENTER
                cell.border = BORDER
            ws3.cell(row=r, column=COL_DAYOFF, value=f'=MOD(ROW()-{first_row},7)')
            ws3.cell(row=r, column=COL_SHIFTCODE, value=f'={demand_ref}')
            r += 1
        last_row = r - 1
        priced.append(dict(demand=d, first_row=first_row, last_row=last_row, staff_count=staff_count))
        r += 1

    ws3.column_dimensions['A'].width = 26
    ws3.column_dimensions['B'].width = 12
    for c in range(DAY_COL_START, DAY_COL_END + 1):
        ws3.column_dimensions[get_column_letter(c)].width = 5
    ws3.column_dimensions[get_column_letter(COL_DAYOFF)].hidden = True
    ws3.column_dimensions[get_column_letter(COL_SHIFTCODE)].hidden = True
    ws3.freeze_panes = get_column_letter(DAY_COL_START) + str(FIRST_STAFF_ROW)

    full_range = f'{get_column_letter(DAY_COL_START)}{FIRST_STAFF_ROW}:{get_column_letter(DAY_COL_END)}{r - 1}'
    ws3.conditional_formatting.add(
        full_range,
        FormulaRule(formula=[f'AND({get_column_letter(DAY_COL_START)}${HOLIDAY_FLAG_ROW}=TRUE,{get_column_letter(DAY_COL_START)}{FIRST_STAFF_ROW}<>"O",{get_column_letter(DAY_COL_START)}{FIRST_STAFF_ROW}<>"")'],
        fill=HOLIDAY_FILL))
    ws3.conditional_formatting.add(full_range, FormulaRule(formula=[f'{get_column_letter(DAY_COL_START)}{FIRST_STAFF_ROW}="O"'], fill=OFF_FILL))
    ws3.conditional_formatting.add(full_range, FormulaRule(
        formula=[f'AND({get_column_letter(DAY_COL_START)}{FIRST_STAFF_ROW}<>"O",{get_column_letter(DAY_COL_START)}{FIRST_STAFF_ROW}<>"")'],
        fill=ON_FILL))

    ws4 = wb.create_sheet('Cost Summary')
    ws4['A1'] = f'Cost Summary — {project["name"]}, {month_name} {year} — every number below is a formula'
    ws4['A1'].font = TITLE_FONT
    ws4.merge_cells('A1:G1')
    ws4['A2'] = ('Night differential (+30%) on night-eligible shifts, non-holiday. Holiday differential '
                 '(+390% night / +300% day) only on dates entered in Roster Setup!A20:A29 of Project_Budget_Input.xlsx.')
    ws4['A2'].font = SUBTITLE_FONT
    ws4.merge_cells('A2:G2')
    ws4.row_dimensions[2].height = 28
    headers4 = ['Position', 'Staff Count (formula)', 'Working Days', 'Holiday Working Days',
                'Base Cost (VND)', 'Differential (VND)', 'Month Total (VND)']
    r4 = 4
    for c, h in enumerate(headers4, start=1):
        cell = ws4.cell(row=r4, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    r4 += 1
    total_row_start = r4
    for p in priced:
        d = p['demand']
        gr = "'Generated Roster'!"
        rng = f"${get_column_letter(DAY_COL_START)}${p['first_row']}:${get_column_letter(DAY_COL_END)}${p['last_row']}"
        hol_row_rng = f"${get_column_letter(DAY_COL_START)}${HOLIDAY_FLAG_ROW}:${get_column_letter(DAY_COL_END)}${HOLIDAY_FLAG_ROW}"
        sd = "'Staffing Demand'!"

        ws4.cell(row=r4, column=1, value=d['Position']).border = BORDER
        ws4.cell(row=r4, column=1).alignment = LEFT

        c2 = ws4.cell(row=r4, column=2,
                       value=f'=IF({sd}$D${d["DemandRow"]}>=7,ROUNDUP({sd}$C${d["DemandRow"]}*7/6,0),{sd}$C${d["DemandRow"]})')
        c2.border = BORDER
        c2.alignment = CENTER

        c3 = ws4.cell(row=r4, column=3, value=f'=SUMPRODUCT(({gr}{rng}<>"O")*({gr}{rng}<>""))')
        c3.border = BORDER
        c3.alignment = CENTER

        c4 = ws4.cell(row=r4, column=4,
                       value=f'=SUMPRODUCT(({gr}{rng}<>"O")*({gr}{rng}<>"")*({gr}{hol_row_rng}=TRUE))')
        c4.border = BORDER
        c4.alignment = CENTER

        c5 = ws4.cell(row=r4, column=5, value=f'=C{r4}*{sd}$E${d["DemandRow"]}')
        c5.number_format = MONEY_FMT
        c5.border = BORDER

        is_night = f'(INDEX(\'Shift Types\'!$E$4:$E$8,MATCH({sd}$B${d["DemandRow"]},\'Shift Types\'!$A$4:$A$8,0))="Yes")'
        c6 = ws4.cell(row=r4, column=6,
                       value=(f'=IF({is_night},(C{r4}-D{r4})*0.3*{sd}$E${d["DemandRow"]}+D{r4}*3.9*{sd}$E${d["DemandRow"]},'
                              f'D{r4}*3*{sd}$E${d["DemandRow"]})'))
        c6.number_format = MONEY_FMT
        c6.border = BORDER

        c7 = ws4.cell(row=r4, column=7, value=f'=E{r4}+F{r4}')
        c7.number_format = MONEY_FMT
        c7.border = BORDER
        r4 += 1
    total_row_end = r4 - 1
    ws4.cell(row=r4, column=1, value='GRAND TOTAL').font = SECTION_FONT
    c7 = ws4.cell(row=r4, column=7, value=f'=SUM(G{total_row_start}:G{total_row_end})')
    c7.number_format = MONEY_FMT
    c7.font = SECTION_FONT
    for col, w in {'A': 26, 'B': 16, 'C': 14, 'D': 16, 'E': 16, 'F': 16, 'G': 18}.items():
        ws4.column_dimensions[col].width = w

    wb.save(ROSTER_OUT)
    print('Saved locally:', ROSTER_OUT)
    try:
        os.makedirs(ROSTER_OUT_DIR, exist_ok=True)
        shutil.copyfile(ROSTER_OUT, ROSTER_FINAL_OUT)
        print('Copied into place:', ROSTER_FINAL_OUT)
        return ROSTER_FINAL_OUT
    except PermissionError as e:
        print('Could not copy into place yet (still locked):', e)
        print('Local copy remains valid at:', ROSTER_OUT)
        return ROSTER_OUT


def main():
    project, ratios, month, year, holiday_days, demand = read_input(INPUT_PATH)
    budget_path = build_budget(project)
    roster_path = build_roster(project, ratios, month, year, holiday_days, demand)
    print('\nDone.')
    print('Budget:', budget_path)
    print('Roster:', roster_path)


if __name__ == '__main__':
    main()
