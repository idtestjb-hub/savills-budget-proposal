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
from estimate_opex import estimate_opex
from estimate_capex_qty import estimate_capex_items

SOURCE_DIR = os.path.dirname(__file__)
BUDGET_AGENT = os.path.abspath(os.path.join(SOURCE_DIR, '..'))
BASE = os.path.abspath(os.path.join(SOURCE_DIR, '..', '..'))

INPUT_PATH = os.path.join(BUDGET_AGENT, 'reports', 'Project_Budget_Input.xlsx')
# Swapped 2026-08-21 to the new Resi-specific template — verified all 19 sheet names and every
# cell this script writes to line up identically with the old "template 2026.xlsx" (same labels,
# same layout), so no other change was needed here. The old file is left in place, untouched.
# Commercial has its own new template ("202608 - 2027 Commercial Budget Form.xlsx") but this
# script's cost logic is still Residential-only (see the Property Segment guard in read_input()
# above) — swapping in the Commercial template would load fine but fill it with wrong numbers.
TEMPLATE_PATH = os.path.join(BASE, 'input', 'template', '202608 - 2027 Resi Budget Form.xlsx')
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
        # Real, negotiated contract terms — see build_project_input_form.py's comment on these
        # cells. Both None (the real, honest default) until the PM enters the actual contract.
        savills_fee_fixed_monthly=pi['B30'].value, savills_fee_pct=pi['B31'].value,
    )
    if project['savills_fee_fixed_monthly'] and project['savills_fee_pct']:
        raise ValueError(
            "Project Info!B30 (Fixed Monthly Fee) and B31 (% of Collected Fee) are BOTH filled in — "
            "pick one basis for Savills' management fee, not both. Clear whichever doesn't apply."
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

# A handful of leaf rows across this template's real-data sheets carry a leftover date/time
# number_format on their H:S cells (residue from whatever real project this template copy was
# last used on) — writing a plain VND integer into a date-formatted cell reads back fine in-memory,
# but the NEXT openpyxl load+save cycle (add_comparison_sheet, right after these run) reinterprets
# the out-of-range serial as an error and bakes in a literal #VALUE!, which then poisons every
# SUM()/SUBTOTAL() that rolls up through it. Forcing a real number format on every cell these
# helpers write avoids that corruption — see fill_management_fund_sheet's original discovery of
# this bug for the full story.
_NUM_FMT = '#,##0'


_REMARKS_COL = 20  # T — real header in every real-data sheet: "Remarks (please give the full,
                   # detailed reason for each cost item's increase/decrease)". Every cell this
                   # generator fills gets a real remark explaining the actual formula/source/numbers
                   # used, not just a value with no explanation of where it came from.


def _write_remark(ws, row, remark):
    if not remark:
        return
    cell = ws.cell(row=row, column=_REMARKS_COL, value=remark)
    cell.alignment = Alignment(wrap_text=True, vertical='top')


def _write_even_monthly_row(ws, row, annual_amount, remark=None):
    """Even 1/12 split — the right default for a flat run-rate cost/revenue that doesn't depend on
    occupancy fill (management fee, staff, utilities, service contracts)."""
    monthly = round(annual_amount / 12)
    ws.cell(row=row, column=3, value='Monthly')  # C: Frequency
    for col in (6, *range(8, 20)):  # F: Unit Price (monthly, drives G=F*12); H:S shown for transparency
        cell = ws.cell(row=row, column=col, value=monthly)
        cell.number_format = _NUM_FMT
    _write_remark(ws, row, remark)


def _write_year1_lump_row(ws, row, annual_amount, remark=None):
    """Year-1 lump sum in month 1 (Schedule frequency, G=SUM(H:S)) — for one-time Capex, matching
    the sinking-fund treatment (100% Year 1) already used elsewhere in this pipeline."""
    ws.cell(row=row, column=3, value='Schedule')  # C: Frequency -> G = SUM(H:S)
    for col, value in [(8, round(annual_amount))] + [(c, 0) for c in range(9, 20)]:
        cell = ws.cell(row=row, column=col, value=value)
        cell.number_format = _NUM_FMT
    _write_remark(ws, row, remark)


# Real, cited flat reference costs added 2026-08-27 from input/logic/EXENSIVE LOGIC.xlsx's new
# Sheet2 (a "COST NATURE DESCRIPTION" column added alongside a second real capex catalog file —
# both re-scanned per the PM's request). Each cites a real regulation, vendor quote, or lab price
# in the source cell; see the write_even_monthly() calls below for the exact figure and citation.
# Public liability insurance (ESI2, real: ~1,000 USD/year premium, real: 1M USD liability cap) is
# NOT included — no real USD/VND conversion rate exists anywhere in this codebase, and guessing one
# would be exactly the kind of fabrication this pipeline has avoided everywhere else.
ENV_REPORT_ANNUAL = 25_000_000            # ESM2 — Decree 40/2019/NĐ-CP Article 47; real service quote
WATER_TEST_SAMPLE_PRICE = 1_352_000       # ESM3 — Pasteur Institute HCMC quote, per QCVN 01-2024/BYT
WATER_TEST_SAMPLES_PER_ROUND = 3          # rooftop tank + basement + 1 random tap, 2 rounds/year
POOL_TEST_SAMPLE_PRICE = 1_366_000        # ESM5 — real estimate, 4 microbiological parameters/sample
POOL_TEST_SAMPLES_PER_YEAR = 8            # 4 rounds/year x 2 samples/round
FIRE_DEPT_CONNECTION_MONTHLY = 500_000    # ESM8 — GSAFE package G500, HCMC Fire Fighting Dept transmission

# Real leaf rows in "2. Budget-Management Fund" (536 rows, verified against the live 2026-08-21
# Resi template) that generate_project_output.py's pipeline actually computes real numbers for, PLUS
# (as of 2026-08-27) 4 real flat-reference costs cited directly in the logic spec above — everything
# ELSE in that sheet (hundreds of granular sub-system Repairs & Maintenance rows, ~19 Admin Expense
# office-line-items, most Insurance/Bank/Audit/Tax rows) still has no matching real data in this
# pipeline and is deliberately left as the template's own blank default rather than guessed;
# confirmed with the PM (2026-08-21) rather than assumed. Row numbers are fixed positions in the
# template, not computed — verified once against the real file; if Savills ever reshapes this
# template, these will need re-verifying against the new row numbers.
MGMT_FUND_ROWS = {
    'mgmt_fee_revenue': 14,     # RM.AP  Management fee of Apartment (revenue)
    'mgmt_fee_expense': 82,     # EMH1   Management fee for Savills (fund pays it out to Savills)
    'staff_remainder': 83,      # EMH2   Staff cost for Savills (all roster positions except Security/Cleaning/Landscape, which get their own outsourced-contract rows below)
    'parking_moto': 26,         # RP1    Motorbike monthly parking (revenue)
    'parking_car': 27,          # RP2    Car monthly parking (revenue)
    'security': 145,            # ESS1   Security service
    'cleaning': 148,            # ESS4   Cleaning service for common area
    'landscape': 160,           # ESS16  Landscaping service
    'pool_salt': 196,           # ESM4   Chemicals for pool (only written if project has a pool)
    'water': 230,               # EEW.C  Water for Common Area and Facilities
    'electricity': 240,         # EEE.C  Electricity for Common Area
    'diesel': 251,              # EED.C  Diesel for back up generators of Common Area and Facilities
    'capex_mo': 223,            # EN1    New capital expenditure for MO
    'capex_me': 224,            # EN2    New capital expenditure for ME team
    'capex_public': 225,        # EN3    New capital expenditure for Common area
    'capex_amenity': 226,       # EN4    New capital expenditure for Tenant area
    'env_report': 194,          # ESM2   Outsourcing Environmental Report
    'water_testing': 195,       # ESM3   Domestic water testing
    'pool_testing': 197,        # ESM5   Pool water testing (only written if project has a pool)
    'fire_dept_connect': 200,   # ESM8   Connect to HCMC Fire Fighting Dept
}


def fill_management_fund_sheet(wb, project, demand, year, derived_rate):
    """Populates the real computed OPEX/Capex/Staff/Parking/Management-Fee numbers this pipeline
    already derives elsewhere (generate_project_output.py) into '2. Budget-Management Fund''s
    pre-labeled leaf rows (MGMT_FUND_ROWS above). Only leaf-row cells (C/F/H:S) are touched — every
    parent/section row above them (e.g. row 13's =SUBTOTAL(9,G14:G24)) is already a live formula in
    the template and rolls these up automatically, verified against the real file before writing
    this.

    Security/Cleaning/Landscape are pulled OUT of the generic staff total and given their own
    outsourced-contract rows (ESS1/ESS4/ESS16) — the template already has dedicated rate/m² detail
    sheets for exactly those 3, so leaving them inside the lump staff-cost line would double-count
    them. Confirmed with the PM (2026-08-21) rather than assumed.

    Monthly columns (H:S): OPEX/Staff/Revenue use an even 1/12 split (flat run-rate regardless of
    occupancy fill — management/utility costs don't scale with how full the building is). Capex
    uses a Year-1 lump sum in month 1 (Schedule frequency), matching the sinking-fund treatment
    (100% Year 1, reserve thereafter) already used in generate_project_output.py's Owner Operating
    Position / Savills Fee Position sheets — this sheet only covers one calendar year, so it gets
    the Year-1 (full lump) value. Both choices confirmed with the PM (2026-08-21)."""
    ws = wb['2. Budget-Management Fund']

    def write_even_monthly(key, annual_amount, remark=None):
        if annual_amount:
            _write_even_monthly_row(ws, MGMT_FUND_ROWS[key], annual_amount, remark)

    def write_year1_lump(key, annual_amount, remark=None):
        if annual_amount:
            _write_year1_lump_row(ws, MGMT_FUND_ROWS[key], annual_amount, remark)

    # ---- Staff (roster) — replicated in pure Python from the same `demand` rows and formula
    # build_staff_sheet (generate_project_output.py) writes as live Excel formulas; see that
    # function's docstring for the source maths this mirrors. ----
    from generate_project_output import (
        NIGHT_SHIFT_CODES, NIGHT_DIFFERENTIAL, SERVICE_CATEGORY_KEYWORDS, SERVICE_EXCLUDE_KEYWORDS,
        PARKING_FEE_CAR_MONTHLY, PARKING_FEE_MOTO_MONTHLY, EMPLOYER_INSURANCE_RATE,
    )

    def position_annual_cost(d):
        staff_per_day, coverage_days, daily_rate = d['StaffPerDay'], d['CoverageDays'], d['AvgDailyRate']
        is_night = d['ShiftCode'] in NIGHT_SHIFT_CODES
        eff_count = math.ceil(staff_per_day * 7 / 6) if coverage_days >= 7 else staff_per_day
        frac_days = 6 if coverage_days >= 7 else coverage_days
        total = 0.0
        for m in range(1, 13):
            days_in_month = cal.monthrange(year, m)[1]
            monthly = eff_count * math.floor(days_in_month * frac_days / 7 + 0.5) * daily_rate
            if is_night:
                monthly *= NIGHT_DIFFERENTIAL
            total += monthly
        # Employer Social/Health/Unemployment Insurance contribution — real rate, see
        # EMPLOYER_INSURANCE_RATE's definition in generate_project_output.py. Required by
        # input/logic/EXENSIVE LOGIC.xlsx's EMH2 formula; matches build_staff_sheet's own
        # 'Annual Total (incl. Employer Insurance)' column so this fill never drifts from it.
        return total * (1 + EMPLOYER_INSURANCE_RATE)

    per_position = {d['Position']: position_annual_cost(d) for d in demand}
    staff_grand_total = sum(per_position.values())

    def category_cost(cat, excluded=False):
        keywords = SERVICE_CATEGORY_KEYWORDS[cat]
        return sum(v for pos, v in per_position.items()
                   if any(kw in pos.lower() for kw in keywords)
                   and (any(ex in pos.lower() for ex in SERVICE_EXCLUDE_KEYWORDS) if excluded
                        else not any(ex in pos.lower() for ex in SERVICE_EXCLUDE_KEYWORDS)))

    security_cost = category_cost('Security')
    cleaning_cost = category_cost('Cleaning') + category_cost('Cleaning', excluded=True)
    landscape_cost = category_cost('Landscape')
    staff_remainder = staff_grand_total - security_cost - cleaning_cost - landscape_cost

    n_security = sum(1 for d in demand if any(kw in d['Position'].lower() for kw in SERVICE_CATEGORY_KEYWORDS['Security']))
    n_cleaning = sum(1 for d in demand if any(kw in d['Position'].lower() for kw in SERVICE_CATEGORY_KEYWORDS['Cleaning']))
    n_landscape = sum(1 for d in demand if any(kw in d['Position'].lower() for kw in SERVICE_CATEGORY_KEYWORDS['Landscape']))

    write_even_monthly('security', security_cost, remark=(
        f"= {n_security} Security position(s) from Staffing Demand (headcount x real AvgDailyRate x coverage days, "
        f"annualized) x {EMPLOYER_INSURANCE_RATE:.1%} employer insurance (Fact_StaffCost.csv, real) = "
        f"{security_cost:,.0f} VND/year. Source: Staff (Roster) sheet, Project_Budget_Output.xlsx."))
    write_even_monthly('cleaning', cleaning_cost, remark=(
        f"= {n_cleaning} Cleaning position(s) (incl. Supervisory) from Staffing Demand, same headcount x rate x "
        f"coverage-days formula as Security above, x {EMPLOYER_INSURANCE_RATE:.1%} employer insurance = "
        f"{cleaning_cost:,.0f} VND/year."))
    write_even_monthly('landscape', landscape_cost, remark=(
        f"= {n_landscape} Landscape/Gardener position(s) from Staffing Demand, same formula, x "
        f"{EMPLOYER_INSURANCE_RATE:.1%} employer insurance = {landscape_cost:,.0f} VND/year. "
        f"(Conditional — 0 and left blank if the project has no garden area.)"))
    write_even_monthly('staff_remainder', staff_remainder, remark=(
        f"= Full roster annual cost incl. {EMPLOYER_INSURANCE_RATE:.1%} employer insurance ({staff_grand_total:,.0f}) "
        f"MINUS Security ({security_cost:,.0f}) MINUS Cleaning ({cleaning_cost:,.0f}) MINUS Landscape "
        f"({landscape_cost:,.0f}) — those 3 are priced separately above (ESS1/ESS4/ESS16) so they aren't "
        f"double-counted here. = {staff_remainder:,.0f} VND/year. Source: Staff (Roster) sheet."))

    # ---- Management fee revenue (Apartment only — same scope as this pipeline's other real
    # writes on '0. Info'!I8; other product types aren't priced here today) ----
    mgmt_fee_annual = derived_rate * project['apartment_nfa'] * 12
    write_even_monthly('mgmt_fee_revenue', mgmt_fee_annual, remark=(
        f"= Derived Apartment management-fee rate ({derived_rate:,.0f} VND/m²/month, nearest-comparable-matched — "
        f"see '0. Info'!I8 and the Comparison sheet) x Apartment NFA ({project['apartment_nfa']:,.0f} m²) x 12 "
        f"= {mgmt_fee_annual:,.0f} VND/year."))
    # EMH1 (Savills' own fee) is NOT the collected management fee — that's the fund's REVENUE, most
    # of which is meant to pay for the real staff/OPEX/Capex costs already itemized elsewhere on
    # this sheet. Before 2026-08-28 this wrongly set EMH1 = mgmt_fee_annual (the entire collected
    # fee), which double-counted against every other cost line and produced a large fake "deficit"
    # (confirmed on Blue Skyline: 6.3bn of a ~7.5bn gap against the real Green Skyline back-test was
    # this one bug). The correct value is a real, negotiated, per-project contract term this
    # pipeline cannot derive — see Project Info!B30/B31 (build_project_input_form.py's comment).
    # Left BLANK, not defaulted to 0 or to the old wrong assumption, until the PM enters one.
    if project.get('savills_fee_fixed_monthly'):
        savills_fee_annual = project['savills_fee_fixed_monthly'] * 12
        write_even_monthly('mgmt_fee_expense', savills_fee_annual, remark=(
            f"= Real fixed fee (Project Info!B30) {project['savills_fee_fixed_monthly']:,.0f} VND/month x 12 "
            f"= {savills_fee_annual:,.0f} VND/year."))
    elif project.get('savills_fee_pct'):
        savills_fee_annual = mgmt_fee_annual * project['savills_fee_pct']
        write_even_monthly('mgmt_fee_expense', savills_fee_annual, remark=(
            f"= Real fee rate (Project Info!B31) {project['savills_fee_pct']:.1%} x Management Fee Revenue "
            f"(RM.AP, above) {mgmt_fee_annual:,.0f} = {savills_fee_annual:,.0f} VND/year."))
    # else: left blank — no real contract term entered yet (Project Info!B30/B31 both empty).

    # ---- Parking Fee revenue (real rate x real slot counts, at 100% occupancy — see
    # build_additional_revenue_sheet's docstring for why that's a ceiling, not a realistic average) ----
    moto_slots = project.get('moto_slots') or 0
    car_slots = project.get('car_slots') or 0
    parking_moto_annual = PARKING_FEE_MOTO_MONTHLY * moto_slots * 12
    parking_car_annual = PARKING_FEE_CAR_MONTHLY * car_slots * 12
    write_even_monthly('parking_moto', parking_moto_annual, remark=(
        f"= {PARKING_FEE_MOTO_MONTHLY:,.0f} VND/month (real rate, A&K Tower's own proposed parking price) x "
        f"{moto_slots:,.0f} motorbike slots (Project Info) x 12 = {parking_moto_annual:,.0f} VND/year. "
        f"At 100% occupancy — a ceiling, not a realistic average (no real occupancy data exists)."))
    write_even_monthly('parking_car', parking_car_annual, remark=(
        f"= {PARKING_FEE_CAR_MONTHLY:,.0f} VND/month (real rate, A&K Tower's own proposed parking price) x "
        f"{car_slots:,.0f} car slots (Project Info) x 12 = {parking_car_annual:,.0f} VND/year. "
        f"At 100% occupancy — a ceiling, not a realistic average (no real occupancy data exists)."))

    # ---- OPEX (Electricity/Water/Diesel — common-area usage; Repairs & Maintenance and Admin
    # Expense are single aggregates in this pipeline but split into 30+/19 specific sub-system rows
    # in the template, so are deliberately left blank rather than forced into one arbitrary row) ----
    opex = estimate_opex(project['total_nfa'], has_pool=project.get('has_pool', False))

    def _opex_remark(category):
        entry = opex.get(category, {})
        annual = entry.get('monthly_vnd', 0) * 12
        if entry.get('ratio_per_m2') is not None:
            return (f"= A&K Tower's real per-m² NFA ratio for {category} ({entry['ratio_per_m2']:,.2f} VND/m²/month, "
                    f"n=1 — the only residential property with independently-verified OPEX data) x this project's "
                    f"Total NFA ({project['total_nfa']:,.0f} m²) x 12 = {annual:,.0f} VND/year.")
        return f"= A&K Tower's real flat monthly reference for {category} x 12 = {annual:,.0f} VND/year (not NFA-scaled)."

    write_even_monthly('water', opex.get('Water', {}).get('monthly_vnd', 0) * 12, remark=_opex_remark('Water'))
    write_even_monthly('electricity', opex.get('Electricity', {}).get('monthly_vnd', 0) * 12, remark=_opex_remark('Electricity'))
    write_even_monthly('diesel', opex.get('Diesel (Generator Fuel)', {}).get('monthly_vnd', 0) * 12,
                        remark=_opex_remark('Diesel (Generator Fuel)'))
    if project.get('has_pool'):
        write_even_monthly('pool_salt', opex.get('Pool Salt', {}).get('monthly_vnd', 0) * 12,
                            remark=(_opex_remark('Pool Salt') +
                                    " Not scaled by pool size/volume — no real data ties pool-salt cost to pool "
                                    "area across more than one property."))

    # ---- Real flat-reference costs from input/logic/EXENSIVE LOGIC.xlsx's Sheet2 (see
    # ENV_REPORT_ANNUAL etc.'s definitions above for the exact citation each one carries) ----
    write_even_monthly('env_report', ENV_REPORT_ANNUAL, remark=(
        f"{ENV_REPORT_ANNUAL:,.0f} VND/year — real periodic environmental report service quote. "
        f"Legally required every 6 months per Decree 40/2019/ND-CP Article 47 (air quality & "
        f"emissions monitoring). Source: input/logic/EXENSIVE LOGIC.xlsx."))
    water_test_annual = WATER_TEST_SAMPLE_PRICE * WATER_TEST_SAMPLES_PER_ROUND * 2
    write_even_monthly('water_testing', water_test_annual, remark=(
        f"= {WATER_TEST_SAMPLE_PRICE:,.0f} VND/sample x {WATER_TEST_SAMPLES_PER_ROUND} samples "
        f"(rooftop tank + basement + 1 random tap) x 2 rounds/year = {water_test_annual:,.0f} VND/year. "
        f"Real Pasteur Institute HCMC quote; 12 parameters tested per QCVN 01-2024/BYT (eff. Jul 2025). "
        f"Source: input/logic/EXENSIVE LOGIC.xlsx."))
    if project.get('has_pool'):
        pool_test_annual = POOL_TEST_SAMPLE_PRICE * POOL_TEST_SAMPLES_PER_YEAR
        write_even_monthly('pool_testing', pool_test_annual, remark=(
            f"= {POOL_TEST_SAMPLE_PRICE:,.0f} VND/sample x {POOL_TEST_SAMPLES_PER_YEAR} samples "
            f"(4 rounds/year x 2 samples/round, 4 microbiological parameters each incl. E.coli) "
            f"= {pool_test_annual:,.0f} VND/year. Source: input/logic/EXENSIVE LOGIC.xlsx."))
    fire_dept_annual = FIRE_DEPT_CONNECTION_MONTHLY * 12
    write_even_monthly('fire_dept_connect', fire_dept_annual, remark=(
        f"= {FIRE_DEPT_CONNECTION_MONTHLY:,.0f} VND/month (GSAFE package G500, fire-alarm transmission "
        f"to HCMC Fire Fighting Dept) x 12 = {fire_dept_annual:,.0f} VND/year. Real vendor package price, "
        f"referenced across similar Savills-managed HCMC projects. Applies to HCMC projects specifically — "
        f"a project outside HCMC would connect to a different local authority at a different real price, "
        f"not this one. Source: input/logic/EXENSIVE LOGIC.xlsx."))

    # ---- Capex — Year-1 lump sum (see docstring above) ----
    capex_items, capex_source = estimate_capex_items(project['total_nfa'], exclude_name=project['name'])
    capex_annual = {}
    capex_counts = {}
    for it in capex_items:
        capex_annual[it['category']] = capex_annual.get(it['category'], 0) + it['unit_price'] * it['qty']
        capex_counts[it['category']] = capex_counts.get(it['category'], 0) + 1
    source_project = capex_source.get('source_project', 'the nearest real comparable') if capex_source else 'the nearest real comparable'
    scale_factor = capex_source.get('scale_factor') if capex_source else None

    def _capex_remark(category):
        n = capex_counts.get(category, 0)
        amount = capex_annual.get(category, 0)
        scale_note = f" (NFA scale factor {scale_factor}x)" if scale_factor else ""
        return (f"= Sum(Qty x real Unit Price) across {n} {category} item(s), scaled from {source_project}'s own "
                f"real Capex line items (Fact_Capex_Rescanned.csv) by Total NFA ratio{scale_note} = {amount:,.0f} "
                f"VND — booked as a full Year-1 lump sum (sinking-fund treatment: 100% Year 1, reserve thereafter).")

    write_year1_lump('capex_mo', capex_annual.get('MO Equipment', 0), remark=_capex_remark('MO Equipment'))
    write_year1_lump('capex_me', capex_annual.get('M&E Equipment', 0), remark=_capex_remark('M&E Equipment'))
    write_year1_lump('capex_public', capex_annual.get('Public Area', 0), remark=_capex_remark('Public Area'))
    write_year1_lump('capex_amenity', capex_annual.get('Amenity Area', 0), remark=_capex_remark('Amenity Area'))


# "2.2 Common area Fund" is a SEPARATE real fund from "2. Budget-Management Fund" — same ~500-code
# catalog structure, but scoped to common-area commercial exploitation (advertising/rentals/visitor
# parking) rather than the whole-building management fee. Its EMH/ESS/EN/EE/etc. rows are the exact
# same codes already filled on "2. Budget-Management Fund"; writing the same Staff/OPEX/Capex
# numbers here too would double-count them, since this pipeline has no real cost-allocation split
# telling us how much of each belongs to which fund — so only genuinely NEW, fund-specific revenue
# goes here. Row numbers verified once against the real file, same caveat as MGMT_FUND_ROWS above.
COMMON_AREA_FUND_ROWS = {
    'lcd_ad': 20,     # RA1.A  LCD Advertising for Apartment
    'lift_ad': 26,    # RA2    Decal Advertising for Lift
}


def fill_common_area_fund_sheet(wb, project):
    """Elevator/lobby advertising revenue — real per-device rates (Fact_MasterRateCard.csv) already
    computed by generate_project_output.py's build_additional_revenue_sheet (ELEVATOR_AD_ITEMS),
    just never placed into the real template before. "Ad frame (tower lobby, inside elevator)" maps
    to RA2 (elevator-specific); the two LCD screen items (tower + basement lobby) combine into RA1.A
    (a generic lobby LCD line, no separate "basement" row in this template). Qty is a stated
    assumption (towers × qty-per-tower, or a flat count), not real per-project elevator-count data —
    same disclosure as the source sheet. Confirmed with the PM (2026-08-21) rather than assumed."""
    from generate_project_output import ELEVATOR_AD_ITEMS
    ws = wb['2.2 Common area Fund']

    towers = project.get('towers') or 1
    lift_annual, lcd_annual = 0.0, 0.0
    lift_parts, lcd_parts = [], []
    for item, rate, qty_per_tower, flat_qty, assumption in ELEVATOR_AD_ITEMS:
        qty = (qty_per_tower * towers) if qty_per_tower is not None else flat_qty
        annual = rate * qty * 12
        part = f"{item}: {rate:,.0f} VND/device/month x {qty:g} device(s) x 12 = {annual:,.0f} ({assumption})"
        if 'inside elevator' in item.lower():
            lift_annual += annual
            lift_parts.append(part)
        else:
            lcd_annual += annual
            lcd_parts.append(part)

    _write_even_monthly_row(ws, COMMON_AREA_FUND_ROWS['lift_ad'], lift_annual, remark=(
        "= " + " + ".join(lift_parts) + f" = {lift_annual:,.0f} VND/year total. "
        "Rate: Fact_MasterRateCard.csv, Service domain, 'Elevator advertising' (real)."))
    _write_even_monthly_row(ws, COMMON_AREA_FUND_ROWS['lcd_ad'], lcd_annual, remark=(
        "= " + " + ".join(lcd_parts) + f" = {lcd_annual:,.0f} VND/year total. "
        "Rate: Fact_MasterRateCard.csv, Service domain, 'Elevator advertising' (real)."))


# "1. Staff cost From 08.2026 (VN)" was pasted into the template by the PM on 2026-08-28 — a REAL
# Savills payroll-calculator sheet (13th month, PIT brackets, SI/HI, Trade Union 2%, 10% admin
# markup — see that sheet's own formulas), not something this pipeline built. Only column G
# (Current Gross Salary, the one real INPUT cell) is written here; every other column is the
# template's own live formula chain computing net pay/insurance/tax/admin fee FROM that input —
# left completely untouched, so the sheet's own math does the work, not a re-implementation of it.
#
# Only positions that exist in THIS project's own Staffing Demand AND have a matching row-group in
# the template get filled — Security/Cleaning/Landscape are deliberately excluded (those are
# outsourced-contract lines already priced separately on "2. Budget-Management Fund" ESS1/ESS4/
# ESS16, exactly matching what EMH2 "Staff cost for Savills" already excludes); Reception has no
# row-group in this sheet at all (it lives on the dedicated "B1. Lịch Lễ tân" sheet instead).
# APM/OM/CSS/ACC/CSR/ACE/ADCE genuinely aren't in Blue Skyline's current Staffing Demand — left
# blank rather than invented; add those positions to Staffing Demand first if they should be
# costed. Real 25-workdays/month conversion sourced from this same template's own
# "1.1 Allowance" sheet (E7=25), not assumed. Night-shift/holiday premiums are NOT folded in here —
# they're what that Allowance sheet's own formulas already exist to compute separately.
STAFF_COST_SHEET = '1. Staff cost From 08.2026 (VN)'
WORKDAYS_PER_MONTH = 25  # real — '1.1 Allowance (From 08.2026)'!E7 in this same template

# keyword -> template abbreviation code (column D groups), matched the same way
# SERVICE_CATEGORY_KEYWORDS/STAFF_MARKET_KEYWORDS already match Staffing Demand positions elsewhere
STAFF_COST_KEYWORDS = {
    'PM': ['property manager'],
    'BE': ['building executive'],
    'CS': ['customer service'],
    'CE': ['chief engineer'],
    'TDS': ['shift leader'],
    'TN': ['technician'],
}
# Split across two template row-groups both abbreviated 'AA' (pool staff vs. gym staff) — resolved
# by keyword instead of the shared abbreviation, using the row's own item label (Z/B column text
# containing "hồ bơi"/"pool" vs "gym") to tell the two groups apart.
STAFF_COST_AA_KEYWORDS = {'pool': ['pool attendant'], 'gym': ['amenities attendant']}


def fill_staff_cost_sheet(wb, project, demand, year):
    if STAFF_COST_SHEET not in wb.sheetnames:
        return  # older template version without this sheet — nothing to fill
    ws = wb[STAFF_COST_SHEET]

    def eff_headcount(d):
        p, q = d['StaffPerDay'], d['CoverageDays']
        return math.ceil(p * 7 / 6) if q >= 7 else p

    def group_stats(keywords):
        matched = [d for d in demand if any(kw in d['Position'].lower() for kw in keywords)]
        if not matched:
            return 0, 0
        total_headcount = sum(eff_headcount(d) for d in matched)
        if total_headcount == 0:
            return 0, 0
        weighted_daily = sum(eff_headcount(d) * d['AvgDailyRate'] for d in matched) / total_headcount
        monthly_gross = round(weighted_daily * WORKDAYS_PER_MONTH)
        return total_headcount, monthly_gross

    # Find each abbreviation's contiguous row-group by scanning column D (template's own layout,
    # not hardcoded row numbers — self-verifying against whatever row positions this copy has).
    rows_by_code = {}
    for r in range(15, 89):
        code = ws.cell(row=r, column=4).value
        label = ws.cell(row=r, column=2).value
        # Pool and gym staff share the same 'AA' abbreviation in this template — the label is the
        # only thing that tells them apart, so it's checked BEFORE falling back to the code column
        # (checking code first would silently merge both groups under one generic 'AA' bucket).
        if label and 'hồ bơi' in str(label).lower():
            rows_by_code.setdefault('AA_POOL', []).append(r)
        elif label and 'gym' in str(label).lower():
            rows_by_code.setdefault('AA_GYM', []).append(r)
        elif code:
            rows_by_code.setdefault(str(code).strip(), []).append(r)
    # Property Manager (row 15) has no abbreviation of its own — it's the sheet's single named row.
    pm_row = 15

    def fill_group(rows, headcount, monthly_gross):
        if not rows or headcount == 0:
            return
        for r in rows[:headcount]:
            c = ws.cell(row=r, column=7, value=monthly_gross)  # G: Current Gross Salary
            c.number_format = '#,##0'

    for code, keywords in STAFF_COST_KEYWORDS.items():
        headcount, monthly_gross = group_stats(keywords)
        if code == 'PM':
            if monthly_gross:
                c = ws.cell(row=pm_row, column=7, value=monthly_gross)
                c.number_format = '#,##0'
            continue
        fill_group(rows_by_code.get(code, []), headcount, monthly_gross)

    for suffix, keywords in STAFF_COST_AA_KEYWORDS.items():
        headcount, monthly_gross = group_stats(keywords)
        fill_group(rows_by_code.get(f'AA_{suffix.upper()}', []), headcount, monthly_gross)


def build_budget(project, demand, year):
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

    # The two "Report-" sheets ship with a hardcoded 'AAA' placeholder in their project-name header,
    # so they were the only sheets still showing 'AAA' in the delivered file. "3.1 Report-Sinking
    # Fund" solves this in the template itself with a cross-sheet formula; reusing that exact
    # convention here keeps ONE source of truth (Budget-Management Fund!AH5, set just above) instead
    # of writing the literal name into three separate places that could later drift apart.
    # NB: do NOT reach for AH5 on every sheet — on "2.2 Common area Fund" that same cell holds the
    # budget YEAR (2027), not a name.
    for sheet in ('2.1 Report-Management Fund', '2.2.1 Report-Common area Fund'):
        wb[sheet]['H4'] = "='2. Budget-Management Fund'!AH5"

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
    # A5!C2 (PCCC subsidy rate) used to be force-set to 0.06 here, but the 2026-08-21 Resi template
    # ships its own updated default (0.078) in that cell — left alone now so the template's own,
    # more current reference value survives instead of being overwritten by this older guess.
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

    # ---- 2. Budget-Management Fund: real computed OPEX/Capex/Staff/Parking/Management-Fee
    # numbers — see MGMT_FUND_ROWS and fill_management_fund_sheet()'s docstring above. ----
    fill_management_fund_sheet(wb, project, demand, year, derived_rate)

    # ---- 2.2 Common area Fund: real elevator/lobby advertising revenue — see
    # COMMON_AREA_FUND_ROWS and fill_common_area_fund_sheet()'s docstring above. ----
    fill_common_area_fund_sheet(wb, project)

    # ---- 1. Staff cost: real per-position headcount/salary from Staffing Demand, mapped onto
    # the PM's own payroll-calculator sheet — see fill_staff_cost_sheet()'s docstring above. ----
    fill_staff_cost_sheet(wb, project, demand, year)

    # Safety net for a real bug class hit this session: Remarks text like "= Derived Apartment
    # management-fee rate... = 13,089,600,000 VND/year" gets serialized by openpyxl as an actual
    # FORMULA (any string cell value starting with "=" is written as <f>...</f>), which Excel then
    # can't parse and strips on open ("Removed Records: Formula from .../sheetN.xml part" —
    # exactly the repair dialog this produced). Same fix generate_project_output.py already applies
    # to its own workbook; reused here rather than re-implemented, so both stay in sync.
    # Imported locally, not at module level: generate_project_output imports read_input/INPUT_PATH/
    # PRODUCT_ROWS from THIS module, so a top-level import here would be circular. Same pattern as
    # the other cross-module imports in this file.
    from generate_project_output import _fix_fake_formula_strings, _strip_onedrive_zip_artifacts
    _fix_fake_formula_strings(wb)

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
        # sample_output/ is inside the synced OneDrive tree, same as reports/ — so it gets the same
        # "[trash]/*.dat" zip-artifact injection that makes Excel throw a repair dialog. This call
        # was missing here (only generate_project_output.py had it), which is how a delivered budget
        # file was found corrupted on 2026-08-26. The injection lands at a VARIABLE delay after the
        # copy, so the stripper polls until stable rather than checking once.
        _strip_onedrive_zip_artifacts(out_path)
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
    from generate_project_output import _strip_onedrive_zip_artifacts  # local import — see build_budget()
    try:
        os.makedirs(ROSTER_OUT_DIR, exist_ok=True)
        shutil.copyfile(ROSTER_OUT, ROSTER_FINAL_OUT)
        print('Copied into place:', ROSTER_FINAL_OUT)
        _strip_onedrive_zip_artifacts(ROSTER_FINAL_OUT)  # reports/ is OneDrive-synced — see build_budget()
        return ROSTER_FINAL_OUT
    except PermissionError as e:
        print('Could not copy into place yet (still locked):', e)
        print('Local copy remains valid at:', ROSTER_OUT)
        return ROSTER_OUT


def main():
    project, ratios, month, year, holiday_days, demand = read_input(INPUT_PATH)
    budget_path = build_budget(project, demand, year)
    roster_path = build_roster(project, ratios, month, year, holiday_days, demand)
    print('\nDone.')
    print('Budget:', budget_path)
    print('Roster:', roster_path)


if __name__ == '__main__':
    main()
