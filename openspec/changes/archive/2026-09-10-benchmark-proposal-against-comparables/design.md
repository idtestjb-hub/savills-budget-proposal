## Context

See `proposal.md` — Why. The `Comparison` sheet already exists (`add_comparison_sheet()` in
`generate_project_budget.py`, called from `build_budget()` after the deliverable is saved). It is a
display-only appendix — not a Savills template sheet, nothing in the pipeline reads it, no
verification baseline records its cells. It currently has three sections: OVERVIEW (how comparable
the projects are), APARTMENT MANAGEMENT FEE RATE (model-derived rate vs comparables' real rates, and
a reality-check gap for an existing project), and SERVICE RATES.

Constraints that shape the approach:

- **Comparable data is `master_comparables.py` only.** Each comparable carries `name`, `nfa` (total
  building net floor area), `units` (apartment units), `total_units`, `rates` (per-product dict, may
  or may not have `Apartment`), `mgmt_rate` (blended whole-property), `mgmt_rate_vat`, `source`.
  There is **no apartment-only net floor area** and **no operating-cost data** per comparable.
- **Operating-cost reference data is one property.** `estimate_opex()` derives this project's
  utilities/repairs/admin from A&K Tower's real ratios (n=1). Staff cost comes from the roster;
  outsourced services (security/cleaning/landscape) from citywide rate cards; capex reserve from
  `derive-capex-reserve-rate`. So a "cost benchmark against comparables" is not possible — only a
  coverage check of this project's proposed fee against this project's own estimated cost.
- **The deliverable's `1. Summary` figures are formula cells with no cached value.** openpyxl
  cannot read their computed values; only Excel (COM) can. `add_comparison_sheet()` runs on openpyxl
  after the deliverable is saved, so it cannot read a year-one revenue or cost number at write time.
  The relevant `1. Summary` rows are template-fixed (Savills' IT-team standard form): row 14 `RM`
  (management-fee revenue), row 13 `R` (total operating income = SUBTOTAL of rows 14–19), row 20 `E`
  (total operating cost = SUBTOTAL of rows 21–45), row 46 `C.` (`=H13-H20`, operating difference
  before tax), row 54 `PART 3:` (`=H46-H48`, after tax — already baselined as
  `estimated_surplus_year1`). Section 2 (rows 66–70) is the sinking fund, a separate fund.
- **`build_budget()` has this project's scale, `derived_rate`, and the comparables (`top2`)** in
  scope at the `add_comparison_sheet()` call — enough to compute the fee-per-apartment and
  revenue-at-comparable-rate figures. It does not have a reliable year-one operating-cost total
  without re-summing a large part of what it writes.
- **`verify.py` already opens the deliverable in an Excel COM session** (`check_revenue_agreement`,
  §5b, added by `unify-revenue-basis-across-outputs`) and reads computed cells, and
  `deliverable_baseline.py` already reads `1. Summary` by code lookup.

## Goals / Non-Goals

**Goals:**

- Add one PROPOSAL BENCHMARK section to `add_comparison_sheet()` that turns the model-derived rate
  into the figures a bid conversation actually uses: fee per apartment, year-one revenue, revenue if
  charged at each comparable's rate, and fee-to-cost coverage, ending in a one-line verdict.
- Keep the section honest about what is a peer comparison (fee) and what is an internal check
  (coverage), on the sheet.
- Make the benchmark's revenue and cost figures provably equal to the workbook's own figures, via a
  verification check, so the appendix cannot drift from the budget.

**Non-Goals:**

- No change to any budgeted line, rate, or baseline figure. Purely additive presentation.
- No new comparable data, no new cost data, no widening of `master_comparables.py` (that is a
  separate data change — roadmap "widen the comparable base").
- No benchmark of staff / services / capex against comparables — the data does not exist.
- No change to the internal analysis workbook or to the `Comparison` sheet's existing three
  sections beyond what is needed to place the new one.

## Decisions

### D1 — The own-project revenue/income/cost/surplus cells are Excel formulas referencing `1. Summary`, not Python re-derivations

The benchmark's four own-project figures are written as formulas: management-fee revenue
`='1. Summary'!H14`, total operating income `='1. Summary'!H13`, total operating cost
`='1. Summary'!H20`, operating surplus `='1. Summary'!H46` (and after-tax `='1. Summary'!H54` where
useful). The surplus percentage is `=H46/H13` inside the Comparison sheet.

- **Why:** those `1. Summary` cells are formulas with no cached value, so `add_comparison_sheet()`
  cannot read their numbers at write time — it would have to re-sum a large part of what
  `build_budget()` writes, creating a second source of truth that can silently drift. A formula ref
  makes the benchmark carry the deliverable's own figure forward **by construction** — the same
  principle the project already applies to keeping the two workbooks in agreement.
- **The `1. Summary` rows referenced are template-fixed** (Savills' standard form), not
  pipeline-generated, and `deliverable_baseline.py` already depends on this exact layout — so the
  ref is no more fragile than what the verification harness already assumes, and a broken ref is
  caught by D4.
- **No signature change** to `add_comparison_sheet()`; nothing new threaded through `build_budget()`.
- **Alternative considered — compute in Python and pass in:** rejected because the operating-cost
  total is not cleanly in scope and re-deriving it duplicates the pipeline.

### D2 — The coverage check covers the operating fund only; the sinking fund / capex reserve is excluded

Coverage compares `1. Summary` section 1: total operating income (`H13`) against total operating
cost (`H20`), giving the operating surplus (`H46`, before Savills' fee and before tax). Savills' own
fee (`EMH1`) is left blank per decision D1, so `H20` already excludes it. The sinking fund (section
2, rows 66–70) is left out of **both** sides.

- **Why:** the sinking fund is a separate, legally ring-fenced fund in Vietnamese residential
  management; residents contribute to it separately and `1. Summary` section 1 does not carry that
  income, so adding only its expense side would understate coverage. "Does the operating budget
  balance" is a clean, honest question on section 1 alone — and it is exactly what `1. Summary`
  PART 3 / the already-baselined `estimated_surplus_year1` represents.
- **Alternative considered — include capex reserve (`+ H70`):** rejected — its matching income is
  not in section 1, so the comparison would be lopsided.

### D3 — Fee per apartment: exact for this project, flagged approximation for comparables

This project: `derived Apartment rate × (apartment_nfa / apartment_units)`. Comparable: `real
Apartment rate × (comparable nfa / comparable units)` — but `comparable nfa` is total building area,
so this is gross (includes shared/parking area) and an upper bound. The cell is labelled as such.
The comparables passed in (`top2`, the `used` list from `derive_product_rate`) are already
pre-filtered to those with a verified Apartment rate, so the "comparable has no Apartment rate"
gap cannot occur for the passed set — but the row still renders a blank-with-note if a rate is
somehow absent, per the spec.

- **Why:** `master_comparables.py` has no apartment-only area. A flagged upper bound is more useful
  to a PM than omitting the comparison, and the direction of the bias is known and stated.
- **Alternative considered — omit comparable fee per apartment, keep only VND/m²:** cleaner but
  loses the number clients actually relate to. Kept with the caveat instead.
- **Follow-up:** if `master_comparables.py` later carries apartment-only area, this caveat drops
  out automatically.

### D4 — Verification: one new COM check, sharing the existing pattern

Add `check_benchmark_reconciles(paths)` in `verification/checks.py`, following
`check_revenue_agreement`'s shape (COM session, deliverable copy, `CalculateFullRebuild`,
`max(5_000 VND, 5e-5 × value)` tolerance). It opens the deliverable and:

1. reads the PROPOSAL BENCHMARK own-project cells (revenue, operating income, operating cost,
   operating surplus) from the `Comparison` sheet and the matching `1. Summary` cells, and fails if
   any pair differs beyond tolerance or a benchmark cell is an Excel error;
2. reads one "revenue if charged at comparable X's rate" projection and, when that comparable's
   Apartment rate equals the derived rate, fails if it differs from the own-project revenue.

Wired into `verify.py` as section 5c, after 5b. It does not touch any baseline.

### D5 — Coverage bands and verdict wording are stated on the sheet and reviewed by the PM

Proposed bands: surplus as % of year-one management-fee revenue — **thin < 5%**, **normal 5–15%**,
**generous > 15%**, **shortfall < 0%**. The verdict line composes two clauses: fee-vs-range ("within
the range Savills charges for comparable buildings" / "X% below the lowest comparable" / "X% above
the highest") and coverage ("and year-one fee revenue covers estimated operating cost with an N%
surplus" / "but year-one fee revenue does not cover estimated operating cost"). The thresholds and
the wording are in `generate_project_budget.py` as named constants for a PM to adjust.

## Risks / Trade-offs

- **[The comparable fee-per-apartment upper bound is misread as exact]** → cell label says
  "approx — gross area per unit" and the caveat is on the sheet; the verdict line uses the VND/m²
  rate range (exact), not the per-apartment figure, for the inside/below/above test.
- **[Coverage reads as a market benchmark]** → the section note states that the cost side is this
  project's own estimate from one reference property (n=1), a consistency check not a second
  opinion. The spec makes this a requirement.
- **[A formula ref to `1. Summary` breaks (`#REF!`, wrong row) after a template reshape]** → D4's
  check opens the deliverable in Excel and fails if a benchmark cell is an error or disagrees with
  its source; a template reshape would break `deliverable_baseline.py` too and is caught there.
- **[A project with no apartments]** → the section is apartment-fee-centric; for an apartment-free
  project (rare — the rate section already assumes apartments) the fee rows print a single line
  saying the fee benchmark applies to apartment projects, and the coverage rows still render.

## Migration Plan

Additive. No baseline re-record (no budgeted figure moves). Deploy = ship the code; the next
`run.py` writes the new section. Rollback = revert the `add_comparison_sheet()` change and remove
`check_benchmark_reconciles` from `verify.py`. Manual spot-check (per the project's tasks rule): run
against one real project, confirm by hand that fee per apartment = rate × avg apartment NFA, that
revenue-at-comparable-rate = apartment NFA × comparable rate × 12 plus unchanged non-apartment
revenue, and that the coverage cells match `1. Summary` rows 13/20/46.

## Open Questions

- Exact band thresholds (5% / 15%) are a first proposal for the PM to confirm — they do not change
  the spec, the approach, or the tasks, only the constant values.
