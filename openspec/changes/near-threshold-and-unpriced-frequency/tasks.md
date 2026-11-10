## 1. Table builder

- [x] 1.1 `build_line_frequency.py`: add `USER_FREQUENCIES` (ESC2, ESC3, ESS7, EMA18, all Yearly) with the note of D1.
  A code in both exception lists stops the build. Verify: a unit test on a TEST DATA votes file. Under the rule alone
  the near-threshold code is not listed; with the list it is Yearly, with counts in the source and the note.
- [x] 1.2 Rebuild the table on the office machine from the saved raw read (`--from-votes`, cwd in ZWork), keeping the
  old file as `Ref_LineFrequency.csv.backup-<date>`. Verify: 15 rows (11 + the four), leak check clean, and the
  user reviews the four new rows.

## 2. Unpriced rows

- [x] 2.1 `_apply_line_frequencies`: widen the "no price" shape to a Monthly row with F blank or 0 (not a formula) of a
  listed code that is not in `_PM_LINES` (D2).
  - Verify the unpriced row with unit tests: C becomes the table's frequency, the months are marked, F = 0 (blank too),
    the remark is unchanged, and U = 0.
  - Verify the rows that must not change: a PM line stays as before, and a Schedule row and an unlisted code are
    untouched.
- [x] 2.2 Run the full test suite and `python verification/verify.py`. Verify: all tests pass and verify.py reports
  PASS (the baselines may differ, see 3.3).

## 3. Measure and sign off

- [x] 3.1 Measure before/after on the 5 fixtures and the M3 real-project runs (recipe of
  `default-frequency-from-real-budgets`; `M3_DATA_OVERLAY` for the data-only A/B).
  - List every row that moves: code, C, F, months, annual VND and remark.
  - Compare the annual totals of both funds and `1. Summary`. Expect only per-time rounding.
  - Report in `Savills-local\backups\budget-agent\<date>-near-threshold-measure\summary.md`.
- [x] 3.2 Check one generated sample in Excel. Verify: no error cell, ESA16 (or another unpriced listed row) shows
  Yearly with T1 marked and U = 0, and one of the four codes, when priced, is paid once in T1 with the annual amount
  unchanged.
- [x] 3.3 Get the user's sign-off on the before/after, then re-record the three baselines once. Verify: `baseline.py`
  and verify.py PASS after re-recording.
