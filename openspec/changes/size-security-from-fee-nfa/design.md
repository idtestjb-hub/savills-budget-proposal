## Context

`_staff_on_duty()` recomputes every ratio-driven Staffing Demand row that still holds its seeded formula, from Project
Info and Roster Setup, and uses a number the PM typed as typed. `contract_cost('Security')` (inside
`fill_management_fund_sheet`, not edited here) turns the security rows into posts:
- each row counts ROUNDUP(people × 7/6) roles when it covers 7 days;
- three 8-hour roles make one 24-hour post at 17,500,000 VND per month;
- night rows add 30%.

`service_levels.measure_security()` counts on-duty people × shift hours ÷ 24 per 10,000 m² of fee-paying NFA.

## Decisions

- **D1 Posts from fee-paying NFA, gates as the floor.** total = max(ROUNDUP(NFA ÷ 10,000 × ratio), gate posts + 1),
  where gate posts = ROUNDUP(Gate Count × Staff per Gate). Patrol per shift = total − gate posts − 1, at least 0. The
  subtraction uses the gate rule, not whatever the gate rows hold, so the patrol row stays computable on its own, as
  in the cleaning change (its D3).
- **D2 Default 1.7 from the real projects.** The median of the 32 form-read, classified projects of
  `Ref_ServiceLevelProjects.csv` (1.719), rounded. It is a fixed number on the form, not computed at run time, so a PM
  sees it and can change it.
- **D3 New label in row 5, old one ignored.** `Security: m² Open Space per Patrol Staff` measures something else.
  Reading it as the new ratio would give 5,000 posts per 10,000 m². So the old label is not read, and the default is
  used, with the reason "the form has no such field".
- **D4 An older form's single patrol row.** That form has one `Security - Patrol / Open Space` row on shift S. The
  reader adds the afternoon and night rows in memory, with the same rule and a note, before anything uses the demand
  list. The posts, the money, the roster and the service level therefore equal those of a new form. Doing it in
  memory, rather than relabelling the row `24H`, keeps the night premium on one row in three, as a new form has it.
  The user's choice "count that row as a 24-hour post" is met this way.
- **D5 Pricing untouched.** `contract_cost` keeps the per-row 7/6 relief and the night blend (user's choice,
  2026-10-19).

## Risks

- A small project gets at least its gate and CCTV posts, as before; the floor never lowers today's count.
- The per-row 7/6 rounding makes `ESS1` about 25-45% above posts × 17.5 m × 12 on the M3 projects. This was measured
  and accepted; the 7/6 question is open for after core v1.
- Projects whose real budgets are Nâng cao (well above 1.7 posts per 10,000 m²) stay below their real figure.
