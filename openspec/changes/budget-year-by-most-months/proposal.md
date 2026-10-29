## Why

Three Review runs on the server stopped on 2026-10-28, each for a different reason:

- **ONE VERANDAH** (`FORM Budget 2025`, period 08/2024–07/2025): the import calls the file's year by the year that holds
  most of its months (2025, `review_import.py`), so the new period is 08/2025–07/2026. The budget generator calls a
  budget's year by its first month (`AL5 = start_year`), so the new budget is "2025" too, and the prior-year check
  stops the run ("Prior Budget Year 2025 is not before the budget year 2025"). The Savills form names its own default
  period 01/09/2026–31/08/2027 "2027", the PM files name 08/2024–07/2025 "Budget 2025", and the scan store uses the
  most-months rule; only the generator differs.
- **HOÀNG ANH GIAI VIỆT** (budget 2025, new budget 2026): `Ref_UtilityTariffs.csv` holds diesel only from 01/10/2026,
  so 01/01/2026 has no price (TariffError).
- **Masteri An Phú** (budget 2024, new budget 2025): `Ref_LaborLawParams.csv` starts at 01/07/2024, so the prior year
  2024 has no regional minimum wage for January–June.

User's choices on 2026-10-28: fix all three now; a budget's year is the calendar year that holds most of its twelve
months (a 6/6 split takes the later year); diesel gets one row per month, the price in force at 00:00 on the 1st.

## What Changes

- `BudgetPeriod.budget_year`: the calendar year holding most of the twelve months, the later year on a 6/6 split.
- The generators use it wherever the period's first year stood for the budget year: `AL5`, `existing_result`,
  `utilities_result` (both generators). The roster's sample month and every month-dated lookup are unchanged.
- Data (`Budget_Agent\data\generation_B_verified`, outside this repo, shipped by the server's usual data copy):
  - `Ref_UtilityTariffs.csv`: diesel `listed_price` one row per month 01/2024–09/2026 (Petrolimex announcements) and
    `listed_vat_pct` by period; diesel's own VAT rows (10% while the general cut excluded fuel, 0% from 27/03/2026 to
    31/12/2026); the 01/10/2026 price corrected to "no VAT inside" (it was recorded as 8%), which raises every 2027
    diesel price about 8% (30,260 → 32,681 VND/l); electricity 09/11/2023–10/10/2024 (QĐ 2941/QĐ-BCT); general VAT
    01–06/2024; SAWACO business and public-body water 2024–06/2025;
  - `Ref_LaborLawParams.csv`: `min_wage_region` I–IV and `insurance_base` in force 01/2024–06/2024 (Nghị định
    38/2022/NĐ-CP, Nghị định 24/2023/NĐ-CP), plus any further rows the Masteri rerun shows missing.

## Capabilities

### New Capabilities

### Modified Capabilities
- `budget-period`: the budget year of a period is the year holding most of its months.
- `dated-tax-and-tariff-rates`: diesel is priced from the listed price in force on the 1st of each month, from a
  monthly history.

## Impact

- `budget_period.py`, `generate_project_budget.py`, `generate_project_output.py`, `utility_tariffs.py` (diesel's own
  VAT row); tests.
- A January start keeps its budget year. Recorded baselines with a diesel line move with the corrected 2027 price.
- A non-January period's deliverable now says the later year where most months fall (07/2027–06/2028 is "2028").
