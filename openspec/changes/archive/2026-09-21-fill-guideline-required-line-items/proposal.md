## Why

The newest AI Guideline file (`docs/AI Guideline - 2027 Resi Budget Form (IT team)  1.xlsx`,
2026-09-14) fills in a "Bắt buộc/Required" vs "Tùy chọn/Optional" vs "Thông thường/Standard"
classification on `2. Budget-Management Fund` and `2.2 Common area Fund` that was blank in every
guideline copy this pipeline has read before — 979 cells differ from the previous copy, confirmed
by a direct diff. This is a machine-readable completeness contract that did not exist before: 86
codes carrying a leaf code are marked Required on `2. Budget-Management Fund` alone, and a
comparable count on `2.2 Common area Fund`. Most already have a pricing method and are already
filled by the existing pipeline (RM.AP, RO2-4, EMH1-4, ESS1/4/16, EEW/EEE/EED, EN1-3, and more) —
but at least one confirmed family is not: `EMA1` (Telephone & internet), `EMA2` (Stationery),
`EMA3` (Printing ink), `EMA4` (Photocopy rental), and `EMA7` (Drinking water) are all marked
Required, yet the pipeline only ever fills the `EMA15` catch-all, sourced as one blended per-m²
ratio from a single comparable property (A&K Tower) — EMA1-4 and EMA7 are always zero. Real-world
evidence this is material, not cosmetic: `reports/Green Skyline - Backtest vs Real Budget.xlsx`
records the pipeline's EMA output as 0 against that project's real, actual Administrative Expense
of 105,625,263 VND — a full miss, not a rounding gap.

The root cause behind the EMA gap specifically: the pipeline's only comparable source for
admin-expense pricing (A&K Tower, via `estimate_opex.py`) gives one combined, blended figure — it
never had the individual EMA1-4/7 breakdown to draw from. Green Skyline's real budget apparently
does carry (or can be re-derived to carry) that detail. The fix generalizes to a standing principle
this proposal states as a requirement: **when a Required line item has no pricing method because
the pipeline's current comparable source only has a combined figure, and another available
comparable source has the itemized detail, the itemized source should be used and shown — not
silently left at zero because the first-checked source happened to be blended.**

## What Changes

- **A recorded reference of every Required/Optional/Standard code**, transcribed from the new
  guideline file's own classification column, for every sheet that carries it (`2. Budget-
  Management Fund`, `2.2 Common area Fund` confirmed so far; scan for others during
  implementation) — a new `data/master_list_verified/` CSV, matching the existing
  `Costing_Method_Catalogue.csv` / `AI_Guideline_Canonical_Positions.csv` pattern.
- **A gap analysis** (implementation task, not resolved here): cross-reference that Required list
  against what `generate_project_budget.py` actually writes (via `MGMT_FUND_ROWS`,
  `Costing_Method_Catalogue.csv`'s recorded methods, and the fold-into-catch-all rows) to produce a
  definitive list of Required codes currently left at zero.
- **Pricing for the confirmed EMA gap** (`EMA1`/`EMA2`/`EMA3`/`EMA4`/`EMA7`), each written to its
  own leaf row instead of folded into `EMA15`'s catch-all — `EMA7` (Drinking water) already has a
  working `headcount × consumption` calculation elsewhere (the analysis workbook's OPEX sheet);
  `EMA1`-`EMA4` need a comparable-property source with itemized detail, which A&K Tower's OPEX data
  does not have.
- **Pricing for any further confirmed gap** the implementation-time scan surfaces, using the same
  standard: an existing catalogue method wired up if one exists; flagged back to the user (not
  invented) if a Required code genuinely has no sourced method anywhere yet.
- **A completeness check** in `verify.py`: every code marked Required on the recorded reference
  SHALL carry a non-zero figure on the generated deliverable, or a stated, deliberate reason it is
  zero for this specific project (e.g. no pool → pool-related Required codes stay zero).
- **The itemized-over-combined sourcing rule**, applied at least to the EMA case and recorded as a
  standing principle for future comparable-property sourcing work generally.

## Capabilities

### New Capabilities

- `guideline-required-line-items`: the deliverable's `2. Budget-Management Fund` (and
  `2.2 Common area Fund`) SHALL carry a non-zero figure for every code the AI Guideline classifies
  as Required, sourced from the most itemized comparable data available rather than a blended
  figure when a more detailed source exists — and verification SHALL enforce it.

### Modified Capabilities

None. `outsourced-service-costs` (Security/Cleaning/Landscape) is a related but separate sourcing
concern — this change does not touch it, and its own requirements do not change.

## Impact

- **Affected code**:
  - `generate_project_budget.py` — `fill_management_fund_sheet()`'s EMA handling (and whatever
    else the gap analysis surfaces), replacing catch-all folding with individual leaf writes where
    a Required code demands it.
  - `estimate_opex.py` / `generate_project_output.py` — admin-expense (and any other affected
    category) sourcing, to draw from an itemized comparable source instead of A&K Tower's blended
    figure where one exists.
  - `data/master_list_verified/` — new Required/Optional/Standard reference CSV; likely an
    extension to `Costing_Method_Catalogue.csv` for any newly-priced code.
  - `verification/checks.py` + `verify.py` — the new completeness check.
- **Affected data**: Generation A (deliverable-writing) only, same boundary every change in this
  project maintains. No Generation B table, no Fact/Dim join key change.
- **Baselines**: figure-moving — `deliverable_baseline.json` (and the analysis `baseline.json` if
  the analysis workbook's own EMA/admin figure also moves) re-recorded after PM sign-off, same
  pattern as `reconcile-summary-with-detail-sheets`.
- **Risk**: Medium-High — this fills previously-zero Required line items, a real, client-facing
  surplus decrease, on a broader scope than any single line item fixed so far this session. Measure
  on a real project and get explicit Head-of-PM sign-off before archive — do not assume the
  Green Skyline backtest's 105,625,263 figure is still exactly right; re-measure on current code.
