"""Coverage and method-fidelity measurement (change report-method-coverage-in-verification).

Answers two questions nothing in `verify.py` asked before this change:
  - Do we fill the line at all? (coverage, against real reference budgets — never against the
    pipeline's own output, which would report 100% and mean nothing; design.md D4)
  - Do we use the method the costing spec states? (method fidelity, against a recorded human
    judgement per code — never inferred at run time; design.md D1)

This module measures. It does not change any figure, method or cost code (proposal.md, "What
Changes... Deliberately not in scope"), and it does not fail a run for a low score — only a
*missing* verdict fails (design.md D2/D3).
"""
import csv
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_SOURCE_CODE = os.path.dirname(_HERE)
_BUDGET_AGENT = os.path.dirname(_SOURCE_CODE)

# Real project budgets held for this purpose (input/budget_planning/ — gitignored, same handling as
# every other real client workbook this repository reads; design.md D6). Read-only.
_11D_PATH = os.path.join(
    os.path.dirname(_BUDGET_AGENT), 'input', 'budget_planning',
    '20232710 - Dự án 11D Thi Sách Nội bộ (final).xlsx')
_GREEN_SKYLINE_PATH = os.path.join(
    os.path.dirname(_BUDGET_AGENT), 'input', 'budget_planning',
    '20260204 - Budget - Green Skyline ngân sách Pre +Operation năm 1__repaired.xlsx')
# The '__repaired' copy is used directly (not the original) — the original carries the same
# OneDrive-zip corruption documented in docs/*-onedrive-corruption*.md and openpyxl cannot open it
# at all (`ValueError: ... could not assign names ... invalid XML`), confirmed by hand 2026-09-17.
# Both files: real client figures, per design.md D6 — never copied elsewhere, read in place.

# Both reference projects turned out to be residential apartment properties (confirmed 2026-09-17
# by reading each file's own Info sheet directly — 11D: 157 "Căn hộ" units; Green Skyline: 1,251
# "Apartment" units, 0 office/retail area in either) — design.md's risk section describes "one
# office and one residential", which does not match either file found under input/budget_planning/
# today. Not corrected in design.md by this change (that document is a record of the 2026-09-09
# proposal, not something this change rewrites) — flagged here so a reader of this module does not
# inherit the stale premise. Task 4.2's actual requirement — report each project separately, never
# average them into one figure — is followed regardless of property type, since two limited,
# residential-only reference points still should not be blended.
REFERENCE_BUDGETS = {
    '11D Thi Sách': dict(
        path=_11D_PATH,
        sheet='B2.Chi tiết dự toán ngân sách',
        header_row=13,       # row 13: 'No/ Stt' | 'CODE' | 'ITEMS' | 'Estimate Budget of Year 1'
        code_col=6,           # F
        indicator_col=5,      # E — populated marks a rollup/section-header row; blank marks a leaf
        value_col=8,          # H — 'Estimate Budget of Year 1 (Excluding VAT)'
        data_start_row=14,
        sentinel_codes=('RM.AP', 'EMH1', 'ESS1'),   # must appear in code_col, or the layout moved
        # design.md D5's reconciliation anchor: the three top-level, mutually exclusive branches
        # under this budget's own "PART 1"/"PART 2" split — R (revenue, row 17), E (total operating
        # expense, row 98, itself = EM+ES+EN+EE+ER+ESH+ESP, confirmed by direct arithmetic), D (tax,
        # row 516). Anchored by ROW rather than by code: D's own row carries its hierarchy-indicator
        # value ('D') but no code at all in the code column, so it cannot be found by code lookup
        # like R and E can. Confirmed this is the complete set: nothing with a code exists past PL2
        # (the final derived P&L row).
        top_level_anchor_rows=(17, 98, 516),
        # Codes whose hierarchy-indicator column is BLANK (so they read like a leaf by the normal
        # signal) but are genuinely unmarked rollups whose own stated value double-counts against
        # real children found by an exact code-prefix + matching-value search — e.g. RA1 (row 42)
        # and RA1.A (row 43) carry the identical 123,272,727.27, and ESS9 (row 162) exactly equals
        # the sum of ESS9.A/S/0/P. Specific to this file's own hand-added summary rows, not a
        # codebook-wide pattern (Green Skyline has a different one, ERF10, not these two).
        rollup_despite_no_indicator=frozenset({'RA1', 'ESS9'}),
    ),
    'Green Skyline': dict(
        path=_GREEN_SKYLINE_PATH,
        sheet='2a.Budget-MF 12 months (year 1)',
        header_row=9,          # row 9: 'No\nStt' | 'CODE\nMã' | 'ITEMS' | ...
        code_col=26,           # Z
        indicator_col=25,      # Y
        value_col=38,          # AL — 'Total Budget of Year 12 months (Year 01)'
        data_start_row=11,
        sentinel_codes=('RM.AP', 'EMH1', 'ESS1'),
        # Same three-branch anchor as 11D, by row: R (row 12), E (row 77), D (row 493). D again has
        # no code in the code column, only in the hierarchy-indicator column.
        top_level_anchor_rows=(12, 77, 493),
        # ERF10 (row 458) exactly equals the sum of ERF10.1-4 — this file's own equivalent of 11D's
        # RA1/ESS9 (an unmarked summary row), found independently by the same code-prefix search.
        rollup_despite_no_indicator=frozenset({'ERF10'}),
    ),
}

# Codes whose hierarchy-indicator column IS populated (so they read like a rollup by the normal
# signal) but are genuinely single leaf line items, not section headers with children beneath them
# — discovered by hand while building the 2026-09-17 gap analysis in 05-decisions.md (EM#/ES#/EE#),
# and independently while building this module (ESR): both files' EM#/ES#/EE# figures reproduce
# that document's own Green Skyline/11D totals (88,455,588 and 102,370,162) to the VND once treated
# as leaves, and both files' own top-level (R+E+D) totals only reconcile exactly once ESR is treated
# as a leaf too — confirmed present, childless and identically shaped in both reference files, so
# kept here as one shared, codebook-wide set rather than duplicated per file. This is data with a
# comment, not a regex (design.md D5) — any future code added here needs the same kind of
# confirmation, not a guess from the shape of the code string.
_LEAF_DESPITE_INDICATOR = frozenset({'EM#', 'ES#', 'EE#', 'ESR'})

_RECONCILE_TOLERANCE = 1.0  # VND — both files store values as floats with float rounding noise


class ReferenceLayoutError(RuntimeError):
    """A reference budget's columns could not be confirmed — refuses to load rather than guess.

    Raised when none of a project's sentinel codes are found in the configured code column, which
    is the condition task 2.2 requires: 'a file whose layout is not recognised fails to load rather
    than loading the wrong columns'.
    """


class ReferenceReconciliationError(RuntimeError):
    """The sum of extracted leaf values did not reconcile against the budget's own section totals."""


def extract_reference_budget(name):
    """Return `{code: {'value': float, 'sheet': str, 'row': int, 'item': str}}` for every LEAF cost
    code in the named reference budget (rollups/section headers excluded; design.md D5).

    Raises ReferenceLayoutError if the configured columns don't contain the expected sentinel
    codes (task 2.2), or ReferenceReconciliationError if the extracted leaves don't sum to the
    budget's own top-level section totals (task 2.1).
    """
    import openpyxl
    import warnings

    cfg = REFERENCE_BUDGETS[name]
    if not os.path.exists(cfg['path']):
        raise FileNotFoundError(
            f"Reference budget for {name!r} not found at {cfg['path']!r}. This file is real client "
            f"data held under input/budget_planning/ (design.md D6) — it is not tracked in git and "
            f"must exist on this machine for coverage/fidelity measurement to run at all.")

    with warnings.catch_warnings():
        warnings.simplefilter('ignore')  # the repaired Green Skyline file still carries a few
        # unrelated bad-date warnings on unrelated cells (H149/H199 etc.) — harmless, not this
        # code's concern, and noisy enough on every run to suppress deliberately rather than let
        # verify.py's output imply something is wrong with THIS file every time it runs.
        wb = openpyxl.load_workbook(cfg['path'], data_only=True)
    ws = wb[cfg['sheet']]

    # ---- task 2.2: confirm the layout before trusting it ----
    found_codes = set()
    for r in range(cfg['header_row'], ws.max_row + 1):
        c = ws.cell(row=r, column=cfg['code_col']).value
        if isinstance(c, str) and c.strip():
            found_codes.add(c.strip())
    missing_sentinels = [s for s in cfg['sentinel_codes'] if s not in found_codes]
    if missing_sentinels:
        raise ReferenceLayoutError(
            f"{name}: none of the expected sentinel codes {missing_sentinels} were found in column "
            f"{cfg['code_col']} of sheet {cfg['sheet']!r}. The file's layout does not match what "
            f"this extractor was configured for — refusing to load rather than reading the wrong "
            f"columns. Re-check REFERENCE_BUDGETS' code_col/indicator_col/value_col/header_row "
            f"against the file directly before changing this.")

    # ---- extract every leaf row, tracking rollup totals for the reconciliation check (2.1) ----
    rollup_despite_no_indicator = cfg.get('rollup_despite_no_indicator', frozenset())
    leaves = {}
    rollup_totals = {}   # code -> its OWN stated value, for every rollup row seen
    for r in range(cfg['data_start_row'], ws.max_row + 1):
        code = ws.cell(row=r, column=cfg['code_col']).value
        if not (isinstance(code, str) and code.strip()):
            continue
        code = code.strip()
        indicator = ws.cell(row=r, column=cfg['indicator_col']).value
        value = ws.cell(row=r, column=cfg['value_col']).value
        if not isinstance(value, (int, float)):
            value = 0.0
        is_rollup = ((bool(indicator) and code not in _LEAF_DESPITE_INDICATOR)
                     or code in rollup_despite_no_indicator)
        if is_rollup:
            rollup_totals[code] = float(value)
            continue
        item = ws.cell(row=r, column=cfg['code_col'] + 1).value
        leaves[code] = dict(value=float(value), sheet=cfg['sheet'], row=r,
                             item=str(item).strip() if item else None)

    # ---- task 2.1: reconcile the extracted leaves against the budget's own top-level totals ----
    # Every leaf belongs under exactly one of the top-level rollups (design.md doesn't require a
    # full recursive per-branch check; this is the single check strong enough to catch a systematic
    # extraction error — e.g. a whole section silently skipped or double-counted — without needing
    # to parse this file's mixed letter/roman/arabic hierarchy-id scheme into a full tree). Anchored
    # by row, not by code, since one of the three (tax) carries no code of its own.
    anchor_values = [ws.cell(row=r, column=cfg['value_col']).value for r in cfg['top_level_anchor_rows']]
    top_total = sum(v for v in anchor_values if isinstance(v, (int, float)))
    leaf_total = sum(v['value'] for v in leaves.values())
    if abs(leaf_total - top_total) > _RECONCILE_TOLERANCE:
        raise ReferenceReconciliationError(
            f"{name}: sum of {len(leaves)} extracted leaf codes = {leaf_total:,.2f}, but the "
            f"budget's own top-level section totals (rows {cfg['top_level_anchor_rows']}) = "
            f"{top_total:,.2f} — off by {leaf_total - top_total:,.2f}. A systematic extraction "
            f"error (a section skipped, double-counted, or a rollup mis-classified as a leaf) is "
            f"more likely than the two figures genuinely disagreeing.")

    return leaves


def write_site_codes():
    """Every cost code this pipeline currently writes to, derived from the pipeline's own row
    mappings (task 3.2) — not a second, hand-maintained list that could silently drift from them.
    """
    import generate_project_budget as gpb
    codes = set(gpb.MGMT_FUND_EXPECTED_CODE.values())
    codes.update(gpb.PRODUCT_REVENUE_EXPECTED_CODE.values())
    return codes


# ---- Method verdicts: a recorded human judgement per code, held against reality by
# check_method_verdicts() below — never inferred at run time (design.md D1/D3.5). `spec_method` is
# Costing_Method_Catalogue.csv's own `method` column, the spec's stated basis for that code (or an
# explicit note when the catalogue has no entry at all). `actual_method` is what the pipeline
# genuinely does today, read from the source, not assumed. `verdict` is 'matches', 'partial', or
# 'mismatch'. `reasoning` says why.
#
# Recorded 2026-09-17. Supersedes proposal.md's 2026-09-09 hand count (68.7% matches / 31.0%
# mismatch, the 31.0% entirely EEE.C/EEW.C/EED.C) for a specific, investigated reason, not a
# silent drift: `cost-energy-from-consumption-and-tariff` archived the very next day, 2026-09-10,
# and rewired exactly those three codes onto consumption x tariff — which is what the catalogue has
# stated as their method all along. Confirmed directly against estimate_opex.py's own docstring
# ("Electricity/Water/Diesel: consumption x tariff... change cost-energy-from-consumption-and-
# tariff") before changing their verdict here — this is task 4.5's "investigate the difference
# rather than adjust the expectation," not an assumption that today's code must be better.
METHOD_VERDICTS = {
    # ---- Revenue: management fee per product (PRODUCT_REVENUE_ROWS) ----
    **{code: dict(
        spec_method='area-x-rate',
        actual_method='Fee area (0. Info) x applied rate (0. Info), written month by month via the '
                       'Schedule columns — the pipeline\'s build_management_fund_sheet does exactly '
                       'this for every priced product.',
        verdict='matches',
        reasoning='Direct implementation of the catalogue\'s own stated method; no divergence found.',
    ) for code in ('RM.AP', 'RM.OT', 'RM.OF', 'RM.SM', 'RM.RE', 'RM.SA', 'RM.SH', 'RM.VI', 'RM.KG')},

    'RM.0A': dict(
        spec_method='developer-covers-unlet',
        actual_method='Mirrors the resident fill-up curve — the developer\'s share is exactly the '
                       'unlet share of the same product each month, from the same fill-up model RM.AP '
                       'already uses.',
        verdict='matches',
        reasoning='Same fill-up curve as the product revenue it mirrors; no separate derivation to '
                   'drift from it.',
    ),

    # ---- Management-fee expense / staff (EMH family) ----
    'EMH1': dict(
        spec_method='contract-fixed-or-cpi-or-nfa',
        actual_method='Written as a literal 0 — deliberately left blank until a real management-fee '
                       'contract exists (docs/05-decisions.md: "Savills\' own management fee stays '
                       'blank until contract terms arrive"). None of the three bases the spec states '
                       '(fixed fee, CPI escalation, NFA x unit price) is computed.',
        verdict='mismatch',
        reasoning='Zero is a placeholder, not one of the three stated bases — flagged rather than '
                   'silently counted as satisfying any of them. Surplus/EMH already carries this '
                   'caveat on every deliverable (docs/project-status.md §5, item D1).',
    ),
    'EMH2': dict(
        spec_method='a1-live-formula-plus-unplaced-rows',
        actual_method='A live formula into the deliverable\'s own "A1. Staff cost" sheet (AC96) plus '
                       'real, individually-priced rows for any position A1 has no row-group for '
                       '(change reconcile-summary-with-detail-sheets D2, 2026-09-17).',
        verdict='matches',
        reasoning='The catalogue\'s own method key was written to describe this exact mechanism; '
                   'confirmed directly against the live formula string in a freshly generated '
                   'deliverable (Fund!F83) the same day this verdict was recorded.',
    ),
    'EMH4': dict(
        spec_method='regulation-driven',
        actual_method='Mandatory annual ATLĐ/PCCC training + officer allowance, from sheet "A5. Trợ '
                       'cấp PCCC" (change fill-guideline-required-line-items, 2026-09-14).',
        verdict='matches',
        reasoning='Regulation-driven figure sourced from the named sheet, as the catalogue states.',
    ),

    # ---- Parking revenue ----
    **{code: dict(
        spec_method='bays-x-fill-x-rate',
        actual_method='Bays x monthly fill % x rate, written month by month via the Schedule columns '
                       '— the pipeline\'s fill_management_fund_sheet computes exactly this from the '
                       'same fill-up curves used elsewhere on the deliverable.',
        verdict='matches',
        reasoning='Direct implementation; fill curves are the same ones the parking fill-up sheet '
                   'itself displays, not a second, undocumented estimate.',
    ) for code in ('RP1', 'RP2')},

    # ---- Outsourced services ----
    'ESS1': dict(
        spec_method='contract-posts-x-24h-rate',
        actual_method='Posts x citywide 24h post rate x 12, blended for night differential, headcount '
                       'and shift hours read from the roster sheet.',
        verdict='matches',
        reasoning='Direct implementation of the catalogue\'s stated basis.',
    ),
    'ESS4': dict(
        spec_method='contract-posts-x-rate',
        actual_method='Posts x citywide post rate x 12, headcount and shift hours from the roster '
                       'sheet.',
        verdict='matches',
        reasoning='Direct implementation of the catalogue\'s stated basis.',
    ),
    'ESS16': dict(
        spec_method='contract-headcount-x-12',
        actual_method='Monthly contract x 12, contract sized from the landscape roster headcount.',
        verdict='matches',
        reasoning='Direct implementation of the catalogue\'s stated basis.',
    ),

    # ---- Pool ----
    'ESM4': dict(
        spec_method='pool-volume-x-dose-x-price',
        actual_method='Pool volume (m3, summed across every pool the project has) x 2.5 kg/m3/month '
                       '(midpoint of the guideline\'s stated 1-4 kg range) x 6,000 VND/kg x 12 '
                       '(estimate_opex.py, POOL_SALT_* constants).',
        verdict='matches',
        reasoning='Direct implementation, midpoint of the guideline\'s own stated range, with the '
                   'range itself reported alongside the figure so it is never read as more precise '
                   'than it is.',
    ),

    # ---- Energy: consumption x tariff (fixed by cost-energy-from-consumption-and-tariff, '10-10) ----
    **{code: dict(
        spec_method='consumption-x-tariff',
        actual_method='Per-m² usage ratio from A&K Tower (n=1) x this project\'s NFA x a dated tariff '
                       '(Fact_OPEX.csv UnitPrice, read live, flagged stale before the 2027 budget '
                       'cycle) x 12.',
        verdict='matches',
        reasoning='Rewired onto consumption x tariff by change cost-energy-from-consumption-and-'
                   'tariff, archived 2026-09-10 — the day after proposal.md\'s 2026-09-09 measurement '
                   'recorded these three as the entire mismatched 31.0%. That measurement predates '
                   'the fix; the code today matches the catalogue\'s stated method for all three. '
                   'Usage stays a single-project ratio (n=1) — a real, separate, already-disclosed '
                   'caveat (estimate_opex.py\'s own docstring), not a method mismatch.',
    ) for code in ('EEE.C', 'EEW.C', 'EED.C')},

    # ---- Repairs & Maintenance ----
    'ERM': dict(
        spec_method='not recorded in Costing_Method_Catalogue.csv',
        actual_method='A blended per-m² cost ratio derived from A&K Tower alone (estimate_opex.py\'s '
                       '"two ratio categories" — no consumption/tariff split, no per-line breakdown), '
                       'restored to the deliverable 2026-09-17 by fix-parking-allocation-divide-by-'
                       'zero after being deferred since 2026-09-09.',
        verdict='mismatch',
        reasoning='No catalogue entry exists for this code, so there is no stated method to compare '
                   'against — the pipeline\'s own single-reference-property ratio has nothing backing '
                   'it the way, say, EMA15\'s identical shape is explicitly sanctioned by the '
                   'catalogue\'s own "section-catch-all" method. Recorded as a mismatch rather than '
                   'silently treated as satisfying an unstated spec, per D1\'s own reasoning: a '
                   'confident wrong verdict is worse than an honest gap.',
    ),

    # ---- Admin catch-all ----
    'EMA15': dict(
        spec_method='section-catch-all',
        actual_method='One blended per-m² ratio (A&K Tower alone) written to this single leaf row, '
                       'covering the whole EMA section rather than itemising EMA1-EMA19 separately.',
        verdict='matches',
        reasoning='The catalogue\'s own stated method for this specific code IS the catch-all shape '
                   'the pipeline uses — unlike ERM, this approximation is the spec\'s own answer for '
                   'this code, not an absence of one.',
    ),

    # ---- Capex (asset lists) ----
    **{code: dict(
        spec_method='asset-list-sum-depreciated-24mo',
        actual_method='Sum(quantity x unit cost) for the asset group, written off over the first 24 '
                       'operating months.',
        verdict='matches',
        reasoning='Direct implementation of the catalogue\'s stated basis.',
    ) for code in ('EN1', 'EN2', 'EN3', 'EN4')},

    # ---- Regulation-driven flat/frequency items ----
    'ESM2': dict(spec_method='regulation-count-x-cost',
                 actual_method='Required reports/year x vendor cost per report.',
                 verdict='matches', reasoning='Direct implementation.'),
    'ESM3': dict(spec_method='frequency-x-unit-cost',
                 actual_method='Required testing frequency/year x cost per test.',
                 verdict='matches', reasoning='Direct implementation.'),
    'ESM5': dict(spec_method='frequency-x-unit-cost',
                 actual_method='Tests/year x unit cost (only written if the project has a pool).',
                 verdict='matches', reasoning='Direct implementation.'),
    'ESM8': dict(spec_method='regulation-fixed-fee',
                 actual_method='Annual fixed connection fee per the authority tariff.',
                 verdict='matches', reasoning='Direct implementation.'),
    'EMA7': dict(spec_method='headcount-x-consumption',
                 actual_method='BQL headcount x 1 L/person/day, 19 L bottle at 60,000 VND incl. VAT.',
                 verdict='matches', reasoning='Direct implementation.'),
    'ESC12': dict(spec_method='regulation-fixed-estimate',
                  actual_method='~14,000,000 VND/year, the guideline\'s own provisional figure, '
                                'written directly (change fill-guideline-required-line-items).',
                  verdict='matches', reasoning='Direct implementation of the guideline\'s own figure.'),
    'ESM25': dict(spec_method='frequency-x-unit-cost',
                  actual_method='4 occurrences/year x ~3,500,000 VND/occurrence (per SCE), '
                                '= ~14,000,000 VND/year.',
                  verdict='matches', reasoning='Direct implementation of the catalogue\'s stated basis.'),
    # Added 2026-09-21, change complete-ai-guideline-remark-coverage (B2.6 / waste-collection-
    # costing track) — ESS9 written for the first time; this registry predates that write.
    'ESS9': dict(spec_method='regulation-quantity-x-3-part-unit-price',
                 actual_method='(Apartment units x 2.63 kg/unit/day + Shophouse units x 3.945 '
                               'kg/unit/day) x 30 days x (486 + 180 + 421 VND/kg), QĐ 65/2026/QĐ-UBND\'s '
                               'collection+transport+treatment tariff (replacing the QĐ 67/2025 prices on '
                               'the AI Guideline\'s \'B2.6 Rác sinh hoạt (QD67)\' worksheet), with the VAT '
                               'of each budget month added.',
                 verdict='matches', reasoning='Direct implementation of the guideline\'s own stated '
                                              'formula and cited rates — the Shophouse weight uses the '
                                              'guideline\'s formula-instruction basis (3.945 kg/unit/'
                                              'day) over its own inconsistent note text (~3.41), '
                                              'disclosed in the written remark, not a method mismatch.'),
    'ESI1': dict(spec_method='asset-value-x-premium-rate',
                 actual_method='No figure written — no insured-asset-value input exists on the intake '
                                'form, so the pipeline correctly leaves this at 0 rather than guess an '
                                'asset value (remark-only line, per generate_project_budget.py).',
                 verdict='partial',
                 reasoning='The rate basis (0.05% of asset value, Nghị định 105/2025) is correctly '
                           'identified and stated on the remark, but no figure is actually computed — '
                           'neither fully implementing the spec\'s method nor silently substituting a '
                           'different one. "Partial" rather than "mismatch": nothing is derived by a '
                           'wrong method, because nothing is derived at all.'),
}


def departure_verdicts(catalogue_path=None):
    """Verdicts for codes whose catalogue entry departs from the AI Guideline (spec costing-method-catalogue,
    requirement "A method that departs from the AI Guideline records who approved it"; change
    use-operating-project-actuals). Read from the catalogue's own record in `precedence_note`, never
    hand-kept here: an approved departure (approver, date and decision record all present) is the expected
    method, 'matches'; a departure without that record is a 'mismatch'.

    These codes are written only when the PM enters an amount, so they are not in write_site_codes() and
    leave the verdict cross-check and the coverage figures unchanged; compute_fidelity() and the coverage
    check read a written one through here."""
    import operating_inputs as oi
    out = {}
    for row in oi._catalogue_rows(catalogue_path):
        rec = oi.parse_departure(row.get('precedence_note'))
        if rec.get('departs_from_guideline') != 'yes':
            continue
        approved = all(rec.get(k) for k in ('approved_by', 'approved_on', 'decision_record'))
        out[row['code'].strip()] = dict(
            spec_method=row.get('method'),
            actual_method=row.get('method_detail'),
            verdict='matches' if approved else 'mismatch',
            reasoning=(f"Approved departure from the AI Guideline ({rec.get('guideline_says', '')}); approved by "
                       f"{rec.get('approved_by')} on {rec.get('approved_on')}, {rec.get('decision_record')}."
                       if approved else
                       f"Departs from the AI Guideline ({rec.get('guideline_says', '')}) with no approval record."),
        )
    return out


def check_method_verdicts():
    """Cross-check the recorded verdicts against the pipeline's actual write sites (design.md D2).

    Returns (ok, missing_verdict_codes, orphaned_verdict_codes):
      - missing_verdict_codes: written by the pipeline, no recorded verdict — task 3.3.
      - orphaned_verdict_codes: a verdict is recorded, but the code is no longer written — task 3.4.
    `ok` is True only when both lists are empty.
    """
    written = write_site_codes()
    recorded = set(METHOD_VERDICTS.keys())
    missing = sorted(written - recorded)
    orphaned = sorted(recorded - written)
    return (not missing and not orphaned), missing, orphaned


def compute_fidelity(code_to_value, catalogue_path=None):
    """Share of written cost that matches, partially matches, and does not match the spec's stated
    method (task 4.3), plus which codes make up each share (task 4.4).

    `code_to_value` is {code: annual VND} for every code this run actually wrote a non-null figure
    for, read from the generated deliverable's own G column — weighted by real VND, not by a bare
    code count, since a code-count share would let one huge line and one tiny line count equally,
    which is not what "share of written cost" means.

    Returns {'matches': {'value': float, 'share': float, 'codes': [...]},
             'partial':  {...}, 'mismatch': {...}, 'total_value': float}.
    """
    ok, missing, orphaned = check_method_verdicts()
    if not ok:
        raise RuntimeError(
            f"Cannot compute fidelity while verdicts and write sites disagree — missing verdicts for "
            f"{missing}, orphaned verdicts for {orphaned}. Fix the registry or the write sites first.")

    buckets = {'matches': [], 'partial': [], 'mismatch': []}
    departures = departure_verdicts(catalogue_path)
    for code, value in code_to_value.items():
        verdict = (METHOD_VERDICTS.get(code) or departures[code])['verdict']
        buckets[verdict].append((code, value))

    total_value = sum(v for _c, v in code_to_value.items())
    report = {'total_value': total_value}
    for verdict, entries in buckets.items():
        value = sum(v for _c, v in entries)
        report[verdict] = dict(
            value=value,
            share=(value / total_value) if total_value else 0.0,
            codes=sorted(c for c, _v in entries),
        )
    return report


def compute_coverage(reference_name, written_codes):
    """Which cost codes `reference_name`'s real budget uses that `written_codes` (the pipeline's own
    write sites) does not fill, and what share of that budget's value they represent (task 4.1).
    Never averaged across projects — the caller reports each named project's own dict separately
    (task 4.2).
    """
    leaves = extract_reference_budget(reference_name)
    reference_total = sum(v['value'] for v in leaves.values())
    unfilled = {code: v for code, v in leaves.items() if code not in written_codes and v['value']}
    unfilled_total = sum(v['value'] for v in unfilled.values())
    filled_total = reference_total - unfilled_total
    return dict(
        reference_project=reference_name,
        reference_total_value=reference_total,
        filled_value=filled_total,
        filled_share=(filled_total / reference_total) if reference_total else 0.0,
        unfilled_codes=sorted(unfilled.keys()),
        unfilled_value=unfilled_total,
        unfilled_share=(unfilled_total / reference_total) if reference_total else 0.0,
    )
