## Why

`EXENSIVE LOGIC.xlsx` is Savills' own costing methodology: 267 leaf cost codes, each with a stated
calculation formula. Where the pipeline fills a code, it should use the method the spec states for
it. For four codes it did not.

| Code | Method in the spec | Method in the code (before) |
|---|---|---|
| `ESS1` Security | Monthly contract fee × 12 **OR** headcount × cost per guard × 12 | headcount × daily rate |
| `ESS4` Cleaning | **m² × unit price × 12** OR monthly contract × 12 | headcount × daily rate |
| `ESS16` Landscape | **Monthly contract × 12** | headcount × daily rate |
| `ESM4` Pool chemicals | **Pool volume × kg/m³/month × unit price × 12** | one project's flat figure |

Only `ESS1` sanctions a headcount basis. `ESS4` and `ESS16` did not, and all three used it.
`ESM4` states a formula outright, and the code used a constant.

Worse, the two generators disagreed about the answer. The deliverable charged one figure and the
analysis costed another, differing by **210,372,000 VND** on the synthetic sample — the same class of
divergence the recovery audit was built to catch.

Separately, `CAPEX_RESERVE_RATE = 0.10` was hardcoded, with a comment conceding it was *"a commonly
cited property-management rule of thumb, NOT this project's own real reserve policy, which isn't in
the source data."* It **is** in the source data.

## What Changes

**Service contracts on the spec's method.** `ESS1`, `ESS4` and `ESS16` are priced as
**monthly contract × 12**, where a vendor contract is what it is in practice: a number of posts at a
citywide post rate, blended for the project's own night-shift split. Both generators use the
identical figure, so the deliverable and the analysis agree by construction.

**The `m²` branch is not implementable and this records why.** `Fact_MasterRateCard.csv` has **no
per-m² cleaning rate** — every Service-domain row is priced `VND/position/month`. The spec's
alternative branch for `ESS4` is used instead, and the output says so.

**Capex reserve derived, not assumed.** A new extractor reads `EN1`–`EN3` from the real project
budgets into a reference table; the rate is computed from it at run time and reported with its
sample size and range. **0.1093** (n=4, range 8.33%–12.50%) replaces the hardcoded 0.10.

**A full-repeat year is not a reserve year.** Green Skyline repeats its full Year-1 Capex in Year 2
(×1.03) and only drops to the reserve in Year 3. Averaged in, that observation would have produced a
27.4% rate. The extractor classifies repeat years apart from reserve years.

**The written spec is wrong about the reserve and this is recorded.** `EN1`–`EN3` state *"khoảng
0.1%"*. No real project is near it; 0.1% implies a thousand-year replacement cycle. Correcting
Savills' document is Savills' call — the pipeline records the contradiction rather than perpetuating
either figure silently.

**Pool chemicals costed from volume, not copied from one project.** `ESM4`'s stated method —
salt electrolysis at 4,000 ppm, 1–4 kg/m³/month at 6,000đ/kg — needs pool **volume in m³**, which
the intake form did not collect. It now does. The line is computed as
`volume × 2.5 kg/m³/month × 6,000 × 12` (2.5 being the midpoint of the stated range, with the full
range reported alongside every figure), in `estimate_opex()` so both generators read one number.

The flat figure this replaces turned out to *be* this formula: A&K Tower's 79,884,000 VND/year
implies 444 m³ at the midpoint rate, against the spec's own 440 m³ worked example — 0.9% apart.
Reusing it for other projects was reusing A&K's pool, not A&K's evidence. A project that leaves
the field blank still gets that flat figure, now explicitly labelled as a fallback that does not
vary with pool size.

**The verification hand-checks were no longer independent.** `read_sample_scale()` read the fixture
by fixed cell address. When the Product Mix block grew from 5 products to 9, five of its seven
inputs silently became `0`/`None`, and the two checks consuming them kept reporting OK — one by
falling back to the workbook it was supposed to be checking, the other by comparing against zero.
Both now read by label and fail when they cannot reach their input.

Deliberately **not** in scope:

- **`EMH1`.** The spec's CPI-adjusted and NFA×price branches do not exist in code. `EMH1` is blank
  per D1 anyway.
- **The remaining 250 unimplemented codes.** Most need per-project inputs that do not exist.
- Widening the citywide service rates beyond n=1 (`R-D02`).

## Capabilities

### New Capabilities

- `logic-spec-method-alignment`: the requirement that a cost code the pipeline fills is computed by
  the method Savills' own costing spec states for it, and what happens when that method cannot be
  implemented from available data.

### Modified Capabilities

- `budget-workflow-verification`: a hand-check that cannot read the input it is anchored to must
  fail rather than fall back to the artifact under test. This belongs here because this change is
  where the degradation was found and fixed.

<!-- The Capex reserve work belongs to the separate `derive-capex-reserve-rate` change, which
     already owns that capability's spec; its tasks are ticked there rather than duplicating the
     capability across two active changes. This proposal describes the capex work only because the
     two were implemented in one sitting. -->

## Impact

**Code**

- `rescan_capex_reserve.py` — new extractor.
- `generate_project_budget.py` — `ESS1`/`ESS4`/`ESS16` priced by contract; remarks rewritten;
  `pool_volume_m3` read from the form; the `ESM4` write site defers to `estimate_opex()`.
- `generate_project_output.py` — `CAPEX_RESERVE_RATE` derived; the three service categories in Cost
  Priority point at the Service sheet's contract figure; `Cleaning — Supervisory` folded into it;
  the OPEX sheet shows a category's stated method where it has one.
- `estimate_opex.py` — `ESM4` computed from pool volume; `POOL_SALT_*` constants cited to the spec.
- `build_project_input_form.py` — `Pool Volume (m³)` field added at `B31`; `Gate / Entrance Count`
  moves to `B32` and `_GATE_COUNT` follows it; fee section moves to rows 34–36.
- `verification/baseline.py` — `read_sample_scale()` reads by label; two hand-checks now fail
  rather than degrade.

**Data**

- `Fact_CapexReserve.csv` — new. No existing table modified, no join key changed.
- `verification/fixtures/Sample_Project_Input.xlsx` — regenerated in the current form layout with
  Pool Volume = 440 m³. Its predecessor is kept as `Sample_Project_Input_PRE_ESM4_POOL_VOLUME.xlsx`;
  nothing was discarded.

**Figures**

- `staff_cost_annual` −54,030,000, `total_profit_value` +54,030,000, `margin` +0.0044,
  `markup` +0.0134. Staff TOTAL across all categories −210,372,000.
- `opex_pool_salt_annual` 79,884,000 → 79,200,000 on the regenerated fixture (440 m³). No other
  tracked figure moves with it: Pool Salt is Conditional, so it sits outside the Must-Have OPEX
  subtotal that `opex_annual` and `total_profit_value` read. On a real project the movement is
  whatever that project's own pool volume implies, which is the point of the change.
- **The trade-off, stated:** the contract method uses citywide rates at n=1, so it is more faithful
  to the written method and **less project-specific** than the roster basis it replaces. A cleaning
  supervisor and a line cleaner now cost the same.

**Not affected**

- No dependency changes. No production data changes. No template changes.
