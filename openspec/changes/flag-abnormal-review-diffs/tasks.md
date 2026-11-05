## 1. Rule and Review outputs

- [x] 1.1 `review.py`: `ABNORMAL_PCT`, `ABNORMAL_VND`, `LABEL_ABNORMAL`, `ABNORMAL_FILL`, `is_abnormal(diff, pct)`; `assemble()` sets `abnormal` on each row and `counts['abnormal']`; `summary_json()` adds `abnormal` and `abnormal_rule`; `summary_md()` and the sheet's row 3 state the count; row 2 names the rule
- [x] 1.2 `build_review_sheet()`: fill the "Chênh" and "%" cells of an abnormal line, open its remark with "BẤT THƯỜNG"
- [x] 1.3 Tests `tests/test_review_sheet.py`: the rule's four cases (both over, % only, VND only, no approved figure); assembled rows and counts; the sheet's fill and remark; the JSON list

## 2. Web data

- [x] 2.1 `webapp/adjust.py`: `abnormal_keys(workdir)` (list from the summary file, `None` when the file predates the rule); `flag_abnormal(items)` fallback with `review.is_abnormal`
- [x] 2.2 `webapp/server.py`: `abnormal_keys` and `abnormal_rule` in `GET /api/runs/<id>/adjust`
- [x] 2.3 Tests `tests/test_webapp_adjust.py`: keys from the summary file; fallback on an old run; the GET carries both fields

## 3. Web page

- [x] 3.1 `webapp/static/index.html`: button "Mã công cụ ra 0" (default hidden except abnormal; hidden count; shown only when zero rows exist), checkbox "Chỉ dòng bất thường", tag "Bất thường" and filled cells on the adjust table, count on the THU / CHI rows, count in the Review counts line, tag on "10 dòng lệch lớn nhất", guide text with the thresholds
- [x] 3.2 Look at the table in the browser pane on an invented Review run: default view short, button shows the rows, filter leaves only the flagged lines, tags readable in light and dark theme

## 4. Docs, measurement and verify

- [x] 4.1 `webapp/README.md` (bảng điều chỉnh), `docs/32` section 3, `docs/project-status.md`
- [x] 4.2 (measured, see design.md; thresholds 20% / 50 triệu confirmed by the user 05/11/2026) Measure on CITY GARDEN (read-only Review run in `C:\ZWork`, scope statement first): lines flagged by fund and by kind, flagged top-10 codes, zero rows hidden by default; write to design.md "Measured"; the user confirms the thresholds (or picks new ones)
- [x] 4.3 (05/11: 1351 passed + 1 xfailed; verify.py PASS) `python verification/verify.py` from `Budget_Agent/source_code/` passes; full test run passes
