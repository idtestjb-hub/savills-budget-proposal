## 1. Print-layout module (openpyxl layer)

- [x] 1.1 Write failing tests in `tests/test_print_layout.py` on a copy of the 2027 form, and confirm they fail for the
  right reason. They cover:
  - print area X2:BB526, A3 landscape, fit 1 wide, print titles 9:10, footer "Page &P of &N";
  - row 1 and A:W outside the area;
  - AC, AE, AF, AI folded at outline level 2 with their formulas unchanged.
- [x] 1.2 Write failing tests for the row rule, and confirm they fail. Cases:
  - a coded line with nothing is hidden;
  - a line with only a remark shows;
  - a line with only a prior approved figure shows;
  - a line with only a report figure shows;
  - a 0-valued plain roman-numeral group row (VI) shows;
  - a 0-valued dotted sub-group (V.1) hides;
  - stray text in X on a detail row does not force it visible;
  - rows 506–513 are hidden;
  - the AutoFilter is saved over A12:AW505 with "Use" and blank on column B.
- [x] 1.3 Write failing tests for the signature block, and confirm they fail:
  - exactly 8 boxes on rows 514–526, in the order and with the roles of the spec;
  - every merged span inside X:AO, with no overlap (spans may include folded columns);
  - no text left in AP:BB on those rows;
  - no name, only roles, the instruction and blank date lines.
- [x] 1.4 Implement `print_layout.apply(wb)` (design D1–D5, D7) with the fixed span table for the 8 boxes. Verify
  1.1–1.3 pass.

## 2. Wire into the generator and the adjust step

- [x] 2.1 Call `print_layout.apply(wb)` in `build_budget()` right after `budget_adjustment.apply` and `_add_pm_rows`,
  before `wb.save(local_out)`. Regenerate the fictional sample project. Open the result through Excel COM and verify:
  - no repair prompt;
  - no `#REF!`, `#DIV/0!` or `#VALUE!`;
  - rows hidden as expected;
  - the 8 boxes inside X:AO.
- [x] 2.2 Call `print_layout.apply(wb)` in `webapp/adjust_run.py` before `wb.save(deliverable)`. Verify with a test in
  `tests/test_webapp_adjust.py`: an edit that gives a hidden line an amount leaves that row visible after the save.
- [x] 2.3 Measure before and after on the fictional sample. Verify:
  - `1. Summary` totals, PART 1–3 totals and every coded amount are identical, so no figure moves;
  - the count of hidden rows is recorded in the change folder as `measure-before-after.md`.

## 3. Verification check

- [x] 3.1 Add a check to `verification/checks.py` and run it from `verify.py` on the recalculated copy. It confirms:
  - every row hidden in the file is "Not Use" in Excel's column B, or is in rows 506–513;
  - every "Not Use" coded row is hidden, except top-level section rows (D3);
  - hidden coded rows hold 0 or blank in AB:BB and no remark in AO;
  - the signature block is within X:AO.

  Verify it passes on the fictional sample, and fails on a copy where one hidden row is given an amount.

## 4. PDF export (Excel layer and web)

- [x] 4.1 Implement `print_layout.export_pdf(deliverable, paper, out)` and `webapp/print_run.py` (design D6):
  - copy, recalc, filter, forced top-level section rows, hidden rows 506–513 and columns AC/AE/AF/AI;
  - area and paper per button, fit 1 wide, titles 9:10, footer;
  - signature kept on one page, with the PyMuPDF fallback;
  - close without saving.

  Verify with an Excel-marked test, skipped when Excel is missing, on the fictional sample:
  - the A4 PDF has A4 landscape pages;
  - its last page holds "Đề xuất" once and "Phê duyệt" 7 times;
  - no page holds the text "TRUE";
  - the A3 PDF has 12 month headings;
  - the deliverable's modified time is unchanged.
- [x] 4.2 Add `POST /api/runs/{id}/print` (`paper` A4|A3) with a status poll, and output kind `deliverable_pdf` in
  `VIEWER_KINDS` (not in `SITE_HIDDEN_KINDS`). Plain Vietnamese errors for:
  - Excel missing;
  - the file open on the server (`~$`);
  - an export failure.

  Verify with tests in `tests/test_webapp_roles.py` and `tests/test_webapp_results.py`:
  - a viewer can export and download;
  - in site mode the PDF is listed;
  - the lock file gives the plain error.
- [x] 4.3 Add "PDF A4" and "PDF A3" buttons to the run result page, next to the deliverable download. Check in the
  browser on a local server: both buttons produce a PDF, the outputs list shows it, and the download opens.

## 5. Documentation and close

- [x] 5.1 Update the project documents:
  - `RUNNING.md`: the print setup, the PDF buttons and their Excel requirement;
  - `docs/09-template-map.md`: the signature rows and print rows;
  - `docs/05-decisions.md`: the 2026-11-11 choices (Not Use by column B, 4 folded columns, 8-box block from the
    approved sample with the Savills "Xem xét" box removed, file + web);
  - a short PM note in plain Vietnamese: how to reapply the column B filter, how to print A4 from Excel.

  Verify the documents contain no person names and no real budget amounts.
- [ ] 5.2 Have the Head of PM review one A4 and one A3 PDF of the fictional sample against the approved sample, and
  record the sign-off in `docs/project-status.md`. Only layout is affected, no figure.
- [x] 5.3 Run `python verification/verify.py` from `Budget_Agent/source_code/` and the full `pytest` suite. Both must
  pass.
