## Why

The tool sizes the cleaning crew from the open-space area (`Circulation / Hardscape Area` ÷ 3,000 m² per cleaner) plus
one supervisor per two towers. Two measurements show that this basis does not work:
- the standard sample gets 3 cleaning people on duty for 54,400 m² of fee-paying NFA, that is 18,133 m² per person,
  outside the 1,000–8,000 bounds of the service-level table (`Service Levels` sheet: `chưa phân loại: ngoài cận`);
- in the M3 acceptance run of 2026-10-19 (four real projects), `ESS4` cleaning was 0 VND on all four, because no
  source gives the open-space area, while the real budgets carry 1.4 to 14.4 bn VND a year.

The anonymous service-level table built from the real-budget scan store (`Ref_ServiceLevelProjects.csv`) already
measures real Savills projects on the same basis: 30 form-read projects have a median of 3,324 m² of fee-paying NFA
per cleaning person on duty (P25 2,822, P75 4,431), inside the Tiêu chuẩn band of 2,500–4,000.

## What Changes

Decided by the user on 2026-10-19:
- **Basis:** the cleaning people on duty per day = ROUNDUP(total fee-paying NFA ÷ the ratio). The open-space area no
  longer drives cleaning. It still drives the security patrol.
- **Ratio:** a new Roster Setup field `Cleaning: m² Fee-paying NFA per Cleaning Staff`, default 3,300 (the form-read
  median, rounded). It stays editable. Blank, zero, or a form without the field means 3,300, and the row says so.
- **Supervisors inside the count:** `Cleaning - Supervisor` stays ROUNDUP(towers ÷ towers per supervisor), and
  `Cleaning - Common Area` = the total minus that, at least 1. With the default ratio, the project therefore lands on
  the chosen ratio, measured the way the `Service Levels` sheet measures it.
- **Older forms:** their `Cleaning - Common Area` cell still holds the open-space formula. The generator already
  recomputes a formula cell from Project Info and Roster Setup, so old forms get the new rule. The old label
  `Cleaning: m² Open Space per Cleaner` is no longer read, because its value means something else. A number the PM
  typed over the formula still wins.
- **Figures move:** `ESS4` and the cleaning rows on Staffing Demand, the roster, `A3. Vệ sinh - Cleaning`, the
  analysis's Service sheet and `Service Levels`, and the fund totals that include them. The standard sample goes from
  3 to 17 cleaning people on duty. The recorded verify baselines are re-recorded once, in group 10 of
  `apply-head-of-pm-decisions-2026-10`, so this change is measured as its own A/B and verified with the baseline gates
  open.

## Capabilities

### New Capabilities
- `cleaning-staffing-default`: how the cleaning crew is sized when the PM has not typed it.

### Modified Capabilities
- none

## Impact

- Code: `generate_project_budget.py` (`_RATIO_DEFAULTS`, the ratio read, `RATIO_DRIVEN_STAFFING`, the ratio list on the
  deliverable), `generate_project_output.py` (the ratio description on Staffing Estimate), `build_project_input_form.py`
  (Roster Setup row 6, the Staffing Demand formula and its note).
- Not touched: `fill_management_fund_sheet` and `estimate_opex` (lane A, M2 part 2); `ESS1` security; the cleaning
  post price (8,000,000 VND per post per month, one reference project).
- Tests: new unit tests; verify with the baseline gates open; A/B on the fixtures and on the four real projects of M3.
