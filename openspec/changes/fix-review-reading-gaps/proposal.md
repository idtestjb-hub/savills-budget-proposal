## Why

Old reading gaps of the Review, open since sessions P13–P16 and measured again on 2026-10-29:

- **Month columns.** The search for the twelve months takes the first column to the right of the year column whose
  header rows (8–14) hold a `mm/yyyy` text, and stops at the first column after it without one. On store file
  `af4d13e79552` a Remarks cell in those rows ("… 12/2025") is taken as the only month, so the twelve real months
  01–12/2026 two columns further right are missed; the MF fund reads as 2025 with "1 cột tháng thay vì 12".
- **Stale template range.** 63 approved columns in the store have headers like "Approved budget of Year 2025 (From
  01.2023 to 12.2023)": the range left from an older template wins over the year the PM wrote, so the column is
  read as 2023 and dropped as not N-1.
- **Error cell as remark.** A remark cell that is an Excel error in the source (`#REF!`, seen on EN1) is copied as
  text `#REF!`; openpyxl writes it back as an error cell, the only error cell on the Review sheet.
- **Files the Review cannot read are still selectable.** Sycamore (21 months: two MF sheets "(N1) 100%" and
  "(9TN2) 100%") stops with "sheet '2.1. Staff cost From Savills': no column of budget codes found" because the
  sheet-name rule takes a staff-cost sheet as the Management Fund; "(1) Ngân sách đính kèm HĐ" (Phase 01, no R/E rows)
  stops at the R/E rows. A PM picks them and only learns it after the run.
- Rerun on 2026-10-29: of the three 2026 files that stopped on 26/10, A&K (`2020f361796c`) now completes (P17 fixes;
  the city must be entered); the other two are the multi-phase files above.

## What Changes

User's choices on 2026-10-29 (all recommended options):

- **Months**: the twelve months are the first run of twelve consecutive columns (right of the year column, within
  40 columns) whose header is a month; when no run reaches twelve, the longest run, flagged as today.
- **Approved / expected column with a full-year range of another year**: when the header states a year and its range
  is exactly 01–12 of a different single year, the stated year wins (how `header_year_over_range`), and the Review
  note of the chosen column says the range is old template text.
- **Remark that is an Excel error**: written as text "(ghi chú trong file gốc là ô lỗi #REF!)" (the error code as found).
- **Unreadable files**: a store file whose `prior_coverage.csv` row has status `error` (the Review reader cannot read
  it) is not selectable on the Review tab, reason "Review chưa đọc được file này (sheet quỹ quản lý khác form chuẩn,
  ví dụ ngân sách nhiều giai đoạn)", kind `review_unread`. `build_prior_coverage.py` keeps measuring over the files
  selectable before this rule, so the flag does not switch itself off at the next build.
- The sheet-name rule no longer takes a staff-cost, night-shift or break-even sheet ("staff cost", "ca đêm", "hv",
  "hòa vốn") as a Management Fund budget sheet. Sycamore then stops at another sheet the old rule takes ("2.3.2. Lịch
  Lễ tân", any name starting with "2"), so it stays unreadable and is marked not selectable; the name rule itself is
  not widened here.
- Also in this change (already made, small): `open_workbook` releases the source file when it has to read the
  repaired copy (it stayed locked until garbage collection; test added); the two summary tables of the adjust page
  (`#adj-prev`, `#adj-res-t`) scroll sideways in their own box instead of overflowing at 400 px.

## Capabilities

### New Capabilities

### Modified Capabilities
- `budget-review-workflow`: month run, stale range, error remark, staff-cost sheet.
- `library-overview`: files the Review reader cannot read are not selectable.

## Impact

- `review_import.py` (month run, error remark, sheet rule, `_load_read_only`), `review_measures.py`
  (`parse_period`), `webapp/library.py` (coverage-based reason), `build_prior_coverage.py`, `webapp/static/index.html`.
- `parse_period` is shared with the scan store (`scan_budgets_v2`): the store is not rebuilt in this change;
  `prior_coverage.csv` is rebuilt and copied to `_kho_quet` (counts reported before and after).
- Review figures change only on files that hit one of the gaps; measured before/after on the 53 selectable files.
- Needs one deploy through [Hub] (code + `prior_coverage.csv`).
