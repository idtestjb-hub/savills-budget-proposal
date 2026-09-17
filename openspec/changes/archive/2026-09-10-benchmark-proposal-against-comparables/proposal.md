## Why

When PM bids for a new residential management contract, the number that wins or loses the deal is
the management fee, and the client's board always asks "why this figure". Today the pipeline's
`Comparison` sheet only benchmarks the **rate input** — it shows the model-derived Apartment rate
next to the two nearest comparables' Apartment rates and, for an existing Savills project, a
reality-check gap. It stops there. It never lays the **finished proposal** — the fee a real
apartment owner would pay each month, the full year-one management-fee revenue, and whether that
revenue actually covers the operating budget the same workbook proposes — beside the comparable
projects Savills already runs. A PM preparing a bid has to assemble that comparison by hand, which
is exactly the slow, inconsistent manual step this tool exists to remove.

## What Changes

- The client deliverable's `Comparison` sheet gains a **PROPOSAL BENCHMARK** section that presents
  this project's finished proposal next to the same two nearest comparables, in the terms a client
  and a PM argue about:
  - **Management fee per apartment, VND per month** — the model's Apartment rate (VND/m²/month)
    times this project's average apartment NFA — next to each comparable's fee per apartment,
    computed the same way from that comparable's real Apartment rate and its average apartment area.
  - **Year-one management-fee revenue, VND** — the deliverable's own total (the ramped `RM.*` lines
    plus the `RM.0A` developer top-up), shown next to "what this project's revenue would be if it
    were charged at comparable A's rate" and "…at comparable B's rate", so the gap is a VND figure,
    not a hand-wave.
  - **Fee-to-cost coverage** — the same year-one management-fee revenue against this project's own
    estimated year-one operating cost (the figure the analysis workbook already computes), shown as
    a surplus in VND and as a percentage of revenue, with a plain band ("thin < 5%", "normal
    5–15%", "generous > 15%") so a PM sees at a glance whether the draft fee is viable before it
    goes to a client.
  - A one-line **verdict** in plain language: whether the proposed fee sits inside, below, or above
    the range set by the two comparables, and whether it covers cost.
- The section states, on the sheet, what is a **real peer benchmark** (the fee comparison — drawn
  from 85 comparables' real rates) and what is an **internal consistency check** (the coverage
  figure — this project's estimated cost is itself derived from one reference property's ratios, so
  coverage confirms the draft hangs together, it is not a second opinion from the market).
- No change to any figure the pipeline writes into a budget line. The benchmark section only
  re-presents figures the two workbooks already produce, plus the two "if charged at the
  comparable's rate" projections, which are clearly labelled as projections.

## Capabilities

### New Capabilities

- `proposal-benchmark`: how the client deliverable presents the finished budget proposal —
  fee per apartment, year-one management-fee revenue, and fee-to-cost coverage — alongside the
  nearest comparable projects Savills manages, so a PM can defend the proposed fee in a competitive
  bid; and how those benchmark figures are kept reconciled with the workbook they appear in.

### Modified Capabilities

<!-- none — the Comparison sheet's PROPOSAL BENCHMARK section is new behaviour with no existing
     requirement governing it. product-revenue-pricing still owns how the rates themselves are
     derived; this change only presents the result. -->

## Impact

- **Affected code**: `generate_project_budget.py` — `add_comparison_sheet()` (new section) and its
  call site in `build_budget()` (needs to pass the deliverable's own year-one management-fee total
  and the estimated year-one operating cost, both already computed upstream in the same function).
- **Affected data**: none. Reads `master_comparables.py` (Generation B comparable rates and scale —
  already read by this sheet) and figures already computed in `build_budget()`. Writes no data.
  **No Generation A or Generation B table changes; no Fact/Dim join key changes** — the Copilot
  Studio package's live data is unaffected.
- **Affected outputs**: the client deliverable's `Comparison` sheet only. It is a display-only
  appendix, not a Savills template sheet; nothing in the pipeline reads it and no verification
  baseline records its cells. The internal analysis workbook is unchanged.
- **Verification**: a new lightweight check that the benchmark section's "year-one management-fee
  revenue" equals the workbook's own `RM` total and its "estimated operating cost" equals the
  analysis workbook's figure — so the appendix can never quietly drift from the budget it summarises.
- **Risk**: Low. No budgeted figure moves; the change is additive presentation. The one judgement
  call is the wording of the coverage bands and the verdict line, which a PM should review.
