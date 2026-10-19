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
from openpyxl.utils import get_column_letter, column_index_from_string
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule

from generate_project_budget import (read_input, INPUT_PATH, PRODUCT_ROWS, existing_result,
                                     utilities_result, template_vat_inclusive, period_workdays,
                                     _new_prospect_duty, _a11_code_of, _a1_group_of, _is_outsourced)
import budget_period
import vn_holidays
import existing_utilities
import existing_staffing
import operating_inputs
from master_comparables import (
    MASTER_COMPARABLES, SECURITY_RATE_CITYWIDE, CLEANING_RATE_CITYWIDE, LANDSCAPE_RATE_CITYWIDE,
    RATE_CARD_SOURCE, resolve_product_rates,
)
from estimate_capex_qty import estimate_capex_qty, estimate_capex_items
from estimate_new_project import estimate_staff_headcount
from estimate_opex import estimate_opex, RATIO_CATEGORIES as OPEX_RATIO_CATEGORIES
import labor_law_params
# The month-by-month fill-up ramp now lives in fill_curve.py, shared with generate_project_budget.py
# so the client deliverable and this analysis ramp identically. Same curve as before — moved, not
# changed (0% at month 0, linear to 0.50/0.70/0.90/1.00 at each year end).
from fill_curve import (MONTH_ANCHORS as _MONTH_ANCHORS, monthly_fill_path as _monthly_fill_path,
                        STABLE_FILL as _STABLE_FILL)

SOURCE_DIR = os.path.dirname(__file__)
BUDGET_AGENT = os.path.abspath(os.path.join(SOURCE_DIR, '..'))
RATE_CARD_CSV = os.path.join(BUDGET_AGENT, 'data', 'generation_B_verified', 'Fact_MasterRateCard.csv')
OUTPUT_PATH = os.path.join(BUDGET_AGENT, 'reports', 'Project_Budget_Output.xlsx')

MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
NIGHT_SHIFT_CODES = {'D', '24H'}  # from the Shift Types reference — Night Shift? = Yes
NIGHT_DIFFERENTIAL = 1.3  # +30% night-shift premium, same factor build_staff_sheet applies

# Real, from data/generation_A_star_schema/Fact_StaffCost.csv (SI_HI_Company / Unemployment ÷
# GrossSalary): exactly 20.5% and 1.0% respectively across every one of the 911 real rows with
# nonzero insurance data (verified — not an average of a spread). Matches Vietnamese law's employer
# Social+Health Insurance (20.5%) and Unemployment Insurance (1%) contribution rates on top of gross
# salary — required by input/logic/EXENSIVE LOGIC.xlsx's own EMH2 formula ("Sum(Headcount x Salary
# x 12) + Employer insurance contribution"), never wired into this sheet before. A handful of real
# rows show a lower ratio (as low as 15.99%) — Vietnamese law caps the SI/HI contribution BASE at a
# multiple of the regional statutory salary, so very high individual salaries pay a lower effective
# % of their actual gross; that cap isn't modeled here (matches what the uncapped majority of the
# real rows show, appropriate for the operational-role salary levels in this pipeline).
EMPLOYER_SI_HI_RATE = 0.205
EMPLOYER_UNEMPLOYMENT_RATE = 0.01
EMPLOYER_INSURANCE_RATE = EMPLOYER_SI_HI_RATE + EMPLOYER_UNEMPLOYMENT_RATE

# The standard form's own real payroll calculator, 'A1. Staff cost 08.2026 (VN)', prices Savills'
# in-house staff on a fuller basis than the flat EMPLOYER_INSURANCE_RATE above — its own formula
# chain (rows 4-8, hidden reference block) adds a 13th-month salary, caps the statutory SI/HI/UI/
# Trade-Union contributions at 20x a regional base, and marks the whole employer cost up 10% for
# Savills' admin fee. Nothing read that total back into '1. Summary' before (docs/09-template-map.md
# §9 finding 2) — 'EMH2' used the flat rate above instead and understated staff cost by 320,427,060
# VND on the Wayne Tower example. Change reconcile-summary-with-detail-sheets, design D2/D3: EMH2
# becomes a formula reference into A1's own total; this analysis workbook's own staff figure moves
# onto the same components so the two keep agreeing (the "EMH2 never drifts from build_staff_sheet"
# invariant), rather than re-deriving the same numbers with the PIT-bracket logic duplicated.
#
# These used to be STATUTORY_*_2026 constants copied from the template's "Hide" reference rows
# ('A1. Staff cost 08.2026 (VN)'!I4 / I5 / L7:V8 / AB1), and drifted from the law whenever the law
# changed. They now come from the labour-law table (data/generation_B_verified/
# Ref_LaborLawParams.csv, change carry-forward-staffing) through statutory_payroll_params().
# This sheet uses the values in force in the last month of the schedule year, for Region I (the
# region the template's A1!I5 assumes): for 2026 and 2027 that is 2,530,000 / 5,310,000, x20 caps,
# 20.5% / 1% / 2%, 10% markup — the template's own values, so no figure moved.
def _plain(x):
    """A table value as it should print inside formula text: 2530000.0 -> 2530000."""
    return int(x) if float(x).is_integer() else x


def statutory_payroll_params(year, region=None):
    """A1's payroll parameters for `year`: the values in force in its last month (see above)."""
    p = labor_law_params.params_for_year(year, region)
    m = 12
    base = p.value('insurance_base', m)
    ui_base = p.value('min_wage_region', m)
    return {
        'si_hi_base': _plain(base),
        'ui_base': _plain(ui_base),
        'si_hi_cap': _plain(base * p.value('si_hi_ceiling_multiple', m)),
        'ui_cap': _plain(ui_base * p.value('ui_ceiling_multiple', m)),
        'si_hi_rate': _plain(round(p.value('employer_si_rate', m) + p.value('employer_hi_rate', m), 6)),
        'ui_rate': _plain(p.value('employer_ui_rate', m)),
        'union_rate': _plain(p.value('union_rate', m)),
        'markup': _plain(p.value('admin_markup', m)),
    }


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
# Landscape's own AvgDailyRate comment divides the citywide rate straight by the working days, no
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
    # The new-prospect categories below; the same rows build_project_input_form.py sets their default rates from.
    'Assistant Property Manager': (17_000_000, 2, 'Trợ lý trưởng ban quản lý'),
    'Assistant Chief Engineer': (17_427_160, 24, 'Trợ lý Kỹ sư trưởng'),
    'Customer Service Supervisor': (14_240_818, 10, 'Trưởng nhóm Chăm Sóc Khách Hàng'),
    'Operations Manager': (26_395_822, 14, 'Quản lý vận hành'),
    'Accountant': (13_574_175, 54, 'Kế toán'),
    'Cashier': (10_028_473, 13, 'Thủ Quỹ'),
    'Technical Secretary': (10_737_610, 4, 'Thư ký Bộ phận kỹ thuật'),
}

# A new prospect costs every in-house position on its own category (change apply-head-of-pm-decisions-2026-10, D6-b):
# the four positions the analysis left out, and the assistant and supervisor positions that the substring match filed
# under Property Manager, Chief Engineer and Customer Service. A position takes its first matching category, so the
# assistant and supervisor categories come first. Existing mode keeps STAFF_MARKET_KEYWORDS and its figures (G2-a).
NEW_PROSPECT_STAFF_MARKET_KEYWORDS = {
    'Assistant Property Manager': ['assistant property manager'],
    'Assistant Chief Engineer': ['assistant chief engineer'],
    'Customer Service Supervisor': ['customer service supervisor'],
    **STAFF_MARKET_KEYWORDS,
    'Operations Manager': ['operations manager'],
    'Accountant': ['accountant'],
    'Cashier': ['cashier'],
    'Technical Secretary': ['technical secretary'],
}


def staff_market_categories(project):
    """The staff categories of the analysis for this project, and whether a position takes its first match only."""
    if project.get('existing') is None:
        return NEW_PROSPECT_STAFF_MARKET_KEYWORDS, True
    return STAFF_MARKET_KEYWORDS, False


def in_staff_category(position, name, categories, first_match):
    p = position.lower()
    if first_match:
        return next((k for k, kws in categories.items() if any(kw in p for kw in kws)), None) == name
    return any(kw in p for kw in categories[name])


# A1's per-person extras on a new prospect's 'Staff (Roster)' rows (columns AB:AF, after the working days in AA), from
# the constants existing_staffing.a1_row_cost uses. Annual, for the row's $B people; outsourced rows carry none.
A1_EXTRA_HEADERS = ['Team Building (A1)', f'Training {existing_staffing.A1_TRAINING_RATE:.1%} (A1)',
                    'Health Check (A1)', 'Accident Insurance (A1)', 'Uniform (A1)']
EXTRAS_FIRST_COL = 28                                                  # AB
EXTRAS_FIRST_LETTER = get_column_letter(EXTRAS_FIRST_COL)
EXTRAS_LAST_LETTER = get_column_letter(EXTRAS_FIRST_COL + len(A1_EXTRA_HEADERS) - 1)


def a1_extra_formulas(r, position):
    """The five extras of row `r` (one person's monthly gross = $AA/12 x $R), in A1_EXTRA_HEADERS' order."""
    if _is_outsourced(position):
        return [0] * len(A1_EXTRA_HEADERS)
    code = 'PM' if _a1_group_of(position) == 'PM' else None
    team = existing_staffing.A1_TEAM_BUILDING_PM if code == 'PM' else existing_staffing.A1_TEAM_BUILDING
    gross = f'$AA{r}/12*$R{r}'
    return [f'=$B{r}*{team}*12',
            f'=$B{r}*{gross}*{existing_staffing.A1_TRAINING_RATE}*12',
            f'=$B{r}*{existing_staffing.A1_CHECKUP_ANNUAL}',
            f'=$B{r}*{existing_staffing.a1_accident_formula(code, gross)}*12',
            f'=$B{r}*{existing_staffing.A1_UNIFORM}*12']

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
    product — see master_comparables.py's PRODUCT_RATE_COLUMNS and resolve_product_rates(). Real
    per-product rate data is thin outside Apartment (most comparables only have one blended
    rate), so any product with zero qualifying comparables falls back to this project's own
    derived Apartment rate — labeled in red as a fallback, never silently dropped from revenue
    and never silently presented as if it were product-specific real data."""
    ws = wb.create_sheet('Management Fee')
    title_block(ws, 'Management Fee',
                'Each product priced with its own derived rate from real comparables with a rate for that product '
                '(Apartment rate used as a labeled fallback where none exist) — see master_comparables.py.', 'A1:E1')

    # Every rate on this sheet comes from master_comparables.resolve_product_rates() — the same
    # call generate_project_budget.py makes once per run — so this workbook and the deliverable
    # cannot disagree on any product's rate (change use-operating-project-actuals, P5). Apartment's
    # carries the within-1km ±20% rate-swing cap (task 2.5, 2026-09-16); when no comparable has an
    # Apartment rate at all it is the blended whole-property rate, which before P5 only the
    # deliverable had.
    rates = resolve_product_rates(project)
    apt_rate, apt_note = rates['apartment_rate'], rates['rate_note']
    # Which operating-project fields this run found, and the entered-vs-comparable rates (design D6).
    for line in operating_inputs.report_lines(
            project.get('operating') or operating_inputs.blank_inputs(), rates):
        print(line)
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
    apt_entered = rates.get('apartment_entered')     # P1: the PM's actual Apartment rate, when entered
    ws.cell(row=r, column=1, value=(f"Applied Apartment rate — PM-entered actual rate ({apt_entered['vat']}) "
                                    f"(VND/m²/month)" if apt_entered else
                                    'Derived Apartment rate (VND/m²/month)')).font = Font(bold=True)
    rate_cell = ws.cell(row=r, column=2, value=apt_rate)
    rate_cell.fill = HIGHLIGHT_FILL
    rate_cell.number_format = MONEY_FMT
    rate_cell.border = BORDER
    r += 1
    if apt_entered:
        ws.cell(row=r, column=1, value='Comparable-derived Apartment rate (reference only)').font = Font(italic=True, size=9)
        c = ws.cell(row=r, column=2, value=rates.get('apartment_comparable_rate'))
        c.number_format = MONEY_FMT
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
        # The resolver's per-product decision: Apartment capped, the others uncapped or falling back
        # to the Apartment rate (the 2026-09-16 bug was this loop re-deriving Apartment uncapped).
        _p_rate = rates['products'][product]
        rate, used, note, is_fallback = _p_rate['rate'], _p_rate['used'], _p_rate['note'], _p_rate['is_fallback']
        if is_fallback:
            note = (f"No comparable has a real {product} rate — using this project's "
                    + ("applied Apartment rate, the PM-entered actual rate" if apt_entered else "derived Apartment rate")
                    + f" ({apt_rate:,}) as the best available proxy.")
        if _p_rate['source'] == 'entered':
            _cmp = _p_rate.get('comparable_rate')
            note = (f"PM-entered actual rate ({_p_rate['vat']}), applied as entered with no VAT conversion; "
                    + (f"comparables give {_cmp:,.0f} ({(rate - _cmp) / _cmp * 100:+.1f}%)." if _cmp
                       else "no comparable has a rate for it."))
        ws.cell(row=r, column=1, value=product).border = BORDER
        c2 = ws.cell(row=r, column=2, value=nfa)
        c2.border = BORDER
        c2.number_format = '#,##0'
        c3 = ws.cell(row=r, column=3, value=rate)
        c3.border = BORDER
        c3.number_format = MONEY_FMT
        if is_fallback:
            c3.font = Font(italic=True, color='C00000')
        source_label = (f"PM-entered actual rate ({_p_rate['vat']})" if _p_rate['source'] == 'entered' else
                        (f"{len(used)} real comparable(s): " + ', '.join(c['name'] for c in used)) if used else
                        'Apartment rate (fallback — no product-specific comparable)')
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
                derived_rate=apt_rate, top2=rates['comparables'], rate_note=apt_note, own_real=own_real,
                vat_pct=rates.get('vat_pct'), vat_flags=rates.get('vat_flags') or {},
                apartment_entered=rates.get('apartment_entered'),
                apartment_comparable_rate=rates.get('apartment_comparable_rate'),
                apartment_rates_on_basis=rates.get('apartment_rates_on_basis'))


# ============================================================================================
def build_comparison_sheet(wb, project, mgmt):
    """Side-by-side comparison against the same 2 real projects the Management Fee sheet derived
    its rate from — scale, management-fee rate (with a reality check if this project's own real
    rate happens to be known), and the flat citywide service rates for context."""
    top2, derived_rate, rate_note, own_real = mgmt['top2'], mgmt['derived_rate'], mgmt['rate_note'], mgmt['own_real']
    ws = wb.create_sheet('Comparison')
    from master_comparables import comparable_match_basis
    match_basis = comparable_match_basis(top2, project.get('district'), project.get('city'),
                                          input_lat=project.get('lat'), input_lon=project.get('lon'),
                                          input_nfa=project.get('total_nfa'))
    title_block(ws, 'Comparison', f"{project['name']} vs. the {len(top2)} nearest real comparable(s) WITH A VERIFIED APARTMENT RATE, ranked by {match_basis} — {len(MASTER_COMPARABLES)} real candidates considered. Other product types (Officetel/Shophouse/etc.) are priced from a different comparable set — see the Management Fee sheet's Rate source column.", 'A1:D1')

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
    if project.get('address'):
        # Citation only — not a matching input; see build_project_input_form.py's comment on this
        # field for why it isn't geocoded into District/City/Latitude/Longitude.
        r = data_row(r, 'Address', [project['address']] + ['—', '—'])
    r = data_row(r, 'Total NFA (m²) — matching basis', [project['total_nfa']] + [c['nfa'] for c in top2])
    r = data_row(r, 'NFA delta from this project', ['—'] + [round(abs(c['nfa'] - project['total_nfa'])) for c in top2])
    r = data_row(r, 'Apartment NFA (m²) — for reference only, not the matching basis',
                 [project['apartment_nfa']] + ['—', '—'])
    r = data_row(r, 'Apartment units', [project['apartment_units']] + [c['units'] for c in top2])
    r += 1

    section(ws, r, 'APARTMENT MANAGEMENT FEE RATE', ncols=4); r += 1
    r = data_row(r, 'Real Apartment rate per comparable (VND/m²/month)',
                 ['—'] + [f"{c['rates']['Apartment']:,} ({c['mgmt_rate_vat']})"
                          if (c.get('rates') or {}).get('Apartment') else 'BLANK (no real rate)' for c in top2])
    _entered = mgmt.get('apartment_entered')
    if _entered:
        # P1: the comparables and the rate they give stay for reference; the applied rate is the PM's.
        _model = mgmt.get('apartment_comparable_rate')
        r = data_row(r, 'MODEL-DERIVED Apartment rate (this project, reference only)',
                     [f'{_model:,}' if _model else 'none (no comparable rate)', '', ''])
        r = data_row(r, f"APPLIED Apartment rate — PM-entered actual rate ({_entered['vat']})",
                     [f'{derived_rate:,}', '', ''], fill=HIGHLIGHT_FILL)
    else:
        r = data_row(r, 'MODEL-DERIVED Apartment rate (this project)', [f'{derived_rate:,}', '', ''], fill=HIGHLIGHT_FILL)
    if rate_note:
        r = data_row(r, 'Derivation note', [rate_note, '', ''])
    # Group 4 (change apply-head-of-pm-decisions-2026-10): comparable rates quoted excluding VAT were multiplied by
    # (1 + VAT of the budget period's first month) before averaging; a comparable not in the hand-checked table is
    # used as including VAT and flagged here, in the internal analysis only.
    if mgmt.get('vat_pct') is not None:
        r = data_row(r, 'Comparable VAT basis',
                     [f"Rates quoted excluding VAT (per the hand-checked table) were multiplied by "
                      f"{1 + mgmt['vat_pct'] / 100:.2f} (VAT of the budget period's first month) before averaging. "
                      f"A rate the PM entered is not converted.", '', ''])
    for _product, _names in (mgmt.get('vat_flags') or {}).items():
        r = data_row(r, f'VAT basis NOT verified — {_product}',
                     [f"{', '.join(_names)}: not in the hand-checked table, used as including VAT.", '', ''],
                     fill=HIGHLIGHT_FILL)
    if own_real:
        gap = derived_rate - own_real['rates']['Apartment']
        r = data_row(r, "This project's ACTUAL real Apartment rate (reality check)",
                     [f"{own_real['rates']['Apartment']:,} ({own_real['mgmt_rate_vat']})", '', ''], fill=HIGHLIGHT_FILL)
        r = data_row(r, 'Gap (derived − real)', [f'{gap:+,} VND  ({gap/own_real["rates"]["Apartment"]*100:+.0f}%)', '', ''], fill=HIGHLIGHT_FILL)
    else:
        r = data_row(r, 'Reality check', ['Not applicable — new prospect, no independently known real rate', '', ''])
    r += 1

    # ---- PEER BENCHMARK (change apply-head-of-pm-decisions-2026-10, D14): the peer columns the client
    # deliverable's Comparison sheet no longer carries. Same comparables, same order as the rate above.
    # The deliverable shows this project's column and a verdict that names no reference project. ----
    from generate_project_budget import _benchmark_fee_clause
    section(ws, r, 'PEER BENCHMARK — internal only; the client Comparison sheet names no reference project', ncols=4); r += 1
    apt_nfa = project.get('apartment_nfa') or 0
    apt_units = project.get('apartment_units') or 0
    # On the basis the rate was averaged on (excl.-VAT rates converted, group 4), not as quoted.
    comp_rates = mgmt.get('apartment_rates_on_basis') or [(c.get('rates') or {}).get('Apartment') for c in top2]
    if mgmt.get('vat_pct') is not None:
        r = data_row(r, 'Real Apartment rate on one VAT basis (VND/m²/month)',
                     ['—'] + [f'{x:,.0f}' if x else '—' for x in comp_rates])
    if apt_nfa and apt_units:
        comp_fpa = [f"{round(cr * c['nfa'] / c['units']):,}  (approx, upper bound)" if (cr and c.get('units'))
                    else '— (no rate or unit count on file)' for c, cr in zip(top2, comp_rates)]
        r = data_row(r, 'Management fee per apartment (VND/month)',
                     [f'{round(derived_rate * apt_nfa / apt_units):,}'] + comp_fpa)
        r = data_row(r, 'How fee per apartment is computed',
                     [f"This project: rate × {apt_nfa / apt_units:,.0f} m² average apartment NFA (apartment NFA ÷ "
                      f"apartment units). Comparables: real Apartment rate × (Total building NFA ÷ apartment units) — "
                      f"apartment-only area is not on file, so this is an approximation and an upper bound.", '', ''])
    else:
        r = data_row(r, 'Management fee per apartment (VND/month)', ['— (this project has no apartments)', '', ''])
    _rev = f"'Management Fee'!{mgmt['annual_revenue_cell']}"
    proj = []
    for cr in comp_rates:
        if cr and apt_nfa:
            d = round(apt_nfa * (cr - derived_rate) * 12)
            proj.append(f"={_rev}" + (f"+{d}" if d > 0 else (f"-{abs(d)}" if d < 0 else "")))
        else:
            proj.append('—')
    _rev_row = r
    r = data_row(r, 'Year-1 management-fee revenue (VND)', [f"={_rev}"] + proj)
    for col in range(2, 3 + len(top2)):
        ws.cell(row=_rev_row, column=col).number_format = MONEY_FMT
    r = data_row(r, 'Revenue columns per comparable',
                 ["A PROJECTION: this project's annual management-fee revenue (Management Fee sheet) with only the "
                  "Apartment lines re-priced at that comparable's Apartment rate — not that comparable's own revenue.",
                  '', ''])
    _have = [x for x in comp_rates if x]
    r = data_row(r, 'Range of the comparables\' real Apartment rates, one VAT basis (VND/m²/month)',
                 [f'{min(_have):,.0f} – {max(_have):,.0f}' if _have else '— (no comparable rate)', '', ''])
    r = data_row(r, 'Verdict wording on the client sheet (fee part)',
                 [_benchmark_fee_clause(derived_rate, comp_rates, entered=bool(_entered)), '', ''])
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
                ('Calendar working days per person (column AA), the same count A1 uses; night and holiday allowance '
                 'per shift, as A1.1 (block below the total)'
                 if project.get('existing') is None else
                 'Estimated from average weekly coverage (see script docstring) — night differential (+30%) '
                 'included, holiday differentials excluded'), 'A1:F1')
    ws['A3'] = 'Year'
    ws['A3'].font = Font(bold=True)
    ws['B3'] = year

    headers = ['Position', 'Staff Count'] + MONTH_NAMES + ['Annual Total (Gross)']
    HEADER_ROW = 5
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=HEADER_ROW, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    # Columns 16-19 (P-S) are hidden per-row helper cells (StaffPerDay/CoverageDays/AvgDailyRate/
    # IsNight, written per-row below) — these new columns sit right after them rather than being
    # inserted earlier, so none of the existing formula column references above need to shift.
    # T-Z replicate 'A1. Staff cost 08.2026 (VN)''s own employer-cost chain (13th month, capped SI/HI, UI and union,
    # admin markup) as explicit formulas, replacing the old flat EMPLOYER_INSURANCE_RATE (x1.215) shortcut — change
    # reconcile-summary-with-detail-sheets, D3. A new prospect also carries A1's per-person extras (AB:AF) and caps
    # each person's pay, as A1 does (change apply-head-of-pm-decisions-2026-10, D7).
    s = statutory_payroll_params(year)
    for c, h in [(20, '13th-Month Salary (A1 basis)'),
                 (21, f'Employer SI/HI {s["si_hi_rate"]:.1%} (capped, A1 basis)'),
                 (22, f'Employer UI {s["ui_rate"]:.1%} (capped, A1 basis)'),
                 (23, f'Trade Union {s["union_rate"]:.1%} (capped, A1 basis)'),
                 (24, 'Subtotal Before Admin Markup'),
                 (25, f'Admin Markup ({s["markup"]:.0%}, A1 basis)'),
                 (26, 'Annual Total (Full Payroll Basis — A1)')]:
        cell = ws.cell(row=HEADER_ROW, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER

    DAYS_ROW = 6
    # A new prospect pays each person the calendar working days of the budget period / 12 every month, the count A1
    # uses (column AA; change apply-head-of-pm-decisions-2026-10, D6). Existing mode keeps the coverage estimate
    # below, so its figures do not move (G2-a).
    calendar_days = project.get('existing') is None
    WORKDAYS_COL = 27                                                  # AA
    if calendar_days:
        period = project.get('budget_period') or budget_period.default()
        ws.cell(row=DAYS_ROW, column=1, value=(
            f'Working days: Mon–Sat minus paid holidays in {period.label()} (column AA), paid evenly ÷ 12'
        )).font = Font(italic=True, size=9)
        h = ws.cell(row=HEADER_ROW, column=WORKDAYS_COL, value='Working Days / Person in Period (calendar)')
        h.fill, h.font, h.alignment, h.border = HEADER_FILL, HEADER_FONT, CENTER, BORDER
        ws.column_dimensions['AA'].width = 18
        for c, h in enumerate(A1_EXTRA_HEADERS, start=EXTRAS_FIRST_COL):
            cell = ws.cell(row=HEADER_ROW, column=c, value=h)
            cell.fill, cell.font, cell.alignment, cell.border = HEADER_FILL, HEADER_FONT, CENTER, BORDER
            ws.column_dimensions[get_column_letter(c)].width = 16
    else:
        ws.cell(row=DAYS_ROW, column=1, value='Days in Month').font = Font(italic=True, size=9)
        for i in range(12):
            col = 3 + i
            f = ws.cell(row=DAYS_ROW, column=col, value=f'=DAY(EOMONTH(DATE($B$3,{i + 1},1),0))')
            f.font = Font(italic=True, size=9, color='7F7F7F')
            f.alignment = CENTER

    si_hi_cap = s['si_hi_cap']
    ui_cap = s['ui_cap']

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
        if calendar_days:
            wd = ws.cell(row=r, column=WORKDAYS_COL,
                         value=(period_workdays(period, d['CoverageDays'], d['Position'])
                                if d['StaffPerDay'] else 0))
            wd.border, wd.alignment = BORDER, CENTER
        for i in range(12):
            col = 3 + i
            col_letter = get_column_letter(col)
            day_ref = f'{col_letter}${DAYS_ROW}'
            if calendar_days:
                # Night work is priced per shift in the allowance block below, as A1.1 does (docs/30 M4-a), not as a
                # x1.3 loading on the night rows.
                formula = f'=$B{r}*$AA{r}/12*$R{r}'
            else:
                formula = (f'=$B{r}*ROUND({day_ref}*IF($Q{r}>=7,6,$Q{r})/7,0)*$R{r}'
                           f'*IF($S{r}=1,{NIGHT_DIFFERENTIAL},1)')
            cell = ws.cell(row=r, column=col, value=formula)
            cell.number_format = MONEY_FMT
            cell.border = BORDER
        annual_col = 3 + 12
        annual = ws.cell(row=r, column=annual_col,
                          value=f'=SUM(C{r}:{get_column_letter(annual_col - 1)}{r})')
        annual.number_format = MONEY_FMT
        annual.border = BORDER
        annual.font = Font(bold=True)
        annual_letter = get_column_letter(annual_col)
        thirteenth = ws.cell(row=r, column=20, value=f'={annual_letter}{r}/12')
        thirteenth.number_format = MONEY_FMT
        thirteenth.border = BORDER
        if calendar_days:
            # A1 caps each person's pay ($AA/12 x $R a month), not the row's total of $B people.
            def capped(cap, rate):
                return f'=$B{r}*MIN($AA{r}/12*$R{r},{cap})*{rate}*12'
        else:
            def capped(cap, rate):
                return f'=MIN({annual_letter}{r}/12,{cap})*{rate}*12'
        si_hi = ws.cell(row=r, column=21, value=capped(si_hi_cap, s['si_hi_rate']))
        si_hi.number_format = MONEY_FMT
        si_hi.border = BORDER
        ui = ws.cell(row=r, column=22, value=capped(ui_cap, s['ui_rate']))
        ui.number_format = MONEY_FMT
        ui.border = BORDER
        union = ws.cell(row=r, column=23, value=capped(si_hi_cap, s['union_rate']))
        union.number_format = MONEY_FMT
        union.border = BORDER
        extras = ''
        if calendar_days:
            for c, v in enumerate(a1_extra_formulas(r, d['Position']), start=EXTRAS_FIRST_COL):
                cell = ws.cell(row=r, column=c, value=v)
                cell.number_format, cell.border = MONEY_FMT, BORDER
            extras = f'+SUM({EXTRAS_FIRST_LETTER}{r}:{EXTRAS_LAST_LETTER}{r})'
        subtotal = ws.cell(row=r, column=24, value=f'={annual_letter}{r}+T{r}+U{r}+V{r}+W{r}{extras}')
        subtotal.number_format = MONEY_FMT
        subtotal.border = BORDER
        markup = ws.cell(row=r, column=25, value=f'=X{r}*{s["markup"]}')
        markup.number_format = MONEY_FMT
        markup.border = BORDER
        total_incl = ws.cell(row=r, column=26, value=f'=X{r}+Y{r}')
        total_incl.number_format = MONEY_FMT
        total_incl.border = BORDER
        total_incl.font = Font(bold=True)
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
    total_cols = ['T', 'U', 'V', 'W', 'X', 'Y', 'Z']
    if calendar_days:
        total_cols += [get_column_letter(c) for c in range(EXTRAS_FIRST_COL, EXTRAS_FIRST_COL + len(A1_EXTRA_HEADERS))]
    for col_letter in total_cols:
        c = ws.cell(row=r, column=column_index_from_string(col_letter),
                     value=f'=SUM({col_letter}{first_row}:{col_letter}{last_row})')
        c.number_format = MONEY_FMT
        c.font = SECTION_FONT
    ANNUAL_TOTAL_CELL = f'Z{r}'  # full payroll basis, A1's components
    r += 1
    ws.cell(row=r, column=1, value=(
        "Column Z uses the deliverable's own 'A1. Staff cost' components per person: 13th month, employer SI/HI, UI "
        "and Trade Union capped on each person's pay, A1's per-person extras for in-house staff (team building, 1.3% "
        'training, health check, accident insurance, uniform; columns AB:AF), then the admin markup. Outsourced '
        'Security / Cleaning / Landscape are costed at the bare contract (column O) in every category total.'
        if calendar_days else
        "Column Z uses the deliverable's own 'A1. Staff cost' components (13th month, capped employer SI/HI, UI and "
        "Trade Union, admin markup) on each row's total pay. It leaves out A1's per-person extras (team building, "
        'training, health check, accident insurance, uniform), which only a new prospect carries here.'
    )).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:F{r}')
    ws.row_dimensions[r].height = 42
    r += 2

    allowance_cells, allowance_total_cell = {}, None
    if calendar_days:
        r, allowance_cells, allowance_total_cell = _write_allowance_block(ws, r, demand, period)

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
    for col_letter, w in {'T': 16, 'U': 16, 'V': 16, 'W': 16, 'X': 18, 'Y': 16, 'Z': 22}.items():
        ws.column_dimensions[col_letter].width = w

    r += 2
    build_roster_detail_grid(ws, demand, r)

    # Category-level annual cost, as a live cross-sheet formula summing this sheet's own Annual
    # Total (Full Payroll Basis) cells — for the Service sheet's comparison columns and Cost
    # Priority. Same matching AND exclusion rules Service itself uses (SERVICE_CATEGORY_KEYWORDS /
    # SERVICE_EXCLUDE_KEYWORDS), so "Security" here means the exact same 7 rows Service prices as
    # Security, not a looser/different definition. Column Z (not the bare-gross O) so every
    # downstream sheet that sums this dict picks up the loaded cost automatically.
    def _cell_sum(rows, col='Z'):
        return (("='Staff (Roster)'!" + "+'Staff (Roster)'!".join(f'{col}{rr}' for rr in rows))
                if rows else '=0')

    # Which column each category sums, and why it matters:
    #   Z = Annual Total, Full Payroll Basis — Savills' own in-house payroll (A1 basis).
    #   O = the bare annual, no employer contribution — outsourced vendor contracts.
    # Everything under SERVICE_CATEGORY_KEYWORDS (Security / Cleaning / Landscape, and their
    # Supervisory variants) is an outsourced contract: the template files them under ES =
    # Expenses for Outsource Service, and their daily rates come from Fact_MasterRateCard.csv's
    # SERVICE domain — vendor post prices that already cover the vendor's own staff insurance.
    # Loading them again would charge it twice. See openspec change
    # fix-outsourced-service-cost-basis and docs/05-decisions.md D3. generate_project_budget.py
    # makes the identical split, so the two workbooks report the same figures.
    OUTSOURCED_COL = get_column_letter(annual_col)   # bare annual, no employer contribution

    category_annual_cells = {}
    # The SAME categories on the in-house basis (column U, loaded). Used only by the Service
    # sheet's "Staff (Roster) Equivalent, incl. Employer Insurance" column, which exists to answer
    # "what would this cost if Savills employed them directly" — that comparison is meaningless if
    # the column silently switches to the outsourced basis, and its header would then be false.
    category_annual_cells_inhouse = {}
    for cat, keywords in SERVICE_CATEGORY_KEYWORDS.items():
        rows = [position_row[pos] for pos in position_row
                if any(kw in pos.lower() for kw in keywords)
                and not any(ex in pos.lower() for ex in SERVICE_EXCLUDE_KEYWORDS)]
        category_annual_cells[cat] = _cell_sum(rows, OUTSOURCED_COL)
        category_annual_cells_inhouse[cat] = _cell_sum(rows)
        # Rows excluded from the citywide-comparable bucket (e.g. Cleaning - Supervisor) are still
        # a real cost — captured here under their own key so nothing silently drops out of any
        # sheet that sums category_annual_cells for a full-coverage total (e.g. Cost Priority).
        # They are part of the same outsourced contract, so they take the same basis.
        excluded_rows = [position_row[pos] for pos in position_row
                          if any(kw in pos.lower() for kw in keywords)
                          and any(ex in pos.lower() for ex in SERVICE_EXCLUDE_KEYWORDS)]
        if excluded_rows:
            category_annual_cells[f'{cat} — Supervisory'] = _cell_sum(excluded_rows, OUTSOURCED_COL)
            category_annual_cells_inhouse[f'{cat} — Supervisory'] = _cell_sum(excluded_rows)
    market, first_match = staff_market_categories(project)
    for cat in market:
        rows = [position_row[pos] for pos in position_row if in_staff_category(pos, cat, market, first_match)]
        category_annual_cells[cat] = _cell_sum(rows)
        category_annual_cells_inhouse[cat] = _cell_sum(rows)
    # A new prospect's night and holiday allowance (the block above) joins the category of the positions it is paid to.
    for cat, refs in allowance_cells.items():
        for cells in (category_annual_cells, category_annual_cells_inhouse):
            cells[cat] = cells.get(cat, '=0') + ''.join(f"+'Staff (Roster)'!{ref}" for ref in refs)

    # ---- Cost the three outsourced services the way EXENSIVE LOGIC.xlsx says to ----
    # ESS1 "Monthly contract fee x 12", ESS4 "m2 x unit price x 12 OR monthly contract x 12",
    # ESS16 "Monthly contract x 12". None of those is a roster sum, so these three categories point
    # at the Service sheet's own contract calculation (its column H) rather than at Staff (Roster).
    # generate_project_budget.py's ESS rows use the identical figure, so the deliverable and this
    # workbook now cost them the same — before this they differed by 210,372,000 VND on the sample.
    #
    # The Service sheet writes Security/Cleaning/Landscape at fixed rows 5/6/7 (header at row 4,
    # three categories in a fixed order — see build_service_sheet). Their Supervisory variants are
    # part of the same vendor contract and are therefore already inside that figure, so they are
    # dropped here rather than added on top.
    SERVICE_CONTRACT_ROW = {'Security': 5, 'Cleaning': 6, 'Landscape': 7}
    for cat, row in SERVICE_CONTRACT_ROW.items():
        if cat in category_annual_cells:
            category_annual_cells[cat] = f"='Service'!H{row}"
        category_annual_cells.pop(f'{cat} — Supervisory', None)

    return dict(annual_total_cell=ANNUAL_TOTAL_CELL, category_annual_cells=category_annual_cells,
                category_annual_cells_inhouse=category_annual_cells_inhouse,
                allowance_total_cell=allowance_total_cell, market_categories=market, first_match=first_match)


def _write_allowance_block(ws, r, demand, period):
    """A new prospect's night and holiday allowance on 'Staff (Roster)', per shift and on the same counts as the
    deliverable's A1.1 (change apply-head-of-pm-decisions-2026-10, D5 and M4-a): daily wage = A1 gross / (working days
    / 12); annual = daily wage x (30% x normal nights x night staff + 390% x holidays x night staff + 300% x holidays x
    holiday day staff). Returns (next row, {staff category: [annual cells]}, total cell or None)."""
    duty = _new_prospect_duty(demand, period)
    n = len(vn_holidays.paid_holidays_in_period(period.first_day, period.last_day))
    nights = (period.last_day - period.first_day).days + 1 - n
    wd = period_workdays(period, 6)
    section(ws, r, "NIGHT AND HOLIDAY ALLOWANCE — per shift, on the deliverable's A1.1 counts (Labour Code 2019 "
                   'Art. 98)', ncols=6)
    r += 1
    headers = ['A1.1 Code', 'Positions', 'A1 Gross / Person / Month', 'Daily Wage', 'Night Staff',
               'Normal Nights (30%)', 'Holiday Nights (390%)', 'Holiday Day Staff', 'Holidays (300%)',
               'Annual Allowance']
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill, cell.font, cell.alignment, cell.border = HEADER_FILL, HEADER_FONT, CENTER, BORDER
    r += 1
    first = r
    cells = {}
    for d in duty:
        positions = [x['Position'] for x in demand
                     if x.get('StaffPerDay') and not _is_outsourced(x['Position']) and _a11_code_of(x['Position']) == d.code]
        values = [d.code, ', '.join(positions), d.gross, f'=C{r}/({wd}/12)', d.night_normal, nights, n,
                  d.day_holiday, n,
                  (f'=D{r}*({existing_staffing.A11_NIGHT_RATE}*E{r}*F{r}'
                   f'+{existing_staffing.A11_HOLIDAY_NIGHT_RATE}*E{r}*G{r}'
                   f'+{existing_staffing.A11_HOLIDAY_DAY_RATE}*H{r}*I{r})')]
        for c, v in enumerate(values, start=1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.border = BORDER
            if c in (3, 4, 10):
                cell.number_format = MONEY_FMT
        cat = next((k for k in NEW_PROSPECT_STAFF_MARKET_KEYWORDS
                    if positions and in_staff_category(positions[0], k, NEW_PROSPECT_STAFF_MARKET_KEYWORDS, True)),
                   f'Night & Holiday Allowance ({d.code})')
        cells.setdefault(cat, []).append(f'J{r}')
        r += 1
    total = None
    if duty:
        ws.cell(row=r, column=1, value='TOTAL').font = SECTION_FONT
        c = ws.cell(row=r, column=10, value=f'=SUM(J{first}:J{r - 1})')
        c.number_format, c.font = MONEY_FMT, SECTION_FONT
        total = f'J{r}'
        r += 1
    note = ('Holiday day work is counted for 7-day positions with a night shift only (morning + afternoon staff); '
            'night work for every in-house position with a D or 24H shift. Equals 12 x the deliverable\'s EMH3 '
            '(A1.1!S13). Added to each position\'s category below, not loaded with insurance or markup (A1 adds it '
            'plain at AC90).' if duty else
            'No in-house position has a night shift (D or 24H), so there is no night or holiday allowance (EMH3 = 0).')
    ws.cell(row=r, column=1, value=note).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:F{r}')
    ws.row_dimensions[r].height = 40
    return r + 2, cells, total


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
               'Annual (×12)', 'Staff (Roster) Equivalent, Full Payroll Basis (VND/year)', 'Gap %', 'Gap Assessment', 'Qty source']
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
        # Deliberately the IN-HOUSE (loaded) figure: this column is the "what if Savills employed
        # them" side of the comparison, and its header says incl. Employer Insurance.
        c9 = ws.cell(row=r, column=9, value=staff['category_annual_cells_inhouse'][name])
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
                   'Market-Rate Monthly Total (VND)', 'Staff (Roster) Equivalent, incl. Employer Insurance (VND/year)', 'Gap %', 'Gap Assessment', 'Source item']
    for c, h in enumerate(mkt_headers, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    r += 1
    mkt_first_row = r
    market, first_match = staff['market_categories'], staff['first_match']
    for name in market:
        matched = [d for d in demand if in_staff_category(d['Position'], name, market, first_match)]
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
                   "of a vendor's night post (the factor Existing mode's Staff (Roster) still uses) — without it, "
                   'this flat citywide '
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


def _real_ad_frame_qty(project, tower_count):
    """The 'Ad frame' row's real quantity when the project supplies its own real passenger-elevator
    count (Project Info's 'Passenger Elevators per Tower' — change
    wire-real-elevator-count-into-ad-revenue, task 2.1), else None (caller keeps
    ELEVATOR_AD_ITEMS's own fallback qty_per_tower/assumption completely unchanged). Only the FIRST
    ELEVATOR_AD_ITEMS tuple ('Ad frame...') ever calls this — the two LCD-screen rows have no real
    per-project data source and are untouched by this change (design.md Non-Goals).

    Deliberately tiny — not a bigger abstraction over ELEVATOR_AD_ITEMS's shape — so both generators
    compute this one override identically and can never silently disagree on the QUANTITY (design.md
    Risks), while each still writes its own remark text in its own language/format, matching how
    `assumption` (English) / `_AD_ITEM_VI` (Vietnamese) already work as separate concerns."""
    real_per_tower = project.get('passenger_elevators_per_tower')
    if not real_per_tower:
        return None
    return round(tower_count * real_per_tower)


def _real_basement_lcd_qty(project):
    """The 'LCD screen (basement lobby)' row's real quantity when the project supplies its own real
    basement count (Project Info's 'Number of Basements' — task 2.6, added 2026-09-16 alongside the
    elevator field, same amendment pattern), else None (caller keeps ELEVATOR_AD_ITEMS's own flat_qty
    of 1 unchanged). One screen assumed per basement level (each level needs its own lobby signage),
    same "leave unassumed until real data exists" reasoning as `_real_ad_frame_qty()`.

    No internal-data or statutory basis exists for a basement-COUNT formula (checked directly against
    Dim_Property_Residential.csv: basement count tracks parking-slot count only loosely, not floor
    count, and the spread is too wide to derive a ratio) — manual entry only, same conclusion as the
    elevator-count research this session. Only the THIRD ELEVATOR_AD_ITEMS tuple ('LCD screen
    (basement lobby)') ever calls this — the 'Ad frame' and 'LCD screen (tower lobby)' rows are
    untouched."""
    real_basements = project.get('basement_count')
    if not real_basements:
        return None
    return round(real_basements)


def _collect_on_behalf_table(ws, r, project):
    """P4 (use-operating-project-actuals): the collect-on-behalf pairs the deliverable writes, each amount
    twice - on its RO3/RO4 revenue line and on the paired expense line - from the same entered figures.
    Pass-through money: not added to any profit or revenue total here, so this workbook's figures do not
    move. Nothing is shown when no amount is entered."""
    from generate_project_budget import _collect_on_behalf_lines
    lines = _collect_on_behalf_lines(project)
    if not lines:
        return r
    section(ws, r, 'COLLECT ON BEHALF (THU HỘ / CHI HỘ) — pass-through pairs, net 0, not in any total', ncols=6)
    r += 1
    headers = ['Product / utility', 'Revenue line', 'Revenue (VND/year)', 'Paired expense line',
               'Expense (VND/year)', 'Source']
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    r += 1
    for line in lines:
        values = [f"{line['product']} {line['utility']}", line['revenue_code'], line['monthly'] * 12,
                  line['expense_code'], line['monthly'] * 12,
                  'Entered by the PM on Project Info (VND/month x 12); paid out on residents\' behalf.']
        for c, v in enumerate(values, start=1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.border = BORDER
            if c in (3, 5):
                cell.number_format = MONEY_FMT
        r += 1
    return r


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
    # P2 (use-operating-project-actuals): a recorded monthly figure the PM entered replaces rate x slots,
    # the same figure the deliverable writes on RP1/RP2.
    recorded = ((project.get('operating') or {}).get('parking')) or {}
    for label, key, rate, slots in [('Car', 'car', PARKING_FEE_CAR_MONTHLY, project.get('car_slots') or 0),
                                     ('Motorbike', 'moto', PARKING_FEE_MOTO_MONTHLY, project.get('moto_slots') or 0)]:
        monthly = recorded.get(key)
        ws.cell(row=r, column=1, value=label).border = BORDER
        c2 = ws.cell(row=r, column=2, value=rate if monthly is None else None)
        c2.number_format = MONEY_FMT
        c2.border = BORDER
        c3 = ws.cell(row=r, column=3, value=slots)
        c3.border = BORDER
        c3.alignment = CENTER
        c4 = ws.cell(row=r, column=4, value=f'=B{r}*C{r}' if monthly is None else monthly)
        c4.number_format = MONEY_FMT
        c4.border = BORDER
        c5 = ws.cell(row=r, column=5, value=f'=D{r}*12')
        c5.number_format = MONEY_FMT
        c5.border = BORDER
        c6 = ws.cell(row=r, column=6, value=PARKING_FEE_SOURCE if monthly is None else (
            'Recorded average monthly revenue entered by the PM (Project Info, project at stable operation); '
            'not slots x rate.'))
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
    BREAKEVEN_PCT_CELL = f'B{r}'
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
    for idx, (item, rate, qty_per_tower, flat_qty, assumption) in enumerate(ELEVATOR_AD_ITEMS):
        real_qty = _real_ad_frame_qty(project, tower_count) if idx == 0 else None
        real_basements = _real_basement_lcd_qty(project) if idx == 2 else None
        if real_qty is not None:
            est_qty = real_qty
            assumption = (f"Real data: this project's own {project['passenger_elevators_per_tower']:g} "
                          f"passenger elevator(s) per tower (Project Info intake) x {tower_count} "
                          f"tower(s) = {est_qty} ad frame(s) — not an assumption.")
        elif real_basements is not None:
            est_qty = real_basements
            assumption = (f"Real data: this project's own {project['basement_count']:g} basement "
                          f"level(s) (Project Info intake) = {est_qty} screen(s) — not an assumption.")
        else:
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
    r += 1
    _collect_on_behalf_table(ws, r + 1, project)

    for col, w in {'A': 40, 'B': 22, 'C': 20, 'D': 20, 'E': 20, 'F': 60}.items():
        ws.column_dimensions[col].width = w

    return dict(annual_total_cell=TOTAL_ANNUAL_CELL, lease_breakeven_cell=f"'Additional Revenue'!{BREAKEVEN_PCT_CELL}",
                advertising_annual_cell=f"'Additional Revenue'!{AD_ANNUAL_CELL}")


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

    from generate_project_budget import _opex_kwargs, _general_vat_months
    opex = estimate_opex(project['total_nfa'], **_opex_kwargs(project))
    ur = project.get('utilities_result')
    if ur is None and 'Electricity' in opex and template_vat_inclusive():
        # A new prospect's electricity is priced before VAT: add each budget month's VAT, as the deliverable does
        # (change apply-head-of-pm-decisions-2026-10, task 2.7). Water and diesel are already priced with VAT.
        _vat = _general_vat_months(project)
        _elec = opex['Electricity']
        _excl = _elec['monthly_vnd']
        _elec['monthly_vnd'] = round(_excl * (1 + sum(_vat) / len(_vat) / 100))
        _elec['ratio_per_m2'] = round(_elec['monthly_vnd'] / project['total_nfa'], 2) if project['total_nfa'] else None
        _elec['source'] += (f" VAT: the tariff is before VAT, so each budget month's general VAT is added "
                            f"({', '.join(sorted({f'{v:g}%' for v in _vat}))}): {_excl:,.0f} VND/month before VAT "
                            f"-> {_elec['monthly_vnd']:,.0f} VND/month.")
    if ur is not None:
        # Existing-project mode (change carry-forward-common-utilities, design D6): electricity and water
        # show the client deliverable's own figures, built from the project's actual spend, so the two
        # workbooks never disagree. The walk from last year is on the 'Utility Bridge' sheet.
        for category, line in (('Electricity', 'EEE.C'), ('Water', 'EEW.C')):
            lr = ur.lines[line]
            p = lr.budget_prices[0]
            basis = 'actual spend' if lr.basis == 'actual' else 'approved prior-year amount'
            vat = 'incl.' if ur.incl_vat else 'excl.'
            opex[category] = dict(
                monthly_vnd=lr.annual / 12, ratio_per_m2=None, n='actual', existing=True,
                source=(f"EXISTING PROJECT: {line} from the project's own {basis}; "
                        f"see '{existing_utilities.BRIDGE_SHEET}'."),
                usage=f'{lr.q_budget:,.0f} {lr.unit}/month ({lr.basis})',
                price=(f"{p.price(ur.incl_vat):,.0f} VND/{lr.unit} {vat} VAT "
                       f"(Jan {ur.budget_year}, {lr.category})"),
                reference_only=None)

    r = 4
    section(ws, r, 'ESTIMATED MONTHLY OPEX', ncols=8); r += 1
    headers = ['Category', 'Monthly (VND)', 'Annual (×12)', 'Ratio (VND/m² NFA/month)', 'n', 'Source',
               'Usage assumed (per this project)', 'Tariff (as of)']
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
        c4 = ws.cell(row=r, column=4, value=entry['ratio_per_m2'] if entry['ratio_per_m2'] is not None
                     else 'n/a (actual spend)' if entry.get('existing') else 'n/a (flat)')
        c4.border = BORDER
        c4.alignment = CENTER
        c5 = ws.cell(row=r, column=5, value=entry['n'])
        c5.border = BORDER
        c5.alignment = CENTER
        # Pool Salt carries a `method` (a formula the costing spec states) rather than an A&K
        # ratio; show it ahead of the sourcing note so the calculation is what's read first.
        c6 = ws.cell(row=r, column=6,
                     value=f"{entry['method']} {entry['source']}".strip() if entry.get('method')
                           else entry['source'])
        c6.border = BORDER
        c6.alignment = LEFT
        # Usage × tariff split (Electricity / Water / Diesel — change
        # cost-energy-from-consumption-and-tariff). Blank for the ratio-only and flat categories.
        if entry.get('existing'):
            for col, text in ((7, entry['usage']), (8, entry['price'])):
                cc = ws.cell(row=r, column=col, value=text)
                cc.border = BORDER
                cc.alignment = LEFT
        elif entry.get('tariff'):
            base = entry['usage_unit'].split('/')[0]
            c7 = ws.cell(row=r, column=7,
                         value=f"{entry['project_quantity_month']:,.0f} {entry['usage_unit']}  "
                               f"({entry['usage_per_m2']:,.4f} {base}/m²/month × NFA, n=1)")
            as_of = entry['tariff_as_of']
            c8 = ws.cell(row=r, column=8,
                         value=f"{entry['tariff']:,.0f} {entry['tariff_unit']}  (as of {as_of}"
                               + ("; earlier than the 2027 budget year — confirm current" if entry.get('tariff_stale') else "")
                               + ")")
            for cc in (c7, c8):
                cc.border = BORDER
                cc.alignment = LEFT
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

    for col, w in {'A': 24, 'B': 20, 'C': 20, 'D': 22, 'E': 8, 'F': 60, 'G': 40, 'H': 34}.items():
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
    'Accountant': ('Must-Have', 'The management office keeps the accounts of the management fee and the funds.'),
    'Cashier': ('Optional', 'Depends on the size of the office and how fees are collected.'),
    'Operations Manager': ('Optional', 'A layer above the department heads on larger or higher-tier properties.'),
    'Technical Secretary': ('Optional', 'Administrative support for a larger technical team.'),
    # Must-Have as before the split, when they were costed inside Property Manager / Chief Engineer (the user's
    # choice, 2026-10-18), so splitting them out does not lower the Must-Have headline.
    'Assistant Property Manager': ('Must-Have', 'Part of the Property Manager function on the properties that staff it.'),
    'Assistant Chief Engineer': ('Must-Have', 'Part of the Chief Engineer function on the properties that staff it.'),
    'Customer Service Supervisor': ('Optional', 'Leads a larger customer service team.'),
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


CONTINGENCY_REPAIRS_ITEM = 'Repairs & Maintenance (materials only)'


def _write_contingency_section(ws, r, project, staff, item_rows, total_cells, must_have_cells):
    """The analysis's own contingency (change apply-head-of-pm-decisions-2026-10, group 6, design D9): the
    deliverable's contingency rate times this workbook's in-house staff plus OPEX less repairs, at 100% fill, once
    on the Must-Have basis and once on the Full Cost basis, as live formulas over this sheet's own rows. In-house
    staff leaves out the categories priced as vendor contracts on the Service sheet (Security, Cleaning,
    Landscape), which the deliverable carries as outsourced services. It does not equal the deliverable's year-1
    VND (the user's choice, 2026-10-19). Returns the cells and the next free row."""
    rate = project.get('contingency_rate', 0.02)
    section(ws, r, 'CONTINGENCY (rate x in-house staff + OPEX less repairs, at 100% fill)', ncols=6); r += 1
    for c, h in enumerate(['Item', 'Must-Have Only (VND)', 'Full Cost (VND)'], start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    r += 1

    def must(cat_rows, necessity_map, names):
        return [f'B{cat_rows[n]}' for n in names if necessity_map.get(n, ('',))[0] == 'Must-Have']

    staff_rows = item_rows.get('Staff', {})
    outsourced = [n for n, f in staff['category_annual_cells'].items()
                  if n in staff_rows and str(f).startswith("='Service'!")]
    opex_rows = item_rows.get('OPEX', {})
    repairs = [CONTINGENCY_REPAIRS_ITEM] if CONTINGENCY_REPAIRS_ITEM in opex_rows else []

    def less(base, cells):
        return f"={base or 0}" + ''.join(f'-{c}' for c in cells)

    rows = [
        ('Contingency Rate (Project Info, the deliverable\'s EM#/ES#/EE# rate)', rate, rate),
        ('In-house staff (less the ' + '/'.join(outsourced) + ' vendor contracts)' if outsourced else 'In-house staff',
         less(must_have_cells['staff'], must(staff_rows, STAFF_NECESSITY, outsourced)),
         less(total_cells['staff'], [f'B{staff_rows[n]}' for n in outsourced])),
        ('OPEX less Repairs & Maintenance',
         less(must_have_cells['opex'], must(opex_rows, OPEX_NECESSITY, repairs)),
         less(total_cells['opex'], [f'B{opex_rows[n]}' for n in repairs])),
    ]
    first = r
    for label, b, c in rows:
        ws.cell(row=r, column=1, value=label).border = BORDER
        ws.cell(row=r, column=1).alignment = LEFT
        for col, v in ((2, b), (3, c)):
            cell = ws.cell(row=r, column=col, value=v)
            cell.number_format = '0.0%' if r == first else MONEY_FMT
            cell.border = BORDER
        r += 1
    ws.cell(row=r, column=1, value='Contingency = Rate x (In-house staff + OPEX less repairs)').font = SECTION_FONT
    for col in ('B', 'C'):
        cell = ws[f'{col}{r}']
        cell.value = f'=ROUND({col}{first}*({col}{first + 1}+{col}{first + 2}),0)'
        cell.number_format = MONEY_FMT
        cell.font = SECTION_FONT
    total_row = r
    r += 1
    ws.cell(row=r, column=1,
            value=('Same rate as the deliverable\'s contingency lines, over this workbook\'s own costs in the same scope, '
                   'at 100% fill. It does not equal the deliverable\'s VND: the deliverable is year 1 on the fill-up '
                   'curve and its service contingency also covers the outsourced contracts. Total Profit Value and '
                   'every cost total built from it include this line (Summary toggle picks the column).')
            ).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:F{r}')
    ws.row_dimensions[r].height = 40
    r += 2
    return dict(rate_cell=f'B{first}', must_have_cell=f'B{total_row}', total_cell=f'C{total_row}', next_row=r)


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
        item_rows[category_label] = {name: cat_first_row + i for i, name in enumerate(ordered)}
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
    item_rows = {}
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

    cont = _write_contingency_section(ws, r, project, staff, item_rows,
                                      dict(staff=f'B{staff_total_row}', opex=f'B{opex_total_row}'),
                                      dict(staff=staff_must_have_row, opex=opex_must_have_row))
    r = cont['next_row']

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
                opex_total_cell=f"'Cost Priority'!B{opex_total_row}",
                contingency_rate_cell=f"'Cost Priority'!{cont['rate_cell']}",
                contingency_must_have_cell=f"'Cost Priority'!{cont['must_have_cell']}",
                contingency_total_cell=f"'Cost Priority'!{cont['total_cell']}")


def build_year1_strategy_sheet(wb, project, mgmt, cost_priority, extra_revenue):
    """How to avoid negative profit before the building reaches full occupancy. Every number in
    LEVERS 1-4 is a live cross-sheet formula reading cells this workbook already computes
    elsewhere (Cost Basis toggle, Cost Priority necessity split, the parking-lease alternative,
    elevator advertising) — nothing new is estimated here. LEVER 5 is explicitly labeled
    ADVISORY: real industry practice, not modeled as a workbook formula, because none of it
    reduces to a cell in THIS project's real source data the way Levers 1-4 do."""
    ws = wb.create_sheet('Year 1 Strategy')
    title_block(ws, 'Year 1 Strategy — Avoiding Negative Profit Before Full Occupancy',
                _stable_prefix(project, SENSITIVITY_STABLE_NOTE_EN) +
                'Real projects rarely open at 90%+ fill. This sheet lays out how to still clear Year 1 while '
                'ramping up — Levers 1-4 are live formulas reading numbers already built into this workbook; '
                'Lever 5 is real-world practice this workbook doesn\'t model with a cell. See NOTES at the bottom.',
                'A1:F1')

    MUST_HAVE = dict(staff=cost_priority['staff_must_have_cell'], capex=cost_priority['capex_must_have_cell'],
                      opex=cost_priority['opex_must_have_cell'], cont=cost_priority['contingency_must_have_cell'])
    FULL = dict(staff=cost_priority['staff_total_cell'], capex=cost_priority['capex_total_cell'],
                opex=cost_priority['opex_total_cell'], cont=cost_priority['contingency_total_cell'])
    MGMT_100 = f"'Management Fee'!{mgmt['annual_revenue_cell']}"

    r = 4
    section(ws, r, 'THE PROBLEM, IN NUMBERS', ncols=5); r += 1
    ws.cell(row=r, column=1,
            value=('Below the breakeven fill % (A), Must-Have-only staffing still loses money — no lever below '
                   'closes that gap on its own, only occupancy or a developer subsidy does. Between (A) and (B), '
                   'switching to Must-Have-only staffing (Lever 1) is the difference between profit and loss at '
                   'that fill level. Above (B), even the full service tier clears Year 1.')
            ).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:F{r}')
    ws.row_dimensions[r].height = 40
    r += 1
    ws.cell(row=r, column=1, value='(A) Breakeven Fill % — Must-Have Only staffing').font = Font(bold=True)
    c = ws.cell(row=r, column=2, value=f"=({MUST_HAVE['staff']}+{MUST_HAVE['opex']}+{MUST_HAVE['capex']}+{MUST_HAVE['cont']})/{MGMT_100}")
    c.number_format = '0.0%'
    c.font = Font(bold=True)
    c.fill = HIGHLIGHT_FILL
    A_CELL = f'B{r}'
    r += 1
    ws.cell(row=r, column=1, value='(B) Breakeven Fill % — Full Cost (all service tiers)').font = Font(bold=True)
    c = ws.cell(row=r, column=2, value=f"=({FULL['staff']}+{FULL['opex']}+{FULL['capex']}+{FULL['cont']})/{MGMT_100}")
    c.number_format = '0.0%'
    c.font = Font(bold=True)
    c.fill = HIGHLIGHT_FILL
    B_CELL = f'B{r}'
    r += 2

    section(ws, r, 'LEVER 1 — Cost Basis Toggle (Summary sheet, cell B11)', ncols=5); r += 1
    ws.cell(row=r, column=1,
            value=(f'Switching the Summary sheet\'s toggle to "Must-Have Only" during ramp-up drops the breakeven '
                   f'fill % from (B) to (A) above — a real, computed gap, not a rule of thumb. It works because '
                   f'Optional roles (Shift Leader especially — a 24/7-coverage role on the same scale as Security, '
                   f'not a minor add-on) and Conditional amenity-dependent roles can be phased in only once '
                   f'occupancy or amenity usage actually justifies them, rather than staffed from day one.')
            ).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:F{r}')
    ws.row_dimensions[r].height = 55
    r += 1
    ws.cell(row=r, column=1, value='Cost deferred by staying Must-Have-only (Optional + Conditional, all categories)').font = Font(bold=True)
    c = ws.cell(row=r, column=2,
                value=f"=({FULL['staff']}-{MUST_HAVE['staff']})+({FULL['opex']}-{MUST_HAVE['opex']})+({FULL['capex']}-{MUST_HAVE['capex']})"
                      f"+({FULL['cont']}-{MUST_HAVE['cont']})")
    c.number_format = MONEY_FMT
    c.font = Font(bold=True)
    c.fill = HIGHLIGHT_FILL
    r += 2

    section(ws, r, 'LEVER 2 — Phase Non-Essential Capex (Cost Priority sheet)', ncols=5); r += 1
    ws.cell(row=r, column=1,
            value=('The Conditional/Mixed Capex categories (Amenity Area, Public Area) are one-time purchases, not '
                   'recurring cost — deferring them doesn\'t just lower Year 1 cost, it delays the cash outlay '
                   'itself until amenity usage or move-ins justify buying the equipment.')
            ).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:F{r}')
    ws.row_dimensions[r].height = 40
    r += 1
    ws.cell(row=r, column=1, value='Deferrable Capex (Conditional + Mixed categories, VND)').font = Font(bold=True)
    c = ws.cell(row=r, column=2, value=f"={FULL['capex']}-{MUST_HAVE['capex']}")
    c.number_format = MONEY_FMT
    c.font = Font(bold=True)
    c.fill = HIGHLIGHT_FILL
    r += 2

    section(ws, r, 'LEVER 3 — Lease Parking to an Operator Instead of Per-Vehicle Billing (Additional Revenue sheet)', ncols=5); r += 1
    ws.cell(row=r, column=1,
            value=('A fixed monthly lease to a parking operator trades upside at high occupancy for a guaranteed '
                   'floor at low occupancy — exactly what Year 1 needs. Below the breakeven % below, leasing '
                   'collects more than per-vehicle billing would at that same fill level (real comparable data, '
                   'not a rule of thumb — see Additional Revenue sheet for the 3 real comparables behind it).')
            ).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:F{r}')
    ws.row_dimensions[r].height = 40
    r += 1
    ws.cell(row=r, column=1, value='Breakeven fill % — below this, leasing beats per-vehicle billing').font = Font(bold=True)
    c = ws.cell(row=r, column=2, value=f"={extra_revenue['lease_breakeven_cell']}")
    c.number_format = '0.0%'
    c.font = Font(bold=True)
    c.fill = HIGHLIGHT_FILL
    r += 2

    section(ws, r, 'LEVER 4 — Elevator Advertising (Additional Revenue sheet)', ncols=5); r += 1
    ws.cell(row=r, column=1,
            value=('Ad revenue from elevator/lobby screens doesn\'t depend on residential fill % the way the '
                   'management fee does — it\'s driven by foot traffic and device placement, so it\'s cash flow '
                   'that doesn\'t wait for occupancy to ramp up.')
            ).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:F{r}')
    ws.row_dimensions[r].height = 40
    r += 1
    ws.cell(row=r, column=1, value='Annual elevator advertising revenue (VND)').font = Font(bold=True)
    c = ws.cell(row=r, column=2, value=f"={extra_revenue['advertising_annual_cell']}")
    c.number_format = MONEY_FMT
    c.font = Font(bold=True)
    c.fill = HIGHLIGHT_FILL
    r += 2

    section(ws, r, 'LEVER 5 — Real Industry Practices (ADVISORY — not modeled as a formula in this workbook)', ncols=5); r += 1
    ws.cell(row=r, column=1,
            value=('These are genuine, commonly-used practices in Vietnamese residential management, but none of '
                   'them reduce to a cell in this project\'s real source data the way Levers 1-4 do — shown here '
                   'as advisory context, not computed figures.')
            ).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:F{r}')
    ws.row_dimensions[r].height = 25
    r += 1
    advisory_headers = ['Practice', 'How it helps Year 1']
    for c, h in enumerate(advisory_headers, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    ws.merge_cells(f'B{r}:F{r}')
    r += 1
    advisory_rows = [
        ('Developer revenue-guarantee / subsidy agreement',
         'During handover ramp-up, the developer (not the PM company) contractually covers the gap between actual '
         'fee collections and the operating-cost floor for an agreed period — the developer, not the building, '
         'carries unsold/unoccupied-unit risk.'),
        ('Handover-linked fee collection, front-loaded',
         'Management fee is typically collectible from each unit\'s own handover date, not building completion — '
         'developers commonly accelerate handover schedules specifically to front-load fee collection ahead of '
         'full occupancy.'),
        ('Tiered / early-bird parking pricing',
         'A discounted monthly rate for the first 6-12 months accelerates parking lease-up, raising realized '
         'occupancy faster than flat pricing would.'),
        ('External / non-resident parking rental',
         'Renting excess slots to nearby offices or non-owner residents fills capacity independent of the building\'s '
         'own move-in pace, rather than waiting for resident demand alone.'),
    ]
    for practice, why in advisory_rows:
        ws.cell(row=r, column=1, value=practice).border = BORDER
        ws.cell(row=r, column=1).alignment = LEFT
        ws.cell(row=r, column=1).font = Font(bold=True)
        ws.merge_cells(f'B{r}:F{r}')
        c2 = ws.cell(row=r, column=2, value=why)
        c2.border = BORDER
        c2.alignment = LEFT
        for col in range(2, 7):
            ws.cell(row=r, column=col).border = BORDER
        ws.row_dimensions[r].height = 40
        r += 1
    r += 1

    section(ws, r, 'NOTES', ncols=4); r += 1
    notes = [
        '(A)/(B) Both are LIVE formulas: (Selected costs at that basis) ÷ (Management Fee Revenue at 100% fill). They '
        'move automatically if project inputs (NFA, headcount, rates) change and the workbook is regenerated.',
        'Lever 1 pulls the same Cost Priority "of which Must-Have"/category-total cells the Summary sheet\'s toggle '
        'uses — necessity classification (Must-Have/Conditional/Optional) is domain judgment, not extracted from a '
        'real data source; see Cost Priority sheet for exactly which items are in which bucket.',
        'Lever 2 is the same VND gap as Lever 1\'s Capex component, isolated here because — unlike Staff/OPEX, which '
        'are recurring — deferring Capex delays an actual one-time cash outlay, not just a Year 1 expense line.',
        'Levers 3-4 are real data (see Additional Revenue sheet for the comparables and rates behind them); neither '
        'is currently added into the Summary sheet\'s Total Profit Value (see that sheet\'s NOTE 8).',
        'Lever 5 is included for completeness because it\'s standard industry practice, not because this workbook '
        'has real data behind it for THIS project — treat it as a checklist to raise with the developer/client, not '
        'a number to plug in.',
    ]
    for note in notes:
        ws.cell(row=r, column=1, value=note).font = Font(italic=True, size=9, color='7F7F7F')
        ws.cell(row=r, column=1).alignment = LEFT
        ws.merge_cells(f'A{r}:F{r}')
        ws.row_dimensions[r].height = 28
        r += 1

    for col, w in {'A': 46, 'B': 20, 'C': 20, 'D': 20, 'E': 20, 'F': 20}.items():
        ws.column_dimensions[col].width = w

    return dict(breakeven_must_have_cell=f"'Year 1 Strategy'!{A_CELL}",
                breakeven_full_cost_cell=f"'Year 1 Strategy'!{B_CELL}")


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
    SELECTED_CONTINGENCY_CELL = _selected('Selected Contingency (per toggle, VND; Cost Priority sheet)',
                                          cost_priority['contingency_must_have_cell'],
                                          cost_priority['contingency_total_cell'])
    # No spacer row after it: the contingency takes the old spacer, so Total Profit Value and the Key Figures stay
    # on the rows verification/baseline.py reads (Summary B19, B33:B40).

    section(ws, r, 'TOTAL PROFIT VALUE (per Cost Basis toggle above), AT 100% FILL', ncols=5); r += 1
    ws.cell(row=r, column=1, value='Total Profit Value = Mgmt Fee Revenue (3) − Selected Staff (4) − Selected OPEX (7) − Selected Capex (6) − Contingency (10)').font = Font(bold=True, size=12)
    c = ws.cell(row=r, column=2,
                value=f"='Management Fee'!{mgmt['annual_revenue_cell']}-{SELECTED_STAFF_CELL}"
                      f"-{SELECTED_OPEX_CELL}-{SELECTED_CAPEX_CELL}-{SELECTED_CONTINGENCY_CELL}")
    c.number_format = MONEY_FMT
    c.font = Font(bold=True, size=12)
    c.fill = HIGHLIGHT_FILL
    PROFIT_CELL = f'B{r}'
    r += 1
    ws.cell(row=r, column=1, value='Margin (Total Profit Value ÷ Mgmt Fee Revenue) (9)').font = Font(bold=True, size=12)
    c = ws.cell(row=r, column=2, value=f"={PROFIT_CELL}/('Management Fee'!{mgmt['annual_revenue_cell']})")
    c.number_format = '+0.0%;-0.0%'
    c.font = Font(bold=True, size=12)
    c.fill = HIGHLIGHT_FILL
    MARGIN_CELL = f'B{r}'
    r += 1
    ws.cell(row=r, column=1, value='Markup (Total Profit Value ÷ Selected Costs) — for pricing reference only').font = Font(size=10, italic=True)
    c = ws.cell(row=r, column=2,
                value=f"={PROFIT_CELL}/({SELECTED_STAFF_CELL}+{SELECTED_OPEX_CELL}+{SELECTED_CAPEX_CELL}"
                      f"+{SELECTED_CONTINGENCY_CELL})")
    c.number_format = '+0.0%;-0.0%'
    c.font = Font(size=10, italic=True)
    MARKUP_CELL = f'B{r}'
    r += 1
    ws.cell(row=r, column=1, value=('Margin (profit ÷ revenue) is the standard accounting definition — use this for '
                                     'reporting/benchmarking. Markup (profit ÷ cost) answers a different question '
                                     '("how far above cost is the fee priced") and is shown only as a secondary '
                                     'reference; the two will always differ for the same underlying numbers. '
                                     '"Must-Have Only" excludes Conditional (pool/garden-dependent) and Optional '
                                     '(service-tier choices, e.g. Shift Leader/Customer Service/Reception) costs '
                                     'entirely, not just discounts them — see Cost Priority sheet for exactly which '
                                     'items. "Full Cost" includes everything. At full (100%) fill — see FILL-UP '
                                     'SCENARIOS below for earlier-stage ramp-up. Year 1 specific, not steady-state '
                                     '(would exclude the one-time Capex).')
            ).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:E{r}')
    ws.row_dimensions[r].height = 68
    r += 2

    NET_TOTAL_CELLS = dict(
        mgmt=f"'Management Fee'!{mgmt['annual_revenue_cell']}",
        extra=f"'Additional Revenue'!{extra_revenue['annual_total_cell']}",
    )
    section(ws, r, 'FILL-UP SCENARIOS — revenue ramps with fill %, costs (per toggle above) assumed at full regardless', ncols=6); r += 1
    ws.cell(row=r, column=1,
            value=(_stable_prefix(project, SENSITIVITY_STABLE_NOTE_EN) +
                   'Simplifying assumption, not derived from real data: Mgmt Fee Revenue (3) scales with fill % (fewer '
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
    fill_headers = ['Fill %', 'Mgmt Fee Revenue (3)', 'Staff (4) + OPEX (7) + Capex (6) + Contingency (10) — per toggle',
                     'Total Profit Value', 'Margin (Profit ÷ Revenue)', 'Additional Revenue (8) — reference only']
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
        c3 = ws.cell(row=r, column=3, value=f"={SELECTED_STAFF_CELL}+{SELECTED_OPEX_CELL}+{SELECTED_CAPEX_CELL}"
                                             f"+{SELECTED_CONTINGENCY_CELL}")
        c3.number_format = MONEY_FMT
        c3.border = BORDER
        c4 = ws.cell(row=r, column=4, value=f'=B{r}-C{r}')
        c4.number_format = MONEY_FMT
        c4.border = BORDER
        c4.font = Font(bold=True)
        c5 = ws.cell(row=r, column=5, value=f'=D{r}/B{r}')
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
        ('(9) Margin (Total Profit Value ÷ Mgmt Fee Revenue)', f'={MARGIN_CELL}'),
        ('(10) Contingency — per Cost Basis toggle (VND)', f"={SELECTED_CONTINGENCY_CELL}"),
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
        '(10) Contingency at the deliverable\'s EM#/ES#/EE# rate, over in-house staff (4, less the Security/Cleaning/Landscape vendor contracts) plus OPEX (7) less Repairs & Maintenance, per the toggle, at 100% fill — see Cost Priority sheet. IN Total Profit Value. Not equal to the deliverable\'s year-1 contingency, which follows the fill-up curve and also covers the outsourced contracts.',
        '(9) Margin, the standard accounting definition (profit ÷ revenue), not markup (profit ÷ cost) — the two answer different questions and will always differ for the same numbers. Markup is shown as a secondary reference next to Total Profit Value above, for pricing conversations specifically.',
    ]
    for note in notes:
        ws.cell(row=r, column=1, value=note).font = Font(italic=True, size=9, color='7F7F7F')
        ws.cell(row=r, column=1).alignment = LEFT
        ws.merge_cells(f'A{r}:D{r}')
        ws.row_dimensions[r].height = 28
        r += 1

    for col, w in {'A': 42, 'B': 24, 'C': 24, 'D': 20, 'E': 20, 'F': 24}.items():
        ws.column_dimensions[col].width = w

    return dict(toggle_cell=f"'Summary'!{TOGGLE_CELL}",
                selected_staff_cell=f"'Summary'!{SELECTED_STAFF_CELL}",
                selected_opex_cell=f"'Summary'!{SELECTED_OPEX_CELL}",
                selected_capex_cell=f"'Summary'!{SELECTED_CAPEX_CELL}",
                selected_contingency_cell=f"'Summary'!{SELECTED_CONTINGENCY_CELL}",
                profit_cell=f"'Summary'!{PROFIT_CELL}",
                margin_cell=f"'Summary'!{MARGIN_CELL}")


YEAR_FILL_PATH = [('Year 1', 0.50), ('Year 2', 0.70), ('Year 3', 0.90), ('Year 4', 1.00)]

# 'Stable Operation?' = Yes on the intake form (change use-operating-project-actuals, P3): the yearly and
# monthly views run at fill_curve.STABLE_FILL in every period, and the notes say so. The two what-if
# tables (Summary 'Fill-up Scenarios', 'Year 1 Strategy') stay as sensitivities with one line saying the
# budget itself uses 100% (answer A1, 2026-10-11).
STABLE_NOTE_EN = ("STABLE OPERATION: the intake form declares this project at stable operation (Stable "
                  "Operation? = Yes), so every year and month on this sheet is at 100% fill; the new-building "
                  "50/70/90/100% path described here is not applied. ")
SENSITIVITY_STABLE_NOTE_EN = ("STABLE OPERATION: the budget uses 100% fill (intake 'Stable Operation?' = Yes); "
                              "this table is a sensitivity for reference only. ")


def _year_fill_path(project):
    """YEAR_FILL_PATH, or every year at the stable fill when the project is declared at stable operation."""
    if project.get('stable_operation'):
        return [(label, _STABLE_FILL) for label, _pct in YEAR_FILL_PATH]
    return YEAR_FILL_PATH


def _stable_prefix(project, note=STABLE_NOTE_EN):
    return note if project.get('stable_operation') else ''

# Disclosed assumption, NOT real data: Capex on the rollover sheets follows a sinking-fund
# pattern — Year 1 always carries the full initial fit-out lump sum (matches the Summary/Cost
# Priority sheets' "Year-1 lump sum" framing exactly), repeating in full for every year before
# project['capex_drop_year'] (an input, default Year 2 — change derive-capex-reserve-rate, task
# 4), which drops to a smaller ongoing reserve contribution instead of repeating the full purchase
# (equipment like elevators/generators gets replaced on a multi-year cycle, not annually). The
# reserve rate itself is DERIVED from real
# projects — see _load_capex_reserve() below — not assumed.
CAPEX_RESERVE_CSV = os.path.join(BUDGET_AGENT, 'data', 'generation_A_star_schema',
                                 'Fact_CapexReserve.csv')


def _load_capex_reserve():
    """Derive the ongoing Capex reserve rate from what real projects actually did.

    Replaces a hardcoded 0.10 whose own comment admitted it was "a commonly cited
    property-management rule of thumb, NOT this project's own real reserve policy, which isn't in
    the source data". It IS in the source data — see rescan_capex_reserve.py, which measures it.

    Uses the ANNUALISED reading: three of the four reserve observations write exactly Year-1 / 12
    into a year that is 8, 9 or 12 months long, so the literal ratio understates a full year for the
    short ones. Both readings are recorded in the table; the literal mean is 8.46%, the annualised
    10.93%. Neither is anywhere near the 0.1% that EXENSIVE LOGIC.xlsx states — that figure would
    imply a thousand-year replacement cycle, and correcting Savills' document is their call.

    Full-repeat years (a later year at ~100% of Year 1, i.e. equipment bought across two years) are
    excluded: they set the DROP YEAR, not the rate.
    """
    import csv as _csv
    if not os.path.exists(CAPEX_RESERVE_CSV):
        raise FileNotFoundError(
            f'Capex reserve reference data not found at {CAPEX_RESERVE_CSV}. Run '
            f'"python rescan_capex_reserve.py" to extract it from the real project budgets. '
            f'Refusing to fall back to a hardcoded rate — an unevidenced reserve rate is exactly '
            f'what this reads real data to avoid.')
    with open(CAPEX_RESERVE_CSV, encoding='utf-8-sig') as fh:
        rows = [r for r in _csv.DictReader(fh) if r.get('ObservationType') == 'reserve']
    if not rows:
        raise ValueError(
            f'{CAPEX_RESERVE_CSV} contains no "reserve" observations — only full-repeat years, or '
            f'nothing at all. Re-run rescan_capex_reserve.py.')
    rates = [float(r['ImpliedRateAnnualised']) for r in rows]
    names = [r['Project'].split(' - ')[-1][:28] for r in rows]
    return (sum(rates) / len(rates), len(rates), min(rates), max(rates), names)


(CAPEX_RESERVE_RATE, CAPEX_RESERVE_N, CAPEX_RESERVE_LO,
 CAPEX_RESERVE_HI, CAPEX_RESERVE_PROJECTS) = _load_capex_reserve()

# One sentence that travels with the rate wherever it is quoted, so the figure is never shown
# without its evidence and its sample size.
CAPEX_RESERVE_SOURCE = (
    f'{CAPEX_RESERVE_RATE:.1%} is DERIVED from {CAPEX_RESERVE_N} real Savills projects '
    f'(range {CAPEX_RESERVE_LO:.1%}-{CAPEX_RESERVE_HI:.1%}), measured as each project\'s later-year '
    f'Capex against its Year-1 Capex and annualised for short years — see Fact_CapexReserve.csv and '
    f'rescan_capex_reserve.py. It is NOT a rule of thumb. Note the written cost spec '
    f'(EXENSIVE LOGIC.xlsx, EN1-EN3) states ~0.1%, which no real project comes close to.')


# Change derive-capex-reserve-rate, task 4 (2026-09-21) — the drop-to-reserve year is now an input
# (project['capex_drop_year'], default 2, see generate_project_budget._resolve_capex_drop_year).
# Shared by both the Owner Operating Position and Savills Fee Position sheets, yearly and monthly
# tables alike, so the four write sites cannot drift on what "the drop year" means.
def _capex_reserve_formula(cell, year_num, drop_year):
    """(formula, is_full_purchase_year) for one row of the 4-year yearly sinking-fund table.
    Years before `drop_year` repeat the full lump-sum purchase (like Year 1 always does); `drop_year`
    and every year after it carry the derived ongoing reserve rate instead."""
    full = year_num < drop_year
    formula = f'={cell}' if full else f'={cell}*{CAPEX_RESERVE_RATE}'
    return formula, full


def _capex_reserve_monthly_formula(cell, month_num, drop_year):
    """(formula, fill_color_or_None) for one row of the 48-month monthly sinking-fund breakdown —
    same drop-year logic as _capex_reserve_formula, but the lump sum for a full-purchase year lands
    on that year's first month only, with its other 11 months at zero."""
    year_num = (month_num - 1) // 12 + 1
    month_in_year = (month_num - 1) % 12 + 1
    if year_num < drop_year:
        if month_in_year == 1:
            return f'={cell}', 'FFF7CC'
        return 0, None
    return f'={cell}*{CAPEX_RESERVE_RATE}/12', 'E2EFDA'


def build_owner_operating_position_sheet(wb, project, mgmt, summary, year1_strategy):
    """Tracks whether the BUILDING's own operating account — resident collections vs. Staff/OPEX/
    Capex reimbursement, deliberately EXCLUDING Savills' own fee — becomes self-sustaining as fill
    ramps year over year, with a running cumulative balance. Unlike the Savills Fee Position sheet,
    this one genuinely CAN and does cross from deficit to surplus within the model: Collections
    scale with fill % up to 100%, while the operating cost floor (no Savills profit layered on
    top) sits below that ceiling once fill passes the breakeven % already computed on the Year 1
    Strategy sheet. Cross-references that sheet's (A)/(B) cells rather than recomputing them."""
    ws = wb.create_sheet('Owner Operating Position')
    title_block(ws, "Owner Operating Position — Does the Building's Own Account Self-Fund?",
                'Resident collections vs. the building\'s own Staff/OPEX/Capex reimbursement (per the Cost Basis '
                'toggle, NOT including Savills\' own fee) — tracked year by year as fill ramps, with a running '
                'cumulative balance. Years/fill path are a disclosed simplifying assumption — see NOTES.', 'A1:F1')

    MGMT_100 = f"'Management Fee'!{mgmt['annual_revenue_cell']}"
    RECURRING_COST = (f"({summary['selected_staff_cell']}+{summary['selected_opex_cell']}"
                      f"+{summary['selected_contingency_cell']})")
    CAPEX_CELL = summary['selected_capex_cell']
    DROP_YEAR = project['capex_drop_year']
    DROP_YEAR_NOTE = (f'the evidenced default of Year {DROP_YEAR}' if project['capex_drop_year_is_default']
                       else f"this project's own stated Year {DROP_YEAR}")

    r = 4
    section(ws, r, 'YEAR-BY-YEAR OPERATING POSITION', ncols=6); r += 1
    ws.cell(row=r, column=1,
            value=(_stable_prefix(project) +
                   f'Simplifying assumption, not derived from a real ramp-up schedule: treats the same 50/70/90/100% '
                   f'fill path used elsewhere in this workbook as 4 sequential years, one stage per year. Staff/OPEX '
                   f'are held at full each year (per the Cost Basis toggle). Capex follows a sinking-fund pattern: '
                   f'Year 1 carries the full initial lump sum (matching the Summary/Cost Priority sheets exactly), '
                   f'repeating in full for every year before {DROP_YEAR_NOTE}, which drops to a '
                   f'{CAPEX_RESERVE_RATE:.1%} ongoing reserve contribution instead — a disclosed assumption, not '
                   f'this project\'s own real reserve policy (see NOTES).')
            ).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:F{r}')
    ws.row_dimensions[r].height = 55
    r += 1
    headers = ['Year', 'Fill %', 'Annual Collections (VND)', 'Staff + OPEX + Contingency, per toggle (VND)',
               'Capex — per sinking-fund (VND)', 'Total Operating Cost (VND)',
               'Annual Surplus / (Deficit) (VND)', 'Cumulative Balance (VND)']
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    r += 1
    year_first_row = r
    prev_cum_cell = None
    for i, (year_label, pct) in enumerate(_year_fill_path(project)):
        ws.cell(row=r, column=1, value=year_label).border = BORDER
        ws.cell(row=r, column=1).alignment = CENTER
        ws.cell(row=r, column=2, value=pct).number_format = '0%'
        ws.cell(row=r, column=2).border = BORDER
        ws.cell(row=r, column=2).alignment = CENTER
        c3 = ws.cell(row=r, column=3, value=f'={MGMT_100}*B{r}')
        c3.number_format = MONEY_FMT
        c3.border = BORDER
        c4 = ws.cell(row=r, column=4, value=f'={RECURRING_COST}')
        c4.number_format = MONEY_FMT
        c4.border = BORDER
        capex_formula, capex_is_full = _capex_reserve_formula(CAPEX_CELL, i + 1, DROP_YEAR)
        c5 = ws.cell(row=r, column=5, value=capex_formula)
        c5.number_format = MONEY_FMT
        c5.border = BORDER
        c5.fill = PatternFill('solid', fgColor='FFF7CC' if capex_is_full else 'E2EFDA')
        c6 = ws.cell(row=r, column=6, value=f'=D{r}+E{r}')
        c6.number_format = MONEY_FMT
        c6.border = BORDER
        c7 = ws.cell(row=r, column=7, value=f'=C{r}-F{r}')
        c7.number_format = MONEY_FMT
        c7.border = BORDER
        c7.font = Font(bold=True)
        cum_formula = f'=G{r}' if prev_cum_cell is None else f'={prev_cum_cell}+G{r}'
        c8 = ws.cell(row=r, column=8, value=cum_formula)
        c8.number_format = MONEY_FMT
        c8.border = BORDER
        c8.font = Font(bold=True)
        prev_cum_cell = f'H{r}'
        r += 1
    year_last_row = r - 1

    green_rule = FormulaRule(formula=[f'H{year_first_row}>=0'], fill=PatternFill('solid', fgColor='C6EFCE'))
    red_rule = FormulaRule(formula=[f'H{year_first_row}<0'], fill=PatternFill('solid', fgColor='FFC7CE'))
    ws.conditional_formatting.add(f'H{year_first_row}:H{year_last_row}', green_rule)
    ws.conditional_formatting.add(f'H{year_first_row}:H{year_last_row}', red_rule)
    r += 1
    ws.cell(row=r, column=1,
            value=(f'Capex column: yellow = full lump-sum purchase, green = reserve contribution '
                   f'({CAPEX_RESERVE_RATE:.1%} of Year 1) — drops at {DROP_YEAR_NOTE}.')
            ).font = Font(italic=True, size=8, color='7F7F7F')
    r += 1

    section(ws, r, 'MONTHLY BREAKDOWN (48 months, smooth ramp — see NOTES for the interpolation assumption)', ncols=8); r += 1
    ws.cell(row=r, column=1,
            value=(_stable_prefix(project) +
                   f'Fill % ramps smoothly month to month toward the SAME 50/70/90/100% year-end anchors used above '
                   f'— starting near 0%, not flat for all 12 months of Year 1. This shows worse early-month numbers '
                   f'than the flat yearly average above, on purpose: a real building doesn\'t open at 50% fill on '
                   f'day 1. Capex follows the same sinking-fund pattern as the yearly table: a full lump sum hits '
                   f'the first month of every year before {DROP_YEAR_NOTE} (Months 2-12 of that year have no '
                   f'additional Capex), then every month from {DROP_YEAR_NOTE}\'s own first month onward carries '
                   f'a {CAPEX_RESERVE_RATE:.1%} reserve contribution spread evenly per month.')
            ).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:H{r}')
    ws.row_dimensions[r].height = 50
    r += 1
    m_headers = ['Month', 'Fill %', 'Monthly Collections (VND)', 'Staff + OPEX + Contingency (VND)', 'Capex — per sinking-fund (VND)',
                 'Total Operating Cost (VND)', 'Monthly Surplus / (Deficit) (VND)', 'Margin (Profit ÷ Revenue)',
                 'Cumulative Balance (VND)']
    for c, h in enumerate(m_headers, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    r += 1
    month_first_row = r
    prev_cum_cell = None
    for month_num, month_label, fill in _monthly_fill_path(bool(project.get('stable_operation'))):
        ws.cell(row=r, column=1, value=month_label).border = BORDER
        ws.cell(row=r, column=1).alignment = CENTER
        c2 = ws.cell(row=r, column=2, value=fill)
        c2.number_format = '0.0%'
        c2.border = BORDER
        c2.alignment = CENTER
        c3 = ws.cell(row=r, column=3, value=f'=({MGMT_100}/12)*B{r}')
        c3.number_format = MONEY_FMT
        c3.border = BORDER
        c4 = ws.cell(row=r, column=4, value=f'={RECURRING_COST}/12')
        c4.number_format = MONEY_FMT
        c4.border = BORDER
        capex_formula, capex_fill = _capex_reserve_monthly_formula(CAPEX_CELL, month_num, DROP_YEAR)
        c5 = ws.cell(row=r, column=5, value=capex_formula)
        c5.number_format = MONEY_FMT
        c5.border = BORDER
        if capex_fill:
            c5.fill = PatternFill('solid', fgColor=capex_fill)
        c6 = ws.cell(row=r, column=6, value=f'=D{r}+E{r}')
        c6.number_format = MONEY_FMT
        c6.border = BORDER
        c7 = ws.cell(row=r, column=7, value=f'=C{r}-F{r}')
        c7.number_format = MONEY_FMT
        c7.border = BORDER
        c8 = ws.cell(row=r, column=8, value=f'=G{r}/C{r}')
        c8.number_format = '+0.0%;-0.0%'
        c8.border = BORDER
        cum_formula = f'=G{r}' if prev_cum_cell is None else f'={prev_cum_cell}+G{r}'
        c9 = ws.cell(row=r, column=9, value=cum_formula)
        c9.number_format = MONEY_FMT
        c9.border = BORDER
        c9.font = Font(bold=True)
        prev_cum_cell = f'I{r}'
        r += 1
    month_last_row = r - 1
    ws.conditional_formatting.add(f'I{month_first_row}:I{month_last_row}',
                                   FormulaRule(formula=[f'I{month_first_row}>=0'], fill=PatternFill('solid', fgColor='C6EFCE')))
    ws.conditional_formatting.add(f'I{month_first_row}:I{month_last_row}',
                                   FormulaRule(formula=[f'I{month_first_row}<0'], fill=PatternFill('solid', fgColor='FFC7CE')))
    r += 1

    section(ws, r, 'CROSS-CHECK — breakeven fill %, from the Year 1 Strategy sheet', ncols=5); r += 1
    ws.cell(row=r, column=1,
            value=('The year the cumulative balance above turns green (≥0) should be the first year whose Fill % '
                   'passes one of these two breakeven thresholds — whichever matches the Cost Basis toggle\'s '
                   'current setting on the Summary sheet. Not a new calculation, just the same numbers checked '
                   'two ways.')
            ).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:E{r}')
    ws.row_dimensions[r].height = 40
    r += 1
    ws.cell(row=r, column=1, value='(A) Breakeven Fill % — Must-Have Only staffing').font = Font(bold=True)
    c = ws.cell(row=r, column=2, value=f"={year1_strategy['breakeven_must_have_cell']}")
    c.number_format = '0.0%'
    c.font = Font(bold=True)
    r += 1
    ws.cell(row=r, column=1, value='(B) Breakeven Fill % — Full Cost (all service tiers)').font = Font(bold=True)
    c = ws.cell(row=r, column=2, value=f"={year1_strategy['breakeven_full_cost_cell']}")
    c.number_format = '0.0%'
    c.font = Font(bold=True)
    r += 2

    section(ws, r, 'NOTES', ncols=4); r += 1
    notes = [
        'This is the building\'s OWN operating account — Staff/OPEX/Capex reimbursement only, deliberately '
        'excluding Savills\' own fee. It genuinely crosses from deficit to surplus once collections pass the '
        'operating cost floor — unlike the Savills Fee Position sheet, whose "required" line includes Savills\' '
        'profit target on top and never structurally exceeds 100%-fill revenue by construction.',
        'Year 1-4 / 50-100% fill is the same disclosed simplifying assumption used on the Summary sheet\'s Fill-up '
        'Scenarios and the Year 1 Strategy sheet — not a contractually defined ramp-up schedule.',
        'The Monthly Breakdown adds ONE more assumption on top of that: fill % ramps smoothly (linearly) between '
        'the same year-end anchors, starting from 0% at month 0, instead of jumping straight to each year\'s value. '
        'The yearly table above holds fill % flat within each year, which understates how bad early months really '
        'are — the monthly table is the more realistic view for that reason.',
        f'Capex follows a sinking-fund pattern: Year 1 carries the FULL initial lump sum — the exact same figure '
        f'and treatment as the Summary/Cost Priority sheets\' "Year-1 lump sum, not amortized" — so those sheets '
        f'and this one now agree on Year 1, repeating in full for every year before {DROP_YEAR_NOTE}, which drops '
        f'to a {CAPEX_RESERVE_RATE:.1%} ongoing reserve contribution instead of repeating the full purchase, since '
        f'equipment like elevators/generators gets replaced on a multi-year cycle, not annually. '
        f'{CAPEX_RESERVE_SOURCE}',
        'Every VND figure here is a live formula reading the Summary sheet\'s Cost Basis toggle output — nothing '
        'is re-derived independently.',
    ]
    for note in notes:
        ws.cell(row=r, column=1, value=note).font = Font(italic=True, size=9, color='7F7F7F')
        ws.cell(row=r, column=1).alignment = LEFT
        ws.merge_cells(f'A{r}:I{r}')
        ws.row_dimensions[r].height = 40
        r += 1

    for col, w in {'A': 12, 'B': 12, 'C': 20, 'D': 20, 'E': 22, 'F': 20, 'G': 20, 'H': 20, 'I': 22}.items():
        ws.column_dimensions[col].width = w


def build_savills_fee_position_sheet(wb, project, mgmt, summary):
    """Models the agency-model mechanic the PM described: Savills recognizes its FULL package
    (staff/OPEX/capex reimbursement + its own service fee/profit) every year regardless of actual
    fill % — that recognized-profit line is always positive, by design, tracked year over year.
    Separately, actual CASH collected from the building may fall short of that package; the gap
    accumulates as a receivable owed by the owner, settled per the PM's description at contract
    end. Unlike Owner Operating Position, this cumulative receivable does NOT structurally clear
    to zero within the ramp horizon on its own (see NOTES for exactly why) — it only clears via
    the real, still-unconfirmed settlement mechanism."""
    ws = wb.create_sheet('Savills Fee Position')
    title_block(ws, "Savills Fee Position — Full Package Recognized Every Year",
                'Savills\' recognized profit is always positive, protected regardless of fill % — tracked '
                'separately from the cash-timing gap (the rollover receivable owed by the owner), which does '
                'NOT self-clear the way the Owner Operating Position sheet\'s balance does. See NOTES.', 'A1:F1')

    MGMT_100 = f"'Management Fee'!{mgmt['annual_revenue_cell']}"
    BASE_PACKAGE = (f"({summary['selected_staff_cell']}+{summary['selected_opex_cell']}"
                    f"+{summary['selected_contingency_cell']}+{summary['profit_cell']})")
    CAPEX_CELL = summary['selected_capex_cell']
    DROP_YEAR = project['capex_drop_year']
    DROP_YEAR_NOTE = (f'the evidenced default of Year {DROP_YEAR}' if project['capex_drop_year_is_default']
                       else f"this project's own stated Year {DROP_YEAR}")
    FULL_YEARS_LABEL = 'Year 1' if DROP_YEAR == 2 else f'Years 1-{DROP_YEAR - 1}'
    RESERVE_YEARS_LABEL = f'Years {DROP_YEAR}-4'

    r = 4
    section(ws, r, "SAVILLS' RECOGNIZED PROFIT — ALWAYS POSITIVE, PROTECTED", ncols=5); r += 1
    ws.cell(row=r, column=1,
            value=('Savills books its full profit target every year regardless of actual fill % — this is the '
                   '"we always take full profit" the PM described. Reads the same Total Profit Value the Summary '
                   'sheet\'s Cost Basis toggle drives, so it stays in sync automatically.')
            ).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:E{r}')
    ws.row_dimensions[r].height = 28
    r += 1
    headers = ['Year', 'Fill %', "Savills' Recognized Profit (VND)", 'Cumulative Recognized Profit (VND)', '', '']
    for c, h in enumerate(headers, start=1):
        if not h:
            continue
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    r += 1
    prev_cum_cell = None
    for year_label, pct in _year_fill_path(project):
        ws.cell(row=r, column=1, value=year_label).border = BORDER
        ws.cell(row=r, column=1).alignment = CENTER
        ws.cell(row=r, column=2, value=pct).number_format = '0%'
        ws.cell(row=r, column=2).border = BORDER
        ws.cell(row=r, column=2).alignment = CENTER
        c3 = ws.cell(row=r, column=3, value=f"={summary['profit_cell']}")
        c3.number_format = MONEY_FMT
        c3.border = BORDER
        cum_formula = f'=C{r}' if prev_cum_cell is None else f'={prev_cum_cell}+C{r}'
        c4 = ws.cell(row=r, column=4, value=cum_formula)
        c4.number_format = MONEY_FMT
        c4.border = BORDER
        c4.font = Font(bold=True)
        c4.fill = HIGHLIGHT_FILL
        prev_cum_cell = f'D{r}'
        r += 1
    r += 1

    section(ws, r, "SAVILLS' FULL PACKAGE (guaranteed regardless of fill %)", ncols=5); r += 1
    package_rows = [
        ('Staff Cost Reimbursement (per Cost Basis toggle, VND)', summary['selected_staff_cell'], None),
        ('OPEX Reimbursement (per Cost Basis toggle, VND)', summary['selected_opex_cell'], None),
        ('Contingency Reimbursement (per Cost Basis toggle, VND)', summary['selected_contingency_cell'], None),
        (f'Capex Reimbursement — {FULL_YEARS_LABEL} full lump sum (VND)', summary['selected_capex_cell'], 'FFF7CC'),
        ("Savills' Own Service Fee / Profit, at 100% fill (VND)", summary['profit_cell'], None),
    ]
    package_cells = []
    for label, cell, hl in package_rows:
        ws.cell(row=r, column=1, value=label).border = BORDER
        ws.cell(row=r, column=1).alignment = LEFT
        c2 = ws.cell(row=r, column=2, value=f'={cell}')
        c2.number_format = MONEY_FMT
        c2.border = BORDER
        if hl:
            c2.fill = PatternFill('solid', fgColor=hl)
        package_cells.append(f'B{r}')
        r += 1
    ws.cell(row=r, column=1, value=f'TOTAL FULL PACKAGE, {FULL_YEARS_LABEL} (VND)').font = Font(bold=True, size=12)
    c = ws.cell(row=r, column=2, value='=' + '+'.join(package_cells))
    c.number_format = MONEY_FMT
    c.font = Font(bold=True, size=12)
    c.fill = HIGHLIGHT_FILL
    FULL_PACKAGE_CELL = f'B{r}'
    r += 1
    ws.cell(row=r, column=1, value=f'Capex Reimbursement — {RESERVE_YEARS_LABEL} reserve ({CAPEX_RESERVE_RATE:.1%} of Year 1) (VND)').font = Font(size=10, italic=True)
    c = ws.cell(row=r, column=2, value=f"={summary['selected_capex_cell']}*{CAPEX_RESERVE_RATE}")
    c.number_format = MONEY_FMT
    c.font = Font(size=10, italic=True)
    c.fill = PatternFill('solid', fgColor='E2EFDA')
    r += 1
    ws.cell(row=r, column=1, value=f'RECURRING PACKAGE, {RESERVE_YEARS_LABEL} (Staff+OPEX+Contingency+Profit; Capex at reserve rate) (VND)').font = Font(bold=True, size=12)
    c = ws.cell(row=r, column=2,
                value=f"={summary['selected_staff_cell']}+{summary['selected_opex_cell']}"
                      f"+{summary['selected_contingency_cell']}+{summary['profit_cell']}"
                      f"+{summary['selected_capex_cell']}*{CAPEX_RESERVE_RATE}")
    c.number_format = MONEY_FMT
    c.font = Font(bold=True, size=12)
    c.fill = HIGHLIGHT_FILL
    RECURRING_PACKAGE_CELL = f'B{r}'
    r += 1
    ws.cell(row=r, column=1,
            value=(f'{FULL_YEARS_LABEL}\'s full package always equals Management Fee Revenue at 100% fill exactly '
                   f'(Costs + Profit = Revenue by construction) — a cross-check, not a coincidence. '
                   f'{RESERVE_YEARS_LABEL}\'s recurring package is LOWER (drops {1-CAPEX_RESERVE_RATE:.1%} of the '
                   f'Capex reimbursement, per the sinking-fund assumption — see NOTES), which means the receivable '
                   f'below CAN partially unwind in high-fill later years, unlike {FULL_YEARS_LABEL} where it '
                   f'structurally can\'t.')
            ).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:E{r}')
    ws.row_dimensions[r].height = 55
    r += 2

    # Head of PM decision B1-b (change apply-head-of-pm-decisions-2026-10, group 7): the fee the PM entered for EMH1,
    # beside the profit this sheet computes. Display only — nothing above or below sums these rows.
    section(ws, r, "SAVILLS' FEE ENTERED ON PROJECT INFO (EMH1) — beside the profit computed above", ncols=5); r += 1
    import savills_fee
    for label, value, fmt in savills_fee.analysis_rows(project, MGMT_100) + [
            ("Computed: Savills' Own Service Fee / Profit, at 100% fill (VND)", f"={summary['profit_cell']}", 'money')]:
        ws.cell(row=r, column=1, value=label).border = BORDER
        ws.cell(row=r, column=1).alignment = LEFT
        c2 = ws.cell(row=r, column=2, value=value)
        c2.border = BORDER
        if fmt:
            c2.number_format = MONEY_FMT if fmt == 'money' else fmt
        r += 1
    r += 1

    section(ws, r, 'CASH COLLECTED vs. FULL PACKAGE OWED — THE ROLLOVER RECEIVABLE', ncols=6); r += 1
    ws.cell(row=r, column=1,
            value=('Same year path as above. The gap between what the building actually collects and Savills\' '
                   'package accumulates as a receivable owed by the owner — modeled here as a deferred rollover, '
                   'per the PM\'s description (settled at contract end), NOT paid down year to year. If the real '
                   'mechanism is periodic cash-calls instead, this balance would clear each year rather than '
                   f'accumulate. Capex follows the sinking-fund pattern above (full in {FULL_YEARS_LABEL}, '
                   f'reserve rate in {RESERVE_YEARS_LABEL}) — see NOTES.')
            ).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:G{r}')
    ws.row_dimensions[r].height = 40
    r += 1
    headers2 = ['Year', 'Fill %', 'Actual Collections (VND)', 'Capex Component (VND)',
                'Package Owed — Staff+OPEX+Contingency+Profit+Capex (VND)', 'Shortfall This Year (VND)',
                'Cumulative Receivable Owed by Owner (VND)']
    for c, h in enumerate(headers2, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    r += 1
    prev_cum_cell = None
    for i, (year_label, pct) in enumerate(_year_fill_path(project)):
        ws.cell(row=r, column=1, value=year_label).border = BORDER
        ws.cell(row=r, column=1).alignment = CENTER
        ws.cell(row=r, column=2, value=pct).number_format = '0%'
        ws.cell(row=r, column=2).border = BORDER
        ws.cell(row=r, column=2).alignment = CENTER
        c3 = ws.cell(row=r, column=3, value=f'={MGMT_100}*B{r}')
        c3.number_format = MONEY_FMT
        c3.border = BORDER
        capex_formula, capex_is_full = _capex_reserve_formula(CAPEX_CELL, i + 1, DROP_YEAR)
        c4 = ws.cell(row=r, column=4, value=capex_formula)
        c4.number_format = MONEY_FMT
        c4.border = BORDER
        c4.fill = PatternFill('solid', fgColor='FFF7CC' if capex_is_full else 'E2EFDA')
        c5 = ws.cell(row=r, column=5, value=f"={BASE_PACKAGE}+D{r}")
        c5.number_format = MONEY_FMT
        c5.border = BORDER
        c6 = ws.cell(row=r, column=6, value=f'=E{r}-C{r}')
        c6.number_format = MONEY_FMT
        c6.border = BORDER
        cum_formula = f'=F{r}' if prev_cum_cell is None else f'={prev_cum_cell}+F{r}'
        c7 = ws.cell(row=r, column=7, value=cum_formula)
        c7.number_format = MONEY_FMT
        c7.border = BORDER
        c7.font = Font(bold=True)
        c7.fill = HIGHLIGHT_FILL
        prev_cum_cell = f'G{r}'
        r += 1
    r += 1

    section(ws, r, 'MONTHLY BREAKDOWN — the rollover receivable (48 months, smooth ramp — see NOTES)', ncols=7); r += 1
    ws.cell(row=r, column=1,
            value=(_stable_prefix(project) +
                   f'Same smooth month-by-month fill % ramp used on the Owner Operating Position sheet, applied to '
                   f'the receivable above. Staff/OPEX/Profit portion is held flat per month; Capex follows the same '
                   f'sinking-fund pattern as the yearly table — a full lump sum in the first month of every year '
                   f'before {DROP_YEAR_NOTE}, then a {CAPEX_RESERVE_RATE:.1%} reserve contribution spread evenly '
                   f'per month from {DROP_YEAR_NOTE}\'s own first month onward.')
            ).font = Font(italic=True, size=9, color='7F7F7F')
    ws.cell(row=r, column=1).alignment = LEFT
    ws.merge_cells(f'A{r}:G{r}')
    ws.row_dimensions[r].height = 40
    r += 1
    m_headers2 = ['Month', 'Fill %', 'Monthly Collections (VND)', 'Capex Component (VND)',
                  'Monthly Package Owed (VND)', 'Monthly Shortfall (VND)', 'Cumulative Receivable Owed by Owner (VND)']
    for c, h in enumerate(m_headers2, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    r += 1
    prev_cum_cell = None
    for month_num, month_label, fill in _monthly_fill_path(bool(project.get('stable_operation'))):
        ws.cell(row=r, column=1, value=month_label).border = BORDER
        ws.cell(row=r, column=1).alignment = CENTER
        c2 = ws.cell(row=r, column=2, value=fill)
        c2.number_format = '0.0%'
        c2.border = BORDER
        c2.alignment = CENTER
        c3 = ws.cell(row=r, column=3, value=f'=({MGMT_100}/12)*B{r}')
        c3.number_format = MONEY_FMT
        c3.border = BORDER
        capex_formula, capex_fill = _capex_reserve_monthly_formula(CAPEX_CELL, month_num, DROP_YEAR)
        c4 = ws.cell(row=r, column=4, value=capex_formula)
        c4.number_format = MONEY_FMT
        c4.border = BORDER
        if capex_fill:
            c4.fill = PatternFill('solid', fgColor=capex_fill)
        c5 = ws.cell(row=r, column=5, value=f'={BASE_PACKAGE}/12+D{r}')
        c5.number_format = MONEY_FMT
        c5.border = BORDER
        c6 = ws.cell(row=r, column=6, value=f'=E{r}-C{r}')
        c6.number_format = MONEY_FMT
        c6.border = BORDER
        cum_formula = f'=F{r}' if prev_cum_cell is None else f'={prev_cum_cell}+F{r}'
        c7 = ws.cell(row=r, column=7, value=cum_formula)
        c7.number_format = MONEY_FMT
        c7.border = BORDER
        c7.font = Font(bold=True)
        c7.fill = HIGHLIGHT_FILL
        prev_cum_cell = f'G{r}'
        r += 1
    r += 1

    section(ws, r, 'NOTES', ncols=4); r += 1
    notes = [
        'Two DIFFERENT lines, both real: Savills\' recognized profit (top table) is always positive by design — '
        'that answers "we always take full profit." The cumulative receivable (bottom table) tracks the separate '
        'question of whether that profit has actually been PAID IN CASH yet, or is still owed. In Year 1 it '
        'cannot shrink on its own, because the required package is pinned to 100%-fill revenue, which actual '
        'collections can approach but never exceed. From Year 2 onward the required package DROPS (sinking-fund '
        'Capex reserve, see below), so the receivable CAN partially unwind in high-fill later years — a real '
        'behavior change from the Year 1 dynamic, not a bug.',
        'The settlement mechanism/timing is still NOT confirmed with the PM/actual contract terms. If there\'s an '
        'owner-funded working capital reserve or periodic cash-calls, Savills carries little real risk from this '
        'receivable. If it\'s genuinely deferred to contract end with nothing backing it, Savills is '
        'float-financing the shortfall and carries real credit risk if the owner can\'t eventually cover it.',
        'Year 1-4 / 50-100% fill is the same disclosed simplifying assumption used across this workbook — not a '
        'contractually defined ramp-up schedule.',
        'The Monthly Breakdown adds ONE more assumption: fill % ramps smoothly (linearly) between the same '
        'year-end anchors, starting from 0% at month 0, instead of jumping straight to each year\'s value — same '
        'interpolation as the Owner Operating Position sheet, so the two stay comparable month for month.',
        f'Capex follows a sinking-fund pattern: Year 1 carries the FULL lump sum — matching the Summary/Cost '
        f'Priority sheets\' "Year-1 lump sum, not amortized" exactly — repeating in full for every year before '
        f'{DROP_YEAR_NOTE}, which drops to a {CAPEX_RESERVE_RATE:.1%} ongoing reserve contribution instead of '
        f'repeating the full purchase. {CAPEX_RESERVE_SOURCE}',
    ]
    for note in notes:
        ws.cell(row=r, column=1, value=note).font = Font(italic=True, size=9, color='7F7F7F')
        ws.cell(row=r, column=1).alignment = LEFT
        ws.merge_cells(f'A{r}:G{r}')
        ws.row_dimensions[r].height = 40
        r += 1

    for col, w in {'A': 12, 'B': 24, 'C': 22, 'D': 22, 'E': 24, 'F': 22, 'G': 28}.items():
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


def build_staff_bridge_sheet(wb, result):
    """'Staff Bridge' (Existing-project mode only, change carry-forward-staffing D4/D13): from the
    prior-year baseline to the budget year in fixed steps, per staff line, with the reason record of
    every change. Internal: the client deliverable never carries it. Its total equals EMH2 + EMH3 +
    EMH4 of the deliverable, which verification confirms after Excel recalculates the deliverable."""
    es = existing_staffing
    ws = wb.create_sheet(es.BRIDGE_SHEET)
    title_block(ws, f'Staff Bridge — approved budget {result.prior_year} to budget year {result.budget_year}',
                'Internal (Existing-project mode). Not part of the client deliverable. VND per year. The '
                'budget-year total equals EMH2 + EMH3 + EMH4 on the client deliverable.', 'A1:G1')
    info = [
        ('Prior budget year', result.prior_year),
        ('Budget year', result.budget_year),
        ('Minimum wage region', result.region),
        ('Baseline', 'Prior-Year Roster (per position)' if result.kind == 'roster'
         else 'Approved line amounts (no per-position roster)'),
        ('Insurance base on A1 (VND/month)', result.a1_cells['I4']),
        ('Regional minimum wage on A1 (VND/month)', result.a1_cells['I5']),
    ]
    r = 4
    for label, value in info:
        ws.cell(row=r, column=1, value=label).font = Font(bold=True)
        c = ws.cell(row=r, column=2, value=value)
        if isinstance(value, float):
            c.number_format = MONEY_FMT
        r += 1

    r += 1
    for c, h in enumerate(['Step', 'EMH2', 'EMH3', 'EMH4', 'Total', 'Note'], start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill, cell.font, cell.alignment, cell.border = HEADER_FILL, HEADER_FONT, CENTER, BORDER
    lines = [result.lines[k] for k in es.STAFF_LINES]
    bc = result.backcast
    if bc.get('flag'):
        baseline_note = ('FLAG: the recomputed prior year differs from the approved EMH2 by more than 1% '
                         f"({bc['recomputed']:,.0f} vs {bc['approved']:,.0f})")
    elif result.kind == 'roster':
        baseline_note = 'Prior year recomputed with the law in force in each month of that year'
    else:
        baseline_note = 'Approved amounts, carried forward'
    steps = [
        ('Prior-year approved (as entered)', [l.approved for l in lines],
         'Shown for reference; not part of the sum below.'),
        (es.BRIDGE_BASELINE_LABEL, [l.baseline for l in lines], baseline_note),
        ('Wage and insurance effect (law)', [l.law for l in lines],
         'Minimum-wage floor, insurance base and rates of the budget year' if result.kind == 'roster'
         else 'Not computable without a per-position roster'),
        ('Headcount and salary changes (PM)', [l.headcount for l in lines],
         'Roster changes and new positions, each with its reason below'),
        ('Allowance effect (calendar, minimum wage)', [l.allowance for l in lines],
         'EMH3 night/holiday allowance and EMH4 fire-team allowance'),
        ('PM line overrides', [l.override for l in lines], 'Whole-line overrides with a reason code'),
        (es.BRIDGE_TOTAL_LABEL, [l.budget for l in lines], 'Equals the client deliverable'),
    ]
    first = r + 1
    for label, values, note in steps:
        r += 1
        ws.cell(row=r, column=1, value=label).border = BORDER
        for i, v in enumerate(values):
            c = ws.cell(row=r, column=2 + i, value=v)
            c.number_format, c.border = MONEY_FMT, BORDER
        tot = ws.cell(row=r, column=5, value=f'=SUM(B{r}:D{r})')
        tot.number_format, tot.border = MONEY_FMT, BORDER
        ws.cell(row=r, column=6, value=note).alignment = LEFT
    total_row = r
    r += 1
    ws.cell(row=r, column=1, value='Check: baseline + effects − total (must be 0)').font = Font(italic=True)
    for col in 'BCDE':
        c = ws.cell(row=r, column=ord(col) - 64,
                    value=f'=ROUND({col}{first + 1}+{col}{first + 2}+{col}{first + 3}+{col}{first + 4}'
                          f'+{col}{first + 5}-{col}{total_row},0)')
        c.number_format = MONEY_FMT
    for row in (first + 1, total_row):
        ws.cell(row=row, column=1).font = Font(bold=True)

    r += 2
    ws.cell(row=r, column=1, value=es.REASONS_TITLE).font = Font(bold=True, size=11)
    r += 1
    for c, h in enumerate(es.REASON_HEADERS, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill, cell.font, cell.alignment, cell.border = HEADER_FILL, HEADER_FONT, CENTER, BORDER
    for rec in result.reason_rows:
        r += 1
        row = [rec['line'], rec['item'], rec['baseline'], rec['budget'], rec['diff'], rec['code'],
               rec['note'], rec['text'], rec['source'], rec['status'] or 'OK']
        for c, v in enumerate(row, start=1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.border = BORDER
            if c == 5:
                cell.number_format = MONEY_FMT
            if c == 10 and rec['status']:
                cell.font = Font(bold=True, color='C00000')
    if not result.reason_rows:
        r += 1
        ws.cell(row=r, column=1, value='No staffing line changed.')

    if result.actual_rows:
        r += 2
        ws.cell(row=r, column=1, value='ACTUAL HEADCOUNT (optional, shown only)').font = Font(bold=True, size=11)
        r += 1
        for c, h in enumerate(['Position', 'Baseline heads', 'Actual heads', 'Differs', 'Source', 'Note'], 1):
            cell = ws.cell(row=r, column=c, value=h)
            cell.fill, cell.font, cell.alignment, cell.border = HEADER_FILL, HEADER_FONT, CENTER, BORDER
        for a in result.actual_rows:
            r += 1
            for c, v in enumerate([a['position'], a['baseline'], a['heads'],
                                   'yes' if a['differs'] else 'no', a['source'], a['note']], 1):
                ws.cell(row=r, column=c, value=v).border = BORDER

    notes = list(result.notes) + [
        "The 'Staff (Roster)' sheet and the Summary staff figure of this workbook are the New-prospect "
        "estimate from Staffing Demand. In Existing-project mode the budget's staff lines are the ones "
        "on this sheet."]
    r += 2
    ws.cell(row=r, column=1, value='Notes').font = Font(bold=True, size=11)
    for n in notes:
        r += 1
        ws.cell(row=r, column=1, value=n).alignment = LEFT
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=7)
        ws.row_dimensions[r].height = 30
    for col, w in {'A': 44, 'B': 20, 'C': 20, 'D': 18, 'E': 20, 'F': 34, 'G': 22, 'H': 60, 'I': 8,
                   'J': 18}.items():
        ws.column_dimensions[col].width = w
    return ws


def build_utility_bridge_sheet(wb, result):
    """'Utility Bridge' (Existing-project mode only, change carry-forward-common-utilities design D6): for
    EEE.C and EEW.C, from the approved prior year through the consumption, tariff, VAT and PM-override
    effects to the budget year, then the months used and every flag. Internal: the client deliverable
    never carries it. Its budget-year figures equal EEE.C and EEW.C on the deliverable (VND per year)."""
    eu = existing_utilities
    ws = wb.create_sheet(eu.BRIDGE_SHEET)
    basis = 'including' if result.incl_vat else 'excluding'
    title_block(ws, f'Utility Bridge — approved budget {result.prior_year} to budget year {result.budget_year}',
                'Internal (Existing-project mode). Not part of the client deliverable. VND per year, on the '
                f"deliverable's VAT basis ({basis} VAT). The budget-year figures equal EEE.C and EEW.C on the "
                'client deliverable.', 'A1:F1')
    r = 4
    for label, value in (('Prior budget year', result.prior_year), ('Budget year', result.budget_year),
                         ('VAT basis', 'including VAT' if result.incl_vat else 'excluding VAT (KHOÁN)'),
                         ('Tariff region', result.region or '(blank)')):
        ws.cell(row=r, column=1, value=label).font = Font(bold=True)
        ws.cell(row=r, column=2, value=value)
        r += 1
    r += 1
    for c, h in enumerate(['Step', *eu.LINES, 'Note'], start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill, cell.font, cell.alignment, cell.border = HEADER_FILL, HEADER_FONT, CENTER, BORDER
    r += 1
    steps = [
        ('Approved prior year', 'approved', 'Approved amount converted to this VAT basis; blank when not given'),
        ('Actual baseline', 'baseline',
         'Baseline consumption x the price of the latest month used (or prior-year prices)'),
        ('Consumption vs approved', 'consumption', 'Actual baseline minus the approved amount'),
        ('Tariff effect', 'tariff', 'Budget-year base price (and drainage charge) vs the baseline price'),
        ('VAT effect', 'vat', 'Budget-year VAT vs the baseline VAT'),
        ('PM override effect', 'override', 'Override consumption minus baseline consumption, at budget-year prices'),
        ('Rounding (monthly amounts)', 'rounding', 'Each month is written to the deliverable in whole VND'),
        (eu.BRIDGE_TOTAL_LABEL, 'budget', 'Equals the line on the client deliverable'),
    ]
    for label, key, note in steps:
        ws.cell(row=r, column=1, value=label).font = Font(bold=(key == 'budget'))
        for c, line in enumerate(eu.LINES, start=2):
            cell = ws.cell(row=r, column=c, value=result.lines[line].bridge.get(key))
            cell.number_format = MONEY_FMT
            cell.border = BORDER
        ws.cell(row=r, column=len(eu.LINES) + 2, value=note).alignment = LEFT
        r += 1

    for line in eu.LINES:
        lr = result.lines[line]
        r += 1
        section(ws, r, f'{line} — {eu.LINE_NAME_VI[line]}', ncols=7)
        r += 1
        p = lr.budget_prices[0]
        bill = f' — bill price {lr.bill_price:,.0f} ({lr.bill_source})' if lr.bill_price is not None else ''
        details = (
            ('Basis', 'actual spend, last 12 months' if lr.basis == 'actual' else 'approved prior-year amount'),
            ('Tariff category', lr.category + bill),
            (f'Baseline consumption ({lr.unit}/month)', lr.q_bar),
            (f'Budget-year consumption ({lr.unit}/month)', lr.q_budget),
            (f'January {result.budget_year} price (VND/{lr.unit}, excl. VAT)', p.net()),
            (f'January {result.budget_year} price (VND/{lr.unit}, incl. VAT)', p.gross()),
            ('Reasons', '; '.join(x['text'] for x in lr.reasons if x['text'])),
            ('Flags', '; '.join(lr.flags) or 'none'),
            ('Note', lr.note or ''),
        )
        for label, value in details:
            ws.cell(row=r, column=1, value=label).font = Font(bold=True)
            cell = ws.cell(row=r, column=2, value=value)
            if isinstance(value, float):
                cell.number_format = MONEY_FMT
            else:
                cell.alignment = LEFT
            r += 1
        if lr.months:
            for c, h in enumerate(['Month', 'Amount (VND)', 'Includes VAT', f'Consumption ({lr.unit})',
                                   'Consumption source', f'Unit price (VND/{lr.unit})', 'Flag'], start=1):
                cell = ws.cell(row=r, column=c, value=h)
                cell.fill, cell.font, cell.alignment, cell.border = HEADER_FILL, HEADER_FONT, CENTER, BORDER
            r += 1
            for mu in lr.months:
                values = [f'{mu.month:02d}/{mu.year}', mu.amount, 'Yes' if mu.incl_vat else 'No', mu.consumption,
                          'derived from the amount' if mu.derived else 'bill', mu.unit_price, mu.flag]
                for c, v in enumerate(values, start=1):
                    cell = ws.cell(row=r, column=c, value=v)
                    cell.border = BORDER
                    if isinstance(v, float):
                        cell.number_format = MONEY_FMT
                r += 1
    for col, w in {'A': 44, 'B': 22, 'C': 22, 'D': 22, 'E': 26, 'F': 22, 'G': 50}.items():
        ws.column_dimensions[col].width = w
    return ws


def build_service_levels_sheet(wb, project, demand):
    """'Service Levels' (change add-service-level-table, design D9): the cleaning and security crews the tool has
    just costed, set against the fixed thresholds in data/service_levels/Ref_ServiceLevelThresholds.csv and the
    anonymous real-project table Ref_ServiceLevelProjects.csv. Internal, display only: it writes no value that any
    other sheet reads, so every recorded baseline stays where it is. A missing data file or a project without a
    fee-paying NFA gives 'chưa phân loại' with the reason; the run still completes."""
    import service_levels as sl
    ws = wb.create_sheet(sl.SHEET_NAME)
    title_block(ws, 'Service Levels — cleaning and security crews against fixed thresholds and real projects',
                'Internal, display only (change add-service-level-table). Changes no figure. Measures: m² of fee-paying '
                'NFA per cleaning person on duty per day; 24-hour-equivalent security posts per 10,000 m² of fee-paying '
                'NFA (a 24H shift row = 24 h, any other shift row = 8 h). Levels from the editable threshold table; the '
                'percentile is among real Savills projects whose headcount was read from their own A2/A3 forms, the '
                'project itself left out.', 'A1:M1')
    r = 4
    try:
        res = sl.evaluate(project, demand)
    except (OSError, ValueError, KeyError) as exc:
        ws.cell(row=r, column=1, value='Service levels could not be computed: ' + f'{type(exc).__name__}: {exc}').font = Font(bold=True, color='C00000')
        ws.cell(row=r + 1, column=1, value='Cần hai file data/service_levels/Ref_ServiceLevelThresholds.csv và '
                                           'Ref_ServiceLevelProjects.csv (xem RUNNING.md). Không có con số nào khác bị ảnh hưởng.').alignment = LEFT
        ws.column_dimensions['A'].width = 120
        return ws

    headers = ['Service', 'People on duty / day', 'Roster headcount', '24h-equivalent posts', 'Fee-paying NFA (m²)',
               'Measure', 'Unit', 'Level', 'Near cut-off', 'Thresholds applied',
               'Percentile among form-read real projects (%)', 'Projects compared (form-read)',
               'Inferred rows (reference only, not compared)']
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill, cell.font, cell.alignment, cell.border = HEADER_FILL, HEADER_FONT, CENTER, BORDER
    r += 1
    th = res['thresholds']

    def _rule(t):
        f = (lambda v: f'{v:,.0f}') if t.cutoff_1 >= 100 else (lambda v: f'{v:g}')
        bounds = (f'; ngoài cận {f(t.bound_low)}–{f(t.bound_high)} = chưa phân loại'
                  if t.bound_low is not None and t.bound_high is not None else '')
        return (f'< {f(t.cutoff_1)} = {t.levels[0]}; {f(t.cutoff_1)} đến < {f(t.cutoff_2)} = {t.levels[1]}; '
                f'≥ {f(t.cutoff_2)} = {t.levels[2]}{bounds} (duyệt {t.approved_on})')

    for service, label in (('cleaning', 'Cleaning'), ('security', 'Security')):
        s = res['services'][service]
        cls = s['classification']
        values = [label, s['on_duty'], s['roster'], s['posts24'] if service == 'security' else None,
                  res['nfa'] or None, s['value'], th[service].unit, cls.label,
                  sl.NEAR_MARK if cls.near else '', _rule(th[service]),
                  s['percentile'], s['n_form'], s['n_inferred']]
        for c, v in enumerate(values, start=1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.border = BORDER
            if isinstance(v, float):
                cell.number_format = '#,##0.00' if (c in (4, 6) and v < 100) else MONEY_FMT
            cell.alignment = LEFT if c in (7, 8, 10) else CENTER
        r += 1
    land = ['Landscape', None, None, None, res['nfa'] or None, None, '', res['landscape'], '', 'chưa đặt ngưỡng',
            None, None, None]
    for c, v in enumerate(land, start=1):
        cell = ws.cell(row=r, column=c, value=v)
        cell.border = BORDER
        cell.alignment = LEFT if c in (8, 10) else CENTER
    r += 2

    section(ws, r, 'THRESHOLD TABLE — data/service_levels/Ref_ServiceLevelThresholds.csv (editable without code)', ncols=13)
    r += 1
    thead = ['Service', 'Measure', 'Unit', 'Cut-off 1', 'Cut-off 2', 'Level below cut-off 1', 'Level between',
             'Level from cut-off 2', 'Bound low', 'Bound high', 'Approved on', 'Bounds approved on', 'Source']
    for c, h in enumerate(thead, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill, cell.font, cell.alignment, cell.border = HEADER_FILL, HEADER_FONT, CENTER, BORDER
    r += 1
    for t in th.values():
        vals = [t.service, t.measure, t.unit, t.cutoff_1, t.cutoff_2, *(t.levels or ('', '', '')),
                t.bound_low, t.bound_high, t.approved_on, t.bounds_approved_on, t.source]
        for c, v in enumerate(vals, start=1):
            cell = ws.cell(row=r, column=c, value=v if v is not None else ('' if c > 3 else v))
            cell.border = BORDER
            cell.alignment = LEFT if c in (2, 3, 13) else CENTER
        r += 1
    r += 1

    section(ws, r, 'ROWS COUNTED FROM STAFFING DEMAND (people on duty per day; the roster count adds rest-day cover)', ncols=13)
    r += 1
    for c, h in enumerate(['Service', 'Position', 'Shift code', 'On duty / day', 'Hours counted (security)',
                           'Roster Staff Count'], start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill, cell.font, cell.alignment, cell.border = HEADER_FILL, HEADER_FONT, CENTER, BORDER
    r += 1
    for service, label in (('cleaning', 'Cleaning'), ('security', 'Security')):
        for pos, shift, spd, hrs, rc in res['services'][service]['rows']:
            for c, v in enumerate([label, pos, shift, spd, hrs, rc], start=1):
                cell = ws.cell(row=r, column=c, value=v)
                cell.border = BORDER
                cell.alignment = LEFT if c == 2 else CENTER
            r += 1
        if not res['services'][service]['rows']:
            ws.cell(row=r, column=1, value=label).border = BORDER
            ws.cell(row=r, column=2, value='No matching row in Staffing Demand').border = BORDER
            r += 1
    r += 1

    section(ws, r, 'GHI CHÚ', ncols=13)
    r += 1
    snapshot = ''
    try:
        rows_real = sl.load_projects()
        snapshot = rows_real[0].get('snapshot', '') if rows_real else ''
        n_total = len(rows_real)
    except OSError:
        n_total = 0
    notes = [
        'Mức dịch vụ chỉ để tham khảo: không làm thay đổi con số nào trong ngân sách, roster hay bản giao khách hàng.',
        'Diện tích dùng là NFA thu phí (tổng mọi sản phẩm), không phải diện tích cần vệ sinh. Lẫn sàn gộp với sàn '
        'sử dụng có thể làm chi phí vệ sinh lệch khoảng 15%.',
        'Ngưỡng là số tròn đọc từ phân bố của các dự án thật trong kho quét ngân sách (duyệt 16/10/2026, sửa '
        '18/10/2026), không phải chuẩn bên ngoài. Sửa ngưỡng trong file CSV, kèm ngày duyệt mới.',
        'Số người lấy từ Staffing Demand, cột "Staff On Duty / Day": do PM nhập, hoặc công cụ ước từ tỷ lệ Roster Setup '
        'khi để trống. Khi ước, mức phản ánh benchmark của công cụ chứ không phải dự án.',
        f'Tập so sánh: {n_total} dự án thật ẩn danh ({snapshot}); chỉ dự án có số người đọc từ form A2/A3 của ngân sách '
        'và đã phân loại được đưa vào percentile. Dự án suy số người từ chi phí chỉ ghi để tham khảo, vì cách suy '
        'biến đơn giá cao thành số người nhiều. Percentile = tỷ lệ dự án so sánh có chỉ số nhỏ hơn hoặc bằng dự án này.',
        '"sát ngưỡng": chỉ số cách một ngưỡng dưới 10%, nên một thay đổi nhỏ về số người sẽ đổi mức.',
        '"chưa phân loại": thiếu NFA, thiếu số người, hoặc chỉ số ngoài cận (nghi đọc sai). Không đoán để điền.',
        'Vệ sinh và bảo vệ là hai mức riêng, không gộp thành một nhãn.',
        'Cảnh quan: chưa đặt ngưỡng vì kho không có diện tích cây xanh.',
    ]
    for n in notes:
        ws.cell(row=r, column=1, value=n).alignment = LEFT
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=13)
        ws.row_dimensions[r].height = 30
        r += 1
    for col, w in {'A': 16, 'B': 30, 'C': 16, 'D': 18, 'E': 18, 'F': 14, 'G': 24, 'H': 34, 'I': 14, 'J': 60,
                   'K': 22, 'L': 18, 'M': 22}.items():
        ws.column_dimensions[col].width = w
    return ws


def main():
    project, ratios, month, year, holiday_days, demand = read_input(INPUT_PATH)
    if project.get('utilities') is not None:
        # Existing-project EEE.C / EEW.C, on the same budget year and VAT basis as the deliverable.
        project['utilities_result'] = utilities_result(project, project['budget_period'].start_year, template_vat_inclusive())

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
    summary = build_summary_sheet(ws_summary, project, mgmt, staff, service, capex, opex, extra_revenue, cost_priority)
    year1_strategy = build_year1_strategy_sheet(wb, project, mgmt, cost_priority, extra_revenue)
    build_owner_operating_position_sheet(wb, project, mgmt, summary, year1_strategy)
    build_savills_fee_position_sheet(wb, project, mgmt, summary)
    if project.get('existing') is not None:
        build_staff_bridge_sheet(wb, existing_result(project, demand, project['budget_period'].start_year))
    if project.get('utilities_result') is not None:
        build_utility_bridge_sheet(wb, project['utilities_result'])
    # Last among the internal sheets and read-only (change add-service-level-table, design D9).
    build_service_levels_sheet(wb, project, demand)

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
