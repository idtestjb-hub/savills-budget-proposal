## 1. Budget year by most months

- [x] 1.1 `BudgetPeriod.budget_year` (most months, later year on 6/6) with tests (01/2027, 08/2025, 07/2027, 12/2026)
- [x] 1.2 Use it for `AL5`, `existing_result` and `utilities_result` in `generate_project_budget.py` and
      `generate_project_output.py`; leave the roster month and month-dated lookups on the start month
- [x] 1.3 Diesel's own VAT row (`vat`/`diesel`) overrides the general rate in `diesel_price`; tests
- [x] 1.4 Local Review of ONE VERANDAH (08/2024–07/2025) passes the prior-year check. Done 2026-10-28: AL5 2026, period 01/08/2025–31/07/2026, Review sheet written

## 2. Data rows (Budget_Agent\data\generation_B_verified, outer repo)

- [x] 2.1 `Ref_UtilityTariffs.csv`: diesel listed price one row per month 01/2024–09/2026, listed VAT by period, each
      with source and checked date
- [x] 2.2 `Ref_LaborLawParams.csv`: minimum wage I–IV and insurance base for 01/2024–06/2024
- [x] 2.3 Rerun Masteri An Phú locally; add any further dated row it shows missing, with its source (electricity
      2023-11 to 2024-10, general VAT 01–06/2024, SAWACO water 2024–06/2025)

## 3. Verify and ship

- [x] 3.1 Full tests + `verification/verify.py` PASS; local Review of the three files completes. Done 2026-10-28: 1288 passed + 1 xfailed; verify.py PASS after re-recording the three baselines (diesel only, +7,666,512 VND/year); Masteri, ONE VERANDAH, HAGV complete locally
- [x] 3.2 Release note for [Hub] (code + data); after deploy rerun the three Reviews on the server. Done 2026-10-29: 57fa053 deployed 12:52 (8b9a6a1f3e2c); HAGV, Masteri An Phú, ONE VERANDAH reruns done (rc 0)
