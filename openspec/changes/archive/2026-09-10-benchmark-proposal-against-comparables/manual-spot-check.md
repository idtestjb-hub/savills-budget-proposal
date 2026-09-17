# Manual spot-check — task 4.1

**Project used:** Diamond Skyline (the live `Project_Budget_Input.xlsx`; a real project, treated as
a new prospect — not in `master_comparables.py` with a verified Apartment rate, so the reality-check
row correctly reads "not applicable").

**Run:** `python generate_project_budget.py` on 2026-09-10, then the generated
`Budget_Agent/sample_output/Diamond Skyline - Sample Consulting Budget.xlsx` opened in Excel (COM,
`CalculateFullRebuild`).

Comparables selected (nearest by Total building NFA, with a verified Apartment rate):
Masteri An Phu 16,800 · Green Skyline 15,000 → derived Apartment rate **15,900** VND/m²/month.
Project scale: apartment NFA 72,000 m², 600 apartment units.

| # | Check | Expected (by hand) | On the sheet | ✓ |
|---|---|---|---|---|
| a | Fee per apartment = derived rate × (apt NFA ÷ apt units) | 15,900 × (72,000 ÷ 600) = 15,900 × 120 = **1,908,000** | B "Management fee per apartment" = 1,908,000 | ✓ |
| a′ | Comparable fee per apartment (upper bound) = rate × (total NFA ÷ apt units) | Masteri 16,800 × (75,518.73 ÷ 1,048) = **1,210,606**; Green 15,000 × (92,100.09 ÷ 1,251) = **1,104,318** | C = 1,210,606 (approx); D = 1,104,318 (approx) | ✓ |
| b | Projection = own revenue + apt NFA × (comp rate − derived rate) × 12 | Masteri: 15,020,400,000 + 72,000 × 900 × 12 = 15,020,400,000 + 777,600,000 = **15,798,000,000**; Green: − 777,600,000 = **14,242,800,000** | C = 15,798,000,000; D = 14,242,800,000 | ✓ |
| c | Coverage cells = `1. Summary` H13 / H20 / H46, and % = H46 ÷ H13 | H13 17,612,957,357 · H20 10,300,946,679 · H46 7,312,010,678 · % = 41.5% | benchmark income/cost/surplus identical; % = 41.5% → band "generous" | ✓ |
| d | Verdict reads correctly for 15,900 vs [15,000, 16,800], surplus > 15% | "sits within the 15,000-16,800 range … in line with what Savills charges" + "balances before Savills' fee with a workable surplus" | exact | ✓ |

Verdict fee-clause branches (below / above / one-comparable / none) unit-tested separately via
`_benchmark_fee_clause()` — all six produce correct plain-language output.

`verification/verify.py`: PASS — 24 analysis + 7 deliverable baselines unchanged; new §5c
(`check_benchmark_reconciles`) reconciles all 6 benchmark figures; negative-tested (a broken
`='1. Summary'!H999` ref is caught and named).
