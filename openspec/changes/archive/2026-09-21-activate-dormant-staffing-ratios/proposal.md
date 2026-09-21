## Why

`_staff_on_duty()` (`generate_project_budget.py:426-471`) treats a Staffing Demand row as a deliberate
PM override — and skips the portfolio-derived ratio entirely — whenever its cell holds a truthy
number that is not a formula string (`numeric and not is_formula`). `build_project_input_form.py`'s
`EXAMPLE_DEMAND` list seeds 8 of the 11 portfolio-ratio-driven roles at a bare `1` (Property Manager,
Chief Engineer, Building Executive, Customer Service, Reception, Technician ×3 shift rows, Shift
Leader ×3 shift rows, Amenities Attendant ×2 shift rows — 13 rows total), which trips that same
detector on every freshly-generated intake form, before any PM has typed anything. Verified against
`Fact_StaffingRatio_ByPosition.csv`: every one of these 8 roles clears the `_POSITION_RATIO_MIN_N =
10` usability floor (n = 25, 24, 19, 22, 12, 26, 22, 12 respectively), so this is not a thin-data
non-issue — the ratio would produce a real, likely different headcount for all 8 if the seed did not
block it.

Three roles added later (2026-09-09: Assistant Property Manager, Accountant, Cashier) are seeded at
`0` instead, and `0` is falsy, so the same override check does not trip — their ratios already fire
correctly today. That is the working precedent this change reuses, not a new mechanism.

## What Changes

- Reseed the 8 affected roles' 13 `EXAMPLE_DEMAND` rows from `1` to `0`, matching the Assistant
  Property Manager / Accountant / Cashier pattern already shipping in the same file.
- No change to `_staff_on_duty()`, `_portfolio_headcount()`, or any ratio arithmetic — this only
  changes which rows the already-correct, already-exercised ratio logic actually reaches.
- **BREAKING** in effect, not in interface: any FRESH intake form generated after this change will
  show a different (ratio-derived, not a flat `1`) starting headcount for these 8 roles, which moves
  that project's staff cost if the PM does not override it. A project's ALREADY-generated intake
  form — one a PM has already opened, possibly already typed real numbers into — is unaffected; the
  seed only matters before the form exists.

## Capabilities

### New Capabilities
- `portfolio-derived-staffing-defaults`: the Staffing Demand sheet's default (non-overridden)
  headcount for a role with a portfolio-derived ratio SHALL come from that ratio, not from a static
  placeholder — covering the mechanism as a whole (which already partly works, for 3 of 11 roles)
  rather than only the 8 rows this change activates. This capability was never formally specified
  despite already being partly built and shipping; this change is the first point its externally
  observable behavior is correct for every role it claims to cover, so it is the right moment to
  specify it.

### Modified Capabilities
(none — no existing spec covers the Staffing Demand ratio mechanism; confirmed no archived change
under `openspec/changes/archive/` and no capability under `openspec/specs/` names it)

## Impact

- `Budget_Agent/source_code/build_project_input_form.py`: `EXAMPLE_DEMAND`'s 13 affected rows'
  `StaffPerDay` value, `1` → `0`.
- No change to `generate_project_budget.py` — `_staff_on_duty()`/`_portfolio_headcount()` are correct
  today and already serve the 3-role batch that works; this change only lets them reach the other 8.
- Every downstream consumer of Staffing Demand headcount (roster sheet, `A1. Staff cost`, `EMH2`
  payroll pull, staff-cost total, year-one surplus) moves for any freshly-generated project that
  contains one of the 8 affected roles and whose PM does not override the new default — needs the
  same measure-then-Head-of-PM-sign-off gate as every other figure-moving change in this project (see
  `fill-guideline-required-line-items`, `activate-common-area-fund-cost-share`,
  `reconcile-summary-with-detail-sheets` for the established pattern), with a per-role breakdown in
  the measured effect rather than 8 separate change proposals — matching how this project has already
  batched other multi-item fixes (`localize-line-level-remarks`, `fill-guideline-required-line-items`).

Not in scope: `rank-comparables-by-location` (separate proposal, already created this session) and
the elevator-count change (queued next) — independent in scope and risk, same reasoning this project
already used to keep `localize-line-level-remarks` and `add-multiyear-preopening-budget-phases`
separate despite a shared source investigation.
