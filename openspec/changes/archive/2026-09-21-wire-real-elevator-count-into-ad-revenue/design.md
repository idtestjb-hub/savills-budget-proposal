## Context

`ELEVATOR_AD_ITEMS` is a static list of `(item, rate, qty_per_tower, flat_qty, assumption)` tuples,
iterated identically by two call sites: `build_additional_revenue_sheet` (`generate_project_output.py`,
analysis workbook) and `fill_common_area_fund_sheet` (`generate_project_budget.py`, client
deliverable, via its own `_AD_ITEM_VI` Vietnamese-label lookup added earlier this session). Both loops
compute `est_qty = round(tower_count * qty_per_tower) if qty_per_tower is not None else flat_qty` and
write `assumption`/its Vietnamese counterpart verbatim into the remark. Originally only the first tuple
("Ad frame...") was in scope; task 2.6 (below) extends the same pattern to the third tuple ("LCD screen
(basement lobby)") once a real basement count is supplied. The middle tuple ("LCD screen (tower
lobby)") stays untouched under any input — no real per-project data source exists for it.

## Goals / Non-Goals

**Goals:**
- A supplied real elevator count changes the "Ad frame" row's quantity AND its remark (real data,
  not "assumption, not real data") on both workbooks identically.
- No change to the two LCD rows under any input.
- No change to `ELEVATOR_AD_ITEMS`'s own shape as a static list — keep it the source of rates and the
  fallback quantities/assumption text it already is; make the two call sites, not the constant,
  responsible for substituting real data when available.

**Non-Goals:**
- Not populating `B4. DT Quảng cáo - Elevator adv`'s own E5/E6 — see proposal.md.
- Not asking for a full per-tower elevator breakdown (towers can vary) — a single "per tower" figure
  matches how `tower_count` is already used uniformly elsewhere in this pipeline (e.g.
  `_TOWERS_PER_SUPERVISOR`), so this is consistent with an existing simplification, not a new one.
- (Superseded by task 2.6 below, 2026-09-16 — recorded rather than deleted so the reasoning trail
  stays honest: this line originally said "not distinguishing basement-lobby ad frames from
  tower-lobby ones by real data... there is no equivalent real-data source for anything
  basement-related" — true at the time, no longer true once the PM asked for it and a real basement
  count field was added the same session.)
- Not deriving a basement-COUNT formula from building scale (floor count, parking slots, etc.) —
  checked directly against `Dim_Property_Residential.csv` real data: basement count tracks parking
  slot count only loosely (1-basement buildings range 4-838 car slots) and not floor count at all (a
  108-floor tower and a 15-floor one both commonly have exactly 1 basement level). Too noisy for a
  formula, same conclusion as the elevator-count research — manual entry only, both fields.

## Decisions

### Where the override lives: the two call sites, not `ELEVATOR_AD_ITEMS` itself

`ELEVATOR_AD_ITEMS` stays a plain constant. Each of the two consuming loops, when iterating the first
tuple specifically, checks `project.get('passenger_elevators_per_tower')`:
- If set: `qty_per_tower = passenger_elevators_per_tower`, and the remark is built from a real-data
  sentence instead of `assumption`.
- If `None`: behavior is byte-identical to today — `qty_per_tower` and `assumption` come from the
  tuple exactly as now.

Rejected alternative: turning `ELEVATOR_AD_ITEMS` into a list of callables (`assumption` and
`qty_per_tower` as functions of `project`) so the constant itself encodes the real-vs-fallback logic.
Rejected because it would touch all three tuples' shape for a decision that only the first one needs,
and because `ELEVATOR_AD_ITEMS` is also read by its own docstring/other tooling as a flat data table —
keeping it flat is the smaller, more legible change.

### Field name and placement: "Passenger Elevators per Tower", a Project Info field

Placed alongside Tower Count / Gate Count in the intake form's Project Info section (not
`EXAMPLE_DEMAND`, which is Staffing Demand — a different sheet/section entirely). "Passenger" is
explicit in the label, not left implicit, because the template's own M5 worked-example note shows
Savills already separates passenger from cargo elevators for this exact purpose — a label that just
said "Elevators per Tower" would invite a PM to enter the total including cargo elevators, silently
overstating ad-frame quantity.

### Real-data remark wording

Mirror the two-state pattern already used throughout this session's other remark work (e.g. the
comparable-basis label in `rank-comparables-by-location`): when real, state the figure came from the
project's own intake; when assumed, keep today's exact "Assumption, not real data: ..." wording
unchanged. No new disclosure convention invented — reuse the one this codebase already uses
everywhere else.

### Amendment (task 2.6, 2026-09-16): same pattern extended to the basement-LCD row

On request, after the elevator field shipped: "if we have lift then also go along with the base[ment]
and everything else relevant." Investigated first rather than building immediately — checked whether
any internal data or external standard could size basement count from building scale (see the
Non-Goals entry above) and found neither holds up, exactly as the elevator-count research already
found for elevators. So this amendment does NOT add a basement-count formula; it adds a second manual
field and wires it into the one place that already had an analogous hardcoded assumption:
`ELEVATOR_AD_ITEMS`'s third tuple, "LCD screen (basement lobby)", previously a flat `flat_qty=1`
"one screen per project" regardless of how many basement levels actually exist.

Same shape as `_real_ad_frame_qty()`: a small helper, `_real_basement_lcd_qty(project)`, returns the
real basement count when `project.get('basement_count')` is set, else `None` (caller keeps the
existing flat-1 fallback unchanged). Both generators' loops now check `idx == 2` for this override,
alongside the existing `idx == 0` check for the ad-frame override — the middle tuple (`idx == 1`,
"LCD screen (tower lobby)") is untouched under any input, matching the original scope exactly.

Field placement: grouped with Passenger Elevators per Tower in PROJECT SCALE (both are real
per-project infrastructure counts, moved there together per the same request that relocated
District/City/Latitude/Longitude/Street Address out of their own separate sections).

## Risks / Trade-offs

- **[Risk] A PM enters a total elevator count (including cargo) instead of passenger-only, silently
  overstating ad-frame revenue** → *Mitigation*: the field label states "Passenger" explicitly (see
  Decisions); no code-level way to detect a wrong PM entry, same limitation every other free-text PM
  input in this pipeline already has (Tower Count, Gate Count, etc.) — not a new class of risk.
- **[Risk] The two generators could drift if the override logic is written twice, once per call
  site, instead of shared** → *Mitigation*: task-level requirement to implement the override as one
  small shared helper (e.g. `_ad_frame_qty_and_note(project, tower_count)`) both call sites invoke,
  not copy-pasted logic — verify both workbooks agree on quantity and remark wording as a task.

## Migration Plan

1. Add the intake field (`build_project_input_form.py`, Project Info section) and its `read_input()`
   entry (`generate_project_budget.py`, optional per the established pattern).
2. Add the shared override helper and call it from both `build_additional_revenue_sheet` and
   `fill_common_area_fund_sheet`'s "Ad frame" handling.
3. Generate the deliverable + analysis for Wayne Tower and the standard sample, once with the field
   unset (confirm byte-identical to today) and once with a real supplied count (confirm RA1.A moves as
   expected); write both to this change's `measured-effect.md`.
4. Present the measured movement to the Head of PM.
5. Only after sign-off: re-record whichever baseline(s) moved.

## Open Questions

None — the two real decisions (where the override lives, and the field's exact scope) are resolved
above.
