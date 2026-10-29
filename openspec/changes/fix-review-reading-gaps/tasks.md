## 0. Before

- [x] 0.1 Before figures on the 53 selectable files (month count, periods, budget year, N-1 kinds kept), ids only, in ZWork

## 1. Reading rules

- [x] 1.1 `review_import.read_fund_sheet`: first run of twelve month columns, else the longest
- [x] 1.2 `review_measures.parse_period`: stated year over a full-year range of another year (approved / expected); note in `choose_measures`
- [x] 1.3 `review_import.read_fund_sheet`: Excel error remark becomes the reminder text
- [x] 1.4 `review_import.choose_fund_sheets`: staff-cost and night-shift sheets never MF/CA budget sheets
- [x] 1.5 `review_import.open_workbook`: release the source when reading the repaired copy (+ test)
- [x] 1.6 Tests for 1.1–1.4 on invented workbooks

## 2. Store and web

- [x] 2.1 `webapp/library.py`: `review_unread` reason from `prior_coverage.csv`; `build_prior_coverage.py` measures without it
- [x] 2.2 `webapp/static/index.html`: `#adj-prev` and `#adj-res-t` in a sideways-scrolling box
- [ ] 2.3 Rebuild `prior_coverage.csv`, copy into `_kho_quet`; tests for 2.1

## 3. Verify

- [x] 3.1 After figures on the same 53 files; every difference explained by one of the rules
- [x] 3.2 Full test suite, `openspec validate --all --strict`, `python verification/verify.py` PASS
- [x] 3.3 Local web at 400 px: adjust page tables do not overflow the page
- [ ] 3.4 Release note for [Hub]; after the deploy, Kho tab counts and one Review on the server
