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

### D6 — The source workbooks are not in this repository; tariffs come from the method catalogue, usage from A&K's recorded cost (decided during apply, 2026-09-10)

`Project_Clone2_NewData` has no `input/budget_planning/` — the A&K Tower and Parking Building
budget workbooks (with the `D3a`, `D2. Nước Công Cộng`, `D4. Chi Phí Dầu` sheets D3 wanted to
re-extract) are not here. `docs/06-unread-datasets.md` already records the modules that reference
that path as broken, and `rescan_opex_from_source.py` was always a curated list of hand-verified
figures with prose provenance, not a live reader.

What is available instead, and is arguably better:

- **The method catalogue** (`Costing_Method_Catalogue.csv`, built by `adopt-guideline-as-costing-method-spec`,
  PM-signed) carries the guideline's tariffs with real legal citations:
  - `EEE.C` electricity — **2,226 VND/kWh**, QĐ 1279/QĐ-BCT dated **2025-05-09** (under-6kV admin rate).
  - `EEW.C` water — **19,786 VND/m³**, SAWACO built-up (base + VAT 5% + PBVMT 30% + VAT-on-PBVMT 8%).
  - `EED.C` diesel — "DO 0.005S Vùng 1 listed price on the budget date" (no fixed number); the
    recorded A&K provenance gives **19,260 VND/litre**.
- **A&K Tower's recorded monthly cost** (`rescan_opex_from_source.py`, each figure traced to a
  named cell) stays the usage anchor.

**The model:** `usage_ratio_per_m² = A&K_recorded_monthly_cost ÷ tariff ÷ A&K_NFA`, then
`figure = usage_ratio_per_m² × project_NFA × tariff`. Algebraically the tariff cancels when it is
unchanged, so **every current figure reproduces bit-for-bit** (verified across four NFA values —
delta 0). Changing a tariff moves the figure proportionally (task 4.5). Usage stays `n=1` (A&K) and
stays labelled.

**Electricity** reconciles cleanly — A&K's own implied tariff (cost ÷ its 163-row kWh model) is
2,226, the same as QĐ 1279. **Water** does not: A&K's ~2020 bill rate is unknown, so dividing its
cost by the 2026 SAWACO tariff gives an *implied* m³ that is a lower bound if A&K's real rate was
below 19,786. The remark says exactly this. **Diesel** uses A&K's recorded 19,260 VND/litre, dated
~2020 and flagged stale for a 2027 budget.

This supersedes D3's "water may not split": it splits, with the caveat stated on the output.
Tasks 2.1–2.3 are read from the recorded provenance + the catalogue rather than from the absent
workbooks; task 2.2's "read the equipment model directly" is not possible and the divided figure is
used, which is sound because A&K's tariff and the catalogue's agree.

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

- ~~Whether `D2. Nước Công Cộng` carries volumes~~ — moot: the sheet is not in this repository
  (D6). Water splits against the catalogue's SAWACO tariff instead, with the caveat stated on the
  output.
- Whether to update tariffs to current published EVN/SAWACO rates, and for which budget year. PM's
  call, and it moves client-facing numbers. Electricity's 2,226 VND/kWh is already current (QĐ 1279,
  2025-05-09); water's 19,786 is a guideline example; diesel's 19,260 is ~2020 and stale.
- Whether diesel should be modelled on running hours rather than a per-m² litre ratio. **Decided
  during apply: stays per-m² (design D1)** — proven-neutral is the priority; running-hours is a
  follow-up. Flagged in the remark and `docs/05`.
