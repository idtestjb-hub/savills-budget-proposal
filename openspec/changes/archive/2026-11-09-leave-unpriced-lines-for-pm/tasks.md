## 1. Kind of each zero line

- [x] 1.1 `_write_zero_reason` takes `kind` ('pm' / 'zero'); 'pm' writes "PM điền: <reason>" and records `_PM_LINES`
  (code, row, A/B, reason); every caller passes its kind per the spec list (no-method loop A except EMO2 = zero;
  EMH1 / ESI1 blank / EMH3 existing-no-duty = B; ESI1 0, ESI2 0, EMH3 new-no-night, contingency 0 % = zero)
- [x] 1.2 `real_budget_ranges` results carry `pm_fill` (no values file, no NFA, < 10 budgets = True; pool, tower,
  in-house, lump = False); `_write_real_budget_range_lines` passes it and types no 0 on PM lines
- [x] 1.3 `fill_common_area_fund_sheet` leads with "PM điền" or "Để ở mức 0" from the map; tests for both
- [x] 1.4 Run log records the PM lines (code, kind)

## 2. Blank, shaded cells

- [x] 2.1 PM lines: F and H–S hold no typed number; fill FFF2CC and number format `#,##0;-#,##0;;@` on F and H–S
- [x] 2.2 Test on a generated sample: no #VALUE!/#REF! on the rows or `1. Summary` after Excel recalculation

## 3. Sheet 4 rows on every run

- [x] 3.1 Move `review.add_zero_rows` to `budget_adjustment.add_lumped_rows(deliverable, rows, mark)`; hidden helper
  column for mark + reason; detail unit price empty, type "Nhập số"
- [x] 3.2 Generation step of every run adds the PM rows; Review adds the other approved zero-tool codes, one row per code
- [x] 3.3 Excel test: typing 24,000,000 VND on ESM6's detail cell gives 2,000,000 VND per month and the Summary follows
- [x] 3.4 Older sheets: no column added by `upgrade()` (design risk note); the web reads a missing mark as no PM line; test

## 4. Web adjust table

- [x] 4.1 `webapp/adjust.py` reads mark/reason; PM lines never hidden by "Mã công cụ ra 0"
- [x] 4.2 `index.html`: "PM điền" badge + reason tooltip, empty "Thành tiền gốc", toolbar "N dòng chờ PM điền" and filter
- [x] 4.3 Saving a figure rewrites the fund remark to "Số do PM nhập: … Công cụ không tính được: …"; clearing restores
  "PM điền: …"; web tests
- [x] 4.4 Browser check on a new-project run and a Review run

## 5. Analysis and verification

- [x] 5.1 Analysis block "Dòng chờ PM điền" (code, item, kind, reason, count)
- [x] 5.2 `checks.check_pm_lines` + verify.py wiring for the standard, existing and operating samples; failure test
  (a typed 0 is caught)
- [x] 5.3 Update remark/wording checks that expected "Để ở mức 0" on A/B codes; client-facing scan accepts "PM điền"

## 6. Measure, docs, sign-off

- [x] 6.1 Before/after on the 5 fixtures and the CITY GARDEN Review run: figures equal to the VND, list of cells and
  remarks that changed; summary in `Savills-local\backups\budget-agent\<date>-pm-filled-lines-measure`
- [x] 6.2 Re-record baselines only where cells changed from 0 to blank; tests + verify.py PASS
- [x] 6.3 docs/32 (sheet 4 PM rows), webapp README, RUNNING.md note; project-status
- [x] 6.4 PM sign-off on the before/after (signed off by the user on behalf of the PM, 2026-11-09; ESR has its sheet-4 row)
