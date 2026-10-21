## Context

The standard form allocates each cost line across product types through fixed weight cells:
- `2. Budget-Management Fund`: BG10 (`='0. Info'!$D$8`, apartment NFA) and BH10 (`='0. Info'!D12`, parking area,
  never filled). Every leaf row's `BG<row>`/`BH<row>` reads them, and BJ/BK divide by `SUM(BG<row>:BH<row>)`.
- `A2` M7:P7 (apartment, shophouse, retail, parking) and `A3`/`A4` P7:S7, written by `_fill_service_post_sheet`.
- BM11/BN11 (monthly vs casual parking), written inside `fill_management_fund_sheet`.

## Decisions

- **D1 Trigger on "no Apartment NFA".** The user's choice (2026-10-19).
  - On sheet 2 this is the same as "weights sum to 0", because BH10 is always 0.
  - On A2 it differs when a villa-only project has car bays: the parking column is then above 0, and without the
    rule the whole security cost would go to parking.
- **D2 Write the weight cells, not `'0. Info'!D8`.** D8 feeds the fee table on `'0. Info'`; putting villas there would
  show them as apartments. BG10 gets a value (the Villas NFA) and a cell note. Its label BG9 says that villas are
  counted in the apartment column.
- **D3 Post-process after the fund sheet.** `_fill_product_mix_fallbacks(wb, project)` runs in the generator's main
  flow right after `fill_management_fund_sheet` returns, so lane A's function is not edited for BG10 or the parking
  sheet. It writes:
  - BG10 and BG9;
  - the parking sheet's D6;
  - 0 over the bay-dividing formulas of a vehicle type with 0 bays.
- **D4 One shared weight.** `_apartment_column_weight(project)` returns the apartment NFA, or the Villas NFA when there
  is none, and says whether the fallback was used. `_fill_service_post_sheet` and `_fill_product_mix_fallbacks` both
  call it.
- **D5 Nominal BM11.** When neither vehicle type has a monthly revenue weight, BM11 = 1 and BN11 = 0. Every allocation
  row then has BK = 0 (no parking cost to split), and the formula stays defined. The guard that refuses a zero sum
  stays, for the case where the cells were not empty but sum to 0.
- **D6 Neither apartments nor villas.** A shophouse-only or office-only project now passes the gate if its total NFA is
  above 0, but its sheet-2 weight stays 0, so the deliverable can carry `#DIV/0!`. This is out of scope and listed as
  an open gap.

## Risks

- Villas sit in the column headed `Căn hộ/ Apartment` on A2-A4. The note on the cell says so.
- Inside `fill_management_fund_sheet` (lane A), the parking fill curve still follows `apartment_units`. With no
  apartments it is the plain resident curve. For a project with 0 bays no figure depends on it.
