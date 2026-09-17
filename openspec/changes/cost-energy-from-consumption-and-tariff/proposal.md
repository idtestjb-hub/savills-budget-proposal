## Why

`EXENSIVE LOGIC.xlsx` states a consumption-based method for all three energy codes. The pipeline
uses a cost-per-m² ratio for all three.

| Code | Method in the spec | Method in the code |
|---|---|---|
| `EEE.C` Electricity | Projected annual kWh × updated tariff | A&K's VND/m² cost ratio × this project's NFA |
| `EEW.C` Water | Monthly average m³ × tariff × 12 | same |
| `EED.C` Diesel | (Running hours × consumption rate × diesel price) × 12 | same |

On the synthetic sample these three are **3,036,370,116 VND/year — 31.0% of every cost the
deliverable carries**, and they are the whole of the pipeline's measured method drift: scoring every
cost code written into the deliverable against the spec gives 68.7% matching, 0.3% partial, and
31.0% not matching, with these three lines accounting for all of the last figure.

**A cost ratio freezes two different things into one number.** `4,089.11 VND/m²/month` for
electricity is A&K Tower's *usage profile* multiplied by A&K Tower's *tariff*, at extraction time.
So:

- **A tariff change moves the budget by nothing.** Electricity price is the single input most
  certain to change year on year, and today it cannot move a generated budget at all — the number
  only updates if somebody re-extracts A&K's workbook.
- **Every new project inherits A&K's equipment and occupancy** by construction, with no way to say
  so, because usage is not separable from price.
- **The n=1 problem cannot be narrowed**, since a blended cost cannot be widened by adding a tariff.

This is very likely the mechanism behind the already-recorded **"water ~3.3× high"** error. Today
that error is undiagnosable: there is no way to tell whether the pipeline over-estimates how much
water a building uses, or over-prices it, because it only ever holds the product.

**The source data already works the spec's way.** The extraction flattened it. `Fact_OPEX.csv`'s
`Source` column records, in prose:

| Project | Category | Consumption | Tariff |
|---|---|---|---|
| A&K Tower | Electricity | 163-row equipment load calc | **2,226 VND/kWh** |
| A&K Tower | Diesel | ~12h/yr testing + ~10h/yr backup | **19,260 VND/litre** |
| Parking Building | Electricity | **62,622 kWh/month** | **~3,751 VND/kWh** (blended) |
| Parking Building | Water | **3,300 m³/month** | **29,000 VND/m³** |
| Parking Building | Diesel | **523 litres/month** | **22,000 VND/litre** |
| A&K Tower | Water | *not recorded* | *not recorded* |

A&K's electricity implies **1.837 kWh/m²/month** (262,210,141 ÷ 2,226 ÷ 64,124). A&K's diesel line
is already `hours × rate × price` in its own source sheet — exactly the spec's formula, collapsed to
a monthly VND figure by the ETL.

## What Changes

**The three energy lines are costed as consumption × tariff**, the method the spec states and the
method the source workbooks already use.

**`Fact_OPEX.csv` gains structured consumption and tariff columns.** The figures above stop living
in a prose `Source` string and become data, with the unit named (`kWh`, `m³`, `litre`) and
provenance kept. The existing `MonthlyVND` column stays, so nothing that reads the table today
breaks.

**Tariffs become a named, updatable input rather than an embedded constant.** Each carries its
source and the date it was current, so a stale tariff is visible instead of silent.

**Every generated note reports both halves.** A reader sees the usage assumed, the tariff applied,
and the sample size behind each — so a wrong figure can be diagnosed as a usage error or a price
error rather than just "too high".

**Where a tariff is not recoverable, the change says so rather than inventing one.** A&K's water
line has neither m³ nor tariff in the extraction. Two honest paths exist — re-extract them from the
`D2. Nước Công Cộng` sheet, which is itemised by tower and should carry both; or fall back to the
existing cost ratio for water alone, labelled as not yet split. The design records which was taken
and why. **No tariff is guessed to make the formula work.**

Deliberately **not** in scope:

- **Widening the usage basis beyond n=1.** Splitting cost into usage × price does not add a second
  residential property. The usage ratio stays as thin as it is, and stays labelled `n=1`. What
  changes is that it is now *nameable* and separately improvable (`R-D02`).
- **Resolving the "water 3.3× high" error.** This change makes it diagnosable, not fixed. Which half
  is wrong is a question for the data once the split exists.
- Any other cost code, and `EMH1`.

## Capabilities

### New Capabilities

<!-- None. This is the same requirement logic-spec-method-alignment already states, applied to
     three more codes, plus one addition about a rate that changes over time. -->

### Modified Capabilities

- `logic-spec-method-alignment`: adds the requirement that where the spec states a method as
  *quantity × price*, the pipeline SHALL hold and report the two separately rather than only their
  product — and that a price expected to change over time carries the date it was current.

## Impact

**Code**

- `rescan_opex_from_source.py` — extracts consumption and tariff alongside cost.
- `estimate_opex.py` — electricity, water and diesel computed as usage ratio × tariff; the source
  string reports both halves and each one's `n`.
- `generate_project_budget.py` / `generate_project_output.py` — remarks quote usage, tariff and
  sample size. No change to where either figure is written.

**Data**

- `Fact_OPEX.csv` (**Generation A**) gains columns; no existing column changes meaning and no row is
  removed. **No Fact/Dim join key changes**, so the Copilot Studio package's live Generation B data
  is unaffected.

**Figures**

- `opex_electricity_annual`, `opex_water_annual` and `opex_diesel_annual` should reproduce their
  current values to within rounding **if** the split is arithmetically faithful — usage × tariff is
  the same product the ratio already held. A material move means the extraction disagrees with the
  flattened figure, which is a finding to investigate, not to re-baseline away.
- Once tariffs are updated to current published rates, the figures move by the tariff delta. That is
  a separate, deliberate step and should be taken as its own decision with the PM.

**Not affected**

- No dependency changes. No production data changes. No template changes.
