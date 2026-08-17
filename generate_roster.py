"""
Roster/shift GENERATION model — reads Roster_Input_Form.xlsx and produces a full calendar-month
roster where the schedule grid and every cost number are LIVE EXCEL FORMULAS, not Python-computed
values. Change a rate, a holiday date, or the month in the form and reopen the output — Excel
recalculates it, nothing needs to be re-run except when the number of STAFF ROWS changes (that's
a structural layout decision — how many rows to draw — which Python still makes once, at
generation time; see the note below).

v3 added: Project Info (tower count, areas, apartment units, pool/garden) read from the form and
shown in the roster's header for context. The schedule grid cells, day/weekday headers,
days-in-month, holiday highlighting, and every Cost Summary number are formulas referencing
Setup/Staffing Demand/Shift Types directly — not values baked in by this script.

v4 added: Gate Count, Open Space, and a Staffing Ratios block in the form's Setup sheet, so
Staff On Duty / Day for gate-, area-, and tower-scaled positions arrives here as an already-
resolved formula result (see build_roster_input_form.py for where that formula lives — it's
evaluated in the input form, not here). This script just reads whatever number that formula
cached; it doesn't know or care whether a Staffing Demand cell was typed or computed.

What's still a build-time (not live-formula) decision: how many staff rows to draw for each
position. Excel formulas can't dynamically add or remove rows without VBA or spill functions
(avoided here — LibreOffice can't evaluate them reliably). So Python still computes staff_count
= ceil(K*7/6) once to know how many rows to lay out; that same formula is ALSO shown as a live
cell in Cost Summary so the number is transparent and re-checkable, not just trusted.

Outputs: reports/Roster_Demand_Model.xlsx
  - Shift Types       reference table (copied from the form)
  - Generated Roster  full calendar-month grid, every schedule cell a formula
  - Cost Summary      every column a formula referencing the roster grid + Staffing Demand
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

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
FORM_PATH = os.path.join(BASE, 'reports', 'Roster_Input_Form.xlsx')
OUT_DIR = os.path.join(BASE, 'reports')
FINAL_OUT = os.path.join(OUT_DIR, 'Roster_Demand_Model.xlsx')
OUT = os.path.join(tempfile.gettempdir(), 'Roster_Demand_Model.xlsx')  # save locally first (OneDrive sync lock workaround)

MAX_DAYS = 31
DAY_COL_START = 3  # column C
DAY_COL_END = DAY_COL_START + MAX_DAYS - 1  # column AG (33)
COL_DAYOFF = DAY_COL_END + 1   # AH — hidden helper
COL_SHIFTCODE = DAY_COL_END + 2  # AI — hidden helper


def read_input_form(path):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Roster_Input_Form.xlsx not found at {path}.\n"
            "Run build_roster_input_form.py first, fill it in, then re-run this script."
        )
    wb = openpyxl.load_workbook(path, data_only=True)

    ws_setup = wb['Setup']
    project = dict(
        name=ws_setup['B4'].value, towers=ws_setup['B5'].value, site_area=ws_setup['B6'].value,
        gfa=ws_setup['B7'].value, units=ws_setup['B8'].value,
        has_pool=str(ws_setup['B9'].value).strip().lower() == 'yes',
        pool_area=ws_setup['B10'].value,
        has_garden=str(ws_setup['B11'].value).strip().lower() == 'yes',
        garden_area=ws_setup['B12'].value,
        gate_count=ws_setup['B13'].value, open_space=ws_setup['B14'].value,
    )
    ratios = dict(
        staff_per_gate=ws_setup['B19'].value, sqm_per_patrol=ws_setup['B20'].value,
        sqm_per_cleaner=ws_setup['B21'].value, towers_per_supervisor=ws_setup['B22'].value,
        sqm_per_gardener=ws_setup['B23'].value,
    )
    month, year = ws_setup['B26'].value, ws_setup['B27'].value
    if not month or not year:
        raise ValueError("Setup!B26 (Month) and Setup!B27 (Year) must both be filled in.")
    month, year = int(month), int(year)

    holiday_days = set()
    for r in range(34, 44):
        d = ws_setup.cell(row=r, column=1).value
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
        if staff is None:
            raise ValueError(
                f"Staffing Demand row {r} ('{pos}'): Staff On Duty / Day is blank. If this cell holds a "
                "formula (ratio-driven row), open Roster_Input_Form.xlsx in Excel and save it once so the "
                "formula has a cached value openpyxl can read — this file was likely built but never opened."
            )
        demand.append(dict(
            Position=str(pos), ShiftCode=str(code),
            StaffPerDay=int(round(staff)), CoverageDays=int(days), AvgDailyRate=float(rate),
            SourceRow=r,
        ))
    if not demand:
        raise ValueError("Staffing Demand sheet has no complete rows — fill in Position + Shift Code at minimum.")

    return project, ratios, month, year, holiday_days, demand


# ============ Styling ============
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


def main():
    project, ratios, month, year, holiday_days, demand = read_input_form(FORM_PATH)
    days_in_month = cal.monthrange(year, month)[1]
    month_name = cal.month_name[month]
    print(f"Generating formula-driven roster for {project['name']} — {month_name} {year} "
          f"({days_in_month} days), holidays flagged: {sorted(holiday_days) or 'none'}")

    os.makedirs(OUT_DIR, exist_ok=True)
    wb = openpyxl.Workbook()

    # ---- Sheet 1: Shift Types (reference, formulas point at this) ----
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

    # ---- Sheet 2: Staffing Demand (copied from the form, formulas reference THIS copy) ----
    ws2 = wb.create_sheet('Staffing Demand')
    ws2['A1'] = f'Staffing Demand — copied from Roster_Input_Form.xlsx for {project["name"]}'
    ws2['A1'].font = TITLE_FONT
    ws2.merge_cells('A1:E1')
    ws2['A2'] = 'To change these numbers: edit Roster_Input_Form.xlsx and re-run generate_roster.py.'
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
        d['DemandRow'] = i  # row in THIS sheet, for formula references
    for col, w in {'A': 30, 'B': 12, 'C': 18, 'D': 18, 'E': 20}.items():
        ws2.column_dimensions[col].width = w

    # Setup mini-sheet holding Month/Year/Holidays so roster formulas have something to reference
    ws0 = wb.create_sheet('Setup')
    ws0['A1'] = 'Project Info + Schedule Setup (copied from Roster_Input_Form.xlsx)'
    ws0['A1'].font = TITLE_FONT
    ws0.merge_cells('A1:B1')
    info_rows = [
        ('Project Name', project['name']), ('Tower Count', project['towers']),
        ('Site Area (m²)', project['site_area']), ('Building GFA (m²)', project['gfa']),
        ('Apartment Units', project['units']),
        ('Has Swimming Pool?', 'Yes' if project['has_pool'] else 'No'),
        ('Pool Area (m²)', project['pool_area']),
        ('Has Garden / Landscape?', 'Yes' if project['has_garden'] else 'No'),
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
    # info_rows has 18 entries starting at row 3, so Month lands on row 20, Year on row 21.
    ws0['A22'] = 'Days in month'
    ws0['A22'].font = Font(bold=True)
    ws0['B22'] = '=DAY(EOMONTH(DATE(B21,B20,1),0))'
    ws0['A24'] = 'Holiday dates this month'
    ws0['A24'].font = Font(bold=True)
    for i, d in enumerate(sorted(holiday_days), start=25):
        ws0.cell(row=i, column=1, value=d)
    holiday_last_row = max(25 + len(holiday_days) - 1, 25)
    ws0.column_dimensions['A'].width = 40
    ws0.column_dimensions['B'].width = 20
    MONTH_CELL = 'Setup!$B$20'
    YEAR_CELL = 'Setup!$B$21'
    DAYS_IN_MONTH_CELL = 'Setup!$B$22'
    HOLIDAY_RANGE = f'Setup!$A$25:$A${holiday_last_row}'

    # ---- Sheet: Generated Roster (formula-driven grid) ----
    ws3 = wb.create_sheet('Generated Roster')
    header_bits = [f"{project['towers']} tower(s)", f"{project['gfa']:,.0f} m² GFA" if project['gfa'] else None,
                   f"{project['units']:,.0f} units" if project['units'] else None,
                   f"{project['gate_count']} gate(s)" if project['gate_count'] else None,
                   f"{project['open_space']:,.0f} m² open space" if project['open_space'] else None,
                   'pool' if project['has_pool'] else None, 'garden' if project['has_garden'] else None]
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

    HOLIDAY_FLAG_ROW = 5   # hidden
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
        # Row 5 (hidden): TRUE/FALSE holiday flag for this day column
        f_flag = ws3.cell(row=HOLIDAY_FLAG_ROW, column=c,
                           value=f'=IF({col_letter}{DAY_NUM_ROW}="",FALSE,COUNTIF({HOLIDAY_RANGE},{col_letter}{DAY_NUM_ROW})>0)')
        # Row 6: day number, blank past days-in-month
        f_day = ws3.cell(row=DAY_NUM_ROW, column=c,
                          value=f'=IF(COLUMN()-{DAY_COL_START - 1}<={DAYS_IN_MONTH_CELL},COLUMN()-{DAY_COL_START - 1},"")')
        f_day.fill = HEADER_FILL
        f_day.font = HEADER_FONT
        f_day.alignment = CENTER
        f_day.border = BORDER
        # Row 7: weekday abbreviation
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
            # Hidden helper columns
            ws3.cell(row=r, column=COL_DAYOFF, value=f'=MOD(ROW()-{first_row},7)')
            ws3.cell(row=r, column=COL_SHIFTCODE, value=f'={demand_ref}')
            r += 1
        last_row = r - 1
        priced.append(dict(demand=d, first_row=first_row, last_row=last_row, staff_count=staff_count))
        r += 1  # blank spacer row between positions

    ws3.column_dimensions['A'].width = 26
    ws3.column_dimensions['B'].width = 12
    for c in range(DAY_COL_START, DAY_COL_END + 1):
        ws3.column_dimensions[get_column_letter(c)].width = 5
    ws3.column_dimensions[get_column_letter(COL_DAYOFF)].hidden = True
    ws3.column_dimensions[get_column_letter(COL_SHIFTCODE)].hidden = True
    ws3.freeze_panes = get_column_letter(DAY_COL_START) + str(FIRST_STAFF_ROW)

    # Conditional formatting: holiday columns tinted, "O" cells greyed, working cells blue
    full_range = f'{get_column_letter(DAY_COL_START)}{FIRST_STAFF_ROW}:{get_column_letter(DAY_COL_END)}{r - 1}'
    ws3.conditional_formatting.add(
        full_range,
        FormulaRule(formula=[f'AND({get_column_letter(DAY_COL_START)}${HOLIDAY_FLAG_ROW}=TRUE,{get_column_letter(DAY_COL_START)}{FIRST_STAFF_ROW}<>"O",{get_column_letter(DAY_COL_START)}{FIRST_STAFF_ROW}<>"")'],
        fill=HOLIDAY_FILL))
    ws3.conditional_formatting.add(full_range, FormulaRule(formula=[f'{get_column_letter(DAY_COL_START)}{FIRST_STAFF_ROW}="O"'], fill=OFF_FILL))
    ws3.conditional_formatting.add(full_range, FormulaRule(
        formula=[f'AND({get_column_letter(DAY_COL_START)}{FIRST_STAFF_ROW}<>"O",{get_column_letter(DAY_COL_START)}{FIRST_STAFF_ROW}<>"")'],
        fill=ON_FILL))

    # ---- Sheet: Cost Summary (every column a formula) ----
    ws4 = wb.create_sheet('Cost Summary')
    ws4['A1'] = f'Cost Summary — {project["name"]}, {month_name} {year} — every number below is a formula'
    ws4['A1'].font = TITLE_FONT
    ws4.merge_cells('A1:G1')
    ws4['A2'] = ('Night differential (+30%) on night-eligible shifts, non-holiday. Holiday differential '
                 '(+390% night / +300% day) only on dates entered in Setup!A34:A43 of Roster_Input_Form.xlsx.')
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
        gr = f"'Generated Roster'!"
        rng = f"${get_column_letter(DAY_COL_START)}${p['first_row']}:${get_column_letter(DAY_COL_END)}${p['last_row']}"
        hol_row_rng = f"${get_column_letter(DAY_COL_START)}${HOLIDAY_FLAG_ROW}:${get_column_letter(DAY_COL_END)}${HOLIDAY_FLAG_ROW}"
        sd = f"'Staffing Demand'!"

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
