## Context

See `proposal.md` — Why. Established by reading the costing spec, `estimate_opex.py`,
`rescan_opex_from_source.py` and `Fact_OPEX.csv`.

- `Fact_OPEX.csv` has four columns: `Project`, `Category`, `MonthlyVND`, `Source`. Consumption and
  tariff exist **only inside the prose `Source` string**, and only for some rows.
- `estimate_opex()` divides `MonthlyVND` by the source property's NFA to get a VND/m²/month ratio,
  then multiplies by the new project's NFA. Electricity is `4,089.11 VND/m²/month`.
- The three energy lines are 3,036,370,116 VND/yr on the sample — 31.0% of deliverable cost, and the
  entirety of the pipeline's measured method drift.
- A&K electricity: 262,210,141 ÷ 2,226 VND/kWh = 117,794 kWh/month = **1.837 kWh/m²/month**.
- A&K diesel's source sheet is already `hours × rate × price`; the ETL collapsed it.
- **A&K water records neither m³ nor tariff.** Only Parking Building does (3,300 m³ @ 29,000/m³),
  and Parking Building is a different building type that `estimate_opex` deliberately never blends
  into the residential ratio.

## Goals / Non-Goals

**Goals**

- Each energy line computed as usage × tariff, the method its spec states.
- Tariff separately stored, separately updatable, and dated.
- Every generated note reports usage, tariff and each one's `n`, so a wrong figure is diagnosable.
- The reproduced figures match today's to within rounding, proving the split is faithful.

**Non-Goals**

- Widening the usage basis beyond `n=1`. This change makes the thinness nameable, not smaller.
- Fixing the "water ~3.3× high" error. It makes it diagnosable.
- Updating tariffs to current published rates — a separate, deliberate decision with the PM.
- Any other cost code; `EMH1`.

## Decisions

### D1 — Split into a usage ratio and a tariff, keeping the ratio per m² of NFA

Electricity becomes `kWh/m²/month × NFA × tariff × 12`, and the same shape for water and diesel.

*Why keep a per-m² usage ratio at all:* it is the only scaling basis the pipeline has. A new
prospect supplies NFA, not projected kWh. The spec says "projected annual kWh" without saying how to
project it; deriving it from a real building's usage per m² is the honest reading of that with the
data available.

*What this actually fixes:* the tariff stops being frozen inside the ratio. Usage stays `n=1` and
stays labelled so. These are separate problems, and only one of them is solvable today.

### D2 — Keep `MonthlyVND` and add columns beside it

`Fact_OPEX.csv` gains `Quantity`, `Unit`, `UnitPrice`, `PriceAsOf`. `MonthlyVND` stays.

*Why not replace it:* `MonthlyVND` is what every current reader uses, and for rows where no split is
recoverable it remains the only figure. Keeping it means the table is readable before and after, and
the reconciliation check in Group 4 has something to reconcile against.

*Constraint honoured:* Generation A table, additive columns only, no join key touched, so the
Copilot Studio package's Generation B data is unaffected.

### D3 — A&K water is not split; it falls back and says so

A&K's water row records no m³ and no tariff, so no split is derivable from the table as it stands.

*The order of preference, and why:*

1. **Re-extract from `D2. Nước Công Cộng`.** The row's own source note says it is itemised by tower
   across public water, garden watering, floor washing, pool top-up and a 10% loss allowance — so
   volumes are very likely present. This is the correct fix and should be attempted first.
2. **If they are not present, water falls back to the existing cost ratio**, labelled on the output
   as not yet split, with the reason.

*Why not use Parking Building's 29,000 VND/m³:* it is a different building type, which is precisely
why `estimate_opex` already refuses to blend that property into the residential ratio. Borrowing its
tariff to complete a formula would be inventing a rate — the failure mode this project is recovering
from. It is also implausible as a residential rate.

*Consequence, stated:* the change may land with electricity and diesel split and water not. That is
an honest partial result and better than a fabricated one. The task list treats it as a real
possible outcome rather than a failure.

### D4 — The figures must not move

Usage × tariff is the same product the cost ratio already held, so all three figures should
reproduce to within rounding.

*This is the correctness test for the whole change.* A material movement means the extracted usage
or tariff disagrees with the flattened cost — a finding about the data, to be investigated and
written down, **not** something to re-baseline away. Re-recording the baseline to absorb an
unexplained move would destroy the only evidence that the split was faithful.

### D5 — Tariffs carry a date

Each `UnitPrice` gets a `PriceAsOf`. Notes quote it.

*Why:* the whole point is that a tariff changes. A rate with no date silently becomes wrong, which
is the situation this change exists to end. A rate older than the budget year should be visible to
whoever reads the generated workbook, not just to whoever reads the code.

## Risks / Trade-offs

- **Usage stays `n=1`** → unchanged and stated. The change is honest about fixing the price half
  only. A reader could mistake "now on the spec's method" for "now accurate"; the notes must not
  allow that.
- **A&K's implied 1.837 kWh/m²/month is derived, not read** → it comes from dividing a real cost by
  a real stated tariff. If the 2,226 VND/kWh is itself a blended or partial figure, the derived usage
  absorbs that error. The extraction should read usage from the 163-row equipment model directly
  where possible, and say which it did.
- **Water may not split** → D3. Accepted as a possible partial outcome.
- **A tariff update will move client-facing figures** → deliberately out of scope here so the split
  can be proven neutral first. Flag to the PM that the update is the next decision, not an
  afterthought.
- **Parking Building's blended 3,751 VND/kWh** is not comparable to A&K's 2,226 → it is a different
  building type and stays out of the residential basis, consistent with existing behaviour.

## Migration Plan

Additive columns; existing readers keep working. Rollback is reverting the code and leaving the new
columns unread — the table stays valid either way. If the baseline was re-recorded, re-record it back
with a reason.

## Open Questions

- Whether `D2. Nước Công Cộng` actually carries volumes (D3 path 1). Answerable only by reading it.
- Whether to update tariffs to current published EVN/SAWACO rates, and for which budget year. PM's
  call, and it moves client-facing numbers.
- Whether diesel should be modelled on running hours (the spec's wording, and A&K's own basis) rather
  than a per-m² litre ratio. A&K records ~22 hours/year of generator run time, which does not
  obviously scale with floor area at all.
