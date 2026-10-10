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

This script will not replace an existing Project_Budget_Input.xlsx: it stops with a message unless run
with --force, which first copies the existing file beside itself as Project_Budget_Input_PRE_FORCE_*.xlsx.

After filling this in and SAVING, click the green "RUN BUDGET AGENT" button on the Project Info
sheet (or double-click "Run Budget Agent.cmd" in reports/, or run `python run.py`) — it produces
the budget workbook, the analysis workbook and the roster from this single file.
"""
import argparse
import datetime
import filecmp
import os
import shutil
import sys
import tempfile

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, Protection
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.comments import Comment

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT_DIR = os.path.join(BASE, 'reports')
FINAL_OUT = os.path.join(OUT_DIR, 'Project_Budget_Input.xlsx')
OUT = os.path.join(tempfile.gettempdir(), 'Project_Budget_Input.xlsx')
BACKUP_PREFIX = 'Project_Budget_Input_PRE_FORCE_'

RUN_LAUNCHER = 'Run Budget Agent.cmd'   # sits in reports\, next to this workbook


def add_run_button(ws, top_row=1, left_col=6):
    """A green 'RUN BUDGET AGENT' panel on the Project Info sheet (F1:G3), clear of the A:D inputs.

    NOT a hyperlink: this workbook lives on SharePoint/OneDrive, and Excel resolves a cell
    hyperlink against the web URL, so a link to the local .cmd just opens a 404 in the browser.
    The panel is an instruction to double-click reports\\Run Budget Agent.cmd in File Explorer —
    which always works. For a real one-click button, add a VBA macro (see docs / RUNNING.md).
    """
    from openpyxl.utils import get_column_letter
    cL, cR = get_column_letter(left_col), get_column_letter(left_col + 1)
    span = f'{cL}{top_row}:{cR}{top_row + 1}'
    ws.merge_cells(span)
    cell = ws.cell(row=top_row, column=left_col)
    cell.value = 'TO RUN  ▶  double-click  "Run Budget Agent.cmd"  in this folder'
    cell.fill = PatternFill('solid', fgColor='548235')
    cell.font = Font(bold=True, size=11, color='FFFFFF')
    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    thick = Side(style='medium', color='375623')
    for row in ws[span]:
        for c in row:
            c.border = Border(left=thick, right=thick, top=thick, bottom=thick)
    ws.row_dimensions[top_row].height = 22
    ws.row_dimensions[top_row + 1].height = 22

    note_row = top_row + 2
    ws.merge_cells(f'{cL}{note_row}:{cR}{note_row}')
    note = ws.cell(row=note_row, column=left_col,
                   value='Fill the yellow cells, SAVE, close this file, then run the launcher. '
                         'Or run  python run.py  in source_code\\.')
    note.font = Font(italic=True, size=8, color='7F7F7F')
    note.alignment = Alignment(horizontal='center', wrap_text=True)
    ws.row_dimensions[note_row].height = 40
    for col in (cL, cR):
        if ws.column_dimensions[col].width is None or ws.column_dimensions[col].width < 18:
            ws.column_dimensions[col].width = 18

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
_GATE_COUNT = "'Project Info'!$B$11"   # moved under Tower Count 2026-09-15, was $B$32
_POOL_AREA = "'Project Info'!$B$39"    # shifted +6 then +1 (2026-09-16) by District/City/Lat/Lon/
                                        # Address/Passenger Elevators/Number of Basements moving into
                                        # PROJECT SCALE above it; was $B$32
# Lifeguards per m2 of pool water surface. STATUTORY, not a Savills assumption — Thông tư
# 03/2018/TT-BVHTTDL Điều 5 khoản 3: "ít nhất 200m2 mặt nước bể bơi/01 nhân viên". Deliberately NOT
# placed in Roster Setup's editable Staffing Ratios block, which holds our own tunable assumptions;
# a legal minimum should not sit in a list of preferences. Mirrored by POOL_LIFEGUARD_M2_PER_STAFF
# in generate_project_budget.py, which is the authoritative copy. See docs/15-pool-staffing-regulation.md.
_POOL_M2_PER_LIFEGUARD = 200
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
    f'closure; edit by hand if that specific fidelity matters. Delete both rows if Project Info!B29 = No.'
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
    # StaffPerDay seeded at 0, not 1 (change activate-dormant-staffing-ratios, 2026-09-17) — matching
    # the Assistant Property Manager / Accountant / Cashier pattern below: 0 is falsy, so
    # _staff_on_duty()'s override detector (`numeric and not is_formula`) does not trip, and the row
    # falls through to its portfolio ratio instead of shipping frozen at a placeholder `1`. Ratio
    # coverage verified against Fact_StaffingRatio_ByPosition.csv before this change (n=25/24/19/22/12
    # for Reception/PM/Chief Engineer/Building Exec/Customer Service; n=26/22/12 for the three
    # Technician/Shift Leader/Amenities Attendant shift-split roles) — all clear the usability floor.
    ('Reception', 'HC', 0, 7, 340000, None),
    ('Customer Service', 'HC', 0, 7, _CUSTOMER_SERVICE_DAILY, _CUSTOMER_SERVICE_NOTE),
    ('Property Manager', 'HC', 0, 6, _PROPERTY_MANAGER_DAILY, _PROPERTY_MANAGER_NOTE),
    ('Chief Engineer', 'HC', 0, 6, _CHIEF_ENGINEER_DAILY, _CHIEF_ENGINEER_NOTE),
    ('Building Executive', 'HC', 0, 6, _BUILDING_EXEC_DAILY, _BUILDING_EXEC_NOTE),
    ('Technician (Morning)', 'S', 0, 7, _TECHNICIAN_DAILY, _TECHNICIAN_NOTE),
    ('Technician (Afternoon)', 'C', 0, 7, _TECHNICIAN_DAILY, _TECHNICIAN_NOTE),
    ('Technician (Night)', 'D', 0, 7, _TECHNICIAN_DAILY, _TECHNICIAN_NOTE),
    ('Shift Leader (Morning)', 'S', 0, 7, _SHIFT_LEADER_DAILY, _SHIFT_LEADER_NOTE),
    ('Shift Leader (Afternoon)', 'C', 0, 7, _SHIFT_LEADER_DAILY, _SHIFT_LEADER_NOTE),
    ('Shift Leader (Night)', 'D', 0, 7, _SHIFT_LEADER_DAILY, _SHIFT_LEADER_NOTE),
    # Per-shift lifeguard count from pool water-surface area (statutory ratio, see _POOL_M2_PER_LIFEGUARD).
    # Falls back to 1 — A&K Tower's own real pattern — when Pool Area is not supplied, matching how
    # ESM4 falls back when Pool Volume is unknown. Two rows = two shifts, so the ratio applies per shift.
    ('Pool Attendant (Morning)', 'S',
     f'=IF({_POOL_AREA}>0,ROUNDUP({_POOL_AREA}/{_POOL_M2_PER_LIFEGUARD},0),1)', 6,
     _POOL_ATTENDANT_DAILY, _POOL_ATTENDANT_NOTE),
    ('Pool Attendant (Afternoon)', 'C',
     f'=IF({_POOL_AREA}>0,ROUNDUP({_POOL_AREA}/{_POOL_M2_PER_LIFEGUARD},0),1)', 6,
     _POOL_ATTENDANT_DAILY, _POOL_ATTENDANT_NOTE),
    ('Amenities Attendant (Morning)', 'S', 0, 6, _AMENITIES_ATTENDANT_DAILY, _AMENITIES_ATTENDANT_NOTE),
    ('Amenities Attendant (Afternoon)', 'C', 0, 6, _AMENITIES_ATTENDANT_DAILY, _AMENITIES_ATTENDANT_NOTE),
    ('Gardener / Landscape', 'HC', f'=ROUNDUP({_GARDEN_AREA}/{_SQM_PER_GARDENER},0)', 6, 423000,
     'Source: Fact_MasterRateCard.csv, Service/Landscape "8/24 position" row — 11,000,000 VND/month ÷ 26 ≈ 423,000/day. Delete this row if no garden. ' + _RATIO_NOTE),

    # Added 2026-09-09. The 2027 Resi template carries staff-cost rows for 13 position codes; this
    # form only ever shipped 6 of them, so APM/OM/CSS/ACC/CSR/ACE/ADCE could not be costed at all —
    # not "priced at zero", but invisible, with no row to type a headcount into. They now ship at
    # STAFF = 0, which costs nothing and reads as a deliberate "this project has none" rather than
    # an omission. Enter a headcount to include one.
    # Rates are real, from Fact_MasterRateCard.csv (Staff domain), converted the same way as every
    # other row on this sheet: monthly ÷ 26 working days, rounded to the nearest 1,000. Each note
    # carries the source row and its sample size, so a thin one is visible as thin.
    ('Assistant Property Manager', 'HC', 0, 6, 654000,
     'Trợ lý Trưởng Ban Quản Lý (template code APM). Real: Fact_MasterRateCard.csv "Trợ lý trưởng ban quản lý" '
     '17,000,000 VND/month (n=2 — thin) ÷ 26 ≈ 654,000/day. Ships at 0 — enter a headcount if this project has one.'),
    ('Operations Manager', 'HC', 0, 6, 1015000,
     'Quản lý vận hành (template code OM). Real: Fact_MasterRateCard.csv "Quản lý vận hành" 26,395,822 VND/month '
     '(n=14) ÷ 26 ≈ 1,015,000/day. Ships at 0 — enter a headcount if this project has one.'),
    ('Customer Service Supervisor', 'HC', 0, 6, 548000,
     'Trưởng nhóm Chăm sóc khách hàng (template code CSS). Real: Fact_MasterRateCard.csv "Trưởng nhóm Chăm Sóc '
     'Khách Hàng" 14,240,818 VND/month (n=10) ÷ 26 ≈ 548,000/day. Ships at 0 — enter a headcount if needed.'),
    ('Accountant', 'HC', 0, 6, 522000,
     'Kế toán (template code ACC). Real: Fact_MasterRateCard.csv "Kế toán" 13,574,175 VND/month (n=54 — the '
     'best-evidenced staff rate in the table) ÷ 26 ≈ 522,000/day. Ships at 0 — enter a headcount if needed.'),
    ('Cashier', 'HC', 0, 6, 386000,
     'Thủ quỹ (template code CSR). Real: Fact_MasterRateCard.csv "Thủ Quỹ" 10,028,473 VND/month (n=13) ÷ 26 '
     '≈ 386,000/day. Ships at 0 — enter a headcount if needed.'),
    ('Assistant Chief Engineer', 'HC', 0, 6, 670000,
     'Trợ lý Kỹ sư trưởng (template code ACE). Real: Fact_MasterRateCard.csv "Trợ lý Kỹ sư trưởng" 17,427,160 '
     'VND/month (n=24) ÷ 26 ≈ 670,000/day. Ships at 0 — enter a headcount if needed.'),
    ('Technical Secretary', 'HC', 0, 6, 413000,
     'Thư ký bộ phận Kỹ thuật (template code ADCE). Real: Fact_MasterRateCard.csv "Thư ký Bộ phận kỹ thuật" '
     '10,737,610 VND/month (n=4 — thin) ÷ 26 ≈ 413,000/day. Ships at 0 — enter a headcount if needed.'),
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


class LiveInputExists(RuntimeError):
    """A project input workbook is already in place and the build was not forced."""

    def __init__(self, path):
        self.path = path
        super().__init__(
            f'{path} already exists, so nothing was built and the file is unchanged. '
            f'To replace it with a blank form, run again with --force; the existing file is first '
            f'copied beside it as {BACKUP_PREFIX}<date_time>.xlsx.')


class LiveInputBackupFailed(RuntimeError):
    """The backup copy needed before a forced rebuild could not be made, so nothing was replaced."""


def _backup_existing(path):
    """Copy `path` beside itself as Project_Budget_Input_PRE_FORCE_<yyyy-mm-dd_hhmmss>.xlsx.

    The name follows the hand-made backups already in reports/ (..._PRE_<reason>_<date>.xlsx) and
    carries the time to the second, with a counter if that name is taken, so a second forced run can
    never overwrite the backup of the project the first one replaced. The copy is compared byte for
    byte with the original before the caller is allowed to replace it.
    """
    stamp = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')
    folder = os.path.dirname(path)
    backup, n = os.path.join(folder, f'{BACKUP_PREFIX}{stamp}.xlsx'), 1
    while os.path.exists(backup):
        n += 1
        backup = os.path.join(folder, f'{BACKUP_PREFIX}{stamp}_{n}.xlsx')
    try:
        shutil.copy2(path, backup)
        same = filecmp.cmp(path, backup, shallow=False)
    except OSError as exc:
        raise LiveInputBackupFailed(
            f'Could not back up {path} before replacing it ({exc}). Nothing was replaced.') from exc
    if not same:
        raise LiveInputBackupFailed(
            f'The backup {backup} differs from {path}. Nothing was replaced; check the backup.')
    return backup


# ---- Existing-project mode (change carry-forward-staffing, task 2.1) -------------------------
# Used by main() for a fresh form and by add_existing_project_sheets.py for a filled one, so both
# carry exactly the same labels. The labels are what existing_staffing.read_existing() looks for.
REASON_LIST_COL = 14          # N on 'Prior-Year Roster': the reason codes the dropdowns offer
ROSTER_INPUT_ROWS = 30
ACTUAL_INPUT_ROWS = 20


def _reason_list_ref():
    from existing_staffing import ROSTER_SHEET, REASON_CODES
    from openpyxl.utils import get_column_letter
    col = get_column_letter(REASON_LIST_COL)
    return f"='{ROSTER_SHEET}'!${col}$3:${col}${2 + len(REASON_CODES)}"


def add_existing_project_fields(ws, row):
    """'Project Mode', 'Minimum Wage Region' and 'Prior Budget Year' on Project Info, from `row`."""
    import existing_staffing as es
    section(ws, row, 'EXISTING PROJECT — carry last year\'s approved staffing forward')
    mode = labeled_input(ws, row + 1, es.MODE_LABEL, es.MODE_NEW)
    dv = DataValidation(type='list', formula1='"' + ','.join(es.MODES) + '"', showErrorMessage=True,
                        errorTitle='Project Mode', error='Pick New prospect or Existing project')
    ws.add_data_validation(dv)
    dv.add(mode)
    mode.comment = Comment(
        "New prospect: the staffing is estimated as before. Existing project: the staff lines (A1, "
        "EMH2, EMH3, EMH4) start from last year's APPROVED budget on the 'Prior-Year Roster' sheet, "
        "are recalculated under state law only, and every change needs a reason.", 'Budget Planning Agent')
    region = labeled_input(ws, row + 2, es.REGION_LABEL + ' — blank = I', None)
    dv2 = DataValidation(type='list', formula1='"I,II,III,IV"', showErrorMessage=True,
                         errorTitle='Minimum Wage Region', error='Pick I, II, III or IV')
    ws.add_data_validation(dv2)
    dv2.add(region)
    region.comment = Comment(
        "Regional minimum-wage zone of the project's location (Nghị định 293/2025/NĐ-CP appendix). "
        "Used only in Existing-project mode, for the minimum-wage floor and the unemployment-insurance "
        "ceiling. Blank means Region I, which the standard form assumes.", 'Budget Planning Agent')
    labeled_input(ws, row + 3, es.PRIOR_YEAR_LABEL + ' — the approved budget copied', None, fmt='0')


def add_prior_year_roster_sheet(wb):
    """The 'Prior-Year Roster' sheet: four labelled blocks plus the reason-code list (design D8-D10)."""
    import existing_staffing as es
    from openpyxl.utils import get_column_letter
    ws = wb.create_sheet(es.ROSTER_SHEET)
    # The title must not read like a block title: existing_staffing finds blocks by their titles.
    ws['A1'] = 'Existing-project inputs — used only when Project Mode is "Existing project"'
    ws['A1'].font = TITLE_FONT
    ws['A2'] = ("Copy from LAST YEAR'S APPROVED budget, not a draft: the A1 staff sheet (one row per "
                "position: heads and monthly gross per head), the night/holiday allowance sheet, and "
                "the approved EMH2/EMH3/EMH4 amounts. Type changes in the 'New …' columns with a reason.")
    ws['A2'].font = SUB_FONT

    dv_reason = DataValidation(type='list', formula1=_reason_list_ref(), showErrorMessage=True,
                               errorTitle='Reason Code', error='Pick a reason code from the list')
    dv_shift = DataValidation(type='list', formula1='"' + ','.join(SHIFT_CODES) + '"',
                              showErrorMessage=True, errorTitle='Invalid shift code',
                              error='Pick a code from the Shift Types sheet')
    ws.add_data_validation(dv_reason)
    ws.add_data_validation(dv_shift)

    def block(row, title, headers, n_rows, prefill=(), widths_from=1):
        section(ws, row, title, span=f'A:{get_column_letter(len(headers))}')
        for c, h in enumerate(headers, start=1):
            cell = ws.cell(row=row + 1, column=c, value=h)
            cell.fill = HEADER_FILL
            cell.font = HEADER_FONT
            cell.alignment = CENTER
            cell.border = BORDER
        for i in range(n_rows):
            for c in range(1, len(headers) + 1):
                cell = ws.cell(row=row + 2 + i, column=c)
                cell.fill = INPUT_FILL
                cell.border = BORDER
            if i < len(prefill):
                ws.cell(row=row + 2 + i, column=1, value=prefill[i])
        return row + 2, row + 1 + n_rows

    r = 4
    first, last = block(r, es.SEC_ROSTER, [
        'Position', 'Shift Code', 'Headcount', 'Monthly Gross per Head (VND)', 'Budget Year',
        'New Headcount', 'New Monthly Gross (VND)', 'Reason Code', 'Reason Note', 'Note'],
        ROSTER_INPUT_ROWS)
    for i in range(first, last + 1):
        dv_shift.add(ws.cell(row=i, column=2))
        dv_reason.add(ws.cell(row=i, column=8))
        for c in (4, 7):
            ws.cell(row=i, column=c).number_format = '#,##0'
    r = last + 2
    first, last = block(r, es.SEC_DUTY, [
        'Code', 'Night Staff per Normal Night', 'Night Staff per Holiday Night',
        'Day Staff per Holiday', 'Monthly Gross for Allowance (VND)', 'Note'],
        len(es.DUTY_CODES), prefill=es.DUTY_CODES)
    for i in range(first, last + 1):
        ws.cell(row=i, column=5).number_format = '#,##0'
    r = last + 2
    first, last = block(r, es.SEC_LINES, [
        'Line', 'Prior-Year Approved (VND/year)', 'Budget-Year Override (VND/year)', 'Reason Code',
        'Reason Note'], len(es.STAFF_LINES), prefill=es.STAFF_LINES)
    for i in range(first, last + 1):
        dv_reason.add(ws.cell(row=i, column=4))
        for c in (2, 3):
            ws.cell(row=i, column=c).number_format = '#,##0'
    r = last + 2
    block(r, es.SEC_ACTUAL + ' (OPTIONAL — C&B payroll / PM timesheet, shown only, changes no figure)',
          ['Position', 'Actual Headcount', 'Source', 'Note'], ACTUAL_INPUT_ROWS)

    ws.cell(row=2, column=REASON_LIST_COL, value='Reason codes (dropdown list)').font = Font(bold=True)
    for i, code in enumerate(es.REASON_CODES):
        ws.cell(row=3 + i, column=REASON_LIST_COL, value=code)
    for col, w in {'A': 30, 'B': 14, 'C': 14, 'D': 20, 'E': 20, 'F': 16, 'G': 20, 'H': 34, 'I': 30,
                   'J': 24, get_column_letter(REASON_LIST_COL): 44}.items():
        ws.column_dimensions[col].width = w
    return ws


def add_demand_reason_columns(ws, first_row, last_row):
    """'Reason Code' / 'Reason Note' on Staffing Demand, in the first free columns of header row 4.
    Only Existing-project mode reads them: a position the prior-year roster does not cover is new."""
    col = 1
    while ws.cell(row=4, column=col).value not in (None, ''):
        col += 1
    dv = DataValidation(type='list', formula1=_reason_list_ref(), showErrorMessage=True,
                        errorTitle='Reason Code', error='Pick a reason code from the list')
    ws.add_data_validation(dv)
    for offset, header in enumerate(('Reason Code', 'Reason Note')):
        cell = ws.cell(row=4, column=col + offset, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
        for r in range(first_row, last_row + 1):
            c = ws.cell(row=r, column=col + offset)
            c.fill = INPUT_FILL
            c.border = BORDER
            c.protection = Protection(locked=False)
            if offset == 0:
                dv.add(c)
    from openpyxl.utils import get_column_letter
    ws.column_dimensions[get_column_letter(col)].width = 34
    ws.column_dimensions[get_column_letter(col + 1)].width = 30
    return col


def main(force=False):
    # Fail before building anything: replacing a filled-in project with placeholder data has
    # destroyed live input more than once (RUNNING.md, step 1).
    if os.path.exists(FINAL_OUT):
        if not force:
            raise LiveInputExists(FINAL_OUT)
        print('Backed up existing input to:', _backup_existing(FINAL_OUT))

    wb = openpyxl.Workbook()

    # ================= Sheet 1: Project Info =================
    ws1 = wb.active
    ws1.title = 'Project Info'
    ws1['A1'] = 'Project Info — fill in the yellow cells, SAVE, then run "Run Budget Agent.cmd" (see top-right box)'
    ws1['A1'].font = TITLE_FONT
    ws1.merge_cells('A1:D1')
    ws1['A2'] = ('Shaped after the real "0. Info" sheet used across Savills\' 8 real project budget files, so it '
                 'matches what a new prospect would actually be able to supply up front. Residential only for now — '
                 'see the Property Segment note below.')
    ws1['A2'].font = SUB_FONT
    ws1.merge_cells('A2:D2')

    ws1['A3'] = 'Property Segment'
    ws1['A3'].font = Font(bold=True)
    c_segment = ws1.cell(row=3, column=2, value='Residential')
    c_segment.fill = INPUT_FILL
    c_segment.border = BORDER
    c_segment.alignment = CENTER
    dv_segment = DataValidation(type='list', formula1='"Residential,Commercial"',
                                 showErrorMessage=True, errorTitle='Invalid segment',
                                 error='Pick Residential or Commercial')
    ws1.add_data_validation(dv_segment)
    dv_segment.add(c_segment)
    c_segment.comment = Comment(
        'Commercial isn\'t built out yet — this pipeline\'s cost logic (management-fee rate, staffing pattern, '
        'Capex/OPEX scaling) is entirely Residential apartment-building math, comparable-matched on Apartment NFA. '
        'Selecting Commercial here will make generate_project_budget.py stop immediately with a clear error instead '
        'of silently running Residential math on a Commercial project. Real Commercial data does exist '
        '(Dim_Property_Commercial.csv, 59 comparables) but nothing in the generator reads it yet.',
        'Budget Planning Agent')

    section(ws1, 4, 'PROJECT SCALE')
    labeled_input(ws1, 5, 'Project Name', 'New Prospect')
    ws1['B5'].alignment = LEFT
    labeled_input(ws1, 6, 'Site Area (m²)', 12000)
    labeled_input(ws1, 7, 'Garden / Landscape Area (m²)', 1800)
    labeled_input(ws1, 8, 'Circulation / Hardscape Area (m²) — used as open-space proxy for roster', 6000)
    labeled_input(ws1, 9, 'Floor Count', 30)
    labeled_input(ws1, 10, 'Tower Count', 2)
    # Grouped with the other whole-building counts (change move-gate-and-pool-count-fields,
    # 2026-09-15) rather than left under AMENITIES, where it read oddly next to pool fields it has
    # nothing to do with. Moving it changes only where it sits on the sheet — read_input() finds it
    # by label, not position, so no code outside this file's own _GATE_COUNT constant depends on the
    # row number. See that constant, updated to match.
    labeled_input(ws1, 11, 'Gate / Entrance Count', 2)

    # District/City/Latitude/Longitude/Street Address/Passenger Elevators — moved INTO PROJECT SCALE
    # (2026-09-16, on request) rather than left as separate sections appended at the end of the
    # sheet, where they read as a late afterthought disconnected from the rest of the project's
    # basic facts. This IS an insertion into the middle of the sheet, not an append — normally
    # avoided on this file (see input_labels.py's own docstring on the row-shift risk), done safely
    # here only because every downstream absolute-cell reference was checked first: `grep
    # "'Project Info'!\$" across source_code/` finds exactly 5 hardcoded cell constants
    # (_TOWER_COUNT/_GARDEN_AREA/_OPEN_SPACE/_GATE_COUNT/_POOL_AREA, all just below, feeding Roster
    # Setup's staffing formulas) — the first four sit ABOVE this insertion point (rows 7/8/10/11) and
    # are untouched; only _POOL_AREA (below, in AMENITIES) shifted, and its constant was updated to
    # match. `read_input()` itself finds every field by label, never by row, so it needed no change.
    c_district = labeled_input(ws1, 12, 'District — leave blank if unknown', None)
    c_district.alignment = LEFT
    c_district.comment = Comment(
        "Used to prefer a real comparable property in the SAME district when ranking who this "
        "project's management-fee rate is derived from — a same-district match ranks ahead of a "
        "different-district one even if the latter is closer in size. Leave blank to keep today's "
        "size-only comparable matching. Spell it the way Savills' own Master List does (e.g. "
        "'Bình Thạnh', 'District 7', 'Thủ Đức') — matching is exact text, not fuzzy.",
        'Budget Planning Agent')
    c_city = labeled_input(ws1, 13, 'City / Province — leave blank if unknown', None)
    c_city.alignment = LEFT
    c_city.comment = Comment(
        "Fallback tier when no comparable shares this project's District above: prefers a comparable "
        "in the same city/province over one with no location match at all. Leave blank to keep "
        "today's size-only comparable matching.",
        'Budget Planning Agent')
    c_lat = labeled_input(ws1, 14, 'Latitude — leave blank if unknown', None)
    c_lat.alignment = LEFT
    c_lat.comment = Comment(
        "Decimal degrees (e.g. 10.8044), from Google Maps or the project's own siting documents — "
        "not looked up automatically. Used only to refine ordering WITHIN the District/City tier "
        "above (nearer comparables by real distance rank ahead of farther ones); it cannot move a "
        "comparable into a better tier than District/City already placed it in, and a comparable "
        "with no coordinates on file simply keeps ranking by size, exactly as today. Leave blank if "
        "unknown — District/City tiering alone still applies.",
        'Budget Planning Agent')
    c_lon = labeled_input(ws1, 15, 'Longitude — leave blank if unknown', None)
    c_lon.alignment = LEFT
    c_lon.comment = Comment(
        "Decimal degrees (e.g. 106.7476), paired with Latitude above — leave both blank together, "
        "or fill both; a lone value on just one of the two is treated as no coordinates at all.",
        'Budget Planning Agent')
    c_address = labeled_input(ws1, 16, 'Street Address — leave blank if unknown', None)
    c_address.alignment = LEFT
    c_address.comment = Comment(
        "Free text (e.g. \"11D Thi Sách, Bến Nghé, District 1\"). Printed on the deliverable as a "
        "citation only — does NOT feed District/City/Latitude/Longitude above or comparable "
        "matching; this pipeline has no address lookup or mapping capability. Fill in District/City "
        "(and Latitude/Longitude if known) separately for those to take effect.",
        'Budget Planning Agent')
    c_elevators = labeled_input(ws1, 17, 'Passenger Elevators per Tower — leave blank if unknown', None)
    c_elevators.alignment = LEFT
    c_elevators.comment = Comment(
        "PASSENGER elevators only — do not include cargo/freight elevators. Used to size the "
        "'Ad frame (tower lobby, inside elevator)' advertising-revenue line (an ad frame per "
        "passenger elevator bank) with this project's own real count instead of the standard "
        "~2-per-tower assumption. Does not affect the two LCD-screen advertising lines below — see "
        "Number of Basements just below for the one that does.",
        'Budget Planning Agent')
    # Grouped with Passenger Elevators above (2026-09-16, on request — both are real per-project
    # infrastructure counts, not location facts). Used to size the 'LCD screen (basement lobby)'
    # advertising-revenue line with a real count instead of the standard flat "1 per project"
    # assumption — same amendment pattern as the elevator field (change
    # wire-real-elevator-count-into-ad-revenue, task 2.6). No statutory or internal-data basis exists
    # for how many basements a building of a given size SHOULD have (checked directly: real Master
    # List data shows basement count tracks parking-slot count loosely, not floor count, and the
    # spread is too wide for a formula) — manual entry only, same reasoning as the elevator field.
    c_basements = labeled_input(ws1, 18, 'Number of Basements — leave blank if unknown', None)
    c_basements.alignment = LEFT
    c_basements.comment = Comment(
        "How many basement levels the building has (e.g. 1 shared basement under 2 towers = 1, not "
        "2). Used to size the 'LCD screen (basement lobby)' advertising-revenue line — one screen "
        "per basement level instead of the standard flat assumption of 1 screen per project "
        "regardless of basement count. Does not affect the 'Ad frame' or 'LCD screen (tower lobby)' "
        "lines. Leave blank to keep today's flat-1 assumption.",
        'Budget Planning Agent')

    section(ws1, 20, 'PRODUCT MIX — enter what applies, leave 0 for products this project doesn\'t have')
    headers = ['Product', 'GFA (m²)', 'NFA (m²)', 'Units']
    for c, h in enumerate(headers, start=1):
        cell = ws1.cell(row=21, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    # Nine products, matching generate_project_budget.py's PRODUCT_ROWS and PRODUCT_REVENUE_ROWS.
    # Order follows the template's own RM.* revenue rows so the form reads in the same sequence as
    # the deliverable. Adding or removing one here shifts every section below — see the row
    # constants immediately after this block, and read_input()'s matching cell references.
    products = ['Apartment', 'Officetel', 'Office', 'Shopping Mall', 'Retail',
                'Shop Apartment', 'Shophouse', 'Villas', 'Nursery / Nhà trẻ']
    example_apartment = (85000, 70000, 1300)
    for i, name in enumerate(products, start=22):
        c1 = ws1.cell(row=i, column=1, value=name)
        c1.border = BORDER
        c1.alignment = LEFT
        vals = example_apartment if name == 'Apartment' else (0, 0, 0)
        for j, v in enumerate(vals, start=2):
            c = ws1.cell(row=i, column=j, value=v)
            c.fill = INPUT_FILL
            c.border = BORDER
            c.alignment = CENTER
    APT_NFA_ROW = 22  # Apartment row — read_input() actually finds this by label, not this constant;
                       # kept in sync for any future direct reference, not read anywhere today.

    section(ws1, 32, 'PARKING')
    labeled_input(ws1, 33, 'Car Parking Slots', 300)
    labeled_input(ws1, 34, 'Moto Parking Slots', 2000)

    section(ws1, 36, 'AMENITIES (drive roster staffing)')
    dv_yn = DataValidation(type='list', formula1='"Yes,No"', showErrorMessage=True,
                            errorTitle='Invalid', error='Pick Yes or No')
    ws1.add_data_validation(dv_yn)
    c_pool = labeled_input(ws1, 37, 'Has Swimming Pool?', 'No')
    dv_yn.add(c_pool)
    # Grouped directly under 'Has Swimming Pool?' (change move-gate-and-pool-count-fields,
    # 2026-09-15) rather than appended at the end of the sheet, where it read as an afterthought
    # disconnected from the other pool fields. See input_labels.py's own docstring for why a MOVE
    # like this is safe where an insertion elsewhere might not be: read_input() finds every field by
    # label, and nothing outside this file addresses this field's row directly — grep
    # "'Project Info'!\$" across source_code/ before ever moving a field, to confirm that stays true.
    c_pool_count = labeled_input(ws1, 38, 'Number of Pools (count) — leave blank if unknown', 0)
    c_pool_count.comment = Comment(
        "How many distinct swimming pools the project has (e.g. 1 adult pool + 1 children's pool "
        "= 2). Separate from 'Pool Volume' below, which is already the TOTAL water volume across "
        "every pool and is what drives the ESM4 chemical-cost estimate — this count does not change "
        "that figure. Leave at 0 / blank if 'Has Swimming Pool?' is 'No'.",
        'Budget Planning Agent')
    labeled_input(ws1, 39, 'Pool Area (m²) — optional', 0)
    c_pool_vol = labeled_input(ws1, 40, 'Pool Volume (m³) — total water volume, all pools', 0)
    c_pool_vol.comment = Comment(
        "Total water volume across every pool, in cubic metres. EXENSIVE LOGIC.xlsx (ESM4) costs "
        "pool chemicals from VOLUME, not area: salt-electrolysis pools hold 4,000 ppm and consume "
        "roughly 1-4 kg of salt per m3 per month at about 6,000 VND/kg. Its worked example is an "
        "adult pool of 320 m3 plus a children's pool of 120 m3 = 440 m3. "
        "Leave at 0 if you do not know it — the budget then falls back to a flat reference figure "
        "taken from one real project and says so on the row. That fallback does NOT change with "
        "pool size, so a large pool and a small one cost the same.",
        'Budget Planning Agent')

    section(ws1, 42, "SAVILLS' MANAGEMENT FEE (EMH1) — leave BOTH blank until this project's real contract terms are known")
    c_fixed_fee = labeled_input(ws1, 43, 'Fixed Monthly Fee (VND) — leave blank if not fixed-fee', None)
    c_fee_pct = labeled_input(ws1, 44, "% of Collected Management Fee — leave blank if not %-based", None, fmt='0.0%')
    fee_comment_text = (
        "Real, negotiated per-project contract terms — cannot be derived or assumed. Blank means "
        "'not yet known', not zero: the generator leaves EMH1 (\"Management fee for Savills\") "
        "blank on the real template rather than defaulting to the wrong assumption this pipeline "
        "used before 2026-08-28 (Savills keeping 100% of the collected management fee, which "
        "double-counts against the real staff/OPEX/Capex costs the fee is meant to cover). Fill in "
        "ONE of these two fields once the real contract is known — a fixed VND/month amount (e.g. "
        "Green Skyline's real 88,000,000/month), or a % of the collected management fee — never "
        "both at once.")
    # Two separate Comment instances, not one shared object — openpyxl comments track their own
    # per-cell state, and reusing a single instance across cells risks corrupting the saved file.
    c_fixed_fee.comment = Comment(fee_comment_text, 'Budget Planning Agent')
    c_fee_pct.comment = Comment(fee_comment_text, 'Budget Planning Agent')

    # Appended after every existing field (change apply-guideline-remark-model, task-6 "Group B"),
    # not inserted between them — this sheet has a history of row-shift bugs from inserting fields
    # in the middle (see input_labels.py's own docstring), and read_input() finds every field by
    # label anyway, so appending is the only truly safe place to add one.
    #
    # REMARK-ONLY. The AI Guideline's RM narrative (docs/13-remark-case-model.md Group B) has a
    # blank for how many months of management fee the developer prepays on handover: "Ước tính
    # theo thông tin CĐT cung cấp thu trước .... tháng PQL cư dân khi bàn giao nhà". This pipeline's
    # RM.0A figure (the developer's top-up on un-handed-over units) is computed independently, from
    # the resident fill-up curve — it does NOT depend on this field. So filling it in only makes the
    # RM remark state the real month count instead of describing the mechanism without one; it
    # changes no budgeted figure. Left blank (None) is the honest default until the PM knows the
    # real negotiated term — same pattern as the Savills-fee fields just above.
    section(ws1, 46, "MANAGEMENT FEE PRE-COLLECTION (remark only — does not change any figure)")
    c_prepaid = labeled_input(
        ws1, 47, 'Months of Management Fee Prepaid on Handover — leave blank if unknown', None)
    c_prepaid.comment = Comment(
        "How many months of management fee the developer collects from a resident up front at "
        "handover, per the AI Guideline's RM remark (\"thu trước .... tháng PQL cư dân khi bàn giao "
        "nhà\"). This is the real negotiated collection term — cannot be assumed. Leave blank until "
        "known; the RM. management-fee remark then describes the mechanism (the developer covers "
        "the fee on units not yet handed over) without naming a month count, rather than guessing "
        "one. Filling it in only changes the wording of that remark — RM.0A's actual VND figure "
        "already comes from the resident fill-up curve and does not use this field.",
        'Budget Planning Agent')

    # Change complete-ai-guideline-remark-coverage, D1 — appended after every existing field (same
    # no-row-shift-risk reason as the prepaid field just above). One shared basis/year, not one per
    # product: a single building has one drawing set, not a different citation per product type.
    section(ws1, 49, "PRODUCT AREA CITATION (remark only — does not change any figure)")
    c_area_basis = labeled_input(
        ws1, 50, 'Area basis / drawing reference — leave blank if unknown', None)
    c_area_basis.comment = Comment(
        "The legal/drawing basis for the chargeable areas on '0. Info' (e.g. \"NSA per the TKTC "
        "construction drawings\"), per the AI Guideline's '0. Info' remark. This is a real "
        "project-specific citation — cannot be assumed. Leave blank until known; the '0. Info' "
        "remark then states the area is PM-supplied, without inventing a drawing reference. Does "
        "not change any area or fee figure — wording only.",
        'Budget Planning Agent')
    c_area_year = labeled_input(
        ws1, 51, 'Area basis confirmed as of year — leave blank if unknown', None)
    c_area_year.comment = Comment(
        "The year the area basis above was last confirmed/updated by the Investor (e.g. 2026). "
        "Paired with the area basis field — leave blank if that field is blank.",
        'Budget Planning Agent')

    # Appended, not inserted — same no-row-shift-risk reason as every field added above (see
    # input_labels.py's own docstring on why appending, not inserting, is the default-safe choice).
    section(ws1, 53, 'BUDGET HORIZON')
    c_years = labeled_input(ws1, 54, 'Operating Years to Budget', 1)
    c_years.comment = Comment(
        "How many operating years the budget should cover, counting from handover. 1 means the "
        "first operating year only — what this pipeline produces today, and the default. "
        "A value above 1 is currently REJECTED rather than ignored: the per-year budget sheets, "
        "year-on-year cost escalation and multi-year summary it implies are specified but not yet "
        "built, so accepting it would give you a one-year workbook that claims to be more. "
        "Any pre-opening phase before handover is counted separately and is not part of this "
        "number.",
        'Budget Planning Agent')

    # Appended, not inserted — same no-row-shift-risk reason as every field above (change
    # derive-capex-reserve-rate, task 4, 2026-09-21).
    c_capex_drop = labeled_input(
        ws1, 55, 'Capex Drop-to-Reserve Year — leave blank for the evidenced default (Year 2)', None)
    c_capex_drop.comment = Comment(
        "On the Owner Operating Position / Savills Fee Position sheets' 4-year Capex sinking-fund "
        "table: Year 1 always carries the full initial lump-sum purchase. Years BEFORE this field's "
        "value also carry a full lump sum (equipment bought again); this year and every year after "
        "it carry the derived ongoing reserve contribution instead. Default (blank): Year 2 — what "
        "3 of the 4 real reference projects behind the derived rate actually do. Enter 3 or 4 if "
        "this project's own replacement cycle is known to be longer (Green Skyline, one of those "
        "four, repeats a full purchase in Year 2 and drops in Year 3 — costs ~290M VND differently "
        "from the default on that shape of project). Year 1 cannot be entered here — it always "
        "carries the full lump sum.",
        'Budget Planning Agent')

    for col, w in {'A': 34, 'B': 16, 'C': 16, 'D': 14}.items():
        ws1.column_dimensions[col].width = w

    add_run_button(ws1)          # green RUN button at F1:G2, hyperlinked to Run Budget Agent.cmd

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
    ws2['A17'] = ('LEAVE BLANK and the pipeline fills these in from the Month and Year above — Tết and '
                  'Hùng Kings\' Day are lunar and get converted properly, not hardcoded. The reference '
                  'table below lists every statutory day for 2026 and 2027 so you can see what it will '
                  'use. Type dates here ONLY to override — for example to apply the government\'s annual '
                  '"hoán đổi" swap-day announcement, which is a policy decision and cannot be computed.')
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

    # ---- Reference block: every statutory holiday, computed and written out, so a PM can SEE what
    # the pipeline will use rather than trusting an invisible calculation. Read-only — the yellow
    # block above is the override. Added 2026-09-09 after the dates were computed but nowhere shown.
    from vn_holidays import paid_days_of_year
    r = HOLIDAY_LAST_ROW + 2
    section(ws2, r, 'STATUTORY HOLIDAYS — REFERENCE ONLY (computed, do not edit)')
    r += 1
    note = ws2.cell(row=r, column=1, value=(
        'Labour Code 2019 Article 112 clause 1 — 11 days a year, plus 24 November (Ngày Văn hóa Việt Nam) from '
        '01/07/2026 under Nghị quyết 28/2026/QH16 Article 2: 12 days from 2026. Tết and Giỗ Tổ Hùng Vương are lunar, so they move '
        'every year; these are converted with the Vietnamese lunar calendar (UTC+7) and the conversion is '
        'checked against six past Tết dates on every run. NOT included: the annual "hoán đổi" swap days, '
        'which extend Tết in practice and are announced by the government each year — type those into the '
        'yellow block above if this project needs them.'))
    note.font = LEGEND_FONT
    note.alignment = LEFT
    ws2.merge_cells(f'A{r}:D{r}')
    ws2.row_dimensions[r].height = 46
    r += 1
    # 'Holiday date', not 'Date' — the input block above already has 'Date (DD)', and the label
    # resolver reduces both to 'date' and refuses to guess between them.
    for c, h in enumerate(['Holiday date', 'Day', 'Month', 'Holiday'], start=1):
        cell = ws2.cell(row=r, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.border = BORDER
        cell.alignment = CENTER
    r += 1
    for yr in (2026, 2027):
        for d, name in paid_days_of_year(yr):
            ws2.cell(row=r, column=1, value=d.strftime('%Y-%m-%d')).alignment = CENTER
            ws2.cell(row=r, column=2, value=d.strftime('%a')).alignment = CENTER
            ws2.cell(row=r, column=3, value=d.month).alignment = CENTER
            ws2.cell(row=r, column=4, value=name).alignment = LEFT
            for c in range(1, 5):
                ws2.cell(row=r, column=c).border = BORDER
                ws2.cell(row=r, column=c).fill = COMPUTED_FILL
            r += 1

    for col, w in {'A': 30, 'B': 34, 'C': 14, 'D': 46}.items():
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
        c1.protection = Protection(locked=False)
        c2 = ws4.cell(row=i, column=2, value=code)
        c2.border = BORDER
        c2.alignment = CENTER
        c2.fill = INPUT_FILL
        c2.protection = Protection(locked=False)
        dv_shift.add(c2)
        # Staff On Duty / Day: a row seeded with a live formula (the ratio-driven rows — Main Gate,
        # Patrol, Cleaning, Gardener, Pool Attendant) stays LOCKED, so a stray paste or fill-handle
        # drag can't silently wipe out the formula, which is what actually happened before this was
        # added — the three-case rule in _staff_on_duty() would then read whatever number landed
        # there as a deliberate override, with no sign anything was lost.
        #
        # This does not remove the override this sheet is built around (see _staff_on_duty()) — it
        # changes how you make one. Today, typing over a live cell IS the override. With protection
        # on, Excel blocks that keystroke and shows "this cell is protected"; Review > Unprotect
        # Sheet (one click, no password) opens it back up. That extra step is the point: it turns an
        # accidental overwrite into an impossible one, while leaving a deliberate override exactly as
        # available as before. A row with no formula (every other position, including the ones
        # 2026-09-14 wired to the portfolio-derived ratios — those are seeded as a plain number, not
        # a formula, so there is nothing here to protect) stays unlocked as it always was.
        is_formula_row = isinstance(staff, str) and staff.lstrip().startswith('=')
        c3 = ws4.cell(row=i, column=3, value=staff)
        c3.border = BORDER
        c3.alignment = CENTER
        c3.fill = INPUT_FILL
        c3.protection = Protection(locked=is_formula_row)
        c4 = ws4.cell(row=i, column=4, value=days)
        c4.border = BORDER
        c4.alignment = CENTER
        c4.fill = INPUT_FILL
        c4.protection = Protection(locked=False)
        c5 = ws4.cell(row=i, column=5, value=rate)
        c5.number_format = '#,##0'
        c5.border = BORDER
        c5.fill = INPUT_FILL
        c5.protection = Protection(locked=False)
        if note:
            c5.comment = Comment(note, 'Budget Planning Agent')
    for col, w in {'A': 30, 'B': 12, 'C': 18, 'D': 18, 'E': 20}.items():
        ws4.column_dimensions[col].width = w

    # Existing-project mode (change carry-forward-staffing): appended after every existing field,
    # same no-row-shift rule as above.
    add_existing_project_fields(ws1, 57)
    add_prior_year_roster_sheet(wb)
    add_demand_reason_columns(ws4, 5, last_row)

    # Protection only bites where a cell is explicitly locked (every yellow cell above was just set
    # to locked=False) — the row/section headers, this sheet's own two title cells, and any blank
    # row beyond `last_row` stay at openpyxl's default (locked=True) and are now genuinely protected
    # too, which is appropriate: there is nothing to type into a header. insertRows/deleteRows are
    # explicitly allowed so "edit, add, or delete rows freely" (this sheet's own A1 title) keeps
    # working with protection on. No password — Review > Unprotect Sheet is one click; the goal is
    # stopping an accidental keystroke, not gatekeeping a deliberate one.
    ws4.protection.sheet = True
    ws4.protection.insertRows = False
    ws4.protection.deleteRows = False
    ws4.protection.formatCells = False
    ws4.protection.formatRows = False
    ws4.protection.selectLockedCells = False
    ws4.protection.selectUnlockedCells = False

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
    parser = argparse.ArgumentParser(description='Build a blank Project_Budget_Input.xlsx in reports/.')
    parser.add_argument('--force', action='store_true',
                        help='replace an existing Project_Budget_Input.xlsx (it is backed up first)')
    args = parser.parse_args()
    try:
        main(force=args.force)
    except (LiveInputExists, LiveInputBackupFailed) as exc:
        print('STOPPED:', exc)
        sys.exit(1)
