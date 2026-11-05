## Context

`adjustment_detail.collect()` builds the sheet-4 items inside `build_budget()` from the fund lines the generator
wrote; `_parents()` skips a line whose months sum below 1. `budget_adjustment.apply()` writes the sheet and turns the
fund row's month cells into `original month × ratio`, where `ratio_formula` returns 1 when the original is 0 (so a
zero line can never move). `review.run()` runs the generators at step [3/4], then at [4/4] recalculates a copy with
Excel and assembles `data['rows_by']`, which already knows, per fund and section, every code's approved figure and
tool figure (`tool_num`), its label and whether it is on the form. `webapp/adjust.read_items()` reads the sheet by
scanning total rows; `apply_edits()` writes D, L, J, K. The web table gets the approved figure per code from the
analysis's Review sheet (`approved_by_key`).

## Goals / Non-Goals

**Goals:** every code with an approved figure can be adjusted on the web and in Excel; the largest differences are
visible on the table without the PM cross-reading the top list; the two result sections fold.

**Non-Goals:** pricing the "Chưa có phương pháp" codes (that stays per-code work); adding zero rows on a new-project
run (no approved figure exists); changing the Review sheet; changing which codes the top list holds.

## Decisions

**D1. Zero rows are added in `review.run()`, not in the generator.** (Applied 2026-11-05 after the recalculation, not
before it: `review.zero_tool_rows(data)` takes the rows of `assemble()` (tool figure measured by Excel) and
`review.add_zero_rows(deliverable, rows)` appends them right after `assemble`, so the choice of codes uses the real tool
figure instead of a guess from the un-recalculated workbook. The added lines are 0 untouched, so the recalculated copy
the Review sheet was built from stays valid; the measured run below recalculates the final deliverable to prove it.
The description below is the original plan.) The generator does not know the approved
figures. After [3/4], before `recalc_copy`, `review.add_zero_rows(deliverable, data_rows)` opens the deliverable with
openpyxl, builds the items `{code, sheet, name_vi, freq, months: [0]*12, annual: 0, subs: [lumped row qty 1, price 0,
amount 0, qty locked]}` for each on-form row with `abs(approved) >= 0.5` and `abs(tool_num) < 0.5` whose code is
found in column Y of its fund sheet (`find_fund_row`; a code not found is reported in the run log and skipped), then
calls `budget_adjustment.append_items(wb, items)` and saves. `rows_by` is therefore assembled from the recalculated
copy as today, but the row list needed for the zero rows is computed first from `prior_lines` and `tool_lines` of
the un-recalculated deliverable (the tool figure of a zero line is 0 either way). The OneDrive artifact strip
helpers of `generate_project_output.py` are applied after the save, as for every workbook written here.

**D2. `append_items(wb, items)`** adds total and detail rows after the sheet's last row, in the fund sheet's row order
within the appended block, and links each fund row; the data validation range is extended; protection and outline
settings are kept. `build_sheet()` is untouched (it rebuilds from scratch for a new-project run).

**D3. Type "Nhập số".** `ADJUSTMENT_TYPES` gains `'Nhập số'` (fifth item, dropdown order kept). Detail formula branch:
`IF(D="Nhập số", K, ...)` where K ("Đơn giá mới") holds the typed annual amount; the web labels that cell "Số nhập
(VND/năm)" when the type is "Nhập số". On a code with several detail rows the figure is per row, as the other
types. Locked-quantity rows are not affected (K is always editable).

**D4. Month link for a zero original.** `month_formula` becomes `=IF('4'!$I$p=0, '4'!$M$p/12, '4'!$S..$p*ratio)`:
when the original annual is 0 the fund row's month = new amount / 12, else as today. For an Annual-frequency row the
template's month columns stay the twelve-way split (the fund row's own column F formula follows the months, as
every linked row today). `wrapped_formula` (rows with an existing formula) is unchanged: such rows never have a zero
original.

**D5. Web.** `read_items()` returns `adj_type` 'Nhập số' and `zero_row=True` when `amount == 0 and has_subs`;
`new_amount()` and `_validate()` treat 'Nhập số' as K per row (not negative). The table's "Chênh so với duyệt" =
`amount − approved` and `%` on `approved` (N/A when approved is 0), only when `approved_by_key` returned figures.
Sort control "Thứ tự: form 2027 | lệch lớn nhất"; in the second order groups are kept but their codes sort by
`|diff|` descending and groups by their largest member. Codes in `summary.top` get a mark "Top 10" beside the code.

**D6. Folding.** The two `<section>`s get a button `▾ / ▸` on the `<h2>`; state in `localStorage` keys
`rv-fold-sum`, `rv-fold-ties`; default open. The 10-largest table and the notes keep their current `.dg-wrap` boxes.

## Risks / Trade-offs

- Openpyxl re-saves the deliverable once more on Review runs (already done for the analysis); the artifact strip
  helpers cover the known OneDrive traps.
- A "Nhập số" figure spread over twelve equal months may not match the approved budget's own timing; the fund row's
  remark names the spread. The PM can instead type month figures in Excel as before.
- Older deliverables without the type: `upgrade_sheet` already rewrites column M and the dropdown on save; the new
  branch rides on that path, so no separate migration.

## Measured (2026-11-05, task 2.3)

Review of CITY GARDEN (`Budget 2026 City Garden_rv5_05.12.2025.xlsx`, store id dcdac7ae4a81; MF 411 and CA 373 lines
read, budget 2026, new year 2027), run in a work folder outside the library with the code of this change. Exit 0, ties
8 of 8. The run added **102 "Nhập số" lines** to sheet 4 (sheet 4 has 138 total rows, 36 before); 0 skipped.
Excel recalculation of the deliverable before and after the lines were added:

| | before | after |
|---|---:|---:|
| MF R | 39,598,242,982.74 | 39,598,242,982.74 |
| MF E | 36,236,851,099.00 | 36,236,851,099.00 |
| CA R | 47,636,364.00 | 47,636,364.00 |
| CA E | 43,211,326.74 | 43,211,326.74 |

No line of either fund sheet moved (409 and 371 lines compared), no error cell in the recalculated workbook. Nine of
the ten codes of the Review's top list are now on the web table (ESS38, RM.AP, RO15, EEW.AA, EEW.A, RR8, EMH1, ESS16,
ESI1); RI1 (tool 43.2 triệu, a figure read from another sheet) stays off sheet 4 as before.
