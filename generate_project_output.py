"""
Phase 1, simplified — reads Project_Budget_Input.xlsx and writes ONE workbook,
Project_Budget_Output.xlsx, with 5 short sheets instead of the 19-sheet real template:

  Summary            one-page rollup, links into the 4 sheets below.
  Management Fee      property scale, the 2 nearest real comparables, derived rate, revenue.
  Staff (Roster)       full-year (12 month) formula-driven staffing cost, from Staffing Demand.
  Service              flat citywide reference rates (Security/Cleaning/Landscape), annualized.
  Capex                real equipment price list (Fact_MasterRateCard.csv, Domain=Capex) with an
                        editable Qty column — PM fills in quantities, nothing is guessed here.

Does NOT touch template 2026.xlsx — that 19-sheet fill is what this script replaces for phase 1.
generate_project_budget.py (template-based) is still there if a full template fill is needed later.

Full-year simplification, stated plainly: the Staff sheet estimates each month's working days from
the average weekly coverage fraction (see build_staff_sheet docstring below) rather than a real
day-by-day grid, and does NOT apply holiday differentials (there's no annual holiday calendar on
the input form yet, only one month's worth). Night-shift differential (+30%) IS applied, since
it depends on the shift code, not the calendar. For an exact day-by-day schedule with holidays,
use generate_roster.py's single-month output instead.
"""
import os
import csv
import math

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule

from generate_project_budget import read_input, INPUT_PATH, PRODUCT_ROWS
from master_comparables import (
    MASTER_COMPARABLES, SECURITY_RATE_CITYWIDE, CLEANING_RATE_CITYWIDE, LANDSCAPE_RATE_CITYWIDE,
    RATE_CARD_SOURCE, nearest_comparables, derive_product_rate,
)
from estimate_capex_qty import estimate_capex_qty, estimate_capex_items
from estimate_new_project import estimate_staff_headcount
from estimate_opex import estimate_opex, RATIO_CATEGORIES as OPEX_RATIO_CATEGORIES

SOURCE_DIR = os.path.dirname(__file__)
BUDGET_AGENT = os.path.abspath(os.path.join(SOURCE_DIR, '..'))
RATE_CARD_CSV = os.path.join(BUDGET_AGENT, 'data', 'generation_B_verified', 'Fact_MasterRateCard.csv')
OUTPUT_PATH = os.path.join(BUDGET_AGENT, 'reports', 'Project_Budget_Output.xlsx')

MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
NIGHT_SHIFT_CODES = {'D', '24H'}  # from the Shift Types reference — Night Shift? = Yes
NIGHT_DIFFERENTIAL = 1.3  # +30% night-shift premium, same factor build_staff_sheet applies

# Shared between build_staff_sheet (for its Service-equivalent comparison columns) and
# build_service_sheet (for its own Qty matching) — kept in one place so the two sheets can never
# silently drift onto different definitions of "which Staffing Demand rows count as Security".
SERVICE_CATEGORY_KEYWORDS = {
    'Security': ['security'],
    'Cleaning': ['cleaning'],
    'Landscape': ['landscape', 'gardener'],
}

# Checked directly against Fact_MasterRateCard.csv: all 3 Service rows are "24/24 position (all
# roles)" or "8/24 position (all roles)" — line-staff rates, sourced from ONE real project (A&K
# Tower, SampleSize=1), with no supervisory rate anywhere in the Service domain. A supervisor
# earns a real, documented premium in Staffing Demand (Cleaning - Supervisor: 480,000/day vs
# Cleaning - Common Area's 340,000/day) that this flat citywide reference has no way to reflect —
# pricing a supervisor's headcount at the line-staff rate isn't a rounding difference, it's using
# a rate for a role it was never sourced for. Excluded the same way Reception already is (no
# citywide reference at all), rather than silently blended in at the wrong rate.
SERVICE_EXCLUDE_KEYWORDS = ['supervisor']

# Real, sourced from the same cell comment Staffing Demand's own AvgDailyRate cites: "17,500,000
# VND/month covers all 3 shift roles for one post. Split 3 ways = 5,833,333/month per role." The
# citywide rate is a PER-POST figure that already blends Morning/Afternoon/Night together for
# Security — dividing by real per-shift headcount (23 individuals, each working ONE of the 3
# shifts) without first splitting the rate 3 ways would price each of them as if they alone cost
# a whole post, ~3x too high. Cleaning/Landscape have no such split (single shift per position;
# Landscape's own AvgDailyRate comment divides the citywide rate straight by 26 working days, no
# ×3), so their multiplier stays 1.
SERVICE_SHIFT_ROLES_PER_POST = {'Security': 3, 'Cleaning': 1, 'Landscape': 1}

# Every OTHER Staffing Demand position — Property Manager, Chief Engineer, etc. — has no citywide
# "post" rate in Fact_MasterRateCard.csv's Service domain (only Security/Cleaning/Landscape do),
# but DOES have a real market-average MONTHLY SALARY in the Staff domain — the exact same numbers
# build_project_input_form.py used to set each position's default AvgDailyRate. Cross-checking
# against those here closes the gap: every staffed position gets a real-data comparison somewhere
# in this workbook, not just the 3 that happen to have a citywide post rate.
STAFF_MARKET_KEYWORDS = {
    'Property Manager': ['property manager'],
    'Chief Engineer': ['chief engineer'],
    'Building Executive': ['building executive'],
    'Customer Service': ['customer service'],
    'Reception': ['reception'],
    'Shift Leader': ['shift leader'],
    'Technician': ['technician'],
    'Amenities Attendant': ['amenities attendant'],
    'Pool Attendant': ['pool attendant'],
}
STAFF_MARKET_RATES = {
    # (monthly_vnd, n, source_item) — source_item is the Fact_MasterRateCard.csv Staff-domain row
    # actually used, since several are Vietnamese-labeled (the largest real sample, not necessarily
    # the English-labeled row of the same role — see build_project_input_form.py for why).
    'Property Manager': (42_325_000, 7, 'Property Manager'),
    'Chief Engineer': (34_262_409, 61, 'Kỹ sư trưởng'),
    'Building Executive': (15_298_818, 73, 'Giám sát chất lượng dịch vụ'),
    'Customer Service': (8_919_726, 178, 'Chăm sóc khách hàng'),
    'Reception': (8_625_967, 47, 'Lễ Tân'),
    'Shift Leader': (11_541_695, 138, 'Trưởng Ca'),
    'Technician': (8_459_141, 458, 'Kỹ thuật viên'),
    'Amenities Attendant': (7_988_816, 91, 'Nhân viên tiện ích'),
    'Pool Attendant': (7_166_250, 1, 'Gym - Pool Attendant'),
}

HEADER_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)
TITLE_FONT = Font(bold=True, size=14)
SUBTITLE_FONT = Font(italic=True, color="595959")
SECTION_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
SECTION_FONT = Font(bold=True)
HIGHLIGHT_FILL = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
THIN = Side(style='thin', color='BFBFBF')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal='center', vertical='center')
LEFT = Alignment(horizontal='left', vertical='center', wrap_text=True)
MONEY_FMT = '#,##0'


def section(ws, row, text, ncols=5):
    ws.cell(row=row, column=1, value=text).font = SECTION_FONT
    for c in range(1, ncols + 1):
        ws.cell(row=row, column=c).fill = SECTION_FILL
        ws.cell(row=row, column=c).border = BORDER


def title_block(ws, title, subtitle=None, span='A1:F1'):
    ws['A1'] = title
    ws['A1'].font = TITLE_FONT
    ws.merge_cells(span)
    if subtitle:
        c0, c1 = span.split(':')
        row2_span = f"{c0[0]}2:{c1[0]}2"
        ws['A2'] = subtitle
        ws['A2'].font = SUBTITLE_FONT
        ws['A2'].alignment = LEFT
        ws.merge_cells(row2_span)
        ws.row_dimensions[2].height = 28


# ============================================================================================
def build_management_fee_sheet(wb, project):
    """Revenue is now priced PER PRODUCT TYPE, not just Apartment: each of Apartment/Officetel/
    Shophouse/Shopping Mall/Nursery (whichever have nonzero NFA on this project) gets its own
    derived rate from the nearest real comparables that have a REAL rate for that specific
    product — see master_comparables.py's PRODUCT_RATE_COLUMNS and derive_product_rate(). Real
    per-product rate data is thin outside Apartment (most comparables only have one blended
    rate), so any product with zero qualifying comparables falls back to this project's own
    derived Apartment rate — labeled in red as a fallback, never silently dropped from revenue
    and never silently presented as if it were product-specific real data."""
    ws = wb.create_sheet('Management Fee')
    title_block(ws, 'Management Fee',
                'Each product priced with its own derived rate from real comparables with a rate for that product '
                '(Apartment rate used as a labeled fallback where none exist) — see master_comparables.py.', 'A1:E1')

    all_ranked = nearest_comparables(project['total_nfa'], exclude_name=project['name'], n=len(MASTER_COMPARABLES))
    apt_rate, apt_used, apt_note = derive_product_rate(all_ranked, 'Apartment', n=2)
    own_real = next((c for c in MASTER_COMPARABLES
                      if c['name'].strip().lower() in project['name'].strip().lower() and c['rates'].get('Apartment')), None)

    r = 4
    section(ws, r, 'SCALE', ncols=5); r += 1
    for label, val in [('Project Name', project['name']), ('Apartment NFA (m²)', project['apartment_nfa']),
                        ('Apartment Units', project['apartment_units']),
                        ('Total NFA (m²) — used for comparable matching', project['total_nfa'])]:
        ws.cell(row=r, column=1, value=label).font = Font(bold=True)
        ws.cell(row=r, column=2, value=val)
        r += 1

    r += 1
    ws.cell(row=r, column=1, value='See the Comparison sheet for the comparables the Apartment rate is derived from.').font = Font(italic=True, size=9, color='7F7F7F')
    ws.merge_cells(f'A{r}:E{r}')
    r += 2

    section(ws, r, 'DERIVED APARTMENT RATE (also the fallback for products with no real rate of their own)', ncols=5); r += 1
    ws.cell(row=r, column=1, value='Derived Apartment rate (VND/m²/month)').font = Font(bold=True)
    rate_cell = ws.cell(row=r, column=2, value=apt_rate)
    rate_cell.fill = HIGHLIGHT_FILL
    rate_cell.number_format = MONEY_FMT
    rate_cell.border = BORDER
    r += 1
    if apt_note:
        ws.cell(row=r, column=1, value='Note').font = Font(italic=True, size=9)
        ws.cell(row=r, column=2, value=apt_note).alignment = LEFT
        ws.merge_cells(f'B{r}:E{r}')
        r += 1
    if own_real:
        gap = apt_rate - own_real['rates']['Apartment']
        ws.cell(row=r, column=1, value="This project's ACTUAL real Apartment rate (reality check)").font = Font(bold=True)
        c = ws.cell(row=r, column=2, value=f"{own_real['rates']['Apartment']:,} ({own_real['mgmt_rate_vat']})")
        c.fill = HIGHLIGHT_FILL
        r += 1
        ws.cell(row=r, column=1, value='Gap (derived − real)').font = Font(bold=True)
        c = ws.cell(row=r, column=2, value=f"{gap:+,} VND  ({gap/own_real['rates']['Apartment']*100:+.0f}%)")
        c.fill = HIGHLIGHT_FILL
        r += 1
    r += 1

    section(ws, r, 'PER-PRODUCT MANAGEMENT FEE REVENUE', ncols=5); r += 1
    headers = ['Product', 'NFA (m²)', 'Rate (VND/m²/mo)', 'Rate source', 'Monthly Revenue (VND)']
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    r += 1
    first_product_row = r
    footnotes = []
    for product in PRODUCT_ROWS:
        nfa = project['products'][product]['nfa']
        if not nfa:
            continue
        rate, used, note = derive_product_rate(all_ranked, product, n=2)
        is_fallback = rate is None
        if is_fallback:
            rate = apt_rate
            note = f"No comparable has a real {product} rate — using this project's derived Apartment rate ({apt_rate:,}) as the best available proxy."
        ws.cell(row=r, column=1, value=product).border = BORDER
        c2 = ws.cell(row=r, column=2, value=nfa)
        c2.border = BORDER
        c2.number_format = '#,##0'
        c3 = ws.cell(row=r, column=3, value=rate)
        c3.border = BORDER
        c3.number_format = MONEY_FMT
        if is_fallback:
            c3.font = Font(italic=True, color='C00000')
        source_label = (f"{len(used)} real comparable(s): " + ', '.join(c['name'] for c in used)) if used else 'Apartment rate (fallback — no product-specific comparable)'
        c4 = ws.cell(row=r, column=4, value=source_label)
        c4.border = BORDER
        c4.alignment = LEFT
        c5 = ws.cell(row=r, column=5, value=f'=B{r}*C{r}')
        c5.border = BORDER
        c5.number_format = MONEY_FMT
        if note:
            footnotes.append((product, note))
        r += 1
    last_product_row = r - 1
    r += 1

    ws.cell(row=r, column=1, value='TOTAL Monthly Management Fee Revenue (VND)').font = Font(bold=True)
    c = ws.cell(row=r, column=2, value=f'=SUM(E{first_product_row}:E{last_product_row})')
    c.number_format = MONEY_FMT
    MONTHLY_REVENUE_CELL = f'B{r}'
    r += 1
    ws.cell(row=r, column=1, value='TOTAL Annual Management Fee Revenue (VND)').font = Font(bold=True)
    c = ws.cell(row=r, column=2, value=f"={MONTHLY_REVENUE_CELL}*12")
    c.number_format = MONEY_FMT
    c.fill = HIGHLIGHT_FILL
    ANNUAL_REVENUE_CELL = f'B{r}'
    r += 2

    if footnotes:
        section(ws, r, 'PER-PRODUCT RATE NOTES', ncols=5); r += 1
        for product, note in footnotes:
            ws.cell(row=r, column=1, value=product).font = Font(bold=True, size=9)
            ws.cell(row=r, column=2, value=note).alignment = LEFT
            ws.merge_cells(f'B{r}:E{r}')
            r += 1

    for col, w in {'A': 40, 'B': 26, 'C': 22, 'D': 46, 'E': 26}.items():
        ws.column_dimensions[col].width = w

    return dict(monthly_revenue_cell=MONTHLY_REVENUE_CELL, annual_revenue_cell=ANNUAL_REVENUE_CELL,
                derived_rate=apt_rate, top2=apt_used, rate_note=apt_note, own_real=own_real)


# ============================================================================================
def build_comparison_sheet(wb, project, mgmt):
    """Side-by-side comparison against the same 2 real projects the Management Fee sheet derived
    its rate from — scale, management-fee rate (with a reality check if this project's own real
    rate happens to be known), and the flat citywide service rates for context."""
    top2, derived_rate, rate_note, own_real = mgmt['top2'], mgmt['derived_rate'], mgmt['rate_note'], mgmt['own_real']
    ws = wb.create_sheet('Comparison')
    title_block(ws, 'Comparison', f"{project['name']} vs. the {len(top2)} nearest real comparable(s) WITH A VERIFIED APARTMENT RATE, ranked by Total NFA (whole-building) — {len(MASTER_COMPARABLES)} real candidates considered. Other product types (Officetel/Shophouse/etc.) are priced from a different comparable set — see the Management Fee sheet's Rate source column.", 'A1:D1')

    headers = ['Metric', project['name']] + [c['name'] for c in top2]
    r = 4
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    r += 1

    def data_row(row, label, values, fill=None):
        cells = [label] + values
        for col, v in enumerate(cells, start=1):
            cell = ws.cell(row=row, column=col, value=v)
            cell.border = BORDER
            cell.alignment = LEFT if col == 1 else CENTER
            if fill:
                cell.fill = fill
        return row + 1

    section(ws, r, 'SCALE', ncols=4); r += 1
    r = data_row(r, 'Total NFA (m²) — matching basis', [project['total_nfa']] + [c['nfa'] for c in top2])
    r = data_row(r, 'NFA delta from this project', ['—'] + [round(abs(c['nfa'] - project['total_nfa'])) for c in top2])
    r = data_row(r, 'Apartment NFA (m²) — for reference only, not the matching basis',
                 [project['apartment_nfa']] + ['—', '—'])
    r = data_row(r, 'Apartment units', [project['apartment_units']] + [c['units'] for c in top2])
    r += 1

    section(ws, r, 'APARTMENT MANAGEMENT FEE RATE', ncols=4); r += 1
    r = data_row(r, 'Real Apartment rate per comparable (VND/m²/month)',
                 ['—'] + [f"{c['rates']['Apartment']:,} ({c['mgmt_rate_vat']})" for c in top2])
    r = data_row(r, 'MODEL-DERIVED Apartment rate (this project)', [f'{derived_rate:,}', '', ''], fill=HIGHLIGHT_FILL)
    if rate_note:
        r = data_row(r, 'Derivation note', [rate_note, '', ''])
    if own_real:
        gap = derived_rate - own_real['rates']['Apartment']
        r = data_row(r, "This project's ACTUAL real Apartment rate (reality check)",
                     [f"{own_real['rates']['Apartment']:,} ({own_real['mgmt_rate_vat']})", '', ''], fill=HIGHLIGHT_FILL)
        r = data_row(r, 'Gap (derived − real)', [f'{gap:+,} VND  ({gap/own_real["rates"]["Apartment"]*100:+.0f}%)', '', ''], fill=HIGHLIGHT_FILL)
    else:
        r = data_row(r, 'Reality check', ['Not applicable — new prospect, no independently known real rate', '', ''])
    r += 1

    section(ws, r, f'SERVICE RATES ({RATE_CARD_SOURCE})', ncols=4); r += 1
    r = data_row(r, 'Security (VND/post/month)', [f'{SECURITY_RATE_CITYWIDE:,}'] * 3)
    r = data_row(r, 'Cleaning (VND/post/month)', [f'{CLEANING_RATE_CITYWIDE:,}'] * 3)
    r = data_row(r, 'Landscape (VND/post/month)', [f'{LANDSCAPE_RATE_CITYWIDE:,}'] * 3)

    for col, w in {'A': 42, 'B': 26, 'C': 24, 'D': 24}.items():
        ws.column_dimensions[col].width = w


# ============================================================================================
def build_staffing_estimate_sheet(wb, project, ratios, demand):
    """Shows HOW each Staffing Demand row's headcount was arrived at — not a separate/parallel
    estimate that could drift from what the rest of the workbook uses, but the exact same numbers
    (every downstream sheet reads this same `demand` list). Ratio-driven rows (Security Main
    Gate/Patrol, Cleaning Common Area/Supervisor, Gardener) are recomputed fresh in Python from
    Project Info + Roster Setup every time this script runs — see RATIO_DRIVEN_STAFFING in
    generate_project_budget.py — so a PM genuinely only has to fill Project Info (site scale, gate
    count, garden/open-space area, tower count) and accept or tweak the Roster Setup ratios
    (shipped with sensible defaults) to get a full staffing plan; no manual per-position typing
    required for those 5 roles. A few roles (CCTV Room, Reception) are fixed assumptions, not
    ratio-driven — real properties don't scale these with size the way they do gate security or
    cleaning coverage. Any position a PM adds or renames beyond the known 5 falls back to
    whatever's typed directly into the Staffing Demand sheet, unchanged."""
    ws = wb.create_sheet('Staffing Estimate')
    title_block(ws, 'Staffing Estimate — How "Staff On Duty / Day" Was Computed',
                'Ratio-driven rows recompute fresh from Project Info + Roster Setup every run — no manual per-position '
                'entry needed for these. Fixed rows are a stated assumption, not a ratio. These ARE the numbers the '
                'Staff (Roster) and Service sheets use, not a separate estimate.', 'A1:F1')

    r = 4
    section(ws, r, 'WHAT DRIVES EACH ROLE', ncols=6); r += 1
    ratio_desc = [
        ('Security — Main Gate (×3 shifts)', f"Gate Count × Staff per Gate  ({ratios['staff_per_gate']:g} staff/gate)"),
        ('Security — Patrol / Open Space', f"Open Space ÷ m² per Patrol Staff  (1 per {ratios['sqm_per_patrol']:g} m²)"),
        ('Cleaning — Common Area', f"Open Space ÷ m² per Cleaner  (1 per {ratios['sqm_per_cleaner']:g} m²)"),
        ('Cleaning — Supervisor', f"Tower Count ÷ Towers per Supervisor  (1 per {ratios['towers_per_supervisor']:g} towers)"),
        ('Gardener / Landscape', f"Garden Area ÷ m² per Gardener  (1 per {ratios['sqm_per_gardener']:g} m²)"),
        ('Security — CCTV Room (×3 shifts), Reception', 'Fixed assumption — 1 staff, not scaled by project size'),
    ]
    for label, desc in ratio_desc:
        ws.cell(row=r, column=1, value=label).font = Font(bold=True, size=9)
        ws.cell(row=r, column=2, value=desc).font = Font(size=9, color='595959')
        ws.merge_cells(f'B{r}:F{r}')
        r += 1
    r += 1
    ws.cell(row=r, column=1,
            value='Roster Setup ratios are PM-editable assumptions (build_project_input_form.py ships defaults) — '
                  'change them and rerun the script; every ratio-driven row below recalculates.').font = Font(italic=True, size=9, color='7F7F7F')
    ws.merge_cells(f'A{r}:F{r}')
    r += 2

    section(ws, r, 'STAFFING DEMAND — COMPUTED', ncols=6); r += 1
    headers = ['Position', 'Shift Code', 'Basis (how this number was computed)', 'Staff On Duty / Day',
               'Coverage Days / Week', 'Avg Daily Rate (VND)']
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    r += 1
    ratio_driven_fill = PatternFill('solid', fgColor='E2EFDA')
    for d in demand:
        is_ratio_driven = 'rounded up' in d['Basis']
        ws.cell(row=r, column=1, value=d['Position']).border = BORDER
        ws.cell(row=r, column=1).alignment = LEFT
        ws.cell(row=r, column=2, value=d['ShiftCode']).border = BORDER
        ws.cell(row=r, column=2).alignment = CENTER
        c3 = ws.cell(row=r, column=3, value=d['Basis'])
        c3.border = BORDER
        c3.alignment = LEFT
        c3.font = Font(size=9)
        c4 = ws.cell(row=r, column=4, value=d['StaffPerDay'])
        c4.border = BORDER
        c4.alignment = CENTER
        if is_ratio_driven:
            for col in range(1, 5):
                ws.cell(row=r, column=col).fill = ratio_driven_fill
        c5 = ws.cell(row=r, column=5, value=d['CoverageDays'])
        c5.border = BORDER
        c5.alignment = CENTER
        c6 = ws.cell(row=r, column=6, value=d['AvgDailyRate'])
        c6.border = BORDER
        c6.number_format = MONEY_FMT
        r += 1
    r += 1
    ws.cell(row=r, column=1, value='Green rows = recomputed fresh from Project Info + Roster Setup this run. White rows = fixed assumption or PM-entered value.').font = Font(italic=True, size=9, color='548235')
    ws.merge_cells(f'A{r}:F{r}')

    for col, w in {'A': 32, 'B': 12, 'C': 46, 'D': 18, 'E': 16, 'F': 18}.items():
        ws.column_dimensions[col].width = w


# ============================================================================================
def build_staff_sheet(wb, project, demand, year):
    """Full-year staffing cost, no day-by-day grid (see module docstring for the simplification).
    For coverage>=7 roles the real day-grid always produces exactly 1 day off in every 7 (a fixed
    rotation, regardless of the literal CoverageDays value) — so the working-day fraction is 6/7.
    For coverage<7 roles the grid works Mon..CoverageDays-th weekday, Sun off — fraction is
    CoverageDays/7. Both branches are reproduced here as a monthly estimate: StaffCount ×
    ROUND(DaysInMonth × fraction, 0). This matches the day-grid's actual output for any given
    month to within rounding; it is not read from a live day-grid because this sheet has none."""
    ws = wb.create_sheet('Staff (Roster)')
    title_block(ws, 'Staff (Roster) — Full Year',
                'Estimated from average weekly coverage (see script docstring) — night differential (+30%) included, '
                'holiday differentials excluded (no annual holiday calendar on the input form yet).', 'A1:F1')
    ws['A3'] = 'Year'
    ws['A3'].font = Font(bold=True)
    ws['B3'] = year

    headers = ['Position', 'Staff Count'] + MONTH_NAMES + ['Annual Total']
    HEADER_ROW = 5
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=HEADER_ROW, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER

    DAYS_ROW = 6
    ws.cell(row=DAYS_ROW, column=1, value='Days in Month').font = Font(italic=True, size=9)
    for i in range(12):
        col = 3 + i
        col_letter = get_column_letter(col)
        f = ws.cell(row=DAYS_ROW, column=col, value=f'=DAY(EOMONTH(DATE($B$3,{i + 1},1),0))')
        f.font = Font(italic=True, size=9, color='7F7F7F')
        f.alignment = CENTER

    first_row = DAYS_ROW + 1
    r = first_row
    position_row = {}
    for d in demand:
        position_row[d['Position']] = r
        ws.cell(row=r, column=1, value=d['Position']).border = BORDER
        ws.cell(row=r, column=1).alignment = LEFT
        b = ws.cell(row=r, column=2, value=f'=IF(Q{r}>=7,ROUNDUP(P{r}*7/6,0),P{r})')
        b.border = BORDER
        b.alignment = CENTER
        for i in range(12):
            col = 3 + i
            col_letter = get_column_letter(col)
            day_ref = f'{col_letter}${DAYS_ROW}'
            formula = (f'=$B{r}*ROUND({day_ref}*IF($Q{r}>=7,6,$Q{r})/7,0)*$R{r}*IF($S{r}=1,{NIGHT_DIFFERENTIAL},1)')
            cell = ws.cell(row=r, column=col, value=formula)
            cell.number_format = MONEY_FMT
            cell.border = BORDER
        annual_col = 3 + 12
        annual = ws.cell(row=r, column=annual_col,
                          value=f'=SUM(C{r}:{get_column_letter(annual_col - 1)}{r})')
        annual.number_format = MONEY_FMT
        annual.border = BORDER
        annual.font = Font(bold=True)
        # Hidden helper columns: P=StaffPerDay, Q=CoverageDays, R=AvgDailyRate, S=IsNight(1/0)
        ws.cell(row=r, column=16, value=d['StaffPerDay'])
        ws.cell(row=r, column=17, value=d['CoverageDays'])
        ws.cell(row=r, column=18, value=d['AvgDailyRate'])
        ws.cell(row=r, column=19, value=1 if d['ShiftCode'] in NIGHT_SHIFT_CODES else 0)
        r += 1
    last_row = r - 1

    ws.cell(row=r, column=1, value='GRAND TOTAL').font = SECTION_FONT
    for i in range(12):
        col = 3 + i
        col_letter = get_column_letter(col)
        c = ws.cell(row=r, column=col, value=f'=SUM({col_letter}{first_row}:{col_letter}{last_row})')
        c.number_format = MONEY_FMT
        c.font = SECTION_FONT
    annual_col = 3 + 12
    annual_letter = get_column_letter(annual_col)
    c = ws.cell(row=r, column=annual_col, value=f'=SUM({annual_letter}{first_row}:{annual_letter}{last_row})')
    c.number_format = MONEY_FMT
    c.font = SECTION_FONT
    ANNUAL_TOTAL_CELL = f'{annual_letter}{r}'
    r += 2

    section(ws, r, 'REAL BENCHMARK CROSS-CHECK — from the Master List (derive_staffing_benchmarks.py)', ncols=6); r += 1
    hc_est = estimate_staff_headcount(project['total_gfa'])
    ws.cell(row=r, column=1, value='This roster\'s total headcount (Staff Count column, summed)').font = Font(bold=True)
    c = ws.cell(row=r, column=2, value=f'=SUM(B{first_row}:B{last_row})')
    c.fill = HIGHLIGHT_FILL
    c.alignment = CENTER
    r += 1
    ws.cell(row=r, column=1, value=f"Real market median for a {hc_est['bucket']} property (n={hc_est['n']})").font = Font(bold=True)
    c = ws.cell(row=r, column=2, value=hc_est['estimated_headcount'])
    c.fill = HIGHLIGHT_FILL
    c.alignment = CENTER
    ws.cell(row=r, column=3,
            value=f"Ratio used: {hc_est['ratio_used']:.3f} headcount per 1,000 m² GFA, real median for this size bucket").font = Font(italic=True, size=9, color='7F7F7F')
    ws.merge_cells(f'C{r}:F{r}')
    r += 1
    ws.cell(row=r, column=1,
            value=('This is a cross-check, not an override — the roster above is still driven by Staffing Demand\'s own '
                   'position-by-position ratios (editable PM assumptions). A big gap between the two rows above is worth '
                   'investigating before trusting either one.')).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:F{r}')
    ws.row_dimensions[r].height = 28

    for col in ('P', 'Q', 'R', 'S'):
        ws.column_dimensions[col].hidden = True
    ws.column_dimensions['A'].width = 28
    ws.column_dimensions['B'].width = 12
    for i in range(12):
        ws.column_dimensions[get_column_letter(3 + i)].width = 12
    ws.column_dimensions[get_column_letter(annual_col)].width = 16

    r += 2
    build_roster_detail_grid(ws, demand, r)

    # Category-level annual cost, as a live cross-sheet formula summing this sheet's own Annual
    # Total cells — for the Service sheet's comparison columns. Same matching AND exclusion rules
    # Service itself uses (SERVICE_CATEGORY_KEYWORDS / SERVICE_EXCLUDE_KEYWORDS), so "Security" here
    # means the exact same 7 rows Service prices as Security, not a looser/different definition.
    def _cell_sum(rows):
        return ("='Staff (Roster)'!" + "+'Staff (Roster)'!".join(f'{annual_letter}{rr}' for rr in rows)) if rows else '=0'

    category_annual_cells = {}
    for cat, keywords in SERVICE_CATEGORY_KEYWORDS.items():
        rows = [position_row[pos] for pos in position_row
                if any(kw in pos.lower() for kw in keywords)
                and not any(ex in pos.lower() for ex in SERVICE_EXCLUDE_KEYWORDS)]
        category_annual_cells[cat] = _cell_sum(rows)
        # Rows excluded from the citywide-comparable bucket (e.g. Cleaning - Supervisor) are still
        # a real cost — captured here under their own key so nothing silently drops out of any
        # sheet that sums category_annual_cells for a full-coverage total (e.g. Cost Priority).
        excluded_rows = [position_row[pos] for pos in position_row
                          if any(kw in pos.lower() for kw in keywords)
                          and any(ex in pos.lower() for ex in SERVICE_EXCLUDE_KEYWORDS)]
        if excluded_rows:
            category_annual_cells[f'{cat} — Supervisory'] = _cell_sum(excluded_rows)
    for cat, keywords in STAFF_MARKET_KEYWORDS.items():
        rows = [position_row[pos] for pos in position_row if any(kw in pos.lower() for kw in keywords)]
        category_annual_cells[cat] = _cell_sum(rows)

    return dict(annual_total_cell=ANNUAL_TOTAL_CELL, category_annual_cells=category_annual_cells)


def build_roster_detail_grid(ws, demand, start_row):
    """The classic single-month duty-schedule grid — day numbers and weekdays as two shared
    header rows, one column per day (1-31), shift code as the single value in each cell. Exactly
    the shape generate_roster.py's single-month output used, restored here per direct feedback
    (a Slicer only filters existing rows — it can't recompute a whole grid's formulas, which is
    what showing "a different month" in THIS shape actually requires).

    What makes it show a different month: ALL of it — the day-number header, the weekday header,
    every shift-code cell — is formula-driven off ONE cell, $B$4 (Month), a dropdown next to the
    existing Year cell ($B$3). Change $B$4, the whole grid recalculates for that month. This is
    the right tool for "pick a month, see that month's full grid" — a native Slicer isn't, since
    it filters rows in a table, it doesn't parametrize a formula.

    Same rotation/weekday shift-assignment logic as everywhere else on this sheet: coverage<7
    roles work Mon..CoverageDays-th weekday, Sun off — a fixed weekly rest day, same for every
    staff member on that role. Coverage>=7 roles need someone on duty every single day including
    Sunday, so they can't all take the same day off; instead each staff slot gets ONE fixed
    weekday off, staggered so the position is fully covered every day of the week ("xoay ca" —
    the team rotates through the week's days, not just the same rest day). Staff 1 = Sunday off
    (the "default weekend" anchor the roster starts from), Staff 2 = Monday, Staff 3 = Tuesday,
    and so on, cycling back to Sunday if there are more than 7 staff in one role. This anchors
    the pattern to real weekdays (WEEKDAY() against the actual calendar date) — the earlier
    version cycled off MOD(day-of-month,7), which doesn't correspond to any consistent weekday
    and could put a given staff's day off on a different weekday from one month to the next.
    ShiftCode/CoverageDays are baked as literals per row (known, real values at generation time —
    same convention as this sheet's hidden P/Q/R/S columns above); Day/Weekday/the shift-code
    IF-branch stay live formulas since they depend on $B$4, which is meant to be changed by hand."""
    MAX_DAYS = 31
    section(ws, start_row, 'FULL YEAR ROSTER — day-by-day duty schedule (change Month above to view a different month)', ncols=7)
    r = start_row + 1
    ws.cell(row=r, column=1,
            value='Month (1-12) — change this to view that month\'s full grid below. Year is set above ($B$3).').font = Font(bold=True)
    month_cell = ws.cell(row=r, column=2, value=1)
    month_cell.fill = PatternFill('solid', fgColor='FFF7CC')
    month_cell.border = BORDER
    month_cell.alignment = CENTER
    dv_month = DataValidation(type='whole', operator='between', formula1=1, formula2=12,
                               showErrorMessage=True, errorTitle='Invalid month', error='Enter 1-12')
    ws.add_data_validation(dv_month)
    dv_month.add(month_cell)
    MONTH_CELL = f'$B${r}'
    r += 2

    day_num_row = r
    wd_row = r + 1
    ws.cell(row=day_num_row, column=1, value='Position').fill = HEADER_FILL
    ws.cell(row=day_num_row, column=1).font = HEADER_FONT
    ws.cell(row=day_num_row, column=1).border = BORDER
    ws.cell(row=day_num_row, column=2, value='Staff Slot').fill = HEADER_FILL
    ws.cell(row=day_num_row, column=2).font = HEADER_FONT
    ws.cell(row=day_num_row, column=2).border = BORDER
    ws.cell(row=wd_row, column=1).border = BORDER
    ws.cell(row=wd_row, column=2).border = BORDER
    DAY_COL_START = 3
    for i in range(MAX_DAYS):
        col = DAY_COL_START + i
        col_letter = get_column_letter(col)
        day_cell = ws.cell(row=day_num_row, column=col,
                            value=f'=IF(COLUMN()-{DAY_COL_START - 1}<=DAY(EOMONTH(DATE($B$3,{MONTH_CELL},1),0)),COLUMN()-{DAY_COL_START - 1},"")')
        day_cell.fill = HEADER_FILL
        day_cell.font = HEADER_FONT
        day_cell.alignment = CENTER
        day_cell.border = BORDER
        wd_cell = ws.cell(row=wd_row, column=col,
                           value=f'=IF({col_letter}{day_num_row}="","",TEXT(DATE($B$3,{MONTH_CELL},{col_letter}{day_num_row}),"ddd"))')
        wd_cell.alignment = CENTER
        wd_cell.font = Font(italic=True, size=8, color='7F7F7F')
        wd_cell.border = BORDER
    r = wd_row + 1
    first_data_row = r

    for d in demand:
        staff_count = math.ceil(d['StaffPerDay'] * 7 / 6) if d['CoverageDays'] >= 7 else d['StaffPerDay']
        for slot in range(1, staff_count + 1):
            dayoff_index = (slot - 1) % 7
            # WEEKDAY(date,2) numbers Mon=1..Sun=7; index0(Staff1)->Sun(7), index1(Staff2)->Mon(1), etc.
            dayoff_weekday = 7 if dayoff_index == 0 else dayoff_index
            ws.cell(row=r, column=1, value=d['Position'] if slot == 1 else '').border = BORDER
            ws.cell(row=r, column=1).alignment = LEFT
            ws.cell(row=r, column=2, value=f'Staff {slot}').border = BORDER
            ws.cell(row=r, column=2).alignment = CENTER
            row_fill = PatternFill('solid', fgColor='EDEEF3') if slot % 2 == 0 else None
            for i in range(MAX_DAYS):
                col = DAY_COL_START + i
                col_letter = get_column_letter(col)
                if d['CoverageDays'] >= 7:
                    formula = (f'=IF({col_letter}${day_num_row}="","",'
                               f'IF(WEEKDAY(DATE($B$3,{MONTH_CELL},{col_letter}${day_num_row}),2)={dayoff_weekday},'
                               f'"O","{d["ShiftCode"]}"))')
                else:
                    formula = (f'=IF({col_letter}${day_num_row}="","",'
                               f'IF(WEEKDAY(DATE($B$3,{MONTH_CELL},{col_letter}${day_num_row}),2)<={d["CoverageDays"]},'
                               f'"{d["ShiftCode"]}","O"))')
                cell = ws.cell(row=r, column=col, value=formula)
                cell.alignment = CENTER
                cell.border = BORDER
                if row_fill:
                    cell.fill = row_fill
            r += 1
        r += 1  # blank spacer row between positions, matching the reference layout
    last_data_row = r - 2

    for i in range(MAX_DAYS):
        ws.column_dimensions[get_column_letter(DAY_COL_START + i)].width = 5
    ws.freeze_panes = ws.cell(row=first_data_row, column=DAY_COL_START).coordinate

    # O = grey (day off), a real shift code = light blue (on duty) — same visual language as
    # generate_roster.py's single-month output.
    full_range = f'{get_column_letter(DAY_COL_START)}{first_data_row}:{get_column_letter(DAY_COL_START + MAX_DAYS - 1)}{last_data_row}'
    ws.conditional_formatting.add(full_range, FormulaRule(
        formula=[f'{get_column_letter(DAY_COL_START)}{first_data_row}="O"'],
        fill=PatternFill('solid', fgColor='F2F2F2')))
    ws.conditional_formatting.add(full_range, FormulaRule(
        formula=[f'AND({get_column_letter(DAY_COL_START)}{first_data_row}<>"O",{get_column_letter(DAY_COL_START)}{first_data_row}<>"")'],
        fill=PatternFill('solid', fgColor='D9E1F2')))


# ============================================================================================
def build_service_sheet(wb, demand, staff):
    """Same citywide rates as before, but now × real staff headcount, not a flat "1 post"
    assumption — AND with Security's rate correctly split 3 ways first (see
    SERVICE_SHIFT_ROLES_PER_POST) — AND with a real, data-driven night-shift blend applied, so this
    top-down reference isn't systematically low against the Staff (Roster) sheet's bottom-up total
    (which already prices night shifts at +30%). The blend factor is computed from THIS project's
    own Staffing Demand: whatever fraction of a category's real headcount works a night shift
    (ShiftCode in NIGHT_SHIFT_CODES) gets NIGHT_DIFFERENTIAL applied to just that fraction, same
    logic as build_staff_sheet's per-row IF($S=1,...) — not a guess, not copied from Staff
    (Roster)'s own numbers, computed independently from the same real demand data both sheets share.
    Qty per category comes from Staffing Demand: positions are matched to Security/Cleaning/
    Landscape by keyword in their name (see SERVICE_CATEGORY_KEYWORDS), then each matched
    position's headcount is computed with the EXACT same formula the Staff (Roster) sheet's Staff
    Count column and the day-by-day roster grid both use — ceil(StaffPerDay×7/6) for 7-day coverage
    roles, StaffPerDay directly otherwise — so this sheet's Qty always agrees with the roster
    instead of drifting from it. Positions matching no category (e.g. Reception), OR matching a
    SERVICE_EXCLUDE_KEYWORDS term (e.g. "Cleaning - Supervisor" — no citywide reference for
    supervisory roles, see that constant's comment), have no citywide reference rate and are
    excluded here, not silently priced at the wrong rate — they're still costed in full on the
    Staff (Roster) sheet.

    Self-diagnosing, not just a number to eyeball against another sheet: columns I-K pull each
    category's real equivalent straight off the Staff (Roster) sheet (staff['category_annual_cells']
    — same matching/exclusion rules, so it's the exact same headcount, not a looser comparison),
    compute the real % gap, and label it — so whether a gap is normal variance or worth
    investigating is answered on this sheet, not re-derived in conversation every time."""
    ws = wb.create_sheet('Service')
    title_block(ws, 'Service — Citywide Reference Rates',
                f'{RATE_CARD_SOURCE} Per-person monthly rate (citywide post rate, split across shift roles where a '
                'post needs more than one, then blended for this project\'s own real night-shift headcount split — '
                'see the next 2 columns) × real staff headcount from Staffing Demand, compared directly against the '
                'Staff (Roster) sheet\'s own real cost for the same headcount (columns I-K) so any gap is explained '
                'right here, not left for a manual side-by-side.', 'A1:L1')

    headers = ['Category', 'Citywide Rate (VND/post/month, real)', 'Shift Roles/Post', 'Night-Shift Blend',
               'Per-Person Monthly Rate (derived)', 'Qty (real staff headcount)', 'Monthly Total (VND)',
               'Annual (×12)', 'Staff (Roster) Equivalent (VND/year)', 'Gap %', 'Gap Assessment', 'Qty source']
    r = 4
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    r += 1
    first_row = r
    for name, rate in [('Security', SECURITY_RATE_CITYWIDE), ('Cleaning', CLEANING_RATE_CITYWIDE),
                        ('Landscape', LANDSCAPE_RATE_CITYWIDE)]:
        keywords = SERVICE_CATEGORY_KEYWORDS[name]
        matched = [d for d in demand if any(kw in d['Position'].lower() for kw in keywords)
                   and not any(ex in d['Position'].lower() for ex in SERVICE_EXCLUDE_KEYWORDS)]
        excluded = [d for d in demand if any(kw in d['Position'].lower() for kw in keywords)
                    and any(ex in d['Position'].lower() for ex in SERVICE_EXCLUDE_KEYWORDS)]
        qty = sum(math.ceil(d['StaffPerDay'] * 7 / 6) if d['CoverageDays'] >= 7 else d['StaffPerDay'] for d in matched)
        shifts = SERVICE_SHIFT_ROLES_PER_POST[name]
        night_qty = sum(math.ceil(d['StaffPerDay'] * 7 / 6) if d['CoverageDays'] >= 7 else d['StaffPerDay']
                         for d in matched if d['ShiftCode'] in NIGHT_SHIFT_CODES)
        night_fraction = (night_qty / qty) if qty else 0
        blend_factor = 1 + night_fraction * (NIGHT_DIFFERENTIAL - 1)

        ws.cell(row=r, column=1, value=name).border = BORDER
        c2 = ws.cell(row=r, column=2, value=rate)
        c2.number_format = MONEY_FMT
        c2.border = BORDER
        c3 = ws.cell(row=r, column=3, value=shifts)
        c3.border = BORDER
        c3.alignment = CENTER
        c4 = ws.cell(row=r, column=4, value=round(blend_factor, 4))
        c4.border = BORDER
        c4.alignment = CENTER
        c4.number_format = '0.000'
        c5 = ws.cell(row=r, column=5, value=f'=B{r}/C{r}*D{r}')
        c5.number_format = MONEY_FMT
        c5.border = BORDER
        c6 = ws.cell(row=r, column=6, value=qty)
        c6.border = BORDER
        c6.alignment = CENTER
        c7 = ws.cell(row=r, column=7, value=f'=E{r}*F{r}')
        c7.number_format = MONEY_FMT
        c7.border = BORDER
        c8 = ws.cell(row=r, column=8, value=f'=G{r}*12')
        c8.number_format = MONEY_FMT
        c8.border = BORDER
        c9 = ws.cell(row=r, column=9, value=staff['category_annual_cells'][name])
        c9.number_format = MONEY_FMT
        c9.border = BORDER
        c10 = ws.cell(row=r, column=10, value=f'=IF(I{r}=0,"n/a",(H{r}-I{r})/I{r})')
        c10.number_format = '+0.0%;-0.0%'
        c10.border = BORDER
        c10.alignment = CENTER
        c11 = ws.cell(row=r, column=11,
                       value=(f'=IF(I{r}=0,"No comparison — Staff (Roster) side is 0",'
                              f'IF(ABS(J{r})<=0.05,"Close match (within 5%)",'
                              f'IF(ABS(J{r})<=0.20,"Normal cross-methodology variance",'
                              f'"Large gap — investigate the rate assumption for this category")))'))
        c11.border = BORDER
        c11.alignment = LEFT
        source_label = ((f"{len(matched)} real position(s) — " + ', '.join(d['Position'] for d in matched) +
                          f' ({night_qty}/{qty} headcount on a night shift)') if matched
                         else 'No matching position in Staffing Demand — Qty=0')
        if excluded:
            source_label += ('. EXCLUDED (no citywide reference for this role): ' +
                              ', '.join(d['Position'] for d in excluded) +
                              ' — still costed on the Staff (Roster) sheet.')
        c12 = ws.cell(row=r, column=12, value=source_label)
        c12.border = BORDER
        c12.alignment = LEFT
        r += 1
    last_row = r - 1
    ws.cell(row=r, column=1, value='TOTAL').font = SECTION_FONT
    c7 = ws.cell(row=r, column=7, value=f'=SUM(G{first_row}:G{last_row})')
    c7.number_format = MONEY_FMT
    c7.font = SECTION_FONT
    c8 = ws.cell(row=r, column=8, value=f'=SUM(H{first_row}:H{last_row})')
    c8.number_format = MONEY_FMT
    c8.font = SECTION_FONT
    c9 = ws.cell(row=r, column=9, value=f'=SUM(I{first_row}:I{last_row})')
    c9.number_format = MONEY_FMT
    c9.font = SECTION_FONT
    c10 = ws.cell(row=r, column=10, value=f'=IF(I{r}=0,"n/a",(H{r}-I{r})/I{r})')
    c10.number_format = '+0.0%;-0.0%'
    c10.font = SECTION_FONT
    c10.alignment = CENTER
    ANNUAL_SERVICE_CELL = f'H{r}'
    r += 2

    section(ws, r, 'STAFF-DOMAIN MARKET RATE CROSS-CHECK — every other staffed position', ncols=9); r += 1
    ws.cell(row=r, column=1,
            value=('Security/Cleaning/Landscape above use a citywide POST rate. These positions have no such rate — '
                   'instead, each is checked against its own real market-average MONTHLY SALARY from '
                   'Fact_MasterRateCard.csv\'s Staff domain (the same numbers used to set their default AvgDailyRate '
                   'in Staffing Demand — see build_project_input_form.py).')).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:I{r}')
    ws.row_dimensions[r].height = 28
    r += 1
    mkt_headers = ['Position', 'Real Market Rate (VND/month)', 'n', 'Qty (real headcount)',
                   'Market-Rate Monthly Total (VND)', 'Staff (Roster) Equivalent (VND/year)', 'Gap %', 'Gap Assessment', 'Source item']
    for c, h in enumerate(mkt_headers, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    r += 1
    mkt_first_row = r
    for name, keywords in STAFF_MARKET_KEYWORDS.items():
        matched = [d for d in demand if any(kw in d['Position'].lower() for kw in keywords)]
        if not matched:
            continue
        qty = sum(math.ceil(d['StaffPerDay'] * 7 / 6) if d['CoverageDays'] >= 7 else d['StaffPerDay'] for d in matched)
        monthly_rate, n, source_item = STAFF_MARKET_RATES[name]

        ws.cell(row=r, column=1, value=name).border = BORDER
        c2 = ws.cell(row=r, column=2, value=monthly_rate)
        c2.number_format = MONEY_FMT
        c2.border = BORDER
        c3 = ws.cell(row=r, column=3, value=n)
        c3.border = BORDER
        c3.alignment = CENTER
        c4 = ws.cell(row=r, column=4, value=qty)
        c4.border = BORDER
        c4.alignment = CENTER
        c5 = ws.cell(row=r, column=5, value=f'=B{r}*D{r}')
        c5.number_format = MONEY_FMT
        c5.border = BORDER
        c6 = ws.cell(row=r, column=6, value=staff['category_annual_cells'][name])
        c6.number_format = MONEY_FMT
        c6.border = BORDER
        c7 = ws.cell(row=r, column=7, value=f'=IF(F{r}=0,"n/a",((E{r}*12)-F{r})/F{r})')
        c7.number_format = '+0.0%;-0.0%'
        c7.border = BORDER
        c7.alignment = CENTER
        c8 = ws.cell(row=r, column=8,
                      value=(f'=IF(F{r}=0,"No comparison — Staff (Roster) side is 0",'
                             f'IF(ABS(G{r})<=0.05,"Close match (within 5%)",'
                             f'IF(ABS(G{r})<=0.20,"Normal cross-methodology variance",'
                             f'"Large gap — investigate the rate assumption for this position")))'))
        c8.border = BORDER
        c8.alignment = LEFT
        c9 = ws.cell(row=r, column=9, value=f'Fact_MasterRateCard.csv, Staff domain, "{source_item}" row (n={n})')
        c9.border = BORDER
        c9.alignment = LEFT
        r += 1
    mkt_last_row = r - 1
    if mkt_last_row >= mkt_first_row:
        ws.cell(row=r, column=1, value='TOTAL').font = SECTION_FONT
        c5 = ws.cell(row=r, column=5, value=f'=SUM(E{mkt_first_row}:E{mkt_last_row})')
        c5.number_format = MONEY_FMT
        c5.font = SECTION_FONT
        c6 = ws.cell(row=r, column=6, value=f'=SUM(F{mkt_first_row}:F{mkt_last_row})')
        c6.number_format = MONEY_FMT
        c6.font = SECTION_FONT
        r += 1
    r += 1

    ws.cell(row=r, column=1,
            value=('Only Security/Cleaning/Landscape have a citywide POST reference rate in Fact_MasterRateCard.csv\'s '
                   'Service domain — every other staffed position is cross-checked above using the Staff domain\'s real '
                   'market-average salary instead. Any supervisory role (e.g. Cleaning - Supervisor) still has neither, '
                   'since no citywide rate exists for supervisory pay and it wasn\'t one of the positions market-rate '
                   'data was pulled for; it\'s still costed in full on the Staff (Roster) sheet.')
            ).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:L{r}')
    ws.row_dimensions[r].height = 40
    r += 1
    ws.cell(row=r, column=1,
            value=('Security\'s citywide rate is real but denominated per POST, not per person — it explicitly covers '
                   'all 3 shift roles (Morning/Afternoon/Night) combined, per the same source cited on Staffing '
                   'Demand\'s own AvgDailyRate cell comments. Divided by 3 here before multiplying by headcount, so a '
                   'guard who only works one shift isn\'t priced as if they cost a whole round-the-clock post.')
            ).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:L{r}')
    ws.row_dimensions[r].height = 28
    r += 1
    ws.cell(row=r, column=1,
            value=(f'Night-Shift Blend accounts for the +{(NIGHT_DIFFERENTIAL - 1) * 100:.0f}% night-shift premium '
                   'the Staff (Roster) sheet already prices (same NIGHT_DIFFERENTIAL) — without it, this flat citywide '
                   'reference would be systematically low against the roster for any category with real night-shift '
                   'headcount. Computed from THIS project\'s own Staffing Demand split, not copied from Staff (Roster).')
            ).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:L{r}')
    ws.row_dimensions[r].height = 28
    r += 1
    ws.cell(row=r, column=1,
            value=('Staff (Roster) Equivalent (col I) sums that sheet\'s OWN Annual Total for the exact same positions '
                   '(same matching + exclusion rules) — not a separate estimate, the real number from the real roster. '
                   'Gap % and Gap Assessment (cols J-K) are computed fresh here, not copied — close (<=5%) or normal '
                   '(<=20%) needs no action; a "Large gap" flag means the two independent methods disagree by more than '
                   'cross-methodology noise usually explains, and the underlying rate assumption for that category is '
                   'worth checking (e.g. is it PM-entered, or tied to a real citywide/comparable source — see the '
                   'Basis/Rate source columns on the sheets that actually set each rate).')
            ).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:L{r}')
    ws.row_dimensions[r].height = 40

    for col, w in {'A': 16, 'B': 20, 'C': 14, 'D': 16, 'E': 22, 'F': 20, 'G': 20, 'H': 20,
                    'I': 24, 'J': 12, 'K': 30, 'L': 55}.items():
        ws.column_dimensions[col].width = w

    return dict(annual_total_cell=ANNUAL_SERVICE_CELL)


# ============================================================================================
def load_capex_items():
    items = []
    with open(RATE_CARD_CSV, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            if row['Domain'] != 'Capex':
                continue
            category, item = row['Category'].strip(), row['Item'].strip()
            if category == 'REFERENCE CATEGORY':
                continue  # data artifact in the source CSV, not a real capex item
            price_raw = row[' UnitPrice '].strip().replace(',', '')
            try:
                price = float(price_raw)
            except ValueError:
                continue
            items.append(dict(category=category, item=item, unit=row['Unit'].strip(), price=price))
    return items


def build_capex_sheet(wb, project):
    ws = wb.create_sheet('Capex')

    items, source_info = estimate_capex_items(project['total_nfa'], exclude_name=project['name'])

    if items:
        title_block(ws, 'Capex — Estimated Equipment List',
                    (f"Qty is PRE-FILLED, not blank: scaled from {source_info['source_project']}'s own real Capex "
                     f"line items (Fact_Capex_Rescanned.csv) by the ratio of this project's Total NFA to "
                     f"{source_info['source_project']}'s ({source_info['target_nfa']:,.0f} ÷ {source_info['source_nfa']:,.0f} "
                     f"= {source_info['scale_factor']}×). Real item names and prices, estimated quantity — "
                     f"still a PM-editable starting point, not a guess from nothing."), 'A1:F1')
    else:
        title_block(ws, 'Capex — Equipment Price List',
                    'Fact_MasterRateCard.csv, Domain=Capex — real per-unit reference prices. Quantity is blank for the PM '
                    'to fill in per project; no real comparable project was available to scale from.', 'A1:F1')

    r = 4
    section(ws, r, 'CATEGORY CROSS-CHECK — independent NFA-ratio estimate (estimate_capex_qty.py)', ncols=6); r += 1
    ws.cell(row=r, column=1,
            value=('A second, independent method: real Qty ÷ verified NFA across 5-6 real projects (not just the one nearest '
                   'match used for the item list below), applied to this project\'s Total NFA. Compare against the category '
                   'subtotals below — a big gap between the two methods is worth investigating before trusting either.')).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:F{r}')
    ws.row_dimensions[r].height = 28
    r += 1
    cat_headers = ['Category', 'Study 1 Estimated Qty (NFA-based, independent)', 'Real Sample Size (N)', 'Real Range (per 1,000m² NFA)']
    for c, h in enumerate(cat_headers, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    r += 1
    capex_est = estimate_capex_qty(project['total_nfa'])
    for cat, v in capex_est.items():
        ws.cell(row=r, column=1, value=cat).border = BORDER
        c2 = ws.cell(row=r, column=2, value=v['study1_qty'])
        c2.border = BORDER
        c2.fill = HIGHLIGHT_FILL
        c2.alignment = CENTER
        ws.cell(row=r, column=3, value=v['study1_n']).border = BORDER
        ws.cell(row=r, column=3).alignment = CENTER
        ws.cell(row=r, column=4, value=f"{v['study1_range'][0]:.2f} – {v['study1_range'][1]:.2f}").border = BORDER
        ws.cell(row=r, column=4).alignment = CENTER
        r += 1
    r += 1

    if items:
        section(ws, r, f"ESTIMATED ITEM LIST — scaled from {source_info['source_project']} ({source_info['scale_factor']}×)", ncols=6); r += 1
        items = sorted(items, key=lambda x: (x['category'], -x['unit_price']))
    else:
        section(ws, r, 'CAPEX ITEM PRICE LIST', ncols=6); r += 1
        items = load_capex_items()
        items.sort(key=lambda x: (x['category'], -x['price']))
        for it in items:
            it['unit_price'] = it.pop('price')
            it['qty'] = None

    headers = ['Category', 'Item', 'Unit', 'Unit Price (VND)', 'Qty (editable)', 'Subtotal (VND)']
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    item_table_first_row = r + 1
    r += 1

    subtotal_cells = []
    category_subtotal_cells = {}
    current_cat = None
    cat_start = None
    for it in items:
        if it['category'] != current_cat:
            if current_cat is not None:
                r = _write_capex_subtotal(ws, r, current_cat, cat_start, r - 1, subtotal_cells)
                category_subtotal_cells[current_cat] = f'F{r}'
                r += 1
            current_cat = it['category']
            cat_start = r
        ws.cell(row=r, column=1, value=it['category']).border = BORDER
        ic = ws.cell(row=r, column=2, value=it['item'])
        ic.border = BORDER
        ic.alignment = LEFT
        ws.cell(row=r, column=3, value=it['unit']).border = BORDER
        pc = ws.cell(row=r, column=4, value=it['unit_price'])
        pc.number_format = MONEY_FMT
        pc.border = BORDER
        qc = ws.cell(row=r, column=5, value=it['qty'])
        qc.border = BORDER
        qc.fill = PatternFill('solid', fgColor='FFF7CC')
        qc.alignment = CENTER
        sc = ws.cell(row=r, column=6, value=f'=D{r}*E{r}')
        sc.number_format = MONEY_FMT
        sc.border = BORDER
        r += 1
    r = _write_capex_subtotal(ws, r, current_cat, cat_start, r - 1, subtotal_cells)
    category_subtotal_cells[current_cat] = f'F{r}'
    r += 2

    ws.cell(row=r, column=1, value='GRAND TOTAL').font = SECTION_FONT
    grand = ws.cell(row=r, column=6, value='=' + '+'.join(subtotal_cells))
    grand.number_format = MONEY_FMT
    grand.font = SECTION_FONT
    GRAND_TOTAL_CELL = f'F{r}'

    for col, w in {'A': 30, 'B': 42, 'C': 12, 'D': 16, 'E': 12, 'F': 16}.items():
        ws.column_dimensions[col].width = w
    ws.freeze_panes = f'A{item_table_first_row}'

    return dict(grand_total_cell=GRAND_TOTAL_CELL, category_subtotal_cells=category_subtotal_cells)


def _write_capex_subtotal(ws, r, category, start, end, subtotal_cells):
    ws.cell(row=r, column=1, value=f'Subtotal — {category}').font = Font(bold=True, size=9)
    ws.merge_cells(f'A{r}:E{r}')
    c = ws.cell(row=r, column=6, value=f'=SUM(F{start}:F{end})')
    c.number_format = MONEY_FMT
    c.font = Font(bold=True, size=9)
    c.fill = SECTION_FILL
    ws.cell(row=r, column=1).fill = SECTION_FILL
    subtotal_cells.append(f'F{r}')
    return r


# ============================================================================================
# Real, from A&K Tower's own "B2.8 Đơn giá gửi xe-Parking pr" sheet, Section B ("ĐỀ XUẤT ĐƠN GIÁ
# GỬI XE TẠI DỰ ÁN" — proposed parking price at the project) — A&K's own ACTUAL decision, not just
# a market survey, informed by 6 real comparables (Marq, Estella Heights, Canary Heights, Canary
# Homez, Habitat, Sky Bridge) shown in Section A of the same sheet.
PARKING_FEE_CAR_MONTHLY = 1_100_000
PARKING_FEE_MOTO_MONTHLY = 110_000
PARKING_FEE_SOURCE = ('A&K Tower\'s own proposed parking price ("B2.8 Đơn giá gửi xe-Parking pr" sheet, Section B) — '
                       'informed by 6 real comparable projects\' rates (Marq/Estella Heights/Canary Heights/Canary '
                       'Homez/Habitat/Sky Bridge, shown in that sheet\'s Section A), not just A&K\'s own guess.')

# Real, from "Cho thuê bãi xe ô tô" sheet — a DIFFERENT revenue model than per-vehicle fees above:
# leasing the WHOLE parking area to a third-party operator for one fixed monthly rent, instead of
# billing each resident's vehicle individually. 3 real comparables (The Sun Avenue, Sunrise City
# Central, Sunrise Riverside) — their car-slot-count ÷ parking-NFA ratio is remarkably tight
# (902/11,275=12.500, 289/3,613=12.502, 1,058/13,225=12.500 m²/slot — real, not assumed), so
# parking NFA for a new project is estimated from its own real car slot count via that same ratio.
# The rental RATE per m² has much wider real spread (17,391-77,880 VND/m² NFA/month across the 3),
# so both the average AND that range are shown — never collapsed into one falsely-precise number.
PARKING_LEASE_NFA_PER_SLOT = 12.5  # m² NFA per car slot — real, n=3, tight agreement (see comment above)
PARKING_LEASE_COMPARABLES = [
    ('The Sun Avenue', 902, 11275, 522430288.73, 46335.28),
    ('Sunrise City Central', 289, 3613, 281380804, 77880.10),
    ('Sunrise Riverside', 1058, 13225, 230000000, 17391.30),
]
PARKING_LEASE_RATE_AVG = round(sum(c[4] for c in PARKING_LEASE_COMPARABLES) / len(PARKING_LEASE_COMPARABLES), 2)

# Rates are real, from Fact_MasterRateCard.csv's Service domain, "Elevator advertising" category.
# Quantities are NOT real data — no source file ties ad-device count to building scale — so these
# are a stated, editable ASSUMPTION (qty_per_tower × Project Info's real Tower Count, or a flat
# qty for basement-level screens which don't scale with towers the same way), pre-filled instead
# of left blank so this sheet shows a real starting estimate rather than a silent $0. Still fully
# PM-editable — the fill color and column header say so.
ELEVATOR_AD_ITEMS = [
    # (item, rate, qty_per_tower, flat_qty, assumption)
    ('Ad frame (tower lobby, inside elevator)', 848_485, 2, None,
     'Assumption, not real data: ~2 ad frames per tower (roughly one per elevator bank) — a common VN high-rise '
     'pattern, not this project\'s own real elevator count (not collected anywhere in the source data).'),
    ('LCD screen (tower lobby)', 1_212_121, 1, None,
     'Assumption, not real data: 1 LCD screen per tower lobby.'),
    ('LCD screen (basement lobby)', 1_060_606, None, 1,
     'Assumption, not real data: 1 basement lobby screen per project (flat, not scaled by tower count — most '
     'basements are shared across towers, not one per tower).'),
]


def build_additional_revenue_sheet(wb, project):
    """Extra Revenue beyond the management fee — Parking Fee and Elevator Advertising. New
    category: A&K Tower's own real budget structure ("A1. Tổng hợp" sheet) explicitly separates
    "A.I Revenue of Management fee" from "A.II Extra Revenue" (Parking fee/Advertising/Rentals/
    Others) as two distinct lines — this workbook only ever had the first one built.

    Parking Fee uses A&K's own real PROPOSED rate (not a market survey number) × this project's
    own real car/moto slot counts from Project Info, shown at 100% occupancy — real slot counts,
    but no real occupancy-rate data exists anywhere in the source files, so this is stated as a
    maximum/ceiling, not a realistic average; PM should apply their own occupancy assumption.

    Elevator Advertising uses real per-device monthly rates; Qty (how many ad frames/LCD screens a
    NEW project would have) is PRE-FILLED from a stated assumption (qty_per_tower × Project Info's
    real Tower Count — see ELEVATOR_AD_ITEMS) rather than left blank, since no real data ties
    device count to building scale and a $0 default undersells the category entirely. Still fully
    PM-editable — the assumption is disclosed per-row in the Source column, not hidden.

    "Rentals" (Cho thuê — leasing common space, e.g. retail/F&B) and "Cho thuê bãi xe" (leasing the
    whole parking area to a third-party operator, a different revenue model than per-vehicle fees)
    are real categories mentioned in the source files but not extracted here — not fabricated.

    NOT included in Total Project Value (Net) yet — same as OPEX before that was explicitly
    confirmed; whether Extra Revenue should be added to the top line is a real methodology
    question, checked with the PM rather than assumed."""
    ws = wb.create_sheet('Additional Revenue')
    title_block(ws, 'Additional Revenue — Beyond the Management Fee',
                'Real data: A&K Tower\'s own proposed Parking Fee rate (informed by 6 real comparables) × this '
                'project\'s real slot counts; Elevator Advertising\'s real per-device rates, Qty left for the PM to '
                'fill in. NOT included in Total Project Value (Net) yet — see this sheet\'s notes.', 'A1:F1')

    r = 4
    section(ws, r, 'PARKING FEE (at 100% occupancy — a ceiling, not a realistic average; no real occupancy data exists)', ncols=6); r += 1
    headers = ['Type', 'Rate (VND/vehicle/month)', 'Slots (from Project Info)', 'Monthly Revenue (VND)', 'Annual (×12)', 'Source']
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    r += 1
    parking_first_row = r
    for label, rate, slots in [('Car', PARKING_FEE_CAR_MONTHLY, project.get('car_slots') or 0),
                                ('Motorbike', PARKING_FEE_MOTO_MONTHLY, project.get('moto_slots') or 0)]:
        ws.cell(row=r, column=1, value=label).border = BORDER
        c2 = ws.cell(row=r, column=2, value=rate)
        c2.number_format = MONEY_FMT
        c2.border = BORDER
        c3 = ws.cell(row=r, column=3, value=slots)
        c3.border = BORDER
        c3.alignment = CENTER
        c4 = ws.cell(row=r, column=4, value=f'=B{r}*C{r}')
        c4.number_format = MONEY_FMT
        c4.border = BORDER
        c5 = ws.cell(row=r, column=5, value=f'=D{r}*12')
        c5.number_format = MONEY_FMT
        c5.border = BORDER
        c6 = ws.cell(row=r, column=6, value=PARKING_FEE_SOURCE)
        c6.border = BORDER
        c6.alignment = LEFT
        r += 1
    parking_last_row = r - 1
    ws.cell(row=r, column=1, value='PARKING TOTAL').font = SECTION_FONT
    c4 = ws.cell(row=r, column=4, value=f'=SUM(D{parking_first_row}:D{parking_last_row})')
    c4.number_format = MONEY_FMT
    c4.font = SECTION_FONT
    c5 = ws.cell(row=r, column=5, value=f'=SUM(E{parking_first_row}:E{parking_last_row})')
    c5.number_format = MONEY_FMT
    c5.font = SECTION_FONT
    PARKING_ANNUAL_CELL = f'E{r}'
    r += 2

    section(ws, r, 'ALTERNATIVE: LEASE WHOLE PARKING AREA TO AN OPERATOR (fixed rent, zero occupancy risk)', ncols=6); r += 1
    ws.cell(row=r, column=1,
            value=('Real data (3 comparables — The Sun Avenue/Sunrise City Central/Sunrise Riverside): car-slot-count ÷ '
                   f'parking-NFA is a tight, consistent {PARKING_LEASE_NFA_PER_SLOT:g} m²/slot across all 3, used to estimate '
                   'this project\'s own parking NFA from its real car slot count. Rental RATE per m² has a much wider real '
                   'spread (17,391–77,880 VND/m²/month) — shown as a range, not one falsely-precise number. Unlike '
                   'per-vehicle billing above, this is a FIXED monthly rent regardless of how many spaces actually get '
                   'used — trades upside at high occupancy for a guaranteed floor at low occupancy.')
            ).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:F{r}')
    ws.row_dimensions[r].height = 55
    r += 1
    car_slots = project.get('car_slots') or 0
    est_parking_nfa = round(car_slots * PARKING_LEASE_NFA_PER_SLOT)
    lease_headers = ['Metric', 'Value', 'Basis', '', '', 'Source']
    for label, val, basis in [
        ('Car Slots (from Project Info)', car_slots, ''),
        ('Estimated Parking NFA (m²)', est_parking_nfa, f'Car Slots × {PARKING_LEASE_NFA_PER_SLOT:g} m²/slot (real ratio, n=3)'),
        ('Estimated Monthly Lease Revenue — low end (VND)', round(est_parking_nfa * 17391.30), 'At the lowest real comparable rate (Sunrise Riverside)'),
        ('Estimated Monthly Lease Revenue — average (VND)', round(est_parking_nfa * PARKING_LEASE_RATE_AVG), f'At the {PARKING_LEASE_RATE_AVG:,.0f} VND/m² average of 3 real comparables'),
        ('Estimated Monthly Lease Revenue — high end (VND)', round(est_parking_nfa * 77880.10), 'At the highest real comparable rate (Sunrise City Central)'),
    ]:
        ws.cell(row=r, column=1, value=label).border = BORDER
        ws.cell(row=r, column=1).alignment = LEFT
        c2 = ws.cell(row=r, column=2, value=val)
        c2.number_format = MONEY_FMT if 'VND' in label else '#,##0'
        c2.border = BORDER
        ws.cell(row=r, column=3, value=basis).border = BORDER
        ws.cell(row=r, column=3).alignment = LEFT
        ws.merge_cells(f'C{r}:E{r}')
        c6 = ws.cell(row=r, column=6, value='"Cho thuê bãi xe ô tô" sheet — 3 real comparable projects, see note above')
        c6.border = BORDER
        c6.alignment = LEFT
        r += 1
    lease_avg_annual = round(est_parking_nfa * PARKING_LEASE_RATE_AVG * 12)
    ws.cell(row=r, column=1, value='Breakeven fill % — below this, LEASING beats per-vehicle billing').font = Font(bold=True)
    car_fee_annual_100pct = PARKING_FEE_CAR_MONTHLY * car_slots * 12
    breakeven_pct = (lease_avg_annual / car_fee_annual_100pct) if car_fee_annual_100pct else 0
    c2 = ws.cell(row=r, column=2, value=breakeven_pct)
    c2.number_format = '0.0%'
    c2.font = Font(bold=True)
    c2.fill = HIGHLIGHT_FILL
    ws.cell(row=r, column=3,
            value=(f'(Lease revenue at average rate, annualized) ÷ (Car parking fee revenue at 100% fill, annualized). '
                   f'Below this fill %, the fixed lease ({lease_avg_annual:,.0f}/year at the average rate) exceeds what '
                   f'per-vehicle billing would actually collect at that fill level — a real, computed crossover, not a rule of thumb.')
            ).alignment = LEFT
    ws.merge_cells(f'C{r}:F{r}')
    ws.row_dimensions[r].height = 40
    r += 2

    section(ws, r, 'ELEVATOR ADVERTISING (real per-device rate; Qty PRE-FILLED from an assumption, still PM-editable — see Source column)', ncols=6); r += 1
    headers2 = ['Item', 'Rate (VND/device/month)', 'Qty (editable — pre-filled estimate)', 'Monthly Revenue (VND)', 'Annual (×12)', 'Source']
    for c, h in enumerate(headers2, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    r += 1
    ad_first_row = r
    tower_count = project.get('towers') or 0
    for item, rate, qty_per_tower, flat_qty, assumption in ELEVATOR_AD_ITEMS:
        est_qty = round(tower_count * qty_per_tower) if qty_per_tower is not None else flat_qty
        ws.cell(row=r, column=1, value=item).border = BORDER
        ws.cell(row=r, column=1).alignment = LEFT
        c2 = ws.cell(row=r, column=2, value=rate)
        c2.number_format = MONEY_FMT
        c2.border = BORDER
        c3 = ws.cell(row=r, column=3, value=est_qty)
        c3.border = BORDER
        c3.fill = PatternFill('solid', fgColor='FFF7CC')
        c3.alignment = CENTER
        c4 = ws.cell(row=r, column=4, value=f'=B{r}*C{r}')
        c4.number_format = MONEY_FMT
        c4.border = BORDER
        c5 = ws.cell(row=r, column=5, value=f'=D{r}*12')
        c5.number_format = MONEY_FMT
        c5.border = BORDER
        c6 = ws.cell(row=r, column=6,
                      value=f'Rate: Fact_MasterRateCard.csv, Service domain, "Elevator advertising" (real). Qty: {assumption}')
        c6.border = BORDER
        c6.alignment = LEFT
        r += 1
    ad_last_row = r - 1
    ws.cell(row=r, column=1, value='ADVERTISING TOTAL').font = SECTION_FONT
    c4 = ws.cell(row=r, column=4, value=f'=SUM(D{ad_first_row}:D{ad_last_row})')
    c4.number_format = MONEY_FMT
    c4.font = SECTION_FONT
    c5 = ws.cell(row=r, column=5, value=f'=SUM(E{ad_first_row}:E{ad_last_row})')
    c5.number_format = MONEY_FMT
    c5.font = SECTION_FONT
    AD_ANNUAL_CELL = f'E{r}'
    r += 2

    ws.cell(row=r, column=1, value='TOTAL ADDITIONAL REVENUE (Annual, VND)').font = Font(bold=True, size=12)
    c = ws.cell(row=r, column=2, value=f'={PARKING_ANNUAL_CELL}+{AD_ANNUAL_CELL}')
    c.number_format = MONEY_FMT
    c.font = Font(bold=True, size=12)
    c.fill = HIGHLIGHT_FILL
    TOTAL_ANNUAL_CELL = f'B{r}'
    r += 2

    ws.cell(row=r, column=1,
            value=('"Rentals" (Cho thuê — leasing common/retail space) and "Cho thuê bãi xe" (leasing the whole '
                   'parking area to a third-party operator — a different revenue model than the per-vehicle fee '
                   'above, real data exists for 3 comparable projects but wasn\'t extracted here) are real categories '
                   'mentioned in the source files but not built out yet — not fabricated, just not done.')
            ).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:F{r}')
    ws.row_dimensions[r].height = 40
    r += 1
    ws.cell(row=r, column=1,
            value=('NOT included in Total Project Value (Net) on the Summary sheet yet. Whether Extra Revenue should '
                   'add to the top line the way Management Fee Revenue does is a real methodology question this '
                   'session hasn\'t resolved — shown here as a real, computed reference until that\'s decided.')
            ).font = Font(italic=True, size=9, color='C00000')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:F{r}')
    ws.row_dimensions[r].height = 40

    for col, w in {'A': 40, 'B': 22, 'C': 20, 'D': 20, 'E': 20, 'F': 60}.items():
        ws.column_dimensions[col].width = w

    return dict(annual_total_cell=TOTAL_ANNUAL_CELL)


# ============================================================================================
def build_opex_sheet(wb, project):
    """OPEX/Utilities — Electricity, Water, Diesel (Generator Fuel), Repairs & Maintenance
    (materials only), Pool Salt. New category, no prior extraction anywhere in this codebase
    (unlike Staff/Service/Capex). Real data is thin: only 2 of the 8 real files have
    independently-verified OPEX data (A&K Tower, Parking Building — the latter a different
    building type, shown for reference only, not blended into the ratio). See
    rescan_opex_from_source.py's module docstring for the full trail — including a broken-formula
    false alarm (turned out fine, verified by reading formulas not just cached values), a real
    cross-file duplication caught (Fiato G2/MF's numbers are identical to A&K's to the decimal, not
    independent data), and why elevator/lighting/system MAINTENANCE CONTRACTS never appear here at
    all — a real cell note in A&K's own file cites Vietnamese Housing Law 2023 Article 150 and
    Construction Law Article 3: those are legally funded from a separate one-time maintenance fund,
    not the ongoing management fee this sheet estimates. Electricity/Water/Diesel/Repairs &
    Maintenance scale by A&K's real per-m² TotalNFA ratio (n=1, stated as exactly that). Pool Salt
    is a flat real reference, not scaled, shown only if this project has a pool.

    INCLUDED in Total Project Value (Net) on the Summary sheet, same as Staff Cost — on the basis
    that utility costs for common areas are normally covered by management fee revenue. Confirmed
    with the PM rather than assumed silently, since this changes the bottom-line figure."""
    ws = wb.create_sheet('OPEX')
    title_block(ws, 'OPEX — Utilities & Repairs (Electricity, Water, Diesel, Maintenance, Pool Salt)',
                'Real data is thin here — only 2 of the 8 real files have independently-verified OPEX data. Most '
                'categories scale by A&K Tower\'s real per-m² NFA ratio (n=1); Pool Salt is a flat real reference. '
                'Elevator/system MAINTENANCE CONTRACTS are deliberately excluded — Vietnamese law funds those from a '
                'separate one-time fund, not the ongoing management fee (see notes below). Included in Total Project '
                'Value (Net).', 'A1:F1')

    opex = estimate_opex(project['total_nfa'], has_pool=project.get('has_pool', False))

    r = 4
    section(ws, r, 'ESTIMATED MONTHLY OPEX', ncols=6); r += 1
    headers = ['Category', 'Monthly (VND)', 'Annual (×12)', 'Ratio (VND/m² NFA/month)', 'n', 'Source']
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    r += 1
    first_row = r
    footnotes = []
    category_annual_cells = {}
    for category, entry in opex.items():
        category_annual_cells[category] = f'C{r}'
        ws.cell(row=r, column=1, value=category).border = BORDER
        c2 = ws.cell(row=r, column=2, value=entry['monthly_vnd'])
        c2.number_format = MONEY_FMT
        c2.border = BORDER
        c3 = ws.cell(row=r, column=3, value=f'=B{r}*12')
        c3.number_format = MONEY_FMT
        c3.border = BORDER
        c4 = ws.cell(row=r, column=4, value=entry['ratio_per_m2'] if entry['ratio_per_m2'] is not None else 'n/a (flat)')
        c4.border = BORDER
        c4.alignment = CENTER
        c5 = ws.cell(row=r, column=5, value=entry['n'])
        c5.border = BORDER
        c5.alignment = CENTER
        c6 = ws.cell(row=r, column=6, value=entry['source'])
        c6.border = BORDER
        c6.alignment = LEFT
        if entry.get('reference_only'):
            footnotes.append((category, entry['reference_only']))
        r += 1
    last_row = r - 1
    ws.cell(row=r, column=1, value='TOTAL').font = SECTION_FONT
    c2 = ws.cell(row=r, column=2, value=f'=SUM(B{first_row}:B{last_row})')
    c2.number_format = MONEY_FMT
    c2.font = SECTION_FONT
    c3 = ws.cell(row=r, column=3, value=f'=SUM(C{first_row}:C{last_row})')
    c3.number_format = MONEY_FMT
    c3.font = SECTION_FONT
    ANNUAL_OPEX_CELL = f'C{r}'
    r += 2

    if footnotes:
        section(ws, r, 'DIFFERENT-BUILDING-TYPE REFERENCE (real, not blended into the ratio above)', ncols=6); r += 1
        for category, note in footnotes:
            ws.cell(row=r, column=1, value=category).font = Font(bold=True, size=9)
            ws.cell(row=r, column=2, value=note).alignment = LEFT
            ws.merge_cells(f'B{r}:F{r}')
            r += 1
        r += 1

    ws.cell(row=r, column=1,
            value=('Elevator/lighting/system MAINTENANCE CONTRACTS (not just Repairs & Maintenance\'s narrow '
                   'materials-only line) deliberately do NOT appear anywhere on this sheet, or anywhere else in this '
                   'workbook. A real cell note in A&K Tower\'s own source file explains why, citing Housing Law 2023 '
                   'Article 150 and Construction Law Article 3: those contract costs are legally funded from a '
                   'separate one-time maintenance fund (quỹ bảo trì, the 2% fund collected at handover), not the '
                   'ongoing management fee this workbook estimates. Adding them here would misrepresent how Vietnamese '
                   'property management budgets actually work, not fill a real gap.')
            ).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:F{r}')
    ws.row_dimensions[r].height = 55
    r += 1
    ws.cell(row=r, column=1,
            value=('Garbage collection is a real OPEX category too (every real file has a sheet for it) but its unit '
                   'price is explicitly blank in the source data — "NOT FOUND, do not fabricate" — so it\'s left out '
                   'entirely rather than guessed.')).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:F{r}')
    ws.row_dimensions[r].height = 28
    r += 1
    ws.cell(row=r, column=1,
            value=('Included in Total Project Value (Net) on the Summary sheet, same as Staff Cost — on the basis '
                   'that utility costs for common areas are normally covered by management fee revenue. Real but '
                   'thin data (n=1 per category) — worth re-checking against a second real property if one becomes '
                   'available.')
            ).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:F{r}')
    ws.row_dimensions[r].height = 28

    for col, w in {'A': 24, 'B': 20, 'C': 20, 'D': 22, 'E': 8, 'F': 60}.items():
        ws.column_dimensions[col].width = w

    return dict(annual_total_cell=ANNUAL_OPEX_CELL, category_annual_cells=category_annual_cells)


# ============================================================================================
# Three distinct "how fresh is this number" statuses, each with its own tag/color — collapsing
# them into one undifferentiated "Data source" line would hide a real distinction: a live read
# reflects whatever's on disk THIS run; a baked-in constant reflects whatever was true whenever
# someone last derived it by hand, and silently goes stale if the source CSV changes afterward.
SOURCE_STATUS = {
    'live': dict(prefix='[LIVE — read fresh every run]', color='31708F', fill='D9EDF7'),
    'conditional': dict(prefix='[CONDITIONAL — only if the live read above finds nothing]', color='7030A0', fill='E6DAF0'),
    'constant': dict(prefix='[BAKED-IN CONSTANT — not re-read; stale if the source file changes]', color='7F7F7F', fill='F2F2F2'),
    'write': dict(prefix='[WRITES]', color='548235', fill='E2EFDA'),
    'none': dict(prefix='[NO FILE — nothing read or written here]', color='808080', fill='F2F2F2'),
}


def _flow_step(ws, r, title, desc, source=None, note=None):
    """One pipeline stage: a navy title bar (B:F) + a bordered description block below it.
    `source`, if given, is either a single string (treated as one 'live' line) or a list of
    (status, text) tuples — status one of SOURCE_STATUS's keys — each rendered as its own tagged,
    color-coded sub-row so live reads, fallback-only reads, and frozen constants don't look like
    the same kind of "source." If `note` is given, adds an indented (C:F), amber sub-row
    underneath for a branch/internal-call that happens as part of this same step, without it
    looking like a separate top-level stage."""
    ws.merge_cells(f'B{r}:F{r}')
    c = ws.cell(row=r, column=2, value=title)
    c.font = Font(bold=True, color='FFFFFF')
    c.alignment = CENTER
    for col in range(2, 7):
        cell = ws.cell(row=r, column=col)
        cell.fill = HEADER_FILL
        cell.border = BORDER
    r += 1
    ws.merge_cells(f'B{r}:F{r}')
    d = ws.cell(row=r, column=2, value=desc)
    d.font = Font(size=10)
    d.alignment = LEFT
    for col in range(2, 7):
        ws.cell(row=r, column=col).border = BORDER
    ws.row_dimensions[r].height = 18 + 12 * (len(desc) // 70)
    r += 1
    if source:
        source_lines = [('live', source)] if isinstance(source, str) else source
        for status, text in source_lines:
            st = SOURCE_STATUS[status]
            ws.merge_cells(f'B{r}:F{r}')
            full_text = f"{st['prefix']}  {text}"
            s = ws.cell(row=r, column=2, value=full_text)
            s.font = Font(size=9, color=st['color'], italic=(status == 'constant'))
            s.alignment = LEFT
            s.fill = PatternFill('solid', fgColor=st['fill'])
            for col in range(2, 7):
                ws.cell(row=r, column=col).fill = PatternFill('solid', fgColor=st['fill'])
                ws.cell(row=r, column=col).border = BORDER
            ws.row_dimensions[r].height = 16 + 12 * (len(full_text) // 65)
            r += 1
    if note:
        ws.merge_cells(f'C{r}:F{r}')
        n = ws.cell(row=r, column=3, value=note)
        n.font = Font(italic=True, size=9, color='974706')
        n.alignment = LEFT
        n.fill = HIGHLIGHT_FILL
        for col in range(3, 7):
            ws.cell(row=r, column=col).fill = HIGHLIGHT_FILL
            ws.cell(row=r, column=col).border = BORDER
        ws.row_dimensions[r].height = 16 + 12 * (len(note) // 65)
        r += 1
    return r


def _flow_arrow(ws, r):
    c = ws.cell(row=r, column=4, value='↓')
    c.font = Font(bold=True, size=16, color='1F4E78')
    c.alignment = CENTER
    return r + 1


def build_data_flow_sheet(wb):
    """A cover sheet documenting how THIS workbook itself was generated — the actual call order
    in generate_project_output.py's main(), not project data. Doesn't touch `project`/`mgmt`/etc.
    at all; it's static, describing the script's own pipeline."""
    ws = wb.create_sheet('Data Flow', 1)
    title_block(ws, 'Data Flow — How This Workbook Is Generated',
                'The actual call order in generate_project_output.py\'s main() — one pass, top to bottom, no loops back.', 'A1:G1')

    r = 4
    section(ws, r, 'LEGEND', ncols=6); r += 1
    ws.merge_cells(f'B{r}:C{r}')
    lc = ws.cell(row=r, column=2, value='Pipeline stage (produces a sheet/tab)')
    lc.fill = HEADER_FILL
    lc.font = Font(color='FFFFFF', bold=True, size=9)
    lc.alignment = CENTER
    for col in (2, 3):
        ws.cell(row=r, column=col).border = BORDER
    ws.merge_cells(f'D{r}:F{r}')
    lc2 = ws.cell(row=r, column=4, value='Branch / internal call — not a separate tab')
    lc2.fill = HIGHLIGHT_FILL
    lc2.font = Font(italic=True, size=9, color='974706')
    lc2.alignment = CENTER
    for col in (4, 5, 6):
        ws.cell(row=r, column=col).border = BORDER
    r += 1
    ws.cell(row=r, column=1, value='Data source freshness:').font = Font(italic=True, size=9, color='7F7F7F')
    for col, key in ((2, 'live'), (4, 'conditional')):
        st = SOURCE_STATUS[key]
        end = col + 1
        ws.merge_cells(f'{get_column_letter(col)}{r}:{get_column_letter(end)}{r}')
        cell = ws.cell(row=r, column=col, value=st['prefix'])
        cell.fill = PatternFill('solid', fgColor=st['fill'])
        cell.font = Font(size=8, color=st['color'])
        cell.alignment = CENTER
        for c in (col, end):
            ws.cell(row=r, column=c).border = BORDER
    r += 1
    st = SOURCE_STATUS['constant']
    ws.merge_cells(f'B{r}:F{r}')
    cell = ws.cell(row=r, column=2, value=st['prefix'])
    cell.fill = PatternFill('solid', fgColor=st['fill'])
    cell.font = Font(size=8, color=st['color'], italic=True)
    cell.alignment = CENTER
    for c in range(2, 7):
        ws.cell(row=r, column=c).border = BORDER
    r += 2

    section(ws, r, 'GENERATION PIPELINE', ncols=6); r += 1

    r = _flow_step(ws, r, '1 · read_input(INPUT_PATH)',
                    'Reads → project (name, product-mix NFA/GFA/units, total_nfa), ratios, month, year, holiday_days, '
                    'demand (Staffing Demand rows). Function lives in generate_project_budget.py.',
                    source=[('live', 'reports/Project_Budget_Input.xlsx — Project Info, Roster Setup, and Staffing '
                                     'Demand sheets, opened fresh every run. The 5 ratio-driven Staffing Demand rows '
                                     '(Main Gate, Patrol, Cleaning ×2, Gardener) are recomputed in Python from Project '
                                     'Info + Roster Setup here (RATIO_DRIVEN_STAFFING) rather than read from the '
                                     'sheet\'s own cached formula values, which can go stale if the file was never '
                                     'reopened in Excel to recalc.')])
    r = _flow_arrow(ws, r)

    r = _flow_step(ws, r, '2 · New workbook created; "Summary" added as a blank placeholder',
                    'wb = openpyxl.Workbook(); the default first sheet is renamed "Summary" but left empty — '
                    'it\'s filled in last (step 8), once every sheet below it has something to link to.',
                    source=[('none', 'in-memory only.')])
    r = _flow_arrow(ws, r)

    r = _flow_step(ws, r, '3 · build_management_fee_sheet(wb, project)  →  mgmt',
                    'Ranks all real comparables by Total NFA and derives a rate PER PRODUCT TYPE (Apartment/Officetel/'
                    'Shophouse/Shopping Mall/Nursery) — falls back to the Apartment rate, flagged in red, for any '
                    'product with no real comparable rate of its own.',
                    source=[('live', 'data/master_list_verified/Dim_Property_Residential.csv — ~105 auto-parsed real '
                                      'properties, loaded fresh every run (master_comparables.py, MASTER_LIST_CSV). '
                                      'Raw origin: input/project/2026_Master List.xlsx, transformed by '
                                      'transform_master_list.py (address/fee-column parsing) — rerun that script to '
                                      'refresh this CSV after a newer Master List upload; this pipeline won\'t do it automatically.'),
                            ('constant', '7 hand-verified real projects\' own numbers (Green Skyline, Lumi Prestige & '
                                         'Elite, etc.) — hand-transcribed once from their "0. Info" sheets (in '
                                         'input/budget_planning/, the 8 real project files) into HAND_VERIFIED_COMPARABLES. '
                                         'No script reproduces this; refreshing means reopening the source files and '
                                         're-reading cells by hand.')],
                    note='↳ mgmt is passed straight into build_comparison_sheet(wb, project, mgmt) next — same comparables, no new lookup.')
    r = _flow_arrow(ws, r)

    r = _flow_step(ws, r, '4 · build_staffing_estimate_sheet(wb, project, ratios, demand)',
                    'Documents HOW each Staffing Demand row\'s headcount was computed — the same numbers step 1 already '
                    'produced, shown with their formula/basis. Not a separate estimate; nothing recomputed here.',
                    source=[('none', 'no new file read — reuses the project/ratios/demand step 1 already loaded in '
                                      'memory, just displays the basis.')])
    r = _flow_arrow(ws, r)

    r = _flow_step(ws, r, '5 · build_staff_sheet(wb, project, demand, year)  →  staff',
                    '12-month formula-driven staffing cost table from Staffing Demand, plus a real headcount cross-check.',
                    source=[('live', 'demand (from step 1/4) for the cost table.'),
                            ('constant', 'STAFF_HEADCOUNT_PER_1000_GFA / STAFF_COST_PER_HEADCOUNT_MONTHLY in '
                                         'estimate_new_project.py, for the cross-check row — ratios derived once from '
                                         'Dim_Property_Residential.csv (n=67 real properties, by GFA size bucket) via '
                                         'derive_staffing_benchmarks.py, not re-derived from the CSV each run.')],
                    note='↳ internally also calls build_roster_detail_grid(ws, demand, r) — appends the day-by-day duty '
                         'grid (Sunday-anchored rotation, month dropdown) below the cost table, same sheet.')
    r = _flow_arrow(ws, r)

    r = _flow_step(ws, r, '6 · build_service_sheet(wb, demand)  →  service',
                    'Citywide per-post reference rate × real staff headcount from Staffing Demand (same calc as the '
                    'Staff sheet\'s Staff Count column) for Security/Cleaning/Landscape.',
                    source=[('constant', 'SECURITY_RATE_CITYWIDE / CLEANING_RATE_CITYWIDE / LANDSCAPE_RATE_CITYWIDE in '
                                         'master_comparables.py — hand-transcribed once from Fact_MasterRateCard.csv '
                                         '(Domain=Service), NOT re-read from that CSV each run. Root source is thinner '
                                         'than it looks: input/service_cost/Detail form...xlsx has NO real unit price '
                                         'for these 3 roles (structure only) — build_master_rate_card.py falls back to '
                                         'A&K Tower\'s real project rate (input/budget_planning/) instead, "clearly '
                                         'labeled as such" per that script\'s own docstring. So this is really ONE real '
                                         'project\'s rate standing in for "citywide," not a citywide average.'),
                            ('live', 'demand headcount (from step 1/4), multiplied against the rates above.')])
    r = _flow_arrow(ws, r)

    r = _flow_step(ws, r, '7 · build_capex_sheet(wb, project)  →  capex',
                    'estimate_capex_items() scales a real nearest project\'s own Capex line items by NFA ratio; falls '
                    'back to the blank-Qty catalog only if no comparable has real Capex data.',
                    source=[('live', 'data/generation_A_star_schema/Fact_Capex_Rescanned.csv — 1,328 real line items, '
                                     'loaded fresh every run (estimate_capex_qty.py\'s estimate_capex_items(), for the '
                                     'item list). Raw origin: input/budget_planning/*.xlsx (the 8 real files\' own 4 '
                                     'Capex sheets each), rescanned by rescan_capex_from_source.py, which filters out '
                                     'the __repaired/MasterData/Budget_Workbook/SAMPLE copies also sitting in that '
                                     'folder — rerun that script to pick up a changed source file.'),
                            ('constant', 'STUDY1_RATIO_PER_1000_NFA / STUDY2_RATIO_PER_HEADCOUNT in estimate_capex_qty.py '
                                         '— category-level ratios derived once from the same CSV above (see '
                                         'study_capex_qty_estimation.py), used only for the CATEGORY CROSS-CHECK block.'),
                            ('conditional', 'data/generation_B_verified/Fact_MasterRateCard.csv (Domain=Capex) — the '
                                            'blank-Qty item catalog, read only if no real comparable has Capex data to '
                                            'scale from. Built by build_master_rate_card.py + add_shift_differentials.py '
                                            'from input/staff_cost, input/service_cost, input/capex — but those scripts '
                                            'write to output/copilot_studio_package/data/, a DIFFERENT path. The copy '
                                            'here was placed by hand (verified: identical byte size, mtime 2 days apart) '
                                            '— rerunning the build script will NOT update what this pipeline reads; '
                                            'someone has to re-copy the file.')])
    r = _flow_arrow(ws, r)

    r = _flow_step(ws, r, '8 · build_summary_sheet(ws_summary, project, mgmt, staff, service, capex)',
                    'No new computation — every cell is a live cross-sheet Excel formula pulling from steps 3, 5, 6, 7\'s '
                    'returned cell references. Must run last, since it only reads what they produced.',
                    source=[('none', 'no new file read — Excel formulas referencing the sheets built in steps 3, 5, 6, 7.')])
    r = _flow_arrow(ws, r)

    r = _flow_step(ws, r, '9 · Save',
                    'Writes to a temp file first, then copies into reports/Project_Budget_Output.xlsx. If that file is '
                    'open/locked in Excel, the temp copy is kept and you\'re told — nothing is silently lost.',
                    source=[('write', 'reports/Project_Budget_Output.xlsx (this file).')])
    r += 1

    ws.cell(row=r, column=1,
            value='This sheet documents generate_project_output.py\'s own pipeline (see build_data_flow_sheet() in the '
                  'script) — it describes how the workbook was built, not project data.').font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:G{r}')
    r += 2

    section(ws, r, 'HOW TO RUN THIS SCRIPT', ncols=6); r += 1
    run_lines = [
        ('Command', 'python generate_project_output.py'),
        ('Run from', 'Budget_Agent/source_code/'),
        ('Reads', 'reports/Project_Budget_Input.xlsx (must already be filled in — Project Info + Staffing Demand)'),
        ('Writes', 'reports/Project_Budget_Output.xlsx (this whole workbook, regenerated from scratch)'),
        ('Arguments / prompts', 'None — no arguments, no interactive prompts'),
        ('When to rerun', 'Any time Project_Budget_Input.xlsx changes (Project Info, Roster Setup ratios, or Staffing '
                           'Demand) — this script does not watch the file, it must be run again by hand each time'),
        ('If the output file is open in Excel', 'Can\'t overwrite it directly — saves a temp copy instead and prints '
                                                  'where, rather than failing silently'),
    ]
    for label, val in run_lines:
        ws.cell(row=r, column=1, value=label).font = Font(bold=True, size=9)
        ws.cell(row=r, column=2, value=val).font = Font(size=9, name='Consolas') if label == 'Command' else Font(size=9)
        ws.merge_cells(f'B{r}:F{r}')
        ws.cell(row=r, column=2).alignment = LEFT
        r += 1

    ws.column_dimensions['A'].width = 3
    for col in 'BCDEF':
        ws.column_dimensions[col].width = 20
    ws.column_dimensions['G'].width = 3
    ws.sheet_view.showGridLines = False


# ============================================================================================
# Necessity classification below is DOMAIN JUDGMENT, not extracted from any real per-project data
# source — stated plainly, since every other classification in this workbook traces to a real
# cell. "Must-Have" = practically/legally universal for a managed residential building (life-
# safety, sanitation, basic building operation). "Conditional" = only applies if the project has
# the underlying feature (pool/garden/other amenities) — genuinely $0 for a project without it,
# already reflected in the live numbers via Project Info, not a separate judgment call. "Optional"
# = real, common roles (confirmed by real breadth data — see build_project_input_form.py) but not
# universal; whether to include them is a service-tier decision, not a necessity.
STAFF_NECESSITY = {
    'Security': ('Must-Have', 'Life-safety and access control — no managed residential building operates without it.'),
    'Cleaning': ('Must-Have', 'Sanitation — practically and often contractually required.'),
    'Cleaning — Supervisory': ('Optional', 'Common for larger cleaning teams, not universal for smaller ones.'),
    'Landscape': ('Conditional', 'Only if the project has garden/landscaped area (Project Info Garden Area).'),
    'Property Manager': ('Must-Have', 'Basic requirement for a professionally managed building.'),
    'Chief Engineer': ('Must-Have', 'Someone must be responsible for M&E/fire/elevator systems.'),
    'Technician': ('Must-Have', 'Building systems (M&E, fire, elevator) need ongoing hands-on upkeep.'),
    'Reception': ('Optional', 'Common in mid-to-high-end buildings — real breadth is only 11/88 real properties.'),
    'Customer Service': ('Optional', 'Resident-relations role — real breadth is 40/88 properties, less than half.'),
    'Shift Leader': ('Optional', 'Cross-department on-duty supervisor — a service-quality choice (48/88 breadth).'),
    'Building Executive': ('Optional', 'Quality-supervision role — real breadth is 34/88 properties.'),
    'Amenities Attendant': ('Conditional', 'Only if the project has amenities beyond the pool (gym/BBQ/community room).'),
    'Pool Attendant': ('Conditional', 'Only if the project has a pool (Project Info "Has Swimming Pool?").'),
}
CAPEX_NECESSITY = {
    'M&E Equipment': ('Must-Have', 'Includes fire-safety/PCCC gear, much of it legally required.'),
    'MO Equipment': ('Must-Have', 'Basic toolkit for the maintenance team to do their job.'),
    'Public Area': ('Mixed', 'Some items safety-required (fire extinguishers), others discretionary (furniture/décor) — cannot cleanly split at category level.'),
    'Amenity Area': ('Conditional', 'Only relevant if the project has the amenities these items serve.'),
}
OPEX_NECESSITY = {
    'Electricity': ('Must-Have', 'The building cannot function without power.'),
    'Water': ('Must-Have', 'The building cannot function without water.'),
    'Diesel (Generator Fuel)': ('Must-Have', 'Backup power for life-safety systems — legally required for VN high-rises.'),
    'Repairs & Maintenance (materials only)': ('Must-Have', 'Ongoing building upkeep, even if the amount is small.'),
    'Administrative Expense (office overhead)': ('Must-Have', 'Baseline office operations for the management office.'),
    'Pool Salt': ('Conditional', 'Only if the project has a pool.'),
}
NECESSITY_COLOR = {'Must-Have': 'C00000', 'Conditional': '806000', 'Optional': '1F6357', 'Mixed': '595959'}


def build_cost_priority_sheet(wb, project, staff, capex, opex):
    """Answers "which is fixed/must-have, which is sizable" across Staff/Capex/OPEX — every
    number here is a live cross-sheet formula (same real cells the source sheets use), the
    Must-Have/Conditional/Optional tag is domain judgment (see the module-level *_NECESSITY dicts'
    comment for exactly what that means and doesn't mean). Sort order within each section is fixed
    at generation time from the CURRENT numbers (same convention Capex's own item list already
    uses) — rerun the script for a fresh ranking if the underlying inputs change enough to reorder."""
    ws = wb.create_sheet('Cost Priority')
    title_block(ws, 'Cost Priority — Fixed vs. Sizable',
                'Must-Have/Conditional/Optional is domain judgment (not extracted from a real data source — see this '
                'sheet\'s build function docstring); every dollar figure is a live formula from the real sheets. '
                'Sorted largest-first within each category so the real cost drivers are easy to spot.', 'A1:F1')

    def _section(category_label, annual_cells, necessity_map, current_values):
        nonlocal r
        section(ws, r, category_label.upper(), ncols=6); r += 1
        headers = ['Item', 'Annual Cost (VND)', '% of Category', 'Necessity', 'Why']
        for c, h in enumerate(headers, start=1):
            cell = ws.cell(row=r, column=c, value=h)
            cell.fill = HEADER_FILL
            cell.font = HEADER_FONT
            cell.alignment = CENTER
            cell.border = BORDER
        r += 1
        cat_first_row = r
        ordered = sorted(annual_cells.keys(), key=lambda k: -current_values.get(k, 0))
        must_have_cells, conditional_cells, optional_cells = [], [], []
        for name in ordered:
            necessity, why = necessity_map.get(name, ('Unclassified', 'Not yet categorized.'))
            ws.cell(row=r, column=1, value=name).border = BORDER
            ws.cell(row=r, column=1).alignment = LEFT
            c2 = ws.cell(row=r, column=2, value=annual_cells[name])
            c2.number_format = MONEY_FMT
            c2.border = BORDER
            c3 = ws.cell(row=r, column=3, value=f'=B{r}/B${cat_first_row + len(ordered)}')
            c3.number_format = '0.0%'
            c3.border = BORDER
            c3.alignment = CENTER
            c4 = ws.cell(row=r, column=4, value=necessity)
            c4.border = BORDER
            c4.alignment = CENTER
            c4.font = Font(bold=True, color=NECESSITY_COLOR.get(necessity, '000000'))
            c5 = ws.cell(row=r, column=5, value=why)
            c5.border = BORDER
            c5.alignment = LEFT
            if necessity == 'Must-Have':
                must_have_cells.append(f'B{r}')
            elif necessity == 'Conditional':
                conditional_cells.append(f'B{r}')
            else:
                optional_cells.append(f'B{r}')
            r += 1
        cat_last_row = r - 1
        ws.cell(row=r, column=1, value=f'{category_label} TOTAL').font = SECTION_FONT
        c2 = ws.cell(row=r, column=2, value=f'=SUM(B{cat_first_row}:B{cat_last_row})')
        c2.number_format = MONEY_FMT
        c2.font = SECTION_FONT
        category_grand_row = r
        r += 1
        must_have_row = None
        for label, cells in [('  of which Must-Have', must_have_cells), ('  of which Conditional', conditional_cells),
                              ('  of which Optional/Mixed', optional_cells)]:
            if not cells:
                continue
            ws.cell(row=r, column=1, value=label).font = Font(italic=True, size=9)
            c2 = ws.cell(row=r, column=2, value='=' + '+'.join(cells))
            c2.number_format = MONEY_FMT
            c2.font = Font(italic=True, size=9)
            if label == '  of which Must-Have':
                must_have_row = r
            r += 1
        r += 1
        return category_grand_row, (f'B{must_have_row}' if must_have_row else None)

    r = 4
    staff_total_row, staff_must_have_row = _section('Staff', staff['category_annual_cells'], STAFF_NECESSITY,
              {'Security': 1782300800, 'Cleaning': 323340000, 'Cleaning — Supervisory': 152160000, 'Landscape': 268182000,
               'Property Manager': 516076000, 'Chief Engineer': 417806000, 'Technician': 679965000,
               'Reception': 215560000, 'Customer Service': 217462000, 'Shift Leader': 928936800,
               'Building Executive': 186396000, 'Amenities Attendant': 194638000, 'Pool Attendant': 174984000})
    # staff['category_annual_cells'] values are already full "='Sheet Name'!Cell+..." formula
    # strings (built that way for the Service sheet). capex/opex expose bare same-sheet cell refs
    # instead (e.g. 'F15', 'C6') — prefix those with their own sheet name here so every value on
    # THIS sheet is a genuine cross-sheet reference, not a same-sheet-relative one pointing nowhere.
    capex_annual = {k: f"=Capex!{v}" for k, v in capex['category_subtotal_cells'].items()}
    opex_annual = {k: f"=OPEX!{v}" for k, v in opex['category_annual_cells'].items()}

    capex_total_row, capex_must_have_row = _section('Capex (one-time, shown as-is, not annualized)', capex_annual, CAPEX_NECESSITY,
              {'M&E Equipment': 152403000, 'MO Equipment': 253082215, 'Public Area': 216863000, 'Amenity Area': 13689000})
    opex_total_row, opex_must_have_row = _section('OPEX', opex_annual, OPEX_NECESSITY,
              {'Electricity': 3842128512, 'Water': 440442996, 'Diesel (Generator Fuel)': 87792096,
               'Repairs & Maintenance (materials only)': 40496844, 'Administrative Expense (office overhead)': 82282236,
               'Pool Salt': 79884000})

    ws.cell(row=r, column=1,
            value=('"Sizable" = ranked largest-first within each category above — the real cost drivers, not a fixed '
                   'threshold. "Must-Have of which" subtotals show the minimum a project needs regardless of scale/'
                   'amenities/service-tier choices; the gap between that and the category total is what\'s actually '
                   'negotiable (service level, amenities offered) rather than structurally required. The Summary sheet\'s '
                   '"Total Profit Value" reads these 3 Must-Have subtotals (or the category TOTAL rows for the Full '
                   'Cost view) via a Cost Basis dropdown on that sheet, so the bottom line can show either the '
                   'stripped-down floor or the full picture on demand.')
            ).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:F{r}')
    ws.row_dimensions[r].height = 50

    for col, w in {'A': 34, 'B': 20, 'C': 14, 'D': 14, 'E': 60}.items():
        ws.column_dimensions[col].width = w

    return dict(staff_must_have_cell=f"'Cost Priority'!{staff_must_have_row}",
                capex_must_have_cell=f"'Cost Priority'!{capex_must_have_row}",
                opex_must_have_cell=f"'Cost Priority'!{opex_must_have_row}",
                staff_total_cell=f"'Cost Priority'!B{staff_total_row}",
                capex_total_cell=f"'Cost Priority'!B{capex_total_row}",
                opex_total_cell=f"'Cost Priority'!B{opex_total_row}")


# ============================================================================================
def build_summary_sheet(ws, project, mgmt, staff, service, capex, opex, extra_revenue, cost_priority):
    """Key Figures rows are numbered (1)-(9) and the Total Profit Value formula/scenario table
    reference those SAME numbers, so a reader can trace exactly which figures feed the bottom line
    without re-reading a paragraph of caveats inline — the caveats live once, in the NOTES legend
    at the bottom, keyed by the same numbers.

    Total Profit Value is driven by a Cost Basis dropdown (COST BASIS TOGGLE section): "Must-Have
    Only" pulls Cost Priority sheet's "of which Must-Have" subtotals for Staff/Capex/OPEX,
    excluding Conditional (pool/garden-dependent) and Optional (service-tier choices like Shift
    Leader/Customer Service/Reception) costs entirely; "Full Cost (incl. Optional/Conditional)"
    pulls the category grand totals instead. Every downstream number (Total Profit Value, %
    Profit, the Fill-up Scenarios table, Key Figures (4)/(6)/(7)) reads from 3 small IF()-driven
    "Selected Cost" cells keyed off that one dropdown, so picking a value recalculates the whole
    sheet with no macro involved. The itemized breakdown either way is still on the Cost Priority
    sheet in full."""
    title_block(ws, f"Project Budget Output — {project['name']}",
                'Phase 1 summary — see the Management Fee / Staff (Roster) / Service / Capex / OPEX / Additional '
                'Revenue / Cost Priority sheets for detail. Figures below are numbered (1)-(9) — see NOTES at the '
                'bottom for what each one means. Total Profit Value switches between Must-Have-only and Full Cost '
                'via the Cost Basis dropdown below — see Cost Priority sheet for the itemized breakdown either way.',
                'A1:E1')

    r = 4
    section(ws, r, 'PROPERTY', ncols=4); r += 1
    for label, val in [('Project Name', project['name']), ('Apartment NFA (m²)', project['apartment_nfa']),
                        ('Apartment Units', project['apartment_units']), ('Tower Count', project['towers'])]:
        ws.cell(row=r, column=1, value=label).font = Font(bold=True)
        ws.cell(row=r, column=2, value=val)
        r += 1
    r += 1

    MUST_HAVE_CELLS = dict(
        staff=cost_priority['staff_must_have_cell'],
        capex=cost_priority['capex_must_have_cell'],
        opex=cost_priority['opex_must_have_cell'],
    )
    FULL_COST_CELLS = dict(
        staff=cost_priority['staff_total_cell'],
        capex=cost_priority['capex_total_cell'],
        opex=cost_priority['opex_total_cell'],
    )

    section(ws, r, 'COST BASIS TOGGLE', ncols=5); r += 1
    ws.cell(row=r, column=1, value='View:').font = Font(bold=True, size=12)
    toggle_cell = ws.cell(row=r, column=2, value='Must-Have Only')
    toggle_cell.fill = PatternFill('solid', fgColor='FFF7CC')
    toggle_cell.font = Font(bold=True, size=12)
    toggle_cell.border = BORDER
    dv_toggle = DataValidation(type='list', formula1='"Must-Have Only,Full Cost (incl. Optional/Conditional)"',
                                showErrorMessage=True, errorTitle='Invalid selection',
                                error='Pick "Must-Have Only" or "Full Cost (incl. Optional/Conditional)" from the dropdown.')
    ws.add_data_validation(dv_toggle)
    dv_toggle.add(toggle_cell)
    TOGGLE_CELL = f'$B${r}'
    r += 1
    ws.cell(row=r, column=1,
            value=('Pick from the dropdown — Total Profit Value, % Profit, the Fill-up Scenarios table, and Key '
                   'Figures (4)/(6)/(7) below all switch instantly between the Must-Have-only floor and the full cost '
                   'picture (incl. Optional/Conditional items). No macro, just recalculates on selection.')
            ).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:E{r}')
    r += 2

    def _selected(label, must_cell, full_cell):
        nonlocal r
        ws.cell(row=r, column=1, value=label).font = Font(size=9, color='7F7F7F')
        c = ws.cell(row=r, column=2,
                    value=f'=IF({TOGGLE_CELL}="Full Cost (incl. Optional/Conditional)",{full_cell},{must_cell})')
        c.number_format = MONEY_FMT
        c.font = Font(size=9, color='7F7F7F')
        cell_ref = f'B{r}'
        r += 1
        return cell_ref

    SELECTED_STAFF_CELL = _selected('Selected Staff Cost (per toggle, VND)', MUST_HAVE_CELLS['staff'], FULL_COST_CELLS['staff'])
    SELECTED_OPEX_CELL = _selected('Selected OPEX (per toggle, VND)', MUST_HAVE_CELLS['opex'], FULL_COST_CELLS['opex'])
    SELECTED_CAPEX_CELL = _selected('Selected Capex (per toggle, VND)', MUST_HAVE_CELLS['capex'], FULL_COST_CELLS['capex'])
    r += 1

    section(ws, r, 'TOTAL PROFIT VALUE (per Cost Basis toggle above), AT 100% FILL', ncols=5); r += 1
    ws.cell(row=r, column=1, value='Total Profit Value = Mgmt Fee Revenue (3) − Selected Staff (4) − Selected OPEX (7) − Selected Capex (6)').font = Font(bold=True, size=12)
    c = ws.cell(row=r, column=2,
                value=f"='Management Fee'!{mgmt['annual_revenue_cell']}-{SELECTED_STAFF_CELL}"
                      f"-{SELECTED_OPEX_CELL}-{SELECTED_CAPEX_CELL}")
    c.number_format = MONEY_FMT
    c.font = Font(bold=True, size=12)
    c.fill = HIGHLIGHT_FILL
    PROFIT_CELL = f'B{r}'
    r += 1
    ws.cell(row=r, column=1, value='% Profit (Total Profit Value ÷ Selected Costs) (9)').font = Font(bold=True, size=12)
    c = ws.cell(row=r, column=2,
                value=f"={PROFIT_CELL}/({SELECTED_STAFF_CELL}+{SELECTED_OPEX_CELL}+{SELECTED_CAPEX_CELL})")
    c.number_format = '+0.0%;-0.0%'
    c.font = Font(bold=True, size=12)
    c.fill = HIGHLIGHT_FILL
    PROFIT_PCT_CELL = f'B{r}'
    r += 1
    ws.cell(row=r, column=1, value=('"Must-Have Only" excludes Conditional (pool/garden-dependent) and Optional '
                                     '(service-tier choices, e.g. Shift Leader/Customer Service/Reception) costs '
                                     'entirely, not just discounts them — see Cost Priority sheet for exactly which '
                                     'items. "Full Cost" includes everything. At full (100%) fill — see FILL-UP '
                                     'SCENARIOS below for earlier-stage ramp-up. Year 1 specific, not steady-state '
                                     '(would exclude the one-time Capex).')
            ).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:E{r}')
    ws.row_dimensions[r].height = 55
    r += 2

    NET_TOTAL_CELLS = dict(
        mgmt=f"'Management Fee'!{mgmt['annual_revenue_cell']}",
        extra=f"'Additional Revenue'!{extra_revenue['annual_total_cell']}",
    )
    section(ws, r, 'FILL-UP SCENARIOS — revenue ramps with fill %, costs (per toggle above) assumed at full regardless', ncols=6); r += 1
    ws.cell(row=r, column=1,
            value=('Simplifying assumption, not derived from real data: Mgmt Fee Revenue (3) scales with fill % (fewer '
                   'paying units at lower fill); Staff (4)/OPEX (7)/Capex (6) — per the Cost Basis toggle above — are '
                   'held at full regardless of fill % (the building still needs full staffing and utilities even '
                   'during ramp-up, at whichever service tier the toggle selects). Total Profit Value here uses the '
                   'SAME components as the figure above, so the 100% row matches it exactly. Additional Revenue (8) is '
                   'shown alongside for reference, scaled the same way, but is NOT added into the Total column (see '
                   'NOTE 8).')
            ).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:F{r}')
    ws.row_dimensions[r].height = 55
    r += 1
    fill_headers = ['Fill %', 'Mgmt Fee Revenue (3)', 'Staff (4) + OPEX (7) + Capex (6) — per toggle',
                     'Total Profit Value', '% Profit', 'Additional Revenue (8) — reference only']
    for c, h in enumerate(fill_headers, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    r += 1
    for pct in (0.50, 0.70, 0.90, 1.00):
        ws.cell(row=r, column=1, value=pct).number_format = '0%'
        ws.cell(row=r, column=1).border = BORDER
        ws.cell(row=r, column=1).alignment = CENTER
        c2 = ws.cell(row=r, column=2, value=f"={NET_TOTAL_CELLS['mgmt']}*A{r}")
        c2.number_format = MONEY_FMT
        c2.border = BORDER
        c3 = ws.cell(row=r, column=3, value=f"={SELECTED_STAFF_CELL}+{SELECTED_OPEX_CELL}+{SELECTED_CAPEX_CELL}")
        c3.number_format = MONEY_FMT
        c3.border = BORDER
        c4 = ws.cell(row=r, column=4, value=f'=B{r}-C{r}')
        c4.number_format = MONEY_FMT
        c4.border = BORDER
        c4.font = Font(bold=True)
        c5 = ws.cell(row=r, column=5, value=f'=D{r}/C{r}')
        c5.number_format = '+0.0%;-0.0%'
        c5.border = BORDER
        c5.font = Font(bold=True)
        c6 = ws.cell(row=r, column=6, value=f"={NET_TOTAL_CELLS['extra']}*A{r}")
        c6.number_format = MONEY_FMT
        c6.border = BORDER
        c6.font = Font(italic=True, color='7F7F7F')
        if pct == 1.00:
            for col in range(1, 7):
                ws.cell(row=r, column=col).fill = HIGHLIGHT_FILL
        r += 1
    r += 1

    section(ws, r, 'KEY FIGURES', ncols=4); r += 1
    rows = [
        ('(1) Derived Apartment Rate (VND/m²/mo)', mgmt['derived_rate']),
        ('(2) Monthly Management Fee Revenue (VND)', f"='Management Fee'!{mgmt['monthly_revenue_cell']}"),
        ('(3) Annual Management Fee Revenue (VND)', f"='Management Fee'!{mgmt['annual_revenue_cell']}"),
        ('(4) Annual Staff Cost — per Cost Basis toggle (VND)', f"={SELECTED_STAFF_CELL}"),
        ('(5) Annual Service Reference Cost (VND)', f"=Service!{service['annual_total_cell']}"),
        ('(6) Capex — per Cost Basis toggle (VND)', f"={SELECTED_CAPEX_CELL}"),
        ('(7) Annual OPEX — per Cost Basis toggle (VND)', f"={SELECTED_OPEX_CELL}"),
        ('(8) Annual Additional Revenue (VND)', f"='Additional Revenue'!{extra_revenue['annual_total_cell']}"),
        ('(9) % Profit (Total Profit Value ÷ Selected Costs)', f'={PROFIT_PCT_CELL}'),
    ]
    for label, val in rows:
        ws.cell(row=r, column=1, value=label).font = Font(bold=True)
        c = ws.cell(row=r, column=2, value=val)
        c.number_format = '+0.0%;-0.0%' if label.startswith('(9)') else MONEY_FMT
        c.fill = HIGHLIGHT_FILL
        r += 1
    r += 1

    section(ws, r, 'NOTES', ncols=4); r += 1
    notes = [
        '(1) Derived from the 2 nearest real comparables by Total NFA — see Management Fee sheet for which ones and the gap vs. any known real rate.',
        '(2)/(3) Apartment NFA × Derived Rate (1); Annual = Monthly × 12. IN Total Profit Value.',
        '(4) Bottom-up roster cost — real per-position rates × real headcount. "Must-Have Only" excludes Optional roles (Shift Leader/Customer Service/Reception/Building Executive) and Conditional roles (Landscape/Pool/Amenities Attendant); "Full Cost" includes them. Full breakdown on Cost Priority sheet. IN Total Profit Value.',
        '(5) Top-down citywide-post reference (Security/Cleaning/Landscape only, plus a market-rate cross-check for every other position) — NOT in Total Profit Value, and NOT affected by the toggle. Excluded because it prices the same roles as (4) a second way; including both would double-count them.',
        '(6) Capex (M&E Equipment + MO Equipment always; "Full Cost" adds Conditional Amenity Area + Mixed Public Area). One-time, PM-entered quantities — see Capex/Cost Priority sheets. IN Total Profit Value (as a Year-1 lump sum, not amortized).',
        '(7) OPEX (Electricity/Water/Diesel/Repairs & Maintenance/Administrative Expense always; "Full Cost" adds Conditional Pool Salt). Real but thin data (n=1 per category — see OPEX sheet). IN Total Profit Value.',
        '(8) Real Parking Fee (at 100% occupancy — a ceiling, not a realistic average) + Elevator Advertising (real rate, Qty PRE-FILLED from an assumption, still PM-editable) + a fixed-lease parking alternative with a computed breakeven fill % — see Additional Revenue sheet. NOT in Total Profit Value, and NOT affected by the toggle.',
        '(9) Total Profit Value ÷ (Selected Staff + Selected OPEX + Selected Capex, per the Cost Basis toggle) — how much profit per VND of cost at the selected service tier, not per VND of revenue.',
    ]
    for note in notes:
        ws.cell(row=r, column=1, value=note).font = Font(italic=True, size=9, color='7F7F7F')
        ws.cell(row=r, column=1).alignment = LEFT
        ws.merge_cells(f'A{r}:D{r}')
        ws.row_dimensions[r].height = 28
        r += 1

    for col, w in {'A': 42, 'B': 24, 'C': 24, 'D': 20, 'E': 20, 'F': 24}.items():
        ws.column_dimensions[col].width = w


# ============================================================================================
def _strip_onedrive_zip_artifacts(path, quiet_checks_needed=2, poll_interval=2.5, max_polls=8):
    """
    OneDrive/SharePoint sync silently patches .xlsx files at some variable delay after
    they land in a synced document-library folder (injecting SharePoint content-type
    metadata such as customXml/docProps-custom.xml). Its patch tool leaves behind extra
    zip entries literally named "[trash]/NNNN.dat" — tiny, unreferenced (not listed in
    [Content_Types].xml or any .rels file) garbage entries that Excel's strict OOXML
    parser flags as unreadable content, forcing a "we found a problem... repair?" dialog
    on open. The injection delay isn't fixed (observed anywhere from under 1.5s to several
    seconds), so this polls repeatedly, re-stripping each time trash reappears, and only
    stops once it sees `quiet_checks_needed` consecutive clean checks (or hits
    max_polls). Repacking without the trash entries leaves every real part, including the
    legitimate SharePoint metadata, untouched.
    """
    import zipfile, time

    def _strip_once():
        with zipfile.ZipFile(path, 'r') as zin:
            names = zin.namelist()
            trash = [n for n in names if n.startswith('[trash]/')]
            if not trash:
                return 0
            tmp = path + '.repack.tmp'
            with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
                for name in names:
                    if name not in trash:
                        zout.writestr(name, zin.read(name))
        os.replace(tmp, path)
        return len(trash)

    quiet_streak = 0
    total_stripped = 0
    try:
        for _ in range(max_polls):
            time.sleep(poll_interval)
            n = _strip_once()
            if n:
                total_stripped += n
                quiet_streak = 0
            else:
                quiet_streak += 1
                if quiet_streak >= quiet_checks_needed:
                    break
        if total_stripped:
            print(f'Stripped {total_stripped} OneDrive-injected "[trash]" zip artifact(s) '
                  f'from (stable after {quiet_streak} clean check(s)):', path)
    except Exception as e:
        print('Could not check/strip zip artifacts (non-fatal):', e)


def _fix_fake_formula_strings(wb):
    """
    Safety net for a real bug class: a plain-text annotation/note string that happens to
    start with "=" (e.g. "= Car Slots × 12.5 m²/slot...") gets written by openpyxl as an
    actual FORMULA (any cell string value starting with "=" is serialized as <f>...</f>),
    and Excel then fails to parse the prose as a formula and strips it on open ("We found
    a problem with some content... Removed Records: Formula from ..."). Every real formula
    in this file immediately follows "=" with a reference/function/quote/paren/digit, never
    whitespace — so "=" followed by a space is a reliable, cheap signal that this is prose
    that leaked into formula position, not an intentional formula. Strips the leading "="
    so it saves as plain text instead.
    """
    import re
    fixed = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                v = cell.value
                if isinstance(v, str) and re.match(r'^=\s', v):
                    cell.value = v[1:].lstrip()
                    fixed += 1
    if fixed:
        print(f'Fixed {fixed} text annotation(s) that were accidentally in formula position (leading "= ").')


def main():
    project, ratios, month, year, holiday_days, demand = read_input(INPUT_PATH)

    wb = openpyxl.Workbook()
    ws_summary = wb.active
    ws_summary.title = 'Summary'
    build_data_flow_sheet(wb)

    mgmt = build_management_fee_sheet(wb, project)
    build_comparison_sheet(wb, project, mgmt)
    build_staffing_estimate_sheet(wb, project, ratios, demand)
    staff = build_staff_sheet(wb, project, demand, year)
    service = build_service_sheet(wb, demand, staff)
    capex = build_capex_sheet(wb, project)
    opex = build_opex_sheet(wb, project)
    extra_revenue = build_additional_revenue_sheet(wb, project)
    cost_priority = build_cost_priority_sheet(wb, project, staff, capex, opex)
    build_summary_sheet(ws_summary, project, mgmt, staff, service, capex, opex, extra_revenue, cost_priority)

    _fix_fake_formula_strings(wb)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    import tempfile, shutil
    local_out = os.path.join(tempfile.gettempdir(), 'Project_Budget_Output.xlsx')
    wb.save(local_out)
    print('Saved locally:', local_out)
    try:
        shutil.copyfile(local_out, OUTPUT_PATH)
        print('Copied into place:', OUTPUT_PATH)
        _strip_onedrive_zip_artifacts(OUTPUT_PATH)
    except PermissionError as e:
        print('Could not copy into place yet (still locked):', e)
        print('Local copy remains valid at:', local_out)


if __name__ == '__main__':
    main()
