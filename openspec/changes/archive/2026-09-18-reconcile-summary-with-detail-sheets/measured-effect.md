# Measured effect — reconcile-summary-with-detail-sheets

Measured 2026-09-14 by regenerating the deliverable via `generate_project_budget.build_budget()`
under `verification.run_workflow.redirected_paths` (writes land in a throw-away temp directory, the
real source workbook is never touched — SHA-256 hash-verified unchanged before/after every run
below) and reading the result through Excel COM (`CalculateFullRebuild`) so every formula chain
(RO2a, EMH2 → A1, the analysis workbook's payroll columns) is live-recalculated, not read from a
stale cache.

## Real project used: Wayne Tower

This is the only real, currently-filled project workbook in this environment
(`Budget_Agent/reports/Project_Budget_Input.xlsx`). The task called for a second real project as a
cross-check; none exists here — the other files in `reports/` are pre-change backup snapshots of
this same project (`_PRE_HOLIDAYS_`, `_PRE_MIGRATION_`, `_PRE_ROLES_`), not a distinct project, and
`docs/project-status.md` already records that this clone of the repo has no other source workbooks.
The `ZZ Sample Tower (TEST DATA — NOT A REAL PROJECT)` fixture is included below as a second data
point, clearly marked — but it turns out to carry the *same* staffing/demand numbers as Wayne Tower
(confirmed: every figure below matches exactly), so it validates the formula wiring, not an
independent magnitude.

| Component | Before (old formula) | After (this change) | Movement |
|---|---:|---:|---:|
| `RO2a` (Bank Interest on Savills account) | `G37`=10,000,000, `AK37`=5,000,000 (mismatched) | `G37`=`AK37`=0 | **−5,000,000** revenue |
| `EMH2` (Staff cost for Savills) | 4,291,165,917 (Python `Σ position_bare_annual_cost × 1.215`) | 4,929,946,164 (`A1!AC96` 4,611,592,980 + `A1` rows 98:99 — Reception, 2 headcount, live formula — 318,353,184) | **+638,780,247** cost |
| **Year-1 estimated surplus** | — | — | **−643,780,247 VND** |

Same figures, exactly, on the `ZZ Sample Tower` fixture (see note above on why).

**Revised once more after this table was first written**: Reception's cost was initially a
Python-computed constant folded into `EMH2`'s formula string (312,597,927 VND, giving a total swing
of −638,024,990). On direct feedback that this wasn't auditable — nothing on `A1. Staff cost` showed
how that number was derived — Reception was given real rows on `A1` itself (one per headcount unit,
`A1`'s own exact formula chain, same statutory-cap cells every other row uses). The live formula
naturally also picks up `A1`'s smaller extras the Python constant had omitted (team building, 1.3%
training, annual checkup, accident insurance, uniform), moving Reception's cost from 312,597,927 to
318,353,184 (+5,755,257) — reflected in the table above.

## What moved and why

- **RO2a** was a template default (`Half a Year` frequency, only one of two payment-month cells
  ever filled) that made the fund sheet's `G` (Total Price) read 10,000,000 while `AK` (what
  `1. Summary` actually sums) read only 5,000,000 — a fabricated 5,000,000 of "bank interest" with
  no real basis. Zeroing it removes that fabrication; a PM now enters a real figure if there is one.
- **EMH2** moved because the old Python shortcut (`headcount × rate × 21.5%` employer-insurance
  approximation) never referenced the deliverable's own real payroll calculator
  (`A1. Staff cost 08.2026 (VN)`, which nothing previously read). `A1` prices 13th-month salary,
  employer SI/HI 20.5% and UI 1% (both capped), Trade Union 2% (capped), and Savills' own 10% admin
  markup — a materially larger basis than the flat 21.5% shortcut. `EMH2` is now a live formula
  reference into `A1!AC96` plus `A1`'s own row(s) for the one roster position (`Reception`) that has
  no *predefined* row-group there.
- **Reception is now priced as real rows on `A1` itself** (2 rows, one per headcount unit — B98/B99
  = "Lễ tân", D98/D99 = "LT" — each using row 15's own formula chain, so its 13th-month/SI-HI/UI/
  union/markup math is identical to, and shares the same statutory-cap cells as, every other
  position on the sheet). This replaced an earlier version where Reception's cost was a
  Python-computed constant folded into `EMH2`'s own formula string — correct in total but not
  auditable, since nothing on `A1` showed how the number was derived. Reworked after that was
  flagged as unacceptable.
- Reception's real cost (318,353,184 VND) is **not** the small "<0.5% of staff" residual first
  assumed in design.md — measured, it is 2 of the 23-head in-house roster (8.7%), and its cost is
  proportionate to that headcount share, not an outlier. Corrected in the design doc and in the
  `Staff (Roster)` analysis sheet's own disclosure text.
- The analysis workbook (`generate_project_output.py build_staff_sheet`) was moved onto the same
  payroll-basis components — but it still estimates Reception via the narrower
  `full_payroll_annual_cost()` function (312,597,927), not `A1`'s own now-real formula (318,353,184)
  — a small, disclosed +5,755,257 gap on top of the ~4% in-house-total residual already noted (not
  the ~1% first assumed) — isolated to a pre-existing, separate gap in `A1`'s own gross-salary
  assignment for night-shift roles (it averages Morning/Afternoon/Night into one flat salary,
  dropping the night-shift pay differential the rest of the pipeline applies). Both residuals are in
  what gross salary/extras `A1` assigns per row, not in the payroll-basis math this change adds on
  top of it — out of scope here (re-pricing staff is an explicit non-goal); the night-shift gap is
  flagged separately for a follow-up change.
- **204** `#DIV/0!` cells on `A2`/`A3`/`A4` (Security/Cleaning/Landscape reference sheets, read by
  no formula in the deliverable) are gone — their allocation-split basis (product NFA + car-slot
  count) is now filled instead of left at the template's all-zero default. The pipeline also stops
  writing rate/count values other formulas never read on 8 orphan helper sheets. Total deliverable
  error-value cells: 254 → 50 (the remaining 50 are the parking-allocation block, out of scope,
  owned by a separate change).
- `verification/checks.py check_summary_reconciles` (wired into `verify.py` as a new section) now
  enforces: every `1. Summary` code total ties to its `2. Budget-Management Fund` children, every
  fund leaf's `G` equals `AK`, the surplus derivation (`H46`/`H54`), and `EMH` equals `A1`'s own
  total (found by its own label, not a hardcoded cell) plus the top-up. Clean pass (506/506) on
  Wayne Tower, ZZ Sample, and the default verification fixture.

## Not yet done

- Task 6.2 (manual spot-check) and 6.3 (Head-of-PM sign-off) — pending, see tasks.md.
- Task 5.3 (re-recording `deliverable_baseline.json` / `baseline.json` for the moved figures) is
  deliberately **not** done yet — gated on 6.2/6.3 sign-off, per design.md's migration plan.
- Task 7 (deliverable caveat notes, docs updates) — pending.
