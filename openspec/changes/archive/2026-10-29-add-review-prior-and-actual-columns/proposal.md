## Why

The Review of an operating project sets the approved budget of the running year (N) beside the tool's budget for the
next year (N+1). A PM who prepares N+1 also needs the trend and the reality: what was approved the year before (N-1),
what was actually spent in N-1 up to when the budget was written, and what N-1 was expected to end at. A budget of
year N is written during N-1, so these are N-1 figures. The user asked (2026-10-26) for these in
the Review, rolling each year (Review for 2027: 2025 and 2026; for 2028: 2026 and 2027).

The Savills form already carries them inside the approved budget file of year N: the fund sheets and the report sheets
(`2.1 Report-Management Fund`, `2.2.1 Report-Common area Fund`) hold columns "Approved budget of Year N-1", "Total
Actual From … to …" and "Expected Report Year N-1". The scan store found and reconciled such columns: 44 of the 53 files
the Review can select have a Management Fund column of the year before that ties to its totals (31 of the 37 files of
2026 carry "Approved budget of Year 2025"). The Review reader ignores them on purpose today. No second file is needed.

## What Changes

- The Review reads, from the file of year N it already reads, three more columns per fund sheet when the file has
  them: **Duyệt N-1** (approved budget of the year before), **Thực tế lũy kế N-1** (actual to date of N-1, with its months),
  **Dự kiến cả năm N-1** (expected full year N-1). Columns are recognised by their own header text, by the scan store's rules,
  and checked for the right year.
- The Excel `Review` sheet shows, per code: Duyệt N-1 | Thực tế lũy kế N-1 | Dự kiến cả năm N-1 | Duyệt N | Công cụ
  N+1, plus three % columns: Duyệt N so Duyệt N-1, Dự kiến N-1 so Duyệt N-1, Duyệt N so Dự kiến N-1. The existing difference
  and % of the tool against Duyệt N stay. Summary block and subtotals carry the same columns.
- The Budget web shows the same figures in the revenue / expense / surplus table and the adjust table.
- (Added 2026-10-27.) The `Review` sheet groups the lines as on the 2027 form, every level nested (EM > EMH > EMH2),
  with a "Cộng <code>" subtotal row (Excel `SUBTOTAL`) above each group and +/- outline to fold it; codes not on the
  form keep their own block with a subtotal. Figures, ties, summaries and the web do not change.
- A column that does not tie to its own R and E rows is shown with a flag and never fails the run. A file without such
  a column leaves it blank with "File không có số …". The actual-to-date column is shown as read with its period and
  month count, never annualised.
- No choice to make on the page and no second file: the columns come with the file.
- No figure of the N+1 budget changes; no baseline moves. A file without any of the three columns gives the same
  Review as today, apart from the blank columns.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `budget-review-workflow`: the reader also returns the N-1 approved, actual-to-date and expected columns of the
  file; the Review sheet, the summaries and the web tables show them. The Kho ngân sách tab (`library-overview`) does
  not change.

## Impact

- Code: `review_import.py` (find and read the three columns on the fund and report sheets), `review.py` (assemble,
  Review sheet, summaries, ties), `webapp/adjust.py` (read Review columns by header), `webapp/results.py` and
  `webapp/static/index.html` (two tables). Tests beside the existing review and webapp tests.
- Data read: only the approved file of year N the Review already reads (its fund and report sheets). Data written: only
  the run folder. No library file is changed.
- Deploy: a [Hub] release of budget-web after the change is verified (release note; not deployed by the session that
  builds it).
- Not in scope: reading a separate N-1 file; using any of these columns in the N+1 generators; the six "Form riêng"
  files; the price table and the store.
