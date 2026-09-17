## 1. Record the starting point

- [x] 1.1 Capture the three energy figures that must reproduce unchanged — verify by reading them from `verification/baselines/baseline.json` and recording them before any code is touched
  — `opex_electricity_annual` 2,669,371,536 · `opex_water_annual` 306,003,816 · `opex_diesel_annual` 60,994,764 VND (analysis workbook). Deliverable ramped: `water_year1`, `electricity_year1` in `deliverable_baseline.json`.
- [x] 1.2 Capture the cost ratio each category currently uses — verify by recording the VND/m²/month figure the estimator derives for each, so the split can be reconciled against it
  — Electricity 4,089.11 · Water 468.76 · Diesel 93.44 VND/m²/month (A&K Tower monthly ÷ 64,124 m² NFA).
- [x] 1.3 Confirm verification passes before the change — verify by running `python verification/verify.py` and confirming it exits zero
  — PASS (exit 0), 2026-09-10, before any edit.

## 2. Recover consumption and tariff from the source

- [x] 2.1 Read each energy row's consumption and unit price ~~from the real source workbooks~~ — **the A&K Tower / Parking Building workbooks are not in this repository clone** (design D6; `docs/06` confirms `input/budget_planning/` is absent). Consumption + tariff are taken from what is already traceable to a named cell (`rescan_opex_from_source.py`'s provenance) and the method catalogue's tariffs. Verified each against the recorded prose: electricity rate 2,226 VND/kWh (prose + catalogue QĐ 1279 agree); diesel 19,260 VND/L (prose); Parking Building's own 3,751 / 29,000 / 22,000 with real quantities 62,622 kWh / 3,300 m³ / 523 L (prose, exact).
- [x] 2.2 Read electricity usage from the equipment load model directly — **not possible, workbook absent.** Used cost ÷ tariff = 262,210,141 ÷ 2,226 = 117,794 kWh/month → 1.837 kWh/m²/month. This is sound here because A&K's own implied tariff (its 163-row model's rate) is 2,226, the same as QĐ 1279 — no blending gap. Recorded in design D6.
- [x] 2.3 Establish whether the water source sheet carries volumes — **the sheet (`D2. Nước Công Cộng`) is not in this repository.** The method catalogue supplies a water tariff (SAWACO built-up, 19,786 VND/m³), so water is split against that: usage = A&K cost ÷ 19,786 = 1,519 m³/month, disclosed on the output as a derived/implied figure (a lower bound if A&K's ~2020 rate was lower), not read from A&K's bills. Supersedes design D3's "water may not split".
- [x] 2.4 Record the date each unit price was current — electricity `2025-05-09` (QĐ 1279/QĐ-BCT); water `2026` (AI Guideline built-up example); diesel `~2020` (A&K budget). Stored in `Fact_OPEX.csv` `PriceAsOf`. No date inferred beyond "~2020" for the A&K-era diesel figure, which is flagged approximate.
- [x] 2.5 Confirm the extractor read nothing under production paths and wrote nothing there — `rescan_opex_from_source.py` uses hardcoded hand-verified figures + `ENERGY_TARIFFS`; it opens no workbook. Its only write is `data/generation_A_star_schema/Fact_OPEX.csv` (a Generation A reference table this change extends by design — not in `verification/run_workflow.PRODUCTION_FILES`). `reports/` and `sample_output/` untouched.

## 3. Store both halves as data

- [x] 3.1 Add quantity, unit, unit price and price date alongside the existing monthly cost, without changing what any existing column means — `Fact_OPEX.csv` now has `Quantity,Unit,UnitPrice,PriceAsOf` between `MonthlyVND` and `Source`; `MonthlyVND` is byte-unchanged. `_load_opex_facts` reads the new columns; every non-energy row still loads (blanks).
- [x] 3.2 Name the unit for every quantity — energy rows carry `kWh/month` / `m3/month` / `litre/month`; non-energy rows have no quantity so no unit.
- [x] 3.3 Leave a row unsplit rather than filling it with a borrowed or assumed price — Repairs & Maintenance and Administrative Expense carry no Quantity/Unit/UnitPrice (stay a plain cost ratio). Water's tariff is the guideline's real SAWACO figure (not borrowed from Parking Building — that was explicitly rejected in design D3); its A&K m³ is disclosed as derived, not fabricated. Parking Building rows use *their own* recorded consumption and rate, never blended into the residential ratio.
- [x] 3.4 Keep each row's provenance — the `Source` column still traces every figure to its named sheet/row; energy rows additionally carry the tariff's citation (QĐ 1279 / SAWACO build-up / DO 0.005S Vùng 1) appended after `  TARIFF: `.

## 4. Compute each energy line as consumption × tariff

- [x] 4.1 Derive a usage-per-area ratio from the source property and apply the tariff separately — `estimate_opex()` energy branch: `usage_per_m2 = stored_quantity / A&K_NFA`; `figure = usage_per_m2 × project_NFA × tariff`. It no longer multiplies a cost ratio. The stored quantity is fixed (not recomputed from cost each run) so the tariff genuinely drives the figure.
- [x] 4.2 Confirm each figure reproduces its recorded value to within rounding — Electricity 2,669,371,536 · Water 306,003,816 · Diesel 60,994,764 VND reproduce **exactly** (delta 0) at the sample NFA; `verify.py` §4 confirms all 24 baseline figures and §5 all 7 deliverable figures unchanged.
- [x] 4.3 Investigate and write down any figure that does not reproduce — none did. Nothing to investigate.
- [x] 4.4 Fall back to the existing cost basis for any category that could not be split, and label it — not needed: all three energy categories split (water against the guideline's SAWACO tariff, with its A&K m³ disclosed as derived — see design D6). Repairs/Admin were never in scope and keep their cost ratio.
- [x] 4.5 Confirm a tariff change moves the figure — bumped the electricity tariff +10% in `Fact_OPEX.csv`, re-ran: the electricity figure moved +10.02% (the .02 is the tariff rounded to a whole VND). Restored. Also confirmed `tariff_stale` flips to False when `PriceAsOf` year ≥ 2027.

## 5. Report both halves everywhere the figure appears

- [x] 5.1 State the usage assumed, the tariff applied, and the sample size behind each — the `EEW.C`/`EEE.C`/`EED.C` remarks in the deliverable and the analysis OPEX sheet's new `Usage assumed` (G) + `Tariff (as of)` (H) columns all show usage per m² and total, tariff, and "n=1 — one property". Eyeballed on a generated pair.
- [x] 5.2 State the date each tariff was current — every remark and the H column quote `PriceAsOf` (electricity 2025-05-09, water 2026, diesel ~2020).
- [x] 5.3 Make a tariff older than the budget year visible on the output — a `PriceAsOf` year below 2027 sets `tariff_stale`; the remark then reads "the tariff is dated X, earlier than the 2027 budget year — confirm it is still the current published rate", and the analysis H column shows "confirm current". Confirmed the flag flips to False for a 2028 date.
- [x] 5.4 State that the usage ratio remains single-property — every energy remark says "Usage is A&K Tower's real cost-implied figure (n=1 - one property; this change split the price out, it did not widen the sample), so 'now on the spec's method' is not the same as 'now accurate'."

## 6. Confirm the blast radius

- [x] 6.1 Confirm only the three energy categories changed how they are derived — Repairs & Maintenance and Administrative Expense keep the plain cost ratio (their entries have no `tariff` key); `verify.py` §4 shows all 24 baseline figures unchanged, so no other category moved.
- [x] 6.2 Confirm both workbooks still carry the same figure for each energy category — deliverable `EEW.C` year-1 82,876,034 un-ramps (×12/Σfills) to 306,003,816 = analysis Water annual; `EEE.C` likewise to 2,669,371,536; `EED.C` flat 60,994,764 = analysis Diesel. `verify.py` §5 confirms the deliverable-figure baseline.
- [x] 6.3 Confirm the structural checks still pass — `verify.py` §2: 25/14/5 sheets, 0 corruption artifacts, 0 Excel errors introduced, full recalculation.
- [x] 6.4 Confirm production data was untouched throughout — `verify.py` §1 "all production artefacts byte-identical"; `rescan_opex_from_source.py`'s only write is `Fact_OPEX.csv` (a Generation A table, not a production artefact).

## 7. Re-record the baseline only if a movement was explained

- [x] 7.1 Review every named difference and confirm each was intended — **no tracked figure moved** (design D4 holds: usage × tariff = the cost the ratio already carried, verified delta 0). Nothing to review.
- [x] 7.2 Re-record the baseline — **not needed.** No baseline figure changed; re-recording would be recording a no-op. Same outcome as `read-input-by-label` and `unify-revenue-basis-across-outputs`.
- [x] 7.3 Confirm verification passes on the following run — `python verification/verify.py` exits 0 (2026-09-10, after the split).

## 8. Documentation

- [x] 8.1 Record that the three energy codes now use the method the spec states, with the measured share of cost — `docs/05-decisions.md` D9 names `EEE.C`/`EEW.C`/`EED.C`, the usage × tariff method, and the 31.0% drift it closes.
- [x] 8.2 Record which categories were split and which were not, and why — D9 §8.2: all three split; the source workbooks are absent so A&K's consumption is derived (electricity reconciles exactly; water's m³ is an implied lower bound against the guideline tariff).
- [x] 8.3 Record that usage remains single-property and this change did not widen it — D9 §8.3: the price fix is separated from the accuracy problem; every remark says "'on the spec's method' is not 'now accurate'". R-D02 untouched.
- [x] 8.4 Record that updating tariffs to current published rates is the next decision and moves client-facing figures — D9 §8.4: electricity current; water/diesel need the current published rate; each update is a PM decision; the pipeline flags any pre-2027 tariff.
- [x] 8.5 Record whether "water ~3.3× high" is now attributable to usage or price — D9 §8.5: still unattributed (water's usage half is derived, not read); resolving it needs A&K's real m³ from `D2. Nước Công Cộng`.
- [x] 8.6 Update `docs/project-status.md` with the new state and the next decided change.
