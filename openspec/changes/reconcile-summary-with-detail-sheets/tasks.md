## 1. RO2a — zero the split placeholder

- [x] 1.1 In `fill_management_fund_sheet()` (`generate_project_budget.py`), after the RM/parking
  writes, explicitly set `2. Budget-Management Fund!F37 = 0` and clear `K37`. Add a one-line comment
  citing `docs/09-template-map.md` §9 finding 1. Verify by generating and reading (COM): `G37` and
  `AK37` both = 0; `1. Summary!H18` (RO) drops by 5,000,000 vs the pre-change run.
  **Done 2026-09-14** — COM-verified on Wayne Tower: `G37 = AK37 = 0`.

## 2. EMH2 — drive from the A1 payroll sheet

- [x] 2.1 Add a helper that returns the annual cost of every in-house roster position
  `fill_staff_cost_sheet()` did **not** place on `A1` (today: Reception), priced on the full-payroll
  basis from task 3.1 — not `× 1.215`. Verify it returns 0 when every position maps to an `A1`
  row-group, and the Reception cost otherwise.
  **Done 2026-09-14, then reworked same day on PM feedback** — first version applied
  `full_payroll_annual_cost()` (shared with task 3.1) to each `unplaced` position's
  `position_bare_annual_cost`, giving a Python CONSTANT (312,597,927 VND for Reception). Feedback:
  that number wasn't auditable — nothing on `A1` showed how it was derived. Reworked: `_unplaced_
  positions(demand)` now returns `(name, headcount, monthly_gross)` for `fill_staff_cost_sheet()` to
  write as REAL rows on `A1` (task 2.1a below), and `EMH2` references those rows live instead of a
  constant. On Wayne Tower/ZZ Sample, `unplaced` = exactly `['Reception']`, 2 headcount, real `A1`
  total 318,353,184 VND (~6.9% of `A1!AC96`) — matching Reception's 8.7% headcount share of the
  23-head roster (proportionate, not an outlier; corrected the design's earlier "<0.5%" estimate —
  see design.md Risks).
- [x] 2.1a (added) Give every `_unplaced_positions()` entry a REAL row on `A1. Staff cost` —
  `fill_staff_cost_sheet()`, starting at `_A1_UNPLACED_FIRST_ROW` (98, the first blank row below
  A1's own grand total), one row per headcount unit (mirroring `fill_group()`'s per-person write for
  every other position), copying row 15's own formula chain (I/J/K/L/M/N/O/P/Q/R/S/T/U/V/W/X/Z/AA/
  AB/AC — same `$L$7`/`$T$7`/etc. cap cells every other row shares) with `D≠"PM"` so the row falls
  to the non-PM team-building/accident-insurance branches. A one-line Vietnamese note above the
  block explains why these rows have no fixed position in the standard layout.
  **Done 2026-09-14** — COM-verified on Wayne Tower: rows 98/99 both "Lễ tân"/"LT", `G`=8,500,000
  each, `AC`=13,264,716 each (318,353,184/year combined). Bug caught and fixed during verification:
  the first version wrote ONE row per position NAME (using the per-person gross, not multiplied by
  headcount) — silently halving Reception's cost. Fixed to flatten to one row per headcount unit;
  `EMH2`'s SUM range sizing in 2.2 had the identical bug, fixed the same way.
- [x] 2.2 Replace the `write_even_monthly('staff_remainder', …)` call for `EMH2` (row 83) with a
  dedicated write: `C83 = "Monthly"`, `F83 = "=('A1. Staff cost 08.2026 (VN)'!AC96 + <top_up>)/12"`
  (real formula string, `<top_up>` a Python constant), and the remark explaining it now equals the
  A1 payroll total. Keep the sec/cln/lsc exclusion note. Verify (COM): `G83` and `AK83` both equal
  `A1!AC96 + top_up` within rounding; `1. Summary!H22` (EMH) rises to that value.
  **Done 2026-09-14, reworked same day (see 2.1a)** — `<top_up>` is now a live reference to `A1`'s
  own unplaced-position row(s), not a Python constant: `SUM('A1...'!AC98:AC99)*12` for 2+ rows, a
  bare cell ref for exactly 1. COM-verified on Wayne Tower: `G83 = AK83 = 1. Summary!H22 =
  4,929,946,164 = A1!AC96(4,611,592,980) + (AC98+AC99)*12(318,353,184)`, exact to the VND.
  `verification/checks.py check_summary_reconciles`'s own formula-parsing (task 5.1) was updated to
  read these live cells too, rather than assuming a constant — confirmed via `check_summary_
  reconciles` passing 506/506 on Wayne Tower and ZZ Sample after the rework.
- [x] 2.2a (added) `data/master_list_verified/Costing_Method_Catalogue.csv`'s `EMH2` row still
  described the OLD method (`method`=`headcount-x-salary-plus-employer-insurance`, `method_detail`=
  "Sum(headcount x salary x 12) + employer insurance contribution (~21.5% loading)") — caught when
  the user compared the deliverable against "the AI Guide rule" and it didn't match. **Confirmed
  low-blast-radius first**: grepped the pipeline for `CATALOGUE_PATH` — the only live read is
  `_catalogue_vat_rule()`, which reads just the `#`-header VAT-rule block, never the data rows; and
  `verify.py`'s `check_remark_content` uses its own separate hardcoded `_REMARK_RECIPE_ANCHORS`, not
  this CSV. So the stale row was a documentation drift, not a functional bug — nothing in the
  deliverable or `verify.py` was reading the wrong rule. Fixed anyway (it is the recorded contract
  for what each code's methodology is): `method` → `a1-live-formula-plus-unplaced-rows`,
  `method_detail` and `remark_components` rewritten to describe the real `A1`-formula-plus-real-rows
  approach. Re-verified `_catalogue_vat_rule()` still parses correctly and the CSV's other 110 rows
  are untouched (row count unchanged, spot-checked `RM.AP`).
- [x] 2.3 Remove the now-dead `staff_remainder = staff_grand_total − security_loaded − …`
  computation and its `position_annual_cost` `× 1.215` path **only if** nothing else uses them;
  otherwise leave and note. Verify the generator still runs (`python run.py`).
  **Done 2026-09-14** — removed `per_position`, `staff_grand_total`, `category_cost`/
  `category_total`, `security_loaded`/`cleaning_loaded`/`landscape_loaded`, `staff_remainder`,
  `n_security`/`n_cleaning`/`n_landscape`, and the dead `position_annual_cost(d)` nested function.
  `position_bare_annual_cost` and `position_annual_cost_outsourced` kept (still price ESS1/4/16).
  Generator re-run clean on both fixtures via COM above.

## 3. Analysis workbook — same payroll basis

- [x] 3.1 In `generate_project_output.py` `build_staff_sheet()`, add the employer-side payroll
  components `A1` applies — 13th-month spread, statutory SI/HI/UI at the 2026 caps, Trade Union 2%,
  and the `× 1.10` admin markup — as explicit formula columns, replacing the flat `× 1.215`. Verify
  the analysis `Staff` sheet's annual total lands within 1% of the deliverable's `A1!AC96` for the
  Wayne Tower and fixture inputs; state any residual and its cause on the sheet.
  **Done 2026-09-14** — added columns T-Z (13th-month, capped SI/HI, capped UI, capped Trade Union,
  subtotal, admin markup, full total), COM-verified on Wayne Tower. Residual is **~4%, not ~1%** —
  see design.md D3 for the full measurement. Root cause isolated and disclosed on the sheet itself
  (A1's gross-salary step drops the night-shift differential for shift roles; out of scope to fix
  here). The disclosure note text was corrected to state this instead of the original "~1%" claim.
- [x] 3.2 Confirm the `EMH2 ↔ build_staff_sheet` "never drifts" invariant still holds — both now on
  the A1 basis. Verify by comparing the two totals for one project (COM).
  **Done 2026-09-14, note updated after task 2.1a's rework** — originally: the shared
  `full_payroll_annual_cost()` function itself does not drift — Reception matched to the VND on
  both sheets (312,597,927 = 312,597,927), confirming the invariant for the function. After 2.1a
  gave Reception real rows on `A1` (using `A1`'s own full formula, not `full_payroll_annual_cost()`),
  that specific match no longer holds — `A1`'s real Reception total is 318,353,184 vs this sheet's
  312,597,927 estimate (design.md D3). The invariant now needs a caveat: `full_payroll_annual_cost()`
  itself still doesn't drift from `A1`'s employer-side components, but `A1` prices Reception on its
  own FULLER formula (extras included) that this function deliberately omits — a disclosed, small
  residual, not a drift bug. The ~4% in-house-total gap from 3.1 (night-shift differential) is a
  separate, larger, pre-existing issue, unrelated to this.

## 4. Orphan helper sheets

- [x] 4.1 In `build_budget()` / `fill_management_fund_sheet()`, remove the writes to sheets no
  formula reads: `A2. Bảo vệ - Security` (`G3`), `A3. Vệ sinh - Cleaning` (`K3`),
  `A4. Cây xanh - Landscape` (`K3`), `B2. Mùi hương - Scent`, `B3. Vật tư vệ sinh - Consumable`,
  `B3. Thu gom rác - Garbage coll `, `B4. DT Quảng cáo - Elevator adv`,
  `B5. Đơn giá gửi xe - Parking pr` (rates/counts). Keep only a project-name write where a formula
  elsewhere displays it. Verify by scanning the generated deliverable: none of those cells is
  referenced by any formula, and ESS1/4/16 + advertising figures are unchanged.
  **Done 2026-09-14** — confirmed by direct formula scan of the template: 0 cross-sheet references
  to any of these 8 sheets' name/rate cells (Consumable's *data* cells C7/D7/D8/D11 ARE read by
  Garbage's own formulas — a within-the-orphan-family link, still a dead end downstream, so both
  stay removed per design.md D4). Also found A3/A4's rate write was landing on the wrong cell (`K3`,
  a text-label cell) instead of the template's real rate input (`J3`) — moot now that the write is
  removed entirely, not worth a separate fix.
- [x] 4.2 Clear the 204 `#DIV/0!` cells on `A2 / A3 / A4` — either fill each sheet's own input
  cells so it recalculates as a clean reference view of the outsourced contract, or blank the
  offending formulas (same approach `_populate_fillup_sheets` uses for unused `#DIV/0!` rows). Pick
  the smaller change. Verify (COM): those three sheets recalculate with 0 error cells.
  **Done 2026-09-14** — chose (a): every position row's cost-split formula (`Q/R/S/T` on A2,
  `T/U/V/W` on A3/A4) divides by `SUM` of that sheet's own allocation-basis cells (A2!M7:P7,
  A3/A4!P7:S7 — Apartment/Shophouse/Retail/Parking), which the template ships all-zero. Filled them
  with this project's real product NFA + car-slot count (12 cells total, 3 sheets) instead of
  blanking ~200 formulas. COM-verified on Wayne Tower: total deliverable error cells 254 -> 50, and
  the 50 remaining are entirely the out-of-scope parking-allocation block (`2. Budget-Management
  Fund`) — A2/A3/A4 each now recalculate with 0 errors.
- [x] 4.3 Record the deliverable's post-change error-cell count as the new ceiling in
  `verification/baselines/` (a small JSON, or extend `deliverable_baseline.json`). Verify it is
  below the previous 257 by exactly the number of cells removed in 4.2.

## 5. Verification

- [x] 5.1 Add `check_summary_reconciles(paths)` to `verification/checks.py` (mirror
  `check_benchmark_reconciles`: COM, deliverable copy, `CalculateFullRebuild`, `_tol = max(5_000.0,
  abs(v)*5e-5)`). Checks: (a) `1. Summary` code totals vs fund `AK`; (b) every fund leaf `G` vs
  `AK`; (c) `H46 = H13 − H20`, `H54 = H46 − H48`; (d) `EMH` vs `A1!AC96 + top_up` (A1 total found by
  its "Total cost/year" label, not a bare row number); (e) error-cell count vs the recorded ceiling.
  Return `(ok, rows, differences, notes)`.
  **Done 2026-09-14** — while building this, found and fixed two real bugs in the check itself
  (not the pipeline): (1) naively summing every fund row whose code shared a prefix
  double-counted every section — a family carries a bare "section header" row (code exactly
  'EMH', 'RI', 'RPa', ...) whose own G/AK is already `SUBTOTAL()` of its numbered children, so
  summing both doubled several totals (EMH, RI, EMA, ESM, EN, EEW, EEE, EED all showed exactly
  2x). Fixed by reading each row's own G-formula text and excluding rows whose formula is a
  `SUBTOTAL(...)` (a structural signal, not a guess at which code strings are "headers" — `RO`
  turned out to nest THREE levels of subtotal, RO > RO2/RO3/RO4 > RO2a/RO2b etc., which a
  code-name heuristic would have missed). (2) An earlier attempt using "does this code look like a
  string-prefix of another matched code" false-positived on `ESM2` vs `ESM25` (decimal-numbering
  coincidence, not a parent/child relation) — replaced by the formula-based signal above. (d)
  implemented as a genuine label search across A1's used range (not a hardcoded `Cells(96,29)`),
  so a future A1 reshape is caught by drift between the label-found total and the pipeline's
  still-hardcoded EMH2 formula, rather than both sides silently agreeing on the wrong cell.
  COM-verified clean (506/506, 0 differences) on Wayne Tower, ZZ Sample, and the default
  `Sample_Project_Input.xlsx` fixture.
- [x] 5.2 Wire `check_summary_reconciles` into `verify.py` as section 5d, after 5b/5c; on failure
  print the disagreeing figures and exit non-zero. Verify `python verification/verify.py` runs the
  new section.
  **Done 2026-09-14** — added as section 5e (verify.py already had an existing, unrelated 5d —
  `check_remark_content`, from `apply-guideline-remark-model` — kept its numbering, placed this
  check after it rather than renumbering something already shipped).
- [ ] 5.3 Re-record `verification/baselines/deliverable_baseline.json` (`estimated_surplus_year1`
  + a new staff figure) and `verification/baselines/baseline.json` (analysis staff figures) with a
  `--reason` naming this change — **only after task 6.2 sign-off**. Verify `verify.py` PASS on the
  following run.

## 6. Measure, spot-check, sign-off

- [x] 6.1 Generate the deliverable + analysis for Wayne Tower and one more real project. Record, for
  each: year-one `estimated_surplus_year1` before and after, split into the `RO2a` component
  (−5,000,000) and the staff component (≈ −320,000,000). Write the table into the change's
  `measured-effect.md`.
  **Done 2026-09-14, with a scope note, figure revised once more after task 2.1a's rework** — this
  environment has only ONE real, filled project workbook (Wayne Tower); the other `reports/` files
  are backup snapshots of that same project, not a second one. Measured on Wayne Tower (real) and
  `ZZ Sample Tower` (test fixture, clearly labeled) — the actual movement is **−643,780,247 VND**
  (was −638,024,990 before Reception got real `A1` rows; ≈−325,000,000 was this task's own original
  text — see design.md D2's corrected figure and `measured-effect.md`). Table written to
  `measured-effect.md`, source hash-verified unchanged before/after.
- [ ] 6.2 **Manual spot-check** (project rule — aggregation logic changed): by hand confirm
  (a) `EMH` on `1. Summary` = `A1. Staff cost` row 96 + Reception; (b) `RO2a` `G` and `AK` both 0;
  (c) `1. Summary` total revenue = sum of its child rows and = `2. Budget-Management Fund`'s `AK12`;
  (d) analysis `Staff` total within 1% of `A1!AC96`. Record the four checks and the projects used.
  **NOT DONE — needs the Head of PM** (project rule: a human spot-check, not an automated one,
  before a change that alters aggregation logic on client-facing figures). Note (d)'s own target
  ("within 1%") is now known to be ~4% per task 3.1 — the spot-check should confirm that residual is
  understood/acceptable, not that it hits the original 1% figure.
- [ ] 6.3 Present the measured movement to the Head of PM; capture the sign-off in the change notes
  and `docs/05-decisions.md` before archiving.

## 7. Docs

- [x] 7.1 Add the two `1. Summary` caveat notes (chargeable area = `0. Info` subset; advertising on
  `2.2 Common area Fund`) in `add_comparison_sheet`'s sibling location or `build_budget`. Verify
  **Done 2026-09-14** — written to `1. Summary!K10`/`K11` (blank in the template, next to the
  chargeable-area figure at H10), Vietnamese-only per the established convention, reusing the
  `_rowless` product list already computed for `0. Info!G7`'s identical caveat rather than
  recomputing it. COM-verified on Wayne Tower (correctly names its rowless product, "Nursery / Nhà
  trẻ") and confirmed `check_summary_reconciles` still passes 506/506 (no figure moved).
  they render as plain text on `1. Summary` and move no figure.
- [ ] 7.2 Update `docs/05-decisions.md` (new decision entry), `docs/09-template-map.md` §9 (mark
  findings 1, 2, 4 resolved; leave the RO2a template-owner note), and `docs/project-status.md`.
  Verify all three mention the change with the date and the signed-off figure movement.
