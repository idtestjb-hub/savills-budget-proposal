## Context

See `proposal.md` — Why. In short: `generate_project_budget.py` ranks comparable projects by
`project['apartment_nfa']`, `generate_project_output.py` by `project['total_nfa']`, and the
comparable table (`MASTER_COMPARABLES` in `master_comparables.py`) stores each comparable's **Total
building NFA**. So the deliverable compares an apartment-only figure against whole-building figures.

Relevant current state:

- `generate_project_budget.py` calls `nearest_comparables(project['apartment_nfa'], …)` at three
  sites: the per-product rate loop (~line 708), and the derived-headline-rate block plus its
  `all_ranked` companion (~lines 1108–1109). The "Comparables" appendix (~lines 1302–1304) shows an
  "Apartment NFA (m²)" row and a delta computed against `apartment_nfa`.
- `generate_project_output.py` already calls `nearest_comparables(project['total_nfa'], …)` (~line
  179) and labels the row "Total NFA (m²) — used for comparable matching".
- `master_comparables.py`'s own module docstring already states the matching basis is Total NFA for
  every candidate, including for per-product rates (`derive_product_rate` scopes *which* comparables
  qualify by product-rate availability but ranks them by the same Total-NFA delta).
- The synthetic fixture "ZZ Sample Tower" has Apartment NFA 52,000 m² and Total NFA 54,400 m²
  (Apartment 52,000 + Shophouse 1,500 + Nursery 900) — a 4.4% gap.
- The `product-revenue-pricing` capability (from the complete-but-unarchived `price-all-product-types`)
  already asserts "The two workbooks report the same revenue … priced on the same basis". That
  claim is not currently true; this change makes it true and has verification enforce it.

## Goals / Non-Goals

**Goals:**

- One comparable-matching basis — Total building NFA — used by both generators.
- The client deliverable's management-fee revenue equals the analysis workbook's, by construction,
  for every project (not by coincidence on one fixture).
- Verification fails if the two generators ever disagree on comparable selection or on derived
  management-fee revenue.
- The figure movement is measured on a real project and signed off before archive.

**Non-Goals:**

- Per-product NFA ranking (see Decision 1).
- Changing `generate_project_output.py`'s rate logic — it is already on the target basis.
- Carrying `Master Info` into the client deliverable — decided against (proposal — What Changes).
- Re-shaping the synthetic fixture into a mixed-use project — that moves all 24 analysis-workbook
  baselines and is a separate piece of work (see Risks).
- Revisiting the fallback rule (a product with no real rate uses the derived Apartment rate) —
  unchanged.

## Decisions

### Decision 1 — Match on Total building NFA, not per-product NFA or Apartment NFA

Both generators rank and average comparables by the delta between this project's **Total building
NFA** and each comparable's stored NFA.

- **Why not per-product NFA** (rank each product's rate against comparables by that product's own
  NFA): the comparable table does not carry per-product NFA for most rows — the ~75 Master-List
  comparables have a single "NFA" column, and even the 7 hand-verified projects only split a few
  product types. Ranking by a field that is mostly absent means mostly falling back, which is worse
  than a consistent whole-building proxy. `master_comparables.py` already chose this trade-off.
- **Why not Apartment NFA on both sides** (change the analysis to match the deliverable): every
  comparable's stored figure is Total NFA. Matching on Apartment NFA would require adding an
  Apartment-NFA figure to every comparable row, including the ~75 auto-parsed Master-List rows that
  have no such breakdown — new data this change has no source for.
- Total NFA is the whole-building size proxy the table was built on and the analysis generator
  already uses. Aligning the deliverable to it is the minimal correct change.

### Decision 2 — Sequence after `price-all-product-types`

This change's delta **modifies** `product-revenue-pricing`. That capability exists today only as a
delta spec inside the unarchived `price-all-product-types` (complete, 24/24). A MODIFIED delta needs
the requirement to exist in `openspec/specs/product-revenue-pricing/spec.md`, which happens when
`price-all-product-types` is archived.

Plan: archive `price-all-product-types` (and, while there, `read-input-by-label`, also complete)
before `/opsx:apply` on this change. If for some reason that is not done first, this change's
archive step will report the missing requirement and stop — nothing is lost, the order is just
enforced late instead of early.

### Decision 3 — The cross-generator check compares live figures, and lives beside the deliverable baseline

The new verification check runs both generators on the fixture and compares, beyond rounding:
total management-fee revenue, each product's revenue, and the derived rate. It reads the figures
the same way the existing deliverable-figure check does (Excel COM recalculation), and reports a
disagreement by name with both values in VND. It runs every time, independent of whether a baseline
is being compared — a baseline catches *drift from a recorded number*, this catches *the two
workbooks diverging from each other*, which a single-workbook baseline cannot see.

It belongs in `verification/checks.py` next to `check_deliverable_figures`, surfaced by `verify.py`
as its own line in section 5.

### Decision 4 — Measure on Diamond Skyline, disclose the movement, get PM sign-off

Diamond Skyline is the real project used to sign off changes A and B, and it is mixed-use
(apartment + parking + other), so its Apartment NFA is below its Total NFA. Measure, for Diamond
Skyline: the deliverable's derived management-fee rate and total RM revenue before and after, each
per-product RM line, `RM.0A`, and the estimated surplus — all in VND — and record the table in this
change's design (a D-appendix, as change B did) for PM sign-off before archive. Re-record
`verification/baselines/deliverable_baseline.json` with a stated reason.

### Decision 5 — The headline rate uses `derive_product_rate('Apartment')`, not `derive_mgmt_rate` (added during apply)

Found while measuring: the deliverable computed **two** Apartment rates with two functions.
`derive_product_rate(all_ranked, 'Apartment')` priced the actual RM revenue (and is what the
analysis shows). `derive_mgmt_rate(top2)` — a whole-property blended rate over *any* nearest
comparable — fed the client-visible `0. Info`!I8 fee-rate cell, the Comparison sheet, and the
console log. The two pick different comparables, so they give different numbers. Before this change
they happened to agree on the synthetic fixture; switching the matching NFA pulls them apart, and
on Diamond Skyline they were already three different values (`0. Info`!I8 = 15,150; RM priced at
18,400; analysis = 15,900).

So `build_budget` now derives its headline rate with `derive_product_rate(all_ranked, 'Apartment',
n=2)` — the same function `fill_management_fund_sheet()` and `generate_project_output.py` use — and
`derive_mgmt_rate` is kept only as the last-resort fallback for a project where no comparable
carries an Apartment rate. The Comparison sheet and `0. Info`!I8 now show one rate, and it is the
rate the budget charges. This is a net simplification and squarely inside "unify the revenue basis";
it is called out here because it went beyond the literal task list. `verify.py`'s new
`check_revenue_agreement` proves the alignment holds.

## D-appendix — Measured effect (task 4.1)

Diamond Skyline, both generators run against the real input, deliverable and analysis recalculated
in Excel. "Before" = the pipeline as it stood after change B (deliverable ranks comparables on
Apartment NFA, headline rate via `derive_mgmt_rate`). "After" = this change. All VND.

| Figure | Before | After | Δ |
|---|--:|--:|--:|
| **`0. Info`!I8 — Apartment fee rate shown to the client** (VND/m²/month) | 15,150 | 15,900 | +750 |
| Apartment RM (full-occupancy year) | 15,897,600,000 | 13,737,600,000 | −2,160,000,000 |
| Officetel RM | 475,200,000 | 394,200,000 | −81,000,000 |
| Shophouse RM | 125,400,000 | 125,400,000 | 0 |
| Nursery RM (falls back to Apartment rate) | 883,200,000 | 763,200,000 | −120,000,000 |
| **Total RM revenue** (RM collected + `RM.0A`, full-occupancy equivalent) | 17,381,400,000 | 15,020,400,000 | **−2,361,000,000 (−13.6%)** |
| — of which `RM.0A` developer top-up (year-1 ramped total) | 12,673,937,500 | 10,952,375,000 | −1,721,562,500 |
| **Analysis workbook — Total Annual Management Fee Revenue** | 15,020,400,000 | 15,020,400,000 | **0** (analysis already ranked on Total NFA) |
| **Deliverable − analysis gap** | +2,361,000,000 (+15.7%) | **0** | gap closed |
| **Deliverable estimated year-1 surplus** (`1. Summary` PART 3) | 9,671,416,438 | 7,312,010,678 | **−2,359,405,760** |

**What moved and why.** The deliverable was pricing Apartment (and the Nursery that falls back to
it) off comparables selected by an apartment-only area against whole-building comparables — it
picked Masteri An Phu + Diamond Alnata Plus and derived 18,400. Ranking on Total building NFA
(78,300 m²) instead picks Masteri An Phu + Green Skyline and derives 15,900 — the same figure the
internal analysis has been showing all along. Officetel moves the same way (22,000 → 18,250).
Shophouse is unchanged (its comparable set did not move). The −2.36bn revenue drop flows straight
to the surplus; nothing else in the budget changes.

This is the correction backlog **B3** describes: the deliverable was ~15.7% above the analysis that
explains it, and it was the deliverable that was wrong. After this change the two agree by
construction and `verify.py` enforces it.

### Negative test (task 3.3)

With the matching bug reintroduced (deliverable back on Apartment NFA) and both generators run
against Diamond Skyline, `check_revenue_agreement` returns `ok=False` and names the disagreements:

```
Apartment      deliverable 15,897,600,000   analysis 13,737,600,000  <-- DISAGREE
Officetel      deliverable    475,200,000   analysis    394,200,000  <-- DISAGREE
Nursery        deliverable    883,200,000   analysis    763,200,000  <-- DISAGREE
TOTAL          deliverable 17,381,400,000   analysis 15,020,400,000  <-- DISAGREE
```

(The synthetic fixture "ZZ Sample Tower" is apartment-dominant — Apartment 52,000 / Total 54,400 m²
— and `derive_product_rate` picks the same comparables at either NFA, so the bug is invisible there.
The negative proof needs a mixed-use project. A dedicated mixed-use fixture is a sensible follow-up
but re-bases all 24 analysis-workbook figures, so it is out of scope here.)

## Risks / Trade-offs

- **The synthetic fixture is apartment-dominant (4.4% NFA gap), so the harness check has light
  coverage.** → The check still fires if the two generators are wired to different fields at all
  (any gap makes them select-or-rank differently once comparables are close together). Real
  confidence comes from the Diamond Skyline measurement. A dedicated mixed-use fixture is the right
  long-term answer but is out of scope here because it re-bases all 24 analysis figures — raise it
  as a follow-up.
- **The movement direction is not predictable.** Switching 52,000 → 54,400 m² (or Diamond Skyline's
  larger gap) can swap a comparable in or out, so the derived rate may move up or down, not
  monotonically. → Do not assume; measure and show the table.
- **The deliverable baseline moves.** → It did NOT, in the end. The synthetic fixture is
  apartment-dominant, so `derive_product_rate` picks the same comparables at Apartment NFA (52,000)
  and Total NFA (54,400), and `0. Info`!I8 lands on 18,350 either way. All 7 deliverable-baseline
  figures and all 24 analysis figures are unchanged; no re-record needed (same outcome as
  `read-input-by-label`). The real movement is on mixed-use projects like Diamond Skyline
  (D-appendix) — visible there, invisible to the fixture-only baseline, which is exactly why
  `check_revenue_agreement` was added.
- **`RM.0A` and parking-area management fee move too**, because they are priced off the same
  per-product base. → Include them in the measurement table so nothing moves unexplained.
- **Rollback** is reverting the `generate_project_budget.py` edits (the `total_nfa` call sites and
  the `derive_product_rate` headline-rate block). No baseline to restore (it did not move), no data
  migration, no schema change.

## Migration Plan

1. Archive `price-all-product-types` and `read-input-by-label` (Decision 2). ✔
2. Point `generate_project_budget.py`'s comparable-matching at `project['total_nfa']`; derive the
   headline rate with `derive_product_rate('Apartment')` (Decision 5); relabel the Comparison sheet.
3. Add `check_revenue_agreement` to `verification/checks.py` and `verify.py`. ✔
4. Run `verify.py` — fixture unchanged, `check_revenue_agreement` PASS. ✔
5. Generate the Diamond Skyline deliverable + analysis before and after; fill the D-appendix. ✔
6. **PM sign-off on the −2.36bn RM / −2.36bn surplus movement** (pending).
7. No `deliverable_baseline.json` re-record — the fixture figures did not move.
8. Archive.
