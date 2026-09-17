# Tasks — ramp-occupancy-scaled-lines

Moves headline figures **on purpose**. Money stays in VND with units stated. Reads/writes no
Generation A or B table; no Fact/Dim join-key change. Per `openspec/config.yaml`, task group 5 is
the manual spot-check against a known project's numbers.

## 1. The shared fill-up curve

- [x] 1.1 Create `source_code/fill_curve.py`: `MONTH_ANCHORS`, `monthly_fill_path()` (moved verbatim from `generate_project_output.py`), and `year1_fills()` → the 12 fractions for operational months 1–12 (`0.5 * m / 12`). Verify: `year1_fills()` returns 12 values rising from ~0.042 to 0.50; unit-level sanity asserts pass.
- [x] 1.2 `generate_project_output.py` imports `MONTH_ANCHORS` / `monthly_fill_path` from `fill_curve` and deletes its local `_MONTH_ANCHORS` / `_monthly_fill_path`. Verify: `python verification/verify.py` — all 24 analysis baseline figures still match (the analysis workbook is byte-equivalent in its numbers).

## 2. The month-by-month writer

- [x] 2.1 Add `_write_ramped_row(ws, row, monthly_values, remark)` to `generate_project_budget.py` alongside `_write_even_monthly_row`: `C='Schedule'`, twelve values into `H:S`, `F` cleared, `G=SUM(H:S)` left to the template. Verify: a written row's `H:S` holds the twelve values and Excel's `G` equals their sum after recalculation.
- [x] 2.2 Add `RM.0A` to the row map and its guard: `MGMT_FUND_ROWS['mgmt_fee_developer'] = 23`, `MGMT_FUND_EXPECTED_CODE['mgmt_fee_developer'] = 'RM.0A'`. Verify: the run stops if row 23 is not `RM.0A` on the current template; confirmed `RM.0A` is at row 23.

## 3. Ramp the lines (design D3–D5)

- [x] 3.1 **`RM.AP..RM.KG`** — route the per-product loop in `fill_management_fund_sheet` through `_write_ramped_row`: product month m = (product NFA × product rate) × `resident_fill(m)`. Verify: December value = full monthly fee × 0.50; twelve values sum to the ramped annual; remark states the full-occupancy annual and names the curve sheet.
- [x] 3.2 **`RM.0A`** — write row 23: month m = (Σ full monthly fee over all products) × `(1 − resident_fill(m))`. Verify: `RM.AP..RM.KG + RM.0A` for each month equals the full monthly fee for all units within rounding; `RM.0A` is 0 in a 100%-fill month; remark states units-not-handed-over basis and that it falls as occupancy rises.
- [x] 3.3 **`RPa` / `RP1` / `RP2`** — `parking_fill(m) = min(1, resident_fill(m) × k)`, `k=2` where that vehicle's bays < units else 1; month m = bays × `parking_fill(m)` × monthly rate. Verify: early-month parking revenue is well below the old flat figure; twelve values sum to the ramped annual; remark names `Tiến độ lấp đầy bãi xe` and states the ~2× rule when it applied.
- [x] 3.4 **`EEW` / `EEW.C`** — month m = (annual / 12) × `resident_fill(m)`. Verify: December = full monthly × 0.50; remark states the occupancy basis.
- [x] 3.5 **`EEE` / `EEE.C`** — `elec_fill(m) = max(0.40, min(1, resident_fill(m) / 0.40))`; month m = (annual / 12) × `elec_fill(m)`. Verify: month 1 (fill ~4%) is at 0.40 × full monthly; a month at ≥40% fill is at full monthly; remark states the 40% floor and the QĐ 1279 tariff basis.
- [x] 3.6 Confirm `EED` (diesel), `ESS4` (cleaning), `ESS1` (security), `ESS16` (landscape) and every non-`occupancy_scaled` code are still written flat by `_write_even_monthly_row` / their existing path. Verify: a diff of those rows' `H:S` against a pre-change run shows no change.

## 4. Populate the fill-up sheets (design D6)

- [x] 4.1 Re-read `Tỷ lệ lấp đầy cư dân` and `Tiến độ lấp đầy bãi xe` in the built template; pin the curve-row cells (resident %, motorbike %, car %) and the count cells the pipeline should fill. Record the cell map in this task.
- [x] 4.2 Write the twelve monthly fill-up percentages (and the unit / bay counts the curve rows divide by) into those cells; clear any `#DIV/0!` the cleared example inputs left. Verify: after recalculation the two sheets have zero error cells and their curve rows show the same percentages the budget lines were distributed by.
- [x] 4.3 Confirm no budget total anywhere in the deliverable changed because of 4.2 (the fund/summary sheets do not reference these sheets — proven in change A task 1.3; re-confirm). Verify: recalculated `1. Summary` totals are identical with and without step 4.2.

## 5. Measure and disclose the figure movement

- [x] 5.1 Generate the deliverable for one real project (e.g. Diamond Skyline) before this change and after; record each affected line's year-1 total in VND (`RM` Σ products, `RM.0A`, `RPa`, `RP1`, `RP2`, `EEW.C`, `EEE.C`) and the estimated surplus, both values. Verify: a table exists in `design.md` (new "D3a — measured effect" section) with before/after/delta for every line.
- [x] 5.2 Confirm total management-fee revenue (`RM` + `RM.0A`) is roughly unchanged vs the old flat `RM`, and that the surplus change is fully explained by parking + utilities. Verify: the explanation is in the table's notes.
- [x] 5.3 Manual spot-check sign-off: the project owner reviews the 5.1 table and confirms the movement is expected and acceptable. Verify: sign-off recorded in `docs/05-decisions.md` (D8 section) with the project name, date, and the surplus before/after in VND.

## 6. Verification baseline (design D7 / the `budget-workflow-verification` delta)

- [x] 6.1 Add `verification/baselines/deliverable_baseline.json` — year-1 totals of `RM` (Σ), `RM.0A`, `RPa`, `EEW.C`, `EEE.C` and the deliverable surplus, read from the recalculated deliverable, with units and cell locations.
- [x] 6.2 `checks.py` gains `check_deliverable_figures(paths, baseline=None)`: reads those cells from the generated deliverable, compares to the baseline within tolerance, fails and names any line that differs — including a line that reverted to a flat `Monthly` write. Re-recordable with a stated reason, like the analysis baseline. Verify: forcing one line back to `_write_even_monthly_row` makes `verify.py` fail and name it.
- [x] 6.3 Wire `check_deliverable_figures` into `verify.py`'s run and its section output. Verify: `python verification/verify.py` is green with the new section shown; `openspec validate ramp-occupancy-scaled-lines --strict` reports valid.

## 7. Records

- [x] 7.1 Update `docs/05-decisions.md` D8: mark the ramp built; link the 5.1 measured-effect table and the 5.3 sign-off. Verify: D8 status line updated.
- [x] 7.2 Update `docs/08-guideline-change-family.md`: mark change B done; note the fill-up sheets are now populated and `RM.0A` is live. Verify: the table row for B shows done.
