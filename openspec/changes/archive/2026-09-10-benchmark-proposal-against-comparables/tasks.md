## 1. Confirm the `1. Summary` anchors

- [x] 1.1 Confirm the standard-form template (`input/template/2027 Resi Budget Form (IT team).xlsx`)
  `1. Summary` sheet holds, at fixed rows: row 14 = `RM` (management-fee revenue), row 13 = `R`
  total operating income, row 20 = `E` total operating cost, row 46 = `C.` operating difference
  (`=H13-H20`), row 54 = `PART 3:` after tax. Column H = annual total. Record the row numbers as
  named constants in `generate_project_budget.py` (`_SUMMARY_ROW_MGMT_FEE = 14`, etc.). Verify by
  loading the template and printing B/F/H of those rows.

## 2. Build the PROPOSAL BENCHMARK section

- [x] 2.1 Add module-level constants near the other Comparison-sheet constants:
  `COVERAGE_BAND_THIN_MAX = 0.05`, `COVERAGE_BAND_NORMAL_MAX = 0.15`, band labels
  (`thin` / `normal` / `generous` / `shortfall`), and the verdict-clause wording. Verify they are
  referenced, not inlined.
- [x] 2.2 In `add_comparison_sheet()`, after the APARTMENT MANAGEMENT FEE RATE section, add
  `section(r, 'PROPOSAL BENCHMARK — is the proposed fee defensible in a bid?')` and a one-line note:
  the fee rows compare against comparable projects' real Apartment rates; the coverage rows are an
  internal consistency check on this project's own estimate (operating fund only — sinking fund
  excluded). Verify the section renders in a generated file.
- [x] 2.3 **Fee per apartment (VND/month)** row. This project `= round(derived_rate *
  project['apartment_nfa'] / project['apartment_units'])`. Each comparable `= round(c['rates']
  ['Apartment'] * c['nfa'] / c['units'])`, cell labelled "approx — gross area per unit"; blank with
  a note if `c['rates'].get('Apartment')` is falsy or `c['units']` is missing. Verify against a hand
  calculation for one project.
- [x] 2.4 **Year-one management-fee revenue (VND)** row. This project cell `= "='1. Summary'!H14"`.
  Each comparable cell `= "='1. Summary'!H14 - {apt_rev_at_derived} + {apt_rev_at_comp}"` where
  `apt_rev_at_derived = round(apartment_nfa * derived_rate * 12)` and `apt_rev_at_comp =
  round(apartment_nfa * c_apt_rate * 12)` are Python constants; label "if this project charged at
  <comparable>'s Apartment rate — projection". Verify the formula string is a real formula (starts
  `='`, not `= `) and that it reduces to `='1. Summary'!H14` when `c_apt_rate == derived_rate`.
- [x] 2.5 **Coverage** rows, this-project column only (comparables blank — no cost data):
  total operating income `="='1. Summary'!H13"`, total operating cost `="='1. Summary'!H20"`,
  operating surplus before Savills' fee & tax `="='1. Summary'!H46"`, surplus % of income
  `="='1. Summary'!H46/'1. Summary'!H13"` (percent number format). Put the numeric thresholds in the
  band row's label ("thin < 5% · normal 5–15% · generous > 15% · shortfall < 0%") and make the band
  value an Excel `IF` formula off `'1. Summary'!H46/'1. Summary'!H13` (thresholds from the 2.1
  constants). Verify a deliberately loss-making input shows a negative surplus and the "shortfall"
  band.
- [x] 2.6 **Verdict** row. Compose in Python where the inputs are known at generation time (the
  fee-vs-range clause: this project's `derived_rate` in VND/m²/month vs `min`/`max` of
  `[c['rates']['Apartment'] for c in comparables]`), and as an Excel `IF` on `'1. Summary'!H46` for
  the coverage clause (balances / does not balance before Savills' fee). Handle: inside range,
  below lowest (state % gap), above highest (state % gap), one comparable only ("narrow comparable
  base"), `own_real is None` (skip the reality-check mention). Verify each fee-vs-range branch with
  a crafted `comparables` list.

## 3. Verification

- [x] 3.1 Add `check_benchmark_reconciles(paths)` to `verification/checks.py` (mirror
  `check_revenue_agreement`: COM, deliverable copy, `CalculateFullRebuild`, `_tol` = `max(5_000.0,
  abs(v) * 5e-5)`). Read the `Comparison` sheet's PROPOSAL BENCHMARK own-project cells (revenue,
  operating income, operating cost, operating surplus) and the matching `1. Summary` cells; fail
  naming any pair that differs beyond `_tol` or any benchmark cell that is an Excel error. Also read
  one projection cell and, when that comparable's Apartment rate equals the derived rate, fail if it
  differs from the own-project revenue. Return `(ok, rows, differences, notes)`.
- [x] 3.2 Import and call `check_benchmark_reconciles` in `verify.py` as section 5c, after 5b; on
  failure print the disagreeing figures and mark the run failed (same handling as 5b). Verify
  `python verification/verify.py` still passes on the synthetic fixture.
- [x] 3.3 Confirm no baseline moves: record the 24 analysis + 7 deliverable baseline values before
  the change, run `verify.py` after, confirm all 31 are unchanged (this change writes only the
  display-only `Comparison` sheet).

## 4. Manual spot-check (project rule: aggregation logic changed)

- [x] 4.1 Run both generators against one real project (Diamond Skyline or an EXAMPLE file). By
  hand confirm: (a) fee per apartment = derived Apartment rate × (apartment NFA ÷ apartment units);
  (b) a projection = apartment NFA × that comparable's Apartment rate × 12, plus this project's
  non-apartment revenue unchanged; (c) the coverage cells equal `1. Summary` H13/H20/H46 and the %
  matches; (d) the verdict line reads correctly for that project's rate vs the comparable range.
  Record the four checks and the project used in the archive notes.

## 5. Docs

- [x] 5.1 Update `docs/05-decisions.md` (the D2 "Comparison sheet" note) and
  `docs/project-status.md` to record the PROPOSAL BENCHMARK section: what it shows, that it is
  display-only and carries `1. Summary` figures forward by formula, and that no budgeted figure
  moved. Verify both files mention the change with the date.
