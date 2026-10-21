## Why

The M3 acceptance run of 2026-10-19 (four real projects) could not run a low-rise project as it is:
- the tool refuses a form with no Apartment NFA (`Project Info!C14:D14 ... must be filled in`), so a villa-only project
  had to be entered with its villas booked on the Apartment row, which puts its fee on `RM.AP` instead of `RM.VI`;
- the tool refuses a project with 0 car and 0 motorbike bays (`BM11:BN11 ... sum to zero`), so the run entered one
  invented motorbike bay.

With both refusals removed on a copy, the run finished, but the recalculated deliverable carried 2,112 `#DIV/0!` cells.
The standard form splits costs by product type over weights for apartment, shophouse, retail and parking, and has no
villa column. The cells:
- `2. Budget-Management Fund` BJ:BN, which divide by `SUM(BG:BH)`; BG10 = `'0. Info'!D8`, the apartment NFA;
- `A2` Q:U, `A3` and `A4` T:X, which divide by the allocation basis on row 7;
- `Tiến độ lấp đầy bãi xe` row 11 from month 13 (`=R6*$D$6*150%/$D$11`, motorbike bays).

## What Changes

Decided by the user on 2026-10-19:
- **Run gate:** Apartment NFA is no longer required. A form needs a total NFA above 0 over all products. A total of 0
  is refused with a clear message.
- **Villas in the apartment column:** when the project has no Apartment NFA, the apartment allocation weight takes the
  Villas NFA: BG10 on `2. Budget-Management Fund`, M7 on `A2`, P7 on `A3` and `A4`, each with a note. `'0. Info'!D8`
  stays empty, so no management-fee revenue moves. The trigger is "no Apartment NFA", not "weights sum to 0", so a
  villa-only project with car bays still gives its villas their share.
- **Parking fill-up sheet:** D6 (units) takes the total units of all products when there are no apartment units. A
  vehicle type with 0 bays has the fill formulas that divide by its bay count written as 0, with a note.
- **Parking allocation weight:** with no monthly parking revenue weight at all, BM11 = 1 (nominal) and BN11 = 0, so the
  351 allocation rows stay defined. The BM11/BN11 block moves out of `fill_management_fund_sheet` into
  `_parking_allocation_weights`, called from one line.
- **Summary narrative:** the `RM` sentence on `1. Summary` leaves out a product with NFA 0 and no recorded rate.

Figures move only for a project without apartments or without parking bays. The standard sample, the other fixtures
and the three real M3 projects that have apartments and bays do not change.

## Capabilities

### New Capabilities
- `villa-only-and-no-parking-projects`: running a project without apartments or without parking bays.

### Modified Capabilities
- none

## Impact

- Code, `generate_project_budget.py`:
  - the `read_input` gate and the `RM` branch of `_recipe_narrative`;
  - new `_apartment_column_weight`, `_parking_allocation_weights` and `_fill_product_mix_fallbacks`;
  - the allocation basis in `_fill_service_post_sheet`;
  - `fill_management_fund_sheet` (lane A) changes in one place only: its BM11/BN11 block becomes a call to
    `_parking_allocation_weights`.
- New fixture builder `verification/fixtures/build_villa_fixture.py` (invented data), used by the tests and the A/B.
- Not touched: pricing, staffing, `estimate_opex`, the parking revenue rows RP1/RP2, `'0. Info'`.
