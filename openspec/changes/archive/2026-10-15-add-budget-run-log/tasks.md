Sign-off: the user, standing in for the Head of PM. No budget figure moves, so the sign-off is on the record's contents
and on the run-time cost (task 5.3). Measurements run on the standard sample (`Sample_Project_Input.xlsx`) and on the
regression clone in `Savills-local\budget-test\`; scripts and logs go under `Savills-local\budget-test\<date>-<change>\`.
Records written by tests go to a temporary folder, never to the live `reports/run_log/`.

## 1. Confirm the cells (no code change)

- [x] 1.1 On the standard sample's finished deliverable, recalculated in Excel, list for the two fund sheets: the
  annual total column header, the section rows `R` and `E`, the VAT switch cell, and the Required leaf codes from
  `AI_Guideline_Required_Classification.csv`. Verify that the leaf count equals the "Required codes checked" count
  `verify.py` prints.
- [x] 1.2 On the finished analysis workbook, find the Summary labels *Total Profit Value*, *Mgmt Fee Revenue* and the
  *Cost Basis* dropdown. Record their exact texts in `design.md` (D4). Verify against a recalculated copy that
  Total Profit Value equals Mgmt Fee Revenue minus the selected staff, operating and capex costs.

## 2. The run-log module

- [x] 2.1 Create `run_log.py`: record fields (D5), file naming with the `-2`, `-3` suffix (D1), and the guard that
  turns any exception into a one-line `Run log:` warning (D6). Verify with unit tests on invented data: the file
  name for a name with accents and spaces, two records in the same second, a read-only folder, and a record that
  parses back to the same values.
- [x] 2.2 Add the Excel measurement on read-only temporary copies (D3, D4): Required counts with the three classes,
  revenue, expense, surplus, error cells, VAT basis, mode, year, and the analysis profit fields. Verify with unit
  tests on a small invented workbook built with formulas: filled / zero with reason / zero with no reason, the
  EMA1-4 disclosure on EMA15, a SUBTOTAL row excluded, a missing `R` row giving a blank and a named status.
- [x] 2.3 Make the no-Excel path write a record with blank figures and status `excel_unavailable`. Verify with a unit
  test that hides `win32com`.

## 3. Wire it into `run.py`

- [x] 3.1 Call `run_log.write(...)` in `main()` after the same-project check passes, wrapped so that no exception
  reaches the caller. Verify that a run whose analysis fails writes no record, and that the return code of a
  normal run is unchanged.
- [x] 3.2 Print one summary line after the DONE block: the record's file name, the completeness percentage, and the
  two profit figures (or the warning). Verify on the standard sample.

## 4. Verification

- [x] 4.1 Add the `verify.py` check (D7): record exists and parses; counts add up; surplus equals revenue minus
  expense; Required counts, revenue and expense equal the independent reading; read-only folder gives a warning
  and the same return code; no-Excel case. Verify that a planted wrong count makes the check fail and names it.
- [x] 4.2 Confirm `verify.py` leaves the live `reports/run_log/` folder as it found it. Verify by listing the folder
  before and after.

## 5. Measure and close

- [x] 5.1 Run the standard sample and the regression clone with and without the log call. Verify that every cell of the
  three workbooks is identical between the two runs, and that the baselines need no re-record. Record the extra
  seconds per run.
- [x] 5.2 Run `python verification/verify.py` from `Budget_Agent/source_code/`, and the full unit test suite. Verify
  that it passes on all sections and every test passes.
- [x] 5.3 Show the user one real record from the regression clone (figures, status, file name) and the measured extra
  run time, and record the sign-off in `design.md`.
- [x] 5.4 Update `RUNNING.md` (what the log folder is, how to read a record, what a blank figure means),
  `docs/project-status.md` and `docs/05-decisions.md`. Verify with `openspec validate --strict`.
- [x] 5.5 Write the hand-off for the dashboard: the record schema, the folder path in the library, and the example
  record, for the Hub web session. The page itself is a separate release.
