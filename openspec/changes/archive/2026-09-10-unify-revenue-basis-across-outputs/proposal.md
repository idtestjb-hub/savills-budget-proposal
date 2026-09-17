## Why

The client deliverable and the internal analysis workbook are meant to report the **same**
management-fee revenue for the same project — the `product-revenue-pricing` capability says so in
as many words. They do not. The two generators choose their comparable projects on different size
measures: the client-deliverable generator ranks comparables by the project's **Apartment NFA**,
while the analysis generator ranks them by **Total building NFA**. The comparable table itself is
keyed on Total building NFA, so the deliverable is matching an apartment-only area against
whole-building areas — not like for like.

On the synthetic sample the two happened to land on the same rate — coincidence, recorded in
decision **D2**. On the "Yellow Sky" test project they diverge by **1,091,580,000 VND (6.5%)** of
management-fee revenue, the deliverable being the higher and the wrong one. This is the unresolved
half of finding **X-01** and open backlog item **B3**, and it is change **C** of the AI Guideline
change family (`docs/08-guideline-change-family.md`).

## What Changes

- The client-deliverable generator ranks and averages comparable projects on **Total building
  NFA** — the same measure the analysis generator and the comparable table already use. This is the
  only functional change.
- Every rate the deliverable derives from comparables moves with it: the headline management-fee
  rate, each per-product rate (`RM.AP`…`RM.KG`), and — because they are priced off the same base —
  `RM.0A` (the developer's top-up on unsold units) and the parking-area management fee where it is
  written.
- The deliverable's "Comparables" appendix relabels its size row from "Apartment NFA" to "Total NFA
  (matching basis)" and shows the delta on that measure, so the sheet explains the selection it
  actually made.
- The internal analysis generator is **unchanged** — it already matches on Total NFA.
- Verification gains a check that the two generators select the same comparables and derive the same
  management-fee revenue for the same project, so this cannot silently drift apart again.
- **Not in this change — carrying `Master Info` into the client deliverable.** Decided against: the
  sheet names roughly 40 other Savills-managed projects alongside their management and staff data,
  and putting that in front of a client is the open **A10** exposure. The benchmark stays an
  internal analysis aid. This narrows decision **D6** further (change A already dropped `Master
  Info` from the standard template for a separate reason — stale external-workbook links).
- **Already delivered, not repeated here — per-product `RM` rows.** `price-all-product-types` wrote
  those; this change only corrects the basis they are priced on.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `product-revenue-pricing`: the requirement **"The two workbooks report the same revenue"** is
  tightened — "priced on the same basis" is made explicit as *ranked and averaged over comparable
  projects selected on the same size measure, Total building NFA* — and a requirement is added that
  **verification enforces** the two generators' agreement on comparable selection and on derived
  management-fee revenue, rather than the spec merely asserting it.

## Impact

- **Code:** `generate_project_budget.py` — the three `nearest_comparables(project['apartment_nfa'],
  …)` call sites become `project['total_nfa']`, plus the "Comparables" appendix rows that read
  `apartment_nfa` for the size comparison. No change to `generate_project_output.py`.
- **Figures (VND):** the deliverable's total management-fee revenue and its derived per-m²/month
  rate move for any project whose Apartment NFA differs materially from its Total building NFA — i.e.
  any mixed-use project, and any project with sizeable parking, retail or office area. Direction and
  size are per-project; on "Yellow Sky" the deliverable falls ~1,091,580,000 VND (6.5%) to meet the
  analysis. The effect is measured on a real project and signed off by PM before archive.
- **Verification:** `verification/baselines/deliverable_baseline.json` re-recorded with a stated
  reason; a new cross-generator agreement check added to the harness.
- **Reference data / Copilot Studio:** none. This change reads the existing Generation B comparable
  data (`MASTER_COMPARABLES` / `Dim_Property_Residential.csv`) and writes no Generation A or
  Generation B table. It changes **no Fact/Dim join key**, so the Copilot Studio package's live data
  is unaffected.
- **Sequencing:** the delta modifies `product-revenue-pricing`, which today exists only as a delta
  in the unarchived change `price-all-product-types`. That change is complete (24/24) and should be
  archived first so `product-revenue-pricing` is an accepted spec this change can modify.
