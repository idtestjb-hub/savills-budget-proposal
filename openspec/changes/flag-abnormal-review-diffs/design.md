## Context

`review.assemble()` builds every compared line as a dict with `approved`, `converted`, `tool_num`, `diff`, `pct`,
`label`, `remark`, `on_form`; `build_review_sheet()` writes them with `_put()`; `summary_json()` / `summary_md()` write the
run's summary files; `run()` logs. On the web, `GET /api/runs/<id>/adjust` (`webapp/server.py`) returns the sheet-4
items with `approved` (from the analysis's Review sheet via `adjust.review_columns`) and `top_keys` (from
`review_summary.json`); `index.html` filters rows in `visible()`, renders them in `renderAdjust()` and marks the top-10
codes with `topKeys()`. Items carry `zero_row` (change `adjust-rows-for-zero-tool-codes`).

## Goals / Non-Goals

**Goals:** one rule, applied once in `review.py`, visible in the analysis workbook, the summary files, the Review page and
the adjust table; the adjust table opens short by default without hiding anything flagged.

**Non-Goals:** per-code or per-project thresholds; changing the top-10 list; flagging on new-project runs (no approved
figure); hiding rows in the Excel sheet 4; pricing the zero-tool codes.

## Decisions

**D1. The rule lives in `review.py` and the flag travels with the data.** `ABNORMAL_PCT = 0.20`, `ABNORMAL_VND =
50_000_000.0`, `is_abnormal(diff, pct)` = `abs(diff) >= ABNORMAL_VND and (pct is None or abs(pct) >= ABNORMAL_PCT)`.
`assemble()` sets `row['abnormal']`; `counts['abnormal']` counts them; `summary_json()` adds `abnormal: [{fund, code,
diff, pct}]` and `abnormal_rule: {pct, vnd}`. The web reads the list (`adjust.abnormal_keys(workdir)`, like `top_keys`),
so the page and the sheet always agree.

**D2. Old runs fall back to the same rule on the table's own figures.** When `review_summary.json` has no `abnormal`
key, `adjust.abnormal_keys()` returns `None` and the server computes the set from each item's `amount - approved` with
`review.is_abnormal` (items with a known approved figure only, so codes without a Review line are never flagged). The
response carries `abnormal_rule` in both cases so the page can print the thresholds.

**D3. Review sheet: fill, not a column.** Adding a column would move the header positions `adjust.review_columns` and
older readers scan by name (they would still work) but would also change the sheet the PM team knows. Instead the
"Chênh" and "%" cells (columns 10 and 11) of an abnormal line get `ABNORMAL_FILL` (`FCE4D6`) and the remark starts with
`LABEL_ABNORMAL` ("BẤT THƯỜNG"), so an Excel filter on the "Ghi chú" column or on colour finds them. Row 3 adds
"bất thường (≥20% và ≥50 triệu/năm): n"; row 2 names the rule.

**D4. Default view of the adjust table.** `visible(it)` hides an item when `it.zero_row && !adj.showZero &&
!abnormal(it)`. `adj.showZero` starts `false` on every open (the user asked for hidden by default; it is not stored in
`localStorage`, unlike the column toggles, so the table always opens short). The button text shows the hidden count:
"Mã công cụ ra 0 (n đang ẩn)" / "Ẩn mã công cụ ra 0". The button is hidden when no item has `zero_row`. Group subtotals
keep summing the visible rows, as today, so the THU / CHI header rows state "… · k mã công cụ ra 0 đang ẩn" to make the
omission explicit.

**D5. Filter "Chỉ dòng bất thường"** is a checkbox beside "Chỉ mã đã điều chỉnh"; both can be on. It is hidden on
new-project runs with the other approved-only controls.

**D6. Tag and cells.** `<span class="abn">Bất thường</span>` after the code (before "Top 10"), class `abn-cell` on the
two difference cells; the "10 dòng lệch lớn nhất" table shows the same tag after the code. Colours come from the
Savills palette variables already in the page (`--sav-neg` for text, a light tint for fills), with a dark-theme variant.

## Risks / Trade-offs

- The adjust table's `amount` (sum of sheet-4 detail rows) and the Review's `tool_num` (fund line after Excel
  recalculation) differ by rounding on a few codes; a line at the exact threshold could be flagged in one place and not
  the other on an old run that uses D2. New runs use the list from the summary file, so they agree.
- 102 zero rows hidden means the group "Duyệt" sums shrink by their approved figures; D4 states the hidden count on the
  header rows and the button shows it, and the Review sheet and summary are unaffected.

## Measured (2026-11-05, task 4.2)

Review of CITY GARDEN (`Budget 2026 City Garden_rv5_05.12.2025.xlsx`, the copy packed in the site package = store id
dcdac7ae4a81; facts from the package's `site.json`), read-only run in a work folder outside the library with this
change's code. Exit 0, ties 8 of 8 (and the 10 N-1 reference ties). The run added 100 "Nhập số" lines (P20 measured 102
on the same file with other facts; the tool's figures differ slightly, MF R 39,598.7 vs 39,598.2 triệu VND).

| | count |
|---|---:|
| Compared lines (Review sheet) | 196 |
| Flagged abnormal (≥20% and ≥50 triệu VND/năm) | **82** (MF 69, CA 13) |
| … by size of the difference | ≥1 tỷ: 9 · 100 triệu–1 tỷ: 42 · 50–100 triệu: 31 |
| Top 10 flagged | 9 of 10 (RM.AP −7.4% is the one not flagged) |
| Codes on the adjust table | 138 = 100 zero rows + 38 priced |
| Flagged codes on the table | 73 = 58 zero rows + 15 priced (MF R 13, MF E 52, CA R 6, CA E 2) |
| Zero rows hidden by default | **42** (table opens with 96 codes instead of 138) |
| Flagged lines with no sheet-4 row | 9: EM#, ES#, EE# (contingency), RI1 (own sheet), CA EEE.C / EMH2 / ESS1 / ESS4 / RO2a (formula shares) |

The fallback rule (D2, table figures) and the summary-file list agree on every code of this run. The 58 flagged zero
rows are the approved codes above 50 triệu VND/năm that the tool has no method for: they stay visible by default, which
is what the user asked for ("ẩn, trừ dòng bất thường"). The user confirms the thresholds (tasks.md 4.2) before archive.
