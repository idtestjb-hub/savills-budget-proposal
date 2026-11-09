## 1. Remark-only fix edit

- [x] 1.1 `webapp/adjust.py`: `fixed_remark(item, current)` = `lf.with_sentence(current, freq_sentence(item))`; test
  on Quarterly→Half a Year, Monthly (sentence removed), no sentence yet (appended), PM text kept
- [x] 1.2 `apply_edits`: an edit `{key, fix_remark: true}` validates the key only, re-checks `remark_stale` on the saved
  state, writes column T only, skips sheet 4 and `_pm_remark`; formula remark → skipped with reason; returns fixed and
  skipped codes to the caller (D4)
- [x] 1.3 `_write_freq`: keep a formula remark and report the code as skipped (D3); test
- [x] 1.4 Test: a workbook with three lines changed offline (TEST DATA sample) → fix → no line `remark_stale`, every
  sheet-4 cell equal before/after (cell-by-cell compare), only the three T cells differ

## 2. Save path and result

- [x] 2.1 `webapp/adjust_run.py`: `adjust_result.json` and the saves history carry `remarks_fixed` (count, codes) and
  `remarks_skipped` (code, reason); log line "[2/3] … cập nhật remark n dòng"
- [x] 2.2 Test through `adjust_run.py` on the sample with Excel: R / E / surplus of both funds equal before/after;
  backup file written; no Excel error cell

## 3. Web

- [x] 3.1 `index.html`: button "Cập nhật remark (n dòng)" beside the save button, shown only when n ≥ 1; locked while
  any row is dirty or a save runs (tooltip); posts `{key, fix_remark: true}` for every flagged key; follows the job as
  the save button does
- [x] 3.2 Result text "Đã cập nhật remark n dòng" and the skipped codes
- [x] 3.3 Browser check on a TEST DATA run (local web on a free port): change three frequencies offline in Excel,
  reload, press the button, confirm the remarks, no flag, totals unchanged; stop the local web afterwards
  (2026-11-09, P28: ZZ Sample Tower run, ESM25 → Half a Year, ESC12 → Yearly T6, ESM3 → Monthly; button "Cập nhật
  remark (3 dòng)", locked with an unsaved inflation; after 27 s "Đã cập nhật remark 3 dòng", no flag left; Excel
  totals of the backup (state before the button) and after are equal to the VND on both funds, 0 error cells)

## 4. Close

- [x] 4.1 Figures: none move (no generator change); state it in the report with the before/after totals of 2.2 and
  3.3. Sign-off by the user. (2026-11-09, P28: fund totals before/after the button equal to the VND on both funds;
  the user asked to archive after that report)
- [x] 4.2 `python verification/verify.py` from `Budget_Agent/source_code/` passes (2026-11-09, P28: PASS)
