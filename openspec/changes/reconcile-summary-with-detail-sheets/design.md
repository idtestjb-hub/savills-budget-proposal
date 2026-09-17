## Context

See `proposal.md` — Why, and `docs/09-template-map.md` §3–§9 for the full formula graph. Facts that
shape the approach:

- `1. Summary` reads column **`AK`** (`=SUM(AQ:BB)`, a month-by-month cash-flow projection) of
  `2. Budget-Management Fund`, not column `G` (`=IF(Schedule,SUM(H:S),F×E)`). The two agree
  unconditionally only for `Schedule` and `Monthly` frequency rows.
- The pipeline's three write helpers already produce `G ≡ AK`: `_write_ramped_row` (Schedule),
  `_write_even_monthly_row` (Monthly), `_write_year1_lump_row` (Schedule). The **only** fund leaf
  row where `G ≠ AK` is `RO2a` — a template default the pipeline never touches.
- `EMH2` (row 83) is written by `_write_even_monthly_row('staff_remainder', …)` where
  `staff_remainder = Σ position_bare_annual_cost(d) × 1.215` over non-outsourced positions.
- `fill_staff_cost_sheet()` writes only column `G` (monthly gross) of `A1. Staff cost`, per
  position row-group; the sheet's own formulas compute 13th-month / PIT / SI-HI-UI / union / **×1.10
  admin markup** → **row 96 `AC` = annual total**. `A1` has no Reception row-group (Reception is on
  `B1. Lịch Lễ tân`).
- `A2 / A3 / A4` (security / cleaning / landscape helpers), `B2 / B3 (Consumable) / B3 (Garbage) /
  B4 / B5` are read by **no formula** anywhere in the deliverable (confirmed by scanning every
  cross-sheet reference). The pipeline still writes rates/counts + the project name into them.
  `A2 / A3 / A4` recalculate to **204 `#DIV/0!`** because their real input cells (`M:P`, `H`) are
  never filled.
- `verify.py` already opens the deliverable in Excel (`check_revenue_agreement`,
  `check_benchmark_reconciles`), and `deliverable_baseline.py` reads `1. Summary` by code lookup.
- The current `check_formula_errors` gate is "no errors introduced beyond the blank template's
  count" — a ceiling of 257, not zero.

## Goals / Non-Goals

**Goals**

- `1. Summary` ties to `2. Budget-Management Fund` on every code, every surplus, and both total
  columns — enforced by `verify.py`.
- `EMH` on the summary equals the deliverable's own `A1` payroll total plus any outside-costed
  in-house position; the analysis workbook moves onto the same payroll basis.
- The deliverable stops shipping error cells and dead-end writes the pipeline controls; the error
  ceiling ratchets down.

**Non-Goals**

- The parking-allocation `#DIV/0!` block (`BJ/BK/BM/BN`, 50 cells) — owned by
  `fix-parking-allocation-divide-by-zero`; this change lowers the ceiling only by the cells it
  actually removes.
- Populating the sinking fund (`3. Budget-Sinking Fund`) — Change D/E.
- The `0. Info` Nursery revenue gap and the common-area advertising consolidation — notes only, no
  figure change.
- Re-pricing staff (headcount, grade mix) — out of scope; only the payroll *basis* moves.

## Decisions

### D1 — `RO2a`: zero it (PM confirmed)

`fill_management_fund_sheet` gains a small explicit step: set `2. Budget-Management Fund!F37 = 0`,
clear the `K37` date, leave `C37` as the template ships it. `G37` then = `0 × 2` = 0 and `AK37`
= 0. Bank interest becomes a line a PM fills with a real figure.

- **Why not fill the second payment month:** that keeps a fabricated 10,000,000 with no basis.
- **Why not leave it for the template owner:** the deliverable would keep shipping a grand total
  5,000,000 short of its own detail sheet — indefensible to a client. (Still worth raising upstream;
  a `docs/05` note will record it.)
- **Effect:** `1. Summary` revenue and surplus **−5,000,000** vs today (today's `AK` already only
  counted 5M; zeroing removes it).

### D2 — `EMH2`: a formula into `A1` row 96, plus real row(s) for any position `A1` has no
row-group for

`_write_even_monthly_row` is replaced for this one row by a dedicated write:
`C83 = "Monthly"`, `F83 = "=('A1...'!AC96 + <unplaced_ref>*12)/12"`. `G83 = F83 × 12` and
`AK83 = SUM(AQ:BB) = F83 × 12` — both resolve to `A1!AC96 + <unplaced total>`, tying to the payroll
sheet by construction.

- **Revised after initial implementation, on PM feedback**: `<unplaced_ref>` was first a
  Python-computed constant folded straight into this formula string — correct in total, but not
  auditable: nothing on `A1` showed *how* that number was derived, and a PM reviewing `A1` had no
  row to trace, edit, or recalculate. Reworked so `fill_staff_cost_sheet()` instead gives every
  unplaced position **real rows on `A1` itself** — one row per headcount unit (mirroring exactly how
  every other position's headcount becomes N rows via `fill_group()`), at `_A1_UNPLACED_FIRST_ROW`
  (98), copying row 15's own formula chain column-for-column (same `$L$7`/`$T$7`/etc. statutory-cap
  cells every other row uses, so it can never drift from them). `<unplaced_ref>` is then a live
  reference to those row(s) — `'A1...'!AC98` for one row, `SUM('A1...'!AC98:AC99)` for several — not
  a number. Nothing about the DELIVERABLE'S figures needed to change for this — `A1!AC96` and the
  reconciliation logic are untouched — only where Reception's own math lives and how visible it is.
- **Why not `B1. Lịch Lễ tân` instead** (Reception's own sheet): checked directly — it is a pure
  duty-roster grid (which day each person works which shift), no payroll math at all, and its own
  template rows are even mislabeled (`Chăm sóc khách hàng`, not `Lễ tân`, by default). Building a
  payroll calculator there from scratch would be a bigger, riskier change than adding rows to `A1`.
- **Why not write into a spare row A1 already has** (several position-groups ship with more rows
  than any project uses, e.g. Customer Service has 17): rejected — the row's own printed label
  (column B) would still say e.g. "Chăm sóc khách hàng 3", so writing Reception's numbers into it
  trades one kind of hiding (a formula constant) for another (a mislabeled row).
- **Why a formula, not a read-back:** `A1!AC96` is a formula cell with no cached value; openpyxl
  cannot read it at write time. A formula reference is the same pattern the RM benchmark already
  uses.
- **Alternative — replicate A1's payroll maths in Python for `EMH2`:** rejected — `A1` already does
  it correctly (Savills' own calculator); duplicating the PIT-bracket logic invites drift. (This is
  exactly what the first `<top_up>` implementation did in miniature, for just the "smaller extras"
  team-building/training/checkup/accident-insurance/uniform components — the real-row rework removes
  that duplication too, at the cost of a small, disclosed additional figure movement — see below.)
- **Effect (measured on Wayne Tower, live COM re-check):** `EMH` **+638,780,247** (staff — old
  4,291,165,917 vs new 4,929,946,164), surplus **−638,780,247**. (5,755,257 VND of this is the
  real-row rework itself: Reception's live `A1` formula now includes the smaller extras — team
  building, 1.3% training, annual checkup, accident insurance, uniform — that the first
  Python-constant version of `<top_up>` had omitted; see the first bullet above.)

### D3 — Analysis workbook: fold the same payroll components into `build_staff_sheet`

`generate_project_output.py`'s staff sheet currently costs each position at
`bare cost × 1.215`. It gains the components `A1` applies: the 13th-month spread, real employer
statutory insurance (SI/HI/UI at the 2026 caps `A1` uses), Trade Union 2%, and the **×1.10 admin
markup** — as explicit columns/formulas (T-Z on the `Staff (Roster)` sheet).

- **Why not replicate `A1`'s PIT brackets exactly:** PIT is an *employee* deduction, not an
  employer cost — it does not change the gross-to-total-cost bridge that `EMH2` needs. The
  employer-side components (insurance + union + markup + 13th-month) are what matter, and those are
  bracket-free. Any residual vs `A1` is stated on the analysis sheet.
- **Measured residual (Wayne Tower, live COM re-check):** the shared `full_payroll_annual_cost()`
  function itself does not drift — this sheet's Reception total matched `A1`'s FIRST (Python-top-up)
  implementation to the VND. After D2's real-row rework, `A1` prices Reception with its own full
  formula chain (including the smaller extras this function deliberately omits — team building,
  1.3% training, checkup, accident insurance, uniform), so a small new gap exists there too:
  318,353,184 (`A1`'s 2 real rows, annualised) vs 312,597,927 (this sheet's `full_payroll_annual_cost`
  estimate) — 5,755,257 VND, the same components named in D2. Folding this sheet onto `A1`'s full
  formula too (not just the employer-side components already shared) is a further refinement, not
  done here. Separately, the sheet's
  *in-house total* (all non-outsourced positions, i.e. the figure comparable to `A1!AC96 + top_up`)
  runs **~4%** above the deliverable, not the ~1% first assumed. Root cause, isolated: `A1`'s own
  gross-salary step (`fill_staff_cost_sheet`'s `group_stats`, unchanged by this task) averages a
  shift role's Morning/Afternoon/Night daily rates into **one flat monthly gross with no night
  differential**, then writes that same flat figure to every headcount row regardless of shift — so
  `A1` currently understates gross pay for Technician-Night and Shift-Leader-Night specifically. This
  sheet prices each shift at its own rate (Night ×1.30), so it runs higher for exactly those rows —
  quantified: Technician-Night vs Morning/Afternoon excess 89,642,052 + Shift-Leader-Night excess
  122,464,835 = 212,106,887, which alone exceeds the whole 197,542,240 measured residual (other
  smaller effects net roughly flat). **This is a pre-existing gap in `A1`'s gross-salary assignment,
  not in the payroll-basis math either sheet applies on top of gross — out of scope for this change**
  (re-pricing staff, including fixing what feeds a role's gross salary, is a non-goal above). Stated
  accurately on the `Staff (Roster)` sheet's own disclosure note; flagged as a follow-up candidate.
- The existing `EMH2 … "never drifts from build_staff_sheet"` invariant is preserved for the shared
  `full_payroll_annual_cost()` function itself — both now sit on the same payroll-basis math. The
  residual above is upstream of that function (in what gross salary is even computed for a
  night-shift row on `A1`), not a drift between the two sheets' payroll formulas.

### D4 — Orphan helper sheets: stop writing, and clear the errors on the ones we can't drop

- **`A2 / A3 / A4`** — the pipeline stops writing `G3/K3` rates and the project name into them (no
  formula reads them; ESS1/4/16 are priced in Python). To remove their 204 `#DIV/0!` the change
  either (a) fills their own input cells so they recalculate cleanly as a *reference* view of the
  outsourced contracts, or (b) if that is not cheap, blanks the offending formulas the same way
  `_populate_fillup_sheets` already blanks unused `#DIV/0!` rows. Apply picks whichever is smaller;
  the spec only requires "no error the pipeline could resolve".
- **`B2 / B3 (Consumable) / B3 (Garbage) / B4 / B5`** — the pipeline stops writing rates/counts
  into them (dead-end). Their advertising / consumable figures are already computed in Python and
  written to `2.2 Common area Fund` / the budget sheet. Any `#REF!` they carry from the template is
  pre-existing and stays counted against the ceiling, not "introduced".
- The project-name write stays only where a formula elsewhere shows it.

### D5 — `verify.py` section 5d: `check_summary_reconciles`

New `verification/checks.py` function, mirroring `check_benchmark_reconciles` (one COM session,
`CalculateFullRebuild`, `_tol = max(5_000.0, abs(v)*5e-5)`):

1. For every code on `1. Summary` rows 12–54: summary `H` vs fund `AK` for that code.
2. For every fund leaf row 12–494: `G` vs `AK`.
3. `1. Summary!H46` vs `H13 − H20`; `H54` vs `H46 − H48`.
4. `EMH` vs `A1!AC96` + the recorded top-up.
5. Error-cell count vs a new ceiling in `verification/baselines/` (starts at the post-change count,
   only ever lowered).

Wired into `verify.py` after §5c. `deliverable_baseline.py` re-records `estimated_surplus_year1`
and adds the new staff figure; `baseline.py` (analysis) re-records the staff figures. Both on PM
sign-off.

### D6 — Deliverable notes (no figure change)

Two short strings written to `1. Summary` (near the existing header block): the chargeable-area
caveat (`0. Info` 4-product subset) and the advertising-on-a-separate-fund caveat. Written as plain
cell text with the same remark-format sweep already applied.

## Risks / Trade-offs

- **[The −644M surplus movement surprises the PM]** → measured on Wayne Tower with the components
  shown separately; recorded in `docs/05`; PM sign-off gate before archive. This is a *correction*,
  not new conservatism — the old surplus was overstated. (Estimated at −325M before implementation;
  −638M once the Reception top-up and the real `A1` formula chain were both first measured;
  −643,780,247 after the D2 real-row rework picked up `A1`'s smaller extras for Reception too — each
  revision is disclosed with its cause, not silently replaced.)
- **[`A1!AC96` row moves if Savills reshapes `A1`]** → `check_summary_reconciles` reads it by the
  same "Total cost/year" label lookup, not a bare row number; a reshape breaks the check loudly. The
  same applies to `_A1_UNPLACED_FIRST_ROW` (98) — a reshape of `A1`'s own rows (15-96) would need
  that constant re-verified; it is not label-derived, since there is no template label to key off for
  a row `A1` doesn't define.
- **[Reception's cost is not a small residual]** → originally assumed "one or two positions, <0.5%
  of staff." Measured on Wayne Tower it is 2 effective headcount out of 23 in the in-house roster
  (8.7%), costing 318,353,184 VND/year — proportionate to its headcount share, not an outlier, but
  not the small line item first assumed. Disclosed at its real size. **Now priced as real rows on
  `A1` itself** (D2 rework, on PM feedback that a formula-string constant wasn't an acceptable
  substitute for an auditable line item) — resolves the "later refinement" this risk note originally
  deferred.
- **[Clearing `A2/A3/A4` formulas loses a reference view a PM might want]** → those sheets show
  nothing today (all `#DIV/0!`); a clean zero or a populated reference view is strictly better.
- **[The analysis staff basis change moves the analysis baseline too]** → expected; re-recorded on
  the same sign-off, with the reason naming this change.

## Migration Plan

1. Land the code behind the reconciliation; run `verify.py` — expect it to FAIL on the moved
   figures (baseline not yet re-recorded).
2. Generate for Wayne Tower + one more real project; record `estimated_surplus_year1` before/after
   with the `RO2a` / staff split; manual spot-check (tasks §5).
3. PM reviews the movement and signs off.
4. Re-record `deliverable_baseline.json` and `baseline.json` with the reason; `verify.py` passes.
5. Rollback = revert the code; the baselines revert with it.

## Open Questions

- ~~Whether to fold Reception onto `A1. Staff cost` as a real row-group... or keep the Python
  top-up.~~ **Resolved 2026-09-14, on direct PM feedback**: folded onto `A1` as real rows (D2
  rework). A formula-string constant with no visible calculation wasn't acceptable once a PM was
  actually looking at `A1` for Reception's detail and couldn't find it. `EMH` is not quite
  `A1!AC96` exactly — it is `A1!AC96` plus `A1`'s own new unplaced-position row(s), all on `A1`.
