Rules decided by the user on 2026-10-19: fee-paying NFA ÷ 10,000 × ratio, gates and CCTV as the floor, default 1.7,
an older form's patrol row counted on all three shifts, pricing (7/6, night premium) unchanged. Measurements and logs
go to `Savills-local\budget-test\2026-10-19-laneC-security\`. Real project names stay in `Savills-local`.

## 1. Build

- [x] 1.1 `generate_project_budget.py`: the ratio key `posts24_per_10k_nfa` (default 1.7, new label, the old label not
  read), the patrol rule of design D1 on the three patrol rows, the older form's in-memory rows (D4), the ratio list on
  the deliverable. Verify with unit tests.
- [x] 1.2 `build_project_input_form.py`: Roster Setup row 5 becomes the new field (1.7 and its note), and Staffing
  Demand has three patrol rows with the formula. `generate_project_output.py`: the Staffing Estimate description.
  Verify with unit tests that the formula and the Python rule give the same number.
- [x] 1.3 Run the full test suite and `verify.py` with the baseline gates open. Verify: all pass.

## 2. Measure and sign off

- [x] 2.1 A/B, before and after, on the four fixtures and the four real M3 projects (`run_m3.py`): security posts,
  `ESS1`, fund expense and surplus, the security level on `Service Levels`. Verify: only security-driven figures move.
- [x] 2.2 The user signs off the measured movement (2026-10-20).
