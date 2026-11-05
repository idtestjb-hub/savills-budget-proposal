## 1. Sheet 4: type "Nhập số" and the zero-original month link

- [ ] 1.1 `budget_adjustment.py`: `ADJUSTMENT_TYPES` + `TYPE_ENTER = 'Nhập số'`; `detail_formula` branch `IF(D="Nhập số", K, ...)`; `month_formula` with the zero-original split (D4); dropdown list updated
- [ ] 1.2 `budget_adjustment.append_items(wb, items)` (D2): rows after the last, validation range extended, fund rows linked, protection kept
- [ ] 1.3 Tests `tests/test_budget_adjustment.py`: formula text of the new branch; month formula on a zero original; `append_items` on a built workbook keeps the earlier rows and links the new fund row; new-project `apply()` output unchanged (row count and formulas)

## 2. Review adds the zero rows

- [ ] 2.1 `review.py`: `zero_tool_rows(prior_lines, tool, tcodes)` and `add_zero_rows(deliverable, rows, log)` called after [3/4] and before `recalc_copy` (D1); artifact strip after save; run-log lines "thêm N dòng Nhập số trên sheet 4: ..." and the skipped codes
- [ ] 2.2 Tests `tests/test_review*.py`: a recorded Review fixture with two zero-tool codes gets two rows and linked months; a code missing from column Y is logged and skipped; `counts` and `top` unchanged
- [ ] 2.3 Measure on one Review run (CITY GARDEN or the user's pick): R / E of both funds before and after this change identical with no edit (Excel), ties still 8/8 as before; record in design.md "Measured"

## 3. Web adjust table

- [ ] 3.1 `webapp/adjust.py`: `TYPES` + 'Nhập số'; `read_items` → `zero_row`; `new_amount`, `_validate`, `apply_edits` for the type (K per row); `approved_by_key` unchanged
- [ ] 3.2 `webapp/static/index.html`: column "Chênh so với duyệt" (+ %) on Review runs; sort control "Thứ tự" (form | lệch lớn nhất) with group handling (D5); "Top 10" mark from `summary.top`; "Nhập số" in the type list; cell label "Số nhập (VND/năm)"; preview
- [ ] 3.3 Tests `tests/test_webapp_adjust.py`: read a sheet with a zero row; preview and validation of "Nhập số"; save writes D and K only; a negative figure is refused

## 4. Result sections fold

- [ ] 4.1 `webapp/static/index.html`: fold buttons on the two headings, `localStorage` keys, default open (D6)
- [ ] 4.2 Check at 1280 px and 400 px wide: folded headings keep their text; the adjust table box is unaffected

## 5. Docs and verify

- [ ] 5.1 `webapp/README.md` (bảng điều chỉnh: cột lệch, thứ tự, Nhập số, dòng công cụ ra 0), guide tab text, `docs/32` section 3, `docs/project-status.md`
- [ ] 5.2 `python verification/verify.py` from `Budget_Agent/source_code/` passes; full test run passes; sign-off by the user on the measured run (2.3)
