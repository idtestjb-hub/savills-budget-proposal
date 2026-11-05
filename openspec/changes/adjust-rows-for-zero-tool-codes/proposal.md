## Why

On the Review page the PM reads the "10 dòng lệch lớn nhất" and then looks for those codes on the adjustment table
to fix them, and cannot find most of them (user, 2026-11-05). Measured on the CITY GARDEN review run of 2026-10-20:
6 of the 10 largest differences are codes the tool priced at 0 ("Chưa có phương pháp", "Công cụ ra 0"), and sheet
`4. Điều chỉnh` has no row for a fund line whose twelve months sum to zero (`adjustment_detail._parents`, line 105),
so the web table, which reads that sheet, cannot show them. The table also lists codes in form order with a
"Chênh lệch" column that means new-vs-original (0 until edited), not tool-vs-approved, so even a code that is on the
table does not stand out as a large difference. Two sections above the table (approved vs tool, the ties) take a
screen each before the table starts.

## What Changes

User's choice on 2026-11-05: add rows with a new type "Nhập số"; add the difference column and sorting; add
expand/collapse buttons.

- **A row for every code the approved budget prices and the tool leaves at 0.** After a Review generates the
  deliverable, every on-form code with an approved figure and a tool figure of 0 gets a total row on sheet
  `4. Điều chỉnh` with one lumped detail row (quantity 1, original amount 0) and the fund row's month cells linked to
  it. The row's "Thành tiền gốc" is 0 and its "Duyệt" column shows the approved figure.
- **New adjustment type "Nhập số".** The PM types the new annual amount in the detail row's yellow cell; the new
  amount is that figure; the fund sheet spreads it evenly over the twelve months (the only case where the
  new / original ratio cannot be used). Available on every code that has detail rows; the natural choice for the
  zero rows. The dropdown, the Excel formula, the web preview and the web validation agree.
- **The web table shows "Chênh so với duyệt"** (tool's figure minus approved, VND and %) beside "Duyệt" on Review
  runs, and offers sorting by that column (largest absolute difference first) besides the form order; the 10 codes of
  the Review's top list are marked. Group subtotals keep working in both orders.
- **Expand/collapse** on the Review result sections "Ngân sách đã duyệt so với ngân sách năm mới" and "Đối chiếu
  tổng": a button on each heading folds the section to its heading; both start open; the state is remembered in the
  browser.

## Capabilities

### New Capabilities
- `budget-web-review-results`: the Review result sections on the page and their folding.

### Modified Capabilities
- `budget-adjustment-sheet`: the "Nhập số" type; rows for zero-tool codes after a Review.
- `budget-web-adjust-table`: the "Chênh so với duyệt" column, sorting by difference, marking of the top-10 codes.

## Impact

- Changed: `budget_adjustment.py` (type, detail formula branch, month link for a zero original), `review.py` (add the
  zero rows after the generators, before Excel recalculates), `webapp/adjust.py` (read/validate/write the type),
  `webapp/static/index.html` (column, sort, marks, fold buttons), `webapp/README.md`, docs/32.
- Reads: nothing new. Writes: the deliverable's sheet `4. Điều chỉnh` and the linked fund rows, only on Review runs.
- Figures: a zero row left untouched keeps every month at 0, so no recorded baseline figure moves; the before/after
  check on one Review run is a task. The deliverable's cell count on sheet 4 grows by the number of zero rows.
- Sheet Review in the analysis still compares the tool's figures before adjustment, as today.
