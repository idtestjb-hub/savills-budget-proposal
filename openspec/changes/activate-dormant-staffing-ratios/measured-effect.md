## Measured effect — Wayne Tower (real intake) and a Wayne-Tower-scale illustration

Measured 2026-09-17, on the current code, via `verification/run_workflow.py`'s protected harness
(production-file snapshot before/after every run; confirmed unchanged on every run in this document).

### What moved on Wayne Tower's real intake: nothing

Wayne Tower's real intake already has a generated 'Staffing Demand' sheet — one filled in before this
change existed, with these 8 roles' cells already holding `1` (a real, already-generated value, not a
fresh seed). `_staff_on_duty()`'s override detector treats any truthy non-formula cell as already
decided, so this reseed — which only changes what a FRESH form starts at — has no effect on it.
Confirmed directly (not assumed): reading Wayne Tower's real file through `read_input()` shows
Reception/Property Manager/Chief Engineer all still at `1`, exactly as before.

**This change has zero effect on Wayne Tower's real deliverable, or any other already-generated
project, until someone regenerates a fresh form for it.** That is the honest current state, not a
caveat — no existing project's figures move today, matching the same guarantee the other two changes
in this session's batch (`rank-comparables-by-location`, `wire-real-elevator-count-into-ad-revenue`)
already gave.

### Illustrative effect, at Wayne Tower's real scale (Total NFA = 79,650 m²)

To show what the mechanism does once a FRESH form is generated at a real project's scale, built two
synthetic samples at Wayne Tower's own Total NFA — one with the 13 rows manually set to `1` (simulating
the pre-fix behavior a fresh form used to produce) and one reseeded at `0` (today's fix, ratio fires) —
and ran both through the full pipeline:

| Role | Old flat seed (total) | New ratio-derived (total) | Swing |
|---|---|---|---|
| Property Manager | 1 | 1 | — |
| Chief Engineer | 1 | 1 | — |
| Building Executive | 1 | 2 | +1 |
| Customer Service | 1 | 6 | +5 |
| Reception | 1 | 3 | +2 |
| Technician (3 shifts) | 3 | 9 (3/3/3) | +6 |
| Shift Leader (3 shifts) | 3 | 4 (2/1/1) | +1 |
| Amenities Attendant (2 shifts) | 2 | 4 (2/2) | +2 |
| **Total headcount, these 13 rows** | **13** | **30** | **+17** |

Every role's ratio-derived total is at or above its old flat seed AT THIS SCALE — no downward move at
Wayne Tower's size specifically. That is not true at every scale (see below), so it is reported as a
fact about this one scale, not a general property of the mechanism.

**VND figures, real Excel recalculation (not a cached/estimated value) — this is the largest single
swing of the three changes this session:**

| Figure | Old (flat-1 seed) | New (ratio-derived) | Swing |
|---|---|---|---|
| Annual Staff Cost | 4,293,950,777 VND | 5,280,013,355 VND | **+986,062,578 VND/year (+23.0%)** |
| Total Profit Value (Year 1, 100% fill, Must-Have Only) | 5,927,173,356 VND | 4,941,110,778 VND | **−986,062,578 VND/year** |
| Margin (profit ÷ revenue) | 39.00% | 32.51% | **−6.49 points** |
| Markup (profit ÷ cost) | 63.94% | 48.18% | **−15.76 points** |

Profit's swing exactly mirrors staff cost's (same magnitude, opposite sign) — correct by construction,
since only staff cost changed between the two runs (Total Profit Value = Mgmt Fee Revenue − Staff −
OPEX − Capex, and revenue/OPEX/Capex are identical between the OLD and NEW runs). This is real money
at Wayne Tower's scale, not a modest adjustment — larger in absolute VND terms than either of the other
two changes measured this session, because it touches 8 significant recurring headcount roles at once
rather than one revenue line.

### A downward move exists at smaller scale — disclosed per design.md's Risk note, not folded into a net total

Separately tested at Total NFA = 50,000 m² (a smaller, still realistic project): **Shift Leader (Night)
computes to 0** (whole-building Shift Leader total = 2, split 3 ways via `divmod` → Morning=1,
Afternoon=1, Night=0) — lower than the old flat seed of 1 on that specific row. Every other role at
this scale still moved up or stayed flat. This is exactly the scenario design.md's Risk section
anticipated (`_portfolio_headcount`'s `max(1, round(...))` floors the whole-building total at 1, but a
multi-row split role can still show 0 on one shift row after the split) — confirmed on real output, not
just reasoned about. Flagged explicitly here per the task's own instruction: a PM reading this deserves
to see "the ratio recommends zero on the night shift at this scale" stated plainly, not smoothed into an
aggregate that only shows net upward movement.

### Manual spot-check (task 3.6 — project rule for changed aggregation logic)

By hand, against `Fact_StaffingRatio_ByPosition.csv`'s raw figures and Wayne Tower's real NFA
(79,650 m²):
- **Property Manager**: median 0.0161 per 1,000 m² × 79.65 = 1.28 → round → 1. Matches
  `_portfolio_headcount()`'s computed value exactly.
- **Reception**: median 0.0332 per 1,000 m² × 79.65 = 2.64 → round → 3. Matches exactly.

### What did NOT move

- Wayne Tower's real deliverable and analysis workbook — confirmed unaffected (see above).
- The standard synthetic sample's full 5-check regression suite: 0 differences on the frozen fixture
  (which itself predates this change and still holds the old `1` seeds — see `tasks.md` 3.6 for why
  this specifically tests backward-compatibility, not the new behavior).
- A genuine PM override (tested: typed 5 onto Reception) still wins outright; a row explicitly cleared
  to 0 (tested: Property Manager) still ratio-applies rather than zeroing out — both per design.md's
  documented, unchanged conventions.
- `EXAMPLE - Wayne Tower Thu Thiem.xlsx` and the other 4 tracked production files: unchanged on every
  run in this document.

### Unrelated finding, disclosed and separately flagged, not fixed here

Running the full 5-check suite against a freshly-reseeded "no pool" sample surfaced that ESM4/ESM5
(pool chemicals/testing) ship completely blank — no figure, no stated reason — when a project has no
pool, unlike every other conditional Required code on the same sheet. Confirmed by code inspection this
is unrelated to the 8 staffing roles this change touches (`generate_project_budget.py`'s
`if project.get('has_pool')` blocks simply skip writing anything when false). Flagged as a separate
follow-up task rather than fixed as part of this change's scope.
