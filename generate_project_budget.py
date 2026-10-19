"""
Unified generator — reads the ONE merged input file (Project_Budget_Input.xlsx, built by
build_project_input_form.py) and produces:

  1. A filled budget workbook (from template 2026.xlsx) with a Comparison sheet showing this
     project's derived management-fee rate and proposal benchmark; the reference projects it was
     derived from are named only in the internal analysis (generate_project_output.py).
  2. A full calendar-month roster (same formula-driven engine as generate_roster.py), reading
     staffing ratios and demand from the same input file.

Replaces the earlier split (build_roster_input_form.py + generate_roster.py for the roster,
generate_from_real_project.py for the budget) with a single input -> two outputs pipeline, and
replaces that script's HARDCODED per-run comparable list with a dynamic lookup against
master_comparables.py (built from real, directly-verified project data — see that module).

Comparable matching is real, not fictional: nearest 2 by |Total building NFA delta| — the same
basis generate_project_output.py uses, so the two workbooks pick the same comparables (change
`unify-revenue-basis-across-outputs`) — excluding the
input project itself by name if it happens to match one already in the master table (so
re-running this against a real project's own numbers, e.g. Green Skyline, doesn't compare it
to itself). The "reality check" row on the Comparison sheet only appears when the input
project's OWN real rate is independently known from the master table — for a genuinely new,
unlisted prospect, it correctly reports "not applicable — new prospect."
"""
import csv
import os
import re
import math
import shutil
import tempfile
import unicodedata
import calendar as cal
import datetime

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import FormulaRule
from openpyxl.comments import Comment

from common_utils_v2 import repair_workbook
from master_comparables import (
    MASTER_COMPARABLES, SECURITY_RATE_CITYWIDE, CLEANING_RATE_CITYWIDE, LANDSCAPE_RATE_CITYWIDE,
    RATE_CARD_SOURCE, resolve_product_rates,
)
from estimate_opex import estimate_opex
from estimate_capex_qty import estimate_capex_items
from input_labels import SheetLabels, normalise
import budget_period
import vn_holidays
import utility_tariffs
import existing_staffing
import existing_utilities
import operating_inputs
import contingency
import savills_fee
import breakeven_cells
import real_budget_ranges
from fill_curve import (year1_fills, year1_electricity_fills, parking_fills,
                        MONTH_ANCHORS as FILL_ANCHORS)

SOURCE_DIR = os.path.dirname(__file__)
BUDGET_AGENT = os.path.abspath(os.path.join(SOURCE_DIR, '..'))
BASE = os.path.abspath(os.path.join(SOURCE_DIR, '..', '..'))

INPUT_PATH = os.path.join(BUDGET_AGENT, 'reports', 'Project_Budget_Input.xlsx')
# Swapped 2026-09-10 to Savills' current standard form (decision D6, change
# `rebase-output-onto-25-sheet-form`). It is the 25-sheet AI Guideline Resi form with its
# instruction columns removed and `Master Info` dropped — see input/template/README.md and
# `build_standard_template.py` in that change. `2. Budget-Management Fund` and `2.2 Common area
# Fund` are row-identical to the superseded `202608` form (every code this script writes sits at
# the same row — the guards in fill_management_fund_sheet / fill_common_area_fund_sheet check that
# on every run); it adds the resident/parking fill-up sheets and the QĐ 67/2025 waste sheet as
# blank scaffolding for later changes, and carries the standard `1. Summary` / sinking-fund sheets.
# The superseded `202608 - 2027 Resi Budget Form.xlsx` stays in input/template/ for rollback.
# Commercial has its own template ("202608 - 2027 Commercial Budget Form.xlsx") but this script's
# cost logic is Residential-only (see the Property Segment guard in read_input()).
TEMPLATE_PATH = os.path.join(BASE, 'input', 'template', '2027 Resi Budget Form (IT team).xlsx')
# The AI Guideline's remark rules — line components, summary-narrative recipes, the VAT-treatment
# sentence — live here, one authority for both this generator and verify.py's remark-content check
# (change apply-guideline-remark-model). Read for wording only; it changes no budgeted figure.
CATALOGUE_PATH = os.path.join(BUDGET_AGENT, 'data', 'master_list_verified', 'Costing_Method_Catalogue.csv')
BUDGET_OUT_DIR = os.path.join(BUDGET_AGENT, 'sample_output')
ROSTER_OUT_DIR = os.path.join(BUDGET_AGENT, 'reports')
ROSTER_FINAL_OUT = os.path.join(ROSTER_OUT_DIR, 'Roster_Demand_Model.xlsx')
ROSTER_OUT = os.path.join(tempfile.gettempdir(), 'Roster_Demand_Model.xlsx')

MAX_DAYS = 31
DAY_COL_START = 3
DAY_COL_END = DAY_COL_START + MAX_DAYS - 1
COL_DAYOFF = DAY_COL_END + 1
COL_SHIFTCODE = DAY_COL_END + 2

# ORDER MATTERS: read_input() pairs this list positionally with the intake form's Product Mix rows
# (row 14 upward), and build_project_input_form.py writes them in this same order. The sequence
# follows the template's own RM.* revenue rows, so form, deliverable and analysis all read alike.
# Changing this list means changing the form's `products` list and the row constants below it.
PRODUCT_ROWS = ['Apartment', 'Officetel', 'Office', 'Shopping Mall', 'Retail',
                'Shop Apartment', 'Shophouse', 'Villas', 'Nursery / Nhà trẻ']

# Where each product's management-fee revenue is written in "2. Budget-Management Fund".
# Fixed positions in the Savills template, verified against the real file — rows 14-24 are the
# RM.* per-product revenue block. Only the nine products this pipeline can price appear here:
#   RM.0A (Other Area — developer pays on unsold units) needs the occupancy fill-up curve, and
#   RM.PA (management fee on parking areas) needs parking area in m². Neither input exists yet, so
#   both rows are deliberately left blank rather than guessed. See the change's proposal.
PRODUCT_REVENUE_ROWS = {
    'Apartment':          14,   # RM.AP
    'Officetel':          15,   # RM.OT
    'Office':             16,   # RM.OF
    'Shopping Mall':      17,   # RM.SM
    'Retail':             18,   # RM.RE
    'Shop Apartment':     19,   # RM.SA
    'Shophouse':          20,   # RM.SH
    'Villas':             21,   # RM.VI
    'Nursery / Nhà trẻ':  22,   # RM.KG  (Kindergarten)
}
PRODUCT_REVENUE_EXPECTED_CODE = {
    'Apartment': 'RM.AP', 'Officetel': 'RM.OT', 'Office': 'RM.OF', 'Shopping Mall': 'RM.SM',
    'Retail': 'RM.RE', 'Shop Apartment': 'RM.SA', 'Shophouse': 'RM.SH', 'Villas': 'RM.VI',
    'Nursery / Nhà trẻ': 'RM.KG',
}

# --- Comparison-sheet PROPOSAL BENCHMARK section (change benchmark-proposal-against-comparables) ---
# '1. Summary' anchor rows in the standard form (input/template/2027 Resi Budget Form (IT team).xlsx).
# Template-fixed; column H is the annual total. Verified against the template 2026-09-10.
#   row 14 = RM       management-fee revenue        (VLOOKUP into '2. Budget-Management Fund')
#   row 13 = R        total operating income        (=SUBTOTAL(9,H14:H19))
#   row 20 = E        total operating cost          (=SUBTOTAL(9,H21:H45) — Savills' own fee EMH1 blank)
#   row 46 = C.       operating difference          (=H13-H20; before tax and before Savills' fee)
#   row 54 = PART 3:  after-tax estimate            (=H46-H48)
# The benchmark references these by formula so it carries the deliverable's own figures forward
# rather than restating them — see the change's design.md D1.
_SUMMARY_ROW_MGMT_FEE = 14
_SUMMARY_ROW_OPERATING_INCOME = 13
_SUMMARY_ROW_OPERATING_COST = 20
_SUMMARY_ROW_OPERATING_SURPLUS = 46

# Coverage band: year-1 operating surplus ('1. Summary'!H46) as a share of total operating income
# ('1. Summary'!H13). A first proposal for the PM to confirm (design.md Open Questions).
COVERAGE_BAND_THIN_MAX = 0.05
COVERAGE_BAND_NORMAL_MAX = 0.15
COVERAGE_BAND_LABEL = 'shortfall < 0%  ·  thin 0–5%  ·  normal 5–15%  ·  generous > 15%'


def _benchmark_fee_clause(derived_rate, comp_apt_rates, entered=False):
    """The fee-vs-comparable-range half of the PROPOSAL BENCHMARK verdict line, in plain language.
    `comp_apt_rates` is the real Apartment rate (VND/m²/month) of each comparable the rate was
    derived from. Kept module-level so each branch is unit-testable (see the change's tasks 2.6).
    The line goes to the client deliverable, so it names no reference project and quotes none of
    their rates or the range's end points: only where the fee sits, and by how much in percent when
    it is outside (change apply-head-of-pm-decisions-2026-10, D14). The basis is the Apartment rate
    in VND/m²/month, not the fee per apartment (user, 2026-10-19)."""
    rates = [r for r in (comp_apt_rates or []) if r]
    if not rates:
        return (f"No reference project with a verified Apartment rate - the {derived_rate:,.0f} "
                f"VND/m2/month fee cannot be benchmarked against reference projects.")
    lo, hi = min(rates), max(rates)
    head = (f"Proposed Apartment fee {derived_rate:,.0f} VND/m2/month"
            + (" (PM-entered actual rate)" if entered else ""))
    if len(rates) < 2:
        d = (derived_rate - lo) / lo * 100
        where = ("matches" if abs(d) < 0.5
                 else f"is {abs(d):.0f}% {'above' if d > 0 else 'below'}")
        return (f"{head} {where} the real Apartment rate of the one available reference project - "
                f"narrow base, treat as indicative.")
    if lo <= derived_rate <= hi:
        return (f"{head} sits within the range of the reference projects' real Apartment rates - "
                f"in line with what Savills charges for comparable buildings.")
    if derived_rate < lo:
        return (f"{head} is {(lo - derived_rate) / lo * 100:.0f}% below the lowest real Apartment rate "
                f"of the reference projects - review before the proposal goes out.")
    return (f"{head} is {(derived_rate - hi) / hi * 100:.0f}% above the highest real Apartment rate "
            f"of the reference projects - review before the proposal goes out.")

# Ratio-driven Staffing Demand rows — matches the ROUNDUP(...) formulas build_project_input_form.py
# bakes into the Staffing Demand sheet's "Staff On Duty / Day" cells for these exact position
# names. Recomputed HERE in Python (not read from the cell's cached formula value) so a PM who
# edits Project Info or Roster Setup without reopening the file in Excel to force a recalc still
# gets a fresh, correct number — openpyxl reads cached formula results, which go stale silently
# otherwise. Any OTHER position in the sheet (CCTV/Reception — fixed, not ratio-driven — or any
# custom row a PM adds) is left exactly as typed; only these 5 known ratio-driven rows are touched.
# ---- Pool lifeguards (nhân viên cứu hộ) --------------------------------------------------------
# Thông tư 03/2018/TT-BVHTTDL Điều 5 khoản 3: "Số lượng nhân viên cứu hộ phải bảo đảm ít nhất 200m2
# mặt nước bể bơi/01 nhân viên" — at least 200 m2 of pool WATER SURFACE per lifeguard, on continuous
# duty ("thường trực") whenever the pool is open. Full sourcing, currency check and the scope caveat:
# docs/15-pool-staffing-regulation.md.
#
# Three things this deliberately does NOT do, each for a reason recorded in that document:
#   * It does not scale by POOL COUNT. There is no per-pool ratio anywhere in Vietnamese law — three
#     small pools totalling 180 m2 clear the test with one lifeguard; one 400 m2 pool needs two.
#   * It does not apply a "one lifeguard per physically separate pool" floor. That is a supervision
#     judgment, not statute, so it is raised in the basis text for a PM to decide rather than silently
#     added to the figure.
#   * It does not use the tiered "250-500 m2 -> 2, 501-1,000 -> 3" figures that circulate online.
#     Those appear in no statute, current or repealed.
#
# Scope caveat, which is why the basis says "standard" and never "legally required": the circular's
# đối tượng áp dụng reaches any organiser of swimming activity, but its only enforcement hook (the
# fine in Nghị định 46/2019 Điều 20) sits in the sport-BUSINESS regime. For a residents-only chung cư
# pool the ratio is a defensible benchmark; it is not established as a binding obligation.
POOL_LIFEGUARD_M2_PER_STAFF = 200
# Used when the project has a pool but no water-surface area was supplied — A&K Tower's own real
# staffing pattern (one attendant per shift). Same fallback shape ESM4 uses when Pool Volume is
# unknown: keep a real reference figure and say on the row that the stated method could not run.
POOL_ATTENDANT_FALLBACK_PER_SHIFT = 1


def _pool_lifeguards_per_shift(p, r):
    """Lifeguards on duty per shift, and the basis to report for the figure."""
    if not p.get('has_pool'):
        return 0, ("No swimming pool on this project ('Has Swimming Pool?' = No), so no lifeguard "
                   "is budgeted")
    area = p.get('pool_area')
    try:
        area = float(area) if area is not None else 0.0
    except (TypeError, ValueError):
        area = 0.0
    if area <= 0:
        return POOL_ATTENDANT_FALLBACK_PER_SHIFT, (
            "Pool Area (m2) not supplied, so the statutory water-surface calculation could not be "
            "run. Falls back to A&K Tower's own real pattern of one attendant per shift. Enter the "
            "pool water-surface area on Project Info to cost this line to the stated standard "
            "instead")
    return area / POOL_LIFEGUARD_M2_PER_STAFF, (
        f"Pool water surface ({area:,.0f} m2) / {POOL_LIFEGUARD_M2_PER_STAFF} m2 per lifeguard, the "
        f"standard for pool operation in Thong tu 03/2018/TT-BVHTTDL Dieu 5.3 (\"it nhat 200m2 mat "
        f"nuoc be boi/01 nhan vien\"), applied per shift because the circular requires lifeguards on "
        f"continuous duty. NOTE this is the standard for pool operation, NOT an established legal "
        f"obligation for a residents-only pool - its enforcement provision sits in the sport-business "
        f"regime (see docs/15-pool-staffing-regulation.md). It also assumes one attendant can "
        f"supervise every pool: if the pools are physically separated, supervision practice may need "
        f"one per location - a PM judgment, not part of this figure. Shift count comes from the rows "
        f"on the Staffing Demand sheet, under working-hours limits in Bo luat Lao dong 2019, not from "
        f"the pool circular")


# ---- In-house roles, estimated from the portfolio ----------------------------------------------
# Until 2026-09-14 every in-house role on the Staffing Demand sheet (Property Manager, Chief
# Engineer, Technician, Customer Service …) carried a fixed seeded default of 1, because nothing
# tied their headcount to property scale — a 20,000 m² building and a 120,000 m² one were both
# offered one technician, and a PM who zeroed the row got zero back with no estimate behind it.
#
# There IS now a population that answers this: reports/Project_Detail_Lists.xlsx ("Staff Positions by
# Project") carries a real headcount per position for 88 operating properties, and 26 of those match
# by name to a property in Dim_Property_Residential.csv carrying a real NFA. derive_position_staffing
# _ratios.py measures that population and writes Fact_StaffingRatio_ByPosition.csv.
#
# What these ratios are and are not: a portfolio MEDIAN of what comparable buildings actually employ,
# per 1,000 m² of NFA. They are not a standard, a Savills policy, or a statutory minimum — they
# describe what peers do. The spread is wide (P25–P75 is on every row of the CSV), so the figure is a
# starting point a PM is expected to overrule, which the override rule in _staff_on_duty() supports.
_POSITION_RATIO_MIN_N = 10          # a role measured on fewer properties keeps its seeded default
_POSITION_RATIOS = None             # lazily loaded; {Role: {...}} from the derived CSV

# Which Staffing Demand rows make up each role, in order. A role's derived headcount is a whole-
# building total, so it is split across its rows rather than applied to each — otherwise a 7-technician
# building would be rounded up to 3 per shift and budgeted as 9.
_PORTFOLIO_ROLE_ROWS = {
    'Property Manager': ['Property Manager'],
    'Assistant Property Manager': ['Assistant Property Manager'],
    'Chief Engineer': ['Chief Engineer'],
    'Building Executive': ['Building Executive'],
    'Customer Service': ['Customer Service'],
    'Reception': ['Reception'],
    'Accountant': ['Accountant'],
    'Cashier': ['Cashier'],
    'Technician': ['Technician (Morning)', 'Technician (Afternoon)', 'Technician (Night)'],
    'Shift Leader': ['Shift Leader (Morning)', 'Shift Leader (Afternoon)', 'Shift Leader (Night)'],
    'Amenities Attendant': ['Amenities Attendant (Morning)', 'Amenities Attendant (Afternoon)'],
}


def _position_ratios():
    global _POSITION_RATIOS
    if _POSITION_RATIOS is None:
        path = os.path.join(BUDGET_AGENT, 'data', 'master_list_verified',
                            'Fact_StaffingRatio_ByPosition.csv')
        loaded = {}
        try:
            with open(path, encoding='utf-8-sig') as fh:
                for row in csv.DictReader(line for line in fh if not line.startswith('#')):
                    loaded[row['Role']] = {
                        'n': int(row['N_Properties']),
                        'median': float(row['MedianPer1000m2NFA']),
                        'p25': float(row['P25Per1000m2NFA']),
                        'p75': float(row['P75Per1000m2NFA']),
                    }
        except (OSError, KeyError, ValueError):
            # Missing or unreadable derived file is not fatal: every affected row falls back to the
            # seeded default, which is what this pipeline did before the ratios existed.
            loaded = {}
        _POSITION_RATIOS = loaded
    return _POSITION_RATIOS


def _portfolio_headcount(role, row_name, project):
    """This row's share of `role`'s portfolio-derived headcount, and the basis to report.

    Returns (None, reason) when the role has no usable ratio, which tells the caller to keep whatever
    the form holds rather than estimate.
    """
    stats = _position_ratios().get(role)
    if not stats:
        return None, f'No derived ratio for {role}'
    if stats['n'] < _POSITION_RATIO_MIN_N:
        return None, (f'{role} is measured on only {stats["n"]} comparable propert'
                      f'{"y" if stats["n"] == 1 else "ies"} — too few to estimate from')
    nfa = project.get('total_nfa') or 0
    if nfa <= 0:
        return None, 'No NFA on this project'

    rows = _PORTFOLIO_ROLE_ROWS[role]
    total = max(1, round(stats['median'] * nfa / 1000.0))
    share, extra = divmod(total, len(rows))
    index = rows.index(row_name)
    value = share + (1 if index < extra else 0)
    spread = f'{stats["p25"]:.3f}-{stats["p75"]:.3f}'
    across = (f', split across {len(rows)} shift rows' if len(rows) > 1 else '')
    return value, (
        f'{role}: portfolio median {stats["median"]:.4f} per 1,000 m2 NFA x this project\'s NFA '
        f'({nfa:,.0f} m2) = {total} for the building{across}. Measured on {stats["n"]} comparable '
        f'residential propert{"y" if stats["n"] == 1 else "ies"} (P25-P75 {spread}), from '
        f'Fact_StaffingRatio_ByPosition.csv. This is what peer buildings actually employ, not a '
        f'Savills standard or a statutory minimum - overrule it by typing your own figure')


def _portfolio_ratio_fn(role, row_name):
    """A RATIO_DRIVEN_STAFFING entry for one row of `role`."""
    def estimate(project, _ratios):
        value, basis = _portfolio_headcount(role, row_name, project)
        if value is None:
            raise _NoPortfolioRatio(basis)
        return value, basis
    return estimate


class _NoPortfolioRatio(Exception):
    """Raised when a portfolio role cannot be estimated, so the form's own value stands."""


def _cleaning_total(project, ratios):
    """Cleaning people on duty per day, supervisors included: ROUNDUP(total fee-paying NFA ÷ ratio).

    Change fix-cleaning-staffing-ratio (2026-10-19): the same measure the Service Levels sheet classifies
    (service_levels.measure_cleaning), so the default ratio lands the project on the level it was chosen for."""
    return math.ceil(float(project.get('total_nfa') or 0) / ratios['nfa_per_cleaning_staff'])


def _cleaning_supervisors(project, ratios):
    return math.ceil(float(project.get('towers') or 0) / ratios['towers_per_supervisor'])


def _cleaners_on_duty(project, ratios):
    """'Cleaning - Common Area': the cleaning total minus the supervisor rule, at least 1 (design D3). The
    open-space area plays no part: no real source gives it, and it left ESS4 at 0 on real projects."""
    total = _cleaning_total(project, ratios)
    sup = _cleaning_supervisors(project, ratios)
    value = max(1, total - sup)
    return value, (
        f"Fee-paying NFA ({float(project.get('total_nfa') or 0):,.0f} m²) ÷ m² Fee-paying NFA per Cleaning Staff "
        f"({ratios['nfa_per_cleaning_staff']:g}{_ratio_note('nfa_per_cleaning_staff')}) = {total} on duty, "
        f"supervisors included, minus {sup} supervisor(s) (Tower Count ÷ Towers per Supervisor), at least 1")


RATIO_DRIVEN_STAFFING = {
    'Security - Main Gate (Morning)': lambda p, r: (
        p['gate_count'] * r['staff_per_gate'], f"Gate Count ({p['gate_count']:g}) × Staff per Gate ({r['staff_per_gate']:g}{_ratio_note('staff_per_gate')})"),
    'Security - Main Gate (Afternoon)': lambda p, r: (
        p['gate_count'] * r['staff_per_gate'], f"Gate Count ({p['gate_count']:g}) × Staff per Gate ({r['staff_per_gate']:g}{_ratio_note('staff_per_gate')})"),
    'Security - Main Gate (Night)': lambda p, r: (
        p['gate_count'] * r['staff_per_gate'], f"Gate Count ({p['gate_count']:g}) × Staff per Gate ({r['staff_per_gate']:g}{_ratio_note('staff_per_gate')})"),
    'Security - Patrol / Open Space': lambda p, r: (
        p['open_space'] / r['sqm_per_patrol'], f"Open Space ({p['open_space']:,.0f} m²) ÷ m² per Patrol Staff ({r['sqm_per_patrol']:g}{_ratio_note('sqm_per_patrol')})"),
    'Cleaning - Common Area': lambda p, r: _cleaners_on_duty(p, r),
    'Cleaning - Supervisor': lambda p, r: (
        p['towers'] / r['towers_per_supervisor'], f"Tower Count ({p['towers']:g}) ÷ Towers per Supervisor ({r['towers_per_supervisor']:g}{_ratio_note('towers_per_supervisor')})"),
    'Gardener / Landscape': lambda p, r: (
        p['garden_area'] / r['sqm_per_gardener'], f"Garden Area ({p['garden_area']:,.0f} m²) ÷ m² per Gardener ({r['sqm_per_gardener']:g}{_ratio_note('sqm_per_gardener')})"),
    # One entry per shift row — the ratio is a per-instant requirement, so it applies to each shift.
    'Pool Attendant (Morning)': _pool_lifeguards_per_shift,
    'Pool Attendant (Afternoon)': _pool_lifeguards_per_shift,
}

# In-house roles, estimated from the portfolio population (see _portfolio_headcount). Registered here
# rather than written out one by one so a role added to _PORTFOLIO_ROLE_ROWS is wired up by that edit
# alone, and so the row names on the form stay the single place they are spelled.
for _role, _rows in _PORTFOLIO_ROLE_ROWS.items():
    for _row_name in _rows:
        RATIO_DRIVEN_STAFFING[_row_name] = _portfolio_ratio_fn(_role, _row_name)


def _resolve_operating_years(raw):
    """How many operating years the budget covers: 1, or a refusal naming the value.

    A value above 1 is rejected rather than ignored. The per-year budget sheets, the year-on-year
    escalation and the multi-year summary it implies are specified (change
    add-multiyear-preopening-budget-phases) but not built, so accepting 2 and returning a one-year
    workbook would make the field lie about what it produced — the failure mode this form's
    read-by-label design exists to prevent.
    """
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return 1
    try:
        years = int(raw)
        if years != float(raw):
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError(
            f"Project Info 'Operating Years to Budget' is {raw!r}, which is not a whole number of "
            f"years. Enter 1, or clear the cell to take the default of 1."
        )
    if years < 1:
        raise ValueError(
            f"Project Info 'Operating Years to Budget' is {years}. A budget covers at least one "
            f"operating year. Enter 1, or clear the cell to take the default of 1."
        )
    if years > 1:
        raise ValueError(
            f"Project Info 'Operating Years to Budget' is {years}, but only 1 is supported today. "
            f"Budgeting more than one operating year needs per-year budget sheets, year-on-year "
            f"cost escalation and a multi-year summary — specified in the change "
            f"'add-multiyear-preopening-budget-phases' but not yet implemented. Set this cell to 1."
        )
    return years


# Change derive-capex-reserve-rate, D3 — evidenced default: 3 of the 4 real reference projects
# (Parking Building, Lumi Prestige & Elite, Lumi Signature) drop to the reserve at Year 2; only
# Green Skyline repeats a full Year-2 purchase and drops at Year 3. See Fact_CapexReserve.csv.
CAPEX_DROP_YEAR_DEFAULT = 2


def _resolve_capex_drop_year(raw):
    """(drop_year, is_default) for the Owner Operating Position / Savills Fee Position sheets'
    4-year Capex sinking-fund table: Years before `drop_year` carry a full lump-sum purchase (like
    Year 1 always does); `drop_year` and every year after it carry the derived reserve rate instead.

    Year 1 SHALL always carry the full lump sum (design.md D5's own invariant — a tracked baseline
    figure moving here would mean this change reached further than intended), so `drop_year` below
    2 is rejected, not silently floored. Only 4 years are modelled (YEAR_FILL_PATH), so anything
    above 4 is rejected too, rather than accepted and silently never taking effect.
    """
    stated = not (raw is None or (isinstance(raw, str) and not raw.strip()))
    if not stated:
        return CAPEX_DROP_YEAR_DEFAULT, True
    try:
        year = int(raw)
        if year != float(raw):
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError(
            f"Project Info 'Capex Drop-to-Reserve Year' is {raw!r}, which is not a whole year "
            f"number. Enter 2, 3 or 4, or clear the cell to take the default of "
            f"{CAPEX_DROP_YEAR_DEFAULT}."
        )
    if year < 2 or year > 4:
        raise ValueError(
            f"Project Info 'Capex Drop-to-Reserve Year' is {year}. Year 1 always carries the full "
            f"lump-sum purchase (it cannot itself be the drop year), and only Years 1-4 are modelled "
            f"on the Owner Operating Position / Savills Fee Position sheets. Enter 2, 3 or 4, or "
            f"clear the cell to take the default of {CAPEX_DROP_YEAR_DEFAULT}."
        )
    return year, False


def _resolve_coords(raw_lat, raw_lon):
    """(lat, lon) as floats, or (None, None). A lone value on just one of the two fields is treated
    as no coordinates at all — nearest_comparables() only uses them as a pair (a real distance needs
    both), so a half-filled pair silently degrading to "no coordinates" (today's behavior) is safer
    than guessing the other half or raising on an honest partial entry."""
    try:
        lat = float(raw_lat) if raw_lat not in (None, '') else None
    except (TypeError, ValueError):
        lat = None
    try:
        lon = float(raw_lon) if raw_lon not in (None, '') else None
    except (TypeError, ValueError):
        lon = None
    if lat is None or lon is None:
        return None, None
    return lat, lon


# Roster Setup's five staffing ratios, and what to use when the cell is left blank or zeroed.
#
# These are NOT derived from data, unlike the per-position ratios above, and cannot currently be:
# the numerator (how many security / cleaning / landscape staff a comparable property employs) is
# not split out in any clean dataset — Project_Detail_Lists.xlsx's Security/Cleaning/Landscape
# sheets carry position names with no headcount and are self-labelled an approximate row-scan, and
# Fact_ServiceCost's real post counts cover ~6 distinct projects against a corrupted Dim_Project.
# For two of the five the denominator is missing too: no comparable property records its open-space
# or garden area. So these stay editable operational assumptions, as the form's own note says.
#
# What this fallback fixes is narrower and real: a zeroed ratio used to CRASH the run
# (ZeroDivisionError), and a zeroed "Staff per Gate" silently produced a building with no security
# at all. Blank or zero now means "use the standard assumption", and the row says that it did.
_RATIO_DEFAULTS = {
    'staff_per_gate': (1, 'Security: Staff per Gate'),
    'sqm_per_patrol': (5000, 'Security: m² Open Space per Patrol Staff'),
    # Change fix-cleaning-staffing-ratio (2026-10-19): the one ratio here that IS derived from data. 3,300 m² of
    # fee-paying NFA per cleaning person on duty (supervisors included) = the median of the 30 form-read, classified
    # real projects in data/service_levels/Ref_ServiceLevelProjects.csv (3,324), rounded; inside the Tiêu chuẩn band.
    # It replaces 'Cleaning: m² Open Space per Cleaner', which is no longer read (design D4).
    'nfa_per_cleaning_staff': (3300, 'Cleaning: m² Fee-paying NFA per Cleaning Staff'),
    'towers_per_supervisor': (2, 'Cleaning: Towers per Supervisor'),
    'sqm_per_gardener': (2000, 'Landscape: m² Garden per Gardener'),
}
_RATIO_DEFAULTED = set()      # which ratios fell back on this run, for the basis text
_RATIO_NOT_ON_FORM = set()    # which of those had no field at all (a form older than the ratio)


def _ratio_or_default(raw, key, on_form=True):
    default, label = _RATIO_DEFAULTS[key]
    if on_form:
        _RATIO_NOT_ON_FORM.discard(key)
    else:
        _RATIO_NOT_ON_FORM.add(key)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = 0.0
    if value > 0:
        _RATIO_DEFAULTED.discard(key)
        return value
    _RATIO_DEFAULTED.add(key)
    return default


def _ratio_note(key):
    """' (standard assumption — cell left blank)' when this ratio fell back, else ''."""
    if key not in _RATIO_DEFAULTED:
        return ''
    if key in _RATIO_NOT_ON_FORM:
        return ' — standard default, the form has no such field on Roster Setup (an older form)'
    return ' — standard assumption, the Roster Setup cell was blank or zero'


def _staff_on_duty(pos, cached, formula_cell, ratio_fn, project, ratios, row):
    """Headcount for one Staffing Demand row, and the basis to report for it.

    Three cases, in the order they are tested:

    1. The cell still holds the seeded `=ROUNDUP(...)` suggestion — the PM has not overridden it.
       Recompute it in Python rather than trusting the cached result. openpyxl reads the value Excel
       last cached, which goes stale the moment someone edits Project Info or Roster Setup without
       reopening the file in Excel, and stale-but-plausible is the worst kind of wrong.
    2. The cell holds a number the PM typed over that formula — a deliberate override. Use it. The
       whole point of a suggestion is that it can be overruled, and silently discarding the PM's
       number (which is what this did before) makes the field a lie.
    3. The cell is blank or zero on a row this script knows a ratio for — fall back to the ratio.
       To budget a position at genuinely zero headcount, delete the row; that is already the form's
       convention for a position that does not apply (see the Pool Attendant note).

    A row with no ratio behind it keeps its previous behaviour exactly: a typed value is used as
    typed (zero included), and a blank is an error, because there is nothing to fall back to.
    """
    raw_formula = formula_cell.value if formula_cell is not None else None
    is_formula = isinstance(raw_formula, str) and raw_formula.lstrip().startswith('=')
    has_value = cached is not None and not (isinstance(cached, str) and not cached.strip())
    try:
        numeric = float(cached) if has_value else None
    except (TypeError, ValueError):
        raise ValueError(
            f"Staffing Demand row {row} ('{pos}'): Staff On Duty / Day is {cached!r}, which is not a "
            f"number. Enter a whole number of staff, or delete the row if the position does not apply."
        )

    if ratio_fn:
        if numeric and not is_formula:   # a real typed override — 0 falls through to the ratio
            return int(round(numeric)), (
                f'PM override — {numeric:g} typed over this row\'s ratio suggestion on the Staffing '
                f'Demand sheet, and used as typed')
        try:
            value, basis = ratio_fn(project, ratios)
        except _NoPortfolioRatio as exc:
            # The role has no ratio good enough to estimate from (too few comparable properties, or
            # no NFA). Keep whatever the form holds — its seeded default — and say why on the row.
            kept = int(round(numeric)) if numeric else 0
            return kept, (f'Staffing Demand value kept as-is: {exc}, so no portfolio estimate was '
                          f'applied to this row')
        suffix = '' if is_formula else (' (Staffing Demand cell was blank or zero, so the ratio '
                                        'was used)')
        return math.ceil(value), f'{basis} = {value:.2f}, rounded up{suffix}'

    # No ratio for this position — unchanged from before.
    if not has_value:
        raise ValueError(
            f"Staffing Demand row {row} ('{pos}'): Staff On Duty / Day is blank and this position isn't one of "
            "the ratio-driven rows this script knows how to compute — enter a value directly."
        )
    return int(round(numeric)), 'PM-entered value (Staffing Demand sheet, not ratio-driven)'


def _resolve_pool_count(raw, has_pool):
    """How many distinct pools to cost per-pool items for.

    Only the per-POOL items scale with this — ESM5's microbiological sampling, which is taken from
    each body of water separately. ESM4's chemicals must NOT: they are priced from `Pool Volume`,
    which the intake form defines as the total across every pool, and whose source worked example is
    itself already two pools (a 320 m3 adult pool plus a 120 m3 children's pool = 440 m3). Scaling
    that by the count would charge the same water twice.

    A pool with no stated count is one pool, not zero — which is also exactly the figure this
    pipeline produced before the count was wired in.
    """
    stated = not (raw is None or (isinstance(raw, str) and not raw.strip()))
    count = 0
    if stated:
        try:
            count = int(raw)
            if count != float(raw):
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError(
                f"Project Info 'Number of Pools' is {raw!r}, which is not a whole number of pools. "
                f"Enter a whole number, or clear the cell."
            )
        if count < 0:
            raise ValueError(
                f"Project Info 'Number of Pools' is {count}. A count cannot be negative. Enter a "
                f"whole number, or clear the cell."
            )
    if not has_pool:
        if count > 0:
            raise ValueError(
                f"Project Info says 'Has Swimming Pool?' is No but 'Number of Pools' is {count}. "
                f"These contradict each other, and guessing which one is right would silently drop "
                f"or invent this project's pool costs. Set the pool count to 0, or set 'Has "
                f"Swimming Pool?' to Yes."
            )
        return 0, False
    # Has a pool: a blank or zero count means one pool, assumed — it is the smallest number
    # consistent with 'Has Swimming Pool? = Yes', and keeps the figure identical to what this
    # pipeline produced before the count existed.
    return (count, True) if count >= 1 else (1, False)


def read_input(path):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found. Run build_project_input_form.py first, fill it in, then re-run this script."
        )
    wb = openpyxl.load_workbook(path, data_only=True)
    # A second view of the same file, formulas unevaluated. The cached-value view above cannot tell
    # "=ROUNDUP(...)" (the seeded ratio suggestion) apart from a number a PM typed over it — both
    # read back as a bare number. Staffing Demand needs that distinction to honour a real override
    # without trusting a stale cached formula result. See _staff_on_duty().
    wb_formulas = openpyxl.load_workbook(path, data_only=False)

    pi = wb['Project Info']
    segment = str(SheetLabels(pi).value('Property Segment') or 'Residential').strip()
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
    # Every field is found by its LABEL, not its address. Row positions in this sheet have moved
    # before (the Product Mix block grew from 5 products to 9 and pushed everything below it down
    # four rows) and reading by address silently returned the wrong cells. See input_labels.py.
    L = SheetLabels(pi)
    project = dict(
        name=L.value('Project Name'), segment=segment,
        site_area=L.value('Site Area'), garden_area=L.value('Garden / Landscape Area'),
        open_space=L.value('Circulation / Hardscape Area'),
        floor_count=L.value('Floor Count'), towers=L.value('Tower Count'),
        car_slots=L.value('Car Parking Slots'), moto_slots=L.value('Moto Parking Slots'),
        has_pool=str(L.value('Has Swimming Pool?')).strip().lower() == 'yes',
        pool_area=L.value('Pool Area'),
        # Optional: absent on workbooks created before ESM4 was costed from volume.
        pool_volume_m3=(L.value('Pool Volume') if L.has('Pool Volume') else None),
        gate_count=L.value('Gate / Entrance Count'),
        # Real, negotiated contract terms — see build_project_input_form.py's comment on these
        # cells. Both None (the real, honest default) until the PM enters the actual contract.
        # A blank cell here is an EMPTY FIELD, not a missing one — the resolver returns None.
        savills_fee_fixed_monthly=L.value(savills_fee.FIXED_LABEL),
        savills_fee_pct=L.value(savills_fee.PCT_LABEL),
        # Optional: absent on workbooks created before this field was added (change
        # apply-guideline-remark-model, docs/13-remark-case-model.md Group B). Remark-only — see
        # build_project_input_form.py's comment on this field; RM.0A's own figure never reads it.
        handover_prepaid_months=(L.value('Months of Management Fee Prepaid on Handover')
                                 if L.has('Months of Management Fee Prepaid on Handover') else None),
        # Optional: absent on workbooks created before this field was added (change
        # complete-ai-guideline-remark-coverage). Remark-only, per the AI Guideline's '0. Info'
        # note — no figure reads either field. Blank on both when the PM hasn't supplied a basis.
        area_basis=(L.value('Area basis / drawing reference')
                   if L.has('Area basis / drawing reference') else None),
        area_basis_year=(L.value('Area basis confirmed as of year')
                         if L.has('Area basis confirmed as of year') else None),
        # Optional: absent on workbooks created before this field was added (change
        # complete-ai-guideline-remark-coverage). Separate from `pool_volume_m3`, which already
        # totals every pool and is what drives ESM4's chemical-cost estimate — this count is not
        # wired into any figure yet, informational only.
        pool_count=(L.value('Number of Pools') if L.has('Number of Pools') else None),
        # Optional: absent on workbooks created before this field was added. Absent or blank means
        # one operating year — today's behaviour. Validated just below.
        operating_years=(L.value('Operating Years to Budget')
                         if L.has('Operating Years to Budget') else None),
        # Optional: absent on workbooks created before this field was added (change
        # rank-comparables-by-location, 2026-09-15). Feeds nearest_comparables()'s location tiering
        # only — no figure changes when absent, comparable matching stays size-only exactly as today.
        district=(L.value('District') if L.has('District') else None),
        city=(L.value('City / Province') if L.has('City / Province') else None),
        # Optional: absent on workbooks made before change apply-head-of-pm-decisions-2026-10 (group 2). Blank or
        # absent means the business group. A new prospect's water is priced by it from the dated tariff file.
        water_group=(L.value(utility_tariffs.WATER_GROUP_LABEL) if L.has(utility_tariffs.WATER_GROUP_LABEL)
                     else None),
        # Optional: absent on workbooks made before change apply-head-of-pm-decisions-2026-10 (group 3).
        esi2_premium_usd=(L.value(ESI2_PREMIUM_LABEL) if L.has(ESI2_PREMIUM_LABEL) else None),
        usd_rate=(L.value(USD_RATE_LABEL) if L.has(USD_RATE_LABEL) else None),
        # Optional: absent on workbooks created before this field was added (change
        # rank-comparables-by-location, task 2.4, 2026-09-16). Refines ORDER within whatever tier
        # District/City above already placed a candidate in — never changes tiers. A lone value on
        # just one of Latitude/Longitude is treated as no coordinates (see _resolve_coords below).
        lat=(L.value('Latitude') if L.has('Latitude') else None),
        lon=(L.value('Longitude') if L.has('Longitude') else None),
        # Optional: absent on workbooks created before this field was added (2026-09-16). Display/
        # citation only — see build_project_input_form.py's comment on this field. Does not feed
        # District/City/Latitude/Longitude above or comparable matching in any way.
        address=(L.value('Street Address') if L.has('Street Address') else None),
        # Optional: absent on workbooks created before this field was added (change
        # wire-real-elevator-count-into-ad-revenue, 2026-09-16). PASSENGER elevators only — see
        # build_project_input_form.py's comment. Feeds generate_project_output.py's
        # _real_ad_frame_qty() only; no other figure reads it.
        passenger_elevators_per_tower=(L.value('Passenger Elevators per Tower')
                                       if L.has('Passenger Elevators per Tower') else None),
        # Optional: absent on workbooks created before this field was added (2026-09-16). Feeds
        # generate_project_output.py's _real_basement_lcd_qty() only; no other figure reads it.
        basement_count=(L.value('Number of Basements') if L.has('Number of Basements') else None),
        # Optional: absent on workbooks created before this field was added (change
        # derive-capex-reserve-rate, task 4, 2026-09-21). Feeds generate_project_output.py's
        # Owner Operating Position / Savills Fee Position sinking-fund tables only — no figure on
        # any other sheet reads it. Validated, with its evidenced default applied, just below.
        capex_drop_year=(L.value('Capex Drop-to-Reserve Year')
                         if L.has('Capex Drop-to-Reserve Year') else None),
    )
    project['lat'], project['lon'] = _resolve_coords(project['lat'], project['lon'])
    project['operating_years'] = _resolve_operating_years(project['operating_years'])
    project['capex_drop_year'], project['capex_drop_year_is_default'] = _resolve_capex_drop_year(
        project['capex_drop_year'])
    # Optional: absent on workbooks made before change apply-head-of-pm-decisions-2026-10 (group 1). Blank or absent
    # means January 2027. Anything that is not a month stops the run (budget_period.BudgetPeriodError).
    project['budget_period'] = budget_period.from_value(
        L.value(budget_period.LABEL) if L.has(budget_period.LABEL) else None)
    project['esi2'] = _resolve_esi2(project['esi2_premium_usd'], project['usd_rate'])
    # Optional: absent on workbooks made before change apply-head-of-pm-decisions-2026-10 (group 6). Blank or absent
    # means 2%; text, a negative rate or one above 10% stop the run (contingency.ContingencyRateError).
    project['contingency_rate'], project['contingency_rate_is_default'] = contingency.resolve_rate(
        L.value(contingency.LABEL) if L.has(contingency.LABEL) else None)
    project['pool_count'], project['pool_count_stated'] = _resolve_pool_count(
        project['pool_count'], project['has_pool'])
    if project['savills_fee_fixed_monthly'] and project['savills_fee_pct']:
        raise ValueError(savills_fee.both_filled_message())
    # Existing-project mode (change carry-forward-staffing): the prior-year baseline and the PM's
    # changes, or None for a New-prospect workbook — every workbook made before that change.
    project['existing'] = existing_staffing.read_existing(wb, L)
    # Existing-project common-area electricity and water (change carry-forward-common-utilities): the
    # 'Prior-Year Utilities' inputs, or None for a New-prospect workbook.
    project['utilities'] = existing_utilities.read_utilities(wb, L)
    # Each product read from the row bearing ITS OWN name, inside the Product Mix block. Reading
    # positionally from a fixed start row is what once made the PARKING rows below the block get
    # read as product areas when the block grew.
    products = {}
    for name in PRODUCT_ROWS:
        if not L.has(name):
            # A product row the form does not carry. Unlike a missing SCALAR field — which is an
            # error, because every scalar has always existed — an absent product simply means this
            # workbook predates that product being offered. "Not on the form" and "on the form with
            # no area" mean the same thing to the budget: nothing to price, row left blank.
            # This is what lets a workbook filled in before the Product Mix grew still be read.
            products[name] = dict(gfa=0, nfa=0, units=0)
            continue
        row = L.row_of(name)
        products[name] = dict(gfa=pi.cell(row=row, column=2).value or 0,
                              nfa=pi.cell(row=row, column=3).value or 0,
                              units=pi.cell(row=row, column=4).value or 0)
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
    # A villa-only or other low-rise project has no Apartment NFA (change support-villa-only-and-no-parking):
    # comparable matching is by total NFA, so only a form with no product area at all is refused.
    if not project['total_nfa']:
        raise ValueError("Project Info: the Product Mix has no NFA on any product row — fill in the NFA of at "
                         "least one product (comparable matching is by total NFA).")
    # Operating-project fields (change use-operating-project-actuals): all optional and validated in
    # operating_inputs.py. A form without them reads as blank, and the run is the run before that change.
    project['operating'] = operating_inputs.read_operating_inputs(pi, L, products)
    project['stable_operation'] = project['operating']['stable']

    rs = wb['Roster Setup']
    R = SheetLabels(rs)
    ratios = dict(
        staff_per_gate=_ratio_or_default(
            R.value('Security: Staff per Gate'), 'staff_per_gate'),
        sqm_per_patrol=_ratio_or_default(
            R.value('Security: m² Open Space per Patrol Staff'), 'sqm_per_patrol'),
        nfa_per_cleaning_staff=_ratio_or_default(
            R.value(_RATIO_DEFAULTS['nfa_per_cleaning_staff'][1]) if R.has(_RATIO_DEFAULTS['nfa_per_cleaning_staff'][1])
            else None, 'nfa_per_cleaning_staff', on_form=R.has(_RATIO_DEFAULTS['nfa_per_cleaning_staff'][1])),
        towers_per_supervisor=_ratio_or_default(
            R.value('Cleaning: Towers per Supervisor'), 'towers_per_supervisor'),
        sqm_per_gardener=_ratio_or_default(
            R.value('Landscape: m² Garden per Gardener'), 'sqm_per_gardener'),
    )
    month, year = R.value('Month'), R.value('Year')
    if not month and not year:
        # Both blank: the sample month is the budget's first month (change apply-head-of-pm-decisions-2026-10,
        # group 1). One blank and one filled is still a form mistake.
        year, month = project['budget_period'].start_year, project['budget_period'].start_month
    if not month or not year:
        raise ValueError("Roster Setup's Month and Year must both be filled in (or both left blank to use the "
                         "budget's first month).")
    month, year = int(month), int(year)

    # Holidays sit under their own section header, one date per row. Found by the header rather
    # than the old fixed range 20-30, so the list can grow or the section can move.
    holiday_days = set()
    holiday_header = 'PUBLIC HOLIDAYS THIS MONTH'
    if R.has(holiday_header):
        first = R.section_row(holiday_header)
        for r in range(first + 1, first + 20):
            d = rs.cell(row=r, column=1).value
            # Stop at the computed reference block that now sits below this one. Its column A holds
            # full dates ('2026-02-17'), which int() rejects anyway — but relying on that would mean
            # the parser only works by accident, and a future block with bare numbers in column A
            # would be silently swallowed as holidays.
            if isinstance(d, str) and 'REFERENCE ONLY' in d.upper():
                break
            if d is None or str(d).strip() == '':
                continue
            try:
                holiday_days.add(int(d))
            except (TypeError, ValueError):
                continue          # the block's own 'Date (DD)' column header, or a note row

    # Nothing typed in? Compute them. Four of Vietnam's statutory holidays are fixed solar dates,
    # but Tet and Gio To Hung Vuong are LUNAR and move every year, so a hand-typed list goes stale
    # the moment the rostered month changes and nobody remembers. vn_holidays converts them (Ho Ngoc
    # Duc's algorithm, UTC+7) and self-validates against six Tet dates that already happened.
    # A typed list still wins: it is how a PM applies the annual "hoan doi" swap-day announcement,
    # which is a policy decision this cannot compute.
    holidays_were_computed = False
    if not holiday_days:
        from vn_holidays import holidays_in_month
        holiday_days = set(holidays_in_month(year, month))
        holidays_were_computed = True

    ws_demand = wb['Staffing Demand']
    ws_demand_f = wb_formulas['Staffing Demand']
    # Reason Code / Reason Note: found by their header (row 4), absent on forms made before change
    # carry-forward-staffing. Only Existing-project mode reads them (a new position's reason).
    demand_headers = {normalise(ws_demand.cell(row=4, column=c).value): c
                      for c in range(1, (ws_demand.max_column or 1) + 1)}
    reason_code_col = demand_headers.get('reason code')
    reason_note_col = demand_headers.get('reason note')
    demand = []
    for r in range(5, ws_demand.max_row + 1):
        pos = ws_demand.cell(row=r, column=1).value
        code = ws_demand.cell(row=r, column=2).value
        staff = ws_demand.cell(row=r, column=3).value
        days = ws_demand.cell(row=r, column=4).value
        rate = ws_demand.cell(row=r, column=5).value
        if not pos or not code:
            continue
        staff, basis = _staff_on_duty(
            pos, staff, ws_demand_f.cell(row=r, column=3),
            RATIO_DRIVEN_STAFFING.get(str(pos)), project, ratios, r)
        demand.append(dict(
            Position=str(pos), ShiftCode=str(code),
            StaffPerDay=staff, CoverageDays=int(days), AvgDailyRate=float(rate),
            SourceRow=r, Basis=basis,
            ReasonCode=ws_demand.cell(row=r, column=reason_code_col).value if reason_code_col else None,
            ReasonNote=ws_demand.cell(row=r, column=reason_note_col).value if reason_note_col else None,
        ))
    if not demand:
        raise ValueError("Staffing Demand sheet has no complete rows.")
    # The roster month and its holidays, for the deliverable's reception calendar 'B1' (design D15).
    project['roster_month'] = (year, month)
    project['roster_holidays'] = sorted(holiday_days)

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


_CODE_COL = 25     # Y — every row of "2. Budget-Management Fund" carries its own Savills cost code
                   # here (ESS1, ESM4, EMA15, ...). Used to verify a hardcoded row position still
                   # points at the cost line it is supposed to, rather than trusting the number.
_REMARKS_COL = 20  # T — real header in every real-data sheet: "Remarks (please give the full,
                   # detailed reason for each cost item's increase/decrease)". Every cell this
                   # generator fills gets a real remark explaining the actual formula/source/numbers
                   # used, not just a value with no explanation of where it came from.


# The AI Guideline's universal rule: a remark for an inclusive-of-VAT figure must carry a
# VAT-treatment sentence naming the VAT status and the budget year. The switch is
# `2. Budget-Management Fund`!F7 ("Mô hình tài chính:" — KHOÁN = excl-VAT throughout, so no
# sentence; KHÔNG KHOÁN / THU HỘ CHI HỘ = incl-VAT throughout). build_budget() sets this once from
# _vat_sentence(); _write_remark(), _opex_remark() and _compose_summary_narratives() append it.
# Empty string = exclusive-of-VAT run (or the switch could not be read) -> nothing is appended.
_ACTIVE_VAT_SENTENCE = ''

# Zero reasons written on '2. Budget-Management Fund' in this run: code -> the Vietnamese reason,
# without the "Để ở mức 0: " lead-in and without the VAT sentence. fill_common_area_fund_sheet()
# copies each onto the matching '2.2 Common area Fund' line, which is a share of that same zero
# (change explain-common-area-fund-zero-lines). Built from what was actually written, never a fixed
# list, so a code that gets priced (EMH1 once Savills' fee terms are entered) drops out of both
# sheets together. build_budget() clears both dicts at the start of every run.
_ZERO_REASONS = {}
# Catch-all lines whose remark carries other codes' reasons (EMA15 for EMA1-EMA4, matching
# checks._REQUIRED_CODE_DISCLOSED_ON): code -> a figure-free remark for the matching '2.2' line.
# Figure-free because the '2. Fund' remark quotes that sheet's own amounts, not the '2.2' share.
_CATCH_ALL_REASONS = {}
# The unit price each priced revenue line actually uses, recorded when the line is written: RM.* in
# VND per m² per month, RP1/RP2 in VND per slot per month. The '1. Summary' narratives quote these,
# not year-1 revenue divided by area or slots, which is a ramp-diluted average (change
# fix-deliverable-remark-wording). Cleared by build_budget() at the start of every run.
_UNIT_RATES = {}
# RM.* code -> VAT basis of a rate the PM entered (change use-operating-project-actuals, P1), so the
# '1. Summary' fee narrative states the basis the PM gave instead of "(đã gồm VAT)". Cleared with
# _UNIT_RATES at the start of every run.
_ENTERED_RATE_VAT = {}
# The figures the helper sheets A2-A4, B3 garbage, B4 and B5 show, recorded where the fund lines are priced (ESS1/
# ESS4/ESS16 posts, ESS9 units, RA1.A/RA2 devices, RP1/RP2 prices) so fill_helper_sheets() writes the same numbers
# instead of working them out again (change apply-head-of-pm-decisions-2026-10, D15). Cleared by build_budget().
_HELPER_FIGURES = {}
_VAT_SWITCH_DEFAULT = ('2. Budget-Management Fund', 'F7')
# ERCS1 stays 0 until residential service quotes arrive (Head of PM decision B7, design D9c); '2.2' copies it.
ERCS1_REASON_VI = ("Đang chờ báo giá dịch vụ cho chung cư; đến khi có báo giá, hệ thống chưa có đơn giá nào có nguồn "
                   "trích dẫn để tính theo Tần suất x đơn giá.")


def _catalogue_vat_rule():
    """The VAT-treatment sentence rule, read from the catalogue's `#` header block (one authority,
    shared with verify.py's check_remark_content). Returns (switch_sheet, switch_cell, sentence_vi)
    with `<year>` still a placeholder. Falls back to the guideline's own wording if an older
    catalogue has no header block.

    Vietnamese only (2026-09-11, user direction — see docs/12-sample-remark-rescan.md): the
    guideline's own text is Vietnamese throughout, and the worked sample never renders it in
    English either. The catalogue still records `vat_sentence_en` for reference; it is not read."""
    sheet, cell = _VAT_SWITCH_DEFAULT
    vi = 'Chi phí hạng mục này đã bao gồm VAT và dự ước tại năm <year>.'
    try:
        with open(CATALOGUE_PATH, encoding='utf-8-sig') as f:
            for line in f:
                if not line.startswith('#'):
                    break
                s = line.lstrip('#').strip()
                if s.startswith('vat_switch_sheet') and '=' in s:
                    sheet = s.split('=', 1)[1].strip()
                elif s.startswith('vat_switch_cell') and '=' in s:
                    cell = s.split('=', 1)[1].strip()
                elif s.startswith('vat_sentence_vi') and '=' in s:
                    vi = s.split('=', 1)[1].strip()
    except OSError:
        pass
    return sheet, cell, vi


def _budget_year(wb, fallback=None):
    """The budget year — `2. Budget-Management Fund`!AL5, the template's own "Budget Year" field.
    The guideline's VAT sentence and the composed narratives are "for year <budget year>", which is
    NOT the roster's calendar year (`build_budget`'s `year` arg — 2026 on the current fixture while
    the budget year is 2027). Falls back to that calendar year if AL5 cannot be read."""
    try:
        v = wb['2. Budget-Management Fund']['AL5'].value
        if v not in (None, ''):
            return str(v).strip().split('.')[0]
    except (KeyError, TypeError, AttributeError):
        pass
    return str(fallback) if fallback is not None else ''


def _vat_sentence(wb, year):
    """The Vietnamese VAT-treatment sentence for this run, or '' when figures exclude VAT.

    Reads the "Mô hình tài chính" switch (default `2. Budget-Management Fund`!F7). `KHOÁN` = the
    figures exclude VAT -> ''. `KHÔNG KHOÁN` / `THU HỘ CHI HỘ` -> the sentence. An unrecognised or
    blank switch is treated as inclusive (the form ships `THU HỘ CHI HỘ`; its `Y4` and
    `1. Summary`!F7 both say "Including VAT")."""
    sheet, cell, vi = _catalogue_vat_rule()
    raw = ''
    try:
        raw = wb[sheet][cell].value or ''
    except (KeyError, TypeError):
        raw = ''
    norm = ' '.join(str(raw).split()).upper()
    if norm == 'KHOÁN':                       # explicit exclusive-of-VAT model
        return ''
    y = _budget_year(wb, year)
    return vi.replace('<year>', y)


def _append_vat(remark):
    """Append the active VAT-treatment sentence unless it (or nothing) is already there. A
    multi-line remark (a bulleted rollup, a numbered recipe) gets it on its own line; a single-line
    remark gets it appended after a space, matching the worked sample's usage."""
    if not _ACTIVE_VAT_SENTENCE or not remark:
        return remark
    if _ACTIVE_VAT_SENTENCE in remark or operating_inputs.ENTERED_RATE_YEAR_PREFIX in remark:
        return remark                     # already there, or an entered-rate line with its own (W3)
    if remark.endswith('\n'):
        sep = ''
    elif '\n' in remark:
        sep = '\n'
    elif remark.endswith(' '):
        sep = ''
    else:
        sep = ' '
    return f"{remark}{sep}{_ACTIVE_VAT_SENTENCE}"


def _write_remark(ws, row, remark):
    if not remark:
        return
    remark = _append_vat(remark)
    cell = ws.cell(row=row, column=_REMARKS_COL, value=remark)
    cell.alignment = Alignment(wrap_text=True, vertical='top')
    # Clearing the inherited accounting format and sizing the row/column is done in one sweep by
    # _normalise_all_remark_columns() after every sheet is filled — see build_budget().


def _write_zero_reason(ws, row, code, reason):
    """Write a "left at zero" remark on '2. Budget-Management Fund' and record the reason so the
    matching '2.2 Common area Fund' line can state it too (see _ZERO_REASONS)."""
    _write_remark(ws, row, remark=f"Để ở mức 0: {reason}")
    _ZERO_REASONS[code] = reason


def _normalise_all_remark_columns(wb):
    """Make every "Remarks / Ghi chú" column across the deliverable display its text as wrapped
    text, not `########`.

    Every such column in the standard form ships with an ACCOUNTING number format
    (`_(* #,##0_);_(* \\(#,##0\\);_(* "-"??_);_(@_)`). Excel renders a long *text* value through it
    as a formatted value — shown as `########` when it will not fit — instead of as plain
    overflowing text. This bites twice: the cells the pipeline writes directly
    (`2. Budget-Management Fund`/`2.2 Common area Fund` column T), and the cells on `1. Summary` and
    the "Report-" sheets that pull those remarks across with a formula (e.g.
    `='2. Budget-Management Fund'!T148`).

    For every column whose header says "Remark" or "Ghi chú", this gives each text/formula cell
    below that header a text-friendly number format (`#,##0;-#,##0;;@` — plain text via the `@`
    section, and a blank instead of a stray "0"/"-" where a template pull-formula lands on an empty
    row), turns on wrap, grows the row, and widens a narrow column. Percent-formatted cells are
    skipped as a precaution; whitespace-only template placeholders are left untouched.
    """
    text_fmt = '#,##0;-#,##0;;@'
    CHARS_PER_LINE = 46            # ~ column width 48, minus a margin
    for ws in wb.worksheets:
        header_row = {}            # remarks column -> the row its header sits on
        for row in ws.iter_rows(min_row=1, max_row=16):
            for cell in row:
                v = cell.value
                if isinstance(v, str) and ('remark' in v.lower() or 'ghi chú' in v.lower()):
                    header_row.setdefault(cell.column, cell.row)
        for col, hrow in sorted(header_row.items()):
            letter = get_column_letter(col)
            touched = False
            for row in range(hrow + 1, ws.max_row + 1):
                cell = ws.cell(row=row, column=col)
                v = cell.value
                if not isinstance(v, str) or not v.strip():
                    continue
                if '%' in (cell.number_format or ''):
                    continue
                cell.number_format = text_fmt
                cell.alignment = Alignment(wrap_text=True, vertical='top')
                touched = True
                if v.startswith('='):
                    lines = 5                          # a pulled remark — can't measure it here
                else:
                    text_len = len(v) + v.count('\n') * CHARS_PER_LINE
                    # 30-line cap: a composed '1. Summary' K narrative (change
                    # apply-guideline-remark-model) is bilingual and runs longer than a line note.
                    lines = min(30, max(1, math.ceil(text_len / CHARS_PER_LINE)))
                needed = lines * 15 + 4
                if (ws.row_dimensions[row].height or 0) < needed:
                    ws.row_dimensions[row].height = needed
            if touched and (ws.column_dimensions[letter].width or 0) < 48:
                ws.column_dimensions[letter].width = 48


# =================================================================================================
# '1. Summary' column-K composed narratives (change apply-guideline-remark-model)
#
# The AI Guideline instructs, per '1. Summary' PART-1 row, what its client-facing Remarks cell must
# say (docs/11-guideline-remark-model.md; recipes recorded in Costing_Method_Catalogue.csv
# `summary_recipe`). The standard template ships column K blank or pulling one detail line's remark
# (`='2. Budget-Management Fund'!T148`). This composes it instead — Vietnamese, from the project's
# own data — for every PART-1 total the pipeline gave a non-zero figure. Plain text, no formula.
# Display only: no budgeted figure changes.
#
# Wording (2026-09-11, user direction): Vietnamese only, no English — and every blank in the AI
# Guideline's own note text (its "<...>" placeholders) filled with this project's real data, in the
# guideline's own phrasing, matched against the worked sample's actual usage rather than paraphrased.
# See docs/12-sample-remark-rescan.md for the guideline-vs-sample side-by-side that grounds this.
# =================================================================================================
ENABLE_SUMMARY_REMARK_COMPOSER = True

# summary_row -> (kind, catalogue code that owns the recipe, fund-code matchers that roll into it).
# A matcher '=X' means the exact code X; 'X' means any code starting X (so 'RM.' catches RM.AP..KG,
# 'EMA' catches EMA1..EMA19). Use '=' for ESS1/ESS4/ESS16 — they share the 'ESS1' prefix.
# kind: 'recipe' = fill-in-the-blanks bilingual template; 'rollup' = "Dự ước bao gồm: <child names>".
_SUMMARY_PART1 = [
    (14, 'recipe', 'RM',    ('RM.',)),
    (15, 'recipe', 'RPa',   ('RP1', 'RP2', 'RP3')),
    (18, 'rollup', 'RO',    ('RO',)),
    (19, 'recipe', 'RI',    ('RI',)),
    (22, 'recipe', 'EMH',   ('EMH',)),
    (23, 'rollup', 'EMA',   ('EMA',)),
    (24, 'rollup', 'EMB',   ('EMB',)),
    (27, 'rollup', 'ESC',   ('ESC',)),
    (29, 'recipe', 'ESS1',  ('=ESS1',)),
    (30, 'recipe', 'ESS4',  ('=ESS4',)),
    (31, 'rollup', 'ESS16', ('=ESS16',)),
    (32, 'rollup', 'ESI1',  ('ESI',)),
    (33, 'rollup', 'ESM',   ('ESM',)),
    (34, 'rollup', 'ESA6',  ('ESA', 'ESL')),
    (36, 'recipe', 'EN',    ('EN',)),
    (38, 'recipe', 'EEW',   ('EEW',)),
    (39, 'recipe', 'EEE',   ('EEE',)),
    (40, 'recipe', 'EED',   ('EED',)),
    (43, 'rollup', 'ER',    ('ER',)),
]
_SUMMARY_K_COL = 11  # K — "Remarks / Ghi chú" on '1. Summary'
# Fixed legal sentence the Accreditation narrative (row 34) must carry — recorded verbatim on the
# ESA6 catalogue row (`fixed_sentence`); mirrored here so the composer needs no catalogue read.
_ACCREDITATION_SENTENCE = ("Theo Điều 150 Luật Nhà ở 2023 và Điều 32 Quy chế quản lý, sử dụng nhà "
                           "chung cư, một số chi phí kiểm định khi vận hành có thể sử dụng Quỹ bảo trì.")

# Short Vietnamese product labels for the RM narrative — the fund sheet's own item names are the
# full "Phí quản lý thu từ <X>" line, which reads redundantly once it is itself inside a sentence
# that already says "Mức phí quản lý ...". PRODUCT_REVENUE_ROWS keys are the only products this
# pipeline prices, so this covers every one that can appear.
_PRODUCT_VI_LABEL = {
    'Apartment': 'căn hộ', 'Officetel': 'officetel', 'Office': 'văn phòng',
    'Shopping Mall': 'trung tâm thương mại', 'Retail': 'khối đế thương mại',
    'Shop Apartment': 'shop apartment', 'Shophouse': 'shophouse', 'Villas': 'biệt thự',
    'Nursery / Nhà trẻ': 'nhà trẻ',
}

# Vietnamese labels for the roster's canonical Security/Cleaning positions (build_project_input_form.py
# / build_roster_input_form.py — the full, enumerable list this pipeline ever generates demand for,
# after the shift-time suffix is collapsed off). Falls back to the raw English role name for a
# position outside this fixed set, rather than guessing a translation.
_SECURITY_CLEANING_ROLE_VI = {
    'Security - Main Gate': 'Vị trí cổng chính',
    'Security - CCTV Room': 'Trực phòng CCTV',
    'Security - Patrol / Open Space': 'Tuần tra khu vực công cộng',
    'Cleaning - Common Area': 'Vệ sinh khu vực công cộng',
    'Cleaning - Supervisor': 'Giám sát',
}


def _collect_written(wb):
    """What the pipeline actually wrote to the two fund sheets, read back from the cells it set:
    {code: {'row', 'value', 'sheet', 'name_vi', 'name_en'}}.

    The fill functions set column C (Frequency) and H:S / F only on the rows they fill; an untouched
    row has C blank and is skipped. Most cells written are literals, so openpyxl sees the value
    directly — EXCEPT EMH2 (change reconcile-summary-with-detail-sheets, design D2), which is a
    formula reference into 'A1. Staff cost 08.2026 (VN)''s own total and has no cached value until
    Excel recalculates it. Such a row is still returned — a caller needs to know the code WAS
    funded — with `value=None`, so it is treated as "written, amount unknown here" rather than
    silently dropped (which would make the code look unfunded and its '1. Summary' row look zero).
    Used by _compose_summary_narratives — the "written" set of design.md D1, gathered after the
    fills rather than threaded through every writer.
    """
    written = {}
    scan = [
        ('2. Budget-Management Fund',
         set(MGMT_FUND_ROWS.values()) | set(PRODUCT_REVENUE_ROWS.values())),
        ('2.2 Common area Fund', set(COMMON_AREA_FUND_ROWS.values())),
    ]
    def _as_number(cell_value):
        """None for a formula string (openpyxl has no cached value for it without Excel) or
        anything else that isn't already a plain number."""
        if isinstance(cell_value, (int, float)):
            return float(cell_value)
        if cell_value in (None, ''):
            return 0.0
        return None

    for sheet_name, rows in scan:
        ws = wb[sheet_name]
        for r in sorted(rows):
            freq = ws.cell(row=r, column=3).value
            if not isinstance(freq, str) or not freq.strip():
                continue
            if freq.strip().lower() == 'monthly':
                f_val = _as_number(ws.cell(row=r, column=6).value)
                value = None if f_val is None else f_val * 12   # None = formula, value unknown here
            else:                                        # Schedule / Year-1 lump
                cell_vals = [_as_number(ws.cell(row=r, column=c).value) for c in range(8, 20)]
                value = None if any(v is None for v in cell_vals) else sum(cell_vals)
            if value is not None and abs(value) < 1:
                continue                                    # genuinely zero/blank — not funded
            code = (ws.cell(row=r, column=_CODE_COL).value or '')
            code = code.strip() if isinstance(code, str) else str(code)
            raw_name = ws.cell(row=r, column=_CODE_COL + 1).value or code
            parts = [p.strip(' \t()') for p in str(raw_name).replace('\r', '').split('\n') if p.strip(' \t()')]
            written[code] = {
                'row': r, 'value': value, 'sheet': sheet_name,
                'name_en': parts[0] if parts else code,
                'name_vi': parts[-1] if len(parts) > 1 else (parts[0] if parts else code),
            }
    return written


def _vi_list(items):
    """The AI Guideline's own bullet format for an itemised list — one '- item' per line, matching
    the worked sample's actual usage (docs/12-sample-remark-rescan.md), not a comma-joined sentence."""
    return '\n'.join(f"- {it}" for it in items)


def _children_for(matchers, written):
    """`written` entries a '1. Summary' row rolls up: a matcher '=X' means exactly code X; 'X' means
    any code starting with X. Ordered by fund-sheet row."""
    def hit(code):
        for m in matchers:
            if m.startswith('='):
                if code == m[1:]:
                    return True
            elif code.startswith(m):
                return True
        return False
    return sorted(((c, w) for c, w in written.items() if hit(c)), key=lambda cw: cw[1]['row'])


def _rollup_narrative(children, fixed_sentence=''):
    """"Dự ước bao gồm:" + one "- <child name>" per line, the AI Guideline's own list format
    (docs/12-sample-remark-rescan.md) — not a comma-joined sentence. Plus an optional fixed
    sentence (e.g. the Điều 150 accreditation clause)."""
    if not children:
        return None
    vi = "Dự ước bao gồm:\n" + _vi_list(w['name_vi'] for _c, w in children)
    if fixed_sentence:
        vi += '\n' + fixed_sentence
    return vi


# English unit labels from Fact_OPEX.csv's Unit column -> their form in a Vietnamese remark. The
# source data and the English analysis workbook keep the English labels; only client-facing
# Vietnamese text is translated (change explain-common-area-fund-zero-lines, design D5).
_UNIT_VI = {
    'm3/month': 'm3/tháng', 'kWh/month': 'kWh/tháng', 'litre/month': 'lít/tháng', 'VND/litre': 'VND/lít',
}


def _vi_unit(unit):
    return _UNIT_VI.get(unit) or (unit or '').replace('/month', '/tháng').replace('litre', 'lít')


def _opex_kwargs(project):
    """estimate_opex arguments shared by every call: the pool, and (group 2) the budget period and water group
    that price water and diesel from the dated tariff file."""
    bp = project.get('budget_period') or budget_period.default()
    return dict(has_pool=project.get('has_pool', False), pool_volume_m3=project.get('pool_volume_m3'),
                period_months=bp.months, water_group=project.get('water_group'))


def _general_vat_months(project, kind=utility_tariffs.VAT_GENERAL):
    """The VAT rate (percent) in force in each of the twelve budget months, from the dated tariff file: the
    general rate, or kind=VAT_INSURANCE (10% in every month, outside the reduction)."""
    bp = project.get('budget_period') or budget_period.default()
    rows = utility_tariffs.load_rows()
    return [utility_tariffs.vat_rate(y, m, kind, rows=rows) for y, m in bp.months]


def _vat_factors(project, kind=utility_tariffs.VAT_GENERAL):
    """(1 + that month's VAT) for each budget month when the run includes VAT; 1.0 each when the financial
    model excludes it (KHOÁN). Applied only to amounts the tool prices excluding VAT (design D9a)."""
    if not _ACTIVE_VAT_SENTENCE:
        return [1.0] * 12
    return [1 + r / 100 for r in _general_vat_months(project, kind)]


# ESI2, building insurance quoted in USD (change apply-head-of-pm-decisions-2026-10, group 3, design D10).
ESI2_DEFAULT_PREMIUM_USD = 1000        # the costing logic file's example for a 1,000,000 USD liability limit
ESI2_LIABILITY_LIMIT_USD = 1_000_000
USD_RATE_DEFAULT = 26190               # Vietcombank selling rate, 05/10/2026
USD_RATE_DATE = '05/10/2026'
ESI2_PREMIUM_LABEL = 'ESI2 Annual Premium (USD)'
USD_RATE_LABEL = 'USD Exchange Rate (VND per USD)'


def _resolve_esi2(premium_raw, rate_raw):
    """The ESI2 inputs with their defaults. Blank premium = 1,000 USD (flagged as default); a 0 premium is the PM's
    choice to price nothing (the line stays 0 with a reason); blank rate = 26,190. Text, a negative number or a zero
    rate stop the run and name the field."""
    def number(raw, label, allow_zero):
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            return None
        try:
            if isinstance(raw, bool):
                raise ValueError
            value = float(raw)
        except (TypeError, ValueError):
            raise ValueError(f"Project Info '{label}' is {raw!r}, which is not a number. Enter a number, or clear "
                             f"the cell to use the default.") from None
        if value < 0 or (value == 0 and not allow_zero):
            raise ValueError(f"Project Info '{label}' is {raw!r}. It must be "
                             f"{'zero or more' if allow_zero else 'more than zero'}. Enter a valid number, or "
                             f"clear the cell to use the default.")
        return value
    premium = number(premium_raw, ESI2_PREMIUM_LABEL, True)
    rate = number(rate_raw, USD_RATE_LABEL, False)
    return dict(premium_usd=ESI2_DEFAULT_PREMIUM_USD if premium is None else premium,
                premium_is_default=premium is None,
                rate=USD_RATE_DEFAULT if rate is None else rate, rate_is_default=rate is None)


def _rate_phrase(months, rates):
    """'8% đến hết tháng 12/2026 và 10% từ tháng 01/2027' for rates that change inside the period; '10%' if flat."""
    runs = []
    for (y, m), r in zip(months, rates):
        if not runs or runs[-1][0] != r:
            runs.append([r, (y, m), (y, m)])
        else:
            runs[-1][2] = (y, m)
    if len(runs) == 1:
        return f'{runs[0][0]:g}%'
    parts = []
    for i, (r, first, last) in enumerate(runs):
        if i == 0:
            parts.append(f'{r:g}% đến hết tháng {last[1]:02d}/{last[0]}')
        else:
            parts.append(f'{r:g}% từ tháng {first[1]:02d}/{first[0]}')
    return ' và '.join(parts)


def _energy_narrative_vi(category, project, yr):
    """Vietnamese narrative for one of the three consumption-x-tariff OPEX categories (Water,
    Electricity, Diesel (Generator Fuel)) — shared by the '1. Summary' composed narrative
    (_recipe_narrative, EEW/EEE/EED) and the line-level remark on '2. Budget-Management Fund'
    (_opex_remark), so the two levels describe the same figure in the same words instead of one
    Vietnamese and one English (change localize-line-level-remarks, 2026-09-15). `yr` is the
    already-resolved budget year (see _budget_year) — both call sites pass their own, since a
    module-level function cannot read the workbook object either closure captured it from.
    """
    ur = project.get('utilities_result')
    if ur is not None and category in ('Water', 'Electricity'):
        # Existing-project mode: the project's own actual consumption, no curve, no floor.
        return existing_utilities.narrative_vi(ur, 'EEW.C' if category == 'Water' else 'EEE.C')
    opex = estimate_opex(project['total_nfa'], **_opex_kwargs(project))
    e = opex.get(category, {})
    qty = e.get('project_quantity_month', 0)
    unit = _vi_unit(e.get('usage_unit', ''))
    tariff = e.get('tariff', 0)
    tunit = _vi_unit(e.get('tariff_unit', ''))
    as_of = e.get('tariff_as_of', '')
    if category == 'Water':
        d = e.get('dated') or {}
        # The price source follows the tariff row's category, never a substring of the date text (design D3).
        group_vi = ('hành chính sự nghiệp' if d.get('group') == utility_tariffs.CAT_W_ADMIN else 'kinh doanh dịch vụ')
        price_source = (f"Đơn giá nước nhóm khách hàng {group_vi} theo bảng giá nước sạch của SAWACO (TP.HCM)"
                        + (", mặc định khi ô 'Nhóm khách hàng nước' để trống; PM chọn nhóm hành chính sự nghiệp "
                           "khi hóa đơn ghi vậy" if d.get('group_is_default') else ", theo nhóm PM đã chọn")
                        + ".")
        if utility_tariffs.region_of(project.get('city')) != utility_tariffs.HCMC:
            price_source += (" Dự án nằm ngoài TP.HCM hoặc chưa ghi tỉnh/thành: đây là giá SAWACO TP.HCM, cần đối "
                             "chiếu hóa đơn nước địa phương.")
        bp = project.get('budget_period') or budget_period.default()
        bvmt = _rate_phrase(bp.months, d.get('vat_bvmt', [8.0] * 12))
        basis = (operating_inputs.water_stable_vi(yr) if project.get('stable_operation') else
                 f"Chi phí hạng mục này dự ước tại năm {yr} dựa trên tỷ lệ "
                 f"lấp đầy cư dân tại trang 'Tỷ lệ lấp đầy cư dân'.")
        return (f"Khối lượng nước tiêu thụ tính: {qty:,.0f} {unit}, đơn giá bao gồm thuế VAT {d.get('vat_water', 5):g}%, "
                f"PBVMT {d.get('wastewater_pct', 30):g}%, VAT bvmt {bvmt} ({tariff:,.0f} {tunit}"
                + (" tháng đầu" if len(set(e.get('tariff_by_month', []))) > 1 else "") + f"). {price_source} " + basis)
    if category == 'Electricity':
        basis = (f"Dự ước tại năm {yr}. {operating_inputs.ELECTRICITY_STABLE_VI}"
                 if project.get('stable_operation') else
                 f"Dự ước tại năm {yr} dựa "
                 f"trên tỷ lệ lấp đầy cư dân, căn cứ theo trang 'Tỷ lệ lấp đầy cư dân' — mức tối "
                 f"thiểu khi tỷ lệ lấp đầy bằng 0 là khoảng 40% full chi phí, đạt full chi phí khi "
                 f"tỷ lệ lấp đầy từ 40% trở lên.")
        bp = project.get('budget_period') or budget_period.default()
        vat_clause = (f", cộng VAT {_rate_phrase(bp.months, _general_vat_months(project))} theo từng tháng"
                      if _ACTIVE_VAT_SENTENCE else "")
        return (f"Tổng lượng điện tiêu thụ 1 tháng {qty:,.0f} {unit}. Đơn giá điện đang áp dụng "
                f"theo mức đơn giá điện dưới 6KV — đơn vị hành chính sự nghiệp ({tariff:,.0f} "
                f"{tunit} trước VAT{vat_clause}), theo Quyết định 1279/QĐ-BCT ngày 09/05/2025. " + basis)
    d = e.get('dated') or {}
    if d:
        bp = project.get('budget_period') or budget_period.default()
        price = (f"Giá dầu DO 0,05S-II Vùng 1 niêm yết ngày {d['as_of'].strftime('%d/%m/%Y')} là "
                 f"{d['listed']:,.0f} đ/lít đã gồm VAT {d['listed_vat']:g}%; quy đổi theo VAT từng tháng "
                 f"({_rate_phrase(bp.months, d['vat_by_month'])}) là {tariff:,.0f} {tunit}"
                 + (" tháng đầu" if len(set(e.get('tariff_by_month', []))) > 1 else "") + ".")
    else:
        price = f"Giá dầu DO 0.005S Vùng 1 niêm yết {as_of} là {tariff:,.0f} {tunit}."
    return (f"Dự ước tiêu thụ {qty:,.0f} {unit}. Mỗi năm chạy test không tải khoảng 12 giờ; "
            f"chạy backup điện có tải do sự cố điện lưới và bảo trì máy biến thế + tủ điện hạ "
            f"thế chính khoảng 8 giờ/năm. " + price)


def _recipe_narrative(key, wb, project, demand, year, written):
    """The fill-in-the-blanks Vietnamese templates for the recipe-driven '1. Summary' rows —
    the AI Guideline's own note text (docs/11-guideline-remark-model.md,
    scratchpad/guideline_summary.txt) with its blanks filled from this project's data, wording
    matched to the worked sample's actual usage (docs/12-sample-remark-rescan.md; 2026-09-11, user
    direction — Vietnamese only). A clause with no real data behind it is a stated caveat, never a
    fabricated number (project rule). The parts each must contain are recorded in the catalogue
    `summary_recipe` column and enforced by verify.py.
    """
    yr = _budget_year(wb, year)

    if key == 'RM':
        rev = {c: w for c, w in written.items() if c.startswith('RM.') and c != 'RM.0A'}
        code_to_prod = {v: k for k, v in PRODUCT_REVENUE_EXPECTED_CODE.items()}
        area_bits, rate_bits = [], []
        for c, w in sorted(rev.items(), key=lambda cw: cw[1]['row']):
            prod = code_to_prod.get(c, c)
            label = _PRODUCT_VI_LABEL.get(prod, w['name_vi'])
            nfa = ((project.get('products') or {}).get(prod) or {}).get('nfa') or 0
            if c not in _UNIT_RATES and not nfa:
                continue        # a product this project does not have (e.g. RM.AP of a villa-only project)
            if c not in _UNIT_RATES:
                raise ValueError(f"No recorded unit rate for {c}: the fee narrative must quote the "
                                 f"rate the line is priced at, not revenue divided by area.")
            rate = _UNIT_RATES[c]
            area_bits.append(f"{nfa:,.0f} m2 ({label})")
            rate_bits.append(operating_inputs.summary_entered_rate_vi(label, rate, _ENTERED_RATE_VAT[c])
                             if c in _ENTERED_RATE_VAT else
                             f"{label} là {rate:,.0f} VND/m2/tháng (đã gồm VAT)")
        dev = written.get('RM.0A', {}).get('value', 0)
        # Group B (docs/13-remark-case-model.md): real if the PM entered it on the intake form,
        # else describe the mechanism without a month count — never a guessed number.
        prepaid = project.get('handover_prepaid_months')
        point4 = (f"4/ Dự ước tỷ lệ bàn giao và tỷ lệ nợ xấu theo kinh nghiệm QLVH của Savills tại các dự "
                  f"án tương đương")
        if project.get('stable_operation'):
            # Stable operation (use-operating-project-actuals P3): RM.0A is 0, nothing awaits handover.
            point3 = operating_inputs.SUMMARY_RM_POINT3_STABLE_VI
            point4 = operating_inputs.SUMMARY_RM_POINT4_STABLE_VI
        elif prepaid:
            point3 = (f"3/ Ước tính theo thông tin CĐT cung cấp thu trước {prepaid:g} tháng PQL cư "
                     f"dân khi bàn giao nhà, và CĐT sẽ đóng PQL những căn chưa bàn giao — dự ước "
                     f"{dev:,.0f} VND trong năm, giảm dần theo tỷ lệ lấp đầy cư dân")
        else:
            point3 = (f"3/ CĐT sẽ đóng PQL cho những căn chưa bàn giao — dự ước {dev:,.0f} VND "
                     f"trong năm, giảm dần theo tỷ lệ lấp đầy cư dân")
        vi = (
            f"Dự ước doanh thu phí quản lý năm {yr} dựa trên cơ sở:\n"
            f"1/ Diện tích thu phí theo thông tin CĐT cung cấp là: {', '.join(area_bits)}\n"
            f"2/ Mức phí quản lý " + '; '.join(rate_bits) + "\n"
            f"{point3}\n"
            f"{point4}\n"
            f"=> Chi tiết xem tại trang 'Tỷ lệ lấp đầy cư dân'.\n"
            # K14-a (decision of 2026-10-19, design D9c): this is revenue, and each rate above states its own VAT
            # basis, so the narrative always ends with the revenue sentence; _append_vat() adds nothing after it.
            + operating_inputs.entered_rate_year_vi(yr)
        )
        return vi

    if key == 'RPa':
        moto = written.get('RP1', {}).get('value', 0)
        car = written.get('RP2', {}).get('value', 0)
        moto_slots = project.get('moto_slots') or 0
        car_slots = project.get('car_slots') or 0
        # The priced monthly price per slot, not year-1 revenue spread over the slots (that is a
        # ramp-diluted average and reads as the price).
        moto_rate = round(_UNIT_RATES['RP1']) if moto_slots else 0
        car_rate = round(_UNIT_RATES['RP2']) if car_slots else 0
        lines = []
        # P2: a recorded monthly figure is quoted as the PM's recorded average, never as a per-bay rate.
        recorded = ((project.get('operating') or {}).get('parking')) or {}
        if recorded.get('moto') is not None:
            lines.append(operating_inputs.summary_parking_recorded_vi('moto', recorded['moto'], yr))
        elif moto_slots:
            basis = (operating_inputs.SUMMARY_PARKING_STABLE_VI + " "
                     if project.get('stable_operation') else
                     "Dự ước theo tỷ lệ lấp đầy cư dân tại trang 'Tiến độ lấp đầy bãi xe'. ")
            lines.append(basis +
                        f"Giả định trung bình mỗi căn hộ có 02 xe máy ({moto_slots:,.0f} chỗ), với "
                        f"đơn giá gửi tháng khoảng {moto_rate:,.0f} VND/xe/tháng — dự ước "
                        f"{moto:,.0f} VND năm {yr}")
        if recorded.get('car') is not None:
            lines.append(operating_inputs.summary_parking_recorded_vi('car', recorded['car'], yr))
        elif car_slots:
            lines.append(f"Bãi xe ô tô ({car_slots:,.0f} chỗ), đơn giá gửi tháng khoảng "
                        f"{car_rate:,.0f} VND/xe/tháng — dự ước {car:,.0f} VND năm {yr}")
        vi = ("Dự toán hạng mục doanh thu này bao gồm:\n" + _vi_list(lines) +
              "\n=> Chi tiết doanh thu bãi xe tại trang 'Tiến độ lấp đầy bãi xe'.")
        return vi

    if key == 'RI':
        return ("Dự ước bao gồm:\n"
                "- Thu kinh phí vận hành đã chi hộ quỹ khai thác khu vực chung\n"
                "Chi tiết xem tại trang '2.2 Common area Fund'.")

    if key == 'EMH':
        from generate_project_output import SERVICE_CATEGORY_KEYWORDS
        svc_kws = [k for cat in ('Security', 'Cleaning', 'Landscape')
                   for k in SERVICE_CATEGORY_KEYWORDS[cat]]
        head = 0
        for d in (demand or []):
            pos = d.get('Position', '').lower()
            if not any(k in pos for k in svc_kws):
                head += d.get('StaffPerDay', 0) or 0
        emh1 = written.get('EMH1', {}).get('value') or 0
        # EMH2 is a formula reference into 'A1. Staff cost 08.2026 (VN)' (change
        # reconcile-summary-with-detail-sheets) — openpyxl has no cached number for it here, so the
        # clause states the real basis without a figure rather than showing a stale or wrong one.
        emh2_value = written.get('EMH2', {}).get('value')
        payroll_clause = (f"lương gộp dự ước {emh2_value:,.0f} VND"
                          if emh2_value is not None else
                          "lương gộp theo bảng lương thực tế")
        fee_clause = savills_fee.summary_clause_vi(project if emh1 else {}, emh1)
        vi = (
            "Chi phí hạng mục này dự ước bao gồm:\n"
            "- Chi phí quản lý của Công Ty Quản lý bao gồm chi phí thương hiệu, phần mềm, các hỗ "
            "trợ từ văn phòng chính. Chi phí hạng mục này được đề xuất dựa trên khối lượng công "
            f"việc và thực tế bàn giao sản phẩm của dự án. {fee_clause}\n"
            f"- Số lượng nhân sự Ban quản lý ({head:g} vị trí làm việc mỗi ngày, chưa gồm bảo vệ/vệ sinh/cây xanh — "
            f"thuê ngoài) dựa trên quy mô, đặc thù dự án cũng như các yêu cầu về chất lượng nhân sự "
            f"phù hợp với phân khúc dự án — {payroll_clause}, đã gồm BHXH/BHYT/BHTN phần người sử "
            "dụng lao động. Thời gian làm việc ca đêm các ngày, ca ngày dịp lễ tết theo đặc thù "
            "công việc tại dự án và quy định của nhà nước\n"
            "=> Chi tiết chi phí nhân sự xem tại trang 'A1. Staff cost 08.2026 (VN)'\n"
            "=> Chi tiết chi phí huấn luyện bắt buộc hàng năm (ATLĐ, PCCC) theo nghị định 105 tại "
            "trang 'A5. Trợ cấp PCCC'."
        )
        return vi

    if key in ('ESS1', 'ESS4'):
        cat = 'Security' if key == 'ESS1' else 'Cleaning'
        from generate_project_output import SERVICE_CATEGORY_KEYWORDS, SERVICE_EXCLUDE_KEYWORDS
        kws = SERVICE_CATEGORY_KEYWORDS[cat]
        priced, other = {}, {}          # priced = the posts contract_cost() counts; other = supervisor etc.
        for d in (demand or []):
            pos = d.get('Position', '')
            if not any(k in pos.lower() for k in kws):
                continue
            spd = d.get('StaffPerDay', 0) or 0
            eff = math.ceil(spd * 7 / 6) if (d.get('CoverageDays', 0) or 0) >= 7 else spd
            # collapse "(Morning)/(Afternoon)/(Night)/(Day)" shift-time suffixes into one role
            role = re.sub(r'\s*\((?:Morning|Afternoon|Evening|Night|Day)\)\s*$', '', pos).strip()
            bucket = other if any(ex in pos.lower() for ex in SERVICE_EXCLUDE_KEYWORDS) else priced
            bucket[role] = bucket.get(role, 0) + eff
        priced = {r: n for r, n in priced.items() if n}
        other = {r: n for r, n in other.items() if n}
        sheet_ref = "'A2. Bảo vệ - Security'" if cat == 'Security' else "'A3. Vệ sinh - Cleaning'"
        def _role_vi(r):
            return _SECURITY_CLEANING_ROLE_VI.get(r, r)
        roles = [f"{n:g} {_role_vi(r)}" for r, n in sorted(priced.items())] or [f"theo {sheet_ref}"]
        # Posts that are listed but not in this line's cost (a supervisor, say) go in their own
        # sentence, so the list above adds up to the stated total (change fix-deliverable-remark-wording).
        not_counted = ', '.join(f"{n:g} {_role_vi(r)}" for r, n in sorted(other.items()))
        not_counted_note = f" {not_counted} không nằm trong khoản này." if not_counted else ''
        total_posts = sum(priced.values())
        val = written.get(key, {}).get('value', 0)
        from master_comparables import SECURITY_RATE_CITYWIDE, CLEANING_RATE_CITYWIDE
        rate = SECURITY_RATE_CITYWIDE if cat == 'Security' else CLEANING_RATE_CITYWIDE
        if cat == 'Security':
            vi = (f"Dự ước {total_posts:g} vị trí bảo vệ (quy đổi 24h) bao gồm: {', '.join(roles)} "
                  f"— dựa trên trang {sheet_ref}.{not_counted_note}\n"
                  f"Đơn giá vị trí 24h khoảng {rate:,.0f} VND/vị trí/tháng.\n"
                  f"Dự ước {val:,.0f} VND năm {yr}.")
        else:
            vi = (f"Dự ước {total_posts:g} nhân viên vệ sinh tính tiền bao gồm: {', '.join(roles)} — dựa "
                  f"trên trang {sheet_ref}.{not_counted_note}\n"
                  f"Đơn giá nhân viên vệ sinh khoảng {rate:,.0f} VND/vị trí/tháng (bắt buộc); đơn "
                  f"giá tea lady/giám sát nếu có.\n"
                  f"Dự ước {val:,.0f} VND năm {yr}.")
        return vi

    if key == 'EN':
        code_to_group_vi = {
            'EN1': 'Trang thiết bị văn phòng ban quản lý',
            'EN2': 'Trang thiết bị công cụ dụng cụ kỹ thuật & PCCC',
            'EN3': 'Trang thiết bị công cộng, khu tiện ích',
            'EN4': 'Trang thiết bị khu tiện ích / khách thuê',
        }
        got = [(c, w) for c, w in sorted(written.items(), key=lambda cw: cw[1]['row'])
               if c.startswith('EN')]
        grp = [f"{code_to_group_vi.get(c, w['name_vi'])}: {w['value']:,.0f} VND" for c, w in got]
        vi = ("Chi phí đầu tư trang thiết bị đầu tư ban đầu (CAPEX) bao gồm:\n" + _vi_list(grp) +
              "\nChi phí này dự kiến được khấu hao hết trong 24 tháng đầu vận hành của dự án.")
        return vi

    if key in ('EEW', 'EEE', 'EED'):
        cat = {'EEW': 'Water', 'EEE': 'Electricity', 'EED': 'Diesel (Generator Fuel)'}[key]
        return _energy_narrative_vi(cat, project, yr)

    return None


def _compose_summary_narratives(wb, project, demand, year, written):
    """Write a composed, Vietnamese, client-facing narrative into '1. Summary' column K for every
    PART-1 total the pipeline gave a non-zero figure — per the AI Guideline's recipe for that row
    (docs/11-guideline-remark-model.md; wording matched to docs/12-sample-remark-rescan.md). Runs
    after the fills and BEFORE _normalise_all_remark_columns() so the (now much taller) K rows are
    sized. Plain text; no budgeted figure moves.

    No-op while ENABLE_SUMMARY_REMARK_COMPOSER is False — the template's own K cells (blank /
    single-line pull) are left untouched.
    """
    if not ENABLE_SUMMARY_REMARK_COMPOSER:
        return []
    ws = wb['1. Summary']
    common_area_codes = set(COMMON_AREA_FUND_EXPECTED_CODE.values())
    common_area_active = any(c in written for c in common_area_codes)
    claimed = set()
    filled = []
    for srow, kind, code, prefixes in _SUMMARY_PART1:
        children = [(c, w) for c, w in _children_for(prefixes, written) if c not in claimed]
        if kind == 'recipe':
            # RI has no fund leaf in `written` — its row 78 (RI1) is a template formula pulling from
            # '2.2 Common area Fund'. Compose it whenever the common-area fund produced revenue.
            if code == 'RI' and not common_area_active:
                continue
            narrative = _recipe_narrative(code, wb, project, demand, year, written)
            if narrative is None:
                continue
            if code != 'RI' and not children:
                continue
        else:  # rollup
            fixed = _ACCREDITATION_SENTENCE if srow == 34 else ''
            # EMA (row 23): the pipeline writes one blended per-m² section ratio to the EMA15
            # catch-all leaf — there is no per-line breakdown to list. Say so rather than imply the
            # section is just "Others".
            if code == 'EMA' and children and all(c == 'EMA15' for c, _w in children):
                fixed = ("Đây là ước tính chung cho toàn bộ mục chi phí quản lý văn phòng theo một "
                         "suất trên m², chưa tách theo từng khoản mục.")
            narrative = _rollup_narrative(children, fixed_sentence=fixed)
            if narrative is None:
                continue
        for c, _w in children:
            claimed.add(c)
        narrative = _append_vat(narrative)
        cell = ws.cell(row=srow, column=_SUMMARY_K_COL, value=narrative)
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        filled.append(f"K{srow}({code})")
    filled += _write_contingency_narratives(wb, project, written)
    if filled:
        print('  1. Summary narratives:', ', '.join(filled))
    return filled


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


def _populate_fillup_sheets(wb, apt_units, shop_units, car_bays, moto_bays,
                            resident_fills, car_fills, moto_fills, car_rate, moto_rate, stable=False):
    """Show, on the deliverable's two fill-up sheets, the exact monthly curves the occupancy-scaled
    budget lines were distributed by (spec: a reader can trace a ramped figure to its curve).

    The sheets ship an elaborate handover-rate → cumulative-units → occupancy model built for a
    human filling 24 months by hand. Rather than reverse-engineer that, this writes the pipeline's
    one curve (fill_curve.year1_fills) straight into the sheets' occupancy / parking-fill rows as
    values, feeds the few input cells the remaining formulas divide by, and clears the two rows on
    the resident sheet that compute unused cumulative-unit ratios (they divide by cells the pipeline
    does not populate). Nothing on these sheets feeds any budget total — proven in change A.
    Columns: resident sheet months 1-12 = G:R; parking sheet months 1-12 = F:Q.
    """
    from common_utils_v2 import find_sheet_loose
    res = wb[find_sheet_loose(wb, 'lấp đầy cư dân')]
    pk = wb[find_sheet_loose(wb, 'lấp đầy bãi xe')]

    res['F6'] = apt_units or 0
    res['F7'] = shop_units or 0
    for i, f in enumerate(resident_fills):            # G(7)..R(18)
        res.cell(row=6, column=7 + i, value=f)        # handover rate (= occupancy in the one-curve model)
        res.cell(row=7, column=7 + i, value=f)
        res.cell(row=20, column=7 + i, value=f)       # "Tỷ lệ lấp đầy" — the curve the budget uses
    for row in (23, 26):                              # unused cumulative-unit ratio rows -> #DIV/0!
        for c in range(1, res.max_column + 1):
            cell = res.cell(row=row, column=c)
            if isinstance(cell.value, str) and cell.value.startswith('='):
                cell.value = None

    pk['D6'] = apt_units or 0
    pk['D9'] = car_bays or 0
    pk['D10'] = 0
    pk['D11'] = moto_bays or 0
    pk['D22'] = car_rate
    pk['D24'] = moto_rate
    for i, (cf, mf) in enumerate(zip(car_fills, moto_fills)):   # F(6)..Q(17)
        pk.cell(row=9, column=6 + i, value=cf)        # car fill %
        pk.cell(row=11, column=6 + i, value=mf)       # motorbike fill %
        pk.cell(row=12, column=6 + i, value=0)        # bicycle — pipeline does not budget RP3
    if stable:
        # 'Stable Operation?' = Yes: the curves above are 100% flat; say why beside each title.
        res['G2'] = operating_inputs.FILL_SHEET_REASON_VI
        pk['F2'] = operating_inputs.FILL_SHEET_REASON_VI
    # The form's own notes on these sheets name other projects (one of them misspelled, so no data-built name list
    # finds it): replaced by fixed address with the same meaning, without the names (change
    # apply-head-of-pm-decisions-2026-10, D13; listed for the form owner).
    for ws, coord, text in ((res, 'AO27', _FILLUP_NOTE_BAD_DEBT), (res, 'AO28', _FILLUP_NOTE_UNOCCUPIED_DEBT),
                            (res, 'A38', _FILLUP_NOTE_HANDOVER), (pk, 'B42', _FILLUP_NOTE_HANDOVER)):
        ws[coord] = text


def _apartment_column_weight(project):
    """(weight, villas_used): the NFA the standard form's apartment allocation column carries. The form has no villa
    column, so a project without apartments puts its villas there (change support-villa-only-and-no-parking, D1, D4)."""
    prods = project.get('products') or {}
    apartment = (prods.get('Apartment') or {}).get('nfa') or 0
    if apartment:
        return apartment, False
    villas = (prods.get('Villas') or {}).get('nfa') or 0
    return villas, bool(villas)


def _villa_column_note(nfa):
    return (f"Dự án không có căn hộ: diện tích biệt thự ({nfa:,.0f} m2 NFA) được tính vào cột căn hộ để phân bổ chi "
            f"phí, vì mẫu chuẩn không có cột biệt thự.")


_ZERO_BAY_NOTE = ("Dự án không có chỗ {kind}: tỷ lệ lấp đầy từ tháng 13 ghi 0, vì công thức của mẫu chia cho số "
                  "chỗ {kind}.")


def _fill_product_mix_fallbacks(wb, project):
    """The standard form's allocation weights for a project without apartments or without parking bays (change
    support-villa-only-and-no-parking, D2, D3). Runs after fill_management_fund_sheet(); a project with apartments
    and bays is left exactly as that function wrote it."""
    from common_utils_v2 import find_sheet_loose
    weight, villas = _apartment_column_weight(project)
    if villas:
        # Every leaf row's BG<row> reads '=$BG$10'; '0. Info'!D8 stays empty so no fee table shows villas as apartments.
        ws = wb['2. Budget-Management Fund']
        ws['BG10'] = weight
        ws['BG10'].comment = Comment(_villa_column_note(weight), 'Budget Planning Agent')
        ws['BG9'] = 'Biệt thự (tính vào cột căn hộ)'

    pk = wb[find_sheet_loose(wb, 'lấp đầy bãi xe')]
    if not (project.get('apartment_units') or 0):
        pk['D6'] = sum((p.get('units') or 0) for p in (project.get('products') or {}).values())
    for row, slots, kind in ((9, project.get('car_slots'), 'ô tô'), (11, project.get('moto_slots'), 'xe máy')):
        if slots:
            continue
        divides = re.compile(rf'/\s*\$?D\$?{row}(?![0-9])')
        zeroed = 0
        for c in range(1, pk.max_column + 1):
            cell = pk.cell(row=row, column=c)
            if isinstance(cell.value, str) and cell.value.startswith('=') and divides.search(cell.value):
                cell.value = 0
                zeroed += 1
        if zeroed:
            pk.cell(row=row, column=5).value = _ZERO_BAY_NOTE.format(kind=kind)


_FILLUP_NOTE_BAD_DEBT ='Căn cứ trên tỷ lệ nợ xấu PQL của các dự án tham chiếu: 8.7% và 10%'
_FILLUP_NOTE_UNOCCUPIED_DEBT = 'Căn cứ trên tỷ lệ nợ khó thu của những căn chưa về ở của một dự án tham chiếu'
_FILLUP_NOTE_HANDOVER = ('Note: \n- Năm 1 dự ước tiến độ bàn giao của CĐT trong 6 tháng (tương tự tiến độ bàn giao các '
                         'dự án tham chiếu khoảng 1000 căn)\n- Tham khảo tỷ lệ lấp đầy cư dân của một dự án tham chiếu '
                         '(gần 24 tháng mới full cư dân về ở + cho thuê)')


def _write_ramped_row(ws, row, monthly_values, remark=None):
    """Twelve explicit month values into H:S (Schedule frequency, so G=SUM(H:S)) — for a line that
    varies month by month with the occupancy fill-up curve (fill_curve.py), not a flat run-rate.
    F (Unit Price) is cleared: it drives G=F*12 only under the Monthly frequency this does not use."""
    if len(monthly_values) != 12:
        raise ValueError(f'_write_ramped_row needs exactly 12 monthly values, got {len(monthly_values)}')
    ws.cell(row=row, column=3, value='Schedule')  # C: Frequency -> G = SUM(H:S)
    ws.cell(row=row, column=6, value=None)        # F: Unit Price — not used under Schedule
    for i, value in enumerate(monthly_values):
        cell = ws.cell(row=row, column=8 + i, value=round(value))  # H..S
        cell.number_format = _NUM_FMT
    _write_remark(ws, row, remark)


# Real, cited flat reference costs added 2026-08-27 from input/logic/EXENSIVE LOGIC.xlsx's new
# Sheet2 (a "COST NATURE DESCRIPTION" column added alongside a second real capex catalog file —
# both re-scanned per the PM's request). Each cites a real regulation, vendor quote, or lab price
# in the source cell; see the write_even_monthly() calls below for the exact figure and citation.
# Public liability insurance (ESI2, ~1,000 USD/year premium for a 1M USD liability cap) is priced since change
# apply-head-of-pm-decisions-2026-10 (group 3) from an editable USD premium and exchange rate; see _resolve_esi2.
ENV_REPORT_ANNUAL = 25_000_000            # ESM2 — Decree 40/2019/NĐ-CP Article 47; real service quote
WATER_TEST_SAMPLE_PRICE = 1_352_000       # ESM3 — Pasteur Institute HCMC quote, per QCVN 01-2024/BYT
WATER_TEST_SAMPLES_PER_ROUND = 3          # rooftop tank + basement + 1 random tap, 2 rounds/year
POOL_TEST_SAMPLE_PRICE = 1_366_000        # ESM5 — real estimate, 4 microbiological parameters/sample
POOL_TEST_SAMPLES_PER_YEAR = 8            # 4 rounds/year x 2 samples/round, PER POOL
FIRE_DEPT_CONNECTION_MONTHLY = 500_000    # ESM8 — GSAFE package G500, HCMC Fire Fighting Dept transmission
# ESM4 pool chemicals is computed by estimate_opex(), because BOTH generators call that and a
# second copy here is how the two workbooks drift apart. See POOL_SALT_* in estimate_opex.py.

# Added 2026-09-14, change fill-guideline-required-line-items — figures the AI Guideline states
# directly (not a comparable-benchmark estimate), same "real cited figure" class as the four above.
ENV_INCIDENT_PLAN_ANNUAL = 14_000_000       # ESC12 — mandatory annual environmental incident-response
                                             # plan, once/year; guideline's own provisional figure, excl VAT
WASTEWATER_CROSSCHECK_SAMPLE_PRICE = 3_500_000  # ESM25 — cross-check of the STP contractor's own
                                                 # treated-water quality reporting (per SCE), excl VAT
WASTEWATER_CROSSCHECK_PER_YEAR = 4          # quarterly
DRINKING_WATER_L_PER_PERSON_DAY = 1         # EMA7 — guideline: BQL headcount x 1 L/person/day
DRINKING_WATER_BOTTLE_LITERS = 19
DRINKING_WATER_BOTTLE_PRICE = 60_000        # incl. VAT — guideline's own cited 19L bottle vendor price

# Added 2026-09-21, change complete-ai-guideline-remark-coverage (B2.6 / waste-collection-costing
# track) — read directly from the guideline's own 'B2.6 Rác sinh hoạt (QD67)' worksheet (both the
# docs/ source copy and the live TEMPLATE_PATH form carry the same three unit prices). QĐ
# 67/2025/QĐ-UBND's three-part household-waste tariff, VND/kg, excl. VAT. Since change
# apply-head-of-pm-decisions-2026-10 (group 2, task 2.6) the prices are those of QĐ 65/2026/QĐ-UBND
# (group 1 household waste, 01/09/2026 to 30/06/2027): 486 + 180 + 421 = 1,087 VND/kg, replacing
# 485.97 + 180.07 + 420.45 = 1,086.49. VAT is added by month from the dated rate file.
WASTE_COLLECTION_PRICE = 486                # Dịch vụ thu gom tại nguồn CTRSH
WASTE_TRANSPORT_PRICE = 180                 # Dịch vụ vận chuyển CTRSH
WASTE_TREATMENT_PRICE = 421                 # Dịch vụ xử lý CTRSH
WASTE_UNIT_PRICE = (WASTE_COLLECTION_PRICE + WASTE_TRANSPORT_PRICE
                    + WASTE_TREATMENT_PRICE)  # 1,087 VND/kg
WASTE_APARTMENT_KG_PER_UNIT_DAY = 2.63      # guideline note + formula instruction agree for Apartment
# Shophouse: the guideline sheet is internally inconsistent — its note text says "khoảng 3.41kg"
# per unit/day, but the formula instruction beside it says "2.63 x 1.5 x 30 ngày" (= 3.945 kg/day).
# PM decision (design.md D3): use the formula-instruction basis, not the note text — the note is
# the guideline's own inconsistency, disclosed in the written remark, not silently followed.
WASTE_SHOPHOUSE_KG_PER_UNIT_DAY = WASTE_APARTMENT_KG_PER_UNIT_DAY * 1.5   # 3.945
WASTE_DAYS_PER_MONTH = 30                   # guideline's own instruction is monthly ("x 30 ngày"),
                                             # not annual — matches every other Monthly-frequency row

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
    'mgmt_fee_revenue': 14,     # RM.AP  Management fee of Apartment (revenue) — see PRODUCT_REVENUE_ROWS
    'mgmt_fee_developer': 23,   # RM.0A  Management fee the developer pays on units not yet handed over
                               #        — the mirror of the fill-up curve (see fill_management_fund_sheet)
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
    # The other two categories estimate_opex() computes. Both go to the CATCH-ALL leaf of their
    # section, never to the section row itself: EMA (94) is =SUBTOTAL(9,G95:G113) and ER (263) is
    # =SUBTOTAL(9,G264:G485), so writing a value there would replace the template's own arithmetic
    # with a constant and the section would stop summing its own line items. Each figure is one
    # blended per-m² ratio with no per-line breakdown behind it, which is exactly what a catch-all
    # row is for — spreading it across EMA1..EMA19 or the ER systems would invent an allocation.
    'opex_admin': 109,          # EMA15  Others (inside EMA's =SUBTOTAL(9,G95:G113))
    # 'opex_repairs' -> ERM (row 485). Restored 2026-09-17 by change `fix-parking-allocation-divide-
    # by-zero`, which populates BM11:BN11 (the parking-revenue allocation split) and the per-row
    # BG/BH reference every leaf of the ER section needs — both were empty in Savills' template,
    # which is what made writing anything here produce #DIV/0! before that change. Previously
    # deferred by `write-computed-opex-categories-to-deliverable`'s task 2.4 for exactly this reason
    # — this write site is that deferred task, now unblocked.
    'opex_repairs': 485,        # ERM    Repairs & Maintenance (materials only)
    'capex_mo': 223,            # EN1    New capital expenditure for MO
    'capex_me': 224,            # EN2    New capital expenditure for ME team
    'capex_public': 225,        # EN3    New capital expenditure for Common area
    'capex_amenity': 226,       # EN4    New capital expenditure for Tenant area
    'env_report': 194,          # ESM2   Outsourcing Environmental Report
    'water_testing': 195,       # ESM3   Domestic water testing
    'pool_testing': 197,        # ESM5   Pool water testing (only written if project has a pool)
    'fire_dept_connect': 200,   # ESM8   Connect to HCMC Fire Fighting Dept
    # Added 2026-09-14, change fill-guideline-required-line-items (Required codes previously left at
    # the template's blank default with no data-gap reason — see that change's docs/14).
    'pccc_allowance': 85,       # EMH4   Staff related cost (mandatory ATLĐ/PCCC training, officer allowance)
    'drinking_water': 101,      # EMA7   Drinking water
    'env_incident_plan': 143,   # ESC12  Mandatory environmental incident-response plan
    'wastewater_crosscheck': 210,  # ESM25  Cross-check of wastewater-treatment water quality
    'asset_insurance': 189,     # ESI1   Risk asset insurance — no figure written, remark-only (see below)
    # Added 2026-09-21, change complete-ai-guideline-remark-coverage (B2.6 / waste-collection-costing
    # track). NOT the bare "B2.6" name the guideline's own worksheet uses — that worksheet is the
    # RATE SOURCE, not a row on this template. The actual write target, verified by content (column Y
    # alone gives no clue — its codes are short and un-labelled): row 153 is the only one of the
    # nearby ESS9-ESS23 codes whose own column-Z label reads "Normal garbage collection / Thu gom rác
    # sinh hoạt" AND whose column-T guideline note explicitly names Quyết định 67/2025. ESS10 (row
    # 154, hazardous waste) and ESS11 (row 155, construction rubble) are real, different waste
    # streams the guideline's B2.6 sheet does not price at all — left alone. ESS19 (row 163, garbage
    # bags) is a real waste-adjacent consumable with no unit price anywhere — left alone.
    'waste_collection': 153,    # ESS9   Normal domestic garbage collection (QĐ 65/2026)
    'esi2': 190,                # ESI2   Public liability insurance, USD premium x rate x 1.10
    # Added 2026-10-19, change apply-head-of-pm-decisions-2026-10 (group 6): the contingency lines, live month
    # formulas over their group's leaves (_write_contingency_lines; contingency.py).
    'contingency_em': 131,      # EM#    Management-expense contingency
    'contingency_es': 221,      # ES#    Outsourced-service contingency
    'contingency_ee': 262,      # EE#    Energy contingency
}

# Cost code each MGMT_FUND_ROWS key must land on — the guard below checks every row on every run
# (column Y of "2. Budget-Management Fund" carries each row's own code). Verified against the
# 2027 Resi Budget Form (IT team) template, 2026-09-10, change `rebase-output-onto-25-sheet-form`.
MGMT_FUND_EXPECTED_CODE = {
    'mgmt_fee_revenue': 'RM.AP', 'mgmt_fee_developer': 'RM.0A',
    'mgmt_fee_expense': 'EMH1', 'staff_remainder': 'EMH2',
    'parking_moto': 'RP1', 'parking_car': 'RP2', 'security': 'ESS1', 'cleaning': 'ESS4',
    'landscape': 'ESS16', 'pool_salt': 'ESM4', 'water': 'EEW.C', 'electricity': 'EEE.C',
    'diesel': 'EED.C', 'opex_admin': 'EMA15', 'opex_repairs': 'ERM', 'capex_mo': 'EN1', 'capex_me': 'EN2',
    'capex_public': 'EN3', 'capex_amenity': 'EN4', 'env_report': 'ESM2', 'water_testing': 'ESM3',
    'pool_testing': 'ESM5', 'fire_dept_connect': 'ESM8',
    'pccc_allowance': 'EMH4', 'drinking_water': 'EMA7', 'env_incident_plan': 'ESC12',
    'wastewater_crosscheck': 'ESM25', 'asset_insurance': 'ESI1',
    'waste_collection': 'ESS9', 'esi2': 'ESI2',
    'contingency_em': 'EM#', 'contingency_es': 'ES#', 'contingency_ee': 'EE#',
}


def _assert_leaf_rows(ws, sheet_label, rowmap, expected, code_col=_CODE_COL):
    """Stop rather than write a figure to whatever row now sits at a hardcoded position.

    Called once at the top of each fill function. If Savills reshapes a sheet, the positions move
    and the pipeline would silently fill the wrong cost lines — the same failure class that made
    read_input() go label-based. Every leaf row carries its own cost code in column Y, so each
    hardcoded position is checked against it before anything is written.
    """
    for key, row in rowmap.items():
        want = expected.get(key)
        if want is None:
            continue
        found = ws.cell(row=row, column=code_col).value
        found = found.strip() if isinstance(found, str) else found
        if found != want:
            raise ValueError(
                f"'{sheet_label}' row {row} was expected to be cost code {want!r} ('{key}') but "
                f"carries {found!r}. The template's row layout has changed — re-verify the row map "
                f"against the current template rather than adjusting this check."
            )


def _eff_headcount(d):
    """Headcount actually needed to cover a demand row's schedule: 7-day coverage needs 7/6 the
    staff-per-day (a fixed 1-day-off-in-7 rotation), anything less needs exactly StaffPerDay.
    Shared by fill_staff_cost_sheet() and _unplaced_positions() — same math, one place."""
    p, q = d['StaffPerDay'], d['CoverageDays']
    return math.ceil(p * 7 / 6) if q >= 7 else p


def _period_of(project):
    return project.get('budget_period') or budget_period.default()


def period_workdays(period, coverage_days, position=None):
    """One person's working days in the budget period for a position covered `coverage_days` a week: the calendar
    count (Mondays to Saturdays minus the paid holidays; 302 for 2027). New prospects only, in both workbooks; Existing
    mode keeps WORKDAYS_PER_MONTH (change apply-head-of-pm-decisions-2026-10, D6 and G2-a). A staffed position with
    no coverage day stops the run and is named."""
    try:
        return vn_holidays.working_days(period.first_day, period.last_day, coverage_days)
    except ValueError as exc:
        if position:
            raise ValueError(f"Staffing Demand '{position}': {exc}") from None
        raise


def _new_prospect_monthly_gross(rows, period):
    """Headcount-weighted monthly gross of a new prospect's demand rows: each row's daily rate x its working days in
    the period / 12, paid evenly over the twelve months (docs/30 D4-a). Rows with no headcount weigh nothing."""
    staffed = [d for d in rows if _eff_headcount(d)]
    total = sum(_eff_headcount(d) for d in staffed)
    if not total:
        return 0
    return round(sum(_eff_headcount(d) * d['AvgDailyRate']
                     * period_workdays(period, d['CoverageDays'], d['Position'])
                     for d in staffed) / total / 12)


# Vietnamese label / short code for a position with no predefined row-group on 'A1. Staff cost' —
# used only when fill_staff_cost_sheet() gives it a real row (see _A1_UNPLACED_FIRST_ROW). Falls
# back to the raw English name / its first 2 letters for a position not in this small, known set.
_UNPLACED_POSITION_VI = {'Reception': 'Lễ tân'}
_UNPLACED_POSITION_CODE = {'Reception': 'LT'}

# First free row on 'A1. Staff cost 08.2026 (VN)' below its own grand total (row 96) — one blank
# spacer row (97), then one row per unplaced position. fill_staff_cost_sheet() writes these rows
# with A1's own exact formula chain (not a Python replica); fill_management_fund_sheet()'s EMH2
# only needs to know how many rows to SUM, so this row number is the contract between the two
# (they run in that order inside build_budget(), but a formula reference doesn't require the
# referenced cell to already hold a value at write time). Change reconcile-summary-with-detail-sheets.
_A1_UNPLACED_FIRST_ROW = 98


def _unplaced_positions(demand, period=None):
    """Demand rows naming a position that is neither an outsourced Security/Cleaning/Landscape
    contract (SERVICE_CATEGORY_KEYWORDS) nor one of 'A1. Staff cost'\'s own predefined row-groups
    (STAFF_COST_KEYWORDS / STAFF_COST_AA_KEYWORDS) — today: Reception, which otherwise only
    appears on 'B1. Lịch Lễ tân' (a duty roster, no payroll math). Grouped by Position name (the
    same aggregation group_stats() applies to a keyword match) so a multi-shift unplaced role
    gets one combined row instead of one per shift.

    Returns [(position_name, effective_headcount, monthly_gross)] in first-seen order — this order
    IS the row order fill_staff_cost_sheet() writes starting at _A1_UNPLACED_FIRST_ROW, and the
    only thing fill_management_fund_sheet() needs from this list is len(...), to size EMH2's SUM
    range over those rows. `period` is the budget period the monthly gross is counted in (default
    01-12/2027).
    """
    from generate_project_output import SERVICE_CATEGORY_KEYWORDS
    outsourced_kws = [kw for kws in SERVICE_CATEGORY_KEYWORDS.values() for kw in kws]
    staff_cost_kws = ([kw for kws in STAFF_COST_KEYWORDS.values() for kw in kws]
                      + [kw for kws in STAFF_COST_AA_KEYWORDS.values() for kw in kws])
    unplaced_rows = [d for d in demand
                     if not any(kw in d['Position'].lower() for kw in outsourced_kws)
                     and not any(kw in d['Position'].lower() for kw in staff_cost_kws)]
    order, grouped = [], {}
    for d in unplaced_rows:
        grouped.setdefault(d['Position'], []).append(d)
        if d['Position'] not in order:
            order.append(d['Position'])
    result = []
    for name in order:
        rows_for_name = grouped[name]
        total_headcount = sum(_eff_headcount(d) for d in rows_for_name)
        if total_headcount == 0:
            continue
        monthly_gross = _new_prospect_monthly_gross(rows_for_name, period or budget_period.default())
        result.append((name, total_headcount, monthly_gross))
    return result


def _new_prospect_groups(demand, period):
    """[(A1 row-group key, A1 code, headcount, per-person monthly gross)] for every A1 row-group with staff, in the
    template's order (STAFF_COST_KEYWORDS, then the pool and gym groups, both code 'AA')."""
    out = []
    groups = [(code, code, kws, STAFF_COST_EXCLUDE.get(code, ())) for code, kws in STAFF_COST_KEYWORDS.items()]
    groups += [(f'AA_{suffix.upper()}', 'AA', kws, ()) for suffix, kws in STAFF_COST_AA_KEYWORDS.items()]
    for key, code, keywords, exclude in groups:
        matched = [d for d in demand
                   if any(kw in d['Position'].lower() for kw in keywords)
                   and not any(x in d['Position'].lower() for x in exclude)]
        headcount = sum(_eff_headcount(d) for d in matched)
        if headcount:
            out.append((key, code, headcount, _new_prospect_monthly_gross(matched, period)))
    return out


def _new_prospect_below_rows(demand, period, rows_by_code, labels=None):
    """[(label, A1 code, monthly gross)], one per head, for A1's block below the table (from _A1_UNPLACED_FIRST_ROW):
    the unplaced positions first, then each group's heads beyond its template rows. `labels` maps a row-group key to
    the label its extra rows carry (default: the group's code)."""
    out = [(_UNPLACED_POSITION_VI.get(name, name), _unplaced_code_of(name), mg)
           for name, hc, mg in _unplaced_positions(demand, period) for _ in range(hc)]
    for key, code, headcount, mg in _new_prospect_groups(demand, period):
        extra = headcount - len(rows_by_code.get(key, []))
        label = (labels or {}).get(key, code)
        out += [(f'{label} (thêm {k + 1})', code, mg) for k in range(max(0, extra))]
    return out


def _a1_group_labels(ws, rows_by_code):
    """Each A1 row-group's label for its extra rows: its first template row's label up to the first digit
    ('Kỹ thuật viên 1' -> 'Kỹ thuật viên')."""
    return {key: re.split(r'\s*\d', str(ws.cell(row=rows[0], column=2).value or key).strip())[0].strip() or key
            for key, rows in rows_by_code.items()}


def _zero_pay_positions(demand, period):
    """In-house positions with staff whose A1 monthly gross is 0, by name, in first-seen order (flagged, not skipped)."""
    names = []
    for d in demand:
        if (_eff_headcount(d) and not _is_outsourced(d['Position'])
                and not _new_prospect_monthly_gross([d], period) and d['Position'] not in names):
            names.append(d['Position'])
    return names


# ---- Existing-project mode (change carry-forward-staffing) -----------------------------------
# The helpers below hand existing_staffing.compute() this module's own position mapping and the
# New-prospect conversions, unchanged, so a new position in Existing-project mode is priced exactly
# as it would be today. generate_project_output.py calls existing_result() too, so the Staff bridge
# and the deliverable come from one computation.
A11_SHEET = 'A1.1 Allowance (From 08.2026)'


def _a1_group_of(position):
    """The A1 row group a position is costed in ('PM', 'TN', 'AA_POOL', ...), or None."""
    p = position.lower()
    for suffix, keywords in STAFF_COST_AA_KEYWORDS.items():
        if any(kw in p for kw in keywords):
            return f'AA_{suffix.upper()}'
    for code, keywords in STAFF_COST_KEYWORDS.items():
        if any(kw in p for kw in keywords) and not any(x in p for x in STAFF_COST_EXCLUDE.get(code, ())):
            return code
    return None


def _is_outsourced(position):
    from generate_project_output import SERVICE_CATEGORY_KEYWORDS
    p = position.lower()
    return any(kw in p for kws in SERVICE_CATEGORY_KEYWORDS.values() for kw in kws)


def _unplaced_code_of(position):
    return _UNPLACED_POSITION_CODE.get(position, position[:2].upper())


def _monthly_gross_of(rows):
    """Headcount-weighted monthly gross of demand rows, for Existing mode's new positions: still the template's 25
    days a month, so Existing staff lines do not move (G2-a). New prospects use _new_prospect_monthly_gross()."""
    total = sum(_eff_headcount(d) for d in rows)
    if not total:
        return 0
    return round(sum(_eff_headcount(d) * d['AvgDailyRate'] for d in rows) / total * WORKDAYS_PER_MONTH)


def template_budget_year():
    """The template's budget year ('2. Budget-Management Fund'!AL5), read without building a budget."""
    wb = openpyxl.load_workbook(TEMPLATE_PATH, read_only=True, data_only=True)
    try:
        return int(_budget_year(wb))
    finally:
        wb.close()


def existing_result(project, demand, budget_year):
    """existing_staffing.compute() for this project, or None in New-prospect mode."""
    ex = project.get('existing')
    if ex is None:
        return None
    return existing_staffing.compute(ex, demand, int(budget_year), _a1_group_of, _is_outsourced,
                                     _unplaced_code_of, _eff_headcount, _monthly_gross_of,
                                     period=project.get('budget_period'))


def utilities_result(project, budget_year, incl_vat):
    """existing_utilities.compute() for this project, or None in New-prospect mode. `incl_vat` is the
    deliverable's VAT basis (False only when the form's VAT switch reads KHOÁN)."""
    inp = project.get('utilities')
    if inp is None:
        return None
    period = project.get('budget_period')
    return existing_utilities.compute(inp, int(budget_year), incl_vat,
                                      months=period.months if period is not None else None)


# Change use-real-budget-ranges: Required lines with no other price, priced from the range of real Savills budgets
# (real_budget_ranges.py). Rows on '2. Budget-Management Fund', checked against column Y before any write.
REAL_BUDGET_RANGE_ROWS = {'EMB4': 118, 'ESC1': 134, 'ESC2': 135, 'ESC5': 138, 'ESS7': 151, 'ESS12': 156,
                          'ESS23': 167}


def _inhouse_pool_staff(demand):
    """Pool staff the roster employs in-house (A1. Staff Cost). ESS23, outsourced pool staff, is priced only
    when there are none (user's rule, 2026-10-19)."""
    return sum(_eff_headcount(d) for d in demand or ()
               if 'pool' in str(d.get('Position', '')).lower() and not _is_outsourced(str(d['Position'])))


def real_budget_range_results(project, demand, incl_vat, staff_lump=False):
    """{code: RangeResult} for every code real_budget_ranges prices or cross-checks, on this project: its name and
    fee-paying NFA (to leave it out of its own range), pool, towers, in-house pool staff, and the VAT of each
    budget month (none when `incl_vat` is False, the KHOÁN model). `staff_lump`: an Existing project whose staff cost
    is one approved lump (no A1 rows), so ESS23 stays at 0 (user's rule, 2026-10-19). Shared by the deliverable and
    the analysis sheet, so both carry the same figures."""
    bp = project.get('budget_period') or budget_period.default()
    rates = _general_vat_months(project)
    factors = [1 + r / 100 for r in rates] if incl_vat else [1.0] * 12
    clause = (f"cộng VAT {_rate_phrase(bp.months, rates)} theo từng tháng" if incl_vat
              else "chưa cộng VAT theo mô hình tài chính đã chọn")
    return real_budget_ranges.price_all(
        real_budget_ranges.load_values(), nfa=project['total_nfa'], vat_rate=rates[0] / 100,
        vat_inclusive=incl_vat, budget_year=bp.start_year, self_name=project['name'],
        has_pool=project.get('has_pool'), tower_count=project.get('towers'),
        inhouse_pool_staff=_inhouse_pool_staff(demand), staff_lump=staff_lump, vat_factors=factors, vat_clause=clause)


def _staff_is_lump(existing):
    """True for an Existing project whose staff cost is one approved lump: A1 carries no position rows."""
    return bool(existing) and existing.lines['EMH2'].kind == 'lump'


def _row_has_figure(ws, row):
    """True when another writer already put a figure on this fund row (F or a month in H:S)."""
    return any(isinstance(ws.cell(row=row, column=c).value, (int, float)) and ws.cell(row=row, column=c).value
               or (isinstance(ws.cell(row=row, column=c).value, str)
                   and ws.cell(row=row, column=c).value.startswith('='))
               for c in (6, *range(8, 20)))


def _write_real_budget_range_lines(ws, project, demand, existing=None):
    """Write each REAL_BUDGET_RANGE_ROWS code from its real-budget range: the twelve months and the Vietnamese
    remark when the range is usable, else 0 with the reason (no pool, no tower, in-house pool staff, fewer than 10
    projects, no values file). A row another writer already priced is left alone. Returns the codes written, for
    the _FLAGGED_NO_METHOD loop to skip."""
    _assert_leaf_rows(ws, '2. Budget-Management Fund', REAL_BUDGET_RANGE_ROWS,
                      {c: c for c in REAL_BUDGET_RANGE_ROWS})
    results = real_budget_range_results(project, demand, bool(_ACTIVE_VAT_SENTENCE), staff_lump=_staff_is_lump(existing))
    done = set()
    for code, row in REAL_BUDGET_RANGE_ROWS.items():
        if _row_has_figure(ws, row):
            continue
        res = results[code]
        if res.usable:
            if len(set(res.months)) == 1:
                _write_even_monthly_row(ws, row, sum(res.months), res.remark)
            else:
                _write_ramped_row(ws, row, res.months, res.remark)
        else:
            _write_zero_reason(ws, row, code, res.reason.removeprefix('Để 0: '))
        done.add(code)
    return done


def template_vat_inclusive():
    """True unless the template's VAT switch ('2. Budget-Management Fund'!F7) reads KHOÁN — the same
    reading build_budget() makes, for generate_project_output.py's Utility Bridge."""
    wb = openpyxl.load_workbook(TEMPLATE_PATH, read_only=True, data_only=True)
    try:
        return bool(_vat_sentence(wb, None))
    finally:
        wb.close()


def _a1_rows_by_group(ws):
    """Each A1 row group's rows, read from the template's own column D / B (rows 15-88)."""
    rows_by_code = {}
    for r in range(15, 89):
        code = ws.cell(row=r, column=4).value
        label = ws.cell(row=r, column=2).value
        if label and 'hồ bơi' in str(label).lower():
            rows_by_code.setdefault('AA_POOL', []).append(r)
        elif label and 'gym' in str(label).lower():
            rows_by_code.setdefault('AA_GYM', []).append(r)
        elif code:
            rows_by_code.setdefault(str(code).strip(), []).append(r)
    return rows_by_code


def _existing_a1_layout(wb, result):
    """Where each budget-year person goes on A1: ({row: Person}, [Person below the table]).
    Heads beyond a group's template rows, and positions with no group, go below the table from
    _A1_UNPLACED_FIRST_ROW (design D12)."""
    rows_by_group = _a1_rows_by_group(wb[STAFF_COST_SHEET])
    free = {g: list(rows) for g, rows in rows_by_group.items()}
    placed, below = {}, []
    for person in result.persons:
        slots = free.get(person.group) if person.group else None
        if slots:
            placed[slots.pop(0)] = person
        else:
            below.append(person)
    return placed, below


A5_SHEET = 'A5. Trợ cấp PCCC'
_A11_EXTRA_FIRST_ROW = 15     # below A1.1's row 13 total
_A5_EXTRA_FIRST_ROW = 10      # below A5's row 8 total
_A5_TEAM_ROWS = {5: 'Đội trưởng', 6: 'Đội phó', 7: 'Thành viên'}


# ---- A new prospect's holiday and night allowance on A1.1 (change apply-head-of-pm-decisions-2026-10, group 5, D5) --
# Counts come from Staffing Demand (docs/30 B2 + D5, the user's choices of 2026-10-18):
#  - night work, 30% on normal nights and 390% on holiday nights: the staff per day on D and 24H shifts, for any
#    in-house position with a night shift;
#  - day work on a holiday, 300%: only for a position on 7-day coverage that has a night shift ("trực 24/7", B2-a);
#    its holiday day staff = the staff per day of every shift that is not a night shift (morning + afternoon), 24H
#    staff included (a 24H post works both the day and the night).
# Outsourced Security / Cleaning / Landscape are not on A1.1. Codes CS, BE, TDS, TN and AA have a template row (7-11);
# any other qualifying code gets its own row below the table, from _A11_EXTRA_FIRST_ROW, with A1.1's own formulas and
# a total row, as Existing mode's extra rows do. Existing mode never comes here (G2-a).
_A11_NIGHT_SHIFTS = {'D', '24H'}
_A11_TABLE_ROWS = {'CS': 7, 'BE': 8, 'TDS': 9, 'TN': 10, 'AA': 11}


def _a11_code_of(position):
    """The A1.1 code of an in-house position: its A1 code (both AA groups share 'AA'), else its unplaced A1 code."""
    group = _a1_group_of(position)
    if group is None:
        return _unplaced_code_of(position)
    return 'AA' if group.startswith('AA_') else group


def _shift_of(d):
    return str(d.get('ShiftCode') or '').strip().upper()


def _new_prospect_duty(demand, period):
    """[existing_staffing.DutyRow] for every in-house position group with a night shift, in first-seen order. `gross`
    is the group's per-person A1 gross (_new_prospect_monthly_gross)."""
    groups = {}
    for d in demand:
        if not d.get('StaffPerDay') or _is_outsourced(d['Position']):
            continue
        groups.setdefault(_a11_code_of(d['Position']), []).append(d)
    out = []
    for code, rows in groups.items():
        night = sum(d['StaffPerDay'] for d in rows if _shift_of(d) in _A11_NIGHT_SHIFTS)
        if not night:
            continue
        seven_day = max(d['CoverageDays'] or 0 for d in rows) >= 7
        day = sum(d['StaffPerDay'] for d in rows if _shift_of(d) != 'D') if seven_day else 0
        out.append(existing_staffing.DutyRow(code, night, night, day,
                                             gross=_new_prospect_monthly_gross(rows, period)))
    return out


def _new_prospect_a11_total_row(duty):
    """A1.1's total row when some qualifying code has no template row (its rows sit below the table), else None."""
    extra = [d for d in duty if d.code not in _A11_TABLE_ROWS]
    return _A11_EXTRA_FIRST_ROW + len(extra) if extra else None


def _fill_new_prospect_a11(wb, duty, period):
    """Write a new prospect's duty counts on A1.1: the period's day counts (H6/L6/P6), CS's gross lookup (D7, blank in
    the template), the counts of codes with a template row, and a row per other qualifying code below the table."""
    if A11_SHEET not in wb.sheetnames:
        return
    a11 = wb[A11_SHEET]
    money_fmt = '#,##0'
    n = len(vn_holidays.paid_holidays_in_period(period.first_day, period.last_day))
    a11['H6'], a11['L6'], a11['P6'] = (period.last_day - period.first_day).days + 1 - n, n, n
    a1 = f"'{STAFF_COST_SHEET}'"
    a11['D7'] = f"=_xlfn.XLOOKUP(C7,{a1}!$D$15:$D$88,{a1}!$I$15:$I$88)"
    workdays = f'={period_workdays(period, 6)}/12'
    for d in duty:
        r = _A11_TABLE_ROWS.get(d.code)
        if r is None:
            continue
        found = str(a11.cell(row=r, column=3).value or '').strip()
        if found != d.code:
            raise ValueError(f"'{A11_SHEET}' row {r} is code {found!r}, not {d.code!r}.")
        a11.cell(row=r, column=7, value=d.night_normal or None)
        a11.cell(row=r, column=11, value=d.night_holiday or None)
        a11.cell(row=r, column=15, value=d.day_holiday or None)
    extra = [d for d in duty if d.code not in _A11_TABLE_ROWS]
    for i, d in enumerate(extra):
        r = _A11_EXTRA_FIRST_ROW + i
        # A1's code column reaches the unplaced rows below its table (row 98 on), so the lookup covers them too.
        look = lambda col: f"=_xlfn.XLOOKUP(C{r},{a1}!$D$15:$D$140,{a1}!${col}$15:${col}$140)"
        values = {1: len(_A11_TABLE_ROWS) + i + 1, 2: look('B'), 3: d.code, 4: look('I'), 5: workdays,
                  6: f'=IF(E{r}<26,D{r}/E{r},D{r}/26)',
                  7: d.night_normal or None, 8: f'=IF(G{r}>0,$H$6*G{r},0)', 9: '=$I$6', 10: f'=I{r}*H{r}*F{r}',
                  11: d.night_holiday or None, 12: f'=IF(K{r}>0,$L$6*K{r},0)', 13: '=$M$6', 14: f'=M{r}*L{r}*F{r}',
                  15: d.day_holiday or None, 16: f'=IF(O{r}>0,$P$6*O{r},0)', 17: '=$Q$6', 18: f'=Q{r}*P{r}*F{r}',
                  19: f'=R{r}+N{r}+J{r}', 20: f'=S{r}/$T$2',
                  21: 'Vị trí trực có ca đêm, không có dòng sẵn trong bảng trên: thêm dòng với cùng công thức.'}
        for col, v in values.items():
            c = a11.cell(row=r, column=col, value=v)
            if col in (4, 6, 10, 14, 18, 19, 20):
                c.number_format = money_fmt
    t = _new_prospect_a11_total_row(duty)
    if t is not None:
        a11.cell(row=t, column=2, value='Tổng EMH3/tháng (dòng 13 cộng các dòng trên)').font = Font(bold=True)
        a11.cell(row=t, column=20,
                 value=f'=S13+SUM(T{_A11_EXTRA_FIRST_ROW}:T{t - 1})').number_format = money_fmt


def _existing_detail_layout(result, layout):
    """Where design D15's carried / adjustment rows go, shared by the detail-sheet writer and the fund
    formulas: {'EMH2'|'EMH3'|'EMH4': [(row, item)], 'a1_last': last A1 row below the table or None,
    'a11_total' / 'a5_total': the total row or None}."""
    rows = existing_staffing.detail_rows(result)
    below = len(layout[1]) if layout else 0
    first = _A1_UNPLACED_FIRST_ROW + below
    out = {'EMH2': [(first + i, it) for i, it in enumerate(rows['EMH2'])],
           'EMH3': [(_A11_EXTRA_FIRST_ROW + i, it) for i, it in enumerate(rows['EMH3'])],
           'EMH4': [(_A5_EXTRA_FIRST_ROW + i, it) for i, it in enumerate(rows['EMH4'])]}
    n_a1 = below + len(rows['EMH2'])
    out['a1_last'] = _A1_UNPLACED_FIRST_ROW + n_a1 - 1 if n_a1 else None
    out['a11_total'] = _A11_EXTRA_FIRST_ROW + len(rows['EMH3']) if rows['EMH3'] else None
    out['a5_total'] = _A5_EXTRA_FIRST_ROW + len(rows['EMH4']) if rows['EMH4'] else None
    return out


def _rows_text(items):
    """"'label' (dòng r), 'label' (dòng r)" for a remark."""
    return ', '.join(f"'{it['label']}' (dòng {r})" for r, it in items)


def _write_existing_detail_rows(wb, result, layout):
    """Design D15 on the detail sheets: the carried / minimum-wage / PM-adjustment rows below A1, A1.1
    and A5, a total row on A1.1 and A5, zero cost on an A1 PM row without a person, and A5's default
    fire team set to zero when EMH4 is carried forward."""
    money_fmt = '#,##0'
    detail = _existing_detail_layout(result, layout)
    ws = wb[STAFF_COST_SHEET]
    placed = layout[0] if layout else {}
    # The template's PM-row accident insurance (X) costs 154,342 VND/month with no salary; an empty
    # row costs zero here, as in existing_staffing.a1_row_cost.
    for r in _a1_rows_by_group(ws).get('PM', []):
        if r not in placed:
            ws.cell(row=r, column=24, value=0)
    for r, it in detail['EMH2']:
        ws.cell(row=r, column=2, value=it['label'])
        ws.cell(row=r, column=29, value=it['annual'] / 12).number_format = money_fmt
        ws.cell(row=r, column=31, value=it['note'])

    if detail['EMH3']:
        a11 = wb[A11_SHEET]
        for r, it in detail['EMH3']:
            a11.cell(row=r, column=2, value=it['label'])
            a11.cell(row=r, column=19, value=it['annual']).number_format = money_fmt
            a11.cell(row=r, column=20, value=f'=S{r}/$T$2').number_format = money_fmt
            a11.cell(row=r, column=21, value=it['note'])
        t = detail['a11_total']
        a11.cell(row=t, column=2, value='Tổng EMH3/tháng (dòng 13 cộng các dòng trên)').font = Font(bold=True)
        a11.cell(row=t, column=20,
                 value=f'=S13+SUM(T{_A11_EXTRA_FIRST_ROW}:T{t - 1})').number_format = money_fmt

    if detail['EMH4']:
        a5 = wb[A5_SHEET]
        if result.lines['EMH4'].kind == 'carried':
            for r, label in _A5_TEAM_ROWS.items():
                found = unicodedata.normalize('NFC', str(a5.cell(row=r, column=2).value or '')).strip()
                if found != label:     # the template mixes NFC and NFD ('Thành viên')
                    raise ValueError(f"'{A5_SHEET}' row {r} is {a5.cell(row=r, column=2).value!r}, not {label!r}.")
                a5.cell(row=r, column=7, value=0)
        for r, it in detail['EMH4']:
            a5.cell(row=r, column=2, value=it['label'])
            a5.cell(row=r, column=8, value=it['annual']).number_format = money_fmt
            a5.cell(row=r, column=9, value=it['note'])
        t = detail['a5_total']
        a5.cell(row=t, column=2, value='Tổng EMH4/năm (dòng 8 cộng các dòng trên)').font = Font(bold=True)
        a5.cell(row=t, column=8, value=f'=H8+SUM(H{_A5_EXTRA_FIRST_ROW}:H{t - 1})').number_format = money_fmt


def _a1_chain_formulas(r):
    """A1's own per-row formula chain (columns I..AC), as on row 15, for a row written below the
    table. Shared by the New-prospect unplaced rows and Existing-project mode."""
    return {
        9:  f'=ROUND((G{r}*H{r})+G{r},0)',                                    # I Proposed Gross
        10: f'=I{r}',                                                         # J Proposed Total Gross
        11: f'=I{r}',                                                         # K Salary for insurance
        12: f'=IF(I{r}>$L$7,$L$7*$L$8,K{r}*$L$8)',                            # L Employee SI&HI 9.5%
        13: f'=IF(I{r}>$M$7,$M$7*$M$8,K{r}*$M$8)',                            # M Employee UI 1%
        14: f'=I{r}/$N$8',                                                    # N 13th month
        15: f'=IF(I{r}-L{r}-M{r}-$O$7>0,I{r}-L{r}-M{r}-$O$7,0)',              # O Taxable income
        16: (f'=IF(O{r}<=10000000,O{r}*5%,IF(O{r}<=30000000,O{r}*10%-500000,'
            f'IF(O{r}<=60000000,O{r}*20%-3500000,IF(O{r}<=100000000,O{r}*30%-9500000,'
            f'O{r}*35%-14500000))))'),                                        # P PIT
        17: f'=I{r}-L{r}-M{r}+N{r}-P{r}',                                     # Q Net pay
        18: f'=IF(AND(D{r}="PM",I{r}>0),1000000,IF(I{r}>0,300000,))',         # R Team building
        19: f'=I{r}*$S$8',                                                    # S Training 1.3%
        20: f'=IF(I{r}>$T$7,$T$7*$T$8,I{r}*$T$8)',                            # T Employer SI&HI 20.5%
        21: f'=IF(I{r}>$U$7,$U$7*$U$8,I{r}*$U$8)',                            # U Employer UI 1%
        22: f'=IF(I{r}>$V$7,$V$7*$V$8,I{r}*$V$8)',                            # V Trade Union 2%
        23: f'=IF(I{r}>0,$W$7/$W$8,)',                                        # W Annual checkup
        24: (f'=IF(D{r}="PM",(J{r}*30*0.099%+J{r}*3*0.44%+446985+2456000)*58%/12,'
            f'IF(J{r}=0,0,IF((J{r}*30*0.099%+J{r}*3*0.44%+446985)*40%/12<30000,30000,'
            f'(J{r}*30*0.099%+J{r}*3*0.44%+446985)*40%/12)))'),                # X Accident insurance
        26: f'=IF(I{r}>0,300000,)',                                           # Z Uniform (25=Y blank)
        27: f'=ROUND(I{r}+N{r}+R{r}+S{r}+T{r}+U{r}+V{r}+W{r}+X{r}+Y{r}+Z{r},0)',  # AA Total excl admin
        28: f'=ROUND(AA{r}*$AB$1,0)',                                         # AB Admin markup
        29: f'=AA{r}+AB{r}',                                                  # AC Total incl admin
    }


def fill_existing_staff_sheets(wb, result, layout):
    """Existing-project mode's writes to 'A1. Staff cost' and 'A1.1 Allowance' (design D10, D12, D14).
    A1's formula chain is not edited: only column G (gross), C (shift), AE (where the figure comes
    from), the rows below the table, and the hidden reference cells of the budget year."""
    ws = wb[STAFF_COST_SHEET]
    money_fmt = '#,##0'
    c = result.a1_cells
    ws['I4'] = c['I4']
    ws['I5'] = c['I5']
    for coord in ('L7', 'T7', 'V7'):
        ws[coord] = f"=$I$4*{int(c['si_hi_multiple'])}"
    for coord in ('M7', 'U7'):
        ws[coord] = f"=$I$5*{int(c['ui_multiple'])}"
    ws['T8'], ws['U8'], ws['V8'], ws['AB1'] = c['T8'], c['U8'], c['V8'], c['AB1']
    placed, below = layout
    for r, person in placed.items():
        g = ws.cell(row=r, column=7, value=person.gross)
        g.number_format = money_fmt
        ws.cell(row=r, column=3, value=person.shift or None)
        ws.cell(row=r, column=31, value=person.note)
    for i, person in enumerate(below):
        r = _A1_UNPLACED_FIRST_ROW + i
        ws.cell(row=r, column=2, value=_UNPLACED_POSITION_VI.get(person.label, person.label))
        ws.cell(row=r, column=3, value=person.shift or None)
        ws.cell(row=r, column=4, value=person.code)
        g = ws.cell(row=r, column=7, value=person.gross)
        g.number_format = money_fmt
        ws.cell(row=r, column=8, value=0)
        for col, formula in _a1_chain_formulas(r).items():
            cell = ws.cell(row=r, column=col, value=formula)
            cell.number_format = money_fmt
        ws.cell(row=r, column=31, value=person.note)
    if below:
        note = ws.cell(row=_A1_UNPLACED_FIRST_ROW - 1, column=2, value=(
            "Nhân sự vượt số dòng sẵn có của nhóm, hoặc vị trí không có nhóm dòng cố định trong mẫu "
            "chuẩn — định giá dưới đây bằng đúng công thức của bảng trên."))
        note.font = Font(italic=True, size=9, color='7F7F7F')
    elif result.kind == 'lump':
        note = ws.cell(row=_A1_UNPLACED_FIRST_ROW - 1, column=2, value=(
            f"Dự án đang quản lý, không có bảng nhân sự theo vị trí: EMH2 bằng các dòng dưới đây (số đã "
            f"duyệt NS {result.prior_year} mang sang), không tính lại theo lương từng người."))
        note.font = Font(italic=True, size=9, color='7F7F7F')
    _write_existing_detail_rows(wb, result, layout)

    if result.duty and A11_SHEET in wb.sheetnames:
        a11 = wb[A11_SHEET]
        rows = {str(a11.cell(row=r, column=3).value or '').strip(): r for r in range(7, 12)}
        a11['H6'], a11['L6'], a11['P6'] = result.a11_days
        for d in result.duty:
            r = rows[d.code]
            gross = a11.cell(row=r, column=4, value=d.gross)
            gross.number_format = money_fmt
            a11.cell(row=r, column=7, value=d.night_normal or None)
            a11.cell(row=r, column=11, value=d.night_holiday or None)
            a11.cell(row=r, column=15, value=d.day_holiday or None)


def _parking_allocation_weights(ws, recorded, moto_full_monthly, car_full_monthly):
    """BM11/BN11 on '2. Budget-Management Fund': the monthly vs casual parking split the 351 allocation rows divide by.
    Moved out of fill_management_fund_sheet() unchanged except for the nominal weight of a project with no parking
    revenue weight at all (change support-villa-only-and-no-parking, D5)."""
    # ---- Parking allocation weights (BM11/BN11) — change fix-parking-allocation-divide-by-zero.
    # 351 rows on this sheet carry '=IF(BK>0, BK*BM11/SUM(BM11:BN11), 0)'-shaped formulas (monthly
    # vs. casual/visitor parking split). Savills' template ships these two weight cells EMPTY, so
    # the denominator is 0 the moment any of those rows' own BK goes positive — dormant today only
    # because BK routes through '0. Info'!D12 (parking area), which this pipeline never fills; the
    # one exception is ERM (row 485), whose BK bypasses that guard, which is why it already failed
    # before this change (see design.md D1-D2 and this change's proposal.md for the full account).
    #
    # Monthly half: RP1+RP2, exactly what was just written above — no new derivation. Casual half:
    # checked the reference data first (task 2.1) — Costing_Method_Catalogue.csv's own RP5/RP6
    # entries require a "visitor volume assumption" nothing in this pipeline's real data supplies,
    # so there is no basis to write anything but 0. A 100/0 split is arithmetically defined and
    # honestly labelled; a guessed ratio would not be.
    #
    # Only written when both cells are genuinely empty — a project that already carries its own real
    # weights (however they got there) is never overwritten.
    _bm11, _bn11 = ws['BM11'], ws['BN11']
    if _bm11.value in (None, '') and _bn11.value in (None, ''):
        # P2 (design D4): a recorded monthly figure is the weight for its vehicle type. Only the ratio
        # matters (BN11 = 0, so the split stays 100/0); when both recorded figures are 0 the weight falls
        # back to bays x default rate so the divisor stays defined.
        _weight = sum(recorded[k] if recorded.get(k) is not None else full
                      for k, full in (('moto', moto_full_monthly), ('car', car_full_monthly)))
        _bm11.value = _weight or (moto_full_monthly + car_full_monthly)
        _bn11.value = 0
        _nominal = not _bm11.value
        if _nominal:
            # No parking bays and no recorded parking revenue (D5): nothing to split, so every allocation
            # row's BK is 0; a nominal 1 keeps SUM(BM11:BN11) defined.
            _bm11.value = 1
        _bm11.comment = Comment(
            ("Nominal monthly-parking allocation weight (1): this project has no parking bays and no "
             "recorded parking revenue, so there is no parking cost to split; the 1 only keeps the 351 "
             "allocation formulas defined. " if _nominal else
             "Monthly-parking allocation weight — RP1 (motorbike) + RP2 (car) monthly parking revenue, "
             "the same figures written above. ") +
            "Casual/visitor weight (BN11) is 0: no real basis exists "
            "for that split (Costing_Method_Catalogue.csv's RP5/RP6 require a 'visitor volume "
            "assumption' this pipeline has no data for) — 100% of the allocation therefore goes to "
            "monthly parking, not a guessed ratio. Written only because these cells were empty; a "
            "project's own real weights, if entered, are never overwritten.",
            'Budget Planning Agent')
    # Fail loudly rather than ship a workbook whose 351 allocation rows silently depend on whichever
    # ones happened to be written this run (design.md D2) — this is the same class of guard as
    # assert_row_code() elsewhere in this file, just for a template defect instead of a row-position
    # drift.
    if (_bm11.value or 0) + (_bn11.value or 0) == 0:
        raise ValueError(
            "'2. Budget-Management Fund'!BM11:BN11 (parking allocation weights) sum to zero. 351 rows "
            "on this sheet divide by this sum whenever their own BK is positive — an undefined "
            "denominator would reach the client the moment any of those rows fires. Refusing to "
            "produce a deliverable rather than risk a #DIV/0! that depends on which cost rows this "
            "particular run happened to write. See openspec/changes/fix-parking-allocation-divide-by-"
            "zero for the full account."
        )


def fill_management_fund_sheet(wb, project, demand, year, rates, existing=None, existing_layout=None):
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
    the Year-1 (full lump) value. Both choices confirmed with the PM (2026-08-21).

    `rates` is build_budget()'s master_comparables.resolve_product_rates() result: the RM.* rows
    are priced at exactly those rates, never re-derived here (change use-operating-project-actuals, P5)."""
    ws = wb['2. Budget-Management Fund']

    # Check every hardcoded leaf position against its own cost code before writing anything.
    _assert_leaf_rows(ws, '2. Budget-Management Fund', MGMT_FUND_ROWS, MGMT_FUND_EXPECTED_CODE)
    _assert_leaf_rows(ws, '2. Budget-Management Fund', PRODUCT_REVENUE_ROWS, PRODUCT_REVENUE_EXPECTED_CODE)

    def assert_row_code(key, expected_code):
        """Stop rather than write to whatever row happens to sit at a hardcoded position.

        Every row in MGMT_FUND_ROWS is a fixed template position. If Savills reshapes the sheet,
        those positions move and the pipeline would silently fill the wrong cost lines — the same
        failure class that made read_input() go label-based. The sheet carries each row's own cost
        code in column Y, so the position can be checked against it before anything is written.

        Applied to the two rows this change adds. The other twenty are unverified: each needs its
        code read off the real template and confirmed one at a time, which is its own task.
        """
        row = MGMT_FUND_ROWS[key]
        found = ws.cell(row=row, column=_CODE_COL).value
        found = found.strip() if isinstance(found, str) else found
        if found != expected_code:
            raise ValueError(
                f"'2. Budget-Management Fund' row {row} was expected to be cost code "
                f"{expected_code!r} ('{key}') but carries {found!r}. The template's row layout has "
                f"changed, so writing here would put this figure on the wrong cost line. Re-verify "
                f"MGMT_FUND_ROWS against the current template rather than adjusting this check."
            )

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
        PARKING_FEE_CAR_MONTHLY, PARKING_FEE_MOTO_MONTHLY, SERVICE_SHIFT_ROLES_PER_POST,
    )
    from master_comparables import (
        SECURITY_RATE_CITYWIDE, CLEANING_RATE_CITYWIDE, LANDSCAPE_RATE_CITYWIDE,
    )
    SERVICE_CITYWIDE_RATES = {'Security': SECURITY_RATE_CITYWIDE,
                              'Cleaning': CLEANING_RATE_CITYWIDE,
                              'Landscape': LANDSCAPE_RATE_CITYWIDE}

    def position_bare_annual_cost(d):
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
        # Returns the BARE cost — headcount x rate x coverage, night differential applied, no
        # employer contribution. Callers choose the basis they need; see position_annual_cost().
        return total

    def position_annual_cost_outsourced(d):
        """Outsourced cost: the bare cost, with no employer contribution added.

        Security, cleaning and landscape are vendor contracts (ES = Expenses for Outsource Service
        in the template), and their daily rates already come from Fact_MasterRateCard.csv's SERVICE
        domain — a vendor post price, which by construction already covers that vendor's own staff
        insurance. Adding an employer contribution on top would charge it twice.

        Evidence these roles are not Savills payroll: Dim_Position.csv has 408 positions across
        ME/GEN/CS/MGT/AMN/ACC/ADM with no security, cleaning or landscape department; the 12,897
        salary rows in Fact_StaffCost.csv contain none of them; and the rate card has no
        Staff-domain rate for any of the three. See openspec change
        fix-outsourced-service-cost-basis, and docs/05-decisions.md D3.
        """
        return position_bare_annual_cost(d)

    per_position_outsourced = {d['Position']: position_annual_cost_outsourced(d) for d in demand}

    # ---- ESS1 / ESS4 / ESS16 priced the way EXENSIVE LOGIC.xlsx says to price them ----
    # The spec's methods are:
    #   ESS1  Security  : "Monthly contract fee x 12 OR (Headcount x Cost per guard x 12)"
    #   ESS4  Cleaning  : "m2 x Unit price x 12 OR Monthly contract x 12"
    #   ESS16 Landscape : "Monthly contract x 12"
    # Only ESS1 sanctions a headcount basis, which is what all three used before 2026-09-08.
    #
    # The m2 branch for ESS4 CANNOT be implemented: Fact_MasterRateCard.csv has no per-m2 cleaning
    # rate anywhere — every Service-domain row is priced VND/position/month. So all three use the
    # "monthly contract x 12" branch, where a vendor contract is what it actually is in practice:
    # a number of posts at a post price. That is exactly what the Service sheet computes in its
    # column H, so the deliverable and the analysis now agree by construction.
    #
    # TRADE-OFF, stated because it is real: the post rates are citywide and n=1 (A&K Tower), so
    # this is less project-specific than the roster basis it replaces — the roster differentiated a
    # cleaning supervisor from a line cleaner, this does not. It is more faithful to the written
    # method and less granular. Widening those rates is R-D02, separate work.
    def contract_cost(cat):
        keywords = SERVICE_CATEGORY_KEYWORDS[cat]
        matched = [d for d in demand if any(kw in d['Position'].lower() for kw in keywords)
                   and not any(ex in d['Position'].lower() for ex in SERVICE_EXCLUDE_KEYWORDS)]
        qty = sum(math.ceil(d['StaffPerDay'] * 7 / 6) if d['CoverageDays'] >= 7 else d['StaffPerDay']
                  for d in matched)
        if not qty:
            _record_contract_posts(cat, demand, matched, SERVICE_CITYWIDE_RATES[cat],
                                   SERVICE_SHIFT_ROLES_PER_POST[cat], 1.0, 0)
            return 0.0, 0, 1.0
        night_qty = sum(math.ceil(d['StaffPerDay'] * 7 / 6) if d['CoverageDays'] >= 7 else d['StaffPerDay']
                        for d in matched if d['ShiftCode'] in NIGHT_SHIFT_CODES)
        # Rounded to 4dp because the Service sheet writes the blend into a cell at that precision
        # and multiplies by the rounded value. Using the exact one here would leave the two
        # workbooks differing by tens of thousands of VND on Security.
        blend = round(1 + (night_qty / qty) * (NIGHT_DIFFERENTIAL - 1), 4)
        post_rate = SERVICE_CITYWIDE_RATES[cat]
        roles = SERVICE_SHIFT_ROLES_PER_POST[cat]
        _record_contract_posts(cat, demand, matched, post_rate, roles, blend, qty)
        return (post_rate / roles) * blend * qty * 12, qty, blend

    security_cost, n_sec_posts, sec_blend = contract_cost('Security')
    cleaning_cost, n_cln_posts, cln_blend = contract_cost('Cleaning')
    landscape_cost, n_lsc_posts, lsc_blend = contract_cost('Landscape')

    _CONTRACT_BASIS = (
        "Phương pháp: hợp đồng hàng tháng x 12, trong đó hợp đồng được tính theo số vị trí x đơn giá "
        "vị trí theo mặt bằng chung thành phố (chỉ một dự án tham chiếu). KHÔNG cộng thêm bảo hiểm người sử "
        "dụng lao động: đơn giá vị trí của nhà thầu đã bao gồm chi phí nhân sự của chính nhà thầu.")
    write_even_monthly('security', security_cost, remark=(
        f"= {SERVICE_CITYWIDE_RATES['Security']:,.0f} VND/vị trí/tháng / {SERVICE_SHIFT_ROLES_PER_POST['Security']} "
        f"vai trò ca x hệ số ca đêm {sec_blend:.4f} x {n_sec_posts} vị trí x 12 = "
        f"{security_cost:,.0f} VND/năm. {_CONTRACT_BASIS}"))
    write_even_monthly('cleaning', cleaning_cost, remark=(
        f"= {SERVICE_CITYWIDE_RATES['Cleaning']:,.0f} VND/vị trí/tháng / {SERVICE_SHIFT_ROLES_PER_POST['Cleaning']} "
        f"vai trò ca x hệ số {cln_blend:.4f} x {n_cln_posts} vị trí x 12 = {cleaning_cost:,.0f} VND/năm. "
        f"{_CONTRACT_BASIS} Phương án thay thế của tiêu chuẩn ('m² x đơn giá') không được sử dụng vì "
        f"không có đơn giá vệ sinh theo m² trong dữ liệu nguồn."))
    write_even_monthly('landscape', landscape_cost, remark=(
        f"= {SERVICE_CITYWIDE_RATES['Landscape']:,.0f} VND/vị trí/tháng / {SERVICE_SHIFT_ROLES_PER_POST['Landscape']} "
        f"vai trò ca x hệ số {lsc_blend:.4f} x {n_lsc_posts} vị trí x 12 = {landscape_cost:,.0f} VND/năm. "
        f"{_CONTRACT_BASIS} (Có điều kiện — bằng 0 và để trống nếu dự án không có diện tích sân vườn.)"))
    # ---- EMH2 "Staff cost for Savills" — driven ENTIRELY from the deliverable's own real payroll
    # calculator, 'A1. Staff cost 08.2026 (VN)', instead of the old Python headcount x rate x
    # EMPLOYER_INSURANCE_RATE shortcut (docs/09-template-map.md §9 finding 2; change
    # reconcile-summary-with-detail-sheets, design D2). fill_staff_cost_sheet() has already placed
    # every in-house position it recognises onto A1's own predefined row-groups, AND given any
    # position with no row-group there (today: Reception — it otherwise only appears on
    # 'B1. Lịch Lễ tân', a duty roster with no payroll math) a REAL row of its own starting at
    # _A1_UNPLACED_FIRST_ROW, using A1's own exact formula chain (not a Python replica) — so its
    # cost is a live, auditable, editable Excel calculation, not a number hidden inside this
    # formula string. This cell only needs to know how many such rows exist, to size the SUM range.
    # The block below A1's table also holds every group's heads beyond its template rows (D7), so the SUM range spans
    # every row fill_staff_cost_sheet() writes there — one per head, never one per position name.
    _a1_ws = wb[STAFF_COST_SHEET]
    _a1_groups = _a1_rows_by_group(_a1_ws)
    below_rows = _new_prospect_below_rows(demand, _period_of(project), _a1_groups, _a1_group_labels(_a1_ws, _a1_groups))
    top_up_names = list(dict.fromkeys(re.sub(r' \(thêm \d+\)$', '', label) for label, _c, _g in below_rows))
    total_unplaced_rows = len(below_rows)

    assert_row_code('staff_remainder', 'EMH2')
    emh2_row = MGMT_FUND_ROWS['staff_remainder']
    ws.cell(row=emh2_row, column=3, value='Monthly')                    # C — Frequency
    a1_ref = "'A1. Staff cost 08.2026 (VN)'"
    # A1's total (AC96) already holds A1.1's allowance (AC90 = A1.1!S13, for AC95 months); EMH3 carries that allowance,
    # so EMH2 leaves it out, in Existing mode's form (change apply-head-of-pm-decisions-2026-10, D5).
    a1_base = f"{a1_ref}!AC96-{a1_ref}!AC90*{a1_ref}!AC95"
    if total_unplaced_rows:
        last_unplaced_row = _A1_UNPLACED_FIRST_ROW + total_unplaced_rows - 1
        unplaced_range = (f"{a1_ref}!AC{_A1_UNPLACED_FIRST_ROW}"
                          if total_unplaced_rows == 1 else
                          f"SUM({a1_ref}!AC{_A1_UNPLACED_FIRST_ROW}:AC{last_unplaced_row})")
        emh2_formula = f"=({a1_base}+{unplaced_range}*12)/12"
    else:
        emh2_formula = f"=({a1_base})/12"
    f_cell = ws.cell(row=emh2_row, column=6, value=emh2_formula)        # F — Unit Price (formula)
    f_cell.number_format = _NUM_FMT
    for col in range(8, 20):                                            # H:S — same formula, shown
        c = ws.cell(row=emh2_row, column=col, value=emh2_formula)       # every month for transparency
        c.number_format = _NUM_FMT
    _write_remark(ws, emh2_row, (
        f"= 'A1. Staff cost 08.2026 (VN)'!AC96 trừ phụ cấp ca đêm/ngày lễ (AC90 x AC95, tính riêng ở EMH3) "
        f"— tổng quỹ lương thực tế cả năm của chính trang này, "
        f"cho mọi vị trí theo đúng nhóm dòng đã định sẵn (lương tháng 13, BHXH/BHYT người sử dụng "
        f"lao động 20,5% và Bảo hiểm thất nghiệp 1% đã tính trần, Kinh phí công đoàn 2%, các khoản "
        f"phụ cấp riêng của từng vị trí, toàn bộ chi phí người sử dụng lao động cộng thêm "
        f"10% phí quản lý của Savills)"
        + (f" + dòng {_A1_UNPLACED_FIRST_ROW}"
           + (f"-{last_unplaced_row}" if total_unplaced_rows > 1 else '')
           + f" của CÙNG trang này ({', '.join(top_up_names)}, {total_unplaced_rows} người) — các vị "
             f"trí mà bố cục chuẩn của A1 không có sẵn nhóm dòng, được định giá tại đó bằng công thức "
             f"sống GIỐNG HỆT mọi dòng khác ở trên."
           if total_unplaced_rows else
           ". Mọi vị trí nội bộ đều đã có nhóm dòng trên A1 — không còn vị trí nào cần thêm.") +
        f" Bảo vệ/Vệ sinh/Cây xanh vẫn không tính vào đây — đó là các hợp đồng thuê ngoài được định "
        f"giá riêng ở trên (ESS1/ESS4/ESS16)."))

    # ---- Management fee revenue, priced PER PRODUCT ----
    # Every product the project reports area for gets its own rate and its own template row. The
    # rates come from `rates` — master_comparables.resolve_product_rates(), called once by
    # build_budget() and also by generate_project_output.py's Management Fee sheet — so the two
    # workbooks agree by construction (change use-operating-project-actuals, P5: before it this
    # function derived the Apartment rate a second time and every other product's rate a third).
    # Before 2026-09-08 only Apartment was priced here, which understated the deliverable's revenue
    # against the analysis by 1,930,800,000 VND (14.8%) — finding X-01.
    apt_rate = rates['apartment_rate']
    # Occupancy ramp (change `ramp-occupancy-scaled-lines`, catalogue: these codes are
    # occupancy_scaled). A new building opens the year part-empty, so collected management fee rises
    # month by month with the resident fill-up curve (fill_curve.year1_fills — 0% -> 50% over year 1,
    # the same curve the internal analysis uses). RM.0A below is the mirror: the developer pays the
    # fee on units not yet handed over, so collected + developer = the full fee every month.
    stable = bool(project.get('stable_operation'))
    fills = year1_fills(stable)
    # Vietnamese, matching '1. Summary'!K's own composed-narrative wording conventions (change
    # localize-line-level-remarks, 2026-09-15 — was English; see design.md D1 for the pattern this
    # follows). {pct} is pre-formatted (e.g. "50%") so the same note serves both the product-revenue
    # loop (FILL_ANCHORS[1][1]) and, unchanged, any future caller that passes a different anchor.
    def _anchor_note_vi(pct):
        return (f"Phân bổ theo 12 tháng theo đường cong lấp đầy cư dân tại trang 'Tỷ lệ lấp đầy cư "
                f"dân' — một giả định đã công bố (0% khi bàn giao, tăng tuyến tính đến {pct:.0%} vào "
                f"cuối năm vận hành thứ nhất), không phải số liệu thực tế riêng của dự án này. Giả "
                f"định ngân sách này tính cho các tháng vận hành 1-12.")
    _anchor_note = (operating_inputs.STABLE_NOTE_VI if stable    # 'Stable Operation?' = Yes
                    else _anchor_note_vi(FILL_ANCHORS[1][1]))
    mgmt_fee_annual = 0.0        # full-occupancy annual — drives EMH1's %; unchanged by the ramp
    total_full_monthly = 0.0     # sum of (rate x NFA) over products — the base for RM.0A
    for product, row in PRODUCT_REVENUE_ROWS.items():
        nfa = (project['products'].get(product) or {}).get('nfa')
        if not nfa:
            continue                      # no area for this product — leave the row blank, not 0
        # Apartment's rate carries the swing cap; the others are uncapped or fall back to it — all
        # decided in the resolver (the 2026-09-16 RM.AP bug was this loop re-deriving it uncapped).
        _p_rate = rates['products'][product]
        rate, used, is_fallback = _p_rate['rate'], _p_rate['used'], _p_rate['is_fallback']
        _UNIT_RATES[PRODUCT_REVENUE_EXPECTED_CODE[product]] = rate
        full_monthly = rate * nfa
        annual = full_monthly * 12
        mgmt_fee_annual += annual
        total_full_monthly += full_monthly
        product_vi = _PRODUCT_VI_LABEL.get(product, product)
        if _p_rate['source'] == 'entered':
            # P1: the PM's actual rate, applied as entered (PM-1: a different VAT basis is disclosed, not
            # converted); no comparable is named as its source.
            _ENTERED_RATE_VAT[PRODUCT_REVENUE_EXPECTED_CODE[product]] = _p_rate['vat']
            _mismatch = operating_inputs.vat_mismatch_vi(_p_rate['vat'])
            _write_ramped_row(ws, row, [full_monthly * f for f in fills], (
                operating_inputs.entered_rate_remark_vi(product_vi, rate, _p_rate['vat'], nfa,
                                                        full_monthly, annual)
                + f" {_anchor_note}" + (f" {_mismatch}" if _mismatch else '')
                + f" {operating_inputs.entered_rate_year_vi(_budget_year(ws.parent))}"))
            continue
        _apt_entered = (operating_inputs.FALLBACK_ENTERED_APARTMENT_VI
                        if rates.get('apartment_entered') else '')
        # The client deliverable names no other project (decision D3); the analysis lists them (change
        # apply-head-of-pm-decisions-2026-10, D13).
        basis = (f"Nguồn đơn giá: {len(used)} dự án tham chiếu thực tế."
                 if used else
                 f"DỰ PHÒNG — không có dự án tham chiếu nào trong danh sách chính có đơn giá thực tế "
                 f"cho {product_vi}, nên đơn giá Apartment của dự án này{_apt_entered} được dùng thay thế. Đây "
                 f"KHÔNG phải đơn giá riêng cho {product_vi}.")
        _write_ramped_row(ws, row, [full_monthly * f for f in fills], (
            f"= Đơn giá {product_vi} ({rate:,.0f} VND/m²/tháng) x Diện tích tính phí {product_vi} "
            f"({nfa:,.0f} m²) = {full_monthly:,.0f} VND/tháng khi lấp đầy 100% ({annual:,.0f} "
            f"VND/năm). {_anchor_note} {basis}"))
    if not mgmt_fee_annual:
        raise ValueError('No product has any chargeable area — nothing to price.')

    # RM.0A — the developer's management fee on units not yet handed over. Mirror of the curve:
    # (full monthly fee for ALL units) x (1 - fill) each month, so RM + RM.0A = the full fee monthly.
    # At stable operation no unit awaits handover, so the developer pays nothing in any month, whatever
    # the stable fill is (fill_curve.STABLE_FILL).
    developer_monthly = ([0.0] * 12 if stable else
                         [total_full_monthly * (1 - f) for f in fills])
    assert_row_code('mgmt_fee_developer', 'RM.0A')
    _write_ramped_row(ws, MGMT_FUND_ROWS['mgmt_fee_developer'], developer_monthly,
                      operating_inputs.RM0A_STABLE_VI if stable else (
        f"= Tổng phí quản lý đầy đủ cho toàn bộ căn ({total_full_monthly:,.0f} VND/tháng) x (100% - "
        f"tỷ lệ lấp đầy%) mỗi tháng — chủ đầu tư chi trả phần phí cho các căn chưa bàn giao. Giảm về "
        f"0 khi tòa nhà lấp đầy dần. {_anchor_note} "
        f"Tổng năm 1: {sum(developer_monthly):,.0f} VND; RM + RM.0A mỗi tháng = tổng phí đầy đủ."))
    # EMH1 (Savills' own fee) is NOT the collected management fee — that's the fund's REVENUE, most
    # of which is meant to pay for the real staff/OPEX/Capex costs already itemized elsewhere on
    # this sheet. Before 2026-08-28 this wrongly set EMH1 = mgmt_fee_annual (the entire collected
    # fee), which double-counted against every other cost line and produced a large fake "deficit"
    # (confirmed on Blue Skyline: 6.3bn of a ~7.5bn gap against the real Green Skyline back-test was
    # this one bug). The correct value is a real, negotiated, per-project contract term this
    # pipeline cannot derive — see the Project Info fields savills_fee.FIXED_LABEL / PCT_LABEL.
    # Left BLANK, not defaulted to 0 or to the old wrong assumption, until the PM enters one.
    # Group 7 (design D9c): the fixed fee is entered excl. VAT and gets each budget month's VAT (B1-a); the % fee
    # is a share of the full fee at 100% occupancy (RM + RM.0A), which already includes VAT, so none is added.
    _fee_basis = savills_fee.basis(project)
    if _fee_basis:
        if _fee_basis == savills_fee.FIXED:
            _fee_bp = project.get('budget_period') or budget_period.default()
            _fee_vat_text = (f"cộng VAT {_rate_phrase(_fee_bp.months, _general_vat_months(project))} theo từng tháng"
                             if _ACTIVE_VAT_SENTENCE else "chưa cộng VAT theo mô hình tài chính đã chọn")
            _fee_months, _fee_remark = savills_fee.fixed_line(project['savills_fee_fixed_monthly'],
                                                               _vat_factors(project), _fee_vat_text)
        else:
            _fee_months, _fee_remark = savills_fee.percent_line(project['savills_fee_pct'], mgmt_fee_annual)
        if len(set(_fee_months)) == 1:
            write_even_monthly('mgmt_fee_expense', _fee_months[0] * 12, remark=_fee_remark)
        else:
            _write_ramped_row(ws, MGMT_FUND_ROWS['mgmt_fee_expense'], _fee_months, _fee_remark)
    # else: left blank — no real contract term entered yet (both fields empty).

    # ---- Monthly parking revenue (RP1 motorbike, RP2 car — the template subtotals these into RPa).
    # Occupancy-scaled (catalogue): bays x monthly rate x parking fill %(month). Parking fill tracks
    # the resident curve, ~2x faster where bays < units. There is no developer top-up for parking, so
    # unlike RM this genuinely drops in year 1. ----
    units_for_parking = project.get('apartment_units') or 0
    moto_slots = project.get('moto_slots') or 0
    car_slots = project.get('car_slots') or 0
    moto_full_monthly = PARKING_FEE_MOTO_MONTHLY * moto_slots
    car_full_monthly = PARKING_FEE_CAR_MONTHLY * car_slots
    _UNIT_RATES['RP1'] = PARKING_FEE_MOTO_MONTHLY
    _UNIT_RATES['RP2'] = PARKING_FEE_CAR_MONTHLY
    moto_fills = parking_fills(moto_slots, units_for_parking, stable)
    car_fills = parking_fills(car_slots, units_for_parking, stable)

    def _parking_note(slots, units, ramp_faster):
        if stable:
            return operating_inputs.PARKING_STABLE_VI
        base = ("phân bổ theo đường cong lấp đầy bãi xe tại trang 'Tiến độ lấp đầy bãi xe' (bám "
                "theo đường cong cư dân, 0% -> khoảng 50% trong năm vận hành thứ nhất)")
        return base + (" — nhanh gấp khoảng 2 lần tốc độ lấp đầy cư dân do số chỗ đậu ít hơn số căn hộ"
                       if ramp_faster else "") + "."
    # "= X VND/tháng khi lấp đầy 100%. <curve>" for a new building; "= X VND/tháng, tính lấp đầy bãi xe
    # 100% ..." at stable operation (approved wording, design.md W1).
    _full_clause = "," if stable else " khi lấp đầy 100%."
    # P2 (use-operating-project-actuals): a recorded monthly figure, entered by the PM for a project at
    # stable operation, replaces bays x default rate x fill for that vehicle type, flat over 12 months.
    # _UNIT_RATES then holds the monthly figure, so the RPa narrative quotes it, not a per-bay rate.
    _recorded = ((project.get('operating') or {}).get('parking')) or {}
    _HELPER_FIGURES['parking'] = {
        'moto': dict(rate=PARKING_FEE_MOTO_MONTHLY, slots=moto_slots, recorded=_recorded.get('moto')),
        'car': dict(rate=PARKING_FEE_CAR_MONTHLY, slots=car_slots, recorded=_recorded.get('car'))}
    for _key, _code, _vehicle in (('moto', 'RP1', 'parking_moto'), ('car', 'RP2', 'parking_car')):
        if _recorded.get(_key) is not None:
            _UNIT_RATES[_code] = _recorded[_key]
            _write_ramped_row(ws, MGMT_FUND_ROWS[_vehicle], [_recorded[_key]] * 12,
                              operating_inputs.parking_recorded_remark_vi(_key, _recorded[_key]))

    if _recorded.get('moto') is None:
        _write_ramped_row(ws, MGMT_FUND_ROWS['parking_moto'], [moto_full_monthly * f for f in moto_fills], (
            f"= {PARKING_FEE_MOTO_MONTHLY:,.0f} VND/tháng (đơn giá thực tế, theo đề xuất giữ xe của một dự án "
            f"tham chiếu) x {moto_slots:,.0f} chỗ xe máy (theo Project Info) = {moto_full_monthly:,.0f} "
            f"VND/tháng{_full_clause} {_parking_note(moto_slots, units_for_parking, bool(moto_slots and units_for_parking and moto_slots < units_for_parking))} "
            f"Tổng năm 1: {sum(moto_full_monthly * f for f in moto_fills):,.0f} VND."))
    if _recorded.get('car') is None:
        _write_ramped_row(ws, MGMT_FUND_ROWS['parking_car'], [car_full_monthly * f for f in car_fills], (
            f"= {PARKING_FEE_CAR_MONTHLY:,.0f} VND/tháng (đơn giá thực tế, theo đề xuất giữ xe của một dự án "
            f"tham chiếu) x {car_slots:,.0f} chỗ ô tô (theo Project Info) = {car_full_monthly:,.0f} VND/tháng"
            f"{_full_clause} {_parking_note(car_slots, units_for_parking, bool(car_slots and units_for_parking and car_slots < units_for_parking))} "
            f"Tổng năm 1: {sum(car_full_monthly * f for f in car_fills):,.0f} VND."))

    _parking_allocation_weights(ws, _recorded, moto_full_monthly, car_full_monthly)

    # ---- Per-row area-basis reference (BG<row>/BH<row>) — scope expanded into this same change
    # (2026-09-17) after proving the BM11/BN11 fix on the actual triggering state (a non-zero parking
    # area) and finding 6 rows STILL producing #DIV/0!, through a different mechanism than BM11/BN11.
    #
    # Every one of the 356 rows carrying the BM/BN allocation formula also has its own BG<row>/BH<row>
    # cells, and every one of them — 350 out of 356 — is a formula reading the SAME shared reference
    # cells: '=$BG$10' / '=$BH$10' (confirmed by direct inspection, not assumed: RM.AP/RM.OT/.../RM.KG
    # and 340+ others all carry exactly this). BK<row> (and BJ<row>) divide by
    # SUM($BG<row>:$BH<row>), so a row missing this reference divides by zero the moment its own AL
    # (cost basis) is positive — independent of whether BM11/BN11 above are populated.
    #
    # 6 rows are missing it: EMH1/EMH2/EMH3 (Savills management-fee-family codes), VAT, CIT1a/CIT1b
    # (tax codes), and ERM (row 485) — the row that originally motivated this whole change. ERM's own
    # BK reads a different cell directly and does not depend on BG/BH (proposal.md's own finding), so
    # it was not erroring from THIS cause — but it is still missing the same reference every sibling
    # row carries, which is corrected here for the same reason the others are: consistency with the
    # template's own established pattern, not just chasing today's visible symptom.
    #
    # Detected dynamically (scan for either of the two real signals a row belongs to this family,
    # not a hardcoded row list) so this does not silently stop working if a future template revision
    # shifts rows — same reasoning as the BM11/BN11 guard just above.
    #
    # Two signals, needed together — found only by testing the actual triggering state end-to-end
    # and following each still-erroring cell to its real cause, not by reasoning about the template
    # in the abstract:
    #   (a) BM or BN references the shared $BM$11/$BN$11 weight (the normal, direct-formula shape
    #       350 of 356 rows already have) — catches ERM (row 485) too: its own BJ/BK read a
    #       different cell and never divide by BG/BH at all (proposal.md's own finding, and why it
    #       was the one row that already failed before this change), but its BM/BN still follow this
    #       shape, and leaving its BG/BH blank when every one of its 355 siblings has the real
    #       reference is the same inconsistency this fix corrects everywhere else.
    #   (b) BJ or BK itself divides by SUM($BG<row>:$BH<row>) — catches VAT (row 498), whose BM/BN
    #       are SUBTOTAL() rollups of child rows rather than the direct formula, so signal (a) alone
    #       misses it even though its own BJ/BK have the exact same defect as the other 5.
    def _row_needs_bg_bh_reference(_r):
        _bm = ws.cell(row=_r, column=65).value  # BM
        _bn = ws.cell(row=_r, column=66).value  # BN
        _bj = ws.cell(row=_r, column=62).value  # BJ
        _bk = ws.cell(row=_r, column=63).value  # BK
        _refs_shared_weight = any(
            isinstance(_f, str) and ('$BM$11' in _f.replace(' ', '') or '$BN$11' in _f.replace(' ', ''))
            for _f in (_bm, _bn)
        )
        _divides_by_bg_bh = any(
            isinstance(_f, str) and 'SUM($BG' in _f.replace(' ', '') for _f in (_bj, _bk)
        )
        return _refs_shared_weight or _divides_by_bg_bh

    _bg_bh_fixed_rows = []
    for _r in range(11, ws.max_row + 1):
        if not _row_needs_bg_bh_reference(_r):
            continue
        _bg_cell, _bh_cell = ws.cell(row=_r, column=59), ws.cell(row=_r, column=60)  # BG, BH
        if _bg_cell.value in (None, '') and _bh_cell.value in (None, ''):
            _bg_cell.value = '=$BG$10'
            _bh_cell.value = '=$BH$10'
            _bg_bh_fixed_rows.append(_r)
    if _bg_bh_fixed_rows:
        _bg_cell_first = ws.cell(row=_bg_bh_fixed_rows[0], column=59)
        _bg_cell_first.comment = Comment(
            f"Area-basis reference — restored to match the same formula every sibling row on this "
            f"sheet already carries ('=$BG$10'/'=$BH$10'), missing on this row (and "
            f"{len(_bg_bh_fixed_rows) - 1} other row(s): {_bg_bh_fixed_rows[1:]}) in Savills' own "
            f"template. Without it, this row's BJ/BK divide by an empty SUM the moment its own cost "
            f"basis (AL{_bg_bh_fixed_rows[0]}) is positive. See "
            f"openspec/changes/fix-parking-allocation-divide-by-zero for the full account.",
            'Budget Planning Agent')
    # Same "impossible to ship a landmine" guard as BM11/BN11 above, for this second pattern: fail
    # rather than emit a workbook where any of the 356 rows still has both cells blank — whether from
    # a template row this scan did not anticipate, or the write above somehow not landing.
    _still_missing = [
        _r for _r in range(11, ws.max_row + 1)
        if _row_needs_bg_bh_reference(_r)
        and ws.cell(row=_r, column=59).value in (None, '')
        and ws.cell(row=_r, column=60).value in (None, '')
    ]
    if _still_missing:
        raise ValueError(
            f"'2. Budget-Management Fund' rows {_still_missing} still have both BG and BH blank after "
            f"the area-basis-reference fix — their own BJ/BK would divide by zero the moment their "
            f"cost basis is positive. Refusing to produce a deliverable. See "
            f"openspec/changes/fix-parking-allocation-divide-by-zero for the full account."
        )

    # ---- Repair a fund leaf row whose AK/AQ:BB formulas were corrupted to read a different row's
    # cells instead of its own. Found on ERM (row 485, code 'ERM'): every one of the 27 rows this
    # pipeline writes to has AK<row> = SUM(AQ<row>:BB<row>), deriving from itself — row 485 alone had
    # AK485 = SUBTOTAL(9,AK486), reading row 486 (code 'ERM1'), a separate leaf the pipeline never
    # otherwise writes. '1. Summary' reads AK, not G, so this understated ERM there even though G485
    # (this sheet's own total) was correct — caught by change reconcile-summary-with-detail-sheets's
    # own check_summary_reconciles, which compares every leaf's G against its AK, headers included.
    #
    # First attempt populated row 486 instead (reasoning: G263's own SUBTOTAL range stops at 485
    # while AK263's reaches 486, so maybe the template meant 486 to hold ERM's AK-side detail).
    # Empirically wrong: G79 (the wider "(E)" rollup, range 80:494) already spans BOTH 485 and 486,
    # so populating 486 made it a second genuine leaf there too — turning AK79's prior deficit into
    # an equal-and-opposite G79 excess, never net-zero. Reverted (see
    # openspec/changes/fix-parking-allocation-divide-by-zero design.md, "Amendment (2026-09-17,
    # part 2)").
    #
    # Row 486 itself still carries a fully intact, byte-for-byte-normal AK/AQ:BB formula set
    # (confirmed by direct comparison against row 484, a genuine sibling leaf) — it has simply never
    # been written to, which is what makes it read as an unused row the template author never
    # intended to carry independent data. That, plus row 485's AK/AQ:BB uniquely pointing away from
    # itself, reads as a template row-insert artifact rather than a two-row design. The repair
    # restores row 485's own formulas using row 486's intact text — the same "populate with the
    # template's own established formula, not an invented substitute" principle as the BG/BH fix
    # just above, applied to a formula cell instead of a blank one. Detected dynamically (any leaf
    # row — G formula not itself a SUBTOTAL — whose AK is a SUBTOTAL of a different row) rather than
    # hardcoded to row 485, for the same reason as every other guard in this function: this must not
    # silently stop catching the defect if the template shifts.
    _ak_ref_re = re.compile(r'=SUBTOTAL\(9,[A-Z]{1,3}(\d+)\)', re.IGNORECASE)
    _ak_fixed_rows = []
    for _r in range(11, ws.max_row + 1):
        _g_formula = ws.cell(row=_r, column=7).value  # G
        if not (isinstance(_g_formula, str) and _g_formula.startswith('=')
                and 'SUBTOTAL' not in _g_formula.upper()):
            continue  # only genuine leaves — section headers legitimately use SUBTOTAL on G too
        _ak_formula = ws.cell(row=_r, column=37).value  # AK
        if not isinstance(_ak_formula, str):
            continue
        _m = _ak_ref_re.fullmatch(_ak_formula.replace(' ', ''))
        if not _m:
            continue  # only the exact "=SUBTOTAL(9,<ref>)" shape — not a header row with extra terms
        _donor_row = int(_m.group(1))
        if _donor_row == _r:
            continue
        for _col in (37, *range(43, 55)):  # AK, AQ..BB
            _donor_formula = ws.cell(row=_donor_row, column=_col).value
            if isinstance(_donor_formula, str):
                ws.cell(row=_r, column=_col).value = re.sub(
                    rf'(?<=[A-Z]){_donor_row}\b', str(_r), _donor_formula)
        _ak_fixed_rows.append((_r, _donor_row))
    if _ak_fixed_rows:
        _ak_cell_first = ws.cell(row=_ak_fixed_rows[0][0], column=37)
        _ak_cell_first.comment = Comment(
            f"AK/AQ:BB formulas restored to derive from this row's own cells — this row's template "
            f"formulas pointed at row {_ak_fixed_rows[0][1]} instead (and "
            f"{len(_ak_fixed_rows) - 1} other row(s): {_ak_fixed_rows[1:]}), which left "
            f"'1. Summary' (reads AK, not G) understating this line even though this sheet's own G "
            f"total was correct. Repaired using the referenced row's own intact formula text. See "
            f"openspec/changes/fix-parking-allocation-divide-by-zero for the full account.",
            'Budget Planning Agent')

    # Show the resident and parking curves on the deliverable's two fill-up sheets.
    _populate_fillup_sheets(
        wb, apt_units=project.get('apartment_units'),
        shop_units=(project['products'].get('Shophouse') or {}).get('units'),
        car_bays=car_slots, moto_bays=moto_slots,
        resident_fills=fills, car_fills=car_fills, moto_fills=moto_fills,
        car_rate=PARKING_FEE_CAR_MONTHLY, moto_rate=PARKING_FEE_MOTO_MONTHLY, stable=stable)

    # ---- RO2a "Bank Interest on Savills account" — a fund leaf where the template's own default
    # makes G (F x occurrences) disagree with AK (the month-by-month total '1. Summary' actually
    # reads): C37='Half a Year' (occurrences=2) with F37=5,000,000 but only one payment month (K37)
    # filled, so G37=10,000,000 while AK37=5,000,000 (docs/09-template-map.md §9 finding 1; change
    # reconcile-summary-with-detail-sheets, design D1, PM confirmed). Not the only such leaf — ERM
    # (row 485) had a structurally different cause (corrupted AK/AQ:BB formulas, not an
    # occurrences-vs-payment-months mismatch), fixed just above. No real bank-interest
    # figure exists for a prospect, so rather than fabricate a second payment month this zeroes the
    # line — G37=AK37=0, and it becomes a line a PM fills with a real negotiated figure.
    found = ws.cell(row=37, column=_CODE_COL).value
    found = found.strip() if isinstance(found, str) else found
    if found != 'RO2a':
        raise ValueError(f"'2. Budget-Management Fund' row 37 was expected to be cost code 'RO2a' "
                         f"but carries {found!r}. Re-verify the row against the current template "
                         f"rather than adjusting this check.")
    ws.cell(row=37, column=6, value=0)      # F37 — Unit Price -> G37 = 0 x 2 = 0
    ws.cell(row=37, column=11, value=None)  # K37 — the one filled payment-month date, cleared
    _write_remark(ws, 37, (
        "= 0. Chưa có căn cứ thực tế nào cho khoản thu lãi tiền gửi ngân hàng của Savills đối với một "
        "dự án chưa có tài khoản. Mẫu chuẩn để dòng này ở chế độ Nửa năm (2 lần/năm) với đơn giá "
        "5.000.000, nhưng chỉ điền 1 trong 2 tháng thanh toán, nên Tổng giá (G) và Tổng ngân sách năm "
        "(AK) không khớp nhau (10.000.000 so với 5.000.000) — trường hợp duy nhất bị lệch như vậy "
        "trên trang này. Đưa về 0 thay vì tự đoán tháng thanh toán thứ hai; PM sẽ điền số liệu thực "
        "tế khi dự án đã có tài khoản ngân hàng và mức lãi suất thực tế."))

    # ---- OPEX (Electricity/Water/Diesel — common-area usage; Repairs & Maintenance and Admin
    # Expense are single blended aggregates in this pipeline, so each lands on its section's
    # catch-all leaf (EMA15 / ERM) rather than being spread across the 30+/19 specific sub-system
    # rows the template itemizes — see MGMT_FUND_ROWS and _CATCH_ALL_NOTE below) ----
    opex = estimate_opex(project['total_nfa'], **_opex_kwargs(project))
    _opex_yr = _budget_year(wb, year)

    _OPEX_CATEGORY_VI = {
        'Water': 'Nước', 'Electricity': 'Điện', 'Diesel (Generator Fuel)': 'Dầu diesel (máy phát điện)',
        'Administrative Expense (office overhead)': 'Chi phí hành chính (chi phí văn phòng)',
        'Repairs & Maintenance (materials only)': 'Sửa chữa & bảo trì (vật tư)',
        'Pool Salt': 'Muối hồ bơi',
    }

    def _opex_remark(category):
        # The VAT-treatment sentence is NOT appended here: every string this returns is passed as a
        # `remark=` to _write_even_monthly_row / _write_ramped_row, which call _write_remark(), which
        # calls _append_vat() on the final (already concatenated) text — so the sentence lands once,
        # at the end, on an incl-VAT run. See _vat_sentence() / _ACTIVE_VAT_SENTENCE.
        entry = opex.get(category, {})
        annual = entry.get('monthly_vnd', 0) * 12
        if entry.get('method'):
            # Pool Salt — a stated formula, not an A&K ratio. estimate_opex() owns both the
            # calculation and its caveats so this workbook and the analysis one cannot disagree.
            # The client wording (no project name, decision D3) where estimate_opex gives one.
            return (f"{entry.get('method_client', entry['method'])} "
                    f"{entry.get('source_client', entry.get('source', ''))}").strip()
        if entry.get('tariff'):
            # Electricity / Water / Diesel — consumption x tariff (change
            # cost-energy-from-consumption-and-tariff), narrated in Vietnamese by the same helper
            # the '1. Summary' composed narrative uses (change localize-line-level-remarks,
            # 2026-09-15) — this line-level remark and that summary line now read identically
            # instead of one Vietnamese and one English. The n=1/provenance caveats the old English
            # text stated explicitly are preserved as a second Vietnamese sentence, since a client
            # reading only this cell should still see them.
            # The date, without the internal-document label some tariffs carry in their source data.
            tariff_date = re.sub(r"\s*\(AI Guideline built-up example\)", '', str(entry['tariff_as_of']))
            if entry.get('dated'):
                tariff_date = datetime.date.fromisoformat(tariff_date).strftime('%d/%m/%Y')
            if entry.get('dated') and category == 'Diesel (Generator Fuel)':
                date_note = (f" Giá niêm yết ngày {tariff_date}; giá dầu điều chỉnh khoảng 7 ngày một lần, "
                             f"cần xác nhận giá hiện hành trước khi sử dụng số liệu này.")
            else:
                date_note = (
                    f" Đơn giá đã lập ngày {tariff_date}, trước năm ngân sách {_opex_yr} — "
                    f"cần xác nhận đây vẫn là đơn giá công bố hiện hành trước khi sử dụng số liệu này."
                    if entry.get('tariff_stale') else
                    f" Đơn giá lập ngày {tariff_date}.")
            return (
                _energy_narrative_vi(category, project, _opex_yr) + date_note +
                f" Mức tiêu thụ lấy theo số liệu thực tế của một dự án tham chiếu (chỉ một dự án), "
                f"nên đây là ước tính ban đầu; cần đối chiếu với số liệu của dự án này khi có.")
        cat_vi = _OPEX_CATEGORY_VI.get(category, category)
        if entry.get('ratio_per_m2') is not None:
            return (f"= Tỷ lệ VND/m² NFA thực tế của dự án tham chiếu cho {cat_vi} ({entry['ratio_per_m2']:,.2f} "
                    f"VND/m²/tháng, chỉ một dự án tham chiếu — dự án chung cư duy nhất có số liệu OPEX được kiểm chứng độc lập) "
                    f"x Tổng NFA của dự án này ({project['total_nfa']:,.0f} m²) x 12 = {annual:,.0f} VND/năm.")
        return (f"= Số liệu cố định hàng tháng thực tế của dự án tham chiếu cho {cat_vi} x 12 = "
                f"{annual:,.0f} VND/năm (không tính theo NFA).")

    # Water and electricity are occupancy-scaled (catalogue): a half-empty building uses less.
    # Water tracks the resident curve directly; electricity has a floor — lifts, pumps, common-area
    # lighting and fire systems run regardless — so it never falls below 40% of full load and reaches
    # full load once the building is ~40% occupied, not only at 100%. Diesel is NOT occupancy-scaled
    # (it is driven by generator test/backup hours), so it stays flat.
    water_full_monthly = opex.get('Water', {}).get('monthly_vnd', 0)
    # By-month full-occupancy amounts when the tariff changes inside the period (VAT step); else flat.
    water_full_by_month = opex.get('Water', {}).get('monthly_vnd_by_month') or [water_full_monthly] * 12
    elec_full_monthly = opex.get('Electricity', {}).get('monthly_vnd', 0)
    _ur = project.get('utilities_result')
    if _ur is not None:
        # Existing-project mode (change carry-forward-common-utilities): the twelve amounts from the
        # project's actual consumption at each month's price — no fill-up curve, no electricity floor.
        for _key, _line in (('water', 'EEW.C'), ('electricity', 'EEE.C')):
            _write_ramped_row(ws, MGMT_FUND_ROWS[_key], _ur.lines[_line].amounts, (
                existing_utilities.narrative_vi(_ur, _line)
                + existing_utilities.adjustment_sentence(_ur, _line)))
    else:
        _full_note = "." if stable else (f" (nếu lấp đầy 100%: {sum(water_full_by_month):,.0f} VND/năm).")
        _water_months = [w * f for w, f in zip(water_full_by_month, fills)]
        _write_ramped_row(ws, MGMT_FUND_ROWS['water'], _water_months, (
            _opex_remark('Water') + " " + _anchor_note
            + f" Tổng năm 1: {sum(_water_months):,.0f} VND" + _full_note))
        _elec_fills = year1_electricity_fills(stable)
        # The floor-at-40%/reaches-full-by-~40%-occupancy mechanism is already stated in Vietnamese by
        # _energy_narrative_vi() above (change localize-line-level-remarks, 2026-09-15) — this used to
        # restate it in English before that helper existed; corrected 2026-09-21 (found reading this
        # remark aloud for change localize-line-level-remarks task 7.1) to just add the year-1 total,
        # not repeat the mechanism a second time.
        _vf = _vat_factors(project)
        _elec_months = [elec_full_monthly * f * v for f, v in zip(_elec_fills, _vf)]
        _write_ramped_row(ws, MGMT_FUND_ROWS['electricity'], _elec_months, (
            _opex_remark('Electricity')
            + f" Tổng năm 1: {sum(_elec_months):,.0f} VND"
            + ("." if stable else f" (nếu lấp đầy 100%: {sum(elec_full_monthly * v for v in _vf):,.0f} VND/năm).")))
    _diesel_months = opex.get('Diesel (Generator Fuel)', {}).get('monthly_vnd_by_month')
    if _diesel_months and len(set(_diesel_months)) > 1:    # VAT steps inside the period: one value per month
        _write_ramped_row(ws, MGMT_FUND_ROWS['diesel'], _diesel_months,
                          _opex_remark('Diesel (Generator Fuel)'))
    else:
        write_even_monthly('diesel', opex.get('Diesel (Generator Fuel)', {}).get('monthly_vnd', 0) * 12,
                           remark=_opex_remark('Diesel (Generator Fuel)'))
    # P4 (use-operating-project-actuals): collect-on-behalf (thu hộ / chi hộ) pairs, only where entered.
    _write_collect_on_behalf(ws, project)

    # The other two categories estimate_opex() computes. Until 2026-09-09 both were calculated on
    # every run, written into the analysis workbook, counted in its Cost Priority ranking — and
    # never written here, so the two workbooks disagreed by 85,302,456 VND/year on the sample while
    # nothing warned. Each lands on its section's catch-all leaf; see MGMT_FUND_ROWS.
    _CATCH_ALL_NOTE = (
        " Đây là dòng tổng hợp của cả nhóm, không phải chi tiết từng khoản: số liệu là một tỷ lệ gộp "
        "cho toàn bộ nhóm, không có dữ liệu nào cho biết cách phân bổ cho từng khoản mục riêng, nên "
        "việc tự chia nhỏ số liệu này sẽ là tạo ra một cơ cấu chi tiết không có thật.")

    assert_row_code('opex_admin', 'EMA15')
    write_even_monthly('opex_admin',
                        opex.get('Administrative Expense (office overhead)', {}).get('monthly_vnd', 0) * 12,
                        remark=(_opex_remark('Administrative Expense (office overhead)') +
                                _CATCH_ALL_NOTE +
                                " Bao gồm toàn bộ nhóm Chi phí hành chính (EMA) — điện thoại/internet văn "
                                "phòng, văn phòng phẩm, mực in, thuê máy photocopy, bưu phí, nước uống, bảo "
                                "trì thiết bị văn phòng và nhu yếu phẩm ca đêm, được liệt kê chi tiết trong "
                                "ghi chú dòng nguồn của dự án tham chiếu."))
    # EMA1-EMA4 stay at zero and are disclosed on this catch-all (checks._REQUIRED_CODE_DISCLOSED_ON);
    # '2.2 Common area Fund' gets the same disclosure on its own EMA15 share, without this sheet's
    # amounts (change explain-common-area-fund-zero-lines, design D3).
    _CATCH_ALL_REASONS['EMA15'] = (
        "Phần phân bổ từ dòng EMA15 (dòng tổng hợp Chi phí hành chính) trên '2. Budget-Management "
        "Fund'. Các khoản EMA1–EMA4 (điện thoại và internet, văn phòng phẩm, mực in, thuê máy "
        "photocopy) chưa có nguồn số liệu chi tiết riêng nên được gộp vào dòng tổng hợp này, không "
        "tách thành dòng riêng — xem ghi chú tại dòng EMA15 trên trang đó.")

    assert_row_code('opex_repairs', 'ERM')
    write_even_monthly('opex_repairs',
                        opex.get('Repairs & Maintenance (materials only)', {}).get('monthly_vnd', 0) * 12,
                        remark=(_opex_remark('Repairs & Maintenance (materials only)') +
                                _CATCH_ALL_NOTE +
                                " Đây là vật tư sửa chữa (phụ tùng, vật liệu), KHÔNG bao gồm hợp đồng bảo "
                                "trì hệ thống — chi phí hợp đồng bảo trì được chi từ quỹ bảo trì riêng theo "
                                "Điều 150 Luật Nhà ở 2023, không nằm trong quỹ vận hành này. Lưu ý: chi phí "
                                "thực tế phát sinh nhiều nhất trong nhóm ER tại các dự án tham chiếu là dịch "
                                "vụ thông hút bể phốt/bể tự hoại (ERCS) — một dịch vụ, không phải vật tư — "
                                "nên KHÔNG được tính trong số liệu này; số liệu này chỉ là vật tư sửa chữa."))

    if project.get('has_pool'):
        # ESM4 — pool chemicals. estimate_opex() computes this from the project's pool volume by
        # the method the spec states, and carries its own caveats in the remark; see POOL_SALT_*
        # in estimate_opex.py. Both generators read that one figure.
        write_even_monthly('pool_salt', opex.get('Pool Salt', {}).get('monthly_vnd', 0) * 12,
                            remark=_opex_remark('Pool Salt'))

    # ---- Real flat-reference costs from input/logic/EXENSIVE LOGIC.xlsx's Sheet2 (see
    # ENV_REPORT_ANNUAL etc.'s definitions above for the exact citation each one carries) ----
    write_even_monthly('env_report', ENV_REPORT_ANNUAL, remark=(
        f"{ENV_REPORT_ANNUAL:,.0f} VND/năm — báo giá thực tế dịch vụ báo cáo quan trắc môi trường "
        f"định kỳ. Bắt buộc theo quy định 6 tháng/lần theo Nghị định 40/2019/NĐ-CP Điều 47 (quan "
        f"trắc chất lượng không khí và khí thải)."))
    water_test_annual = WATER_TEST_SAMPLE_PRICE * WATER_TEST_SAMPLES_PER_ROUND * 2
    write_even_monthly('water_testing', water_test_annual, remark=(
        f"= {WATER_TEST_SAMPLE_PRICE:,.0f} VND/mẫu x {WATER_TEST_SAMPLES_PER_ROUND} mẫu "
        f"(bồn nước mái + tầng hầm + 1 vòi ngẫu nhiên) x 2 đợt/năm = {water_test_annual:,.0f} "
        f"VND/năm. Báo giá thực tế của Viện Pasteur TP.HCM; kiểm nghiệm 12 chỉ tiêu theo QCVN "
        f"01-2024/BYT (hiệu lực từ tháng 7/2025)."))
    if project.get('has_pool'):
        # Sampling is per body of water — an adult pool and a children's pool are tested separately
        # — so this scales with the pool COUNT. Pool chemicals (ESM4) deliberately do not: they are
        # priced from total pool volume, which already sums every pool. See _resolve_pool_count().
        pools = project.get('pool_count') or 1
        pool_test_annual = POOL_TEST_SAMPLE_PRICE * POOL_TEST_SAMPLES_PER_YEAR * pools
        count_note = (f"{pools} hồ bơi theo phiếu đầu vào" if project.get('pool_count_stated')
                      else "giả định 1 hồ bơi — phiếu đầu vào xác nhận có hồ bơi nhưng chưa ghi số lượng")
        write_even_monthly('pool_testing', pool_test_annual, remark=(
            f"= {POOL_TEST_SAMPLE_PRICE:,.0f} VND/mẫu x {POOL_TEST_SAMPLES_PER_YEAR} mẫu "
            f"(4 đợt/năm x 2 mẫu/đợt, mỗi mẫu 4 chỉ tiêu vi sinh gồm cả E.coli) "
            f"x {pools} hồ bơi = {pool_test_annual:,.0f} VND/năm. Mỗi hồ bơi được lấy mẫu riêng, "
            f"nên số liệu này tăng theo số lượng hồ bơi ({count_note}); hóa chất hồ bơi (ESM4) thì "
            f"không, vì được định giá theo tổng thể tích nước của toàn bộ hồ bơi."))
    fire_dept_annual = FIRE_DEPT_CONNECTION_MONTHLY * 12
    write_even_monthly('fire_dept_connect', fire_dept_annual, remark=(
        f"= {FIRE_DEPT_CONNECTION_MONTHLY:,.0f} VND/tháng (gói GSAFE G500, truyền tín hiệu báo cháy "
        f"về Phòng Cảnh sát PCCC TP.HCM) x 12 = {fire_dept_annual:,.0f} VND/năm. Đơn giá gói dịch vụ "
        f"thực tế, tham chiếu từ các dự án tương tự do Savills quản lý tại TP.HCM. Chỉ áp dụng cho "
        f"dự án tại TP.HCM — dự án ở tỉnh/thành khác sẽ kết nối với cơ quan PCCC địa phương khác, "
        f"với đơn giá thực tế khác, không phải đơn giá này."))

    # ---- Added 2026-09-14, change fill-guideline-required-line-items: Required codes that were
    # left at the template's blank default with no basis stated, but that DO have a real, findable
    # pricing method (Costing_Method_Catalogue.csv) — see that change's docs/14. ----
    def write_vat_monthly(key, annual_excl, remark, kind=utility_tariffs.VAT_GENERAL):
        """A line the tool prices excluding VAT, spread evenly over the year, with each month's VAT added
        (design D4): one value when every month carries the same rate, otherwise one value per month."""
        vf = _vat_factors(project, kind)
        if len(set(vf)) == 1:
            write_even_monthly(key, annual_excl * vf[0], remark=remark)
        else:
            _write_ramped_row(ws, MGMT_FUND_ROWS[key], [annual_excl / 12 * v for v in vf], remark)
        return sum(annual_excl / 12 * v for v in vf)

    _vat_bp = project.get('budget_period') or budget_period.default()
    _vat_text = (f"cộng VAT {_rate_phrase(_vat_bp.months, _general_vat_months(project))} theo từng tháng"
                 if _ACTIVE_VAT_SENTENCE else "chưa cộng VAT theo mô hình tài chính đã chọn")
    _env_total = sum(ENV_INCIDENT_PLAN_ANNUAL / 12 * v for v in _vat_factors(project))
    write_vat_monthly('env_incident_plan', ENV_INCIDENT_PLAN_ANNUAL, remark=(
        f"{ENV_INCIDENT_PLAN_ANNUAL:,.0f} VND/năm trước VAT, {_vat_text} = {_env_total:,.0f} VND/năm — kế hoạch "
        f"ứng phó sự cố môi "
        f"trường bắt buộc (phòng ngừa & ứng phó tràn đổ/sự cố khẩn cấp), một lần/năm. Hướng dẫn lập ngân sách của Savills "
        f"nêu trực tiếp số liệu tạm tính này; không phải số liệu ước tính theo dự án tham chiếu."))
    wastewater_crosscheck_annual = WASTEWATER_CROSSCHECK_SAMPLE_PRICE * WASTEWATER_CROSSCHECK_PER_YEAR
    _ww_total = sum(wastewater_crosscheck_annual / 12 * v for v in _vat_factors(project))
    write_vat_monthly('wastewater_crosscheck', wastewater_crosscheck_annual, remark=(
        f"= {WASTEWATER_CROSSCHECK_SAMPLE_PRICE:,.0f} VND/lần (trước VAT, theo SCE) x "
        f"{WASTEWATER_CROSSCHECK_PER_YEAR} lần/năm (hàng quý) = {wastewater_crosscheck_annual:,.0f} "
        f"VND/năm trước VAT, {_vat_text} = {_ww_total:,.0f} VND/năm — đối chiếu chéo với báo cáo chất lượng "
        f"nước sau xử lý của nhà thầu vận hành trạm xử lý nước thải (STP)."))

    # EMA7 Drinking water — guideline: BQL headcount x 1 L/person/day, 19 L bottle, real vendor
    # price. BQL headcount = every in-house roster position except Security/Cleaning/Landscape
    # (those are outsourced contracts, priced separately at ESS1/ESS4/ESS16 — same exclusion
    # fill_staff_cost_sheet() and EMH2 already use). Covers BQL office and resident-reception water.
    _bql_exclude_kws = [kw for kws in SERVICE_CATEGORY_KEYWORDS.values() for kw in kws]
    bql_headcount = sum(_eff_headcount(d) for d in demand
                         if not any(kw in d['Position'].lower() for kw in _bql_exclude_kws))
    if bql_headcount:
        dw_bottles_per_year = bql_headcount * DRINKING_WATER_L_PER_PERSON_DAY * 365 / DRINKING_WATER_BOTTLE_LITERS
        dw_annual = dw_bottles_per_year * DRINKING_WATER_BOTTLE_PRICE
        write_even_monthly('drinking_water', dw_annual, remark=(
            f"= {bql_headcount} nhân sự BQL (tính theo số người, gồm cả vòng nghỉ 7/6) x "
            f"{DRINKING_WATER_L_PER_PERSON_DAY} lít/người/ngày x 365 "
            f"ngày / {DRINKING_WATER_BOTTLE_LITERS} lít/bình x {DRINKING_WATER_BOTTLE_PRICE:,.0f} "
            f"VND/bình (đã gồm VAT) = {dw_annual:,.0f} VND/năm. Nhân sự BQL = toàn bộ nhân sự nội bộ "
            f"trừ Bảo vệ/Vệ sinh/Cây xanh (thuê ngoài, định giá riêng). Bao gồm nước dùng tại văn "
            f"phòng BQL và khu tiếp đón cư dân."))

    # ESS9 Normal domestic garbage collection — AI Guideline's 'B2.6 Rác sinh hoạt (QD67)' sheet,
    # QĐ 67/2025/QĐ-UBND's 3-part tariff (collection + transport + treatment). Apartment and
    # Shophouse only — the guideline sheet has no Officetel/Office section, so those stay unpriced,
    # same as every other line this pipeline declines to guess. Change complete-ai-guideline-
    # remark-coverage (B2.6 / waste-collection-costing track), added 2026-09-21.
    _waste_apt_units = (project['products'].get('Apartment') or {}).get('units') or 0
    _waste_shop_units = (project['products'].get('Shophouse') or {}).get('units') or 0
    if _waste_apt_units or _waste_shop_units:
        _waste_apt_monthly = (_waste_apt_units * WASTE_APARTMENT_KG_PER_UNIT_DAY
                               * WASTE_DAYS_PER_MONTH * WASTE_UNIT_PRICE)
        _waste_shop_monthly = (_waste_shop_units * WASTE_SHOPHOUSE_KG_PER_UNIT_DAY
                                * WASTE_DAYS_PER_MONTH * WASTE_UNIT_PRICE)
        waste_monthly = _waste_apt_monthly + _waste_shop_monthly
        waste_annual = waste_monthly * 12
        _HELPER_FIGURES['waste'] = dict(apt_units=_waste_apt_units, shop_units=_waste_shop_units,
                                        monthly=waste_monthly)
        _waste_total = sum(waste_monthly * v for v in _vat_factors(project))
        write_vat_monthly('waste_collection', waste_annual, remark=(
            f"= (Căn hộ: {_waste_apt_units} căn x {WASTE_APARTMENT_KG_PER_UNIT_DAY} kg/căn/ngày"
            + (f" + Shophouse: {_waste_shop_units} căn x {WASTE_SHOPHOUSE_KG_PER_UNIT_DAY:.3f} "
               f"kg/căn/ngày" if _waste_shop_units else "")
            + f") x {WASTE_DAYS_PER_MONTH} ngày x {WASTE_UNIT_PRICE:,.0f} VND/kg (thu gom "
              f"{WASTE_COLLECTION_PRICE:,.0f} + vận chuyển {WASTE_TRANSPORT_PRICE:,.0f} + "
              f"xử lý {WASTE_TREATMENT_PRICE:,.0f}, theo Quyết định 65/2026/QĐ-UBND, có hiệu lực từ "
              f"01/09/2026, trước VAT) = {waste_monthly:,.0f} VND/tháng trước VAT, {_vat_text} = "
              f"{_waste_total:,.0f} VND/năm."
            + (" Khối lượng Shophouse tính theo công thức trong hướng dẫn lập ngân sách của Savills (2.63 x 1.5 x "
               "30 ngày = 3.945 kg/căn/ngày), khác với ghi chú bằng chữ trên cùng trang nguồn "
               "(khoảng 3.41kg) — hai số liệu này mâu thuẫn nhau trong tài liệu gốc, đã chọn theo "
               "công thức." if _waste_shop_units else "")))

    # ESI2 public liability insurance (group 3): USD premium x exchange rate, then insurance VAT (10% in every month,
    # outside the VAT reduction), spread evenly. Blank premium = the 1,000 USD default; 0 = the PM prices nothing.
    _esi2 = project['esi2']
    if _esi2['premium_usd'] > 0:
        _esi2_excl = _esi2['premium_usd'] * _esi2['rate']
        _esi2_total = sum(_esi2_excl / 12 * v for v in _vat_factors(project, utility_tariffs.VAT_INSURANCE))
        _esi2_vat = (f"cộng VAT {_rate_phrase(_vat_bp.months, _general_vat_months(project, utility_tariffs.VAT_INSURANCE))}"
                     f" (bảo hiểm không thuộc diện giảm VAT xuống 8%)" if _ACTIVE_VAT_SENTENCE
                     else "chưa cộng VAT theo mô hình tài chính đã chọn")
        write_vat_monthly('esi2', _esi2_excl, kind=utility_tariffs.VAT_INSURANCE, remark=(
            f"= {_esi2['premium_usd']:,.0f} USD/năm"
            + (f" (mặc định theo ví dụ của tiêu chuẩn định giá Savills cho hạn mức trách nhiệm "
               f"{ESI2_LIABILITY_LIMIT_USD:,.0f} USD; PM nhập phí báo giá thực tế tại ô '{ESI2_PREMIUM_LABEL}')"
               if _esi2['premium_is_default'] else " (phí do PM nhập)")
            + f" x tỷ giá {_esi2['rate']:,.0f} VND/USD"
            + (f" (giá bán Vietcombank ngày {USD_RATE_DATE}; PM sửa được tại ô '{USD_RATE_LABEL}')"
               if _esi2['rate_is_default'] else " (do PM nhập)")
            + f" = {_esi2_excl:,.0f} VND/năm trước VAT, {_esi2_vat} = {_esi2_total:,.0f} VND/năm."))
    else:
        _write_zero_reason(ws, MGMT_FUND_ROWS['esi2'], 'ESI2', (
            f"PM nhập phí bảo hiểm trách nhiệm công cộng bằng 0 USD tại ô '{ESI2_PREMIUM_LABEL}', nên không tính "
            f"khoản này. Để trống ô đó để dùng mức mặc định {ESI2_DEFAULT_PREMIUM_USD:,.0f} USD/năm."))

    # EMH4 PCCC training/allowance — 'A5. Trợ cấp PCCC' is a template sheet with its own real,
    # already-computed total (1 team leader + 2 deputies + 17 members trained 4x/year, 2 days/
    # training, at the regional minimum wage x 30% night/holiday-training loading, per NĐ 105/2025/
    # NĐ-CP) — read live via a formula reference rather than re-computed in Python, same "wire an
    # existing calculation to its own leaf" pattern as EMH2/A1. The team-size assumption (20 people)
    # is the template's own fixed default, not scaled by this project's real headcount — disclosed,
    # not silently accepted as necessarily right for every project size.
    if 'A5. Trợ cấp PCCC' in wb.sheetnames:
        pccc_row = MGMT_FUND_ROWS['pccc_allowance']
        ws.cell(row=pccc_row, column=3, value='Monthly')
        f_cell = ws.cell(row=pccc_row, column=6, value="='A5. Trợ cấp PCCC'!$H$8/12")
        f_cell.number_format = _NUM_FMT
        _write_remark(ws, pccc_row, remark=(
            # Localized (change localize-line-level-remarks, 2026-09-15) — was English; not in that
            # change's original task list (found and closed while building its verification check,
            # task 6.1, so the new comprehensive no-internal-filename scan would not need a special-
            # case exemption for one known, easily-fixed gap).
            "= 'A5. Trợ cấp PCCC'!H8 (Tổng cộng/năm) / 12 — khoản huấn luyện ATLĐ/PCCC hàng năm bắt "
            "buộc và phụ cấp cán bộ PCCC theo NĐ 105/2025/NĐ-CP, tính cho đội hình mặc định của mẫu "
            "chuẩn (1 đội trưởng + 2 đội phó + 17 thành viên, huấn luyện 4 lần/năm, 2 ngày/đợt) theo "
            "mức lương tối thiểu vùng cộng 30% phụ cấp huấn luyện ca đêm/ngày lễ. Quy mô đội hình là "
            "mặc định cố định của mẫu chuẩn, không quy đổi theo số nhân sự thực tế của dự án này."))

    # EMH1 and ESI1 are Required but genuinely have no basis to price from yet — no Savills
    # management-fee contract terms exist for a prospect, and no insured asset value is captured
    # anywhere in this pipeline's inputs. Inventing either would be exactly the fabrication this
    # pipeline avoids elsewhere (Costing_Method_Catalogue.csv states both as deliberately blank
    # pending real data). Left at zero — remark-only, so the reason is stated rather than silent,
    # per spec guideline-required-line-items' "genuinely does not apply" scenario.
    #
    # BUG FIX (change localize-line-level-remarks, 2026-09-15): this EMH1 write used to be
    # unconditional, so it silently overwrote the real remark the fixed-fee/% branch above wrote
    # whenever a PM entered actual Savills contract terms — the FIGURE was always right (a separate
    # write, earlier), only the explanatory text was wrong, and only when real data existed, which
    # is exactly the case nobody had tested. Found by testing this change's own EMH1 translation
    # against a project with Fixed Monthly Fee filled in. Now guarded the same way the fixed-fee/%
    # branch's own condition already is.
    if not savills_fee.basis(project):
        _write_zero_reason(ws, MGMT_FUND_ROWS['mgmt_fee_expense'], 'EMH1', savills_fee.ZERO_REASON_VI)
    _write_zero_reason(ws, MGMT_FUND_ROWS['asset_insurance'], 'ESI1', (
        "chưa có giá trị tài sản bảo hiểm nào được ghi nhận trong dữ liệu đầu vào của "
        "hệ thống. Căn cứ ví dụ theo hướng dẫn lập ngân sách của Savills: tổng giá trị tài sản x 0,05%/năm (đã gồm bảo "
        "hiểm cháy nổ bắt buộc), theo Nghị định 105/2025/NĐ-CP. Sẽ định giá khi có giá trị tài sản "
        "thực tế hoặc giá trị hợp đồng do chủ đầu tư cung cấp."))

    # ---- Required codes with genuinely no findable pricing method or real input (checked this
    # session — Costing_Method_Catalogue.csv either has no entry, or the one entry it has needs
    # data this pipeline cannot source). Flagged rather than guessed (spec guideline-required-
    # line-items; docs/14-required-line-item-gaps.md has the full investigation each reason
    # summarizes). Remark-only — no figure written. Each write verifies its own row still carries
    # the expected code first, the same protection MGMT_FUND_ROWS gets via _assert_leaf_rows,
    # inlined here since these are one-off disclosure targets, not WRITE-VALUE rows that belong in
    # that table. ----
    # Reasons kept in English here as the engineering record (this dict is not what the client
    # reads); the VIETNAMESE text the deliverable actually shows is composed below, at write time,
    # from the same reasons — change localize-line-level-remarks, 2026-09-15. Internal filenames
    # (Costing_Method_Catalogue.csv, docs/14-required-line-item-gaps.md) and the internal change
    # name (complete-ai-guideline-remark-coverage) are named here for engineers but never reach the
    # cell text.
    _FLAGGED_NO_METHOD = {
        28:  ('RP3',   "No pricing method recorded for bicycle parking revenue "
                        "(Costing_Method_Catalogue.csv has RP1/RP2/RP5/RP6 only), and '0. Info' "
                        "carries no bicycle bay count or rate."),
        84:  ('EMH3',  "'A1.1 Allowance (From 08.2026)' has the right formula shape for night-"
                        "shift/holiday allowance, but this pipeline has no established source for "
                        "which roster positions work night shifts — every count on that sheet is "
                        "zero. Needs its own investigation, not guessed here."),
        115: ('EMB1',  "Benchmark-by-comparable, but the only comparable OPEX source in this repo "
                        "(Fact_OPEX.csv, A&K Tower) has no bank-fee line at all."),
        118: ('EMB4',  "Benchmark-by-comparable, but the only comparable OPEX source in this repo "
                        "(Fact_OPEX.csv, A&K Tower) has no audit-fee line at all."),
        122: ('EMO2',  "Conditional on EMO1 (owners-board salary subsidy), which is itself usually "
                        "zero in year 1 per the guideline — legitimately zero for a year-1 budget, "
                        "not a pricing gap."),
        126: ('EMO6',  "No pricing method recorded in Costing_Method_Catalogue.csv."),
        # EM# (131), ES# (221) and EE# (262) removed 2026-10-19 (change apply-head-of-pm-decisions-2026-10, group 6):
        # now priced as a rate of their group by _write_contingency_lines.
        134: ('ESC1', "Needs a real count of planned events and their scale — no such input "
                        "exists anywhere in this pipeline (Staffing Demand, 0. Info, or otherwise)."),
        135: ('ESC2',  "Catalogue describes the shape (drills/year x cost/drill + a year-1 plan-"
                        "preparation fee) but gives no real cited VND figure, unlike ESC12/ESM25."),
        137: ('ESC4',  "No pricing method recorded in Costing_Method_Catalogue.csv."),
        138: ('ESC5',  "No pricing method recorded in Costing_Method_Catalogue.csv."),
        # ESS9 removed 2026-09-21 (change complete-ai-guideline-remark-coverage, B2.6 track): now
        # priced above via MGMT_FUND_ROWS['waste_collection'], no longer a no-method line.
        #
        # Correction, same date: this dict previously claimed ESS10/ESS12/ESS17/ESS18/ESS19/ESS23
        # were all "the same QĐ 67/2025 tariff family as ESS9" and all owned by this change. Checked
        # each row's own column-Z label directly against the live template while implementing ESS9 —
        # that claim was right for only two of the six (ESS10, ESS19); the other four are unrelated
        # line items that happen to sit nearby: ESS12 is pest control, ESS17 is planting cost, ESS18
        # is public-toilet toiletries, ESS23 is outsourced pool staff. None of them have anything to
        # do with waste collection or QĐ 67. Corrected below rather than left to keep misleading a
        # reader of the generated deliverable.
        154: ('ESS10', "A real, different waste stream (hazardous garbage) from ESS9 (normal "
                        "domestic garbage, now priced) — the AI Guideline's 'B2.6 Rác sinh hoạt "
                        "(QD67)' sheet gives a household-waste rate only for normal domestic waste, "
                        "nothing for hazardous waste."),
        156: ('ESS12', "No pricing method recorded in Costing_Method_Catalogue.csv."),
        161: ('ESS17', "No pricing method recorded in Costing_Method_Catalogue.csv."),
        162: ('ESS18', "No pricing method recorded in Costing_Method_Catalogue.csv."),
        163: ('ESS19', "A real waste-collection consumable (garbage bags), but the guideline's QĐ "
                        "65/2026 rate on ESS9 prices the collection/transport/treatment SERVICE only "
                        "— it has no unit price for bags themselves, and no other source in this "
                        "pipeline does either."),
        167: ('ESS23', "No pricing method recorded in Costing_Method_Catalogue.csv."),
        198: ('ESM6',  "No pricing method recorded in Costing_Method_Catalogue.csv."),
        199: ('ESM7',  "No pricing method recorded in Costing_Method_Catalogue.csv."),
        201: ('ESM9',  "No pricing method recorded in Costing_Method_Catalogue.csv."),
        202: ('ESM10', "No pricing method recorded in Costing_Method_Catalogue.csv."),
        204: ('ESM12', "No pricing method recorded in Costing_Method_Catalogue.csv."),
        205: ('ESM13', "No pricing method recorded in Costing_Method_Catalogue.csv."),
        220: ('ESR',   "Section rollup row — no formula or basis stated anywhere this pipeline can "
                        "read."),
        480: ('ERCS1', "Residential service quotes are awaited; until then the 'benchmark unit cost' has "
                        "no real cited source anywhere in this pipeline (Head of PM decision B7)."),
    }
    # Vietnamese reason for each code above, keyed by code (not row, so the pairing survives a
    # template row-shift and _assert_row_code below still catches a real mismatch). Kept separate
    # from the English dict rather than merged into it, so the engineering reason (which may cite a
    # filename) and the client-facing reason (which must not) can never accidentally swap.
    _FLAGGED_NO_METHOD_VI = {
        'RP3':   "Chưa có phương pháp định giá cho doanh thu giữ xe đạp, và '0. Info' không có số "
                 "chỗ hay đơn giá giữ xe đạp.",
        'EMH3':  "Trang 'A1.1 Allowance (From 08.2026)' đã có đúng dạng công thức tính phụ cấp ca "
                 "đêm/ngày lễ, nhưng hệ thống chưa có nguồn xác định vị trí nào làm ca đêm — mọi số "
                 "liệu trên trang đó hiện đang bằng 0. Cần khảo sát riêng, không tự đoán tại đây.",
        'EMB1':  "Định giá theo dự án tham chiếu, nhưng nguồn OPEX tham chiếu duy nhất hiện có "
                 "không có dòng phí ngân hàng nào.",
        'EMB4':  "Định giá theo dự án tham chiếu, nhưng nguồn OPEX tham chiếu duy nhất hiện có "
                 "không có dòng phí kiểm toán nào.",
        'EMO2':  "Phụ thuộc vào EMO1 (hỗ trợ lương Ban quản trị), khoản này thường bằng 0 trong năm "
                 "đầu theo hướng dẫn lập ngân sách của Savills — hợp lý khi bằng 0 cho ngân sách năm 1, không phải thiếu "
                 "phương pháp định giá.",
        'EMO6':  "Chưa có phương pháp định giá được ghi nhận.",
        'ESC1':  "Cần số liệu thực tế về số sự kiện dự kiến và quy mô — hiện chưa có đầu vào này ở "
                 "bất kỳ đâu trong hệ thống.",
        'ESC2':  "Đã có mô tả cách tính (số đợt diễn tập/năm x chi phí/đợt + phí lập kế hoạch năm "
                 "1) nhưng chưa có số liệu VND thực tế được trích dẫn, khác với ESC12/ESM25.",
        'ESC4':  "Chưa có phương pháp định giá được ghi nhận.",
        'ESC5':  "Chưa có phương pháp định giá được ghi nhận.",
        'ESS10': "Một dòng rác thải thực tế nhưng khác với ESS9 (rác sinh hoạt thông thường, đã "
                 "được định giá) — trang 'B2.6 Rác sinh hoạt (QD67)' của hướng dẫn lập ngân sách của Savills chỉ nêu đơn "
                 "giá cho rác sinh hoạt thông thường (QĐ 65/2026), không có đơn giá cho rác thải "
                 "nguy hại.",
        'ESS12': "Chưa có phương pháp định giá được ghi nhận.",
        'ESS17': "Chưa có phương pháp định giá được ghi nhận.",
        'ESS18': "Chưa có phương pháp định giá được ghi nhận.",
        'ESS19': "Một vật tư tiêu hao thực tế liên quan đến thu gom rác (túi rác), nhưng đơn giá QĐ "
                 "65/2026 tại ESS9 chỉ định giá DỊCH VỤ thu gom/vận chuyển/xử lý — không có đơn giá "
                 "cho bản thân túi rác, và không có nguồn nào khác trong hệ thống có đơn giá này.",
        'ESS23': "Chưa có phương pháp định giá được ghi nhận.",
        'ESM6':  "Chưa có phương pháp định giá được ghi nhận.",
        'ESM7':  "Chưa có phương pháp định giá được ghi nhận.",
        'ESM9':  "Chưa có phương pháp định giá được ghi nhận.",
        'ESM10': "Chưa có phương pháp định giá được ghi nhận.",
        'ESM12': "Chưa có phương pháp định giá được ghi nhận.",
        'ESM13': "Chưa có phương pháp định giá được ghi nhận.",
        'ESR':   "Dòng tổng hợp của nhóm — không có công thức hay căn cứ nào được nêu rõ mà hệ "
                 "thống có thể đọc được.",
        'ERCS1': ERCS1_REASON_VI,
    }
    # Change use-real-budget-ranges: EMB4, ESC1, ESC2, ESC5, ESS7, ESS12, ESS23 from the real-budget range, or 0
    # with the range's own reason; those codes skip the generic no-method reason below.
    _range_codes = _write_real_budget_range_lines(ws, project, demand, existing)
    for _row, (_code, _reason) in _FLAGGED_NO_METHOD.items():
        _found = ws.cell(row=_row, column=_CODE_COL).value
        _found = _found.strip() if isinstance(_found, str) else _found
        if _found != _code:
            raise ValueError(
                f"'2. Budget-Management Fund' row {_row} was expected to be cost code {_code!r} "
                f"but carries {_found!r} — re-verify _FLAGGED_NO_METHOD against the current "
                f"template rather than adjusting this check."
            )
        if _code in _range_codes:
            continue
        if _code == 'EMH3' and _existing_emh3_priced(existing):
            continue    # priced in Existing-project mode (_write_existing_staff_lines)
        if _code == 'EMH3' and not existing:
            continue    # a new prospect's EMH3 comes from A1.1 (_write_new_prospect_emh3)
        if _code == 'EMH3' and not existing.duty:
            _write_zero_reason(ws, _row, _code, (
                f"{existing_staffing.BLANK_DUTY_TEXT}, và NS {existing.prior_year} không có số EMH3 đã duyệt, nên "
                f"EMH3 = 0. Nếu dự án có trực đêm hoặc làm ngày lễ, PM điền bảng này rồi chạy lại."))
            continue
        _write_zero_reason(ws, _row, _code, (
            f"{_FLAGGED_NO_METHOD_VI[_code]} Không tự đặt ra số liệu — đã được rà soát "
            f"và ghi nhận đầy đủ."))

    # ---- Capex — Year-1 lump sum (see docstring above) ----
    capex_items, capex_source = estimate_capex_items(project['total_nfa'], exclude_name=project['name'])
    capex_annual = {}
    capex_counts = {}
    for it in capex_items:
        capex_annual[it['category']] = capex_annual.get(it['category'], 0) + it['unit_price'] * it['qty']
        capex_counts[it['category']] = capex_counts.get(it['category'], 0) + 1
    scale_factor = capex_source.get('scale_factor') if capex_source else None

    _CAPEX_CATEGORY_VI = {
        'MO Equipment': 'Thiết bị Ban Quản lý (MO)', 'M&E Equipment': 'Thiết bị Cơ điện (M&E)',
        'Public Area': 'Khu vực công cộng', 'Amenity Area': 'Khu vực tiện ích',
    }

    def _capex_remark(category):
        n = capex_counts.get(category, 0)
        amount = capex_annual.get(category, 0)
        cat_vi = _CAPEX_CATEGORY_VI.get(category, category)
        scale_note = f" (hệ số quy đổi theo NFA {scale_factor}x)" if scale_factor else ""
        return (f"= Tổng(Số lượng x Đơn giá thực tế) của {n} khoản mục {cat_vi}, quy đổi từ danh mục "
                f"Capex thực tế của dự án tham chiếu gần nhất theo tỷ lệ Tổng "
                f"NFA{scale_note} = {amount:,.0f} VND — ghi nhận trọn gói vào Năm 1 (theo nguyên tắc "
                f"quỹ dự phòng bảo trì: 100% vào Năm 1, các năm sau là dự phòng).")

    write_year1_lump('capex_mo', capex_annual.get('MO Equipment', 0), remark=_capex_remark('MO Equipment'))
    write_year1_lump('capex_me', capex_annual.get('M&E Equipment', 0), remark=_capex_remark('M&E Equipment'))
    write_year1_lump('capex_public', capex_annual.get('Public Area', 0), remark=_capex_remark('Public Area'))
    write_year1_lump('capex_amenity', capex_annual.get('Amenity Area', 0), remark=_capex_remark('Amenity Area'))

    if existing:
        _write_existing_staff_lines(ws, existing, existing_layout)
    else:
        _write_new_prospect_emh3(ws, demand, _period_of(project))

    _write_contingency_lines(ws, contingency.FUND_SHEET, project)
    # BK507/BK511, the parking break-even cells: "N/A" instead of #DIV/0! at parking area 0 (decision B10).
    breakeven_cells.guard(ws)


_FUND_EMH3_ROW = 84


def _write_new_prospect_emh3(ws, demand, period):
    """A new prospect's EMH3 on '2. Budget-Management Fund': A1.1's monthly total (S13, or its total row when a
    qualifying code sits below the table), or 0 with the reason when no in-house position has a night shift
    (change apply-head-of-pm-decisions-2026-10, D5)."""
    found = str(ws.cell(row=_FUND_EMH3_ROW, column=_CODE_COL).value or '').strip()
    if found != 'EMH3':
        raise ValueError(f"'2. Budget-Management Fund' row {_FUND_EMH3_ROW} is {found!r}, not EMH3.")
    duty = _new_prospect_duty(demand, period)
    if not duty:
        _write_zero_reason(ws, _FUND_EMH3_ROW, 'EMH3', (
            "Staffing Demand không có vị trí nội bộ nào làm ca đêm (ca D hoặc 24H), nên không có phụ cấp ca đêm, "
            "ca đêm ngày lễ và ca ngày ngày lễ theo Điều 98 Bộ luật Lao động 2019."))
        return
    t = _new_prospect_a11_total_row(duty)
    formula = f"='{A11_SHEET}'!S13" if t is None else f"='{A11_SHEET}'!T{t}"
    ws.cell(row=_FUND_EMH3_ROW, column=3, value='Monthly')
    for col in [6] + list(range(8, 20)):
        ws.cell(row=_FUND_EMH3_ROW, column=col, value=formula).number_format = _NUM_FMT
    n = len(vn_holidays.paid_holidays_in_period(period.first_day, period.last_day))
    nights = (period.last_day - period.first_day).days + 1 - n
    wd = period_workdays(period, 6)

    def who(d):
        parts = [f"{d.night_normal} người trực đêm"]
        if d.day_holiday:
            parts.append(f"{d.day_holiday} người ca ngày dịp lễ")
        return f"{d.code} ({', '.join(parts)})"
    _write_remark(ws, _FUND_EMH3_ROW, (
        f"= '{A11_SHEET}'!" + ('S13' if t is None else f"T{t} (dòng 13 cộng các dòng thêm bên dưới)")
        + f" — phụ cấp làm ca đêm ngày thường (30%, {nights} đêm), ca đêm ngày lễ (390%, {n} đêm) và ca ngày "
          f"ngày lễ (300%, {n} ngày) theo Điều 98 Bộ luật Lao động 2019, tính trên lương ngày = lương gộp trên A1 / "
          f"({wd}/12) ngày công. Số người trực lấy từ Staffing Demand: {', '.join(who(d) for d in duty)}. Ca ngày "
          f"dịp lễ chỉ tính cho vị trí trực 7 ngày/tuần có ca đêm (ca sáng và ca chiều cộng lại); vị trí chỉ làm ca "
          f"ngày không tính. A1 đã gồm khoản này ở AC90, nên EMH2 trừ ra để không tính hai lần."))


def _existing_emh3_priced(existing):
    """True when Existing-project mode gives EMH3 a figure (its zero reason must not be written)."""
    if not existing:
        return False
    line = existing.lines['EMH3']
    return line.kind in ('duty', 'carried') or line.override != 0


def _write_existing_staff_lines(ws, existing, layout):
    """EMH2, EMH3 and EMH4 on '2. Budget-Management Fund' in Existing-project mode (design D8-D11,
    D15): always a formula into A1 / A1.1 / A5, whose carried and PM-adjustment rows
    _write_existing_detail_rows() writes at the rows _existing_detail_layout() gives; each remark is
    the line's own explanation followed by the "Điều chỉnh so với NS <năm>" sentence when the figure
    moved (spec deliverable-remarks)."""
    a1_ref = f"'{STAFF_COST_SHEET}'"
    a11_ref = f"'{A11_SHEET}'"

    def put(row, value):
        ws.cell(row=row, column=3, value='Monthly')
        for col in [6] + list(range(8, 20)):
            c = ws.cell(row=row, column=col, value=value)
            c.number_format = _NUM_FMT

    def remark(row, code, base):
        text = base + existing_staffing.adjustment_sentence(existing, code)
        _write_remark(ws, row, text)
        # A line that ends at zero (e.g. an approved EMH4 of 0 kept at 0) gives its reason to the
        # matching '2.2 Common area Fund' allocation too, as _write_zero_reason does elsewhere.
        if not existing.lines[code].budget:
            _ZERO_REASONS[code] = text

    detail = _existing_detail_layout(existing, layout)

    # EMH2 — always a formula into A1 (design D15): the table, less the allowance that EMH3 carries,
    # plus every row below it (overflow heads, the carried amount, the PM adjustment).
    emh2 = existing.lines['EMH2']
    row = MGMT_FUND_ROWS['staff_remainder']
    last = detail['a1_last']
    extra = ''
    if last is not None:
        extra = (f"+{a1_ref}!AC{_A1_UNPLACED_FIRST_ROW}*12" if last == _A1_UNPLACED_FIRST_ROW else
                 f"+SUM({a1_ref}!AC{_A1_UNPLACED_FIRST_ROW}:AC{last})*12")
    put(row, f"=({a1_ref}!AC96-{a1_ref}!AC90*{a1_ref}!AC95{extra})/12")
    if emh2.kind == 'lump':
        base = (f"= các dòng {_rows_text(detail['EMH2'])} của trang '{STAFF_COST_SHEET}': dự án không có "
                f"bảng nhân sự theo vị trí nên bảng lương trên trang để trống và không tính lại theo lương "
                f"từng người.")
    else:
        base = (f"= '{STAFF_COST_SHEET}'!AC96 trừ phụ cấp ca đêm/ngày lễ (AC90, tính riêng ở EMH3)"
                + (f" cộng các dòng từ {_A1_UNPLACED_FIRST_ROW} của cùng trang" if last is not None else '')
                + f" — quỹ lương cả năm của nhân sự mang từ NS {existing.prior_year} đã duyệt, tính lại "
                  f"theo lương tối thiểu vùng {existing.region} và mức đóng bảo hiểm năm "
                  f"{existing.budget_year} (lương tháng 13, BHXH/BHYT 20,5% và BHTN 1% có trần, kinh "
                  f"phí công đoàn 2%, cộng 10% phí quản lý của Savills).")
        if detail['EMH2']:
            base += f" Gồm dòng {_rows_text(detail['EMH2'])}."
    remark(row, 'EMH2', base)

    # EMH3 — A1.1!S13, or A1.1's total row when carried / adjustment rows sit below it.
    emh3 = existing.lines['EMH3']
    if _existing_emh3_priced(existing):
        assert_code = ws.cell(row=_FUND_EMH3_ROW, column=_CODE_COL).value
        if str(assert_code).strip() != 'EMH3':
            raise ValueError(f"'2. Budget-Management Fund' row {_FUND_EMH3_ROW} is {assert_code!r}, not EMH3.")
        h6, n, _p6 = existing.a11_days
        duty_text = (f"phụ cấp làm ca đêm ngày thường (30%), ca đêm ngày lễ (390%) và ca ngày ngày lễ "
                     f"(300%) theo Điều 98 Bộ luật Lao động, cho số nhân sự trực mang từ NS "
                     f"{existing.prior_year}; năm {existing.budget_year} có {n} ngày lễ hưởng nguyên lương "
                     f"và {h6} ngày thường")
        t = detail['a11_total']
        if t is None:
            put(_FUND_EMH3_ROW, f"={a11_ref}!S13")
            base = f"= '{A11_SHEET}'!S13 — {duty_text}."
        else:
            put(_FUND_EMH3_ROW, f"={a11_ref}!T{t}")
            base = (f"= '{A11_SHEET}'!T{t}: dòng 13 ("
                    + (duty_text if emh3.kind == 'duty' else 'bằng 0')
                    + f") cộng dòng {_rows_text(detail['EMH3'])}.")
        if not existing.duty:
            base = f"{existing_staffing.BLANK_DUTY_TEXT}. {base}"
        remark(_FUND_EMH3_ROW, 'EMH3', base)

    # EMH4 — A5's total row when carried forward or overridden; left to the template otherwise.
    emh4 = existing.lines['EMH4']
    if detail['EMH4']:
        row = MGMT_FUND_ROWS['pccc_allowance']
        t = detail['a5_total']
        put(row, f"='{A5_SHEET}'!H{t}/12")
        if emh4.kind != 'carried':
            base = (f"= '{A5_SHEET}'!H{t} / 12: đội PCCC mặc định của mẫu (dòng 8) cộng dòng "
                    f"{_rows_text(detail['EMH4'])}.")
        elif emh4.budget:
            base = (f"= '{A5_SHEET}'!H{t} / 12: dòng {_rows_text(detail['EMH4'])} — phụ cấp huấn luyện "
                    f"đội PCCC cơ sở theo NĐ 105/2025/NĐ-CP tính trên lương tối thiểu vùng {existing.region}; "
                    f"đội mặc định của mẫu đặt về 0.")
        else:
            base = (f"Không dùng ở NS {existing.prior_year} đã duyệt (số đã duyệt bằng 0), giữ nguyên "
                    f"cho năm {existing.budget_year}: = '{A5_SHEET}'!H{t} / 12, đội mặc định của mẫu đặt "
                    f"về 0.")
        remark(row, 'EMH4', base)


# "2.2 Common area Fund" is a SEPARATE real fund from "2. Budget-Management Fund" — same ~500-code
# catalog structure, but scoped to common-area commercial exploitation (advertising/rentals/visitor
# parking) rather than the whole-building management fee. Its EMH/ESS/EN/EE/etc. rows are the exact
# same codes already filled on "2. Budget-Management Fund". This comment used to say writing
# anything there would double-count them, "since this pipeline has no real cost-allocation split
# telling us how much of each belongs to which fund" — so only genuinely NEW, fund-specific revenue
# was written here (still true for COMMON_AREA_FUND_ROWS below).
#
# UPDATE 2026-09-14 (change fill-guideline-required-line-items): that premise turned out to be
# wrong, or at least stale — the template itself already ships a real allocation split for exactly
# this. Every EMH/EMA/EMB/EMO/ESC/ESS/ESI/ESM/ESR/EN/EE*/ER* leaf row's F column is a template-
# native formula, `XLOOKUP(code, '2. Fund'!Y, '2. Fund'!AL) * $F$8` — a revenue-proportional SHARE
# of the matching 2.Fund line (F8 = common-area revenue / (total 2.Fund revenue + common-area
# revenue), ~0.45% on Wayne Tower), not a duplicate of the full figure. It resolves to zero today
# only because the template ships column C blank on ~213 of these rows (E's own IF-chain needs C =
# "Monthly"/"Schedule"/etc. to return 12 instead of blank/0) — see
# _activate_common_area_passthrough_rows, which activates it by writing 'Monthly' into C wherever
# it's currently blank, changing nothing else. Verified this does not touch COMMON_AREA_FUND_ROWS'
# own two rows or any of the ~9 rows the template itself already set C on.
#
# This is now activated in code (fill_common_area_fund_sheet calls it), but is NOT signed off.
# UPDATE 2026-09-14, measured: RI1 on '2. Fund' (row 78, booked as revenue) reads live from
# '2.2 Common area Fund'!AH40 — a cross-sheet reference, NOT '2. Fund'!AH40 as
# Costing_Method_Catalogue.csv's RI1 row states (that catalogue entry is stale/wrong) — and AH40
# moves in exact lockstep with this activation's own newly-populated expense rows. Isolated
# measurement (activate-common-area-fund-cost-share/measured-effect.md): turning this on moves the
# deliverable's reported year-1 surplus UP by 40,096,270 VND on Wayne Tower, with '2.2'’s own
# worsened position never appearing in '1. Summary'!H54 anywhere — either a legitimate previously-
# hidden recovery now correctly shown, or a one-sided recognition that inflates the surplus. Real
# accounting question this pipeline cannot answer on its own. Tracked separately — see OpenSpec
# change activate-common-area-fund-cost-share — gated on PM/finance sign-off before archiving, same
# as every other figure-moving change here. Do not fold its effect into another change's measured
# figure until that sign-off lands. Row numbers verified once against the real file, same caveat as
# MGMT_FUND_ROWS above.
COMMON_AREA_FUND_ROWS = {
    'lcd_ad': 20,     # RA1.A  LCD Advertising for Apartment
    'lift_ad': 26,    # RA2    Decal Advertising for Lift
}
COMMON_AREA_FUND_EXPECTED_CODE = {'lcd_ad': 'RA1.A', 'lift_ad': 'RA2'}


def _activate_common_area_passthrough_rows(ws, skip_codes=()):
    """'2.2 Common area Fund' ships 200+ expense leaf rows whose F column is a template-native
    XLOOKUP pulling a revenue-proportional share of the matching '2. Budget-Management Fund' leaf
    (F{row} = XLOOKUP(code, '2.Fund'!Y, '2.Fund'!AL) * $F$8) — the template's own already-correct
    formula, not something this pipeline computes. But G{row} = IF(C='Schedule', SUM(H:S), F*E),
    and E{row} only evaluates to 12 when C{row} reads 'Monthly'/'Schedule'/etc (see E's own IF
    chain); the template ships C BLANK on every one of these rows except a handful it pre-set
    (ESS1/ESS4/EMB3/ESC12/ESI1/ESI2/ESM25/ESS38/EEE.P), so E silently resolves to 0 and the
    correct F-value never reaches G. This writes 'Monthly' into C only where it is currently blank
    AND F is this exact XLOOKUP-into-2.Fund pattern — activating the template's own formula, never
    overwriting a value the template (or a prior run) already set, and never touching a row whose F
    is something else (a literal revenue rate, or genuinely blank). Change
    fill-guideline-required-line-items, task group 4 (the mechanical half of the fix — the other
    half is pricing the still-zero source figure on '2. Budget-Management Fund' itself)."""
    activated = []
    for row in range(1, ws.max_row + 1):
        code = ws.cell(row=row, column=25).value  # Y
        if not code or str(code).strip() in skip_codes:   # skip: collect-on-behalf lines (decision D11)
            continue
        c_cell = ws.cell(row=row, column=3)
        if c_cell.value not in (None, ''):
            continue  # template (or a prior run) already set a frequency here — leave it alone
        f_val = ws.cell(row=row, column=6).value
        if isinstance(f_val, str) and 'XLOOKUP' in f_val and '2. Budget-Management Fund' in f_val:
            c_cell.value = 'Monthly'
            activated.append(str(code).strip())
    return activated


def _write_common_area_zero_reasons(ws):
    """Give every '2.2 Common area Fund' line that is a share of a zero '2. Budget-Management Fund'
    line that line's own reason (change explain-common-area-fund-zero-lines). Rows are found by code
    (column Y), not by row number, because the two sheets' rows differ. A row whose F is the
    template's XLOOKUP-into-'2. Fund' allocation gets the reason marked "phần phân bổ". The three
    section-contingency rows (EM#, ES#, EE#) are '2.2''s own lines, not allocations (F blank or 0);
    they are priced by _write_contingency_lines since group 6 of apply-head-of-pm-decisions-2026-10,
    and carry a '2. Fund' reason only at a contingency rate of 0, which is equally true of them, so they
    get the same reason without the allocation wording (user decision 2026-10-04). Any
    other row is skipped: the copied reason would not be known to apply. A Remarks cell already
    holding template text is left alone; whitespace counts as empty (two template cells ship a
    single space)."""
    written = []
    for row in range(1, ws.max_row + 1):
        code = ws.cell(row=row, column=_CODE_COL).value
        code = code.strip() if isinstance(code, str) else None
        if code not in _ZERO_REASONS and code not in _CATCH_ALL_REASONS:
            continue
        f_val = ws.cell(row=row, column=6).value
        is_allocation = isinstance(f_val, str) and 'XLOOKUP' in f_val and '2. Budget-Management Fund' in f_val
        is_own_contingency = code.endswith('#') and code in _ZERO_REASONS and f_val in (None, '', 0)
        if not (is_allocation or is_own_contingency):
            continue
        existing = ws.cell(row=row, column=_REMARKS_COL).value
        if existing is not None and str(existing).strip():
            continue
        if is_own_contingency:
            remark = f"Để ở mức 0: {_ZERO_REASONS[code]}"
        elif code in _ZERO_REASONS:
            remark = f"Để ở mức 0 (phần phân bổ từ '2. Budget-Management Fund'): {_ZERO_REASONS[code]}"
        else:
            remark = _CATCH_ALL_REASONS[code]
        _write_remark(ws, row, remark=remark)
        written.append(code)
    return written


# The standard form ships the single word "demo" as the remark on RP5 (daily two-wheeler visitor
# parking revenue) on '2.2 Common area Fund'. RP5 is a Required code that this pipeline leaves at
# 0 (its method needs a visitor-volume assumption that no input supplies, docs/14), and '2. Budget-
# Management Fund' carries no reason for it, so _write_common_area_zero_reasons() cannot copy one.
# The reason below replaces the placeholder (change fix-verify-hand-check-and-rp5-remark, text
# approved by the user 2026-10-05).
_RP5_PLACEHOLDER = 'demo'
_RP5_ZERO_REASON_VI = (
    "Để ở mức 0: Doanh thu giữ xe hai bánh vãng lai theo ngày phụ thuộc vào số lượt khách vãng lai "
    "mỗi ngày, mà hiện chưa có số liệu đầu vào nào cung cấp, nên không tự đặt ra con số.")


def _write_common_area_rp5_reason(ws):
    """Write RP5's own zero reason on '2.2 Common area Fund', in place of the form's placeholder.
    Written only when the remark cell is empty or holds exactly the placeholder (any other text is
    someone's own and stays), and only while the line really is at zero: a rate in F means the
    line is priced and "Để ở mức 0" would be false. Returns the row written, or None."""
    for row in range(1, ws.max_row + 1):
        code = ws.cell(row=row, column=_CODE_COL).value
        if not (isinstance(code, str) and code.strip() == 'RP5'):
            continue
        existing = ws.cell(row=row, column=_REMARKS_COL).value
        if str(existing or '').strip() not in ('', _RP5_PLACEHOLDER):
            return None
        if ws.cell(row=row, column=6).value not in (None, '', 0):
            return None
        _write_remark(ws, row, remark=_RP5_ZERO_REASON_VI)
        return row
    return None


def _code_rows(ws, codes, sheet_label):
    """{code: row} for each code in `codes`, found in column Y. Fails naming any code not found."""
    rows = {}
    for r in range(1, (ws.max_row or 1) + 1):
        c = ws.cell(row=r, column=_CODE_COL).value
        if isinstance(c, str) and c.strip() in codes:
            rows[c.strip()] = r
    missing = sorted(set(codes) - set(rows))
    if missing:
        raise ValueError(f"{sheet_label} has no row for {', '.join(missing)} (column Y).")
    return rows


def _contingency_rate(project):
    """(rate, is_default) as read_input resolved it; 2% default for a project dict built without read_input."""
    return (project.get('contingency_rate', contingency.DEFAULT_RATE),
            project.get('contingency_rate_is_default', True))


def _write_contingency_lines(ws, sheet, project):
    """EM#, ES# and EE# on one fund sheet (change apply-head-of-pm-decisions-2026-10, group 6, design D9): each
    month a live =ROUND(rate*(SUBTOTAL(9,<leaves>)-<excluded>),0) over the group's month-allocation column,
    written Schedule so G = SUM(H:S). The energy base also leaves out every expense line the catalogue pairs as
    collect-on-behalf, so an entered pair moves revenue and expense alike and the surplus does not move. At a rate
    of 0 the '2. Fund' lines keep their template zero with the approved reason, which '2.2' copies through
    _ZERO_REASONS (_write_common_area_zero_reasons). Returns the layout written."""
    rate, is_default = _contingency_rate(project)
    paired = set(operating_inputs.cob_pairing(CATALOGUE_PATH).values())
    lines = contingency.layout(ws, sheet, extra_exclusions=paired)
    if not rate:
        if sheet == contingency.FUND_SHEET:
            for line in lines:
                _write_zero_reason(ws, line['row'], line['code'], contingency.ZERO_REASON_VI)
        return lines
    for line in lines:
        row = line['row']
        ws.cell(row=row, column=3, value='Schedule')   # C: Frequency -> G = SUM(H:S)
        ws.cell(row=row, column=6, value=None)         # F: not used under Schedule
        for i, formula in enumerate(contingency.month_formulas(sheet, line, rate)):
            cell = ws.cell(row=row, column=8 + i, value=formula)
            cell.number_format = _NUM_FMT
        _write_remark(ws, row, remark=contingency.remark_vi(line, rate, is_default))
    return lines


def _write_contingency_narratives(wb, project, written):
    """'1. Summary' K25, K35 and K42 (group 6): the rows whose H reads a contingency line (H25 = EMO + EM#,
    H35 = ESR + ES#, H42 = EE#). Each lists what else the row sums, then the contingency item. The template's
    K42 pulls an unrelated remark (T251), so it is overwritten. Returns the cells written."""
    ws = wb['1. Summary']
    fund = wb[contingency.FUND_SHEET]
    rate, _default = _contingency_rate(project)
    lines = {l['code']: l for l in contingency.layout(fund, contingency.FUND_SHEET)}
    filled = []
    for srow, code, others in ((25, 'EM#', ('EMO',)), (35, 'ES#', ('=ESR',)), (42, 'EE#', ())):
        line = lines[code]
        h = str(ws.cell(row=srow, column=8).value or '')
        if f"AK{line['row']}" not in h.replace('$', '') and ws.cell(row=srow, column=2).value != code:
            raise ValueError(f"'1. Summary'!H{srow} is {h!r}; it no longer reads {code} (row {line['row']}).")
        items = [w['name_vi'] for _c, w in _children_for(others, written)] if others else []
        items.append(contingency.summary_item_vi(line, rate))
        narrative = _append_vat("Dự ước bao gồm:\n" + _vi_list(items))
        cell = ws.cell(row=srow, column=_SUMMARY_K_COL, value=narrative)
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        filled.append(f"K{srow}({code})")
    return filled


def _collect_on_behalf_lines(project):
    """The entered collect-on-behalf amounts as revenue/expense pairs (operating_inputs.cob_lines), each
    monthly amount rounded to the VND once so the two sides of every pair add up exactly; [] when none."""
    ops = project.get('operating') or {}
    if not ops.get('cob'):
        return []
    lines = operating_inputs.cob_lines(ops, operating_inputs.cob_pairing(CATALOGUE_PATH))
    for line in lines:
        line['monthly'] = round(line['monthly'])
    return lines


def _write_collect_on_behalf(ws, project):
    """P4 (use-operating-project-actuals): each entered amount on its RO3 (water) / RO4 (electricity)
    revenue row and on the expense line the catalogue pairs it with (PM-2), flat over 12 months, so
    revenue and expense rise by the same amount and the surplus does not move. Several revenue rows
    paired with one expense line add up on it. Nothing is written when no amount is entered: the
    guideline's "not estimated" stands. Returns the lines written."""
    lines = _collect_on_behalf_lines(project)
    if not lines:
        return []
    rows = _code_rows(ws, {l['revenue_code'] for l in lines} | {l['expense_code'] for l in lines},
                      "'2. Budget-Management Fund'")
    by_expense = {}
    for line in lines:
        product_vi = _PRODUCT_VI_LABEL.get(line['product'], line['product'])
        _write_ramped_row(ws, rows[line['revenue_code']], [line['monthly']] * 12,
                          operating_inputs.cob_revenue_remark_vi(line['utility'], product_vi, line['monthly'],
                                                                 line['expense_code']))
        by_expense.setdefault(line['expense_code'], []).append(line)
    for code, paired in by_expense.items():
        utilities = {l['utility'] for l in paired}
        if len(utilities) != 1:
            raise ValueError(f"{code} is paired with both water and electricity lines in the catalogue; "
                             f"one expense line can carry only one utility.")
        monthly = sum(l['monthly'] for l in paired)
        _write_ramped_row(ws, rows[code], [monthly] * 12,
                          operating_inputs.cob_expense_remark_vi(paired[0]['utility'], monthly,
                                                                 [l['revenue_code'] for l in paired]))
    return lines


def _keep_collect_on_behalf_out_of_common_area(wb, ws, expense_codes):
    """Decision D11 (2026-10-11): collect-on-behalf pairs stay out of '2.2 Common area Fund'. The paired
    expense lines get no share there (their frequency stays blank, so the template's own E is 0) and say
    why, and F8's revenue base leaves out the RO3/RO4 revenue rows, so every other line's share - and RI1,
    which reads this sheet's expense total back as revenue - is what it would be without the amounts."""
    rows = _code_rows(ws, set(expense_codes), "'2.2 Common area Fund'")
    for code, row in rows.items():
        ws.cell(row=row, column=3, value=None)
        _write_remark(ws, row, operating_inputs.COB_COMMON_AREA_VI)
    fund = wb['2. Budget-Management Fund']
    ranges = []
    for prefix in ('RO3.', 'RO4.'):
        rs = [r for r in range(1, (fund.max_row or 1) + 1)
              if str(fund.cell(row=r, column=_CODE_COL).value or '').startswith(prefix)]
        if rs:
            ranges.append(f"'2. Budget-Management Fund'!$AL${min(rs)}:$AL${max(rs)}")
    base = "SUBTOTAL(9,'2. Budget-Management Fund'!$AL$13:$AL$76)"
    f8 = str(ws['F8'].value or '')
    if base not in f8:
        raise ValueError(f"'2.2 Common area Fund'!F8 is {f8!r}, not the template's revenue-share formula; "
                         f"cannot leave the collect-on-behalf revenue out of its base.")
    ws['F8'] = f8.replace(base, f"({base}-SUBTOTAL(9,{','.join(ranges)}))")


def fill_common_area_fund_sheet(wb, project):
    """Elevator/lobby advertising revenue — real per-device rates (Fact_MasterRateCard.csv) already
    computed by generate_project_output.py's build_additional_revenue_sheet (ELEVATOR_AD_ITEMS),
    just never placed into the real template before. "Ad frame (tower lobby, inside elevator)" maps
    to RA2 (elevator-specific); the two LCD screen items (tower + basement lobby) combine into RA1.A
    (a generic lobby LCD line, no separate "basement" row in this template). Qty is a stated
    assumption (towers × qty-per-tower, or a flat count), not real per-project elevator-count data —
    same disclosure as the source sheet. Confirmed with the PM (2026-08-21) rather than assumed.

    Also activates the sheet's own template-native expense pass-through rows (EMH/EMA/EMB/EMO/ESC/
    ESS/ESI/ESM/ESR/EN/EE*/ER* — a proportional share of each matching '2. Budget-Management Fund'
    line) — see _activate_common_area_passthrough_rows."""
    from generate_project_output import ELEVATOR_AD_ITEMS, _real_ad_frame_qty, _real_basement_lcd_qty
    ws = wb['2.2 Common area Fund']
    _assert_leaf_rows(ws, '2.2 Common area Fund', COMMON_AREA_FUND_ROWS, COMMON_AREA_FUND_EXPECTED_CODE)
    _cob_expense_codes = sorted({l['expense_code'] for l in _collect_on_behalf_lines(project)})
    _activate_common_area_passthrough_rows(ws, skip_codes=_cob_expense_codes)
    _write_common_area_zero_reasons(ws)
    _write_common_area_rp5_reason(ws)
    _write_contingency_lines(ws, contingency.COMMON_SHEET, project)
    if _cob_expense_codes:
        _keep_collect_on_behalf_out_of_common_area(wb, ws, _cob_expense_codes)

    # Vietnamese display name and assumption text per item, kept SEPARATE from ELEVATOR_AD_ITEMS'
    # own `item`/`assumption` fields (change localize-line-level-remarks, 2026-09-15) rather than
    # translating those in place — `'inside elevator' in item.lower()` below classifies each item by
    # matching English text in `item`, so renaming that field to Vietnamese would silently break the
    # lift-ad/LCD-ad split. Same pattern as `_PRODUCT_VI_LABEL` / `_OPEX_CATEGORY_VI`: the underlying
    # identifier stays what the code matches on, the display text is a lookup beside it.
    _AD_ITEM_VI = {
        'Ad frame (tower lobby, inside elevator)': (
            'Khung quảng cáo (sảnh tòa nhà, trong thang máy)',
            'Giả định, không phải số liệu thực tế: khoảng 2 khung quảng cáo/tòa (tương ứng mỗi cụm '
            'thang máy một khung) — mẫu hình phổ biến ở chung cư cao tầng Việt Nam, không phải số '
            'thang máy thực tế của dự án này (chưa được thu thập ở bất kỳ đâu trong dữ liệu nguồn).'),
        'LCD screen (tower lobby)': (
            'Màn hình LCD (sảnh tòa nhà)',
            'Giả định, không phải số liệu thực tế: 1 màn hình LCD mỗi sảnh tòa.'),
        'LCD screen (basement lobby)': (
            'Màn hình LCD (sảnh tầng hầm)',
            'Giả định, không phải số liệu thực tế: 1 màn hình sảnh tầng hầm cho cả dự án (cố định, '
            'không quy đổi theo số tòa).'),
    }
    towers = project.get('towers') or 1
    lift_annual, lcd_annual = 0.0, 0.0
    lift_parts, lcd_parts = [], []
    for idx, (item, rate, qty_per_tower, flat_qty, assumption) in enumerate(ELEVATOR_AD_ITEMS):
        real_qty = _real_ad_frame_qty(project, towers) if idx == 0 else None
        real_basements = _real_basement_lcd_qty(project) if idx == 2 else None
        item_vi, assumption_vi = _AD_ITEM_VI.get(item, (item, assumption))
        if real_qty is not None:
            qty = real_qty
            assumption_vi = (f"Số liệu thực tế: dự án này có {project['passenger_elevators_per_tower']:g} "
                             f"thang máy chở khách/tòa (theo thông tin dự án) x {towers} tòa = {qty} "
                             f"khung quảng cáo — không phải giả định.")
        elif real_basements is not None:
            qty = real_basements
            assumption_vi = (f"Số liệu thực tế: dự án này có {project['basement_count']:g} tầng hầm "
                             f"(theo thông tin dự án) = {qty} màn hình — không phải giả định.")
        else:
            qty = (qty_per_tower * towers) if qty_per_tower is not None else flat_qty
        annual = rate * qty * 12
        _HELPER_FIGURES.setdefault('ads', []).append(dict(item=item, item_vi=item_vi, rate=rate, qty=qty,
                                                          note=assumption_vi))
        part = (f"{item_vi}: {rate:,.0f} VND/thiết bị/tháng x {qty:g} thiết bị x 12 = {annual:,.0f} "
                f"({assumption_vi})")
        if 'inside elevator' in item.lower():
            lift_annual += annual
            lift_parts.append(part)
        else:
            lcd_annual += annual
            lcd_parts.append(part)

    _write_even_monthly_row(ws, COMMON_AREA_FUND_ROWS['lift_ad'], lift_annual, remark=(
        "= " + " + ".join(lift_parts) + f" = {lift_annual:,.0f} VND/năm. "
        "Đơn giá thực tế (nhóm Dịch vụ, 'Quảng cáo thang máy')."))
    _write_even_monthly_row(ws, COMMON_AREA_FUND_ROWS['lcd_ad'], lcd_annual, remark=(
        "= " + " + ".join(lcd_parts) + f" = {lcd_annual:,.0f} VND/năm. "
        "Đơn giá thực tế (nhóm Dịch vụ, 'Quảng cáo thang máy')."))


# "A1. Staff cost 08.2026 (VN)" is the standard form's own REAL Savills payroll-calculator sheet
# (13th month, PIT brackets, SI/HI, Trade Union 2%, 10% admin markup — see that sheet's own
# formulas), not something this pipeline built. It is the same calculator a PM had pasted into the
# superseded 202608 form as "1. Staff cost From 08.2026 (VN)" — byte-identical except cell G15
# (change `rebase-output-onto-25-sheet-form`, 2026-09-10). Only column G (Current Gross Salary, the
# one real INPUT cell) is written here; every other column is the template's own live formula
# chain computing net pay/insurance/tax/admin fee FROM that input — left completely untouched.
#
# Only positions that exist in THIS project's own Staffing Demand AND have a matching row-group in
# the template get filled — Security/Cleaning/Landscape are deliberately excluded (those are
# outsourced-contract lines already priced separately on "2. Budget-Management Fund" ESS1/ESS4/
# ESS16, exactly matching what EMH2 "Staff cost for Savills" already excludes); Reception has no
# row-group in this sheet at all (it lives on the dedicated "B1. Lịch Lễ tân" sheet instead).
# APM/OM/CSS/ACC/CSR/ACE/ADCE genuinely aren't in Blue Skyline's current Staffing Demand — left
# blank rather than invented; add those positions to Staffing Demand first if they should be
# costed. Daily rate to monthly gross: the daily rate x the person's calendar working days in the
# budget period / 12 (period_workdays(); 302 / 12 for 2027 — change apply-head-of-pm-decisions-2026-10,
# D6). Night-shift/holiday premiums are NOT folded in here — they're what that Allowance sheet's own
# formulas already exist to compute.
STAFF_COST_SHEET = 'A1. Staff cost 08.2026 (VN)'
# Existing mode only (its new positions, through _monthly_gross_of): the template's 'A1.1 Allowance
# (From 08.2026)'!E7 = 25 days a month, kept so Existing staff lines do not move (G2-a).
WORKDAYS_PER_MONTH = 25

# keyword -> template abbreviation code (column D groups), matched the same way
# SERVICE_CATEGORY_KEYWORDS/STAFF_MARKET_KEYWORDS already match Staffing Demand positions elsewhere
STAFF_COST_KEYWORDS = {
    'PM': ['property manager'],
    'BE': ['building executive'],
    'CS': ['customer service'],
    'CE': ['chief engineer'],
    'TDS': ['shift leader'],
    'TN': ['technician'],
    # Added 2026-09-09 with the seven positions the intake form previously had no row for. The
    # template has always carried staff-cost rows for these codes; nothing could reach them.
    'APM': ['assistant property manager'],
    'OM': ['operations manager'],
    'CSS': ['customer service supervisor'],
    'ACC': ['accountant'],
    'CSR': ['cashier'],
    'ACE': ['assistant chief engineer'],
    'ADCE': ['technical secretary'],
}
# Matching is plain substring, so three of the new titles are contained inside an existing code's
# keyword: "Assistant Property Manager" contains "property manager", "Assistant Chief Engineer"
# contains "chief engineer", and "Customer Service Supervisor" contains "customer service". Without
# these exclusions each new role would be silently costed as its senior counterpart — an assistant
# priced as a Property Manager, which is both wrong and invisible. Same idea as
# SERVICE_EXCLUDE_KEYWORDS, which exists for exactly this class of collision.
STAFF_COST_EXCLUDE = {
    'PM': ['assistant property manager'],
    'CE': ['assistant chief engineer'],
    'CS': ['customer service supervisor'],
}
# Split across two template row-groups both abbreviated 'AA' (pool staff vs. gym staff) — resolved
# by keyword instead of the shared abbreviation, using the row's own item label (Z/B column text
# containing "hồ bơi"/"pool" vs "gym") to tell the two groups apart.
STAFF_COST_AA_KEYWORDS = {'pool': ['pool attendant'], 'gym': ['amenities attendant']}


def fill_staff_cost_sheet(wb, project, demand, year):
    if STAFF_COST_SHEET not in wb.sheetnames:
        return  # older template version without this sheet — nothing to fill
    ws = wb[STAFF_COST_SHEET]
    period = _period_of(project)

    # A1.1's daily-wage divisor (E7:E11, the template's 25) becomes the same calendar count A1's gross uses, so a
    # holiday or night shift is priced on the daily wage the monthly gross was built from (docs/30 D4-b).
    if A11_SHEET in wb.sheetnames:
        a11 = wb[A11_SHEET]
        for r in range(7, 12):
            a11.cell(row=r, column=5, value=f'={period_workdays(period, 6)}/12')
        _fill_new_prospect_a11(wb, _new_prospect_duty(demand, period), period)

    # Each group's heads fill its own template rows (found by column D / B, _a1_rows_by_group); heads beyond them go
    # below the table with the unplaced positions (change apply-head-of-pm-decisions-2026-10, D7 / docs/30 D6: no head
    # is dropped, the Property Manager included).
    money_fmt = '#,##0'
    rows_by_code = _a1_rows_by_group(ws)
    for key, _code, headcount, monthly_gross in _new_prospect_groups(demand, period):
        for r in rows_by_code.get(key, [])[:headcount]:
            ws.cell(row=r, column=7, value=monthly_gross).number_format = money_fmt   # G: Current Gross Salary

    # ---- The block below the table, from _A1_UNPLACED_FIRST_ROW: positions with no predefined row-group (today:
    # Reception), then the extra heads of any group, each a REAL row with A1's IDENTICAL formula chain (copied from
    # row 15's own formulas, column for column) — not a Python-computed number folded into 'EMH2' on another sheet.
    # This is what makes that cost auditable/editable in Excel like any other position, and it shares A1's own
    # statutory-cap cells ($L$7/$T$7/etc.), so it can never drift from what every other row on this sheet uses.
    # Change reconcile-summary-with-detail-sheets — built after PM feedback that a top-up folded into another sheet's
    # formula string wasn't an acceptable substitute for a real, visible line item. One row PER HEADCOUNT UNIT.
    below = _new_prospect_below_rows(demand, period, rows_by_code, _a1_group_labels(ws, rows_by_code))
    for i, (label, code, monthly_gross) in enumerate(below):
        r = _A1_UNPLACED_FIRST_ROW + i
        ws.cell(row=r, column=2, value=label)                                          # B Position
        ws.cell(row=r, column=4, value=code)                                           # D code
        ws.cell(row=r, column=7, value=monthly_gross).number_format = money_fmt        # G Current Gross
        ws.cell(row=r, column=8, value=0)                                              # H Increase rate
        for col, formula in _a1_chain_formulas(r).items():
            ws.cell(row=r, column=col, value=formula).number_format = money_fmt
    if below:
        note = ws.cell(row=_A1_UNPLACED_FIRST_ROW - 1, column=2, value=(
            "Vị trí không có nhóm dòng cố định trong mẫu chuẩn của Savills, hoặc số người vượt số dòng sẵn có của "
            "nhóm ở trên — định giá dưới đây bằng đúng công thức của bảng trên (không phải số ước tính riêng)."))
        note.font = Font(italic=True, size=9, color='7F7F7F')
    for name in _zero_pay_positions(demand, period):
        print(f"WARNING  A1 '{STAFF_COST_SHEET}': '{name}' has staff but a gross pay of 0 (daily rate blank or 0 in "
              f"Staffing Demand). The row is written at 0, not skipped — enter its daily rate.")


# ---- Helper sheets A2-A4, B1-B5 (change apply-head-of-pm-decisions-2026-10, D15; spec deliverable-helper-sheets) ----
# The form ships these sheets with sample posts, a sample reception calendar and sample helper figures. They now show
# this project's own: the A2-A4 posts and rate ESS1/ESS4/ESS16 were priced on (each total x 12 = its line), the
# reception calendar by the roster's rest rule, the B3 garbage, B4 advertising and B5 parking figures the fund lines
# use, and "Chưa áp dụng" where the tool has no figure of its own (B2, B3 consumables). No formula outside these
# sheets reads them, and A5 (EMH4) is not touched.

def _post_persons(d):
    """People a Staffing Demand row needs, relief for the weekly day off included (as ESS1/ESS4/ESS16 count them)."""
    return math.ceil(d['StaffPerDay'] * 7 / 6) if d['CoverageDays'] >= 7 else d['StaffPerDay']


def _record_contract_posts(cat, demand, matched, post_rate, roles, blend, qty):
    """Kept by fill_management_fund_sheet()'s contract_cost(): the posts, rate and night blend one of ESS1/ESS4/ESS16
    was priced on, plus the posts it leaves out (a supervisor), for the A2-A4 helper sheets."""
    from generate_project_output import SERVICE_CATEGORY_KEYWORDS, SERVICE_EXCLUDE_KEYWORDS
    kws = SERVICE_CATEGORY_KEYWORDS[cat]
    excluded = [d for d in demand if any(kw in d['Position'].lower() for kw in kws)
                and any(ex in d['Position'].lower() for ex in SERVICE_EXCLUDE_KEYWORDS)]
    _HELPER_FIGURES.setdefault('contract', {})[cat] = dict(
        post_rate=post_rate, roles=roles, blend=blend, qty=qty,
        posts=[(d, _post_persons(d)) for d in matched if _post_persons(d)],
        excluded=[(d, _post_persons(d)) for d in excluded if _post_persons(d)])


# One entry per outsourced service sheet. `base_hours` is the hours the sheet's row price divides the rate cell by
# (A2: $G$3/24*E, A3/A4: $J$3/8*E), so a person's row hours are base_hours / roles and the sheet total equals the
# fund line by construction. `rows` places a post on its standard row by a keyword of its Staffing Demand name; a
# post with no standard row goes on `main_row` with a note (the user's choice, 2026-10-19: the sheets have no blank
# row). `unpriced_row` is the standard row without a price, for a post the line leaves out (a supervisor).
_POST_SHEETS = {
    'Security': dict(sheet='A2. Bảo vệ - Security', rate_cell='G3', rate_label='E3', price_col=7, line='ESS1',
                     base_hours=24, shift_cols=None, qty_col=6, total_cell='H31', main_row=16, unpriced_row=None,
                     note_col=3, note_row=37, conversion_hours_cell='E35', alloc_cols=('M', 'N', 'O', 'P'),
                     rows=(('main gate', 14), ('side gate', 15), ('cctv', 12), ('fcc', 13), ('patrol', 16)),
                     vi='bảo vệ'),
    'Cleaning': dict(sheet='A3. Vệ sinh - Cleaning', rate_cell='J3', rate_label='H3', price_col=10, line='ESS4',
                     base_hours=8, shift_cols={'S': 6, 'C': 7}, qty_col=8, total_cell='K23', main_row=12,
                     unpriced_row=10, note_col=3, note_row=25, conversion_hours_cell=None,
                     alloc_cols=('P', 'Q', 'R', 'S'),
                     rows=(('common area', 12), ('clubhouse', 13), ('parking', 20)), vi='vệ sinh'),
    'Landscape': dict(sheet='A4. Cây xanh - Landscape', rate_cell='J3', rate_label='H3', price_col=10, line='ESS16',
                      base_hours=8, shift_cols={'S': 6, 'C': 7}, qty_col=8, total_cell='K11', main_row=10,
                      unpriced_row=8, note_col=3, note_row=13, conversion_hours_cell=None,
                      alloc_cols=('P', 'Q', 'R', 'S'), rows=(('gardener', 10), ('landscape', 10)), vi='cây xanh'),
}
_SHIFT_VI = {'HC': 'hành chính', 'S': 'ca sáng', 'C': 'ca chiều', 'D': 'ca đêm', '24H': 'trực 24/24'}
_HELPER_NOTE_FONT = Font(italic=True, size=9)


def _helper_note(ws, row, col, text):
    cell = ws.cell(row=row, column=col, value=text)
    cell.font = _HELPER_NOTE_FONT
    cell.alignment = Alignment(wrap_text=False, vertical='top')
    return cell


def _fill_service_post_sheet(wb, project, cat):
    """A2/A3/A4: this project's posts on the standard rows, the line's rate x night blend in the rate cell, every
    other standard row at quantity 0 with its name and duty description kept, and the allocation basis filled."""
    spec = _POST_SHEETS[cat]
    ws = wb[spec['sheet']]
    fig = (_HELPER_FIGURES.get('contract') or {}).get(cat)
    if fig is None:
        raise ValueError(f"{spec['line']} was not priced before its helper sheet '{spec['sheet']}' was filled.")
    qty_cols = [spec['qty_col']] + sorted((spec['shift_cols'] or {}).values())
    # Position rows: a name in D and working hours in E (group headers have neither hours nor a price).
    total_row = ws[spec['total_cell']].row
    position_rows = [r for r in range(8, total_row)
                     if isinstance(ws.cell(row=r, column=5).value, (int, float))
                     and isinstance(ws.cell(row=r, column=4).value, str)]
    priced_rows = {r for r in position_rows
                   if spec['rate_cell'].replace('G', '$G$').replace('J', '$J$')
                   in str(ws.cell(row=r, column=spec['price_col']).value or '')}
    if spec['main_row'] not in priced_rows:
        raise ValueError(f"'{spec['sheet']}' row {spec['main_row']} no longer carries the sheet's price formula: "
                         f"re-check _POST_SHEETS against the template.")
    for r in position_rows:
        for c in qty_cols:
            ws.cell(row=r, column=c).value = None
        ws.cell(row=r, column=spec['qty_col']).value = 0

    hours = spec['base_hours'] / fig['roles']
    placed = {}            # row -> {'shifts': {code: n}, 'merged': [(position, n)], 'night': n, 'unpriced': bool}
    not_placed = []
    for group, unpriced in ((fig['posts'], False), (fig['excluded'], True)):
        for d, n in group:
            if unpriced:
                if spec['unpriced_row'] is None:
                    not_placed.append((d['Position'], n))
                    continue
                r, matched = spec['unpriced_row'], True
            else:
                p = d['Position'].lower()
                r = next((row for kw, row in spec['rows'] if kw in p and row in priced_rows), None)
                matched = r is not None
                r = r if matched else spec['main_row']
            slot = placed.setdefault(r, dict(shifts={}, merged=[], night=0, unpriced=unpriced))
            code = d['ShiftCode']
            slot['shifts'][code] = slot['shifts'].get(code, 0) + n
            if not matched:
                slot['merged'].append((d['Position'], n))
            if spec['shift_cols'] is not None and code not in spec['shift_cols'] and code != 'HC':
                slot['night'] += n
    for r, slot in placed.items():
        ws.cell(row=r, column=5).value = hours
        if spec['shift_cols'] is None:
            ws.cell(row=r, column=spec['qty_col']).value = sum(slot['shifts'].values())
        else:
            ws.cell(row=r, column=spec['qty_col']).value = None
            per_col = {}
            for code, n in slot['shifts'].items():
                col = spec['shift_cols'].get(code, spec['qty_col'])
                per_col[col] = per_col.get(col, 0) + n
            for col, n in per_col.items():
                ws.cell(row=r, column=col).value = n

    rate_cell = ws[spec['rate_cell']]
    rate_cell.value = f"={fig['post_rate']:.0f}*{fig['blend']:g}"
    rate_cell.number_format = '#,##0'
    label = ws[spec['rate_label']]
    if isinstance(label.value, str) and 'hệ số ca đêm' not in label.value:
        label.value = label.value + '\n(đã gồm hệ số ca đêm)'
    if spec['conversion_hours_cell'] and hours not in (24, 12):
        ws[spec['conversion_hours_cell']] = hours       # the 24h-conversion block counts the hours the rows use

    prods = project.get('products') or {}
    apartment_weight, villas = _apartment_column_weight(project)
    basis = (apartment_weight, (prods.get('Shophouse') or {}).get('nfa') or 0,
             (prods.get('Retail') or {}).get('nfa') or 0, project.get('car_slots') or 0)
    for col, value in zip(spec['alloc_cols'], basis):
        ws[f'{col}7'] = value
    if villas:
        ws[f"{spec['alloc_cols'][0]}7"].comment = Comment(_villa_column_note(apartment_weight), 'Budget Planning Agent')

    annual = fig['post_rate'] / fig['roles'] * fig['blend'] * fig['qty'] * 12
    rate_ref = spec['rate_cell']
    notes = []
    if not fig['qty']:
        notes.append(f"Staffing Demand của dự án không có vị trí {spec['vi']} thuê ngoài: các dòng ghi số lượng 0.")
    notes.append(f"Số lượng là số người làm ca {hours:g} giờ, đã gồm người thay ca nghỉ hằng tuần của vị trí trực 7 "
                 f"ngày/tuần (số người trực mỗi ngày x 7/6, làm tròn lên).")
    if cat == 'Security':
        notes.append(f"Đơn giá ô {rate_ref} = {fig['post_rate']:,.0f} VND/vị trí 24h/tháng x hệ số ca đêm "
                     f"{fig['blend']:.4f} (đã gồm hệ số ca đêm); một người ca {hours:g} giờ bằng 1/{fig['roles']:g} "
                     f"vị trí 24h.")
    else:
        notes.append(f"Đơn giá ô {rate_ref} = {fig['post_rate']:,.0f} VND/người/tháng x hệ số ca đêm "
                     f"{fig['blend']:.4f} (đã gồm hệ số ca đêm)." if fig['blend'] != 1 else
                     f"Đơn giá ô {rate_ref} = {fig['post_rate']:,.0f} VND/người/tháng (dự án không có ca đêm cho vị trí này).")
    for r in sorted(placed):
        slot = placed[r]
        code_txt = ws.cell(row=r, column=3).value or ''
        name_txt = str(ws.cell(row=r, column=4).value or '').split('/')[0].strip()
        detail = ', '.join(f"{_SHIFT_VI.get(c, c)} {n:g}" for c, n in slot['shifts'].items())
        line = f"{code_txt} {name_txt}: {sum(slot['shifts'].values()):g} người ({detail})"
        if slot['unpriced']:
            line += f", không tính giá trong khoản {spec['line']} (vị trí giám sát)"
        if slot['merged']:
            line += ('; gồm ' + ', '.join(f"{p} ({n:g} người)" for p, n in slot['merged'])
                     + ': không có dòng chuẩn tương ứng nên gộp vào dòng này')
        if slot['night']:
            line += f"; {slot['night']:g} người ca đêm/24h ghi ở cột ca hành chính"
        notes.append(line + '.')
    for p, n in not_placed:
        notes.append(f"Không ghi trên trang này: {p} ({n:g} người), vị trí giám sát không thuộc khoản {spec['line']}.")
    notes.append(f"Tổng chi phí/tháng x 12 = {annual:,.0f} VND/năm, bằng dòng {spec['line']} trang "
                 f"'2. Budget-Management Fund'.")
    _helper_note(ws, spec['note_row'], spec['note_col'], 'Ghi chú:').font = Font(bold=True, italic=True, size=9)
    for i, text in enumerate(notes, start=1):
        _helper_note(ws, spec['note_row'] + i, spec['note_col'], f"{i}. {text}")


_B1_SHEET = 'B1. Lịch Lễ tân'
_B1_FIRST_ROW, _B1_ROWS = 7, 5           # the form's five staff rows
_B1_DAY_COL = 4                          # D = day 1 ... AH = day 31
_B1_COUNTER_COLS = {36: '=COUNTIF(D{r}:AH{r},"O")', 37: '=COUNTIF(D{r}:AH{r},$AK$6)', 38: '=COUNTIF(D{r}:AH{r},"PH")',
                    39: '=COUNTIF($D{r}:$AH{r},$AM$6)', 40: '=COUNTIF(D{r}:AH{r},"N")'}   # AJ:AN
_WEEKDAY_VI = ('Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ Nhật')
_SHIFT_NAME_VI = {'HC': 'Hành chính', 'S': 'Ca sáng', 'C': 'Ca chiều', 'D': 'Ca đêm', '24H': 'Trực 24/24'}
_B1_NOT_USED = 'Chưa áp dụng: xem lịch theo tháng ở mục A.'


def _roster_month(project):
    """(year, month, holiday days) of the roster: Roster Setup's month, or the budget's first month when blank."""
    if project.get('roster_month'):
        year, month = project['roster_month']
    else:
        bp = project.get('budget_period') or budget_period.default()
        year, month = bp.start_year, bp.start_month
    holidays = project.get('roster_holidays')
    if holidays is None:
        holidays = vn_holidays.holidays_in_month(year, month)
    return year, month, sorted(holidays)


def _reception_calendar(demand, year, month):
    """[(demand row, [duty code per day])] for each reception person, by the roster's own rest rule: on a 7-day post
    person s rests on the days d with (d - 1) mod 7 = s mod 7; on a shorter post every person rests on the weekdays
    past the post's coverage days (build_roster's Generated Roster formulas)."""
    days = cal.monthrange(year, month)[1]
    people = []
    for d in demand:
        p = d['Position'].lower()
        if 'reception' not in p and 'lễ tân' not in p:
            continue
        for s in range(int(_post_persons(d))):
            codes = []
            for day in range(1, days + 1):
                if d['CoverageDays'] >= 7:
                    codes.append('O' if (day - 1) % 7 == s % 7 else d['ShiftCode'])
                else:
                    on = datetime.date(year, month, day).isoweekday() <= d['CoverageDays']
                    codes.append(d['ShiftCode'] if on else 'O')
            people.append((d, codes))
    return people


def _fill_reception_calendar(wb, project, demand):
    """B1: the reception duty calendar for the roster month in part A; parts B and C (by day, by week) say they are
    not used. More than five people: the first five are shown and a note gives the rest (the user's choice,
    2026-10-19: no rows are inserted into the form)."""
    ws = wb[_B1_SHEET]
    year, month, holidays = _roster_month(project)
    days = cal.monthrange(year, month)[1]
    people = _reception_calendar(demand, year, month)
    for day in range(1, 32):
        col = _B1_DAY_COL + day - 1
        real = day <= days
        ws.cell(row=5, column=col).value = _WEEKDAY_VI[datetime.date(year, month, day).weekday()] if real else None
        ws.cell(row=6, column=col).value = day if real else None
    for i in range(_B1_ROWS):
        r = _B1_FIRST_ROW + i
        for c in range(1, 43):                                   # A:AP
            ws.cell(row=r, column=c).value = None
        if i >= len(people):
            continue
        d, codes = people[i]
        ws.cell(row=r, column=1).value = i + 1
        ws.cell(row=r, column=2).value = f'Lễ tân {i + 1}'
        ws.cell(row=r, column=3).value = _SHIFT_NAME_VI.get(d['ShiftCode'], d['ShiftCode'])
        for day, code in enumerate(codes, start=1):
            ws.cell(row=r, column=_B1_DAY_COL + day - 1).value = code
        for c, f in _B1_COUNTER_COLS.items():
            ws.cell(row=r, column=c).value = f.format(r=r)
        ws.cell(row=r, column=42, value=f'={days}-AJ{r}-AK{r}-AM{r}/2')       # AP: days worked
    for r in range(19, 23):
        ws.cell(row=r, column=2).value = None
    ws['A22'] = None
    if not people:
        ws.cell(row=_B1_FIRST_ROW, column=2).value = 'Dự án không có vị trí lễ tân.'
        ws['B19'] = 'Dự án không có vị trí lễ tân trong Staffing Demand, nên không có lịch lễ tân.'
    else:
        by_shift = {}
        for d, _codes in people:
            by_shift[d['ShiftCode']] = by_shift.get(d['ShiftCode'], 0) + 1
        ws['B19'] = (f"Lịch làm việc tháng {month:02d}/{year} ({days} ngày), lập theo lịch trực của dự án: "
                     f"{len(people)} lễ tân (" + ', '.join(f"{n} {_SHIFT_VI.get(c, c)}" for c, n in by_shift.items())
                     + ").")
        rules = []
        for cov in sorted({d['CoverageDays'] for d, _c in people}, reverse=True):
            rules.append('vị trí trực 7 ngày/tuần: mỗi người nghỉ 1 ngày/tuần (O), xoay vòng' if cov >= 7 else
                         f'vị trí trực {cov} ngày/tuần: nghỉ (O) các ngày còn lại trong tuần')
        ws['B20'] = 'Ngày nghỉ theo lịch trực: ' + '; '.join(rules) + '.'
        ws['B21'] = ('Ngày lễ trong tháng: ' + ', '.join(f"{h:02d}/{month:02d}" for h in holidays)
                     + '; mã ca giữ nguyên như lịch trực.' if holidays else 'Tháng này không có ngày lễ.')
        if len(people) > _B1_ROWS:
            ws['A22'] = 4
            ws['B22'] = (f"Dự án cần {len(people)} lễ tân; bảng trên ghi lịch {_B1_ROWS} người đầu, "
                         f"{len(people) - _B1_ROWS} người còn lại xếp theo cùng quy tắc nghỉ.")
    ws['Z20'], ws['Z21'] = 'S: 6h-15h', 'C: 13h-22h'        # the roster's shift hours (Shift Types)
    # C. by week (rows 26-30) and B. by day (rows 38-48, hidden): sample codes cleared, the #REF! of B42/C42 with them.
    for r in range(26, 31):
        for c in range(1, 12):
            ws.cell(row=r, column=c).value = None
    ws['B26'] = _B1_NOT_USED
    ws['C38'], ws['E38'] = _B1_NOT_USED, None
    for r in range(42, 49):
        for c in range(1, 35):
            ws.cell(row=r, column=c).value = None


def _fill_b2_b5(wb, project):
    """B2 (scent) and B3 consumables: the tool has no figure, so the sample quantities and prices are cleared and the
    sheet says "Chưa áp dụng" (norms, row names and column titles kept). B3 garbage: ESS9's units, rate and unit
    price (its total x 12 = ESS9 before VAT). B4: the RA1.A/RA2 devices and rates. B5: the RP1/RP2 monthly prices for
    this project; the reference-project part is not filled (it would name other projects)."""
    na = 'Chưa áp dụng.'
    # B2 scent
    ws = wb['B2. Mùi hương - Scent']
    for r in (6, 7, 8):
        ws.cell(row=r, column=7).value = None
        ws.cell(row=r, column=8).value = None
    _helper_note(ws, 11, 1, 'Chưa áp dụng: công cụ chưa tính chi phí máy tạo mùi hương cho dự án này; số lượng và '
                            'đơn giá mẫu của form đã được xoá.')

    # B3 consumables
    ws = wb['B3. Vật tư vệ sinh - Consumable']
    for r in range(6, 12):
        for c in (3, 11, 12, 13, 18):                          # C units, K:M unit prices, R notes on the sample
            ws.cell(row=r, column=c).value = None
    ws['R6'] = na
    for coord in ('Q13', 'M42', 'R43', 'R44'):                 # Q13: the form's own #REF!; the rest stray sample cells
        ws[coord] = None
    _helper_note(ws, 14, 1, 'Chưa áp dụng: công cụ chưa tính chi phí vật tư vệ sinh cho dự án này; số căn, số người '
                            'và đơn giá mẫu của form đã được xoá, giữ định mức.')

    # B3 garbage collection (ESS9)
    ws = wb['B3. Thu gom rác - Garbage coll ']
    waste = _HELPER_FIGURES.get('waste')
    for r, units_key, kg, product in ((5, 'apt_units', WASTE_APARTMENT_KG_PER_UNIT_DAY, 'Căn hộ'),
                                      (6, 'shop_units', WASTE_SHOPHOUSE_KG_PER_UNIT_DAY, 'Shophouse')):
        units = (waste or {}).get(units_key) or 0
        ws.cell(row=r, column=3).value = units or None
        ws.cell(row=r, column=5).value = 1 if units else None
        if units:
            k = ws.cell(row=r, column=11, value=f'={kg:g}*{WASTE_DAYS_PER_MONTH}*{WASTE_UNIT_PRICE}')
            k.number_format = '#,##0'
            ws.cell(row=r, column=13, value=(
                f"{product}: {units:,.0f} căn x 100% x {kg:g} kg/căn/ngày x {WASTE_DAYS_PER_MONTH} ngày x "
                f"{WASTE_UNIT_PRICE:,.0f} VND/kg (thu gom {WASTE_COLLECTION_PRICE:,.0f} + vận chuyển "
                f"{WASTE_TRANSPORT_PRICE:,.0f} + xử lý {WASTE_TREATMENT_PRICE:,.0f}, Quyết định 65/2026/QĐ-UBND, "
                f"trước VAT)."))
        else:
            ws.cell(row=r, column=11).value = None
            ws.cell(row=r, column=13).value = na
    for r in range(7, 11):
        ws.cell(row=r, column=13).value = na
    ws['J12'], ws['J49'], ws['A51'] = None, None, None
    ws['A50'] = (f"Đơn giá theo Quyết định 65/2026/QĐ-UBND: {WASTE_UNIT_PRICE:,.0f} VND/kg trước VAT. Tổng chi phí/"
                 f"tháng x 12 bằng dòng ESS9 trang '2. Budget-Management Fund' trước VAT." if waste else
                 'Dự án không có căn hộ hoặc shophouse: chưa áp dụng.')

    # B4 elevator and lobby advertising (RA1.A + RA2)
    ws = wb['B4. DT Quảng cáo - Elevator adv']
    for r in (5, 6):
        for c in (3, 5, 6, 7, 9, 10, 13):
            ws.cell(row=r, column=c).value = None
    ws['F13'] = None
    ws['B5'] = 'Sảnh tòa nhà/\nTower lobby'
    ws['B6'] = 'Sảnh tầng hầm/\nBasement lobby'
    place = {'Ad frame (tower lobby, inside elevator)': (5, 6, 7), 'LCD screen (tower lobby)': (5, 9, 10),
             'LCD screen (basement lobby)': (6, 9, 10)}
    ads = _HELPER_FIGURES.get('ads') or []
    notes = {5: [], 6: []}
    monthly = 0.0
    for a in ads:
        r, qc, pc = place[a['item']]
        ws.cell(row=r, column=qc).value = a['qty']
        ws.cell(row=r, column=pc, value=a['rate']).number_format = '#,##0'
        notes[r].append(f"{a['item_vi']}: {a['note']}")
        monthly += a['rate'] * a['qty']
    for r in (5, 6):
        ws.cell(row=r, column=13).value = '\n'.join(notes[r]) or na
    if project.get('passenger_elevators_per_tower'):
        ws['E5'] = project['passenger_elevators_per_tower'] * (project.get('towers') or 1)
    ws['M7'] = (f"Tổng/tháng x 12 = {monthly * 12:,.0f} VND/năm, bằng RA1.A + RA2 trang '2.2 Common area Fund'."
                if ads else na)

    # B5 parking prices
    ws = wb['B5. Đơn giá gửi xe - Parking pr']
    ws['B7'] = 'Chưa áp dụng (đơn giá đề xuất cho dự án ở mục B).'
    ws['B17'] = project['name']
    parking = _HELPER_FIGURES.get('parking') or {}
    parts = []
    for key, col, code, vi in (('car', 3, 'RP2', 'ô tô'), ('moto', 5, 'RP1', 'xe máy')):
        p = parking.get(key) or {}
        if p.get('recorded') is not None:
            ws.cell(row=17, column=col).value = na
            parts.append(f"{vi}: doanh thu thực tế PM nhập {p['recorded']:,.0f} VND/tháng (dòng {code}), không có "
                         f"đơn giá/xe")
        elif p.get('slots'):
            ws.cell(row=17, column=col, value=p['rate']).number_format = '#,##0'
            parts.append(f"{vi}: {p['rate']:,.0f} VND/xe/tháng, đơn giá dòng {code}")
        else:
            ws.cell(row=17, column=col).value = na
            parts.append(f"{vi}: dự án không có chỗ đậu")
        ws.cell(row=17, column=col + 1, value=na)               # transit fare: the tool has no figure
    ws['G17'], ws['H17'] = na, na                               # bicycle
    ws['I17'] = ('Đơn giá tháng theo trang "2. Budget-Management Fund": ' + '; '.join(parts)
                 + '. Giá vé lượt và xe đạp: chưa áp dụng.')


def fill_helper_sheets(wb, project, demand):
    """Fills the deliverable's helper sheets A2-A4 and B1-B5 from what fill_management_fund_sheet() and
    fill_common_area_fund_sheet() priced (design D15). Must run after both."""
    for cat in _POST_SHEETS:
        _fill_service_post_sheet(wb, project, cat)
    _fill_reception_calendar(wb, project, demand)
    _fill_b2_b5(wb, project)


def build_budget(project, demand, year):
    # Every product's rate is decided ONCE, here, by master_comparables.resolve_product_rates() —
    # the same function generate_project_output.py calls — and every place below that writes or
    # shows a rate reads it from `rates`: the RM.* rows (fill_management_fund_sheet), the '0. Info'
    # fee table and its complete-total note, and the Comparison sheet (change
    # use-operating-project-actuals, P5). Comparable matching runs on TOTAL building NFA; the
    # blended whole-property rate is the last-resort Apartment fallback for the rare project where
    # no comparable carries an Apartment rate at all (see the resolver's docstring).
    rates = resolve_product_rates(project)
    derived_rate, top2, rate_note = rates['apartment_rate'], rates['comparables'], rates['rate_note']
    # Which operating-project fields this run found, and the entered-vs-comparable rates (design D6).
    for line in operating_inputs.report_lines(
            project.get('operating') or operating_inputs.blank_inputs(), rates):
        print(line)

    own_real = next((c for c in MASTER_COMPARABLES
                      if c['name'].strip().lower() in project['name'].strip().lower()
                      and c['rates'].get('Apartment')), None)

    print(f"Comparables for {project['name']} (TotalNFA={project['total_nfa']:,.0f} m² — matching basis):")
    for c in top2:
        real = c['rates'].get('Apartment') or c['mgmt_rate']
        rate_str = f"{real:,} ({c['mgmt_rate_vat']})" if real else 'no real rate'
        print(f"  - {c['name']}: NFA={c['nfa']:,.0f}, delta={abs(c['nfa']-project['total_nfa']):,.0f}, rate={rate_str}")
    print(f"Derived Apartment mgmt fee rate: {derived_rate:,} VND/m²/month" + (f"  [{rate_note}]" if rate_note else ''))
    if own_real:
        real_apt = own_real['rates']['Apartment']
        gap = derived_rate - real_apt
        print(f"Reality check: {project['name']}'s own real Apartment rate is {real_apt:,} "
              f"({own_real['mgmt_rate_vat']}) — gap {gap:+,} ({gap/real_apt*100:+.0f}%)")

    local_template = os.path.join(tempfile.gettempdir(), 'template_2026_local.xlsx')
    shutil.copyfile(TEMPLATE_PATH, local_template)
    repaired = repair_workbook(local_template)
    wb = openpyxl.load_workbook(repaired, data_only=False)

    # The budget period (change apply-head-of-pm-decisions-2026-10, group 1): the fund sheet's twelve month columns
    # start from AH6 (its month headers and the ramp sheets all read it), so the template's own 01/09/2026-31/08/2027
    # was being shown beside a summary that said calendar 2027. One period, written to every place that shows it,
    # and AL5 (the budget year the narratives quote) is the period's first year.
    _period = project['budget_period']
    _fund = wb['2. Budget-Management Fund']
    _fund['AH6'] = datetime.datetime.combine(_period.first_day, datetime.time())
    _fund['AL6'] = datetime.datetime.combine(_period.last_day, datetime.time())
    _fund['AL5'] = _period.start_year
    wb['1. Summary']['H4'] = datetime.datetime.combine(_period.first_day, datetime.time())
    wb['1. Summary']['H5'] = datetime.datetime.combine(_period.last_day, datetime.time())

    # The AI Guideline's universal VAT-treatment sentence for this run — appended to every line-level
    # remark (via _write_remark -> _append_vat) and to every composed `1. Summary` narrative, or ''
    # when the fund sheet's "Mô hình tài chính" switch says figures exclude VAT (change
    # apply-guideline-remark-model). A module global so the many small remark writers need no new arg.
    global _ACTIVE_VAT_SENTENCE
    _ACTIVE_VAT_SENTENCE = _vat_sentence(wb, year)

    wb['2. Budget-Management Fund']['AH5'] = project['name']
    # A2/A3/A4/B2/B3(x2)/B4/B5 dropped from this loop — no formula anywhere reads their name cell
    # (confirmed by scanning every cross-sheet reference in the template). A5 and B1 are kept: those
    # are read elsewhere. Change reconcile-summary-with-detail-sheets, D4.
    for sheet, coord in [
        ('A5. Trợ cấp PCCC', 'B1'), ('B1. Lịch Lễ tân', 'B1'),
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

    # ---- 0. Info: user-input scale + derived rate. This is a DISPLAY sheet — its K column
    # (= I rate x D NFA) recomputes from what's written here, but nothing in the pipeline reads it;
    # each product's RM.* revenue is written straight to "2. Budget-Management Fund". The standard
    # form's fee table has one row per product: Apartment(8)/Officetel(9)/Office(10)/Shophouse(11)
    # (the superseded 202608 form had Shopping Mall at row 11 — change `rebase-output-onto-25-sheet-form`).
    # Each product with an area gets BOTH its scale AND its rate, priced by the SAME per-product
    # rates as the RM.* rows on the budget sheet (resolve_product_rates, Apartment-rate fallback), so
    # this sheet's K column agrees with the budget sheet. Shopping Mall / Retail / Shop Apartment /
    # Villas / Nursery have no row in this table — their revenue is on the budget sheet only, so the
    # K19 total here is the four-product subset, not the whole management fee.
    info = wb['0. Info']
    _INFO_FEE_ROWS = {'Apartment': 8, 'Officetel': 9, 'Office': 10, 'Shophouse': 11}
    for _prod, _row in _INFO_FEE_ROWS.items():
        _p = project['products'].get(_prod) or {}
        if not _p.get('nfa'):
            continue
        info[f'C{_row}'], info[f'D{_row}'], info[f'E{_row}'] = _p['gfa'], _p['nfa'], _p['units']
        # The applied rate from the one resolver (P5) — Apartment's carries the swing cap, so this
        # cell cannot drift from the RM.* rows or the analysis (the 2026-09-16 '0. Info'!I8 bug
        # was this cell recomputing the rate on its own).
        info[f'I{_row}'] = rates['products'][_prod]['rate']
        # G = 'Ghi chú' — the AI Guideline's own '0. Info' remark: per-product area basis + as-of
        # year (change complete-ai-guideline-remark-coverage). The PM's own citation when entered;
        # otherwise state the area is PM-supplied rather than invent a drawing/legal reference.
        _prod_vi = _PRODUCT_VI_LABEL.get(_prod, _prod)
        if project.get('area_basis'):
            _year_clause = f" năm {project['area_basis_year']}" if project.get('area_basis_year') else ''
            info[f'G{_row}'] = (f"Diện tích {_prod_vi} theo {project['area_basis']}. Cập nhật theo "
                                f"thông số Chủ Đầu Tư cung cấp{_year_clause}.")
        else:
            info[f'G{_row}'] = f"Diện tích {_prod_vi} do PM cung cấp — chưa có căn cứ bản vẽ/pháp lý cụ thể."
    # Products this project has that the standard form's 0.Info table cannot show (no row for them):
    # flag them so a reader knows the K19 total here is a subset, and where the full figure lives.
    _rowless = [p for p in PRODUCT_ROWS
                if p not in _INFO_FEE_ROWS and (project['products'].get(p) or {}).get('nfa')]
    if _rowless:
        info['G7'] = ("Also priced but not shown in this 4-product table (no row on the standard form): "
                      + ', '.join(_rowless) + ". Full management-fee revenue is on '2. Budget-Management "
                      "Fund' (rows RM.AP–RM.KG) and '1. Summary'.")
        # The disclosure above says the missing products' revenue is "elsewhere", but leaves TỔNG
        # CỘNG (row 19) reading as if it were the whole project — its own SUBTOTAL() formula sums
        # only rows 7:17 of a template that has no row for Villas/Nursery/etc. at all (change
        # move-gate-and-pool-count-fields sibling work, 2026-09-15; see docs/ audit of project GENZ).
        # The template genuinely cannot be extended — its row-7 SUBTOTAL range (C8:C12) and the
        # parking block starting at row 12 are baked into the file itself, not something this
        # generator controls, and this project's convention is never to edit the template to make
        # room. Rows 20+ are blank on every version of this sheet checked, so a second, COMPLETE
        # total is added there instead — same figures as row 19 would show if it could see every
        # product, at the same resolved rate (resolve_product_rates, apt-rate fallback) the real
        # RM.* revenue rows use, so this total and '2. Budget-Management Fund' cannot disagree.
        _rowless_total_gfa = _rowless_total_nfa = _rowless_total_units = _rowless_total_fee = 0.0
        _rowless_parts = []
        for _rp in _rowless:
            _rinfo = project['products'].get(_rp) or {}
            _rnfa = _rinfo.get('nfa') or 0
            _rrate = rates['products'][_rp]['rate']
            _rfee = _rrate * _rnfa
            _rowless_total_gfa += _rinfo.get('gfa') or 0
            _rowless_total_nfa += _rnfa
            _rowless_total_units += _rinfo.get('units') or 0
            _rowless_total_fee += _rfee
            _rowless_parts.append(f"{_PRODUCT_VI_LABEL.get(_rp, _rp)}: {_rfee:,.0f} đ/tháng "
                                  f"({_rrate:,.0f} đ/m² x {_rnfa:,.0f} m²)")
        info['B21'] = 'TỔNG CỘNG THỰC TẾ (toàn bộ sản phẩm)'
        info['C21'] = f'=C19+{_rowless_total_gfa:g}'
        info['D21'] = f'=D19+{_rowless_total_nfa:g}'
        info['E21'] = f'=E19+{_rowless_total_units:g}'
        info['K21'] = f'=K19+{_rowless_total_fee:g}'
        for _col in ('C21', 'D21', 'E21', 'K21'):
            info[_col].number_format = '#,##0'
        info['G21'] = ("Dòng TỔNG CỘNG ở trên (hàng 19) không có chỗ cho " + ', '.join(_rowless) +
                       " trên mẫu chuẩn Savills, nên dòng này cộng thêm: " + '; '.join(_rowless_parts) +
                       ". Đơn giá tính theo cùng phương pháp với các sản phẩm khác "
                       "(2 dự án tương đồng gần nhất, dự phòng theo đơn giá Apartment nếu không có "
                       "dự án tương đồng cho sản phẩm này) — khớp với doanh thu thực tại '2. "
                       "Budget-Management Fund'.")
    info['F12'] = project['car_slots']
    # I12 (parking mgmt fee/m²) left blank -- no consistent real per-project reference was found
    # across comparables (each real file's own parking fee differs and isn't NFA-comparable the
    # way the apartment fee is); PM to confirm before this line item is trusted.

    # ---- 2. Budget-Management Fund: real computed OPEX/Capex/Staff/Parking/Management-Fee
    # numbers — see MGMT_FUND_ROWS and fill_management_fund_sheet()'s docstring above. ----
    _ZERO_REASONS.clear()
    _CATCH_ALL_REASONS.clear()
    _UNIT_RATES.clear()
    _ENTERED_RATE_VAT.clear()
    _HELPER_FIGURES.clear()
    # Existing-project mode (change carry-forward-staffing): computed once here, before the fund
    # sheet, because EMH2's formula needs to know how many A1 rows go below the table.
    existing = existing_result(project, demand, _budget_year(wb, year))
    if existing and not existing.duty:
        print(f"WARNING  Existing project: the '{existing_staffing.SEC_DUTY}' table is empty. EMH3 is "
              + (f"carried at the approved {existing.prior_year} amount" if existing.lines['EMH3'].kind == 'carried'
                 else '0') + ' and its remark says so; the tool does not infer duty counts from the shift codes.')
    existing_layout = _existing_a1_layout(wb, existing) if existing else None
    # Existing-project EEE.C / EEW.C (change carry-forward-common-utilities): computed once, on the VAT
    # basis the switch above set; fill_management_fund_sheet() and the '1. Summary' narrative read it.
    project['utilities_result'] = utilities_result(project, _budget_year(wb, year), bool(_ACTIVE_VAT_SENTENCE))
    fill_management_fund_sheet(wb, project, demand, year, rates,
                               existing=existing, existing_layout=existing_layout)
    # A project without apartments or without parking bays (change support-villa-only-and-no-parking).
    _fill_product_mix_fallbacks(wb, project)

    # ---- 2.2 Common area Fund: real elevator/lobby advertising revenue — see
    # COMMON_AREA_FUND_ROWS and fill_common_area_fund_sheet()'s docstring above. ----
    fill_common_area_fund_sheet(wb, project)

    # ---- A2-A4, B1-B5 helper sheets: this project's own posts, reception calendar and helper figures, from what
    # the two fund sheets just priced (change apply-head-of-pm-decisions-2026-10, D15). No formula outside these
    # sheets reads them, so no fund figure can move. ----
    fill_helper_sheets(wb, project, demand)

    # ---- 1. Staff cost: real per-position headcount/salary from Staffing Demand, mapped onto
    # the PM's own payroll-calculator sheet — see fill_staff_cost_sheet()'s docstring above. ----
    if existing:
        fill_existing_staff_sheets(wb, existing, existing_layout)
    else:
        fill_staff_cost_sheet(wb, project, demand, year)

    # ---- '4. Điều chỉnh' (docs/32): the parent rows and sub-rows of every fund line written above, read while the
    # figures are still numbers; budget_adjustment.apply() builds the sheet right before the save. ----
    import adjustment_detail
    _adjust_items = adjustment_detail.collect(wb, project, demand)

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

    # ---- 1. Summary column K: the AI Guideline's composed, Vietnamese, client-facing narrative for
    # every non-zero PART-1 total — replaces the template's blank / single-line-pull K cells (change
    # apply-guideline-remark-model). Reads back what the fills wrote; composes plain text. Runs
    # BEFORE _normalise_all_remark_columns() so the (much taller) K rows are sized, and AFTER
    # _fix_fake_formula_strings() for the same leaked-"=" reason as the sweep. Display only. ----
    _compose_summary_narratives(wb, project, demand, year, _collect_written(wb))

    # ---- Two caveat notes near the header block, no figure change (change
    # reconcile-summary-with-detail-sheets, D6): the chargeable-area figure at H10 is the 4-product
    # '0. Info' subset (mirrors the same caveat already written to '0. Info'!G7 when a rowless
    # product exists — see PRODUCT_ROWS / _INFO_FEE_ROWS above); and common-area advertising revenue
    # lives on a different fund entirely, so a reader looking for it on this sheet is told where.
    summary_ws = wb['1. Summary']
    area_note = ("Diện tích thu phí trên đây (H10) chỉ gồm 4 sản phẩm có dòng trên '0. Info' "
                 "(Căn hộ/Officetel/Office/Shophouse).")
    if _rowless:
        area_note += (" Dự án này còn có " + ', '.join(_rowless)
                       + " — được định giá tại '2. Budget-Management Fund' nhưng không cộng vào "
                         "diện tích/doanh thu hiển thị ở đây.")
    k10 = summary_ws.cell(row=10, column=_SUMMARY_K_COL, value=area_note)
    k10.alignment = Alignment(wrap_text=True, vertical='top')
    k11 = summary_ws.cell(row=11, column=_SUMMARY_K_COL, value=(
        "Doanh thu quảng cáo khu vực chung (LCD/Frame) được hạch toán tại '2.2 Common area Fund' — "
        "một quỹ riêng — không nằm trong quỹ quản lý vận hành này."))
    k11.alignment = Alignment(wrap_text=True, vertical='top')

    # ---- Remarks columns: render every note (written here, and pulled across to '1. Summary' /
    # the Report sheets) as wrapped text, not '########'. Runs AFTER _fix_fake_formula_strings so a
    # remark that leaked a leading "= " is already plain text and its length measures correctly. ----
    _normalise_all_remark_columns(wb)

    out_filename = f"{project['name']} - Sample Consulting Budget.xlsx"
    local_out = os.path.join(tempfile.gettempdir(), out_filename)
    # '4. Điều chỉnh' is built last: it turns the fund lines' month cells into formulas, which every reader above
    # (the narratives, _collect_written) needs as numbers. Skipped when the sheet module is not present.
    try:
        import budget_adjustment
    except ImportError:
        budget_adjustment = None
    if budget_adjustment is not None:
        budget_adjustment.apply(wb, _adjust_items)
    wb.save(local_out)
    print('Saved locally:', local_out)

    add_comparison_sheet(local_out, project, top2, derived_rate, rate_note, own_real, rates=rates)

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


def add_comparison_sheet(path, project, comparables, derived_rate, rate_note, own_real, rates=None):
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

    # Client deliverable: this project's own figures only. No column past B, no reference project's
    # name, rate or fee per apartment (change apply-head-of-pm-decisions-2026-10, D3/D14). The peer
    # columns live on the internal analysis's Comparison sheet (generate_project_output.py
    # build_comparison_sheet). check_benchmark_reconciles fails if anything is written past column B.
    from master_comparables import comparable_match_basis, SIZE_SIMILARITY_BAND
    # No input_nfa: with it the phrase names any badly-sized comparable; the neutral sentence below
    # says the same without the name.
    match_basis = comparable_match_basis(comparables, project.get('district'), project.get('city'),
                                          input_lat=project.get('lat'), input_lon=project.get('lon'))
    _n_ref = len(comparables)
    _oversized = bool(project.get('total_nfa')) and any(
        abs(c['nfa'] - project['total_nfa']) / project['total_nfa'] > SIZE_SIMILARITY_BAND for c in comparables)

    ws['A1'] = f"PROPOSAL BENCHMARK — {project['name']}"
    ws['A1'].font = Font(bold=True, size=13)
    ws.merge_cells('A1:B1')
    ws['A2'] = (f'The Apartment management-fee rate is set from the real Apartment rates of {_n_ref} reference '
                f'project(s) in Savills\' reference list, ranked by {match_basis}. The reference projects are not '
                'named here; the internal analysis lists them. This sheet shows this proposal\'s own figures — '
                'fee per apartment, year-1 revenue, whether the operating budget balances — and where the fee '
                'sits against the reference projects.'
                + (f' At least one reference project differs from this project\'s Total NFA by more than '
                   f'{SIZE_SIMILARITY_BAND:.0%} — no closer-sized one exists in the current data.' if _oversized else ''))
    ws['A2'].font = Font(italic=True, color='595959')
    ws['A2'].alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
    ws.merge_cells('A2:B2')
    ws.row_dimensions[2].height = 72

    r = 4
    for c, h in enumerate(['Metric', project['name']], start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center
        cell.border = border
    r += 1

    def section(row, label):
        ws.cell(row=row, column=1, value=label).font = section_font
        for c in range(1, 3):
            ws.cell(row=row, column=c).fill = section_fill
            ws.cell(row=row, column=c).border = border
        return row + 1

    def data_row(row, label, value, fill=None):
        for col, v in ((1, label), (2, value)):
            cell = ws.cell(row=row, column=col, value=v)
            cell.border = border
            cell.alignment = left if col == 1 else center
            if fill:
                cell.fill = fill
        return row + 1

    _proj_total_units = sum((p.get('units') or 0) for p in project['products'].values())
    _proj_products = [name for name in PRODUCT_ROWS if (project['products'].get(name) or {}).get('nfa')]

    def _density(units, nfa):
        return round(units / nfa * 1000, 1) if (units and nfa) else '—'

    r = section(r, 'OVERVIEW — this project')
    if project.get('address'):
        # Citation only — not a matching input (see build_project_input_form.py's comment on this
        # field for why it isn't geocoded).
        r = data_row(r, 'Address', project['address'])
    r = data_row(r, 'Total building NFA (m²) — the matching basis', project['total_nfa'])
    r = data_row(r, 'Apartment NFA (m²)', project['apartment_nfa'])
    r = data_row(r, 'Apartment units', project['apartment_units'])
    r = data_row(r, 'Total units (all products)', _proj_total_units)
    r = data_row(r, 'Density (apartment units per 1,000 m² NFA)',
                 _density(project['apartment_units'], project['total_nfa']))
    r = data_row(r, 'Product types', ', '.join(_proj_products) or '—')

    r += 1
    r = section(r, 'APARTMENT MANAGEMENT FEE RATE')
    _entered = (rates or {}).get('apartment_entered')
    _fallback = (rates or {}).get('apartment_source') == 'blended-fallback' or 'fell back to the whole-property' in (rate_note or '')
    if _entered:
        # P1: the reference projects' rate stays for reference; the applied rate is the PM's.
        _model = rates.get('apartment_comparable_rate')
        r = data_row(r, 'MODEL-DERIVED Apartment rate (this project, reference only)',
                     f'{_model:,}' if _model else 'none (no reference rate)')
        r = data_row(r, f"APPLIED Apartment rate — PM-entered actual rate ({_entered['vat']})",
                     f'{derived_rate:,}', fill=reality_fill)
    else:
        r = data_row(r, 'MODEL-DERIVED Apartment rate (this project)', f'{derived_rate:,}', fill=reality_fill)
    # The raw derivation note can name a reference project or quote its rate; it stays in the analysis.
    _how = ('No reference project has a real Apartment rate — the model rate is the whole-property blended rate of '
            'the reference projects.' if _fallback else
            f'The model rate is the average of the real Apartment rates of {_n_ref} reference project(s), on one '
            f'VAT basis.')
    r = data_row(r, 'How the rate is set',
                 ('The PM entered the actual rate, which is applied. ' if _entered else '') + _how)
    if own_real:
        real_apt = own_real['rates']['Apartment']
        gap = derived_rate - real_apt
        gap_pct = gap / real_apt * 100
        r = data_row(r, f"{project['name']}'s ACTUAL real Apartment rate (reality check)",
                     f"{real_apt:,} ({own_real['mgmt_rate_vat']})", fill=reality_fill)
        r = data_row(r, 'Gap (derived − real)', f'{gap:+,} VND  ({gap_pct:+.0f}%)', fill=reality_fill)
    else:
        r = data_row(r, 'Reality check', 'Not applicable — new prospect, no independently known real rate')

    # ---- PROPOSAL BENCHMARK — the figures a bid conversation uses: fee per apartment, year-1
    # revenue, and whether the operating budget balances. The money cells are FORMULAS into
    # '1. Summary', so the benchmark carries the deliverable's own figures forward instead of
    # restating them (change benchmark-proposal-against-comparables — design D1). Coverage is the
    # operating fund only; the sinking fund / capex reserve is a separate ring-fenced fund. ----
    _S = "'1. Summary'"
    _ratio = f"{_S}!H{_SUMMARY_ROW_OPERATING_SURPLUS}/{_S}!H{_SUMMARY_ROW_OPERATING_INCOME}"

    def note_row(row, text, height=30):
        cell = ws.cell(row=row, column=1, value=text)
        cell.font = Font(italic=True, color='595959')
        cell.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
        ws.cell(row=row, column=1).border = border
        ws.row_dimensions[row].height = height
        return row + 1

    def money_row(row, label, value, fill=None):
        nr = data_row(row, label, value, fill=fill)
        ws.cell(row=row, column=2).number_format = '#,##0'
        return nr

    r += 1
    r = section(r, 'PROPOSAL BENCHMARK — is the proposed fee defensible in a bid?')
    r = note_row(r,
        "PEER COMPARISON: where the proposed fee sits (verdict below) is drawn from the reference "
        "projects' real Apartment rates, which the internal analysis lists. INTERNAL CHECK: the "
        "coverage rows test this project's own budget — operating fund only; the sinking fund / capex "
        "reserve is a separate ring-fenced fund and is not included. This project's operating cost is "
        "its own estimate, built from reference-property ratios, so coverage confirms the budget "
        "balances — it is a consistency check, not a market benchmark.",
        height=86)

    apt_nfa = project.get('apartment_nfa') or 0
    apt_units = project.get('apartment_units') or 0
    # On the basis the rate was averaged on (excl.-VAT rates converted, group 4), not as quoted.
    comp_apt_rates = (rates or {}).get('apartment_rates_on_basis') or \
        [(c.get('rates') or {}).get('Apartment') for c in comparables]

    if apt_nfa and apt_units:
        this_fpa = round(derived_rate * apt_nfa / apt_units)
        r = data_row(r, 'Management fee per apartment (VND/month)', f'{this_fpa:,}')
        r = note_row(r,
            f"{derived_rate:,.0f} VND/m²/month × {apt_nfa / apt_units:,.0f} m² average apartment NFA "
            f"(apartment NFA ÷ apartment units).")
    else:
        r = data_row(r, 'Management fee per apartment (VND/month)', '— (this project has no apartments)')

    r = money_row(r, 'Year-1 management-fee revenue (VND)', f"={_S}!H{_SUMMARY_ROW_MGMT_FEE}")
    r = money_row(r, 'Year-1 total operating income (VND) — fee + parking + other',
                  f"={_S}!H{_SUMMARY_ROW_OPERATING_INCOME}")
    r = money_row(r, 'Year-1 total operating cost (VND) — before Savills’ fee',
                  f"={_S}!H{_SUMMARY_ROW_OPERATING_COST}")
    r = money_row(r, 'Year-1 operating surplus (VND) — before Savills’ fee & tax',
                  f"={_S}!H{_SUMMARY_ROW_OPERATING_SURPLUS}", fill=reality_fill)
    _pct_r = r
    r = data_row(r, 'Operating surplus as % of operating income', f"={_ratio}", fill=reality_fill)
    ws.cell(row=_pct_r, column=2).number_format = '0.0%'
    r = data_row(r, f'Coverage band  ({COVERAGE_BAND_LABEL})',
                 f'=IF({_ratio}<0,"shortfall",IF({_ratio}<{COVERAGE_BAND_THIN_MAX},"thin",'
                 f'IF({_ratio}<{COVERAGE_BAND_NORMAL_MAX},"normal","generous")))',
                 fill=reality_fill)

    # -- Verdict: one line. Fee-vs-range is known now; the balance clause is a live IF on H46. --
    fee_clause = _benchmark_fee_clause(derived_rate, comp_apt_rates, entered=bool(_entered))
    verdict = (f'="{fee_clause}"'
               f'&IF({_S}!H{_SUMMARY_ROW_OPERATING_SURPLUS}<0,'
               f'" The operating budget does NOT balance before Savills’ fee.",'
               f'IF({_ratio}<{COVERAGE_BAND_THIN_MAX},'
               f'" The operating budget balances before Savills’ fee, but the surplus is thin.",'
               f'" The operating budget balances before Savills’ fee with a workable surplus."))')
    ws.cell(row=r, column=1, value='VERDICT').font = Font(bold=True)
    vcell = ws.cell(row=r, column=2, value=verdict)
    vcell.font = Font(bold=True)
    vcell.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
    ws.cell(row=r, column=1).fill = PatternFill('solid', start_color='FFF2CC', end_color='FFF2CC')
    ws.cell(row=r, column=1).border = border
    ws.cell(row=r, column=2).fill = PatternFill('solid', start_color='FFF2CC', end_color='FFF2CC')
    ws.cell(row=r, column=2).border = border
    ws.row_dimensions[r].height = 78
    r += 1

    r += 1
    # The file name is the analysis workbook's label; the client's Comparison sheet names the thing.
    r = section(r, f"SERVICE RATES ({RATE_CARD_SOURCE.replace('Fact_MasterRateCard.csv', 'standard rate card')})")
    r = data_row(r, 'Security (VND/post/month)', f'{SECURITY_RATE_CITYWIDE:,}')
    r = data_row(r, 'Cleaning (VND/post/month)', f'{CLEANING_RATE_CITYWIDE:,}')
    r = data_row(r, 'Landscape (VND/post/month)', f'{LANDSCAPE_RATE_CITYWIDE:,}')

    widths = {'A': 54, 'B': 60}
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
        ('Ratio — Cleaning: m² Fee-paying NFA per Cleaning Staff', ratios['nfa_per_cleaning_staff']),
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
    # Change new-prospect-paid-holidays: name the law the computed dates follow.
    from vn_holidays import LAW_NOTE_VN
    ws0['B23'] = (f'{LAW_NOTE_VN} Ngày nhập tay tại Roster Setup (nếu có) thay cho danh sách tự tính.')
    ws0['B23'].alignment = Alignment(wrap_text=True, vertical='top')
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
