## Context

`_staff_on_duty()` (`generate_project_budget.py:426-471`) decides, per Staffing Demand row, whether to
use a ratio-derived headcount or whatever the cell already holds. It has exactly one signal for "has
a PM already overridden this": `numeric and not is_formula` — a truthy, non-formula cell value. It
cannot distinguish "PM typed a real override" from "the form was seeded with a truthy placeholder and
nobody has touched it yet." `EXAMPLE_DEMAND` (`build_project_input_form.py`) is the sole source that
seeds a fresh form, so the seed's shape is the only lever available to make a role start in the
"not yet overridden" state — there is no separate flag cell or metadata column recording provenance.

Two working precedents already exist in the same file for two different roles' worth of correct
seeding: the 2026-09-09 batch (Assistant Property Manager, Accountant, Cashier — seeded `0`, ratio
fires) and Pool Attendant (built earlier this session — seeded as a real Excel formula string, so
`is_formula` is true and the row is never mistaken for an override at all). See proposal.md for the
8 roles / 13 rows this change reconciles onto the first of those two patterns.

## Goals / Non-Goals

**Goals:**
- Every portfolio-ratio role behaves identically on a fresh form: ratio applies until genuinely
  overridden, exactly like the 3-role batch that already works.
- Zero change to `_staff_on_duty()`/`_portfolio_headcount()` — the override-detection mechanism and
  its "delete the row to force zero" convention are both pre-existing and correct; only the seed
  values that feed them are wrong for 8 roles.

**Non-Goals:**
- Not building a more expressive override-provenance mechanism (e.g. a separate "PM touched this"
  flag cell) that could distinguish a real zero override from a not-yet-touched seed. That would be
  a bigger, riskier change to a mechanism that already works correctly for 3 roles; reusing the
  proven pattern is strictly simpler and has no new failure mode to reason about.
- Not changing the Pool Attendant, Security, or Cleaning rows — none of the three use the portfolio-
  ratio mechanism this change touches (Pool Attendant has its own statutory-ratio formula; Security/
  Cleaning use gate-count/area-based Excel formulas with no `ratio_fn` at all).

## Decisions

### Reseed at `0`, not as a formula string

Two ways to make `is_formula`/`numeric` fail to look like an override, both raised while
investigating this change:

1. **Seed at `0` (chosen).** `0` is falsy, so `numeric and not is_formula` is `False` regardless of
   `is_formula`, and the row falls through to `ratio_fn`. Already proven correct for 3 roles in this
   exact file.
2. **Seed as a trivial formula string** (e.g. `'=1'`), matching how Pool Attendant avoids the bug.
   Rejected for these 8 roles: Pool Attendant's formula is a REAL formula computing a real fallback
   value (`IF(PoolArea>0, ROUNDUP(...), 1)`) that Excel itself can display meaningfully if the row is
   ever inspected outside this pipeline; a synthetic `'=1'` with no real computation behind it would
   be formula-shaped for no reason, purely to trip `is_formula`, which is more surprising to read in
   the source than a plain `0` that already has an established, documented meaning ("not yet
   overridden, ships at zero until estimated or overridden") in this same file.

### No change to the "delete the row to force zero" convention

`_staff_on_duty()`'s own docstring already documents this: a ratio-covered role cannot be typed to a
literal zero (zero is indistinguishable from "not yet touched"); the row must be deleted instead.
This change does not alter that — it is pre-existing behavior for the 3-role batch already, and the
new spec's own scenario states it as a real, load-bearing constraint on how a PM must use the form,
not an oversight to fix here.

## Risks / Trade-offs

- **[Risk] A PM who has already generated a form under the OLD seeding (bare `1`) and left it
  untouched will see the ratio activate the moment they regenerate rather than when they save** →
  *Mitigation*: this only affects a FRESH generation, per the proposal's Impact section; an
  already-filled real project workbook is never re-seeded by this pipeline, so no in-flight project
  is retroactively changed. Worth confirming directly (task 2) rather than assumed, since "does
  regenerating ever touch an existing filled form" is exactly the kind of claim this project has been
  burned by asserting instead of testing.
- **[Risk] Eight roles' headcount can move simultaneously, making the aggregate swing harder to read
  than a single-role change** → *Mitigation*: proposal.md already commits to a per-role breakdown in
  the measured effect, not just a total, so the Head of PM can sanity-check each one.
- **[Risk] A role whose portfolio ratio produces a LOWER headcount than the old flat seed (`1`) is
  possible** (e.g. a role whose median per-1,000-m² figure rounds down to 0 on a small project,
  though `_portfolio_headcount`'s `max(1, round(...))` floors the whole-building total at 1, so a
  single-row role can't go to 0 this way — only a multi-row split role could show 0 on one shift row
  after the split) → *Mitigation*: no code change needed, this is existing `_portfolio_headcount`
  behavior already exercised by the 3-role batch; call out in the measured effect if any of the 8
  roles' totals move down rather than up, since a PM reading "the ratio recommends fewer staff than
  we assumed" deserves that framed honestly, not buried in a net figure.

## Migration Plan

1. Reseed the 13 rows in `EXAMPLE_DEMAND` (`build_project_input_form.py`) from `1` to `0`.
2. Verify no other code path seeds these same roles independently (confirm `EXAMPLE_DEMAND` is the
   sole seed source for a fresh form — task 1).
3. Generate a fresh intake form and the deliverable + analysis for Wayne Tower and the standard
   sample; record, per role, the before/after headcount and the resulting VND swing in staff cost and
   year-one surplus. Write the table to this change's `measured-effect.md`.
4. Present the measured movement to the Head of PM, per-role, alongside the reminder that these
   figures are portfolio medians (peer-building behavior), not a Savills standard or statutory
   minimum.
5. Only after sign-off: re-record whichever baseline(s) moved.

## Open Questions

None — the one real design choice (reseed value vs. formula string) is resolved above.
