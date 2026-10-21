Rules chosen by the user on 2026-10-20 before any code (design D2, D3, D6, D7): the year column as the approved
figure, the deliverable's VAT basis with the approved figure converted per line, no copying of an approved figure
where the tool has no method, fee rates, parking revenue and collect-on-behalf amounts taken from the file. Measurements, logs and the real
project's name go to `Savills-local\budget-test\2026-10-20-laneC-review\`; nothing real enters the repository.

## 1. Read the approved budget (review_import.py)

- [x] 1.1 `read_prior_budget(path)`: open (stripped copy on a defined-name failure), choose the two fund sheets by
  name, find the code and indicator columns, the R / E / PL1 / PL2 anchors, the leaf rows, the value column that
  ties, the month columns and the VAT basis; return the lines with flags and the sheet's own R and E figures
  (design D1, D2). Verify with unit tests on an invented workbook built by the test (D12): ties, the untied second
  column ignored, a line whose months disagree flagged, a line without a code, PDF and xlsb refused.
- [x] 1.2 `read_info(wb)`: products (NFA, units, rate, VAT basis), parking bays, project name, from `0. Info`
  (D7). Verify with a unit test on an invented Info sheet; a missing row gives a blank and a note.
- [x] 1.3 `template_codes()`: the codes of each fund sheet of the 2027 template, cached; `CODE_ALIASES` empty;
  `METHOD_VI` from the catalogue's method keys (D4, D6). Verify: every catalogue method has a Vietnamese text (test).

## 2. Fill the Existing-project form

- [x] 2.1 `write_form(prior, info, facts, template_form, out_path)`: a fresh form or a dated copy, the Existing
  fields and sheets added as `add_existing_project_sheets` does, `Project Info` filled (D7), `STAFF LINES`,
  `UTILITY LINES`, the `Prior-Year Budget` sheet with `IMPORT NOTES` (D8). Verify with a unit test on the standard
  fixture: the labels read back through `existing_staffing.read_existing()` and `existing_utilities.read_utilities()`
  without error, the original fixture's bytes unchanged, every blank scale field listed in the notes.
- [x] 2.2 `read_prior_budget_sheet(wb)`: the sheet read back by block title and header (D8). Verify: a round trip
  in the test of 2.1 returns the same lines.

## 3. The Review sheet and the command (review.py)

- [x] 3.1 `tool_lines(deliverable)`: Excel recalculation of a copy, leaf rows and R / E rows of both fund sheets,
  the VAT basis from `F7` (D5). Verify on the standard sample's deliverable in a temporary folder: the leaf sums tie
  to R and E (one test, skipped without Excel).
- [x] 3.2 `build_review_sheet(wb, prior_lines, tool, labels, meta)`: the sheet of design D9, with the VAT
  conversion of D3, the labels of D6 and the subtotals. Verify with a unit test on dictionaries of figures: the
  converted figures of the spec's scenarios, the labels, the section subtotals, no Excel needed.
- [x] 3.3 `main()`: the command of D10 on `verification.isolation.redirected_paths`, the two ties with a non-zero
  exit on failure, the printed summary, `review_summary.md` and `.json`. Verify: a test runs it on the Existing
  fixture plus an invented approved-budget workbook in a temporary folder (skipped without Excel) and checks the live
  files are unchanged and the ties print.
- [x] 3.4 `RUNNING.md`: a section "2d. Budget Review of an operating project" (the command, what it fills, what it
  leaves blank, what is not in this MVP). `README.md` of source_code: the two new modules in the module map.

## 4. Measure and sign off

- [x] 4.1 `pytest tests` and `verify_gate_open.py` (background, about 15 minutes) pass; the gate-open log goes to the
  measurement folder.
- [x] 4.2 A/B before (7907742) and after on the standard sample and the five fixtures: no differing cell on any
  sheet that existed before (D11). Log in the measurement folder.
- [x] 4.3 Demo run on the real 2026 file chosen by the coordinating session (its `file_id` is in the M3 config;
  facts the file lacks from the M3 facts file), in the measurement folder: the Review sheet, the two ties, the summary
  (revenue, expense, surplus approved vs tool; the ten largest differences; lines read, with a figure, not on the
  form, unreadable). `task_log.md` on the model of the security change's log.
- [x] 4.4 The user signed off the Review sheet's shape and the demo figures (2026-10-20); commit on lane-c when the user says so;
  the hash goes to the coordinating session. Then `python verification/verify.py` from `Budget_Agent/source_code/`
  passing (the recorded gates stay open until group 10 re-records them).
