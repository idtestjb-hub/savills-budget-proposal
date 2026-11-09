## 0. Before starting

- [x] 0.1 Confirm `adjust-rows-for-zero-tool-codes` is archived (it changes the same sheet and table); verify with
  `openspec list` showing it under archive
- [x] 0.2 Record the "before": generate the standard sample and the City Garden Review at the current commit into an
  isolated copy, keep the per-code annual, F and 12-month figures of both fund sheets; verify the before tables exist
  in the measurement folder

## 1. Default frequency table

- [x] 1.1 Write `build_line_frequency.py` (office script): read the template's column C values other than Monthly and
  their month cells, plus the per-year counts the costing code prices with; write
  `data/generation_B_verified/Ref_LineFrequency.csv` (code, frequency, times, first_month, source, note); verify the
  file lists RO2a, ESC12 and ESM25 with a source on every row and no project name
- [x] 1.2 Show the table to the user and record the review (accepted rows, changed rows with the reason); verify the
  user's OK is noted in design.md "Measured"
- [x] 1.3 Add `line_frequency.py`: read the table, the month rule (first month + step inside the period, ranges per
  frequency), times per frequency, the Vietnamese sentence; verify `tests/test_line_frequency.py` covers the six
  frequencies, a July-start period, an out-of-range first month and each sentence

## 2. Generation writes the form's way

- [x] 2.1 In `generate_project_budget.py`, write C, D, F (per-time price = annual ÷ times) and H:S (row-8 month header
  references) for each line the table lists; Schedule lines and unlisted lines unchanged; verify a test that a
  defaulted ESM25 keeps 14,000,000 VND a year at 3,500,000 per time in T1, T4, T7, T10
- [x] 2.2 Add the frequency sentence to the remark of every non-Monthly line (deliverable-remarks rules); verify the
  remark tests and the internal-wording scan pass
- [x] 2.3 Excel COM check on the generated standard sample: U = 0 and V = TRUE on every written line of both fund
  sheets, no #VALUE!/#REF!/#DIV/0!; verify the check's output lists 0 failures

## 3. Sheet 4

- [x] 3.1 `adjustment_detail.py`: collect lines of every frequency, with original times, per-time price and months;
  verify a test that a template Half a Year line (RO2a) is listed with 2 times and its annual amount
- [x] 3.2 `budget_adjustment.py`: add AE..BF (new frequency, first month, times, 12 month inputs, helpers, original
  times) with the input validation lists; total-row M × new ÷ original times, Schedule = sum of month inputs; verify
  the scenarios of spec budget-adjustment-sheet in `tests/test_budget_adjustment.py`
- [x] 3.3 Fund-row link per design D4 (C, D, F, H:S formulas; U rewritten with SUMPRODUCT on linked rows); verify by
  Excel recalculation that a blank AE leaves every figure equal to the before file, and each of the five frequencies
  gives the spec's figures with U = 0 and V = TRUE
- [x] 3.4 Upgrade of an older sheet 4 on save (adds the cells, figures unchanged); verify with a deliverable from the
  installed City Garden package run
- [x] 3.5 `review.add_zero_rows`: take the table's default, keep a frequency the fund row has; verify a test with a
  zero-tool code listed as Yearly

## 4. Web adjust table

- [x] 4.1 `webapp/adjust.py`: read and write the new inputs, validation messages of spec budget-web-adjust-table,
  remark sentence replacement (design D8); verify `tests/test_webapp_adjust.py` new cases pass
- [x] 4.2 `webapp/static/index.html`: Tần suất column with Vietnamese and form labels, Tháng đầu list labelled with the
  period month, Optional tick boxes, Schedule amount cells, preview with the times ratio, the Schedule note; verify in
  the browser on a local run: pick Quarterly, save, reopen shows Quarterly and T3
- [x] 4.3 Preview equals Excel: a test saves one edit per frequency, recalculates through Excel COM and compares the
  web preview's new amount with column M; verify 0 differences

## 5. Verification, measurement and sign-off

- [x] 5.1 `verification/verify.py`: the U/V/frequency check on every written line and the five sheet-4 frequency edits
  on the standard sample (spec budget-workflow-verification); verify verify fails on a fixture with a three-month
  Quarterly line and passes on the real outputs
- [x] 5.2 Measure after vs before (0.2): annual figures equal on every code; list F and month changes per defaulted
  code; City Garden Review counts unchanged; write `summary.md` in the measurement folder; verify the table is complete
- [x] 5.3 User signs off the before/after (who: the user); then re-record the baselines once, with the reason; verify
  the sign-off is recorded in design.md "Measured"
- [x] 5.4 `site_data.py` KEEP gains `Ref_LineFrequency.csv`; docs (README module table, RUNNING, webapp/README, outer
  `docs/05-decisions.md` "Line frequency", `docs/project-status.md`); verify the site-package test and the
  name scan pass
- [x] 5.5 Full test suite and `python verification/verify.py`, run from Budget_Agent/source_code/, both pass; record
  the counts (2026-11-09: 1439 passed, 1 xfailed; verify.py PASS, new check OK 7 checks)
