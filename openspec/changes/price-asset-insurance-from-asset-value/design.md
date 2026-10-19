## Context

`ESI2` (public liability insurance) is already priced from two optional Project Info fields: the premium in USD and
the exchange rate. `_resolve_esi2` validates them, and `write_vat_monthly` inside `fill_management_fund_sheet` adds
the insurance VAT kind (`utility_tariffs.VAT_INSURANCE`, 10% every month) and spreads the amount evenly. `ESI1` gets a
remark-only zero through `_write_zero_reason`.

## Decisions

- **D1 Same pattern as ESI2.** Two optional fields read by label. A new `_resolve_esi1` returns the value, the rate,
  and whether the default rate was used. `ESI1 Premium Rate` is a fraction, shown as a percent on the form
  (0.0005 = 0.05%).
- **D2 Default rate 0.05%.** This is the AI Guideline's example for a commercial apartment building, citing Decree
  105/2025/NĐ-CP. The remark says whether the default or the PM's rate was used. A rate above 1% is refused as a
  likely typing slip (for example 0.05 entered meaning 0.05%).
- **D3 VAT and timing like ESI2.** 10% insurance VAT in every month, outside the 8% reduction, spread evenly over the
  12 months. One real budget adds 10% VAT on the premium; another pays in two instalments. An even spread keeps the
  monthly sheet simple and matches ESI2.
- **D4 One line in lane A's function.** `_write_asset_insurance(ws, project, write_vat_monthly)` takes the closure
  that already prices ESI2, so the VAT handling has one source. `fill_management_fund_sheet` replaces its ESI1
  `_write_zero_reason` call with this call.
- **D5 RM.OA2 untouched.** The user's choice (2026-10-19). The form has no field saying whether the management fee
  already includes insurance.
- **D6 Appended below every section.** The Existing and Operating sections are written at fixed rows (57 and 62)
  after the scalar fields, so a fixed row number in that range is overwritten. The section starts two rows below the
  last used row and is found again by label.

## Risks

- A PM who enters the asset value without the discounted rate gets the undiscounted 0.05%. The remark names the rate
  used.
- The `2.2 Common area Fund` ESI1 line follows its existing share rule. Nothing about it changes here.
