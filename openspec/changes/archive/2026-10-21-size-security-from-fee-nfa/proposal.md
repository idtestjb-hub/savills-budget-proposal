## Why

The tool sizes security from the gates and the open-space area: each gate gets one guard per shift, the CCTV room gets
one per shift, and patrol is `Circulation / Hardscape Area` ÷ 5,000 m² on the morning shift only. No source in the M3
acceptance run (2026-10-19, four real projects) gave the open-space area, so patrol was 0 everywhere, and a project
without a stated gate count had only the CCTV room. `ESS1` came out at 420 to 1,260 million VND a year, against 1,209
to 17,446 million in the real budgets (25,585 million |gap| over the four).

The anonymous service-level table (`Ref_ServiceLevelProjects.csv`) already measures real Savills projects on the
basis the `Service Levels` sheet classifies: 24-hour security posts per 10,000 m² of fee-paying NFA. The 32 form-read,
classified projects have a median of 1.719 (P25 1.269, P75 2.325), inside the Tiêu chuẩn band of 1.5–3.0.

## What Changes

Decided by the user on 2026-10-19:
- **Basis:** the security 24-hour posts = max(ROUNDUP(total fee-paying NFA ÷ 10,000 × the ratio), gate posts + 1
  CCTV post). Gate rows and CCTV rows stay as they are (the floor). Patrol takes the rest, on all three shifts. The
  open-space area no longer drives security.
- **Ratio:** a new Roster Setup field `Security: 24h Posts per 10,000 m² Fee-paying NFA`, default 1.7 (the form-read
  median, rounded). It replaces `Security: m² Open Space per Patrol Staff` in row 5. Blank, zero, or a form without the
  field means 1.7, and the row says so. The old label is not read.
- **Patrol rows:** a new form has `Security - Patrol (Morning)`, `(Afternoon)` and `(Night)`, each = MAX(0, posts −
  gate posts − 1). An older form has a single `Security - Patrol / Open Space` row on the morning shift. The run then
  counts that row as a 24-hour post on all three shifts, so the money and the posts equal a new form's. A number the PM
  typed over a patrol formula still wins.
- **Pricing unchanged:** 17,500,000 VND per 24-hour post per month, the per-row 7/6 rest-day relief and the night
  premium stay as today (the user's choice: the 7/6 question is left for after core v1).
- **Figures move:** `ESS1`, the security rows on Staffing Demand, the roster, `A2. Bảo vệ - Security`, the analysis's
  Service sheet and `Service Levels`, and the fund totals that include them. Recorded verify baselines are re-recorded
  once, in group 10 of `apply-head-of-pm-decisions-2026-10`.

## Capabilities

### New Capabilities
- `security-staffing-default`: how the security posts are sized when the PM has not typed them.

### Modified Capabilities
- none

## Impact

- Code: `generate_project_budget.py` (`_RATIO_DEFAULTS`, the ratio read, `RATIO_DRIVEN_STAFFING`, the patrol rows of
  an older form), `build_project_input_form.py` (Roster Setup row 5, the three patrol rows and their formula),
  `generate_project_output.py` (the ratio description on Staffing Estimate).
- Not touched: `fill_management_fund_sheet` and `contract_cost` (pricing), `estimate_opex`, `master_comparables`,
  the cleaning and landscape rules.
- Tests: new unit tests; verify with the baseline gates open; A/B on the fixtures and on the four real projects of M3.
