# Starting point (task 1.1/1.2), recorded 2026-09-17 before any code in this change is touched

This change adds no write site and alters no calculation (proposal.md, "Figures: None move"). Every
figure below, read from `verification/baselines/baseline.json` and `verification/baselines/
deliverable_baseline.json` as they stood immediately before this change started, MUST still match
byte-for-byte at task 6.1 — the baseline files themselves must not be re-recorded by this change.

`python verification/verify.py` exits 0 (PASS) before this change starts — confirmed 2026-09-17.

## `baseline.json` (recorded 2026-09-17T17:14:54+07:00, reason: rank-comparables-by-location)

| Figure | Value | Unit |
|---|---:|---|
| derived_apartment_rate | 16,500.0 | VND/m²/month |
| mgmt_fee_revenue_monthly | 916,987,500.0 | VND |
| mgmt_fee_revenue_annual | 11,003,850,000.0 | VND |
| staff_cost_annual | 3,923,305,124.5000005 | VND |
| service_reference_annual | 1,846,958,000.0 | VND |
| capex_selected | 309,940,810.0 | VND |
| opex_annual | 3,121,672,572.0 | VND |
| additional_revenue_annual | 7,210,545,456.0 | VND |
| total_profit_value | 3,648,931,493.5 | VND |
| margin | 0.3316049831195445 | ratio |
| markup | 0.4961212677305958 | ratio |
| service_security_annual | 1,294,958,000.0 | VND |
| service_cleaning_annual | 288,000,000.0 | VND |
| service_landscape_annual | 264,000,000.0 | VND |
| capex_mo_equipment | 181,667,810.0 | VND |
| capex_public_area | 172,735,000.0 | VND |
| capex_me_equipment | 128,273,000.0 | VND |
| capex_amenity_area | 12,939,000.0 | VND |
| opex_electricity_annual | 2,669,371,536.0 | VND |
| opex_water_annual | 306,003,816.0 | VND |
| opex_diesel_annual | 60,994,764.0 | VND |
| opex_repairs_annual | 28,135,740.0 | VND |
| opex_admin_annual | 57,166,716.0 | VND |
| opex_pool_salt_annual | 79,200,000.0 | VND |

24 figures.

## `deliverable_baseline.json` (recorded 2026-09-17T19:55:03+07:00, reason: fix-parking-allocation-divide-by-zero amendment)

| Figure | Value | Unit |
|---|---:|---|
| rm_collected_year1 | 2,980,209,375.0 | VND |
| rm_developer_year1 | 8,023,640,626.0 | VND |
| parking_moto_year1 | 572,000,000.0 | VND |
| parking_car_year1 | 2,717,000,000.0 | VND |
| water_year1 | 82,876,033.0 | VND |
| electricity_year1 | 1,837,973,526.0 | VND |
| estimated_surplus_year1 | 4,813,449,847.589485 | VND |

7 figures.

## Method-fidelity starting point (proposal.md's own recorded measurement, 2026-09-09)

68.7% of written cost matches the spec's method, 31.0% does not — entirely `EEE.C`, `EEW.C`,
`EED.C` (the three energy categories, priced by a method the spec does not state for them).
Coverage ~74% of 11D Thi Sách's spend, ~72% of Green Skyline's. Task 4.5 must reproduce this
figure from the implemented check, on the current code, or investigate the difference rather than
adjust the expectation.
