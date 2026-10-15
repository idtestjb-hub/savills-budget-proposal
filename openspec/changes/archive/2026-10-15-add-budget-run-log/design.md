## Context

See proposal.md for the motivation. What shapes the approach:

- **`run.py`** runs `generate_project_budget.py` (deliverable + roster), then `generate_project_output.py` (analysis),
  then checks that both name the same project. Its `main()` is the one place where all three workbooks exist and are
  known to belong together.
- **The workbooks are written by openpyxl**, so their totals are live formulas with no cached values until Excel
  opens them. Any figure (revenue, expense, surplus, Required line amounts, Total Profit Value) therefore needs an
  Excel recalculation. `verification/checks.py` (`check_required_line_items`) already does this on a temporary copy
  with `CalculateFullRebuild` and reads `data/master_list_verified/AI_Guideline_Required_Classification.csv`.
- **The analysis workbook is overwritten on every run**; `sample_output/` keeps only deliverables.
- **Several PMs work on one SharePoint library** from different PCs. Appending to one shared file would create
  OneDrive conflict copies.
- **The outer repository** (`PM/Project`, holds `Budget_Agent/reports/`) has no remote; the inner repository
  (`source_code/`) is pushed to GitHub, so the records must not enter it.
- **Excel is used by verification only** today (RUNNING.md). Making a normal run depend on it would be a new
  dependency, so it must be optional.

## Goals / Non-Goals

**Goals:**
- One immutable record per complete run, readable by a dashboard without opening any workbook.
- Figures that equal what the PM sees when the workbook is opened in Excel.
- A run that is exactly as safe as before: no new way to fail.

**Non-Goals:**
- The dashboard page (Hub web flow, separate release).
- Back-filling the five existing deliverables. They have no analysis workbook, so profit would be blank; a later
  one-off script can add them if the dashboard needs them.
- Any change to a budget figure, a remark or a recorded baseline.
- Recording the roster, remarks or any per-person information.
- Tracking later edits a PM makes to a workbook by hand after the run.

## Decisions

### D1. One JSON file per run, in `reports/run_log/`
- **Chosen:** `Budget_Agent/reports/run_log/<yyyymmdd-hhmmss>_<project-slug>.json`, UTF-8, with a `schema` number.
  The slug is the project name folded to ASCII letters and digits, at most 40 characters.
- **Why:** no two runs share a file, so there is no append, no lock, and no OneDrive conflict copy when two PMs run at
  the same time. A file is never edited, so a sync can only add files.
- **Alternatives:** one shared CSV (rejected: conflicts and Excel locks); a SQLite file (rejected: binary, same
  conflict problem); recording in the Hub server only (rejected: runs happen on PM PCs).
- A second run in the same second adds `-2`, `-3`, and so on, to the name.

### D2. A new module, `run_log.py`, called once at the end of `run.py`
- `run.py` calls `run_log.write(...)` after the "both outputs describe the same project" check passes, and before
  the staffing and utility reports. The call is wrapped so that any exception becomes a warning (D6).
- The module takes plain paths (deliverable, analysis, input, log folder) so `verify.py` can point it at the
  synthetic project's redirected paths.
- The module does not import anything from `verification/`. It repeats the small Required-line rule that
  `check_required_line_items` uses, and `verify.py` cross-checks the two (D7).

### D3. Excel measurement on read-only temporary copies
- Copy the deliverable and the analysis to a temporary folder, open the copies read-only in a hidden Excel,
  `CalculateFullRebuild`, read the cells, close, quit in a `finally`. The output files are never opened by Excel, so
  a PM who has the deliverable open is not disturbed and nothing is locked.
- One Excel session reads both workbooks.
- If `pythoncom` or `win32com` is missing, or Excel cannot start, the record is written with the figures blank (D6).

### D4. How each figure is found (by label, as the generators do)
- **Required lines:** the Required leaf codes of `AI_Guideline_Required_Classification.csv` for the two fund sheets;
  a row is a leaf when its G formula is not a SUBTOTAL (the rule `verify.py` already uses). The amount is the annual
  total column; its column is found from the header text, not a fixed letter.
  - filled: amount above 0;
  - zero with a reason: amount 0 and a non-empty remark in the remarks column that is not a listed form placeholder
    (`_FORM_PLACEHOLDER_REMARKS`), including the EMA1-4 disclosure on EMA15;
  - zero with no reason: the rest.
  - This is the same classification `verify.py` applies, except that a zero with a reason counts as not complete
    (user's decision, 2026-10-13).
- **Revenue, expense, surplus:** the section total rows coded `R` and `E` on `2. Budget-Management Fund`, annual
  total column; surplus is R minus E computed by the module. Figures are in the deliverable's own VAT basis, which
  the record states (read from the VAT switch on the fund sheet, as `verify.py` does).
- **Error cells:** count of cells on the deliverable whose recalculated value is an Excel error.
- **Savills profit:** the cell the analysis Summary labels *Total Profit Value*, the *Mgmt Fee Revenue* it is measured
  on, and the *Cost Basis* dropdown value. The labels are found by text in column A. If a label is missing the field
  is blank and the status names it.
- **Mode and year:** New prospect or Existing from `Project Info`; budget year from the fund sheet header.

**Confirmed against a recalculated finished workbook (tasks 1.1 and 1.2, 2026-10-13, regression clone):**
- The amount of every line, and of the `R` and `E` section rows, is column G (`Total Price`); on the section rows it
  equals the annual total column AK. Column G is used because `verify.py` reads it, so the two readings share a cell.
- The Required leaf lines on the two fund sheets number 118 on the standard form; `verify.py` reports the same 118 as
  passing (its 169 includes group rows that are skipped). A code that appears on both fund sheets counts once per sheet.
- Analysis `Summary` labels, column A with the figure in column B: `View:` (the cost basis), `Total Profit Value =`
  (text continues; the figure sits in B on the same row) and `(3) Annual Management Fee Revenue (VND)`.
- The VAT switch is `2. Budget-Management Fund!F7`: `KHOÁN` means the amounts exclude VAT, any other value inclusive.
- The budget year is the cell right of the header cell that starts `Budget Year` in row 5 of the fund sheet.
- Measured extra run time: about 20 seconds (Excel opens a copy of each of the two workbooks once).

### D5. Record fields
`schema`, `run_id`, `run_time_local`, `project_name`, `project_mode`, `stable_operation`, `budget_year`,
`deliverable_file`, `vat_basis`, `required_total`, `required_filled`, `required_zero_with_reason`,
`required_zero_no_reason`, `required_missing_from_deliverable`, `required_pct`, `revenue_vnd`, `expense_vnd`,
`fund_surplus_vnd`, `savills_profit_vnd`, `mgmt_fee_revenue_vnd`, `profit_cost_basis`, `error_cells`, `status`
(`ok` or a short reason such as `excel_unavailable` or `missing_label:Total Profit Value`).
Percentages are stored as fractions with the counts beside them, so a page can recompute them.

### D6. Failure policy: warn, blank, carry on
- Every step of the measurement and the write sits inside one guard. A caught problem prints one line starting
  `Run log:` and never changes the return code of `run.py`.
- A figure that could not be read is `null`, never 0, so a dashboard cannot mistake it for a real zero.
- If the folder cannot be written, no record is written and the warning says so.
- **Alternative:** stop the run on a log failure. Rejected: the log is a by-product and must not block a PM from
  getting a budget.

### D7. How `verify.py` checks it
- A new check runs the module on the synthetic project's redirected outputs into a temporary log folder and
  asserts: the file exists and parses; the three counts add up to the total; surplus equals revenue minus expense;
  and the Required counts, revenue and expense equal the same values obtained through
  `check_required_line_items`' own reading and a direct Excel read.
- A second case makes the log folder read-only and asserts a warning and an unchanged return code.
- A third case simulates "no Excel" and asserts blank figures with status `excel_unavailable`.
- The check never touches the live `reports/run_log/`.

### D8. Invented names in tests and specs
Tests and specs use invented project names. Real names appear only in records written in the library.

## Risks / Trade-offs

- **[Extra run time]** one more Excel recalculation (the deliverable is about 1.3 MB) → measured in task 5.1; if it
  exceeds one minute, make the measurement start in the background while the PM reads the console summary.
- **[Two copies of the Required rule]** `run_log.py` and `check_required_line_items` could drift apart → D7 compares
  them on every `verify.py` run.
- **[The Total Profit Value depends on the PM's Cost Basis toggle and fill assumptions]** two PMs can get different
  profit for the same project → the record stores the cost basis and the management fee revenue beside it, and
  the dashboard shows the basis.
- **[The record describes the run, not later hand edits]** a PM who edits the workbook afterwards changes figures
  the log never sees → stated in the dashboard's footnote; a re-run writes a new record.
- **[An old PC without Excel gives blank records]** → status says why; the dashboard counts such runs as "not measured".
- **[Real names in records]** → they stay in the library and the outer repository (no remote); the Hub page removes
  nothing, so access to it follows the library's.

## Open Questions

- Whether the Hub page should hide runs of test projects (names such as the sample). A simple `is_test` flag could be
  added to the record later; not needed now.
- The exact label texts on the analysis Summary sheet are confirmed in task 1.2 against a real analysis workbook; the
  design only fixes that they are found by label.

## Sign-off (task 5.3)

2026-10-15: the user, standing in for the Head of PM, accepted the record's contents (a real record from the regression
clone: 118 Required lines, 50 filled / 68 zero with reason / 0 without reason, fund surplus and Savills profit
reported separately, status `ok`) and the run-time cost. Measured extra time per run: 14 s on the standard sample,
about 40 s on the clone (one pair of runs each, Excel started cold). Output workbooks identical cell by cell with and
without the log (1.5 million cells per case); `verify.py` PASS; 603 unit tests pass.
