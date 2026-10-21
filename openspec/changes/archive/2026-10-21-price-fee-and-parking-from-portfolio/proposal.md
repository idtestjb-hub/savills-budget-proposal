## Why

Two revenue unit rates on the client deliverable still rest on one or two reference projects, and the M3 back-test
on four real projects (2026-10-19) put them among the largest deviations the tool produces:

- **`RM.AP`, the apartment management-fee rate (VND per m² per month)**, is the average of the two nearest
  comparables that carry a per-product Apartment rate. Only 11 of the 105 master-list rows carry one, so the
  "two nearest" are often far away in size and location. On the four real projects the line was 41,559 million
  VND a year off in total (City Garden −45%, Lumi Signature −71%, Masteri Thảo Điền −12%, Verosa priced as if
  it had apartments).
- **`RP1` and `RP2`, the monthly parking prices (VND per vehicle per month)**, are two constants copied from one
  reference project's parking proposal in 2025: 110,000 for a motorbike and 1,100,000 for a car. The master
  list holds a parking price for 53 (cars) and 61 (motorbikes) real projects that the tool never reads. The
  two lines were 4,336 million VND a year off in total on the four projects.

The user chose both lines for core v1 on 2026-10-19 (deviation list, groups A and J) and, on 2026-10-20, chose
the sources and rules below.

## What Changes

- **`RM.AP` is priced from the real budgets of Savills-managed projects**, through the anonymous value table
  that already prices seven cost lines (`Budget_Agent/data/real_budget_ranges/Ref_RealBudgetValues.csv`,
  change `use-real-budget-ranges`). The build step gains one code, `RM.AP`: the full apartment management fee
  per month (the fee collected on `RM.AP` plus the developer's share on `RM.0A`, which the developer pays on
  units not yet handed over) divided by the project's **apartment** NFA, excluding VAT, brought to 2027 prices
  with the sourced CPI table. 24 of the 41 store projects carry a usable value (budget years 2025: 7, 2026: 13,
  2027: 3, 2028: 1); the median today is about 17,000 VND per m² per month before VAT.
- **The applied Apartment rate becomes the range's median** (the project itself left out, IQR outliers dropped,
  at least 10 projects), converted to the deliverable's VAT basis at the budget period's first month, in the
  one place both workbooks already read it from (`resolve_product_rates`). Below 10 projects, or without the
  values file, the tool prices exactly as today (two nearest comparables) and says so. The two nearest
  comparables are still shown on the Comparison sheets and still drive the benchmark verdict; non-Apartment
  products keep their own comparable rates and their Apartment fallback, which now follows the new rate.
- **A rate the PM entered still wins.** The existing Product Mix field "Actual Rate (VND/m²/month)" ranks ahead
  of the range exactly as it ranked ahead of the comparables; nothing about it changes.
- **`RP1` and `RP2` are priced from the master list's parking prices.** A new reader parses the first-vehicle
  monthly price out of the free-text car and motorbike fee columns of `Dim_Property_Residential.csv` (53 car
  and 61 motorbike prices today; "no paid parking", 0, blank and unreadable texts are listed, not priced). The
  applied price is the median after leaving out the project's own row and IQR outliers, used as quoted
  (including VAT, no CPI step: the master list is the 2026 snapshot of list prices), with the same 10-project
  floor. Medians today: about 1,200,000 VND per car and 145,000 VND per motorbike per month.
- **Two new optional fields on `Project Info`**: "Car Parking Price (VND/vehicle/month)" and "Motorbike Parking
  Price (VND/vehicle/month)". An entered price wins over the range for that vehicle type in both workbooks and
  on the helper sheet B5; the recorded monthly parking revenue of a project at stable operation still ranks
  ahead of both. Blank or 0 means "not entered". A form without the fields reads as blank.
- **Vietnamese remarks on the deliverable** name the number of projects, the median and the P25–P75 band
  (no project names, decision D3); the `1. Summary` narratives and helper sheet B5 quote the same prices.
  The internal analysis shows, for `RM.AP`, the new row on the `Real-Budget Ranges` sheet (every project id,
  value, the ones left out and why) and, for parking, a new block on the Additional Revenue sheet listing
  every master-list row read with its parsed price or the reason it was not used.
- **Only `RM.AP`, `RP1`, `RP2` and their consequences move**: `RM.0A` (mirror of the full fee), `EMH1` when the
  Savills fee is a percentage, `RI1` (interest on the fund balance), the contingency on `EM#`/`ES#`/`EE#`
  through `RI1`, the `RPa` subtotal, the parking allocation weights `BM11`, `0. Info`'s fee table, the
  Comparison sheets and the benchmark line. Every other line is unchanged, which the A/B proves line by line.

Not in this change: a segment or grade split of the fee range (the user chose the whole-portfolio median; a
"fee level" selector was offered and declined), a parking price by district, the parking fill-up curve, the
casual parking lines `RP3`–`RP9`, and the `RM.VI` villa rate.

## Capabilities

### New Capabilities
- `parking-revenue-pricing`: how the monthly parking prices behind `RP1` and `RP2` are decided — entered price,
  else the master-list median, else the former constants — and what the remarks, narratives and helper sheet say.

### Modified Capabilities
- `product-revenue-pricing`: the order of sources for the Apartment rate gains the real-budget range between the
  entered rate and the two-comparable average; the comparables keep their display and benchmark roles.
- `real-budget-ranges`: the data file carries one more code, `RM.AP`, measured per m² of apartment NFA with the
  developer's share included; the tool forms its range like the others and exposes it as a rate, not an amount.
- `input-workbook-reading`: two optional parking-price fields on `Project Info`, read by label, blank-tolerant.
- `deliverable-remarks`: the `RM.AP`, `RP1` and `RP2` remarks for the range-priced case and the entered-price case.

## Impact

- **Code**: `build_real_budget_ranges.py` and `real_budget_ranges.py` (the `RM.AP` code, apartment NFA as
  denominator, `RM.0A` added, a rate result); `master_comparables.resolve_product_rates()` (the range as the
  Apartment source); new `parking_prices.py` (parser and range); `operating_inputs.py` and
  `build_project_input_form.py` (two fields); `generate_project_budget.py` (fund rows `RM.AP`/`RP1`/`RP2`,
  `_UNIT_RATES`, `RPa` narrative, helper B5, `0. Info` fee note); `generate_project_output.py` (Management Fee,
  Comparison, Additional Revenue and `Real-Budget Ranges` sheets); `verification/` (the entered-fields guard
  and the fixture check for the new fields).
- **Data files read**: `Budget_Agent/data/real_budget_ranges/Ref_RealBudgetValues.csv` (rebuilt, one more code),
  `Budget_Agent/data/generation_B_verified/Ref_CPI_VN.csv`, `Budget_Agent/data/master_list_verified/
  Dim_Property_Residential.csv` (two columns the tool never read before). **Data files written**: the rebuilt
  `Ref_RealBudgetValues.csv` and its `README.txt` (outer repository, anonymous). The scan store and the id map
  stay in `Savills-local`.
- **Baselines**: recorded figures move on the standard sample (`derived_apartment_rate`, management-fee
  revenue, parking revenue, surplus and every total they feed). Verify runs with the two baseline gates open
  (`verify_gate_open.py`), as for every change since group 6; the baselines are re-recorded once in group 10 of
  `apply-head-of-pm-decisions-2026-10`.
- **Sign-off**: the user, standing in for the Head of PM, on the measured before/after (standard sample, the
  four fixtures, the four real projects of the M3 runner), before anything is committed on `lane-b`.
  `main` stays frozen at `14778cb` until after the PM presentation of 2026-10-21.
