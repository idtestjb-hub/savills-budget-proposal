"""
Builds the "just make it work with present data, simple and readable" summary reports --
totals and indexes, no formulas, no deep drill-down. These were the first checkpoint before
build_master_rate_card.py's more precise per-unit rate cards.

Outputs (all in output/simple_reports/):
  - Staff_Cost_Summary.xlsx    Overview / By Position (totals) / Index by Project
  - Capex_Summary.xlsx         By Category / Top Items
  - Service_Cost_Structure.xlsx  position/item roster per category (master file ships no price)

Superseded for AGENT/FABRIC use by build_master_rate_card.py (which reframes these same
sources around price-for-1-unit instead of portfolio totals) -- keep this module around for
quick human sanity-checks and portfolio-scale totals, not for feeding the reasoning layer.
"""
import os
import re
import glob
from collections import defaultdict

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from common_utils_v2 import repair_workbook

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT_DIR = os.path.join(BASE, 'output', 'simple_reports')

HEADER_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)
TITLE_FONT = Font(bold=True, size=14)
SUBTITLE_FONT = Font(italic=True, color="595959")
TOTAL_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
TOTAL_FONT = Font(bold=True)
THIN = Side(style='thin', color='BFBFBF')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal='center', vertical='center')
LEFT = Alignment(horizontal='left', vertical='center', wrap_text=True)
MONEY_FMT = '#,##0'


def style_header_row(ws, row, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        if cell.value is not None:
            cell.fill = HEADER_FILL
            cell.font = HEADER_FONT
            cell.alignment = CENTER
            cell.border = BORDER


def build_staff_cost_summary():
    src = os.path.join(BASE, 'input', 'staff_cost', '2026 Staff Cost Data (Master Data) update.xlsx')
    wb_src = openpyxl.load_workbook(src, data_only=True)
    ws_src = wb_src['DS Staff cost (KT - 2025)']
    rows = list(ws_src.iter_rows(min_row=11, max_row=ws_src.max_row, values_only=True))
    data = [r for r in rows if r[2] is not None and r[3] is not None and isinstance(r[4], (int, float))]

    by_position = defaultdict(lambda: {'count': 0, 'gross_total': 0.0, 'admin_total': 0.0})
    for r in data:
        d = by_position[r[3]]
        d['count'] += 1
        d['gross_total'] += r[4] or 0
        d['admin_total'] += r[6] or 0

    by_project = defaultdict(lambda: {'code': None, 'count': 0, 'gross_total': 0.0, 'admin_total': 0.0})
    for r in data:
        d = by_project[r[2]]
        d['code'] = r[0]
        d['count'] += 1
        d['gross_total'] += r[4] or 0
        d['admin_total'] += r[6] or 0

    total_headcount = len(data)
    total_gross = sum(r[4] or 0 for r in data)
    total_admin = sum(r[6] or 0 for r in data)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Overview'
    ws['A1'] = 'Staff Cost Summary — Savills Master Staff Data'
    ws['A1'].font = TITLE_FONT
    ws.merge_cells('A1:C1')
    overview_rows = [
        ('Total staff records', total_headcount),
        ('Distinct projects covered', len(by_project)),
        ('Distinct position titles', len(by_position)),
        ('Total Gross Salary (VND/month, all projects)', total_gross),
        ('Total Admin Fee (VND/month, all projects)', total_admin),
        ('Total Gross + Admin (VND/month, all projects)', total_gross + total_admin),
    ]
    r = 5
    ws.cell(row=r, column=1, value='Metric').font = HEADER_FONT
    ws.cell(row=r, column=1).fill = HEADER_FILL
    ws.cell(row=r, column=2, value='Value').font = HEADER_FONT
    ws.cell(row=r, column=2).fill = HEADER_FILL
    r += 1
    for label, val in overview_rows:
        ws.cell(row=r, column=1, value=label).border = BORDER
        c = ws.cell(row=r, column=2, value=val)
        c.border = BORDER
        if isinstance(val, (int, float)) and val > 10000:
            c.number_format = MONEY_FMT
        r += 1
    ws.column_dimensions['A'].width = 42
    ws.column_dimensions['B'].width = 20

    ws2 = wb.create_sheet('By Position')
    ws2['A1'] = 'Staff Cost by Position — aggregated across all projects'
    ws2['A1'].font = TITLE_FONT
    ws2.merge_cells('A1:F1')
    headers = ['Position', 'Headcount', 'Total Gross Salary', 'Avg Gross Salary', 'Total Admin Fee', 'Total (Gross+Admin)']
    r = 4
    for c, h in enumerate(headers, start=1):
        ws2.cell(row=r, column=c, value=h)
    style_header_row(ws2, r, len(headers))
    r += 1
    position_rows = []
    for pos, d in by_position.items():
        total = d['gross_total'] + d['admin_total']
        avg = d['gross_total'] / d['count'] if d['count'] else 0
        position_rows.append((pos, d['count'], d['gross_total'], avg, d['admin_total'], total))
    position_rows.sort(key=lambda x: x[5], reverse=True)
    for pos, cnt, gross, avg, admin, total in position_rows:
        ws2.cell(row=r, column=1, value=pos).border = BORDER
        ws2.cell(row=r, column=1).alignment = LEFT
        ws2.cell(row=r, column=2, value=cnt).border = BORDER
        for col, val in ((3, gross), (4, avg), (5, admin), (6, total)):
            cell = ws2.cell(row=r, column=col, value=val)
            cell.number_format = MONEY_FMT
            cell.border = BORDER
        r += 1
    ws2.cell(row=r, column=1, value='GRAND TOTAL').font = TOTAL_FONT
    ws2.cell(row=r, column=2, value=total_headcount).font = TOTAL_FONT
    for col, val in ((3, total_gross), (5, total_admin), (6, total_gross + total_admin)):
        cell = ws2.cell(row=r, column=col, value=val)
        cell.number_format = MONEY_FMT
        cell.font = TOTAL_FONT
    for c in range(1, 7):
        ws2.cell(row=r, column=c).fill = TOTAL_FILL
    for col, w in {'A': 45, 'B': 12, 'C': 20, 'D': 18, 'E': 18, 'F': 20}.items():
        ws2.column_dimensions[col].width = w
    ws2.freeze_panes = 'A5'

    ws3 = wb.create_sheet('Index by Project')
    ws3['A1'] = 'Project Index'
    ws3['A1'].font = TITLE_FONT
    ws3.merge_cells('A1:E1')
    headers3 = ['Project Code', 'Project Name', 'Headcount', 'Total Gross Salary', 'Total (Gross+Admin)']
    r = 4
    for c, h in enumerate(headers3, start=1):
        ws3.cell(row=r, column=c, value=h)
    style_header_row(ws3, r, len(headers3))
    r += 1
    project_rows = sorted(
        [(d['code'], name, d['count'], d['gross_total'], d['gross_total'] + d['admin_total'])
         for name, d in by_project.items()],
        key=lambda x: x[4], reverse=True)
    for code, name, cnt, gross, total in project_rows:
        ws3.cell(row=r, column=1, value=code).border = BORDER
        ws3.cell(row=r, column=2, value=name).border = BORDER
        ws3.cell(row=r, column=2).alignment = LEFT
        ws3.cell(row=r, column=3, value=cnt).border = BORDER
        for col, val in ((4, gross), (5, total)):
            cell = ws3.cell(row=r, column=col, value=val)
            cell.number_format = MONEY_FMT
            cell.border = BORDER
        r += 1
    for col, w in {'A': 16, 'B': 32, 'C': 12, 'D': 20, 'E': 20}.items():
        ws3.column_dimensions[col].width = w
    ws3.freeze_panes = 'A5'

    out = os.path.join(OUT_DIR, 'Staff_Cost_Summary.xlsx')
    wb.save(out)
    print('Saved:', out)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    build_staff_cost_summary()
    # Capex_Summary.xlsx / Service_Cost_Structure.xlsx: see build_master_rate_card.py for the
    # up-to-date, per-unit-price version of this same data -- not duplicated here.


if __name__ == '__main__':
    main()
