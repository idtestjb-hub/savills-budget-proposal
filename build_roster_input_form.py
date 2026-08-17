"""
Builds the fillable roster INPUT FORM — Roster_Input_Form.xlsx.

v4: adds Gate Count + Open Space Area to Project Info, and a "Staffing Ratios" section that
drives Staff On Duty / Day as a LIVE FORMULA for gate-, area-, and tower-scaled positions
(Security - Main Gate, Security - Patrol, Cleaning - Common Area, Cleaning - Supervisor,
Gardener) instead of a typed-in number.

Important honesty note on the ratios: there is no real dataset to derive "1 security staff per
X m²" from. The 89-property staff-headcount data (Project_Detail_Lists.xlsx) and the 8-project
scale data (Dim_Property_v2_verified.csv) are disjoint populations with no shared identifier —
same gap documented in docs/Fact_Dim_Master_Mapping.md. So these ratios are editable PM
assumptions with reasonable starting defaults, NOT a benchmark computed from real Savills data.
Change them to your own operational standard before trusting the suggested counts.

Three sheets:
  Setup             Project Info + Staffing Ratios (assumptions) + Month/Year/holiday dates.
  Shift Types       reference table (not edited).
  Staffing Demand   Position, Shift Code (dropdown), staff/day (formula for scaled positions,
                    typed number otherwise), coverage days, daily rate.

Pool Attendant and Gardener/Landscape rates use REAL rates from Fact_MasterRateCard.csv, cited
in a comment on each cell — not invented numbers. Delete rows for amenities the project doesn't
have.
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
FINAL_OUT = os.path.join(OUT_DIR, 'Roster_Input_Form.xlsx')
OUT = os.path.join(tempfile.gettempdir(), 'Roster_Input_Form.xlsx')

SHIFT_CODES = ['HC', 'S', 'C', 'D', '24H']
SHIFT_REF = [
    ('HC', 'Hành chính / Admin hours', '08:00-17:00', 8, 'No'),
    ('S', 'Ca sáng / Morning shift', '06:00-15:00', 9, 'No'),
    ('C', 'Ca chiều / Afternoon shift', '13:00-22:00', 9, 'No'),
    ('D', 'Ca đêm / Night shift (24h post overnight portion)', '22:00-06:00', 8, 'Yes'),
    ('24H', '24/24 continuous post', '00:00-24:00', 24, 'Yes'),
]

# (Position, ShiftCode, StaffPerDay, CoverageDays, AvgDailyRate, source_note)
# Daily rate = real Fact_MasterRateCard monthly total / 26 working days (VN convention).
#
# Security is 3-shift coverage (S/C/D), not a single "24H" row: the real rate card prices
# "24/24 position (all roles)" as ONE POST covering round-the-clock, priced as a team — not one
# person working a continuous 24-hour shift. Nobody can humanely work 24h on, <24h off, six days
# out of seven. S (morning) + C (afternoon) + D (night) together cover the 24 hours realistically,
# each person working one 8-9 hour shift. The "24H" shift type stays in Shift Types for the rare
# case a post is genuinely covered by actual 24h-on/48h-off duty guards — just don't use it as a
# daily-rotation shift code the way this script's round-robin (1 day off per 7) assumes.
_SECURITY_MONTHLY_ALL_ROLES = 17_500_000  # Fact_MasterRateCard.csv: Service/Security "24/24 position (all roles)"
_SECURITY_DAILY_PER_ROLE = round(_SECURITY_MONTHLY_ALL_ROLES / 3 / 26, -3)  # split 3 shift-roles, /26 working days
_SECURITY_NOTE = (
    f'Source: Fact_MasterRateCard.csv, Service/Security "24/24 position (all roles)" row — '
    f'{_SECURITY_MONTHLY_ALL_ROLES:,} VND/month covers all 3 shift roles for one post. '
    f'Split 3 ways = {_SECURITY_MONTHLY_ALL_ROLES // 3:,}/month per role ÷ 26 working days ≈ {_SECURITY_DAILY_PER_ROLE:,.0f}/day.'
)

# Cell refs into the Setup sheet's Staffing Ratios block (defined once the layout is fixed below).
_GATE_COUNT = 'Setup!$B$13'
_OPEN_SPACE = 'Setup!$B$14'
_TOWER_COUNT = 'Setup!$B$5'
_GARDEN_AREA = 'Setup!$B$12'
_STAFF_PER_GATE = 'Setup!$B$19'
_SQM_PER_PATROL = 'Setup!$B$20'
_SQM_PER_CLEANER = 'Setup!$B$21'
_TOWERS_PER_SUPERVISOR = 'Setup!$B$22'
_SQM_PER_GARDENER = 'Setup!$B$23'

_RATIO_NOTE = ('Formula-driven from Setup!Staffing Ratios — an editable PM assumption, not a real benchmark '
               '(no dataset joins staff headcount to property scale for the same properties; see '
               'Fact_Dim_Master_Mapping.md). Adjust the ratio in Setup, not this cell, to change the suggestion.')

# (Position, ShiftCode, StaffPerDay [int or "=formula"], CoverageDays, AvgDailyRate, source_note)
# Daily rate = real Fact_MasterRateCard monthly total / 26 working days (VN convention).
EXAMPLE_DEMAND = [
    ('Security - Main Gate (Morning)', 'S', f'=ROUNDUP({_GATE_COUNT}*{_STAFF_PER_GATE},0)', 7, _SECURITY_DAILY_PER_ROLE, _SECURITY_NOTE + ' ' + _RATIO_NOTE),
    ('Security - Main Gate (Afternoon)', 'C', f'=ROUNDUP({_GATE_COUNT}*{_STAFF_PER_GATE},0)', 7, _SECURITY_DAILY_PER_ROLE, _SECURITY_NOTE + ' ' + _RATIO_NOTE),
    ('Security - Main Gate (Night)', 'D', f'=ROUNDUP({_GATE_COUNT}*{_STAFF_PER_GATE},0)', 7, _SECURITY_DAILY_PER_ROLE, _SECURITY_NOTE + ' ' + _RATIO_NOTE),
    ('Security - CCTV Room (Morning)', 'S', 1, 7, _SECURITY_DAILY_PER_ROLE, _SECURITY_NOTE + ' Not gate-scaled — a control room is normally 1 regardless of gate count.'),
    ('Security - CCTV Room (Afternoon)', 'C', 1, 7, _SECURITY_DAILY_PER_ROLE, _SECURITY_NOTE),
    ('Security - CCTV Room (Night)', 'D', 1, 7, _SECURITY_DAILY_PER_ROLE, _SECURITY_NOTE),
    ('Security - Patrol / Open Space', 'S', f'=ROUNDUP({_OPEN_SPACE}/{_SQM_PER_PATROL},0)', 7, _SECURITY_DAILY_PER_ROLE,
     _SECURITY_NOTE + ' ' + _RATIO_NOTE + ' Shown for one shift only — for full 24h patrol coverage, copy this row for C and D shifts too, same pattern as Main Gate.'),
    ('Cleaning - Common Area', 'S', f'=ROUNDUP({_OPEN_SPACE}/{_SQM_PER_CLEANER},0)', 7, 340000, _RATIO_NOTE),
    ('Cleaning - Supervisor', 'HC', f'=ROUNDUP({_TOWER_COUNT}/{_TOWERS_PER_SUPERVISOR},0)', 6, 480000, _RATIO_NOTE),
    ('Reception', 'HC', 1, 7, 340000, None),
    ('Pool Attendant', 'S', 1, 7, 314000,
     'Source: Fact_MasterRateCard.csv, "Gym - Pool Attendant" row — 8,156,849 VND/month ÷ 26 working days ≈ 314,000/day. Delete this row if no pool.'),
    ('Gardener / Landscape', 'HC', f'=ROUNDUP({_GARDEN_AREA}/{_SQM_PER_GARDENER},0)', 6, 423000,
     'Source: Fact_MasterRateCard.csv, Service/Landscape "8/24 position" row — 11,000,000 VND/month (A&K Tower real project) ÷ 26 ≈ 423,000/day. Delete this row if no garden. ' + _RATIO_NOTE),
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

    # ================= Sheet 1: Setup =================
    ws1 = wb.active
    ws1.title = 'Setup'
    ws1['A1'] = 'Roster Setup — fill in the yellow cells, then run generate_roster.py'
    ws1['A1'].font = TITLE_FONT
    ws1.merge_cells('A1:D1')

    section(ws1, 3, 'PROJECT INFO')
    labeled_input(ws1, 4, 'Project Name', 'Sunrise Marina')
    ws1['B4'].alignment = LEFT
    labeled_input(ws1, 5, 'Tower Count', 2)
    labeled_input(ws1, 6, 'Site Area (m²)', 12000)
    labeled_input(ws1, 7, 'Building GFA (m²)', 85000)
    labeled_input(ws1, 8, 'Apartment Units', 1300)
    dv_yn = DataValidation(type='list', formula1='"Yes,No"', showErrorMessage=True,
                            errorTitle='Invalid', error='Pick Yes or No')
    ws1.add_data_validation(dv_yn)
    c_pool = labeled_input(ws1, 9, 'Has Swimming Pool?', 'Yes')
    dv_yn.add(c_pool)
    labeled_input(ws1, 10, 'Pool Area (m²) — optional', 450)
    dv_garden = DataValidation(type='list', formula1='"Yes,No"', showErrorMessage=True,
                                errorTitle='Invalid', error='Pick Yes or No')
    ws1.add_data_validation(dv_garden)
    c_garden = labeled_input(ws1, 11, 'Has Garden / Landscape?', 'Yes')
    dv_garden.add(c_garden)
    labeled_input(ws1, 12, 'Garden Area (m²) — optional', 1800)
    labeled_input(ws1, 13, 'Gate / Entrance Count', 2)
    labeled_input(ws1, 14, 'Open Space / Common Outdoor Area (m²)', 6000)

    section(ws1, 16, 'STAFFING RATIOS — adjust to your own standard')
    ws1['A17'] = ('These are editable assumptions, not a real benchmark — there is no dataset that joins '
                  'staff headcount to property scale for the same properties (the 89-property staffing data '
                  'and the 8-project scale data are disjoint populations; see Fact_Dim_Master_Mapping.md). '
                  'Change these to your own operational standard — Staffing Demand below recalculates automatically.')
    ws1['A17'].font = LEGEND_FONT
    ws1['A17'].alignment = LEFT
    ws1.merge_cells('A17:D17')
    ws1.row_dimensions[17].height = 50
    labeled_input(ws1, 19, 'Security: Staff per Gate', 1)
    labeled_input(ws1, 20, 'Security: m² Open Space per Patrol Staff', 5000)
    labeled_input(ws1, 21, 'Cleaning: m² Open Space per Cleaner', 3000)
    labeled_input(ws1, 22, 'Cleaning: Towers per Supervisor', 2)
    labeled_input(ws1, 23, 'Landscape: m² Garden per Gardener', 2000)

    section(ws1, 25, 'SCHEDULE SETUP')
    labeled_input(ws1, 26, 'Month (1-12)', 9)
    dv_month = DataValidation(type='whole', operator='between', formula1=1, formula2=12,
                               showErrorMessage=True, errorTitle='Invalid month', error='Enter 1-12')
    ws1.add_data_validation(dv_month)
    dv_month.add(ws1['B26'])
    labeled_input(ws1, 27, 'Year', 2026)
    ws1['A28'] = 'Days in this month (auto)'
    ws1['A28'].font = Font(bold=True)
    c28 = ws1.cell(row=28, column=2, value='=DAY(EOMONTH(DATE(B27,B26,1),0))')
    c28.fill = COMPUTED_FILL
    c28.border = BORDER
    c28.alignment = CENTER
    c28.font = Font(italic=True)

    section(ws1, 30, 'PUBLIC HOLIDAYS THIS MONTH')
    ws1['A31'] = ('Lunar-calendar holidays (Tết, Hùng Kings\' Day) move every year — enter the actual '
                  'dates from your company\'s official 2026 calendar, one per row below. Fixed-date '
                  'holidays (Jan 1, Apr 30, May 1, Sep 2) still need to be entered here too — nothing '
                  'is assumed automatically.')
    ws1['A31'].font = LEGEND_FONT
    ws1['A31'].alignment = LEFT
    ws1.merge_cells('A31:D31')
    ws1.row_dimensions[31].height = 42

    ws1['A33'] = 'Date (DD)'
    ws1['B33'] = 'Holiday name'
    for c in ('A33', 'B33'):
        ws1[c].fill = HEADER_FILL
        ws1[c].font = HEADER_FONT
        ws1[c].border = BORDER
        ws1[c].alignment = CENTER
    example_holidays = {34: (2, 'National Day')}
    for r in range(34, 44):
        c1 = ws1.cell(row=r, column=1)
        c1.fill = INPUT_FILL
        c1.border = BORDER
        c1.alignment = CENTER
        c2 = ws1.cell(row=r, column=2)
        c2.fill = INPUT_FILL
        c2.border = BORDER
        if r in example_holidays:
            day, name = example_holidays[r]
            c1.value = day
            c2.value = name
    for col, w in {'A': 30, 'B': 34, 'C': 14, 'D': 14}.items():
        ws1.column_dimensions[col].width = w

    # ================= Sheet 2: Shift Types (reference) =================
    ws2 = wb.create_sheet('Shift Types')
    ws2['A1'] = 'Shift Type Reference — do not edit, used by the Shift Code dropdown and roster formulas'
    ws2['A1'].font = TITLE_FONT
    ws2.merge_cells('A1:E1')
    headers = ['Code', 'Name', 'Hours', 'Duration (hrs)', 'Night Shift?']
    for c, h in enumerate(headers, start=1):
        cell = ws2.cell(row=3, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    for i, row_vals in enumerate(SHIFT_REF, start=4):
        for c, v in enumerate(row_vals, start=1):
            cell = ws2.cell(row=i, column=c, value=v)
            cell.border = BORDER
            cell.alignment = LEFT if c == 2 else CENTER
    for col, w in {'A': 8, 'B': 44, 'C': 16, 'D': 14, 'E': 12}.items():
        ws2.column_dimensions[col].width = w

    # ================= Sheet 3: Staffing Demand =================
    ws3 = wb.create_sheet('Staffing Demand')
    ws3['A1'] = 'Staffing Demand — edit, add, or delete rows freely'
    ws3['A1'].font = TITLE_FONT
    ws3.merge_cells('A1:E1')
    ws3['A2'] = 'Shift Code must match a code from the "Shift Types" sheet — use the dropdown. Rates cited in cell comments where sourced from real data.'
    ws3['A2'].font = SUB_FONT
    ws3.merge_cells('A2:E2')

    headers3 = ['Position', 'Shift Code', 'Staff On Duty / Day', 'Coverage Days / Week', 'Avg Daily Rate (VND)']
    for c, h in enumerate(headers3, start=1):
        cell = ws3.cell(row=4, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER

    dv_shift = DataValidation(type='list', formula1='"' + ','.join(SHIFT_CODES) + '"',
                               showErrorMessage=True, errorTitle='Invalid shift code',
                               error='Pick a code from the Shift Types sheet')
    ws3.add_data_validation(dv_shift)

    last_row = 4 + max(len(EXAMPLE_DEMAND), 20)
    for i in range(5, last_row + 1):
        idx = i - 5
        if idx < len(EXAMPLE_DEMAND):
            pos, code, staff, days, rate, note = EXAMPLE_DEMAND[idx]
        else:
            pos = code = staff = days = rate = note = None
        c1 = ws3.cell(row=i, column=1, value=pos)
        c1.border = BORDER
        c1.alignment = LEFT
        c1.fill = INPUT_FILL
        c2 = ws3.cell(row=i, column=2, value=code)
        c2.border = BORDER
        c2.alignment = CENTER
        c2.fill = INPUT_FILL
        dv_shift.add(c2)
        c3 = ws3.cell(row=i, column=3, value=staff)
        c3.border = BORDER
        c3.alignment = CENTER
        c3.fill = INPUT_FILL
        c4 = ws3.cell(row=i, column=4, value=days)
        c4.border = BORDER
        c4.alignment = CENTER
        c4.fill = INPUT_FILL
        c5 = ws3.cell(row=i, column=5, value=rate)
        c5.number_format = '#,##0'
        c5.border = BORDER
        c5.fill = INPUT_FILL
        if note:
            c5.comment = Comment(note, 'Budget Planning Agent')
    for col, w in {'A': 30, 'B': 12, 'C': 18, 'D': 18, 'E': 20}.items():
        ws3.column_dimensions[col].width = w

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
