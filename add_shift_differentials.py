"""
Appends staff shift-differential RULES to the rate card built by build_master_rate_card.py.

Source: staff_cost/2026 Staff Cost Data (Master Data) update.xlsx, sheet "B3.1. Ca dem Le Tet"
(night-shift/holiday allowance detail). The key finding worth preserving: these are flat
legally-mandated surcharge percentages ("Phu cap theo luat" = allowance per law), NOT
per-project numbers -- they apply to ANY position's average daily salary, not just the 4
positions that happened to have real example data filled in.

Run this AFTER build_master_rate_card.py -- it appends to the CSV that script writes and
adds a sheet to the Excel it writes. Idempotent on the Excel (deletes+recreates the sheet
if run twice); NOT idempotent on the CSV (re-running will append duplicate rows -- rebuild
from build_master_rate_card.py first if re-running this).
"""
import os
import csv
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT_DIR = os.path.join(BASE, 'output', 'simple_reports')
DATA_DIR = os.path.join(BASE, 'output', 'copilot_studio_package', 'data')
XLSX_PATH = os.path.join(OUT_DIR, 'Master_Rate_Card.xlsx')
CSV_PATH = os.path.join(DATA_DIR, 'Fact_MasterRateCard.csv')

SHIFT_RULE_ROWS = [
    dict(Domain='Staff', Category='Shift Differential (rule)', Item='Night shift on normal working day',
         Unit='% surcharge on avg daily salary', UnitPrice=30, AdminFeePerStaff=None, TotalPerStaff=None,
         SampleSize=None, Source='Vietnamese labor law, as coded in staff-cost master file ("Phu cap theo luat")',
         Notes='Applies to ANY position — multiply their avg daily salary by this %, add to base pay for that shift'),
    dict(Domain='Staff', Category='Shift Differential (rule)', Item='Night shift on public holiday/Tet',
         Unit='% surcharge on avg daily salary', UnitPrice=390, AdminFeePerStaff=None, TotalPerStaff=None,
         SampleSize=None, Source='Vietnamese labor law, as coded in staff-cost master file ("Phu cap theo luat")',
         Notes='Combines night-work + holiday-work premiums'),
    dict(Domain='Staff', Category='Shift Differential (rule)', Item='Day shift on public holiday/Tet',
         Unit='% surcharge on avg daily salary', UnitPrice=300, AdminFeePerStaff=None, TotalPerStaff=None,
         SampleSize=None, Source='Vietnamese labor law, as coded in staff-cost master file ("Phu cap theo luat")',
         Notes=''),
]

# Real worked examples from the same source sheet: (position, avg_daily_salary,
# night_normal_shifts_yr, night_holiday_shifts_yr, day_holiday_shifts_yr, total_yearly_cost)
SHIFT_EXAMPLE_ROWS = [
    ('Building Executive / Giám sát chất lượng dịch vụ', 600000, 0, 0, 11, 19800000),
    ('Customer Service / Chăm sóc khách hàng', 340000, 0, 0, 44, 44880000),
    ('Technical Duty Shift / Trưởng ca kỹ thuật', 480000, 354, 11, 11, 87408000),
    ('Technician / Nhân viên kỹ thuật', 340000, 354, 11, 22, 73134000),
]


def append_to_csv():
    cols = ['Domain', 'Category', 'Item', 'Unit', 'UnitPrice', 'AdminFeePerStaff', 'TotalPerStaff', 'SampleSize', 'Source', 'Notes']
    with open(CSV_PATH, 'a', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writerows(SHIFT_RULE_ROWS)
    print('Appended', len(SHIFT_RULE_ROWS), 'shift-differential rule rows to', CSV_PATH)


def add_excel_sheet():
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    title_font = Font(bold=True, size=14)
    subtitle_font = Font(italic=True, color="595959")
    section_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    section_font = Font(bold=True)
    thin = Side(style='thin', color='BFBFBF')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    center = Alignment(horizontal='center', vertical='center')
    left = Alignment(horizontal='left', vertical='center', wrap_text=True)
    money_fmt = '#,##0'

    wb = openpyxl.load_workbook(XLSX_PATH)
    if 'Staff - Shift Rules' in wb.sheetnames:
        del wb['Staff - Shift Rules']
    ws = wb.create_sheet('Staff - Shift Rules', index=1)

    ws['A1'] = 'Staff Shift Differentials'
    ws['A1'].font = title_font
    ws.merge_cells('A1:E1')
    ws['A2'] = ('Flat legally-mandated surcharge percentages, NOT per-project numbers — apply to ANY '
                'position\'s average daily salary. Source: staff_cost/2026 Staff Cost Data (Master Data) '
                'update.xlsx, sheet "B3.1. Ca dem Le Tet".')
    ws['A2'].font = subtitle_font
    ws.merge_cells('A2:E2')
    ws.row_dimensions[2].height = 30

    r = 4
    ws.cell(row=r, column=1, value='RULES (apply to any position)').font = section_font
    for c in range(1, 6):
        ws.cell(row=r, column=c).fill = section_fill
        ws.cell(row=r, column=c).border = border
    r += 1
    for c, h in enumerate(['Shift Type', 'Surcharge %', 'Formula', 'Source'], start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center
        cell.border = border
    r += 1
    for item in SHIFT_RULE_ROWS:
        ws.cell(row=r, column=1, value=item['Item']).border = border
        ws.cell(row=r, column=1).alignment = left
        c2 = ws.cell(row=r, column=2, value=item['UnitPrice'] / 100)
        c2.number_format = '0%'
        c2.border = border
        c2.alignment = center
        ws.cell(row=r, column=3, value='Avg daily salary × (1 + surcharge %)').border = border
        ws.cell(row=r, column=4, value=item['Source']).border = border
        ws.cell(row=r, column=4).alignment = left
        r += 1

    r += 1
    ws.cell(row=r, column=1, value='WORKED EXAMPLES (4 real positions, from the same source sheet)').font = section_font
    for c in range(1, 7):
        ws.cell(row=r, column=c).fill = section_fill
        ws.cell(row=r, column=c).border = border
    r += 1
    for c, h in enumerate(['Position', 'Avg Daily Salary', 'Night Shifts/yr (normal)', 'Night Shifts/yr (holiday)', 'Day Shifts/yr (holiday)', 'Total Yearly Shift Cost'], start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center
        cell.border = border
    r += 1
    for pos, daily, nn, nh, dh, total in SHIFT_EXAMPLE_ROWS:
        ws.cell(row=r, column=1, value=pos).border = border
        ws.cell(row=r, column=1).alignment = left
        c2 = ws.cell(row=r, column=2, value=daily); c2.number_format = money_fmt; c2.border = border
        for col, val in ((3, nn), (4, nh), (5, dh)):
            cell = ws.cell(row=r, column=col, value=val)
            cell.border = border
            cell.alignment = center
        c6 = ws.cell(row=r, column=6, value=total); c6.number_format = money_fmt; c6.border = border
        r += 1

    for col, w in {'A': 42, 'B': 24, 'C': 24, 'D': 24, 'E': 24, 'F': 22}.items():
        ws.column_dimensions[col].width = w
    ws.freeze_panes = 'A6'

    wb.save(XLSX_PATH)
    print('Added "Staff - Shift Rules" sheet to', XLSX_PATH)


if __name__ == '__main__':
    append_to_csv()
    add_excel_sheet()
