## Why

`ELEVATOR_AD_ITEMS` (`generate_project_output.py:1286-1296` — consumed by both the analysis
workbook's `build_additional_revenue_sheet` and the client deliverable's `fill_common_area_fund_sheet`
RA1.A/RA2 rows) assumes "~2 ad frames per tower" for the "Ad frame (tower lobby, inside elevator)"
revenue line. This is a disclosed guess, not real data — verified this session: no field anywhere in
`generate_project_budget.py` or the `0. Info` intake sheet reads a per-project elevator count.

The standard deliverable template already reserves a real home for this exact figure: sheet
`B4. DT Quảng cáo - Elevator adv`, column E ("Số lượng thang/ Number of ladders"), currently blank on
both its rows. Its own worked-example note (cell M5): *"Mỗi tháp có 3 thang khách + 1 tháng hàng. Có
03 tháp"* (each tower has 3 passenger elevators + 1 cargo elevator; 3 towers) confirms both the
column's real intended meaning and that Savills already distinguishes **passenger** elevators (where
an ad frame goes) from **cargo/freight** ones (where it doesn't) for this exact purpose. This sheet's
own G5/J5/J6 rate formulas are independently confirmed as the source of `ELEVATOR_AD_ITEMS`'s rates
(`14,000,000*80%/12/1.1 = 848,485`, matching exactly) — the rates are real; only the quantity is
guessed.

## What Changes

- Add one new optional project-intake field, **"Passenger Elevators per Tower"**, using the exact
  pattern already established for every field added after the original form shipped
  (`generate_project_budget.py:554-591`: `L.value(...) if L.has(...) else None`) — older intake
  workbooks without this field keep working unchanged.
- Use it for the "Ad frame" row's quantity in `ELEVATOR_AD_ITEMS` when supplied; keep today's
  disclosed "2 per tower" assumption exactly as now when the field is absent.
- The two LCD-screen rows (tower lobby, basement lobby) are unaffected — those are screen counts, a
  separate assumption this change does not touch.
- `B4. DT Quảng cáo - Elevator adv`'s own E5/E6 cells stay unwritten — neither generator populates
  that sheet today, and starting to is a separate, larger scope decision this change does not need to
  make to fix the actual problem (the ad-revenue quantity assumption).
- **BREAKING** in effect, not interface: any project whose PM supplies a real passenger-elevator
  count different from 2/tower will see its RA1.A ad-frame revenue change. A project that has not
  been asked this yet (the field absent) is unaffected.

## Capabilities

### New Capabilities
- `elevator-advertising-quantity`: how the pipeline determines the quantity of elevator ad frames a
  project has, for RA1.A revenue — a real per-project figure when supplied, a disclosed fallback
  assumption when not. Never formally specified despite the mechanism already existing and shipping
  (with the fallback-only figure); this is the right moment to specify it as its behavior gains a
  real, non-assumed path for the first time.

### Modified Capabilities
(none — no existing spec covers this line's quantity; the one incidental mention found in
`proposal-benchmark`'s spec is a total-income rollup listing "advertising" as one of several income
sources, not a requirement about how that figure is derived)

## Impact

- `Budget_Agent/source_code/build_project_input_form.py`: one new `EXAMPLE_DEMAND`-adjacent Project
  Info field (this is a Project Info field, not a Staffing Demand row — placed alongside Tower Count/
  Gate Count/etc., not in `EXAMPLE_DEMAND` itself).
- `Budget_Agent/source_code/generate_project_budget.py`: `read_input()`'s project dict gains
  `passenger_elevators_per_tower` (optional, `None` when absent).
- `Budget_Agent/source_code/generate_project_output.py`: `ELEVATOR_AD_ITEMS`'s "Ad frame" row's
  quantity calculation (currently a hardcoded `qty_per_tower=2`) reads the new field when present.
- Figure-moving for any project supplying a real count different from 2/tower — RA1.A on
  `2.2 Common area Fund` (client deliverable) and the Additional Revenue sheet (analysis workbook).
  Given RA1.A's rate is a modest ~848K VND/device/month, the expected swing is small relative to the
  other two changes proposed this session (`rank-comparables-by-location`,
  `activate-dormant-staffing-ratios`) — stated as an expectation to verify in the measured effect, not
  assumed negligible without measuring. Needs the same measure-then-Head-of-PM-sign-off gate as every
  other figure-moving change here.

Not in scope: basement count (no consumer exists anywhere in the pipeline for it yet — deliberately
not proposed this session, since wiring it in is meaningless without a decided use first) and
utility-by-product-mix (no real data exists anywhere in this repo; not a code fix). Both raised in the
same investigation session as this proposal and the other two already created
(`rank-comparables-by-location`, `activate-dormant-staffing-ratios`) — independent in scope and risk.
