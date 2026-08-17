"""
Builds docs/PROJECT_PLAN_v2.xlsx — the operational plan for the pipeline as it actually exists
today, replacing the earlier docs/PROJECT_PLAN.xlsx (built when the design still depended on the
19-sheet template + a Fabric/Copilot Studio deployment). That plan is now stale: the live pipeline
is three plain Python scripts and two Excel files, no template fill, no Fabric/Copilot dependency.

Three phases, matching the pipeline exactly:
  1. Process Master Data      transform_master_list.py + derive_staffing_benchmarks.py — turns
                               input/project/2026_Master List.xlsx into the CSV/Excel reference
                               data. Mostly one-time/periodic (re-run when the source file updates).
  2. Input Template            build_project_input_form.py — the PM/BD fills in Project_Budget_
                               Input.xlsx once per new prospect.
  3. Generate Budget Plan       generate_project_output.py — produces Project_Budget_Output.xlsx
                               (Summary, Management Fee, Comparison, Staff, Service, Capex) once
                               per new prospect.

Each task is tagged Frequency = 'One-time (build)' or 'Per New Project', because the two are not
comparable and summing them together would misrepresent the actual per-project cost — Phase_Rollup
breaks the man-day total out by both Phase and Frequency for that reason.
"""
import os
import shutil
import tempfile

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

BUDGET_AGENT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT_DIR = os.path.join(BUDGET_AGENT, 'docs')
FINAL_OUT = os.path.join(OUT_DIR, 'PROJECT_PLAN_v2.xlsx')
OUT = os.path.join(tempfile.gettempdir(), 'PROJECT_PLAN_v2.xlsx')

HEADER_FILL = PatternFill('solid', fgColor='1F4E78')
HEADER_FONT = Font(color='FFFFFF', bold=True)
PHASE_FILLS = {1: PatternFill('solid', fgColor='D9E9E3'), 2: PatternFill('solid', fgColor='F0E4D7'),
               3: PatternFill('solid', fgColor='E5E0EE')}
TITLE_FONT = Font(bold=True, size=14)
SUB_FONT = Font(italic=True, color='595959')
THIN = Side(style='thin', color='BFBFBF')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal='center', vertical='center')
LEFT = Alignment(horizontal='left', vertical='center', wrap_text=True)

DONE = 'Done'
RECURRING = 'Recurring (per project)'
NOT_STARTED = 'Not started'
ONE_TIME = 'One-time (build)'
PER_PROJECT = 'Per New Project'

# Phase, Stage, Task, Description, Owner Role, Frequency, Man-Days, Depends On, Software/License, Status
TASKS = [
    (1, '1. Process Master Data', 'Receive / validate source file', 'Confirm input/project/2026_Master List.xlsx is current (Residential + Commercial sheets)', 'Data Analyst', ONE_TIME, 0.25, '—', 'Excel', DONE),
    (1, '1. Process Master Data', 'Run transform_master_list.py', 'Parses both sheets into Dim_Property_Residential.csv / Dim_Property_Commercial.csv — number-locale parsing, multi-rate fee split, address split, district standardization', 'Data Engineer', ONE_TIME, 0.5, 'Source file validated', 'Python 3.x, openpyxl', DONE),
    (1, '1. Process Master Data', 'Review Data Quality sheet', 'Check Master_List_Review.xlsx: parse coverage (63/105 residential rows have GFA+Fee+Staff+Headcount), flagged fee/address rows', 'Data Engineer', ONE_TIME, 0.25, 'Transform run', 'Excel', DONE),
    (1, '1. Process Master Data', 'Resolve flagged rows', 'Manually check implausible values the transform could not resolve on its own (e.g. Thiso Mall fee outlier) and unparsed fee/address text', 'PM / Data Analyst', ONE_TIME, 0.5, 'Data Quality reviewed', 'Excel', NOT_STARTED),
    (1, '1. Process Master Data', 'Run derive_staffing_benchmarks.py', 'Computes real headcount-per-1000m² by size bucket and correlation with Headcount for GFA/Tower/Gate/Elevator/Units/Parking', 'Data Engineer', ONE_TIME, 0.25, 'CSVs published', 'Python, pandas, numpy', DONE),
    (1, '1. Process Master Data', 'Publish to Power BI', 'Load Dim_Property_Residential.csv / Commercial.csv / Fact_StaffingBenchmark_Derived.csv as a Power BI dataset', 'Data Engineer', ONE_TIME, 0.5, 'Benchmarks derived', 'Power BI Desktop + Service (Pro license for sharing)', NOT_STARTED),
    (1, '1. Process Master Data', 'Wire master_comparables.py to new data', 'Replace the old 8-project hardcoded comparable list with a live lookup against the new ~60-property dataset — bigger N, real per-size-bucket staffing ratios instead of the "editable assumption" disclaimer', 'Data Engineer', ONE_TIME, 1.0, 'CSVs published', 'Python', NOT_STARTED),

    (2, '2. Input Template', 'Build / maintain input template', 'build_project_input_form.py — Project Info, Roster Setup, Shift Types, Staffing Demand in one file', 'Data Engineer', ONE_TIME, 0.5, '—', 'Python, openpyxl', DONE),
    (2, '2. Input Template', 'Fill Project Info', 'Property scale, product mix, parking, pool/garden, gate count — the fields a real new prospect can supply up front', 'PM / BD', PER_PROJECT, 0.25, 'Template built', 'Excel', RECURRING),
    (2, '2. Input Template', 'Fill Roster Setup + Staffing Demand', 'Staffing ratios (editable PM assumption), month/year, public holidays, position list', 'PM / BD', PER_PROJECT, 0.25, 'Project Info filled', 'Excel', RECURRING),
    (2, '2. Input Template', 'Open + save once in Excel', 'Materializes the ratio-driven formula cache so the generator script can read Staff On Duty / Day values', 'PM / BD', PER_PROJECT, 0.05, 'Roster Setup filled', 'Excel (desktop, not web)', RECURRING),

    (3, '3. Generate Budget Plan', 'Run generate_project_output.py', 'Matches 2 nearest real comparables, derives management-fee rate, builds Summary / Management Fee / Comparison / Staff (Roster) / Service / Capex sheets', 'Data Engineer / PM', PER_PROJECT, 0.1, 'Input template complete', 'Python, openpyxl', RECURRING),
    (3, '3. Generate Budget Plan', 'Verify zero formula errors', 'Excel COM full recalculation + scan for #REF!/#VALUE!/#NAME?/#DIV/0!/etc. across every sheet', 'Data Engineer', PER_PROJECT, 0.15, 'Output generated', 'Excel, PowerShell', RECURRING),
    (3, '3. Generate Budget Plan', 'Review Summary + Management Fee + Comparison', 'Check Total Project Value math, the 2 matched comparables, and the reality-check gap when this project\'s own real rate is known', 'PM', PER_PROJECT, 0.25, 'Errors verified', 'Excel', RECURRING),
    (3, '3. Generate Budget Plan', 'Review Staff (Roster) + Service', 'Sanity-check the 12-month staffing cost and the citywide service reference rates', 'PM', PER_PROJECT, 0.25, 'Summary reviewed', 'Excel', RECURRING),
    (3, '3. Generate Budget Plan', 'Fill Capex quantities', 'PM enters real quantities against the equipment price list — nothing pre-guessed', 'PM', PER_PROJECT, 0.25, 'Staff/Service reviewed', 'Excel', RECURRING),
    (3, '3. Generate Budget Plan', 'Deliver to stakeholder', 'Final read-through, send Project_Budget_Output.xlsx', 'PM', PER_PROJECT, 0.15, 'Capex filled', '—', RECURRING),
]


def section(ws, row, text, span='A:J'):
    ws.cell(row=row, column=1, value=text).font = Font(bold=True, size=11)
    c0, c1 = span.split(':')
    ws.merge_cells(f'{c0}{row}:{c1}{row}')


def build_readme(wb):
    ws = wb.create_sheet('README')
    ws['A1'] = 'PROJECT_PLAN_v2 — the pipeline as it actually exists today'
    ws['A1'].font = TITLE_FONT
    ws.merge_cells('A1:F1')
    lines = [
        '',
        'Replaces docs/PROJECT_PLAN.xlsx, which planned around the 19-sheet template 2026.xlsx fill '
        'and a Fabric/Copilot Studio deployment. That is no longer the live path — Phase 1 now runs as '
        'three plain Python scripts producing five short Excel sheets, no Fabric or Copilot dependency.',
        '',
        'Three phases, matching source_code/ exactly:',
        '  1. Process Master Data  — transform_master_list.py, derive_staffing_benchmarks.py',
        '  2. Input Template        — build_project_input_form.py (Project_Budget_Input.xlsx)',
        '  3. Generate Budget Plan  — generate_project_output.py (Project_Budget_Output.xlsx: '
        'Summary, Management Fee, Comparison, Staff, Service, Capex)',
        '',
        'Frequency column matters: "One-time (build)" tasks are already done and will not recur unless '
        'the source Master List changes shape. "Per New Project" tasks repeat every time a PM runs this '
        'for a new prospect — that recurring cost is what Phase_Rollup reports separately from the '
        'one-time build cost, since summing the two together would misstate the real per-project cost.',
        '',
        'Two tasks are flagged Not started, both in Phase 1: resolving a few flagged rows (fee/address '
        'text the parser could not confidently read), publishing the data to Power BI, and — the one '
        'that matters most — wiring master_comparables.py to this new ~60-property dataset instead of '
        'the old hardcoded 8-project list it still uses today.',
    ]
    for i, line in enumerate(lines, start=2):
        ws.cell(row=i, column=1, value=line).alignment = LEFT
        ws.merge_cells(f'A{i}:F{i}')
        ws.row_dimensions[i].height = 16 if line else 6
    ws.column_dimensions['A'].width = 130


def build_full_plan(wb):
    ws = wb.create_sheet('Full_Plan')
    headers = ['Phase', 'Stage', 'Task', 'Description', 'Owner Role', 'Frequency', 'Man-Days', 'Depends On', 'Software / License Needed', 'Status']
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    for r, task in enumerate(TASKS, start=2):
        fill = PHASE_FILLS.get(task[0])
        for c, val in enumerate(task, start=1):
            cell = ws.cell(row=r, column=c, value=val)
            cell.border = BORDER
            cell.alignment = LEFT if c in (3, 4, 9) else CENTER
            if fill:
                cell.fill = fill
            if c == 7:
                cell.number_format = '0.00'
    widths = {'A': 8, 'B': 22, 'C': 30, 'D': 60, 'E': 18, 'F': 18, 'G': 10, 'H': 26, 'I': 34, 'J': 16}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w
    ws.freeze_panes = 'A2'
    return len(TASKS)


def build_phase_rollup(wb, n_tasks):
    ws = wb.create_sheet('Phase_Rollup')
    ws['A1'] = 'Man-days by Phase and Frequency (formula-driven — edit Full_Plan, this recalculates)'
    ws['A1'].font = TITLE_FONT
    ws.merge_cells('A1:D1')

    headers = ['Phase', 'One-time (build) man-days', 'Per New Project man-days (one run)', 'Total man-days']
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=3, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER

    phases = [(1, '1. Process Master Data'), (2, '2. Input Template'), (3, '3. Generate Budget Plan')]
    last_row = n_tasks + 1
    r = 4
    for phase_num, phase_label in phases:
        ws.cell(row=r, column=1, value=phase_label).border = BORDER
        c2 = ws.cell(row=r, column=2, value=f'=SUMIFS(Full_Plan!$G$2:$G${last_row},Full_Plan!$A$2:$A${last_row},{phase_num},Full_Plan!$F$2:$F${last_row},"{ONE_TIME}")')
        c2.border = BORDER
        c2.number_format = '0.00'
        c3 = ws.cell(row=r, column=3, value=f'=SUMIFS(Full_Plan!$G$2:$G${last_row},Full_Plan!$A$2:$A${last_row},{phase_num},Full_Plan!$F$2:$F${last_row},"{PER_PROJECT}")')
        c3.border = BORDER
        c3.number_format = '0.00'
        c4 = ws.cell(row=r, column=4, value=f'=B{r}+C{r}')
        c4.border = BORDER
        c4.number_format = '0.00'
        r += 1
    ws.cell(row=r, column=1, value='TOTAL').font = Font(bold=True)
    for col in ('B', 'C', 'D'):
        cell = ws.cell(row=r, column=ord(col) - 64, value=f'=SUM({col}4:{col}{r - 1})')
        cell.font = Font(bold=True)
        cell.number_format = '0.00'
        cell.border = BORDER
    ws.cell(row=r, column=1).border = BORDER

    ws['A10'] = 'Read as: one-time build cost is a sunk cost already spent this session. Per-project cost is what it takes a PM to run this for the NEXT new prospect.'
    ws['A10'].font = SUB_FONT
    ws['A10'].alignment = LEFT
    ws.merge_cells('A10:D10')
    ws.row_dimensions[10].height = 28

    widths = {'A': 26, 'B': 26, 'C': 32, 'D': 16}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w


def build_resource_summary(wb):
    ws = wb.create_sheet('Resource_Summary')
    ws['A1'] = 'Resources needed'
    ws['A1'].font = TITLE_FONT
    ws.merge_cells('A1:C1')

    headers = ['Role', 'Software / License', 'Notes']
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=3, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER

    rows = [
        ('Data Engineer', 'Python 3.x, openpyxl, pandas, numpy', 'Runs transform_master_list.py, derive_staffing_benchmarks.py, generate_project_output.py; maintains master_comparables.py'),
        ('Data Engineer', 'Excel (desktop) + PowerShell', 'Excel COM automation for formula recalculation and error-scanning — the Windows-native replacement for the xlsx skill\'s recalc.py, which fails on this environment'),
        ('Data Engineer', 'Power BI Desktop + Service (Pro license)', 'Publishing the Dim_Property CSVs and staffing benchmarks — not yet done'),
        ('PM / BD', 'Excel (desktop, not web)', 'Fills Project_Budget_Input.xlsx; ratio-driven formula cells need a real Excel save, not the web app, to cache their values'),
        ('PM', 'Excel (desktop)', 'Reviews Project_Budget_Output.xlsx, fills Capex quantities, delivers to stakeholder'),
        ('Data Analyst', 'Excel', 'Validates the source Master List file arrives correctly shaped; resolves flagged/ambiguous rows'),
    ]
    r = 4
    for role, sw, notes in rows:
        ws.cell(row=r, column=1, value=role).border = BORDER
        c2 = ws.cell(row=r, column=2, value=sw)
        c2.border = BORDER
        c2.alignment = LEFT
        c3 = ws.cell(row=r, column=3, value=notes)
        c3.border = BORDER
        c3.alignment = LEFT
        r += 1

    widths = {'A': 18, 'B': 34, 'C': 70}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w


def main():
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    build_readme(wb)
    n_tasks = build_full_plan(wb)
    build_resource_summary(wb)
    build_phase_rollup(wb, n_tasks)

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
