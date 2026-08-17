"""
Builds ONE merged input file — Project_Budget_Input.xlsx — replacing the earlier 2-file split
(build_roster_input_form.py's Roster_Input_Form.xlsx alone). A user fills in property scale once,
on the "Project Info" sheet, and both the budget generator and the roster generator read it —
no more re-typing tower count / garden area / gate count in two places.

Four sheets:
  Project Info      Property scale, shaped like the real "0. Info" sheet used across the 8 real
                     project files (site area, footprint, garden, circulation, product mix table,
                     parking, pool, gate count) — fill in the yellow cells.
  Roster Setup       Staffing ratios (editable PM assumptions, not a real benchmark — see note
                     below), month/year, public holidays.
  Shift Types        reference table (not edited).
  Staffing Demand    Position, Shift Code, staff/day (formula for scaled positions, referencing
                     Project Info directly), coverage days, daily rate.

Run generate_project_budget.py after filling this in — it produces both the budget workbook and
the roster from this single file.
"""
import os
import shutil
import tempfile

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.comments import Comment

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT_DIR = os.path.join(BASE, 'reports')
FINAL_OUT = os.path.join(OUT_DIR, 'Project_Budget_Input.xlsx')
OUT = os.path.join(tempfile.gettempdir(), 'Project_Budget_Input.xlsx')

SHIFT_CODES = ['HC', 'S', 'C', 'D', '24H']
SHIFT_REF = [
    ('HC', 'Hành chính / Admin hours', '08:00-17:00', 8, 'No'),
    ('S', 'Ca sáng / Morning shift', '06:00-15:00', 9, 'No'),
    ('C', 'Ca chiều / Afternoon shift', '13:00-22:00', 9, 'No'),
    ('D', 'Ca đêm / Night shift (24h post overnight portion)', '22:00-06:00', 8, 'Yes'),
    ('24H', '24/24 continuous post', '00:00-24:00', 24, 'Yes'),
]

# Cell refs into the Project Info sheet (row layout fixed below).
_TOWER_COUNT = "'Project Info'!$B$10"
_GARDEN_AREA = "'Project Info'!$B$7"
_OPEN_SPACE = "'Project Info'!$B$8"
_GATE_COUNT = "'Project Info'!$B$27"
# Cell refs into the Roster Setup sheet's Staffing Ratios block.
_STAFF_PER_GATE = "'Roster Setup'!$B$4"
_SQM_PER_PATROL = "'Roster Setup'!$B$5"
_SQM_PER_CLEANER = "'Roster Setup'!$B$6"
_TOWERS_PER_SUPERVISOR = "'Roster Setup'!$B$7"
_SQM_PER_GARDENER = "'Roster Setup'!$B$8"

_SECURITY_MONTHLY_ALL_ROLES = 17_500_000  # Fact_MasterRateCard.csv: Service/Security "24/24 position (all roles)"
_SECURITY_DAILY_PER_ROLE = round(_SECURITY_MONTHLY_ALL_ROLES / 3 / 26, -3)
_SECURITY_NOTE = (
    f'Source: Fact_MasterRateCard.csv, Service/Security "24/24 position (all roles)" row — '
    f'{_SECURITY_MONTHLY_ALL_ROLES:,} VND/month covers all 3 shift roles for one post. '
    f'Split 3 ways = {_SECURITY_MONTHLY_ALL_ROLES // 3:,}/month per role ÷ 26 working days ≈ {_SECURITY_DAILY_PER_ROLE:,.0f}/day.'
)
_RATIO_NOTE = ('Formula-driven from Roster Setup!Staffing Ratios — an editable PM assumption, not a real '
               'benchmark (no dataset joins staff headcount to property scale for the same properties; see '
               'Fact_Dim_Master_Mapping.md). Adjust the ratio in Roster Setup, not this cell, to change the suggestion.')

# Added after scanning A&K Tower's real file directly: its own staffing plan (sheet "A2.2 Staff
# cost") has Property Manager, Technician (shift-based, Morning/Afternoon/Night), and Pool/Amenities
# Attendant (2 shifts, pool closed Mondays per A&K's own ops note) — none of which this template had
# before, even though real portfolio-wide rates for all three already exist in Fact_MasterRateCard.csv's
# Staff domain (built by build_master_rate_card.py, just never wired into this template). Rates below
# use the Staff domain's own English-labeled rows for Property Manager/Pool Attendant, and the
# Vietnamese-labeled "Kỹ thuật viên" row for Technician since it has by far the largest real sample
# (n=458 vs n=25 for the English "Technician" label — same role, just counted separately by the source
# extraction because the label differs).
_PROPERTY_MANAGER_MONTHLY = 42_325_000  # Fact_MasterRateCard.csv, Staff domain, "Property Manager" row, n=7
_PROPERTY_MANAGER_DAILY = round(_PROPERTY_MANAGER_MONTHLY / 26, -3)
_PROPERTY_MANAGER_NOTE = (
    f'Source: Fact_MasterRateCard.csv, Staff domain, "Property Manager" row — {_PROPERTY_MANAGER_MONTHLY:,} VND/month '
    f'(real, n=7 across the portfolio) ÷ 26 working days ≈ {_PROPERTY_MANAGER_DAILY:,.0f}/day. Admin hours (HC), not '
    f'shift-based. Not scaled by project size — no real ratio ties PM headcount to scale, so this is a fixed, '
    f'PM-adjustable assumption (1 PM per project), same treatment as Reception.'
)

_TECHNICIAN_MONTHLY = 8_459_141  # Fact_MasterRateCard.csv, Staff domain, "Kỹ thuật viên" row, n=458 (largest sample in the whole card)
_TECHNICIAN_DAILY = round(_TECHNICIAN_MONTHLY / 26, -3)
_TECHNICIAN_NOTE = (
    f'Source: Fact_MasterRateCard.csv, Staff domain, "Kỹ thuật viên" (Technician) row — {_TECHNICIAN_MONTHLY:,} VND/month '
    f'(real, n=458 — the largest single sample in the whole rate card) ÷ 26 working days ≈ {_TECHNICIAN_DAILY:,.0f}/day. '
    f'Not scaled by project size (no real ratio found linking technician headcount to scale) — fixed at 1/shift, a '
    f'PM-adjustable starting point, same treatment as Security - CCTV Room.'
)

_POOL_ATTENDANT_MONTHLY = 7_166_250  # Fact_MasterRateCard.csv, Staff domain, "Gym - Pool Attendant" row, n=1
_POOL_ATTENDANT_DAILY = round(_POOL_ATTENDANT_MONTHLY / 26, -3)
_POOL_ATTENDANT_NOTE = (
    f'Source: Fact_MasterRateCard.csv, Staff domain, "Gym - Pool Attendant" row — {_POOL_ATTENDANT_MONTHLY:,} VND/month '
    f'(real, n=1) ÷ 26 working days ≈ {_POOL_ATTENDANT_DAILY:,.0f}/day. A&K Tower\'s own real staffing plan runs this '
    f'role 2 shifts (Morning/Afternoon), pool closed Mondays — modeled here as 6-day coverage, but this template\'s '
    f'day-off convention is always Sunday (same as every other <7-day role) — it does NOT reproduce the real Monday '
    f'closure; edit by hand if that specific fidelity matters. Delete both rows if Project Info!B25 = No.'
)

# Added after re-scanning ALL 8 real project files' own staffing sheets AND the portfolio-wide
# reports/Project_Detail_Lists.xlsx ("Staff Positions by Project", 88 distinct real properties) —
# not just A&K this time. Ranked every distinct position by how many of the 88 properties actually
# have it (breadth of real adoption, not just headcount), then picked the 5 clearly-operational,
# building-level roles that rank highest and were still missing: Chief Engineer (62/88 — more
# common than Property Manager itself), Shift Leader (48/88), Customer Service (40/88 — a distinct,
# more common role than Reception's 11/88, kept as an addition not a replacement), Building
# Executive/service-quality supervisor (34/88), Amenities Attendant (24/88, beyond just the pool).
# Deliberately excluded pure back-office roles that also ranked high (Accountant 46/88, Senior
# Accountant 27/88, Cashier 12/88, Admin staff 10/88, Operations Manager 14/88) — those are
# portfolio/corporate-level costs, not building-roster staffing, which is this template's scope.
_CHIEF_ENGINEER_MONTHLY = 34_262_409  # Fact_MasterRateCard.csv, Staff domain, "Kỹ sư trưởng" row, n=61 (most common of the 3 label variants)
_CHIEF_ENGINEER_DAILY = round(_CHIEF_ENGINEER_MONTHLY / 26, -3)
_CHIEF_ENGINEER_NOTE = (
    f'Source: Fact_MasterRateCard.csv, Staff domain, "Kỹ sư trưởng" (Chief Engineer) row — {_CHIEF_ENGINEER_MONTHLY:,} '
    f'VND/month (real, n=61 — present in 62 of 88 real properties, more common than Property Manager itself) ÷ 26 '
    f'working days ≈ {_CHIEF_ENGINEER_DAILY:,.0f}/day. Admin hours (HC), senior oversight of the Technician team — '
    f'not scaled by project size, fixed 1/project, same treatment as Property Manager.'
)

_BUILDING_EXEC_MONTHLY = 15_298_818  # Fact_MasterRateCard.csv, Staff domain, "Giám sát chất lượng dịch vụ" row, n=73
_BUILDING_EXEC_DAILY = round(_BUILDING_EXEC_MONTHLY / 26, -3)
_BUILDING_EXEC_NOTE = (
    f'Source: Fact_MasterRateCard.csv, Staff domain, "Giám sát chất lượng dịch vụ" (Building Executive / service-quality '
    f'supervisor) row — {_BUILDING_EXEC_MONTHLY:,} VND/month (real, n=73 — present in 34 of 88 real properties) ÷ 26 '
    f'working days ≈ {_BUILDING_EXEC_DAILY:,.0f}/day. Admin hours (HC) — fixed 1/project, same treatment as Property Manager.'
)

_CUSTOMER_SERVICE_MONTHLY = 8_919_726  # Fact_MasterRateCard.csv, Staff domain, "Chăm sóc khách hàng" row, n=178 (largest sample of any new role added here)
_CUSTOMER_SERVICE_DAILY = round(_CUSTOMER_SERVICE_MONTHLY / 26, -3)
_CUSTOMER_SERVICE_NOTE = (
    f'Source: Fact_MasterRateCard.csv, Staff domain, "Chăm sóc khách hàng" (Customer Service) row — '
    f'{_CUSTOMER_SERVICE_MONTHLY:,} VND/month (real, n=178, present in 40 of 88 real properties — more common than '
    f'Reception/Lễ Tân\'s 11/88) ÷ 26 working days ≈ {_CUSTOMER_SERVICE_DAILY:,.0f}/day. Added alongside Reception, not '
    f'replacing it — real buildings commonly run both as distinct roles (front-desk/access vs resident relations). '
    f'Same admin-hours, 7-day treatment as Reception.'
)

_SHIFT_LEADER_MONTHLY = 11_541_695  # Fact_MasterRateCard.csv, Staff domain, "Trưởng Ca" row, n=138 (largest sample of any new role added here)
_SHIFT_LEADER_DAILY = round(_SHIFT_LEADER_MONTHLY / 26, -3)
_SHIFT_LEADER_NOTE = (
    f'Source: Fact_MasterRateCard.csv, Staff domain, "Trưởng Ca" (Shift Leader / on-duty manager) row — '
    f'{_SHIFT_LEADER_MONTHLY:,} VND/month (real, n=138 — present in 48 of 88 real properties) ÷ 26 working days ≈ '
    f'{_SHIFT_LEADER_DAILY:,.0f}/day. Cross-department on-duty supervisor covering the property when Property '
    f'Manager/Chief Engineer aren\'t on-site — modeled 3 shifts like Security/Technician since the role\'s whole point '
    f'is round-the-clock presence. Not scaled by project size, fixed 1/shift.'
)

_AMENITIES_ATTENDANT_MONTHLY = 7_988_816  # Fact_MasterRateCard.csv, Staff domain, "Nhân viên tiện ích" row, n=91
_AMENITIES_ATTENDANT_DAILY = round(_AMENITIES_ATTENDANT_MONTHLY / 26, -3)
_AMENITIES_ATTENDANT_NOTE = (
    f'Source: Fact_MasterRateCard.csv, Staff domain, "Nhân viên tiện ích" (Amenities Attendant) row — '
    f'{_AMENITIES_ATTENDANT_MONTHLY:,} VND/month (real, n=91, present in 24 of 88 real properties) ÷ 26 working days ≈ '
    f'{_AMENITIES_ATTENDANT_DAILY:,.0f}/day. Broader than Pool Attendant — covers gym/BBQ/community-room amenities '
    f'beyond just the pool. 2 shifts (Morning/Afternoon), 6-day coverage — no real per-project ops note found for '
    f'which specific day is off (unlike Pool Attendant\'s documented Monday closure), so this uses the template\'s '
    f'default Sunday-off convention without further evidence either way.'
)

# (Position, ShiftCode, StaffPerDay [int or "=formula"], CoverageDays, AvgDailyRate, source_note)
EXAMPLE_DEMAND = [
    ('Security - Main Gate (Morning)', 'S', f'=ROUNDUP({_GATE_COUNT}*{_STAFF_PER_GATE},0)', 7, _SECURITY_DAILY_PER_ROLE, _SECURITY_NOTE + ' ' + _RATIO_NOTE),
    ('Security - Main Gate (Afternoon)', 'C', f'=ROUNDUP({_GATE_COUNT}*{_STAFF_PER_GATE},0)', 7, _SECURITY_DAILY_PER_ROLE, _SECURITY_NOTE + ' ' + _RATIO_NOTE),
    ('Security - Main Gate (Night)', 'D', f'=ROUNDUP({_GATE_COUNT}*{_STAFF_PER_GATE},0)', 7, _SECURITY_DAILY_PER_ROLE, _SECURITY_NOTE + ' ' + _RATIO_NOTE),
    ('Security - CCTV Room (Morning)', 'S', 1, 7, _SECURITY_DAILY_PER_ROLE, _SECURITY_NOTE + ' Not gate-scaled — a control room is normally 1 regardless of gate count.'),
    ('Security - CCTV Room (Afternoon)', 'C', 1, 7, _SECURITY_DAILY_PER_ROLE, _SECURITY_NOTE),
    ('Security - CCTV Room (Night)', 'D', 1, 7, _SECURITY_DAILY_PER_ROLE, _SECURITY_NOTE),
    ('Security - Patrol / Open Space', 'S', f'=ROUNDUP({_OPEN_SPACE}/{_SQM_PER_PATROL},0)', 7, _SECURITY_DAILY_PER_ROLE,
     _SECURITY_NOTE + ' ' + _RATIO_NOTE + ' Shown for one shift only — for full 24h patrol coverage, copy this row for C and D shifts too.'),
    ('Cleaning - Common Area', 'S', f'=ROUNDUP({_OPEN_SPACE}/{_SQM_PER_CLEANER},0)', 7, 340000, _RATIO_NOTE),
    ('Cleaning - Supervisor', 'HC', f'=ROUNDUP({_TOWER_COUNT}/{_TOWERS_PER_SUPERVISOR},0)', 6, 480000, _RATIO_NOTE),
    ('Reception', 'HC', 1, 7, 340000, None),
    ('Customer Service', 'HC', 1, 7, _CUSTOMER_SERVICE_DAILY, _CUSTOMER_SERVICE_NOTE),
    ('Property Manager', 'HC', 1, 6, _PROPERTY_MANAGER_DAILY, _PROPERTY_MANAGER_NOTE),
    ('Chief Engineer', 'HC', 1, 6, _CHIEF_ENGINEER_DAILY, _CHIEF_ENGINEER_NOTE),
    ('Building Executive', 'HC', 1, 6, _BUILDING_EXEC_DAILY, _BUILDING_EXEC_NOTE),
    ('Technician (Morning)', 'S', 1, 7, _TECHNICIAN_DAILY, _TECHNICIAN_NOTE),
    ('Technician (Afternoon)', 'C', 1, 7, _TECHNICIAN_DAILY, _TECHNICIAN_NOTE),
    ('Technician (Night)', 'D', 1, 7, _TECHNICIAN_DAILY, _TECHNICIAN_NOTE),
    ('Shift Leader (Morning)', 'S', 1, 7, _SHIFT_LEADER_DAILY, _SHIFT_LEADER_NOTE),
    ('Shift Leader (Afternoon)', 'C', 1, 7, _SHIFT_LEADER_DAILY, _SHIFT_LEADER_NOTE),
    ('Shift Leader (Night)', 'D', 1, 7, _SHIFT_LEADER_DAILY, _SHIFT_LEADER_NOTE),
    ('Pool Attendant (Morning)', 'S', 1, 6, _POOL_ATTENDANT_DAILY, _POOL_ATTENDANT_NOTE),
    ('Pool Attendant (Afternoon)', 'C', 1, 6, _POOL_ATTENDANT_DAILY, _POOL_ATTENDANT_NOTE),
    ('Amenities Attendant (Morning)', 'S', 1, 6, _AMENITIES_ATTENDANT_DAILY, _AMENITIES_ATTENDANT_NOTE),
    ('Amenities Attendant (Afternoon)', 'C', 1, 6, _AMENITIES_ATTENDANT_DAILY, _AMENITIES_ATTENDANT_NOTE),
    ('Gardener / Landscape', 'HC', f'=ROUNDUP({_GARDEN_AREA}/{_SQM_PER_GARDENER},0)', 6, 423000,
     'Source: Fact_MasterRateCard.csv, Service/Landscape "8/24 position" row — 11,000,000 VND/month ÷ 26 ≈ 423,000/day. Delete this row if no garden. ' + _RATIO_NOTE),
]

HEADER_FILL = PatternFill('solid', fgColor='1F4E78')
HEADER_FONT = Font(color='FFFFFF', bold=True)
SECTION_FILL = PatternFill('solid', fgColor='D9E1F2')
SECTION_FONT = Font(bold=True, size=11)
TITLE_FONT = Font(bold=True, size=14)
SUB_FONT = Font(italic=True, color='595959')
INPUT_FILL = PatternFill('solid', fgColor='FFF7CC')
COMPUTED_FILL = PatternFill('solid', fgColor='F2F2F2')
LEGEND_FONT = Font(italic=True, size=9, color='7F6000')
THIN = Side(style='thin', color='BFBFBF')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal='center', vertical='center')
LEFT = Alignment(horizontal='left', vertical='center', wrap_text=True)


def section(ws, row, text, span='A:D'):
    ws.cell(row=row, column=1, value=text).font = SECTION_FONT
    c0, c1 = span.split(':')
    ws.merge_cells(f'{c0}{row}:{c1}{row}')
    for col in range(ord(c0) - 64, ord(c1) - 64 + 1):
        ws.cell(row=row, column=col).fill = SECTION_FILL


def labeled_input(ws, row, label, value, fill=INPUT_FILL, fmt=None):
    ws.cell(row=row, column=1, value=label).font = Font(bold=True)
    c = ws.cell(row=row, column=2, value=value)
    c.fill = fill
    c.border = BORDER
    c.alignment = CENTER
    if fmt:
        c.number_format = fmt
    return c


def main():
    wb = openpyxl.Workbook()

    # ================= Sheet 1: Project Info =================
    ws1 = wb.active
    ws1.title = 'Project Info'
    ws1['A1'] = 'Project Info — fill in the yellow cells, then run generate_project_budget.py'
    ws1['A1'].font = TITLE_FONT
    ws1.merge_cells('A1:D1')
    ws1['A2'] = 'Shaped after the real "0. Info" sheet used across Savills\' 8 real project budget files, so it matches what a new prospect would actually be able to supply up front.'
    ws1['A2'].font = SUB_FONT
    ws1.merge_cells('A2:D2')

    section(ws1, 4, 'PROJECT SCALE')
    labeled_input(ws1, 5, 'Project Name', 'New Prospect')
    ws1['B5'].alignment = LEFT
    labeled_input(ws1, 6, 'Site Area (m²)', 12000)
    labeled_input(ws1, 7, 'Garden / Landscape Area (m²)', 1800)
    labeled_input(ws1, 8, 'Circulation / Hardscape Area (m²) — used as open-space proxy for roster', 6000)
    labeled_input(ws1, 9, 'Floor Count', 30)
    labeled_input(ws1, 10, 'Tower Count', 2)

    section(ws1, 12, 'PRODUCT MIX — enter what applies, leave 0 for products this project doesn\'t have')
    headers = ['Product', 'GFA (m²)', 'NFA (m²)', 'Units']
    for c, h in enumerate(headers, start=1):
        cell = ws1.cell(row=13, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    products = ['Apartment', 'Officetel', 'Shophouse', 'Shopping Mall', 'Nursery / Nhà trẻ']
    example_apartment = (85000, 70000, 1300)
    for i, name in enumerate(products, start=14):
        c1 = ws1.cell(row=i, column=1, value=name)
        c1.border = BORDER
        c1.alignment = LEFT
        vals = example_apartment if name == 'Apartment' else (0, 0, 0)
        for j, v in enumerate(vals, start=2):
            c = ws1.cell(row=i, column=j, value=v)
            c.fill = INPUT_FILL
            c.border = BORDER
            c.alignment = CENTER
    APT_NFA_ROW = 14  # Apartment row — generate_project_budget.py reads C14 (NFA)

    section(ws1, 20, 'PARKING')
    labeled_input(ws1, 21, 'Car Parking Slots', 300)
    labeled_input(ws1, 22, 'Moto Parking Slots', 2000)

    section(ws1, 24, 'AMENITIES (drive roster staffing)')
    dv_yn = DataValidation(type='list', formula1='"Yes,No"', showErrorMessage=True,
                            errorTitle='Invalid', error='Pick Yes or No')
    ws1.add_data_validation(dv_yn)
    c_pool = labeled_input(ws1, 25, 'Has Swimming Pool?', 'No')
    dv_yn.add(c_pool)
    labeled_input(ws1, 26, 'Pool Area (m²) — optional', 0)
    labeled_input(ws1, 27, 'Gate / Entrance Count', 2)

    for col, w in {'A': 34, 'B': 16, 'C': 16, 'D': 14}.items():
        ws1.column_dimensions[col].width = w

    # ================= Sheet 2: Roster Setup =================
    ws2 = wb.create_sheet('Roster Setup')
    ws2['A1'] = 'Roster Setup — staffing ratios, schedule month, public holidays'
    ws2['A1'].font = TITLE_FONT
    ws2.merge_cells('A1:D1')

    section(ws2, 3, 'STAFFING RATIOS — adjust to your own standard')
    ws2['A3'].font = SECTION_FONT
    legend_row = 3
    ws2['A4'] = None  # placeholder, ratios start row 4 per _STAFF_PER_GATE etc. above
    labeled_input(ws2, 4, 'Security: Staff per Gate', 1)
    labeled_input(ws2, 5, 'Security: m² Open Space per Patrol Staff', 5000)
    labeled_input(ws2, 6, 'Cleaning: m² Open Space per Cleaner', 3000)
    labeled_input(ws2, 7, 'Cleaning: Towers per Supervisor', 2)
    labeled_input(ws2, 8, 'Landscape: m² Garden per Gardener', 2000)
    ws2['A9'] = ('These are editable assumptions, not a real benchmark — no dataset joins staff headcount to '
                 'property scale for the same properties. Change to your own operational standard — '
                 'Staffing Demand recalculates automatically.')
    ws2['A9'].font = LEGEND_FONT
    ws2['A9'].alignment = LEFT
    ws2.merge_cells('A9:D9')
    ws2.row_dimensions[9].height = 40

    section(ws2, 11, 'SCHEDULE SETUP')
    labeled_input(ws2, 12, 'Month (1-12)', 9)
    dv_month = DataValidation(type='whole', operator='between', formula1=1, formula2=12,
                               showErrorMessage=True, errorTitle='Invalid month', error='Enter 1-12')
    ws2.add_data_validation(dv_month)
    dv_month.add(ws2['B12'])
    labeled_input(ws2, 13, 'Year', 2026)
    ws2['A14'] = 'Days in this month (auto)'
    ws2['A14'].font = Font(bold=True)
    c14 = ws2.cell(row=14, column=2, value='=DAY(EOMONTH(DATE(B13,B12,1),0))')
    c14.fill = COMPUTED_FILL
    c14.border = BORDER
    c14.alignment = CENTER
    c14.font = Font(italic=True)

    section(ws2, 16, 'PUBLIC HOLIDAYS THIS MONTH')
    ws2['A17'] = ('Lunar-calendar holidays (Tết, Hùng Kings\' Day) move every year — enter the actual dates '
                  'from your company\'s official 2026 calendar, one per row below. Fixed-date holidays '
                  '(Jan 1, Apr 30, May 1, Sep 2) still need to be entered here too — nothing is assumed.')
    ws2['A17'].font = LEGEND_FONT
    ws2['A17'].alignment = LEFT
    ws2.merge_cells('A17:D17')
    ws2.row_dimensions[17].height = 42

    ws2['A19'] = 'Date (DD)'
    ws2['B19'] = 'Holiday name'
    for c in ('A19', 'B19'):
        ws2[c].fill = HEADER_FILL
        ws2[c].font = HEADER_FONT
        ws2[c].border = BORDER
        ws2[c].alignment = CENTER
    for r in range(20, 30):
        c1 = ws2.cell(row=r, column=1)
        c1.fill = INPUT_FILL
        c1.border = BORDER
        c1.alignment = CENTER
        c2 = ws2.cell(row=r, column=2)
        c2.fill = INPUT_FILL
        c2.border = BORDER
    HOLIDAY_FIRST_ROW, HOLIDAY_LAST_ROW = 20, 29
    for col, w in {'A': 30, 'B': 34, 'C': 14, 'D': 14}.items():
        ws2.column_dimensions[col].width = w

    # ================= Sheet 3: Shift Types (reference) =================
    ws3 = wb.create_sheet('Shift Types')
    ws3['A1'] = 'Shift Type Reference — do not edit, used by the Shift Code dropdown and roster formulas'
    ws3['A1'].font = TITLE_FONT
    ws3.merge_cells('A1:E1')
    headers3 = ['Code', 'Name', 'Hours', 'Duration (hrs)', 'Night Shift?']
    for c, h in enumerate(headers3, start=1):
        cell = ws3.cell(row=3, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    for i, row_vals in enumerate(SHIFT_REF, start=4):
        for c, v in enumerate(row_vals, start=1):
            cell = ws3.cell(row=i, column=c, value=v)
            cell.border = BORDER
            cell.alignment = LEFT if c == 2 else CENTER
    for col, w in {'A': 8, 'B': 44, 'C': 16, 'D': 14, 'E': 12}.items():
        ws3.column_dimensions[col].width = w

    # ================= Sheet 4: Staffing Demand =================
    ws4 = wb.create_sheet('Staffing Demand')
    ws4['A1'] = 'Staffing Demand — edit, add, or delete rows freely'
    ws4['A1'].font = TITLE_FONT
    ws4.merge_cells('A1:E1')
    ws4['A2'] = 'Shift Code must match a code from the "Shift Types" sheet — use the dropdown. Rates cited in cell comments where sourced from real data.'
    ws4['A2'].font = SUB_FONT
    ws4.merge_cells('A2:E2')

    headers4 = ['Position', 'Shift Code', 'Staff On Duty / Day', 'Coverage Days / Week', 'Avg Daily Rate (VND)']
    for c, h in enumerate(headers4, start=1):
        cell = ws4.cell(row=4, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER

    dv_shift = DataValidation(type='list', formula1='"' + ','.join(SHIFT_CODES) + '"',
                               showErrorMessage=True, errorTitle='Invalid shift code',
                               error='Pick a code from the Shift Types sheet')
    ws4.add_data_validation(dv_shift)

    last_row = 4 + max(len(EXAMPLE_DEMAND), 20)
    for i in range(5, last_row + 1):
        idx = i - 5
        if idx < len(EXAMPLE_DEMAND):
            pos, code, staff, days, rate, note = EXAMPLE_DEMAND[idx]
        else:
            pos = code = staff = days = rate = note = None
        c1 = ws4.cell(row=i, column=1, value=pos)
        c1.border = BORDER
        c1.alignment = LEFT
        c1.fill = INPUT_FILL
        c2 = ws4.cell(row=i, column=2, value=code)
        c2.border = BORDER
        c2.alignment = CENTER
        c2.fill = INPUT_FILL
        dv_shift.add(c2)
        c3 = ws4.cell(row=i, column=3, value=staff)
        c3.border = BORDER
        c3.alignment = CENTER
        c3.fill = INPUT_FILL
        c4 = ws4.cell(row=i, column=4, value=days)
        c4.border = BORDER
        c4.alignment = CENTER
        c4.fill = INPUT_FILL
        c5 = ws4.cell(row=i, column=5, value=rate)
        c5.number_format = '#,##0'
        c5.border = BORDER
        c5.fill = INPUT_FILL
        if note:
            c5.comment = Comment(note, 'Budget Planning Agent')
    for col, w in {'A': 30, 'B': 12, 'C': 18, 'D': 18, 'E': 20}.items():
        ws4.column_dimensions[col].width = w

    wb.save(OUT)
    print('Saved locally:', OUT)
    try:
        os.makedirs(OUT_DIR, exist_ok=True)
        shutil.copyfile(OUT, FINAL_OUT)
        print('Copied into place:', FINAL_OUT)
    except PermissionError as e:
        print('Could not copy into place yet (still locked):', e)
        print('Local copy remains valid at:', OUT)


if __name__ == '__main__':
    main()
