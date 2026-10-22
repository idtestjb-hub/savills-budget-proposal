## 1. Shared aggregate-row module

- [x] 1.1 Write failing tests in `tests/test_budget_rows.py` on small in-memory workbooks: a SUBTOTAL spanning a
  sibling (`RO4` over `RO4.x` + `RO5`), an aggregate caching 0, an array-formula SUBTOTAL, a typed-in parent equal to
  its children, a formula over non-coded rows, a `SUM` single-cell reference. Verify they fail for the right reason.
- [x] 1.2 Implement `budget_rows.py` (`find_aggregates`, `dropped`, `prefix_kids`, formula range parsing for SUBTOTAL 9/109 and
  SUM, normal and array formulas). Verify 1.1 passes.
- [x] 1.3 Add tie explanation (`explain_tie`): direct, filter (hidden rows with an auto-filter or more than half
  hidden), double count (SUM aggregate or a parent carrying its children's figure), both, none; Vietnamese notes as in the spec, with figures in VND. Write tests first, including
  a gap nothing explains. Verify they pass.

## 2. Budget Review reader

- [x] 2.1 Read formulas and hidden rows alongside values in `review_import` (same stripped copy when the original
  cannot be opened). `read_fund_sheet` uses `budget_rows` for leaves and the column tie. Verify the existing
  `tests/test_review_import.py` still passes unchanged.
- [x] 2.2 `choose_fund_sheets` prefers a visible sheet; the year column with R = 0 is passed over when another tying
  column has R ≠ 0. Tests first on a two-sheet workbook and a two-column sheet. Verify they pass.
- [x] 2.3 Explanation notes go to the import notes and to the printed source-file tie in `review.py`; an explained
  tie exits 0. Verify with a test on a fixture saved with a filter and one with a SUM parent.
- [x] 2.4 Re-run `probe_review_read.py` (in `Savills-local\budget-test\2026-10-21-p7\`) on MT EASTMARK, DRAGON HILL 2,
  GOLDEN MANSION and VEROSA PARK. Expected:
  - MT reads `2. Budget-THCN` with no double count of `RO4`;
  - DH2 ties after a filter;
  - GM ties after a double count (`RO2` carries `RO2a`'s figure);
  - VEROSA is unchanged.

  Record the output in `2026-10-21-p7\review_after.txt`.

## 3. Scan store rebuild (Savills-local, outside git)

- [x] 3.1 `v2\scan_budgets_v2.py` imports `budget_rows` from `source_code` and writes `tables_v3\`.
  - `reconcile.csv` gains the new states and a `note` column;
  - `build_final_v2.py` maps `ok*` to `high` and writes `final_v3\`;
  - the build log records the `budget_rows.py` commit.

  Back up both scripts beside themselves first.
- [x] 3.2 Run the rebuild, then compare v2 and v3. List every file whose tie state changed and every `fact_line` amount
  that moved, with file and code, in `scan-2026-10-07\v3_vs_v2.md`. Verify:
  - the three mismatching files change state as expected;
  - any other movement is explained line by line.
- [x] 3.3 Rebuild `Ref_RealBudgetValues.csv` from `final_v3` with `build_real_budget_ranges.py`. Record which projects
  joined or left and the median change per code.

## 4. Web library

- [x] 4.1 `webapp/library.py`: default store `final_v3`; label "Khớp tổng (đã giải thích)" with the note for `ok_filter`
  / `ok_double_count`. Tests first in `tests/test_webapp_library.py`. Verify they pass.

## 5. Before / after and sign-off

- [x] 5.1 Measure before (`main` before this change) and after on:
  - the three samples (`deliverable_baseline`);
  - the four real projects of the M3 runner (`2026-10-19-laneC-m3\run_m3.py`).

  The table lists every moved line with old and new figure (VND) and its cause, in
  `Savills-local\budget-test\2026-10-21-p7\before_after.md`.
- [x] 5.2 The user signs off the before/after (and takes it to the Head of PM if a deliverable line moves). Record the
  decision in `docs/05-decisions.md`.
- [x] 5.3 After sign-off, re-record the baselines once. Then `python verification/verify.py` from
  `Budget_Agent/source_code/` passes with the gates closed. Full `pytest` passes.
- [x] 5.4 Write the budget-web release note (`Savills-Automation-Hub-Setup\releases\`) for the store path and labels.
  Write the "Sẵn sàng deploy" line; the [Hub] session deploys.
