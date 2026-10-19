## Why

`ESI1` (risk asset insurance, compulsory fire and explosion cover included) is a Required line, and the tool always
leaves it at 0, because no input carries the insured asset value. In the M3 acceptance run of 2026-10-19, the four
real budgets carry 0 to 2,767 million VND a year on this line, 4,422 million |gap| in total. The AI Guideline prices
it as the total asset value × the premium rate (example: commercial apartment building, 0.05%, Decree 105/2025/NĐ-CP).
One real budget shows the full working: sum insured 6,707,011,785,586 VND × 0.0375% (0.05% after the maximum 25%
discount) = 2,515,129,420 VND, plus 10% VAT.

## What Changes

Decided by the user on 2026-10-19:
- **Two optional Project Info fields**, read by label, in a new section `ASSET INSURANCE (ESI1)` appended below
  every other section of Project Info:
  - `ESI1 Insured Asset Value (VND)`;
  - `ESI1 Premium Rate`, where blank means 0.05%, so a PM can enter a discounted rate.
  A form made before this change has neither field and reads as blank.
- **Pricing:** ESI1 per year = asset value × rate, before VAT. Insurance VAT (10% in every month, outside the
  reduction) is added the same way as `ESI2`, and the amount is spread evenly over the 12 months. The remark gives the
  formula, the rate and where it came from.
- **Blank, 0, negative:**
  - blank value: ESI1 stays 0, and the reason names the field to fill in;
  - 0: ESI1 stays 0, with the reason that the PM entered 0;
  - a negative or non-numeric value, or a rate that is 0, negative or above 1%, stops the run and names the field.
- **Not changed:** `RM.OA2` (fire insurance collected on behalf). The fund carries the cost; recovering it is left for
  after core v1.
- **Code placement:** the ESI1 write moves out of `fill_management_fund_sheet` (lane A) into a new
  `_write_asset_insurance`, called from one line.

Figures move only when the PM fills in the asset value. A form without it produces the same budget as before.

## Capabilities

### New Capabilities
- `asset-insurance-pricing`: pricing ESI1 from the insured asset value.

### Modified Capabilities
- none

## Impact

- Code:
  - `generate_project_budget.py`: the two labels, `_resolve_esi1`, the read in `read_input`, `_write_asset_insurance`,
    and one line in `fill_management_fund_sheet`;
  - `build_project_input_form.py`: new `add_asset_insurance_fields`, called after the Operating section, with the
    notes and the rate validation.
- Not touched: `RM.OA2`, `ESI2`, the `2.2 Common area Fund` share rule, `real_budget_ranges` (ESI1 stays a cross-check
  code there).
