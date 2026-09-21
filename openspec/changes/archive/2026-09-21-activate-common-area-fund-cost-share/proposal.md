## Why

While closing the Required-line-item gap for change `fill-guideline-required-line-items`, a scan of
`2.2 Common area Fund` found that ~213 of its expense leaf rows (`EMH*`, `EMA*`, `EMB*`, `EMO*`,
`ESC*`, `ESS*`, `ESI*`, `ESM*`, `ESR`, `EN*`, `EEW/EEE/EED/EEG*`, `ER*`) carry a **template-native
formula already computing a real figure** — `F{row} = XLOOKUP(code, '2. Budget-Management Fund'!Y,
'2. Budget-Management Fund'!AL) * $F$8`, where `F8 = common-area revenue / (total 2.Fund revenue +
common-area revenue)` (a real cell on this sheet, ~0.45% on the Wayne Tower example) — a
revenue-proportional SHARE of the matching `2. Fund` expense line. It resolves to zero today purely
because the template ships column C (Frequency) blank on those rows; `E{row}`'s own formula only
returns 12 (months) when C reads `"Monthly"`/`"Schedule"`/etc., so with C blank, `G = F*E` collapses
to zero even though F already holds the correct value.

A prior comment in `generate_project_budget.py` (right above `COMMON_AREA_FUND_ROWS`) records a
deliberate decision to leave these rows blank: *"writing the same Staff/OPEX/Capex numbers here too
would double-count them, since this pipeline has no real cost-allocation split telling us how much
of each belongs to which fund."* That premise is contradicted by what was just found — a real
allocation split (the F8 revenue-share ratio) already exists in the template, dormant rather than
absent. But "the template has a formula for this" is not the same as "revenue-share is the correct
accounting basis for splitting common-area costs between the two funds," and there is a second,
unresolved concern: `RI1` on `2. Fund` (the management fund's own recovery of expenses it paid on
behalf of the common-area fund) sources, per `Costing_Method_Catalogue.csv`, from `'2. Budget-
Management Fund'!AH40` itself — not from `2.2 Common area Fund`. Whether populating `2.2`'s own
proportional-share rows creates a double-count against that recovery mechanism is a real
cross-fund-accounting question this pipeline cannot answer on its own.

The fix (`_activate_common_area_passthrough_rows` in `generate_project_budget.py`) is implemented —
it only writes `'Monthly'` into column C on rows where it is currently blank and F is this exact
XLOOKUP pattern, changing nothing else, never overwriting the ~9 rows the template itself already
set C on, and never touching `COMMON_AREA_FUND_ROWS`' own two directly-priced revenue rows. It is
figure-moving (closes most of `2.2 Common area Fund`'s Required-code gap) and is kept out of change
`fill-guideline-required-line-items`'s own measured effect and task list specifically so that
change's real pricing work (which is unambiguous) is not held up waiting on this one's accounting
sign-off.

## What Changes

- Record, in this change's own artifacts, the exact mechanism activated and why the prior
  "no allocation split exists" premise no longer holds.
- Measure the isolated effect of activating these rows alone (not conflated with any other
  change's pricing work) on a real project (Wayne Tower).
- Get explicit PM/finance sign-off on two questions before archiving: (1) is revenue-share the
  correct basis to allocate common-area costs between the two funds, and (2) does this create a
  double-count against `RI1`'s own recovery mechanism.
- If sign-off says yes: keep the activation, record the baseline.
- If sign-off says no, or says a different allocation basis is correct: revert
  `_activate_common_area_passthrough_rows` (or replace its ratio with whatever basis is confirmed
  correct) before this change is archived.

## Impact

- Affected code: `generate_project_budget.py` (`_activate_common_area_passthrough_rows`,
  `fill_common_area_fund_sheet`) — already written, already the live behavior on every subsequent
  run of the pipeline.
- Affected spec: `common-area-fund-cost-share` (new capability).
- Figure-moving: yes — `2.2 Common area Fund`'s own totals move, and downstream cells that read
  from this sheet (`2.2.1 Report-Common area Fund`, `1. Summary`'s common-area-fund figures, if
  any) move with them. Gated on explicit PM/finance sign-off before archiving, per this project's
  standing rule for figure-moving changes — not before implementing, which is already done and
  already live.
- No source data changed; no other sheet's write logic touched.
