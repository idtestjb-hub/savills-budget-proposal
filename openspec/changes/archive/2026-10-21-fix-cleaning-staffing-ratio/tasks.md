Rules decided by the user on 2026-10-19 (asked through the coordinator session P3): fee-paying NFA ÷ ratio, default
3,300, supervisors inside, a new small change. Measurements and logs go to
`Savills-local\budget-test\2026-10-19-laneC-cleaning\`. Real project names stay in `Savills-local`.

## 1. Build

- [x] 1.1 `generate_project_budget.py`: the ratio key `nfa_per_cleaning_staff` (default 3,300, new label, the old label
  not read, the reason when the field is missing), the `Cleaning - Common Area` rule of design D3, the ratio list on
  the deliverable. Verify with unit tests.
- [x] 1.2 `build_project_input_form.py`: Roster Setup row 6 becomes the new field (3,300 and its note), the Staffing
  Demand formula `MAX(1, ROUNDUP(fee NFA ÷ ratio) − ROUNDUP(towers ÷ towers per supervisor))` with its own note.
  `generate_project_output.py`: the Staffing Estimate description. Verify with unit tests that the formula and the
  Python rule give the same number.
- [x] 1.3 Run the full test suite and `verify.py` with the baseline gates open. Verify: all pass.
  - Done 2026-10-19: 904 passed, 1 xfailed; verify (gates open) PASS.

## 2. Measure and sign off

- [x] 2.1 A/B, before (`f8238ea`) and after, on the four fixtures (standard sample, Existing, Existing lump,
  Operating) and the four real projects of M3 (`run_m3.py`): cleaning people, `ESS4`, fund expense and surplus, the
  cleaning level on `Service Levels`. Verify: only cleaning-driven figures move.
  - Done 2026-10-19: fixtures move ESS4 +1,536.0M, ES# +30.7M, RI1 +8.1M (Operating +10.4M) and nothing else; standard
    sample 3 to 17 cleaning people on duty, surplus −1,558.6M. Real projects in `Savills-local/budget-test/2026-10-19-laneC-cleaning/task_log.md`.
- [x] 2.2 The user signs off the measured movement.
  - Signed off 2026-10-19 by the user, with the instruction to commit.
