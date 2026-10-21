## Context

`_staff_on_duty()` (`generate_project_budget.py`) recomputes every ratio-driven Staffing Demand row that still holds
its seeded formula, from Project Info and Roster Setup, and uses a number the PM typed as typed. `contract_cost()` turns
the cleaning rows into posts: a row covered 7 days a week counts ROUNDUP(people × 7/6) posts, priced at the citywide
8,000,000 VND per post per month. `service_levels.measure_cleaning()` divides the total fee-paying NFA (`total_nfa`,
every product) by the people on duty, supervisors included.

## Decisions

- **D1 Ratio over fee-paying NFA, not open space.** Every form has NFA (Apartment NFA is required). No source in the
  M3 run had the open-space area. The measure is the one the service-level table classifies, so the default lands
  where the table can say what it means.
- **D2 Default 3,300 from the real projects.** The median of the 30 form-read, classified projects of
  `Ref_ServiceLevelProjects.csv` (3,324), rounded to 3,300. It is a fixed number on the form, not computed at run
  time, so a PM sees it and can change it; the CSV is the evidence, quoted in the field's note.
- **D3 Supervisors inside.** Cleaners = max(1, ROUNDUP(NFA ÷ ratio) − ROUNDUP(towers ÷ towers per supervisor)). The
  subtraction uses the supervisor rule, not whatever the supervisor row holds, so the cleaner row stays computable on
  its own. A PM who types a supervisor count leaves the cleaner suggestion unchanged.
- **D4 New label, old one ignored.** The new field gets a new label. An older form keeps
  `Cleaning: m² Open Space per Cleaner` = 3,000, which is a different measure: reading it as the new ratio would
  give 3,000 m² NFA per person without anyone having chosen it. So the old label is not read, and the default is
  used with the reason "the form has no such field".

## Risks

- One price for every cleaning post (8,000,000 VND, one reference project) now multiplies a much larger count. `ESS4`
  rises on every project. That is the intended correction, measured in the A/B.
- Very small projects get at least one cleaner plus the supervisors, as before.
